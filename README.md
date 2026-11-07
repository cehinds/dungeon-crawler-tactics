# Dungeon Crawler Tactics — Floor One

A new, compact Floor One RPG for Carl and Princess Donut. Explore a connected dungeon, meet Mordecai, prepare in the safe room, and resolve small turn based tactical encounters on the way to the floor boss and exit. The interface takes its navigation cues from classic menu driven RPGs.

The game rules live in pure C# under `Rebuild/Core`. The browser host runs those same rules through .NET 8 WebAssembly; JavaScript presents the map, menus and battle forecast. The authored items, skills, enemies and dialogue live in `Web/wwwroot/data/floor-one-rpg.json`. Preserved source lore and equipment/skill references are in `Rebuild/ReferenceData`.

New worlds use generation version 4 on a 90 × 52 world map. Supported version 1, version 2 and version 3 safe-room checkpoints migrate to the current world after validation, preserving player progress. The seeded C# generator reads `Web/wwwroot/data/concept-room-rules.json` to assemble room shapes, corridors and whole-object furniture footprints. Its goblin workshop and Ball of Swine boss chamber share an inset industrial-sewer room grammar with side-channel crossings and a north gate right of center; both battle boards use that room's dimensions (18 × 11), with a reserved 12 × 6 central area and three-cell-long crossings through asymmetric water wings, while other tactical encounters retain the 10 × 8 board. Other room arrangements take composition cues from overhead concept sheets: teaching tables, perimeter refuse, restaurant dining aisles, DMV waiting benches, and Sebastian’s separate rest/wash zones. Solid props block movement while reserved approaches keep encounters and services reachable. See `Rebuild/CONCEPT-LAYOUTS.md` for source references, the shared industrial room, and the distinction between source lore and authored layout choices.

## Play locally

Install the .NET 8 SDK, then run:

```sh
dotnet run --project Web/DungeonCrawlerTactics.Web.csproj
```

Open the local URL printed by .NET. Existing art is kept in `Web/wwwroot/assets`. To restore the small playable subset on a fresh checkout:

```sh
python3 Tools/prepare_hosted_assets.py Web/wwwroot --remote
```

Explore with the touch directional controls, WASD, or arrow keys. Press E or Enter to interact, and Esc to open or close the menu. Interact with nearby people and objects to advance the quest. In battle, select a party member, move, choose a skill and target, read the forecast, then confirm the action. Each crawler can move once and act once per turn; end the turn to let enemies respond. The safe room provides rest and saving. Equipment and skills are available through the party menus.

## Verify and publish

```sh
dotnet run --project Rebuild/Tests -c Release
dotnet publish Web/DungeonCrawlerTactics.Web.csproj -c Release -o Web/publish
python3 Tools/prepare_hosted_assets.py Web/publish/wwwroot
python3 -m http.server 8765 --directory Web/publish/wwwroot
```

Open `http://localhost:8765`. A browser integration check is available after installing Python Playwright and Chromium:

```sh
python3 Tools/playtest_floor_one.py --url http://localhost:8765 --browser /usr/bin/chromium
```

To check two generated layouts, prop collision and room screenshots:

```sh
python3 Tools/playtest_concept_layout.py --url http://localhost:8765 --browser /usr/bin/chromium
```

To capture the generated industrial workshop/boss rooms and enter the workshop battle through keyboard play:

```sh
python3 Tools/playtest_reference_arena.py --url http://localhost:8765 --browser /usr/bin/chromium
```

The reference-arena check uses seeds 1337 and 42, checks solid prop collision and the workshop board’s rightmost column, and records desktop/mobile screenshots and runtime JSON in `Rebuild/ReferenceArenaComparison/`. Exploration captures use a disclosed camera-only override to fit each room; they are review evidence, not a claim of pixel parity.

To add real keyboard doorway/bridge crossings and closeup layering captures to the arena checks:

```sh
python3 Tools/playtest_layered_maps.py --url http://localhost:8765 --browser /usr/bin/chromium
```

This runs the arena combat harness and records seeds 1337 and 42 in `Rebuild/LayeredMapComparison/`. Closeups use a disclosed camera-only override. `--skip-arena` is for visual iteration with reused arena evidence; omit it for final verification. Compare the captures with the reference before making any visual-match claim.

For five sequential visual review captures of the seed-1337 industrial rooms, use:

```sh
python3 Tools/capture_map_passes.py --url http://localhost:8765 --browser /usr/bin/chromium --stage pass-01 --label 'Wall depth' --output Rebuild/MyVisualReview
```

Use `--stage baseline` or `--stage pass-01` through `--stage pass-05`; each stage can be captured once, and its folder name is fixed by `--stage`. `--label` supplies the human-readable title. Choose a fresh `--output` directory for a new review set. The screenshot uses actual published WebAssembly room state and renderer output, with a disclosed camera-only framing override and renderer frame timestamp fixed at 1000 ms for comparable lighting. These images document visual review and are distinct from normal-clock gameplay checks above. See [the five-pass review](Rebuild/FIVE-PASS-REVIEW.md). The current comparison gallery is generated locally and is not included in a fresh checkout; final approved captures and retained rejected revisions are stored in `Rebuild/FivePassComparison/` in the working review environment.

The encounter check walks around solid prop footprints to the first encounter using keyboard input, selects and moves units on the canvas, confirms attacks, runs enemy turns, and checks the victory return.

The depth pass adds raised coping with a visible blue wall face and contact shadow, south parapet face gradients, an eastern pipe elbow joined to the channel bank, and two vine accents within blocked-cell bounds. It leaves floor proportions and room boundaries unchanged and uses the existing hosted assets. Final published-browser QA passed for the integrated inspector and map checks; the review still notes remaining source-art differences. See [the depth pass review](Rebuild/DEPTH-PASS-REVIEW.md) and the approved seed-1337 capture in `Rebuild/DepthPassComparison/pass-01/`. To reproduce the capture against a published host, use:

```sh
python3 Tools/capture_map_passes.py --url http://localhost:8765 --browser /usr/bin/chromium --stage pass-01 --label 'Depth pass' --output Rebuild/DepthPassComparison
```

For actual keyboard arena verification with doorway and full bridge crossings plus the read-only floor/wall surface identity audit, run:

```sh
python3 Tools/capture_map_refinement.py --layered --url http://localhost:8765 --browser /usr/bin/chromium --output Rebuild/DepthPassComparison/final-qa
```

The hosted asset manifest is `Tools/hosted-assets.json`: 91 individual files with checksums and an immutable AI-Art source revision. Publishing does not clone the full art repository or package every retained asset.

GitHub Pages builds on pushes to `main`, manual workflow dispatch, and `pages-dev-*` tags. Development tags can request a build without moving `main`; the GitHub Pages environment must also authorize that tag before deployment. The workflow runs the C# tests, publishes the WebAssembly host, and restores only the manifest subset.


## Map object scene graph

`Web/wwwroot/data/map-object-rules.json` catalogs 47 scene-graph types: 27 prop types, 12 terrain/render components, and 8 world-object or interaction kinds. `Web/wwwroot/map-scene-graph.js` builds a pure JavaScript presentation graph from the generated world and catalog. The graph groups objects under rooms and surfaces, while separately showing actual runtime relationships, declared connector geometry, and advisory expected relations. A containment parent means “belongs to this room or surface”; it does not imply a gameplay or physical edge. Advisory relations describe authored placement patterns and do not require that the related object exist.

Placement preview validates a candidate against catalog surface rules, runtime footprint and overlap, required relations where explicitly marked, and route preservation. The preview and placement suggestions operate on a copy of the imported world; exporting graph JSON is also read-only. The scene graph supplies renderer-facing geometry and connector relationships in JavaScript. Catalog assembly types describe authored groups by exact runtime `groupId` and room, with semantic member roles and expected counts; they do not create physical links. C# remains the authority for world generation and gameplay rules; this is not a rewrite of the C# generator. Port declarations are metadata, while active pipe attachments use the catalog's geometric connector rules rather than a general compatible-port solver. See [the object placement guide](Rebuild/OBJECT-PLACEMENT.md) and [the assembly pass review](Rebuild/ASSEMBLY-PASS-REVIEW.md) for scope and review status.

To inspect a generated world locally, publish and serve it as above, then open `http://localhost:8765/object-inspector.html`. The inspector uses the existing C# world generator, lets you select seed 1337 or 42, inspect placements, preview single-object moves, and export graph JSON. Selecting a runtime assembly exposes a read-only whole-group translation preview: set its target world origin or nudge one tile, then inspect member ghosts and the combined validation result. Every member keeps its existing offset, footprint, layer, rotation, and collision value. The preview checks bounds, support, collisions, interaction access, and route preservation together; it does not populate absent members, rotate or commit the assembly, or mutate the generated world. See [the assembly placement pass review](Rebuild/ASSEMBLY-PLACEMENT-REVIEW.md).

The scene-graph contract and fixtures can be checked with Node.js:

```sh
node Tools/test_map_scene_graph.mjs
```

Fixtures are retained in `Tools/fixtures/object-scenes.json`. Final published-host QA passed for both seeds for the existing inspector and map checks, including previews/exports, unchanged worlds, doorways, full bridge crossings, and the refreshed seed-42 eastern-pipe battle capture. Assembly-placement browser QA passed for seeds 1337 and 42, including stair translation, overlap/bounds rejection, teaching-table offset preservation, reset, and unchanged exports; the scene-graph suite passed 62 assembly no-op cases and route/access fixtures. See [the assembly placement review](Rebuild/ASSEMBLY-PLACEMENT-REVIEW.md) and [the assembly catalog review](Rebuild/ASSEMBLY-PASS-REVIEW.md). This assembly-placement pass also passed the full C# core suite, Node scene-graph suite, published-host checks with all 91 checksum-verified assets, and the required floor-one gameplay smoke. These checks cover the current assembly preview scope; they do not constitute a new full arena replay. See [the assembly placement review](Rebuild/ASSEMBLY-PLACEMENT-REVIEW.md) for its final report.

## Reset scope

This is a fresh game implementation. The former gameplay engine, Unity project, UI, generators and legacy tests were removed from the active source tree. The previous tracked revision is preserved by tag `archive/pre-rpg-reset-20261105`; `Rebuild/legacy-removal-inventory.json` records the removed files. Existing art files remain intact, and the separate AI-Art repository is unchanged.

Implemented scope is one connected floor, two party members, authored equipment and skills, tactical battles, a safe room, and a boss route. There is no claim of Unity Editor validation or a complete book adaptation.
