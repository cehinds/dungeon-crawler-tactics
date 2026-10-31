#!/usr/bin/env python3
"""Export the authored Broadcast Art crop manifest; Pillow, no image synthesis.

python3 Tools/build_broadcast_art.py
Sources are preserved under the ignored asset directory and AI-Art originals.
"""
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
DOC = ROOT / 'Docs/BroadcastArt'
OUT = ROOT / 'Web/wwwroot/assets/broadcast-kit'

def main():
    spec = json.loads((DOC / 'crops.json').read_text())
    OUT.mkdir(parents=True, exist_ok=True)
    assets = []
    previews = []
    for batch in spec['batches']:
        source = OUT / batch['source']
        sheet = Image.open(source).convert('RGBA')
        for item in batch['pieces']:
            crop = sheet.crop(item['crop'])
            tile = Image.new('RGBA', (128, 128))
            if item['layer'] == 'terrain':
                tile = crop.resize((128, 128), Image.Resampling.NEAREST)
                # Generated material tiles have near-opaque alpha; terrain must
                # cover its entire square rather than reveal a checker seam.
                tile.putalpha(255)
            elif item['layer'] == 'wall' or item['adjacency'] == 'road-network-study':
                # Ignore faint generated glow when finding structural footprint.
                box = crop.getchannel('A').point(lambda a:255 if a>=200 else 0).getbbox()
                if box:
                    l,t,r,b=box
                    crop = crop.crop((l+2,t+2,r-2,b-2))
                    if item['id'].endswith('wall-ew'):
                        tile.alpha_composite(crop.resize((128,64),Image.Resampling.NEAREST),(0,32))
                    elif item['id'].endswith('wall-ns'):
                        tile.alpha_composite(crop.resize((64,128),Image.Resampling.NEAREST),(32,0))
                    else:
                        tile = crop.resize((128, 128), Image.Resampling.NEAREST)
            else:
                box = crop.getbbox()
                if box:
                    crop = crop.crop(box)
                    crop.thumbnail((112, 112), Image.Resampling.NEAREST)
                    tile.alpha_composite(crop, ((128-crop.width)//2, 120-crop.height))
            path = OUT / 'pieces' / (item['id'] + '.png')
            path.parent.mkdir(exist_ok=True)
            tile.save(path)
            alpha = tile.getchannel('A')
            asset = {k:v for k,v in item.items() if k != 'crop'}
            asset.update({'src':'pieces/'+path.name, 'tileSize':[128,128],
                          'anchor':[64,128], 'authoredRotations':[0],
                          'source':batch['source'], 'sourceCrop':item['crop'],
                          'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),
                          'alphaExtrema':list(alpha.getextrema()), 'contentBounds':tile.getbbox()})
            assets.append(asset)
            previews.append((item['id'],tile))
    # Canonical geometry is composed from real generated wall raster segments.
    # Source decorative junctions remain available as studies above.
    source_tiles={name:tile for name,tile in previews}
    ew=source_tiles['broadcast-combat-wall-ew'].crop((0,32,128,96))
    ew.putalpha(255)
    ns=ew.transpose(Image.Transpose.ROTATE_90)
    center=source_tiles['broadcast-combat-wall-cross'].crop((32,32,96,96))
    center.putalpha(255)
    connections={'ew':'EW','ns':'NS','corner-ne':'NE','corner-nw':'NW','corner-se':'SE','corner-sw':'SW','t-new':'NEW','t-nes':'NES','t-nsw':'NSW','t-esw':'ESW','cross':'NESW'}
    for name,dirs in list(connections.items())+[('door-open','EW'),('door-closed','EW')]:
        tile=Image.new('RGBA',(128,128))
        for side in dirs:
            if side=='N':tile.alpha_composite(ns.crop((0,0,64,64)),(32,0))
            if side=='S':tile.alpha_composite(ns.crop((0,64,64,128)),(32,64))
            if side=='W':tile.alpha_composite(ew.crop((0,0,64,64)),(0,32))
            if side=='E':tile.alpha_composite(ew.crop((64,0,128,64)),(64,32))
        tile.alpha_composite(center,(32,32))
        if name.startswith('door-'):
            # Clear the central passage and place the generated frame inside
            # lateral endcaps. Only the caps touch east/west cell boundaries.
            tile.paste((0,0,0,0),(32,0,96,128))
            door=source_tiles['broadcast-combat-door-n-'+name.split('-')[1]].resize((96,128),Image.Resampling.NEAREST)
            tile.alpha_composite(door,(16,0))
        stable='broadcast-structural-wall-'+name
        path=OUT/'pieces'/(stable+'.png');tile.save(path)
        edge={k:'stone-wall' if k in dirs else 'none' for k in 'NESW'}
        if name.startswith('door-'):
            edge['N']=edge['S']='passage-'+name.split('-')[1]
        assets.append({'id':stable,'src':'pieces/'+path.name,'layer':'wall','anchor':[64,128],'tileSize':[128,128],
            'edges':edge,'adjacency':'canonical-wall-network','authoredRotations':[0],
            'source':'derived from generated combat-source.png raster segments','sourceCrop':[0,0,1024,1536],
            'derivation':{'straight':'broadcast-combat-wall-ew','straightCrop':[0,32,128,96],'center':'broadcast-combat-wall-cross','centerCrop':[32,32,96,96],'connections':dirs,'method':'opaque generated-raster half-segment composition; NS segment is authored 90-degree rotation of EW'},
            'sha256':hashlib.sha256(path.read_bytes()).hexdigest(),'alphaExtrema':list(tile.getchannel('A').getextrema()),'contentBounds':tile.getbbox()})
        previews.append((stable,tile))
    manifest = {'schemaVersion':1,'id':'broadcast-kit','tileSize':128,
                'sourceComponentCount':48,'derivedStructuralCount':13,
                'status':'art-only; 13 derived canonical walls pass matching64px alpha-edge geometry; source junctions/roads remain studies; no full WFC or pixel-seamless certification',
                'assets':assets}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    w, h = 6*176, ((len(previews)+5)//6)*164
    qa=Image.new('RGB',(w,h),(24,28,40)); draw=ImageDraw.Draw(qa)
    for i,(name,tile) in enumerate(previews):
        x,y=(i%6)*176,(i//6)*164
        for yy in range(0,128,16):
            for xx in range(0,128,16):
                draw.rectangle((x+xx,y+yy,x+xx+15,y+yy+15), fill=(55,60,72) if (xx+yy)//16%2 else (36,40,52))
        qa.paste(tile,(x,y),tile)
        draw.text((x+2,y+132),name.replace('broadcast-',''),fill=(240,215,154))
    qa.save(OUT/'qa-sheet.png')
    # Report exact opaque edge intervals, not merely edge contact. Source art
    # junctions can have mismatched bands: this report deliberately exposes it.
    def intervals(values):
        runs=[]; start=None
        for i,v in enumerate(list(values)+[0]):
            if v>=200 and start is None:start=i
            if v<200 and start is not None:runs.append([start,i-1]);start=None
        return runs
    edge_report=[]
    for a in assets:
        if a['layer']!='wall':continue
        im=Image.open(OUT/a['src'])
        sides={'N':[im.getpixel((i,0))[3] for i in range(128)],'S':[im.getpixel((i,127))[3] for i in range(128)],'E':[im.getpixel((127,i))[3] for i in range(128)],'W':[im.getpixel((0,i))[3] for i in range(128)]}
        observed={k:intervals(v) for k,v in sides.items()}
        tests={k:observed[k]==[[32,95]] for k,v in a['edges'].items() if v=='stone-wall'}
        edge_report.append({'id':a['id'],'opaqueEdgeIntervals':observed,'centered64BandChecks':tests,'allTaggedWallEdgesMatch':bool(tests) and all(tests.values())})
    (OUT/'edge-qa.json').write_text(json.dumps({'threshold':200,'expectedInterval':[32,95],'walls':edge_report,'note':'Coverage checks concern alpha geometry, not pixel colors or gameplay collision.'},indent=2)+'\n')
    lookup={name:tile for name,tile in previews}
    demo=Image.new('RGBA',(768,512),(24,28,40,255))
    floor=lookup['broadcast-combat-floor-plain']
    for y in range(0,512,128):
        for x in range(0,768,128):demo.alpha_composite(floor,(x,y))
    placements=[('ew',0,0),('ew',128,0),('ew',256,0),('ns',512,0),('ns',512,128),('ns',512,256),('corner-se',0,256),('ew',128,256),('ns',0,384),('t-new',256,384),('ew',384,384)]
    for name,x,y in placements:demo.alpha_composite(lookup['broadcast-structural-wall-'+name],(x,y))
    demo.save(OUT/'wall-assembly-qa.png')
    canonical=[r for r in edge_report if r['id'].startswith('broadcast-structural-')]
    assert len(canonical)==13 and all(r['allTaggedWallEdgesMatch'] for r in canonical), 'canonical wall connector edge geometry failed'
    print(json.dumps({'exported':len(assets),'qa':str(OUT/'qa-sheet.png')}))

if __name__=='__main__':
    main()
