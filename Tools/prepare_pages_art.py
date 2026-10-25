"""Compact disposable Pages output; archive downloads use the pinned AI-Art revision."""
import argparse
import json
import os
from pathlib import Path
import re
import tempfile
from urllib.parse import urlsplit

PROJECT = Path(__file__).resolve().parents[1]
LIMIT = 1_000_000_000


def atomic_json(path, value):
    # Published fixtures may share hard links with source: replace, never truncate.
    descriptor, temporary = tempfile.mkstemp(prefix='.pages-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'w') as stream:
            stream.write(json.dumps(value, ensure_ascii=False, indent=2) + '\n')
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def prepare(root, lock_path=None):
    root = Path(root).absolute()
    if root.is_symlink() or root.resolve() != root:
        raise ValueError('Publication root must not contain symlinks.')
    if root.name != 'wwwroot' or root.parent.name != 'publish' or not (root / 'index.html').is_file():
        raise ValueError('Expected a disposable generated publish/wwwroot directory.')
    if root == PROJECT / 'Web/wwwroot' or (root / 'index.html').is_symlink():
        raise ValueError('Refusing to modify source assets.')
    lock = json.loads(Path(lock_path or PROJECT / 'art-assets.lock.json').read_text())
    commit = lock.get('commit', '')
    if lock.get('repository') != 'https://github.com/cehinds/AI-Art.git' or not re.fullmatch('[0-9a-f]{40}', commit) or commit == '0' * 40:
        raise ValueError('Expected a pinned canonical AI-Art lock.')
    packs = root / 'assets/style-packs'
    paths = sorted(packs.rglob('*'))
    if any(path.is_symlink() for path in paths):
        raise ValueError('Refusing symlinks in published art assets.')

    def archive_url(value, metadata):
        if not isinstance(value, str):
            return value
        parsed = urlsplit(value)
        if parsed.scheme:
            if parsed.hostname not in ('github.com', 'raw.githubusercontent.com') or not parsed.path.startswith('/cehinds/AI-Art/'):
                return value
            marker = '/dungeon-crawler-tactics/Web/wwwroot/assets/style-packs/'
            if marker not in parsed.path:
                return value
            relative = parsed.path.split(marker, 1)[1]
        else:
            target = (metadata.parent / value).resolve()
            if not target.is_relative_to(packs):
                raise ValueError(f'Archive escapes style packs: {value}')
            relative = target.relative_to(packs).as_posix()
        if not relative.endswith('.zip'):
            return value
        return f'https://raw.githubusercontent.com/cehinds/AI-Art/{commit}/dungeon-crawler-tactics/Web/wwwroot/assets/style-packs/{relative}'

    rewritten = 0
    for path in paths:
        if not path.is_file() or path.name not in ('manifest.json', 'index.json'):
            continue
        document = json.loads(path.read_text())
        before = json.dumps(document, sort_keys=True)
        if 'download' in document:
            document['download'] = archive_url(document['download'], path)
        for collection in document.get('collections', []):
            if 'download' in collection:
                collection['download'] = archive_url(collection['download'], path)
        for download in document.get('downloads', []):
            # Reusable index paths are relative to pack root, not its own directory.
            base = path.parent.parent / 'manifest.json' if path.parent.name == 'reusable' else path
            if 'path' in download:
                download['path'] = archive_url(download['path'], base)
        if json.dumps(document, sort_keys=True) != before:
            atomic_json(path, document)
            rewritten += 1
    removed = []
    for path in paths:
        if not path.is_file():
            continue
        parts = path.relative_to(packs).parts
        raw = 'reusable' in parts and 'raw' in parts and any(part.startswith('views-') for part in parts)
        if path.suffix.lower() == '.zip' or raw:
            removed.append(path.stat().st_size)
            path.unlink()
    size = sum(path.stat().st_size for path in root.rglob('*') if path.is_file())
    if size >= LIMIT:
        raise ValueError(f'Pages artifact exceeds conservative 1 GB limit: {size} bytes.')
    return {'published_bytes': size, 'removed_files': len(removed), 'removed_bytes': sum(removed), 'rewritten_metadata': rewritten, 'art_commit': commit}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.directory), sort_keys=True))
