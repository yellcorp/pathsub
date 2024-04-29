import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

_THIS_FILE = Path(__file__).resolve()
_TESTS_DIR = _THIS_FILE.parent
_PROJECT_DIR = _TESTS_DIR.parent
_FIXTURES_DIR = _PROJECT_DIR / "fixtures"


def make_temp_fixtures_dir():
    _FIXTURES_DIR.mkdir(exist_ok=True, parents=True)
    return TemporaryDirectory(dir=_FIXTURES_DIR, delete=False)


def write_file(path, content: bytes):
    with open(path, "xb") as writer:
        writer.write(content)


def read_file(path):
    with open(path, "rb") as reader:
        return reader.read()


class FixtureDirTestCase(unittest.TestCase):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self._fixture_dir = None

    def setUp(self):
        assert self._fixture_dir is None
        self._fixture_dir = make_temp_fixtures_dir()

    def tearDown(self):
        assert self._fixture_dir is not None
        self._fixture_dir.cleanup()
        self._fixture_dir = None
