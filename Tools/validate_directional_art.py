"""Check roster art references and authored directional frame data before publish."""
import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'Web/wwwroot/assets/directional'
game = json.loads((ROOT / 'UnityPackage/Runtime/Data/game-content.json').read_text())
manifest = json.loads((ART / 'manifest.json').read_text())
count = 0
for character in game['roster']:
    if not character.get('deployable', True):
        continue
    name = character['artId']
    definition = manifest['characters'][name]
    image = Image.open(ART / definition['file']).convert('RGBA')
    assert (ART / definition['portrait']).is_file(), f'{name}: missing portrait'
    assert 0 < definition['bodyHeight'] <= 128, f'{name}: invalid visible height'
    distinct = set()
    for direction in ['se', 'sw', 'ne', 'nw']:
        for pose in ['idle', 'walk1', 'walk2']:
            frame = definition['frames'][direction][pose]
            x, y, width, height = (frame[key] for key in ['x', 'y', 'width', 'height'])
            assert 0 <= x < x + width <= image.width and 0 <= y < y + height <= image.height
            assert 0 <= frame['anchorX'] <= 1 and 0 <= frame['anchorY'] <= 1
            crop = image.crop((x, y, x + width, y + height))
            assert crop.getchannel('A').getbbox(), f'{name}/{direction}/{pose}: empty frame'
            distinct.add(crop.tobytes())
            count += 1
    assert len(distinct) == 12, f'{name}: duplicated directional or walking frames'
print(f'Valid roster art: {count} distinct directional/idle/walking frames across eight deployable characters.')
