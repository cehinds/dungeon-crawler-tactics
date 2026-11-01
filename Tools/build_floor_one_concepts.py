#!/usr/bin/env python3
"""Extract reviewed full concept panels and package deterministic evidence."""
import hashlib
import json
import shutil
import zipfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'Docs/FloorOneConcepts'
OUT = ROOT / 'Web/wwwroot/assets/floor-one-concepts'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')


def baseline():
    return {str(p.relative_to(ROOT)): digest(p) for p in sorted((ROOT/'Web/wwwroot/assets').rglob('*')) if p.is_file() and OUT not in p.parents}


def font(size):
    for p in ('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf','/usr/share/fonts/truetype/liberation2/LiberationSans-Regular.ttf'):
        if Path(p).exists(): return ImageFont.truetype(p,size)
    return ImageFont.load_default()


def preview(panels, path, columns, cell_width, cell_height, title):
    canvas=Image.new('RGB',(columns*cell_width,70+((len(panels)+columns-1)//columns)*cell_height),'#17202a')
    draw=ImageDraw.Draw(canvas);draw.text((16,16),title,fill='white',font=font(22))
    for index,panel in enumerate(panels):
        x=(index%columns)*cell_width;y=70+(index//columns)*cell_height
        im=Image.open(OUT/panel['path']).convert('RGB')
        factor=min((cell_width-20)/im.width,(cell_height-110)/im.height)
        im=im.resize((max(1,round(im.width*factor)),max(1,round(im.height*factor))),Image.Resampling.NEAREST)
        canvas.paste(im,(x+(cell_width-im.width)//2,y))
        label=f"{panel['order']:02d} {panel['id']}"
        words=label.split('-');lines=['']
        for word in words:
            candidate=(lines[-1]+'-'+word).strip('-')
            if draw.textlength(candidate,font=font(20))>cell_width-20 and lines[-1]:lines.append(word)
            else:lines[-1]=candidate
        for row,line in enumerate(lines):draw.text((x+10,y+cell_height-100+row*25),line,fill='white',font=font(20))
        draw.text((x+10,y+cell_height-28),panel['status']+' | inferred composition',fill='#c5d0da',font=font(12))
    canvas.save(path)


def build():
    spec=json.loads((DOCS/'spec.json').read_text());coverage=json.loads((DOCS/'coverage.json').read_text())
    catalog={p['id']:p for p in coverage['panels']}
    if len(spec['sheets'])!=6: raise ValueError('Six reviewed source sheets required')
    prior_path=OUT/'baseline.json'
    prior=json.loads(prior_path.read_text()) if prior_path.exists() else baseline()
    for name,sha in prior.items():
        if digest(ROOT/name)!=sha: raise ValueError('Prior asset changed: '+name)
    OUT.mkdir(parents=True,exist_ok=True);write_json(prior_path,prior)
    records=[];sources=[]
    for sheet in spec['sheets']:
        if not sheet.get('reviewed'): raise ValueError('Source must pass visual review before extraction')
        original=ROOT/sheet['path'];image=Image.open(original).convert('RGBA')
        if list(image.size)!=sheet['canvasSize']:raise ValueError('Unexpected source canvas dimensions')
        if len(sheet['panels'])!=6:raise ValueError('Each sheet requires six reviewed panels')
        destination=OUT/'sources'/(sheet['id']+original.suffix.lower());destination.parent.mkdir(exist_ok=True)
        if original.resolve()!=destination.resolve():shutil.copyfile(original,destination)
        source={'id':sheet['id'],'path':str(destination.relative_to(OUT)),'originalPath':sheet['path'],'sha256':digest(destination),'canvasSize':list(image.size),'dividerLines':sheet['dividerLines'],'provenance':sheet['provenance']}
        sources.append(source)
        boxes=[]
        for cell in sheet['panels']:
            metadata=catalog[cell['id']]
            if metadata['batch']!=sheet['batch']:raise ValueError('Panel assigned to wrong batch')
            x,y,w,h=cell['rect'];box=(x,y,x+w,y+h)
            if min(x,y)<0 or min(w,h)<=0 or x+w>image.width or y+h>image.height:raise ValueError('Invalid native crop rectangle')
            for a,b,c,d in boxes:
                if max(a,x)<min(c,x+w) and max(b,y)<min(d,y+h):raise ValueError('Panel rectangles overlap')
            boxes.append(box)
            pixels=image.crop(box);target=OUT/'panels'/(cell['id']+'.png');target.parent.mkdir(exist_ok=True);pixels.save(target)
            records.append({**metadata,'sourceId':sheet['id'],'sourceRect':cell['rect'],'rectFormat':'xywh','path':str(target.relative_to(OUT)),'nativeSize':list(pixels.size),'sha256':digest(target),'pixelSha256':hashlib.sha256(pixels.tobytes()).hexdigest(),'boundaryReview':cell['boundaryReview']})
    if len(records)!=36 or set(catalog)!={p['id'] for p in records}:raise ValueError('Coverage mismatch')
    if len({p['pixelSha256'] for p in records})!=36:raise ValueError('Duplicate panel pixels')
    records.sort(key=lambda p:p['order']);previews=OUT/'previews';previews.mkdir(exist_ok=True)
    for batch in range(1,7):preview([p for p in records if p['batch']==batch],previews/f'group-{batch:02d}.png',2,540,510,f'Floor 1 concepts — group {batch} | full panels; captions outside artwork')
    preview(records,previews/'overview.png',6,420,350,'Floor 1 concept-art overview | 36 illustrative panels, not a tile kit')
    write_json(OUT/'manifest.json',{'schemaVersion':1,'title':'Floor 1 concept-art studies','scope':coverage['scope'],'projection':spec['projection'],'status':'static concept art; no gameplay integration; not seamless tiles','provenance':spec['provenance'],'sources':sources,'references':coverage['sources'],'panels':records})
    for name in ('README.md','coverage.json','spec.json'):
        shutil.copyfile(DOCS/name,OUT/name)
    tooling=OUT/'tools';tooling.mkdir(exist_ok=True)
    for name in ('build_floor_one_concepts.py','test_floor_one_concepts.py'):shutil.copyfile(ROOT/'Tools'/name,tooling/name)
    files=[p for p in sorted(OUT.rglob('*')) if p.is_file() and p.name not in ('floor-one-concepts.zip','package-manifest.json')]
    write_json(OUT/'package-manifest.json',{'schemaVersion':1,'members':[{'file':str(p.relative_to(OUT)),'bytes':p.stat().st_size,'sha256':digest(p)} for p in files]})
    with zipfile.ZipFile(OUT/'floor-one-concepts.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for p in files+[OUT/'package-manifest.json']:
            info=zipfile.ZipInfo(str(p.relative_to(OUT)),(2026,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;archive.writestr(info,p.read_bytes())
    print('Built 36 native concept panels; ZIP SHA256 '+digest(OUT/'floor-one-concepts.zip'))


if __name__=='__main__':build()
