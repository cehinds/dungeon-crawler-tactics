#!/usr/bin/env python3
"""Deterministic packaging of approved character art; no generated drawing or lore."""
import hashlib
import json
import shutil
import zipfile
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'Web/wwwroot/assets/character-correction'
SPEC = ROOT / 'Docs/CharacterArtCorrection/spec.json'


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, value):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, ensure_ascii=False) + '\n')


def fit(image, size=128):
    scale = min(size / image.width, size / image.height)
    resized = image.resize((max(1, round(image.width * scale)), max(1, round(image.height * scale))), Image.Resampling.NEAREST)
    result = Image.new('RGBA', (size, size))
    result.alpha_composite(resized, ((size-resized.width)//2, size-resized.height))
    return result


def snapshot():
    return {str(p.relative_to(ROOT)): digest(p) for p in sorted((ROOT/'Web/wwwroot/assets').rglob('*')) if p.is_file() and OUT not in p.parents}


def save_preview(rows, path, title, cell_width=260, cell_height=210):
    canvas = Image.new('RGB', (cell_width * 4, 45 + cell_height * len(rows)), '#202530')
    draw = ImageDraw.Draw(canvas)
    draw.text((12, 12), title, fill='white')
    for y, row in enumerate(rows):
        for x, (label, image) in enumerate(row):
            draw.text((x*cell_width+12,45+y*cell_height),label,fill='white')
            if image:
                preview=fit(image, min(160,cell_height-40))
                canvas.paste(preview,(x*cell_width+45,75+y*cell_height),preview)
    canvas.save(path)


def build():
    spec=json.loads(SPEC.read_text())
    if not spec['variants']:
        raise ValueError('No approved source variants configured')
    baseline_path=OUT/'baseline.json'
    baseline=json.loads(baseline_path.read_text()) if baseline_path.exists() else snapshot()
    for path, sha in baseline.items():
        if digest(ROOT/path)!=sha: raise ValueError('Prior asset changed: '+path)
    OUT.mkdir(parents=True,exist_ok=True)
    write_json(baseline_path,baseline)
    sources={}
    for source in spec['sources']:
        src=ROOT/source['path']; target=OUT/'sources'/src.name
        target.parent.mkdir(parents=True,exist_ok=True); shutil.copyfile(src,target)
        sources[source['id']]={**source,'packagePath':str(target.relative_to(OUT)),'sha256':digest(target)}
    records=[]; compatibility={}; pictures={}
    for variant in spec['variants']:
        record={k:v for k,v in variant.items() if k not in ('world','portrait')}
        record['assets']={}
        for role in ('world','portrait'):
            crop=variant[role]; source=sources[crop['sourceId']]
            image=Image.open(OUT/source['packagePath']).convert('RGBA')
            x,y,w,h=crop['rect']; native=image.crop((x,y,x+w,y+h))
            if x<0 or y<0 or x+w>image.width or y+h>image.height: raise ValueError('Crop outside source')
            if native.getchannel('A').getextrema()[0]!=0: raise ValueError('Native art lacks transparency')
            paths={}
            for kind, pixels in [('native',native),('128',fit(native))]:
                target=OUT/kind/(variant['id']+'-'+role+'.png');target.parent.mkdir(exist_ok=True);pixels.save(target)
                paths[kind]={'path':str(target.relative_to(OUT)),'sha256':digest(target),'size':list(pixels.size),'alphaBounds':pixels.getbbox()}
            record['assets'][role]={'sourceId':crop['sourceId'],'rect':crop['rect'],'files':paths}
            pictures[(variant['id'],role)]=native
            for old in variant.get('supersedes',{}).get(role,[]): compatibility.setdefault(old,[]).append({'variantId':variant['id'],'characterId':variant['characterId'],'role':role,'path':paths['native']['path']})
        records.append(record)
    previews=OUT/'previews';previews.mkdir(exist_ok=True)
    rows=[]
    for v in spec['variants']:
        rows.append([(v['label']+' world',pictures[v['id'],'world']),(v['label']+' portrait',pictures[v['id'],'portrait'])])
    save_preview(rows,previews/'contact-sheet.png','Approved character variants | normalized display, not relative height')
    main=[v for v in spec['variants'] if v.get('isMain')]
    rows=[]
    for role in ('world','portrait'):
        for old in (True,False):
            rows.append([(v['label']+(' BEFORE' if old else ' AFTER'),Image.open(ROOT/'Web/wwwroot/assets/exploration-components/components'/((('actor' if role=='world' else 'portrait')+'-'+v['characterId'])+'.png')).convert('RGBA') if old else pictures[v['id'],role]) for v in main])
    save_preview(rows,previews/'before-after.png','Prior exploration art and corrected main variants')
    scale_canvas=Image.new('RGBA',(260*len(main),440),'#202530');draw=ImageDraw.Draw(scale_canvas)
    for i,v in enumerate(main):
        im=pictures[v['id'],'world']; height=round(280*v['worldScale']); im=im.resize((round(im.width*height/im.height),height),Image.Resampling.NEAREST)
        scale_canvas.alpha_composite(im,(i*260+(260-im.width)//2,400-im.height));draw.text((i*260+12,415),v['label']+' scale '+str(v['worldScale']),fill='white')
    scale_canvas.save(previews/'relative-height.png')
    write_json(OUT/'manifest.json',{'schemaVersion':1,'packId':spec['packId'],'status':'reviewable art pack; no runtime integration or walking animation','provenance':spec['provenance'],'sources':list(sources.values()),'variants':records})
    write_json(OUT/'compatibility.json',compatibility)
    for name in ('README.md','sources.json','research-katia-mongo.md','art-brief.md'):
        src=SPEC.parent/name
        if src.exists():shutil.copyfile(src,OUT/name)
    shutil.copyfile(SPEC,OUT/'spec.json')
    tooling=OUT/'tools';tooling.mkdir(exist_ok=True)
    for name in ('build_character_correction.py','test_character_correction.py'):
        shutil.copyfile(ROOT/'Tools'/name,tooling/name)
    package_files=[p for p in sorted(OUT.rglob('*')) if p.is_file() and p.name not in ('character-correction.zip','package-manifest.json')]
    write_json(OUT/'package-manifest.json',{'schemaVersion':1,'members':[{'path':str(p.relative_to(OUT)),'sha256':digest(p),'bytes':p.stat().st_size} for p in package_files]})
    with zipfile.ZipFile(OUT/'character-correction.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for p in package_files+[OUT/'package-manifest.json']:
            info=zipfile.ZipInfo(str(p.relative_to(OUT)),(2026,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;archive.writestr(info,p.read_bytes())
    print(f'Built {len(records)} variants; ZIP SHA256 {digest(OUT/"character-correction.zip")}')


if __name__=='__main__':
    build()
