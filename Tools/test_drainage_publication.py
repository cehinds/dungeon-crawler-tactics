"""The standalone expansion must use Pages' existing pinned-download contract."""
import json
import os
from pathlib import Path
import tempfile
import unittest
from prepare_pages_art import prepare

class DrainagePublicationTests(unittest.TestCase):
    def test_expansion_zip_pruned_and_download_pinned(self):
        with tempfile.TemporaryDirectory() as temporary:
            base=Path(temporary);root=base/'publish/wwwroot';root.mkdir(parents=True)
            (root/'index.html').write_text('fixture')
            expansion=root/'assets/expansions/drainage-channels-v1';expansion.mkdir(parents=True)
            source=base/'source-catalog.json';source.write_text(json.dumps({'download':'drainage-channels-v1.zip','assets':[{'image':{'path':'tiles/straight/top.png'}}]}))
            os.link(source,expansion/'catalog.json')
            (expansion/'drainage-channels-v1.zip').write_bytes(b'zip fixture')
            tile=expansion/'tiles/straight/top.png';tile.parent.mkdir(parents=True);tile.write_bytes(b'native fixture')
            lock=base/'lock.json';lock.write_text(json.dumps({'repository':'https://github.com/cehinds/AI-Art.git','commit':'a'*40}))
            prepare(root,lock)
            catalog=json.loads((expansion/'catalog.json').read_text())
            expected='https://raw.githubusercontent.com/cehinds/AI-Art/'+'a'*40+'/dungeon-crawler-tactics/Web/wwwroot/assets/expansions/drainage-channels-v1/drainage-channels-v1.zip'
            self.assertEqual(catalog['download'],expected)
            self.assertFalse((expansion/'drainage-channels-v1.zip').exists())
            self.assertEqual(catalog['assets'][0]['image']['path'],'tiles/straight/top.png')
            self.assertEqual(json.loads(source.read_text())['download'],'drainage-channels-v1.zip')
            self.assertTrue(tile.exists())

if __name__=='__main__':unittest.main()
