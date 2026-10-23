#!/usr/bin/env python3
"""Extract independently layerable PNGs; requires Pillow, numpy and scipy.

Source atlases are retained byte-for-byte. Connected alpha components prevent
overlapping bounding rectangles from importing pixels from neighboring assets.
Nearest-neighbor sizing preserves prop/structure proportions. Floor diamonds
and the water surface deliberately normalize to the game's 128x64 projection.
"""
from pathlib import Path
import json
import numpy as np
from PIL import Image
from scipy import ndimage

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT / 'Web/wwwroot/assets/room-kit'
SPECS = [
 ('wall-ne','walls','structure',76,['wall','stone','ne'],True),
 ('wall-nw','walls','structure',76,['wall','stone','nw'],True),
 ('wall-corner','walls','structure',128,['wall','stone','corner'],True),
 ('pillar','props','prop',40,['pillar','stone'],True),
 ('door-closed-nw','doors','structure',76,['door','closed','nw'],True),
 ('door-open-nw','doors','structure',76,['door','open','nw'],False),
 ('door-closed-ne','doors','structure',76,['door','closed','ne'],True),
 ('door-open-ne','doors','structure',76,['door','open','ne'],False),
 ('torch','props','prop',32,['torch','fire','light'],False),
 ('lever','props','prop',44,['lever','interactive'],False),
 ('grate','overlays','surface',106,['grate','metal'],False),
 ('oil-overlay','overlays','surface',110,['oil','flammable'],False),
 ('water-overlay','overlays','surface',128,['water','wet'],False),
 ('moss','overlays','overlay',106,['moss','decal'],False),
 ('rubble','props','prop',80,['rubble','stone'],True),
 ('stairs','props','prop',96,['stairs','exit'],False),
]
ORIGINAL = [
 ('stone-a','floors','floor',128,['stone','normal','floor'],False),
 ('stone-b','floors','floor',128,['stone','normal','floor'],False),
 ('water-floor','floors','floor',128,['water','wet','floor'],False),
 ('oil-floor','floors','floor',128,['oil','flammable','floor'],False),
 ('crate','props','prop',68,['crate','wood','pushable'],True),
 ('barrel','props','prop',48,['barrel','oil','explosive'],True),
 ('chest','props','prop',72,['chest','loot'],True),
 ('exit','doors','structure',110,['door','exit','closed'],True),
]

def split_components(path, row_centers):
    image = np.array(Image.open(path).convert('RGBA'))
    labels, _ = ndimage.label(image[:,:,3] > 20)
    groups = [[] for _ in range(4 * len(row_centers))]
    for label, box in enumerate(ndimage.find_objects(labels), 1):
        if box is None:
            continue
        pixels = (labels[box] == label).sum()
        if pixels < 12:
            continue
        cy = (box[0].start + box[0].stop) / 2
        cx = (box[1].start + box[1].stop) / 2
        row = min(range(len(row_centers)), key=lambda r: abs(cy-row_centers[r]))
        col = min(3, int(cx / (image.shape[1]/4)))
        groups[row*4+col].append(label)
    return image, labels, groups

def extract(image, labels, selected):
    mask = np.isin(labels, selected)
    yy, xx = np.where(mask)
    box = [int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)]
    result = image[box[1]:box[3],box[0]:box[2]].copy()
    result[:,:,3][~mask[box[1]:box[3],box[0]:box[2]]] = 0
    return Image.fromarray(result), box

def main():
    assets=[]
    sources=[('structural-atlas.png',[145,425,690,945],SPECS,list(range(16))),
             ('terrain-atlas.png',[203,530,900],ORIGINAL,[0,1,2,3,8,9,10,11]),
             ('effects-atlas.png',[180,540,900],[('fire-overlay','overlays','overlay',48,['fire','burning','hazard'],False)],[0])]
    extraction=[]
    for filename, centers, specs, indices in sources:
        image, labels, groups = split_components(OUT/'source'/filename, centers)
        for spec,index in zip(specs,indices):
            ident,folder,layer,target_width,tags,blocking=spec
            sprite, source_box=extract(image,labels,groups[index])
            ratio=target_width/sprite.width
            projected=layer=='floor' or ident=='water-overlay'
            size=(128,64) if projected else (target_width,max(1,round(sprite.height*ratio)))
            sprite=sprite.resize(size,Image.Resampling.NEAREST)
            padded=Image.new('RGBA',(sprite.width+4,sprite.height+4))
            padded.paste(sprite,(2,2))
            destination=OUT/folder/(ident+'.png')
            destination.parent.mkdir(parents=True,exist_ok=True)
            padded.save(destination)
            flat=layer in ('floor','surface','overlay') and 'fire' not in tags
            anchor={'x':padded.width/2,'y':padded.height/2 if flat else padded.height-2-size[0]/4}
            entry={'id':ident,'file':str(destination.relative_to(OUT)),
                   'label':ident.replace('-',' ').title(),'layer':layer,
                   'width':padded.width,'height':padded.height,'anchor':anchor,
                   'footprint':{'width':1,'height':1},'tags':tags,'blocksMovement':blocking}
            connections=[tag for tag in tags if tag in ('nw','ne')]
            if connections: entry['connections']=connections
            assets.append(entry)
            extraction.append({'id':ident,'source':filename,'sourceBox':source_box,'componentLabels':groups[index],'output':entry['file'],'projectionNormalized':projected})
            assert padded.getchannel('A').crop((0,0,padded.width,2)).getbbox() is None
            assert padded.getchannel('A').crop((0,padded.height-2,padded.width,padded.height)).getbbox() is None
    manifest={'version':1,'tile':{'width':128,'height':64},'assets':assets}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (OUT/'source'/'extraction.json').write_text(json.dumps(extraction,indent=2)+'\n')
    print(f'Extracted {len(assets)} separate transparent PNG components into {OUT}')

if __name__=='__main__':main()
