"""Independent read-only delivery checks; run after build_map_grid_pack.py."""
import hashlib
import io
import json
from pathlib import Path
import unittest
from zipfile import ZipFile
import xml.etree.ElementTree as ET
from PIL import Image, ImageChops, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
PACK = ROOT / 'Web/wwwroot/assets/map-grid-pass'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def equal_pixels(a, b):
    return a.size == b.size and a.convert('RGBA').tobytes() == b.convert('RGBA').tobytes()


class MapGridPackTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest = json.loads((PACK / 'manifest.json').read_text())
        cls.sources = {s['id']: s for s in cls.manifest['sources']}

    def test_sources_and_exact_exhaustive_grid_crops(self):
        sheets = self.manifest['comparison']['cellSheets']
        self.assertEqual(len(sheets), 24)
        self.assertEqual(len({s['id'] for s in sheets}), 24)
        self.assertEqual(len({tuple(s['sourceRect']) for s in sheets}), 24)
        expected_files = set()
        for key in ('reference', 'implementation'):
            source = self.sources[key]
            path = ROOT / source['path']
            self.assertEqual(digest(path), source['sha256'])
            image = Image.open(path)
            self.assertEqual(image.size, (1536, 1024))
            stitched = Image.new('RGBA', image.size)
            for row in range(4):
                for col in range(6):
                    name = f'{chr(65+col)}{row+1}'
                    rect = [col*256,row*256,(col+1)*256,(row+1)*256]
                    sheet = next(s for s in sheets if s['id'] == name)
                    self.assertEqual(sheet['sourceRect'], rect)
                    self.assertTrue((PACK / sheet['path']).is_file())
                    for sr in range(2):
                        for sc in range(2):
                            x, y = col*256+sc*128, row*256+sr*128
                            filename = f'{name}-{sr*2+sc+1}-{key}.png'
                            expected_files.add(filename)
                            crop = Image.open(PACK / 'comparison/subcells' / filename)
                            self.assertTrue(equal_pixels(crop, image.crop((x,y,x+128,y+128))), filename)
                            stitched.paste(crop, (x,y))
            self.assertTrue(equal_pixels(stitched, image), key)
        self.assertEqual({p.name for p in (PACK/'comparison/subcells').glob('*.png')}, expected_files)

    def test_audit_exhaustive_bounds_and_specific_observations(self):
        audit = json.loads((ROOT/'Docs/MapGridPass/comparison.json').read_text())
        self.assertEqual(audit['canvas'], [1536,1024])
        cells = audit['cells']
        self.assertEqual(len(cells),24)
        self.assertEqual(len({c['id'] for c in cells}),24)
        observed = []
        sub_ids = set()
        for row in range(4):
            for col in range(6):
                name = f'{chr(65+col)}{row+1}'
                cell = next(c for c in cells if c['id'] == name)
                self.assertEqual(cell['bounds'],[col*256,row*256,256,256])
                self.assertEqual(len(cell['subcells']),4)
                for index, direction in enumerate(('NW','NE','SW','SE')):
                    sub = next(s for s in cell['subcells'] if s['id'] == f'{name}-{direction}')
                    self.assertNotIn(sub['id'],sub_ids)
                    sub_ids.add(sub['id'])
                    self.assertEqual(sub['bounds'],[col*256+(index%2)*128,row*256+(index//2)*128,128,128])
                    self.assertGreater(len(sub['reference_observed']),10)
                    self.assertGreater(len(sub['implementation_mismatch']),10)
                    self.assertTrue(sub['component_needs'])
                    self.assertTrue(sub['occluded_surface_reconstruction']['instruction'])
                    self.assertTrue(sub['acceptance']['criterion'])
                    observed.append(sub['reference_observed'])
        self.assertEqual(len(sub_ids),96)
        self.assertGreater(len(set(observed)),85, 'Generic duplicate observations cannot substantiate a per-cell audit')

    def test_components_metadata_pixels_and_floor_masks(self):
        components = self.manifest['components']
        self.assertGreater(len(components), 0, 'Reusable components have not been built')
        self.assertEqual(len(components), len({c['id'] for c in components}))
        self.assertEqual(len(components), len({c['path'] for c in components}))
        self.assertEqual(len(components), len({c['sha256'] for c in components}), 'Duplicate exported images must not count as new designs')
        self.assertEqual(len(components), len({(c['sourceId'],tuple(c['sourceRects'][0])) for c in components}), 'Repeated crops must not count as new designs')
        for c in components:
            with self.subTest(component=c['id']):
                for field in ('semanticType','sourceId','sourceRects','provenance','anchor','layer','edgeTags'):
                    self.assertIn(field, c)
                self.assertTrue(c['provenance'])
                self.assertTrue(c['edgeTags'])
                self.assertIn(c['sourceId'], self.sources)
                path = PACK / c['path']
                self.assertEqual(digest(path), c['sha256'])
                image = Image.open(path).convert('RGBA')
                self.assertEqual(list(image.size), c['nativeSize'])
                anchor = c['anchor']
                xy = [anchor['x'],anchor['y']] if isinstance(anchor,dict) else anchor
                self.assertTrue(0 <= xy[0] <= image.width and 0 <= xy[1] <= image.height)
                box = c['sourceRects'][0]
                source = Image.open(ROOT / self.sources[c['sourceId']]['path']).convert('RGBA')
                self.assertTrue(0 <= box[0] < box[2] <= source.width and 0 <= box[1] < box[3] <= source.height)
                expected = source.crop(box)
                if c.get('alphaNormalization') == 'opaque-material-core':
                    expected.putalpha(255)
                elif c.get('alphaNormalization') == 'export-alpha-restore':
                    expected.putalpha(expected.getchannel('A').point(lambda a: 0 if a <= 8 else 255 if a >= 248 else a))
                if c.get('transformations'):
                    raw = Image.open(PACK/c['nativePath']).convert('RGBA')
                    self.assertEqual(digest(PACK/c['nativePath']),c['nativeSha256'])
                    self.assertTrue(equal_pixels(raw,source.crop(box)))
                    self.assertEqual(list(raw.size),c['sourceCropSize'])
                    self.assertEqual(set(c['ports']),{'north','east','south','west'})
                    self.assertTrue(all(isinstance(v,str) and v for v in c['ports'].values()))
                    expected = raw.copy()
                    for operation in c['transformations']:
                        kind = operation['operation']
                        if kind == 'crop':
                            self.assertEqual(operation['sourceRect'],box)
                        elif kind == 'force-opaque':
                            expected.putalpha(255)
                        elif kind == 'background-key-alpha':
                            key = Image.new('RGB',expected.size,tuple(operation['key']))
                            channels = ImageChops.difference(expected.convert('RGB'),key).split()
                            distance = ImageChops.lighter(ImageChops.lighter(channels[0],channels[1]),channels[2])
                            mask = distance.point(lambda v: 0 if v <= operation['threshold'] else 255)
                            expected.putalpha(ImageChops.multiply(expected.getchannel('A'),mask))
                        elif kind == 'reviewed-polygon-mask':
                            mask = Image.new('L',expected.size)
                            ImageDraw.Draw(mask).polygon([tuple(p) for p in operation['points']],fill=255)
                            expected.putalpha(ImageChops.multiply(expected.getchannel('A'),mask))
                        elif kind == 'normalize':
                            resized = expected.resize(tuple(operation['size']),Image.Resampling.LANCZOS)
                            expected = Image.new('RGBA',tuple(operation['canvas']))
                            expected.alpha_composite(resized,tuple(operation['offset']))
                            if c['alphaNormalization'] == 'opaque-material-core':
                                expected.putalpha(255)
                        else:
                            self.fail('Undocumented transformation: '+kind)
                if c.get('derivedTransform') and not c.get('transformations'):
                    transform = c['derivedTransform']
                    resized = expected.resize(tuple(transform['resizedTo']),Image.Resampling.LANCZOS)
                    expected = Image.new('RGBA',tuple(c['nativeSize']))
                    expected.alpha_composite(resized,tuple(transform['canvasOffset']))
                if c.get('alphaMask'):
                    expected.putalpha(Image.open(ROOT/c['alphaMask']).convert('L'))
                self.assertTrue(equal_pixels(expected,image), c['id'])
                self.assertIsNotNone(image.getbbox())
                if c['semanticType'].lower() in ('floor','water') or c.get('alphaNormalization') == 'opaque-material-core':
                    # An opaque reusable floor must cover the entire native rectangle.
                    self.assertEqual(image.getchannel('A').getextrema(), (255,255), c['id'])
                elif c.get('fitMargin',0) > 0:
                    left,top,right,bottom = image.getchannel('A').getbbox()
                    self.assertTrue(left > 0 and top > 0 and right < image.width and bottom < image.height, c['id'])

    def test_component_coverage_references_and_honest_acceptance(self):
        coverage = json.loads((ROOT/'Docs/MapGridPass/component-coverage.json').read_text())
        audit = json.loads((ROOT/'Docs/MapGridPass/comparison.json').read_text())
        known = {c['id'] for c in self.manifest['components']}
        original = json.loads((ROOT/'Web/wwwroot/assets/concept-reconstruction/manifest.json').read_text())
        source_ids = {c['id'] for c in original['layers']}
        expected = {s['id']:s['bounds'] for c in audit['cells'] for s in c['subcells']}
        self.assertEqual(len(coverage['subcells']),96)
        self.assertEqual({s['id'] for s in coverage['subcells']},set(expected))
        needs = 0
        for sub in coverage['subcells']:
            self.assertEqual(sub['bounds'],expected[sub['id']])
            for need in sub['requiredComponents']:
                needs += 1
                self.assertTrue(set(need['availableComponentIds']) <= known)
                self.assertTrue(set(need['existingVisibleSourceIds']) <= source_ids)
                self.assertFalse(need['sourceEvidenceIsCompleteReconstruction'])
        self.assertEqual(needs,coverage['summary']['needInstances'])
        self.assertEqual(coverage['summary']['acceptedSubcells'],0)
        self.assertEqual(coverage['inventoryCounts']['generatedTotal'],len(known))

    def test_expansion_inventory_when_present(self):
        path = PACK/'expansion/manifest.json'
        if not path.exists():
            self.skipTest('Expansion not yet delivered')
        expansion = json.loads(path.read_text())
        integrated = {c['id']:c for c in self.manifest['components']}
        authored = [c for c in expansion['components'] if c['countedAuthoredDesign']]
        self.assertEqual(len(authored),120)
        self.assertEqual(len({c['authoredDesignId'] for c in authored}),120)
        self.assertEqual(len(self.manifest['components']),24+len(expansion['components']))
        self.assertEqual(len(expansion['families']),5)
        for family in expansion['families']:
            members = [c for c in expansion['components'] if c['family'] == family['id']]
            self.assertEqual(sum(c['countedAuthoredDesign'] for c in members),24)
            self.assertEqual(family['authoredDesignCount'],24)
            self.assertEqual(family['componentCount'],len(members))
            self.assertTrue((PACK/family['contactSheet']).is_file())
            for component in members:
                self.assertEqual(integrated[component['id']],component)
                self.assertEqual(component['provenance'],'generated-reconstruction')
                self.assertNotIn('rotate',[t['operation'] for t in component['transformations']])
        for recipe in expansion['nativeAssemblyRecipes']:
            self.assertEqual(digest(PACK/recipe['residualPath']),recipe['residualSha256'])
            self.assertEqual(digest(PACK/recipe['reassembledPath']),recipe['reassembledSha256'])
            residual = Image.open(PACK/recipe['residualPath']).convert('RGBA')
            self.assertEqual(list(residual.size),recipe['size'])
            for placement in recipe['placements']:
                self.assertEqual(placement['operation'],'replace-source-pixels')
                child = Image.open(PACK/placement['nativePath']).convert('RGBA')
                x,y = placement['position']
                self.assertTrue(0 <= x and 0 <= y and x+child.width <= residual.width and y+child.height <= residual.height)
                residual.paste(child,(x,y))
            self.assertTrue(equal_pixels(residual,Image.open(PACK/recipe['reassembledPath'])))
            parent = integrated[recipe['parentId']]
            self.assertTrue(equal_pixels(residual,Image.open(PACK/parent['nativePath'])))


    def test_assembly_recipes_and_openraster(self):
        components = {c['id']: c for c in self.manifest['components']}
        self.assertGreater(len(self.manifest['assemblies']), 0)
        for a in self.manifest['assemblies']:
            merged = Image.new('RGBA', tuple(a['size']))
            for placement in a['placements']:
                c = components[placement['componentId']]
                image = Image.open(PACK/c['path']).convert('RGBA')
                x,y = placement['position']
                self.assertTrue(0 <= x and 0 <= y and x+image.width <= merged.width and y+image.height <= merged.height)
                merged.alpha_composite(image, (x,y))
            self.assertTrue(equal_pixels(merged, Image.open(PACK/a['path'])))
            with ZipFile(PACK/a['oraPath']) as z:
                self.assertIsNone(z.testzip())
                self.assertEqual(z.read('mimetype'), b'image/openraster')
                stack = ET.fromstring(z.read('stack.xml'))
                self.assertEqual((int(stack.attrib['w']),int(stack.attrib['h'])),merged.size)
                layers = stack.findall('./stack/layer')
                self.assertEqual(len(layers),len(a['placements']))
                reconstructed = Image.new('RGBA',merged.size)
                for layer in reversed(layers):
                    image = Image.open(io.BytesIO(z.read(layer.attrib['src']))).convert('RGBA')
                    reconstructed.alpha_composite(image,(int(layer.attrib['x']),int(layer.attrib['y'])))
                self.assertTrue(equal_pixels(merged,reconstructed))
                self.assertTrue(equal_pixels(merged,Image.open(io.BytesIO(z.read('mergedimage.png')))))

    def test_reconstruction_provenance_layers_and_examples(self):
        recipe_path = PACK/'reconstruction/environment-recipe.json'
        self.assertTrue(recipe_path.exists())
        recipe = json.loads(recipe_path.read_text())
        self.assertFalse(recipe['reusableComponent'])
        self.assertEqual(digest(ROOT/recipe['sourceManifest']),recipe['sourceManifestSha256'])
        self.assertTrue(recipe['originalLayers'])
        for layer in recipe['originalLayers']:
            self.assertEqual(digest(ROOT/layer['file']),layer['sha256'])
            self.assertIn(layer['category'],recipe['includeCategories'])
            self.assertEqual(layer['provenance'],'original-visible')
        original = Image.open(PACK/recipe['originalVisible']).convert('RGBA')
        reference = Image.open(ROOT/self.sources['reference']['path']).convert('RGBA')
        opaque = original.getchannel('A').point(lambda a: 255 if a == 255 else 0)
        difference = ImageChops.difference(original.convert('RGB'),reference.convert('RGB'))
        self.assertIsNone(ImageChops.multiply(difference,Image.merge('RGB',(opaque,opaque,opaque))).getbbox())
        inferred = Image.open(PACK/recipe['inferredPatches']).convert('RGBA')
        merged = Image.new('RGBA',original.size)
        merged.alpha_composite(inferred)
        merged.alpha_composite(original)
        final = Image.open(PACK/recipe['output']).convert('RGBA')
        self.assertTrue(equal_pixels(merged,final))
        self.assertEqual(final.getchannel('A').getextrema(),(255,255))
        mask = Image.open(PACK/recipe['inferredMask']).convert('L')
        self.assertEqual(mask.size,original.size)
        for example in recipe['examples']:
            expected_after = final.crop(example['sourceRect'])
            with Image.open(PACK/example['path']) as sheet:
                width,height = expected_after.size
                self.assertEqual(sheet.size,(width*2,height+30))
                self.assertTrue(equal_pixels(sheet.crop((width,30,width*2,height+30)),expected_after))
                reference = Image.open(ROOT/self.sources['reference']['path'])
                self.assertTrue(equal_pixels(sheet.crop((0,30,width,height+30)),reference.crop(example['sourceRect'])))
        with ZipFile(PACK/recipe['ora']) as z:
            self.assertIsNone(z.testzip())
            self.assertTrue(equal_pixels(final,Image.open(io.BytesIO(z.read('mergedimage.png')))))

    def test_zip_exact_members_and_hashes(self):
        archive = PACK/'map-grid-pass.zip'
        files = {str(p.relative_to(PACK)):p for p in PACK.rglob('*') if p.is_file() and p != archive}
        with ZipFile(archive) as z:
            self.assertIsNone(z.testzip())
            self.assertEqual(len(z.namelist()),len(set(z.namelist())))
            self.assertEqual(set(z.namelist()),set(files))
            for name,path in files.items():
                self.assertEqual(hashlib.sha256(z.read(name)).hexdigest(),digest(path),name)

    def test_frozen_assets_unchanged_when_session_baseline_available(self):
        baseline = Path('/tmp/map-grid-frozen-snapshot.json')
        if not baseline.exists():
            self.skipTest('Session-only pre-work baseline absent; see recorded QA evidence')
        for relative, expected in json.loads(baseline.read_text()).items():
            path = ROOT/'Web/wwwroot/assets'/relative
            self.assertTrue(path.is_file(), relative)
            self.assertEqual(digest(path),expected,relative)


if __name__ == '__main__':
    unittest.main()
