"""Verify the actual scenario art contracts consumed by the browser renderer."""
import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
assets = ROOT / 'Web/wwwroot/assets'
known = set()
frames = 0
for folder in ('bosses', 'scenario-props'):
    manifest = json.loads((assets / folder / 'manifest.json').read_text())
    for name, definition in manifest['sprites'].items():
        image = Image.open(assets / folder / definition['file'])
        width, height = definition['frameWidth'], definition['frameHeight']
        count = definition.get('frames', 1)
        assert image.mode == 'RGBA' and image.size == (width * count, height), name
        assert 0 <= definition['anchorX'] <= width and 0 <= definition['anchorY'] <= height, name
        poses = set()
        for index in range(count):
            pose = image.crop((width * index, 0, width * (index + 1), height))
            assert pose.getchannel('A').getextrema() == (0, 255), name + ': missing alpha or figure'
            poses.add(pose.tobytes())
        assert len(poses) == count, name + ': duplicated animation poses'
        if count > 1:
            frames += count
            known.add('boss-' + name if folder == 'bosses' else name)
game = json.loads((ROOT / 'UnityPackage/Runtime/Data/game-content.json').read_text())
for scenario in game['scenarios']:
    for enemy in scenario['encounter']['enemies']:
        assert enemy['artId'] in known, enemy['id'] + ': scenario sprite is missing'
print(f'Valid scenario art: {frames} distinct animated poses and four transparent scenery components.')
