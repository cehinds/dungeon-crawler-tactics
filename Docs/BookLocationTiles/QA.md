# Books 1–8 location tile QA

The expanded art, export, and 93-variant browser review is complete: 31 kits, 93 atlases, and 2,232 component PNGs. The fixed-seed and Play visual roundtrip path has dedicated C# and published-browser regression checks in CI. Publication is tracked by the [Pages deployment workflow](https://github.com/cehinds/dungeon-crawler-tactics/actions/workflows/deploy-pages.yml) after push to main; the exhaustive canonical source audit remains open.

## Art and export: passed

- [x] All 93 native orthogonal atlases and 2,232 component exports validated for source, extraction, pixel ownership, geometry, manifests, and catalog consistency.
- [x] All 2,232 decoded RGBA component pixel hashes are unique; components use 256×256 canvases and anchor `(128, 192)`.
- [x] Combined export totals: 558 floors, 279 north-wall/door components (including 186 doors), 93 west walls, 558 overlays, and 744 props. All use the orthogonal 128×128 square grid.
- [x] All 372 full floor planes in cells 0–3 are fully opaque across 128×128, using a source-sampled grout matte around the inset floor material. The default inset is 6.5%; selected glass/sea/rail floors use larger 8–12% insets and correspondingly narrower source windows, recorded in derived metadata.
- [x] North/west repeat walls use a 6.5% trim along the repeated axis only. Doors and props preserve their alpha; native atlas source pixels remain unchanged by export. `sourceWindow` and `matte` fields preserve derivation provenance.
- [x] 27 focused tile exporter tests passed.
- [x] All 186 door states were visually checked for straight-on framing, vertical jambs, level bases, and no diamond plinths.
- [x] All 144 new components in each art style passed `prepare_kit`; all 600 original baseline components per style also passed.
- [x] 558 native-art scene checks passed; the pixel open-submarine aperture remains clear.

## Browser and runtime: passed

- [x] All 93 gallery variants and 93 generator art combinations passed browser review. Grid toggles restore exact pixels; Book 6–8 filters and evidence display correctly.
- [x] All 2,232 PNG links and 2,511 versioned links returned HTTP 200. No browser errors; the 390px mobile view has no horizontal overflow.
- [x] The generator passed nine style/theme combinations and checks for zoom, pan, rotation, fit, grid and route overlays, material variety, recipe metadata, canonical playable JSON with optional art metadata, PNG download, play cancellation, and failure/retry behavior.
- [x] 152 Python `Tools` unit tests passed, including 20 asset-sync and 27 book-tile geometry tests. Node checks passed for 720 generator cases, 721 schema-valid exports, 461 room-generation checks, 640 rotated-picking checks, and 558 native-art scenes.
- [x] Four generated maps imported into the shared C# runtime; workshop handoff passed.
- The implementation defaults Generate to a fresh seed; editing the seed enables **Keep this seed fixed**, and reroll always chooses a new one.
- Play/export wait for the selected native art to load, then carry the exact preview composition in optional presentation metadata.
- [x] Added published-build browser regression coverage for new/fixed seeds, exact native art and terrain, one-time handoff, reload, failed-save retry and four pointer rotations. The linked workflow records execution results for each revision.

## Tile edge metadata

- [x] All 744 authored assets and 2,232 exported component records carry four-side tags; manifests and ZIPs match the inventory. PNG bytes are unchanged.
- [x] Thirty exporter tests, the authored JSON Schema check, custom connector/rotation tests, and 558 generated-scene checks passed.
- [x] Foundry rotation inspection and 24 library cards with four side lists passed browser checks.

## Publication and source audit

- Publication is tracked by the [Pages deployment workflow](https://github.com/cehinds/dungeon-crawler-tactics/actions/workflows/deploy-pages.yml) after push to main.
- [ ] Complete direct prose review of secondary-sourced Books 6–8 location details and the exhaustive canonical map audit.

The art lab's three whole-style ZIPs stream from the AI-Art branch; all three links returned HTTP 200 with `application/zip`. Individual PNGs and smaller collection downloads remain in the Pages output. The publish workflow removes only the three duplicate aggregate ZIPs after publishing; estimated final site size is 771.5 MiB.

## Asset migration: passed

- [x] The current game lock pins AI-Art commit `b2a02094de3f15a5ba8d81c01e8db4dbceb85626`; its main index contains 21,945 project files. Exact-pin hydration restored 17,516 missing files and verified the 4,429 already present; a subsequent `--check` verified all 21,945 files. The earlier focused seam-fix pin `8753a0061398b2a2169c2098315d26d943f214ff` passed `--check` and full 2,232-PNG reconstruction; the separate originals index tracks generation sources outside the game restore.
- [x] All 20 focused asset-sync tests are included in the passing Python suite.

In a new clone, run `python3 Tools/sync_art_assets.py` before testing or building. Python 3.10 or newer is required.

## Location coverage

- [x] 187 source-linked location, sub-area, and route records through Books 1–8; kit references resolve.
- [x] 176 records have reusable kit associations; 11 remain `review-needed`.
- [x] Visited, mentioned, remote, and uncertain appearances remain distinct.
- [x] Books 6–8 add ten location records, including Ghosts of Earth on Floor 8, Faction Wars on Floor 9, racing and a garage on Floor 10, and the Parade of Horribles route and arena on Floor 11.
- [x] Official author and publisher sources confirm Book 8 publication. Secondary chapter references are identified in [the Books 6–8 research file](research-books-6-8.json).

This is a researched art library, not a full-text concordance or a complete canonical floorplan collection. Room layouts, measurements, and unsupported visual details are adaptations. The browser custom-map runtime can render the native art through optional presentation metadata; it does not change canonical collision or terrain rules, campaign maps, or Unity scenes.
