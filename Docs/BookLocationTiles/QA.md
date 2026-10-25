# Books 1–8 location tile QA

The expanded art, export, and browser review is complete: 31 kits, 93 atlases, and 2,232 component PNGs. Publication is tracked by the [Pages deployment workflow](https://github.com/cehinds/dungeon-crawler-tactics/actions/workflows/deploy-pages.yml) after push to main. The exhaustive canonical source audit remains open.

## Art and export: passed

- [x] All 93 native orthogonal atlases and 2,232 component exports validated for source, extraction, pixel ownership, geometry, manifests, and catalog consistency.
- [x] All 2,232 decoded RGBA component pixel hashes are unique; components use 256×256 canvases and anchor `(128, 192)`.
- [x] Combined export totals: 558 floors, 279 north-wall/door components (including 186 doors), 93 west walls, 558 overlays, and 744 props. All use the orthogonal 128×128 square grid.
- [x] All 186 door states were visually checked for straight-on framing, vertical jambs, level bases, and no diamond plinths.
- [x] All 144 new components in each art style passed `prepare_kit`; all 600 original baseline components per style also passed.
- [x] 558 native-art scene checks passed; the pixel open-submarine aperture remains clear.

## Browser and runtime: passed

- [x] All 93 gallery variants and 93 generator art combinations passed browser review. Grid toggles restore exact pixels; Book 6–8 filters and evidence display correctly.
- [x] All 2,232 PNG links and 2,511 versioned links returned HTTP 200. No browser errors; the 390px mobile view has no horizontal overflow.
- [x] The generator passed nine style/theme combinations and checks for zoom, pan, rotation, fit, grid and route overlays, material variety, recipe metadata, strict canonical playable JSON, PNG download, play cancellation, and failure/retry behavior.
- [x] 156 Python tests passed, including 20 asset-sync tests. Node checks passed for 720 generator cases, 721 schema-valid exports, 461 room-generation checks, 640 rotated-picking checks, and 558 native-art scenes.
- [x] Four generated maps imported into the shared C# runtime; workshop handoff passed.

## Publication and source audit

- Publication is tracked by the [Pages deployment workflow](https://github.com/cehinds/dungeon-crawler-tactics/actions/workflows/deploy-pages.yml) after push to main.
- [ ] Complete direct prose review of secondary-sourced Books 6–8 location details and the exhaustive canonical map audit.

The art lab's three whole-style ZIPs stream from the AI-Art branch; all three links returned HTTP 200 with `application/zip`. Individual PNGs and smaller collection downloads remain in the Pages output. The publish workflow removes only the three duplicate aggregate ZIPs after publishing; estimated final site size is 771.5 MiB.

## Asset migration: passed

- [x] The earlier baseline pin `d12871d5dd8ea9bb4f334215045000fddc23fd52` restored 3,925 files into an empty directory and passed `--check`.
- [x] The final expanded pin `4aab2055cdfbd2ff0d6955d082007ecee0e6cb5b` contains 4,429 project assets and passes sync `--check`; full 2,232-PNG reconstruction and catalog checks passed. The separate `originals/index.json` covers 312 raw originals, which are retained in AI-Art and not restored into the game.
- [x] Restored all 4,429 final pinned assets into an empty directory and verified them with `--check`; all 20 focused asset-sync tests passed.

In a new clone, run `python3 Tools/sync_art_assets.py` before testing or building. Python 3.10 or newer is required.

## Location coverage

- [x] 187 source-linked location, sub-area, and route records through Books 1–8; kit references resolve.
- [x] 176 records have reusable kit associations; 11 remain `review-needed`.
- [x] Visited, mentioned, remote, and uncertain appearances remain distinct.
- [x] Books 6–8 add ten location records, including Ghosts of Earth on Floor 8, Faction Wars on Floor 9, racing and a garage on Floor 10, and the Parade of Horribles route and arena on Floor 11.
- [x] Official author and publisher sources confirm Book 8 publication. Secondary chapter references are identified in [the Books 6–8 research file](research-books-6-8.json).

This is a researched art library, not a full-text concordance or a complete canonical floorplan collection. Room layouts, measurements, and unsupported visual details are adaptations. The tile art is not integrated into playable game maps, encounters, collision, or Unity scenes.
