# Procedural maps

The [Dungeon generator](../Web/wwwroot/dungeon-generator.html) is a browser authoring tool for creating and tuning standalone encounter layouts. It generates three layout families—chambers, caverns and halls—and three visual themes—stone, sewer and crypt. Generation is deterministic for a fixed seed and set of options, so a seed and its settings can be recorded in a recipe and regenerated later.

## Generate and refine

Choose a layout and biome, enter a seed, then set the board size, target room count and prop density. The supported board range is 6–20 columns by 6–16 rows. The generator may produce fewer rooms than requested when the selected board is too small. Regenerate after changing settings to preview the result. The isometric view shows the art; blueprint view shows the map structure. Rotate the preview and toggle the clear-route overlay. The preview marks party spawns, enemies and the exit. For manual placement edits, open the generated map in the room workshop.

The generator uses the existing 25-piece room kit for production map art. The new style-pack biome illustrations are static art-lab references and are not part of the runtime map renderer or gameplay rules.

## Export and play

Export a recipe to preserve the seed and authoring settings for later editing. Export playable JSON to create a standalone battle map supported by the shared C# custom-map importer. The browser can also open the result in the room workshop for further manual painting, or start it as a standalone battle. PNG export is a visual snapshot for sharing and review; it is not an import format.

A valid playable map replaces the active run with a standalone encounter. Defeat all enemies to complete it; the exit marker is an authoring route endpoint, not a new extraction objective. Export the current campaign save first if you want to keep it. Invalid JSON is rejected without replacing the current run. The campaign remains authored; generated maps do not insert themselves into campaign progression.

## Reproducibility and scope

Keep the seed, layout, biome, dimensions, density and requested room count together when sharing a recipe. Recipe exports are the editable authoring record; playable JSON contains the map payload accepted by the runtime importer. View rotation is a preview setting and does not alter the generated map. Changes to the generator or its asset kit may affect future regeneration, so retain the recipe and exported JSON when the exact result matters.

The generator is pure browser authoring JavaScript. Runtime validation and play use the existing shared C# importer and game rules. The tool does not modify campaign data, add new combat rules, or integrate the style-pack illustrations into Unity. Unity Editor compatibility requires separate validation; browser availability and successful C# map import do not establish Unity Editor validation.

## Validation status

The generator checks covered 720 cases for connectivity, map bounds, spawns, canonical assets, dry routes, repeatability and rotations; the existing room-generator checks also passed. Chromium checks covered each layout and view, downloads, mobile overflow and canceling the play confirmation. These checks do not establish Unity Editor integration, which has not been validated.

The integration smoke test also imported four generated maps into the actual
shared C# WebAssembly game, including 6×6 and 20×16 bounds, all three layouts,
maximum prop density and a long seed. All four party members, three enemies and
map placements were retained. Workshop handoff and confirmation cancellation
also passed. Run against a published build:

```sh
node Tools/test_procedural_map.mjs
python3 Tools/playtest_procedural_maps.py --url http://localhost:5200
```

Biome decoration choices are authored in
`Web/wwwroot/assets/map-generation-rules.json`; the deterministic topology and
export adapter live in `Web/wwwroot/procedural-map.js`.

Screenshots: [desktop](Screenshots/dungeon-generator-desktop.png) and
[phone](Screenshots/dungeon-generator-mobile.png).
