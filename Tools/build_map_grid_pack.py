#!/usr/bin/env python3
"""Pixel-preserving map comparison and authored component extraction.

Only crops, alpha extraction, resizing for review, and layer assembly are used.
Artwork reconstruction is supplied by image generation, never painted here.
"""
import argparse, hashlib, io, json, zipfile
from pathlib import Path
from PIL import Image, ImageDraw, ImageChops, ImageFilter
ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'Web/wwwroot/assets/map-grid-pass'
SPEC = ROOT / 'Docs/MapGridPass/component-spec.json'

def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def save(im,path):
    path.parent.mkdir(parents=True,exist_ok=True);im.save(path)
def label(im,text):
    result=Image.new('RGB',(im.width,im.height+30),'#14191c');result.paste(im,(0,30))
    ImageDraw.Draw(result).text((8,8),text,fill='white');return result

def overlay(im,sub=False):
    im=im.convert('RGB').copy();d=ImageDraw.Draw(im)
    step=128 if sub else 256
    for x in range(0,1536,step): d.line((x,0,x,1023),fill='#a3c4c5' if sub else '#ffdb6e',width=1)
    for y in range(0,1024,step): d.line((0,y,1535,y),fill='#a3c4c5' if sub else '#ffdb6e',width=1)
    for r in range(4):
        for c in range(6):
            x,y=c*256,r*256;d.rectangle((x+3,y+3,x+48,y+20),fill='#14191c');d.text((x+6,y+6),f'{chr(65+c)}{r+1}',fill='white')
    return im

def build():
    spec=json.loads(SPEC.read_text());OUT.mkdir(parents=True,exist_ok=True)
    # Retire the early row-first review filenames when rebuilding the column-first audit convention.
    for folder in ['comparison/cells','comparison/subcells']:
        for stale in (OUT/folder).glob('[1-4][A-F]*.png'):stale.unlink()
    sources={s['id']:s for s in spec['sources']};images={}
    for s in sources.values():
        p=ROOT/s['path']
        if not p.exists(): continue
        s.update(sha256=sha(p),width=Image.open(p).width,height=Image.open(p).height)
        images[s['id']]=Image.open(p).convert('RGBA')
    reference,implementation=images['reference'],images['implementation']
    for key,im in [('reference',reference),('implementation',implementation)]:
        save(overlay(im),OUT/f'comparison/{key}-grid.png');save(overlay(im,True),OUT/f'comparison/{key}-subgrid.png')
    thumbs=[];sheets=[]
    auditpath=ROOT/'Docs/MapGridPass/comparison.json'
    audit=json.loads(auditpath.read_text()) if auditpath.exists() else None
    for r in range(4):
        for c in range(6):
            cell=f'{chr(65+c)}{r+1}';rect=[c*256,r*256,(c+1)*256,(r+1)*256]
            sheet=Image.new('RGB',(528,330),'#14191c');draw=ImageDraw.Draw(sheet)
            draw.text((8,8),f'{cell} | reference / implementation | subcells NW NE SW SE',fill='white')
            for index,im in enumerate([reference,implementation]):
                crop=im.crop(rect).convert('RGB');sheet.paste(crop,(index*264,34))
                draw.line((index*264+128,34,index*264+128,290),fill='#ffdb6e');draw.line((index*264,162,index*264+256,162),fill='#ffdb6e')
                for sr in range(2):
                    for sc in range(2):
                        sub=crop.crop((sc*128,sr*128,(sc+1)*128,(sr+1)*128))
                        save(sub,OUT/f'comparison/subcells/{cell}-{sr*2+sc+1}-{"reference" if index==0 else "implementation"}.png')
            draw.text((8,305),f'Source rectangle: {rect}',fill='white')
            path=f'comparison/cells/{cell}.png';save(sheet,OUT/path);sheets.append({'id':cell,'path':path,'sourceRect':rect})
            thumbs.append(sheet.resize((396,248),Image.Resampling.LANCZOS))
    contact=Image.new('RGB',(396*4,248*6),'#14191c')
    for i,im in enumerate(thumbs):contact.paste(im,((i%4)*396,(i//4)*248))
    save(contact,OUT/'comparison/contact-sheet.png')
    overview=Image.new('RGB',(1536,1084),'#14191c')
    overview.paste(label(overlay(reference).resize((768,512)),'Reference'),(0,0));overview.paste(label(overlay(implementation).resize((768,512)),'Implementation'),(768,0))
    overview=overview.crop((0,0,1536,542));save(overview,OUT/'comparison/overview.png')
    components=[]
    for authored in spec.get('components',[]):
        comp=dict(authored);source=images.get(comp['sourceId'])
        if source is None: continue
        rect=comp['sourceRects'][0];piece=source.crop(tuple(rect))
        if comp.get('alphaNormalization')=='opaque-material-core':piece.putalpha(255)
        elif comp.get('alphaNormalization')=='export-alpha-restore':
            piece.putalpha(piece.getchannel('A').point(lambda a: 0 if a<=8 else (255 if a>=248 else a)))
        if comp.get('fitCanvas'):
            target=comp['fitCanvas'];margin=comp.get('fitMargin',4);available=target-2*margin
            ratio=min(available/piece.width,available/piece.height);size=(round(piece.width*ratio),round(piece.height*ratio))
            if comp.get('alphaNormalization')=='opaque-material-core':size=(target,target)
            piece=piece.resize(size,Image.Resampling.LANCZOS);canvas=Image.new('RGBA',(target,target));offset=((target-size[0])//2,(target-size[1])//2);canvas.alpha_composite(piece,offset);piece=canvas
            comp['derivedTransform']={'resizedTo':list(size),'canvasOffset':list(offset),'resampling':'Lanczos','note':'Normalized generated module; not literal original-source pixels'}
        # Alpha can be provided by the generator or an explicit source-derived mask.
        if comp.get('alphaMask'):
            mask=Image.open(ROOT/comp['alphaMask']).convert('L');piece.putalpha(mask)
        save(piece,OUT/comp['path']);comp['nativeSize']=list(piece.size);comp['sha256']=sha(OUT/comp['path']);components.append(comp)
    if components:
        sheet=Image.new('RGB',(256*6,170*4),'#172126');draw=ImageDraw.Draw(sheet)
        for i,comp in enumerate(components):
            x=(i%6)*256;y=(i//6)*170;im=Image.open(OUT/comp['path']).convert('RGBA');sheet.paste(im,(x+64,y+4),im);draw.text((x+8,y+140),comp['id'],fill='white')
        save(sheet,OUT/'components/contact-sheet.png')
    for assembly in spec.get('assemblies',[]):
        layers=[]
        for item in assembly['placements']:
            comp=next(c for c in components if c['id']==item['componentId']);im=Image.open(OUT/comp['path']).convert('RGBA')
            layers.append((comp['id'],im,item['position']))
        merged=Image.new('RGBA',tuple(assembly['size']))
        for name,im,pos in layers: merged.alpha_composite(im,tuple(pos))
        save(merged,OUT/assembly['path']);write_ora(OUT/assembly['oraPath'],assembly['size'],layers,merged)
    environment=build_environment(spec,images)
    expansionPath=OUT/'expansion/manifest.json'
    expansion=json.loads(expansionPath.read_text()) if expansionPath.exists() else None
    if expansion:
        components.extend(expansion.get('components',[]))
        for source in expansion.get('sources',[]):
            if source['id'] not in sources:spec['sources'].append(source)
    coveragePath=ROOT/'Docs/MapGridPass/component-coverage.json'
    coverage=json.loads(coveragePath.read_text()) if coveragePath.exists() else None
    manifest={**spec,'components':components,'environmentReconstruction':environment,'expansion':expansion,'componentCoverage':coverage,'reusableComponentCount':len(components),'componentCounts':{'starterAuthoredDesigns':len(spec['components']),'expansionAuthoredDesigns':expansion.get('counts',{}).get('authoredDesigns',0) if expansion else 0,'derivedVisibleParts':expansion.get('counts',{}).get('derivedVisibleParts',0) if expansion else 0,'totalExports':len(components)},'comparison':{'overview':'comparison/overview.png','contactSheet':'comparison/contact-sheet.png','cellSheets':sheets,'audit':audit,'pixelPolicy':'Original comparisons are exact crops; lines and labels appear on review sheets only.'}}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    package()
    print(f'{len(sheets)} cell sheets, 192 source subcell crops, {len(components)} components; {OUT}')

def package():
    # Ship authored inputs beside the evidence so extraction coordinates and decisions travel with the kit.
    for name in ['component-spec.json','comparison.json','component-coverage.json','expansion-spec.json','README.md','AUDIT.md','QA.md']:
        authored=ROOT/'Docs/MapGridPass'/name
        if authored.exists():
            destination=OUT/'authored'/name;destination.parent.mkdir(parents=True,exist_ok=True);destination.write_bytes(authored.read_bytes())
    (OUT/'authored/build_map_grid_pack.py').write_bytes(Path(__file__).read_bytes())
    for tool in ['extract_map_expansion.py','test_map_grid_pack.py']:
        sourceTool=ROOT/'Tools'/tool
        if sourceTool.exists():(OUT/'authored'/tool).write_bytes(sourceTool.read_bytes())
    members=[{'file':str(p.relative_to(OUT)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(OUT.rglob('*')) if p.is_file() and p.name not in ['map-grid-pass.zip','package-manifest.json']]
    (OUT/'package-manifest.json').write_text(json.dumps({'schemaVersion':1,'members':members},indent=2)+'\n')
    archivePath=OUT/'map-grid-pass.zip';temporaryArchive=OUT.parent/'map-grid-pass.building.zip'
    with zipfile.ZipFile(temporaryArchive,'w',zipfile.ZIP_DEFLATED) as archive:
        for p in sorted(OUT.rglob('*')):
            if p.is_file() and p.name!='map-grid-pass.zip':
                info=zipfile.ZipInfo(str(p.relative_to(OUT)),date_time=(2026,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16;archive.writestr(info,p.read_bytes())
    temporaryArchive.replace(archivePath)

def build_environment(spec,images):
    config=spec.get('environmentReconstruction',{})
    if config.get('cleanPlateSourceId') not in images:return config
    original_manifest=ROOT/config['sourceManifest'];old=json.loads(original_manifest.read_text());base=original_manifest.parent
    plate=images[config['cleanPlateSourceId']]
    if plate.size!=(1536,1024):raise ValueError('Clean plate must match reference canvas exactly')
    visible=Image.new('RGBA',plate.size);groups={};refs=[]
    for layer in old['layers']:
        if layer['category'] not in config['includeCategories'] or not layer.get('file'):continue
        im=Image.open(base/layer['file']).convert('RGBA');pos=layer['offset']
        visible.alpha_composite(im,tuple(pos))
        group=groups.setdefault(layer['category'],Image.new('RGBA',plate.size));group.alpha_composite(im,tuple(pos))
        refs.append({'id':layer['id'],'file':str((base/layer['file']).relative_to(ROOT)),'sha256':sha(base/layer['file']),'position':pos,'category':layer['category'],'provenance':'original-visible'})
    # Excluded dynamic silhouettes need a conservative boundary margin: original masks
    # partition source pixels but leave anti-aliased contours inside adjacent floor masks.
    excluded=Image.new('L',plate.size)
    for layer in old['layers']:
        if layer['category'] in config['includeCategories'] or not layer.get('file'):continue
        im=Image.open(base/layer['file']).convert('RGBA');pos=layer['offset'];local=Image.new('L',plate.size);local.paste(im.getchannel('A'),tuple(pos));excluded=ImageChops.lighter(excluded,local)
    excluded=excluded.filter(ImageFilter.MaxFilter(7))
    # Actor footprints use tight authored bounds plus three pixels where mask contours
    # contaminate adjacent environment fragments. This is inferred boundary repair.
    repair=Image.new('L',plate.size);rd=ImageDraw.Draw(repair)
    for layer in old['layers']:
        if layer['category']!='actor-body' or not layer.get('file'):continue
        x,y=layer['offset'];w,h=layer['size'];rd.rectangle((x-3,y-3,x+w+2,y+h+2),fill=255)
    excluded=ImageChops.lighter(excluded,repair)
    save(repair,OUT/'reconstruction/boundary-repair-mask.png')
    save(excluded,OUT/'reconstruction/dynamic-exclusion-mask.png')
    for name,group in groups.items(): group.putalpha(ImageChops.subtract(group.getchannel('A'),excluded))
    visible.putalpha(ImageChops.subtract(visible.getchannel('A'),excluded))
    alpha=visible.getchannel('A');hidden=ImageChops.invert(alpha);inferred=plate.copy();inferred.putalpha(hidden)
    merged=inferred.copy();merged.alpha_composite(visible)
    save(visible,OUT/'reconstruction/original-visible-environment.png');save(hidden,OUT/'reconstruction/inferred-region-mask.png');save(inferred,OUT/'reconstruction/inferred-environment-patches.png');save(merged,OUT/'reconstruction/clean-environment.png')
    layers=[('INFERRED environment under occlusions',inferred,[0,0])]+[(f'ORIGINAL visible {name}',im,[0,0]) for name,im in groups.items()]
    write_ora(OUT/'reconstruction/clean-environment.ora',plate.size,layers,merged)
    examples=[]
    for name,rect in [('carl-and-path',[448,400,752,568]),('target-and-speech',[736,384,1008,568]),('lower-hud',[0,736,640,1024]),('objective',[0,0,320,112])]:
        a=images['reference'].crop(rect);b=merged.crop(rect);sheet=Image.new('RGB',(a.width*2,a.height+30),'#14191c');sheet.paste(label(a,name+' BEFORE'),(0,0));sheet.paste(label(b,'AFTER: inferred below original visible'),(a.width,0));path=f'reconstruction/examples/{name}.png';save(sheet,OUT/path);examples.append({'id':name,'sourceRect':rect,'path':path})
    recipe={**config,'sourceManifestSha256':sha(original_manifest),'dynamicBoundaryMarginPixels':3,'boundaryRepairMask':'reconstruction/boundary-repair-mask.png','boundaryRepairRule':'actor-body authored tight bounding boxes plus3pixels; inferred to remove source-mask contour contamination','dynamicExclusionMask':'reconstruction/dynamic-exclusion-mask.png','originalLayers':refs,'inferredMask':'reconstruction/inferred-region-mask.png','originalVisible':'reconstruction/original-visible-environment.png','inferredPatches':'reconstruction/inferred-environment-patches.png','output':'reconstruction/clean-environment.png','ora':'reconstruction/clean-environment.ora','examples':examples,'reusableComponent':False,'provenance':'Original visible environment masks preserved; generated clean-plate pixels only in uncovered regions. Hidden original environment cannot be recovered.'}
    (OUT/'reconstruction/environment-recipe.json').write_text(json.dumps(recipe,indent=2)+'\n')
    return recipe

def write_ora(path,size,layers,merged):
    import xml.etree.ElementTree as ET
    root=ET.Element('image',{'w':str(size[0]),'h':str(size[1]),'name':'Map component assembly'});stack=ET.SubElement(root,'stack')
    with zipfile.ZipFile(path,'w',zipfile.ZIP_DEFLATED) as z:
        def put(name,data):
            info=zipfile.ZipInfo(name,date_time=(2026,1,1,0,0,0));info.compress_type=zipfile.ZIP_DEFLATED;info.external_attr=0o644<<16;z.writestr(info,data)
        put('mimetype','image/openraster')
        for i,(name,im,pos) in reversed(list(enumerate(layers))):
            src=f'data/layer{i:03}.png';buf=io.BytesIO();im.save(buf,format='PNG');put(src,buf.getvalue())
            ET.SubElement(stack,'layer',{'name':name,'src':src,'x':str(pos[0]),'y':str(pos[1]),'opacity':'1.0','visibility':'visible','composite-op':'svg:src-over'})
        put('stack.xml',ET.tostring(root));buf=io.BytesIO();merged.save(buf,format='PNG');put('mergedimage.png',buf.getvalue())
if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--package-only',action='store_true');args=parser.parse_args()
    package() if args.package_only else build()
