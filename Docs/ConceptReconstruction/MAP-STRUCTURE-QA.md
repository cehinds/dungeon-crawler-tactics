# Map structure QA

Scope: the source-art concept room generator. These checks do not establish playable-game behavior or semantic correctness of the original fragment annotations.

## Independent contracts

`Tools/test_concept_reconstruction.py` retains the original component digests, binary alpha ownership, exact-once coverage, pixel XOR, ZIP parity, and ORA reconstruction checks. Room verification additionally derives these properties from exported records rather than trusting engine validation booleans:

- Four-neighbor dry-terrain connectivity and a second graph with solid props removed. Every actor remains accessible; every prop has an accessible adjacent cell.
- Native portal anchor alignment and exact authored south-entrance crop, horizontal opening columns projected from actual art bounds, dry art/approach footprints, and exclusion of entity cells and rendered art from those areas.
- Every solid masonry cell has a rendered face and joins the board perimeter through masonry. Corner variants face actual exposed room neighbors.
- Entity art rectangles preserve the authored four-pixel separation. Pier, portal, actor, and prop draws share one upright layer with ground-contact sorting. HUD exclusion, terrain sockets, entity cardinality/spacing, and fixed raster HUD identity/state remain checked.

`Tools/test_concept_room_contract.py` defaults to 1,000 sequential seeds plus seven signed/unsigned and safe-integer boundaries. It repeats the full stream for byte determinism, requires multiple topologies and both channel sides, and compares published plans against the shared engine. Corruption fixtures cover bank orientation, missing entities/draws, malformed grids, HUD intrusion, unknown assets, portal width, pier layer/native size, missing masonry faces, portal/art overlap, entity/art overlap, forged foot depth, malformed presentation crops, water sockets, and a prop closing the only gate. Synthetic equal-screen-footprint tests isolate actor/prop and actor/pier ordering.

## Evidence

Before implementation, 1,319 component, manifest, and derived-catalog SHA-256 digests were captured in `/tmp/map-qa-frozen-hashes.json` for same-session preservation comparison. Baseline manifest SHA-256: `0f101ff69a5e736076f4c2cb12f3d911f410dc3878a707bc55cfbe0fc66199ce`; catalog: `86519c0e53da195c36bcea89a5be51f6e560b6956923420f34ca9f2ce0049bd6`.

Final canonical checks on 2026-10-31:

- `python3 Tools/test_concept_room_contract.py --count 1000` — PASS: 1,007 seeds including boundaries, byte-stable second run, published plan parity, 990 distinct topologies, 17 adversarial geometry/socket fixtures, eight fixed-HUD mismatch fixtures, and four malformed authored crops. Both channel sides appeared.
- `python3 Tools/test_concept_reconstruction.py` — PASS: 1,463 layers / 1,317 visible fragments, 1,572,864 pixels covered exactly once, zero XOR changes, matching ORA replay and component ZIP, and all four published rooms (7, 9, 29, 103) passed independent structure checks with exactly 12 entities each.
- Preservation comparison — all 1,319 baseline component/manifest/catalog files retained identical SHA-256 digests after canonical regeneration. This includes the original fragment manifest and derived catalog.
- Visual review — temporary previews 7/29/103 were inspected during refinement, then the final canonical `procedural/room-9.png` was opened and reviewed. Distinct actors, stepped masonry, native piers, full-width portal openings, the cropped south threshold, and HUD exclusion were confirmed in that representative image. This is a bounded visual review, not exhaustive visual review of 1,007 seeds.

Acceptance: PASS for the stated map-structure contracts and original-art preservation. The original fragment ownership still requires its separate semantic review; the exact raster replay does not settle that question.

## Limits

Connectivity treats actors as temporarily passable and props as permanent one-cell obstacles. Draw-order fixtures verify painter order, not pixel-perfect occlusion against every source texture. The source image and fixed HUD describe an illustrative composition, not recovered gameplay. Visual review remains necessary for material coherence, shape readability, and visual density.
