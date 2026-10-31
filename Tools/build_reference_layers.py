#!/usr/bin/env python3
"""Build native-coordinate editable reference layers; replay without original inputs."""
import argparse, hashlib, io, json, shutil, zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
from PIL import Image, ImageChops, ImageDraw
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'Web/wwwroot/assets/reference-layers'
def sha(p): return hashlib.sha256(p.read_bytes()).hexdigest()
def save(im,p): p.parent.mkdir(parents=True,exist_ok=True);im.save(p)
def zip_member(archive,name,data,compression=zipfile.ZIP_DEFLATED):
    info=zipfile.ZipInfo(str(name),(2026,1,1,0,0,0));info.compress_type=compression;info.external_attr=0o100644<<16
    archive.writestr(info,data)

def compose(scene,base,clean=False,hidden=()):
    im=Image.new('RGBA',tuple(scene['canvas']))
    for layer in sorted(scene['layers'],key=lambda x:x['z']):
        if layer['group'] in hidden or (clean and not layer['cleanVisible']):continue
        if layer.get('visibilityDependency')=='all-dynamic-context' and set(hidden)&{'actors','props','world-effects','hud'}:continue
        im.alpha_composite(Image.open(base/layer['file']).convert('RGBA'),tuple(layer['offset']))
    return im

def build():
    base=ROOT/'Web/wwwroot/assets/concept-reconstruction'; old=json.loads((base/'manifest.json').read_text())
    recon=ROOT/'Web/wwwroot/assets/map-grid-pass/reconstruction'; recipe=json.loads((recon/'environment-recipe.json').read_text())
    source=ROOT/old['source'];ref=Image.open(source).convert('RGBA');size=ref.size
    OUT.mkdir(parents=True,exist_ok=True)
    groups=[{'id':x,'label':x.replace('-',' ').title(),'dynamic':x in ('props','actors','world-effects','hud','context-restoration')} for x in ['underpainting','ground','water','architecture','pipes','machinery','props','actors','world-effects','hud','context-restoration']]
    scene={'schemaVersion':1,'canvas':list(size),'coordinateSystem':'native reference pixels; top-left origin; no scale, rotation or snapping','source':old['source'],'sourceSha256':sha(source),'groups':groups,'layers':[],'provenance':'Existing source component masks imported at original pixel offsets. Generated underpainting is inferred, not recovered source art. No new reusable tile designs are claimed.','comparisonOnly':['original-reference.png'],'cleanMode':'Render only cleanVisible layers; context restorations are hidden with dynamics.','sourceManifestSha256':sha(base/'manifest.json')}
    def emit(im,identifier,group,offset,kind,clean,source_ref,extra=None):
        bbox=im.getbbox()
        if not bbox:return
        x,y=offset; im=im.crop(bbox);x+=bbox[0];y+=bbox[1]
        p=OUT/'layers'/f'{identifier}.png';save(im,p)
        layer={'id':identifier,'group':group,'file':str(p.relative_to(OUT)),'offset':[x,y],'size':list(im.size),'anchor':[0,0],'z':len(scene['layers']),'kind':kind,'cleanVisible':clean,'sourceRef':source_ref,'sha256':sha(p)}
        if extra:layer.update(extra)
        scene['layers'].append(layer)
    under=Image.open(recon/'inferred-environment-patches.png').convert('RGBA')
    for row in range(4):
        for col in range(6):
            emit(under.crop((col*256,row*256,(col+1)*256,(row+1)*256)),f'underpaint-{chr(65+col)}{row+1}','underpainting',(col*256,row*256),'inferred-underpaint',True,{'file':str((recon/'inferred-environment-patches.png').relative_to(ROOT)),'sha256':sha(recon/'inferred-environment-patches.png')},{'note':'Review-region patch of inferred clean plate; not a reusable authored tile.'})
    exclusion=Image.open(recon/'dynamic-exclusion-mask.png').convert('L');include=set(recipe['includeCategories']);pending=[]
    def group(cat):
        if cat in ('floor-slab','void-rock','floor-reflection'):return 'ground'
        if cat in ('water-channel','waterfall'):return 'water'
        if cat.startswith('pipe-'):return 'pipes'
        if cat in ('machine-panel','grate','water-outlet-frame'):return 'machinery'
        if cat in ('crate','prop'):return 'props'
        if cat.startswith('actor-'):return 'actors'
        if cat.startswith('ui-') or cat=='text':return 'hud'
        if cat in include:return 'architecture'
        return 'world-effects'
    for layer in old['layers']:
        if not layer.get('file'):continue
        im=Image.open(base/layer['file']).convert('RGBA');x,y=layer['offset'];g=group(layer['category'])
        sr={'id':layer['id'],'file':str((base/layer['file']).relative_to(ROOT)),'sha256':sha(base/layer['file'])}
        extra={'sourceCategory':layer['category'],'sourceBounds':[x,y,*layer['size']],'sourceZ':layer['z'],'sourceAnchor':[0,0]}
        if layer['category'] in include:
            mask=exclusion.crop((x,y,x+im.width,y+im.height));clipped=im.copy();clipped.putalpha(ImageChops.subtract(im.getchannel('A'),mask))
            emit(clipped,layer['id'],g,(x,y),'original-visible',True,sr,extra)
            context=im.copy();context.putalpha(ImageChops.darker(im.getchannel('A'),mask))
            if context.getbbox():pending.append((context,layer['id']+'--context',(x,y),sr,extra))
        else:pending.append((im,layer['id'],(x,y),sr,{**extra,'dynamicGroup':g}))
    for im,identifier,pos,sr,extra in pending:
        dynamic=extra.get('dynamicGroup');g=dynamic or 'context-restoration'
        emit(im,identifier,g,pos,'original-visible' if dynamic else 'context-restoration',False,sr,{**extra,'visibilityDependency':dynamic or 'all-dynamic-context','unassignedContext':None if dynamic else 'Source boundary restoration spans silhouettes; hidden in clean mode and grouped as explicit exact-view context.','note':'Visible source component' if dynamic else 'Source boundary pixels excluded from clean environment; restore only in exact reference view.'})
    scene['originalFragments']=[{'id':l['id'],'file':l.get('file'),'offset':l.get('offset'),'size':l.get('size'),'visiblePixels':l.get('visiblePixels',0),'sha256':l.get('componentSha256')} for l in old['layers']]
    # Semantic groups have disjoint source pixels; sorting makes them editable ORA stacks.
    order={g['id']:i for i,g in enumerate(groups)}
    scene['layers'].sort(key=lambda l:(order[l['group']],l['z']))
    for z,l in enumerate(scene['layers']):l['z']=z
    exact=compose(scene,OUT);clean=compose(scene,OUT,True)
    diff=ImageChops.difference(ref,exact);rgb=diff.convert('RGB');changed=sum(1 for px in diff.getdata() if px!=(0,0,0,0))
    scene['validation']={'changedRgbaPixels':changed,'maxChannelDifference':max(max(e) for e in diff.getextrema()),'sourceFragmentCount':sum(bool(l.get('file')) for l in old['layers']),'sourceAnnotationCount':len(old['layers']),'exportedLayerCount':len(scene['layers'])}
    if changed:raise ValueError(f'Exact replay differs at {changed} pixels')
    for name,im in [('original-reference.png',ref),('reconstructed.png',exact),('diff.png',rgb),('clean-map.png',clean)]:save(im,OUT/name)
    pair=Image.new('RGBA',(size[0]*2,size[1]));pair.paste(ref,(0,0));pair.paste(exact,(size[0],0));save(pair,OUT/'side-by-side.png')
    # Contact sheet separates semantic strata without changing layer coordinates.
    thumb=(384,256);sheet=Image.new('RGB',(384*4,286*3),'#131b25');d=ImageDraw.Draw(sheet)
    for i,g in enumerate(groups):
        view=compose(scene,OUT,hidden=[q['id'] for q in groups if q!=g]);view.thumbnail(thumb);x=(i%4)*384;y=(i//4)*286;sheet.paste(view,(x,y+26),view);d.text((x+8,y+7),g['label'],fill='white')
    save(sheet,OUT/'exploded-layer.png')
    scene['previewGroups']=[]
    for g in groups:
        for clean_visible in (True,False):
            selected=[l for l in scene['layers'] if l['group']==g['id'] and l['cleanVisible']==clean_visible]
            if not selected:continue
            cache=Image.new('RGBA',size)
            for l in selected:cache.alpha_composite(Image.open(OUT/l['file']).convert('RGBA'),tuple(l['offset']))
            file='group-previews/'+g['id']+('-clean' if clean_visible else '-dynamic')+'.png';save(cache,OUT/file)
            scene['previewGroups'].append({'group':g['id'],'file':file,'offset':[0,0],'cleanVisible':clean_visible,'z':selected[0]['z']})
    for p in [OUT/'manifest.json',OUT/'scene.json',ROOT/'Docs/ReferenceLayers/scene.json']:p.write_text(json.dumps(scene,indent=2)+'\n')
    root=ET.Element('image',w=str(size[0]),h=str(size[1]),name='Native reference reconstruction',version='0.0.3');stack=ET.SubElement(root,'stack')
    with zipfile.ZipFile(OUT/'reference-layers.ora','w') as z:
        zip_member(z,'mimetype',b'image/openraster',zipfile.ZIP_STORED)
        for g in reversed(groups):
            gs=ET.SubElement(stack,'stack',id=g['id'],name=g['label'],opacity='1.0',visibility='visible',**{'composite-op':'svg:src-over'})
            for l in reversed([l for l in scene['layers'] if l['group']==g['id']]):
                ET.SubElement(gs,'layer',name=l['id'],src=l['file'],x=str(l['offset'][0]),y=str(l['offset'][1]),opacity='1.0',visibility='visible',**{'composite-op':'svg:src-over'});zip_member(z,l['file'],(OUT/l['file']).read_bytes())
        zip_member(z,'stack.xml',ET.tostring(root));zip_member(z,'mergedimage.png',(OUT/'reconstructed.png').read_bytes())
    shutil.copyfile(__file__,OUT/'reassemble.py')
    template=ROOT/'Tools/reference_layer_viewer.html'
    if template.exists():
        (OUT/'viewer.html').write_text(template.read_text().replace('<!--REFERENCE_LAYERS_DATA-->','<script>window.REFERENCE_LAYERS='+json.dumps(scene)+'</script>'))
    for name in ('README.md','QA.md'):
        doc=ROOT/'Docs/ReferenceLayers'/name
        if doc.exists():shutil.copyfile(doc,OUT/name)
    for name in ('build_reference_layers.py','test_reference_layers.py','reference_layer_viewer.html'):
        target=OUT/'tools'/name;target.parent.mkdir(exist_ok=True);shutil.copyfile(ROOT/'Tools'/name,target)
    target=OUT/'recipe/scene.json';target.parent.mkdir(exist_ok=True);shutil.copyfile(ROOT/'Docs/ReferenceLayers/scene.json',target)
    inventory=[{'file':str(p.relative_to(OUT)),'bytes':p.stat().st_size,'sha256':sha(p)} for p in sorted(OUT.rglob('*')) if p.is_file() and p.name not in ('reference-layers.zip','package-manifest.json')]
    (OUT/'package-manifest.json').write_text(json.dumps({'schemaVersion':1,'members':inventory,'note':'Inventory excludes this self-referential inventory file and containing ZIP.'},indent=2)+'\n')
    with zipfile.ZipFile(OUT/'reference-layers.zip','w',zipfile.ZIP_DEFLATED) as z:
        for p in sorted(OUT.rglob('*')):
            if p.is_file() and p.name!='reference-layers.zip':zip_member(z,p.relative_to(OUT),p.read_bytes())
    print(json.dumps(scene['validation']))
if __name__=='__main__':
    p=argparse.ArgumentParser();p.add_argument('--scene',type=Path);p.add_argument('--output',type=Path);p.add_argument('--clean',action='store_true');p.add_argument('--hide',action='append',default=[]);a=p.parse_args()
    if a.scene:save(compose(json.loads(a.scene.read_text()),a.scene.parent,a.clean,a.hide),a.output or a.scene.parent/'replayed.png')
    else:build()
