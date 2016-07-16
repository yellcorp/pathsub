from textwrap import dedent

import os
import shutil
import sys
import tempfile


LOG_NONE =  0
LOG_ERROR = 1
LOG_INFO =  2
LOG_DEBUG = 3

__version__ = "0.0.2"
__all__ = [
    "move", "copy",
    "LOG_NONE", "LOG_ERROR", "LOG_INFO", "LOG_DEBUG"
]


class FSItem(object):
    def __init__(self, src_path, dest_path):
        self.src_path = src_path
        self.dest_path = dest_path
        self.current_path = src_path

    def __repr__(self):
        return "FSItem({0.src_path!r}, {0.dest_path!r})".format(self)

    def __str__(self):
        return "<FSItem src_path={0.src_path!r} dest_path={0.dest_path!r} current_path={0.current_path!r}>".format(self)


class OperationError(Exception):
    def __init__(self, description, path, user_message=None):
        super(OperationError, self).__init__(description, path)
        self.description = description
        self.path = path
        self.user_message = user_message or "{}: {}".format(description, path)


def log_method(method):
    def wrapped(self, *args):
        if self.log_stream is not None:
            print("{} {}".format(
                method.__name__, " ".join(repr(a) for a in args),
                file=self.log_stream
            ))
        return method(self, *args)
    return wrapped

class Agent(object):
    def __init__(self, log_stream):
        self.log_stream = log_stream

    @log_method
    def mv(self, src, dest):
        shutil.move(src, dest)

    @log_method
    def cp(self, src, dest):
        shutil.copy2(src, dest) 

    @log_method
    def rm(self, path):
        os.remove(path)

    @log_method
    def mkdir(self, path):
        os.mkdir(path)

    @log_method
    def rmdir(self, path):
        os.rmdir(path)


class Logger(object):
    def __init__(
        self,
        error_stream = sys.stderr,
        info_stream  = sys.stdout,
        debug_stream = None
    ):
        self.error_stream = error_stream
        self.info_stream  = info_stream
        self.debug_stream = debug_stream

    def error(self, message):
        if self.error_stream:
            print(message, file=self.error_stream)

    def info(self, message):
        if self.info_stream:
            print(message, file=self.info_stream)

    def debug(self, message):
        if self.debug_stream:
            print(message, file=self.debug_stream)


def make_conflict_error(attempted_item, blocking_item):
    if attempted_item.dest_path == blocking_item.dest_path:
        problem = "the same name"
    else:
        problem = "names that the filesystem prohibits from coexisting in the same directory"

    user_message = dedent("""\
        The following rename operations result in {problem}:
          {attempted.src_path} -> {attempted.dest_path}
          {blocking.src_path} -> {blocking.dest_path}
        """.format(
            problem=problem,
            attempted=attempted_item,
            blocking=blocking_item
        )
    )

    return OperationError("Path exists", blocking_item.dest_path, user_message)


def make_uninvolved_error(attempted_item):
    user_message = dedent("""\
        Can't perform the following rename as a file or directory with the new name already exists:
          {attempted.src_path} -> {attempted.dest_path}
    """.format(
            attempted=attempted_item
        )
    )
    return OperationError("Path exists", attempted_item.dest_path, user_message)


def generate_path(basis_path):
    dirname, basename = os.path.split(basis_path)
    fh = tempfile.NamedTemporaryFile(prefix=basename + "_", dir=dirname, delete=False)
    name = fh.name
    fh.close()
    return name


def format_exception(exc):
    if hasattr(exc, "user_message"):
        return exc.user_message
    return str(exc)


UNINVOLVED = 0
CONFLICT = 1
PENDING = 2
class BaseJob(object):
    def __init__(self, name_pairs, logger=None):
        self.items = [ FSItem(src, dest) for src, dest in name_pairs ]

        self.logger = logger or Logger()
        self.agent = Agent(logger.debug_stream)

        self.undo = [ ]
        self.index_current = dict((item.current_path, item) for item in self.items)
        self.index_dest    = dict((item.dest_path,    item) for item in self.items)

    def execute(self, abort_on_first_error=False):
        success = True

        for item in self.items:
            if item.src_path == item.dest_path:
                self.logger.debug("{}: no change".format(item.src_path))
                continue

            try:
                self.process_item(item)
            except (EnvironmentError, OperationError) as exc:
                success = False
                self.logger.error(format_exception(exc))
                if abort_on_first_error:
                    break

        return success

    def process_item(self, item):
        raise NotImplementedError

    def push_undo(self, func, args):
        self.undo.append((func, args))

    def exist_reason(self, item):
        path = item.dest_path

        if path in self.index_dest and self.index_dest[path] != item:
            return CONFLICT, self.index_dest[path]

        if path in self.index_current and self.index_current[path] != item:
            return PENDING, self.index_current[path]

        # otherwise do a slow check. this accounts for when the filesystem
        # doesn't allow two different paths to coexist (i.e. case-insensitive,
        # unicode normalization)
        for item in self.items:
            if os.path.exists(item.dest_path):
                return CONFLICT, item

            if (
                item.current_path != item.dest_path and
                os.path.exists(item.current_path)
            ):
                return PENDING, item

        return UNINVOLVED, None

    def change_item_path(self, item, path):
        old_path = item.current_path
        self.move(old_path, path)
        item.current_path = path
        del self.index_current[old_path]
        self.index_current[path] = item

    def move(self, src, dest):
        self.agent.mv(src, dest)
        self.push_undo("mv", (dest, src))

    def ensure_dir_for(self, path):
        # can't use os.makedirs because we need to log the undo for each
        # intermediate dir created
        container = os.path.dirname(path)

        if os.path.isdir(container) or container == "":
            return

        if os.path.exists(container):
            raise OperationError("Path exists but is not a directory", container)

        self.ensure_dir_for(container)
        self.agent.mkdir(container)
        self.push_undo("rmdir", (container,))

    def rollback(self):
        try:
            while len(self.undo) > 0:
                method_name, args = self.undo[-1]
                getattr(self.agent, method_name)(*args)
                self.undo.pop()
        except EnvironmentError as ee:
            self.logger.error("Error while rolling back - incomplete commands follow.")
            self.logger.error("# The first command listed failed with exception: {error!s}".format(error=ee))
            for method_name, args in reversed(self.undo):
                self.logger.error("{method_name} {args}".format(
                    method_name=method_name,
                    args=" ".join(repr(a) for a in args)
                ))
            self.logger.error("# End incomplete commands")
            raise ee


class MoveJob(BaseJob):
    def process_item(self, item):
        self.logger.info("move {} to {}".format(item.src_path, item.dest_path))
        self.ensure_dir_for(item.dest_path)
        if os.path.exists(item.dest_path):
            reason, blocking_item = self.exist_reason(item)

            if reason == PENDING:
                temp_path = generate_path(blocking_item.current_path)
                self.change_item_path(blocking_item, temp_path)

            elif reason == CONFLICT:
                raise make_conflict_error(item, blocking_item)
            
            else:
                raise make_uninvolved_error(item)
                
        self.change_item_path(item, item.dest_path)


class CopyJob(BaseJob):
    def process_item(self, item):
        self.logger.info("copy {} to {}".format(item.src_path, item.dest_path))
        self.ensure_dir_for(item.dest_path)
        if os.path.exists(item.dest_path):
            raise OperationError("Path exists", item.dest_path)
        self.agent.cp(item.current_path, item.dest_path)
        self.push_undo("rm", (item.dest_path,))


def do_batch(job_ctor, src_dest_iter, trial, log):
    if log is None:
        log = LOG_NONE

    if isinstance(log, int):
        streams = (
            sys.stderr if log >= LOG_ERROR else None,
            sys.stdout if log >= LOG_INFO  else None,
            sys.stdout if log >= LOG_DEBUG else None
        )
    else:
        streams = tuple(log)

    logger = Logger(*streams)

    job = job_ctor(src_dest_iter, logger)
    success = job.execute()
    do_rollback = trial or not success

    if trial and not success:
        logger.error("\nErrors occurred in trial mode. Rolling back...")
    elif trial:
        logger.info("\nTrial mode. Rolling back...")
    elif not success:
        logger.error("\nErrors occurred. Rolling back...")

    if do_rollback:
        job.rollback()
        logger.info("Rollback complete")

    return success


def move(src_dest_iter, trial=False, log=LOG_ERROR):
    do_batch(MoveJob, src_dest_iter, trial, log)


def copy(src_dest_iter, trial=False, log=LOG_ERROR):
    do_batch(CopyJob, src_dest_iter, trial, log)
