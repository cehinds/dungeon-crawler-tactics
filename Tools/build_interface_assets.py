#!/usr/bin/env python3
"""Split the authored room atlas and normalize the reusable nine-slice frame.

No rooms or artwork are synthesized. Source PNGs remain available for editing.
All room components use equal canvases and a common floor-tip anchor.
"""
import json
from zipfile import ZipFile, ZIP_DEFLATED
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1] / 'Web/wwwroot/assets'
names = ('carl', 'donut', 'katia', 'mongo', 'training', 'crafting', 'social', 'bedroom')
sheet = Image.open(ROOT / 'house/source/rooms.png').convert('RGBA')
manifest = {'source': 'source/rooms.png', 'components': {}}
for i, name in enumerate(names):
    col, row = i % 4, i // 4
    box = (col * 384, row * 512, (col + 1) * 384, (row + 1) * 512)
    component = sheet.crop(box)
    bounds = component.getchannel('A').point(lambda a: 255 if a > 20 else 0).getbbox()
    assert bounds, name
    sprite = component.crop(bounds)
    canvas = Image.new('RGBA', (384, 400))
    assert sprite.width <= 384 and sprite.height <= 392, (name, sprite.size)
    canvas.paste(sprite, ((384-sprite.width)//2, 392-sprite.height))
    canvas.save(ROOT / f'house/{name}.png', optimize=True)
    manifest['components'][name] = {'file': f'{name}.png', 'width': 384, 'height': 400,
                                   'anchor': [192, 392], 'sourceCell': list(box)}
(ROOT / 'house/manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
frame = Image.open(ROOT / 'interface/source/frame.png').convert('RGBA')
frame = frame.crop(frame.getchannel('A').getbbox()).resize((512, 512), Image.Resampling.NEAREST)
frame.save(ROOT / 'interface/ornate-frame.png', optimize=True)
(ROOT / 'interface/manifest.json').write_text(json.dumps({
    'frame': {'file': 'ornate-frame.png', 'width': 512, 'height': 512,
              'slice': 72, 'source': 'source/frame.png'}}, indent=2) + '\n')
with ZipFile(ROOT / 'interface-components.zip', 'w', ZIP_DEFLATED) as bundle:
    for name in names:
        bundle.write(ROOT / f'house/{name}.png', f'house/{name}.png')
    for path in ('house/manifest.json', 'house/source/rooms.png',
                 'interface/ornate-frame.png', 'interface/manifest.json',
                 'interface/source/frame.png'):
        bundle.write(ROOT / path, path)
print('Built eight room components, one nine-slice frame and downloadable kit.')

icons = Image.open(ROOT / 'signatures/source/icons.png').convert('RGBA')
icon_manifest = {'source': 'source/icons.png', 'icons': {}}
for i, name in enumerate(('triplicate', 'character-actor', 'tripwire', 'dynamite')):
    icon = icons.crop((i*icons.width//4, 0, (i+1)*icons.width//4, icons.height))
    bounds = icon.getchannel('A').point(lambda a: 255 if a > 20 else 0).getbbox()
    assert bounds, name
    icon = icon.crop(bounds)
    ratio = min(112/icon.width, 112/icon.height)
    icon = icon.resize((round(icon.width*ratio), round(icon.height*ratio)), Image.Resampling.NEAREST)
    canvas = Image.new('RGBA', (128, 128))
    canvas.paste(icon, ((128-icon.width)//2, (128-icon.height)//2))
    canvas.save(ROOT / f'signatures/{name}.png', optimize=True)
    icon_manifest['icons'][name] = {'file': f'{name}.png', 'width': 128, 'height': 128}
(ROOT / 'signatures/manifest.json').write_text(json.dumps(icon_manifest, indent=2) + '\n')
print('Built four signature action icons.')
