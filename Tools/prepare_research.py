#!/usr/bin/env python3
"""Copy sourced research to the static codex; --check catches stale public data."""
import argparse
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
FILES = {'classes-skills.json': 'lore-catalog.json',
         'floors-enemies.json': 'floor-research.json', 'housing.json': 'housing-research.json'}
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--check', action='store_true')
args = parser.parse_args()
for source, destination in FILES.items():
    data = (ROOT / 'Research' / source).read_bytes()
    target = ROOT / 'Web/wwwroot/data' / destination
    if args.check:
        if not target.exists() or target.read_bytes() != data:
            raise SystemExit(f'Stale codex data: {target}. Run Tools/prepare_research.py.')
    else:
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(data)
print('Verified public research copies.' if args.check else 'Prepared public research copies.')
