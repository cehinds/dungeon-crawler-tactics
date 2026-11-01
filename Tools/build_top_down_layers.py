#!/usr/bin/env python3
"""Validate and package genuine source masks; keep exact and inferred modes separate."""
import argparse
import bisect
import hashlib
import json
import re
import shutil
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'Web/wwwroot/assets/top-down-layer-kit'
DOCS=ROOT/'Docs/TopDownLayerKit'
VIEWER=ROOT/'Web/wwwroot/top-down-layers.html'


def digest(path):return hashlib.sha256(path.read_bytes()).hexdigest()


def write_json(path,data):
    path.parent.mkdir(parents=True,exist_ok=True)
    path.write_text(json.dumps(data,indent=2,ensure_ascii=False)+'\n')


def resolve(path,directory):
    candidate=Path(path)
    return candidate if candidate.is_absolute() else directory/candidate


def boundaries(extent):return [round(i*extent/14) for i in range(15)]


def address(x,y,width,height):
    result=[]
    for value,extent in ((x,width),(y,height)):
        major=boundaries(extent);index=max(0,min(13,bisect.bisect_right(major,value)-1))
        sub=[major[index]+round((major[index+1]-major[index])*j/3) for j in range(4)]
        local=max(0,min(2,bisect.bisect_right(sub,value)-1));result.append((index,local))
    return chr(65+result[0][0])+str(result[1][0]+1)+'.'+chr(97+result[0][1])+str(result[1][1]+1)


def differences(a,b):
    a=a.convert('RGBA');b=b.convert('RGBA')
    if a.size!=b.size:raise ValueError('Image size mismatch')
    raw=ImageChops.difference(a,b);channels=raw.split();changed=ImageChops.lighter(ImageChops.lighter(channels[0],channels[1]),ImageChops.lighter(channels[2],channels[3]))
    count=sum(changed.histogram()[1:]);mae=sum(value*count for channel in channels for value,count in enumerate(channel.histogram()))/(a.width*a.height*4)
    heat=Image.new('RGBA',a.size,(0,0,0,255));heat.paste((255,70,85,255),mask=changed.point(lambda value:255 if value else 0))
    return {'differentPixels':count,'totalPixels':a.width*a.height,'meanAbsoluteRgbaError':mae},heat


def save_image(image,path):
    path.parent.mkdir(parents=True,exist_ok=True);image.save(path)
    return {'path':str(path.relative_to(OUT)),'sha256':digest(path),'size':list(image.size)}


def archive_output(path):
    return path.name=='top-down-layer-kit.zip' or '.zip.part-' in path.name or path.name.endswith('.zip.parts.json') or path.name=='assemble_archive_parts.py'


def category_layers(components):
    return [{'category':category,'componentIds':[c['id'] for c in components if c['category']==category],'count':sum(c['category']==category for c in components)} for category in sorted({c['category'] for c in components})]


def copy_asset(source,target):
    target.parent.mkdir(parents=True,exist_ok=True);shutil.copyfile(source,target)
    return {'path':str(target.relative_to(OUT)),'sha256':digest(target)}


def preserve_prior():
    target=OUT/'baseline.json'
    if target.exists():
        for path,sha in json.loads(target.read_text()).items():
            if digest(ROOT/path)!=sha:raise ValueError('Prior art changed: '+path)
    else:write_json(target,{str(p.relative_to(ROOT)):digest(p) for p in sorted((ROOT/'Web/wwwroot/assets').rglob('*')) if p.is_file() and OUT not in p.parents})


def validate_scene(input_path,catalog):
    data=json.loads(input_path.read_text());scene_id=data['sceneId']
    if scene_id not in catalog:raise ValueError('Unknown scene ID '+scene_id)
    if data['grid']!={'major':14,'sub':3}:raise ValueError('Expected14/3 grid')
    directory=input_path.parent;src=resolve(data['source']['path'],directory)
    if digest(src)!=data['source']['sha256']:raise ValueError('Source hash mismatch '+scene_id)
    source=Image.open(src).convert('RGBA');w,h=source.size
    if [w,h]!=[data['source']['width'],data['source']['height']]:raise ValueError('Source native size mismatch')
    approved=ROOT/'Web/wwwroot/assets/floor-one-concepts-top-down'/catalog[scene_id]['path']
    if digest(src)!=digest(approved):raise ValueError('Source is not approved top-down panel '+scene_id)
    target=OUT/'scenes'/scene_id
    if target.exists():shutil.rmtree(target)
    target.mkdir(parents=True,exist_ok=True)
    original=save_image(source,target/'original.png');union=Image.new('L',source.size);components=[];largest=0
    ids=set()
    for item in sorted(data['components'],key=lambda c:(c['z'],c['id'])):
        cid=item['id']
        if cid in ids or not re.fullmatch(r'[a-z0-9][a-z0-9_-]*',cid):raise ValueError('Invalid/duplicate componentID')
        ids.add(cid);mask=Image.open(resolve(item['mask'],directory)).convert('L')
        if mask.size!=source.size or set(mask.get_flattened_data())- {0,255}:raise ValueError('Mask must be native binary0/255 '+cid)
        box=mask.getbbox()
        if box is None:raise ValueError('Empty semantic mask '+cid)
        x,y,cw,ch=item['bounds']
        if [item['x'],item['y']]!=[x,y] or min(x,y)<0 or min(cw,ch)<=0 or x+cw>w or y+ch>h:raise ValueError('Invalid component bounds '+cid)
        if box[0]<x or box[1]<y or box[2]>x+cw or box[3]>y+ch:raise ValueError('Mask extends beyond crop '+cid)
        area=mask.histogram()[255];largest=max(largest,area/(w*h))
        if area/(w*h)>.8:raise ValueError('Giant source-image overlay is not a semantic component '+cid)
        crop_box=(x,y,x+cw,y+ch);pixels=source.crop(crop_box);alpha=mask.crop(crop_box);pixels.putalpha(alpha)
        supplied=Image.open(resolve(item['asset'],directory)).convert('RGBA')
        if supplied.size!=pixels.size or supplied.getchannel('A').tobytes()!=alpha.tobytes():raise ValueError('Crop alpha mismatch '+cid)
        visible=ImageChops.difference(supplied.convert('RGB'),pixels.convert('RGB'))
        if any(ImageChops.multiply(channel,alpha).getbbox() for channel in visible.split()):raise ValueError('Visible RGB changed '+cid)
        component={**item,'asset':save_image(pixels,target/'exact/components'/(cid+'.png')),'mask':save_image(mask,target/'exact/masks'/(cid+'.png')),'gridAddress':address(x,y,w,h),'inputGridAddress':item.get('gridAddress'),'bounds':[x,y,cw,ch],'visiblePixelCount':area}
        components.append(component);union=ImageChops.lighter(union,mask)
    if not components:raise ValueError('No semantic components')
    inferred=Image.open(resolve(data['underlay']['path'],directory)).convert('RGBA')
    if inferred.size!=source.size:raise ValueError('Exact underlay must match native dimensions')
    base=Image.composite(inferred,source,union);base_asset=save_image(base,target/'exact/base.png')
    union_asset=save_image(union,target/'exact/union-mask.png');rebuilt=base.copy()
    for item in components:rebuilt.alpha_composite(Image.open(OUT/item['asset']['path']).convert('RGBA'),(item['x'],item['y']))
    metrics,heat=differences(source,rebuilt)
    if metrics['differentPixels']:raise ValueError('Exact reconstruction is not exact '+scene_id)
    under_metrics,_=differences(source,base)
    exact={'base':base_asset,'baseProvenance':data['underlay']['provenance'],'unionMask':union_asset,'components':components,'reconstructed':save_image(rebuilt,target/'exact/reconstructed.png'),'difference':save_image(heat,target/'exact/difference.png'),'metrics':{**metrics,'sourcePixelsAssignedToComponents':union.histogram()[255],'sourcePixelsRemainingVisible':w*h-union.histogram()[255],'baseDifferentPixels':under_metrics['differentPixels'],'largestComponentFraction':largest},'categoryLayers':category_layers(components),'categoryLayerCount':len({c['category'] for c in components}),'claim':'Visible source decomposition only; zero difference is not a clean-base or completed-object quality claim.'}
    result={'schemaVersion':1,'id':scene_id,'name':catalog[scene_id].get('name',scene_id),'order':catalog[scene_id]['order'],'size':[w,h],'source':{**original,'originalInput':str(src),'originalSha256':digest(src)},'grid':{'major':14,'sub':3,'xBoundaries':boundaries(w),'yBoundaries':boundaries(h),'addressRule':'Component top-left anchor uses rounded major boundaries, then local thirds.'},'exact':exact,'limitations':data.get('limitations',data.get('limits',[])),'reviewStatus':data.get('reviewStatus','component silhouettes and completed-kit quality require visual review')}
    reusable=data.get('reusable')
    if reusable and reusable.get('base'):
        plate=Image.open(resolve(reusable['base']['path'],directory)).convert('RGBA')
        if plate.size!=source.size:raise ValueError('Reusable plate must be native size')
        if differences(source,plate)[0]['differentPixels']==0:raise ValueError('Reusable base cannot be unchanged full source')
        reusable_base=save_image(plate,target/'reusable/base.png');new_components=[];seen=set();composition=plate.copy()
        for item in sorted(reusable.get('components',[]),key=lambda c:(c['z'],c['id'])):
            cid=item['id']
            if cid in seen:raise ValueError('Duplicate reusable component')
            seen.add(cid);asset_path=resolve(item['asset'],directory);pixels=Image.open(asset_path).convert('RGBA')
            if not pixels.getbbox():raise ValueError('Empty reusable component')
            if pixels.width==w and pixels.height==h and pixels.getchannel('A').getextrema()[0]==255:raise ValueError('Opaque full-source-sized component rejected')
            component={**item,'asset':save_image(pixels,target/'reusable/components'/(cid+'.png')),'gridAddress':address(item['x'],item['y'],w,h)}
            new_components.append(component);composition.alpha_composite(pixels,(item['x'],item['y']))
        reuse_metrics,reuse_heat=differences(source,composition)
        materials=[]
        for index,material in enumerate(reusable.get('materials',reusable.get('tiles',[]))):
            material_path=material.get('asset',material.get('path'))
            if material_path:
                path=resolve(material_path,directory)
                materials.append({**material,'asset':copy_asset(path,target/'reusable/materials'/(str(index)+'-'+path.name))})
        result['reusable']={'materials':materials,'base':reusable_base,'baseProvenance':reusable['base']['provenance'],'components':new_components,'reconstructed':save_image(composition,target/'reusable/reconstructed.png'),'difference':save_image(reuse_heat,target/'reusable/difference.png'),'metrics':reuse_metrics,'limitations':reusable.get('limitations',[]),'categoryLayers':category_layers(new_components),'categoryLayerCount':len({c['category'] for c in new_components}),'claim':'Inferred reusable interpretation; completed surfaces/objects are not recovered hidden source pixels and are not claimed pixel-exact.'}
    modules=[]
    for index,module in enumerate(data.get('libraryModules',[])+data.get('textureSamples',[])):
        if isinstance(module,dict) and module.get('asset'):
            module_path=resolve(module['asset'],directory)
            modules.append({**module,'asset':copy_asset(module_path,target/'library'/f'{index}-{module_path.name}')})
    result['libraryModules']=modules
    result['authorManifest']={'sha256':digest(input_path),'originalPath':str(input_path)}
    write_json(target/'scene.json',result);result['scenePath']=str((target/'scene.json').relative_to(OUT));return result


def build(inputs,require_all=False):
    catalog_data=json.loads((ROOT/'Web/wwwroot/assets/floor-one-concepts-top-down/manifest.json').read_text());catalog={p['id']:p for p in catalog_data['panels']}
    labels={p['id']:p['name'] for p in json.loads((ROOT/'Docs/FloorOneConceptsTopDown/coverage.json').read_text())['panels']}
    for scene_id in catalog:catalog[scene_id]['name']=labels[scene_id]
    OUT.mkdir(parents=True,exist_ok=True);preserve_prior();scenes=[]
    for path in inputs:scenes.append(validate_scene(path,catalog))
    if len({s['id'] for s in scenes})!=len(scenes):raise ValueError('Duplicate scene inputs')
    if require_all and len(scenes)!=36:raise ValueError('All36 scenes required')
    scenes.sort(key=lambda s:s['order']);manifest={'schemaVersion':1,'title':'Top-down layer kit','scope':'Source-derived semantic components and separate inferred reusable interpretations. Exact pixel metrics cover full source decomposition, not reusable asset quality.','scenes':scenes,'coverage':[{'id':p['id'],'name':labels[p['id']],'order':p['order'],'built':p['id'] in {s['id'] for s in scenes}} for p in catalog_data['panels']]}
    write_json(OUT/'manifest.json',manifest)
    for name in ('README.md','coverage.json','schema.json'):
        if (DOCS/name).exists():shutil.copyfile(DOCS/name,OUT/name)
    tooling=OUT/'tools';tooling.mkdir(exist_ok=True);shutil.copyfile(Path(__file__),tooling/'build_top_down_layers.py')
    if (ROOT/'Tools/test_top_down_layers.py').exists():shutil.copyfile(ROOT/'Tools/test_top_down_layers.py',tooling/'test_top_down_layers.py')
    if (ROOT/'Tools/package_top_down_layers.py').exists():shutil.copyfile(ROOT/'Tools/package_top_down_layers.py',tooling/'package_top_down_layers.py')
    if VIEWER.exists():
        html=VIEWER.read_text();pattern=r'(<script id="scene-data" type="application/json">).*?(</script>)'
        html=re.sub(pattern,lambda m:m.group(1)+json.dumps(manifest,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')+m.group(2),html,flags=re.S);VIEWER.write_text(html)
        shutil.copyfile(VIEWER,OUT/'viewer.html')
    files=[p for p in sorted(OUT.rglob('*')) if p.is_file() and p.name!='package-manifest.json' and not archive_output(p)]
    write_json(OUT/'package-manifest.json',{'schemaVersion':1,'members':[{'file':str(p.relative_to(OUT)),'bytes':p.stat().st_size,'sha256':digest(p)} for p in files]})
    print(json.dumps({'scenes':len(scenes),'components':sum(len(s['exact']['components']) for s in scenes),'exactDifferentPixels':sum(s['exact']['metrics']['differentPixels'] for s in scenes),'reusableScenes':sum('reusable' in s for s in scenes)}))


if __name__=='__main__':
    parser=argparse.ArgumentParser();parser.add_argument('--scene',action='append',required=True);parser.add_argument('--require-all',action='store_true');args=parser.parse_args();build([Path(p).resolve() for p in args.scene],args.require_all)
