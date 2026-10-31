# Combat concept reconstruction kit

This folder documents a semantic inventory and reproducible reconstruction for the flattened concept at `Web/wwwroot/assets/broadcast-kit/combat-concept.png` (1536 × 1024 RGB). Restore the source image according to [ArtStorage](../ArtStorage.md) if it is not present in the checkout. Start with [inventory.json](inventory.json) for the feature list and pixel coordinates, then use [structure-review.md](structure-review.md) for the composition and art construction rules. [brick-landmarks.json](brick-landmarks.json) contains the manually traced 19-zone wall map. `scene-regions.json` and `ui-regions.json` are the source-coordinate annotations. Their shapes identify visible source fragments; they do not contain hidden surfaces.

## Rebuild the visible-fragment package

From the repository root, the routine export workflow reuses the checked-in region JSON and masks:

```sh
python3 Tools/rebuild_combat_concept.py
python3 Tools/generate_concept_scene.py --seed 7 29 103
python3 Tools/test_concept_reconstruction.py
```

For this workflow, install Python with Pillow, NumPy and SciPy available. To edit a region, change the corresponding entry in `scene-regions.json` or `ui-regions.json`; for a mask shape, update its referenced PNG too. Then run the rebuild and downstream commands above. The rebuild command applies the declared mask priorities to assign each visible source pixel to one annotated component, then writes component PNGs, `manifest.json`, `reconstructed.png`, `diff.png`, a coverage map, per-category atlases, `combat-concept.ora` and a portable `combat-concept-components.zip` beneath `Web/wwwroot/assets/concept-reconstruction/`. The procedural command uses that manifest to write seeded room studies. The final command independently checks layer identity, bounds, mask counts, source hash, pixel ownership, reconstructed PNG, a fresh recomposition of the OpenRaster layers, and procedural connectivity.

The mask authoring scripts are a separate source-derived regeneration workflow. `Tools/concept_scene_masks.py` reads the 19-zone hand-traced seam map in `brick-landmarks.json`, rebuilds scene masks and overwrites `scene-regions.json`; it uses SciPy. `Tools/concept_ui_masks.py` recreates the UI masks and overwrites `ui-regions.json`. Run these only when you intend to regenerate the authored annotations from those mappings. They overwrite manual edits to their output JSON files; after regeneration, run the rebuild, procedural generator and verifier in the command block above.

The frozen annotation set contains 1,452 regions: 1,346 scene regions and 106 UI regions. The wall map defines 676 mortar-bounded brick cells across 19 zones; 659 cells have nonempty visible masks, alongside 380 supplemental source-texture fragments. The export has 1,317 visible component PNGs and 135 fully occluded annotations, with zero unassigned and zero changed pixels. Independent raster, ORA, ZIP and procedural checks pass. The targeted visual review accepts the bounded source-visible fragments and records corrected contamination findings in [QA.md](QA.md); it does not certify every ambiguous pixel as an original object matte or recover hidden art. Raster equality proves that the visible source was partitioned and replayed; it does not prove that each alpha edge belongs to the correct semantic object.

Frozen artifact hashes: `manifest.json` `0606b90e6466a7e51216bba0807b36d31e764cdafe4e6dd76bd85558ef072e25`; `combat-concept-components.zip` `d88eba7f087b3e431f0ccd076a5f75b5c311f258b3feefb4d3d05da3f79b2fba`; `combat-concept.ora` `3a01facb60684bbf01aece076827422ad43b3b2bcb6bc5cea0807a13d6ef4595`.

## Generate related room studies

After the fragment package has been built, run:

```sh
python3 Tools/generate_concept_scene.py --seed 7 29 103
```

This writes three reproducible room PNGs and placement JSON files under `Web/wwwroot/assets/concept-reconstruction/procedural/`. Each study uses a 12 × 8 grid of 72-pixel cells, alternates two source-visible floor samples, selects a one- or two-cell contiguous water channel along one side, and accepts wall placements only when breadth-first search keeps all dry cells and the entrance connected to the exit. Actors are placed on distinct reachable cells with minimum spacing. It retains selected source exit structures and fixed source HUD components to show one related scene grammar. The seed controls layout choices; inspect the generated JSON for the actual cells, placements and reachability counts.

The room studies are newly composed illustrations with normalized visible samples. They are not recovered rooms or the original game's rendering algorithm. Fixed source HUD text remains a raster image; the recipe does not generate arbitrary editable labels or stats. The BFS checks report all dry cells connected and an open entrance-to-exit path for seeds 7, 29 and 103; water cells remain nonwalkable.

## Reading the layers and masks

The [OpenRaster file](../../Web/wwwroot/assets/concept-reconstruction/combat-concept.ora) holds separate PNG layers with their original visible RGB and binary ownership masks. The [portable ZIP](../../Web/wwwroot/assets/concept-reconstruction/combat-concept-components.zip) holds the manifest, visible component PNGs, source provenance and recipe. The [browser inspector](../../Web/wwwroot/concept-reconstruction.html) can filter and solo those annotations, show the assembled image or difference view, and download the manifest and individual fragments. These are derived outputs; the original concept source is not included as a hidden layer in the ZIP. Layer names, shapes and text transcriptions are documentation authored for this reconstruction; they are not original source layer names.

Text transcription is editable in the JSON inventory, while the source lettering itself remains a collection of raster glyph masks with antialiased pixels blended against its original background. The flattened source cannot reveal pixels beneath a character, pipe, banner, water effect, foreground prop or HUD. Clean plates and hidden object faces are therefore unavailable. Masonry partitions follow visible source texture and seams; they can split a stone's texture and approximate dim joints, so they should not be treated as original brick assets. Color-assisted actor edge fragments similarly preserve visible colored fringes only and cannot restore occluded anatomy.
