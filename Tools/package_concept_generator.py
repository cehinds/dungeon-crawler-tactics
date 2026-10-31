#!/usr/bin/env python3
"""Package a portable procedural generator with deterministic ZIP metadata."""
import argparse
import hashlib
import json
from pathlib import Path
import zipfile

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'Docs/ConceptReconstruction'
ASSETS = ROOT / 'Web/wwwroot/assets/concept-reconstruction'


def package(asset_root, recipe, engine, renderer, schema, out):
    catalog = json.loads((asset_root / 'catalog.json').read_text())
    entries = catalog['assets']
    entries = entries.values() if isinstance(entries, dict) else entries
    files = {'assets/catalog.json': (asset_root / 'catalog.json').read_bytes(),
             'recipe.json': (json.dumps({**json.loads(recipe.read_text()), '$schema': 'recipe.schema.json'}, indent=2) + '\n').encode(), 'recipe.schema.json': schema.read_bytes(),
             'concept-room-engine.js': engine.read_bytes(), 'generate.py': renderer.read_bytes()}
    for entry in entries:
        relative = Path(entry['file'])
        if relative.is_absolute() or '..' in relative.parts:
            raise ValueError('Unsafe asset path: ' + str(relative))
        files['assets/' + relative.as_posix()] = (asset_root / relative).read_bytes()
    files['README.md'] = b'''# Portable concept room generator

Requires Python 3.10+, Pillow, and Node.js 18+ on PATH.
From this unpacked directory run:

    python generate.py --engine concept-room-engine.js --recipe recipe.json --asset-root assets --out output --seed 9 123

Outputs are room-SEED.png and room-SEED.json plus the executable recipe copy.
The shared JavaScript compiler validates the recipe and catalog before placement.
No original reference, repository checkout, canonical fragment assets, or network is required.
Assets include visible-source assemblies and explicitly synthesized modules; consult catalog provenance.
Literal source fragments are supplied separately in combat-concept-components.zip.
'''
    manifest = {'schemaVersion': 1, 'requiredEntries': sorted(files),
                'sha256': {name: hashlib.sha256(data).hexdigest() for name, data in sorted(files.items())}}
    files['package-manifest.json'] = (json.dumps(manifest, indent=2) + '\n').encode()
    out.parent.mkdir(parents=True, exist_ok=True)
    with zipfile.ZipFile(out, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
        for name, data in sorted(files.items()):
            info = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
            info.create_system = 3
            info.external_attr = (0o100755 if name == 'generate.py' else 0o100644) << 16
            info.compress_type = zipfile.ZIP_DEFLATED
            archive.writestr(info, data, compresslevel=9)
    return {'file': out.name, 'entries': len(files), 'sha256': hashlib.sha256(out.read_bytes()).hexdigest()}


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--asset-root', type=Path, default=ASSETS / 'derived')
    p.add_argument('--recipe', type=Path, default=DOCS / 'procedural-recipe.json')
    p.add_argument('--schema', type=Path, default=DOCS / 'procedural-recipe.schema.json')
    p.add_argument('--engine', type=Path, default=ROOT / 'Web/wwwroot/concept-room-engine.js')
    p.add_argument('--renderer', type=Path, default=ROOT / 'Tools/generate_concept_scene.py')
    p.add_argument('--out', type=Path, default=ASSETS / 'concept-generator.zip')
    a = p.parse_args()
    print(json.dumps(package(a.asset_root, a.recipe, a.engine, a.renderer, a.schema, a.out)))


if __name__ == '__main__':
    main()
