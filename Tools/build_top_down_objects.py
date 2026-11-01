#!/usr/bin/env python3
"""Package complete generated sprites, conservative mappings and honest placement proofs."""
import argparse
import hashlib
import json
import math
import re
import shutil
from pathlib import Path
from PIL import Image,ImageDraw,ImageFont

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'Web/wwwroot/assets/top-down-object-kit'
DOCS=ROOT/'Docs/TopDownObjectKit'
OLD=ROOT/'Web/wwwroot/assets/top-down-layer-kit'
ALPHA_THRESHOLD=16


def sha(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path,data):
    path.parent.mkdir(parents=True,exist_ok=True);path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')


def resolve(path,directory):
    p=Path(path);return p if p.is_absolute() else directory/p


def font(size):return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',size)


def background(size,style):
    colors={'light':('#ecece5','#dddcd2'),'dark':('#202631','#303948'),'floor-blue':('#43546b','#4c5e77'),'floor-sand':('#a38c68','#b29a76'),'checker':('#596574','#89929e')}
    a,b=colors[style];im=Image.new('RGBA',size,a);draw=ImageDraw.Draw(im);step=24 if style=='checker' else 32
    if style.startswith('floor') or style=='checker':
        for y in range(0,size[1],step):
            for x in range(0,size[0],step):
                if (x//step+y//step)%2:draw.rectangle((x,y,x+step-1,y+step-1),fill=b)
                if style.startswith('floor'):draw.rectangle((x,y,x+step-1,y+step-1),outline=(25,32,42,100))
    return im


def asset(image,path):
    path.parent.mkdir(parents=True,exist_ok=True);image.save(path)
    return {'path':str(path.relative_to(OUT)),'sha256':sha(path),'size':list(image.size)}


def rotated(image,degrees):
    return image.transpose({90:Image.Transpose.ROTATE_270,180:Image.Transpose.ROTATE_180,270:Image.Transpose.ROTATE_90}[degrees]) if degrees else image.copy()


def placement(obj,mapping):
    image=rotated(Image.open(OUT/obj['asset']['path']).convert('RGBA'),mapping.get('rotationDegrees',0));bounds=image.getchannel('A').point(lambda a:255 if a>ALPHA_THRESHOLD else 0).getbbox()
    x,y,w,h=mapping['targetBounds'];bw=bounds[2]-bounds[0];bh=bounds[3]-bounds[1];scale=min(w/bw,h/bh)
    pivot=obj['pivot'];px=bounds[0]+bw*pivot[0];py=bounds[1]+bh*pivot[1]
    pixels=image.resize((max(1,round(image.width*scale)),max(1,round(image.height*scale))),Image.Resampling.NEAREST)
    anchor=[x+w/2,y+h/2];position=[round(anchor[0]-px*scale),round(anchor[1]-py*scale)]
    return pixels,{'uniformScale':scale,'rotationDegrees':mapping.get('rotationDegrees',0),'renderSize':list(pixels.size),'position':position,'anchor':anchor,'sourceVisibleBoundsAfterRotation':list(bounds),'policy':'Uniform fit of meaningful visible bounds; native source pixels exported unchanged. Nearest-neighbor placement preview only.'}


def proof_sheet(objects,style,path):
    cellw,cellh=360,360;cols=4;canvas=Image.new('RGB',(cols*cellw,60+math.ceil(len(objects)/cols)*cellh),'#151c27');draw=ImageDraw.Draw(canvas);draw.text((12,12),'Whole reconstructed object library · '+style,font=font(21),fill='white')
    for i,obj in enumerate(objects):
        x=(i%cols)*cellw;y=60+(i//cols)*cellh;tile=background((cellw-12,cellh-55),style);image=Image.open(OUT/obj['asset']['path']).convert('RGBA');factor=min((tile.width-30)/image.width,(tile.height-24)/image.height);image=image.resize((max(1,round(image.width*factor)),max(1,round(image.height*factor))),Image.Resampling.NEAREST);tile.alpha_composite(image,((tile.width-image.width)//2,(tile.height-image.height)//2));canvas.paste(tile.convert('RGB'),(x+6,y));draw.text((x+8,y+cellh-47),obj['label'][:38],font=font(15),fill='white');draw.text((x+8,y+cellh-25),obj['id'][:45],font=font(11),fill='#adbed4')
    canvas.save(path)


def build(paths):
    OUT.mkdir(parents=True,exist_ok=True);baseline=OUT/'baseline.json'
    if baseline.exists():
        for p,digest in json.loads(baseline.read_text()).items():
            if sha(ROOT/p)!=digest:raise ValueError('Prior art changed '+p)
    else:write_json(baseline,{str(p.relative_to(ROOT)):sha(p) for p in sorted((ROOT/'Web/wwwroot/assets').rglob('*')) if p.is_file() and OUT not in p.parents})
    prior=json.loads((OLD/'manifest.json').read_text());scenes={s['id']:s for s in prior['scenes']};objects=[];sources=[];mappings=[];seen=set()
    for input_path in paths:
        data=json.loads(input_path.read_text());directory=input_path.parent;source_images={}
        for source in data['sources']:
            path=resolve(source['path'],directory);im=Image.open(path).convert('RGBA');target=OUT/'sources'/(source['id']+'.png');entry={**source,**asset(im,target),'originalSha256':sha(path),'originalPath':str(path)};sources.append(entry);source_images[source['id']]=im
        for obj in data['objects']:
            if obj.get('active') is False:continue
            if obj['id'] in seen:raise ValueError('Duplicate objectID')
            seen.add(obj['id']);x,y,w,h=obj['sourceRect'];source=source_images[obj['sourceId']]
            if min(x,y)<0 or min(w,h)<=0 or x+w>source.width or y+h>source.height:raise ValueError('Invalid source rect '+obj['id'])
            crop=source.crop((x,y,x+w,y+h));a=crop.getchannel('A');effective=a.point(lambda v:255 if v>ALPHA_THRESHOLD else 0).getbbox()
            if effective is None:raise ValueError('Empty object '+obj['id'])
            edges=list(a.crop((0,0,w,1)).get_flattened_data())+list(a.crop((0,h-1,w,h)).get_flattened_data())+list(a.crop((0,0,1,h)).get_flattened_data())+list(a.crop((w-1,0,w,h)).get_flattened_data())
            if max(edges)>ALPHA_THRESHOLD:raise ValueError('Meaningful silhouette touches crop edge '+obj['id'])
            transparent=a.histogram()[0]/(w*h);meaningful_transparent=sum(a.histogram()[:ALPHA_THRESHOLD+1])/(w*h)
            if meaningful_transparent<.03:raise ValueError('Insufficient transparent background '+obj['id'])
            padded=Image.new('RGBA',(w+4,h+4));padded.paste(crop,(2,2))
            record={**obj,'asset':asset(padded,OUT/'objects'/(obj['id']+'.png')),'padding':2,'rawAlphaBounds':list(a.getbbox()),'visibleBounds':[effective[0]+2,effective[1]+2,effective[2]+2,effective[3]+2],'alphaQa':{'thresholdForBoundsOnly':ALPHA_THRESHOLD,'sourceEdgeAlphaMax':max(edges),'fullyTransparentFraction':transparent,'alphaAtMost16Fraction':meaningful_transparent,'alphaRange':list(a.getextrema()),'policy':'Native RGB/alpha retained exactly; 2 transparent padding pixels added; threshold only measures meaningful bounds.'},'manualQa':{**obj.get('manualQa',{}),'status':'root-approved-whole-shape-review','limits':'Illustrative creature forms are not canonical likeness claims. Minor baked shading/low-alpha generation fringe retained; no separate shadow layer unless explicitly provided.'}}
            objects.append(record)
        mappings.extend(data.get('mappings',[]))
    by_id={o['id']:o for o in objects};normalized=[];scene_coverage=[];excluded_mappings=[]
    for index,mapping in enumerate(mappings):
        if mapping['objectId'] not in by_id:continue
        mapping=dict(mapping)
        if mapping['sceneId']=='swine-switch-chamber' and mapping['objectId'] in ('cd-rail-straight','cd-rail-junction'):
            excluded_mappings.append({**mapping,'reason':'Root rejected entire network footprint assigned to one rail/junction; no valid modular network placement supplied.'});continue
        if mapping['sceneId']=='human-bathroom-portal' and mapping['objectId']=='ef-toilet':
            mapping['rotationDegrees']=180;mapping['orientationReview']='Root correction: cistern at bottom of reference footprint.'
        obj=by_id[mapping['objectId']]
        if re.search(r'rug|carpet',obj['id']):mapping['z']=-1000;mapping['layerReview']='Complete floor textiles render beneath furniture, never over it.'
        if not mapping.get('rotationDegrees') and re.search(r'shelf|bench|cot|bed|counter|rail|wall|table|pipe',obj['id']):
            image=Image.open(OUT/obj['asset']['path']).convert('RGBA');bbox=image.getchannel('A').point(lambda a:255 if a>ALPHA_THRESHOLD else 0).getbbox();source_ratio=(bbox[2]-bbox[0])/(bbox[3]-bbox[1]);target_ratio=mapping['targetBounds'][2]/mapping['targetBounds'][3]
            if (source_ratio>1.35 and target_ratio<1/1.35) or (source_ratio<1/1.35 and target_ratio>1.35):
                mapping['rotationDegrees']=90;mapping['orientationReview']='Long fixture axis aligned to authored native target footprint; uniform scaling retained.'
        if mapping['objectId']=='cd-wall-straight' and mapping.get('replacementScope')=='partial-demo':
            x,y,w,h=mapping['targetBounds'];mapping['targetBounds']=[round(x+w/2-72),y,144,30];mapping['placementReview']='One 144x30 wall module demonstration, not an entire wall replacement.'
        scene=scenes[mapping['sceneId']];old={c['id']:c for c in scene['exact']['components']};old.update({c['id']:c for c in scene['reusable']['components']})
        if not set(mapping['replaceComponentIds'])<=set(old):raise ValueError('Unknown component mapping '+str(mapping))
        pixels,geometry=placement(by_id[mapping['objectId']],mapping);reference=[]
        for cid in mapping['replaceComponentIds']:
            component=old[cid];path=OLD/component['asset']['path'];destination=OUT/'references'/mapping['sceneId']/(cid+'.png');destination.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(path,destination);reference.append({'id':cid,'category':component['category'],'asset':{'path':str(destination.relative_to(OUT)),'sha256':sha(destination),'size':component['asset']['size']},'position':[component['x'],component['y']]})
        normalized.append({**mapping,'id':mapping['sceneId']+'--'+mapping.get('instanceId','placement-'+str(index+1).zfill(3)),'status':'planned-placement-demonstrated','replacementScope':mapping.get('replacementScope','atomic'),'placement':geometry,'previousComponents':reference})
    for scene in prior['scenes']:
        selected=[m for m in normalized if m['sceneId']==scene['id']];complete={cid for m in selected if m['replacementScope']!='partial-demo' for cid in m['replaceComponentIds']} & {c['id'] for c in scene['reusable']['components']};partial={cid for m in selected if m['replacementScope']=='partial-demo' for cid in m['replaceComponentIds']}
        record={'id':scene['id'],'name':scene['name'],'size':scene['size'],'order':scene['order'],'mappings':len(selected),'wholeObjectIds':sorted({m['objectId'] for m in selected}),'mappedAtomicOrAssemblyTargets':len(complete),'partialDemoTargets':len(partial),'previousReusableComponents':len(scene['reusable']['components']),'unmappedComponents':len({c['id'] for c in scene['reusable']['components']}-complete),'status':'partial whole-object placement demonstration' if selected else 'no whole-object placements mapped','originalUrl':'https://raw.githubusercontent.com/cehinds/AI-Art/2147653ec69329e4d01a9f56326573a6fd7cfdda/dungeon-crawler-tactics/Web/wwwroot/assets/top-down-layer-kit/'+scene['source']['path']}
        if selected:
            demo=background(tuple(scene['size']),'floor-sand')
            for item in sorted(selected,key=lambda m:(m['z'],m['id'])):
                pixels,_=placement(by_id[item['objectId']],item);demo.alpha_composite(pixels,tuple(item['placement']['position']))
            record['demonstration']=asset(demo,OUT/'placements'/(scene['id']+'.png'))
        scene_coverage.append(record)
    previews=OUT/'previews';previews.mkdir(exist_ok=True)
    for style in ('checker','light','dark','floor-blue','floor-sand'):proof_sheet(objects,style,previews/(style+'.png'))
    manifest={'schemaVersion':1,'title':'Whole reconstructed top-down objects','claim':'AI-generated whole-object library; source cutouts are comparison evidence only. Placement demonstrations use only mapped whole objects on alternate floors. Unmapped scene components are absent, not claimed restored.','sources':sources,'objects':objects,'mappings':normalized,'excludedMappings':excluded_mappings,'sceneCoverage':scene_coverage,'counts':{'objects':len(objects),'mappingInstances':len(normalized),'scenesWithPlacements':sum(s['mappings']>0 for s in scene_coverage),'unmappedScenes':sum(s['mappings']==0 for s in scene_coverage)}}
    mapped=[scene for scene in scene_coverage if scene.get('demonstration')];cols=6;cw,ch=300,340;montage=Image.new('RGB',(cols*cw,55+math.ceil(len(mapped)/cols)*ch),'#141d2a');draw=ImageDraw.Draw(montage);draw.text((12,12),'Whole-object-only scene demonstrations — unmapped elements absent',font=font(20),fill='white')
    for index,scene in enumerate(mapped):
        im=Image.open(OUT/scene['demonstration']['path']).convert('RGBA');im.thumbnail((cw-16,ch-65),Image.Resampling.NEAREST);x=index%cols*cw;y=55+index//cols*ch;montage.paste(im,(x+(cw-im.width)//2,y));draw.text((x+8,y+ch-55),str(scene['order']).zfill(2)+' '+scene['id'][:30],font=font(12),fill='white');draw.text((x+8,y+ch-32),str(scene['mappings'])+' instances / '+str(scene['unmappedComponents'])+' unmapped',font=font(12),fill='#c6d4e6')
    montage.save(previews/'scene-montage.png')
    write_json(OUT/'manifest.json',manifest)
    for name in ('README.md','coverage.json','schema.json'):
        if (DOCS/name).exists():shutil.copyfile(DOCS/name,OUT/name)
    if (DOCS/'viewer.html').exists():
        html=(DOCS/'viewer.html').read_text();html=re.sub(r'(<script id="object-data" type="application/json">).*?(</script>)',lambda m:m.group(1)+json.dumps(manifest,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')+m.group(2),html,flags=re.S);(DOCS/'viewer.html').write_text(html);shutil.copyfile(DOCS/'viewer.html',OUT/'viewer.html')
    tooling=OUT/'tools';tooling.mkdir(exist_ok=True)
    for name in ('build_top_down_objects.py','test_top_down_objects.py','package_top_down_layers.py'):
        if (ROOT/'Tools'/name).exists():shutil.copyfile(ROOT/'Tools'/name,tooling/name)
    files=[p for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='package-manifest.json' and p.suffix!='.zip' and '.zip.part-' not in p.name and not p.name.endswith('.zip.parts.json') and p.name!='assemble_archive_parts.py']
    write_json(OUT/'package-manifest.json',{'schemaVersion':1,'members':[{'file':str(p.relative_to(OUT)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in files]})
    print(json.dumps(manifest['counts']))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--input',action='append',required=True);args=parser.parse_args();build([Path(p).resolve() for p in args.input])
