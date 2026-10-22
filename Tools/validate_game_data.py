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
    known = {kind: {r['id'] for r in content[kind]} for kind in ('tags', 'classes', 'items')}

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
    if sum(r['selected'] for r in data['roster']) > data['partySize'] or len(data['roster']) < data['partySize']:
        errors.append('roster: invalid party selection/roster size')
    for kind in ('roster', 'classStats'):
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
    for i, encounter in enumerate(data['encounters']):
        base = f'encounters.{i}'
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
