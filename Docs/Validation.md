# Playable build validation — 2026-10-22

The delivered browser build is an executable .NET WebAssembly game using the same C# core as the Unity project. It is not a Unity Web export. Earlier wireframe checks are superseded by this game verification.

## Automated code and content checks

| Check | Result |
|---|---|
| Original rules regression harness | 30 checks passed |
| Playable game harness | 50 checks passed |
| Strict content/campaign validation regressions | 16 tests passed |
| Current combat and campaign JSON | Valid: 12 classes, 36 abilities, 8 items, 8 crawlers, 3 encounters |
| Core, .NET Standard 2.1 / C# 8 | Build succeeded, no warnings or errors |
| Unity runtime presenter against actual Unity 2021.3.33 reference DLLs | Build succeeded; one expected unused Inspector-field warning in original RulesDemo |
| Unity WebGL conditional runtime path | Compiled against the reference DLLs |
| Unity WebGL save bridge JS checks | Five stub checks passed: download, upload, size limit, read error, cancel |
| Blazor WebAssembly Release publication | Succeeded; approximately 43 MB uncompressed static files |

The complete-floor tests use legal commands and forecasts, with no HP edits or instant-win bypass. The default party clears all three rooms including the boss. Independent QA also cleared the floor without items using the default party and two alternate class compositions.

Coverage includes party selection and configurable party capacity, class grants, legal BFS movement, walls/occupancy, team command ownership, activation consumption, exact preview/commit behavior, canceled items, charge spending, hazard damage along both player and enemy paths, water contact, frozen and shocked lifetimes, same-chain death/healing behavior, deterministic chains and event budgets, full-floor XP/rewards, valid save roundtrips, corrupted save rejection, defeat and retry.

## Browser environment

Local static build at `http://127.0.0.1:5173`, tested using Playwright with system Chromium in headless mode. The Browser skill was read and available tools were searched; no connected Browser/js/CUA tool was exposed, so local Chromium was used. Desktop viewport 1440×900 and mobile-width viewport 390×844. This does not establish support across every browser or mobile device.

## Browser verification

| Check | Result |
|---|---|
| Correct page identity and meaningful render | Passed |
| Framework error overlay / blank page | None |
| Relevant console and JavaScript page errors | Zero in final smoke and full run |
| Camp: class changes, reserve/deploy, four-person gate | Passed |
| Battle: select, real movement, target, forecast, cancel and confirm | Passed |
| Oil tile ignition and immediate occupant damage | Passed; final fixture predicts 18 → 14 HP |
| Shared potion charge consumption | Passed |
| Enemy phase returns to player round 2 | Passed |
| Save/reload byte-equivalent checkpoint | Passed |
| Invalid import preserves current state | Passed |
| JSON file download/import controls | Exercised in browser smoke |
| Mobile horizontal overflow | None at tested width |
| Pixel assets, equal grid cells and forecast layout | Screenshots inspected |

A second browser test played the actual WASM C# runtime through all three encounters with the default party: **3 victories, 150 XP, 43 planner iterations, 21 moves, 7 potions and 115 legal previews**. It saved the completed floor, refreshed the browser and restored the completed screen. No JavaScript errors occurred. This scripted traversal uses the same public command bridge as the visible controls; the smoke test separately exercises those controls.

Screenshots were inspected at `/tmp/dungeon-web-forecast.png`, `/tmp/dungeon-web-mobile.png`, and `/tmp/dungeon-complete.png`. These are local verification artifacts, not production assets.

## Unity limitations

No Unity Editor or Unity MCP bridge was available. Editor compilation, scene creation, Play Mode, Unity Web player export, and the native WebGL save bridge in a real exported Unity player have not been executed. The scene/build menus use Editor APIs and the runtime was compiled against real reference assemblies, but that does not replace those checks. Use the included Unity project and run the documented Editor workflow before shipping a Unity Web release.

The full game and browser clients are tested; soundtrack, animated combat, complex spatial spreading, level progression, elevation and procedural content are not implemented. See `PlayableGame.md` for the supported scope.

## Reproduce

```sh
python3 Tools/validate_content.py UnityPackage/Runtime/Data/combat-content.json
python3 Tools/validate_game_data.py
python3 -m unittest discover -s Tools -p 'test_*.py'
dotnet run --project Tests/RulesKernel.Tests.csproj
dotnet run --project Tests/GameTests/GameTests.csproj
dotnet build Tools/Compatibility/Core.Compatibility.csproj
dotnet publish Web/DungeonCrawlerTactics.Web.csproj -c Release -o Web/publish
python3 Tools/prepare_unity_project.py
python3 Tools/serve_game.py
```
