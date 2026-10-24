#!/usr/bin/env python3
"""Split authored floor artwork into four tile-aligned PNG components.

The source boxes are measured alpha bounds, not guessed equal atlas quarters.
The two-pixel overlap around the 128 x 64 logical diamond hides raster seams.
"""
import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1] / 'Web/wwwroot/assets'
ART = ROOT / 'dungeon-stone'
BOXES = [(36, 41, 853, 466), (919, 42, 1738, 465),
         (46, 475, 845, 882), (924, 475, 1728, 882)]
source = Image.open(ART / 'source/floors.png').convert('RGBA')
assets = []
for name, box in zip(('stone-a', 'stone-b', 'stone-c', 'stone-d'), BOXES):
    image = source.crop(box).resize((132, 68), Image.Resampling.NEAREST)
    image.save(ART / (name + '.png'), optimize=True)
    assets.append({'id': name, 'file': '../dungeon-stone/' + name + '.png',
                   'width': 132, 'height': 68, 'anchor': {'x': 66, 'y': 34},
                   'layer': 'floor', 'tags': ['stone', 'floor'], 'sourceBox': list(box)})
(ART / 'floors-manifest.json').write_text(json.dumps({'assets': assets}, indent=2) + '\n')
print('Built four independent floor tiles at the shared 128 x 64 grid anchor.')
