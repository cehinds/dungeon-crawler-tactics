"""Strict JSON campaign checks alongside the C# GameDataValidator."""
import json
from pathlib import Path
import sys
from jsonschema import Draft202012Validator
from validate_content import ROOT, no_duplicate_keys, validate


def validate_game(data, content):
    schema = json.loads((ROOT / 'Tools/game.schema.json').read_text())
    errors = [f"{'.'.join(map(str, e.absolute_path)) or '$'}: {e.message}" for e in Draft202012Validator(schema).iter_errors(data)]
    if errors:
        return errors
    known = {kind: {r['id'] for r in content[kind]} for kind in ('tags', 'classes', 'items', 'abilities')}
    known['roster'] = {r['id'] for r in data['roster']}

    def ref(value, kind, path):
        if value not in known[kind]:
            errors.append(f'{path}: unknown {kind} ID {value}')

    def unique(records, field, path):
        seen = set()
        for i, record in enumerate(records):
            value = record[field]
            if value in seen:
                errors.append(f'{path}.{i}.{field}: duplicate {value}')
            seen.add(value)

    for name, field in [('roster','id'),('classStats','classId'),('encounters','id'),('startingInventory','itemId'),('rewards','id'),('tagRules','tag')]:
        unique(data[name], field, name)
    for name in ('stances', 'forms'):
        unique(data.get(name, []), 'id', name)
        for mode in data.get(name, []):
            if mode.get('grantTag'):
                ref(mode['grantTag'], 'tags', name+'.grantTag')
            if mode.get('rosterId'):
                ref(mode['rosterId'], 'roster', name+'.rosterId')
            if name == 'forms' and not mode.get('rosterId'):
                errors.append('forms: require an explicit rosterId')
    development = data.get('development', {})
    stats = development.get('stats', [])
    unique(stats, 'id', 'development.stats')
    for stat in stats:
        if not any(stat[k] for k in ('hpPerPoint', 'manaPerPoint', 'moveEvery', 'damageEvery', 'healEvery')):
            errors.append('development.stats: each stat needs an actual effect')
    practice_thresholds = development.get('practice', {}).get('useThresholds', [0])
    if practice_thresholds[0] != 0 or any(a >= b for a, b in zip(practice_thresholds, practice_thresholds[1:])):
        errors.append('development.practice.useThresholds: must start at zero and increase strictly')
    achievement_ids = {'achievement.first_move', 'achievement.first_reaction', 'achievement.first_form', 'achievement.first_victory', 'achievement.first_level'}
    for collection in ('recipes', 'lootBoxes'):
        records = development.get(collection, [])
        unique(records, 'id', 'development.' + collection)
        for record in records:
            for key in ('ingredients', 'outputs', 'rewards'):
                entries = record.get(key, [])
                unique(entries, 'itemId', 'development.' + collection + '.' + key)
                for entry in entries:
                    ref(entry['itemId'], 'items', 'development.' + collection + '.' + key)
            if collection == 'lootBoxes':
                if record['achievementId'] and record['achievementId'] not in achievement_ids:
                    errors.append('development.lootBoxes: unknown achievementId')
                if bool(record['achievementId']) == record['fromVictory']:
                    errors.append('development.lootBoxes: reward needs exactly one achievement or victory source')
    unique(data.get('scenarios', []), 'id', 'scenarios')
    for scenario in data.get('scenarios', []):
        room = scenario['encounter']
        enemy_ids = {e['id'] for e in room['enemies']}
        if scenario['bossId'] not in enemy_ids:
            errors.append('scenarios: unknown bossId')
        if not set(scenario['minionIds']) <= enemy_ids or scenario['bossId'] in scenario['minionIds']:
            errors.append('scenarios: invalid minion IDs')
        if scenario['kind'] == 'hoarder' and scenario['minionCap'] > len(scenario['minionIds']):
            errors.append('scenarios: minion cap exceeds authored minions')
        unique(scenario['interactables'], 'id', 'scenarios.interactables')
        positions = set()
        for obj in scenario['interactables']:
            xy = obj['x'], obj['y']
            if not (xy[0] < room['width'] and xy[1] < room['height']) or xy in positions:
                errors.append('scenarios.interactables: outside board or duplicate position')
            positions.add(xy)
        route = [(c['x'], c['y']) for c in scenario['route']]
        if any(x >= room['width'] or y >= room['height'] for x, y in route):
            errors.append('scenarios.route: outside board')
        if scenario['kind'] == 'swine':
            if len(route) < 4 or len(set(route)) != len(route) or any(abs(a[0]-b[0])+abs(a[1]-b[1]) != 1 for a,b in zip(route, route[1:]+route[:1])):
                errors.append('scenarios.route: must be a unique cardinal closed loop')
    progression = data['progression']
    thresholds = progression['xpThresholds']
    if not thresholds or thresholds[0] != 0 or any(a >= b for a, b in zip(thresholds, thresholds[1:])):
        errors.append('progression.xpThresholds: must start at 0 and increase strictly')
    unique(progression['skillUnlocks'], 'id', 'progression.skillUnlocks')
    roster_by_id = {r['id']: r for r in data['roster']}
    for i, unlock in enumerate(progression['skillUnlocks']):
        path = f"progression.skillUnlocks.{i}"
        ref(unlock['rosterId'], 'roster', path+'.rosterId')
        ref(unlock['abilityId'], 'abilities', path+'.abilityId')
        member = roster_by_id.get(unlock['rosterId'])
        if member and not member.get('deployable', True):
            errors.append(path+': skills may only unlock for deployable roster members')
        if unlock['level'] >= len(thresholds):
            errors.append(path+'.level: has no matching XP threshold')
    unique(data['equipment'], 'id', 'equipment')
    for i, gear in enumerate(data['equipment']):
        path = f'equipment.{i}'
        if gear['unlockEncounter'] >= len(data['encounters']):
            errors.append(path+'.unlockEncounter: outside encounter progression')
        if not any(gear[k] for k in ('hpBonus','manaBonus','moveBonus','abilityIds')):
            errors.append(path+': equipment must grant a stat bonus or ability')
        for j, ability_id in enumerate(gear['abilityIds']):
            ref(ability_id, 'abilities', f'{path}.abilityIds.{j}')
    if sum(r['selected'] for r in data['roster']) > data['partySize'] or len(data['roster']) < data['partySize']:
        errors.append('roster: invalid party selection/roster size')
    for i, record in enumerate(data['roster']):
        ref(record['classId'], 'classes', f'roster.{i}.classId')
        if record.get('legacyClassId'):
            ref(record['legacyClassId'], 'classes', f'roster.{i}.legacyClassId')
        if record.get('selected') and not record.get('deployable', True):
            errors.append(f'roster.{i}: non-deployable members cannot be selected')
        for j, ability_id in enumerate(record.get('innateAbilityIds', [])):
            ref(ability_id, 'abilities', f'roster.{i}.innateAbilityIds.{j}')
    replace_targets = [r['replacesId'] for r in data['roster'] if r.get('replacesId')]
    if len(set(replace_targets)) != len(replace_targets):
        errors.append('roster: duplicate replacesId')
    for i, record in enumerate(data['roster']):
        if record.get('replacesId'):
            ref(record['replacesId'], 'roster', f'roster.{i}.replacesId')
            if record['replacesId'] == record['id']:
                errors.append(f'roster.{i}.replacesId: cannot replace itself')
    for kind in ('classStats',):
        for i, record in enumerate(data[kind]):
            ref(record['classId'], 'classes', f'{kind}.{i}.classId')
    missing_stats = known['classes'] - {r['classId'] for r in data['classStats']}
    if missing_stats:
        errors.append(f'classStats: missing {sorted(missing_stats)}')
    for kind in ('startingInventory','rewards'):
        for i, record in enumerate(data[kind]):
            if record['itemId']:
                ref(record['itemId'], 'items', f'{kind}.{i}.itemId')
            elif record['count']:
                errors.append(f'{kind}.{i}: count requires itemId')
    for i, rule in enumerate(data['tagRules']):
        ref(rule['tag'], 'tags', f'tagRules.{i}.tag')
        if rule.get('occupantTag'):
            ref(rule['occupantTag'], 'tags', f'tagRules.{i}.occupantTag')
    unique([e['exploration'] for e in data['encounters']], 'id', 'exploration')
    rooms = [(f'encounters.{i}', e) for i, e in enumerate(data['encounters'])]
    rooms += [(f'scenarios.{i}.encounter', s['encounter']) for i, s in enumerate(data.get('scenarios', []))]
    for base, encounter in rooms:
        if encounter.get('exploration'):
            m = encounter['exploration']
            unique(m['points'], 'id', base+'.exploration.points')
            walls = {(c['x'], c['y']) for c in m['walls']}
            inside = lambda xy: 0 <= xy[0] < m['width'] and 0 <= xy[1] < m['height']
            start = (m['startX'], m['startY'])
            if len(walls) != len(m['walls']) or any(not inside(c) for c in walls) or not inside(start) or start in walls:
                errors.append(base+': invalid exploration walls/start')
            reached = {start}; queue = [start]
            for x,y in queue:
                for c in ((x,y-1),(x-1,y),(x+1,y),(x,y+1)):
                    if inside(c) and c not in walls and c not in reached:
                        reached.add(c); queue.append(c)
            positions = set()
            for p in m['points']:
                xy = p['x'],p['y']
                if xy not in reached or xy in positions:
                    errors.append(base+': unreachable/duplicate exploration discovery')
                positions.add(xy)
                if p['kind'] == 'cache':
                    ref(p['itemId'], 'items', base+'.exploration.points')
                    if p['count'] <= 0: errors.append(base+': cache must grant supplies')
                elif p['itemId'] or p['count']: errors.append(base+': only caches grant supplies')
            if sum(p['kind']=='encounter' for p in m['points']) != 1:
                errors.append(base+': exploration requires one encounter door')

        if len(encounter['playerSpawns']) != data['partySize']:
            errors.append(f'{base}.playerSpawns: must match partySize')
        coordinates = set()
        walls = {(t['x'],t['y']) for t in encounter['tiles'] if t['blocked']}
        for j, tile in enumerate(encounter['tiles']):
            xy = tile['x'], tile['y']
            if xy in coordinates:
                errors.append(f'{base}.tiles.{j}: duplicate tile')
            coordinates.add(xy)
        occupied = set()
        for kind in ('tiles','playerSpawns','enemies'):
            for j, record in enumerate(encounter[kind]):
                path = f'{base}.{kind}.{j}'
                xy = record['x'],record['y']
                if not (xy[0] < encounter['width'] and xy[1] < encounter['height']):
                    errors.append(f'{path}: outside board')
                if kind != 'tiles':
                    if xy in walls or xy in occupied:
                        errors.append(f'{path}: blocked or occupied spawn')
                    occupied.add(xy)
                for tag in record.get('tags', []):
                    ref(tag,'tags',path+'.tags')
                if 'classId' in record:
                    ref(record['classId'],'classes',path+'.classId')
        unique(encounter['enemies'],'id',base+'.enemies')
        if encounter['playerSpawns']:
            start = encounter['playerSpawns'][0]
            reached = {(start['x'],start['y'])}
            queue = list(reached)
            for x,y in queue:
                for nx,ny in ((x,y-1),(x-1,y),(x+1,y),(x,y+1)):
                    if 0 <= nx < encounter['width'] and 0 <= ny < encounter['height'] and (nx,ny) not in walls and (nx,ny) not in reached:
                        reached.add((nx,ny)); queue.append((nx,ny))
            if not occupied <= reached:
                errors.append(f'{base}: a spawn is isolated by walls')
    return sorted(errors)


if __name__ == '__main__':
    try:
        folder = ROOT / 'UnityPackage/Runtime/Data'
        content = json.loads((folder/'combat-content.json').read_text(), object_pairs_hook=no_duplicate_keys)
        data = json.loads((folder/'game-content.json').read_text(), object_pairs_hook=no_duplicate_keys)
        errors = validate(content)
        if not errors:
            errors = validate_game(data,content)
        if errors:
            print('\n'.join(errors),file=sys.stderr)
            sys.exit(1)
        print(f"Valid playable content: {len(data['encounters'])} encounters, {len(data['roster'])} crawlers, {len(content['classes'])} classes, {len(content['abilities'])} abilities, {len(content['items'])} items.")
    except (OSError,ValueError) as error:
        raise SystemExit(str(error))
