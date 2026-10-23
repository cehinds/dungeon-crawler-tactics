import copy
import json
import sys
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'Tools'))
from validate_content import validate
from validate_game_data import validate_game


class RevampContentValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        data_dir = ROOT / 'UnityPackage/Runtime/Data'
        cls.content = json.loads((data_dir / 'combat-content.json').read_text())
        cls.game = json.loads((data_dir / 'game-content.json').read_text())

    def test_identity_actions_and_roster_references_are_valid(self):
        self.assertEqual([], validate(self.content))
        self.assertEqual([], validate_game(self.game, self.content))

    def test_push_requires_positive_distance(self):
        invalid = copy.deepcopy(self.content)
        action = next(a for a in invalid['abilities'] if a['id'] == 'ability.carl_powerful_strike')
        action['effects'][1]['amount'] = 0
        self.assertTrue(any('amount' in error or 'minimum' in error for error in validate(invalid)))

    def test_nondeployable_advisor_cannot_be_selected(self):
        invalid = copy.deepcopy(self.game)
        advisor = next(r for r in invalid['roster'] if r['id'] == 'crawler.mordecai')
        advisor['selected'] = True
        self.assertTrue(any('non-deployable' in error for error in validate_game(invalid, self.content)))

    def test_unknown_innate_action_is_rejected(self):
        invalid = copy.deepcopy(self.game)
        carl = next(r for r in invalid['roster'] if r['id'] == 'crawler.carl')
        carl['innateAbilityIds'].append('ability.not_in_catalog')
        self.assertTrue(any('unknown abilities ID' in error for error in validate_game(invalid, self.content)))

    def test_default_party_uses_distinct_identity_classes_and_legacy_mappings(self):
        expected = {
            'crawler.carl': ('class.compensated_anarchist', 'class.brawler', (42, 12, 4)),
            'crawler.donut': ('class.former_child_actor', 'class.stormcaller', (30, 18, 5)),
            'crawler.katia': ('class.doppelganger', 'class.pyromancer', (44, 10, 4)),
            'crawler.mongo': ('class.raptor_companion', 'class.beastmaster', (30, 8, 5)),
        }
        stats = {s['classId']: (s['hp'], s['energy'], s['move']) for s in self.game['classStats']}
        classes = {c['id']: c['abilityIds'] for c in self.content['classes']}
        for character_id, (class_id, legacy_id, expected_stats) in expected.items():
            member = next(r for r in self.game['roster'] if r['id'] == character_id)
            self.assertEqual((class_id, legacy_id), (member['classId'], member['legacyClassId']))
            self.assertEqual(expected_stats, stats[class_id])
            personal_extras = {'crawler.carl': ['ability.carl_tripwire']}
            self.assertEqual(classes[class_id] + personal_extras.get(character_id, []), member['innateAbilityIds'])

    def test_clockwork_requires_complete_bounded_summon_configuration(self):
        invalid = copy.deepcopy(self.content)
        effect = next(a for a in invalid['abilities'] if a['id'] == 'ability.donut_clockwork_triplicate')['effects'][0]
        del effect['summonRounds']
        self.assertTrue(any('summonRounds' in error for error in validate(invalid)))
        effect['summonRounds'] = 100
        self.assertTrue(any('summonRounds' in error for error in validate(invalid)))

    def test_specialty_rejects_enemy_only_kits(self):
        invalid = copy.deepcopy(self.game)
        donut = next(r for r in invalid['roster'] if r['id'] == 'crawler.donut')
        donut['specialtyClassIds'] = [next(c['id'] for c in self.content['classes'] if not c.get('playerSelectable', True))]
        self.assertTrue(any('enemy-only specialty' in error for error in validate_game(invalid, self.content)))

    def test_magic_missile_is_arcane_and_not_a_lightning_setup(self):
        magic_missile = next(a for a in self.content['abilities'] if a['id'] == 'ability.donut_magic_missile')
        self.assertEqual(['element.arcane'], magic_missile['incomingTags'])
        self.assertFalse(any('element.arcane' in r['incoming']['all'] for r in self.content['reactions']))


if __name__ == '__main__':
    unittest.main()
