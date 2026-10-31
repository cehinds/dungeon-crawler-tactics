# Map grid pass QA

Status: **final expanded asset package passes all nine independent tests**.

The completed starter build passed all seven initial independent tests. Its 24 semantic modules comprise five fully opaque floors, one fully opaque water surface, and 18 isolated pieces with transparent margins. The 24 comparison cells, 192 raw comparison crops, rotations, and layered scene plates are not counted as reusable designs. The expanded asset inventory is verified below; scene reconstruction acceptance remains unchecked.

Run the independent, read-only checks with:

```sh
python3 -m unittest Tools/test_map_grid_pack.py -v
```

The initial comparison build passes exact pixel checks for both 1536×1024 inputs. All 24 distinct 256×256 cells and all 96 distinct 128×128 subcells per input are covered exactly once, with 192 raw crops stitching back to the original inputs without pixel differences. Comparison labels and grid lines are restricted to review images.

The pre-work session snapshot `/tmp/map-grid-frozen-snapshot.json` records SHA256 for 24,981 existing files below `Web/wwwroot/assets`, excluding the new `map-grid-pass` directory. The initial verification confirms every frozen file remains byte-identical. This temporary baseline is evidence for this session, not a portable source of historical truth.

The test suite also checks source and component SHA256 values, exact authored extraction, anchor bounds, nonempty tags, opaque floor alpha, reference integrity in assembly recipes, placement bounds, pixel-identical assembly recomposition, OpenRaster layer reconstruction, and ZIP member completeness and byte equality. These checks validate packaging and pixels, not artistic fidelity. Visual inspection must independently assess isolation, cutoffs, contamination, and misleading provenance.

The clean plate and hidden-surface completions are generated interpretations. They cannot recover unseen original pixels or substantiate a claim of 1:1 reconstruction. Original visible crops and inferred generated surfaces must stay explicitly distinguished in the manifest.

Direct visual inspection covered the original reference, generated atlas, repaired environment plate, all 24 extracted starter modules composited on gray, and the starter assembly. No unintended characters, UI, text, or cut-off prop silhouettes remain in those inspected starter outputs. An earlier environment build retained actor contour fragments; it was rejected, repaired with expanded exclusion masks, and re-inspected. The final starter clean plate preserves three visible waterfall outlets and three horizontal floor grates; the tall left wall inset is a separate feature. All 18 isolated starter silhouettes have at least four pixels of canvas margin.

The reconstruction test verifies that fully opaque original-visible pixels match the original reference exactly, validates the source manifest and layer hashes, recomposes the delivered visible and inferred layers, checks an opaque final image, and verifies the before/after example crops. The generated hidden floor materials remain approximate; the source did not reveal them. No broad gameplay or Unity validation is claimed for this asset-only change.

The expansion was visually reviewed across all five contact sheets: floors, walls, water, industrial fixtures, and props. It adds 120 authored designs and 52 explicitly derived construction parts or embedded detail patches. Combined with the 24 starter designs, the inventory contains 196 PNG exports representing 144 authored designs. Embedded patches retain visible attachment material and are not presented as independently recovered hidden parts. A gauge detail crop was corrected during review to retain its full visible ring and neck. The expansion contains 30 fully opaque floor/water cores; transparent pieces preserve canvas margins.

The independent checks reconstruct declared expansion alpha and normalization transforms from exact native source crops and verify all 22 native assembly recipes. They also validate the 96-quadrant component coverage mapping and its 256 need references. Coverage distinguishes semantic motif availability from scene completion: 58 need instances have available motifs, 198 remain partial, and zero quadrants are accepted as a completed reference reconstruction. Reference-specific joins, integrated exit/controls/bridge assemblies, and runtime composition remain unresolved.

Final verification: `python3 -m unittest Tools/test_map_grid_pack.py -v` passed all nine tests in 13.091 seconds after the completed integration build. The 196 normalized component images have unique SHA256 digests and unique source-ID/crop pairs. Source crops, declared transforms, metadata, native assembly recipes, comparison coverage, original preservation, archive contents, and the frozen baseline all pass. The 52 derived parts are tracked separately from 144 authored designs. This is acceptance of the delivered asset package and its stated provenance, not acceptance of a 1:1 integrated reference scene.
