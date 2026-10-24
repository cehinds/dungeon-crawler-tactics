"""Normalize the generated wall atlas; original generation remains untouched."""
from pathlib import Path
import json
import shutil
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'Web/wwwroot/assets/dungeon-stone'
SOURCE = OUT / 'source/walls.png'
GENERATED = Path('/workspace/generated_images/exec-9c4c6275-16e7-4ed8-9a30-63ddc50908b0.png')
OUT.mkdir(parents=True, exist_ok=True)
SOURCE.parent.mkdir(parents=True, exist_ok=True)
if not SOURCE.exists():
    shutil.copy2(GENERATED, SOURCE)
im = Image.open(SOURCE).convert('RGBA')
# Remove extremely faint generation residue in the otherwise transparent field.
alpha = im.getchannel('A').point(lambda a: 0 if a <= 20 else a)
im.putalpha(alpha)
entries = {}
for name, box, endpoints in [
    ('walls-ne', (68, 93, 704, 783), [(70, 486), (592, 780)]),
    ('walls-nw', (1072, 96, 1706, 784), [(1175, 780), (1704, 485)]),
]:
    # Independently measured front-face ground edge; anisotropic normalization
    # makes its projected slope exactly 1:2 for the engine's isometric grid.
    x0, y0, x1, y1 = box
    sx = 160 / (x1 - x0)
    (ax, ay), (bx, by) = endpoints
    sy = abs((bx - ax) * sx / (2 * (by - ay)))
    height = round((y1 - y0) * sy)
    top = 176 - height
    sprite = im.crop(box).resize((160, height), Image.Resampling.NEAREST)
    canvas = Image.new('RGBA', (160, 176))
    canvas.alpha_composite(sprite, (0, top))
    canvas.save(OUT / f'{name}.png')
    ground = [[round((x-x0)*sx, 2), round((y-y0)*height/(y1-y0)+top, 2)] for x,y in endpoints]
    entries[name] = {'file': f'{name}.png', 'width': 160, 'height': 176,
                     'groundEndpoints': ground,
                     'anchor': [round(sum(p[i] for p in ground)/2, 2) for i in (0,1)],
                     'sourceCrop': list(box)}
(OUT / 'walls-manifest.json').write_text(json.dumps({'source': 'source/walls.png', 'generatedOriginal': str(GENERATED), 'sprites': entries}, indent=2)+'\n')
print(json.dumps(entries, indent=2))
