#!/usr/bin/env python3
"""Extract reviewed authored rectangles; never synthesize or repaint artwork."""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw, ImageChops

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'Web/wwwroot/assets/map-grid-pass'
SPEC = ROOT / 'Docs/MapGridPass/expansion-spec.json'


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def save(image, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)


def extract(spec_path=SPEC):
    spec = json.loads(spec_path.read_text())
    images, sources, components = {}, [], []
    for authored in spec['sources']:
        source = dict(authored)
        path = ROOT / source['path']
        image = Image.open(path).convert('RGBA')
        images[source['id']] = image
        source.update(sha256=sha(path), width=image.width, height=image.height)
        sources.append(source)
    for authored in spec['components']:
        component = dict(authored)
        source = images[component['sourceId']]
        rect = tuple(component['sourceRects'][0])
        if not (0 <= rect[0] < rect[2] <= source.width and 0 <= rect[1] < rect[3] <= source.height):
            raise ValueError(f'Invalid crop: {component["id"]}: {rect}')
        if set(component['ports']) != {'north', 'east', 'south', 'west'}:
            raise ValueError(f'Missing directional sockets: {component["id"]}')
        native = source.crop(rect)
        native_path = f'expansion/native/{component["family"]}/{component["id"]}.png'
        save(native, BASE / native_path)
        piece = native.copy()
        operations = [{'operation': 'crop', 'sourceRect': list(rect)}]
        policy = component['alphaNormalization']
        if policy == 'opaque-material-core':
            piece.putalpha(255)
            operations.append({'operation': 'force-opaque', 'reason': 'Reviewed interior material core excludes atlas gutters'})
        elif policy == 'source-alpha':
            pass
        elif policy == 'reviewed-background-key':
            # Only explicit authored background color; no contour repainting.
            rgb = piece.convert('RGB')
            key = Image.new('RGB', piece.size, tuple(component['backgroundKey']))
            diff = ImageChops.difference(rgb, key)
            channels = diff.split()
            distance = ImageChops.lighter(ImageChops.lighter(channels[0], channels[1]), channels[2])
            threshold = component.get('backgroundThreshold', 12)
            mask = distance.point(lambda value: 0 if value <= threshold else 255)
            piece.putalpha(ImageChops.multiply(piece.getchannel('A'), mask))
            operations.append({'operation': 'background-key-alpha', 'key': component['backgroundKey'], 'threshold': threshold})
        else:
            raise ValueError(f'Unknown alpha policy: {policy}')
        if component.get('maskPolygon'):
            mask = Image.new('L', piece.size)
            ImageDraw.Draw(mask).polygon([tuple(p) for p in component['maskPolygon']], fill=255)
            piece.putalpha(ImageChops.multiply(piece.getchannel('A'), mask))
            operations.append({'operation': 'reviewed-polygon-mask', 'points': component['maskPolygon']})
        for cutout in component.get('maskCutouts', []):
            mask = Image.new('L', piece.size, 255)
            ImageDraw.Draw(mask).polygon([tuple(p) for p in cutout], fill=0)
            piece.putalpha(ImageChops.multiply(piece.getchannel('A'), mask))
            operations.append({'operation': 'reviewed-polygon-cutout', 'points': cutout})
        margin = component.get('fitMargin', 0 if policy == 'opaque-material-core' else 3)
        if policy == 'opaque-material-core':
            size = (128, 128)
        else:
            scale = min((128-2*margin)/piece.width, (128-2*margin)/piece.height)
            size = (max(1, round(piece.width*scale)), max(1, round(piece.height*scale)))
        piece = piece.resize(size, Image.Resampling.LANCZOS)
        offset = ((128-size[0])//2, (128-size[1])//2)
        canvas = Image.new('RGBA', (128, 128))
        canvas.alpha_composite(piece, offset)
        if policy == 'opaque-material-core':
            canvas.putalpha(255)
        path = f'expansion/components/{component["family"]}/{component["id"]}.png'
        save(canvas, BASE/path)
        operations.append({'operation': 'normalize', 'size': list(size), 'offset': list(offset), 'canvas': [128,128], 'resampling': 'Lanczos'})
        component.update(path=path, nativePath=native_path, nativeSize=[128,128], sourceCropSize=list(native.size), nativeSha256=sha(BASE/native_path), sha256=sha(BASE/path), transformations=operations, derivedTransform={'resizedTo': list(size), 'canvasOffset': list(offset), 'resampling': 'Lanczos'}, fitCanvas=128)
        components.append(component)
    families = []
    for family in spec['families']:
        records = [c for c in components if c['family'] == family['id']]
        columns = 6
        rows = (len(records)+columns-1)//columns
        sheet = Image.new('RGB', (columns*256, max(1,rows)*172), '#192126')
        draw = ImageDraw.Draw(sheet)
        for i, component in enumerate(records):
            x, y = i%columns*256, i//columns*172
            image = Image.open(BASE/component['path'])
            sheet.paste(image, (x+64,y+4), image)
            draw.text((x+6,y+137), component['id'], fill='white')
            draw.text((x+6,y+153), component['semanticType'], fill='#adc3cb')
        path = f'expansion/contact-sheets/{family["id"]}.png'
        save(sheet, BASE/path)
        families.append({**family, 'contactSheet': path, 'componentCount':len(records)})
    recipes = []
    for parent in [c for c in components if c.get('countedAuthoredDesign')]:
        children = [c for c in components if c.get('parentId') == parent['id']]
        if not children:
            continue
        original = Image.open(BASE/parent['nativePath']).convert('RGBA')
        residual = original.copy()
        placements = []
        for child in children:
            offset = child['nativeAssemblyOffset']
            native = Image.open(BASE/child['nativePath']).convert('RGBA')
            if offset[0] < 0 or offset[1] < 0 or offset[0]+native.width > original.width or offset[1]+native.height > original.height:
                raise ValueError(f'Child outside parent: {child["id"]}')
            ImageDraw.Draw(residual).rectangle((offset[0],offset[1],offset[0]+native.width-1,offset[1]+native.height-1),fill=(0,0,0,0))
            placements.append({'componentId':child['id'],'nativePath':child['nativePath'],'position':offset,'operation':'replace-source-pixels'})
        residual_path = f'expansion/assemblies/{parent["id"]}-residual.png'
        save(residual,BASE/residual_path)
        rebuilt = residual.copy()
        for placement in placements:
            rebuilt.paste(Image.open(BASE/placement['nativePath']),tuple(placement['position']))
        reassembled_path = f'expansion/assemblies/{parent["id"]}-reassembled.png'
        save(rebuilt,BASE/reassembled_path)
        if rebuilt.tobytes() != original.tobytes():
            raise ValueError(f'Native source reconstruction mismatch: {parent["id"]}')
        recipes.append({'parentId':parent['id'],'size':list(original.size),'residualPath':residual_path,'residualSha256':sha(BASE/residual_path),'placements':placements,'reassembledPath':reassembled_path,'reassembledSha256':sha(BASE/reassembled_path),'pixelExact':True,'note':'Native source-pixel replacement recipe; residual preserves visible surrounding pixels, never infers artwork behind child parts.'})
    manifest = {**spec, 'sources': sources, 'components': components, 'families': families, 'nativeAssemblyRecipes': recipes}
    destination = BASE/'expansion/manifest.json'
    destination.parent.mkdir(parents=True, exist_ok=True)
    destination.write_text(json.dumps(manifest, indent=2)+'\n')
    print(f'{len(components)} reviewed expansion components across {len(families)} families')


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--spec', type=Path, default=SPEC)
    args = parser.parse_args()
    extract(args.spec)
