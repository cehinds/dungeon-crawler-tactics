"""Validate and package the authored PNG room kit for download and Unity import.

Run after build_room_kit.py. Source atlases stay in the repository; the download
contains only standalone sprites, placement metadata and the usage guide.
"""
import json
from pathlib import Path
import shutil
from zipfile import ZipFile, ZIP_DEFLATED

from PIL import Image

ROOT = Path(__file__).resolve().parents[1]
KIT = ROOT / 'Web/wwwroot/assets/room-kit'
UNITY = ROOT / 'UnityPackage/Runtime/Resources/RoomKit'


def package():
    manifest_path = KIT / 'manifest.json'
    manifest = json.loads(manifest_path.read_text())
    assert manifest['tile'] == {'width': 128, 'height': 64}, 'Expected a 2:1 isometric grid'
    seen = set()
    files = [manifest_path]
    for asset in manifest['assets']:
        assert asset['id'] not in seen, f"Duplicate asset: {asset['id']}"
        seen.add(asset['id'])
        path = (KIT / asset['file']).resolve()
        assert path.is_relative_to(KIT.resolve()), 'Asset path must stay inside the kit'
        with Image.open(path) as sprite:
            assert sprite.mode == 'RGBA', f'{path.name}: expected RGBA'
            assert sprite.size == (asset['width'], asset['height']), f'{path.name}: dimensions differ'
            alpha = sprite.getchannel('A')
            assert alpha.getextrema()[0] == 0 and alpha.getbbox(), f'{path.name}: transparency/content missing'
        assert asset['layer'] in ['floor', 'surface', 'structure', 'prop', 'overlay']
        assert all(isinstance(asset['anchor'][axis], (int, float)) for axis in ['x', 'y'])
        assert isinstance(asset['blocksMovement'], bool)
        files.append(path)
    guide = ROOT / 'Docs/RoomKit.md'
    assert guide.exists(), 'Room kit guide is required'
    UNITY.mkdir(parents=True, exist_ok=True)
    for path in files:
        target = UNITY / path.relative_to(KIT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(path, target)
    archive_path = KIT / 'room-kit.zip'
    with ZipFile(archive_path, 'w', ZIP_DEFLATED) as archive:
        for path in files:
            archive.write(path, path.relative_to(KIT))
        archive.write(guide, 'README.md')
    print(f'Validated {len(seen)} transparent PNG assets. Created {archive_path.relative_to(ROOT)}')
    print('Copied PNGs and manifest into UnityPackage/Runtime/Resources/RoomKit.')


if __name__ == '__main__':
    package()
