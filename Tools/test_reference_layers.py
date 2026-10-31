#!/usr/bin/env python3
"""Independent native-pixel checks for the reference layer deliverable."""
import hashlib
import io
import json
from pathlib import Path, PurePosixPath
import unittest
import zipfile
from xml.etree import ElementTree as ET

import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'Web/wwwroot/assets/reference-layers'
PRIOR = ROOT / 'Web/wwwroot/assets/concept-reconstruction'
MAP = ROOT / 'Web/wwwroot/assets/map-grid-pass/reconstruction'


def digest(data):
    return hashlib.sha256(data).hexdigest()


def rgba(path):
    return Image.open(path).convert('RGBA')


def equal(a, b, label):
    aa, bb = np.asarray(a), np.asarray(b)
    assert aa.shape == bb.shape, f'{label}: dimensions differ'
    changed = int(np.any(aa != bb, axis=2).sum())
    assert changed == 0, f'{label}: {changed} changed pixels'


class ReferenceLayersTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((BASE / 'manifest.json').read_text())
        cls.original = json.loads((PRIOR / 'manifest.json').read_text())
        cls.layers = cls.manifest['layers']

    def compose(self, clean=False):
        canvas = Image.new('RGBA', (1536, 1024))
        for layer in sorted(self.layers, key=lambda x:x['z']):
            if clean and not layer['cleanVisible']:
                continue
            canvas.alpha_composite(rgba(BASE / layer['file']), tuple(layer['offset']))
        return canvas

    def test_native_recomposition(self):
        self.assertEqual(self.manifest['canvas'], [1536, 1024])
        source = ROOT / self.original['source']
        self.assertEqual(digest(source.read_bytes()), self.original['sourceSha256'])
        equal(self.compose(), rgba(source), 'independent PNG source comparison')
        equal(self.compose(), rgba(BASE / 'reconstructed.png'), 'published reconstruction')
        equal(self.compose(True), rgba(MAP / 'clean-environment.png'), 'all dynamic groups disabled')
        equal(self.compose(True), rgba(BASE / 'clean-map.png'), 'published clean map')

    def test_geometry_provenance_and_ownership(self):
        groups = {g['id']:g for g in self.manifest['groups']}
        self.assertEqual(len(groups), len(self.manifest['groups']))
        original = {l['id']:l for l in self.original['layers']}
        seen, zs = set(), set()
        source = np.asarray(rgba(ROOT / self.original['source']))
        inference = np.asarray(Image.open(MAP / 'inferred-region-mask.png').convert('L')) > 0
        for layer in self.layers:
            ident = layer['id']
            self.assertNotIn(ident, seen); seen.add(ident)
            self.assertNotIn(layer['z'], zs); zs.add(layer['z'])
            self.assertIn(layer['group'], groups)
            file = BASE / layer['file']
            self.assertEqual(digest(file.read_bytes()), layer['sha256'])
            im = rgba(file); x,y = layer['offset']; w,h = layer['size']
            self.assertEqual(im.size, (w,h))
            self.assertTrue(all(isinstance(v,int) for v in [x,y,w,h,layer['z']]))
            self.assertTrue(0 <= x < x+w <= 1536 and 0 <= y < y+h <= 1024)
            ax,ay = layer['anchor']; self.assertTrue(0 <= ax <= w and 0 <= ay <= h)
            a = np.asarray(im); mask = a[:,:,3] > 0
            self.assertTrue(mask.any(), ident)
            self.assertLess(int(mask.sum()), 1536*1024*.4, 'full reference draw fallback')
            self.assertNotEqual(layer['file'], 'original-reference.png')
            ref = layer['sourceRef']; p = ROOT / ref['file']
            self.assertEqual(digest(p.read_bytes()), ref['sha256'])
            if layer['kind'] in ('original-visible', 'context-restoration'):
                self.assertIn(ref['id'], original)
                prior = original[ref['id']]
                self.assertEqual(ref['sha256'], prior['componentSha256'])
                self.assertTrue(np.array_equal(a[:,:,:3][mask], source[y:y+h,x:x+w,:3][mask]), ident)
                self.assertTrue(np.isin(a[:,:,3], [0,255]).all())
                if layer['kind'] == 'context-restoration':
                    self.assertFalse(layer['cleanVisible'])
                    self.assertTrue(layer.get('unassignedContext') or layer.get('contextOwner') or groups[layer['group']].get('dynamic'), 'context restoration needs declared ownership')
            elif layer['kind'] == 'inferred-underpaint':
                self.assertTrue(np.all(~mask | inference[y:y+h,x:x+w]), 'invented pixels outside inferred region')
            else:
                self.fail(f'unknown provenance {layer["kind"]}')
        for group in groups.values():
            trail = set(); current = group
            while current.get('parentId'):
                self.assertNotIn(current['id'], trail); trail.add(current['id'])
                self.assertIn(current['parentId'], groups); current = groups[current['parentId']]

    def test_original_fragment_coverage(self):
        inventory = self.manifest['originalFragments']
        self.assertEqual(len(inventory), len(self.original['layers']))
        indexed = {l['id']:l for l in inventory}
        self.assertEqual(len(indexed), len(inventory))
        for prior in self.original['layers']:
            entry = indexed[prior['id']]
            for key in ('file', 'offset', 'size', 'visiblePixels'):
                self.assertEqual(entry.get(key), prior.get(key))
            self.assertEqual(entry.get('sha256'), prior.get('componentSha256'))
        originals = {l['id']:l for l in self.original['layers'] if l.get('file')}
        bysource = {}
        for layer in self.layers:
            if layer['kind'] != 'inferred-underpaint':
                bysource.setdefault(layer['sourceRef']['id'], []).append(layer)
        self.assertEqual(set(bysource), set(originals))
        for ident, prior in originals.items():
            original = rgba(PRIOR / prior['file'])
            restored = Image.new('RGBA', original.size)
            coverage = np.zeros((original.height, original.width), dtype=np.uint16)
            sx,sy = prior['offset']
            for layer in bysource[ident]:
                self.assertEqual(layer['sourceBounds'], prior['offset'] + prior['size'])
                self.assertEqual(layer['sourceAnchor'], prior.get('anchor', [0,0]))
                im = rgba(BASE / layer['file']); x,y = layer['offset']; x-=sx; y-=sy
                self.assertTrue(0 <= x < x+im.width <= original.width and 0 <= y < y+im.height <= original.height)
                coverage[y:y+im.height,x:x+im.width] += np.asarray(im)[:,:,3] > 0
                restored.alpha_composite(im, (x,y))
            self.assertTrue(np.array_equal(coverage, (np.asarray(original)[:,:,3]>0).astype(np.uint16)), ident)
            equal(restored, original, f'original fragment {ident}')

    def test_prior_assets_unchanged(self):
        snapshot = Path('/tmp/reference-layers-prior-hashes.json')
        if not snapshot.exists():
            self.skipTest('session-only frozen baseline unavailable')
        for path, sha in json.loads(snapshot.read_text()).items():
            self.assertEqual(digest((ROOT / path).read_bytes()), sha, path)

    def test_openraster_independent_replay(self):
        byfile = {l['file']:l for l in self.layers}
        with zipfile.ZipFile(BASE / 'reference-layers.ora') as z:
            self.assertEqual(z.read('mimetype'), b'image/openraster')
            tree = ET.fromstring(z.read('stack.xml'))
            self.assertEqual([int(tree.attrib[k]) for k in ('w','h')], [1536,1024])
            nodes = list(tree.iter('layer'))
            self.assertEqual(len(nodes), len(byfile))
            self.assertEqual({n.attrib['src'] for n in nodes}, set(byfile))
            parent = {c:p for p in tree.iter() for c in p}
            canvas = Image.new('RGBA', (1536,1024))
            replay_ids = []
            for n in reversed(nodes):
                layer = byfile[n.attrib['src']]
                self.assertEqual(z.read(n.attrib['src']), (BASE / layer['file']).read_bytes())
                self.assertEqual([int(n.attrib.get(k,0)) for k in ('x','y')], layer['offset'])
                self.assertEqual(parent[n].attrib.get('id'), layer['group'])
                self.assertEqual(n.attrib.get('visibility','visible'), 'visible')
                canvas.alpha_composite(rgba(io.BytesIO(z.read(n.attrib['src']))), tuple(layer['offset']))
                replay_ids.append(layer['id'])
            self.assertEqual(replay_ids, [l['id'] for l in sorted(self.layers,key=lambda l:l['z'])])
            equal(canvas, rgba(ROOT / self.original['source']), 'independent ORA replay')
            equal(canvas, rgba(io.BytesIO(z.read('mergedimage.png'))), 'ORA merged preview')

    def test_archive_complete_and_identical(self):
        with zipfile.ZipFile(BASE / 'reference-layers.zip') as z:
            names = z.namelist()
            self.assertEqual(len(names), len(set(names)), 'duplicate ZIP members')
            for name in names:
                p = PurePosixPath(name)
                self.assertFalse(p.is_absolute() or '..' in p.parts or '\\' in name)
                self.assertTrue((BASE / name).is_file(), name)
                self.assertEqual(z.read(name), (BASE / name).read_bytes(), name)
            inventory = json.loads((BASE / 'package-manifest.json').read_text())['members']
            self.assertEqual(len(inventory), len({entry['file'] for entry in inventory}))
            self.assertEqual(set(names), {entry['file'] for entry in inventory} | {'package-manifest.json'})
            for entry in inventory:
                name = entry['file']
                self.assertEqual(len(z.read(name)), entry['bytes'], name)
                self.assertEqual(digest(z.read(name)), entry['sha256'], name)
            self.assertIn('manifest.json', names)
            self.assertIn('scene.json', names)
            self.assertIn('reference-layers.ora', names)
            self.assertTrue({l['file'] for l in self.layers} <= set(names))


if __name__ == '__main__':
    unittest.main()
