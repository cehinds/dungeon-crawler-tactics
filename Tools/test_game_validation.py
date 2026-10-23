import copy
import json
import unittest
from validate_content import ROOT
from validate_game_data import validate_game


class CampaignValidationTests(unittest.TestCase):
    def setUp(self):
        folder = ROOT / 'UnityPackage/Runtime/Data'
        self.game = json.loads((folder/'game-content.json').read_text())
        self.content = json.loads((folder/'combat-content.json').read_text())

    def test_authored_floor_is_valid(self):
        self.assertEqual([],validate_game(self.game,self.content))

    def test_misspelled_config_is_rejected(self):
        self.game['tagRules'][0]['damageOnEntry'] = 10
        self.assertTrue(any('damageOnEntry' in e for e in validate_game(self.game,self.content)))

    def test_unknown_contact_tag_is_rejected(self):
        self.game['tagRules'][0]['occupantTag'] = 'status.typo'
        self.assertTrue(any('status.typo' in e for e in validate_game(self.game,self.content)))

    def test_enemy_outside_actual_map_is_rejected(self):
        self.game['encounters'][0]['enemies'][0]['x'] = 11
        self.assertTrue(any('outside board' in e for e in validate_game(self.game,self.content)))

    def test_spawn_in_wall_is_rejected(self):
        self.game['encounters'][0]['playerSpawns'][0] = {'x':4,'y':2}
        self.assertTrue(any('blocked' in e for e in validate_game(self.game,self.content)))

    def test_duplicate_enemy_id_is_rejected(self):
        room = self.game['encounters'][0]
        room['enemies'][1]['id'] = room['enemies'][0]['id']
        self.assertTrue(any('duplicate' in e for e in validate_game(self.game,self.content)))

    def test_isolated_enemy_is_rejected(self):
        room = self.game['encounters'][0]
        enemy = room['enemies'][0]
        enemy['x'],enemy['y'] = 9,7
        room['tiles'] += [{'x':8,'y':7,'blocked':True,'tags':[]},{'x':9,'y':6,'blocked':True,'tags':[]}]
        self.assertTrue(any('isolated' in e for e in validate_game(self.game,self.content)))

    def test_exploration_requires_reachable_unique_door(self):
        room = self.game['encounters'][0]['exploration']
        room['points'][0]['x'] = 0
        self.assertTrue(any('unreachable' in e for e in validate_game(self.game,self.content)))

    def test_exploration_cache_requires_known_supply(self):
        self.game['encounters'][0]['exploration']['points'][1]['itemId'] = 'item.typo'
        self.assertTrue(any('item.typo' in e for e in validate_game(self.game,self.content)))

    def test_exploration_sector_ids_are_unique(self):
        self.game['encounters'][1]['exploration']['id'] = self.game['encounters'][0]['exploration']['id']
        self.assertTrue(any('duplicate' in e for e in validate_game(self.game,self.content)))

    def test_exploration_rejects_unknown_authoring_fields(self):
        self.game['encounters'][0]['exploration']['procedural'] = True
        self.assertTrue(any('procedural' in e for e in validate_game(self.game,self.content)))

    def test_recipe_unknown_ingredient_is_rejected(self):
        self.game['development']['recipes'][0]['ingredients'][0]['itemId'] = 'item.typo'
        self.assertTrue(any('item.typo' in e for e in validate_game(self.game,self.content)))

    def test_duplicate_recipe_ingredient_is_rejected(self):
        entries = self.game['development']['recipes'][0]['ingredients']
        entries.append(copy.deepcopy(entries[0]))
        self.assertTrue(any('duplicate' in e for e in validate_game(self.game,self.content)))

    def test_nonmonotonic_practice_thresholds_are_rejected(self):
        self.game['development']['practice']['useThresholds'] = [0, 8, 3]
        self.assertTrue(any('increase strictly' in e for e in validate_game(self.game,self.content)))

    def test_loot_source_requires_known_achievement(self):
        self.game['development']['lootBoxes'][0]['achievementId'] = 'achievement.typo'
        self.assertTrue(any('achievementId' in e for e in validate_game(self.game,self.content)))

    def test_scenario_requires_authored_boss(self):
        self.game['scenarios'][0]['bossId'] = 'boss.typo'
        self.assertTrue(any('bossId' in e for e in validate_game(self.game,self.content)))

    def test_rolling_route_cannot_teleport(self):
        scenario = next(s for s in self.game['scenarios'] if s['kind'] == 'swine')
        scenario['route'][1] = {'x': 0, 'y': 0}
        self.assertTrue(any('cardinal closed loop' in e for e in validate_game(self.game,self.content)))

    def test_scenario_spawns_cannot_overlap(self):
        room = self.game['scenarios'][0]['encounter']
        room['enemies'][0]['x'] = room['playerSpawns'][0]['x']
        room['enemies'][0]['y'] = room['playerSpawns'][0]['y']
        self.assertTrue(any('occupied spawn' in e for e in validate_game(self.game,self.content)))


if __name__ == '__main__':
    unittest.main()
