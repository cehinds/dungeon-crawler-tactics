# Tile edge tags

Tile edge tags describe visual compatibility for the Book Location Tiles library. All 744 authored inventory assets carry tags, propagated to 2,232 exports across Pocket Dungeon, Ink & Lanterns, and Dungeon After Dark. They do not describe collision, walkability, hazards, or navigation. The original room kit and other style art packs are outside this feature's scope.

## Authored format

Each asset in `Docs/BookLocationTiles/inventory.json` has an `edges` object with exactly four keys: `north`, `east`, `south`, and `west`. Each value is a nonempty array of unique lowercase dotted tags, and every side has exactly one `join.*` connector. Connectors may use any valid name, such as `join.floor` or `join.road`. Additional tags describe appearance or a feature, for example `visual.starter-dungeon` or `portal.open`.

```json
{
  "id": "example-road-floor",
  "edges": {
    "north": ["join.road", "visual.stone"],
    "east": ["join.road"],
    "south": ["join.floor"],
    "west": ["join.road"]
  }
}
```

Two opposite sides connect when their connector strings match. For example, `join.road` on one tile's east edge connects to `join.road` on its neighbor's west edge. A clockwise quarter-turn maps north to east, east to south, south to west, and west to north; tags are rotated with the tile.

`join.manual` marks an edge whose placement needs human review. An asset with any `join.manual` side must set `"edgeReview": "manual"`, and that review flag requires at least one `join.manual` side. Manual joins never autoconnect. `join.overlay` identifies a component placed over a floor; it is ignored during floor-edge matching. Each side still needs exactly one connector.

The [`tile-edge.schema.json`](../Tools/tile-edge.schema.json) schema validates the `edges` object. The exporter also checks the asset’s manual-review flag.

## Authoring, export, and inspection

The inventory is the authored truth. The tile builder validates edge metadata and copies `edges` and `edgeReview` into each style's manifest and kit ZIP; it does not alter source PNGs. After editing inventory, rebuild the library and catalog using the commands in [Book Location Tiles](BookLocationTiles/README.md#rebuilding-and-checking), then follow its existing [AI-Art asset sync workflow](BookLocationTiles/README.md#rebuilding-and-checking) to propagate generated library assets to the art repository.

In Foundry, open **Map details → Tile edge tags** to select an asset and rotation and inspect its four sides. This is an inspector, not an authoring control. It reports the floor-edge check for the current preview. Every card in the [Book Location Tiles library](https://cehinds.github.io/dungeon-crawler-tactics/book-tiles.html) also has a collapsible edge-tag section.

The generator validates adjacent full-floor edges before export or Play. It checks matching connectors after quarter-turn rotation; a mismatch blocks the preview composition from export/Play. This is seam validation for authored art, not a full Wang-tile or WFC autotiler. It does not change movement, collision, hazards, or game rules.
