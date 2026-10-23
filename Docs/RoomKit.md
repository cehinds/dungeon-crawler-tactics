# Modular room kit

The room kit is a separate visual authoring tool for assembling small isometric rooms from transparent PNGs. Open `Web/wwwroot/room-kit.html` while serving the repository over HTTP (for example, after starting the local game server). Choose a seed, dimensions, and prop density; toggle the visible layers; filter or download individual PNGs; then export the generated room JSON. The same seed, dimensions, and density produce the same placement data.

The workshop exports visual authoring recipes and playable standalone rooms. Choose **Play this room** to send the edited layout directly to the game, or export playable JSON and import it through Save & options. A valid import replaces the active run with a standalone encounter; export the current save first to preserve it. This is not a procedural campaign generator: the main floor remains authored in `UnityPackage/Runtime/Data/game-content.json`.

## Build and files

Install the optional extraction dependencies and rebuild from the source atlases at the repository root:

```sh
python3 -m pip install -r Tools/art-requirements.txt
python3 Tools/build_room_kit.py
```

The script writes separate transparent PNGs and `manifest.json` under `Web/wwwroot/assets/room-kit/`; original atlases and extraction records stay in `source/`. Extraction uses connected alpha components, nearest-neighbor resizing, and two pixels of transparent padding. Floor sprites and `water-overlay` are normalized to a 128×64 logical tile plus padding, so their PNGs are 132×68 with anchor `(66, 34)`. Other sprites keep their source proportions and may be taller or wider than one tile.

Package and validate the completed kit with:

```sh
python3 Tools/package_room_kit.py
```

This validates the 25 RGBA sprites and manifest, writes `Web/wwwroot/assets/room-kit/room-kit.zip` for the workshop download, and copies the manifest and PNGs into `UnityPackage/Runtime/Resources/RoomKit/`. The ZIP includes the standalone PNGs, manifest, and this guide as `README.md`; source atlases stay outside the archive.

The manifest is version 1 with logical tiles of 128×64 pixels and 25 PNG assets. Every asset record has `id`, `file`, `label`, `layer`, pixel `width` and `height`, a pixel `anchor`, integer-cell `footprint`, `tags`, and `blocksMovement`; `connections` is optional. The workshop uses only one-cell footprints today. `blocksMovement` affects the preview route and obstacle list; tags and connections describe asset metadata and orientation.

| Layer | Manifest asset IDs |
| --- | --- |
| `floor` | `stone-a`, `stone-b`, `water-floor`, `oil-floor` |
| `surface` | `grate`, `oil-overlay`, `water-overlay` |
| `structure` | `wall-ne`, `wall-nw`, `wall-corner`, `door-closed-nw`, `door-open-nw`, `door-closed-ne`, `door-open-ne`, `exit` |
| `prop` | `pillar`, `torch`, `lever`, `rubble`, `stairs`, `crate`, `barrel`, `chest` |
| `overlay` | `moss`, `fire-overlay` |

Asset filenames and IDs are separate: use manifest `file` to load a PNG and `id` as its stable recipe reference. `anchor.x` and `anchor.y` are pixel coordinates measured from the PNG's top-left corner to the center of its grid cell. Place the sprite so that this anchor lands on the projected cell center; sprite dimensions may exceed one 128×64 logical tile, especially for tall walls, doors, and props.

## Projection and draw order

For grid coordinate `(x, y)`, the 2:1 isometric projection is:

```text
screenX = (x - y) * 64
screenY = (x + y) * 32
```

Increasing `x` moves right and down; increasing `y` moves left and down. The seeded preview uses `-nw` wall/door variants on its `x = 0` boundary and `-ne` variants on its `y = 0` boundary. Respect `connections` when combining oriented pieces.

Draw floors first, then `surface` overlays. Draw upright pieces in increasing `x + y` depth so nearer cells cover farther cells. For equal depth, the preview orders `structure`, then `prop`, then `overlay`. The layer toggles use these same names and order.

For Unity sprites, set Texture Type to Sprite (2D and UI), keep the PNG at its authored pixel dimensions, use Pixels Per Unit = 128, Point filtering, and no compression. The package script copies the files but does not create or configure Unity texture importer metadata, so apply those settings in the Unity Editor. Convert the manifest's top-left anchor to Unity's normalized pivot as `(anchor.x / width, 1 - anchor.y / height)`. Keep transparent pixels intact so the feet or base align with the cell center without stretching the art.

## Exported room recipe

The download is a JSON document with `schemaVersion: 1`, `kind: "dungeon-room-authoring"`, the manifest path, seed, width, height, density, tile dimensions, start and exit cells, entrance/exit doors, `clearRoute`, `blockedCells`, and `placements`. Each placement references a manifest `assetId` and includes its own ID, layer, integer `x`/`y`, movement-blocking flag, rotation (0–3 quarter turns), and optional kind such as `wall`, `door`, or `exit`. This recipe preserves visual placements for further editing; it is distinct from a game checkpoint and from the playable-map export described below.

## Manual authoring and rotation

Choose an asset in the palette, then click a cell to paint its layer. Erase removes the selected layer. Piece rotation and map-camera rotation are separate controls; the four camera views preserve world coordinates and pointer picking. Recipe import validates IDs, positions and layers. Export room JSON retains decorative placements and piece rotations.

## Play an edited room

1. Build or import a recipe, then paint/erase its components and rotate pieces as needed.
2. Use dimensions between **6 and 20 columns**, and **6 and 16 rows** for runtime play. The recipe editor can represent smaller layouts, but the playable importer rejects them.
3. Choose **Play this room**. The workshop stores the playable map and opens the game, which submits it to the shared C# importer. Alternatively, **Export game tiles** downloads `encounter-map-tiles.json`; import that file using Save & options → Import map.
4. A valid import starts a standalone room. An invalid map leaves the current game intact. Export a campaign checkpoint before importing if it should be retained.

The playable JSON includes `schemaVersion: 1`, a label, `width`, `height`, collision/surface `tiles` and the full visual `placements`, including rotations. It can also specify player spawn and enemy records. Omitted actor records receive deterministic defaults: four party starts and three enemies. This export can still supply tile fields for an authored encounter, but runtime play no longer requires rebuilding the application.

Before replacing a run, C# checks dimensions, collection bounds, supported water/oil/burning tags, known asset IDs, layer/rotation/blocking compatibility, unique legal actor positions and walkable connectivity. Component art and live combat state persist in custom-room saves. New run clears the custom map override. The importer starts a single room rather than merging workshop content into the middle of a campaign.

## Rendering and platform limits

The runtime and workshop use measured PNG anchors and one 128×64 logical diamond grid. This aligns placement coordinates; it does not imply that every decorative silhouette fills exactly one tile. Sprite dimensions can exceed a cell, while movement still follows logical blocking. Ground surfaces remain below characters; fire, projectiles, impacts and floating combat text render above units and walls.

Runtime map import and retained decorative placements are implemented in the shared C# core and browser presentation. The earlier native Unity IMGUI presenter does not have full workshop/rendering parity. Copying the kit into Unity Resources or passing reference compilation is not evidence of Unity Editor Play Mode or Web export validation.

## Runtime JSON schema

[`Tools/custom-map.schema.json`](../Tools/custom-map.schema.json) describes the playable import format for editor completion and structural checks. The C# importer additionally validates tile bounds, asset/layer/blocking agreement, spawn occupancy and connectivity. `game-content.json` and its scenario/development sections use [`Tools/game.schema.json`](../Tools/game.schema.json).
