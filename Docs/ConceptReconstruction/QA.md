# Combat concept reconstruction QA

**Final frozen-export verdict: exact raster replay PASS; bounded source-visible fragment review PASS; procedural connectivity and layout-study review PASS.** This approves the delivered visible-fragment pack with the limits below. It does not certify recovery of original layers, hidden surfaces, editable typography, or a complete clean reusable object/whole-brick atlas.

The tested frozen export has **1,452 annotations: 1,317 visible component PNGs and 135 fully occluded annotations**. Every one of the 1,572,864 source pixels is covered exactly once. Pairwise overlap and uncovered pixels are zero; XOR changed pixels are zero. Independently reopened ORA recomposition and component-ZIP checks pass.

The source is `Web/wwwroot/assets/broadcast-kit/combat-concept.png`, 1536 × 1024 RGB, SHA-256 `414d0b05ffd1bf11a7e36538aadb4c0e2e6dcd03fc2e94739a77596c882368fe`.

## Independent checks

Run `python3 Tools/test_concept_reconstruction.py`. The verifier reconstructs only from component PNGs, then opens the original for comparison. It verifies unique IDs, labels/categories, source/component SHA-256 digests, tight bounds, binary alpha, zero RGB behind transparent pixels, pixel counts, provenance and canvas limits. It rejects a full-reference fallback, overlapping ownership and coverage gaps. It compares the independent replay by XOR with the source and exported reconstruction. It reopens the OpenRaster ZIP and independently recomposes its layer files and offsets, checking its merged preview too. The component ZIP is checked against its manifest and the exported files.

The verifier also independently traverses each procedural room from its entrance, excluding walls and water. Every walkable cell, exit and placed component must be reachable; component cells must be distinct. Current room studies for seeds 7, 29 and 103 have 74, 74 and 80 reachable cells respectively, with eight placed components apiece (six bodies and two props).

## Semantic review

Exact raster equality proves visible pixel accounting; it cannot prove correct semantic ownership. Reviews use the source, isolated exported components and contact sheets. Accepted bounded families: seven UI icon silhouettes, six corrected portrait silhouettes and source glyph-shaped text. Rectangular icon/portrait panel backings, Carl frame strips and Mongo muzzle overremoval were corrected. Actor color fringe pieces are named children and recombined in procedural body previews.

The rejected regular wall grid was replaced by explicit source-mortar cells for visible brick courses and capstones, plus honestly named residual `source-masonry-fragment` pieces. Source-joint montage and isolated wall samples were reviewed. The previously reported multi-brick source-fragment examples are superseded by physical-brick masks. These approximate residual pieces are not certified as complete whole-brick extractions.

All concrete defects raised during review were rechecked after correction: actor hair/feather fringes no longer remain in the reported floor cells; cyan route/red target effects have their own edge pieces; both yellow forecast-tail edges were removed from `floor-slab-r04-c06`; gold arch/pipe pieces and the north mounting plate have distinct components; the reported far-right vine fringe was reassigned. The final north test brick has no visible pixels because the separately exported metal mounting plate owns that area. Carl’s broad selected-floor wedges were removed from his visible body; thin baked source edge glow remains disclosed. The final focused comparison is recorded in `/tmp/final-accepted-focused.png`. No unresolved substantial foreign-object contamination remains in the reviewed cases. This is a targeted visual audit plus category overviews, not a proof that every ambiguous pixel has its original semantic owner.

## Browser and procedural review

The inspector was served through a local Python HTTP server and tested in real system Chromium through Playwright. Tests exercised reference/rebuilt/live-difference modes, search, visibility toggles, solo/restore, layer selection, bounds/PNG links, parent-child hierarchy and direct OpenRaster/manifest/component-ZIP links. Mobile testing at 390 × 844 found and fixed long-digest overflow. The final frozen 1,452-region export was reloaded in real Chromium at desktop and mobile sizes: 1,317 visible / 135 occluded rows, zero all-visible difference pixels, loaded seed-29 status, no horizontal overflow and no JavaScript errors. Demo captures are `/tmp/concept-inspector-final-desktop.png` and `/tmp/concept-inspector-final-mobile.png`.

The three procedural room studies were visibly reviewed: coherent distinct dry floor layouts, side water channels, source architecture, recognizable actors and readable source HUDs. Independent connectivity passes. The browser explicitly loads precomputed previews for seeds 7, 29 and 103; it displays loading/loaded status and downloads the corresponding placement recipe. Arbitrary seeds are generated by `python3 Tools/generate_concept_scene.py --seed 123`. This browser viewer does not run the Python generator. Repeated source textures, baked lighting and static source HUD values remain visible and disclosed.

## Limits

A flattened image contains no original layers or hidden surface pixels. Fully occluded annotations produce no invented source pixels. Text is raster glyph art rather than editable typography. One-pixel antialiasing and source-colored light/shadow boundaries can be ambiguous; they are not proof of original object mattes. Extracted effects can retain the substrate color baked into blended source pixels. Approximate fragments and normalized room-study assets must not be described as fully reusable production sprites or a recovered game renderer. No publication, commit or art-storage migration was performed by this QA task.

## Tested artifact SHA-256

| Artifact | SHA-256 |
| --- | --- |
| `manifest.json` | `0606b90e6466a7e51216bba0807b36d31e764cdafe4e6dd76bd85558ef072e25` |
| `combat-concept-components.zip` | `d88eba7f087b3e431f0ccd076a5f75b5c311f258b3feefb4d3d05da3f79b2fba` |
| `combat-concept.ora` | `3a01facb60684bbf01aece076827422ad43b3b2bcb6bc5cea0807a13d6ef4595` |
| `reconstructed.png` | `2e25e0f9703d69b2b786873f124d1571468e02b858bdbaf457a66a965065fc6d` |
| `procedural/room-7.png` | `0063343a266bbd10e5218f4e9f9afeba9a2808c89f707d99bc92ec932f50dae3` |
| `procedural/room-29.png` | `4b60ff91aba9cf4a014c274e50262759ea00a5bfc20f58e145c2f02ad4f8ca6d` |
| `procedural/room-103.png` | `82040d1a855898a77e798d288381d63f2ec9bb7ff56513c3fe477a561d60546e` |
