# Exploration room components

This offline art kit catalogs visible reference evidence and a separate set of reconstructed whole props from the bedroom, training, crafting, forge, corridor, and HUD areas in the exploration concept. The package lives under `Web/wwwroot/assets/exploration-components/`; its `manifest.json` is the authority for each component's ID, category, file, pixel dimensions, pivot, suggested draw layer, decoded-pixel hash, deduplication result, and provenance. The archive is `exploration-components.zip`.

## What's included

The final manifest contains 126 component records: 64 inferred whole-object illustrations, 57 source-visible rectangular context crops, and five clean surface patches. The inferred illustrations break down as 16 bedroom, three entry, six training, seven craft, 13 forge, three effects, four actors, and 12 HUD/UI pieces. The source evidence inventory has 57 crops spanning bedroom/entry, training, craft, forge, actors, and HUD, plus five clean surface regions including the corridor floor. Read `provenance.kind` before using an image:

- `context-containing-reference-crop` is a literal rectangular crop from the flattened concept. It preserves those source pixels exactly, but may include floor, neighboring props, overlaps, shadows, or occlusion. It is evidence from the reference, not a cutout of a complete object.
- `visible-clean-surface-patch` is a visible clean floor or wall region suitable for a limited surface fill. It does not reveal hidden surface detail and can retain seams when repeated.
- `inferred-restored-whole-object` is an AI-inferred, transparent alternate reconstruction intended to provide a reusable complete object. It is not a recovered original layer or a pixel-exact crop of the reference.

The four actor illustrations are single poses; the HUD/UI entries are fixed portrait, action-icon, and blank-panel art rather than animations or live interface state. The manifest's counts describe exported records, not unique source objects, exact object coverage, or newly painted illustrations. A source crop can contain multiple visible things; multiple annotations can overlap. Flattening obscures the pixels behind objects, and the pack does not fill every missing or occluded part of the source. The numbered source preview and `sourceAnnotations` list make the audited crop inventory explicit; unannotated areas are not claimed as extracted components.

## Provenance and duplicate handling

Each restored illustration is labeled as inferred even where it closely resembles a source prop. The build scans existing PNGs in `Web/wwwroot/assets/` and reuses one only when dimensions and every decoded RGBA byte match. `deduplication.algorithm` records this exact criterion. A similar-looking image, a recolor, a resized image, or a visually close crop is not a duplicate under this rule. Exact matches are copied into `dependencies/` and point back to their canonical `existingPath`; all other files remain labeled `new` and are not silently substituted with a near match.

The cropped reference evidence comes directly from `sources/exploration-concept.png` using the rectangles in `Docs/ExplorationComponents/spec.json`. Transparent complete props come from retained source atlases and standalone overrides under `sources/`; their source bounds and hashes are recorded in each manifest entry. The main exports trim each alpha silhouette to its visible bounds, then add eight pixels of transparent padding. Normalized 128-pixel variants are derived files and are not counted again as whole-object illustrations. Per-object alpha masks are also included. Faint generated alpha may be clipped at the reviewed source region, while the solid silhouettes are preserved. `manifest.json` records per-component source paths and bounds. The package hash index (`package-hashes.json`) records SHA-256 for package members.

## Rebuild an arrangement

`room-recipe.json` builds a furnished four-room study with a tiled clean floor patch, two partial wall dividers, and component placements with coordinates, maximum display sizes, and draw layers. It places a bedroom/home entry, training room, craft room, and forge room around a central party and HUD arrangement. The four room-study crops (`bedroom-room-study.png`, `training-room-study.png`, `craft-room-study.png`, and `forge-room-study.png`) isolate those areas; `source-vs-reassembled.png` compares the whole furnished arrangement with the reference. This is an approximate material and layout study. The divider strips do not reconstruct the full house architecture, and the arrangement does not match the source pixel for pixel.

From the extracted package directory, run `python3 replay.py` with Python 3 and Pillow installed. It reads the manifest and recipe, repeats the selected surface patch, places partial architecture overlays, orders props by layer, and writes `previews/reassembled-room.png`. The contact sheets and `previews/source-vs-reassembled.png` help inspect the outputs. Use nearest-neighbor scaling for pixel-art source fragments; inferred whole objects should be scaled only as the composition requires.

To regenerate the package from a source checkout, keep `Docs/ExplorationComponents/spec.json`, the reference image, the source atlases, and the existing asset tree in place, then run:

```sh
python3 Tools/build_exploration_components.py
```

The builder writes the manifest, crops, inferred pieces, previews, recipe, replay script, package hashes, and ZIP under `Web/wwwroot/assets/exploration-components/`. Re-run the independent package checks with:

```sh
python3 Tools/test_exploration_components.py
```

The final scan checked 16,382 canonical PNGs and found zero exact duplicates: all 126 records are marked `new`, with no `dependencies/` copies. It excludes only the generated inputs and outputs listed in `deduplication.excludedPathSubstrings`. Duplicate equality requires identical dimensions and decoded RGBA bytes; visual similarity alone never counts. The checked-out game repository contains the source and builder. After building, the complete download is `Web/wwwroot/assets/exploration-components/exploration-components.zip`; individual PNGs, JSON files, and previews sit beside it. Keep `manifest.json` with any selected files so their IDs and provenance remain available. The ZIP is self-contained and can be copied or hosted as a static download without requiring the original concept image at use time.

This is an art and composition aid only. It does not establish runtime integration, gameplay collision, Unity rendering, or pixel-perfect reconstruction of the flattened concept.
