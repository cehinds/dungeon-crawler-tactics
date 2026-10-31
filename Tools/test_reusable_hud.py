#!/usr/bin/env python3
"""Independent QA for reconstructed, reusable HUD assets (not original pixel fidelity)."""
import hashlib
import json
import io
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
from collections import deque
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'Web/wwwroot/assets/hud-reusable'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def same(first, second, label):
    a = np.array(first.convert('RGBA')); b = np.array(second.convert('RGBA'))
    a[a[:, :, 3] == 0, :3] = 0; b[b[:, :, 3] == 0, :3] = 0
    assert a.shape == b.shape and np.array_equal(a, b), label + ': RGBA mismatch'

def check_no_enclosed_holes(alpha, label):
    """Every transparent pixel must connect to the exterior of the image."""
    clear = np.pad(alpha == 0, 1, constant_values=True)
    reached = np.zeros(clear.shape, dtype=bool)
    queue = deque([(0, 0)]); reached[0, 0] = True
    while queue:
        y, x = queue.popleft()
        for ny, nx in ((y-1,x),(y+1,x),(y,x-1),(y,x+1)):
            if 0 <= ny < clear.shape[0] and 0 <= nx < clear.shape[1] and clear[ny,nx] and not reached[ny,nx]:
                reached[ny,nx] = True; queue.append((ny,nx))
    assert np.all(reached[clear]), label + ': enclosed transparent cutout'


def main():
    manifest = json.loads((BASE / 'manifest.json').read_text())
    source_path = ROOT / manifest['sourceManifest']
    assert sha(source_path.read_bytes()) == manifest['sourceManifestSha256']
    source = json.loads(source_path.read_text())
    source_layers = {a['id']:a for a in source['layers']}
    assets = manifest['assets']; groups = manifest['groups']
    ids = {a['id']:a for a in assets}; gids = {g['id']:g for g in groups}
    assert len(ids) == len(assets) and len(gids) == len(groups) == 17
    assert len(manifest['originals']) == 78
    for original in manifest['originals']:
        assert (BASE / original['file']).read_bytes() == (source_path.parent / source_layers[original['id']]['file']).read_bytes()
    snapshot = Path('/tmp/hud-components-original-qa-hashes.json')
    if snapshot.exists():
        expected = json.loads(snapshot.read_text())
        actual = {str(p.relative_to(source_path.parent)):sha(p.read_bytes()) for p in source_path.parent.rglob('*') if p.is_file()}
        assert actual == expected, 'original hud-components assets changed'
    images = {}
    def compose(entries):
        image = Image.new('RGBA', tuple(manifest['canvas']))
        for asset in sorted(entries,key=lambda a:(a['z'],a['id'])):
            image.alpha_composite(images[asset['id']],tuple(asset['offset']))
        return image
    backgrounds = []
    for asset in assets:
        ident = asset['id']; path = BASE / asset['file']
        assert sha(path.read_bytes()) == asset['sha256']
        image = Image.open(path).convert('RGBA'); images[ident] = image
        assert image.size == tuple(asset['size'])
        assert asset['bounds'] == asset['offset'] + asset['size']
        assert asset['parentId'] in gids
        parent = gids[asset['parentId']]
        assert asset['offsetInParent'] == [asset['offset'][0]-parent['offset'][0],asset['offset'][1]-parent['offset'][1]]
        assert asset['pivot']['kind'] == 'top-left'
        if asset['role'] == 'clean-background':
            backgrounds.append(asset)
            mask = Image.new('L',tuple(manifest['canvas'])); draw = ImageDraw.Draw(mask)
            shape = asset['exteriorShape']
            if shape['type'] == 'rect':
                x,y,w,h = shape['bounds']; draw.rectangle((x,y,x+w-1,y+h-1),fill=255)
            else:
                assert shape['type'] == 'polygon'; draw.polygon([tuple(p) for p in shape['points']],fill=255)
            x,y = asset['offset']; w,h = image.size
            expected = mask.crop((x,y,x+w,y+h))
            alpha = np.array(image)[:,:,3]
            assert np.array_equal(alpha,np.array(expected)), ident + ': silhouette/opacity mismatch'
            assert np.array_equal(np.array(Image.open(BASE/asset['maskFile']).convert('L')),alpha)
            check_no_enclosed_holes(alpha,ident)
        provenance = asset['provenance']
        if provenance['kind'] == 'source-crop':
            original = Image.open(source_path.parent/source_layers[provenance['sourceLayerId']]['file'])
            crop = original.crop(tuple(provenance['crop']))
            if (asset.get('sourceLayerId','').startswith('party-') and asset['role'].startswith('border-')) or (asset.get('sourceLayerId','').endswith('-outline') and asset['role'].startswith('stat-')):
                actual = np.array(image); expected = np.array(crop.convert('RGBA'))
                present = actual[:,:,3] > 0
                assert np.array_equal(actual[present],expected[present]), ident + ': altered source frame pixels'
            else:
                same(image,crop,ident)
        if provenance['kind'] == 'source-pixel-subset':
            original = Image.open(source_path.parent/source_layers[asset['sourceLayerId']]['file']).convert('RGBA')
            expected = np.array(original); actual = np.array(image)
            assert expected.shape == actual.shape
            present = actual[:,:,3] > 0
            assert np.array_equal(actual[present],expected[present]), ident + ': altered fringe source pixels'
        if asset['role'] == 'complete-stat-track':
            assert np.all(np.array(image)[:,:,3] == 255), ident + ': incomplete track'
    assert len(backgrounds) == 16
    referenced = []
    for group in groups:
        parent = group['parentId']; seen = {group['id']}
        while parent != 'hud':
            assert parent in gids and parent not in seen
            seen.add(parent); parent = gids[parent]['parentId']
        entries = [ids[i] for i in group['assetIds']]
        assert all(a['parentId'] == group['id'] for a in entries)
        assert group['assetIds'] == [a['id'] for a in sorted(entries,key=lambda a:(a['z'],a['id']))]
        referenced.extend(group['assetIds'])
        replay = compose(entries); x,y,w,h = group['bounds']
        same(replay.crop((x,y,x+w,y+h)),Image.open(BASE/group['repopulatedFile']),group['id'])
        if group['blankFile']:
            blank_entries = [ids[i] for i in group['blankAssetIds']]
            assert all(a['role'] == 'clean-background' or a['role'].startswith(('border-','stat-')) or a['role'] == 'complete-stat-track' for a in blank_entries)
            blank = compose(blank_entries); x,y,w,h = group['blankBounds']
            same(blank.crop((x,y,x+w,y+h)),Image.open(BASE/group['blankFile']),group['id']+' blank')
            if group['id'] in ('hp','mana'):
                pixels = np.array(Image.open(BASE/group['blankFile']).convert('RGBA')).astype(np.int16)
                red = (pixels[:,:,0]>100) & (pixels[:,:,0]>pixels[:,:,1]*1.5) & (pixels[:,:,3]>0)
                cyan = (pixels[:,:,1]>100) & (pixels[:,:,2]>100) & (pixels[:,:,0]<80) & (pixels[:,:,3]>0)
                assert not np.any(red | cyan), group['id'] + ': colored stat fill contamination in blank'
    assert sorted(referenced) == sorted(ids)
    # All exported frame pieces, including any center residual, rejoin the literal source border.
    frame_sources = {a['sourceLayerId'] for a in assets if a['role'].startswith('border-') or (a['role'].startswith('stat-') and a.get('sourceLayerId','').endswith('-outline'))}
    for ident in frame_sources:
        original = source_layers[ident]; joined = Image.new('RGBA',tuple(original['size']))
        coverage = np.zeros(tuple(original['size'])[::-1],dtype=np.uint8)
        for asset in assets:
            if asset.get('sourceLayerId') != ident: continue
            if asset['role'] == 'source-boundary-fringe':
                joined.alpha_composite(images[asset['id']],(0,0)); continue
            if not (asset['role'].startswith('border-') or asset['role'].startswith('stat-')): continue
            l,t,r,b = asset['slice']['rect'] if 'slice' in asset else asset['provenance']['crop']
            assert 0 <= l < r <= joined.width and 0 <= t < b <= joined.height
            coverage[t:b,l:r] += 1; joined.alpha_composite(images[asset['id']],(l,t))
        assert np.max(coverage) <= 1
        same(joined,Image.open(source_path.parent/original['file']),ident+' border rejoin')
    for material in manifest['materials'].values():
        assert sha((BASE/material['file']).read_bytes()) == material['sha256']
        assert sha((ROOT/material['originalFile']).read_bytes()) == material['originalSha256']
    full = compose(assets)
    same(full,Image.open(BASE/manifest['artifacts']['repopulated']),'full repopulated HUD')
    with zipfile.ZipFile(BASE/manifest['artifacts']['layered']) as archive:
        assert archive.read('mimetype') == b'image/openraster'
        root = ET.fromstring(archive.read('stack.xml')); layers = list(root.iter('layer'))
        assert [l.get('name') for l in reversed(layers)] == [a['id'] for a in sorted(assets,key=lambda a:(a['z'],a['id']))]
        replay = Image.new('RGBA',tuple(manifest['canvas']))
        for layer in reversed(layers):
            ident = layer.get('name'); image = Image.open(io.BytesIO(archive.read(layer.get('src')))).convert('RGBA')
            same(image,images[ident],'ORA '+ident)
            offset = (int(layer.get('x')),int(layer.get('y')))
            assert offset == tuple(ids[ident]['offset']); replay.alpha_composite(image,offset)
        same(replay,full,'ORA replay')
        same(Image.open(io.BytesIO(archive.read('mergedimage.png'))),full,'ORA merged')
    package = json.loads((BASE/'package-manifest.json').read_text())
    package_files = {entry['file'] for entry in package['members']}
    expected_files = {p.relative_to(BASE).as_posix() for p in BASE.rglob('*') if p.is_file() and p.name not in ('package-manifest.json',manifest['artifacts']['archive'])}
    assert package_files == expected_files
    for entry in package['members']:
        content = (BASE/entry['file']).read_bytes()
        assert len(content) == entry['bytes'] and sha(content) == entry['sha256']
    with zipfile.ZipFile(BASE/manifest['artifacts']['archive']) as archive:
        assert archive.testzip() is None
        for path in BASE.rglob('*'):
            if path.is_file() and path.name != manifest['artifacts']['archive']:
                assert archive.read(path.relative_to(BASE).as_posix()) == path.read_bytes()
    print(f'PASS: {len(assets)} parts; {len(backgrounds)} opaque clean backgrounds; 17 groups; original assets invariant; widgets, border rejoin, hashes, ZIP and ORA consistent.')

if __name__ == '__main__':
    main()
