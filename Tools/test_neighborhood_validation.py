"""Original neighborhood authoring contracts and generation preservation."""
import copy
import json
import unittest
from validate_content import ROOT
from validate_game_data import validate_game
from build_lore_catalog import build


class NeighborhoodValidationTests(unittest.TestCase):
    def setUp(self):
        data = ROOT / 'UnityPackage/Runtime/Data'
        self.game = json.loads((data / 'game-content.json').read_text())
        self.content = json.loads((data / 'combat-content.json').read_text())

    def invalid(self, text):
        self.assertTrue(any(text in e for e in validate_game(self.game, self.content)))

    def test_original_neighborhood_has_free_routes_and_three_challenges(self):
        self.assertEqual([], validate_game(self.game, self.content))
        n = self.game['neighborhood']
        self.assertEqual(3, len(n['challenges']))
        self.assertTrue(all(any(not o['abilityId'] and not o['costCount'] for o in i['options']) for i in n['interactions']))
        self.assertFalse(self.game['journey']['floors'][2]['requiredPointIds'])

    def test_missing_sector_reference(self):
        self.game['neighborhood']['sectorId'] = 'sector.missing'
        self.invalid('unknown journey sectorId')

    def test_missing_fallback(self):
        for o in self.game['neighborhood']['interactions'][0]['options']:
            o['abilityId'] = 'ability.strike'
        self.invalid('free untrained fallback')

    def test_interaction_must_reference_lore_point(self):
        self.game['neighborhood']['interactions'][0]['pointId'] = 'discovery.journey_3_door'
        self.invalid('authored lore point')

    def test_bad_challenge_option_reference(self):
        self.game['neighborhood']['challenges'][0]['optionId'] = 'option.missing'
        self.invalid('unknown interaction optionId')

    def test_bad_reward_reference_and_count(self):
        o = self.game['neighborhood']['interactions'][0]['options'][0]
        o['rewardItemId'] = 'item.missing'
        self.invalid('unknown items ID')
        o['rewardItemId'] = ''
        self.invalid('positive count')

    def test_legacy_layout_is_bounded_and_validated(self):
        legacy = self.game['neighborhood']['legacyExploration']
        self.assertEqual((11, 9), (legacy['width'], legacy['height']))
        self.assertEqual('sector.journey_3', legacy['id'])
        legacy['points'][0]['x'] = 0
        self.invalid('unreachable')

    def test_legacy_layout_must_match_sector(self):
        self.game['neighborhood']['legacyExploration']['id'] = 'sector.other'
        self.invalid('must match the current sectorId')

    def test_unknown_schema_fields_rejected(self):
        self.game['neighborhood']['audienceMultiplier'] = 999
        self.invalid('audienceMultiplier')

    def test_lore_generator_preserves_neighborhood_and_all_floors(self):
        research = json.loads((ROOT / 'Research/classes-skills.json').read_text())
        _, regenerated = build(self.content, self.game, research)
        self.assertEqual(self.game['neighborhood'], regenerated['neighborhood'])
        self.assertEqual(self.game['journey'], regenerated['journey'])


if __name__ == '__main__':
    unittest.main()
