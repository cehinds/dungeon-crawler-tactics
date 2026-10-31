#!/usr/bin/env python3
"""Reproducible literal -> derived -> rooms -> inventory -> package -> verification build.

Requires Python 3.10+, Pillow, NumPy, SciPy, jsonschema and Node.js 18+.
Consumes authored JSON and masks as-is; never invokes mask authoring scripts.
"""
import argparse
import hashlib
import json
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'Docs/ConceptReconstruction'
DEFAULT_OUT = ROOT / 'Web/wwwroot/assets/concept-reconstruction'


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--out', type=Path, default=DEFAULT_OUT)
    p.add_argument('--source', type=Path, default=ROOT / 'Web/wwwroot/assets/broadcast-kit/combat-concept.png')
    p.add_argument('--mask-root', type=Path, default=DEFAULT_OUT)
    p.add_argument('--regions', type=Path, nargs='+', default=[DOCS / 'scene-regions.json', DOCS / 'ui-regions.json'])
    p.add_argument('--recipe', type=Path, default=DOCS / 'procedural-recipe.json')
    p.add_argument('--spec', type=Path, default=DOCS / 'reusable-asset-spec.json')
    a = p.parse_args()
    out = a.out.resolve()
    # A failed run must not leave a previous success report that looks current.
    (out / 'build-report.json').unlink(missing_ok=True)
    def run(tool, *args):
        subprocess.run([sys.executable, str(ROOT / 'Tools' / tool), *map(str, args)], cwd=ROOT, check=True)
    run('rebuild_combat_concept.py', '--source', a.source, '--out', out, '--mask-root', a.mask_root, '--regions', *a.regions)
    run('build_reusable_concept_assets.py', '--asset-root', out, '--out', out / 'derived', '--spec', a.spec)
    recipe = json.loads(a.recipe.read_text())
    seeds = sorted(set([9, *recipe.get('requiredSeeds', [7, 29, 103])]))
    run('generate_concept_scene.py', '--recipe', a.recipe, '--asset-root', out / 'derived', '--out', out / 'procedural', '--seed', *seeds)
    # Isolated builds produce an isolated inventory rather than mutating the authored one.
    from sync_concept_inventory import synchronized_inventory
    inventory = json.loads((DOCS / 'inventory.json').read_text())
    updated = synchronized_inventory(inventory, out / 'manifest.json')
    inventory_out = DOCS / 'inventory.json' if out == DEFAULT_OUT.resolve() else out / 'inventory.json'
    inventory_out.write_text(json.dumps(updated, indent=2) + '\n')
    run('package_concept_generator.py', '--asset-root', out / 'derived', '--recipe', a.recipe, '--out', out / 'concept-generator.zip')
    run('test_concept_reconstruction.py', '--manifest', out / 'manifest.json', '--mask-root', a.mask_root)
    if out == DEFAULT_OUT.resolve():
        run('sync_concept_inventory.py', '--check', '--manifest', out / 'manifest.json')
    required = ['manifest.json', 'combat-concept-components.zip', 'concept-generator.zip',
                'combat-concept.ora', 'reconstructed.png', 'diff.png', 'coverage-map.png',
                'derived/catalog.json', 'derived/validation.json', 'procedural/recipe.json']
    required += [f'procedural/room-{seed}.{extension}' for seed in seeds for extension in ('png', 'json')]
    report = {'schemaVersion': 1, 'status': 'built-and-machine-verified; independent visual acceptance pending',
              'sourceReplay': {k: json.loads((out / 'manifest.json').read_text())[k] for k in ('unassignedPixels', 'changedPixels')},
              'outputs': {name: hashlib.sha256((out / name).read_bytes()).hexdigest() for name in required}}
    (out / 'build-report.json').write_text(json.dumps(report, indent=2) + '\n')
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
