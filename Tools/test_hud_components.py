#!/usr/bin/env python3
"""Independent validation of delivered HUD fragments, widgets, slices and archives."""
import hashlib
import io
import json
from pathlib import Path
import xml.etree.ElementTree as ET
import zipfile
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'Web/wwwroot/assets/hud-components'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def rgba(image):
    data = np.array(image.convert('RGBA'))
    # RGB beneath zero alpha has no displayed meaning; retain every visible RGBA byte.
    data[data[:, :, 3] == 0, :3] = 0
    return data

def same(a, b, label):
    assert a.size == b.size, label + ': dimensions differ'
    assert np.array_equal(rgba(a), rgba(b)), label + ': RGBA pixels differ'

def main():
    manifest = json.loads((BASE / 'manifest.json').read_text())
    spec = json.loads((ROOT / 'Docs/HudComponents/spec.json').read_text())
    source_path = ROOT / manifest['source']
    assert sha(source_path.read_bytes()) == manifest['sourceSha256']
    assert sha((ROOT / manifest['fragmentManifest']).read_bytes()) == manifest['fragmentManifestSha256']
    source = Image.open(source_path).convert('RGBA')
    canvas = tuple(manifest['canvas'])
    assert source.size == canvas == (1536, 1024)
    assert set(np.unique(np.array(source)[:, :, 3])) == {0, 255}
    layers = manifest['layers']; groups = manifest['groups']
    ids = {layer['id']: layer for layer in layers}
    group_ids = {group['id']: group for group in groups}
    assert len(ids) == len(layers) == 78
    assert len(group_ids) == len(groups) == 17
    assert set(ids).isdisjoint(group_ids)
    assert [(g['id'], g['parentId'], g['layerIds']) for g in groups] == [(g['id'], g['parentId'], g['layerIds']) for g in spec['groups']]
    references = []
    images = {}
    for group in groups:
        seen = {group['id']}; parent = group['parentId']
        while parent != 'hud':
            assert parent in group_ids and parent not in seen, 'invalid/cyclic group parent'
            seen.add(parent); parent = group_ids[parent]['parentId']
        assert group['bounds'] == group['offset'] + group['size']
        for ident in group['layerIds']:
            assert ident in ids and ids[ident]['parentId'] == group['id']
            references.append(ident)
    assert sorted(references) == sorted(ids), 'missing or duplicated group membership'
    rebuilt = Image.new('RGBA', canvas)
    for layer in layers:
        ident = layer['id']; path = BASE / layer['file']
        assert layer['category'].startswith('ui-') or layer['category'] == 'text', 'non-HUD layer'
        assert not any(word in ident for word in ('tooltip', 'speech', 'world-'))
        assert layer['parentId'] in group_ids
        assert layer.get('sourceParentId') is None or layer['sourceParentId'] in ids
        assert sha(path.read_bytes()) == layer['sha256']
        image = Image.open(path).convert('RGBA'); images[ident] = image
        assert image.size == tuple(layer['size'])
        assert layer['bounds'] == layer['offset'] + layer['size']
        x, y = layer['offset']; w, h = image.size
        assert 0 <= x < x+w <= canvas[0] and 0 <= y < y+h <= canvas[1]
        parent = group_ids[layer['parentId']]
        assert layer['offsetInParent'] == [x-parent['offset'][0], y-parent['offset'][1]]
        assert set(np.unique(np.array(image)[:, :, 3])) <= {0, 255}
        assert np.count_nonzero(np.array(image)[:, :, 3]) == layer['visiblePixels']
        rebuilt.alpha_composite(image, (x, y))
    same(rebuilt, source, 'independent raw fragment replay')
    assert sha(rgba(rebuilt).tobytes()) == manifest['verification']['normalizedRgbaSha256']
    for group in groups:
        widget = Image.new('RGBA', tuple(group['size']))
        for ident in group['layerIds']:
            widget.alpha_composite(images[ident], tuple(ids[ident]['offsetInParent']))
        same(widget, Image.open(BASE / group['file']), group['id'])
    required = {'objective-lantern','objective-label','phase-party','phase-label','phase-dot','phase-round', 'hud-frame','hud-body','hud-carl-name','hud-hp-value','hud-mana-value','hud-movement-count','hud-movement-label','target-card-name','target-card-damage-value','target-card-damage-label','end-turn-label','end-turn-arrow','party-carl-glow','action-move-glow'}
    required |= {f'phase-diamond-{n}' for n in (1,2,3)}
    required |= {f'party-{name}-{part}' for name in ('carl','donut','katia','mongo') for part in ('portrait','marker','frame','body')}
    required |= {f'action-{name}-{part}' for name in ('move','strike','skills','items') for part in ('icon','label','frame','body')}
    assert required <= ids.keys(), 'visible semantic component omitted'
    for item in manifest['nineSlice']:
        original = images[item['layerId']]
        joined = Image.new('RGBA', original.size)
        coverage = np.zeros(original.size[::-1], dtype=np.uint8)
        assert len(item['pieces']) == 9
        for piece in item['pieces']:
            l,t,r,b = piece['rect']; assert 0 <= l < r <= original.width and 0 <= t < b <= original.height
            image = Image.open(BASE / piece['file']).convert('RGBA')
            assert image.size == (r-l,b-t)
            same(image, original.crop((l,t,r,b)), piece['file'])
            joined.alpha_composite(image, (l,t)); coverage[t:b,l:r] += 1
        assert np.all(coverage == 1)
        same(joined, original, item['layerId'] + ' nine-slice rejoin')
    artifacts = manifest['artifacts']
    with zipfile.ZipFile(BASE / artifacts['layered']) as archive:
        assert archive.read('mimetype') == b'image/openraster'
        tree = ET.fromstring(archive.read('stack.xml'))
        assert (int(tree.get('w')), int(tree.get('h'))) == canvas
        ora_layers = list(tree.iter('layer'))
        assert {l.get('name') for l in ora_layers} == set(ids)
        assert len(ora_layers) == len(layers)
        ora_rebuilt = Image.new('RGBA', canvas)
        for layer in reversed(ora_layers):
            ident = layer.get('name'); image = Image.open(io.BytesIO(archive.read(layer.get('src'))))
            same(image, images[ident], 'ORA ' + ident)
            assert [int(layer.get('x')),int(layer.get('y'))] == ids[ident]['offset']
            ora_rebuilt.alpha_composite(image.convert('RGBA'), tuple(ids[ident]['offset']))
        same(ora_rebuilt, source, 'ORA replay')
        same(Image.open(io.BytesIO(archive.read('mergedimage.png'))), source, 'ORA merged image')
    with zipfile.ZipFile(BASE / artifacts['archive']) as archive:
        assert archive.testzip() is None
        for path in BASE.rglob('*'):
            if path.is_file() and path.name != artifacts['archive']:
                assert archive.read(path.relative_to(BASE).as_posix()) == path.read_bytes(), 'ZIP missing/stale ' + str(path)
    for key in ('source','rebuilt'):
        same(Image.open(BASE / artifacts[key]), source, key)
    assert (BASE / artifacts['overview']).is_file()
    print('PASS: 78 PNG fragments; 17 widgets; exact normalized RGBA raw/ORA replay; hierarchy, hashes, ZIP and 27 nine-slices.')

if __name__ == '__main__':
    main()
