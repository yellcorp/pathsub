import itertools
from pathlib import Path

from .agents import Agent


def ensure_dir_for(target, agent: Agent):
    # Basically mkdir -p, which Python provides, but we need to use
    # the Agent so it can record rollback history
    to_make = list(
        itertools.takewhile(
            lambda a: not a.exists(),
            Path(target).parents,
        )
    )
    for ancestor in reversed(to_make):
        agent.mkdir(ancestor)
