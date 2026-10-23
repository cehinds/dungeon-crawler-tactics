# Playable build validation

## Lantern Row tabletop-inspired neighborhood

The final shared-core run passes **572 checks**, including 43 new neighborhood checks alongside the existing 529. All **83 Python validation tests** pass. The neighborhood suite walks the connected map through legal commands, verifies trained and fallback rescue options, resolves all three optional locations, earns all three challenges, wins the encounter through legal forecasts and commits, and restores the exact original campaign. It checks preview/cancel purity, repeated rewards, reloads, innate skills after optional class changes, malformed receipts, cyclic backups and migration of published floor-three exploration saves without changing inventory or the input checkpoint.

The actual published .NET WebAssembly build passes `Tools/playtest_neighborhood.py` at **1440×900 and 390×844**. Visible UI checks cover entry cancellation, preparation, workshop barter, coolant-latch and rescue previews, complete item forecasts including achievement rewards, qualified Katia selection, cancellation, repeated-confirm rejection, three saved challenges and the clue after reload, map movement, encounter entry, explicit next-party-member turn handoff, and return to the preserved campaign. The top journal button is pointer-accessible above the canvas. Both viewports report zero JavaScript errors. These functional checks do not establish human balance or enjoyment.

Both catalogs and their strict schemas validate; the lore generator preserves authored neighborhood and journey data. Canonical Unity sources are synchronized. .NET Standard compatibility and Unity runtime-reference compilation succeed (the existing `RulesDemo.contentJson` Inspector-field warning remains). Browser publication succeeds. Native Unity Editor, Play Mode and Unity Web export remain unverified; this live browser delivery uses the shared C# engine through .NET WebAssembly.


## Eight-floor journey, classes and party house

The final shared-core run passes **529 checks**: 205 game, 42 rules, 44 scenario, 20 custom-map, 43 expedition, 43 rank/class, 80 journey and 52 house/economy checks. All 73 Python validation tests pass. Both JSON catalogs validate with 148 class kits, 88 abilities, 142 class trees and 1,988 class nodes. The generated research snapshot and Unity source sync are verified.

The journey harness completes floors 1–8 through legal commands, including required exploration objectives, the floor-7 bypass and six weakened-enemy captures on floor 8, with checkpoint reloads. Class checks cover branch-point spending, ownership, prerequisites, real level-50 capstone effects, class switching and rank-20 forecasting/commit. Housing checks cover atomic purchase/cancellation, gold receipts, paid practice, crafting prerequisites, personal club credentials, forgery rejection and exact preservation across nested expeditions and boss scenarios.

Art checks cover 96 directional crawler frames, 16 boss/Scatterer poses, four scenery components, 24 new enemy poses, six menu illustrations and 30 component definitions. The room workshop retains 461 generator checks including 450 seeded rooms, plus 640 rotated projection/picking checks. .NET Standard compatibility builds cleanly; Unity runtime reference compilation has zero errors and its existing Inspector-field warning. Native Unity Editor execution, Play Mode and Unity Web export remain unverified. The browser is the shared C# game hosted through .NET WebAssembly.

Browser validation covers the actual WASM game at desktop and phone sizes: six expedition briefings and enemy phases, class-node preview/cancel/commit, home upgrade and training costs, local records, earned credentials, the floor-7 bypass, and floor-8 capture preview/cancel/commit. The menu atlas loads all six illustrations and its thirty stateful components; the source-linked codex exposes floors, classes, skill ranks, enemies and housing. `Tools/playtest_expansion.py` and `Tools/playtest_lore.py` retain the repeatable browser drivers. These are functional checks, not a human balance study.

## Earlier development, scenarios and runtime map milestone

The shared-core suite passes **179 game checks, 44 scenario checks, 20 custom-map checks and 42 rules checks**. The 34 Python validation checks pass (28 under Tools and six cross-validator tests). Both authored catalogs validate. The art validator verifies 16 distinct boss/Scatterer poses plus four transparent scenery components, alongside the existing 96 directional crawler frames. .NET Standard 2.1 compatibility builds without warnings or errors; Unity runtime reference compilation has zero errors and the existing unused Inspector-field warning. Unity Editor, Play Mode and native Unity Web export remain unverified.

Scenario tests complete Hoarder, Juicer and Ball of Swine using ordinary legal commands, then reload the victorious checkpoints. They also verify exact campaign restoration, mid-phase intentions, capped emergence, interruption, cover interception/destruction, carried parts, partial construction, helper recovery, real Speedbump collision damage, defeat/retry, forged-state rejection and snapshot isolation. Completed level-four campaigns can enter and return from a scenario without losing state. Boss victory and defeat screens expose return/retry controls. Bosses still occupy one logical tile.

Visible Chromium checks at 1366×768 and 390×844 cover stat forecast/cancel/commit, a personal practice record, recipe cost cancellation/commit, owned-box opening and persistence, all three scenario briefings and enemy phases, scenario interaction confirmation, invalid-map rejection without changing the saved run, valid map import/reload, and no duplicate level-up notice on scenario return. Crafting dialogs also fit at 360×640 and 844×390. No JavaScript errors occurred. The development browser driver uses a documented one-hit battle fixture to reach an earned level quickly; the separate complete-floor driver uses ordinary legal commands throughout.

The full-floor browser driver still completes three victories and 150 XP, using 116 driver ticks, 39 moves, seven potions and 997 legal previews. Its completed save survives refresh. The actual workshop **Play this room** button imports 111 visual placements into a playable battle and preserves the exact map after reload. Generator/editor tests retain 450 seeded layouts, 640 rotated picking checks and canonical tile validation. Root and renderer reviews inspect the new grounded scenery, danger lanes and anchored boss sprites at desktop and phone sizes.

`Tools/playtest_development.py`, `Tests/ScenarioTests` and `Tests/CustomMapTests` provide reproducible milestone coverage. CI now runs the scenario/custom-map harnesses and the scenario art validator before publishing.


## Earlier forms, turn freedom and mechanics review

The new shared-core harness passes **140 game checks**, including both action orders, explicit activation completion, default enemy attacks, form/stance forecasts, no-op mode rejection, achievement uniqueness and Guarded mode save roundtrips. The rules harness passes 42 checks; all 27 Python validation tests pass. Unity runtime reference compilation succeeds with zero errors and one existing Inspector-field warning. Native Unity Editor/Play Mode/Web export remain unverified.

The browser full-floor driver completed 3 victories, 150 XP and level 4 using legal commands: 116 driver ticks, 39 moves, 7 potions and 997 legal previews. The completed save survived refresh with no page errors. Visible campaign checks passed at 1366×768, 390×844 and 844×390, including selected-ability details, action then movement, explicit End Turn, all character sheets, form cancel/confirm, achievement history and reload. A real enemy Heavy Blow produced the corresponding narrator declaration and HP change. A movement fixture captured six enemy movement events across 74 changing frames, with the phase banner and input lock.

The tile workshop passed painting/erasing, four component/camera rotations, JSON roundtrip and campaign-tile export checks on all three viewport sizes. Node coverage includes 450 seeded layouts, 640 rotated projection/picking checks, layer/export checks and acceptance by the canonical campaign validator. Root inspected the corrected continuous perimeter meeting the floor, layered fire, and immediately visible history dialogs.

The review gallery loaded all seven images and all 45 checklist entries at 1440×1000 and 390×844; status filters worked, no horizontal overflow or JavaScript errors occurred. Its unchecked boss scenarios and advanced progression systems remain proposed.

## Earlier progression and movement update

The shared-C# game harness passed 122 checks and the rules harness passed 42 checks. Both authored catalogs validate (20 classes, 66 abilities, 8 consumables, 9 roster entries and 3 encounters); all 27 Python validator tests pass. The directional-art validator checks 96 distinct frames across all eight deployable characters. Netstandard2.1 compatibility succeeds, and Unity runtime reference compilation succeeds with zero errors and one existing Inspector-field warning. Unity Editor execution remains unverified.

New regression coverage includes enemy wall detours and movement events, level growth and personal skill unlocks, equipment ownership/slots/effective stats, safe-room rest, objective views, legacy-save progression migration, and a complete three-encounter run.

The actual WebAssembly browser driver also completed all three encounters: 3 victories, 150 XP, level 4, 32 moves, 7 potions and 1,039 legal previews across 75 driver ticks. The completed save survived refresh with no JavaScript errors. It now explicitly rests between encounters, matching the safe-room flow.

## Earlier animated dungeon revamp

The earlier shared-C# build passed 96 game checks, 42 rules checks, 21 existing Python validation tests and 6 new content-validation regression tests. Both authored JSON catalogs validate. The netstandard2.1 compatibility build passes. Unity presentation source also compiles against Unity runtime references with zero errors and one existing unused-field warning; Unity Editor Play Mode and Web export remain unverified.

The actual local WebAssembly build completed all three encounters through the public browser command bridge: 3 wins, 150 XP, 33 moves, 7 potions and 860 legal previews across 79 driver ticks. Its completed save reloaded successfully with no JavaScript errors. This is functional automation, not a balance or human enjoyment study.

Visible-UI Playwright checks passed at 1366×768, 390×844 and 844×390: exploration, pointer targeting, forecasts, movement, Magic Missile, Shapeshift, Puddle Jumper, Wet + Lightning, individual party turn order, inspect panels and viewport fit. A separate rapid-input check verified move → ability → target ordering and refresh during animation restoring the committed position. See [Revamp-QA.md](Revamp-QA.md) for the test scope and measured latency.

That revision had 16 classes, 46 abilities, 8 items, 9 roster entries (8 deployable) and 3 encounters. Presentation assets are components rendered over actual game coordinates; they are not a static concept screenshot.

## Earlier playable build verification

The following records the previous revision and is retained as historical evidence. Its content counts and check totals are superseded above.

The delivered browser build is an executable .NET WebAssembly game using the same C# core as the Unity project. It is not a Unity Web export. Earlier wireframe checks are superseded by this game verification.

## Automated code and content checks

| Check | Result |
|---|---|
| Rules and defense regression harness | 42 checks passed |
| Playable game and exploration harness | 67 checks passed |
| Strict content/campaign validation regressions | 21 tests passed |
| Current combat and campaign JSON | Valid: 12 classes, 36 abilities, 8 items, 8 crawlers, 3 encounters |
| Core, .NET Standard 2.1 / C# 8 | Build succeeded, no warnings or errors |
| Unity runtime presenter against actual Unity 2021.3.33 reference DLLs | Build succeeded; one expected unused Inspector-field warning in original RulesDemo |
| Unity WebGL conditional runtime path | Compiled against the reference DLLs |
| Unity WebGL save bridge JS checks | Five stub checks passed: download, upload, size limit, read error, cancel |
| Blazor WebAssembly Release publication | Succeeded; approximately 43 MB uncompressed static files |

The complete-floor tests use legal commands and forecasts, with no HP edits or instant-win bypass. The default party clears all three rooms including the boss. Independent QA also cleared the floor without items using the default party and two alternate class compositions.

Coverage includes fog discovery without revealing through walls, cache-once rewards, exploration save validation and legacy battle resume, legal target views without state mutation, pre-damage defenses and lethal-hit protection, party selection and configurable party capacity, class grants, legal BFS movement, walls/occupancy, team command ownership, activation consumption, exact preview/commit behavior, canceled items, charge spending, hazard damage along both player and enemy paths, water contact, frozen and shocked lifetimes, same-chain death/healing behavior, deterministic chains and event budgets, full-floor XP/rewards, valid save roundtrips, corrupted save rejection, defeat and retry.

## Browser environment

Revised local static build at `http://127.0.0.1:5188`, tested using Playwright with system Chromium in headless mode. The Browser skill was read and available tools were searched; no connected Browser/js/CUA tool was exposed, so local Chromium was used. Current revision checked at desktop 1366×768 and phone sizes 390×844 and 360×740; original full-floor testing also used 1440×900. This does not establish support across every browser or mobile device.

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

A second browser test played the actual WASM C# runtime through all three encounters with the default party: **3 victories, 150 XP, 86 planner iterations including exploration, 21 combat moves, 8 potions and 122 legal previews**. It saved the completed floor, refreshed the browser and restored the completed screen. No JavaScript errors occurred. This scripted traversal uses the same public command bridge as the visible controls; the smoke test separately exercises those controls.

The compact battle/camp layouts were inspected in `/tmp/live-battle.png` and `/tmp/camp-360.png`. The board and confirmation remain visible while a bounded ability list may scroll on smaller phones. See [Playability-Review.md](Playability-Review.md). Earlier screenshots were inspected at `/tmp/dungeon-web-forecast.png`, `/tmp/dungeon-web-mobile.png`, and `/tmp/dungeon-complete.png`. These are local verification artifacts, not production assets.

## Responsive dialogs and notifications

The published local WASM build passed `Tools/playtest_ui.py` at 1366×768, 390×844, 360×640 and 844×390. The checks use visible controls to change class, export a save, explore corridors, cancel and confirm a Guardian forecast, and open/close supplies. Cancel preserves the exact serialized save and restores focus; confirm applies Guarded and produces success feedback. Export feedback remains inside the active native dialog. Confirmation buttons fit the viewport, battle pages do not scroll, short portrait camp fits, and no JavaScript page errors occurred. JavaScript syntax checks also passed. See [Modal-Feedback-QA.md](Modal-Feedback-QA.md) for focused feedback checks and limitations.

## Unity limitations

No Unity Editor or Unity MCP bridge was available. Editor compilation, scene creation, Play Mode, Unity Web player export, and the native WebGL save bridge in a real exported Unity player have not been executed. The scene/build menus use Editor APIs and the runtime was compiled against real reference assemblies, but that does not replace those checks. Use the included Unity project and run the documented Editor workflow before shipping a Unity Web release.

Soundtrack, complex spatial spreading, elevation and procedural campaign content remain unimplemented. Animated combat and level progression are now supported in the browser build. See `PlayableGame.md` for the supported scope.

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

Optional full browser traversal (requires Playwright and a local Chromium executable):

```sh
python3 -m pip install playwright
python3 Tools/playtest_floor.py --url http://localhost:8000 --browser /usr/bin/chromium
python3 Tools/playtest_ui.py --url http://localhost:8000 --browser /usr/bin/chromium
```
