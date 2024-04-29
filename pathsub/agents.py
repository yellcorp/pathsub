import os
import shlex
import shutil
from abc import ABC, abstractmethod
from collections import deque
from dataclasses import dataclass


def _q(value):
    return shlex.quote(os.fspath(value))


class Agent(ABC):
    @abstractmethod
    def move(self, src, dest) -> None: ...

    @abstractmethod
    def mkdir(self, path) -> None: ...

    @abstractmethod
    def rmdir(self, path) -> None: ...


class Executive(Agent):
    def move(self, src, dest) -> None:
        open(dest, "x").close()
        shutil.move(src, dest)

    def mkdir(self, path) -> None:
        os.mkdir(path)

    def rmdir(self, path) -> None:
        os.rmdir(path)


class Operation(ABC):
    @abstractmethod
    def execute(self, agent: Agent) -> None: ...

    @abstractmethod
    def get_undo(self) -> "Operation": ...


@dataclass(slots=True)
class Move(Operation):
    src: str
    dest: str

    def __str__(self):
        return "mv {src} {dest}".format(
            src=_q(self.src),
            dest=_q(self.dest),
        )

    def execute(self, agent: Agent):
        agent.move(self.src, self.dest)

    def get_undo(self):
        return Move(self.dest, self.src)


@dataclass(slots=True)
class Mkdir(Operation):
    path: str

    def __str__(self):
        return "mkdir {path}".format(path=_q(self.path))

    def execute(self, agent: Agent):
        agent.mkdir(self.path)

    def get_undo(self):
        return Rmdir(self.path)


@dataclass(slots=True)
class Rmdir(Operation):
    path: str

    def __str__(self):
        return "rmdir {path}".format(path=_q(self.path))

    def execute(self, agent: Agent):
        agent.rmdir(self.path)

    def get_undo(self):
        return Mkdir(self.path)


class RollbackError(Exception):
    def __init__(self, message, remaining_operations: list[Operation]):
        super().__init__(message)
        self.remaining_operations = remaining_operations


class HistoryAgent(Agent):
    def __init__(self, delegate: Agent):
        self._delegate = delegate
        self._undo: deque[Operation] = deque()

    def move(self, src, dest):
        self._execute_log(Move(src, dest))

    def mkdir(self, path):
        self._execute_log(Mkdir(path))

    def rmdir(self, path):
        self._execute_log(Rmdir(path))

    def _execute_log(self, op: Operation):
        undo_op = op.get_undo()
        self._execute(op)
        self._undo.append(undo_op)

    def _execute(self, op: Operation):
        op.execute(self._delegate)

    def rollback(self) -> list[tuple[str, Exception]]:
        non_critical_errors: list[tuple[str, Exception]] = []

        while self._undo:
            op = self._undo.pop()

            try:
                self._execute(op)
            except OSError as os_error:
                if isinstance(op, Rmdir):
                    # We can live with a failed rmdir
                    non_critical_errors.append((op.path, os_error))
                else:
                    self._undo.append(op)
                    raise RollbackError(
                        "Rollback failed",
                        remaining_operations=list(reversed(self._undo)),
                    ) from os_error

        return non_critical_errors
