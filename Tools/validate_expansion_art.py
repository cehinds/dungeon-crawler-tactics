#!/usr/bin/env python3
"""Check the new enemy animation contract and all linked menu illustrations."""
import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1] / 'Web/wwwroot'
folder = ROOT / 'assets/expedition-enemies'
manifest = json.loads((folder / 'manifest.json').read_text())
assert set(manifest['sprites']) == {'sludge', 'cinder', 'frost', 'spore', 'sentry', 'mauler'}
for name, sprite in manifest['sprites'].items():
    image = Image.open(folder / sprite['file'])
    width, height = sprite['frameWidth'], sprite['frameHeight']
    assert image.mode == 'RGBA' and image.size == (width * 4, height), name
    assert 0 < sprite['anchorX'] < width and 0 < sprite['anchorY'] < height, name
    poses = set()
    for frame in range(4):
        cell = image.crop((frame * width, 0, (frame + 1) * width, height))
        alpha = cell.getchannel('A')
        assert alpha.getextrema()[0] == 0 and alpha.getbbox(), (name, frame)
        poses.add(cell.tobytes())
    assert len(poses) == 4, name
atlas = json.loads((ROOT / 'menu-atlas.json').read_text())
assert len(atlas['menus']) == 6 and len(atlas['components']) == 30
for menu in atlas['menus']:
    image = Image.open(ROOT / menu['image'])
    assert image.width >= 1280 and image.height >= 720, menu['id']
print('Validated 24 distinct enemy frames, six menu illustrations and 30 component definitions.')
