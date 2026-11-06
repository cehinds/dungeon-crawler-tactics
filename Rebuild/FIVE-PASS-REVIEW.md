# Five-pass map art review

Review target: `Web/wwwroot/assets/reference-layers/clean-map.png` compared with `Rebuild/LayeredMapComparison/Final/seed-1337-boss.png`. This is a visual direction checklist for the next five art passes; it does not claim pixel parity. Keep the Floor One map lore and characters intact. Preserve the authored walkable floor, obstacles, water, and fixture collision rules while improving presentation.

## Pass 1 — Wall faces and depth — approved

- The reference has irregular block scale, broken silhouettes, deep shadow under the upper wall and around the lower masonry, and foliage breaking up long edges. The current baseline reads as a uniform dark brick backing with thin pale cap strips and abrupt rectangular cutouts.
- Strengthen foreground/background separation: add a consistent dark face/shadow beneath wall caps, shape wall ends and corners around channels and the southern approach, and break long straight runs with restrained masonry variation and vines. Keep doorway/gate opening legible; don't let decorative pixels imply walkable cells.
- Candidate source assets: `Web/wwwroot/assets/wall-components/layers/` (face, cap, and shadow variants by wall shape); `Web/wwwroot/assets/wall-components/parts/` (outer/inner boundaries and doorway jamb/lintel/threshold); `Web/wwwroot/assets/book-tiles/dungeon-after-dark/starter-dungeon/components/starter-dungeon-dark-stone-block-wall-northwest.png` and `...-northeast.png` (native masonry edge pieces).
- Implemented in `Rebuild/FivePassComparison/pass-01/seed-1337-boss.png`: layered masonry faces, caps, and corner shaping give the wall mass clearer depth around the arena and water. The gate opening and current room footprint remain legible. Root visually approved this pass. Remaining difference: wall courses and edges still look more regular than the broken, foliage-softened reference.

## Pass 2 — Water and banks — approved after correction

- Reference water has dark-to-cyan depth, broken white foam, visible splash at outlets, and uneven stone banks with moss. Baseline water is a repeated bright cyan lattice bounded by thin straight outlines, so it competes with the arena floor and reads like a flat tile fill.
- Reduce repeated high-contrast highlights; add dark pool variation, localized foam/splashes at the four visible outlets, and layered bank stones that overlap water edges naturally. Preserve the dry crossings and impassable water footprint exactly.
- Candidate source assets: `Web/wwwroot/assets/top-down-layer-kit/scenes/kua-entrance-chamber/reusable/components/kua-entrance-chamber-west-water-basin.png`, `.../kua-entrance-chamber-east-water-basin.png`, and `.../kua-entrance-chamber-aquatic-floor-mosaic.png` (water/basin treatment); `Web/wwwroot/assets/top-down-layer-kit/scenes/green-slime-territory/reusable/components/drain-nw.png`, `drain-east.png`, and `drain-south.png` (outlet/drain details). Adapt as presentation overlays only.
- The first water revision was rejected for being too dark; its evidence is retained at `Rebuild/FivePassComparison/revisions/pass-02-too-dark/`. The corrected approved capture is `Rebuild/FivePassComparison/pass-02/seed-1337-boss.png`: water now has a deeper blue base with readable cyan surface detail and localized edge foam/splash cues. Root visually approved the correction. Remaining difference: the reference has brighter broken white highlights and more varied bank silhouettes.

## Pass 3 — Pipe routes and connections — approved

- In the reference, pipes turn into the wall, use collars and junctions, and visibly terminate at water outlets or machinery. The baseline has isolated vertical pipe segments above the room and separate pipes in side pools; their cut ends look unconnected.
- Make each visible run feel mounted: add wall-entry collars, elbows/tees where appropriate, shadow/contact at masonry, and connect outlet ends visually to splash points. Preserve existing fixture locations and collision. Avoid moving map objects or implying new routes.
- Candidate source assets: `Web/wwwroot/assets/top-down-layer-kit/scenes/connecting-alley/reusable/components/pipe-nw.png`, `pipe-center.png`, `pipe-south.png`, and `grate-north.png` (pipe junction and grate language); `Web/wwwroot/assets/top-down-layer-kit/scenes/swine-switch-chamber/reusable/components/rail-piece-00.png` through `rail-piece-05.png` (modular industrial line segments where suitable).
- Implemented in `Rebuild/FivePassComparison/pass-03/seed-1337-boss.png`: added wall-entry/turn details and contact treatments so the pipe runs read as mounted infrastructure with outlet relationships. Root visually approved this pass. Remaining difference: the reference has more continuous pipe routing across the upper machinery wall.

## Pass 4 — Floor variation — approved after revision

- The reference floor varies tile wear and color, has wet patches and drain grates, and uses small warm/cool reflections to guide the eye. Baseline's large arena reads as a repeated blue-gray grid with only a few nearly black patches and grates.
- Add restrained per-tile wear and hue variation, localized wetness near water and drains, a few scuffs/stains, and richer grates with inset shadows. Keep the playable central lane visually calm and readable; do not alter its tile or obstacle data.
- Candidate source assets: `Web/wwwroot/assets/book-tiles/dungeon-after-dark/starter-dungeon/components/starter-dungeon-grey-flagstone-floor.png`, `starter-dungeon-worn-grey-flagstone-floor.png`, `starter-dungeon-cracked-grey-flagstone-floor.png`, and `starter-dungeon-wet-grey-flagstone-floor.png` (surface variation); `Web/wwwroot/assets/top-down-layer-kit/scenes/connecting-alley/reusable/components/grate-north.png`, `grate-east.png`, `grate-south.png`, and `grate-west.png` (grate forms).
- The initial revision was rejected for looking too uniform; that superseded capture is retained at `Rebuild/FivePassComparison/revisions/pass-04-too-uniform/`.
- Revised approved capture: `Rebuild/FivePassComparison/pass-04/seed-1337-boss.png` adds broader fractures and contrasting wet patches near channels and drains. Root approved this result. Remaining difference: the tile textures still repeat and feel less hand-painted than the reference.

## Pass 5 — Lighting integration — approved

- The reference has localized amber torch pools and gold reflections, alongside deep blue ambient shadow and cyan bounce from water. Baseline has bright torches and gold trim at the north gate, but little colored spill on adjacent stone and no readable reflections on nearby floor or water.
- Integrate soft, bounded warm light beneath the gate torches and warm machinery, cool bounce at channel edges, and restrained glints on wet floor. Keep dark corners dark and preserve contrast around units, target markers, and text; no actor or HUD redesign is in scope.
- Candidate source assets: `Web/wwwroot/assets/top-down-layer-kit/scenes/swine-switch-chamber/reusable/components/torch-ne-estimated-glow.png`, `torch-nw-estimated-glow.png`, `torch-e1-estimated-glow.png`, `torch-e2-estimated-glow.png`, `torch-w1-estimated-glow.png`, and `torch-w2-estimated-glow.png` (soft light reference); `Web/wwwroot/assets/book-tiles/dungeon-after-dark/starter-dungeon/components/starter-dungeon-wall-torch.png` (native torch artwork). Treat glows as presentation layers, never as changes to collision or visibility rules.
- Implemented in `Rebuild/FivePassComparison/pass-05/seed-1337-boss.png`: warm torch/machinery spill and cool channel bounce now reach nearby stone and water while keeping the central lane readable. Root visually approved this pass. The five-pass visual set is recorded in `Rebuild/FivePassComparison/`; its gallery is generated locally and is not part of a fresh checkout.

## Completion record

All five passes have visual approval, with rejections and corrected captures retained. Remaining source differences include repeated tile texture, lighter wall depth and less authored clutter than the reference, and a room silhouette that is not identical. This is an approved art iteration, not a 1:1 reproduction claim.

## Verification

Final QA passed: 102 C# tests, full Web publish with all 91 hosted assets verified, Floor One browser UI/combat/enemy-turn/victory flow on the normal animation clock, and fresh arena plus layered traversal checks for seeds 1337 and 42 on the normal animation clock. Arena evidence was not reused; keyboard doorway and full bridge crossings passed for both seeds. No runtime errors or missing game assets were reported. Details are in `Rebuild/FivePassComparison/final-qa/verification.json` and its referenced logs/reports. The captured source renderer fingerprint matches the verified final visual suite; it records the pre-commit source state, not a post-commit revision.
