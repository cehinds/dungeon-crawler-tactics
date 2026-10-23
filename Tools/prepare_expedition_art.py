#!/usr/bin/env python3
"""Normalize generated atlas cells into anchored idle/walk/walk/attack strips.

This only crops and scales existing art. Source atlases are retained for editing.
Run from any directory; no image generation or runtime dependency is involved.
"""
import json
from pathlib import Path
from PIL import Image

ROOT = Path(__file__).resolve().parents[1] / 'Web/wwwroot/assets/expedition-enemies'
SHEETS = [
    ('elemental', ['sludge', 'cinder', 'frost'], [0, 328, 652, 1024], [0, 378, 765, 1134, 1536]),
    ('constructs', ['spore', 'sentry', 'mauler'], [0, 330, 675, 1024], [0, 385, 768, 1090, 1536]),
]


def main():
    sprites = {}
    for sheet, names, rows, columns in SHEETS:
        source = Image.open(ROOT / 'source' / (sheet + '.png')).convert('RGBA')
        for row, name in enumerate(names):
            cells = []
            for column in range(4):
                cell = source.crop((columns[column], rows[row], columns[column + 1], rows[row + 1]))
                # Remove barely visible matte noise; retain antialiased body pixels.
                alpha = cell.getchannel('A').point(lambda value: 0 if value < 32 else value)
                cell.putalpha(alpha)
                bounds = alpha.getbbox()
                if bounds is None:
                    raise ValueError(f'Empty source cell: {name}/{column}')
                cells.append(cell.crop(bounds))
            scale = min(144 / max(cell.width for cell in cells), 132 / max(cell.height for cell in cells))
            strip = Image.new('RGBA', (640, 160))
            for frame, cell in enumerate(cells):
                cell = cell.resize((round(cell.width * scale), round(cell.height * scale)), Image.Resampling.NEAREST)
                strip.alpha_composite(cell, (frame * 160 + (160 - cell.width) // 2, 148 - cell.height))
            strip.save(ROOT / (name + '.png'), optimize=True)
            sprites[name] = dict(file=name + '.png', frameWidth=160, frameHeight=160,
                                 anchorX=80, anchorY=148, bodyHeight=108, frames=4)
    (ROOT / 'manifest.json').write_text(json.dumps(dict(schemaVersion=1, sprites=sprites), indent=2) + '\n')
    print('Prepared six anchored enemy strips, 24 animation frames.')


if __name__ == '__main__':
    main()
