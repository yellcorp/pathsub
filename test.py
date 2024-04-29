import subprocess
import sys

result = subprocess.run([sys.executable, "-m", "unittest", "discover", "-v", "tests"])
sys.exit(result.returncode)
