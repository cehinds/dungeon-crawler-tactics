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
    unique(data.get("sponsorChallenges", []), "id", "sponsorChallenges")
    for challenge in data.get("sponsorChallenges", []):
        ref(challenge["rewardItemId"], "items", "sponsorChallenges.rewardItemId")
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
    # Skill ownership, benefits and prerequisite DAGs mirror the shared-C# boundary.
    trees = data.get('skillTrees', [])
    class_trees = data.get('classSkillTrees', [])
    unique(trees + class_trees, 'id', 'skillTrees')
    unique(class_trees, 'classId', 'classSkillTrees')
    class_by_id = {kit['id']: kit for kit in content['classes']}
    if len(class_trees) > len(class_by_id):
        errors.append('classSkillTrees: exceeds class catalog')
    unique(trees, 'rosterId', 'skillTrees')
    roster_by_id = {r['id']: r for r in data['roster']}
    all_nodes = []
    all_trees = [('skillTrees', i, tree) for i, tree in enumerate(trees)] + [('classSkillTrees', i, tree) for i, tree in enumerate(class_trees)]
    for collection, ti, tree in all_trees:
        path = f'{collection}.{ti}'
        if collection == 'skillTrees':
            owner = roster_by_id.get(tree['rosterId'])
            if owner is None or not owner.get('deployable', True):
                errors.append(path + ': skill-tree owner must be a deployable crawler')
        else:
            owner = class_by_id.get(tree['classId'])
            if owner is None or not owner.get('playerSelectable', True):
                errors.append(path + ': class skill-tree owner must be a selectable class')
        nodes = {node['id']: node for node in tree['nodes']}
        all_nodes.extend(tree['nodes'])
        for ni, node in enumerate(tree['nodes']):
            node_path = f'{path}.nodes.{ni}'
            if node['level'] > (min(50, len(data['progression']['xpThresholds'])) if collection == 'skillTrees' else 50):
                errors.append(node_path + ': level has no matching XP threshold')
            if not node['abilityIds'] and not any(node[key] for key in ('hpBonus', 'manaBonus', 'moveBonus', 'damageBonus', 'healBonus')):
                errors.append(node_path + ': node must grant a supported benefit')
            for ability in node['abilityIds']:
                ref(ability, 'abilities', node_path + '.abilityIds')
            for parent in node['prerequisiteIds']:
                if parent not in nodes:
                    errors.append(node_path + ': prerequisite must reference a node in its own tree')
                elif nodes[parent]['level'] > node['level']:
                    errors.append(node_path + ': prerequisite level exceeds child level')
        visiting, visited = set(), set()
        def visit(node_id):
            if node_id in visiting:
                errors.append(path + ': skill-tree prerequisite cycle')
                return
            if node_id in visited:
                return
            visiting.add(node_id)
            for parent in nodes[node_id]['prerequisiteIds']:
                if parent in nodes:
                    visit(parent)
            visiting.remove(node_id)
            visited.add(node_id)
        for node_id in nodes:
            visit(node_id)
    unique(all_nodes, 'id', 'skillTrees.nodes')
    if trees:
        owners = {tree['rosterId'] for tree in trees}
        if owners != {r['id'] for r in data['roster'] if r.get('deployable', True)}:
            errors.append('skillTrees: every deployable crawler needs exactly one tree')

    expeditions = data.get('expeditions', [])
    unique(expeditions, 'id', 'expeditions')
    for ei, expedition in enumerate(expeditions):
        room = expedition['encounter']
        path = f'expeditions.{ei}'
        if len(room['tiles']) > room['width'] * room['height']:
            errors.append(path + ': tile collection exceeds map area')
        unique(expedition['decorations'], 'id', path + '.decorations')
        for di, piece in enumerate(expedition['decorations']):
            if piece['x'] >= room['width'] or piece['y'] >= room['height']:
                errors.append(f'{path}.decorations.{di}: outside board')

    for mode in data.get('forms', []) + data.get('stances', []):
        if mode.get('practiceAbilityId'):
            ref(mode['practiceAbilityId'], 'abilities', 'tacticalMode.practiceAbilityId')

    profiles = development.get('practice', {}).get('abilityProfiles', [])
    unique(profiles, 'abilityId', 'development.practice.abilityProfiles')
    if len(profiles) > len(known['abilities']):
        errors.append('development.practice.abilityProfiles: exceeds ability catalog')
    rank_tag_owners = {}
    rank_tag_roots = set()
    for pi, profile in enumerate(profiles):
        path = f'development.practice.abilityProfiles.{pi}'
        ref(profile['abilityId'], 'abilities', path + '.abilityId')
        modes = profile.get('castModes', [])
        unique(modes, 'id', path + '.castModes')
        ability = next((a for a in content['abilities'] if a['id'] == profile['abilityId']), None)
        if modes and ability and not any(e['op'] == 'Damage' for e in ability['effects']):
            errors.append(path + ': cast modes require a damage effect')
        milestones = profile.get('milestones', [])
        unique(milestones, 'rank', path + '.milestones')
        for milestone in milestones:
            for tag in milestone.get('addTags', []) + milestone.get('removeTags', []):
                ref(tag, 'tags', path + '.status')
            for replacement in milestone.get('tagReplacements', []):
                ref(replacement['fromTag'], 'tags', path + '.fromTag')
                ref(replacement['toTag'], 'tags', path + '.toTag')
                base, variant = replacement['fromTag'], replacement['toTag']
                rank_tag_roots.add(base)
                if base == variant or (variant in rank_tag_owners and rank_tag_owners[variant] != base):
                    errors.append(path + ': invalid or shared rank tag family')
                rank_tag_owners[variant] = base
                ability = next((a for a in content['abilities'] if a['id'] == profile['abilityId']), None)
                if ability and not any(e['op'] == 'AddTag' and e.get('tag') == base for e in ability['effects']):
                    errors.append(path + ': replacement source must be an authored AddTag effect')
            if not milestone.get('description') or not any(milestone.get(key, 0) for key in ('damageBonus', 'healBonus', 'costReduction', 'rangeBonus', 'pushBonus', 'summonHpBonus', 'summonMoveBonus', 'summonRoundsBonus', 'tagReplacements', 'addTags', 'removeTags')):
                errors.append(path + ': rank milestones need a description and supported benefit')

    if rank_tag_roots.intersection(rank_tag_owners):
        errors.append('rank tag families cannot chain or cycle')

    journey = data.get('journey')
    journey_rooms = []
    if journey:
        floors = journey['floors']
        unique(floors, 'id', 'journey.floors')
        expected_mechanics = ['tutorial', 'tutorial', 'classes', 'route', 'beacons', 'hunt', 'none', 'capture'] + ['none'] * 10
        for fi, floor in enumerate(floors):
            path = f'journey.floors.{fi}'
            kind = 'locked' if fi >= 8 else 'bypass' if fi == 6 else 'battle'
            if floor['number'] != fi + 1 or floor['available'] != (fi < 8) or floor['kind'] != kind:
                errors.append(path + ': invalid ordered floor number, availability or kind')
            if floor['mechanic'] != expected_mechanics[fi]:
                errors.append(path + ': invalid floor mechanic')
            required = floor.get('requiredPointIds', [])
            room = floor.get('encounter')
            if kind != 'battle':
                if room is not None or required or floor.get('captureCount', 0):
                    errors.append(path + ': bypass and locked floors cannot contain encounters or objectives')
                continue
            if room is None or not room.get('exploration'):
                errors.append(path + ': playable journey floor requires an encounter and exploration')
                continue
            journey_rooms.append((path + '.encounter', room))
            points = {point['id']: point for point in room['exploration']['points']}
            if len(required) != len(set(required)) or any(point not in points or points[point]['kind'] != 'lore' for point in required):
                errors.append(path + ': unknown or duplicate lore route objective')
            if (fi == 3 and len(required) != 1) or (fi == 4 and len(required) != 4):
                errors.append(path + ': route requires one lever and beacons require four objectives')
            if fi == 7:
                if floor.get('captureCount', 0) != 6 or len(room['enemies']) != 6:
                    errors.append(path + ': capture floor requires exactly six authored monsters')
            elif floor.get('captureCount', 0):
                errors.append(path + ': only the capture floor may require cards')

    neighborhood = data.get('neighborhood')
    if neighborhood:
        sectors = [room['exploration'] for _, room in journey_rooms if room.get('exploration')]
        sector = next((m for m in sectors if m['id'] == neighborhood['sectorId']), None)
        if sector is None:
            errors.append('neighborhood: unknown journey sectorId')
        legacy = neighborhood.get('legacyExploration')
        if legacy and legacy['id'] != neighborhood['sectorId']:
            errors.append('neighborhood.legacyExploration: must match the current sectorId')
        points = {p['id']: p for p in sector['points']} if sector else {}
        interactions = neighborhood['interactions']
        unique(interactions, 'id', 'neighborhood.interactions')
        unique(neighborhood['challenges'], 'id', 'neighborhood.challenges')
        used_points = set()
        for interaction in interactions:
            path = 'neighborhood.interactions.' + interaction['id']
            if interaction['camp']:
                if interaction['pointId']:
                    errors.append(path + ': camp interaction cannot reference a point')
            elif interaction['pointId'] not in points or points[interaction['pointId']]['kind'] != 'lore':
                errors.append(path + ': interaction requires an authored lore point')
            elif interaction['pointId'] in used_points:
                errors.append(path + ': duplicate interaction point')
            else:
                used_points.add(interaction['pointId'])
            unique(interaction['options'], 'id', path + '.options')
            if not any(not o['abilityId'] and not o['costItemId'] and not o['costCount'] for o in interaction['options']):
                errors.append(path + ': interaction requires a free untrained fallback')
            for option in interaction['options']:
                for prefix in ('cost', 'reward'):
                    item, count = option[prefix + 'ItemId'], option[prefix + 'Count']
                    if bool(item) != bool(count):
                        errors.append(path + ': item and positive count must be supplied together')
                    if item:
                        ref(item, 'items', path)
                if option['abilityId']:
                    ref(option['abilityId'], 'abilities', path)
        by_id = {i['id']: i for i in interactions}
        for challenge in neighborhood['challenges']:
            path = 'neighborhood.challenges.' + challenge['id']
            interaction = by_id.get(challenge['interactionId'])
            if interaction is None:
                errors.append(path + ': unknown interactionId')
            elif challenge['optionId'] and challenge['optionId'] not in {o['id'] for o in interaction['options']}:
                errors.append(path + ': unknown interaction optionId')
            ref(challenge['rewardItemId'], 'items', path)

    home = data.get('home')
    if home:
        upgrades = home.get('upgrades', [])
        unique(upgrades, 'id', 'home.upgrades')
        by_id = {upgrade['id']: upgrade for upgrade in upgrades}
        if sum(upgrade['kind'] == 'space' for upgrade in upgrades) != 1:
            errors.append('home.upgrades: requires exactly one personal space')
        if not home.get('description') or not home.get('economyNote'):
            errors.append('home: description and economy note are required')
        for ability in home.get('trainingAbilityIds', []):
            ref(ability, 'abilities', 'home.trainingAbilityIds')
        if len(home.get('trainingAbilityIds', [])) != len(set(home.get('trainingAbilityIds', []))):
            errors.append('home.trainingAbilityIds: duplicate ability')
        for ui, upgrade in enumerate(upgrades):
            path = f'home.upgrades.{ui}'
            purchasable = upgrade.get('purchasable', True)
            if not upgrade.get('description') or not upgrade.get('costNote'):
                errors.append(path + ': description and price context are required')
            if any(not source for source in upgrade.get('sourceIds', [])):
                errors.append(path + ': source references cannot be empty')
            if not purchasable and not upgrade.get('eligibilityReason'):
                errors.append(path + ': unavailable upgrades require an eligibility explanation')
            if upgrade['kind'] == 'club' and (purchasable or upgrade['priceBasis'] != 'unknown' or upgrade['cost'] != 0):
                errors.append(path + ': club admission cannot be sold as a generic home pass')
            if upgrade['priceBasis'] == 'unknown' and purchasable:
                errors.append(path + ': unknown price cannot be purchasable')
            if upgrade.get('craftOutputBonus', 0) and upgrade['kind'] != 'tools':
                errors.append(path + ': only tools may grant crafting output bonuses')
            current, chain = upgrade, set()
            while current.get('prerequisiteId'):
                if current['id'] in chain:
                    errors.append(path + ': home prerequisite cycle')
                    break
                chain.add(current['id'])
                parent = by_id.get(current['prerequisiteId'])
                if parent is None or not parent.get('purchasable', True):
                    errors.append(path + ': unknown or ineligible home prerequisite')
                    break
                current = parent
            else:
                if upgrade['kind'] != 'space' and purchasable and current['kind'] != 'space':
                    errors.append(path + ': upgrades must require the personal space')

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
        if unlock['level'] > len(thresholds):
            errors.append(path+'.level: has no matching XP threshold')
    unique(data['equipment'], 'id', 'equipment')
    for i, gear in enumerate(data['equipment']):
        path = f'equipment.{i}'
        if gear['unlockEncounter'] > len(data['encounters']):
            errors.append(path+'.unlockEncounter: outside encounter progression')
        if not any(gear[k] for k in ('hpBonus','manaBonus','moveBonus','abilityIds')):
            errors.append(path+': equipment must grant a stat bonus or ability')
        for j, ability_id in enumerate(gear['abilityIds']):
            ref(ability_id, 'abilities', f'{path}.abilityIds.{j}')
    tiers = data.get('equipmentRewardTiers', [])
    unique(tiers, 'id', 'equipmentRewardTiers')
    reward_gear = {g['id']: g for g in data['equipment']}
    tier_items, tier_wins = set(), set()
    for tier in tiers:
        if tier['requiredWins'] in tier_wins:
            errors.append('equipmentRewardTiers: repeated win milestone')
        tier_wins.add(tier['requiredWins'])
        for item_id in tier['equipmentIds']:
            if item_id not in reward_gear or not reward_gear[item_id].get('rewardOnly', False) or item_id in tier_items:
                errors.append('equipmentRewardTiers: unknown, repeated or non-reward equipment '+item_id)
            tier_items.add(item_id)
    for gear in data['equipment']:
        if gear.get('rewardOnly', False) and gear['id'] not in tier_items:
            errors.append('equipmentRewardTiers: reward equipment needs a tier '+gear['id'])
    if sum(r['selected'] for r in data['roster']) > data['partySize'] or len(data['roster']) < data['partySize']:
        errors.append('roster: invalid party selection/roster size')
    player_classes = {c['id'] for c in content['classes'] if c.get('playerSelectable', True)}
    for i, record in enumerate(data['roster']):
        if record['classId'] not in player_classes:
            errors.append(f'roster.{i}: enemy-only class cannot be assigned to a crawler')
        if record.get('legacyClassId') and record['legacyClassId'] not in player_classes:
            errors.append(f'roster.{i}: enemy-only legacy class cannot be assigned to a crawler')
        ref(record['classId'], 'classes', f'roster.{i}.classId')
        if record.get('legacyClassId'):
            ref(record['legacyClassId'], 'classes', f'roster.{i}.legacyClassId')
        if record.get('selected') and not record.get('deployable', True):
            errors.append(f'roster.{i}: non-deployable members cannot be selected')
        for j, tag in enumerate(record.get('combatTags', [])):
            ref(tag, 'tags', f'roster.{i}.combatTags.{j}')
        for j, class_id in enumerate(record.get('specialtyClassIds', [])):
            ref(class_id, 'classes', f'roster.{i}.specialtyClassIds.{j}')
            if class_id not in player_classes:
                errors.append(f'roster.{i}: enemy-only specialty class cannot be assigned to a crawler')
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
    rooms += [(f'expeditions.{i}.encounter', e['encounter']) for i, e in enumerate(data.get('expeditions', []))]
    rooms += journey_rooms
    unique(data['encounters'] + [room for _, room in journey_rooms], 'id', 'encountersAndJourney')
    unique([room['exploration'] for room in data['encounters'] + [room for _, room in journey_rooms] if room.get('exploration')], 'id', 'exploration')
    legacy = data.get('neighborhood', {}).get('legacyExploration')
    if legacy:
        # Reuse the complete authored exploration geometry checks without treating
        # this migration-only snapshot as a second playable encounter.
        rooms.append(('neighborhood.legacyExploration', {'exploration': legacy}))
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

        if base == 'neighborhood.legacyExploration':
            continue

        if len(encounter['playerSpawns']) != data['partySize']:
            errors.append(f'{base}.playerSpawns: must match partySize')
        legacy_cells = set()
        for j, tile in enumerate(encounter.get('legacyTiles', [])):
            xy = tile['x'], tile['y']
            if xy in legacy_cells or not (0 <= xy[0] < encounter['width'] and 0 <= xy[1] < encounter['height']):
                errors.append(f'{base}.legacyTiles.{j}: duplicate or outside board')
            legacy_cells.add(xy)
            for tag in tile['tags']:
                ref(tag, 'tags', f'{base}.legacyTiles.{j}.tags')
        unique(encounter.get('decorations', []), 'id', base+'.decorations')
        for j, piece in enumerate(encounter.get('decorations', [])):
            if not (0 <= piece['x'] < encounter['width'] and 0 <= piece['y'] < encounter['height']):
                errors.append(f'{base}.decorations.{j}: outside board')
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
                if kind == 'enemies' and record['id'] in known['roster']:
                    errors.append(path + ': enemy ID collides with roster')
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
