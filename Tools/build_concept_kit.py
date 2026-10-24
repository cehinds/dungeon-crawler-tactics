#!/usr/bin/env python3
"""Install the generated stone components into the shared game/editor PNG kit.

Stable asset IDs preserve room recipes. Wall contact points are scaled with the
image, so the battle renderer can align their real ground edge to the grid.
"""
import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1] / 'Web/wwwroot/assets'
KIT = ROOT / 'room-kit'
ART = ROOT / 'dungeon-stone'
(KIT / 'concept').mkdir(exist_ok=True)
base = json.loads((KIT / 'manifest.json').read_text())
overrides = []
for a in json.loads((ART / 'floors-manifest.json').read_text())['assets']:
    image = Image.open(ART / (a['id'] + '.png'))
    image.save(KIT / 'concept' / (a['id'] + '.png'))
    overrides.append({**a, 'file': 'concept/' + a['id'] + '.png'})
for name, source in json.loads((ART / 'walls-manifest.json').read_text())['sprites'].items():
    asset_id = name.replace('walls-', 'wall-')
    Image.open(ART / source['file']).resize((80, 88), Image.Resampling.NEAREST).save(KIT / 'concept' / (asset_id + '.png'))
    overrides.append({'id': asset_id, 'file': 'concept/' + asset_id + '.png',
                      'width': 80, 'height': 88,
                      'anchor': dict(zip(('x', 'y'), (round(v/2, 3) for v in source['anchor']))),
                      'edgeEndpoints': [[round(v/2, 3) for v in p] for p in source['groundEndpoints']],
                      'layer': 'structure', 'tags': ['wall', 'stone', asset_id[-2:]]})
for asset in base['assets']:
    replacement = next((a for a in overrides if a['id'] == asset['id']), None)
    if replacement:
        asset.update(replacement)
(KIT / 'manifest.json').write_text(json.dumps(base, indent=2) + '\n')
(KIT / 'concept-manifest.json').write_text(json.dumps({'version': 1, 'assets': overrides}, indent=2) + '\n')
print('Installed six stone components; game and workshop share the same anchors.')
