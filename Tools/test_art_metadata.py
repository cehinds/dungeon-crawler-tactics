"""Canonical metadata integration preserves strict legacy art validation."""
import copy
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

import art_metadata
from build_book_tiles import existing_sidecars
from build_style_packs import PackError


class ArtMetadataIntegrationTests(unittest.TestCase):
    def test_legacy_fixture_does_not_require_new_art_tools(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(art_metadata, 'helper', side_effect=AssertionError('unexpected canonical helper')):
            document={'id':'legacy','assets':[]};self.assertEqual(art_metadata.enrich_expected(copy.deepcopy(document),Path(tmp)),document)

    def test_tagged_library_requires_canonical_helper(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp);(root/'art-assets.lock.json').write_text(json.dumps({'commit':'a'*40}));pack=root/'assets/pocket-dungeon';(pack/'reusable').mkdir(parents=True);(pack/'reusable/index.json').write_text('{"assets":[]}')
            art_metadata.helper.cache_clear()
            with patch.object(art_metadata,'ROOT',root):
                with self.assertRaisesRegex(ValueError,'requires the pinned AI-Art checkout'):art_metadata.enrich_expected({'assets':[]},pack)
            art_metadata.helper.cache_clear()

    def test_sidecars_must_match_catalog_and_resolve_to_exact_png(self):
        with tempfile.TemporaryDirectory() as tmp:
            pack=Path(tmp)/'pocket-dungeon';directory=pack/'kit';(directory/'components').mkdir(parents=True);(pack/'reusable').mkdir();(directory/'components/tile.png').write_bytes(b'fixture')
            record={'id':'tile','metadata_path':'kit/components/tile.json','image':{'path':'kit/components/tile.png'},'tags':['ground']}
            index=pack/'reusable/index.json';index.write_text(json.dumps({'assets':[record]}));sidecar=directory/'components/tile.json';sidecar.write_text(json.dumps(record));manifest={'assets':[{'id':'tile','file':'components/tile.png'}]}
            art_metadata.catalog.cache_clear();self.assertEqual(existing_sidecars(directory,manifest),{'components/tile.json'})
            sidecar.write_text(json.dumps({**record,'tags':['tampered']}))
            with self.assertRaisesRegex(PackError,'differs from canonical'):existing_sidecars(directory,manifest)
            record['image']['path']='../outside.png';index.write_text(json.dumps({'assets':[record]}));sidecar.write_text(json.dumps(record));art_metadata.catalog.cache_clear()
            with self.assertRaisesRegex(PackError,'Path escapes pack'):existing_sidecars(directory,manifest)


if __name__=='__main__':unittest.main()
