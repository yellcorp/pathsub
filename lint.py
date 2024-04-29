import subprocess
import sys

ruff_result = subprocess.run(["ruff", "check"])
mypy_result = subprocess.run(["mypy", "pathsub"])
sys.exit(max(ruff_result.returncode, mypy_result.returncode))
