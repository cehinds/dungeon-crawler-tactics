# Reference arena reconstruction notes

This is a visual assembly brief for the blue-slate industrial arena requested for the First Floor. The closest exact source is the flattened combat concept at `Web/wwwroot/assets/broadcast-kit/combat-concept.png`, presented with editable crops in `Web/wwwroot/assets/reference-layers/`. This is a supplied combat illustration, not a canonical Book 1 map or measured room plan. `reference-layers/clean-map.png` is the inferred clean environment plate; `reference-layers/original-reference.png` is the exact flattened source comparison. Open `reference-layers/README.md` before consuming the layer pack: visible fragments, generated underpaint, context restorations, and complete reusable atlas art have different provenance.

## Reusable art and source mapping

| Requested feature | Best existing material | Use and limits |
| --- | --- | --- |
| Slate square floor | `Web/wwwroot/assets/map-grid-pass/components/generated/floor-dry.png`, `floor-wet.png`, `floor-reflection.png`, `floor-cracked.png`; source-visible floor pieces in `reference-layers/layers/floor-slab-*.png` | Generated modules are alternatives for a newly assembled floor. Exact source fragments are cropped floor pixels at native scene positions; use the full clean-map plate when a background is enough. |
| North industrial gold stair exit | Full reusable composite: `Web/wwwroot/assets/completed-layers/components/complete-gold-exit.png` (198 × 204, pivot bottom-center); native art: `completed-layers/native/complete-gold-exit.png` (915 × 943). Exact source alternative: `concept-reconstruction/components/exit-architecture/` plus torch crops. | The scaled completed-layer recipe places the composite at `[916,4]`, z=30136, with source-aligned target bounds `[895,0,1135,212]` on the 1536 × 1024 canvas. It depicts the full gold doorway, stairs and threshold grille, so it is a practical ready-made exit component. This is inferred completed architecture, not source pixels. The exact separate source crops retain their original positions and are preferable for pixel-faithful replay. `floor-one-concepts-top-down/panels/entrance-stairs.png` is a different, generic descent reference. |
| Side channels and waterfalls | `reference-layers/layers/water-channel-*-flow-*.png`, `west-waterfall.png`, `east-waterfall.png`, `southeast-waterfall.png`, `east-arched-water-outlet.png`; generated options `map-grid-pass/components/generated/{water-surface,water-outlet,floor-wet,floor-reflection}.png` | Exact crops reproduce visible water at source coordinates. Generated pieces can form a variant; channel bends, bridge/crossing, waterfall banks, and source-specific joins still need authored assembly. |
| North pipes and controls | `reference-layers/layers/north-pipe-*-segment-*.png`, `north-control-{power,switches,meter}.png`, `north-machine-*.png`; generated `pipe-{straight,tee,elbow}.png` and `machine-controls.png` | Source pieces are assembled in place and may rely on neighboring wall context. Generated pieces are modular alternatives and are not a pixel-exact match. |
| Navy stone walls and caps | `reference-layers/layers/wall-source-stone-*.png`, `brick-exit-*-pier-*.png`; generated `wall-{straight,outer-corner,inner-corner,low-cap,pillar,broken}.png` | Original exact visible masonry is highly fragmented (917 architecture records plus restorations). Generated cap/corner pieces are a useful starting kit; long courses, irregular foreground apron, and clean end joins need review. |
| Grates, crates, barrel, moss | `reference-layers/layers/{west,east,south}-floor-grate.png`, `*-crate-*.png`, `explosive-barrel.png`, `*-vine*.png`; generated `{grate,crate,moss-hanging}.png` | Source positions are grounded in the reference image. Moss and vines are source-visible decoration, not proof that all First Floor walls are overgrown. |
| Warm pools and gold reflections | Exit torch crops above; `exit-gold-reflection.png`; `map-grid-pass/components/generated/floor-reflection.png` | Source has baked warm lighting. Keep generated reflections and glows as separate overlays where possible; no dynamic lighting behavior is implied. |

The native source canvas is **1536 × 1024** pixels, origin at top-left. For exact fragments, `reference-layers/scene.json` is the placement authority: each layer's `offset` is its crop top-left, `size` is crop size, and `z` is painter order. It exports 1,262 original-visible layer records, 23 inferred underpaint patches, and 310 context restorations; the source is flattened, so hidden surfaces are not recoverable. The map-grid and completed-layer component catalogs are authored/inferred designs, not extracted source art.

For a source-pixel exit assembly, these exact `[x, y, width, height]` rectangles are listed in `concept-reconstruction/manifest.json` and match the source canvas. Draw surround/walls behind the opening, then stair and threshold, then the separate torch effects; use manifest z-values for the exact original order.

| Exit crop | Native source rectangle |
| --- | --- |
| Left column / right column | `[899,0,44,153]` / `[1080,0,51,153]` |
| Lintel / upper light | `[943,0,137,32]` / `[987,0,50,29]` |
| Left rail / right rail | `[939,29,23,153]` / `[1065,29,21,154]` |
| Stairs / threshold grille | `[962,33,103,105]` / `[963,139,104,58]` |
| Hazard bases, left / right | `[898,153,47,42]` / `[1080,153,53,44]` |
| Torches, left / right (flame) | `[854,62,34,66]` / `[1140,62,34,66]` |
| Torches, left / right (bracket) | `[854,119,37,28]` / `[1140,119,37,28]` |

The source `reference-layers/layers/` crops use these same native canvas offsets. `completed-layers/components/complete-gold-exit.png` is the intended ready-made composite when an inferred full structure is acceptable; it does not include those original source coordinates internally and should be placed using the recipe's aligned instance above.

## Placement guide

Use normalized `(x, y, width, height)` measured from the top-left of the 1536 × 1024 canvas. These are broad composition guides for a new variant, not canonical coordinates. The exact source plate is asymmetric; the current runtime adaptation retains a northern exit right of center.

| Region | Approximate normalized placement | Assembly cue |
| --- | --- | --- |
| North exit and gold stair frame | x .43–.74, y 0–.21 | Place right of center on the north wall; use the complete-gold-exit component or assemble columns, lintel, frame rails, dark stair opening, treads, threshold grille and paired warm lights. |
| North-west machinery bank | x .20–.43, y 0–.22 | Cluster vertical pipes, collars and control panels against the back wall; leave a clear gap to the stair frame. |
| Main slate arena | x .19–.80, y .17–.76 | Large, nearly square playable floor with broad readable central space and restrained wet patches. Preserve the original grid rhythm. |
| West water run and falls | x 0–.20, y .13–.51 | Dark masonry banks contain a bright blue channel; waterfall drops from an arched outlet near the north-west. |
| East water run and falls | x .79–1, y .12–.84 | Narrow channel follows the east edge and turns into the lower-right basin; show water boundaries and outlet arches clearly. |
| South foreground wall/apron | x 0–1, y .68–.90 | Layer irregular navy blocks and highlighted capstones in front of the room; allow wall breaks for channel crossings. |
| Small fixtures | Interior margins and channel banks | Place floor grates, crates and one warm barrel near edges; avoid crowding the arena center or stair approach. |

For a source-faithful assembly, use exact native offsets from `reference-layers/scene.json` rather than the normalized adaptation table. The exact exit's major pieces occupy x=854–1177 (about .56–.77 canvas width), with its architectural surround concentrated at x=898–1133, y=0–197. Its center is right of the canvas center, and the current runtime retains that right-of-center relationship as an authored adaptation. The completed composite's aligned target bounds are wider, x=895–1135, y=0–212.

## Painter order

Use the semantic scene groups as the starting order, then depth-sort individual foreground objects by contact point:

1. Continuous base floor and wall underpaint. Mark reconstructed pixels as inferred; do not call hidden background original art.
2. Water bodies and channel runs.
3. Floor slabs, wet patches, reflections, and low ground details.
4. Back wall courses, outlet arches, exit surround, and north machinery mounts.
5. Pipes, controls, hanging moss, torches, and other wall fixtures.
6. Exit stair treads and threshold grille; floor grates and edge props.
7. Foreground wall caps, projecting blocks, and any foreground prop portions that must overlap the floor.
8. Combat actors/effects/UI, if needed by the consuming renderer. These are separate from static environment art.

The source pack's `z` values preserve its original painter order and take precedence when replaying its exact composition. The order above is a semantic guide for new assembly, not a renderer contract.

## Floor One adaptations and gaps

The supplied art reads as an industrial combat arena, and its room identity is an authored visual adaptation. Book 1 evidence supports named Floor One places and functions, not this precise room, water system, machinery plan, wall geometry, stair position, crate inventory, or tile measurements. If attached to `goblin-workshop`, workshop/explosive context has Floor One support (`goblins`, `chapter15` in `Rebuild/ReferenceData/book-one-floor-one.json`); exact machinery and room plan remain game-authored. A stair/arena can also evoke the Ball of Swine descent, but its spiral maze, bridges, switch chamber and stairwell are distinct lore cues; do not claim this rectangular industrial room depicts the canonical layout.

Keep Floor One deployable actors to Carl and Princess Donut. Do not place Katia or Mongo in this Floor One arena: their visible source fragments in the combat concept are reference-image content, not permission to expand the Floor One party. Mordecai is an NPC guide, not a deployable character. Any gameplay hazards, water traversal rules, exit transitions, and encounter choreography require explicit game-authored behavior.

Visual review remains necessary: connect wall courses and capstone ends around the full asymmetric perimeter; finish water bends, bank walls, bridge/crossing and waterfall bases; join the north pipe/control bank cleanly to the walls; review the right-of-center exit assembly in our runtime variant; review floor/prop grounding and warm light; verify the arena remains open and navigable. The component coverage audit in `Web/wwwroot/assets/map-grid-pass/` marks its quadrants as not visually accepted. Do not treat a component's presence in the pack as proof the full room has been reconstructed or integrated into runtime.

## Current runtime integration

New worlds use generation version 4 on a 90 × 52 map. The goblin workshop and Ball of Swine room use the shared industrial-sewer composition from `Web/wwwroot/data/concept-room-rules.json`; the C# rules derive each 18 × 11 tactical board from its generated exploration room, including blocked tiles, water and room-relative props. Other encounters remain 10 × 8. The renderer assembles the runtime scene from reusable components; this is an authored adaptation rather than a replay of the flattened reference. Supported version 1, version 2 and version 3 safe-room checkpoints are validated against their original generators before migration to version 4. Historical versions retain their 60 × 38 world geometry. The current authored footprint reserves a 12 × 6 central floor, with asymmetric water wings, three-cell dry crossings and blocked northern masonry carrying wall fixtures.

Run `Tools/playtest_reference_arena.py --url http://localhost:8765 --browser /usr/bin/chromium` against the published host. It captures seeds 1337 and 42, keyboard travel into encounters, prop collision, workshop combat input at the rightmost column, and desktop/mobile views. Output in `Rebuild/ReferenceArenaComparison/` includes screenshots, world/battle JSON, a comparison page and a report. Room screenshots use a disclosed camera-only response override; gameplay state and geometry come from the published WebAssembly engine. Comparison artifacts do not establish pixel parity, visual acceptance or deployment.
