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
    parser.add_argument("--count", type=int, default=200, help="Sequential seeds starting at zero")
    args = parser.parse_args()
    recipe = json.loads((BASE/'procedural/recipe.json').read_text())
    catalog = json.loads((BASE/'derived/catalog.json').read_text())
    script = "const e=require(process.argv[1]),fs=require('fs'),q=JSON.parse(fs.readFileSync(0));for(const seed of q.seeds)process.stdout.write(JSON.stringify(e.generate(q.r,q.c,seed))+'\\n');"
    engine_args = ['node','-e',script,str(ROOT/'Web/wwwroot/concept-room-engine.js')]
    seeds = list(range(args.count)) + [-1, -2147483648, 2147483647, 4294967295, 4294967296, 9007199254740991, -9007199254740991]
    payload = json.dumps({'r':recipe,'c':catalog,'seeds':seeds})
    rooms = {}
    def sweep(retain):
        process = subprocess.Popen(engine_args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, text=True)
        process.stdin.write(payload); process.stdin.close()
        digest = hashlib.sha256(); count = 0
        for line in process.stdout:
            digest.update(line.encode()); room = json.loads(line)
            verify_room(room,recipe,catalog); count += 1
            if retain and room['seed'] in {7,9,29,103}: rooms[room['seed']] = room
        assert process.wait() == 0 and count == len(seeds), 'incomplete seed sweep'
        return digest.hexdigest()
    assert sweep(True) == sweep(False), 'nondeterministic engine'
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
        'unknown draw asset': lambda r:next(d for d in r['drawPlan'] if d.get('entityId')).__setitem__('assetId','missing'),
    }
    for label,mutate in mutations.items():
        damaged = copy.deepcopy(rooms[9]); mutate(damaged)
        try: verify_room(damaged,recipe,catalog)
        except AssertionError: pass
        else: raise AssertionError('Verifier accepted mutation: '+label)
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
    print(f'PASS: {len(seeds)} seeds, byte-stable repeat, published plan parity, eight geometry mutations + eight fixed-HUD mismatch fixtures')

if __name__ == '__main__': main()
