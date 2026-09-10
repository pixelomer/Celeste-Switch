#!/usr/bin/env python3
"""Read-only verification of the research source snapshot; never reset a tree."""
import argparse
import json
from pathlib import Path
import subprocess


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('upstream_root', type=Path)
    args = parser.parse_args()
    manifest = Path(__file__).resolve().parents[1] / 'research/upstreams.lock.json'
    lock = json.loads(manifest.read_text())
    failures = []
    for entry in lock['repositories']:
        path = args.upstream_root / entry['path']
        try:
            actual = subprocess.check_output(['git', '-C', str(path), 'rev-parse', 'HEAD'],
                                             stderr=subprocess.DEVNULL, text=True).strip()
            dirty = subprocess.check_output(['git', '-C', str(path), 'diff', '--name-only', 'HEAD'],
                                            stderr=subprocess.DEVNULL, text=True).strip()
            if actual != entry['commit'] or dirty:
                failures.append(entry['path'])
                print(f'DRIFT {entry["path"]}: HEAD={actual}; tracked changes={bool(dirty)}')
            else:
                print(f'OK {entry["path"]} {actual}')
        except subprocess.CalledProcessError:
            failures.append(entry['path'])
            print(f'MISSING {entry["path"]}')
    raise SystemExit(bool(failures))


if __name__ == '__main__':
    main()
