"""Keep the Pages artifact compact; whole-style downloads are hosted in AI-Art."""
import argparse
import json
from pathlib import Path

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('directory', type=Path)
args = parser.parse_args()
root = args.directory.resolve()
if root.name != 'wwwroot' or root.parent.name != 'publish' or not (root / 'index.html').is_file():
    parser.error('Expected the generated publish/wwwroot directory, not source assets.')
removed = 0
for style in ('pocket-dungeon', 'ink-and-lanterns', 'dungeon-after-dark'):
    archive = root / 'assets/style-packs' / style / f'{style}.zip'
    manifest_path = archive.parent / 'manifest.json'
    if manifest_path.is_file():
        manifest = json.loads(manifest_path.read_text())
        manifest['download'] = f'https://raw.githubusercontent.com/cehinds/AI-Art/refs/heads/dungeon-crawler/dungeon-crawler-tactics/Web/wwwroot/assets/style-packs/{style}/{style}.zip'
        manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + '\n')
    if archive.is_file():
        removed += archive.stat().st_size
        archive.unlink()
size = sum(path.stat().st_size for path in root.rglob('*') if path.is_file())
print(f'Pages artifact: {size / 2**20:.1f} MiB; {removed / 2**20:.1f} MiB of whole-style ZIPs served by AI-Art')
if size >= 1_000_000_000:
    raise SystemExit('Pages artifact exceeds the conservative 1 GB hosting limit.')
