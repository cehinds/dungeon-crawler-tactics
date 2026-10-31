# Map grid audit and reconstruction guide

This pass compares the concept reference with the current room render in fixed screen coordinates, records missing map pieces, and prepares a provenance-aware reconstruction pack. It is an art and room-assembly study. It does not change gameplay or imply that the current procedural room generator uses the new components or layout.

The working comparison and still-open visual criteria are in [AUDIT.md](AUDIT.md) and [comparison.json](comparison.json). The first comparison records mismatches; it does not claim they are fixed. Pack integrity and pixel checks are tracked separately in [QA.md](QA.md).

## Compare the map by grid and subgrid

Both comparison images use the original 1536 × 1024 canvas without crop, rescale, alignment, or camera correction. Coordinates start at the upper-left; rectangles use `[x, y, width, height]` with the right and bottom edge excluded. The six columns are A–F, each 256 px wide; rows 1–4 are 256 px high. Each cell is split into four 128 px quadrants in NW, NE, SW, SE order. For example, C3 is `[512, 512, 256, 256]`; its southeast quadrant is `[640, 640, 128, 128]`.

Use the grid as a repeatable visual index, not as a claim that the art follows tile boundaries. Start with the side-by-side cell image and comparison contact sheet for broad composition. Then open the four subcell crops when locating a pipe joint, wall seam, waterfall edge, actor placement, or HUD overlap. Grid overlays and labels are for review images only; source crops remain unmarked. Compare each region at the same native scale, and inspect joins across adjacent cells after local fixes so walls, water, floor courses, bridges, and lighting continue across boundaries.

The audit describes what is visible in the reference, what differs in the current implementation, the components needed, severity, and any surface hidden by an occluder. All audit acceptance boxes remain unchecked until the composition is rebuilt and reviewed. Highest-priority work is the asymmetric room outline and foreground apron; large irregular masonry and capstones; bent canal, bridge and basin; waterfalls and outlet arches; north pipe/control bank; exit and torches; correct actor positions; grates, damp areas and gold reflections; tactical overlays; and masonry visible around the HUD.

To regenerate the unmarked source comparisons and current component/environment package from authored data, run:

```sh
python3 Tools/build_map_grid_pack.py
```

The script writes under `Web/wwwroot/assets/map-grid-pass/`. `comparison/` contains the overview, full-canvas cell grids, 24 reference/implementation cell sheets, and 192 raw subcell crops (96 from each comparison image). These crops are comparisons, not 192 map tiles or reusable pieces. The starter spec has 24 base modules. The expanded catalog adds 120 full authored designs across five families (24 each: floors, walls, industrial fixtures, water, and props), for 144 authored designs total. Expansion includes another 52 derived exports, for 196 exported PNGs across the combined pack. The expanded manifest records each item's provenance and derivation class.

Expansion source atlases and contact sheets are under `expansion/sources/` and `expansion/contact-sheets/`; native source-scale extracted pieces are under `expansion/native/{family}/`, with normalized 128 × 128 study views under `expansion/components/{family}/`. The original 24 starter modules remain under `components/generated/`. `assemblies/modular-environment-study.png` and its OpenRaster counterpart show only a small placement example, not a full corrected reference-map render. `map-grid-pass.zip` packages the generated outputs and authored inputs. Grid lines and labels exist only in review sheets; raw source crops preserve their source pixels.

## Component families to assemble

The audit's component index is a needs list, not proof that each entry already exists as reusable art. Group related pieces into the following assembly families when authoring or reviewing the pack:

- **Room shell:** large wall blocks, raised faces, jambs, piers, capstones, stepped foreground walls, outer walls, and floor apron/edge pieces.
- **Water and crossings:** bent canal, channel edges, pool/basin water, bank walls, outlet arches, waterfall streams, splash/foam rings, bridge deck, and bronze bridge supports.
- **Pipe and machinery:** vertical tubes, elbows, collars, feet, bases, recessed panels, control cabinets, lamps, and local shadows.
- **Surface detail and fixtures:** vines, moss, wet patches, gold floor reflections, wall inset and floor grates, crates, explosive barrel, torches, and exit hazard trim.
- **Screen composition:** exit frame/lintel/stairs/arrow grate, objective and phase banners, actors and health bars, selection/path/target effects, speech bubble, portraits, and fixed HUD pieces.

The 120 expanded designs are authored full pieces in five named families. The other 52 exports have two different roles: 42 visible construction parts expose a course, shaft, chamber, deck, or similar piece that can be reassembled with its parent; 10 embedded-detail patches preserve a fixture detail that remains attached to surrounding material. They are not 52 additional clean, freestanding layers. The 22 native assembly recipes include residual parent art plus extracted children so the original generated parent image can be recomposed exactly. Inspect each recipe and its `reassembled`/`residual` previews before treating a derived piece as independently placeable. Module IDs, family links, parent links, source rectangles, anchors, layer hints, edge tags, alpha handling, and provenance are in `Docs/MapGridPass/expansion-spec.json` and `expansion/manifest.json`.

Prefer transparent reusable parts with explicit IDs, native size, anchor, tags, source bounds, and provenance. A component subpart may be independently placed only if its spec defines its relation to the parent and includes any residual material needed for faithful recomposition. Keep assembled objects in ordered layers so back walls and water sit behind floor edges, fixtures sort at the wall or floor they attach to, and foreground masonry overlaps the lower scene correctly. Reuse source-visible fragments as cutouts where they are cleanly separable; do not stretch a cutout to fill unseen structure.

`layer` is an ordering hint, not a finished runtime renderer contract. In the starter catalog, floor/water bases use 0, structural and ground overlays use 10, and wall-mounted fixtures or hanging foliage use 20. In expansion, bases use 0, structural and fixture pieces use 3, and light/shadow overlays use 5. The small example assembly has explicit ordered placements. Future actor, foreground prop, or depth-sorted environment integration needs a common contact-depth rule and its own assembly QA.

## Reconstruct occluded environment carefully

The original is a flattened image. Actor masks, pipes, vines, frames, water, and HUD can hide the underlying floor or wall. The hidden pixels cannot be recovered from this evidence. Use neighboring visible geometry, repeated material, and the room's structural logic to create a plausible continuous underlayer, and mark those pixels as inferred. Do not present the inferred surface as an exact original extraction.

The clean environment plate is a generated interpretation of the reference layout. It serves as a substrate for studies and for replacing environment portions excluded or repaired around dynamic silhouettes. The source-visible environment layer preserves only source pixels that are still visible and pass the mask boundary policy. The inferred-region mask identifies where the generated plate supplies pixels; the boundary-repair mask shows conservative margin repairs around actor bounds. Inspect those masks alongside the clean plate and its OpenRaster file. The whole plate is not a reusable component and must not be counted as one.

The current outputs include a 1536 × 1024 `reconstruction/clean-environment.png` and editable `.ora`, `original-visible-environment.png`, `inferred-environment-patches.png`, `inferred-region-mask.png`, `dynamic-exclusion-mask.png`, and `boundary-repair-mask.png`, plus `environment-recipe.json` and four before/after crops. The recipe records 1,178 original visible environment-layer references, their file hashes and placements, the source-manifest hash, category-inclusion policy, three-pixel dynamic-mask dilation, and actor-body bounding-box repairs with a three-pixel margin. Actor, HUD, tactical-overlay, and movable-prop areas are excluded from source environment fragments and supplied by the generated interpretation as needed. The masks document the assembly choice; they do not prove perfect separation of every antialiased object edge.

The generated atlas is not a source of original map pixels. Likewise, the full environment plate is not one of the 144 authored module designs. It supplies a plausible room-layout substrate and interpolates material beneath excluded dynamic objects using generated art. The visible-source assembly contains 1,178 references to existing source fragments; those references are not 1,178 newly authored assets. The inferred-region and exclusion masks show where generated pixels are used. The generated output must keep those areas marked inferred; it cannot establish the unseen original geometry or texture.

Reusable components are separate transparent pieces or assemblies cut from actual visible source fragments, with masks and manifest records. They are intended for placement and composition. The plate is a full-scene background; component pieces are movable building blocks. Keep these products distinct in the spec, export, and any future runtime integration. The pack may preserve alpha coverage and exact pixels where the source extraction says it does, but it does not promise seamless pixel-boundary joins or universal edge matching between modules.

## Repeatable reconstruction workflow

1. Review the matching cell and quadrant criteria in `comparison.json`; confirm the reference feature and the current mismatch at identical scale.
2. Decide whether the feature is a reusable component, a fixed screen element, a base material, or an inferred hidden continuation. Give it a stable ID and record source bounds, layer role, anchor, connection tags, mask, and provenance in the component spec.
3. Extract only the visible source portion. Where a complete illustrated piece requires hidden continuation, create the missing pixels as explicitly inferred art and record the generation/input provenance. Do not silently merge inferred pixels into a source-visible mask.
4. Place components in an assembly recipe using screen coordinates or documented grid cells, then render the complete 1536 × 1024 composition. Check native scale, actor/prop silhouettes, architectural joins, water boundaries, foreground overlap, HUD exclusion, and visible negative space.
5. Inspect the per-cell and per-quadrant comparisons, then inspect seams across neighboring cells. Update an acceptance checkbox only after both the local criterion and its boundary continuity are visually reviewed; keep inferred surfaces labeled.
6. Run the pack checks for exact source crops, alpha masks, assembly recomposition, OpenRaster layers, ZIP membership, and preservation of unrelated assets:

   ```sh
   python3 -m unittest Tools/test_map_grid_pack.py -v
   ```

   These establish data and pixel consistency, not artistic fidelity. `component-coverage.json` maps semantic needs across all 96 quadrants. It reports 256 need instances: 58 available and 198 partial; zero quadrants are visually accepted. “Available” means a matching component or source fragment is indexed, not that the full composition is fixed. Six remaining gap groups include wall/bank joins and cap ends, north control-bank connections, exit assembly, integrated bridge crossing, source-specific water joins, and scene layout/grounding/lighting/runtime integration. Keep every visual acceptance flag open until the room actually uses the parts and is reviewed. `QA.md` currently reports the starter package passed and final expanded-package verification in progress; see it for exact scope and limits.

## Runtime status and limits

This pack documents a reference-guided component library and layout study. The existing room generator has not been integrated with the expanded library or coverage layout, so the audit's scene mismatches remain open. The complete pack is retained as an unused research artifact and is excluded from Pages publication. Passing pack checks does not mean the audit's map criteria are accepted, nor that every source-visible mask is a perfect semantic matte. It does not recover hidden original surfaces, establish game traversal, or promise seamless pixel boundaries between neighboring generated modules. Directional tags describe semantic neighbor intent; they are not pixel-perfect edge guarantees or collision rules.
