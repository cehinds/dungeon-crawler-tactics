#!/usr/bin/env python3
"""Restore only the reviewed Floor One asset subset, never the full art repository."""

import argparse
import hashlib
import json
from pathlib import Path
import shutil
import urllib.request

repo = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("wwwroot", type=Path)
parser.add_argument(
    "--remote", action="store_true", help="Always use the immutable remote revision"
)
args = parser.parse_args()
manifest = json.loads((repo / "Tools/hosted-assets.json").read_text())
for entry in manifest["files"]:
    relative = Path(entry["path"])
    if relative.is_absolute() or ".." in relative.parts:
        raise ValueError(f"Unsafe manifest path: {relative}")
    target = args.wwwroot / "assets" / relative
    local = repo / "Web/wwwroot/assets" / relative
    target.parent.mkdir(parents=True, exist_ok=True)
    if local.exists() and not args.remote:
        data = local.read_bytes()
    else:
        url = f"https://raw.githubusercontent.com/{manifest['repository']}/{manifest['commit']}/{manifest['prefix']}/{relative.as_posix()}"
        with urllib.request.urlopen(url, timeout=60) as response:
            data = response.read()
    if hashlib.sha256(data).hexdigest() != entry["sha256"]:
        raise ValueError(f"Asset checksum mismatch: {relative}")
    target.write_bytes(data)
shutil.copyfile(repo / "Tools/hosted-assets.json", args.wwwroot / "hosted-assets.json")
print(f"Prepared {len(manifest['files'])} verified hosted assets in {args.wwwroot}")
