#!/usr/bin/env python3
"""Check actual asset bytes, placement contracts, pose rectangles and external metadata."""
import argparse
import copy
import hashlib
import json
import math
import sys
from pathlib import Path
from PIL import Image
ROOT=Path(__file__).resolve().parents[1];WEB=ROOT/'Web/wwwroot'
def number(v):return isinstance(v,(int,float)) and not isinstance(v,bool) and math.isfinite(v)
def check(c,metadata=True):
 errors=[];entries=c['assets']+c['tiles']+c['characters'];ids=[a['id'] for a in entries]
 if len(ids)!=len(set(ids)):errors.append('Duplicate asset IDs')
 for a in entries:
  name=a['id'];fail=lambda message:errors.append(name+': '+message)
  if a.get('renderLayer') not in c['renderLayers']:fail('invalid layer')
  pivot=a.get('pivot');footprint=a.get('footprint')
  if a.get('placement')=='no-placement':
   if pivot is not None or footprint is not None:fail('no-placement source claims placement geometry')
  elif a['kind']!='directional-animation':
   if not isinstance(pivot,dict) or any(not number(pivot.get(k)) or not 0<=pivot[k]<=1 for k in ['x','y']):fail('invalid normalized pivot')
   if not isinstance(footprint,dict) or any(not number(footprint.get(k)) or not 0<footprint[k]<=256 for k in ['width','height']):fail('invalid footprint')
  if 'path'in a:
   p=(WEB/a['path']).resolve()
   if not p.is_relative_to(WEB.resolve()):fail('path escapes web root');continue
   if not p.is_file():fail('missing file');continue
   if not a.get('sha256') or hashlib.sha256(p.read_bytes()).hexdigest()!=a['sha256']:fail('sha256 mismatch')
   with Image.open(p) as im:
    if 'width'in a and (a['width'],a['height'])!=im.size:fail('export dimensions differ')
    if a['kind']=='directional-animation':
     if set(a.get('directions',{}))!={'se','sw','ne','nw'}:fail('requires exactly four directions')
     for direction,poses in a.get('directions',{}).items():
      if set(poses)!={'idle','walk1','walk2'}:fail(direction+' requires idle/walk1/walk2')
      for pose,f in poses.items():
       if any(not number(f.get(k)) for k in ['x','y','width','height','anchorX','anchorY']):fail('invalid frame numbers');continue
       if min(f['x'],f['y'])<0 or min(f['width'],f['height'])<=0 or f['x']+f['width']>im.width or f['y']+f['height']>im.height:fail('frame outside image')
       if not 0<=f['anchorX']<=1 or not 0<=f['anchorY']<=1:fail('frame anchor outside normalized bounds')
     if not isinstance(footprint,dict) or any(not number(footprint.get(k)) or footprint[k]<=0 for k in ['width','height']):fail('invalid actor footprint')
     if metadata and a['path'].startswith('assets/block-a/'):
      meta=p.with_suffix('.json')
      if not meta.is_file() or json.loads(meta.read_text())!=a:fail('runtime metadata differs from catalog')
  if a['kind']=='procedural-render-component':
   if set(a.get('edges',{}))!=set('NESW') or a['width']!=a['height'] or a['width']<=0:fail('invalid square connector')
   if set(a.get('edgeTags',{}))!=set('NESW'):fail('missing edge tags')
 for a in c['assemblies']:
  if isinstance(a,dict) and 'required' in a:
   for id in a['required']+a.get('optional',[]):
    if id not in ids:errors.append(a['id']+': unregistered assembly part '+id)
 for b in c['objectCatalogBindings']:
  for id in b['assetIds']:
   if id not in ids:errors.append(b['objectTypeId']+': unregistered '+id)
 if metadata:
  for f in json.loads((ROOT/'Tools/hosted-assets.json').read_text())['files']:
   p=WEB/'assets'/f['path']
   if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=f['sha256']:errors.append('hosted checksum mismatch: '+f['path'])
 return errors
def validate():
 global WEB
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--wwwroot',type=Path,default=WEB,help='Web root containing data/asset-catalog.json and restored assets (default: Web/wwwroot)')
 parser.add_argument('--self-test',action='store_true',help='Also reject intentionally corrupted catalog fixtures')
 args=parser.parse_args()
 WEB=args.wwwroot.resolve()
 c=json.loads((WEB/'data/asset-catalog.json').read_text());errors=check(c)
 if errors:raise SystemExit('\n'.join(errors))
 if args.self_test:
  mutations=[lambda d:d['characters'][0]['directions'].pop('nw'),lambda d:d['characters'][0]['directions']['se'].pop('walk2'),lambda d:d['characters'][0]['directions']['se']['idle'].update(anchorX=2),lambda d:d['assets'][0].update(sha256='0'*64),lambda d:d['tiles'][0].update(pivot={'x':-1,'y':.5}),lambda d:d['tiles'][0].update(footprint={'width':0,'height':1}),lambda d:d['characters'][-1].update(bodyHeight=-1)]
  for mutate in mutations:
   bad=copy.deepcopy(c);mutate(bad)
   if not check(bad):raise SystemExit('Negative fixture was incorrectly accepted')
  print('PASS: seven negative fixtures rejected (direction, pose, anchor, hash, pivot, footprint, metadata drift)')
 print(f"PASS: {len(c['assets'])+len(c['tiles'])+len(c['characters'])} registrations; physical checksums, placement, poses and metadata")
if __name__=='__main__':validate()
