"""Compact disposable Pages output; archive downloads use the pinned AI-Art revision."""
import argparse
import json
import os
from pathlib import Path, PurePosixPath
import re
import tempfile
from urllib.parse import urlsplit, quote

PROJECT = Path(__file__).resolve().parents[1]
LIMIT = 1_000_000_000
REMOTE_LIBRARIES = {
    'style-packs/dungeon-after-dark', 'style-packs/ink-and-lanterns',
    'book-tiles/dungeon-after-dark', 'book-tiles/ink-and-lanterns',
    'book-tiles/pocket-dungeon', 'reusable-gameplay',
}


def publication_exclusion(relative):
    """Shared pre-copy selection and final prune policy, relative to assets/."""
    relative = PurePosixPath(relative)
    parts = relative.parts
    if '__pycache__' in parts or relative.suffix in ('.pyc', '.pyo'):
        return 'runtime-python-cache'
    if parts and parts[0] == 'replay-inputs':
        return 'offline-replay-inputs'
    for library in REMOTE_LIBRARIES:
        directory = PurePosixPath(library)
        if library != 'reusable-gameplay':
            directory /= 'reusable'
        if relative == directory or directory in relative.parents:
            return 'remote-library'
    if (re.search(r'\.zip(?:\.parts\.json|\.part-\d+)?$', relative.name)
            or (relative.name == 'assemble_archive_parts.py' and 'downloads' in parts)):
        return 'remote-download'
    if 'reusable' in parts and 'raw' in parts and any(p.startswith('views-') for p in parts):
        return 'offline-generation-raw'
    return None


def publication_inventory(assets):
    """Read-only exact survivor plan; never follow symlinks."""
    survivors, excluded = [], {}
    for path in sorted(Path(assets).rglob('*')):
        if path.is_symlink():
            raise ValueError('Refusing symlinks in published art assets.')
        if not path.is_file():
            continue
        relative = path.relative_to(assets).as_posix()
        reason = publication_exclusion(relative)
        if reason:
            excluded[reason] = excluded.get(reason, 0) + path.stat().st_size
        else:
            survivors.append({'path': relative, 'bytes': path.stat().st_size})
    return {'survivors': survivors, 'survivor_bytes': sum(r['bytes'] for r in survivors),
            'excluded_bytes_by_reason': excluded}


def compact_libraries(root, commit):
    """Keep canonical offline paths; relocate only the published registry."""
    assets = root / 'assets'
    registry = assets / 'reusable-library.json'
    if not registry.is_file():
        return 0, []
    document = json.loads(registry.read_text())
    if document.get('schema_version', document.get('version')) != 1 or not isinstance(document.get('libraries'), list):
        raise ValueError('Unsupported reusable library registry.')
    prefix = f'https://raw.githubusercontent.com/cehinds/AI-Art/{commit}/dungeon-crawler-tactics/Web/wwwroot/assets/'

    def relative(value):
        if not isinstance(value, str):
            raise ValueError('Library paths must be strings.')
        parsed = urlsplit(value)
        if parsed.scheme:
            marker = '/dungeon-crawler-tactics/Web/wwwroot/assets/'
            if parsed.scheme != 'https' or parsed.hostname != 'raw.githubusercontent.com' or not parsed.path.startswith('/cehinds/AI-Art/') or marker not in parsed.path:
                raise ValueError('Library URLs must use the canonical art repository.')
            value = parsed.path.split(marker, 1)[1]
        value = value.rstrip('/')
        path = PurePosixPath(value)
        if not value or path.is_absolute() or path.as_posix() != value or '\\' in value or ':' in value or any(part in ('.', '..') for part in path.parts):
            raise ValueError(f'Unsafe library path: {value}')
        return path

    removed, count = [], 0
    for entry in document['libraries']:
        base, index = relative(entry.get('base')), relative(entry.get('index'))
        if base.as_posix() not in REMOTE_LIBRARIES:
            continue
        if index != base / 'reusable/index.json':
            raise ValueError(f'Unexpected library index: {index}')
        directory = assets / (base if str(base) == 'reusable-gameplay' else base / 'reusable')
        if any(path.is_symlink() for path in [directory, *directory.parents] if path.is_relative_to(root)):
            raise ValueError('Refusing symlinks in reusable libraries.')
        paths = sorted(directory.rglob('*')) if directory.exists() else []
        if any(path.is_symlink() for path in paths):
            raise ValueError('Refusing symlinks in reusable libraries.')
        for path in paths:
            if path.is_file():
                removed.append(path.stat().st_size)
                path.unlink()
        entry['base'] = prefix + quote(base.as_posix(), safe='/') + '/'
        entry['index'] = prefix + quote(index.as_posix(), safe='/')
        count += 1
    if count:
        atomic_json(registry, document)
    return count, removed


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
    assets = root / 'assets'
    paths = sorted(assets.rglob('*'))
    if any(path.is_symlink() for path in paths):
        raise ValueError('Refusing symlinks in published art assets.')

    def archive_url(value, metadata):
        if not isinstance(value, str):
            return value
        parsed = urlsplit(value)
        if parsed.scheme:
            if parsed.hostname not in ('github.com', 'raw.githubusercontent.com') or not parsed.path.startswith('/cehinds/AI-Art/'):
                return value
            marker = '/dungeon-crawler-tactics/Web/wwwroot/assets/'
            if marker not in parsed.path:
                return value
            relative = parsed.path.split(marker, 1)[1]
        else:
            target = (metadata.parent / value).resolve()
            if not target.is_relative_to(assets):
                raise ValueError(f'Archive escapes assets: {value}')
            relative = target.relative_to(assets).as_posix()
        downloadable = (re.search(r'\.zip(?:\.parts\.json|\.part-\d+)?$', relative)
                        or relative.endswith('/assemble_archive_parts.py'))
        if not downloadable:
            return value
        return f'https://raw.githubusercontent.com/cehinds/AI-Art/{commit}/dungeon-crawler-tactics/Web/wwwroot/assets/{relative}'

    rewritten = 0
    for path in paths:
        if not path.is_file() or path.name not in ('manifest.json', 'index.json', 'catalog.json'):
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
            if 'file' in download:
                download['file'] = archive_url(download.get('path', download['file']), base)
            for part in download.get('parts', []):
                if 'path' in part:
                    part['path'] = archive_url(part['path'], base)
            helper = download.get('assembly_tool', {})
            if 'path' in helper:
                helper['path'] = archive_url(helper['path'], base)
        if json.dumps(document, sort_keys=True) != before:
            atomic_json(path, document)
            rewritten += 1
    removed = []
    for path in paths:
        if not path.is_file():
            continue
        reason = publication_exclusion(path.relative_to(assets).as_posix())
        # compact_libraries also relocates registry entries after this prune.
        if reason:
            removed.append(path.stat().st_size)
            path.unlink()
    remote_libraries, library_removed = compact_libraries(root, commit)
    removed.extend(library_removed)
    size = sum(path.stat().st_size for path in root.rglob('*') if path.is_file())
    if size >= LIMIT:
        raise ValueError(f'Pages artifact exceeds conservative 1 GB limit: {size} bytes.')
    return {'published_bytes': size, 'removed_files': len(removed), 'removed_bytes': sum(removed), 'rewritten_metadata': rewritten, 'remote_libraries': remote_libraries, 'art_commit': commit, 'offline_replay_inputs': f'https://github.com/cehinds/AI-Art/tree/{commit}/dungeon-crawler-tactics/Web/wwwroot/assets/replay-inputs', 'offline_evidence_note': 'Guide/evidence bytes are preserved; offline input paths refer to the canonical pinned Art repository, not the compact Pages artifact.'}


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('directory', type=Path)
    args = parser.parse_args()
    print(json.dumps(prepare(args.directory), sort_keys=True))
