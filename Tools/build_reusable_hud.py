#!/usr/bin/env python3
"""Build clean reusable HUD controls from image-generated surfaces and source parts."""
import hashlib
import json
import shutil
import zipfile
import xml.etree.ElementTree as ET
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'Web/wwwroot/assets/hud-reusable'
SPEC = ROOT / 'Docs/HudComponents/reusable-spec.json'
SIZE = (1536,1024)

def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def dump(p,data): p.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')
def font(n): return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf',n)
def checker(size):
    im=Image.new('RGBA',size,'#18212e');d=ImageDraw.Draw(im)
    for y in range(0,size[1],12):
        for x in range(0,size[0],12):
            if (x//12+y//12)%2:d.rectangle((x,y,x+11,y+11),fill='#263346')
    return im

def zip_write(z,name,data):
    e=zipfile.ZipInfo(name,(1980,1,1,0,0,0));e.compress_type=zipfile.ZIP_DEFLATED;e.external_attr=0o644<<16;z.writestr(e,data)

def shape_mask(shape):
    im=Image.new('L',SIZE);d=ImageDraw.Draw(im)
    if shape['type']=='rect':
        x,y,w,h=shape['bounds'];d.rectangle((x,y,x+w-1,y+h-1),fill=255)
    elif shape['type']=='polygon':d.polygon([tuple(v) for v in shape['points']],fill=255)
    else:raise ValueError('Clean silhouette must be authored rect/polygon')
    return im

def main():
    spec=json.loads(SPEC.read_text());src=ROOT/spec['sourceManifest'];source=json.loads(src.read_text())
    for key in ['navy','parchment']:
        if key not in spec['materials']:raise SystemExit('Provide image-generated material '+key+' in reusable-spec.json materials first.')
    for folder in ['original','backgrounds','masks','parts','blank','populated','details','materials']:(OUT/folder).mkdir(parents=True,exist_ok=True)
    materials={}
    for key,entry in spec['materials'].items():
        p=ROOT/entry['file'];im=Image.open(p).convert('RGB');im=im.crop(entry['crop']) if 'crop' in entry else im
        dest=OUT/'materials'/f'{key}.png';im.save(dest)
        materials[key]=dict(entry,file='materials/'+key+'.png',originalFile=entry['file'],sha256=sha(dest),originalSha256=sha(p),size=list(im.size))
    assets=[];originals={};by_id={e['id']:e for e in source['layers']};group_map={g['id']:g for g in source['groups']}
    def emit(id,im,offset,parent,role,provenance,z=0,folder='parts',**extra):
        file=f'{folder}/{id}.png';im.save(OUT/file)
        a=dict(id=id,file=file,parentId=parent,role=role,provenance=provenance,offset=list(offset),size=list(im.size),bounds=list(offset)+list(im.size),z=z,sha256=sha(OUT/file),pivot={'normalized':[0,0],'pixels':[0,0],'kind':'top-left'},**extra)
        assets.append(a);return a
    def compose(es):
        im=Image.new('RGBA',SIZE)
        for a in sorted(es,key=lambda a:(a['z'],a['id'])):im.alpha_composite(Image.open(OUT/a['file']).convert('RGBA'),tuple(a['offset']))
        return im
    for e in source['layers']:
        im=Image.open(src.parent/e['file']).convert('RGBA');file='original/'+e['id']+'.png';shutil.copyfile(src.parent/e['file'],OUT/file)
        originals[e['id']]=dict(e,file=file,role=e['category'],provenance={'kind':'literal-source-fragment','sourceFile':str((src.parent/e['file']).relative_to(ROOT))})
    backgrounds={};frames={};excluded=set()
    for definition in spec['backgrounds']:
        gid=definition['groupId'];frame=by_id[definition['frameId']];shape=frame['shape'];mask=shape_mask(shape);bbox=mask.getbbox()
        # Stretch image-generated material in native panel space; never retain a holed source body.
        surface=Image.open(OUT/materials[definition['material']]['file']).convert('RGBA').resize((bbox[2]-bbox[0],bbox[3]-bbox[1]),Image.Resampling.LANCZOS)
        local_mask=mask.crop(bbox);surface.putalpha(local_mask);local_mask.save(OUT/'masks'/f'{gid}-exterior.png')
        backgrounds[gid]=emit(gid+'-clean-background',surface,bbox[:2],gid,'clean-background',{'kind':'reconstructed-imagegen-material','materialId':definition['material'],'geometry':'authored-source-silhouette'},z=frame['z']-1,folder='backgrounds',exteriorShape=shape,maskFile=f'masks/{gid}-exterior.png')
        entries=[by_id[i] for i in group_map[gid]['layerIds']]
        excluded.update(e['id'] for e in entries if e['category'] in ['ui-panel','ui-button-body'])
        im=Image.open(OUT/originals[frame['id']]['file']).convert('RGBA');w,h=im.size
        # Source ownership includes occasional bright portrait-colored boundary fringes.
        # Move only those literal pixels to an optional foreground overlay, never repaint the frame.
        if gid.startswith('party-'):
            arr=np.array(im);rgb=arr[:,:,:3].astype(float);rr,gg,bb=rgb[:,:,0],rgb[:,:,1],rgb[:,:,2]
            peak=rgb.max(axis=2);floor=rgb.min(axis=2)
            colored=(arr[:,:,3]>0)&(peak>=90)&((peak-floor)>=45)&((bb>rr*.85)|(gg<rr*.55))
            overlay=arr.copy();overlay[~colored]=0
            if np.any(colored):
                emit(frame['id']+'-portrait-fringe',Image.fromarray(overlay),frame['offset'],gid,'source-boundary-fringe',{'kind':'source-pixel-subset','sourceLayerId':frame['id'],'selection':'bright blue/purple/red non-gold boundary colors; source RGB preserved'},z=frame['z']+1,sourceLayerId=frame['id'])
                arr[colored]=0;im=Image.fromarray(arr)

        l,t,r,b=spec['frameMargins'].get(frame['id'],spec['frameMargins']['default']);l=min(l,w//3);r=min(r,w//3);t=min(t,h//3);b=min(b,h//3)
        xs=[0,l,w-r,w];ys=[0,t,h-b,h];parts=[]
        names=[['top-left','top','top-right'],['left','center-residual','right'],['bottom-left','bottom','bottom-right']]
        for row in range(3):
            for col in range(3):
                box=[xs[col],ys[row],xs[col+1],ys[row+1]];piece=im.crop(box)
                if not piece.getbbox():continue
                name=names[row][col];a=emit(frame['id']+'-'+name,piece,[frame['offset'][0]+box[0],frame['offset'][1]+box[1]],gid,'border-'+name,{'kind':'source-crop','sourceLayerId':frame['id'],'crop':box},z=frame['z'],sourceLayerId=frame['id'],slice={'row':row,'column':col,'rect':box},stretchAxis='x' if name in ['top','bottom'] else 'y' if name in ['left','right'] else None);parts.append(a)
        frames[gid]=parts;excluded.add(frame['id'])
    # Existing track fragments only expose unfilled tail. Rebuild the complete track from that actual tail texture.
    track_assets={};stat_bases={}
    for stat in ['hp','mana']:
        outline=by_id[f'hud-{stat}-outline'];mask=shape_mask(outline['shape']);bb=mask.getbbox()
        base=Image.open(OUT/materials['navy']['file']).convert('RGBA').resize((bb[2]-bb[0],bb[3]-bb[1]),Image.Resampling.LANCZOS);base.putalpha(mask.crop(bb))
        mask.crop(bb).save(OUT/'masks'/f'{stat}-exterior.png')
        stat_bases[stat]=emit(stat+'-clean-background',base,bb[:2],stat,'clean-background',{'kind':'reconstructed-imagegen-material','materialId':'navy','geometry':'authored-source-silhouette'},z=outline['z']-1,folder='backgrounds',exteriorShape=outline['shape'],maskFile=f'masks/{stat}-exterior.png')
        e=by_id[f'hud-{stat}-track'];x,y,w,h=e['shape']['bounds'];im=Image.open(OUT/originals[e['id']]['file']).convert('RGBA')
        arr=np.array(im);cols=np.flatnonzero(np.all(arr[:,:,3]==255,axis=0))
        if len(cols)==0:raise ValueError('No opaque source tail for '+e['id'])
        tail=im.crop((int(cols[0]),0,int(cols[-1])+1,im.height)).resize((w,h),Image.Resampling.NEAREST)
        track_assets[stat]=emit(e['id']+'-complete',tail,[x,y],stat,'complete-stat-track',{'kind':'source-texture-extension','sourceLayerId':e['id'],'note':'Visible opaque source tail extended across complete authored track bounds.'},z=e['z'])
        excluded.add(e['id'])
    split_sources={}
    for e in source['layers']:
        if e['id'] in excluded:continue
        im=Image.open(OUT/originals[e['id']]['file']).convert('RGBA');off=e['offset'];gid=e['parentId']
        if e['category']=='text':
            occupied=np.any(np.array(im)[:,:,3]>0,axis=0);runs=[];start=None
            for x,on in enumerate(list(occupied)+[False]):
                if on and start is None:start=x
                if not on and start is not None:runs.append([start,x]);start=None
            glyphs=[]
            for i,(left,right) in enumerate(runs):
                part=im.crop((left,0,right,im.height));glyphs.append(emit(e['id']+f'-glyph-run-{i+1:02}',part,[off[0]+left,off[1]],gid,'raster-glyph-run',{'kind':'source-crop','sourceLayerId':e['id'],'crop':[left,0,right,im.height]},z=e['z'],sourceLayerId=e['id'],textTranscription=e.get('text',{}).get('value'),editableFont=False))
            split_sources[e['id']]=[a['id'] for a in glyphs]
        elif e['category'] in ['ui-track','ui-fill'] or e['id'].endswith('-outline'):
            if e['id'] in ['hud-hp-outline','hud-mana-outline']:
                arr=np.array(im);rr=arr[:,:,0].astype(float);gg=arr[:,:,1].astype(float);bb=arr[:,:,2].astype(float)
                if e['id']=='hud-hp-outline': colored=(arr[:,:,3]>0)&(rr>gg*1.4)&(rr>70)
                else: colored=(arr[:,:,3]>0)&(gg>rr*1.5)&(bb>rr*1.5)&(gg>90)
                overlay=arr.copy();overlay[~colored]=0
                if np.any(colored):
                    emit(e['id']+'-fill-fringe',Image.fromarray(overlay),off,gid,'source-boundary-fringe',{'kind':'source-pixel-subset','sourceLayerId':e['id'],'selection':'red HP or cyan Mana fill fringe assigned to outline by original segmentation; literal RGB retained'},z=e['z']+1,sourceLayerId=e['id'])
                    arr[colored]=0;im=Image.fromarray(arr)
            cap=min(2,im.width//3);parts=[]
            for suffix,box in [('left-cap',(0,0,cap,im.height)),('stretch',(cap,0,im.width-cap,im.height)),('right-cap',(im.width-cap,0,im.width,im.height))]:
                part=im.crop(box)
                if part.getbbox():parts.append(emit(e['id']+'-'+suffix,part,[off[0]+box[0],off[1]],gid,'stat-'+suffix,{'kind':'source-crop','sourceLayerId':e['id'],'crop':list(box)},z=e['z'],sourceLayerId=e['id'],stretchAxis='x' if suffix=='stretch' else None))
            split_sources[e['id']]=[a['id'] for a in parts]
        else:
            emit(e['id'],im,off,gid,e['category'],{'kind':'literal-source-fragment','sourceLayerId':e['id']},z=e['z'],sourceLayerId=e['id'])
    groups=[]
    for original in source['groups']:
        gid=original['id'];es=[a for a in assets if a['parentId']==gid]
        # Panel-sized blank controls contain only the unbroken clean material and literal border pieces.
        blank_assets=([backgrounds[gid]]+frames[gid]) if gid in backgrounds else ([stat_bases[gid],track_assets[gid]]+[a for a in es if a['role'].startswith('stat-') and a.get('sourceLayerId','').endswith('-outline')]) if gid in track_assets else []
        populated=compose(es);bounds=populated.getbbox();pfile='populated/'+gid+'.png';populated.crop(bounds).save(OUT/pfile)
        bfile=None
        if blank_assets:
            blank=compose(blank_assets);bb=blank.getbbox();bfile='blank/'+gid+'.png';blank.crop(bb).save(OUT/bfile)
        else:bb=None
        groups.append(dict(id=gid,label=original['label'],parentId=original['parentId'],assetIds=[a['id'] for a in sorted(es,key=lambda a:(a['z'],a['id']))],blankAssetIds=[a['id'] for a in blank_assets],blankFile=bfile,blankBounds=[bb[0],bb[1],bb[2]-bb[0],bb[3]-bb[1]] if bb else None,repopulatedFile=pfile,bounds=[bounds[0],bounds[1],bounds[2]-bounds[0],bounds[3]-bounds[1]],offset=list(bounds[:2]),size=[bounds[2]-bounds[0],bounds[3]-bounds[1]]))
        for a in es:a['offsetInParent']=[a['offset'][0]-bounds[0],a['offset'][1]-bounds[1]]
        # One labelled row per actual part, at native size.
        height=70+sum(max(55,a['size'][1]+32) for a in es);width=max(800,max(a['size'][0]+40 for a in es))
        sheet=checker((width,height));d=ImageDraw.Draw(sheet);d.text((16,14),original['label']+' / reusable parts',font=font(22),fill='white');yy=60
        for a in sorted(es,key=lambda a:(a['z'],a['id'])):
            d.text((16,yy),a['id'],font=font(13),fill='#ffd778');sheet.alpha_composite(Image.open(OUT/a['file']),(16,yy+19));yy+=max(55,a['size'][1]+32)
        sheet.convert('RGB').save(OUT/'details'/f'{gid}.png')
    full=compose(assets);full.save(OUT/'repopulated-hud.png')
    # A compact native-scale sheet prioritizes the newly clean controls.
    sheet=checker((1584,1300));d=ImageDraw.Draw(sheet);d.text((24,18),'CLEAN REUSABLE HUD / reconstructed backgrounds',font=font(28),fill='white');d.text((24,59),'Original borders, icons, portraits and raster lettering remain separate.',font=font(17),fill='#b8c6dc')
    x,y,rh=24,100,0
    for g in groups:
        if not g['blankFile'] or g['id']=='bottom-panel':continue
        im=Image.open(OUT/g['blankFile'])
        if x+im.width+24>1560:x=24;y+=rh+42;rh=0
        d.text((x,y),g['label'],font=font(16),fill='#ffd778');sheet.alpha_composite(im,(x,y+27));x+=im.width+28;rh=max(rh,im.height+27)
    y+=rh+45;dock=next(g for g in groups if g['id']=='bottom-panel');d.text((24,y),'Clean bottom dock / no shoe, text, icon or portrait cutouts',font=font(18),fill='#ffd778');sheet.alpha_composite(Image.open(OUT/dock['blankFile']),(24,y+30));y+=220
    d.text((24,y),'Repopulated HUD controls / same separate original foreground parts',font=font(18),fill='#ffd778')
    lower=full.crop((10,740,1528,982));sheet.alpha_composite(lower,(24,y+32));y+=290
    d.text((24,y),f'{len(assets)} reusable parts / 78 archived source fragments / image-generated navy and parchment surfaces',font=font(17),fill='#b8c6dc');sheet.crop((0,0,1584,y+52)).convert('RGB').save(OUT/'overview.png')
    compare=checker((1584,620));d=ImageDraw.Draw(compare);d.text((24,14),'ORIGINAL: source background fragments contain foreground-shaped holes',font=font(21),fill='white');im=Image.open(src.parent/'widgets/bottom-panel.png');compare.alpha_composite(im,(24,58));d.text((24,235),'CLEAN: image-generated material under the original outer border',font=font(21),fill='white');compare.alpha_composite(Image.open(OUT/dock['blankFile']),(24,279));d.text((24,460),'Holes removed throughout the dock, including under lettering, meters, boot and action controls.',font=font(18),fill='#ffd778');compare.crop((0,0,1584,510)).convert('RGB').save(OUT/'original-vs-clean.png')
    move=next(g for g in groups if g['id']=='action-move')
    focused=checker((1100,570));fd=ImageDraw.Draw(focused)
    fd.text((22,16),'MOVE / clean background and separate source parts',font=font(25),fill='white')
    labels=['Old background / icon-shaped holes','Clean background / opaque interior','Blank framed control','Repopulated control']
    images=[Image.open(OUT/originals['action-move-body']['file']),Image.open(OUT/backgrounds['action-move']['file']),Image.open(OUT/move['blankFile']),Image.open(OUT/move['repopulatedFile'])]
    for i,(label,im) in enumerate(zip(labels,images)):
        xx=22+i*268;fd.text((xx,63),label,font=font(13),fill='#ffd778');focused.alpha_composite(im.resize((im.width*2,im.height*2),Image.Resampling.NEAREST),(xx,94))
    fd.text((22,370),'Separate original foreground parts (native source pixels)',font=font(19),fill='white')
    for i,id in enumerate(['action-move-icon','action-move-frame','action-move-label','action-move-glow']):
        xx=22+i*268;fd.text((xx,406),id,font=font(14),fill='#ffd778');im=Image.open(OUT/originals[id]['file']);focused.alpha_composite(im,(xx,434))
    focused.convert('RGB').save(OUT/'move-before-after.png')
    shutil.copyfile(SPEC,OUT/'sources/reusable-spec.json')
    manifest=dict(schemaVersion=1,canvas=list(SIZE),sourceManifest=spec['sourceManifest'],sourceManifestSha256=sha(src),materials=materials,notes=spec['notes'],assets=assets,originals=list(originals.values()),groups=groups,splitSources=split_sources,artifacts={'overview':'overview.png','comparison':'original-vs-clean.png','moveComparison':'move-before-after.png','repopulated':'repopulated-hud.png','layered':'hud-reusable.ora','archive':'hud-reusable.zip'})
    dump(OUT/'manifest.json',manifest)
    root=ET.Element('image',w='1536',h='1024',name='Reusable HUD',version='0.0.3');stack=ET.SubElement(root,'stack')
    with zipfile.ZipFile(OUT/'hud-reusable.ora','w') as z:
        zip_write(z,'mimetype',b'image/openraster')
        for a in reversed(sorted(assets,key=lambda a:(a['z'],a['id']))):
            file='data/'+a['id']+'.png';zip_write(z,file,(OUT/a['file']).read_bytes());ET.SubElement(stack,'layer',name=a['id'],src=file,x=str(a['offset'][0]),y=str(a['offset'][1]),opacity='1.0',visibility='visible',**{'composite-op':'svg:src-over'})
        zip_write(z,'stack.xml',ET.tostring(root,encoding='utf-8',xml_declaration=True));zip_write(z,'mergedimage.png',(OUT/'repopulated-hud.png').read_bytes())
    package=dict(schemaVersion=1,members=[dict(file=p.relative_to(OUT).as_posix(),sha256=sha(p),bytes=p.stat().st_size) for p in sorted(OUT.rglob('*')) if p.is_file() and p.name not in ['hud-reusable.zip','package-manifest.json']])
    dump(OUT/'package-manifest.json',package)
    with zipfile.ZipFile(OUT/'hud-reusable.zip','w') as z:
        for p in sorted(OUT.rglob('*')):
            if p.is_file() and p.name!='hud-reusable.zip':zip_write(z,p.relative_to(OUT).as_posix(),p.read_bytes())
    print(f'Built {len(assets)} reusable parts, {len(backgrounds)+len(stat_bases)} clean backgrounds, {len(groups)} groups')

if __name__=='__main__':main()
