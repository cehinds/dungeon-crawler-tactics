#!/usr/bin/env python3
"""Normalize authored Katia forms (4 directions x idle/walk1/walk2).

Uses the same connected-component measurement and foot anchor as roster art.
Add a transparent source/{bulwark,strider,focused}.png, then run this script.
No attack poses or missing directions are synthesized.
"""
import json
from pathlib import Path
import numpy as np
from PIL import Image
from build_directional_sprites import measure, DIRECTIONS, POSES

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'Web/wwwroot/assets/forms'
HEIGHTS = {'bulwark': 80, 'strider': 88, 'focused': 80}

def main():
    manifest = {'version': 1, 'forms': {}}
    measurements = {}
    for name, height in HEIGHTS.items():
        path = OUT / 'source' / (name + '.png')
        if not path.exists():
            continue
        sprites = measure(path)
        scale = min(height / np.median([s.height for s, _ in sprites[:4]]),
                    116 / max(s.width for s, _ in sprites),
                    120 / max(s.height for s, _ in sprites))
        sheet = Image.new('RGBA', (512, 432))
        frames = {d: {} for d in DIRECTIONS}
        measurements[name] = []
        for i, (sprite, box) in enumerate(sprites):
            row, col = divmod(i, 4)
            size = (max(1, round(sprite.width * scale)), max(1, round(sprite.height * scale)))
            sprite = sprite.resize(size, Image.Resampling.NEAREST)
            px, py = round(64 - size[0] / 2), 128 - size[1]
            assert px >= 0 and px + size[0] <= 128 and py >= 0, (name, i, size)
            sheet.paste(sprite, (col * 128 + px, row * 144 + py))
            frames[DIRECTIONS[col]][POSES[row]] = {
                'x': col * 128, 'y': row * 144, 'width': 128, 'height': 144,
                'drawWidth': 128, 'drawHeight': 144, 'anchorX': .5, 'anchorY': 128 / 144}
            measurements[name].append({'direction': DIRECTIONS[col], 'pose': POSES[row],
                                       'sourceBox': box, 'scale': float(scale)})
        sheet.save(OUT / (name + '.png'))
        manifest['forms']['form.' + name] = {'file': name + '.png', 'rosterId': 'crawler.katia',
            'bodyHeight': round(float(np.median([s.height for s, _ in sprites[:4]])) * scale),
            'frames': frames}
    (OUT / 'manifest.json').write_text(json.dumps(manifest, indent=2) + '\n')
    (OUT / 'source/measurements.json').write_text(json.dumps(measurements, indent=2) + '\n')
    print(f'Built {len(manifest["forms"])} form atlases with {len(manifest["forms"])*12} authored frames.')

if __name__ == '__main__':
    main()
