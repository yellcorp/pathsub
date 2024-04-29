import argparse
import base64
import enum
import functools
import os
import random
import re
import sys
import traceback
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from shlex import quote

from .agents import Agent, Executive, HistoryAgent, RollbackError

__version__ = "0.0.5"

from .fs import ensure_dir_for

HELP_PUNCT = {
    "/": "slash",
    "\\": "backslash",
}


@dataclass
class CliArgs:
    search: str
    replace: str
    paths: list[str]
    basename: bool
    literal: bool
    ignore_case: bool
    dry_run: bool


def make_arg_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Rename or move files by performing find-replace operations on their paths.",
    )

    p.add_argument(
        "search",
        metavar="SEARCH",
        help="""
            The regular expression to match, unless -l/--literal is
            specified, in which case this is interpreted as the
            literal text to match.
        """,
    )

    p.add_argument(
        "replace",
        metavar="REPLACE",
        help="""
            The replacement string. If SEARCH is a regular expression
            (that is, if -l/--literal is not specified), capturing
            groups can be referenced by index with \\N or \\g<N>, or
            by name with \\g<NAME>. For more detail see the
            Python documentation for `re.sub`, specifically the `repl`
            argument.
        """,
    )

    p.add_argument(
        "paths",
        metavar="PATH",
        nargs="+",
        help="The files or directories to rename or move.",
    )

    punct_name = HELP_PUNCT.get(os.sep, "path separator")
    p.add_argument(
        "-b",
        "--basename",
        action="store_true",
        help=f"""
            Change only the basename of the file - that is, the part
            of the path after the last {punct_name}.
        """,
    )

    p.add_argument(
        "-l",
        "--literal",
        action="store_true",
        help="""
            Match the search string as specified, rather than
            interpreting it as a regular expression.
        """,
    )

    p.add_argument(
        "-i",
        "--ignore-case",
        action="store_true",
        help="""
            Case-insensitive matching of strings or regular
            expressions.
        """,
    )

    p.add_argument(
        "-n",
        "--dry-run",
        action="store_true",
        help="""
            Show the intended changes without making them. Different
            files that would end up with identical paths are reported
            as conflicts. This does not query the file system, so only
            exactly identical paths count as conflicts - your OS and
            file system may apply further restrictions such as case
            insensitivity or Unicode normalization. Such conflicts are
            only detected when trying to actually rename the files.
        """,
    )

    # TODO: recursion?

    p.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )

    return p


def make_pattern(expr: str, literal: bool, ignore_case: bool) -> re.Pattern:
    pattern = re.escape(expr) if literal else expr
    return re.compile(pattern, flags=re.IGNORECASE if ignore_case else 0)


def resub_basename(pattern: re.Pattern, repl: str, subject: str) -> str:
    parent, leaf = os.path.split(subject)
    new_leaf = pattern.sub(repl, leaf)
    return os.path.join(parent, new_leaf)


def resub_path(pattern: re.Pattern, repl: str, subject: str) -> str:
    return pattern.sub(repl, subject)


@dataclass(slots=True)
class TargetNameRecord:
    target_path: str
    src_paths: list[str]


@dataclass(slots=True)
class Plan:
    valid_moves: list[tuple[str, str]]
    conflicts: list[tuple[list[str], str]]

    @property
    def has_conflicts(self):
        return len(self.conflicts) > 0


def make_plan(map_path: Callable[[str], str], paths: Sequence[str]) -> Plan:
    namespaces: dict[str, dict[str, TargetNameRecord]] = {}
    plan = Plan([], [])

    for src_path in paths:
        target_path = map_path(src_path)
        if target_path == src_path:
            continue

        target_parent, target_leaf = os.path.split(target_path)
        namespace = namespaces.setdefault(target_parent, {})

        tnr = namespace.get(target_leaf)
        if tnr is None:
            namespace[target_leaf] = TargetNameRecord(target_path, [src_path])
        else:
            tnr.src_paths.append(src_path)

    for namespace in namespaces.values():
        for tnr in namespace.values():
            if len(tnr.src_paths) == 1:
                plan.valid_moves.append((tnr.src_paths[0], tnr.target_path))
            else:
                plan.conflicts.append((tnr.src_paths, tnr.target_path))

    return plan


def print_plan(plan: Plan):
    for src, dest in plan.valid_moves:
        print(f"  {quote(src)} → {quote(dest)}")

    if plan.has_conflicts:
        print(
            "\nThe following operations conflict because they share the same target name:"
        )
        for srcs, dest in plan.conflicts:
            print(f" {quote(dest)}")
            for src in srcs:
                print(f"  {quote(src)} → {quote(dest)}")

    if len(plan.valid_moves) == 0 and not plan.has_conflicts:
        print(
            "Nothing to do - either nothing matched, or all replacements resulted in no change."
        )


def generate_temp_name(path: str):
    stem, suffix = os.path.splitext(path)
    some_bytes = random.randbytes(5)
    some_text = base64.b32encode(some_bytes).decode("ascii")
    return f"{stem}__submv{some_text}{suffix}"


@dataclass(slots=True)
class DeferredMove:
    src_path: str
    temp_path: str
    target_path: str


class CommitError(Exception):
    def __init__(self, message: str, failed_move: tuple[str, str] | None = None):
        super().__init__(message)
        self.failed_move = failed_move

    @classmethod
    def from_failed_move(cls, src: str, dest: str):
        return cls(f"Error moving {src!r} to {dest!r}", (src, dest))


def perform_moves(map_path: Callable[[str], str], paths: Sequence[str], agent: Agent):
    defer: list[DeferredMove] = []

    for src_path in paths:
        target_path = map_path(src_path)
        ensure_dir_for(target_path, agent)
        try:
            print(
                "mv {src} {dest}".format(src=quote(src_path), dest=quote(target_path))
            )
            agent.move(src_path, target_path)
        except (FileExistsError, IsADirectoryError):
            temp_path = generate_temp_name(src_path)
            agent.move(src_path, temp_path)
            defer.append(DeferredMove(src_path, temp_path, target_path))
        except Exception as other_error:
            raise CommitError.from_failed_move(src_path, target_path) from other_error

    for deferred in defer:
        try:
            agent.move(deferred.temp_path, deferred.target_path)
        except Exception as other_error:
            raise CommitError.from_failed_move(
                deferred.src_path, deferred.target_path
            ) from other_error


def print_exception(some_error: Exception, file):
    if isinstance(some_error, OSError):
        # Likely a simple or common error, so don't bother with the stack trace
        print(some_error, file=file)
    else:
        # Something more serious or obscure
        traceback.print_exception(some_error, file=file)


class CommitResult(enum.Enum):
    SUCCESS = 0
    FAILED_WITH_SUCCESSFUL_ROLLBACK = 1
    FAILED_WITH_NONCRITICAL_ROLLBACK = 2
    FAILED_WITH_FAILED_ROLLBACK = 3


def commit(
    map_path: Callable[[str], str],
    paths: Sequence[str],
) -> CommitResult:
    agent = Executive()
    history = HistoryAgent(agent)

    perror = functools.partial(print, file=sys.stderr)
    perror_exc = functools.partial(print_exception, file=sys.stderr)

    try:
        perform_moves(map_path, paths, history)
        return CommitResult.SUCCESS
    except CommitError as commit_error:
        perror("\nError during move:")
        if commit_error.failed_move is not None:
            failed_src, failed_dest = commit_error.failed_move
            perror(f"  mv {quote(failed_src)} {quote(failed_dest)}\n")

        perror_exc(commit_error.__cause__)
        perror("\nRolling back...")

        try:
            non_critical_errors = history.rollback()
        except RollbackError as rollback_error:
            perror("Error during rollback:")
            perror_exc(rollback_error.__cause__)
            perror("\nRollback failed.")
            perror("Perform the following operations to restore the original state:")
            for op in rollback_error.remaining_operations:
                perror(f"  {op}")
            return CommitResult.FAILED_WITH_FAILED_ROLLBACK

    perror("Rollback complete.")
    if len(non_critical_errors) > 0:
        perror("Non-critical errors occurred during rollback:")
        for path, error in non_critical_errors:
            perror(f"  {path}: {error}")
        return CommitResult.FAILED_WITH_NONCRITICAL_ROLLBACK

    return CommitResult.FAILED_WITH_SUCCESSFUL_ROLLBACK


def run(args: CliArgs) -> int:
    pattern = make_pattern(args.search, args.literal, args.ignore_case)
    apply_func = resub_basename if args.basename else resub_path

    def map_path(src_path: str) -> str:
        return apply_func(pattern, args.replace, src_path)

    if args.dry_run:
        print(
            "Showing plan because --dry-run was specified.\n"
            "No changes will be made.\n"
        )
        plan = make_plan(map_path, args.paths)
        print_plan(plan)
        return 1 if plan.has_conflicts else 0

    status = commit(map_path, args.paths)
    return status.value


def main() -> int:
    p = make_arg_parser()
    args = CliArgs(**vars(p.parse_args()))
    return run(args)


def call_main_and_exit():
    sys.exit(main())
