# Modular room kit

The room kit is a separate visual authoring tool for assembling small isometric rooms from transparent PNGs. Open `Web/wwwroot/room-kit.html` while serving the repository over HTTP (for example, after starting the local game server). Choose a seed, dimensions, and prop density; toggle the visible layers; filter or download individual PNGs; then export the generated room JSON. The same seed, dimensions, and density produce the same placement data.

The workshop is not a procedural campaign generator. Its JSON describes a visual room recipe and clear entrance-to-exit route. It does not create encounters, enemies, rewards, or playable campaign maps. Campaign rooms remain authored in `UnityPackage/Runtime/Data/game-content.json`.

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

The download is a JSON document with `schemaVersion: 1`, `kind: "dungeon-room-authoring"`, the manifest path, seed, width, height, density, tile dimensions, start and exit cells, entrance/exit doors, `clearRoute`, `blockedCells`, and `placements`. Each placement references a manifest `assetId` and includes its own ID, layer, integer `x`/`y`, movement-blocking flag, and optional kind such as `wall`, `door`, or `exit`. Keep this recipe separate from campaign content: it is an authoring preview, not a save file or encounter definition.
