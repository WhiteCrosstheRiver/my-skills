"""Install only the two new skill folders; do not touch other configuration."""
import argparse
import shutil
from pathlib import Path


def main():
    p = argparse.ArgumentParser(); p.add_argument('--update', action='store_true'); a = p.parse_args()
    root = Path(__file__).resolve().parents[1]
    pairs = [(root / 'skill/computer-use-delegate', Path.home() / '.codex/skills/computer-use-delegate'),
             (root / 'operator/gui-operator', Path.home() / '.zcode/skills/gui-operator')]
    for src, dst in pairs:
        if dst.exists() and not a.update: raise SystemExit('Skill already exists; inspect it before --update: ' + str(dst))
    for src, dst in pairs:
        shutil.copytree(src, dst, dirs_exist_ok=a.update, ignore=shutil.ignore_patterns('__pycache__', '*.pyc'))
        print(dst)


if __name__ == '__main__': main()
