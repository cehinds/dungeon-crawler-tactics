#!/usr/bin/env python3
"""Independent exploration component provenance, replay, and package checks."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import unittest
import zipfile
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'Web/wwwroot/assets/exploration-components'
SPEC = ROOT / 'Docs/ExplorationComponents/spec.json'

def sha(data):
    return hashlib.sha256(data).hexdigest()

def rgba(path):
    return Image.open(path).convert('RGBA')

def pixel_digest(path):
    """Exact decoded pixels including RGB under alpha; never perceptual similarity."""
    image = rgba(path)
    return image.size, sha(image.tobytes())

def assert_same(test, a, b, message):
    test.assertEqual(a.size, b.size, message + ' dimensions')
    test.assertEqual(a.tobytes(), b.tobytes(), message + ' decoded RGBA')

class ExplorationComponentsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.spec = json.loads(SPEC.read_text())
        cls.m = json.loads((BASE / 'manifest.json').read_text())

    def test_reference_and_context_spec(self):
        reference = rgba(ROOT / self.spec['reference'])
        self.assertEqual(list(reference.size), self.spec['referenceSize'])
        ids = [r['id'] for r in self.spec['sourceRegions']]
        self.assertEqual(len(ids), len(set(ids)))
        self.assertGreaterEqual(len(ids), 50)
        for region in self.spec['sourceRegions']:
            self.assertEqual(region['kind'], 'context-containing-reference-crop')
            x, y, w, h = region['bounds']
            self.assertTrue(w > 0 and h > 0 and 0 <= x < x+w <= reference.width and 0 <= y < y+h <= reference.height, region['id'])

    def test_component_provenance_and_exact_dedupe(self):
        components = self.m['components']
        self.assertEqual(len(components), len({c['id'] for c in components}))
        reference = rgba(ROOT / self.spec['reference'])
        kinds = {}
        for c in components:
            im = rgba(BASE / c['path'])
            self.assertEqual(list(im.size), c['size'], c['id'])
            digest = sha(str(im.size).encode() + im.tobytes())
            self.assertEqual(digest, c['pixelHash'], c['id'])
            p = c['provenance']; kind = p['kind']
            kinds[kind] = kinds.get(kind, 0) + 1
            x, y, w, h = p['sourceBounds']
            source = rgba(ROOT / p['source'])
            packed_source = BASE/p['sourceInPackage']
            self.assertEqual(sha(packed_source.read_bytes()), p['sourceSha256'])
            assert_same(self, source, rgba(packed_source), c['id']+' packaged source')
            self.assertTrue(0 <= x < x+w <= source.width and 0 <= y < y+h <= source.height, c['id'])
            padding = p.get('exportPadding', 0)
            evidence = im.crop((padding,padding,padding+w,padding+h)) if padding else im
            assert_same(self, evidence, source.crop((x,y,x+w,y+h)), c['id'] + ' source crop')
            self.assertEqual(im.size, (w+2*padding,h+2*padding))
            if padding:
                alpha_export = np.asarray(im)[:,:,3]
                self.assertFalse(alpha_export[:padding,:].any() or alpha_export[-padding:,:].any() or alpha_export[:,:padding].any() or alpha_export[:,-padding:].any(), c['id']+' padding must be truly transparent')
            if kind == 'inferred-restored-whole-object':
                self.assertIn('not exact source pixels', p['claim'])
                normal = Image.new('RGBA',(128,128))
                small = im.copy(); small.thumbnail((112,112),Image.Resampling.NEAREST)
                normal.paste(small,((128-small.width)//2,(128-small.height)//2))
                self.assertEqual(c['normalized128Size'],[128,128])
                assert_same(self,normal,rgba(BASE/c['normalized128Path']),c['id']+' normalized derived replay')
                cx,cy,cw,ch = p['cellBounds']
                cell_alpha = source.crop((cx,cy,cx+cw,cy+ch)).getchannel('A')
                self.assertEqual(cell_alpha.tobytes(), Image.open(BASE/p['alphaMask']).convert('L').tobytes(), c['id']+' extraction mask')
                cell_pixels = np.asarray(cell_alpha) >= 128
                if c['category'] != 'effects':
                    self.assertFalse(cell_pixels[0,:].any() or cell_pixels[-1,:].any() or cell_pixels[:,0].any() or cell_pixels[:,-1].any(), c['id']+' solid silhouette clipped at atlas selection boundary')
                self.assertTrue(cx <= x < x+w <= cx+cw and cy <= y < y+h <= cy+ch)
                alpha = np.asarray(im)[:,:,3]
                self.assertTrue((alpha == 0).any(), c['id'] + ' missing alpha exterior')
                self.assertGreater((alpha > 0).mean(), .05, c['id'])
                self.assertLess((alpha > 0).mean(), .98, c['id'])
            elif kind == 'context-containing-reference-crop':
                self.assertIn('context', p['claim'])
                self.assertEqual(p['source'], self.spec['reference'])
            elif kind == 'visible-clean-surface-patch':
                self.assertEqual(p['source'], self.spec['reference'])
            else:
                self.fail('unknown provenance kind ' + kind)
            if c['deduplication'] == 'exact-existing':
                assert_same(self, im, rgba(ROOT/c['existingPath']), c['id']+' exact reuse')
            else:
                self.assertEqual(c['deduplication'], 'new')
        self.assertEqual(kinds, self.m['counts'])
        self.assertGreaterEqual(kinds['inferred-restored-whole-object'], 40)
        reused = {c['id'] for c in components if c['deduplication']=='exact-existing'}
        self.assertEqual(reused, {c['id'] for c in self.m['deduplication']['reused']})
        self.assertEqual(self.m['deduplication']['newCount'], len(components)-len(reused))

    def test_independent_exact_dedupe_scan(self):
        expected = {}
        excluded = self.m['deduplication']['excludedPathSubstrings']
        assets = ROOT/'Web/wwwroot/assets'
        scanned = 0
        for path in sorted(assets.rglob('*.png')):
            relative = path.relative_to(assets).as_posix()
            if any(term in relative.lower() for term in excluded):
                continue
            key = pixel_digest(path)
            expected.setdefault(key,path)
            scanned += 1
        self.assertEqual(scanned, self.m['deduplication']['scannedPngCount'])
        for c in self.m['components']:
            match = expected.get(pixel_digest(BASE/c['path']))
            self.assertEqual(match is not None, c['deduplication']=='exact-existing', c['id'])
            if match is not None:
                self.assertEqual(str(match.relative_to(ROOT)),c['existingPath'])

    def test_component_only_independent_replay_and_surface_coverage(self):
        cs = {c['id']:c for c in self.m['components']}
        r = json.loads((BASE/'room-recipe.json').read_text())
        self.assertIn('Not a pixel reconstruction', r['claim'])
        out = Image.new('RGBA', tuple(r['canvas']), r['background'])
        surface = r['surface']; c = cs[surface['componentId']]
        self.assertEqual(c['provenance']['kind'], 'visible-clean-surface-patch')
        im = rgba(BASE/c['path']); x,y,w,h = surface['tileRect']
        self.assertGreater(w*h/(out.width*out.height), .75)
        floor = Image.new('RGBA', out.size)
        for yy in range(y,y+h,im.height):
            for xx in range(x,x+w,im.width):
                out.alpha_composite(im,(xx,yy)); floor.alpha_composite(im,(xx,yy))
        coverage = np.asarray(floor)[:,:,3] > 0
        for overlay in r.get('surfaceOverlays', []):
            c = cs[overlay['componentId']]
            self.assertEqual(c['provenance']['kind'], 'visible-clean-surface-patch')
            im = rgba(BASE/c['path']).resize(tuple(overlay['size']), Image.Resampling.NEAREST)
            px,py = overlay['position']
            out.alpha_composite(im,(px,py))
            coverage[py:py+im.height,px:px+im.width] &= ~(np.asarray(im)[:,:,3]>0)
        for item in sorted(r['placements'],key=lambda i:i['layer']):
            c = cs[item['componentId']]
            self.assertEqual(c['provenance']['kind'], 'inferred-restored-whole-object')
            im = rgba(BASE/c['path']); im.thumbnail(tuple(item['maxSize']))
            px,py = item['position']
            self.assertTrue(0 <= px and 0 <= py and px+im.width <= out.width and py+im.height <= out.height)
            out.alpha_composite(im, (px,py))
            alpha = np.asarray(im)[:,:,3]>0
            coverage[py:py+im.height,px:px+im.width] &= ~alpha
        self.assertGreater(coverage.mean(), .35, 'floor must remain meaningfully visible')
        self.assertGreaterEqual(len({i['componentId'] for i in r['placements']}), 20, 'furnished composition needs meaningful component variety')
        assert_same(self,out,rgba(BASE/'previews/reassembled-room.png'),'independent component-only replay')

    def test_prior_packs_preserved(self):
        baseline = Path('/tmp/exploration-components-prior-hashes.json')
        if not baseline.exists():
            self.skipTest('session pre-build snapshot is unavailable outside this workspace')
        records = json.loads(baseline.read_text())
        self.assertGreater(len(records), 25000)
        self.assertTrue(any('/wall-components/' in name for name in records))
        for name, digest in records.items():
            self.assertEqual(sha((ROOT / name).read_bytes()), digest, name)

    def test_archive_closure(self):
        archives = list(BASE.glob('*.zip'))
        self.assertEqual(len(archives), 1)
        with zipfile.ZipFile(archives[0]) as archive:
            names = archive.namelist()
            self.assertEqual(len(names), len(set(names)))
            local = {str(p.relative_to(BASE)) for p in BASE.rglob('*') if p.is_file() and p.suffix != '.zip'}
            self.assertEqual(set(names), local)
            records = json.loads((BASE/'package-hashes.json').read_text())['members']
            hashes = {r['file']:r['sha256'] for r in records}
            self.assertEqual(len(records),len(hashes))
            for record in records:
                self.assertEqual(len(archive.read(record['file'])),record['bytes'])
            self.assertEqual(set(hashes), local-{'package-hashes.json'})
            for name,digest in hashes.items():
                self.assertEqual(sha(archive.read(name)),digest,name+' package hash')
            for name in names:
                path = PurePosixPath(name)
                self.assertFalse(path.is_absolute() or '..' in path.parts or '\\' in name)
                self.assertEqual(archive.read(name), (BASE / name).read_bytes(), name)

if __name__ == '__main__':
    unittest.main(verbosity=2)
