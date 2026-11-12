"""Rebuild the offline guide from the checked-in app sources."""
import os
from pathlib import Path
import runpy
import tempfile

root = Path(__file__).resolve().parents[1]
os.chdir(root)
previous = os.environ.get('SLAYER_BUILD_OUTPUT')
with tempfile.TemporaryDirectory(prefix='slayer-build-') as folder:
    output = Path(folder) / 'guide.html'
    os.environ['SLAYER_BUILD_OUTPUT'] = str(output)
    try:
        runpy.run_path(str(root / 'scripts/build-guide.py'), run_name='__main__')
        runpy.run_path(str(root / 'scripts/build-final.py'), run_name='__main__')
        # Both passes finish before the live server can see the new guide.
        replacement = root / '.guide-build.tmp'
        replacement.write_bytes(output.read_bytes())
        os.replace(replacement, root / 'slayer-leveling-guide.html')
    finally:
        if previous is None:
            os.environ.pop('SLAYER_BUILD_OUTPUT', None)
        else:
            os.environ['SLAYER_BUILD_OUTPUT'] = previous
