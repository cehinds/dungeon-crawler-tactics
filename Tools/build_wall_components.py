#!/usr/bin/env python3
"""Build semantic wall networks from existing painted stone, without rotating lighting."""
import hashlib
import shutil
import json
from pathlib import Path
import zipfile
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'Web/wwwroot/assets/wall-components'
SOURCE = ROOT / 'Web/wwwroot/assets/map-grid-pass/expansion/components/walls'
SIDES = {'north': (0, -1, 1), 'east': (1, 0, 2), 'south': (0, 1, 4), 'west': (-1, 0, 8)}


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2) + '\n')


def save(image, relative):
    path = OUT / relative
    path.parent.mkdir(parents=True, exist_ok=True)
    image.save(path)
    return relative


def source_texture(name, box):
    image = Image.open(SOURCE / (name + '.png')).convert('RGBA').crop(box).resize((32, 32), Image.Resampling.LANCZOS).convert('RGB').convert('RGBA')
    # Matched border texels make facing edge profiles identical, including corners.
    image.paste(image.crop((0, 0, 1, 32)), (31, 0))
    image.paste(image.crop((0, 0, 32, 1)), (0, 31))
    return image


def tile_texture(texture):
    image = Image.new('RGBA', (64, 96))
    for y in (-16, 16, 48, 80):
        for x in (-16, 16, 48):
            image.paste(texture, (x, y))
    image.paste(image.crop((0, 0, 1, 96)), (63, 0))
    image.paste(image.crop((0, 0, 64, 1)), (0, 63))
    return image


def network_mask(bits):
    mask = Image.new('L', (64, 96))
    draw = ImageDraw.Draw(mask)
    draw.rectangle((16, 16, 47, 47), fill=255)
    for side, box in [('north', (16, 0, 47, 31)), ('east', (32, 16, 63, 47)), ('south', (16, 32, 47, 63)), ('west', (0, 16, 31, 47))]:
        if bits & SIDES[side][2]:
            draw.rectangle(box, fill=255)
    return mask


def compose(recipe, base=OUT):
    image = Image.new('RGBA', tuple(recipe['canvas']))
    for item in recipe['instances']:
        image.alpha_composite(Image.open(base / item['file']).convert('RGBA'), tuple(item['offset']))
    return image


def main():
    OUT.mkdir(parents=True, exist_ok=True)
    cap = tile_texture(source_texture('walls-capH', (5, 34, 41, 54)))
    face = tile_texture(source_texture('walls-plain', (5, 58, 41, 94)))
    assets = []
    names = {0: 'isolated-pillar', 1: 'end-north', 2: 'end-east', 3: 'turn-north-east', 4: 'end-south', 5: 'straight-north-south', 6: 'turn-east-south', 7: 'junction-north-east-south', 8: 'end-west', 9: 'turn-north-west', 10: 'straight-east-west', 11: 'junction-north-east-west', 12: 'turn-south-west', 13: 'junction-north-south-west', 14: 'junction-east-south-west', 15: 'junction-cross'}
    for bits in range(16):
        name = names[bits]
        mask = network_mask(bits)
        # Faces and shadow occupy the exposed southern silhouette; all cap material
        # remains complete and independent underneath decorative boundary details.
        shifted = Image.new('L', (64, 96)); shifted.paste(mask, (0, 24))
        shadow_mask = Image.new('L', (64, 96)); shadow_mask.paste(mask, (0, 28))
        shadow = Image.new('RGBA', (64, 96), (5, 12, 20, 100)); shadow.putalpha(shadow_mask.point(lambda a: 95 if a else 0))
        face_layer = face.copy(); face_layer.putalpha(shifted)
        cap_layer = cap.copy(); cap_layer.putalpha(mask)
        layers = {}
        final = Image.new('RGBA', (64, 96))
        for kind, image in [('shadow', shadow), ('face', face_layer), ('cap', cap_layer)]:
            layers[kind] = save(image, f'layers/{name}-{kind}.png'); final.alpha_composite(image)
        path = save(final, f'tiles/{name}.png')
        edges = {side: ('stone-network-32-v1' if bits & data[2] else 'empty') for side, data in SIDES.items()}
        assets.append({'id': name, 'file': path, 'kind': 'network-tile', 'mask': bits, 'size': [64, 96], 'pivot': [32, 32], 'footprint': [0, 0, 64, 64], 'overhang': [0, 0, 0, 32], 'connections': [s for s, d in SIDES.items() if bits & d[2]], 'edgeTags': edges, 'sockets': {s: {'tag': edges[s], 'capInterval': [16, 48] if bits & d[2] else None, 'center': {'north': [32, 0], 'east': [64, 32], 'south': [32, 64], 'west': [0, 32]}[s]} for s, d in SIDES.items()}, 'layers': layers, 'alphaIntent': 'transparent exterior; opaque complete stone in cap footprint', 'provenance': {'kind': 'inferred-assembled-variant', 'primitives': ['cap-material', 'face-material'], 'transforms': 'crop and scale; no rotation or scene-region cropping'}})
    # Export true construction primitives at the same pixel scale.
    parts = []
    def part(name, image, role, source):
        parts.append({'id': name, 'file': save(image, f'parts/{name}.png'), 'size': list(image.size), 'role': role, 'provenance': source})
    part('cap-material', cap, 'opaque repeatable stone cap material', {'file': str((SOURCE / 'walls-capH.png').relative_to(ROOT)), 'crop': [5, 34, 41, 54], 'normalizedTo': [32, 32]})
    part('face-material', face, 'opaque repeatable blue masonry material', {'file': str((SOURCE / 'walls-plain.png').relative_to(ROOT)), 'crop': [5, 58, 41, 94], 'normalizedTo': [32, 32]})
    # Existing separately painted inner/outer turns preserve their original lighting.
    for boundary in ('inner', 'outer'):
        for direction in ('NW', 'NE', 'SE', 'SW'):
            name = f'walls-{boundary}{direction}'
            original = Image.open(SOURCE / (name + '.png')).convert('RGBA')
            part(f'boundary-{boundary}-{direction.lower()}', original, f'{boundary} boundary corner; native 128px detail overlay, optional', {'file': str((SOURCE / (name + '.png')).relative_to(ROOT)), 'kind': 'existing-painted-component', 'noRotation': True})
    arch = Image.open(SOURCE / 'walls-emptyarch.png').convert('RGBA')
    arch = arch.crop((9, 3, 119, 125)).resize((128, 128), Image.Resampling.LANCZOS)
    part('doorway-arch', arch, 'whole doorway with intentional transparent passage', {'file': str((SOURCE / 'walls-emptyarch.png').relative_to(ROOT)), 'kind': 'inferred-crop-normalized-component', 'crop': [9, 3, 119, 125], 'normalizedTo': [128, 128]})
    for name, box in [('doorway-jamb-west', (0, 54, 64, 128)), ('doorway-jamb-east', (64, 54, 128, 128)), ('doorway-lintel', (0, 0, 128, 54))]:
        image = Image.new('RGBA', (128, 128)); image.paste(arch.crop(box), box[:2]); part(name, image, 'door construction layer; same 128px canvas/pivot [64,128]', {'file': 'parts/doorway-arch.png', 'crop': list(box)})
    threshold = Image.new('RGBA', (128, 128)); threshold.paste(face.resize((64, 8)), (32, 120))
    part('doorway-threshold', threshold, 'optional threshold spanning passage ground', {'file': 'parts/face-material.png', 'kind': 'inferred-assembled-variant'})
    # Same 16 pieces assemble each layout; masks are inferred only from cardinal neighbors.
    layouts = {}
    rectangle = {(x, y) for x in range(9) for y in range(7) if x in (0, 8) or y in (0, 6)}
    lshape = {(x, 0) for x in range(9)} | {(8, y) for y in range(4)} | {(x, 3) for x in range(4, 9)} | {(4, y) for y in range(3, 7)} | {(x, 6) for x in range(5)} | {(0, y) for y in range(7)}
    corridor = {(x, 3) for x in range(11)} | {(5, y) for y in range(7)} | {(x, 0) for x in range(3, 8)}
    for name, cells in [('rectangle', rectangle), ('l-shape', lshape), ('corridor-junction', corridor)]:
        recipe = {'schemaVersion': 1, 'id': name, 'canvas': [768, 576], 'grid': 64, 'instances': []}
        for x, y in sorted(cells, key=lambda p: (p[1], p[0])):
            bits = sum(d[2] for d in SIDES.values() if (x + d[0], y + d[1]) in cells)
            recipe['instances'].append({'assetId': names[bits], 'file': f'tiles/{names[bits]}.png', 'cell': [x, y], 'offset': [(x + 1) * 64, (y + 1) * 64]})
        if name == 'rectangle':
            # Place a complete 128px arch into a two-cell opening in the south wall.
            recipe['instances'] = [i for i in recipe['instances'] if i['cell'] not in ([3, 6], [4, 6])]
            recipe['instances'].append({'assetId': 'doorway-arch', 'file': 'parts/doorway-arch.png', 'offset': [256, 416], 'role': 'doorway-overlay-in-opening', 'socketCells': [[3, 6], [4, 6]], 'adapters': {'west': {'cell': [3, 6], 'tag': 'stone-network-32-v1'}, 'east': {'cell': [4, 6], 'tag': 'stone-network-32-v1'}}, 'alignment': 'native arch overlaps opening edges; visual adapter, cap-level joins do not imply pixel-identical painted arch sockets'})
        write_json(OUT / f'samples/{name}.json', recipe); save(compose(recipe), f'samples/{name}.png'); layouts[name] = f'samples/{name}.json'
    manifest = {'schemaVersion': 1, 'grid': {'tileSize': 64, 'capWidth': 32, 'canvas': [64, 96], 'overhang': [0, 0, 0, 32], 'pivot': [32, 32], 'faceProjection': [0, 24], 'shadowProjection': [0, 28], 'lighting': 'source lighting retained, no automatic rotations'}, 'assets': assets, 'construction': parts, 'samples': layouts, 'edgeContract': 'Facing edges require matching stone-network-32-v1 tags. Compare cap boundary RGBA profiles; face/shadow project south and render beneath cap. Empty cannot join connected.', 'limitations': 'A stylized square-grid network assembled from sampled painted material. Boundary overlays and doorway are optional native 128px detail pieces; not automatically socket-compatible network tiles.'}
    for item in assets + parts:
        item['sha256'] = hashlib.sha256((OUT / item['file']).read_bytes()).hexdigest()
        provenance = item.get('provenance', {})
        if provenance.get('file'):
            source = ROOT / provenance['file']
            if not source.exists(): source = OUT / provenance['file']
            if source.exists(): provenance['sha256'] = hashlib.sha256(source.read_bytes()).hexdigest()
    write_json(OUT / 'manifest.json', manifest)
    write_json(ROOT / 'Docs/WallComponents/spec.json', {'schemaVersion': 1, 'grid': manifest['grid'], 'sources': [{'file': str((SOURCE / (name + '.png')).relative_to(ROOT)), 'sha256': hashlib.sha256((SOURCE / (name + '.png')).read_bytes()).hexdigest()} for name in ('walls-capH', 'walls-plain', 'walls-emptyarch')], 'moduleNames': names, 'method': 'Crop painted material into 32px texture; tile periodically in world-aligned orientation; apply cardinal union masks; separate cap, complete masonry, shadow. Imported boundary pieces retain original lighting.'})
    font = ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', 17)
    sheet = Image.new('RGB', (1200, 1050), '#242d39'); draw = ImageDraw.Draw(sheet)
    draw.text((24, 15), 'REUSABLE WALL NETWORK — 64px grid / 32px cap', font=font, fill='white')
    for i, asset in enumerate(assets):
        x = 24 + (i % 4) * 294; y = 60 + (i // 4) * 240
        tile = Image.open(OUT / asset['file']).resize((120, 180), Image.Resampling.NEAREST)
        sheet.paste(tile, (x + 45, y), tile); draw.text((x, y + 185), asset['id'], fill='white', font=font)
        draw.text((x, y + 210), ' '.join(s[0].upper() for s in asset['connections']) or 'ISOLATED', fill='#bac9d9', font=font)
    save(sheet, 'contact-sheet.png')
    part_sheet = Image.new('RGB', (1200, 1050), '#242d39')
    part_draw = ImageDraw.Draw(part_sheet)
    part_draw.text((24, 15), 'CONSTRUCTION PARTS — painted material / native boundary details / doorway layers', font=font, fill='white')
    for i, item in enumerate(parts):
        x = 24 + (i % 4) * 294; y = 60 + (i // 4) * 240
        image = Image.open(OUT / item['file']).convert('RGBA')
        image.thumbnail((176, 176), Image.Resampling.NEAREST)
        part_sheet.paste(image, (x + 40, y), image)
        part_draw.text((x, y + 184), item['id'], font=font, fill='white')
        part_draw.text((x, y + 208), str(item['size']) + ' px', font=font, fill='#bac9d9')
    save(part_sheet, 'construction-contact-sheet.png')
    breakdown = Image.new('RGBA', (1024, 256), '#242d39'); d = ImageDraw.Draw(breakdown)
    for i, kind in enumerate(('shadow', 'face', 'cap', 'assembled')):
        image = Image.open(OUT / (assets[10]['file'] if kind == 'assembled' else assets[10]['layers'][kind])).resize((192, 192), Image.Resampling.NEAREST)
        breakdown.alpha_composite(image, (i * 256 + 32, 16)); d.text((i * 256 + 40, 220), kind, font=font, fill='white')
    save(breakdown, 'layer-breakdown.png')
    replay = '''#!/usr/bin/env python3\n"""Replay any supplied sample JSON using only Pillow and files in this pack."""\nimport json, sys\nfrom pathlib import Path\nfrom PIL import Image\nbase = Path(__file__).resolve().parent\nrecipe = json.loads(Path(sys.argv[1]).read_text())\nim = Image.new("RGBA", tuple(recipe["canvas"]))\nfor item in recipe["instances"]:\n    im.alpha_composite(Image.open(base / item["file"]).convert("RGBA"), tuple(item["offset"]))\nim.save(sys.argv[2])\n'''
    (OUT / 'replay.py').write_text(replay)
    # Bundle the source pixels and authoring evidence; replay remains standalone.
    for source in sorted(SOURCE.glob('walls-*.png')):
        if source.stem in ('walls-capH', 'walls-plain', 'walls-emptyarch') or source.stem.startswith(('walls-inner', 'walls-outer')):
            target = OUT / 'sources' / source.name
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copy2(source, target)
    authored = OUT / 'authored'; authored.mkdir(exist_ok=True)
    for source, target in [(Path(__file__), 'build_wall_components.py'), (ROOT / 'Docs/WallComponents/spec.json', 'spec.json'), (ROOT / 'Docs/WallComponents/README.md', 'README.md'), (ROOT / 'Tools/test_wall_components.py', 'test_wall_components.py'), (ROOT / 'Docs/WallComponents/QA.md', 'QA.md')]:
        if source.exists(): shutil.copy2(source, authored / target)
    guide = ROOT / 'Docs/WallComponents/README.md'
    if guide.exists(): shutil.copy2(guide, OUT / 'GUIDE.md')
    # Hash every shipped byte before closing the archive, excluding the archive
    # and this digest list itself (there is no self-referential hash).
    members = []
    for path in sorted(OUT.rglob('*')):
        if path.is_file() and path.name not in ('package-manifest.json', 'wall-components.zip'):
            members.append({'file': str(path.relative_to(OUT)), 'bytes': path.stat().st_size, 'sha256': hashlib.sha256(path.read_bytes()).hexdigest()})
    write_json(OUT / 'package-manifest.json', {'schemaVersion': 1, 'members': members})
    with zipfile.ZipFile(OUT / 'wall-components.zip' , 'w', zipfile.ZIP_DEFLATED) as archive:
        for path in sorted(OUT.rglob('*')):
            if path.is_file() and path.suffix != '.zip':
                member = zipfile.ZipInfo(str(path.relative_to(OUT)), (2026, 1, 1, 0, 0, 0))
                member.compress_type = zipfile.ZIP_DEFLATED
                member.external_attr = 0o100644 << 16
                archive.writestr(member, path.read_bytes())
    print(f'Built {len(assets)} network tiles, {len(parts)} construction pieces, 3 sample layouts')


if __name__ == '__main__':
    main()
