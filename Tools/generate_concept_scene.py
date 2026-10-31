#!/usr/bin/env python3
"""Render the shared browser/Node room compiler with Pillow; no source image needed."""
import argparse
import hashlib
import json
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / 'Web/wwwroot/assets/concept-reconstruction'
RECIPE = ROOT / 'Docs/ConceptReconstruction/procedural-recipe.json'
ENGINE = ROOT / 'Web/wwwroot/concept-room-engine.js'


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--seed', type=int, nargs='+', default=[7, 29, 103])
    parser.add_argument('--engine', type=Path, default=ENGINE)
    parser.add_argument('--recipe', type=Path, default=RECIPE)
    parser.add_argument('--asset-root', type=Path, default=ASSETS / 'derived')
    parser.add_argument('--out', type=Path, default=ASSETS / 'procedural')
    args = parser.parse_args()
    recipe = json.loads(args.recipe.read_text())
    catalog_path = args.asset_root / 'catalog.json'
    catalog = json.loads(catalog_path.read_text())
    entries = catalog['assets']
    assets = {a['id']: a for a in entries} if isinstance(entries, list) else entries
    for asset in assets.values():
        path = (args.asset_root / asset['file']).resolve()
        if not path.is_relative_to(args.asset_root.resolve()):
            raise ValueError('Asset path escapes catalog root')
        expected = asset.get('sha256')
        if expected and hashlib.sha256(path.read_bytes()).hexdigest() != expected:
            raise ValueError(f"Asset hash mismatch: {asset['id']}")
    args.out.mkdir(parents=True, exist_ok=True)
    script = "const fs=require('fs'),engine=require(process.argv[1]);const q=JSON.parse(fs.readFileSync(0,'utf8'));process.stdout.write(JSON.stringify(engine.generate(q.recipe,q.catalog,q.seed)));"
    for seed in args.seed:
        result = subprocess.run(['node', '-e', script, str(args.engine.resolve())], input=json.dumps({'recipe': recipe, 'catalog': catalog, 'seed': seed}), text=True, capture_output=True, check=True)
        room = json.loads(result.stdout)
        canvas = room['canvas']
        image = Image.new('RGBA', (canvas['width'], canvas['height']), canvas['background'])
        for item in room['drawPlan']:
            x, y = round(item['x']), round(item['y'])
            width, height = round(item['width']), round(item['height'])
            if item.get('primitive') == 'rect':
                if width > 0 and height > 0:
                    ImageDraw.Draw(image).rectangle((x, y, x+width-1, y+height-1), fill=item.get('fill'), outline=item.get('stroke'), width=item.get('lineWidth', 1))
            else:
                sprite = Image.open(args.asset_root / assets[item['assetId']]['file']).convert('RGBA')
                if item.get('sourceRect'):
                    sx, sy, sw, sh = item['sourceRect']
                    sprite = sprite.crop((round(sx), round(sy), round(sx+sw), round(sy+sh)))
                sprite = sprite.resize((width, height), Image.Resampling.NEAREST)
                image.alpha_composite(sprite, (x, y))
        image.convert('RGB').save(args.out / f'room-{seed}.png')
        (args.out / f'room-{seed}.json').write_text(json.dumps(room, indent=2)+'\n')
        print(f"Generated room-{seed}: {room['validation']}")
    (args.out / 'recipe.json').write_text(json.dumps(recipe, indent=2)+'\n')


if __name__ == '__main__':
    main()
