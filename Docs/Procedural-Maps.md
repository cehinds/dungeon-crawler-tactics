# Procedural maps

The [Dungeon Foundry](../Web/wwwroot/dungeon-generator.html) is a browser authoring tool for seeded standalone encounters. It generates connected chambers, natural caverns, or grand halls on boards from 6×6 to 20×16 cells, with a target of 2–6 rooms and adjustable prop density. Small boards may fit fewer rooms than requested. A fixed seed and the same generation settings reproduce the layout.

## Preview and themes

The live preview uses the native Book Location Tiles library. Choose Pocket Dungeon, Ink & Lanterns, or Dungeon After Dark, then select one of 31 environment kits. Inspect the map in square art mode or blueprint. The tile grid is orthogonal with 128×128 logical cells. The preview uses square floors, frontal doors, and props and landmarks from the selected kit; it does not mix pieces from related kits. Each room uses one of floor cells 0–3 as its base, with small coherent two-cell wear patches when **Vary room materials** is on. Turn it off for a uniform floor. Environment ambiance changes the preview backdrop and glow, not the art pixels. Material and atmosphere choices are preview metadata; the separate **Playable terrain** control keeps the canonical Stone stronghold, Forgotten sewer, and Ancient crypt choices for game export.

The map reserves connected, walkable positions for the entrance, party, enemies, and exit before adding decoration. The entrance and exit are interior portals; the outer boundary stays blocked. The entrance uses open-door art and the exit uses open-door and stairs art; both are visibly labeled, and the route overlay shows the connected path. The exit is placed at the graph-distant reachable cell and excluded from party spawns. Decorations cannot block those reserved positions or disconnect the dry route.

The selected environment kit supplies preview-only landmarks. A **Blocked object** outline marks a movement-blocking decoration from the canonical playable map at its actual cell and footprint; the decorative book-art landmark itself does not create collision. W, O, and F markers and counts show playable water, oil, and fire tags from the exported map. A wet-looking illustrated floor alone is decorative and is not a hazard. Rotate the whole map in 90-degree steps. Zoom with the controls or `+` and `−`; drag to pan while zoomed, use arrow keys to pan, and press Home or **Fit map** to reset.

## Edit, export, and play

Open a generated layout in the room workshop for manual edits. A recipe preserves the authoring settings and generated layout. The book-library art is for the generator preview: workshop handoff and playable JSON use the canonical room kit and runtime-supported map schema, not the native Book Location Tiles art or theme metadata. Recipe data can retain authoring details, but importing a playable map does not add new tile art, environment themes, or combat rules to the game.

Starting a map launches a standalone encounter and replaces the active run, so export the current campaign save first if you want to keep it. The existing win condition remains defeating all enemies. The exit is a connected route endpoint shown in the preview, not an extraction objective or a new way to complete combat. Invalid playable JSON is rejected without replacing the current run. Generated maps do not enter campaign progression.

The generator is browser authoring JavaScript. Play uses the shared C# runtime and its canonical assets and rules. Style, kit, and floor-variety settings are retained as recipe/workshop visual-authoring metadata and removed from strict canonical playable JSON. No Unity scene or Unity Tile integration is implied by the preview.

## Reproducibility and implementation

Keep the seed, layout, gameplay biome, art style, environment theme, dimensions, density, and requested room count with a recipe. Preview rotation does not change the generated layout. Changes to the generator or its asset library can affect later regeneration; keep the recipe and playable JSON when an exact authored result matters.

Playable biome material and themes are authored in `Web/wwwroot/assets/map-generation-rules.json`. Deterministic layout generation and the canonical playable-map adapter are in `Web/wwwroot/procedural-map.js`; native tile loading and preview rendering are in `Web/wwwroot/generator-art.js` and `Web/wwwroot/dungeon-generator.js`.

## Validation status

156 Python tests passed. Node checks passed for 720 generation cases, 721 schema-valid exports, 461 room-generation checks, 640 rotated-picking checks, and 558 native-art scenes. Four generated maps imported into the shared C# runtime and workshop handoff passed. The generator UI passed nine style/theme combinations, including desktop and mobile layout, zoom/pan/rotation, material variation, grid/route overlays, recipe metadata, canonical playable export, PNG download, cancellation, and failure/retry handling. Expanded browser QA passed across all 93 tile variants. Publication is tracked by the [Pages deployment workflow](https://github.com/cehinds/dungeon-crawler-tactics/actions/workflows/deploy-pages.yml) after push to main. Unity Editor validation has not been run.
