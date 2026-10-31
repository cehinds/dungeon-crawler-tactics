#!/usr/bin/env python3
"""Build an offline, evidence-labeled exploration reference and inferred prop kit."""
import hashlib, json, shutil, zipfile
from pathlib import Path
from PIL import Image, ImageDraw
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'Web/wwwroot/assets/exploration-components'
SPEC=ROOT/'Docs/ExplorationComponents/spec.json'
def digest(im):
    im=im.convert('RGBA'); return hashlib.sha256(str(im.size).encode()+im.tobytes()).hexdigest()
def savejson(p,v): p.write_text(json.dumps(v,indent=2)+'\n')
def sheet(items,path,title):
    w=1000; cellw=200; cellh=200; out=Image.new('RGB',(w,48+((len(items)+4)//5)*cellh),'#142431'); d=ImageDraw.Draw(out); d.text((15,15),title,fill='white')
    for n,(label,im) in enumerate(items):
        x=(n%5)*cellw;y=48+(n//5)*cellh; im=im.copy();im.thumbnail((180,160));out.paste(im,(x+(200-im.width)//2,y),im if im.mode=='RGBA' else None);d.text((x+8,y+166),label[:29],fill='white')
    out.save(path)
def refresh_package():
    for origin,name in [(Path(__file__),'build-script.py'),(SPEC,'spec.json'),(ROOT/'Tools/test_exploration_components.py','test_exploration_components.py'),(ROOT/'Docs/ExplorationComponents/QA.md','QA.md'),(ROOT/'Docs/ExplorationComponents/README.md','GUIDE.md')]:
        if origin.exists():shutil.copyfile(origin,OUT/name)
    members={p.relative_to(OUT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in sorted(OUT.rglob('*')) if p.is_file() and p.suffix!='.zip' and p.name!='package-hashes.json'};savejson(OUT/'package-hashes.json',{'schemaVersion':1,'algorithm':'sha256','members':[{'file':name,'bytes':(OUT/name).stat().st_size,'sha256':value} for name,value in members.items()]})
    z=OUT/'exploration-components.zip'
    with zipfile.ZipFile(z,'w',zipfile.ZIP_DEFLATED) as archive:
        for p in sorted(OUT.rglob('*')):
            if p.is_file() and p!=z:
                info=zipfile.ZipInfo(p.relative_to(OUT).as_posix(),(2026,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644 << 16;archive.writestr(info,p.read_bytes())

def main():
    spec=json.loads(SPEC.read_text()); OUT.mkdir(parents=True,exist_ok=True)
    for generated in ['components','reference-crops','patches','dependencies','previews','masks','normalized-128']:
        if (OUT/generated).exists(): shutil.rmtree(OUT/generated)
    for folder in ['components','reference-crops','patches','dependencies','previews','sources','masks','normalized-128']:(OUT/folder).mkdir(exist_ok=True)
    source=Image.open(ROOT/spec['reference']).convert('RGBA');source.save(OUT/'sources/exploration-concept.png')
    excluded=['sources/','previews/','contact','overview','reconstructed','rebuild','diff','exploded','sheet','concepts/','reviews/','comparisons/','masks/','derived/','procedural/','atlases/','/source','source.png','original-reference','clean-map','reassembled','numbered','hud-source','hud-rebuilt']
    canonical={}; scanned=0
    for p in sorted((ROOT/'Web/wwwroot/assets').rglob('*.png')):
        rel=p.relative_to(ROOT/'Web/wwwroot/assets').as_posix()
        if rel.startswith('exploration-components/') or any(x in rel.lower() for x in excluded): continue
        try:
            im=Image.open(p).convert('RGBA');canonical.setdefault(digest(im),p);scanned+=1
        except Exception: pass
    components=[]; reused=[]; groups={}
    def register(i,cat,im,kind,bounds=None,atlas=None):
        h=digest(im); existing=canonical.get(h); folder='components' if kind=='inferred-restored-whole-object' else ('patches' if kind=='visible-clean-surface-patch' else 'reference-crops')
        path=f'{folder}/{i}.png'
        if existing:
            path='dependencies/'+i+'.png';shutil.copyfile(existing,OUT/path);reused.append({'id':i,'existingPath':existing.relative_to(ROOT).as_posix(),'pixelHash':h})
        else: im.save(OUT/path)
        obj={'id':i,'category':cat,'path':path,'size':list(im.size),'pivot':[im.width//2,im.height],'layer':10 if cat=='ui' else 3,'pixelHash':h,'deduplication':'exact-existing' if existing else 'new','provenance':{'kind':kind,'source':atlas or spec['reference'],'sourceBounds':bounds,'boundsFormat':'xywh','claim':'AI inferred complete alternate object; not exact source pixels' if kind=='inferred-restored-whole-object' else ('Exact rectangular visible reference evidence; includes surrounding context and may include occlusion' if kind=='context-containing-reference-crop' else 'Exact visible clean surface rectangle; repeat seams may remain')}}
        if existing:obj['existingPath']=existing.relative_to(ROOT).as_posix()
        obj['provenance']['originalSourceSha256']=hashlib.sha256((ROOT/(atlas or spec['reference'])).read_bytes()).hexdigest()
        obj['provenance']['sourceInPackage']='sources/'+Path(atlas or spec['reference']).name
        obj['provenance']['sourceSha256']=hashlib.sha256((OUT/obj['provenance']['sourceInPackage']).read_bytes()).hexdigest()
        if kind=='inferred-restored-whole-object':
            normal=im.copy();normal.thumbnail((112,112),Image.Resampling.NEAREST);canvas=Image.new('RGBA',(128,128));canvas.paste(normal,((128-normal.width)//2,(128-normal.height)//2));normalpath='normalized-128/'+i+'.png';canvas.save(OUT/normalpath);obj['normalized128Path']=normalpath;obj['normalized128Size']=[128,128]
        components.append(obj);groups.setdefault(cat,[]).append((i,im));return obj
    overlay=source.copy();draw=ImageDraw.Draw(overlay)
    for n,r in enumerate(spec['sourceRegions'],1):
        x,y,w,h=r['bounds']; register(r['id'],r['category'],source.crop((x,y,x+w,y+h)),r['kind'],r['bounds']);draw.rectangle((x,y,x+w,y+h),outline='#00ffff',width=2);draw.rectangle((x,y,x+25,y+15),fill='black');draw.text((x+2,y+1),str(n),fill='white');r['annotationNumber']=n
    overlay.save(OUT/'previews/numbered-source.png')
    for r in spec['cleanPatches']:
        x,y,w,h=r['bounds'];register(r['id'],'surfaces',source.crop((x,y,x+w,y+h)),'visible-clean-surface-patch',r['bounds'])
    restored=[]
    for a in spec['atlases']:
        ap=ROOT/a['path'];atlas=Image.open(ap).convert('RGBA');
        if ap.resolve()!=(OUT/'sources'/ap.name).resolve(): shutil.copyfile(ap,OUT/'sources'/ap.name)
        cw=atlas.width//a.get('columns',6);ch=atlas.height//a.get('rows',4)
        for n,entry in enumerate(a['objects']):
            x,y,cw,ch=entry.get('bounds',[n%a.get('columns',6)*cw,n//a.get('columns',6)*ch,cw,ch]);im=atlas.crop((x,y,x+cw,y+ch));box=im.getbbox()
            if not box:raise ValueError('Empty atlas cell '+entry['id'])
            im=im.crop(box);padded=Image.new('RGBA',(im.width+16,im.height+16));padded.paste(im,(8,8));ob=register(entry['id'],entry['category'],padded,'inferred-restored-whole-object',[x+box[0],y+box[1],im.width,im.height],a['path']);ob['provenance']['exportPadding']=8;ob['provenance']['softness']='Faint generated alpha halo may be truncated at reviewed source region; solid outline preserved. Export includes 8px transparent padding.';ob['provenance']['cellBounds']=[x,y,cw,ch];ob['provenance']['alphaMask']='masks/'+entry['id']+'.png';atlas.crop((x,y,x+cw,y+ch)).getchannel('A').save(OUT/ob['provenance']['alphaMask']);anchor=next((r for r in spec['sourceRegions'] if r['id']==entry.get('sourceAnchor')),None);ob['provenance']['sourceAnchor']={'id':anchor['id'],'bounds':anchor['bounds'],'boundsFormat':'xywh','relationship':'semantic reference only; generated alternate form'} if anchor else None;restored.append(ob)
    for cat,items in groups.items():sheet(items,OUT/f'previews/{cat}-contact-sheet.png',cat+' | labels correspond to manifest IDs')
    sheet([(c['id'],Image.open(OUT/c['path']).convert('RGBA')) for c in restored],OUT/'previews/exploded-components.png','Complete inferred objects | transparent individual PNGs')
    for plate in ['furniture','effects','actors','ui']:
        items=[(c['id'],Image.open(OUT/c['path']).convert('RGBA')) for c in restored if (c['category'] if c['category'] in ['effects','actors','ui'] else 'furniture')==plate]
        if items:sheet(items,OUT/f'previews/whole-{plate}-plate.png','Complete inferred '+plate+' | transparent PNGs')
    recipe={'schemaVersion':1,'canvas':[1000,760],'background':'#172733','surface':{'componentId':'corridor-floor','tileRect':[35,35,930,690]},'surfaceOverlays':[{'componentId':'stone-wall-strip','position':[35,350],'size':[390,43]},{'componentId':'stone-wall-strip','position':[640,350],'size':[345,43]}],'surfaceClaim':'Visible source material study; repeated floor is not certified seamless; partial architecture only.','placements':[],'claim':'Approximate alternate arrangement from restored independent pieces. Not a pixel reconstruction.'}
    room_counts=[0,0,0,0]
    room_for=lambda c,n:{'bedroom':0,'entry':0,'training':1,'craft':2,'forge':3,'surfaces':3,'effects':1,'actors':1,'ui':1}.get(c['category'],n//12)
    totals=[sum(room_for(c,n)==r for n,c in enumerate(restored)) for r in range(4)]
    for n,c in enumerate(restored):
        room=room_for(c,n)
        k=room_counts[room];room_counts[room]+=1
        x=65+(room%2)*480+(k%4)*110;y=55+(room//2)*380+(k//4)*min(90,280/max(1,(totals[room]+3)//4))
        recipe['placements'].append({'componentId':c['id'],'position':[x,int(y)],'maxSize':[85,int(min(75,250/max(1,(totals[room]+3)//4)))],'layer':c['layer'],'room':['Bedroom and home entry','Training room','Craft room','Forge room'][room]})
    layout={
'bed-red':(70,55,95,185),'nightstand-wood':(175,65,70,90),'bookcase-filled':(260,40,65,135),'wardrobe-wood':(335,40,70,130),'table-square-empty':(300,205,90,90),'stool-round':(315,285,45,50),'rug-red-gold':(65,115,230,180),'rug-blue-gold':(715,115,220,165),'mat-house':(435,45,130,65),'banner-house':(385,45,40,100),'banner-swords':(915,40,50,115),'torch-bracket-unlit':(50,40,35,50),'lantern-hanging':(220,55,35,55),'potted-plant':(370,285,55,70),'pot-empty':(50,610,55,65),'foliage-leafy':(50,570,60,65),'crate-closed':(55,295,60,65),'barrel-closed':(380,610,55,70),'chest-blue':(90,205,80,65),'training-dummy':(805,135,85,140),'weapon-stand-empty':(655,60,65,100),'training-swords-crossed':(730,50,60,70),'dumbbells':(675,215,65,75),'weight-rack':(860,55,70,85),'bench-alchemy-empty':(145,470,235,160),'bench-forge-empty':(755,575,210,115),'tool-rack-empty':(740,420,75,95),'furnace-unlit':(835,420,105,155),'pipe-elbow':(675,435,70,75),'pipe-vertical':(665,510,50,95),'pipe-horizontal':(730,390,190,45),'pipe-t-junction':(680,605,70,55),'toolbox-red':(910,545,60,50),'anvil':(750,625,80,55),'vise':(890,595,65,55),'blueprint-open':(205,495,80,65),'bottles-green':(155,485,45,55),'bottle-blue':(300,495,25,45),'bottle-red':(330,495,25,45),'gear':(840,600,35,35),'hammer':(290,545,35,45),'wrench':(340,550,35,45),'doorway-home':(430,35,150,135),'grate-gold':(605,285,40,60),'wall-lamp-bracket':(395,420,40,55),'fire-overlay':(870,485,35,65),'warm-glow':(825,445,135,135),'selection-cyan':(455,175,80,75),'actor-carl':(455,370,70,110),'actor-donut':(465,285,60,65),'actor-katia':(455,155,70,110),'actor-mongo':(450,505,85,95),'portrait-carl':(45,695,60,60),'portrait-donut':(115,695,60,60),'portrait-katia':(185,695,60,60),'portrait-mongo':(255,695,60,60),'icon-rest':(565,705,60,45),'icon-gear':(665,700,50,50),'icon-train':(765,700,50,50),'icon-craft':(865,700,50,50),'action-frame-normal':(545,685,90,70),'action-frame-selected':(645,685,90,70),'hp-track-empty':(335,705,180,20),'mana-track-empty':(335,735,180,20)}

    for item in recipe['placements']:
        x,y,w,h=layout[item['componentId']];item['position']=[x,y];item['maxSize']=[w,h]
        if item['componentId'] in ['rug-red-gold','rug-blue-gold','mat-house','selection-cyan','warm-glow']:item['layer']=1
        elif item['componentId'] in ['action-frame-normal','action-frame-selected']:item['layer']=8
    savejson(OUT/'room-recipe.json',recipe)
    savejson(OUT/'manifest.json',{'schemaVersion':1,'title':'Exploration components','reference':spec['reference'],'referenceSize':list(source.size),'components':components,'sourceAnnotations':spec['sourceRegions'],'deduplication':{'algorithm':'SHA256 of dimensions plus decoded RGBA bytes; equality requires identical dimensions and pixels','canonicalScanRoot':'Web/wwwroot/assets','excludedPathSubstrings':excluded+['exploration-components/'],'scannedPngCount':scanned,'reused':reused,'newCount':len(components)-len(reused)},'counts':{k:sum(c['provenance']['kind']==k for c in components) for k in ['inferred-restored-whole-object','context-containing-reference-crop','visible-clean-surface-patch']}})
    shutil.copyfile(ROOT/'Tools/build_exploration_components.py',OUT/'build-script.py')
    for evidence, name in [(SPEC,'spec.json'),(ROOT/'Tools/test_exploration_components.py','test_exploration_components.py'),(ROOT/'Docs/ExplorationComponents/QA.md','QA.md')]:
        if evidence.exists():shutil.copyfile(evidence,OUT/name)
    guide=ROOT/'Docs/ExplorationComponents/README.md'
    if guide.exists(): shutil.copyfile(guide,OUT/'GUIDE.md')
    replay='''from pathlib import Path\nimport json\nfrom PIL import Image\np=Path(__file__).resolve().parent\nm=json.loads((p/'manifest.json').read_text()); cs={c['id']:c for c in m['components']}\nr=json.loads((p/'room-recipe.json').read_text()); out=Image.new('RGBA',tuple(r['canvas']),r['background'])\ns=r['surface']; im=Image.open(p/cs[s['componentId']]['path']).convert('RGBA'); x,y,w,h=s['tileRect']\nfor yy in range(y,y+h,im.height):\n for xx in range(x,x+w,im.width):out.alpha_composite(im,(xx,yy))\nfor item in r.get('surfaceOverlays',[]):\n im=Image.open(p/cs[item['componentId']]['path']).convert('RGBA').resize(tuple(item['size']),Image.Resampling.NEAREST);out.alpha_composite(im,tuple(item['position']))\nfor item in sorted(r['placements'],key=lambda i:i['layer']):\n im=Image.open(p/cs[item['componentId']]['path']).convert('RGBA');im.thumbnail(tuple(item['maxSize']));out.alpha_composite(im,tuple(item['position']))\nout.save(p/'previews/reassembled-room.png')\n'''
    (OUT/'replay.py').write_text(replay)
    exec(compile(replay,str(OUT/'replay.py'),'exec'),{'__file__':str(OUT/'replay.py')})
    preview=Image.open(OUT/'previews/reassembled-room.png')
    for n,label in enumerate(['bedroom','training','craft','forge']):
        xx=(n%2)*500;yy=(n//2)*380;study=preview.crop((xx,yy,xx+500,yy+380));study.save(OUT/f'previews/{label}-room-study.png')
    left=source.copy();left.thumbnail((1000,760));comp=Image.new('RGB',(2000,810),'#142431');comp.paste(left,(0,40));comp.paste(preview,(1000,40));d=ImageDraw.Draw(comp);d.text((20,15),'SOURCE REFERENCE',fill='white');d.text((1020,15),'APPROXIMATE FURNISHED REASSEMBLY | partial architecture',fill='white');comp.save(OUT/'previews/source-vs-reassembled.png')
    (OUT/'README.txt').write_text('Offline exploration component pack. Read manifest.json provenance before reuse.\ncomponents/: inferred complete transparent objects. reference-crops/: contextual source evidence, NOT complete objects.\npatches/: visible source surface patches. dependencies/: exact-pixel reused existing assets.\nRun python replay.py with Pillow installed to rebuild the approximate alternate room.\nNo runtime integration. Sources and prior assets remain unchanged.\n')
    refresh_package()
    print(json.dumps({'components':len(components),'restored':len(restored),'zip':str(OUT/'exploration-components.zip')}))
if __name__=='__main__':
    import sys
    refresh_package() if '--package-only' in sys.argv else main()
