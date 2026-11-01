#!/usr/bin/env python3
"""Add deterministic coordinate overlays to clean concept panels without resampling."""
import argparse
import hashlib
import json
import shutil
import zipfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / 'Docs/FloorOneConceptGrids'
OUT = ROOT / 'Web/wwwroot/assets/floor-one-concept-grids'
SETS = {'original':'floor-one-concepts','top-down':'floor-one-concepts-top-down'}
FONT = Path('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf')


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')


def freeze_prior():
    path=OUT/'baseline.json'
    if path.exists():
        prior=json.loads(path.read_text())
        for name,sha in prior.items():
            if digest(ROOT/name)!=sha: raise ValueError('Prior asset changed: '+name)
        return
    prior={str(p.relative_to(ROOT)):digest(p) for p in sorted((ROOT/'Web/wwwroot/assets').rglob('*')) if p.is_file() and OUT not in p.parents}
    write_json(path,prior)


def prepare_font():
    target=OUT/'sources/DejaVuSans.ttf';target.parent.mkdir(parents=True,exist_ok=True)
    if not target.exists(): shutil.copyfile(FONT,target)
    license_path=Path('/usr/share/doc/fonts-dejavu-core/copyright')
    if license_path.exists(): shutil.copyfile(license_path,OUT/'sources/font-license.txt')
    return target


def grid(image, spec, font_path):
    """Grid equal logical cells over unchanged native extent; labels occupy margins."""
    image=image.convert('RGBA');w,h=image.size;margin=spec['margin']
    xs=[round(i*w/14) for i in range(15)];ys=[round(i*h/14) for i in range(15)]
    result=Image.new('RGBA',(w+2*margin,h+2*margin),tuple(spec['marginColor']))
    result.alpha_composite(image,(margin,margin))
    overlay=Image.new('RGBA',image.size)
    draw=ImageDraw.Draw(overlay)
    for positions,vertical in ((xs,True),(ys,False)):
        for boundary in positions:
            position=min(boundary,(w if vertical else h)-1)
            line=(position,0,position,h-1) if vertical else (0,position,w-1,position)
            draw.line(line,fill=tuple(spec['haloColor']),width=3)
            draw.line(line,fill=tuple(spec['lineColor']),width=1)
    result.alpha_composite(overlay,(margin,margin))
    draw=ImageDraw.Draw(result);label_font=ImageFont.truetype(str(font_path),spec['labelSize'])
    for i in range(14):
        cx=margin+(xs[i]+xs[i+1])/2;cy=margin+(ys[i]+ys[i+1])/2
        draw.text((cx,margin/2),chr(65+i),font=label_font,fill='white',anchor='mm')
        draw.text((margin/2,cy),str(i+1),font=label_font,fill='white',anchor='mm')
    return result,{'columns':list('ABCDEFGHIJKLMN'),'rows':list(range(1,15)),'xBoundaries':xs,'yBoundaries':ys,'contentRect':[margin,margin,w,h],'edgeRule':'Logical extent boundaries use round(i*extent/14); outer visible stroke clamps to last pixel. Cells may differ by one pixel.'}


def preview(records, target, title, font_path, columns=2, cell=540):
    row_height=640;canvas=Image.new('RGB',(columns*cell,65+((len(records)+columns-1)//columns)*row_height),'#17202a')
    draw=ImageDraw.Draw(canvas);heading=ImageFont.truetype(str(font_path),21);label=ImageFont.truetype(str(font_path),19)
    draw.text((12,16),title,fill='white',font=heading)
    for index,record in enumerate(records):
        x=(index%columns)*cell;y=65+(index//columns)*row_height
        image=Image.open(OUT/record['path']).convert('RGBA');factor=min((cell-20)/image.width,(row_height-100)/image.height)
        image=image.resize((round(image.width*factor),round(image.height*factor)),Image.Resampling.NEAREST)
        canvas.paste(image,(x+(cell-image.width)//2,y),image)
        text=f"{record['order']:02d} {record['id']}";lines=['']
        for word in text.split('-'):
            candidate=(lines[-1]+'-'+word).strip('-')
            if draw.textlength(candidate,font=label)>cell-20 and lines[-1]:lines.append(word)
            else:lines[-1]=candidate
        for row,line in enumerate(lines):draw.text((x+10,y+row_height-88+25*row),line,fill='white',font=label)
        draw.text((x+10,y+row_height-30),record['set']+' | A-N left to right, 1-14 top to bottom',fill='#c5d0da',font=ImageFont.truetype(str(font_path),13))
    canvas.save(target)


def build(sample=False):
    spec=json.loads((DOCS/'spec.json').read_text())
    if not sample and not spec['styleApprovedByRoot']:raise ValueError('Root must approve sample grid style before full build')
    OUT.mkdir(parents=True,exist_ok=True);freeze_prior();font_path=prepare_font();records=[];source_sets=[]
    for set_id,pack in SETS.items():
        source_dir=ROOT/'Web/wwwroot/assets'/pack;manifest_path=source_dir/'manifest.json';manifest=json.loads(manifest_path.read_text())
        target=OUT/'sources'/(set_id+'-manifest.json');shutil.copyfile(manifest_path,target)
        source_sets.append({'id':set_id,'sourcePack':pack,'manifestPath':str(target.relative_to(OUT)),'manifestSha256':digest(target),'projection':manifest.get('projection','Mixed overhead and frontal concept views')})
        for panel in sorted(manifest['panels'],key=lambda p:p['order']):
            if sample and panel['order']!=1:continue
            source=source_dir/panel['path'];image=Image.open(source);pixels,geometry=grid(image,spec,font_path)
            destination=OUT/'panels'/set_id/(panel['id']+'.png');destination.parent.mkdir(parents=True,exist_ok=True);pixels.save(destination)
            records.append({'id':panel['id'],'set':set_id,'order':panel['order'],'batch':panel['batch'],'sourcePath':str(source.relative_to(ROOT)),'sourceSha256':digest(source),'sourceSize':list(image.size),'path':str(destination.relative_to(OUT)),'sha256':digest(destination),'size':list(pixels.size),'grid':geometry})
    previews=OUT/'previews';previews.mkdir(exist_ok=True)
    if sample:
        preview(records,previews/'sample-review.png','14x14 grid style sample | clean image unchanged beneath lines',font_path)
        print('Sample ready: '+str(previews/'sample-review.png'));return
    if len(records)!=72:raise ValueError('Expected72 gridded concept panels')
    for set_id in SETS:
        for batch in range(1,7):preview([r for r in records if r['set']==set_id and r['batch']==batch],previews/f'{set_id}-group-{batch:02d}.png',f'Floor1 {set_id} concepts | 14x14 coordinate overlays | group{batch}',font_path)
        preview([r for r in records if r['set']==set_id],previews/(set_id+'-overview.png'),f'Floor1 {set_id} | all36 coordinate overlays',font_path,columns=6,cell=420)
    write_json(OUT/'manifest.json',{'schemaVersion':1,'title':'Floor1 concept-art coordinate grids','scope':'72 deterministic overlays across original and top-down concept sets; preserves clean inputs. Grids partition full native panel extent, including any source gutters; they do not establish canonical scale, equal world tile size or seamless geometry.','style':spec,'font':{'path':str(font_path.relative_to(OUT)),'sha256':digest(font_path)},'sourceSets':source_sets,'panels':records})
    for name in ('README.md','spec.json'):shutil.copyfile(DOCS/name,OUT/name)
    tooling=OUT/'tools';tooling.mkdir(exist_ok=True)
    for name in ('build_floor_one_concept_grids.py','test_floor_one_concept_grids.py'):shutil.copyfile(ROOT/'Tools'/name,tooling/name)
    files=[p for p in sorted(OUT.rglob('*')) if p.is_file() and p.name not in ('floor-one-concept-grids.zip','package-manifest.json')]
    write_json(OUT/'package-manifest.json',{'schemaVersion':1,'members':[{'file':str(p.relative_to(OUT)),'bytes':p.stat().st_size,'sha256':digest(p)} for p in files]})
    with zipfile.ZipFile(OUT/'floor-one-concept-grids.zip','w',zipfile.ZIP_DEFLATED) as archive:
        for p in files+[OUT/'package-manifest.json']:
            info=zipfile.ZipInfo(str(p.relative_to(OUT)),(2026,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o100644<<16;archive.writestr(info,p.read_bytes())
    print('Built72 gridded concepts; ZIP SHA256 '+digest(OUT/'floor-one-concept-grids.zip'))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--sample',action='store_true');build(parser.parse_args().sample)
