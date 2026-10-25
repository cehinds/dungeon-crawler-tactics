# Dungeon Crawler Carl location tile coverage

This folder links researched locations and routes from Books 1–8 to reusable map tile kits. The source-linked survey now covers 187 locations and route records, including the Books 6–8 settings on Floors 8–11. Book 8 is published; the research distinguishes official publication evidence from secondary chapter references and flags where direct prose verification remains open. Six new environment families extend the original Book 1–5 library. These records do not imply complete canonical maps or a complete full-text audit.

Start with [coverage.json](coverage.json) for the normalized index and [inventory.json](inventory.json) for kit IDs. The supporting research is in [Books 1–2](research-books-1-2.json), [Books 3–4](research-books-3-4.json), [Book 5](research-book-5.json), and [Books 6–8](research-books-6-8.json). The Books 6–8 file links official author and publisher records, samples where available, and clearly identified secondary chapter indexes. Each coverage record includes source URLs, appearance nuance in `notes`, an appearance category, confidence, and inventory `kitIds` that can support a map.

The `appearance` field describes the evidence status:

- `visited`: the narrative shows the party at or inside the place.
- `mentioned`: a source establishes the place or destination, but the party’s visit is not established.
- `remote`: the place or event is seen, affected, or reported from elsewhere; this does not establish that the party visited it.
- `uncertain`: visit status or the location’s canon details remain unresolved.

`coverage` describes readiness for the map UI. `mapped` means the location has at least one reusable kit association; it does not certify a measured layout. `review-needed` marks unresolved sourcing, visit status, or art details. An empty `kitIds` array is permitted when no inventory kit is a grounded fit. In particular, Train Yard A is disputed, and Yard M is supported only by tertiary discussion; neither is a confirmed visited map.

## Source and art boundaries

Research summaries distinguish prose-supported features from proposed art adaptation. Names, book/floor placement, narrative appearance, and cited visual features are source-grounded to the level recorded by each research file. Tile variation, board layout, dimensions, missing architecture, and visual details not established by those sources are art adaptation. Do not treat a kit assignment as proof that every tile piece appears in a particular named place.

The Iron Tangle’s many colored routes reuse `iron-tracks`, `iron-stations`, and `iron-trains`; they do not imply dozens of distinct station architectures. Larracos references from Book 4 are remote and use `broadcast-portals`. Book 5 reports that the High Elf Castle and qualifying occupants transfer to Floor 9. Carl, crawlers, hunters, most pets, and elves remain on Floor 6 for the bramble-crater battle; the Floor 7–8 epilogue comes afterward. Book 8 coverage includes Havana and cemetery locations on Floor 8, Larracos Faction Wars on Floor 9, race circuits and a garage on Floor 10, and the Parade of Horribles route and arena on Floor 11. Several detailed Book 6–8 appearances rely on clearly flagged secondary chapter indexes and still need direct prose review. Unnamed towns, safe rooms, stations, and bubble environments are consolidated into reusable families rather than expanded into invented canon names.

The expanded inventory has 31 kits in three art styles: 93 atlases and 2,232 component PNGs. All six Books 6–8 kits are fully exported; their 18 atlases add 432 PNGs. All styles use a native orthogonal grid with a 128×128 logical cell; floors are square, with no diamond projection or perspective on door tiles. Each style keeps its own palette and visual character. The exporter preserves native source PNGs and resizes only derived component PNGs onto a 256×256 canvas with anchor `(128, 192)`. Art export and the 93-variant browser review are complete. Publication is tracked by the [Pages deployment workflow](https://github.com/cehinds/dungeon-crawler-tactics/actions/workflows/deploy-pages.yml) after push to main. This is an art library and metadata, not runtime integration.

## Coverage checklist

- [x] Books 1–8 represented across 187 source-linked location, sub-area, and route records.
- [x] Six new reusable art families added for Books 6–8: Havana, cemetery/shrines, Larracos, Faction Wars, racing circuits, and the Parade of Horribles.
- [x] All 31 kits exported across three styles: 93 atlases and 2,232 component PNGs.
- [x] Visited, mentioned, remote, and uncertain appearances retained as distinct UI categories.
- [x] Shared interiors and reused venues associated with common inventory kits where supported.
- [x] Iron Tangle color routes share the rail, station, and train kits.
- [x] Book 4 Larracos remains remote. Book 5’s castle transfer is remote/reported, its bramble crater is on Floor 6, and its epilogue enters Floors 7–8 without implying complete later-floor atlases.
- [x] Yard A dispute and Yard M’s tertiary status are flagged for review.
- [x] Books 5–8 named locations, reusable terrain families, sources, and research gaps are linked in their research files.
- [x] The Floor 8 chamber is mapped while its unknown destination stays unspecified; no Bahamas, Cuba, or other island landscape is claimed as visited.
- [ ] Full-text audit and complete canonical map validation remain pending.

## Using the components

The [location browser](https://cehinds.github.io/dungeon-crawler-tactics/book-tiles.html) presents square-grid exports. Each kit ZIP contains 24 component PNGs, `manifest.json`, and a contact sheet. A generated composition demonstrates layering; it does not export a playable room. Art, door, and browser checks passed for all 93 variants. Publication is tracked by the [Pages deployment workflow](https://github.com/cehinds/dungeon-crawler-tactics/actions/workflows/deploy-pages.yml) after push to main; see [QA.md](QA.md).

Every native component uses a transparent 256×256 canvas and an anchor at `(128, 192)`. Place that anchor on the destination square-grid coordinate. All styles use the same 128×128 logical cell and orthogonal x/y axes. Keep floors square; orient doors frontally with a horizontal base, and use vertical strips for side walls. Preserve the complete PNG canvas rather than treating its transparent margin as tile spacing.

Read `role`, `layer`, `footprint`, `tags`, `walkable`, `anchor`, and `squareLayout` from each asset record; orientation is specified by `squareLayout`. Render ground first, then depth-sort structures and props by their map position. The inventory assigns floor cells 0–5, north walls 6 and doors 12–13, west walls 7, overlays and stairs 8–11 and 14–15, and props 16–23. The exports include square floor pieces, 128×64 north walls, 32×128 west walls, 128×96 frontal doors, and square corners, stairs, and wall caps. Export validation checks full occupancy of the first four floor cells and rejects diamond-shaped floors. Collision and navigation still require an authored game map; the metadata is not a complete autotiling or pathfinding ruleset.

Use assets from one style together to retain its palette and art language. Each style now targets the same square projection. The library includes north and west wall axes; it does not supply every camera rotation of every prop. Rotating a runtime map needs corresponding directional art or an explicit fallback. Door state names describe open or closed states; doors face forward with horizontal bases.

For Unity, import PNGs as Sprite (2D and UI), preserve transparency, and use filtering appropriate to the style. Set consistent pixels per unit within a style. A bottom-oriented anchor `(128, 192)` in this top-left image coordinate system corresponds to normalized Unity pivot `(0.5, 0.25)`. These are import recommendations; this art library does not create Unity Tile assets or validate a Unity scene.

## Rebuilding and checking

Art sources and Web manifests are in the [AI-Art repository](https://github.com/cehinds/AI-Art/tree/dungeon-crawler/dungeon-crawler-tactics). The earlier baseline (`d12871d`) contained 3,925 assets and passed empty-directory restore and checksum verification. The final lock pins commit `4aab2055cdfbd2ff0d6955d082007ecee0e6cb5b`; its main index contains 4,429 project assets. Separately, `originals/index.json` indexes 312 original-generation files that are retained in AI-Art but are not restored into the game. Full source reconstruction and `--check` passed for the project assets. In a new clone, run `python3 Tools/sync_art_assets.py` before testing or building. Python 3.10 or newer is required. For a local AI-Art checkout, pass `--source ../AI-Art`. The exporter preserves source PNGs and resizes derived component PNGs onto 256×256 canvases. Previous crop registration and affine transforms are legacy only. See [QA.md](QA.md) for current results and [Registration.md](Registration.md) for the legacy note.

```sh
python3 Tools/build_book_tiles.py --style all
python3 Tools/build_book_tiles.py --catalog
python3 Tools/build_book_tiles.py --style all --check --catalog
python3 -m unittest discover -s Tools -p 'test_book_tiles.py'
node Tools/test_book_tile_layout.mjs
```

A kit can be rebuilt with `--style STYLE --kit KIT`. Regenerate the catalog after inventory, coverage, or export changes. Exact source hashes and resize metadata in each manifest make every PNG traceable. See [QA.md](QA.md) for the delivery checks and remaining limitations.
