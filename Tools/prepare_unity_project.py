"""Copy canonical source/art into an immediately openable Unity project.

Run again after source edits. Existing scenes, .meta files and project settings
are preserved; matching managed source files are refreshed from UnityPackage.
"""
import json
from pathlib import Path
import shutil

ROOT = Path(__file__).resolve().parents[1]
PROJECT = ROOT / 'UnityProject'


def prepare():
    source = ROOT / 'UnityPackage'
    destination = PROJECT / 'Assets/DungeonCrawlerTactics'
    destination.mkdir(parents=True, exist_ok=True)
    copied = 0
    for file in sorted(source.rglob('*')):
        if not file.is_file() or file.suffix == '.meta':
            continue
        target = destination / file.relative_to(source)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(file, target)
        copied += 1
    settings = PROJECT / 'ProjectSettings'
    settings.mkdir(exist_ok=True)
    version = settings / 'ProjectVersion.txt'
    if not version.exists():
        version.write_text('m_EditorVersion: 6000.0.23f1\n')
    packages = PROJECT / 'Packages'
    packages.mkdir(exist_ok=True)
    manifest = packages / 'manifest.json'
    if not manifest.exists():
        manifest.write_text(json.dumps({'dependencies': {
            'com.unity.modules.audio': '1.0.0',
            'com.unity.modules.imageconversion': '1.0.0',
            'com.unity.modules.imgui': '1.0.0',
            'com.unity.modules.jsonserialize': '1.0.0',
            'com.unity.modules.ui': '1.0.0'
        }}, indent=2) + '\n')
    print(f'Prepared {PROJECT}: {copied} source, data and art files.')
    print('Open this folder with Unity 6. Unity generates metadata and default settings on import.')


if __name__ == '__main__':
    prepare()
