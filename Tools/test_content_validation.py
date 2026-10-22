import copy
import json
import unittest

from validate_content import ROOT, no_duplicate_keys, validate


class ContentValidationTests(unittest.TestCase):
    def setUp(self):
        self.content = json.loads((ROOT / "UnityPackage/Runtime/Data/starter-content.json").read_text())

    def test_seed_is_valid(self):
        self.assertEqual([], validate(self.content))

    def test_unknown_json_field_is_not_silently_ignored(self):
        self.content["abilities"][0]["costt"] = 50
        self.assertTrue(any("costt" in error for error in validate(self.content)))

    def test_missing_query_clause_is_not_silently_defaulted(self):
        del self.content["reactions"][0]["target"]["none"]
        self.assertTrue(validate(self.content))

    def test_unknown_reference_reports_location(self):
        self.content["classes"][0]["abilityIds"].append("ability.typo")
        self.assertTrue(any("classes.0.abilityIds" in error and "ability.typo" in error for error in validate(self.content)))

    def test_duplicate_id_rejected(self):
        self.content["tags"].append(copy.deepcopy(self.content["tags"][0]))
        self.assertTrue(any("duplicate" in error for error in validate(self.content)))

    def test_integer_overflow_rejected(self):
        self.content["abilities"][0]["effects"][0]["amount"] = 2**31
        self.assertTrue(validate(self.content))

    def test_contradictory_query_rejected(self):
        self.content["reactions"][0]["target"]["none"] = ["surface.oil"]
        self.assertTrue(any("conflict" in error for error in validate(self.content)))

    def test_duplicate_json_property_rejected(self):
        with self.assertRaises(ValueError):
            json.loads('{"cost": 1, "cost": 2}', object_pairs_hook=no_duplicate_keys)

    def test_damage_reduction_is_optional_and_nonnegative(self):
        self.content["reactions"][0]["damageReduction"] = 6
        self.assertEqual([], validate(self.content))
        self.content["reactions"][0]["damageReduction"] = -1
        self.assertTrue(validate(self.content))
        self.content["reactions"][0]["damageReduction"] = 2**31
        self.assertTrue(validate(self.content))

    def test_boolean_not_accepted_as_integer(self):
        self.content["abilities"][0]["cost"] = True
        self.assertTrue(validate(self.content))


if __name__ == "__main__":
    unittest.main()
