#!/usr/bin/env python3
"""Deterministically package complete independent modules and compose a reference-inspired room."""
import argparse, hashlib, io, json, shutil, zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
from PIL import Image, ImageDraw
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'Web/wwwroot/assets/completed-layers'
CATEGORIES=['ground','background-masonry','water','architecture','pipes','machinery','props','world-overlay','hud']
def sha(p):return hashlib.sha256(p.read_bytes()).hexdigest()
def writej(p,v):p.parent.mkdir(parents=True,exist_ok=True);p.write_text(json.dumps(v,indent=2)+'\n')
def save(im,p):p.parent.mkdir(parents=True,exist_ok=True);im.save(p)
def member(z,n,data,compression=zipfile.ZIP_DEFLATED):
 i=zipfile.ZipInfo(str(n),(2026,1,1,0,0,0));i.compress_type=compression;i.external_attr=0o100644<<16;z.writestr(i,data)
def compose(s,base):
 im=Image.new('RGBA',tuple(s['canvas']))
 for inst in sorted(s['instances'],key=lambda i:i['z']):
  a=next(a for a in s['assets'] if a['id']==inst['assetId']);im.alpha_composite(Image.open(base/a['file']).convert('RGBA'),tuple(inst['offset']))
 return im

def build():
 OUT.mkdir(parents=True,exist_ok=True)
 for folder in ['components','native','layers','comparisons','studies']:
  if (OUT/folder).exists():shutil.rmtree(OUT/folder)
 for pattern in ['architecture-region-*.png','complete-gold-exit.png','reference-water-*.png','reference-object-*.png']:
  for oldfile in (OUT/'sources').glob(pattern):oldfile.unlink()
 specpath=ROOT/'Docs/CompletedLayers/spec.json';spec=json.loads(specpath.read_text()) if specpath.exists() else {}
 sourcebase=ROOT/'Web/wwwroot/assets/map-grid-pass';old=json.loads((sourcebase/'manifest.json').read_text());hudbase=ROOT/'Web/wwwroot/assets/hud-reusable';hud=json.loads((hudbase/'manifest.json').read_text())
 s={'schemaVersion':1,'canvas':[1536,1024],'coordinateSystem':'native pixels, top-left origin','purpose':'Independent complete components; reference-inspired modular room, not pixel-identical replay.','assets':[],'instances':[],'layers':[],'categories':CATEGORIES,'excluded':'52 derived visible fragments and all exact-view context restorations','coverage':{'ground':[0,0,1536,1024],'water':[0,640,1536,128]},'studies':[]}
 def ingest(identifier,src,cat,meta=None):
  im=Image.open(src).convert('RGBA');p=OUT/'components'/f'{identifier}.png';save(im,p);m=meta or {};alpha=im.getchannel('A')
  a={'id':identifier,'file':str(p.relative_to(OUT)),'category':cat,'size':list(im.size),'pivot':{'pixels':[im.width/2,im.height],'normalized':[.5,1],'kind':'bottom-center'},'collision':{'type':'none' if cat in ['ground','water','world-overlay','hud','background-masonry'] else 'box','bounds':[0,0,*im.size],'purpose':'illustrative placement footprint; validate gameplay collision separately'},'renderLayer':CATEGORIES.index(cat)*100,'sockets':m.get('ports',{k:('stone-surface' if cat=='ground' else 'unconstrained') for k in ['north','east','south','west']}),'alpha':{'intentionalTransparency':alpha.getextrema()[0]<255,'occlusionHoles':False,'meaning':'exterior silhouette and designed openings only; no source-occluder cutouts','reviewStatus':'authored module imported; inferred hidden surfaces, not recovered source pixels'},'provenance':{'kind':'inferred-authored-complete-module','sourceFile':str(src.relative_to(ROOT)),'sha256':sha(src),'sourceId':m.get('sourceId'),'sourceRects':m.get('sourceRects',[])},'sha256':sha(p),'complete':True,'fullComponent':True}
  s['assets'].append(a);return a
 def cat(c):
  t=c['semanticType'];f=c.get('family','')
  if f=='water':return 'water' if t in ['floor','splash','waterfall'] else 'architecture'
  if t=='floor':return 'ground'
  if f=='walls' or t.startswith('wall') or t in ['bank','outlet']:return 'architecture'
  if t in ['water']:return 'water'
  if t in ['pipe','pipe-support','cable']:return 'pipes'
  if 'overlay' in t or t in ['moss','foliage','flame']:return 'world-overlay'
  if f=='industrial' or t in ['machinery','grate']:return 'machinery'
  return 'props'
 modules=[c for c in old['components'] if c.get('parentId')=='generated-full-components' or c.get('countedAuthoredDesign') is True]
 assert len(modules)==144,len(modules)
 for c in modules:
  a=ingest(c['id'],sourcebase/c['path'],cat(c),c);a['provenance']['kind']='existing-authored-module';a['provenance']['sourceManifest']='Web/wwwroot/assets/map-grid-pass/manifest.json'
 for group in hud['groups']:
  if not group.get('blankFile'):continue
  a=ingest('hud-blank-'+group['id'],hudbase/group['blankFile'],'hud');a['referenceOffset']=group['blankBounds'][:2];a['provenance']['kind']='inferred-clean-framed-hud';a['hudRole']='blank-framed-control'
 for c in hud['assets']:
  if c.get('role')=='clean-background':
   a=ingest('hud-'+c['id'],hudbase/c['file'],'hud');a['referenceOffset']=c['offset'];a['provenance']['kind']='inferred-clean-hud-background'
 # Optional genuinely generated new full objects are ingested from reviewed crops; no source scene cutouts.
 for item in spec.get('extraAssets',[]):
  src=ROOT/item['file'];im=Image.open(src).convert('RGBA')
  if item.get('crop'):im=im.crop(tuple(item['crop']))
  native=im.copy();nativepath=OUT/'native'/f"{item['id']}.png";save(native,nativepath)
  if item.get('size'):im=im.resize(tuple(item['size']),Image.Resampling.LANCZOS)
  temp=OUT/'sources'/f"{item['id']}.png";save(im,temp);a=ingest(item['id'],temp,item['category']);a['provenance'].update({'sourceFile':item['file'],'sha256':sha(src),'kind':'inferred-imagegen-completed-object','crop':item.get('crop'),'resizedTo':item.get('size'),'note':item.get('note')});a['nativeFile']=str(nativepath.relative_to(OUT));a['nativeSize']=list(native.size);a['nativeSha256']=sha(nativepath)
 def place(aid,x,y,category=None):
  a=next(a for a in s['assets'] if a['id']==aid);g=category or a['category'];s['instances'].append({'assetId':aid,'offset':[x,y],'category':g,'z':CATEGORIES.index(g)*10000+len(s['instances'])})
 # Every floor pixel survives removal of props, walls, HUD or water.
 for y in range(0,1024,128):
  for x in range(0,1536,128):place(('floors-fine' if (x//128+3*(y//128))%17==0 else 'floor-dry'),x,y)
 # Continuous back masonry is opaque material assembled from floor stone, deliberately behind silhouettes.
 for y in range(0,256,128):
  for x in range(0,1536,128):place('floors-coarse',x,y,'background-masonry')
 for x in range(0,1536,128):place('water-calm',x,640,'water')
 for x in range(0,1536,128):place('walls-plain',x,128);place('walls-lowparapet',x,768)
 for y in [256,384,512]:
  for x in [0,1408]:place('walls-pillarshaft',x,y)
 # Interior partitions have intentional 128-pixel passage gaps, and complete segments.
 for x in [256,384,512,896,1024,1152]:place('walls-damp',x,384)
 for x,y in [(128,192),(256,192),(1024,192),(1152,192)]:place('industrial-pipeH',x,y)
 for x,y in [(128,320),(1152,320)]:place('industrial-pipeV',x,y)
 for aid,x,y in [('industrial-consoleemptysocket',128,448),('industrial-redbuttons',1152,448),('props-gears',1024,448),('props-crateclosed',384,512),('props-cratestack',896,512),('props-redbarrel',1280,512),('props-amberlight',384,256),('props-cyanlight',1024,512)]:place(aid,x,y)
 for a in s['assets']:
  if a['category']=='hud' and a.get('hudRole')=='blank-framed-control':place(a['id'],*a['referenceOffset'])
 # Preserve the secondary modular room before rebuilding at reference footprints.
 secondary=compose(s,OUT);save(secondary,OUT/'modular-room-demo.png')
 if spec.get('referenceArchitecture'):
  archspec=spec['referenceArchitecture'];archpath=ROOT/archspec['file'];arch=Image.open(archpath).convert('RGBA')
  assert arch.size==(1536,1024),arch.size
  if archspec.get('solidAlphaThreshold') is not None:
   threshold=archspec['solidAlphaThreshold'];arch.putalpha(arch.getchannel('A').point(lambda a:255 if a>=threshold else a))
  for box in archspec.get('excludeRects',[]):arch.paste((0,0,0,0),tuple(box))
  s['instances']=[i for i in s['instances'] if i['category'] in ['ground','hud']]
  for y in range(0,256,128):
   for x in range(0,1536,128):place('floors-coarse',x,y,'background-masonry')
  def native_asset(identifier,im,category,offset,kind,source):
   p=OUT/'sources'/f'{identifier}.png';save(im,p);a=ingest(identifier,p,category);a['provenance'].update({'kind':kind,'sourceFile':str(source.relative_to(ROOT)),'sha256':sha(source)});a['countedAuthoredDesign']=False;a['countAuthoredDesign']=False;place(identifier,*offset);return a
  # Whole exit arch is one object. Remaining128 regions are construction surfaces, not falsely counted whole objects.
  for j,b in enumerate(archspec.get('wholeObjects',[])):
   box=b['bounds'];im=arch.crop(tuple(box));objectsource=archpath;objectoffset=box[:2]
   if b.get('replacementFile'):
    objectsource=ROOT/b['replacementFile'];im=Image.open(objectsource).convert('RGBA');im=im.crop(tuple(b['replacementCrop'])) if b.get('replacementCrop') else im.crop(im.getbbox());nativeexit=im.copy();nativeexitpath=OUT/'native'/f"{b.get('id','complete-exit-'+str(j))}.png";save(nativeexit,nativeexitpath);scale=min((box[2]-box[0]-8)/im.width,(box[3]-box[1]-8)/im.height);im=im.resize((round(im.width*scale),round(im.height*scale)),Image.Resampling.LANCZOS);objectoffset=[box[0]+(box[2]-box[0]-im.width)//2,box[1]+4]
   a=native_asset(b.get('id','complete-exit-'+str(j)),im,'architecture',objectoffset,'inferred-completed-architecture-object',objectsource);a['intentionalOpenings']=b.get('intentionalOpenings','doorway opening');a['sourceAlignedBounds']=box
   if b.get('replacementFile'):a['nativeFile']=str(nativeexitpath.relative_to(OUT));a['nativeSize']=list(nativeexit.size);a['nativeSha256']=sha(nativeexitpath);a['provenance']['sourceCrop']=b.get('replacementCrop')
   a['provenance']['replacementOfSourceClippedObject']=bool(b.get('replacementFile'));arch.paste((0,0,0,0),tuple(box))
  for y in range(0,1024,128):
   for x in range(0,1536,128):
    im=arch.crop((x,y,x+128,y+128))
    if im.getbbox():
     a=native_asset(f'architecture-region-{x//128:02}-{y//128:02}',im,'architecture',[x,y],'inferred-completed-construction-region',archpath);a['componentRole']='construction-region';a['intentionalOpenings']='floor/canal exterior; grid-boundary truncation is a construction join, not object occlusion';a['sockets']={k:'construction-continuation' for k in ['north','east','south','west']}
  # Water fills full reference channel footprints, independent of foreground occluders.
  for j,b in enumerate(spec.get('referenceWater',[[69,188,311,358],[174,358,281,502],[1214,173,1313,435],[1295,522,1378,655]])):
   x0,y0,x1,y1=b;im=Image.new('RGBA',(x1-x0,y1-y0));tile=Image.open(OUT/'components/water-calm.png').convert('RGBA')
   for yy in range(0,im.height,128):
    for xx in range(0,im.width,128):im.paste(tile,(xx,yy))
   native_asset('reference-water-'+str(j),im,'water',[x0,y0],'inferred-continuous-material-coverage',sourcebase/'expansion/components/water/water-calm.png')
  # Reusable full objects scaled as whole silhouettes to native source anchors, never copied source masks.
  defaults=[('industrial-pipeV',[351,0,50,200]),('industrial-pipeV',[422,0,42,179]),('industrial-pipeV',[582,0,40,171]),('industrial-pipeV',[619,0,45,181]),('industrial-pipeV',[82,137,35,132]),('industrial-pipeV',[282,410,35,156]),('industrial-pipeV',[272,576,38,100]),('industrial-pipeV',[1490,279,40,215]),('industrial-pipeH',[1360,492,88,34]),('industrial-pipeH',[1234,715,181,35]),('industrial-consoleemptysocket',[435,65,135,125]),('industrial-redbuttons',[765,15,38,161]),('props-cratestack',[79,314,82,97]),('props-cratestack',[1363,253,73,101]),('props-crateclosed',[1363,433,68,61]),('props-crateclosed',[554,687,42,76]),('props-redbarrel',[971,549,67,96])]
  for j,(aid,b) in enumerate(spec.get('referenceObjects',defaults)):
   src=OUT/'components'/f'{aid}.png';im=Image.open(src).convert('RGBA');im=im.crop(im.getbbox())
   if aid in ['industrial-pipeV','industrial-pipeH']:
    vertical=aid.endswith('V');scale=(b[2]/im.width if vertical else b[3]/im.height);tile=im.resize((round(im.width*scale),round(im.height*scale)),Image.Resampling.LANCZOS);im=Image.new('RGBA',tuple(b[2:]));length=b[3] if vertical else b[2];step=tile.height if vertical else tile.width;n=max(1,(length+step-1)//step)
    for k in range(n):
     pos=round(k*max(0,length-step)/max(1,n-1));im.alpha_composite(tile,(0,pos) if vertical else (pos,0))
   else:
    scale=min(b[2]/im.width,b[3]/im.height);im=im.resize((round(im.width*scale),round(im.height*scale)),Image.Resampling.LANCZOS)
   nativeoffset=[b[0]+(b[2]-im.width)//2,b[1]+b[3]-im.height];category=next(a['category'] for a in s['assets'] if a['id']==aid);a=native_asset('reference-object-'+str(j),im,category,nativeoffset,'inferred-complete-object-at-reference-anchor',src);a['provenance']['parentAssetId']=aid;a['provenance']['assembly']='aspect-preserved complete pipe modules repeated along native run' if aid in ['industrial-pipeV','industrial-pipeH'] else 'aspect-preserved full silhouette fit to source anchor bounds'
  s['coverage']['water']={'rects':spec.get('referenceWater',[[69,188,311,358],[174,358,281,502],[1214,173,1313,435],[1295,522,1378,655]]),'coordinateFormat':'xyxy'}
  s['referenceAligned']=True;s['architectureSource']={'file':archspec['file'],'sha256':sha(archpath),'alphaNormalization':{'solidThreshold':archspec.get('solidAlphaThreshold'),'operation':'alpha>=threshold becomes255; lowalpha edge samples retained'},'excludedBakedPipeRects':archspec.get('excludeRects',[]),'wholeObjectBounds':archspec.get('wholeObjects',[]),'semantics':'Completed generated architecture segmented into complete construction regions and whole exit object; no visible scene fallback.'}

 for inst in spec.get('extraInstances',[]):place(inst['assetId'],*inst['offset'])
 for study in spec.get('studies',[]):
  p=ROOT/study['file']
  if p.exists():
   dest=OUT/'studies'/p.name;dest.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(p,dest);s['studies'].append({**study,'file':str(dest.relative_to(OUT)),'countedComponent':False,'usedInComposition':False,'sha256':sha(dest)})
 for idx,g in enumerate(CATEGORIES):
  scene={**s,'instances':[i for i in s['instances'] if i['category']==g]};im=compose(scene,OUT);p=OUT/'layers'/f'{g}.png';save(im,p);s['layers'].append({'id':g,'file':str(p.relative_to(OUT)),'z':idx,'offset':[0,0],'componentCount':len(scene['instances'])})
 s['counts']={'reusedAuthoredMapModules':144,'cleanHudBackgrounds':16,'constructionRegions':sum(a.get('componentRole')=='construction-region' for a in s['assets']),'framedHudControls':16,'newOverlayDesigns':len(spec.get('extraAssets',[])),'generatedArchitectureWholeObjects':len(spec.get('referenceArchitecture',{}).get('wholeObjects',[])),'nativeReferenceObjectVariants':17 if spec.get('referenceArchitecture') else 0,'continuousWaterRegions':len(spec.get('referenceWater',[])) if spec.get('referenceArchitecture') else 0,'additionalNativeAssets':len(s['assets'])-176,'totalAssets':len(s['assets']),'placements':len(s['instances'])}
 demo=compose(s,OUT);save(demo,OUT/'composition-demo.png');save(demo,OUT/'reference-aligned-scene.png');writej(OUT/'manifest.json',s);writej(OUT/'recipe.json',s)
 # Annotated evidence views compare the old actual semantic layers with this complete modular interpretation.
 prior=ROOT/'Web/wwwroot/assets/reference-layers';oldscene=json.loads((prior/'scene.json').read_text())
 contact=Image.new('RGB',(1152,3*290),'#202630');d=ImageDraw.Draw(contact)
 for idx,g in enumerate(CATEGORIES):
  after=Image.open(OUT/'layers'/f'{g}.png').convert('RGBA');before=Image.new('RGBA',(1536,1024))
  mapping={'background-masonry':'underpainting','world-overlay':'world-effects','hud':'hud'}
  for l in oldscene['layers']:
   if l['group']==mapping.get(g,g):before.alpha_composite(Image.open(prior/l['file']).convert('RGBA'),tuple(l['offset']))
  board=Image.new('RGB',(768,290),'#202630');bd=ImageDraw.Draw(board);bd.text((8,6),f'{g}: BEFORE visible fragments / AFTER complete modules',fill='white')
  for j,im in enumerate([before,after]):im.thumbnail((384,256));board.paste(im,(j*384,28),im)
  save(board,OUT/'comparisons'/f'{g}.png');thumb=after.copy();thumb.thumbnail((384,256));x=idx%3*384;y=idx//3*290;contact.paste(thumb,(x,y+26),thumb);d.text((x+8,y+7),g,fill='white')
 save(contact,OUT/'exploded-complete-layers.png')
 xml=ET.Element('image',w='1536',h='1024',name='Complete modular room',version='0.0.3');stack=ET.SubElement(xml,'stack')
 with zipfile.ZipFile(OUT/'completed-layers.ora','w') as z:
  member(z,'mimetype',b'image/openraster',zipfile.ZIP_STORED)
  written=set()
  for g in reversed(CATEGORIES):
   group=ET.SubElement(stack,'stack',name=g,opacity='1.0',visibility='visible',isolation='auto',**{'composite-op':'svg:src-over'})
   for inst in reversed(sorted([i for i in s['instances'] if i['category']==g],key=lambda i:i['z'])):
    a=next(a for a in s['assets'] if a['id']==inst['assetId']);ET.SubElement(group,'layer',name=inst['assetId'],src=a['file'],x=str(inst['offset'][0]),y=str(inst['offset'][1]),opacity='1.0',visibility='visible',**{'composite-op':'svg:src-over'})
    if a['file'] not in written:member(z,a['file'],(OUT/a['file']).read_bytes());written.add(a['file'])
  member(z,'stack.xml',ET.tostring(xml));member(z,'mergedimage.png',(OUT/'composition-demo.png').read_bytes())
 readme='''# Completed layers\n\n144 complete authored map modules and clean HUD backgrounds, plus optional generated repairs. No prior fragments or contextual restorations are included. Original hidden pixels cannot be recovered: surfaces are inferred.\n\nThe main demo follows the reference architecture footprint and source object anchors. Completed architecture is generated inference, split into native construction regions plus the whole gold exit, and assembled only from independent components. Regions are construction surfaces and are not counted as new authored objects. A secondary modular-room-demo demonstrates free reuse. Architecture has designed floor/canal openings. Ground remains fully covered behind all objects. Opaque stone alpha is normalized from generated high-alpha material; designed openings stay transparent. The original generated source is archived and never drawn directly by the recipe.\n\n`manifest.json` records pivots, collision footprints, four-side sockets, alpha intent and provenance. `recipe.json` lists every placement. `layers/` contains nine category plates. The ORA contains 255 editable component instances grouped into nine categories with automatic/pass-through isolation; exact recipe replay is independently checked. `comparisons/` compare old visible-fragment layers against new modular category plates; they are not pixel-match claims.\n\nRebuild from repository: `python3 Tools/build_completed_layers.py`. Replay this portable package: `python3 reassemble.py --recipe recipe.json --output replay.png` (requires Pillow).\n'''
 (OUT/'README.md').write_text(readme);shutil.copyfile(__file__,OUT/'reassemble.py')
 for src in [ROOT/'Tools/test_completed_layers.py',ROOT/'Docs/CompletedLayers/spec.json',ROOT/'Docs/CompletedLayers/QA.md']:
  if src.exists():shutil.copyfile(src,OUT/src.name)
 guide=ROOT/'Docs/CompletedLayers/README.md'
 if guide.exists():shutil.copyfile(guide,OUT/'GUIDE.md')
 writej(OUT/'package-manifest.json',{'schemaVersion':1,'members':[{'file':str(p.relative_to(OUT)),'sha256':sha(p),'bytes':p.stat().st_size} for p in sorted(OUT.rglob('*')) if p.is_file() and p.name not in ['completed-layers.zip','package-manifest.json']]})
 with zipfile.ZipFile(OUT/'completed-layers.zip','w') as z:
  for p in sorted(OUT.rglob('*')):
   if p.is_file() and p.name!='completed-layers.zip':member(z,p.relative_to(OUT),p.read_bytes())
 print(json.dumps({'assets':len(s['assets']),'instances':len(s['instances']),'layers':len(s['layers'])}))
if __name__=='__main__':
 p=argparse.ArgumentParser();p.add_argument('--recipe',type=Path);p.add_argument('--output',type=Path);a=p.parse_args()
 if a.recipe:save(compose(json.loads(a.recipe.read_text()),a.recipe.parent),a.output or a.recipe.parent/'replayed.png')
 else:build()
