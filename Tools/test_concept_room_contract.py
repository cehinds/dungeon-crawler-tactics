#!/usr/bin/env python3
"""Independent seed sweep and adversarial room contract checks."""
import argparse
import copy
import json
import hashlib
import subprocess
from pathlib import Path
from PIL import Image, ImageDraw
from test_concept_reconstruction import verify_room

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'Web/wwwroot/assets/concept-reconstruction'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--count", type=int, default=1000, help="Sequential seeds starting at zero")
    args = parser.parse_args()
    recipe = json.loads((BASE/'procedural/recipe.json').read_text())
    catalog = json.loads((BASE/'derived/catalog.json').read_text())
    script = "const e=require(process.argv[1]),fs=require('fs'),q=JSON.parse(fs.readFileSync(0));for(const seed of q.seeds)process.stdout.write(JSON.stringify(e.generate(q.r,q.c,seed))+'\\n');"
    engine_args = ['node','-e',script,str(ROOT/'Web/wwwroot/concept-room-engine.js')]
    seeds = list(range(args.count)) + [-1, -2147483648, 2147483647, 4294967295, 4294967296, 9007199254740991, -9007199254740991]
    payload = json.dumps({'r':recipe,'c':catalog,'seeds':seeds})
    rooms = {}
    topologies = set(); channel_sides = set()
    def sweep(retain):
        process = subprocess.Popen(engine_args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        process.stdin.write(payload); process.stdin.close()
        digest = hashlib.sha256(); count = 0
        for line in process.stdout:
            digest.update(line.encode()); room = json.loads(line)
            verify_room(room,recipe,catalog); count += 1
            if retain:
                topologies.add(json.dumps(room['grid'],separators=(',',':')))
                channel_sides.add(room['channel']['side'])
                if room['seed'] in {7,9,29,103}: rooms[room['seed']] = room
        assert process.wait() == 0 and count == len(seeds), 'incomplete seed sweep'
        return digest.hexdigest()
    assert sweep(True) == sweep(False), 'nondeterministic engine'
    assert len(topologies) >= min(8,args.count) and channel_sides == {'west','east'}, 'insufficient structural seed variation'
    for seed in recipe.get('requiredSeeds',[7,29,103]):
        published = json.loads((BASE/f'procedural/room-{seed}.json').read_text())
        assert published == rooms[seed], f'CLI plan differs from shared engine seed {seed}'
    mutations = {
        'wrong bank orientation': lambda r:next(d for d in r['drawPlan'] if d['layer']==11).__setitem__('assetId', catalog['roles']['bankWestVariants' if r['channel']['side']=='west' else 'bankEastVariants'][0]),
        'missing prop': lambda r:r['placements'].pop(),
        'unknown cell': lambda r:r['grid'][0].__setitem__(0,'lava'),
        'ragged grid': lambda r:r['grid'][0].pop(),
        'missing draw entity': lambda r:r['drawPlan'].remove(next(d for d in r['drawPlan'] if d.get('entityId'))),
        'HUD overlap': lambda r:next(d for d in r['drawPlan'] if d.get('entityId')).__setitem__('y',747),
        'missing masonry face': lambda r:r['drawPlan'].remove(next(d for d in r['drawPlan'] if d.get('tileRole')=='wallFace' and tuple(d['cell']) in {(x,y) for y,row in enumerate(r['grid']) for x,v in enumerate(row) if v=='wall'})),
        'overlapping entity art': lambda r:next(d for d in r['drawPlan'] if d.get('entityId')).update({k:[d for d in r['drawPlan'] if d.get('entityId')][1][k] for k in ('x','y')}),
        'entity art over portal': lambda r:next(d for d in r['drawPlan'] if d.get('entityId')).update({k:next(d for d in r['drawPlan'] if d.get('portal')=='exit')[k] for k in ('x','y')}),
        'malformed entrance crop': lambda r:next(d for d in r['drawPlan'] if d.get('portal')=='entrance').__setitem__('sourceRect',[0,-1,235,57]),
        'portal art extends beyond opening': lambda r:next(d for d in r['drawPlan'] if d.get('portal')=='exit').__setitem__('width',recipe['board']['columns']*recipe['board']['tileSize']),
        'forged entity foot depth': lambda r:next(d for d in r['drawPlan'] if d.get('entityId')).__setitem__('footY',-999),
        'stretched pier': lambda r:next(d for d in r['drawPlan'] if d.get('tileRole')=='pier').__setitem__('width',64),
        'pier outside upright layer': lambda r:next(d for d in r['drawPlan'] if d.get('tileRole')=='pier').__setitem__('layer',21),
        'unknown draw asset': lambda r:next(d for d in r['drawPlan'] if d.get('entityId')).__setitem__('assetId','missing'),
    }
    for label,mutate in mutations.items():
        damaged = copy.deepcopy(rooms[9]); mutate(damaged)
        try: verify_room(damaged,recipe,catalog)
        except AssertionError: pass
        else: raise AssertionError('Verifier accepted mutation: '+label)
    # A one-cell gate is connected in the bare terrain but closed by a solid prop.
    gated = copy.deepcopy(rooms[9])
    prop = next(p for p in gated['placements'] if p['kind']=='prop')
    gate_x,gate_y = prop['cell']
    for x,value in enumerate(gated['grid'][gate_y]):
        if value != 'water': gated['grid'][gate_y][x] = 'floor' if x==gate_x else 'wall'
    try: verify_room(gated,recipe,catalog)
    except AssertionError as error:
        assert 'prop-obstructed' in str(error), 'gate fixture did not reach obstacle graph check: '+str(error)
    else: raise AssertionError('Verifier accepted prop closing the only gate')
    # Synthetic overlap projects actual engine actor/prop records onto one shared footprint.
    # The foreground color must follow foot depth regardless of entity kind.
    room = rooms[9]
    kinds = {p['id']:p['kind'] for p in room['placements']}
    records = [d for d in room['drawPlan'] if d.get('entityId')]
    pair = next((a,b) for a in records for b in records if kinds[a['entityId']] != kinds[b['entityId']] and a['footY'] != b['footY'])
    ordered = [d for d in records if d in pair]
    canvas = Image.new('RGB',(8,8))
    colors = {'actor':'red','prop':'blue'}
    for d in ordered:ImageDraw.Draw(canvas).rectangle((0,0,7,7),fill=colors[kinds[d['entityId']]])
    front = max(pair,key=lambda d:d['footY'])
    expected = Image.new('RGB',(1,1),colors[kinds[front['entityId']]]).getpixel((0,0))
    assert canvas.getpixel((4,4)) == expected, 'actor/prop overlap violates common foot depth'
    # Actor/pier overlap: synthetic identical screen footprints isolate draw order
    # from texture alpha and require the foreground sample to follow foot depth.
    upright = [d for d in room['drawPlan'] if d.get('entityId') or d.get('tileRole')=='pier']
    pier = next(d for d in upright if d.get('tileRole')=='pier')
    actor = next(d for d in upright if d.get('entityId') and kinds[d['entityId']]=='actor' and d['footY']!=pier['footY'])
    pair = [d for d in upright if d is pier or d is actor]
    canvas = Image.new('RGB',(8,8))
    for d in pair: ImageDraw.Draw(canvas).rectangle((0,0,7,7),fill='blue' if d is pier else 'red')
    front = max(pair,key=lambda d:d['footY'])
    assert canvas.getpixel((4,4)) == Image.new('RGB',(1,1),'blue' if front is pier else 'red').getpixel((0,0)), 'actor/pier overlap violates common foot depth'
    damaged_catalog = copy.deepcopy(catalog)
    entries = damaged_catalog['assets']
    entries = {a['id']:a for a in entries} if isinstance(entries,list) else entries
    water_draw = next(d for d in rooms[9]['drawPlan'] if d['layer']==10 and rooms[9]['grid'][d['cell'][1]][d['cell'][0]]=='water')
    entries[water_draw['assetId']]['edgeTags']['north'] = 'incompatible-water-fixture'
    try: verify_room(rooms[9],recipe,damaged_catalog)
    except AssertionError: pass
    else: raise AssertionError('Verifier accepted mutated water edge socket')
    guard_script = "const e=require(process.argv[1]),q=JSON.parse(require('fs').readFileSync(0));try{e.generate(q.r,q.c,9);process.exit(2)}catch(error){process.stdout.write(error.message);process.exit(error.message.includes('Fixed HUD')?0:3)}"
    def reject_hud(label,change):
        bad = copy.deepcopy(recipe); change(bad)
        result = subprocess.run(['node','-e',guard_script,str(ROOT/'Web/wwwroot/concept-room-engine.js')],input=json.dumps({'r':bad,'c':catalog}),capture_output=True,text=True)
        assert result.returncode == 0 and 'mismatch' in result.stdout, 'Missing explicit fixed-HUD rejection: '+label
    def changed_hp(r):
        r['state']['hp'] = 39
        next(e for e in r['entities'] if e['id']==r['state']['selectedId'])['hp'] = 39
    reject_hud('matching entity/state HP39 over raster32',changed_hp)
    for field,value in [('round',3),('selectedId','katia'),('targetId','rat-east'),('mana',9),('forecastDamage',13)]:
        reject_hud(field, lambda r,field=field,value=value:r['state'].__setitem__(field,value))
    for field in ['selectedId','targetId']:
        def changed_asset(r,field=field):
            next(e for e in r['entities'] if e['id']==r['state'][field])['assetId']='actor-katia'
        reject_hud(field+' asset remapping',changed_asset)
    for crop in (-1, 197, 10000, 1.5):
        bad = copy.deepcopy(recipe); bad['architecture']['entrancePresentation']['cropTop'] = crop
        script = "const e=require(process.argv[1]),q=JSON.parse(require('fs').readFileSync(0));try{e.generate(q.r,q.c,9);process.exit(2)}catch(error){process.stdout.write(error.message)}"
        result = subprocess.run(['node','-e',script,str(ROOT/'Web/wwwroot/concept-room-engine.js')],input=json.dumps({'r':bad,'c':catalog}),capture_output=True,text=True)
        assert result.returncode == 0 and ('crop' in result.stdout.lower()), 'Missing malformed crop rejection: '+str(crop)
    print(f'PASS: {len(seeds)} seeds, byte-stable repeat, published plan parity, {len(mutations)+2} adversarial geometry/socket fixtures + eight fixed-HUD mismatch fixtures + four malformed authored crops; {len(topologies)} distinct topologies')

if __name__ == '__main__': main()
