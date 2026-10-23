"""Authoring regressions for skill DAGs, expedition rooms and enemy-only kits."""
import json
import unittest
from validate_content import ROOT, validate
from validate_game_data import validate_game


class ExpansionValidationTests(unittest.TestCase):
    def setUp(self):
        data = ROOT / 'UnityPackage/Runtime/Data'
        self.game = json.loads((data / 'game-content.json').read_text())
        self.content = json.loads((data / 'combat-content.json').read_text())

    def errors(self):
        return validate_game(self.game, self.content)

    def assert_rejected(self, text):
        self.assertTrue(any(text in error for error in self.errors()), self.errors())

    def test_expansion_and_backward_optional_collections(self):
        self.assertEqual([], validate(self.content))
        self.assertEqual([], self.errors())
        del self.game['skillTrees']
        del self.game['expeditions']
        for kit in self.content['classes']:
            kit.pop('playerSelectable', None)
        self.assertEqual([], validate(self.content))
        self.assertEqual([], self.errors())

    def test_enemy_selectability_requires_boolean(self):
        self.content['classes'][-1]['playerSelectable'] = 'false'
        self.assertTrue(any('playerSelectable' in error for error in validate(self.content)))

    def test_enemy_only_class_cannot_be_roster_default(self):
        self.game['roster'][0]['classId'] = 'class.enemy_sludge'
        self.assert_rejected('enemy-only class')

    def test_unknown_tree_fields_are_rejected(self):
        self.game['skillTrees'][0]['nodes'][0]['damageMultplier'] = 4
        self.assert_rejected('damageMultplier')

    def test_tree_must_have_deployable_owner(self):
        self.game['skillTrees'][0]['rosterId'] = 'crawler.mordecai'
        self.assert_rejected('deployable crawler')

    def test_trees_cover_all_field_characters(self):
        self.game['skillTrees'].pop()
        self.assert_rejected('every deployable crawler')

    def test_node_ids_are_globally_unique(self):
        self.game['skillTrees'][1]['nodes'][0]['id'] = self.game['skillTrees'][0]['nodes'][0]['id']
        self.assert_rejected('duplicate')

    def test_missing_and_cross_tree_prerequisites_are_rejected(self):
        self.game['skillTrees'][0]['nodes'][1]['prerequisiteIds'] = [self.game['skillTrees'][1]['nodes'][0]['id']]
        self.assert_rejected('own tree')

    def test_prerequisite_cycles_are_rejected(self):
        nodes = self.game['skillTrees'][0]['nodes']
        roots = [node for node in nodes if not node['prerequisiteIds']]
        roots[0]['prerequisiteIds'] = [roots[1]['id']]
        roots[1]['prerequisiteIds'] = [roots[0]['id']]
        self.assert_rejected('prerequisite cycle')

    def test_prerequisite_level_cannot_exceed_child(self):
        nodes = self.game['skillTrees'][0]['nodes']
        nodes[0]['prerequisiteIds'] = [nodes[1]['id']]
        self.assert_rejected('prerequisite level')

    def test_empty_node_and_unknown_ability_are_rejected(self):
        node = self.game['skillTrees'][0]['nodes'][0]
        for key in ('hpBonus', 'manaBonus', 'moveBonus', 'damageBonus', 'healBonus'):
            node[key] = 0
        self.assert_rejected('supported benefit')
        node['abilityIds'] = ['ability.typo']
        self.assert_rejected('unknown abilities ID')

    def test_node_bonus_and_cost_are_bounded(self):
        self.game['skillTrees'][0]['nodes'][0]['hpBonus'] = 7
        self.assert_rejected('hpBonus')
        self.game['skillTrees'][0]['nodes'][0]['hpBonus'] = 0
        self.game['skillTrees'][0]['nodes'][0]['pointCost'] = 2
        self.assert_rejected('pointCost')

    def test_expeditions_cannot_grant_campaign_xp(self):
        self.game['expeditions'][0]['encounter']['xp'] = 1
        self.assert_rejected('xp')

    def test_expedition_unknown_fields_and_art_are_rejected(self):
        self.game['expeditions'][0]['countdown'] = 60
        self.assert_rejected('countdown')
        del self.game['expeditions'][0]['countdown']
        self.game['expeditions'][0]['encounter']['enemies'][0]['artId'] = 'unknown'
        self.assert_rejected('artId')

    def test_expedition_dimensions_and_spawn_collision(self):
        room = self.game['expeditions'][0]['encounter']
        room['width'] = 5
        self.assert_rejected('width')
        room['width'] = 12
        room['enemies'][0]['x'], room['enemies'][0]['y'] = 1, 1
        self.assert_rejected('blocked or occupied spawn')

    def test_expedition_disconnected_enemy_is_rejected(self):
        room = self.game['expeditions'][0]['encounter']
        enemy = room['enemies'][0]
        x, y = enemy['x'], enemy['y']
        neighbors = {(x-1,y), (x+1,y), (x,y-1), (x,y+1)}
        room['tiles'] = [tile for tile in room['tiles'] if (tile['x'], tile['y']) not in neighbors]
        room['tiles'] += [{'x':nx, 'y':ny, 'tags':[], 'blocked':True} for nx,ny in neighbors]
        self.assert_rejected('isolated by walls')

    def test_expedition_unknown_class_and_tag_are_rejected(self):
        enemy = self.game['expeditions'][0]['encounter']['enemies'][0]
        enemy['classId'] = 'class.typo'
        self.assert_rejected('unknown classes ID')
        enemy['tags'] = ['status.typo']
        self.assert_rejected('unknown tags ID')

    def test_expedition_decorations_are_validated(self):
        piece = self.game['expeditions'][0]['decorations'][0]
        piece['assetId'] = 'asset.typo'
        self.assert_rejected('assetId')
        piece['assetId'] = 'grate'
        piece['x'] = 14
        self.assert_rejected('outside board')
        piece['x'] = 5
        piece['rotation'] = 4
        self.assert_rejected('rotation')
        piece['rotation'] = 0
        piece['blocksMovement'] = True
        self.assert_rejected('blocksMovement')

    def test_expedition_ids_and_decorations_are_unique(self):
        self.game['expeditions'][1]['id'] = self.game['expeditions'][0]['id']
        self.assert_rejected('duplicate')
        self.game['expeditions'][0]['decorations'][1]['id'] = self.game['expeditions'][0]['decorations'][0]['id']
        self.assert_rejected('decorations.1.id: duplicate')


if __name__ == '__main__':
    unittest.main()
