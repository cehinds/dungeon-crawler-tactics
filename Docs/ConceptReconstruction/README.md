# Combat concept reconstruction kit

This kit rebuilds a 1536 × 1024 flattened combat concept into two related products: an exact, semantic partition of its visible source pixels and an illustrative room generator built from reusable art. Neither product recovers original editable layers or pixels hidden behind other objects. The independently checked results and the boundaries of that review are in [QA.md](QA.md); the item-by-item acceptance record is in [PASS-2-CHECKLIST.md](PASS-2-CHECKLIST.md).

The reference is `Web/wwwroot/assets/broadcast-kit/combat-concept.png`. If it is absent, restore it according to [ArtStorage](../ArtStorage.md). Authored inputs are `scene-regions.json`, `ui-regions.json`, the referenced binary masks, `actor-silhouettes.json`, `source-architecture.json`, [procedural-recipe.json](procedural-recipe.json), and [reusable-asset-spec.json](reusable-asset-spec.json). `inventory.json` is generated from the rebuilt manifest by the inventory sync step; use `Tools/sync_concept_inventory.py` rather than editing generated inventory entries by hand.

## Build and verify

From the repository root, install Python 3.10 or newer with Pillow, NumPy, SciPy and jsonschema, plus Node.js 18 or newer. Run the single build command:

```sh
python3 Tools/build_concept_reconstruction.py
```

The build consumes the checked-in authored masks and annotations as-is. It does not run the mask authoring scripts. It rebuilds the exact source-visible fragment export, creates the reusable illustrated asset catalog and contact sheet, generates the required room studies, synchronizes the inventory, packages the standalone room generator, and runs the independent artifact verifier. Outputs go under `Web/wwwroot/assets/concept-reconstruction/`: the component ZIP, OpenRaster file, manifest, pixel replay and difference images, `derived/` reusable assets, `procedural/` room PNG/JSON pairs, `concept-generator.zip`, and `build-report.json`.

To write a separate build without changing the default output tree, pass `--out /path/to/output`. Inputs can be supplied with `--source`, `--mask-root`, `--regions`, `--recipe`, and `--spec`; the report records hashes for required products. Reproducibility across explicit output roots is checked by the integration workflow and its `reproducibility-report.json`, which compares the complete output hashes and shared asset bytes.

The focused checks can also be run separately:

```sh
python3 Tools/test_concept_input_contract.py
python3 Tools/test_concept_asset_assemblies.py
python3 Tools/test_concept_room_contract.py --count 10000
python3 Tools/test_concept_reconstruction.py
```

These cover authored schema and mask rejection, recursive asset assembly, seeded geometry/edge/state invariants, and exact source replay, ORA hierarchy, ZIP contents and required output pairs. Keep authored region and mask changes deliberate: `Tools/concept_scene_masks.py` regenerates `scene-regions.json` from the 19-zone landmarks, and `Tools/concept_ui_masks.py` regenerates the UI annotations. Both overwrite their corresponding region files; run them only when intentionally changing those annotations, then rebuild and review the new outputs.

## Inspect and generate in the browser

Serve the repository’s static web root from the repository root:

```sh
python3 -m http.server 8000 --directory Web/wwwroot
```

Open `http://localhost:8000/concept-reconstruction.html`. The inspector separates literal source fragments from recursive assemblies, supports search, solo, crop, zoom and pan, and downloads selected PNGs. Its room panel runs the shared JavaScript engine in the browser for arbitrary safe-integer seeds, validates placements, and downloads the displayed room PNG and matching JSON recipe. The browser loads the recipe and catalog on demand; initial page loading does not fetch every component image.

The fragment manifest contains 1,463 annotations, including 1,317 visible source-fragment components for semantic inspection. The separate reusable catalog contains 89 assembled or authored reusable modules, including actors, floor and wall modules, portals, water and effects. Those 89 assets are the room-generator kit; they are not the same deliverable as the 1,317 literal fragments. The standalone [concept-generator.zip](../../Web/wwwroot/assets/concept-reconstruction/concept-generator.zip) includes the catalog, recipe, schemas, shared engine and renderer, so it can generate rooms outside this repository without the original source image or network access. Its README includes the unpacked usage command.

The HUD lettering and displayed statistics are fixed raster artwork. The recipe binds its supported fixed HUD state to the declared actor, target and values; the validator rejects combinations that would contradict that raster. Arbitrary editable labels, live stats, or a reconstructed game renderer are outside this kit.

## Provenance and source limits

The component package preserves the source’s visible pixels exactly and assigns each pixel to one annotated fragment. Exact raster replay demonstrates pixel accounting; it does not establish that every antialiased boundary is the original object matte. The reusable modules use explicit catalog provenance: some assemble visible source fragments, while others are newly authored illustrations. They support related room compositions, not recovery of original production assets or a seamless fluid simulation.

Flattening removed all hidden surface evidence. A character behind an effect, a floor beneath an actor, and a wall behind a pipe cannot be extracted from the image. Source-visible anatomy that is present has been assigned and reviewed, but fully occluded anatomy remains absent. Small source edge and shadow pixels can remain ambiguous. Repeated textures and fixed raster HUD text are disclosed in the catalog and QA record.

Build outputs and immutable catalog/proof artifacts carry generated attachment metadata and verified build receipts. Preserve those receipts with the outputs; do not manually retag the immutable catalog or proof files. When updating the kit, use the documented build and verify its recorded hashes rather than rewriting generated metadata by hand.
