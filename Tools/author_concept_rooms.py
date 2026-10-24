#!/usr/bin/env python3
"""Author compact connected masonry chambers. --check verifies source and topology.

Legacy tile records are retained verbatim for active saved battles; new layouts never
move actors or change enemy definitions, objectives, rewards, or exploration state.
"""
import argparse
import copy
import json
from pathlib import Path
from expand_story_levels import reachable

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / 'UnityPackage/Runtime/Data/game-content.json'


def author(room, sewer=False):
    old = copy.deepcopy(room.get('legacyTiles', room['tiles']))
    room['legacyTiles'] = old
    room['layoutVersion'] = 1
    w, h = room['width'], room['height']
    # Masonry has genuine logical footprints. Gaps are the only doorways.
    walls = {(x,y) for y in range(h) for x in range(w)
             if x in (0,w-1) or y in (0,h-1)}
    if sewer:
        walls |= {(5,y) for y in (2,3,5,6,7)}
        walls |= {(x,4) for x in (6,8,9)}
        doorways = [(5,1,'door-open-ne'),(5,4,'door-open-ne'),(6,4,'door-open-nw'),(7,4,'door-open-nw'),(10,4,'door-open-nw')]
    else:
        walls |= {(4,y) for y in (1,2,5,6)}
        walls |= {(x,4) for x in (1,4,8)}
        # Supply alcove, party chamber and eastern flooded gallery.
        doorways = [(2,4,'door-open-nw'),(3,4,'door-open-nw'),(4,3,'door-open-ne'),(7,4,'door-open-nw')]
    tags = {(t['x'],t['y']): t['tags'] for t in old if t['tags']}
    # Preserve every original hazard footprint; no wall can masquerade as water.
    walls -= set(tags)
    occupied = {(p['x'],p['y']) for p in room['playerSpawns']+room['enemies']}
    assert not walls & occupied
    room['tiles'] = [dict(x=x,y=y,tags=tags.get((x,y),[]),blocked=(x,y) in walls)
                     for y in range(h) for x in range(w) if (x,y) in walls or (x,y) in tags]
    decorations=[]
    def place(asset, layer, x, y):
        decorations.append(dict(id=f"placement.concept_{len(decorations)}",assetId=asset,
            layer=layer,x=x,y=y,rotation=0,blocksMovement=False))
    for x,y,asset in doorways:
        assert (x,y) not in walls
        place(asset,'wall',x,y)
    # Solid props sit exclusively on blocked footprints, never occupy actor cells.
    for x,y,asset in ([(5,2,'barrel'),(8,4,'pillar'),(9,0,'chest')] if sewer else
                      [(4,1,'pillar'),(4,6,'barrel'),(8,4,'chest')]):
        assert (x,y) in walls
        place(asset,'prop',x,y)
    for x,y in ([(1,0),(5,3),(10,0),(0,6)] if sewer else [(1,0),(6,0),(0,5),(9,5)]):
        place('torch','wall',x,y)
    for x,y in ([(5,4),(7,4)] if sewer else [(2,4),(4,3)]):
        place('grate','ground',x,y)
    for x,y in ([(3,0),(0,4),(11,6)] if sewer else [(3,0),(0,4),(9,6)]):
        place('moss','ground',x,y)
    room['decorations']=decorations
    return decorations


def selected(data):
    return [(data['encounters'][0],False),
            (data['journey']['floors'][0]['encounter'],False),
            (data['expeditions'][0]['encounter'],True)]


def validate(data):
    for room,sewer in selected(data):
        walls={(t['x'],t['y']) for t in room['tiles'] if t['blocked']}
        start=room['playerSpawns'][0]
        seen=reachable(room['width'],room['height'],walls,(start['x'],start['y']))
        assert len(seen)==room['width']*room['height']-len(walls),room['id']
        assert all((p['x'],p['y']) in seen for p in room['playerSpawns']+room['enemies'])
        water={(t['x'],t['y']) for t in room['tiles'] if 'surface.water' in t['tags']}
        dry=reachable(room['width'],room['height'],walls | water,(start['x'],start['y']))
        assert all((p['x'],p['y']) in dry for p in room['enemies'] if (p['x'],p['y']) not in water), 'A dry bypass must reach every dry enemy cell'
        # Closing the authored door thresholds separates at least three chambers.
        thresholds={(p['x'],p['y']) for p in room['decorations'] if p['assetId'].startswith('door-open')}
        remaining=seen-thresholds; chambers=0
        while remaining:
            seed=min(remaining); component=reachable(room['width'],room['height'],walls | thresholds,seed)
            remaining-=component; chambers+=1
        assert chambers>=3, (room['id'], 'needs three distinct chambers', chambers)
        for p in room['decorations']:
            if p['assetId'] in ('barrel','pillar','chest'):
                assert (p['x'],p['y']) in walls
        print(f"{room['id']}: {len(seen)} connected floor cells; {len(walls)} solid footprints; {len(room['decorations'])} authored details")


def main():
    p=argparse.ArgumentParser(description=__doc__); p.add_argument('--check',action='store_true');args=p.parse_args()
    data=json.loads(PATH.read_text()); updated=copy.deepcopy(data)
    for room,sewer in selected(updated):
        decorations=author(room,sewer)
        if sewer: updated['expeditions'][0]['decorations']=copy.deepcopy(decorations)
    validate(updated)
    if args.check:
        assert updated==data,'Run Tools/author_concept_rooms.py to update chamber authoring.'
    else:
        PATH.write_text(json.dumps(updated,ensure_ascii=False,indent=2)+'\n')

if __name__=='__main__': main()
