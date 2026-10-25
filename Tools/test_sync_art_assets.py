import contextlib
import io
import json
from pathlib import Path
import subprocess
import tempfile
import unittest
from unittest.mock import patch

import sync_art_assets as art


class ArtSyncTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory()
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.root = self.base / "game"
        self.source = self.base / "art"
        self.root.mkdir()
        self.source.mkdir()
        self.project = self.source / "dungeon-crawler-tactics"
        self.project.mkdir()
        self.paths = ("Docs/sources/test.png", "Web/wwwroot/assets/test.zip")
        self.entries = []
        for index, relative in enumerate(self.paths):
            path = self.project / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(bytes([index, 255, 0, 17]) * 50)
            self.entries.append({"path": relative, "sha256": art.sha256(path), "bytes": path.stat().st_size})
        self.index = self.project / "asset-index.json"
        self.write_index()
        self.git(self.source, "init", "--quiet")
        self.git(self.source, "add", ".")
        self.git(self.source, "-c", "user.name=Test", "-c", "user.email=test@example.invalid",
                 "commit", "--quiet", "-m", "Test art")
        self.lock = {"schemaVersion": 1, "repository": "https://github.com/cehinds/AI-Art.git",
                     "branch": "dungeon-crawler", "commit": self.git(self.source, "rev-parse", "HEAD"),
                     "project": "dungeon-crawler-tactics", "indexSha256": art.sha256(self.index)}
        self.write_lock()

    def git(self, path, *args):
        return subprocess.check_output(["git", "-C", str(path), *args], text=True,
                                       stderr=subprocess.PIPE).strip()

    def write_index(self):
        self.index.write_text(json.dumps({"schemaVersion": 1, "project": "dungeon-crawler-tactics",
                                          "files": self.entries}), encoding="utf-8")

    def write_lock(self):
        (self.root / art.LOCK_NAME).write_text(json.dumps(self.lock), encoding="utf-8")

    def repin_index(self):
        self.write_index()
        self.lock["indexSha256"] = art.sha256(self.index)

    def test_fresh_restore_and_idempotent_check(self):
        (self.project / "unlisted.png").write_bytes(b"not an indexed asset")
        self.assertEqual(art.sync(self.root, self.source, self.lock), (2, 0))
        for entry in self.entries:
            self.assertEqual(art.sha256(self.root / entry["path"]), entry["sha256"])
        self.assertFalse((self.root / "unlisted.png").exists())
        self.assertEqual(art.sync(self.root, self.source, self.lock), (0, 2))
        self.assertEqual(art.sync(self.root, self.source, self.lock, check=True), (0, 2))

    def test_modified_destination_refuses_entire_batch_then_force_restores(self):
        path = self.root / self.paths[1]
        path.parent.mkdir(parents=True)
        path.write_bytes(b"local work")
        with self.assertRaisesRegex(art.SyncError, "Refusing to overwrite"):
            art.sync(self.root, self.source, self.lock)
        self.assertFalse((self.root / self.paths[0]).exists())
        self.assertEqual(path.read_bytes(), b"local work")
        self.assertEqual(art.sync(self.root, self.source, self.lock, force=True), (2, 0))

    def test_missing_check_does_not_write(self):
        with self.assertRaisesRegex(art.SyncError, "Missing or modified"):
            art.sync(self.root, self.source, self.lock, check=True)
        self.assertFalse((self.root / "Docs").exists())

    def test_revision_mismatch(self):
        self.lock["commit"] = "a" * 40
        with self.assertRaisesRegex(art.SyncError, "HEAD does not match"):
            art.sync(self.root, self.source, self.lock)

    def test_index_digest_mismatch(self):
        self.index.write_text(self.index.read_text() + " ")
        with self.assertRaisesRegex(art.SyncError, "index SHA256"):
            art.sync(self.root, self.source, self.lock)

    def test_corrupt_source_refuses_entire_batch(self):
        path = self.project / self.paths[1]
        path.write_bytes(b"x" * path.stat().st_size)
        with self.assertRaisesRegex(art.SyncError, "integrity mismatch"):
            art.sync(self.root, self.source, self.lock)
        self.assertFalse((self.root / "Docs").exists())

    def test_missing_source(self):
        (self.project / self.paths[1]).unlink()
        with self.assertRaisesRegex(art.SyncError, "Missing art file"):
            art.sync(self.root, self.source, self.lock)

    def test_unsafe_and_ambiguous_paths(self):
        for value in ("../escape", "/tmp/escape", "a/../../escape", "a\\b", "C:/escape",
                      "a//b", "a/./b", ".", ".git/config", "a/.GIT/config", "a\nb"):
            with self.subTest(path=value), self.assertRaises(art.SyncError):
                art.safe_relative(value)

    def test_duplicate_index_paths(self):
        self.entries.append(dict(self.entries[0]))
        self.repin_index()
        with self.assertRaisesRegex(art.SyncError, "Duplicate asset path"):
            art.sync(self.root, self.source, self.lock)

    def test_source_symlink_rejected(self):
        path = self.project / self.paths[0]
        path.unlink()
        path.symlink_to(self.project / self.paths[1])
        with self.assertRaisesRegex(art.SyncError, "Symlink"):
            art.sync(self.root, self.source, self.lock)

    def test_destination_symlink_rejected_even_with_force(self):
        elsewhere = self.base / "elsewhere"
        elsewhere.mkdir()
        (self.root / "Docs").symlink_to(elsewhere, target_is_directory=True)
        with self.assertRaisesRegex(art.SyncError, "Symlink"):
            art.sync(self.root, self.source, self.lock, force=True)
        self.assertEqual(list(elsewhere.iterdir()), [])

    def test_file_parent_rejected_before_any_copy(self):
        (self.root / "Web").write_bytes(b"occupied parent")
        with self.assertRaisesRegex(art.SyncError, "parent is not a directory"):
            art.sync(self.root, self.source, self.lock)
        self.assertFalse((self.root / "Docs").exists())

    def test_source_subdirectory_rejected(self):
        with self.assertRaisesRegex(art.SyncError, "checkout root"):
            art.sync(self.root, self.project, self.lock)

    def test_lock_placeholders_and_wrong_repository_rejected(self):
        self.assertEqual(art.read_lock(self.root), self.lock)
        for field, value in (("commit", "0" * 40), ("indexSha256", "0" * 64),
                             ("repository", "https://example.invalid/art.git")):
            with self.subTest(field=field):
                old = self.lock[field]
                self.lock[field] = value
                self.write_lock()
                with self.assertRaises(art.SyncError):
                    art.read_lock(self.root)
                self.lock[field] = old

    def test_cached_checkout_is_pinned_and_reused(self):
        self.git(self.root, "init", "--quiet")
        real_git = art.git

        def local_remote(directory, *args):
            if args[:3] == ("remote", "add", "origin"):
                args = (*args[:3], str(self.source))
            return real_git(directory, *args)

        with patch.object(art, "git", side_effect=local_remote):
            cached = art.cached_source(self.root, self.lock)
            self.assertEqual(real_git(cached, "rev-parse", "HEAD"), self.lock["commit"])
            self.assertEqual(art.cached_source(self.root, self.lock), cached)
            self.assertEqual(art.sync(self.root, cached, self.lock), (2, 0))

    def test_cli_prints_validated_pin_without_fetching(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output):
            self.assertEqual(art.main(["--root", str(self.root), "--print-commit"]), 0)
        self.assertEqual(output.getvalue().strip(), self.lock["commit"])

    def test_late_staging_failure_changes_no_destination(self):
        original_copy = art.shutil.copyfileobj
        count = 0

        def fail_second(input_stream, output_stream):
            nonlocal count
            count += 1
            if count == 2:
                raise OSError("injected late copy failure")
            return original_copy(input_stream, output_stream)

        with patch.object(art.shutil, "copyfileobj", side_effect=fail_second):
            with self.assertRaisesRegex(OSError, "late copy failure"):
                art.sync(self.root, self.source, self.lock)
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), [art.LOCK_NAME])

    def test_late_staging_hash_failure_changes_no_destination(self):
        original_copy = art.shutil.copyfileobj
        count = 0

        def corrupt_second(input_stream, output_stream):
            nonlocal count
            count += 1
            if count == 2:
                output_stream.write(b"source changed after preflight")
            else:
                original_copy(input_stream, output_stream)

        with patch.object(art.shutil, "copyfileobj", side_effect=corrupt_second):
            with self.assertRaisesRegex(art.SyncError, "Source changed while copying"):
                art.sync(self.root, self.source, self.lock)
        self.assertEqual(sorted(p.name for p in self.root.iterdir()), [art.LOCK_NAME])

    def test_replace_failure_rolls_back_new_and_overwritten_files(self):
        existing = self.root / self.paths[1]
        existing.parent.mkdir(parents=True)
        existing.write_bytes(b"local original")
        real_replace = art.os.replace
        failed = False

        def fail_install_once(source, destination):
            nonlocal failed
            if destination == existing and not failed:
                failed = True
                raise OSError("injected replace failure")
            return real_replace(source, destination)

        with patch.object(art.os, "replace", side_effect=fail_install_once):
            with self.assertRaisesRegex(OSError, "replace failure"):
                art.sync(self.root, self.source, self.lock, force=True)
        self.assertEqual(existing.read_bytes(), b"local original")
        self.assertFalse((self.root / "Docs").exists())
        self.assertEqual(list(self.root.glob(".art-sync-*")), [])

    def test_failed_rollback_retains_original_recovery_file(self):
        existing = self.root / self.paths[1]
        existing.parent.mkdir(parents=True)
        existing.write_bytes(b"local original")
        real_replace = art.os.replace

        def fail_install_and_restore(source, destination):
            if destination == existing:
                raise OSError("injected persistent filesystem failure")
            return real_replace(source, destination)

        with patch.object(art.os, "replace", side_effect=fail_install_and_restore):
            with self.assertRaisesRegex(art.SyncError, "recovery files retained"):
                art.sync(self.root, self.source, self.lock, force=True)
        recovery = list(self.root.glob(".art-sync-*/old-*"))
        self.assertEqual(len(recovery), 1)
        self.assertEqual(recovery[0].read_bytes(), b"local original")


if __name__ == "__main__":
    unittest.main()
