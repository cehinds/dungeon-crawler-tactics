#!/usr/bin/env python3
"""Export literal HUD fragments, widget previews and deterministic layered packs."""
import hashlib
import io
import json
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET
from PIL import Image, ImageDraw, ImageFont
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'Web/wwwroot/assets/hud-components'
SPEC = ROOT / 'Docs/HudComponents/spec.json'

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def save_json(path, data):
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False) + '\n')

def zip_write(z, name, data):
    entry = zipfile.ZipInfo(name, (1980, 1, 1, 0, 0, 0))
    entry.compress_type = zipfile.ZIP_DEFLATED
    entry.external_attr = 0o644 << 16
    z.writestr(entry, data)

def normalized(im):
    a = np.array(im.convert('RGBA')); a[a[:,:,3] == 0] = 0
    return a

def render(entries, size=(1536,1024)):
    im = Image.new('RGBA', size)
    for e in entries:
        im.alpha_composite(Image.open(OUT / e['file']).convert('RGBA'), tuple(e['offset']))
    return im

def font(size):
    return ImageFont.truetype('/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf', size)

def checker(size):
    im = Image.new('RGBA', size, '#17202e'); d = ImageDraw.Draw(im)
    for y in range(0,size[1],12):
        for x in range(0,size[0],12):
            if (x//12+y//12)%2: d.rectangle((x,y,x+11,y+11), fill='#202c3d')
    return im

def main():
    spec = json.loads(SPEC.read_text())
    source = ROOT / spec['source']
    origin = ROOT / spec['fragmentManifest']
    raw = json.loads(origin.read_text())
    selected = {i for g in spec['groups'] for i in g['layerIds']}
    by_id = {x['id']:x for x in raw['layers']}
    assert selected <= by_id.keys()
    for folder in ['raw','widgets','details','slices']:
        (OUT/folder).mkdir(parents=True,exist_ok=True)
    layers = []
    for original in raw['layers']:
        if original['id'] not in selected: continue
        e = dict(original)
        group = next(g for g in spec['groups'] if e['id'] in g['layerIds'])
        e['sourceParentId'] = e.get('parentId')
        e['parentId'] = group['id']; e['semanticRole'] = e['category']
        e['file'] = 'raw/'+e['id']+'.png'
        Image.open(origin.parent/original['file']).convert('RGBA').save(OUT/e['file'])
        e['sha256'] = sha(OUT/e['file'])
        e['bounds'] = e['offset']+e['size']; e['anchor'] = {'kind':'top-left','canvasPixels':e['offset']}
        layers.append(e)
    rebuilt = render(layers)
    rebuilt.save(OUT/'hud-rebuilt.png')
    Image.open(source).convert('RGBA').save(OUT/'hud-source.png')
    expected = normalized(Image.open(source)); actual = normalized(rebuilt)
    changed = int(np.any(expected!=actual,axis=2).sum())
    if changed: raise ValueError(f'HUD reconstruction differs at {changed} pixels')
    groups = []
    for group in spec['groups']:
        entries = [e for e in layers if e['id'] in group['layerIds']]
        im = render(entries); bounds = im.getbbox(); cropped = im.crop(bounds)
        file = 'widgets/'+group['id']+'.png'; cropped.save(OUT/file)
        g = dict(group, file=file, offset=list(bounds[:2]), size=list(cropped.size), bounds=[bounds[0],bounds[1],cropped.width,cropped.height],anchor={'kind':'top-left','canvasPixels':list(bounds[:2])})
        groups.append(g)
        for e in entries: e['offsetInParent'] = [e['offset'][0]-bounds[0],e['offset'][1]-bounds[1]]
        # Every raw fragment is shown at native scale, one readable labelled row.
        width = max(760, max(e['size'][0] for e in entries)+48)
        height = 72 + sum(max(56,e['size'][1]+44) for e in entries)
        sheet = checker((width,height)); d=ImageDraw.Draw(sheet)
        d.text((20,14),group['label']+' / individual source layers',font=font(20),fill='white')
        y=62
        for e in entries:
            d.text((20,y),e['id'],font=font(14),fill='#ffd878')
            sheet.alpha_composite(Image.open(OUT/e['file']), (20,y+23))
            y+=max(56,e['size'][1]+44)
        sheet.convert('RGB').save(OUT/'details'/f"{group['id']}.png")
    # Compact native-scale widget layout. Bottom panel is a full-width structural strip.
    overview = checker((1584,980)); d=ImageDraw.Draw(overview)
    d.text((24,18),'HUD COMPONENTS — original raster artwork',font=font(28),fill='white')
    d.text((24,58),'17 widget groups / 78 source layers / native scale',font=font(17),fill='#b8c6dc')
    x,y,row_h=24,104,0
    for g in groups:
        if g['id']=='bottom-panel': continue
        im=Image.open(OUT/g['file'])
        if x+im.width+24>1560: x=24;y+=row_h+48;row_h=0
        d.text((x,y),g['label'],font=font(16),fill='#ffd878')
        overview.alpha_composite(im,(x,y+28));x+=im.width+36;row_h=max(row_h,im.height+28)
    y+=row_h+50
    panel=next(g for g in groups if g['id']=='bottom-panel')
    d.text((24,y),'Bottom panel / structural frame and background only',font=font(17),fill='#ffd878')
    overview.alpha_composite(Image.open(OUT/panel['file']),(24,y+30))
    d.text((24,y+210),'Background holes preserve foreground ownership. All text is raster. Individual layers: details/.',font=font(16),fill='#b8c6dc')
    overview.crop((0,0,1584,min(980,y+250))).convert('RGB').save(OUT/'overview.png')
    slices=[]
    for id, margins in spec['nineSlice'].items():
        e=next(e for e in layers if e['id']==id); im=Image.open(OUT/e['file'])
        l,t,r,b=margins;xs=[0,l,im.width-r,im.width];ys=[0,t,im.height-b,im.height]
        pieces=[]
        for row in range(3):
            for col in range(3):
                box=[xs[col],ys[row],xs[col+1],ys[row+1]];file=f'slices/{id}-{row}-{col}.png'
                im.crop(box).save(OUT/file);pieces.append(dict(file=file,rect=box,row=row,column=col))
        guide = checker(im.size); guide.alpha_composite(im); gd = ImageDraw.Draw(guide)
        for xx in xs[1:-1]: gd.line((xx,0,xx,im.height-1), fill='#ff6c83')
        for yy in ys[1:-1]: gd.line((0,yy,im.width-1,yy), fill='#ff6c83')
        guide_file = f'slices/{id}-guide.png'; guide.save(OUT/guide_file)
        slices.append(dict(layerId=id,margins=margins,guide=guide_file,pieces=pieces,note='Derived native frame slices only. Center is transparent; no hidden panel invented.'))
    manifest=dict(schemaVersion=1,canvas=spec['canvas'],source=spec['source'],sourceSha256=sha(source),fragmentManifest=spec['fragmentManifest'],fragmentManifestSha256=sha(origin),representation='Visible source fragments; hidden pixels are absent.',limitations=spec['limitations'],groups=groups,layers=layers,nineSlice=slices,verification=dict(changedPixels=changed,maxChannelError=int(np.abs(expected.astype(int)-actual.astype(int)).max()),transparentRgbNormalized=True,normalizedRgbaSha256=hashlib.sha256(expected.tobytes()).hexdigest()),artifacts=dict(overview='overview.png',source='hud-source.png',rebuilt='hud-rebuilt.png',layered='hud-components.ora',archive='hud-components.zip'))
    save_json(OUT/'manifest.json',manifest)
    root=ET.Element('image',w='1536',h='1024',name='HUD source components',version='0.0.3');stack=ET.SubElement(root,'stack')
    with zipfile.ZipFile(OUT/'hud-components.ora','w') as z:
        zip_write(z,'mimetype',b'image/openraster')
        for g in reversed(groups):
            gs=ET.SubElement(stack,'stack',name=g['label'],opacity='1.0',visibility='visible', **{'composite-op':'svg:src-over'})
            for e in reversed([e for e in layers if e['parentId']==g['id']]):
                file='data/'+e['id']+'.png';zip_write(z,file,(OUT/e['file']).read_bytes())
                ET.SubElement(gs,'layer',name=e['id'],src=file,x=str(e['offset'][0]),y=str(e['offset'][1]),opacity='1.0',visibility='visible', **{'composite-op':'svg:src-over'})
        zip_write(z,'stack.xml',ET.tostring(root,encoding='utf-8',xml_declaration=True));zip_write(z,'mergedimage.png',(OUT/'hud-rebuilt.png').read_bytes())
    with zipfile.ZipFile(OUT/'hud-components.zip','w') as z:
        for path in sorted(OUT.rglob('*')):
            if path.is_file() and path.name!='hud-components.zip':zip_write(z,path.relative_to(OUT).as_posix(),path.read_bytes())
    print(f'Exported {len(layers)} fragments, {len(groups)} groups; changed RGBA pixels: {changed}')

if __name__ == '__main__':main()
