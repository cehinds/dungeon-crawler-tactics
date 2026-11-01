#!/usr/bin/env python3
"""Native RGBA preservation, structural alpha, conservative placement and history checks."""
import hashlib
import json
import unittest
from pathlib import Path
from PIL import Image

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'Web/wwwroot/assets/top-down-object-kit'


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


class ObjectTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.manifest=json.loads((OUT/'manifest.json').read_text());cls.objects={o['id']:o for o in cls.manifest['objects']};cls.sources={s['id']:s for s in cls.manifest['sources']}

    def test_46_whole_object_provenance_and_native_rgba(self):
        self.assertEqual(len(self.objects),46)
        for obj in self.objects.values():
            self.assertEqual(obj['provenance']['kind'],'ai-generated-whole-object')
            self.assertEqual(obj['manualQa']['status'],'root-approved-whole-shape-review')
            source=Image.open(OUT/self.sources[obj['sourceId']]['path']).convert('RGBA');x,y,w,h=obj['sourceRect'];expected=source.crop((x,y,x+w,y+h));actual=Image.open(OUT/obj['asset']['path']).convert('RGBA')
            self.assertEqual(actual.size,(w+4,h+4));self.assertEqual(actual.crop((2,2,w+2,h+2)).tobytes(),expected.tobytes(),obj['id'])
            self.assertEqual(sha(OUT/obj['asset']['path']),obj['asset']['sha256'])

    def test_actual_alpha_and_meaningful_clip_bounds(self):
        for obj in self.objects.values():
            im=Image.open(OUT/obj['asset']['path']).convert('RGBA');alpha=im.getchannel('A');self.assertEqual(alpha.getpixel((0,0)),0);self.assertEqual(alpha.getpixel((im.width-1,im.height-1)),0)
            self.assertGreaterEqual(alpha.getextrema()[1],200)
            self.assertLessEqual(obj['alphaQa']['sourceEdgeAlphaMax'],16)
            self.assertGreaterEqual(obj['alphaQa']['alphaAtMost16Fraction'],.03)
            # Actual zero alpha and thresholded effective coverage are distinct reported metrics.
            self.assertLessEqual(obj['alphaQa']['fullyTransparentFraction'],obj['alphaQa']['alphaAtMost16Fraction'])
            self.assertIsNotNone(alpha.getbbox())

    def test_mapping_scope_orientation_and_uniform_scale(self):
        mappings=self.manifest['mappings'];self.assertEqual(len(mappings),125);self.assertEqual(len({m['id'] for m in mappings}),125)
        self.assertEqual(len(self.manifest['excludedMappings']),2)
        for mapping in mappings:
            self.assertEqual(mapping['fit'],'contain-uniform');self.assertEqual(mapping['status'],'planned-placement-demonstrated');self.assertIn(mapping['objectId'],self.objects)
            p=mapping['placement'];self.assertIn(p['rotationDegrees'],[0,90,180,270]);obj=self.objects[mapping['objectId']];w,h=obj['asset']['size']
            if p['rotationDegrees']%180:w,h=h,w
            self.assertEqual(p['renderSize'],[max(1,round(w*p['uniformScale'])),max(1,round(h*p['uniformScale']))])
            for previous in mapping['previousComponents']:self.assertTrue((OUT/previous['asset']['path']).exists())
            if 'rug' in obj['id'] or 'carpet' in obj['id']:self.assertEqual(mapping['z'],-1000)
            if mapping['sceneId']=='swine-switch-chamber':self.assertNotIn(mapping['objectId'],['cd-rail-junction','cd-rail-straight'])
            if mapping['sceneId']=='real-mordecai-guild' and mapping['objectId']=='ab-clean-shelf-wood-empty' and mapping['targetBounds'][2]<mapping['targetBounds'][3]:self.assertEqual(p['rotationDegrees'],90)
            if mapping['sceneId']=='human-bathroom-portal' and mapping['objectId']=='ef-toilet':self.assertEqual(p['rotationDegrees'],180)

    def test_scene_coverage_is_explicitly_partial(self):
        scenes=self.manifest['sceneCoverage'];self.assertEqual(len(scenes),36);self.assertEqual(sum(s['mappings']>0 for s in scenes),26);self.assertEqual(sum(s['mappings']==0 for s in scenes),10)
        self.assertEqual(sum(s['unmappedComponents'] for s in scenes),412)
        for scene in scenes:
            self.assertNotIn('complete',scene['status'])
            self.assertEqual(scene['mappings'],sum(m['sceneId']==scene['id'] for m in self.manifest['mappings']))
            if scene['mappings']:self.assertTrue((OUT/scene['demonstration']['path']).exists())

    def test_all_prior_assets_preserved(self):
        for path,digest in json.loads((OUT/'baseline.json').read_text()).items():self.assertEqual(sha(ROOT/path),digest,path)


if __name__=='__main__':unittest.main()
