#!/usr/bin/env python3
"""Author floor-plane proposals from source contours; see Registration.md.

Writes only crop review landmarks, never artwork. Explicit exceptions remain
unregistered. Run with --preview to inspect landmark contacts in /tmp.
"""
import argparse
import json
from pathlib import Path
import numpy as np
from PIL import Image, ImageDraw
from scipy.optimize import least_squares
from build_style_packs import PADDING, extract_cell

ROOT = Path(__file__).resolve().parents[1]
STYLES = ('pocket-dungeon', 'ink-and-lanterns', 'dungeon-after-dark')

def floor_points(tight, iso):
    mask = np.asarray(tight.getchannel('A')) > 128
    h, w = mask.shape
    if not iso:
        # Orthogonal floors have no projected slab. Use modal straight edges,
        # avoiding antialias fringes and isolated decorative corner pixels.
        xs = np.where(mask.any(axis=0))[0]
        ys = np.where(mask.any(axis=1))[0]
        left, right = 0., float(w)
        top, bottom = 0., float(h)
        return [[left,top],[right,top],[right,bottom],[left,bottom]]
    # Only the upper envelope participates: lower alpha includes slab depth.
    xx = np.where(mask.any(axis=0))[0]
    yy = np.array([np.where(mask[:,x])[0][0] for x in xx],dtype=float)
    cx = (w-1)/2
    def line(side):
        keep = ((xx > .12*w)&(xx < .40*w)) if side == 0 else ((xx > .60*w)&(xx < .88*w))
        x,y=xx[keep],yy[keep]
        fit=least_squares(lambda p:p[0]*x+p[1]-y, np.polyfit(x,y,1), loss='soft_l1',f_scale=1.5)
        residual=np.abs(fit.x[0]*x+fit.x[1]-y)
        good=residual<3
        if good.sum()<12: raise ValueError('No stable upper floor edge')
        return np.polyfit(x[good],y[good],1)
    a,b=line(0); c,d=line(1)
    if not (-.85<a<-.25 and .25<c<.85): raise ValueError('Upper edge slopes not a floor diamond')
    tx=(d-b)/(a-c); ty=a*tx+b
    # Use long straight upper-edge support width; extreme endpoints themselves
    # are excluded from fitting. Surface corners sit above the slab sides.
    lx,rx=1.,float(w-2)
    ly,ry=a*lx+b,c*rx+d
    points=[[tx,ty],[rx,ry],[lx+rx-tx,ly+ry-ty],[lx,ly]]
    return [[round(float(v),3) for v in point] for point in points]

# Manually reviewed top planes behind overhanging coral / foliage and rails.
OVERRIDES = {
 ('ink-and-lanterns','bubble-sea',1): [[119,29],[234,97],[119,165],[4,97]],
 ('dungeon-after-dark','bubble-sea',1): [[120,18],[238,87],[120,156],[2,87]],
 ('ink-and-lanterns','hunting-jungle',0): [[122,1],[241,79],[122,157],[3,79]],
 ('ink-and-lanterns','hunting-jungle',1): [[121,1],[240,78],[121,155],[2,78]],
 ('dungeon-after-dark','hunting-jungle',0): [[120,1],[238,70],[120,139],[2,70]],
 ('dungeon-after-dark','hunting-jungle',1): [[120,1],[238,70],[120,139],[2,70]],
 ('ink-and-lanterns','iron-tracks',0): [[141,1],[233,61],[93,153],[1,93]],
 ('ink-and-lanterns','iron-tracks',1): [[77,1],[228,96],[152,148],[1,53]],
}

def author_walls(styles=STYLES, kits=None):
    root=ROOT/'Docs/BookLocationTiles'
    for style in styles:
     p=root/'crops'/f'{style}.json';data=json.loads(p.read_text());views=[]
     for name,cells in data['sheets'].items():
      if kits and name not in kits:continue
      source=Image.open(root/'sources'/style/f'{name}.png').convert('RGBA')
      for spec in cells:
       if spec['cell'] not in (6,7,12,13):continue
       s,b=extract_cell(source,(6,4),spec['cell'],name,spec['sourceBox'],spec.get('alphaIslandSeeds'));t=s.crop(s.getchannel('A').getbbox());mask=np.asarray(t.getchannel('A'))>128;h,w=mask.shape
       xx=np.where(mask.any(axis=0))[0];yy=np.array([np.where(mask[:,x])[0][-1]+1 for x in xx],float)
       # Both feet participate, central arch void and end ornament do not.
       keep=((xx>.08*w)&(xx<.28*w))|((xx>.72*w)&(xx<.92*w));x,y=xx[keep],yy[keep]
       fit=least_squares(lambda q:q[0]*x+q[1]-y,np.polyfit(x,y,1),loss='soft_l1',f_scale=2);a,b=fit.x
       # Extrapolated bbox endpoints can lie below the physical feet.
       # Require actual support along the fitted contact plane. Three-pixel
       # runs reject single-pixel trim/ornament coincidences.
       supported=(np.abs(a*xx+b-yy)<=3)&(xx>=.03*w)&(xx<=.97*w)
       runs=np.convolve(supported.astype(int),np.ones(3,dtype=int),mode='same')>=3
       support=xx[runs]
       if len(support)<6 or support[-1]-support[0]<.45*w:
        raise ValueError(f'{style}/{name}/{spec["cell"]}: insufficient supported contact baseline')
       left,right=float(support[0]),float(support[-1])
       points=[[left,float(a*left+b)],[right,float(a*right+b)]];axis='x'
       if style!='pocket-dungeon' and a<0:points.reverse();axis='y'
       spec['registration']={'kind':'wall','axis':axis,'points':[[round(v,3) for v in pt] for pt in points]}
       if style=='pocket-dungeon' and name=='bubble-sea' and spec['cell']==12:
        # Tall submarine arch, asymmetric feet and foreground steps; reviewed
        # vertical scale keeps its raised arch within the 192px headroom.
        spec['registration']['verticalScale']=.85
       d=ImageDraw.Draw(t);d.line([tuple(pt) for pt in points],fill='#ff00ff',width=3);t.thumbnail((175,150));views.append((name,spec['cell'],axis,t))
     p.write_text(json.dumps(data,indent=2)+'\n');out=Image.new('RGB',(800,25*180),'#333333');d=ImageDraw.Draw(out)
     for i,(name,cell,axis,t) in enumerate(views):
      x,y=i%4*200,i//4*180;out.paste(t,(x,y+20),t);d.text((x,y),f'{name}:{cell} {axis}',fill='white')
     out.save('/tmp/'+style+'-wall-lines.jpg');print(style,len(views),flush=True)

def main():
    parser=argparse.ArgumentParser();parser.add_argument('--preview',action='store_true');parser.add_argument('--walls-only',action='store_true');parser.add_argument('--style', choices=STYLES, action='append');parser.add_argument('--kit', action='append');args=parser.parse_args()
    styles=args.style or STYLES
    kits=set(args.kit or [])
    if args.walls_only:
        author_walls(styles,kits);return
    for style in styles:
        path=ROOT/'Docs/BookLocationTiles/crops'/f'{style}.json'; data=json.loads(path.read_text()); previews=[]; count=0; skipped=[]
        for name,cells in data['sheets'].items():
            if kits and name not in kits:continue
            source=Image.open(ROOT/'Docs/BookLocationTiles/sources'/style/f'{name}.png').convert('RGBA')
            for spec in cells:
                cell=spec['cell']
                if cell not in range(4):continue
                exception=(style=='ink-and-lanterns' and name=='iron-tracks' and cell in (2,3))
                if exception:
                    skipped.append(f'{name}:{cell}');continue
                sprite,_=extract_cell(source,(6,4),cell,name,spec['sourceBox'],spec.get('alphaIslandSeeds'))
                tight=sprite.crop(sprite.getchannel('A').getbbox())
                try:
                    points=OVERRIDES.get((style,name,cell)) or floor_points(tight,style!='pocket-dungeon')
                except ValueError as error:
                    skipped.append(f'{name}:{cell} ({error})');continue
                spec['registration']={'kind':'floor','points':points}
                count+=1
                if args.preview:
                    view=tight.copy();draw=ImageDraw.Draw(view);draw.line([tuple(p) for p in points]+[tuple(points[0])],fill='#ff00ff',width=2)
                    view.thumbnail((175,135));previews.append((name,cell,view))
        path.write_text(json.dumps(data,indent=2)+'\n')
        if args.preview:
            out=Image.new('RGB',(800,((len(previews)+3)//4)*160),'#333333');draw=ImageDraw.Draw(out)
            for index,(name,cell,view) in enumerate(previews):
                x,y=(index%4)*200,(index//4)*160;out.paste(view,(x,y+20),view);draw.text((x,y),f'{name}:{cell}',fill='white')
            out.save(f'/tmp/{style}-planes.jpg')
        print(style,count,'registered; deferred:',', '.join(skipped))
if __name__=='__main__':main()
