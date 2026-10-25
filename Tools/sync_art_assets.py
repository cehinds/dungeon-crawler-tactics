"""Restore the exact art revision pinned by art-assets.lock.json (Python 3, Git).

    python Tools/sync_art_assets.py
    python Tools/sync_art_assets.py --source ../AI-Art

Existing differing files require --force. All source files are verified before
any destination file is changed. The default Git cache lives inside .git.
"""

import argparse
import hashlib
import json
import os
from pathlib import Path, PurePosixPath
import re
import shutil
import subprocess
import sys
import tempfile


ROOT = Path(__file__).resolve().parents[1]
LOCK_NAME = "art-assets.lock.json"


class SyncError(Exception):
    pass


def require(condition, message):
    if not condition:
        raise SyncError(message)


def sha256(path):
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()


def read_json(path):
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError) as error:
        raise SyncError(f"Cannot read {path}: {error}") from error


def read_lock(root):
    lock = read_json(root / LOCK_NAME)
    require(isinstance(lock, dict) and lock.get("schemaVersion") == 1,
            "Unsupported art lock schema")
    require(lock.get("repository") == "https://github.com/cehinds/AI-Art.git",
            "Art lock repository must be https://github.com/cehinds/AI-Art.git")
    require(lock.get("project") == "dungeon-crawler-tactics", "Unexpected art project")
    for field, length in (("commit", 40), ("indexSha256", 64)):
        value = lock.get(field)
        require(isinstance(value, str) and re.fullmatch(rf"[0-9a-f]{{{length}}}", value)
                and value != "0" * length, f"Art lock {field} must be a pinned, nonzero digest")
    return lock


def git(directory, *args):
    try:
        result = subprocess.run(["git", "-C", str(directory), *args], check=True,
                                text=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    except (OSError, subprocess.CalledProcessError) as error:
        detail = getattr(error, "stderr", None) or str(error)
        raise SyncError(f"Git operation failed: {detail.strip()}") from error
    return result.stdout.strip()


def cached_source(root, lock):
    git_dir = Path(git(root, "rev-parse", "--absolute-git-dir"))
    cache = git_dir / "art-assets" / lock["commit"]
    if cache.exists():
        return cache
    cache.parent.mkdir(parents=True, exist_ok=True)
    temporary = Path(tempfile.mkdtemp(prefix="fetch-", dir=cache.parent))
    try:
        git(temporary, "init", "--quiet")
        git(temporary, "remote", "add", "origin", lock["repository"])
        git(temporary, "fetch", "--quiet", "--depth=1", "origin", lock["commit"])
        git(temporary, "-c", "advice.detachedHead=false", "checkout", "--quiet", "--detach", "FETCH_HEAD")
        try:
            temporary.rename(cache)
        except FileExistsError:
            # Another sync may have populated the same immutable revision cache.
            pass
    finally:
        if temporary.exists():
            shutil.rmtree(temporary)
    return cache


def safe_relative(value):
    require(isinstance(value, str) and value and "\\" not in value and ":" not in value
            and not any(ord(char) < 32 for char in value), f"Unsafe asset path: {value!r}")
    path = PurePosixPath(value)
    require(path.parts and not path.is_absolute() and path.as_posix() == value
            and all(part not in (".", "..") and part.lower() != ".git" for part in path.parts),
            f"Unsafe asset path: {value!r}")
    return path


def checked_path(base, relative):
    path = base
    for index, component in enumerate(relative.parts):
        path = path / component
        require(not path.is_symlink(), f"Symlink is not an asset path: {path}")
        if index < len(relative.parts) - 1:
            require(not path.exists() or path.is_dir(), f"Asset parent is not a directory: {path}")
    require(path.resolve().is_relative_to(base.resolve()), f"Asset escapes root: {path}")
    return path


def source_files(source, lock):
    require(git(source, "rev-parse", "--show-toplevel") == str(source.resolve()),
            "--source must be the art repository checkout root")
    require(git(source, "rev-parse", "HEAD") == lock["commit"],
            f"Art checkout HEAD does not match pinned commit {lock['commit']}")
    project = checked_path(source, safe_relative(lock["project"]))
    index_path = checked_path(project, PurePosixPath("asset-index.json"))
    require(index_path.is_file(), f"Missing asset index: {index_path}")
    require(sha256(index_path) == lock["indexSha256"], "Asset index SHA256 does not match art lock")
    index = read_json(index_path)
    require(isinstance(index, dict) and index.get("schemaVersion") == 1
            and index.get("project") == lock["project"], "Unexpected asset index schema or project")
    entries = index.get("files")
    require(isinstance(entries, list) and entries, "Asset index must list files")
    files, seen = [], set()
    for entry in entries:
        require(isinstance(entry, dict), "Invalid asset index entry")
        relative = safe_relative(entry.get("path"))
        key = relative.as_posix().casefold()
        require(key not in seen, f"Duplicate asset path: {relative}")
        seen.add(key)
        expected = entry.get("sha256")
        size = entry.get("bytes")
        require(isinstance(expected, str) and re.fullmatch(r"[0-9a-f]{64}", expected),
                f"Invalid SHA256: {relative}")
        require(type(size) is int and size >= 0, f"Invalid byte count: {relative}")
        path = checked_path(project, relative)
        require(path.is_file(), f"Missing art file: {relative}")
        require(path.stat().st_size == size and sha256(path) == expected,
                f"Art file integrity mismatch: {relative}")
        files.append((relative, path, expected))
    return files


def sync(root, source, lock, force=False, check=False):
    files = source_files(source, lock)
    pending, unchanged = [], 0
    # Preflight the entire index and every existing destination before writing.
    for relative, origin, expected in files:
        destination = checked_path(root, relative)
        require(not destination.exists() or destination.is_file(),
                f"Asset destination is not a file: {relative}")
        if destination.is_file() and sha256(destination) == expected:
            unchanged += 1
            continue
        require(not check, f"Missing or modified hydrated asset: {relative}")
        require(force or not destination.exists(),
                f"Refusing to overwrite differing asset: {relative}; use --force to replace it")
        pending.append((origin, destination, expected))
    if not pending:
        return 0, unchanged
    # Stage and hash every byte before publishing any file. Keep replaced files
    # until the batch succeeds, so ordinary copy/rename failures can roll back.
    staging = Path(tempfile.mkdtemp(prefix=".art-sync-", dir=root))
    preserve_staging = False
    try:
        staged = []
        for index, (origin, destination, expected) in enumerate(pending):
            temporary = staging / str(index)
            with temporary.open("wb") as output, origin.open("rb") as input_stream:
                shutil.copyfileobj(input_stream, output)
            require(sha256(temporary) == expected, f"Source changed while copying: {origin}")
            staged.append((temporary, destination))
        journal, created_directories = [], []
        try:
            for index, (temporary, destination) in enumerate(staged):
                checked_path(root, destination.relative_to(root))
                missing = []
                parent = destination.parent
                while not parent.exists():
                    missing.append(parent)
                    parent = parent.parent
                for directory in reversed(missing):
                    directory.mkdir()
                    created_directories.append(directory)
                entry = {"destination": destination, "backup": None, "installed": False}
                journal.append(entry)
                if destination.exists():
                    require(force, f"Destination appeared while syncing: {destination}")
                    backup = staging / f"old-{index}"
                    os.replace(destination, backup)
                    entry["backup"] = backup
                os.replace(temporary, destination)
                entry["installed"] = True
        except (OSError, SyncError) as error:
            rollback_errors = []
            for entry in reversed(journal):
                try:
                    if entry["backup"] is not None:
                        os.replace(entry["backup"], entry["destination"])
                    elif entry["installed"]:
                        entry["destination"].unlink()
                except OSError as rollback_error:
                    rollback_errors.append(str(rollback_error))
            for directory in reversed(created_directories):
                try:
                    directory.rmdir()
                except OSError as rollback_error:
                    rollback_errors.append(str(rollback_error))
            if rollback_errors:
                preserve_staging = True
                raise SyncError(f"Sync failed ({error}); rollback incomplete: {'; '.join(rollback_errors)}; "
                                f"recovery files retained at {staging}") from error
            raise
    finally:
        if not preserve_staging:
            shutil.rmtree(staging)
    return len(pending), unchanged


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, help="Existing pinned AI-Art checkout (avoids network)")
    parser.add_argument("--root", type=Path, default=ROOT, help=argparse.SUPPRESS)
    parser.add_argument("--force", action="store_true", help="Replace differing listed local files")
    parser.add_argument("--check", action="store_true", help="Verify hydrated files without copying")
    parser.add_argument("--print-commit", action="store_true", help="Print validated pinned revision for CI")
    args = parser.parse_args(argv)
    try:
        root = args.root.resolve()
        lock = read_lock(root)
        if args.print_commit:
            print(lock["commit"])
            return 0
        source = args.source.resolve() if args.source else cached_source(root, lock)
        copied, unchanged = sync(root, source, lock, args.force, args.check)
        print(f"Art assets: {copied} restored, {unchanged} verified at {lock['commit']}")
        return 0
    except (SyncError, OSError) as error:
        print(f"Art sync failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
