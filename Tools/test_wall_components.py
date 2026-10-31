#!/usr/bin/env python3
"""Independent wall pack asset, socket, replay and archive verification."""
import hashlib
import json
from pathlib import Path, PurePosixPath
import unittest
import zipfile
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'Web/wwwroot/assets/wall-components'
SIDES = ('north', 'east', 'south', 'west')
OPPOSITE = {'north':'south','east':'west','south':'north','west':'east'}
def sha(data): return hashlib.sha256(data).hexdigest()
def rgba(path): return Image.open(path).convert('RGBA')
def same(a,b,label):
    aa,bb=np.array(a),np.array(b)
    aa[aa[:,:,3]==0,:3]=0; bb[bb[:,:,3]==0,:3]=0
    assert aa.shape == bb.shape and np.array_equal(aa,bb),label

class WallComponentsTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.m=json.loads((BASE/'manifest.json').read_text())
        cls.assets={a['id']:a for a in cls.m['assets']}

    def test_inventory_shapes_and_layers(self):
        self.assertEqual(len(self.assets),16)
        self.assertEqual({a['mask'] for a in self.assets.values()},set(range(16)))
        for a in self.assets.values():
            self.assertEqual(sha((BASE/a['file']).read_bytes()),a['sha256'])
            self.assertEqual(a['size'][0],64); self.assertGreaterEqual(a['size'][1],64); self.assertEqual(a['pivot'],[32,32])
            expected=np.zeros((a['size'][1],64),bool); expected[16:48,16:48]=True
            for bit,side in enumerate(SIDES):
                active=bool(a['mask'] & (1<<bit))
                self.assertEqual(side in a['connections'],active)
                socket=a['sockets'][side]
                self.assertEqual(socket['tag'],a['edgeTags'][side])
                self.assertEqual(socket['capInterval'],[16,48] if active else None)
                self.assertEqual(socket['center'],{'north':[32,0],'east':[64,32],'south':[32,64],'west':[0,32]}[side])
                self.assertEqual(a['edgeTags'][side]!='empty',active)
                if active:
                    if side=='north': expected[:16,16:48]=True
                    if side=='east': expected[16:48,48:64]=True
                    if side=='south': expected[48:64,16:48]=True
                    if side=='west': expected[16:48,:16]=True
            cap=np.asarray(rgba(BASE/a['layers']['cap']))
            self.assertTrue(np.array_equal(cap[:,:,3],expected.astype('uint8')*255),a['id']+' cap topology or unintended holes')
            composed=Image.new('RGBA',tuple(a['size']))
            for name in ('shadow','face','cap'):
                layer=rgba(BASE/a['layers'][name]); self.assertEqual(layer.size,tuple(a['size']))
                composed.alpha_composite(layer)
            same(composed,rgba(BASE/a['file']),a['id']+' layer replay')

    def test_compatible_cap_edge_pixels(self):
        def edge(a,side):
            p=np.asarray(rgba(BASE/a['layers']['cap']))
            return {'north':p[0,:],'east':p[:64,-1],'south':p[63,:],'west':p[:64,0]}[side]
        for side in SIDES:
            for a in self.assets.values():
                for b in self.assets.values():
                    if a['edgeTags'][side]!='empty' and a['edgeTags'][side]==b['edgeTags'][OPPOSITE[side]]:
                        self.assertTrue(np.array_equal(edge(a,side),edge(b,OPPOSITE[side])),a['id']+' / '+b['id']+' '+side)

    def test_three_independent_room_replays_and_reciprocity(self):
        self.assertEqual(set(self.m['samples']),{'rectangle','l-shape','corridor-junction'})
        signatures=[]
        for name,path in self.m['samples'].items():
            recipe=json.loads((BASE/path).read_text()); image=Image.new('RGBA',tuple(recipe['canvas']))
            cells={tuple(i['cell']):i for i in recipe['instances'] if 'cell' in i}
            extras=[i for i in recipe['instances'] if 'cell' not in i]
            adapters={(tuple(v['cell']),side):v['tag'] for i in extras for side,v in i['adapters'].items()}
            self.assertEqual(len(cells)+len(extras),len(recipe['instances']))
            signatures.append(frozenset(cells))
            for inst in recipe['instances']:
                if 'cell' not in inst:
                    self.assertIn(inst['assetId'],{v['id'] for v in self.m['construction']})
                    image.alpha_composite(rgba(BASE/inst['file']),tuple(inst['offset']))
                    continue
                a=self.assets[inst['assetId']]; self.assertEqual(inst['file'],a['file'])
                x,y=inst['cell']; self.assertEqual(inst['offset'],[64+x*64,64+y*64])
                image.alpha_composite(rgba(BASE/a['file']),tuple(inst['offset']))
                for side,(dx,dy) in zip(SIDES,((0,-1),(1,0),(0,1),(-1,0))):
                    neighbor=cells.get((x+dx,y+dy))
                    if side in a['connections']:
                        if neighbor is None:
                            self.assertEqual(adapters.get(((x+dx,y+dy),OPPOSITE[side])),a['edgeTags'][side],name+' dangling '+side)
                        else:
                            b=self.assets[neighbor['assetId']]
                            self.assertEqual(a['edgeTags'][side],b['edgeTags'][OPPOSITE[side]])
            same(image,rgba((BASE/path).with_suffix('.png')),name+' independent JSON replay')
        self.assertEqual(len(set(signatures)),3)

    def test_construction_and_intentional_door_opening(self):
        parts={a['id']:a for a in self.m['construction']}
        self.assertEqual(len(parts),15)
        for a in parts.values():
            im=rgba(BASE/a['file']); self.assertEqual(list(im.size),a['size']); self.assertTrue(np.asarray(im)[:,:,3].any(),a['id'])
            source=a['provenance']['file']; p=BASE/source if source.startswith('parts/') else ROOT/source
            self.assertTrue(p.is_file(),source)
            self.assertEqual(sha(p.read_bytes()),a['provenance']['sha256'])
            self.assertEqual(sha((BASE/a['file']).read_bytes()),a['sha256'])
        arch=rgba(BASE/parts['doorway-arch']['file']); alpha=np.asarray(arch)[:,:,3]
        self.assertGreater((alpha>0).mean(),.25); self.assertLess((alpha>0).mean(),.8)
        self.assertTrue((alpha[62:112,50:78]==0).all(),'passage must be transparent')
        self.assertGreater((alpha[55:112,20:42]>0).mean(),.7,'west jamb missing')
        self.assertGreater((alpha[55:112,86:108]>0).mean(),.7,'east jamb missing')
        assembled=Image.new('RGBA',arch.size)
        for name in ('doorway-jamb-west','doorway-jamb-east','doorway-lintel'):
            assembled.alpha_composite(rgba(BASE/parts[name]['file']))
        same(assembled,arch,'door construction exact replay')

    def test_archive_closed_and_byte_identical(self):
        with zipfile.ZipFile(BASE/'wall-components.zip') as z:
            names=z.namelist(); self.assertEqual(len(names),len(set(names)))
            local={str(p.relative_to(BASE)) for p in BASE.rglob('*') if p.is_file() and p.suffix!='.zip'}
            self.assertEqual(set(names),local)
            inventory=json.loads((BASE/'package-manifest.json').read_text())['members']
            self.assertEqual(set(names),{e['file'] for e in inventory}|{'package-manifest.json'})
            for e in inventory:
                self.assertEqual(sha(z.read(e['file'])),e['sha256'])
                self.assertEqual(len(z.read(e['file'])),e['bytes'])
            for name in names:
                path=PurePosixPath(name); self.assertFalse(path.is_absolute() or '..' in path.parts or '\\' in name)
                self.assertEqual(z.read(name),(BASE/name).read_bytes(),name)

    def test_prior_packs_preserved(self):
        baseline=Path('/tmp/wall-components-prior-hashes.json')
        if not baseline.exists(): self.skipTest('session-only pre-build baseline unavailable')
        records=json.loads(baseline.read_text())
        self.assertGreater(len(records),2500)
        for p,d in records.items():
            self.assertEqual(sha((ROOT/p).read_bytes()),d,p)

if __name__=='__main__': unittest.main(verbosity=2)
