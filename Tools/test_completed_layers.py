#!/usr/bin/env python3
"""Independent complete-module integrity and replay checks (Pillow + NumPy)."""
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
BASE = ROOT / 'Web/wwwroot/assets/completed-layers'
def sha(data): return hashlib.sha256(data).hexdigest()
def rgba(path): return Image.open(path).convert('RGBA')
def same(a,b,label):
    aa,bb=np.asarray(a),np.asarray(b)
    assert aa.shape == bb.shape and np.array_equal(aa,bb), label

class CompletedLayersTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m=json.loads((BASE/'manifest.json').read_text())
        cls.assets={a['id']:a for a in cls.m['assets']}
    def compose(self, instances=None, omit=()):
        im=Image.new('RGBA',tuple(self.m['canvas']))
        for inst in sorted(instances if instances is not None else self.m['instances'],key=lambda i:i['z']):
            a=self.assets[inst['assetId']]
            if inst['category'] not in omit: im.alpha_composite(rgba(BASE/a['file']),tuple(inst['offset']))
        return im
    def test_inventory_and_provenance(self):
        self.assertEqual(self.m['canvas'],[1536,1024])
        self.assertEqual(len(self.assets),len(self.m['assets']))
        reused=0
        for a in self.assets.values():
            p=BASE/a['file']; im=rgba(p); w,h=im.size
            self.assertEqual(list(im.size),a['size']); self.assertEqual(sha(p.read_bytes()),a['sha256'])
            alpha=np.asarray(im)[:,:,3]
            self.assertTrue(alpha.any(),a['id'])
            if a['category']=='water' and not a.get('legacyIncomplete',False):
                self.assertGreater((alpha>0).mean(),.005,a['id']+' is a nearly empty effect, not a complete silhouette')
            if a.get('legacyIncomplete',False): self.assertFalse(a.get('complete',False),a['id'])
            pivot=a['pivot']['pixels']; normalized=a['pivot']['normalized']
            self.assertEqual(len(pivot),2)
            self.assertTrue(0<=pivot[0]<=w and 0<=pivot[1]<=h,a['id'])
            self.assertAlmostEqual(normalized[0],pivot[0]/w); self.assertAlmostEqual(normalized[1],pivot[1]/h)
            self.assertIsInstance(a['renderLayer'],int)
            self.assertIn('collision',a)
            for point in a['sockets'].values():
                self.assertIsInstance(point,str); self.assertTrue(point)
            self.assertEqual(set(a['sockets']),{'north','east','south','west'})
            self.assertFalse(a['alpha']['occlusionHoles'],a['id'])
            if a.get('componentRole')=='construction-region':
                self.assertFalse(a.get('countAuthoredDesign',True),'grid-derived construction pieces are not authored object designs')
                self.assertLessEqual(w,128); self.assertLessEqual(h,128)
            ref=a['provenance']; source=ROOT/ref['sourceFile']
            self.assertTrue(source.is_file(),str(source)); self.assertEqual(sha(source.read_bytes()),ref['sha256'])
            if a.get('id')=='complete-gold-exit':
                sourcealpha=np.asarray(rgba(source))[:,:,3]; ys,xs=np.where(sourcealpha>32)
                self.assertGreater(xs.min(),0); self.assertGreater(ys.min(),0)
                self.assertLess(xs.max(),sourcealpha.shape[1]-1); self.assertLess(ys.max(),sourcealpha.shape[0]-1)
            self.assertNotIn('reference-layers',ref['sourceFile'])
            self.assertNotIn('/components/',ref['sourceFile'] if 'concept-reconstruction' in ref['sourceFile'] else '')
            self.assertNotIn(ref['kind'],('original-visible','context-restoration','exact-cutout'))
            if ref['kind']=='existing-authored-module': reused+=1
        self.assertEqual(reused,144,'144 reused authored modules must be accounted separately')
        sourcebase=ROOT/'Web/wwwroot/assets/map-grid-pass'
        original=json.loads((sourcebase/'manifest.json').read_text())
        full={c['id']:c for c in original['components'] if c.get('parentId')=='generated-full-components' or c.get('countedAuthoredDesign') is True}
        imported={a['id']:a for a in self.assets.values() if a['provenance']['kind']=='existing-authored-module'}
        self.assertEqual(set(imported),set(full),'reused144 ancestry must exclude52 derived visible fragments')
        for ident,a in imported.items():
            self.assertEqual(a['provenance']['sourceFile'],str((sourcebase/full[ident]['path']).relative_to(ROOT)))
    def test_independent_asset_recipe_replay(self):
        recipe=json.loads((BASE/'recipe.json').read_text())
        self.assertEqual(recipe['instances'],self.m['instances'])
        self.assertEqual(len({i['z'] for i in self.m['instances']}),len(self.m['instances']))
        for i in self.m['instances']:
            self.assertIn(i['assetId'],self.assets)
            self.assertIn(i['category'],{l['id'] for l in self.m['layers']})
            self.assertTrue(all(isinstance(v,int) for v in i['offset']))
        same(self.compose(),rgba(BASE/'composition-demo.png'),'asset-only recipe replay')
        for layer in self.m['layers']:
            instances=[i for i in self.m['instances'] if i['category']==layer['id']]
            same(self.compose(instances),rgba(BASE/layer['file']),layer['id']+' independent plate')
    def test_underlying_surface_coverage(self):
        layers={l['id']:l for l in self.m['layers']}
        ground=next((v for k,v in layers.items() if k in ('ground','floor','floors')),None)
        self.assertIsNotNone(ground,'continuous ground plate required')
        self.assertTrue((np.asarray(rgba(BASE/ground['file']))[:,:,3]==255).all(),'floor has occlusion holes')
        water=layers['water']; alpha=np.asarray(rgba(BASE/water['file']))[:,:,3]
        coverage=self.m['coverage']['water']
        if isinstance(coverage,dict) and 'rects' in coverage:
            regions=coverage['rects']
        elif isinstance(coverage,list) and len(coverage)==4 and isinstance(coverage[0],int):
            regions=[coverage]
        else:
            regions=coverage
        for x,y,w,h in regions:
            if isinstance(coverage,dict) and coverage.get('coordinateFormat')=='xyxy': w,h=w-x,h-y
            self.assertTrue((alpha[y:y+h,x:x+w]==255).all(),'water has actor/prop holes')
        architecture=np.asarray(rgba(BASE/layers['architecture']['file']))
        if self.m.get('counts',{}).get('constructionRegions',0):
            self.assertEqual(int(architecture[145,100,3]),0,'old baked pipe cap remains beneath movable pipe')
            self.assertFalse(architecture[140:153,86:115,3].any(),'old pipe cap source remnant')
        # Move every instance independently and remove dynamic layers: exposed ground remains complete.
        shifted=[dict(i,offset=[i['offset'][0]+37,i['offset'][1]-23]) for i in self.m['instances'] if i['category'] not in ('ground','floor','floors','water')]
        foundation=[i for i in self.m['instances'] if i['category'] in ('ground','floor','floors','water')]
        self.assertTrue((np.asarray(self.compose(foundation+shifted))[:,:,3]==255).all())
    def test_openraster_asset_replay(self):
        with zipfile.ZipFile(BASE/'completed-layers.ora') as z:
            self.assertEqual(z.read('mimetype'),b'image/openraster')
            tree=ET.fromstring(z.read('stack.xml')); self.assertEqual([int(tree.attrib[k]) for k in ('w','h')],self.m['canvas'])
            im=Image.new('RGBA',tuple(self.m['canvas'])); nodes=list(tree.iter('layer'))
            ordered=sorted(self.m['instances'],key=lambda i:i['z'])
            self.assertEqual(len(nodes),len(ordered))
            parents={child:parent for parent in tree.iter() for child in parent}
            for node,instance in zip(reversed(nodes),ordered):
                asset=self.assets[instance['assetId']]
                self.assertEqual(node.attrib['src'],asset['file'])
                self.assertEqual(z.read(node.attrib['src']),(BASE/asset['file']).read_bytes())
                self.assertEqual(node.attrib.get('visibility','visible'),'visible')
                offset=[int(node.attrib.get(k,0)) for k in ('x','y')]
                self.assertEqual(offset,instance['offset'])
                self.assertEqual(parents[node].attrib.get('name'),instance['category'])
                im.alpha_composite(rgba(io.BytesIO(z.read(node.attrib['src']))),tuple(offset))
            same(im,self.compose(),'ORA independent replay')
            same(im,rgba(io.BytesIO(z.read('mergedimage.png'))),'ORA merged image')
    def test_zip_members(self):
        with zipfile.ZipFile(BASE/'completed-layers.zip') as z:
            names=z.namelist(); self.assertEqual(len(names),len(set(names)))
            inventory=json.loads((BASE/'package-manifest.json').read_text())['members']
            self.assertEqual(set(names),{e['file'] for e in inventory}|{'package-manifest.json'})
            for e in inventory:
                n=e['file']; p=PurePosixPath(n); self.assertFalse(p.is_absolute() or '..' in p.parts or '\\' in n)
                data=z.read(n); self.assertEqual(data,(BASE/n).read_bytes()); self.assertEqual(sha(data),e['sha256']); self.assertEqual(len(data),e['bytes'])
    def test_prior_packs_preserved(self):
        baseline=Path('/tmp/completed-layers-prior-hashes.json')
        if not baseline.exists(): self.skipTest('session-only baseline unavailable')
        for p,d in json.loads(baseline.read_text()).items(): self.assertEqual(sha((ROOT/p).read_bytes()),d,p)
if __name__=='__main__': unittest.main(verbosity=2)
