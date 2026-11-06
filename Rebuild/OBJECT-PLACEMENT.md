# Object placement catalog

`Web/wwwroot/data/map-object-rules.json` is the authored vocabulary for map props, terrain, and world-object kinds. It describes object identity, typical subproperties, connector ports, placement surfaces, and expected relationships for scene-graph consumers. It does not calculate runtime collision or footprint: `properties.footprintSource` and `placement.footprintSource` are `runtime`, and the map's prop records remain authoritative for each placed width, height, layer, rotation, and movement-blocking value.

The catalog currently covers all 27 unique prop asset IDs found across `Web/wwwroot/data/concept-room-rules.json` and `Rebuild/DepthPassComparison/baseline/world.json`. Each asset ID maps to one `objectTypes` entry. Terrain glyphs in the baseline use `.` for walkable floor, `#` for blocked masonry, and `~` for channel water. The catalog also names the eight world-object kinds authored by `world-rooms.json`: guide, safe, encounter, boss, exit, chest, door, and discovery.

## Logical tree

- **Map composition**
  - **Terrain** (`terrainTypes`)
    - **Walkable floor**: supports movement and floor props.
    - **Blocked masonry**: receives wallfixtures when the authored layer and room composition put them there; exposed edges can receive caps, faces, or hanging moss.
    - **Channel water**: water surface bounded by floor or masonry; bridge decks can span it and land on floor.
    - **Surface overlays**: floor materials, water/bank pieces, bridge deck, wall face/cap, doorway frame, moss, and light/reflection effects decorate terrain.
  - **Rooms**
    - **Declared assemblies** (`assemblyTypes`), keyed by exact runtime `roomId` and `groupId`; each assembly contains its matching member props.
    - **Unassigned props** remain direct room children.
  - **Placed props** (`objectTypes`, semantic catalog of the member props below)
    - **Architecture**: stair module, wall segment, industrial exit.
    - **Industrial fixtures**: machine, pipe, outlet, grate, industrial torch.
    - **Furniture and service fixtures**: table, chair, bench, bed, bedside lamp, sink counter, toilet, vending machine, rug.
    - **Storage and decoration**: crates, barrel, shelf, plant.
    - **Training and hazards**: weight-bench, barbell, trap-machine.
  - **Assembly kinds** (`assemblyTypes`)
    - **Entry**: stair approach with two torch members.
    - **Teaching and dining**: teaching table, and the safe-room table/bench cluster.
    - **Rest and service**: bedroom, washroom fixtures, and waiting area.
    - **Industrial**: machinery with pipe fittings, pipe banks, gate lights, and north descent.
  - **Room/world markers** (`worldObjectTypes`)
    - Guide, safe room, encounter, boss encounter, exit, chest/cache, door/threshold, discovery.

The scene graph parent chain is map → room → declared assembly → matching member props. Unassigned props remain under the room. Terrain remains the cell/surface hierarchy. Assemblies are created only for present exact room/group combinations; the catalog does not synthesize absent groups or imply every map must contain every type. World markers remain separate room children.

Assembly membership is recognized from runtime prop `groupId` together with `roomId`; it is not inferred from distance, labels, or matching asset names. Each `assemblyTypes` entry names its exact authored group, optional room scope, zone, placement-anchor guidance, bounds source, and semantic member roles mapped to existing `objectTypes`. A missing room scope lets the exact group ID match across rooms. Bounds come from runtime member footprints. `expectedCount` describes the authored pattern; `required` distinguishes members whose absence is a diagnostic from optional members whose absence is informational. Suggested nearby placement is advisory and distinct from the authored placement anchor. The catalog does not create physical links or alter connector geometry.

## Object properties and relationships

Each `objectTypes` record has a stable `id`, a human-readable `label`, `assetIds`, descriptive `tags`, and a default `layer`. `properties.nominalFootprint` records the typical authored footprint for reference; the actual footprint is runtime data. `blocksMovementTypical` is a descriptive default, not a collision rule. `placement.allowedSurfaceTags` expresses suitable placement surfaces, `allowedRotations` lists authored quarter-turn rotations, and `requiredParentTags` is empty where the catalog has no universal parent requirement. `ports` describe connection points for objects that can connect. `expectedRelations` express useful authored composition patterns.

Every relation has `relation`, `targetTags`, `required`, and `description`. Treat `required: false` as an advisory hint. It is not an error when the related object is absent. The bridge terrain type is the one explicit required relationship: when a bridge deck is authored, it must span channel water and meet walkable floor at each bank. This describes the deck as a logical object, not a requirement to add a bridge to any particular map.

A few source-grounded examples:

- `ef-rug-red` has the `underlay` layer and a `rug` tag. In the authored bedroom and teaching-table groups it sits beneath a bed or table, so its furniture relations are advisory.
- `ef-wood-table` and `ef-chair-green` appear together in the authored dining and teaching groups. The catalog describes the chair/table relationship as a grouping hint; it does not require every table to have chairs.
- `ef-bed-red` and `ef-lamp-table` share an authored bedroom group. The bedside relationship is advisory because other rooms need not contain either object.
- The `teaching-table` group in `tutorial-guildhall` has one table, three chairs, and one rug underlay. The rug and chairs are optional assembly members for diagnostics, although present in the authored group.
- `dining-cluster` in `tally-safe-room` has one table, two chairs, and a bench. `rest-bedroom` and `washroom-fixtures` in `sebastian-safe-room` describe separate living and washroom groups; the lamp/rug are optional, while the bed and both washroom fixtures are expected members.
- `northwest-machinery` in both industrial rooms contains one machine and two pipe fittings. The pipe fittings are optional member counts for diagnostics; the group describes authored grouping without claiming the pipes are connected. Pipe banks and gate lights have their own exact group IDs. The north descent belongs to `ball-of-swine-complex`.
- Industrial pipes expose fluid ports. Pipes, machines, and outlets are authored in waterworks groups; connectors may connect where their placement and terrain allow. An outlet's relation to water and a grate's relation to a drain approach remain advisory because the underlying maps can omit either one.
- The renderer derives a bridge deck at a walkable floor cell with opposing water neighbors along one axis; the deck runs across the other axis as part of a crossing that reaches floor at both banks. The deck relation names that structure and requires water beneath the crossing and floor at its two banks for that bridge instance.

These are authored game adaptations and scene-graph vocabulary drawn from room layouts and renderer composition. They are not proof of canonical book details, and they do not impose universal requirements on existing maps. Ports are declared connection metadata. The industrial outlet mouth carries both `water` and `fluid` tags so the declared discharge port can match a pipe port under mutual `validateConnection` compatibility. Active pipe attachments follow the catalog connector geometry. The catalog is not a general compatible-port network solver.

## Adding a type

1. Add an entry to the appropriate array in `map-object-rules.json`: `objectTypes`, `terrainTypes`, or `worldObjectTypes`. Keep `id` values stable and use descriptive tags rather than display names for relationships.
2. For an asset-backed prop, add each active asset ID to exactly one `objectTypes[].assetIds` list. Confirm the active asset inventory in both concept room rules and the baseline world; multiple assets may share a type only when they have the same placement behavior and meaningful relationships.
3. Describe typical subproperties and allowed surfaces. Keep nominal dimensions informational and use `footprintSource: "runtime"`; do not make catalog values replace per-instance runtime footprint or collision data.
4. Add ports only when the object has a real connection point. Add expected relations only when supported by authored group placement, terrain construction, or an explicit renderer composition rule. Keep `required` false unless absence is a real issue for that specific relationship instance; never require a map-wide adjacency just because a type often appears near another type.
5. If adding connector configuration, keep it in the top-level `connectors` object and document its exact fields with the scene-graph consumer. Update this document with the evidence source and a concrete example.

## Catalog type index

The catalog retains 47 existing object, terrain, and world-object types; 13 assembly templates are indexed separately below. The table below is a quick index; the JSON entries carry full tags, placement surfaces, properties, ports, and expected-relation descriptions.

### Props

| ID | Label | Layer | Expected relation tags (advisory unless marked required) |
|---|---|---|---|
| `ab-clean-barrel-wood-top` | Wood barrel | object | crate, barrel |
| `ab-clean-cot-metal-green` | Green metal cot | object | bed, `bedside-lamp` |
| `ab-clean-crate-wood-cross` | Cross-braced crate | object | crate, barrel |
| `ab-clean-plant-leafy-terracotta` | Terracotta potted plant | object | plant |
| `ab-clean-shelf-wood-empty` | Empty wooden shelf | object | crate, barrel |
| `cd-barbell` | Barbell | object | weight-bench |
| `cd-crate` | Dungeon crate | object | crate, barrel |
| `cd-stair-module` | Stone stair module | object | torch, door |
| `cd-torch` | Dungeon torch | object | stairs, wall |
| `cd-trap-machine` | Trap machine | object | crate, wall |
| `cd-wall-straight` | Straight wall segment | object | trap-machine |
| `cd-weight-bench` | Weight bench | object | barbell |
| `ef-bed-red` | Red bed | object | `bedside-lamp`, rug |
| `ef-chair-green` | Green chair | object | table |
| `ef-lamp-table` | Table lamp | object | bed |
| `ef-rug-red` | Red rug | underlay | bed, table |
| `ef-sink-counter` | Sink counter | object | toilet |
| `ef-toilet` | Toilet | object | sink |
| `ef-vending-green` | Green vending machine | object | bench |
| `ef-wood-bench` | Wooden bench | object | table |
| `ef-wood-table` | Wooden table | object | chair, rug |
| `industrial-exit` | Gold industrial exit | underlay | water, wall, door |
| `industrial-grate` | Industrial drain grate | underlay | water, wallfixture |
| `industrial-machine` | Industrial machine | wallfixture | pipe, torch |
| `industrial-outlet` | Industrial water outlet | object | water, pipe, drain |
| `industrial-pipe` | Industrial pipe | object / wallfixture | pipe, machine, outlet |
| `industrial-torch` | Industrial wall torch | wallfixture | machine, pipe |

### Terrain and renderer components

| ID | Label |
|---|---|
| `floor` | Walkable floor |
| `masonry-wall` | Blocked masonry wall |
| `channel-water` | Channel water |
| `bridge-deck` | Iron bridge deck |
| `wall-cap` | Wall cap and coping |
| `wall-face` | Wall face |
| `doorway-frame` | Dry arch doorway frame |
| `hanging-moss` | Hanging wall moss |
| `surface-lighting` | Surface light and reflection |
| `water-splash` | Water splash and ripple effect |
| `floor-materials` | Floor material overlays |
| `wall-corner` | Masonry corner piece |

### World-object kinds

| ID | Label |
|---|---|
| `guide` | Guide |
| `safe` | Safe room |
| `encounter` | Encounter |
| `boss` | Boss encounter |
| `exit` | Exit |
| `chest` | Chest/cache |
| `door` | Door/threshold |
| `discovery` | Discovery |

## Assembly type index

| ID / exact group ID | Room | Zone | Member roles (expected counts) |
|---|---|---|---|
| `stair-approach` / `stair-approach` | `entry-landing` | approach | stair ×1 (required), light ×2 (optional) |
| `teaching-table` / `teaching-table` | `tutorial-guildhall` | classroom | underlay ×1 (optional), table ×1 (required), chair ×3 (optional) |
| `dining-cluster` / `dining-cluster` | `tally-safe-room` | dining | table ×1 (required), seat ×2 (optional), bench ×1 (optional) |
| `rest-bedroom` / `rest-bedroom` | `sebastian-safe-room` | living | underlay ×1 (optional), bed ×1 (required), lamp ×1 (optional) |
| `washroom-fixtures` / `washroom-fixtures` | `sebastian-safe-room` | washroom | toilet ×1 (required), sink-counter ×1 (required) |
| `waiting-area` / `waiting-area` | `dmv-safe-room` | waiting | bench ×1 (required), vending-machine ×1 (optional) |
| `northwest-machinery` / `northwest-machinery` | any room with this exact group ID (currently both industrial rooms) | machinery | machine ×1 (required), pipe-fitting ×2 (optional) |
| `north-pipe-bank` / `north-pipe-bank` | `goblin-workshop` | waterworks | pipe ×1 (required) |
| `west-pipe-bank` / `west-pipe-bank` | `goblin-workshop` | waterworks | pipe ×1 (required) |
| `east-pipe-bank` / `east-pipe-bank` | `goblin-workshop` | waterworks | pipe ×1 (required) |
| `west-gate-torch` / `west-gate-torch` | `goblin-workshop` | lighting | light ×1 (required) |
| `east-gate-torch` / `east-gate-torch` | `goblin-workshop` | lighting | light ×1 (required) |
| `north-descent` / `north-descent` | `ball-of-swine-complex` | exit | exit ×1 (required) |
