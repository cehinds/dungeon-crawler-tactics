# Reusable blue masonry walls

The wall pack converts the completed blue masonry into semantic, connected pieces. Compose its cardinal network tiles and optional construction details; avoid arbitrary crops from the completed scene, which can include floor or foreground objects and cannot describe hidden wall geometry.

## Package contents and schema

The pack is under `Web/wwwroot/assets/wall-components/`. Its `manifest.json` defines 16 network tiles, 15 construction pieces, and three sample layouts. Each tile uses a 64×96 pixel canvas on a 64-pixel grid, with a 64×64 logical footprint, 32-pixel bottom overhang, center pivot `[32,32]`, and 32-pixel cap. The manifest records `id`, `file`, `kind`, 4-bit `mask`, `size`, `pivot`, `footprint`, `overhang`, `connections`, `edgeTags`, `sockets`, three `layers`, alpha intent, and provenance.

The mask uses one bit per cardinal neighbor: north=1, east=2, south=4, west=8. Its value selects one of all 16 semantic cases, from an isolated pillar (0) through ends, turns, straights and junctions to a cross (15). A connected edge is tagged `stone-network-32-v1`; an unconnected edge is `empty`. Join matching connected tags and compare cap boundary RGBA profiles. Empty edges cannot join a connected edge.

Each tile exports separate `shadow`, `face`, and `cap` PNG layers under `layers/`, plus the assembled tile under `tiles/`. Render shadow first, then face, then cap. Face and shadow project south by `[0,24]` and `[0,28]` on the 64×96 canvas. The cap keeps the opaque masonry footprint complete while the face and shadow use the cardinal union mask. The tile pivot and logical footprint define placement; the pack does not define game collision or engine-specific depth sorting.

The 15 construction pieces comprise two repeatable stone materials, eight existing 128-pixel inner/outer corner overlays, and five doorway pieces: whole arch, west and east jambs, lintel, and optional threshold. The source material crops are normalized to 32×32, then periodically tiled to the network canvas; the exported material layer PNGs use the same 64×96 canvas as tiles. The doorway arch is a normalized 128×128 crop from the existing painted arch. The native corner and doorway overlays are details; they are not automatically socket-compatible with the 64-pixel network tiles. The rectangle sample uses the arch across a two-cell opening and records explicit visual adapters at each side; those adapters connect the composition but do not promise pixel-identical painted joins. Apply no automatic rotation: source lighting is directional.

## Sample room recipes

The supplied sample JSON uses `schemaVersion`, `id`, `canvas`, `grid`, and `instances`. Each instance records `assetId`, `file`, grid `cell`, and pixel `offset`. All three examples use a 768×576 canvas and 64-pixel grid.

- `samples/rectangle.json` assembles a 9×7 perimeter with a two-cell south opening. It uses 26 network tiles and overlays the 128×128 arch across the opening with explicit west/east adapters.
- `samples/l-shape.json` assembles a 9×7 L-shaped room (28 wall cells) with exposed ends and turns.
- `samples/corridor-junction.json` assembles a T/crossing corridor network (21 wall cells).

Each JSON has a matching PNG preview in `samples/`. Use these to see how neighboring cells determine the mask, or edit the instance list to build another layout. `replay.py` re-renders a recipe using Pillow and files from the pack.

## Source and limits

The two repeatable stone materials come from cropped regions of the existing painted cap and plain-wall components, normalized to 32×32 and tiled in their original world-aligned orientation. The eight boundary details preserve existing 128-pixel painted art and lighting. Masked network tiles are assembled variants, not 16 newly painted source illustrations; generated layouts and previews are also derived outputs. The doorway is a normalized crop from the existing arch illustration and its jamb/lintel layers are derived partitions. These derived files do not add to the count of newly authored source art or claim hidden source pixels.

This is a visual wall kit. It does not integrate into campaign maps or establish runtime editing, collision, navigation, or native Unity rendering. A consuming renderer must place the 64-pixel cells, order layers and details, and define collision separately. Optional 128-pixel details need their own placement and occlusion decisions.
