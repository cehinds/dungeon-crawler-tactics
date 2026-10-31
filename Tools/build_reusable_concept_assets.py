#!/usr/bin/env python3
"""Build explicitly derived reusable modules; literal source pack stays untouched."""
import json, random, math, hashlib, argparse
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'Web/wwwroot/assets/concept-reconstruction'
OUT=BASE/'derived'
SPEC=ROOT/'Docs/ConceptReconstruction/reusable-asset-spec.json'

def main():
 s=json.loads(SPEC.read_text()); OUT.mkdir(exist_ok=True); (OUT/'door-sealed.png').unlink(missing_ok=True); assets=[]; images={}; rng=random.Random(s['texture']['seed'])
 def save(id,im,kind,anchor=None,edges=None,ids=None,source=False,**extra):
  im.save(OUT/(id+'.png'));images[id]=im
  assets.append(dict(id=id,file=id+'.png',width=im.width,height=im.height,size=[im.width,im.height],anchor=anchor or [im.width//2,im.height],edgeTags=edges or {},kind=kind,provenance={'kind':'visible-source-assembly' if source else ('source-material-derived' if ids or extra.get('sourceBounds') else 'procedurally-synthesized-reference-palette'),'hiddenPixels':'absent' if source else 'explicit synthesis; not recovered source pixels'},sourceComponentIds=ids or [],**extra))
 def textured(size,base,light,seed):
  r=random.Random(seed); im=Image.new('RGBA',size,tuple(base)+(255,));d=ImageDraw.Draw(im)
  for _ in range(int(size[0]*size[1]*.17)):
   x=r.randrange(size[0]);y=r.randrange(size[1]); t=r.uniform(-.35,.45);c=tuple(max(0,min(255,int(a+(b-a)*t))) for a,b in zip(base,light))
   d.line((x,y,x+r.randrange(1,4),y),fill=c)
  return im
 T=s['texture']; mortar=tuple(T['mortar'])+(255,)
 for i in range(s['floor']['variants']):
  # Normalize six distinct reviewed clean source stone materials, without any floor/UI/actor partition holes.
  source_spec=s['floor']['sourceTextures'][i];source_manifest=json.loads((BASE/'manifest.json').read_text())
  source_layer=next(x for x in source_manifest['layers'] if x['id']==source_spec['componentId'])
  material=Image.open(BASE/source_layer['file']).convert('RGBA').crop(tuple(source_spec['localBounds']))
  assert material.getchannel('A').getextrema()==(255,255), 'Floor material contains partition holes'
  material=material.resize((62,62),Image.Resampling.NEAREST)
  im=Image.new('RGBA',(64,64),(46,63,77,255));im.alpha_composite(material,(1,1));d=ImageDraw.Draw(im)
  d.line((1,1,62,1),fill=(74,91,105));d.line((1,2,1,62),fill=(68,85,99))
  save('floor-stone-'+chr(97+i),im,'floor',ids=[source_spec['componentId']],edges=dict.fromkeys(['north','east','south','west'],'stone-mortar-v1'),material='distinct reviewed clean source stone interior at native62px; explicit 1px common mortar and subtle 1px bevel')
 def masonry(size,seed=2):
  im=textured(size,T['wallBase'],T['wallLight'],seed)
  mm=json.loads((BASE/'manifest.json').read_text());by={x['id']:x for x in mm['layers']}
  materials=[Image.open(BASE/by[id]['file']).convert('RGBA').resize((33,17),Image.Resampling.NEAREST) for id in s['walls']['sourceMaterialIds']]
  for row,y in enumerate(range(0,size[1],20)):
   for col,x in enumerate(range(-18 if row%2 else 0,size[0],36)):
    tile=materials[(row+col)%len(materials)];im.alpha_composite(tile,(x+2,y+2))
  d=ImageDraw.Draw(im)
  for y in range(0,size[1],20):
   d.line((0,y,size[0],y),fill=mortar,width=3)
   for x in range(-18 if y//20%2 else 0,size[0],36):
    d.line((x,y,x,y+20),fill=mortar,width=3);d.line((x+3,y+3,x+32,y+3),fill=(63,87,101))
  return im
 for name,size in [('face',(64,64)),('cap',(64,18)),('pier',(24,80)),('corner-inner',(64,64)),('corner-outer',(64,64))]:
  im=masonry(size);d=ImageDraw.Draw(im)
  if name.startswith('corner'):
   mask=Image.new('L',size);md=ImageDraw.Draw(mask);w=s['walls']['cornerWidth'];md.rectangle((0,0,63,w),fill=255);md.rectangle((0,0,w,63),fill=255)
   if name=='corner-inner': mask=mask.transpose(Image.Transpose.FLIP_LEFT_RIGHT)
   im.putalpha(mask)
  if name=='cap':
   source_image=Image.open(ROOT/'Web/wwwroot/assets/broadcast-kit/combat-concept.png').convert('RGBA')
   cap=source_image.crop(tuple(s['walls']['capSourceBounds']))
   im=Image.new('RGBA',size)
   im.alpha_composite(cap,(0,0))
  save('wall-'+name,im,'wall',ids=s['walls']['sourceMaterialIds'],sourceBounds=s['walls']['capSourceBounds'] if name=='cap' else None,material='source blue stone material normalized into explicitly synthesized modular masonry geometry')
 for direction in ['w','e']:
  im=images['wall-cap'].copy();dd=ImageDraw.Draw(im);xx=0 if direction=='w' else 61
  dd.line((xx,2,xx,17),fill=(24,41,56),width=2)
  save('wall-cap-end-'+direction,im,'wall',sourceBounds=s['walls']['capSourceBounds'])
 for direction,angle in [('nw',0),('ne',270),('se',180),('sw',90)]:
  im=Image.new('RGBA',(64,64));im.alpha_composite(images['wall-cap'],(0,0));im.alpha_composite(images['wall-cap'].rotate(90,expand=True),(0,0))
  save('wall-cap-corner-'+direction,im.rotate(angle),'wall',orientation=direction,sourceBounds=s['walls']['capSourceBounds'])
 for base in ['wall-corner-inner','wall-corner-outer']:
  for direction,angle in [('nw',0),('ne',270),('se',180),('sw',90)]:
   save(base+'-'+direction,images[base].rotate(angle), 'wall',ids=s['walls']['sourceMaterialIds'],orientation=direction)
 source_image=Image.open(ROOT/'Web/wwwroot/assets/broadcast-kit/combat-concept.png').convert('RGBA')
 wm=json.loads((BASE/'manifest.json').read_text());water_layers=[x for x in wm['layers'] if x['category']=='water-channel' and x.get('file')]
 water_canvas=Image.new('RGBA',(1536,1024))
 for layer in water_layers:water_canvas.alpha_composite(Image.open(BASE/layer['file']).convert('RGBA'),tuple(layer['offset']))
 water_ids=[x['id'] for x in water_layers]
 source_waters=[water_canvas.crop(tuple(bounds)) for bounds in s['water']['sourceVariants']]
 for material in source_waters:assert material.getchannel('A').getextrema()==(255,255),'Water source contains foreign/absent pixels'
 # Build one source-textured periodic master. Opposing edge profiles average corresponding
 # source pixels, retain their nonconstant foam/blue detail, and share matched corners.
 master=source_waters[2].copy();mp=master.load()
 for y in range(64):
  for d in range(7):
   left=mp[d,y];right=mp[63-d,y];weight=(7-d)/7
   avg=tuple((left[k]+right[k])/2 for k in range(3))
   mp[d,y]=tuple(round(left[k]*(1-weight)+avg[k]*weight) for k in range(3))+(255,)
   mp[63-d,y]=tuple(round(right[k]*(1-weight)+avg[k]*weight) for k in range(3))+(255,)
 for x in range(64):
  for d in range(7):
   top=mp[x,d];bottom=mp[x,63-d];weight=(7-d)/7
   avg=tuple((top[k]+bottom[k])/2 for k in range(3))
   mp[x,d]=tuple(round(top[k]*(1-weight)+avg[k]*weight) for k in range(3))+(255,)
   mp[x,63-d]=tuple(round(bottom[k]*(1-weight)+avg[k]*weight) for k in range(3))+(255,)
 waters=[]
 for index,bounds in enumerate(s['water']['sourceVariants']):
  water=source_waters[index].copy();px=water.load()
  for y in range(64):
   for x in range(64):
    distance=min(x,y,63-x,63-y)
    weight=max(0,min(1,(13-distance)/7))
    original=px[x,y];common=mp[x,y]
    px[x,y]=tuple(round(original[k]*(1-weight)+common[k]*weight) for k in range(3))+(255,)
  id='water-surface' if index==0 else 'water-surface-'+chr(97+index)
  save(id,water,'water',ids=water_ids,material='distinct source water material with explicit shared source-textured periodic master and 7px interior blend',sourceBounds=bounds,edges=dict.fromkeys(['north','east','south','west'],'water-v2'))
  waters.append(water)
 water=waters[0]
 for name,sides in [('bank-n','n'),('bank-e','e'),('bank-s','s'),('bank-w','w'),('corner-ne','ne'),('corner-nw','nw'),('corner-se','se'),('corner-sw','sw'),('end','new'),('outlet','n')]:
  im=water.copy();bank=masonry((64,64));mask=Image.new('L',(64,64));d=ImageDraw.Draw(mask);w=s['water']['bankWidth']
  for side in sides:
   d.rectangle({'n':(0,0,63,w-1),'s':(0,64-w,63,63),'w':(0,0,w-1,63),'e':(64-w,0,63,63)}[side],fill=255)
  im.paste(bank,(0,0),mask)
  if name=='outlet':
   d=ImageDraw.Draw(im);d.rounded_rectangle((21,0,43,24),radius=7,fill=(7,22,31),outline=(100,122,128),width=3);d.line((29,11,29,40),fill=(80,220,245),width=3);d.line((35,14,35,43),fill=(167,247,255),width=2)
  save('water-'+name,im,'water',ids=s['water']['sourceMaterialIds']+s['walls']['sourceMaterialIds'],material='source water and stone textures with explicitly synthesized bank/outlet geometry')
  for variant_index in [1,2]:
   variant=waters[variant_index].copy();variant.paste(bank,(0,0),mask)
   if name=='outlet':
    vd=ImageDraw.Draw(variant);vd.rounded_rectangle((21,0,43,24),radius=7,fill=(7,22,31),outline=(100,122,128),width=3);vd.line((29,11,29,40),fill=(80,220,245),width=3);vd.line((35,14,35,43),fill=(167,247,255),width=2)
   save('water-'+name+'-'+chr(97+variant_index),variant,'water',ids=water_ids+s['walls']['sourceMaterialIds'],sourceBounds=s['water']['sourceVariants'][variant_index],material='source material variant with common periodic edge and authored bank')
 for name,color in s['effects'].items():
  if not isinstance(color,list):continue
  im=Image.new('RGBA',(256,256));d=ImageDraw.Draw(im)
  for width,alpha in [(22,12),(14,25),(8,60),(4,240)]:d.rounded_rectangle((9,9,246,246),radius=8,outline=tuple(color)+(alpha,),width=width)
  im=im.resize((64,64),Image.Resampling.LANCZOS);save('effect-'+name,im,'cell-effect',anchor=[32,64])
 # Source composition uses every recursively linked child exactly once.
 m=json.loads((BASE/'manifest.json').read_text()); layers=m['layers'];byid={x['id']:x for x in layers}
 def assembly(ids):
  chosen=set(ids)
  while True:
   more={x['id'] for x in layers if x.get('parentId') in chosen and x['category'] not in s['assemblies']['excludedCategories']}
   if more<=chosen:break
   chosen|=more
  entries=[x for x in layers if x['id'] in chosen and x.get('file')]
  if not entries:return None,[]
  x0=min(x['offset'][0] for x in entries);y0=min(x['offset'][1] for x in entries);x1=max(x['offset'][0]+x['size'][0] for x in entries);y1=max(x['offset'][1]+x['size'][1] for x in entries)
  im=Image.new('RGBA',(x1-x0,y1-y0))
  for x in sorted(entries,key=lambda a:a.get('z',0)):
   im.alpha_composite(Image.open(BASE/x['file']).convert('RGBA'),(x['offset'][0]-x0,x['offset'][1]-y0))
  return im,[x['id'] for x in entries]
 for x in layers:
  if x['category']=='actor-body':
   im,ids=assembly([x['id']]);actor=x['id'].removesuffix('-body');fraction=s['assemblies']['actorFootAnchorFractions'][actor]
   save('actor-'+actor,im,'actor',anchor=[round(im.width*fraction[0]),round(im.height*fraction[1])],ids=ids,source=True,footprint=[1,1],nativeScale=1.0,assemblyPolicy='body partition plus all recursive non-world-UI children',sourceMatteNote='Minor detached black edge pixels around Mongo remain ambiguous visible source matte' if actor=='mongo' else None)
 for cat in ['crate','prop','grate']:
  for x in layers:
   if x['category']==cat and x.get('file'):
    im,ids=assembly([x['id']]);save('prop-'+x['id'],im,'prop-visible-assembly',ids=ids,source=True,completeness='visible source silhouette; occlusion remains absent')
 im,ids=assembly([x['id'] for x in layers if x['category']=='exit-architecture' or x['id']=='exit-direction-arrow'])
 # The one-pixel threshold joint was partitioned into masonry, not architecture.
 # Restore this visible source strip explicitly; no unseen pixel synthesis.
 portal_joint_bounds=[963,138,1066,139]
 im.alpha_composite(Image.open(ROOT/'Web/wwwroot/assets/broadcast-kit/combat-concept.png').convert('RGBA').crop(tuple(portal_joint_bounds)),(65,138))
 assert im.crop((67,34,166,196)).getchannel('A').getextrema()==(255,255),'Portal visible interior has partition holes'
 save('portal-exit-source-assembly',im,'entrance',ids=ids,source=True,supplementalSourceRegions=[{'bounds':portal_joint_bounds,'reason':'visible threshold joint assigned to source masonry partition'}])
 # Distinct entrances retain assembled source masonry and native texture density.
 portal=im.copy();portal_ids=ids[:]
 for name,state in [('portal-dormant','dormant-blue-portal'),('entrance-open','active-cyan-portal')]:
  variant=portal.copy();px=variant.load()
  for yy in range(variant.height):
   for xx in range(variant.width):
    r,g,b,a=px[xx,yy]
    if a and r>g*1.12 and r>b*1.35:
     if name=='portal-dormant':px[xx,yy]=(int(r*.42),int(g*.68),min(255,int(r*.83)),a)
     else:px[xx,yy]=(int(r*.50),min(255,int(g*1.18)),min(255,int(r*.90)),a)
  if name=='entrance-open':
   arrow_layer=byid['exit-direction-arrow'];arch_layers=[byid[id] for id in portal_ids]
   origin_x=min(layer['offset'][0] for layer in arch_layers);origin_y=min(layer['offset'][1] for layer in arch_layers)
   ax=arrow_layer['offset'][0]-origin_x;ay=arrow_layer['offset'][1]-origin_y;aw,ah=arrow_layer['size']
   arrow=variant.crop((ax,ay,ax+aw,ay+ah));source_arrow=Image.open(BASE/arrow_layer['file']).convert('RGBA');arrow.putalpha(source_arrow.getchannel('A'));arrow=arrow.rotate(180)
   vd=ImageDraw.Draw(variant);vd.rectangle((ax,ay,ax+aw-1,ay+ah-1),fill=(27,37,39,255))
   for gx in range(ax,ax+aw,8):vd.line((gx,ay,gx,ay+ah-1),fill=(72,101,102),width=1)
   for gy in range(ay,ay+ah,8):vd.line((ax,gy,ax+aw-1,gy),fill=(72,101,102),width=1)
   variant.alpha_composite(arrow,(ax,ay))
  save(name,variant,'entrance',ids=portal_ids,supplementalSourceRegions=[{'bounds':portal_joint_bounds,'reason':'visible threshold joint assigned to source masonry partition'}],state=state,footprint=[2,1],material='assembled literal source frame/stairs; explicit derived gold-to-blue hue state; cyan entry arrow rotated180 over explicitly synthesized grille backing',completeness='source visible architecture union; source occlusions remain absent')
 ui=[x['id'] for x in layers if x['category'].startswith('ui-') or x['category']=='text']
 im=Image.new('RGBA',(1536,1024));ids=[]
 for x in sorted(layers,key=lambda a:a.get('z',0)):
  if x['id'] in ui and x.get('file') and (x['offset'][1] < 115 or x['offset'][1] >= 740):
   im.alpha_composite(Image.open(BASE/x['file']).convert('RGBA'),tuple(x['offset']));ids.append(x['id'])
 save('hud-fixed-source-state',im,'hud',ids=ids,source=True,fixedState=s['fixedHudState'],anchor=[0,0])
 for name,source_id in [('crate','west-crate-upper'),('barrel','explosive-barrel'),('grate','west-floor-grate')]:
  im,ids=assembly([source_id])
  save('prop-complete-'+name,im,'prop',ids=ids,source=True,footprint=[1,1],completeness='complete visible source object silhouette; no hidden rear faces inferred')
 roles=dict(floor=['floor-stone-'+c for c in 'abcdef'],wallFace='wall-face',wallCap='wall-cap',wallCorner='wall-corner-outer',pier='wall-pier',water='water-surface',bank='water-bank-w',bankEast='water-bank-e',bankWest='water-bank-w',waterEnd='water-end',entrance='entrance-open',exit='portal-exit-source-assembly',hud='hud-fixed-source-state')
 roles['waterVariants']=['water-surface','water-surface-b','water-surface-c']
 roles['bankEastVariants']=['water-bank-e','water-bank-e-b','water-bank-e-c'];roles['bankWestVariants']=['water-bank-w','water-bank-w-b','water-bank-w-c']
 roles.update(waterEndVariants=['water-end','water-end-b','water-end-c'],waterOutletVariants=['water-outlet','water-outlet-b','water-outlet-c'],wallCapEndWest='wall-cap-end-w',wallCapEndEast='wall-cap-end-e',wallCornerNW='wall-cap-corner-nw',wallCornerNE='wall-cap-corner-ne',wallCornerSE='wall-cap-corner-se',wallCornerSW='wall-cap-corner-sw')
 for asset in assets:
  id=asset['id']
  if asset['kind']=='wall':asset['edgeTags']=dict.fromkeys(['north','east','south','west'],'masonry')
  elif id.startswith('water-bank-w'):
   asset['edgeTags']=dict(north='bank-w',south='bank-w',west='stone-mortar-v1',east='water-v2')
  elif id.startswith('water-bank-e'):
   asset['edgeTags']=dict(north='bank-e',south='bank-e',east='stone-mortar-v1',west='water-v2')
  elif id.startswith('water-'):asset['edgeTags']=dict.fromkeys(['north','east','south','west'],'water-v2')
 catalog=dict(waterVisualLimit=s['water']['visualLimit'],waterVariants=roles['waterVariants'],roles=roles,schemaVersion=1,tileSize=64,canvas=[1536,1024],assets=assets,fixedHudState=s['fixedHudState'],spec=str(SPEC.relative_to(ROOT)))
 (OUT/'catalog.json').write_text(json.dumps(catalog,indent=2)+'\n')
 # Verifiable previews generated from catalog assets rather than the reference background.
 def floorgrid(w,h):
  im=Image.new('RGBA',(64*w,64*h))
  for y in range(h):
   for x in range(w):im.alpha_composite(images['floor-stone-'+chr(97+random.Random(x+y*971+183).randrange(6))],(x*64,y*64))
  return im
 floorgrid(6,6).save(OUT/'preview-floor-adjacency.png')
 im=floorgrid(8,6)
 for x in range(8):im.alpha_composite(images['wall-face'],(x*64,0));im.alpha_composite(images['wall-cap'],(x*64,0))
 for y in range(1,6):
  for x,name in [(0,'bank-w'),(1,'surface'),(2,'bank-e')]:im.alpha_composite((waters[(x+y)%len(waters)] if name=='surface' else images['water-'+name+('' if y%3==0 else '-'+chr(97+y%3))]),(x*64,y*64))
 im.save(OUT/'preview-perimeter-water.png')
 water_preview=Image.new('RGBA',(384,384))
 for y in range(6):
  for x in range(6):water_preview.alpha_composite(waters[random.Random(x+y*971+721).randrange(3)],(x*64,y*64))
 water_preview.save(OUT/'preview-water-adjacency.png')
 im=floorgrid(6,2)
 for y in range(2):
  for x,col in enumerate(['cyan','yellow','red']):im.alpha_composite(images['effect-'+col],(x*128,y*64))
 im.save(OUT/'preview-effects.png')
 actors=[a for a in assets if a['kind']=='actor'];im=Image.new('RGBA',(sum(a['width']+20 for a in actors),180),(22,32,42,255));xx=10
 for a in actors:im.alpha_composite(images[a['id']],(xx,150-a['height']));xx+=a['width']+20
 im.save(OUT/'preview-actor-lineup.png')
 cellw,cellh=200,210;sheet=Image.new('RGB',(cellw*6,cellh*math.ceil(len(assets)/6)),(24,31,40));d=ImageDraw.Draw(sheet)
 for i,a in enumerate(assets):
  x=i%6*cellw;y=i//6*cellh;thumb=images[a['id']].copy();thumb.thumbnail((180,175));sheet.paste(thumb,(x+10,y+5),thumb);d.text((x+5,y+183),a['id'][:30],fill='white')
 sheet.save(OUT/'contact-sheet.png')
 floors=[images['floor-stone-'+c] for c in 'abcdef'];edge=lambda im,box:im.crop(box).tobytes();tests={}
 for n,box in [('north',(0,0,64,1)),('south',(0,63,64,64)),('west',(0,0,1,64)),('east',(63,0,64,64))]:tests[n]=all(edge(f,box)==edge(floors[0],box) for f in floors)
 tests['waterEdgesIdentical']=all(edge(f,box)==edge(waters[0],box) for f in waters for box in [(0,0,64,1),(0,63,64,64),(0,0,1,64),(63,0,64,64)])
 tests['opaqueWater']=all(f.getchannel('A').getextrema()==(255,255) for f in waters)
 tests['opaqueFloors']=all(f.getchannel('A').getextrema()==(255,255) for f in floors);tests['allFloorVariantEdgesIdentical']=all(tests.values())
 (OUT/'validation.json').write_text(json.dumps(tests,indent=2)+'\n');assert all(tests.values()),tests
 print('Built',len(assets),'assets; seam validation passed')
if __name__=='__main__':
 parser=argparse.ArgumentParser(description=__doc__)
 parser.add_argument('--asset-root',type=Path,default=BASE)
 parser.add_argument('--out',type=Path,default=OUT)
 parser.add_argument('--spec',type=Path,default=SPEC)
 args=parser.parse_args();BASE=args.asset_root;OUT=args.out;SPEC=args.spec
 main()
