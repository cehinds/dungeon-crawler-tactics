# Concept layout references

These sheets are visual references for room composition and a top-down presentation. They are generated interpretations, not canonical plans. Floor 1 lore establishes named places and some functions; room dimensions, furniture positions, exact doors, and routes remain game-authored adaptations. See `ReferenceData/book-one-floor-one.json` for source IDs and status notes.

## Source images inspected

| Evidence ID | Image | Contents |
| --- | --- | --- |
| `topdown-E-25` | `Web/wwwroot/assets/floor-one-concepts-top-down/panels/scatterer-territory.png` (source sheet `sources/sheet-e.png`, panel E1) | Scatterer/refuse territory: square paved chamber, several dark floor openings, dense refuse/nest clusters around edges, comparatively open middle, scattered debris. |
| `topdown-F-32` | `Web/wwwroot/assets/floor-one-concepts-top-down/panels/other-descent-landings.png` (source sheet `sources/sheet-f.png`, panel F2) | Descent: long, narrow centered run of parallel stair bands framed by side walls and a larger landing/threshold. Useful as an entrance/stair visual vocabulary. |
| `topdown-F-33` | `Web/wwwroot/assets/floor-one-concepts-top-down/panels/alabama-waffle-house.png` (source sheet `sources/sheet-f.png`, panel F3) | Diner/service interior: long counter zone against one edge, repeated booth/table clusters in rows, clear aisles between clusters. Generic mentioned rest-stop interpretation, not a safe-room plan. |
| `topdown-F-35` | `Web/wwwroot/assets/floor-one-concepts-top-down/panels/other-crawler-guild.png` (source sheet `sources/sheet-f.png`, panel F5) | Tutorial classroom: central table and map, chairs distributed around it, large rug, plants/storage pushed to perimeter, broad approach at one side. |
| `topdown-F-36` | `Web/wwwroot/assets/floor-one-concepts-top-down/panels/generic-safe-room-bedroom-bathroom.png` (source sheet `sources/sheet-f.png`, panel F6) | Bedroom plus washroom: bed dominates one side, bedside surface, narrow partition, separate fixtures in tiled nook; connecting opening stays legible. Generic safe-room composition only. |

All F panels are in row-major order on the 1536 x 1024 source. The sheet and original briefs are indexed in `scratch/floor-one-art/c/provenance-topdown.json` and `scratch/floor-one-art/c/provenance.json` (IDs 25–36). The images were visually inspected; descriptions above report visible groupings, not measured grid dimensions.

The whole-object atlas was also inspected: `/workspace/generated_images/exec-8669bf6a-fb95-4304-8f76-2651716cf20c.png`, source `ef-whole-v2` in `scratch/topdown-object-pass/ef/objects.json`. Its 12 isolated silhouettes include toilet, sink-counter, litter tray/scoop, vending machine, bench, table, chair, bed, rug, plant and side table. These are reconstructed concept props. They help define readable footprints and clusters, but do not establish that a given canonical location contains those exact objects.

## Layout cues and careful adaptations

```text
descent: [landing] -> [parallel stair run]       (F32)
guild:   [perimeter storage] [chairs around table/map] [clear approach] (F35)
refuse:  [edge nests + debris] [open combat/readable center] (E25)
service: [counter] | aisle | [repeated tables/booths]   (F33)
safe:    [bed zone] | [partition/opening] | [wash fixtures] (F36)
```

The overhead sheets use a consistent square stone floor grid, narrow wall-top outlines, warm pools of light, and strong room-specific focal clusters. Room identity reads through floor material and prop arrangement; clear floor lanes keep each purpose legible. The fixture data expresses three spatial grammars as authored groups: stairs with paired torches; a rug-underlaid table with chairs around it; and opposed sleeping and washroom zones. Their anchors, offsets, dimensions, and prop identities are implementation choices. The observed ideas are the stair run, grouped classroom furniture, and separated bed/wash zones; the sheets do not establish exact positions or measurements.

| Game adaptation | Reference cue | What is inferred |
| --- | --- | --- |
| Entry / stair approach | F32 | Broad landing feeding a narrower descent, with parallel tread rhythm. The actual opening, orientation and landing size are adaptable. `entry-landing` is canonical as a place (`sample1`), but this image depicts a generic descent landing. |
| Tutorial guild | F35 | Central teaching surface, seats gathered around it, rug anchoring the group, edges kept quieter. F35 is an unvisited generic guild concept; Mordecai’s actual personal room and its exact classroom plan are not pictured. |
| Refuse / nest territory | E25 | Burrows and refuse gather in irregular edge clusters; a more open center gives combat and traversal space. This is a territory visual, not a measured Hoarder lair blueprint. Lore IDs `hoarder` and `route` establish the lair / Scatterer area, not these exact holes or piles. |
| Service / diner | F33 | Counter separated from seating, repeated booths and tables, readable aisle gaps. This is the generic Waffle House concept (`chapter22` mention), not the canonical safe restaurant footprint. |
| Safe-room bedroom / washroom | F36 | Separate rest and wash zones with a low visual partition and a clear passage between them. The concept is explicitly generic; match services and safety behavior from lore, not its furniture inventory. |
| Workshop / boss chamber | Industrial combat illustration, documented in `REFERENCE-ARENA.md`; no matching overhead panel in E/F | Version 4 gives both rooms a shared industrial-sewer grammar with slate floor, water channels, machinery and grates. Each encounter uses its generated 18 × 11 room as the battle board. Workshop/boss functions have lore support (`goblins`, `chapter15`), while machinery, dimensions and arrangement are authored. |

## Visual-match checklist

- Keep the camera orthographic and overhead; show furniture by its top silhouette.
- Use a regular square floor rhythm and narrow wall tops, with the slate/blue stone and warm amber light palette as a shared baseline.
- Preserve the concept's large-scale organization: clustered perimeter debris, central teaching grouping, repeated dining bays, or distinct bedroom/wash zones.
- Keep at least one legible route through the room and a distinct focal cluster. Small props should support the grouping rather than erase the floor plan.
- Use the object kit as a source for recognizable silhouettes and approximate footprints. It is a reconstructed kit, not exact canonical source art or proof of location inventory.
- Treat dimensions, coordinates, door locations, connectivity, hazards, and specific furniture placement as authored gameplay choices. Avoid presenting them as book-established measurements.

## Current generation and verification

`concept-room-rules.json` is the authored grammar for new version 4 worlds. The 90 × 52 world uses 22 × 16 room sectors. The workshop and Ball of Swine rooms share industrial composition rules with an authored `tileRows` footprint, a reserved 12 × 6 central area, asymmetric three-column water wings and three-cell-long dry crossings; seeded variants retain clear approaches, solid prop collision and impassable water. Their tactical boards copy the generated room tiles and props, with coordinates translated into the room. Other encounters retain 10 × 8 boards. The inset platform, side-channel floor crossings and right-of-center northern gold gate are authored adaptations of the supplied illustration. The gate corridor aligns with the gate; water remains impassable outside the explicit dry crossings. Bridge, wall-cap and doorway overlays present this geometry without changing collision.

Version 1, version 2 and version 3 layouts remain compatibility checkpoints for save validation and migration, not current layout targets; their historical 60 × 38 dimensions remain unchanged. `Tools/playtest_reference_arena.py` captures published WebAssembly state for seeds 1337 and 42, verifies collision and workshop combat input, and writes a reference/runtime comparison under `Rebuild/ReferenceArenaComparison/`. The script discloses its camera-only room framing override. These captures support visual review without establishing pixel parity or canonical room geometry.

`Tools/playtest_layered_maps.py` runs the arena harness and adds keyboard traversal through a doorway and a dry water crossing for seeds 1337 and 42, with closeups under `Rebuild/LayeredMapComparison/`. Its camera-only override and reused-arena iteration option are disclosed in the report. Side-by-side screenshot review remains necessary to assess the reference match; passing connectivity or combat checks does not establish visual parity.

The industrial northern apron is blocked masonry around the explicit gate opening, with the eastern water inset retained. Mounted machinery, pipes and gate torches use the `wallfixture` layer; their footprints remain wall cells in both exploration and combat. The renderer preserves that masonry beneath the art instead of presenting mounted fixtures as furniture standing on floor.
