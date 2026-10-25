"""Reviewed plane/contact registration, independent of decorative alpha bounds.

Landmarks use pixel coordinates in the tight extracted source image. Floor order
is top/right/bottom/left (isometric), TL/TR/BR/BL (orthogonal). Wall points follow
positive grid axis x or y and map to a baseline centered on the canvas anchor.
"""
import math
from PIL import Image
from build_style_packs import require


def apply(matrix, point):
    a, b, c, d, e, f = matrix
    x, y = point
    return (a*x + b*y + c, d*x + e*y + f)


def affine(source, target):
    (x, y), (u, v), (r, s) = source
    determinant = (u-x)*(s-y)-(r-x)*(v-y)
    require(abs(determinant) > 1e-8, 'Registration landmarks must not be collinear')
    def row(values):
        t, q, z = values
        a = ((q-t)*(s-y)-(z-t)*(v-y))/determinant
        b = ((u-x)*(z-t)-(r-x)*(q-t))/determinant
        return a, b, t-a*x-b*y
    return (*row([p[0] for p in target]), *row([p[1] for p in target]))


def registered(tight, asset, style, registration, canvas_size, anchor):
    require(isinstance(registration, dict), 'Registration must be an object')
    kind = registration.get('kind')
    points = registration.get('points')
    require(kind in ('floor', 'wall'), 'Unknown registration kind')
    require(isinstance(points, list) and len(points) == (4 if kind == 'floor' else 2)
            and all(isinstance(p, list) and len(p) == 2
                    and all(type(v) in (int, float) and math.isfinite(v) for v in p) for p in points),
            'Registration requires finite pixel landmarks')
    require((kind == 'floor' and asset['role'] == 'ground')
            or (kind == 'wall' and asset['role'] in ('wall', 'door')),
            'Registration kind does not match asset role')
    w, h = style['tileWidth'], style['tileHeight']
    iso = style['projection'] == 'isometric'
    ax, ay = anchor['x'], anchor['y']
    if kind == 'floor':
        relative = [(0,-h/2),(w/2,0),(0,h/2),(-w/2,0)] if iso else [(-w/2,-h/2),(w/2,-h/2),(w/2,h/2),(-w/2,h/2)]
        target = [(ax+x,ay+y) for x,y in relative]
        matrix = affine([points[i] for i in (0,1,3)], [target[i] for i in (0,1,3)])
        require(math.dist(apply(matrix, points[2]), target[2]) <= 2,
                'Floor registration fourth corner must match the affine plane within 2 pixels')
    else:
        axis = registration.get('axis')
        require(axis in ('x','y'), 'Wall registration requires grid axis x or y')
        dx, dy = ((w/2,h/2) if axis == 'x' else (-w/2,h/2)) if iso else ((w,0) if axis == 'x' else (0,h))
        length = math.dist(*points)
        require(length > 0, 'Wall registration endpoints must differ')
        scale = registration.get('verticalScale', math.hypot(dx,dy)/length)
        require(type(scale) in (int,float) and math.isfinite(scale) and scale > 0,
                'Wall verticalScale must be positive finite')
        target = [(ax-dx/2,ay-dy/2),(ax+dx/2,ay+dy/2)]
        matrix = affine([*points, [points[0][0],points[0][1]-1]],
                        [*target, (target[0][0],target[0][1]-scale)])
    # Validate actual visible pixels, not the empty corners of their rectangle.
    alpha = tight.getchannel('A')
    left=top=float('inf'); right=bottom=float('-inf')
    for y in range(tight.height):
        row = alpha.crop((0,y,tight.width,y+1)).getbbox()
        if row:
            for p in ((row[0],y),(row[2],y),(row[0],y+1),(row[2],y+1)):
                tx,ty=apply(matrix,p)
                left=min(left,tx);right=max(right,tx);top=min(top,ty);bottom=max(bottom,ty)
    require(left >= 0 and top >= 0 and right <= canvas_size[0] and bottom <= canvas_size[1],
            f"{asset['id']}: registration would clip normalized canvas")
    inverse = affine([apply(matrix,p) for p in ((0,0),(1,0),(0,1))], [(0,0),(1,0),(0,1)])
    pixel = style['id'] == 'pocket-dungeon'
    sampling = Image.Resampling.NEAREST if pixel else Image.Resampling.BICUBIC
    result = tight.transform(canvas_size, Image.Transform.AFFINE, inverse, resample=sampling)
    bounds = result.getchannel('A').getbbox()
    derived = {'kind':'normalized-derived-export','sizing':'registered-'+kind,
               'resampling':'nearest' if pixel else 'bicubic', 'affine':list(matrix),
               'width':bounds[2]-bounds[0], 'height':bounds[3]-bounds[1],
               'offset':{'x':bounds[0],'y':bounds[1]},
               'registration':{'kind':kind,'points':[list(p) for p in target]}}
    source_anchor = apply(inverse, (ax, ay))
    return result, derived, {'x':source_anchor[0]/tight.width, 'y':source_anchor[1]/tight.height}


def native_square(tight, asset, style, canvas_size, anchor):
    """Normalize native axis-aligned art; never reproject legacy diamond art."""
    layout = asset['squareLayout']
    require(layout in ('floor','north-wall','west-wall','overlay','prop'),
            f"{asset['id']}: unknown squareLayout")
    require(style['projection'] == 'orthogonal' and style['tileWidth'] == 128
            and style['tileHeight'] == 128, 'Native square layouts require an orthogonal 128 by 128 grid')
    if layout == 'floor':
        require(asset['role'] == 'ground', 'Native floor layout requires ground role')
        if asset.get('cell', 0) < 4:
            alpha = tight.getchannel('A')
            solid = sum(alpha.histogram()[128:]) / (tight.width*tight.height)
            require(solid >= .85, f"{asset['id']}: native full floor must fill a square, not an angled diamond")
            require(.85 <= tight.width/tight.height <= 1/.85,
                    f"{asset['id']}: native full floor must have square source proportions")
        size = (128,128)
        relative = (.5,.5)
    elif layout == 'prop':
        scale = min(asset['renderWidth']/tight.width,240/tight.width,184/tight.height)
        size = (max(1,round(tight.width*scale)),max(1,round(tight.height*scale)))
        relative = (.5,1)
    else:
        require('renderHeight' in asset, f"{asset['id']}: native layout requires renderHeight")
        size = (round(asset['renderWidth']),round(asset['renderHeight']))
        require(size[0] > 0 and size[1] > 0, 'Native dimensions must be positive')
        relative = (1,.5) if layout == 'west-wall' else (.5,1) if layout == 'north-wall' else (.5,.5)
    offset = (round(anchor['x']-relative[0]*size[0]),round(anchor['y']-relative[1]*size[1]))
    require(offset[0]>=0 and offset[1]>=0 and offset[0]+size[0]<=canvas_size[0]
            and offset[1]+size[1]<=canvas_size[1], f"{asset['id']}: native layout would clip normalized canvas")
    pixel = style['id'] == 'pocket-dungeon'
    sampling = Image.Resampling.NEAREST if pixel else Image.Resampling.LANCZOS
    result = Image.new('RGBA',canvas_size)
    result.paste(tight.resize(size,sampling),offset)
    x,y=offset;w,h=size
    if layout == 'floor':
        placement = {'kind':'floor','points':[[x,y],[x+w,y],[x+w,y+h],[x,y+h]]}
    elif layout == 'north-wall':
        placement = {'kind':'wall','axis':'x','points':[[x,y+h],[x+w,y+h]]}
    elif layout == 'west-wall':
        placement = {'kind':'wall','axis':'y','points':[[x+w,y],[x+w,y+h]]}
    else:
        placement = {'kind':layout,'points':[[anchor['x'],anchor['y']]]}
    derived = {'kind':'normalized-derived-export','sizing':'native-square-'+layout,
               'resampling':'nearest' if pixel else 'lanczos',
               'scaleX':w/tight.width,'scaleY':h/tight.height,'width':w,'height':h,
               'offset':{'x':x,'y':y},'placement':placement}
    return result,derived,{'x':relative[0],'y':relative[1]}
