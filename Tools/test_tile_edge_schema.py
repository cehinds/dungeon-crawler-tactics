"""Ensure every authored tile can be consumed using the published edge schema."""
import json
from pathlib import Path
import unittest

from jsonschema import Draft202012Validator


class TileEdgeSchemaTests(unittest.TestCase):
    def test_authored_tile_edges(self):
        root = Path(__file__).resolve().parents[1]
        schema = json.loads((root / 'Tools/tile-edge.schema.json').read_text())
        Draft202012Validator.check_schema(schema)
        validator = Draft202012Validator(schema)
        inventory = json.loads((root / 'Docs/BookLocationTiles/inventory.json').read_text())
        for kit in inventory['kits']:
            for asset in kit['assets']:
                with self.subTest(asset=asset['id']):
                    validator.validate(asset['edges'])


if __name__ == '__main__':
    unittest.main()
