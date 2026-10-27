import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch
from zipfile import ZipFile, BadZipFile
from PIL import Image
import package_room_kit as kit


class RoomKitCheckTests(unittest.TestCase):
    def fixture(self, root):
        directory = root / 'kit'
        directory.mkdir()
        (root / 'Docs').mkdir()
        (root / 'Docs/RoomKit.md').write_text('guide')
        image = Image.new('RGBA', (2, 2))
        image.putpixel((0, 0), (255, 0, 0, 255))
        image.save(directory / 'tile.png')
        (directory / 'manifest.json').write_text(json.dumps({'tile': {'width': 128, 'height': 64}, 'assets': [{'id': 'tile', 'file': 'tile.png', 'width': 2, 'height': 2, 'layer': 'floor', 'anchor': {'x': 0, 'y': 0}, 'blocksMovement': False}]}))
        return directory

    def test_check_preserves_zip_and_does_not_rebuild_unity(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            directory = self.fixture(root)
            with patch.multiple(kit, ROOT=root, KIT=directory, UNITY=root / 'unity'):
                kit.package()
                archive = directory / 'room-kit.zip'
                before = hashlib.sha256(archive.read_bytes()).hexdigest()
                with patch.object(kit.shutil, 'copy2', side_effect=AssertionError('check must not copy')):
                    kit.package(check=True)
                self.assertEqual(hashlib.sha256(archive.read_bytes()).hexdigest(), before)

    def test_missing_stale_and_corrupt_archive_members_are_rejected(self):
        for failure in ['missing', 'stale', 'corrupt']:
            with self.subTest(failure=failure), tempfile.TemporaryDirectory() as tmp:
                root = Path(tmp)
                directory = self.fixture(root)
                with patch.multiple(kit, ROOT=root, KIT=directory, UNITY=root / 'unity'):
                    kit.package()
                    archive = directory / 'room-kit.zip'
                    with ZipFile(archive) as source:
                        members = {name: source.read(name) for name in source.namelist()}
                    if failure == 'corrupt':
                        archive.write_bytes(b'not a ZIP')
                    else:
                        if failure == 'missing':
                            del members['tile.png']
                        else:
                            members['tile.png'] = b'stale'
                        with ZipFile(archive, 'w') as output:
                            for name, body in members.items():
                                output.writestr(name, body)
                    with self.assertRaises((AssertionError, BadZipFile)):
                        kit.package(check=True)
