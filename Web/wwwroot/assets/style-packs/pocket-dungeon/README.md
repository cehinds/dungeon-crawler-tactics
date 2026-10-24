# Pocket Dungeon — extracted concept components

84 individually labeled transparent PNGs, mechanically cropped at native pixel
resolution from 4 generated atlases. Each crop has 4px transparent padding.
Available original and additional concept-scene PNGs are included in concepts/;
manifest.conceptFiles lists the archive-relative paths.
The original source atlases remain in the repository's source/ directory; their
SHA-256 fingerprints, cell coordinates and absolute crop bounds are in manifest.json.
When the generated layout drifts from the requested grid, reviewed non-overlapping
source.region rectangles identify the actual extraction regions; source.cell still
identifies the intended logical slot. Source regions never invent or repaint art.
For tightly packed silhouettes, source.mask records reviewed source-coordinate
alphaIslandSeeds. Eight-connected source pixels with alpha >16 are selected by
flood fill; existing alpha 1–16 fringe within two pixels is also retained. Every
retained RGBA pixel is unchanged. Other pixels become transparent; no colors or
details are synthesized. Overlapping extraction rectangles are permitted only
with an explicit island mask and disjoint substantial-pixel ownership. An island
cut by its extraction rectangle is rejected.
No painting, recoloring or invented detail is performed by the extraction script.

The contact sheet labels sit outside the artwork. preview.png is an illustrative
component arrangement, not a playable room or an integrated game screenshot.
The seven full-canvas layers/*.png composite in manifest order to reproduce it.
Toggle these same layers in the gallery to inspect their contribution. Components
are scaled only in the previews; the individual PNGs preserve source pixels.

Anchors are measured in pixels from each PNG's top-left, including padding.
The default anchor is the original crop's bottom-center. logicalFootprint is
placement guidance, not a collision shape. These are concept components: animation,
directional views, tile seams and runtime collision require a production art pass.

Rebuild: python3 Tools/build_style_packs.py --style pocket-dungeon
Validate without writing: python3 Tools/build_style_packs.py --style pocket-dungeon --check
