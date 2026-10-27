import json
import os
from pathlib import Path
import tempfile
import unittest
from prepare_pages_art import prepare, publication_inventory, publication_exclusion


class MultipartPublicationTests(unittest.TestCase):
    def test_archives_remote_and_source_hardlinks_preserved(self):
        with tempfile.TemporaryDirectory() as directory:
            base = Path(directory)
            root = base / 'publish/wwwroot'
            root.mkdir(parents=True)
            (root / 'index.html').write_text('page')
            pack = root / 'assets/style-packs/pocket-dungeon'
            downloads = pack / 'reusable/downloads'
            downloads.mkdir(parents=True)
            resources = ['library.zip.parts.json', 'library.zip.part-001', 'assemble_archive_parts.py', 'small.zip']
            for name in resources:
                (downloads / name).write_text('original-' + name)
            source = base / 'original-index.json'
            document = {'downloads': [{'format': 'multipart-zip', 'file': 'library.zip.parts.json', 'path': 'reusable/downloads/library.zip.parts.json', 'sha256': 'manifest-hash', 'parts': [{'number': 1, 'file': 'library.zip.part-001', 'path': 'reusable/downloads/library.zip.part-001', 'sha256': 'part-hash'}], 'assembly_tool': {'file': 'assemble_archive_parts.py', 'path': 'reusable/downloads/assemble_archive_parts.py'}}]}
            source.write_text(json.dumps(document))
            index = pack / 'reusable/index.json'
            os.link(source, index)
            native = pack / 'native.png'
            native.write_bytes(b'native')
            guide = root / 'assets/rebuild-guide.json'
            guide.write_bytes(b'{"kind":"rebuild-guide"}\n')
            evidence = root / 'assets/release-evidence/replay-summary.json'
            evidence.parent.mkdir()
            evidence.write_bytes(b'{"status":"pending"}\n')
            lock = base / 'lock.json'
            lock.write_text(json.dumps({'repository': 'https://github.com/cehinds/AI-Art.git', 'commit': 'a' * 40}))
            result = prepare(root, lock)
            updated = json.loads(index.read_text())['downloads'][0]
            for value in [updated['path'], updated['file'], updated['parts'][0]['path'], updated['assembly_tool']['path']]:
                self.assertTrue(value.startswith('https://raw.githubusercontent.com/cehinds/AI-Art/' + 'a' * 40 + '/'))
            self.assertEqual(updated['parts'][0]['file'], 'library.zip.part-001')
            self.assertEqual(updated['file'], updated['path'])
            self.assertEqual(updated['sha256'], 'manifest-hash')
            self.assertEqual(json.loads(source.read_text()), document)
            self.assertTrue(native.exists())
            self.assertEqual(guide.read_bytes(), b'{"kind":"rebuild-guide"}\n')
            self.assertEqual(evidence.read_bytes(), b'{"status":"pending"}\n')
            self.assertTrue(all(not (downloads / name).exists() for name in resources))
            self.assertEqual(result['removed_files'], 4)
            self.assertEqual(prepare(root, lock)['rewritten_metadata'], 0)

    def test_lean_selection_matches_pruning(self):
        self.assertEqual(publication_exclusion('reusable/__pycache__/replay.cpython-312.pyc'), 'runtime-python-cache')
        self.assertEqual(publication_exclusion('replay-inputs/receipts/a.json'), 'offline-replay-inputs')
        self.assertEqual(publication_exclusion('book-tiles/ink-and-lanterns/reusable/index.json'), 'remote-library')
        self.assertIsNone(publication_exclusion('release-evidence/a.json'))
        self.assertIsNone(publication_exclusion('rebuild-guide.json'))
        self.assertIsNone(publication_exclusion('style-packs/pocket-dungeon/reusable/index.json'))
        with tempfile.TemporaryDirectory() as directory:
            assets = Path(directory)
            for name in ['release-evidence/a.json', 'replay-inputs/raw.png', 'style-packs/pocket-dungeon/reusable/downloads/a.zip.part-001']:
                path = assets / name
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(b'bytes')
            plan = publication_inventory(assets)
            self.assertEqual(plan['survivors'], [{'path': 'release-evidence/a.json', 'bytes': 5}])
            self.assertEqual(sum(plan['excluded_bytes_by_reason'].values()), 10)

    def test_refuses_source_directory(self):
        with tempfile.TemporaryDirectory() as directory:
            with self.assertRaises(ValueError):
                prepare(Path(directory))


if __name__ == '__main__':
    unittest.main()
