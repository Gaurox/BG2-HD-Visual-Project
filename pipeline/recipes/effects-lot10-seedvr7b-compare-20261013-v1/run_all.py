"""Serial GPU stages; compare without registering trials or changing installation."""
from pathlib import Path
import subprocess
import sys

HERE = Path(__file__).resolve().parent
ROOT = HERE.parents[2]

for script, arguments in [('produce.py', ['spatial']), ('produce.py', ['temporal']),
                           ('verify.py', []), ('compare.py', [])]:
    print('RUN', script, *arguments, flush=True)
    subprocess.run([sys.executable, '-B', str(HERE / script), *arguments], cwd=ROOT, check=True)
