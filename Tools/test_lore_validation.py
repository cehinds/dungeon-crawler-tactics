"""Semantic authoring checks for lore class trees, ranks, journey and home data."""
import copy
import json
import unittest
from validate_content import ROOT
from validate_game_data import validate_game


class LoreValidationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        folder = ROOT / 'UnityPackage/Runtime/Data'
        cls.baseline = json.loads((folder / 'game-content.json').read_text())
        cls.content = json.loads((folder / 'combat-content.json').read_text())

    def setUp(self):
        self.game = copy.deepcopy(self.baseline)

    def errors(self):
        return validate_game(self.game, self.content)

    def rejected(self, fragment):
        errors = self.errors()
        self.assertTrue(any(fragment in error for error in errors), errors)

    def profile(self):
        row = {'abilityId':'ability.strike', 'milestones':[
            {'rank':5, 'damageBonus':2, 'description':'Invented damage milestone.'}]}
        self.game['development']['practice']['abilityProfiles'] = [row]
        return row

    def home(self):
        space = {'id':'home.test_space', 'label':'Personal space', 'description':'Test base.',
                 'kind':'space', 'cost':100, 'costNote':'Invented test price.', 'priceBasis':'adaptation'}
        training = {'id':'home.test_training', 'label':'Training room', 'description':'Test service.',
                    'kind':'training', 'cost':10, 'costNote':'Invented test price.',
                    'priceBasis':'adaptation', 'prerequisiteId':'home.test_space'}
        self.game['home'] = {'label':'Test home', 'description':'Test housing.', 'economyNote':'Adapted economy.',
                             'availableFromFloor':4, 'startingGold':0, 'victoryGoldBase':10,
                             'victoryGoldPerFloor':2, 'upgrades':[space, training]}
        return self.game['home']

    def test_authored_catalog_and_valid_rank_home_fixtures(self):
        self.assertEqual([], self.errors())
        self.profile()
        self.home()
        self.assertEqual([], self.errors())

    def test_cast_modes_validate_bounds_and_unique_ids(self):
        profile = self.profile()
        mode = {'id': 'mode.economy', 'label': 'Economy', 'minimumRank': 5, 'manaCost': 3, 'damageBonus': -2}
        profile['castModes'] = [mode]
        self.assertEqual([], self.errors())
        for key, invalid in [('minimumRank', 21), ('manaCost', -1), ('damageBonus', -101)]:
            with self.subTest(key=key):
                previous = mode[key]
                mode[key] = invalid
                self.assertTrue(self.errors())
                mode[key] = previous
        profile['castModes'].append(copy.deepcopy(mode))
        self.rejected('duplicate')

    def test_cast_modes_require_damage_effect(self):
        profile = self.profile()
        profile['abilityId'] = 'ability.donut_heal_critter'
        profile['castModes'] = [{'id': 'mode.power', 'label': 'Power', 'minimumRank': 5, 'manaCost': 6, 'damageBonus': 4}]
        self.rejected('cast modes require a damage effect')

    def test_class_owner_must_exist_and_be_selectable(self):
        self.game['classSkillTrees'][0]['classId'] = 'class.missing'
        self.rejected('selectable class')
        self.game['classSkillTrees'][0]['classId'] = 'class.enemy_sludge'
        self.rejected('selectable class')

    def test_class_tree_owner_and_tree_ids_are_unique(self):
        self.game['classSkillTrees'][1]['classId'] = self.game['classSkillTrees'][0]['classId']
        self.rejected('classSkillTrees.1.classId: duplicate')
        self.game['classSkillTrees'][0]['id'] = self.game['skillTrees'][0]['id']
        self.rejected('skillTrees.8.id: duplicate')

    def test_node_ids_are_unique_across_personal_and_class_trees(self):
        self.game['classSkillTrees'][0]['nodes'][0]['id'] = self.game['skillTrees'][0]['nodes'][0]['id']
        self.rejected('duplicate')

    def test_class_prerequisite_cycles_are_rejected(self):
        nodes = self.game['classSkillTrees'][0]['nodes']
        nodes[0]['prerequisiteIds'] = [nodes[7]['id']]
        nodes[7]['prerequisiteIds'] = [nodes[0]['id']]
        self.rejected('prerequisite cycle')

    def test_class_grants_and_cross_tree_prerequisites_are_checked(self):
        node = self.game['classSkillTrees'][0]['nodes'][0]
        node['abilityIds'] = ['ability.missing']
        node['prerequisiteIds'] = [self.game['classSkillTrees'][1]['nodes'][0]['id']]
        self.rejected('unknown abilities ID')
        self.rejected('own tree')

    def test_unlock_at_maximum_level_has_a_threshold(self):
        self.game['progression']['skillUnlocks'][0]['level'] = len(self.game['progression']['xpThresholds'])
        self.assertEqual([], self.errors())

    def test_unknown_and_duplicate_rank_profiles(self):
        profile = self.profile()
        profile['abilityId'] = 'ability.missing'
        self.rejected('unknown abilities ID')
        profile['abilityId'] = 'ability.strike'
        self.game['development']['practice']['abilityProfiles'].append(copy.deepcopy(profile))
        self.rejected('duplicate')

    def test_milestones_require_unique_ranks_and_effects(self):
        profile = self.profile()
        profile['milestones'].append(copy.deepcopy(profile['milestones'][0]))
        self.rejected('milestones.1.rank: duplicate')
        profile['milestones'] = [{'rank':5, 'description':'No benefit.'}]
        self.rejected('supported benefit')
        profile['milestones'] = [{'rank':5, 'damageBonus':1}]
        self.rejected('description')

    def test_milestone_ranks_and_bonuses_are_bounded(self):
        profile = self.profile()
        profile['milestones'][0]['rank'] = 21
        self.rejected('rank')
        profile['milestones'][0]['rank'] = 5
        profile['milestones'][0]['damageBonus'] = 101
        self.rejected('damageBonus')

    def test_journey_order_availability_and_kind(self):
        floor = self.game['journey']['floors'][0]
        floor['number'] = 2
        self.rejected('ordered floor')
        floor['number'] = 1
        floor['available'] = False
        self.rejected('availability')
        floor['available'] = True
        floor['kind'] = 'bypass'
        self.rejected('kind')

    def test_journey_requires_eighteen_entries_and_bypass(self):
        self.game['journey']['floors'].pop()
        self.rejected('floors')
        self.game = copy.deepcopy(self.baseline)
        self.game['journey']['floors'][6]['kind'] = 'battle'
        self.rejected('kind')

    def test_journey_floor_mechanics_and_capture_count(self):
        floor = self.game['journey']['floors'][7]
        floor['mechanic'] = 'hunt'
        self.rejected('floor mechanic')
        floor['mechanic'] = 'capture'
        floor['captureCount'] = 5
        self.rejected('exactly six')
        floor['captureCount'] = 6
        floor['encounter']['enemies'].pop()
        self.rejected('exactly six')

    def test_required_route_and_beacons_are_lore_points(self):
        floor = self.game['journey']['floors'][3]
        floor['requiredPointIds'] = ['discovery.missing']
        self.rejected('route objective')
        floor['requiredPointIds'] = []
        self.rejected('one lever')
        floor = self.game['journey']['floors'][4]
        floor['requiredPointIds'].pop()
        self.rejected('four objectives')

    def test_journey_rooms_use_common_connectivity_validator(self):
        room = self.game['journey']['floors'][2]['encounter']
        enemy = room['enemies'][0]
        x,y = enemy['x'],enemy['y']
        neighbors = {(x-1,y),(x+1,y),(x,y-1),(x,y+1)}
        room['tiles'] = [t for t in room['tiles'] if (t['x'],t['y']) not in neighbors]
        room['tiles'] += [{'x':nx,'y':ny,'blocked':True,'tags':[]} for nx,ny in neighbors]
        self.rejected('isolated by walls')

    def test_journey_route_objective_must_be_reachable(self):
        floor = self.game['journey']['floors'][3]
        point = next(p for p in floor['encounter']['exploration']['points'] if p['id'] in floor['requiredPointIds'])
        point['x'],point['y'] = 0,0
        self.rejected('unreachable')

    def test_home_requires_base_space_and_real_prerequisites(self):
        home = self.home()
        home['upgrades'][1]['prerequisiteId'] = 'home.missing'
        self.rejected('unknown or ineligible home prerequisite')
        home['upgrades'][1].pop('prerequisiteId')
        self.rejected('must require the personal space')
        home['upgrades'].pop(0)
        self.rejected('exactly one personal space')

    def test_home_prerequisite_cycles_are_rejected(self):
        home = self.home()
        home['upgrades'][0]['prerequisiteId'] = home['upgrades'][1]['id']
        self.rejected('home prerequisite cycle')

    def test_unknown_home_prices_and_generic_club_pass_are_forbidden(self):
        home = self.home()
        upgrade = home['upgrades'][1]
        upgrade['priceBasis'] = 'unknown'
        self.rejected('unknown price cannot be purchasable')
        upgrade['kind'] = 'club'
        self.rejected('club admission cannot be sold')
        upgrade.update(purchasable=False, cost=0, eligibilityReason='Earn personal admission.')
        self.assertEqual([], self.errors())

    def test_home_benefits_and_unavailable_explanations(self):
        home = self.home()
        home['upgrades'][1]['craftOutputBonus'] = 1
        self.rejected('only tools')
        home['upgrades'][1].update(craftOutputBonus=0,purchasable=False)
        self.rejected('eligibility explanation')
        home['upgrades'][1].update(eligibilityReason='Unknown availability.',sourceIds=[''])
        self.rejected('source references cannot be empty')


if __name__ == '__main__':
    unittest.main()
