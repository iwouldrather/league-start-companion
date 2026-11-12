"""Watch local app sources, rebuild the guide and restart the local server."""
import argparse
from pathlib import Path
import subprocess
import sys
import time
import webbrowser

ROOT = Path(__file__).resolve().parents[1]


def fingerprints(root=ROOT):
    paths = [root / 'slayer-companion.py', root / 'pob_import.py',root / 'gem_acquisition.py',root / 'poe_tree.py']
    paths += list((root / 'source').rglob('*'))
    paths += list((root / 'scripts').glob('build*.py'))
    return {str(p.relative_to(root)): (p.stat().st_mtime_ns, p.stat().st_size)
            for p in paths if p.is_file()}


def changed(before, after):
    return {p for p in before.keys() | after.keys() if before.get(p) != after.get(p)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8766)
    parser.add_argument('--log')
    parser.add_argument('--no-browser', action='store_true')
    args = parser.parse_args()
    command = [sys.executable, '-u', str(ROOT / 'slayer-companion.py'),
               '--port', str(args.port), '--no-browser']
    if args.log:
        command += ['--log', args.log]
    worker = None

    def build():
        result = subprocess.run([sys.executable, str(ROOT / 'scripts/build.py')], cwd=ROOT)
        if result.returncode:
            print('Build failed. Keeping the previous guide; save a correction to retry.', flush=True)
        return result.returncode == 0

    def start():
        return subprocess.Popen(command, cwd=ROOT)

    def stop():
        if worker and worker.poll() is None:
            worker.terminate()
            try:
                worker.wait(timeout=5)
            except subprocess.TimeoutExpired:
                worker.kill()
                worker.wait()

    try:
        if not build():
            return
        snapshot = fingerprints()
        worker = start()
        time.sleep(.6)
        if worker.poll() is not None:
            return
        print('Live updates enabled. Save source changes; the browser updates automatically.', flush=True)
        if not args.no_browser:
            webbrowser.open(f'http://127.0.0.1:{args.port}/')
        while worker.poll() is None:
            time.sleep(.5)
            candidate = fingerprints()
            if candidate == snapshot:
                continue
            # Wait until the editor has finished its batch of writes.
            time.sleep(.5)
            stable = fingerprints()
            if stable != candidate:
                continue
            changes = changed(snapshot, stable)
            snapshot = stable
            guide_change = any(p.startswith(('source', 'scripts')) or p in {'poe_tree.py','gem_acquisition.py'} for p in changes)
            if guide_change and not build():
                continue
            if {'slayer-companion.py','pob_import.py','gem_acquisition.py','poe_tree.py'} & changes:
                print('Restarting companion after a server change…', flush=True)
                stop()
                worker = start()
            else:
                print('Guide updated.', flush=True)
    except KeyboardInterrupt:
        pass
    finally:
        stop()


if __name__ == '__main__':
    main()
