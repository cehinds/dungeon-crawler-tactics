# Art storage

All generated art binaries and browser asset manifests live in [AI-Art, on the dungeon-crawler branch](https://github.com/cehinds/AI-Art/tree/dungeon-crawler/dungeon-crawler-tactics). The shared repository also has `ff2` and `ashenspire` branches. Dungeon Crawler updates do not alter those game branches.

`art-assets.lock.json` pins an exact commit and the SHA-256 of its project index. The index preserves each original project-relative path and records every file's byte size and SHA-256. The game repository keeps code, authored data, crop definitions and research. PNGs, animation sheets, WebP previews, ZIP packs, source atlases, visual review captures and browser art manifests are restored as ignored working files.

## Fresh checkout

Use Python 3.10 or newer and Git:

```sh
python3 Tools/sync_art_assets.py
```

The synchronizer fetches the pinned public revision into a cache under `.git`, verifies the complete source index, and restores the listed files. Existing differing local assets are preserved unless you explicitly pass `--force`. A failure before publication leaves local files unchanged; publication failures roll back installed files and preserve recovery backups if rollback itself fails.

If you already have AI-Art checked out at the pinned commit:

```sh
python3 Tools/sync_art_assets.py --source ../AI-Art
python3 Tools/sync_art_assets.py --source ../AI-Art --check
```

Restore art before content validators, local play, Unity preparation or browser publication. The Pages workflow checks out the pinned art commit and restores it before validation. Browser URLs and Unity resource paths remain the same.

## Updating art

1. Work on AI-Art's `dungeon-crawler` branch. Put files under `dungeon-crawler-tactics/` using the existing project-relative paths; keep raw generation outputs in `originals/`.
2. Update the game's authored inventory/crops when needed and export the derived files. Copy the completed exports back into the art repository's matching paths.
3. Run `python3 tools/index_assets.py dungeon-crawler-tactics` in AI-Art, review the changes, commit and push that branch.
4. Update `commit` and `indexSha256` in the game's lock to the published art revision and the SHA-256 of `dungeon-crawler-tactics/asset-index.json`.
5. Run the sync check and relevant content/browser tests, then publish the game change.

Available unedited generation originals have their own index and are not downloaded into the game's working tree by the synchronizer. Existing art remains in older game Git history; the migration does not rewrite history.
