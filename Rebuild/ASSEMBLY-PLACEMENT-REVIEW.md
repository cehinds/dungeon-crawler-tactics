# Assembly placement preview review

## Scope

This pass adds a read-only whole-assembly translation preview for existing runtime groups. It preserves runtime member offsets and validates proposed members as one batch. It does not auto-populate a template, rotate groups, commit to the C# world, or mutate the source map.

The graph API accepts an assembly node and a target composite-bounds origin. The inspector takes a target world group origin and translates it to that API coordinate. Runtime footprints, layers, rotations, and blocking values remain attached to each member. Validation checks map bounds, full-footprint support, external and internal solid overlap, and protected access for existing interaction objects. Route checks evaluate the combined proposed solid footprint. The preview is limited to the current generated/runtime map and does not write a changed map or save.

## Verification

Published-browser QA passed for seeds 1337 and 42. The inspector accepted a one-tile translation of the three-member stair approach, rejected a collision and out-of-bounds target, and accepted a no-op. The authored teaching-table assembly passed a no-op check while retaining its rug overlap, member offsets, and rotations. UI nudging and reset worked; world and exported graph data remained unchanged, with no browser errors or mobile overflow.

The scene-graph suite passed 62 authored assembly no-op cases and batch route/access fixtures. The full C# core suite, published-host checks with all 91 checksum-verified assets, and required floor-one gameplay smoke also passed. Workshop and boss gameplay captures remained byte-identical. These checks validate the bounded preview feature; they are not a new full arena replay or a change to C# world generation. The final inspector report is `Rebuild/AssemblyPlacementComparison/final/report.json`.
