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

## Automatic floor matching

When Foundry builds square art, it checks every neighboring floor edge and the wall boundary around the floor. If the original floor choices already match, it keeps them. Otherwise, a deterministic, bounded search considers eligible full-ground assets and their four quarter-turn rotations, preferring the current assets and rotations where possible. The dungeon seed determines stable tie-breaking, so the same input and library produce the same fitted art. Manual and overlay joins are excluded from automatic floor candidates. This changes only the visual floor composition; it does not change the generated map or gameplay tiles.

The search has a 20,000-step budget. If no arrangement satisfies the floor and wall constraints, or the budget is exhausted, Foundry reports a specific fitting error and keeps the last successfully generated map. This is a bounded constraint search over the available floor assets, not an unbounded search or a guarantee that every authored kit can fit every generated boundary.

The current generator uses the kit's first four full-ground assets as its floor palette. Partial floors, corners, doors, and props are not replacement candidates. The shipped full-floor tags already match, so fitting preserves their existing appearance; custom directional connectors can trigger replacement and rotation. Matching tags express authored compatibility, not a pixel-by-pixel guarantee that artwork will look seamless.

## Authoring, export, and inspection

The inventory is the authored truth. The tile builder validates edge metadata and copies `edges` and `edgeReview` into each style's manifest and kit ZIP; it does not alter source PNGs. After editing inventory, rebuild the library and catalog using the commands in [Book Location Tiles](BookLocationTiles/README.md#rebuilding-and-checking), then follow its existing [AI-Art asset sync workflow](BookLocationTiles/README.md#rebuilding-and-checking) to propagate generated library assets to the art repository.

In Foundry, open **Map details → Tile edge tags** to select a catalog asset and rotation and inspect its four tags. Choose **Inspect connections on the map** to show matching joins and mismatches as an overlay. Click a floor tile, or focus the map and use the arrow keys to move the selection and Enter to inspect it; Escape closes the overlay. The dialog then reports the actual placed tile, its quarter-turn, and whether each side matches a neighboring floor or wall. The catalog selector remains available for inspecting other library components; it does not replace or edit the placed tile. Every card in the [Book Location Tiles library](https://cehinds.github.io/dungeon-crawler-tactics/book-tiles.html) also has a collapsible edge-tag section.

The inspector reports unconnected outer sides when no floor or wall boundary is present. `join.manual` remains a human-review tag and is not automatically matched; manual edges are excluded from automatic floor fitting. `join.overlay` belongs to an overlay component and is ignored by floor matching. Edge inspection is visual authoring support: tags and fitted art do not define movement, collision, hazards, or navigation, and the fitter does not generate or alter gameplay maps.
