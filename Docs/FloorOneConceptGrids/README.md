# Floor 1 concept grids

72 coordinate-overlay exports cover all 36 original Floor 1 concepts and all 36 top-down revisions. The clean source images remain unchanged in their existing packs. The coordinator visually approved the revised 14×14 sample before full export.

Each panel has fourteen columns A–N from left to right and fourteen rows 1–14 from top to bottom. Labels occupy added 32-pixel margins above and to the left of the art. Pale translucent one-pixel lines have a subtle dark three-pixel halo. Original native pixels are not resized; pixels outside grid strokes are unchanged. Division boundaries use `round(i * extent / 14)`, so cell widths or heights may differ by one pixel. Coordinates cover the full native panel extent, including existing narrow source gutters. A reference such as C4 means the third column and fourth row.

The grid is a visual discussion aid. It does not establish canonical room dimensions, shared world scale, square physical tiles, collision data, seamless edges or production-ready sprites. The original set retains its mixed camera views; the top-down set retains its documented stylized prop depth. No image generation was used for these overlays.

## Files

- `Web/wwwroot/assets/floor-one-concept-grids/floor-one-concept-grids.zip`: portable output images, previews, manifests and tooling.
- `panels/original/<id>.png` and `panels/top-down/<id>.png`: 72 native images plus outside margins.
- `previews/original-group-01.png` through `original-group-06.png`, and corresponding `top-down-group-*.png`: labeled groups of six.
- `previews/original-overview.png` and `previews/top-down-overview.png`: all 36 in each set.
- `previews/sample-review.png`: initial approved side-by-side style sample.
- `manifest.json`: clean input paths and SHA-256 hashes, output hashes, dimensions, exact grid boundaries, and source-set provenance.
- `package-manifest.json`: every ZIP member except itself, with byte counts and SHA-256 hashes.
- `sources/`: copies of the two source manifests and the pinned label font with its license. Clean input PNGs are retained in the two original concept packs rather than duplicated here.

Extract the ZIP and open an individual PNG or group preview. Source pixel reproduction additionally requires the clean `floor-one-concepts` and `floor-one-concepts-top-down` packs under the repository asset root. Run `python Tools/build_floor_one_concept_grids.py` and `python Tools/test_floor_one_concept_grids.py` from the repository. Tests verify geometry, native pixels outside lines, center-line blending, outside-label placement, complete coverage, preserved prior assets and archive closure. Visual style approval is human review, not a test claim about lore or camera correctness.
