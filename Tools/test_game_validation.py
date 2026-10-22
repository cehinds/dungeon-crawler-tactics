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


if __name__ == '__main__':
    unittest.main()
