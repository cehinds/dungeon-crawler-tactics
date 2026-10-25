# Dungeon Crawler Tactics

A playable Dungeon Crawler Carl fan tactics prototype with a shared C# engine: an eight-floor story route, class and skill progression, a persistent party house, animated isometric combat and tag-driven reactions. The original three-encounter campaign remains available for existing saves.

**Play online:** [Dungeon Crawler Tactics](https://cehinds.github.io/dungeon-crawler-tactics/).

**Art lab:** [Three styles, individual PNG downloads, collections and animation previews](https://cehinds.github.io/dungeon-crawler-tactics/art-lab.html). Each style contains 360 labeled components: 120 existing pieces and 240 new pieces, including 192 static illustrations and 48 source frames for eight six-frame motion studies. That is 1,080 components across all styles; normalized frames, strips, and WebP previews are derived files and are not counted again. Whole-style ZIPs download directly from the [AI-Art repository](https://github.com/cehinds/AI-Art/tree/dungeon-crawler); individual PNGs and smaller collection downloads remain on Pages. The concept-art library remains separate from the production room kit and does not add runtime abilities. See [the art pack guide](Docs/Style-Art-Packs.md) and the [expansion inventory](Docs/AssetExpansion/README.md).

**Lore codex:** [Classes, rank tables, floors, enemies and housing evidence](https://cehinds.github.io/dungeon-crawler-tactics/codex.html) · [Story and housing guide](Docs/Journey-and-Home.md).

**Books 1–8 map tiles:** [Browse location coverage and tile kits](https://cehinds.github.io/dungeon-crawler-tactics/book-tiles.html). The source-linked index covers 187 locations across Books 1–8. All 31 kits across three styles are exported: 93 native square-grid atlases and 2,232 component PNGs, including six new Books 6–8 environment families. Art, export, and expanded browser QA passed. The browser generator can carry this art as presentation metadata in custom maps; it does not change canonical collision or apply these tiles to campaign maps. Publication is tracked by the [Pages deployment workflow](https://github.com/cehinds/dungeon-crawler-tactics/actions/workflows/deploy-pages.yml) after push to main. See the [coverage guide](Docs/BookLocationTiles/README.md) and [QA status](Docs/BookLocationTiles/QA.md). Art sources and Web manifests are maintained in the [AI-Art repository](https://github.com/cehinds/AI-Art/tree/dungeon-crawler/dungeon-crawler-tactics). The current lock pins AI-Art commit `b2a02094de3f15a5ba8d81c01e8db4dbceb85626`, whose main index contains 21,945 project files. Its separate originals index tracks raw generation sources, which are not restored to the game.

**Completion checklist:** [Implemented, tested and still unfinished](Docs/Completion-Checklist.md) · [Expanded story levels](Docs/Story-Levels.md) · [Sponsors, Favor and traps](Docs/Audience-and-Traps.md).

**Visual and signature-move pass:** textured modular walls, illustrated house rooms,
tabbed character sheets and larger turn indicators. Carl can rig traps and throw
Dynamite; Donut can choose a temporary floor specialty and summon two playable
Clockwork copies; Katia can use Rush to extend her movement. See the
[source audit and adaptation boundaries](Docs/Signature-Moves-Audit.md). The
[menu atlas](https://cehinds.github.io/dungeon-crawler-tactics/menu-atlas.html)
also offers the actual house PNG components and reusable frame for download.

**Concept chamber pass:** the first legacy battle, first story battle and Sewers
expedition now use connected chambers with real blocked walls and doorways.
Generated stone PNGs share anchors between the battlefield and room workshop.
The closer camera, four-button action bar and corner forecast emphasize the map;
all abilities remain available in the action book. Existing active saves retain
their original geometry. See [visual review](design-qa.md).

**Tabletop inspiration:** [Official RPG research and prioritized gameplay changes](Docs/Tabletop-Inspiration.md) · [Playable Over City neighborhood: Lantern Row](Docs/Over-City-Neighborhood.md).

**Mechanics review:** [Seven concept sheets and feature checklist](https://cehinds.github.io/dungeon-crawler-tactics/mechanics-review.html) · [Lore research](Docs/Lore-Mechanics-Review.md) · [Implementation plan](Docs/Mechanics-Plan.md) · [Playable boss scenarios and sprite sources](Docs/Boss-Concepts.md).

**Menu atlas:** [Six illustrated menus and 30 interactive components](https://cehinds.github.io/dungeon-crawler-tactics/menu-atlas.html) · [Expansion content](Docs/Expansion.md) · [Component guide](Docs/Menu-Components.md).

**Build rooms:** [Room workshop](https://cehinds.github.io/dungeon-crawler-tactics/room-kit.html) · [Download 25 layerable PNGs](https://cehinds.github.io/dungeon-crawler-tactics/assets/room-kit/room-kit.zip). Paint/erase tiles and components, rotate pieces or the camera, and import/export recipes. Choose **Play this room** to start a validated standalone battle with the full room layout, or export a playable JSON map for import through Save & options. A valid room import replaces the current run; export its save first to keep it. Campaign maps remain authored. See [Room kit guide](Docs/RoomKit.md) for anchors, layers and Unity import settings.

**Procedural maps:** [Dungeon Foundry](https://cehinds.github.io/dungeon-crawler-tactics/dungeon-generator.html) creates seeded chambers, caverns, and halls. Generate chooses a fresh seed by default; edit a seed or select **Keep this seed fixed** to reproduce a layout. Its square-art preview offers three styles and 31 environment kits, with room-floor variation, backdrop ambience, blueprint mode, 90° rotation, zoom, pan, and grid/route overlays. Reserved entrance, party, enemy, and exit positions stay connected. Blocked-object outlines reflect canonical collision; W/O/F markers show actual playable water, oil, and fire, while wet-looking art alone is decorative. Playable JSON keeps canonical terrain/collision and carries optional native-art presentation metadata, so browser Play uses the same style, kit, and composition as the preview without changing gameplay rules. Standalone battles keep the defeat-all-enemies win condition. See [Procedural Maps](Docs/Procedural-Maps.md).

**New clone:** restore the pinned art assets before testing or building with `python3 Tools/sync_art_assets.py` (Python 3.10 or newer). **Play locally:** run `./play.sh` on macOS/Linux, or `Play-Windows.bat` on Windows, then open **http://localhost:8000**. The download archive includes the published game; a source checkout needs the `dotnet publish` command below first.

**Unity:** open `UnityProject/` in Unity 6, choose **Dungeon Crawler → Create Playable Scene**, then press Play. Choose **Build Web Player** from the same menu to export using your installed Unity Web Build Support module.

The included playable browser build runs the actual shared C# game through .NET WebAssembly. It is not a Unity Web export. The full Unity source and scene/build tooling are included, but a Unity Editor was unavailable here for Play Mode or Unity Web export verification.

## What you can play

- Start with Carl, Princess Donut, Katia and Mongo; Mordecai advises from camp. Select four of eight field characters and customize optional classes while retaining personal abilities.
- Follow the story through floors 1–8 with six distinct expanded 17×13 exploration approaches, 24 additional discoveries (12 functional supply caches), Lantern Row, floor objectives and a floor-7 bypass. The original three-room campaign remains available.
- Fight on authored story boards or six optional expedition maps. Use class abilities or shared items, inspect the exact forecast, confirm or cancel.
- Watch actual walk/attack/hit sprite frames and visual reactions on the map. Inspect HP, Mana/MP, movement, conditions, range and exact forecasts in a compact HUD.
- Choose actions in a responsive modal with labeled category colors, Mana costs and legal-target counts. Review the exact forecast in its confirmation modal; end-turn confirmation names the next actor.
- Move and act in either order; actions preserve unused movement. Explicitly end the current character's turn to select the next ready ally; enemies act after the whole party finishes. Watch enemies navigate around walls during a clearly labeled enemy phase.
- Rotate the map through four views, preview movement paths, and pan/zoom on phones. All eight field characters have four-direction idle and walking sprites.
- Earn shared party XP through level 50. In story mode, class changes and manual stat allocation unlock on floor 3. Train skills through committed use: normal cap 15, configured exceptions 20.
- Buy a shared house on floor 4, open eight bedrooms, install training/crafting facilities and a social screen, and claim eligible personal club credentials. Gold income and tactical benefits are labeled adaptations.
- Combine oil/fire, water/wet/lightning, cold/frozen/shatter; use terrain while avoiding hazard damage. Guardian, Bard and Necromancer support abilities now grant real single-hit protection.
- Fight deterministic enemies, collect sponsor supplies, reach the boss, finish the floor, or retry after defeat.
- Earn once-per-run sponsor deliveries, then use bounded AI Favor for eligible environmental supplies. Craft and place one-use Coolant/Shock snares; traps affect either team and persist in saves.
- Choose Katia's four forms and three tactical stances through character sheets, with exact stat tradeoffs. Selected abilities expose descriptions and targeting information.
- Explore the original Lantern Row neighborhood through the safe-room entry or its optional floor 3 discovery. Prepare supplies, follow connected streets, barter or bypass the trapped store, rescue a crawler, and earn saved challenge rewards.
- Follow individual enemy declarations and impact messages; five saved first-time achievements trigger NEW ACHIEVEMENT feedback. Open earned fixed-content boxes and craft four supply recipes in the safe room.
- Try separate Hoarder, Juicer and Ball of Swine scenarios with objective briefings and special interactions, then return to the preserved campaign.
- Explore six optional training expeditions with distinct layouts and enemy kits; your selected build carries in and the campaign restores exactly on return.
- Choose two-branch, six-node skill trees for each of eight crawlers, with stat forecasts, prerequisite checks and saved unlocks.
- Start the optional story campaign from the eighteen-floor guide. Floors 1–8 include seven battles and the destroyed floor-7 bypass, with route, quadrant and capture objectives.
- Autosave, reload, and export/import a portable JSON save.

There are **142 selectable class kits (122 source-attested names plus 20 original kits), six enemy-only kits, 95 ability definitions, 1,988 class-tree nodes, 10 consumables, 6 equipment pieces, 96 base directional character frames and 36 Katia form frames**. Stat formulas, early allocation timing, skill ranks, recipes and scenario rules are tactical adaptations, not canonical book formulas. Progression and equipment are data-driven; see [Progression](Docs/Progression.md). The catalog is a sourced survey, not an exhaustive full-text audit. Numerical rank curves and class trees are game adaptations; unknown canonical ranks stay unknown. Floors 9–18, a complete T’Ghee deck battle system, full club interiors, general summoning, area chains, elevation, procedural campaign levels and audio remain outside this release. The animated browser presentation uses the shared C# engine; Unity's presenter remains the earlier IMGUI implementation.

## Start here

- [GitHub Pages deployment and automatic updates](Docs/GitHubPages.md)
- [Play/setup and current architecture](Docs/PlayableGame.md)
- [Actual class, ability and item catalog](Docs/PlayableContent.md)
- [QA checklist](Docs/Playable-QA.md)
- [Validation evidence](Docs/Validation.md)
- [Revamp character research and adaptation boundaries](Docs/Revamp-Research.md)
- [Revamp browser checks](Docs/Revamp-QA.md)
- [Original clickable wireframes](Wireframes/index.html)

Earlier design documents in `Docs/` are retained as planning context; `PlayableGame.md` and the actual JSON describe the current implementation.

## Editable source

| Path | Responsibility |
|---|---|
| `UnityPackage/Runtime/Core/` | Shared C# rules, campaign, movement, AI, state, saves and validators |
| `UnityPackage/Runtime/Data/combat-content.json` | Classes, abilities, items, tags and reactions |
| `UnityPackage/Runtime/Data/game-content.json` | Roster, stats, maps, enemies, rewards and tag lifetimes |
| `UnityPackage/Runtime/Unity/` | Unity game presentation and browser save bridge |
| `UnityPackage/Editor/` | Scene creation, content/build checks and pixel import settings |
| `UnityPackage/Runtime/Resources/Art/` | Original 128×128 pixel textures |
| `Web/` | Browser presentation and C# WebAssembly bridge |
| `UnityProject/` | Ready-to-open source copy for Unity; generated from UnityPackage |
| `Tests/` | Behavioral regression and complete-floor test harnesses |
| `Tools/` | Content schemas, validators, project preparation and art source |

Edit the canonical `UnityPackage` files. Run `python3 Tools/prepare_unity_project.py` to synchronize managed source into the Unity project without replacing your scenes or metadata. Avoid independently editing both copies.

## Verify or rebuild

Requires Python 3, `Tools/requirements.txt`, and .NET 8 SDK for development:

```sh
python3 -m pip install -r Tools/requirements.txt
python3 Tools/validate_content.py UnityPackage/Runtime/Data/combat-content.json
python3 Tools/validate_game_data.py
python3 Tools/validate_directional_art.py
python3 Tools/validate_form_art.py
python3 Tools/expand_story_levels.py --check
python3 Tools/validate_scenario_art.py
python3 Tools/validate_expansion_art.py
python3 -m unittest discover -s Tools -p 'test_*.py'
dotnet run --project Tests/RulesKernel.Tests.csproj
dotnet run --project Tests/GameTests/GameTests.csproj
dotnet run --project Tests/ScenarioTests/ScenarioTests.csproj
dotnet run --project Tests/CustomMapTests/CustomMapTests.csproj
dotnet run --project Tests/ExpeditionTests/ExpeditionTests.csproj
dotnet run --project Tests/RankTests/RankTests.csproj
dotnet run --project Tests/JourneyTests/JourneyTests.csproj
dotnet run --project Tests/HomeTests/HomeTests.csproj
dotnet run --project Tests/NeighborhoodTests/NeighborhoodTests.csproj
dotnet run --project Tests/AudienceTests/AudienceTests.csproj
dotnet run --project Tests/SignatureTests/SignatureTests.csproj
dotnet build Tools/Compatibility/Core.Compatibility.csproj
dotnet publish Web/DungeonCrawlerTactics.Web.csproj -c Release -o Web/publish
python3 Tools/prepare_unity_project.py
python3 Tools/prepare_research.py --check
```

New classes and combinations of supported effects can be authored in JSON. New mechanical primitives require an explicit C# effect, validation, forecast support and scenario coverage. Keep presentation and character names out of combat logic.
