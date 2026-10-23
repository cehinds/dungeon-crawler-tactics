"""Slice reviewed scenery and Scatterer poses from the retained GPT source atlas."""
import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'Web/wwwroot/assets/scenario-props'
source = Image.open(OUT / 'source-atlas.png').convert('RGBA')
width, height = source.size
manifest = {'schemaVersion': 1, 'sprites': {}}
preview = Image.new('RGBA', (512, 288), (15, 22, 36, 255))
# The generated bench and barricade cross nominal grid boundaries; measured
# cuts isolate them without resizing their silhouettes independently by axis.
bounds = [(0, 0, 490, 480), (490, 0, 894, 480), (894, 0, 1368, 480), (1368, 0, width, 480)]
for index, (name, box) in enumerate(zip(['garbage', 'bench', 'barrier', 'parts'], bounds)):
    crop = source.crop(box); crop = crop.crop(crop.getbbox())
    scale = min(124 / crop.width, 124 / crop.height)
    sprite = crop.resize((round(crop.width * scale), round(crop.height * scale)), Image.Resampling.NEAREST)
    frame = Image.new('RGBA', (128, 144))
    frame.alpha_composite(sprite, (64 - sprite.width // 2, 128 - sprite.height))
    frame.save(OUT / f'{name}.png'); preview.alpha_composite(frame, (index * 128, 0))
    manifest['sprites'][name] = {'file': f'{name}.png', 'frameWidth': 128, 'frameHeight': 144, 'anchorX': 64, 'anchorY': 128}
poses = []
for index in range(4):
    crop = source.crop((index * width // 4, 480, (index + 1) * width // 4, height))
    poses.append(crop.crop(crop.getbbox()))
scale = min(116 / max(p.width for p in poses), 104 / max(p.height for p in poses))
strip = Image.new('RGBA', (512, 144))
for index, crop in enumerate(poses):
    sprite = crop.resize((round(crop.width * scale), round(crop.height * scale)), Image.Resampling.NEAREST)
    strip.alpha_composite(sprite, (index * 128 + 64 - sprite.width // 2, 128 - sprite.height))
strip.save(OUT / 'scatterer.png'); preview.alpha_composite(strip, (0, 144))
manifest['sprites']['scatterer'] = {'file': 'scatterer.png', 'frameWidth': 128, 'frameHeight': 144, 'anchorX': 64, 'anchorY': 128, 'bodyHeight': 100, 'frames': 4}
(OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
preview.save('/tmp/dct-scenario-sprites.png')
print('Normalized four scenery PNGs and four Scatterer poses.')
