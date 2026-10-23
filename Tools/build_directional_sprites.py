#!/usr/bin/env python3
"""Normalize actual GPT-generated directional sheets; never synthesize directions.

Sources: four columns SE/SW/NE/NW, three rows idle/walk1/walk2.
Alpha connected components isolate figures despite imperfect source grid spacing.
All characters share a normalized frame foot anchor (64,128); each character
uses one nearest-neighbor pixel scale across all twelve poses.
Requires Pillow, numpy, scipy. Run from any directory.
"""
import json
from pathlib import Path
import numpy as np
from PIL import Image,ImageDraw
from scipy import ndimage

ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'Web/wwwroot/assets/directional'
HEIGHTS={'carl':80,'donut':50,'katia':80,'mongo':70,'elle':64,'imani':80,'louis':80,'brittany':80}
DIRECTIONS=['se','sw','ne','nw']
POSES=['idle','walk1','walk2']

def measure(path):
    source=np.array(Image.open(path).convert('RGBA'))
    labels,_=ndimage.label(source[:,:,3]>20)
    groups=[[] for _ in range(12)]
    for label,box in enumerate(ndimage.find_objects(labels),1):
        if box is None or (labels[box]==label).sum()<12:continue
        cx=(box[1].start+box[1].stop)/2
        cy=(box[0].start+box[0].stop)/2
        col=min(3,int(cx/(source.shape[1]/4)))
        row=min(2,int(cy/(source.shape[0]/3)))
        groups[row*4+col].append(label)
    sprites=[]
    for selected in groups:
        mask=np.isin(labels,selected)
        yy,xx=np.where(mask)
        box=[int(xx.min()),int(yy.min()),int(xx.max()+1),int(yy.max()+1)]
        arr=source[box[1]:box[3],box[0]:box[2]].copy()
        arr[:,:,3][~mask[box[1]:box[3],box[0]:box[2]]]=0
        sprites.append((Image.fromarray(arr),box))
    return sprites

def main():
    manifest={'version':1,'directions':{'se':'front down-right','sw':'front down-left','ne':'rear up-right','nw':'rear up-left'},'characters':{}}
    measurements={}
    for ident,height in HEIGHTS.items():
        path=OUT/'source'/(ident+'.png')
        if not path.exists():continue
        sprites=measure(path)
        scale=height/np.median([s.height for s,_ in sprites[:4]])
        scale=min(scale,116/max(s.width for s,_ in sprites),120/max(s.height for s,_ in sprites))
        sheet=Image.new('RGBA',(512,432));frames={d:{} for d in DIRECTIONS}
        measurements[ident]=[]
        for i,(sprite,box) in enumerate(sprites):
            row,col=divmod(i,4)
            size=(max(1,round(sprite.width*scale)),max(1,round(sprite.height*scale)))
            sprite=sprite.resize(size,Image.Resampling.NEAREST)
            # Body center, rather than tail center, anchors the raptor's feet.
            fraction=(.66 if col in (0,2) else .34) if ident=='mongo' else .5
            px=round(64-size[0]*fraction);py=128-size[1]
            assert px>=0 and px+size[0]<=128,(ident,i,size,px)
            sheet.paste(sprite,(col*128+px,row*144+py))
            frames[DIRECTIONS[col]][POSES[row]]={'x':col*128,'y':row*144,'width':128,'height':144,'drawWidth':128,'drawHeight':144,'anchorX':.5,'anchorY':128/144}
            measurements[ident].append({'direction':DIRECTIONS[col],'pose':POSES[row],'sourceBox':box,'scale':float(scale)})
        sheet.save(OUT/(ident+'.png'))
        portrait=sheet.crop((0,0,128,144))
        portrait.save(OUT/(ident+'-portrait.png'))
        body_height=round(float(np.median([s.height for s,_ in sprites[:4]]))*scale)
        manifest['characters'][ident]={'file':ident+'.png','portrait':ident+'-portrait.png','bodyHeight':body_height,'frames':frames}
    (OUT/'manifest.json').write_text(json.dumps(manifest,indent=2)+'\n')
    (OUT/'source'/'measurements.json').write_text(json.dumps(measurements,indent=2)+'\n')
    print(f'Built {len(manifest["characters"])} characters, {len(manifest["characters"])*12} actual directional frames')

if __name__=='__main__':main()
