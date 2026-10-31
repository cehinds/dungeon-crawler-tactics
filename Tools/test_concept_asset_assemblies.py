#!/usr/bin/env python3
"""Source assembly checks independently compose declared visible constituents."""
import json
from pathlib import Path
import numpy as np
from PIL import Image
ROOT=Path(__file__).resolve().parents[1]
BASE=ROOT/'Web/wwwroot/assets/concept-reconstruction'
def main():
    manifest=json.loads((BASE/'manifest.json').read_text());layers={l['id']:l for l in manifest['layers']}
    catalog=json.loads((BASE/'derived/catalog.json').read_text());assets={a['id']:a for a in catalog['assets']}
    tested=[]
    for ident in ['portal-exit-source-assembly']:
        asset=assets[ident];ids=asset['sourceComponentIds']
        assert 'exit-direction-arrow' in ids, 'portal arrow omitted'
        parts=[layers[i] for i in ids if layers[i].get('file')]
        x=min(l['offset'][0] for l in parts);y=min(l['offset'][1] for l in parts)
        right=max(l['offset'][0]+l['size'][0] for l in parts);bottom=max(l['offset'][1]+l['size'][1] for l in parts)
        union=Image.new('RGBA',(right-x,bottom-y))
        for l in parts:union.alpha_composite(Image.open(BASE/l['file']).convert('RGBA'),(l['offset'][0]-x,l['offset'][1]-y))
        source = Image.open(ROOT/manifest['source']).convert('RGBA')
        for supplement in asset.get('supplementalSourceRegions',[]):
            left,top,right,bottom = supplement['bounds']
            union.alpha_composite(source.crop((left,top,right,bottom)),(left-x,top-y))
        actual=Image.open(BASE/'derived'/asset['file']).convert('RGBA')
        assert np.array_equal(np.asarray(union),np.asarray(actual)), ident+' incomplete/altered source union'
        assert actual.getextrema()[3]==(0,255), 'portal lacks transparency'
        assert np.all(np.asarray(actual)[34:196,67:166,3] == 255), 'hole in central portal interior'
        tested.append(ident)
    print('PASS exact RGBA union including portal direction arrow:',', '.join(tested))
if __name__=='__main__':main()
