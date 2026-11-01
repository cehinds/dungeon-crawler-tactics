#!/usr/bin/env python3
"""Package a frozen layer-kit receipt; split only archives above GitHub's limit."""
import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
import zipfile

NAME = 'top-down-layer-kit.zip'
DEFAULT = Path(__file__).resolve().parents[1] / 'Web/wwwroot/assets/top-down-layer-kit'


def digest(path):
    value = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b''): value.update(block)
    return value.hexdigest()


def download_artifact(name):
    return name in (NAME, NAME + '.parts.json', 'assemble_archive_parts.py') or re.fullmatch(re.escape(NAME) + r'\.part-\d{3}', name) is not None


def assemble(manifest, output):
    manifest, output = Path(manifest), Path(output)
    doc = json.loads(manifest.read_text())
    if doc.get('schema_version') != 1 or doc.get('kind') != 'multipart-zip': raise ValueError('Unsupported multipart archive')
    inputs = []
    for number, part in enumerate(doc['parts'], 1):
        name = part['file']
        if Path(name).name != name or '\\' in name or name in ('.', '..') or part['number'] != number: raise ValueError('Unsafe/out-of-order archive part')
        path = manifest.parent / name
        if path.is_symlink() or path.stat().st_size != part['bytes'] or digest(path) != part['sha256']: raise ValueError('Part integrity failure: ' + name)
        if path in inputs: raise ValueError('Duplicate archive part')
        inputs.append(path)
    if not inputs or output.resolve() in {manifest.resolve(), *(p.resolve() for p in inputs)}: raise ValueError('Invalid archive output')
    output.parent.mkdir(parents=True, exist_ok=True)
    fd, temporary = tempfile.mkstemp(prefix='.assembling-', dir=output.parent)
    try:
        with os.fdopen(fd, 'wb') as target:
            for source in inputs:
                with source.open('rb') as stream:
                    for block in iter(lambda: stream.read(1024 * 1024), b''): target.write(block)
        result = Path(temporary)
        if result.stat().st_size != doc['archive']['bytes'] or digest(result) != doc['archive']['sha256']: raise ValueError('Assembled ZIP integrity failure')
        os.replace(temporary, output)
    finally:
        Path(temporary).unlink(missing_ok=True)


def package(root=DEFAULT, limit=100 * 1024 * 1024, part_size=90 * 1024 * 1024):
    root = Path(root).resolve()
    receipt = root / 'package-manifest.json'
    doc = json.loads(receipt.read_text())
    if doc.get('schemaVersion') != 1 or not isinstance(doc.get('members'), list): raise ValueError('Invalid payload receipt')
    files = {}
    for member in doc['members']:
        name = member['file']; path = root / name
        if (not path.resolve().is_relative_to(root) or path.is_symlink() or name in files
                or name == receipt.name or download_artifact(name)): raise ValueError('Unsafe/duplicate payload entry')
        if path.stat().st_size != member['bytes'] or digest(path) != member['sha256']: raise ValueError('Payload integrity failure: ' + name)
        files[name] = path
    actual = {p.relative_to(root).as_posix() for p in root.rglob('*') if p.is_file() and p != receipt and not download_artifact(p.relative_to(root).as_posix())}
    if set(files) != actual: raise ValueError('Payload receipt does not cover all files')
    files[receipt.name] = receipt
    fd, temporary = tempfile.mkstemp(prefix='top-down-layer-kit-', suffix='.zip')
    os.close(fd)
    try:
        with zipfile.ZipFile(temporary, 'w', compression=zipfile.ZIP_DEFLATED, compresslevel=9) as archive:
            for name, source in sorted(files.items()):
                info = zipfile.ZipInfo(name, (2026, 1, 1, 0, 0, 0)); info.create_system = 3
                info.external_attr = 0o100644 << 16; info.compress_type = zipfile.ZIP_DEFLATED
                archive.writestr(info, source.read_bytes(), compresslevel=9)
        archive = Path(temporary); whole = {'file': NAME, 'bytes': archive.stat().st_size, 'sha256': digest(archive)}
        for old in root.iterdir():
            if old.is_file() and download_artifact(old.name): old.unlink()
        if whole['bytes'] < limit:
            os.replace(archive, root / NAME)
            return {'format': 'zip', **whole}
        if not 0 < part_size < limit: raise ValueError('Invalid archive part size')
        parts = []
        with archive.open('rb') as stream:
            for number in range(1, 1000):
                block = stream.read(part_size)
                if not block: break
                name = NAME + f'.part-{number:03d}'; target = root / name; target.write_bytes(block)
                parts.append({'number': number, 'file': name, 'bytes': len(block), 'sha256': hashlib.sha256(block).hexdigest()})
            else: raise ValueError('Too many archive parts')
        helper = root / 'assemble_archive_parts.py'; helper.write_bytes(Path(__file__).read_bytes())
        proof = {'schema_version': 1, 'kind': 'multipart-zip', 'archive': whole, 'parts': parts,
                 'payloadManifestSha256': digest(receipt), 'assemblyTool': {'file': helper.name, 'bytes': helper.stat().st_size, 'sha256': digest(helper)},
                 'usage': f'python assemble_archive_parts.py --assemble {NAME}.parts.json --output {NAME}'}
        (root / (NAME + '.parts.json')).write_text(json.dumps(proof, indent=2) + '\n')
        return {'format': 'multipart-zip', **proof}
    finally:
        Path(temporary).unlink(missing_ok=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--asset-root', type=Path, default=DEFAULT)
    parser.add_argument('--assemble', type=Path)
    parser.add_argument('--output', type=Path)
    args = parser.parse_args()
    if args.assemble:
        if not args.output: parser.error('--output is required with --assemble')
        assemble(args.assemble, args.output)
    else:
        print(json.dumps(package(args.asset_root), indent=2))
