"""Validate gallery exports and declared metadata; does not validate map solving."""
import hashlib
import json
from pathlib import Path
import unittest

import jsonschema
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
ART = ROOT / 'Web/wwwroot/assets/broadcast-kit'


class BroadcastArtTests(unittest.TestCase):
    def test_manifest_exports(self):
        manifest = json.loads((ART / 'manifest.json').read_text())
        schema = json.loads((ROOT / 'Docs/BroadcastArt/manifest.schema.json').read_text())
        jsonschema.validate(manifest, schema)
        self.assertEqual(manifest['sourceComponentCount'], 48)
        self.assertEqual(manifest['derivedStructuralCount'], 13)
        self.assertEqual(len(manifest['assets']), 61)
        self.assertEqual(sum('derivation' not in a for a in manifest['assets']),48)
        self.assertEqual(len({a['id'] for a in manifest['assets']}), len(manifest['assets']))
        for asset in manifest['assets']:
            with self.subTest(asset=asset['id']):
                relative = Path(asset['src'])
                self.assertFalse(relative.is_absolute())
                self.assertNotIn('..', relative.parts)
                path = ART / relative
                self.assertEqual(path.stem, asset['id'])
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), asset['sha256'])
                with Image.open(path) as image:
                    self.assertEqual(image.size, (128, 128))
                    self.assertEqual(image.mode, 'RGBA')
                    self.assertEqual(list(image.getchannel('A').getextrema()), asset['alphaExtrema'])
                    self.assertEqual(list(image.getbbox()), asset['contentBounds'])
                    if asset['layer']=='terrain':self.assertEqual(image.getchannel('A').getextrema(),(255,255))
                    if asset['layer'] in ('prop','overlay') and asset['adjacency']!='road-network-study':
                        self.assertEqual(image.getchannel('A').getextrema()[0],0)
                        left,top,right,bottom=image.getbbox()
                        self.assertLessEqual(right-left,112)
                        self.assertLessEqual(bottom-top,112)
                self.assertEqual(set(asset['edges']), {'N', 'E', 'S', 'W'})
                self.assertTrue(all(isinstance(tag, str) and tag for tag in asset['edges'].values()))
                source_path = 'combat-source.png' if 'derivation' in asset else asset['source']
                with Image.open(ART / source_path) as source:
                    x1, y1, x2, y2 = asset['sourceCrop']
                    self.assertTrue(0 <= x1 < x2 <= source.width and 0 <= y1 < y2 <= source.height)


    def test_derived_wall_edge_bands(self):
        manifest=json.loads((ART/'manifest.json').read_text())
        derived=[asset for asset in manifest['assets'] if 'derivation' in asset]
        self.assertEqual(len(derived),13)
        for asset in derived:
            with self.subTest(asset=asset['id']), Image.open(ART/asset['src']) as image:
                alpha=image.getchannel('A')
                for edge,tag in asset['edges'].items():
                    if tag!='stone-wall':continue
                    values={'N':[alpha.getpixel((i,0)) for i in range(128)],
                            'S':[alpha.getpixel((i,127)) for i in range(128)],
                            'W':[alpha.getpixel((0,i)) for i in range(128)],
                            'E':[alpha.getpixel((127,i)) for i in range(128)]}[edge]
                    self.assertEqual([i for i,v in enumerate(values) if v>=200],list(range(32,96)))


if __name__ == '__main__':
    unittest.main()
