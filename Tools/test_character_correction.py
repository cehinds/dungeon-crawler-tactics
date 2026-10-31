#!/usr/bin/env python3
"""Independent pixel, metadata, preservation and archive checks for corrected art."""
import hashlib
import json
import unittest
import zipfile
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'Web/wwwroot/assets/character-correction'


def sha(data):
    return hashlib.sha256(data).hexdigest()


class CorrectionTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=json.loads((OUT/'manifest.json').read_text())
        cls.sources={s['id']:s for s in cls.manifest['sources']}

    def test_exact_native_crops_and_transparency(self):
        for v in self.manifest['variants']:
            for asset in v['assets'].values():
                source=Image.open(OUT/self.sources[asset['sourceId']]['packagePath']).convert('RGBA')
                x,y,w,h=asset['rect'];expected=source.crop((x,y,x+w,y+h))
                actual=Image.open(OUT/asset['files']['native']['path']).convert('RGBA')
                self.assertEqual(expected.size,actual.size)
                self.assertEqual(expected.tobytes(),actual.tobytes())
                self.assertEqual(actual.getchannel('A').getextrema()[0],0)
                self.assertIsNotNone(actual.getbbox())

    def test_128_pixels_and_bounds(self):
        for v in self.manifest['variants']:
            for asset in v['assets'].values():
                native=Image.open(OUT/asset['files']['native']['path']).convert('RGBA')
                factor=min(128/native.width,128/native.height)
                resized=native.resize((max(1,round(native.width*factor)),max(1,round(native.height*factor))),Image.Resampling.NEAREST)
                expected=Image.new('RGBA',(128,128));expected.alpha_composite(resized,((128-resized.width)//2,128-resized.height))
                actual=Image.open(OUT/asset['files']['128']['path']).convert('RGBA')
                self.assertEqual(expected.tobytes(),actual.tobytes())
                self.assertEqual(list(actual.getbbox()),asset['files']['128']['alphaBounds'])

    def test_metadata_and_shared_ids(self):
        variants=self.manifest['variants'];self.assertEqual(len({v['id'] for v in variants}),len(variants))
        self.assertEqual({v['characterId'] for v in variants},{'carl','donut','katia','mongo'})
        self.assertEqual(len([v for v in variants if v.get('isMain')]),4)
        compatibility=json.loads((OUT/'compatibility.json').read_text())
        for v in variants:
            for key in ('bookStage','designChoices','sourceRefs','worldScale'):
                self.assertTrue(v[key])
            self.assertEqual(set(v['assets']),{'world','portrait'})
            for role,olds in v['supersedes'].items():
                for old in olds:self.assertIn({'variantId':v['id'],'characterId':v['characterId'],'role':role,'path':v['assets'][role]['files']['native']['path']},compatibility[old])

    def test_preserved_prior_files(self):
        for path,digest in json.loads((OUT/'baseline.json').read_text()).items():
            self.assertEqual(sha((ROOT/path).read_bytes()),digest,path)

    def test_output_closure_and_archive(self):
        inventory=json.loads((OUT/'package-manifest.json').read_text())['members']
        expected={entry['path']:entry for entry in inventory}
        files={str(p.relative_to(OUT)) for p in OUT.rglob('*') if p.is_file()}
        self.assertEqual(files,set(expected)|{'package-manifest.json','character-correction.zip'})
        with zipfile.ZipFile(OUT/'character-correction.zip') as archive:
            self.assertEqual(set(archive.namelist()),set(expected)|{'package-manifest.json'})
            for path,entry in expected.items():
                data=(OUT/path).read_bytes();self.assertEqual(sha(data),entry['sha256']);self.assertEqual(len(data),entry['bytes']);self.assertEqual(archive.read(path),data)
            self.assertEqual(archive.read('package-manifest.json'),(OUT/'package-manifest.json').read_bytes())


if __name__=='__main__':unittest.main()
