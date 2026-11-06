# Layered map assembly notes

This is a visual assembly guide for the generation-4 procedural arena pass. It records reusable art and practical ordering for layered map drawing. It does not define game rules, collision, navigation, or canonical lore; those remain separate authored data and runtime decisions.

## Reference target and approach

Use `Web/wwwroot/assets/reference-layers/clean-map.png` as the map composition target. It is a broad central stone floor surrounded by raised blue masonry, with gold-capped wall edges, a large northern gate, and water channels with a bridge on the right. The cleaned image includes inferred underpainting, so it is useful for layout and silhouette study rather than evidence of hidden source pixels.

The renderer now assembles wall faces and cap rails at actual wall boundaries, bridge decks over existing dry crossings, and doorway details at narrow open corridor boundaries. These overlays do not supply collision. The industrial workshop and boss chamber share an 18 × 11 inset footprint with a reserved 12 × 6 central area, asymmetric three-column water wings, explicit three-cell-long dry crossings, and a northern gate right of center. Its C#-validated `tileRows` footprint is authored in the room rules. The current world is 90 × 52 with 22 × 16 sectors; historical versions retain 60 × 38 maps. Version 1/2/3 saves validate against their historical generators before migrating to this version-4 layout.

`Tools/playtest_layered_maps.py` produces actual published-browser arena captures and keyboard doorway/bridge crossing closeups for seeds 1337 and 42 in `Rebuild/LayeredMapComparison/`. It runs the reference-arena combat harness unless `--skip-arena` is supplied for visual iteration. Closeups use a disclosed camera-only framing override. Compare the generated screenshots with `reference-layers/clean-map.png`; implementation and traversal checks alone do not establish visual parity.

## Small reusable kit

All paths below are relative to the repository root. The art is already in `Web/wwwroot/assets`; no copying or repacking is required for a renderer that can load those files.

| Need | Reusable files | Verified metadata and practical limit |
| --- | --- | --- |
| Complete masonry doorway frame | `Web/wwwroot/assets/completed-layers/components/props-doorleftjamb.png`, `props-rightjamb.png`, `props-lintel.png`, `props-threshold.png` | Each is 128×128 with bottom-center pivot `[64,128]`. `completed-layers/manifest.json` defines jamb↔lintel↔threshold sockets and wall/floor sockets. The four layers form a coherent frame; place them as one aligned assembly and preserve their painter order. They are visual components, not collision or door-state logic. |
| Alternate blue stone doorway | `Web/wwwroot/assets/wall-components/parts/doorway-jamb-west.png`, `doorway-jamb-east.png`, `doorway-lintel.png`, `doorway-threshold.png`; optional `doorway-arch.png` | Native detail overlays are 128×128. The arch is a 128×128 crop intended to span a two-cell opening; the rectangular sample uses explicit side adapters. These details do not automatically socket to the 64-pixel network tiles, and threshold pixels are very subtle. Avoid automatic rotation because the light is directional. |
| Straight wall courses and caps | `Web/wwwroot/assets/completed-layers/components/walls-plain.png`, `walls-capH.png`, `walls-capV.png` | Each is 128×128, bottom-center pivot `[64,128]`. Manifest edges distinguish `stone-wall-join` from `exposed-stone-end`. Use cap direction to end a course cleanly; repeated plain wall pieces have unconstrained sockets and are less suitable for validating a continuous edge contract. |
| Inner and outer corners | `Web/wwwroot/assets/completed-layers/components/walls-outerNW.png`, `walls-outerNE.png`, `walls-outerSE.png`, `walls-outerSW.png`; matching `walls-innerNW.png`, `walls-innerNE.png`, `walls-innerSE.png`, `walls-innerSW.png` | Each is 128×128 and bottom-center pivoted. Their manifest socket directions identify which edges are joins and which are exposed. These are native painted details; do not rotate to a new orientation without checking light and edge alignment. |
| Water crossings | `Web/wwwroot/assets/completed-layers/components/water-woodbridge.png` or `water-ironbridge.png` | Each is 128×128 and bottom-center pivoted. Manifest sockets label north/south as channel entry/exit and east/west as stone abutments. They visually bridge a channel; map connectivity, walkability, and water hazards still come from the runtime map model. The current renderer uses the separate alpha deck `assets/map-grid-pass/expansion/native/water/water-ironbridge-iron-deck.png` over water backing on dry crossing cells. |
| Cardinal wall network alternative | `Web/wwwroot/assets/wall-components/tiles/` plus `layers/` | The pack has all 16 cardinal masks as 64×96 PNGs on a 64px grid, 64×64 logical footprint, 32px bottom overhang, center pivot `[32,32]`, and 32px cap. For layered placement draw `*-shadow`, then `*-face`, then `*-cap`. Neighbor edge tags use `stone-network-32-v1` or `empty`. The pack is a visual kit and does not define collision/depth sorting. |

The current corridor frame uses separate `water-dryarch-left-jamb.png`, `water-dryarch-right-jamb.png` and `water-dryarch-lintel.png` overlays from `assets/map-grid-pass/expansion/native/water/`. The gold gate retains its complete exit artwork. These are visual assemblies over explicit openings.

The reusable door, wall, corner, and bridge metadata above comes from `Web/wwwroot/assets/completed-layers/manifest.json`. For the 64px-grid network pack, see `Web/wwwroot/assets/wall-components/GUIDE.md` and `manifest.json`; the pack guide records its placement and adapter limits.

## Mounted fixtures and collision

The industrial north apron uses actual `#` wall cells around its gate opening, with a small eastern water inset. Machinery, pipe banks and gate torches use `layer: "wallfixture"` on those wall cells. C# validates that their full footprints remain blocked masonry. Decorative nonblocking pipes may overlap the solid machinery footprint; they do not add a second collision rule. The renderer preserves the wall beneath these fixtures by excluding them from its furniture floor-restoration mask, then merges fixtures, other foreground props and wall fronts by depth around actors. Bridge deck art likewise covers explicit dry cells rather than opening water cells.

## Practical painter order

For a 2D top-down composition, assemble each local area in this order, adjusting only where the image clearly requires it:

1. Draw ground and channel backgrounds.
2. Draw floor slabs, approach paths, and bridge deck surfaces.
3. Draw wall shadows, then wall faces/courses.
4. Draw caps, corner details, and doorway frame pieces. For the 64px network tiles, keep the required shadow→face→cap order.
5. Draw overlays that belong on top of the path, such as threshold accents, grates, water highlights, or small debris.
6. Draw actors and foreground details according to their intended depth.

A walkway may overlap the top of a wall or bridge abutment in image space. Keep its logical walkable cells explicit in map data; use the renderer's depth order to hide seams, not to infer traversal. At a doorway, leave a visible opening through the wall course and place jambs on its sides, lintel above, and threshold across the floor edge. For long walls, make adjacent courses meet on their join edges and finish exposed ends with a cap or corner asset. Do not stretch 128px art across arbitrary distances if the tiled wall network can represent it cleanly.

## Implementation and verification status

- [x] Assemble the inset platform, asymmetric water wings and right-of-center gate against `reference-layers/clean-map.png`; preserve a clear 12 × 6 central floor.
- [x] Keep bridge crossings and gate openings explicit in C# tiles; retain blocked masonry under wall fixtures.
- [x] Merge foreground wall faces, mounted fixtures and props by depth around actors; suppress generic frames near the complete gold exit.
- [x] Verify the four added hosted overlay assets against SHA-256 checksums at the manifest's immutable remote revision.
- [x] Review final structural/layered browser capture against the reference; this accepts the structural pass, without claiming pixel parity.
- [x] Pass C# generation, route, collision, spawn and v1/v2/v3 migration checks on the final geometry.
- [ ] Run the complete browser combat, doorway/bridge crossing and desktop/mobile checks on the final committed wall-fixture build.
- [ ] Inspect the final QA screenshots for native-size wall joins, door openings, bridge banks and overlap popping; retain camera-only framing disclosures.

## Limits

These assets come from existing concept and map-art packs. Some are derived partitions or normalized overlays, and the 64px network tiles are assembled variants of those sources. Their pivots, image bounds, and socket labels support visual placement; they do not promise pixel-perfect joins for every arbitrary scale or composition. The clean-map layer pack separates this one reference composition and its inferred underpaint; it is not a general-purpose room kit. Nothing in this note establishes lore or gameplay behavior as canonical.
