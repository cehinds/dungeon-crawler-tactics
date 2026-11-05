# Dungeon Crawler Tactics — Floor One

A new, compact Floor One RPG for Carl and Princess Donut. Explore a connected dungeon, meet Mordecai, prepare in the safe room, and resolve small turn based tactical encounters on the way to the floor boss and exit. The interface takes its navigation cues from classic menu driven RPGs.

The game rules live in pure C# under `Rebuild/Core`. The browser host runs those same rules through .NET 8 WebAssembly; JavaScript presents the map, menus and battle forecast. The authored items, skills, enemies and dialogue live in `Web/wwwroot/data/floor-one-rpg.json`. Preserved source lore and equipment/skill references are in `Rebuild/ReferenceData`.

## Play locally

Install the .NET 8 SDK, then run:

```sh
dotnet run --project Web/DungeonCrawlerTactics.Web.csproj
```

Open the local URL printed by .NET. Existing art is kept in `Web/wwwroot/assets`. To restore the small playable subset on a fresh checkout:

```sh
python3 Tools/prepare_hosted_assets.py Web/wwwroot --remote
```

Explore with the touch directional controls, WASD, or arrow keys. Press E or Enter to interact, and Esc to open or close the menu. Interact with nearby people and objects to advance the quest. In battle, select a party member, move, choose a skill and target, read the forecast, then confirm the action. Each crawler can move once and act once per turn; end the turn to let enemies respond. The safe room provides rest and saving. Equipment and skills are available through the party menus.

## Verify and publish

```sh
dotnet run --project Rebuild/Tests -c Release
dotnet publish Web/DungeonCrawlerTactics.Web.csproj -c Release -o Web/publish
python3 Tools/prepare_hosted_assets.py Web/publish/wwwroot
python3 -m http.server 8765 --directory Web/publish/wwwroot
```

Open `http://localhost:8765`. A browser integration check is available after installing Python Playwright and Chromium:

```sh
python3 Tools/playtest_floor_one.py --url http://localhost:8765 --browser /usr/bin/chromium
```

It walks to the first encounter using keyboard input, selects and moves units on the canvas, confirms attacks, runs enemy turns, and checks the victory return.

 The hosted asset manifest is `Tools/hosted-assets.json`: 60 individual files with checksums and an immutable AI-Art source revision. Publishing does not clone the full art repository or package every retained asset.

GitHub Pages builds on pushes to `main`, manual workflow dispatch, and `pages-dev-*` tags. A tested development revision can therefore be published without moving `main`. The workflow runs the C# tests, publishes the WebAssembly host, and restores only the manifest subset.

## Reset scope

This is a fresh game implementation. The former gameplay engine, Unity project, UI, generators and legacy tests were removed from the active source tree. The previous tracked revision is preserved by tag `archive/pre-rpg-reset-20261105`; `Rebuild/legacy-removal-inventory.json` records the removed files. Existing art files remain intact, and the separate AI-Art repository is unchanged.

Implemented scope is one connected floor, two party members, authored equipment and skills, tactical battles, a safe room, and a boss route. There is no claim of Unity Editor validation or a complete book adaptation.
