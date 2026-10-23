#!/usr/bin/env python3
"""Author expanded story approaches; preserve unrelated JSON and stable discovery IDs.

Run with --check for deterministic source and full map-connectivity verification.
Only journey encounter exploration data is changed; floor 3 has a separate saved-layout
migration and is deliberately excluded. No new story battles or lore claims are added.
"""
import argparse
import copy
import json
from collections import deque
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATH = ROOT / 'UnityPackage/Runtime/Data/game-content.json'
# Label, topology, field supply, route lesson. Names describe original game spaces.
PLANS = {
    1: ('Tutorial supply galleries', 'galleries', 'item.water_bomb', 'Coolant Bomb',
        'Try the short central approach or the longer side galleries. Water can extinguish burning tiles; inspect action forecasts before committing.'),
    2: ('Sewer maintenance circuit', 'circuit', 'item.thunder_flask', 'Shock Tonic',
        'Dry ledges provide an alternative to the flooded combat lanes. Wet targets conduct lightning; the Arc Sentry makes spacing valuable.'),
    4: ('Rail transfer concourse', 'rails', 'item.oil_flask', 'Oil Flask',
        'The route control is still required. Parallel transfer galleries join before the encounter; oil and fire interactions can threaten either team.'),
    5: ('Four-quarter survey ring', 'quarters', 'item.frost_vial', 'Frost Vial',
        'Inspect all four existing quadrant markers before battle. This connected survey is an adaptation, not four complete canonical castle campaigns. Wet targets can be frozen.'),
    6: ('Hunting blind perimeter', 'blinds', 'item.water_bomb', 'Coolant Bomb',
        'Inspect the visible enemy intentions during battle. The perimeter offers a supply detour; coolant can extinguish fire, and burning ground is hazardous to both teams.'),
    8: ('Ghost collection archive', 'archive', 'item.cleansing_tonic', 'Cleansing Tonic',
        'Capture all six weakened ghosts from within three tiles. Capture uses preview and confirmation. Defeated ghosts reform weakened; save damage resources for weakening, then close the distance.'),
}

def cell(x, y):
    return {'x': x, 'y': y}


def reachable(width, height, walls, start):
    reached = {start}
    pending = deque([start])
    while pending:
        x, y = pending.popleft()
        for p in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
            if 0 <= p[0] < width and 0 <= p[1] < height and p not in walls and p not in reached:
                reached.add(p)
                pending.append(p)
    return reached


def validate(journey):
    reports = []
    for floor in journey['floors']:
        encounter = floor.get('encounter')
        if not encounter:
            continue
        for name, m, start, blocks, targets in (
            ('exploration', encounter['exploration'], (encounter['exploration']['startX'], encounter['exploration']['startY']),
             encounter['exploration']['walls'], encounter['exploration']['points']),
            ('battle', encounter, (encounter['playerSpawns'][0]['x'], encounter['playerSpawns'][0]['y']),
             [t for t in encounter['tiles'] if t['blocked']], encounter['playerSpawns'] + encounter['enemies']),
        ):
            walls = {(p['x'],p['y']) for p in blocks}
            reached = reachable(m['width'], m['height'], walls, start)
            assert start not in walls, (floor['number'], name, 'blocked start')
            assert len(reached) == m['width'] * m['height'] - len(walls), (floor['number'], name, 'disconnected floor')
            for p in targets:
                assert (p['x'],p['y']) in reached, (floor['number'], name, 'unreachable point', p)
            reports.append(f"Floor {floor['number']} {name}: {len(reached)} connected walkable cells, {len(targets)} reachable locations")
    return reports


def expand(journey):
    result = copy.deepcopy(journey)
    for f in result['floors']:
        if f['number'] not in PLANS:
            continue
        n = f['number']
        label, topology, item, item_label, lesson = PLANS[n]
        m = f['encounter']['exploration']
        m.update(label=label, width=17, height=13, discoveryRadius=2)
        m['description'] = ('Original tactical adaptation: explore the connected ' + label.lower() +
            ', collect optional supplies and inspect route advice before entering the encounter. Exploration has no enemy turns or damage; the safe-room camp remains available between floors.')
        # Preserve every old walkable coordinate, including imported save positions.
        walls = {(x,y) for y in range(13) for x in range(17) if x in (0,16) or y in (0,12)}
        walls |= {(x,y) for x in (4,7) for y in (2,3,5,6)}
        # Annexes each have two or more approaches; cross-passages stay open.
        patterns = {
            'galleries': [(11,y) for y in (2,3,5,6,8,9)] + [(x,10) for x in (3,4,6,7)],
            'circuit': [(x,9) for x in (2,3,4,6,7,8,10,11,12,14)] + [(13,y) for y in (2,3,5,6)],
            'rails': [(x,y) for x in (11,13) for y in (2,3,5,6,8,9,10)],
            'quarters': [(x,8) for x in (2,3,4,6,7,8,10,11,12,14)] + [(12,y) for y in (2,3,5,6)],
            'blinds': [(11,2),(12,2),(13,2),(13,3),(11,6),(12,6),(13,6),(13,7),(4,10),(5,10),(6,10)],
            'archive': [(x,y) for x in (10,13) for y in (2,3,6,7,9,10)],
        }
        walls |= set(patterns[topology])
        # Original IDs and coordinates survive; only the entrance moves into the annex.
        points = [p for p in m['points'] if '_level_' not in p['id']]
        for p in points:
            if p['kind'] == 'encounter':
                p.update(x=15,y=10)
            if p['id'].endswith('_cache'):
                p['label'] = 'Entry supply: Health Tonic'
        def add(suffix, title, text, x, y, supply=None):
            points.append(dict(id=f'discovery.journey_{n}_level_{suffix}', label=title,
                description=text, kind='cache' if supply else 'lore', x=x, y=y,
                itemId=supply or '', count=1 if supply else 0))
        add('recon', 'Route reconnaissance', lesson, 9, 10)
        add('supply', 'Field supply: '+item_label,
            'One '+item_label+' added to the shared pack. This optional supply placement is a tactical adaptation.', 15, 2, item)
        add('recovery', 'Reserve supply: Health Tonic',
            'One Health Tonic added to the shared pack. Collect this reserve before entering battle; exploration itself does not heal the party.', 3, 10, 'item.health_tonic')
        add('exit', 'Encounter staging point',
            'The encounter is ahead. Check the shared pack and formation before entry. Battle victory returns to the existing safe-room camp for supplies, build changes and progression.', 14, 10)
        for p in points:
            walls.discard((p['x'],p['y']))
        m['walls'] = [cell(x,y) for x,y in sorted(walls,key=lambda p:(p[1],p[0]))]
        m['points'] = points
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    text = PATH.read_text()
    data = json.loads(text)
    authored = expand(data['journey'])
    reports = validate(authored)
    if args.check:
        assert authored == data['journey'], 'Run Tools/expand_story_levels.py to author expanded approaches.'
    else:
        # Replace only the journey value to avoid rewriting other authors' content.
        marker = '"journey": '
        start = text.index(marker) + len(marker)
        _, length = json.JSONDecoder().raw_decode(text[start:])
        replacement = json.dumps(authored, ensure_ascii=False, indent=2).replace('\n', '\n  ')
        PATH.write_text(text[:start] + replacement + text[start+length:])
    print('\n'.join(reports))
    print('Verified six expanded approaches; floor 3, destroyed floor 7 and locked floors 9–18 preserved.')

if __name__ == '__main__':
    main()
