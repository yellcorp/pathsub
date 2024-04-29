import subprocess
import sys

result = subprocess.run(["isort", "."])
if result.returncode == 0:
    result = subprocess.run(["black", "."])
sys.exit(result.returncode)
