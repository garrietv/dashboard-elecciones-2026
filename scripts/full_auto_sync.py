#!/usr/bin/env python3
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]


def run(script):
    subprocess.run([sys.executable, str(ROOT / 'scripts' / script)], cwd=ROOT, check=True)


def main():
    run('sync_from_worker.py')
    run('update_onpe_pipeline.py')


if __name__ == '__main__':
    main()
