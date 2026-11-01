#!/usr/bin/env python3
"""Independent source/mask reconstruction, mode separation and payload closure checks."""
import hashlib
import json
import re
import unittest
from pathlib import Path
from PIL import Image,ImageChops

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'Web/wwwroot/assets/top-down-layer-kit'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def image(asset):return Image.open(OUT/asset['path']).convert('RGBA')


def archive(path):return path.name=='top-down-layer-kit.zip' or '.zip.part-' in path.name or path.name.endswith('.zip.parts.json') or path.name=='assemble_archive_parts.py'


class LayerTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):cls.manifest=json.loads((OUT/'manifest.json').read_text())

    def test_all36_coverage_and_categories(self):
        scenes=self.manifest['scenes'];self.assertEqual(len(scenes),36);self.assertEqual(len({s['id'] for s in scenes}),36)
        self.assertEqual({s['id'] for s in scenes},{s['id'] for s in self.manifest['coverage']})
        for scene in scenes:
            self.assertTrue(scene['exact']['components']);self.assertIn('reusable',scene)
            for mode in ('exact','reusable'):
                layers=scene[mode]['categoryLayers'];components=scene[mode]['components']
                self.assertEqual(sum(layer['count'] for layer in layers),len(components))
                self.assertEqual(scene[mode]['categoryLayerCount'],len(layers))
                self.assertEqual(len({c['id'] for c in components}),len(components))

    def test_exact_masks_source_pixels_and_rebuilds(self):
        for scene in self.manifest['scenes']:
            source=image(scene['source']);w,h=source.size;union=Image.new('L',source.size)
            self.assertEqual(sha(Path(scene['source']['originalInput'])),scene['source']['originalSha256'])
            rebuilt=image(scene['exact']['base'])
            for component in scene['exact']['components']:
                pixels=image(component['asset']);mask=Image.open(OUT/component['mask']['path']).convert('L')
                self.assertEqual(mask.size,source.size);self.assertEqual(mask.histogram()[0]+mask.histogram()[255],w*h)
                x,y,cw,ch=component['bounds'];expected=source.crop((x,y,x+cw,y+ch));alpha=mask.crop((x,y,x+cw,y+ch))
                self.assertEqual(pixels.getchannel('A').tobytes(),alpha.tobytes())
                difference=ImageChops.difference(pixels.convert('RGB'),expected.convert('RGB'))
                self.assertTrue(all(ImageChops.multiply(channel,alpha).getbbox() is None for channel in difference.split()))
                self.assertLessEqual(mask.histogram()[255]/(w*h),.8)
                rebuilt.alpha_composite(pixels,(x,y));union=ImageChops.lighter(union,mask)
            self.assertEqual(source.tobytes(),rebuilt.tobytes(),scene['id'])
            self.assertEqual(rebuilt.tobytes(),image(scene['exact']['reconstructed']).tobytes())
            self.assertEqual(scene['exact']['metrics']['differentPixels'],0)
            self.assertEqual(union.tobytes(),Image.open(OUT/scene['exact']['unionMask']['path']).convert('L').tobytes())
            base=image(scene['exact']['base']);outside=ImageChops.invert(union)
            for channel in ImageChops.difference(base,source).split():self.assertIsNone(ImageChops.multiply(channel,outside).getbbox())

    def test_reusable_composition_and_provenance(self):
        for scene in self.manifest['scenes']:
            source=image(scene['source']);mode=scene['reusable'];rebuilt=image(mode['base'])
            self.assertNotEqual(source.tobytes(),rebuilt.tobytes())
            self.assertTrue(mode['baseProvenance']['kind'])
            for component in mode['components']:
                self.assertTrue(component['provenance']['kind']);rebuilt.alpha_composite(image(component['asset']),(component['x'],component['y']))
            self.assertEqual(rebuilt.tobytes(),image(mode['reconstructed']).tobytes())
            differences=ImageChops.difference(source,rebuilt).split();maximum=differences[0]
            for channel in differences[1:]:maximum=ImageChops.lighter(maximum,channel)
            self.assertEqual(sum(maximum.histogram()[1:]),mode['metrics']['differentPixels'])

    def test_grid_addresses_and_native_positions(self):
        for scene in self.manifest['scenes']:
            w,h=scene['size'];self.assertEqual(scene['grid']['xBoundaries'],[round(i*w/14) for i in range(15)])
            self.assertEqual(scene['grid']['yBoundaries'],[round(i*h/14) for i in range(15)])
            for mode in ('exact','reusable'):
                for c in scene[mode]['components']:
                    self.assertRegex(c['gridAddress'],r'^[A-N](?:[1-9]|1[0-4])\.[a-c][1-3]$')
                    self.assertIsInstance(c['x'],int);self.assertIsInstance(c['y'],int)

    def test_prior_art_preservation(self):
        for path,digest in json.loads((OUT/'baseline.json').read_text()).items():self.assertEqual(sha(ROOT/path),digest,path)

    def test_payload_hashes_and_closure(self):
        members=json.loads((OUT/'package-manifest.json').read_text())['members'];expected={m['file']:m for m in members}
        actual={str(p.relative_to(OUT)) for p in OUT.rglob('*') if p.is_file() and not archive(p)}
        self.assertEqual(actual,set(expected)|{'package-manifest.json'})
        for path,entry in expected.items():
            target=OUT/path;self.assertEqual(target.stat().st_size,entry['bytes']);self.assertEqual(sha(target),entry['sha256'])
        for name in ('README.md','coverage.json','schema.json'):self.assertEqual((OUT/name).read_bytes(),(ROOT/'Docs/TopDownLayerKit'/name).read_bytes())
        self.assertEqual((OUT/'viewer.html').read_bytes(),(ROOT/'Web/wwwroot/top-down-layers.html').read_bytes())
        html=(OUT/'viewer.html').read_text();embedded=json.loads(re.search(r'<script id="scene-data" type="application/json">(.*?)</script>',html,re.S).group(1))
        self.assertEqual(embedded,self.manifest)


if __name__=='__main__':unittest.main()
