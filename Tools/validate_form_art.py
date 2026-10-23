#!/usr/bin/env python3
"""Validate form IDs, declared frames, alpha, foot anchors and authored distinctness."""
import json
from pathlib import Path
from PIL import Image
ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'Web/wwwroot/assets/forms'
manifest = json.loads((ART / 'manifest.json').read_text())
game = json.loads((ROOT / 'UnityPackage/Runtime/Data/game-content.json').read_text())
forms = {f['id']: f for f in game['forms']}
count = 0
for form_id, definition in manifest['forms'].items():
    assert form_id in forms and definition['rosterId'] == forms[form_id]['rosterId']
    image = Image.open(ART / definition['file'])
    assert image.mode == 'RGBA' and image.size == (512, 432)
    assert 0 < definition['bodyHeight'] <= 120
    distinct = set()
    for direction in ['se', 'sw', 'ne', 'nw']:
        assert set(definition['frames'][direction]) == {'idle', 'walk1', 'walk2'}
        for pose, frame in definition['frames'][direction].items():
            x, y, w, h = (frame[k] for k in ['x', 'y', 'width', 'height'])
            assert 0 <= x < x+w <= image.width and 0 <= y < y+h <= image.height
            assert frame['anchorX'] == .5 and frame['anchorY'] == 128/144
            crop = image.crop((x, y, x+w, y+h))
            bounds = crop.getchannel('A').getbbox()
            assert bounds and bounds[3] == 128, (form_id, direction, pose, bounds)
            assert crop.getchannel('A').getextrema()[0] == 0
            distinct.add(crop.tobytes())
            count += 1
    assert len(distinct) == 12, f'{form_id}: duplicate poses'
expected = {f['id'] for f in game['forms'] if f.get('rosterId') == 'crawler.katia' and f['id'] != 'form.baseline'}
assert set(manifest['forms']) == expected, 'Missing or unexpected authored form IDs'
print(f'Valid form art: {count} distinct authored frames across {len(manifest["forms"])} forms.')
