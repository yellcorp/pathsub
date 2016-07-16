from .core import MOVE, COPY, LOG_ERROR, LOG_INFO, LOG_DEBUG, pathsub, __version__
from .plan import resub_string_iterator, resub_basename_iterator

import argparse
import collections
import re
import sys

from pprint import pprint


DOC_DATA = {
    MOVE: dict(
        other=COPY,
        name="submv",
        verb="rename or move",
        verbing="renaming or moving",
        description="""Rename or move files by performing find-replace
                       operations on their paths."""
    ),
    COPY: dict(
        other=MOVE,
        name="subcp",
        verb="copy",
        verbing="copying",
        description="""Copy files by performing find-replace
                       operations on their paths."""
    )
}

def get_arg_parser(my_strings, other_strings):
    p = argparse.ArgumentParser(
        description=my_strings['description'],
        epilog="""To {other_verb} files instead of {verbing} them, use
                  {other_script}.""".format(
                      other_verb=other_strings['verb'],
                      verbing=my_strings['verbing'],
                      other_script=other_strings['name']
                  )
    )

    p.add_argument("search",
        metavar="SEARCH",
        help="""The regular expression, or string if -l/--literal is specified,
                to match"""
    )

    p.add_argument("replace",
        metavar="REPLACE",
        help="""The replacement string. If SEARCH is a regular expression, the
                content of capturing groups can be used by including \\#,
                \\g<#>, where # is a number, or \\g<NAME>, where NAME is the
                name of a named group."""
    )

    p.add_argument("paths",
        metavar="PATH", nargs="+",
        help="""The files to {}.""".format(my_strings['verb'])
    )

    p.add_argument("-b", "--basename",
        action="store_true",
        help="""Restrict the find/replace to just the file's name - that is,
                the part of the path after the last path separator."""
    )

    p.add_argument("-l", "--literal",
        action="store_true",
        help="""Match the search string as specified, rather than interpreting
                it as a regular expression."""
    )

    p.add_argument("-i", "--ignore-case",
        action="store_true",
        help="""Case-insensitive matching of strings or regular expressions."""
    )

    p.add_argument("-p", "--plan",
        action="store_true",
        help="""Show the intended changes without making them. Because this
                mode doesn't query the filesystem, conflicts can only be
                detected when files share exact paths. The actual operation may
                have more conflicts due to pre-existing files,
                case-insensitivity or unicode normalization."""
    )

    p.add_argument("-t", "--trial",
        action="store_true",
        help="""Make changes, but immediately roll them back when complete.
                This can serve as a more accurate preview than the
                -p/--plan option."""
    )

    p.add_argument("-v", "--verbose",
        action="store_true",
        help="""Show each move, rename or copy as it is performed."""
    )

    p.add_argument("--debug",
        action="store_true",
        help="""Show every filesystem operation as it is performed, including
                intermediate ones and rollbacks."""
    )

    p.add_argument("-q", "--quiet",
        action="store_true",
        help="""Suppress all output, including errors."""
    )

    # TODO: add recurse option, but unless i can figure it out we will also need
    # to force --basename - AND disable mkdir

    # or maybe just use GNU find?

    p.add_argument("--version",
        action="version",
        version="%(prog)s " + __version__
    )

    return p


def show_plan(src_dest_iter, operation, out_stream=sys.stdout):
    verb = "move" if operation == MOVE else "copy"

    sources = set()
    conflicts_dict = collections.OrderedDict()

    for src, dest in src_dest_iter:
        if operation == COPY:
            sources.add(src)
        if src == dest:
            continue
        if dest not in conflicts_dict:
            conflicts_dict[dest] = [ ]
        conflicts_dict[dest].append((src, dest))

    non_conflicts = [ ] # [ (src, dest) ... ]
    conflicts = [ ] # [ (conflict_path, [ (src, dest) ... ] ... ]

    for path, operations in conflicts_dict.items():
        if len(operations) == 1 and operations[0][1] not in sources:
            non_conflicts.extend(operations)
        else:
            conflicts.append((path, operations))

    for src, dest in non_conflicts:
        print("{} {} to {}".format(verb, src, dest), file=out_stream)

    for conflict_path, operations in conflicts:
        reasons = [ ]
        if len(operations) > 1:
            reasons.append("they share the same target name")
        if operations[0][1] in sources:
            reasons.append("the target name already exists")

        print(
                "\n# The following {operations_conflict} because {reasons}:".format(
                operations_conflict = (
                    "operation conflicts" if len(operations) == 1 else
                    "operations conflict"
                ),
                reasons = ", and ".join(reasons)
            ),
            file=out_stream
        )
        for src, dest in operations:
            print("{} {} {}".format(src, symbol, dest), file=out_stream)

    return 0 if len(conflicts) == 0 else 1


def run(operation, argv=None):
    my_strings = DOC_DATA[operation]
    other_strings = DOC_DATA[my_strings["other"]]

    p = get_arg_parser(my_strings, other_strings)
    args = p.parse_args(argv)

    if args.literal:
        pattern = re.escape(args.search)
    else:
        pattern = args.search

    re_flags = 0
    if args.ignore_case:
        re_flags |= re.IGNORECASE

    if args.basename:
        iterator_func = resub_basename_iterator
    else:
        iterator_func = resub_string_iterator

    iterator = iterator_func(pattern, args.replace, args.paths, re_flags)

    if args.debug:
        log_level = LOG_DEBUG
    else:
        log_level = LOG_ERROR - int(args.quiet) + int(args.verbose)

    if args.plan:
        show_plan(iterator, operation=operation)
        return 0
    else:
        if args.trial and log_level < LOG_INFO:
            log_level = LOG_INFO

        success = pathsub(
            iterator,
            operation=operation,
            trial=args.trial,
            log=log_level
        )

        return 0 if success else 1


def submv_main():
    return run(MOVE, sys.argv[1:])


def subcp_main():
    return run(COPY, sys.argv[1:])
