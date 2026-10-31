# Combat concept reconstruction QA — pass 2

**Exact raster replay: PASS. Targeted semantic ownership: PASS. Reusable illustrative modules: PASS within the limits below. Browser and generator checks: PASS for the exercised cases.** These are separate findings; exact replay does not certify semantic ownership or recover hidden art. The previous semantic PASS missed feet, paws, tails and architecture; this record supersedes it.

## Independent automated evidence

`python3 Tools/test_concept_reconstruction.py` passed the final **1,463 annotations / 1,317 visible components**: every one of 1,572,864 source pixels is owned once, with zero gaps, overlaps or XOR changes. Source/component/annotation/mask digests, tight binary-alpha fragments, ORA replay and exact semantic parent chains, ZIP contents, mandatory products and room PNG/JSON pairs passed. Current required seeds 7, 9, 29 and 103 contain nine entities each.

`python3 Tools/test_concept_room_contract.py --count 10000` passed **10,007 seeds twice**, including 0–9,999, signed/unsigned 32-bit boundaries and ±9,007,199,254,740,991. Streamed JSON digests matched. Checks independently cover grid vocabulary/shape, exact seven actors/two props, identities/stats, reachability, spacing, all declared terrain sockets and permitted transitions, bank position/orientation, tile cardinality, shared actor/prop depth order, portal anchors and actual drawing below y=747. Native cap/corner dimensions, cropped boundary geometry and required wall underlays are checked. Published plans match shared generation. Eight geometry fixtures reject omissions, wrong banks, bad sockets, invalid cells and drawing defects. Eight additional fixed-HUD fixtures reject matching entity/state HP changes, round, selected/target identity, mana, forecast damage, and identity-to-art remapping that would disagree with the catalog’s fixed raster HUD. A synthetic overlap fixture projects actual engine actor/prop records onto the same footprint and checks the deeper foot wins.

`python3 Tools/test_concept_input_contract.py` passed both authored schemas and ten rejection fixtures: negative/outside crops, malformed recipe entities/board/state, missing parent, parent cycle, absent mask, wrong mask dimensions and nonbinary mask. `python3 Tools/test_concept_asset_assemblies.py` independently recomposed the exit’s eleven source constituents, including its direction arrow, plus its explicitly documented one-pixel source joint strip: RGBA matched the complete portal asset exactly, and its central 99 × 162 interior is fully opaque with no holes.

Inventory check mode passed; repeated synchronization was identical and a deliberately corrupted in-memory semantic inventory was detected as drift.

A separate `/tmp/qa-copied-input-iu5mw9nu` build used copied source, annotations and masks with explicit paths and a working directory outside the repository. It produced 1,463 annotations and a byte-identical reconstruction. The integration owner’s final `reproducibility-report.json` records two full output roots with all 18 aggregate hashes and 1,423 shared asset files identical. Independent generator-ZIP unpacking outside the repository ran seeds 9 and 314159 twice; PNG/JSON bytes matched and both rooms contained nine entities, with no source image required.

## Independent visual evidence

The corrected seven-actor montage was inspected against grey, magenta, black, original-source and ownership overlays (`/tmp/actor-final-source-review-v2.png`). Fresh derived lineup inspection confirms Katia’s boots, Mongo’s visible foot, Donut’s paws, and all three rats’ pink feet/tails. The earlier stale Donut paw and target-rat magenta wedge were caught and corrected. Small detached Mongo edge/shadow pixels remain a disclosed source-matte ambiguity.

The final canonical nonactor montage `/tmp/qa-final-nonactors.png` was inspected on magenta: reported actor pixels are removed from floor slabs r03-c07, r02-c04, r04-c09, r06-c06 and r06-c07, and from Donut/target ground effects. Floor r00-c00 and r08-c06 are now fully occluded; the neighboring south stepped wall/cap contours were reassigned after the independent reviewer caught the r08-c07 cap. Southwest/southeast perimeter neighbors were rechecked after the expanded repair.

Derived floor, water, wall and effect previews were opened. Floor modules are opaque, distinct source-style textures with thin mortar; effects stay clean over two floor variants. Final native-size room 7 was inspected: caps retain their thin proportions over full wall underlays, corners have supporting wall geometry, water is banked, both portal arrows are complete, all nine entities are visible and the board stops above the party strip. Repeated source texture motifs remain visible; these are illustrative modules, not a seamless fluid simulation or original recovered game assets.

## Independent browser evidence

Real system Chromium served the final static files on port 8793 **without recipe interception**. Initial loading used seven requests; observed cold-page readiness was 210–228 ms on this local test environment, without imposing an arbitrary timing budget. Overlapping seeds 9 then 46 displayed and downloaded seed 46; the full normalized exported JSON matched Node generation. Independently exported browser seed-46 canvas pixels matched Pillow CLI output exactly: zero changed RGB pixels. At 390 × 844 there was no horizontal overflow or JavaScript error. Blocking Katia’s body image produced a visible item error and Retry control; restoring it and retrying recovered the preview. Recursive assembly and solo included both Katia fragments.

The inspector passed collapsed initial groups, exact 100% crop sizing (119 × 127 CSS and source pixels), 400% keyboard/pointer panning, selected-state preservation through filtering, search focus, accurate zero-match reporting, and zero all-visible difference pixels. Downloaded assembly PNG bounds were 119 × 127 with RGBA alpha spanning 0–255. Scripts: `/tmp/qa-independent-browser-static.cjs`, `/tmp/qa-fault-browser.cjs`, `/tmp/qa-inspector-details.cjs`. At 390 × 844, all 28 hierarchy summaries measured at least 44 px high after correction; keyboard Tab reached summaries with a computed 2 px solid focus outline. Real touch tap/search and touch-drag preview panning passed. Authored normal/status/link/control/pressed/focus color pairs measured 7.39–16.17:1 contrast. Visible labels, associated labels and pressed-state semantics were checked. These supported-browser checks do not claim a complete assistive-technology audit.

## Scope and provenance limits

Source-visible assemblies do not restore occluded anatomy. Source edge/shadow ownership can remain ambiguous. Newly authored architecture, water, portal states and tactical modules have catalog provenance and are distinct from exact source fragments. HUD lettering and displayed source stats remain fixed raster art; arbitrary typography/stat rendering is outside this kit. No publication or commit was performed by this QA task. The item-by-item record is [PASS-2-CHECKLIST.md](PASS-2-CHECKLIST.md).

## Tested artifact hashes

| Artifact | SHA-256 |
| --- | --- |
| `manifest.json` | `0f101ff69a5e736076f4c2cb12f3d911f410dc3878a707bc55cfbe0fc66199ce` |
| `combat-concept-components.zip` | `e526886eb6f702134fc77991ecfd436364c36b3d5f137e41e6006558248d6867` |
| `combat-concept.ora` | `9eaf81fc492fa6c27cf4a1fdff575e38ed2ec14aacff39ad3b7f2c1183545769` |
| `concept-generator.zip` | `c215106783a9064bb1f5044de37599616b11402ccf74dc54631cc7a795633ec7` |
| `reconstructed.png` | `2e25e0f9703d69b2b786873f124d1571468e02b858bdbaf457a66a965065fc6d` |
