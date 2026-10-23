"""Normalize the retained GPT atlas into anchored four-pose boss strips.

Bounds are measured against the reviewed source, not an assumed uniform grid.
One scale per character preserves relative size between animation frames.
"""
import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'Web/wwwroot/assets/bosses'
source = Image.open(OUT / 'source-atlas.png').convert('RGBA')
regions = {
    'hoarder': [(0, 0, 354, 372), (354, 0, 717, 372), (717, 0, 1080, 372), (1080, 0, 1448, 372)],
    'juicer': [(0, 372, 357, 706), (357, 372, 718, 706), (718, 372, 1016, 706), (1016, 372, 1448, 706)],
    'swine': [(0, 706, 351, 1086), (351, 706, 710, 1086), (710, 706, 1050, 1086), (1050, 706, 1448, 1086)],
}
manifest = {'schemaVersion': 1, 'source': 'source-atlas.png', 'sprites': {}}
preview = Image.new('RGBA', (768, 576), (15, 22, 36, 255))
for row, (name, bounds) in enumerate(regions.items()):
    crops = []
    for box in bounds:
        crop = source.crop(box)
        crop = crop.crop(crop.getbbox())
        crops.append(crop)
    scale = min(176 / max(c.width for c in crops), 172 / max(c.height for c in crops))
    strip = Image.new('RGBA', (768, 192))
    for frame, crop in enumerate(crops):
        sprite = crop.resize((round(crop.width * scale), round(crop.height * scale)), Image.Resampling.NEAREST)
        strip.alpha_composite(sprite, (frame * 192 + 96 - sprite.width // 2, 184 - sprite.height))
    strip.save(OUT / f'{name}.png')
    preview.alpha_composite(strip, (0, row * 192))
    manifest['sprites'][name] = {'file': f'{name}.png', 'frameWidth': 192, 'frameHeight': 192,
        'anchorX': 96, 'anchorY': 184, 'frames': 4, 'bodyHeight': 168,
        'poses': ['idle', 'walk1', 'walk2', 'attack']}
(OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
preview.save('/tmp/dct-boss-preview.png')
print('Normalized 12 transparent boss poses; preview /tmp/dct-boss-preview.png')
