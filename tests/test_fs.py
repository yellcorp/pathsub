import os.path

from pathsub.agents import Executive
from pathsub.fs import ensure_dir_for
from tests.utils_for_testing import FixtureDirTestCase


class TestEnsureDirFor(FixtureDirTestCase):
    def test_ensure_dir_for_makes_dirs(self):
        agent = Executive()

        parent1 = os.path.join(self._fixture_dir.name, "foo")
        parent2 = os.path.join(parent1, "bar")
        parent3 = os.path.join(parent2, "baz")
        leaf = os.path.join(parent3, "qux.jpg")

        os.mkdir(parent1)
        assert os.path.isdir(parent1)

        ensure_dir_for(leaf, agent)

        self.assertTrue(os.path.isdir(parent3))
        self.assertTrue(os.path.isdir(parent2))
        self.assertTrue(os.path.isdir(parent1))

    def test_ensure_dir_for_no_dirs_needed(self):
        agent = Executive()

        parent1 = os.path.join(self._fixture_dir.name, "foo")
        leaf = os.path.join(parent1, "bar.jpg")

        os.mkdir(parent1)
        assert os.path.isdir(parent1)

        ensure_dir_for(leaf, agent)

        self.assertTrue(os.path.isdir(parent1))
