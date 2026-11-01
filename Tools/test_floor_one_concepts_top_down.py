#!/usr/bin/env python3
"""Verify packaging; recorded camera review is not automated visual correctness."""
import hashlib
import json
import unittest
import zipfile
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'Web/wwwroot/assets/floor-one-concepts-top-down'


def sha(data):return hashlib.sha256(data).hexdigest()


class ConceptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=json.loads((OUT/'manifest.json').read_text())
        cls.coverage=json.loads((OUT/'coverage.json').read_text())
        cls.sources={s['id']:s for s in cls.manifest['sources']}

    def test_exact_native_crops(self):
        for p in self.manifest['panels']:
            source=Image.open(OUT/self.sources[p['sourceId']]['path']).convert('RGBA')
            x,y,w,h=p['sourceRect'];expected=source.crop((x,y,x+w,y+h))
            actual=Image.open(OUT/p['path']).convert('RGBA')
            self.assertEqual(expected.size,actual.size)
            self.assertEqual(expected.tobytes(),actual.tobytes(),p['id'])
            self.assertEqual(sha(actual.tobytes()),p['pixelSha256'])
            self.assertEqual([w,h],p['nativeSize'])

    def test_coverage_and_unique_panels(self):
        panels=self.manifest['panels'];catalog={p['id']:p for p in self.coverage['panels']}
        self.assertEqual(len(panels),36);self.assertEqual({p['id'] for p in panels},set(catalog))
        self.assertEqual(len({p['pixelSha256'] for p in panels}),36)
        refs={s['id'] for s in self.manifest['references']}
        for p in panels:
            for key in catalog[p['id']]:self.assertEqual(p[key],catalog[p['id']][key])
            self.assertTrue(set(p['sourceIds'])<=refs)
            self.assertEqual(p['layout'],'inferred')
        self.assertEqual(self.manifest['scope']['floor'],1)
        self.assertEqual(self.manifest['scope']['book'],1)

    def test_whole_panel_separation(self):
        for source in self.sources.values():
            self.assertEqual(source['cameraReview']['projection'],'direct-overhead')
            self.assertEqual(source['cameraReview']['reviewer'],'root')
            self.assertTrue(source['cameraReview']['assessment'])
            im=Image.open(OUT/source['path']);self.assertEqual(list(im.size),source['canvasSize'])
            rgb=im.convert('RGB')
            for axis,positions in source['dividerLines'].items():
                for position in positions:
                    pixels=[rgb.getpixel((position,j) if axis=='vertical' else (j,position)) for j in range(rgb.height if axis=='vertical' else rgb.width)]
                    limits=source['dividerDarkMaxRGB']
                    dark=sum(r<limits[0] and g<limits[1] and b<limits[2] for r,g,b in pixels)/len(pixels)
                    self.assertGreaterEqual(dark,0.99,'Divider crosses visible scene content')
            panels=sorted([p for p in self.manifest['panels'] if p['sourceId']==source['id']],key=lambda p:p['order'])
            self.assertEqual(len(panels),6)
            for i,p in enumerate(panels):
                x,y,w,h=p['sourceRect'];self.assertGreater(w,0);self.assertGreater(h,0)
                self.assertGreaterEqual(x,0);self.assertGreaterEqual(y,0);self.assertLessEqual(x+w,im.width);self.assertLessEqual(y+h,im.height)
                self.assertTrue(p['boundaryReview'])
                for other in panels[i+1:]:
                    a,b,c,d=other['sourceRect'];self.assertFalse(max(x,a)<min(x+w,a+c) and max(y,b)<min(y+h,b+d))
            for row in range(2):
                group=panels[row*3:row*3+3]
                self.assertTrue(all(group[i]['sourceRect'][0]+group[i]['sourceRect'][2]<=group[i+1]['sourceRect'][0] for i in range(2)))
            self.assertLessEqual(max(p['sourceRect'][1]+p['sourceRect'][3] for p in panels[:3]),min(p['sourceRect'][1] for p in panels[3:]))

    def test_all_panels_are_new_revision_pixels(self):
        original=ROOT/'Web/wwwroot/assets/floor-one-concepts/manifest.json'
        prior=json.loads(original.read_text())
        old={p['id']:p for p in prior['panels']}
        self.assertEqual(set(old),{p['id'] for p in self.manifest['panels']})
        for panel in self.manifest['panels']:
            self.assertNotEqual(panel['pixelSha256'],old[panel['id']]['pixelSha256'],panel['id'])
        self.assertFalse({s['sha256'] for s in prior['sources']} & {s['sha256'] for s in self.sources.values()})

    def test_prior_assets_preserved(self):
        for name,digest in json.loads((OUT/'baseline.json').read_text()).items():self.assertEqual(sha((ROOT/name).read_bytes()),digest,name)

    def test_output_closure_and_zip(self):
        records=json.loads((OUT/'package-manifest.json').read_text())['members'];expected={p['file']:p for p in records}
        files={str(p.relative_to(OUT)) for p in OUT.rglob('*') if p.is_file()}
        self.assertEqual(files,set(expected)|{'package-manifest.json','floor-one-concepts-top-down.zip'})
        for name in ('README.md','coverage.json','spec.json'):
            self.assertEqual((OUT/name).read_bytes(),(ROOT/'Docs/FloorOneConceptsTopDown'/name).read_bytes())
        for name in ('build_floor_one_concepts_top_down.py','test_floor_one_concepts_top_down.py'):
            self.assertEqual((OUT/'tools'/name).read_bytes(),(ROOT/'Tools'/name).read_bytes())
        with zipfile.ZipFile(OUT/'floor-one-concepts-top-down.zip') as archive:
            self.assertEqual(set(archive.namelist()),set(expected)|{'package-manifest.json'})
            for name,record in expected.items():
                data=(OUT/name).read_bytes();self.assertEqual(sha(data),record['sha256']);self.assertEqual(len(data),record['bytes']);self.assertEqual(archive.read(name),data)
            self.assertEqual(archive.read('package-manifest.json'),(OUT/'package-manifest.json').read_bytes())


if __name__=='__main__':unittest.main()
