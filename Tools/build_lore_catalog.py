"""Build adapted lore class kits/trees from the evidence-tagged research artifact.

The source attests class names. Roles, grants, stats and progression are explicit
adaptations. Existing kits, abilities and unrelated campaign fields are preserved.
Run with --check to verify reproducibility without writing files.
"""
import argparse
import copy
import json
import re
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'UnityPackage/Runtime/Data'
PREFIX = 'class.lore_'
TREE_PREFIX = 'classtree.lore_'
ORIGINAL_TREE_PREFIX = 'classtree.original_'
ROLE_STATS = {
    'frontline': (40, 10, 3),
    'skirmisher': (30, 12, 4),
    'elemental': (26, 16, 3),
    'support': (32, 16, 3),
    'performance': (28, 14, 4),
    'engineering': (34, 12, 3),
    'beast': (36, 10, 4),
}


def level_thresholds():
    """Retain legacy levels 1–4; unlock level-50 builds before the final story battle."""
    result = [0, 30, 70, 120, 200]
    for level in range(6, 51):
        step = level - 5
        result.append(result[-1] + 40 + 10 * step + (3 * step * step) // 2)
    assert len(result) == 50 and result[-1] <= 1000000
    return result


def build(combat, game, research):
    combat, game = copy.deepcopy(combat), copy.deepcopy(game)
    ability_ids = {a['id'] for a in combat['abilities']}
    classes = [c for c in combat['classes'] if not c['id'].startswith(PREFIX)]
    stats = [s for s in game['classStats'] if not s['classId'].startswith(PREFIX)]
    trees = [t for t in game.get('classSkillTrees', []) if not t['id'].startswith((TREE_PREFIX, ORIGINAL_TREE_PREFIX))]
    class_ids = {c['id'] for c in classes}
    node_ids = {node['id'] for tree in trees + game.get('skillTrees', []) for node in tree['nodes']}
    profiles = research['proposedClassProfiles']
    seen_profiles = set()
    for profile in profiles:
        slug = profile['id'].removeprefix('class_profile.')
        class_id = PREFIX + slug
        assert slug not in seen_profiles and class_id not in class_ids, 'Duplicate generated class'
        seen_profiles.add(slug)
        class_ids.add(class_id)
        source_floor = profile.get('selectionFloorFromSource')
        floor = max(3, source_floor or 3)
        # The always-available basic attack is separate from learned branch actions.
        classes.append({'id': class_id, 'label': profile['canonicalName'],
                        'abilityIds': ['ability.strike'], 'playerSelectable': True,
                        'minimumFloor': floor})
        hp, mana, move = ROLE_STATS[profile['proposedRole']]
        stats.append({'classId': class_id, 'hp': hp, 'energy': mana, 'move': move})
        old_to_new = {n['id']: 'classnode.lore_' + n['id'].split('.', 1)[1] for n in profile['nodes']}
        nodes = []
        for original in profile['nodes']:
            node = {key: copy.deepcopy(original[key]) for key in
                    ('label', 'level', 'pointCost', 'abilityIds', 'hpBonus', 'manaBonus',
                     'moveBonus', 'damageBonus', 'healBonus')}
            node['id'] = old_to_new[original['id']]
            node['prerequisiteIds'] = [old_to_new[p] for p in original['prerequisiteIds']]
            node['description'] = ('Tactical adaptation: ' + original['branchId'] +
                                   ' branch at class level ' + str(node['level']) +
                                   '. Grants the listed abilities and passive bonuses; not a canonical class grant list.')
            # A Strike root still grants a concrete bonus when Strike is already innate.
            if node['level'] == 1 and node['abilityIds'] == ['ability.strike']:
                node['hpBonus'] = max(2, node['hpBonus'])
            assert node['id'] not in node_ids, 'Duplicate generated node'
            node_ids.add(node['id'])
            assert set(node['abilityIds']) <= ability_ids, 'Unknown ability grant'
            assert node['pointCost'] == 1 and 1 <= node['level'] <= 50
            assert 0 <= node['hpBonus'] <= 6 and 0 <= node['manaBonus'] <= 3
            assert all(0 <= node[key] <= 1 for key in ('moveBonus', 'damageBonus', 'healBonus'))
            nodes.append(node)
        assert len(nodes) == 14
        trees.append({'id': TREE_PREFIX + slug, 'classId': class_id,
                      'label': profile['canonicalName'] + ' — adapted class tree',
                      'description': ('Source-attested name; original game progression. Two branches through class level 50. '
                                      'Roles, ability grants and numerical bonuses are tactical adaptations.'),
                      'nodes': nodes})
    # Preserve the original playable kits and give each its own adapted tree.
    # Match an attested name when possible; otherwise choose the greatest overlap
    # with the original kit's existing actions. Stable source order breaks ties.
    normalize = lambda value: re.sub(r'[^a-z0-9]', '', value.lower())
    profile_by_name = {normalize(p['canonicalName']): p for p in profiles}
    lore_trees = {t['classId']: t for t in trees if t['id'].startswith(TREE_PREFIX)}
    for kit in classes:
        if kit['id'].startswith(PREFIX) or not kit.get('playerSelectable', True):
            continue
        grants = set(kit['abilityIds'])
        profile = profile_by_name.get(normalize(kit['label']))
        if profile is None:
            def overlap(candidate):
                return len(grants & {ability for n in candidate['nodes'] for ability in n['abilityIds']})
            profile = max(profiles, key=overlap)
        source_slug = profile['id'].removeprefix('class_profile.')
        source_tree = lore_trees[PREFIX + source_slug]
        slug = kit['id'].split('.', 1)[1].replace('.', '_')
        def original_id(node_id):
            branch, level = re.search(r'_(pressure|resilience)_(\d+)$', node_id).groups()
            return 'classnode.original_' + slug + '_' + branch + '_' + level
        nodes = copy.deepcopy(source_tree['nodes'])
        for node in nodes:
            node['id'] = original_id(node['id'])
            node['prerequisiteIds'] = [original_id(parent) for parent in node['prerequisiteIds']]
            node['description'] = ('Preserved-kit tactical adaptation: ' + kit['label'] +
                                   '. Grants listed actions and bonuses; no canonical grant list is claimed.')
            if node['abilityIds'] and set(node['abilityIds']) <= grants:
                node['hpBonus'] = max(2, node['hpBonus'])
            assert node['id'] not in node_ids, 'Duplicate original-kit node'
            node_ids.add(node['id'])
        trees.append({'id': ORIGINAL_TREE_PREFIX + slug, 'classId': kit['id'],
                      'label': kit['label'] + ' — original kit class tree',
                      'description': ('An adapted class tree for the preserved playable kit. '
                                      'Two branches through level 50; innate identity and old kit grants remain unchanged.'),
                      'nodes': nodes})
    combat['classes'] = classes
    game['classStats'] = stats
    game['classSkillTrees'] = trees
    assert game['progression']['xpThresholds'][:4] == [0, 30, 70, 120], 'Legacy thresholds changed'
    game['progression']['xpThresholds'] = level_thresholds()
    return combat, game


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--check', action='store_true')
    args = parser.parse_args()
    combat_path, game_path = DATA / 'combat-content.json', DATA / 'game-content.json'
    combat, game = json.loads(combat_path.read_text()), json.loads(game_path.read_text())
    research = json.loads((ROOT / 'Research/classes-skills.json').read_text())
    generated = build(combat, game, research)
    changed = []
    for path, value in zip((combat_path, game_path), generated):
        text = json.dumps(value, indent=2, ensure_ascii=False) + '\n'
        if path.read_text() != text:
            changed.append(path.name)
            if not args.check:
                path.write_text(text)
    if args.check and changed:
        raise SystemExit('Generated content differs: ' + ', '.join(changed))
    generated_trees = [t for t in generated[1]['classSkillTrees'] if t['id'].startswith((TREE_PREFIX, ORIGINAL_TREE_PREFIX))]
    print(('Verified' if args.check else 'Built') + ' ' + str(len(generated_trees)) +
          ' adapted class trees (' + str(len(research['proposedClassProfiles'])) + ' catalog plus preserved player kits), ' + str(sum(len(t['nodes']) for t in generated_trees)) +
          ' class nodes; 50 party levels, final XP threshold ' + str(level_thresholds()[-1]) + '.')


if __name__ == '__main__':
    main()
