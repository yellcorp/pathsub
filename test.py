import subprocess
import sys

cmds = [
    "coverage run -m unittest discover -v tests",
    "coverage report -m",
    "coverage html",
]

rets = [subprocess.run(cmd.split()) for cmd in cmds]
sys.exit(max(ret.returncode for ret in rets))
