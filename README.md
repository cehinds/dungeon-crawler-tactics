# Dungeon Crawler Tactics

A small complete Dungeon Crawler Carl fan tactics game: an animated isometric dungeon, four deployed characters, personal ability kits, three encounters ending in a boss, environmental reactions, shared consumables and sponsor rewards.

**Play online:** [Dungeon Crawler Tactics](https://cehinds.github.io/dungeon-crawler-tactics/).

**Build rooms:** [Room workshop](https://cehinds.github.io/dungeon-crawler-tactics/room-kit.html) · [Download 25 layerable PNGs](https://cehinds.github.io/dungeon-crawler-tactics/assets/room-kit/room-kit.zip). Seeded previews export room recipes; campaign maps remain authored. See [Room kit guide](Docs/RoomKit.md) for anchors, layers and Unity import settings.

**Play locally:** run `./play.sh` on macOS/Linux, or `Play-Windows.bat` on Windows, then open **http://localhost:8000**. Python 3 is required for the local static server. The download archive includes the published game; a source checkout needs the `dotnet publish` command below first.

**Unity:** open `UnityProject/` in Unity 6, choose **Dungeon Crawler → Create Playable Scene**, then press Play. Choose **Build Web Player** from the same menu to export using your installed Unity Web Build Support module.

The included playable browser build runs the actual shared C# game through .NET WebAssembly. It is not a Unity Web export. The full Unity source and scene/build tooling are included, but a Unity Editor was unavailable here for Play Mode or Unity Web export verification.

## What you can play

- Start with Carl, Princess Donut, Katia and Mongo; Mordecai advises from camp. Select four of eight field characters and customize optional classes while retaining personal abilities.
- Explore three fog-covered corridor maps, discover optional supply caches and notes, and choose when to enter each encounter.
- Move on three authored 10×8 boards, use class abilities or shared items, inspect the exact forecast, confirm or cancel.
- Watch actual walk/attack/hit sprite frames and visual reactions on the map. Inspect HP, Mana/MP, movement, conditions, range and exact forecasts in a compact HUD.
- Choose actions in a responsive modal with labeled category colors, Mana costs and legal-target counts. Review the exact forecast in its confirmation modal; end-turn confirmation names the next actor.
- End the current character's turn to select the next ready ally; enemies act after the whole party finishes. Pan/zoom the map on phones.
- Combine oil/fire, water/wet/lightning, cold/frozen/shatter; use terrain while avoiding hazard damage. Guardian, Bard and Necromancer support abilities now grant real single-hit protection.
- Fight deterministic enemies, collect sponsor supplies, reach the boss, finish the floor, or retry after defeat.
- Autosave, reload, and export/import a portable JSON save.

There are **16 selectable class kits, 46 ability definitions, 8 consumables and six new art atlases and a dedicated winged-Mongo portrait**, plus the earlier reserve-character textures. Classes are unlocked at camp; XP is a progress score. Advanced summons, equipment progression, area chains, elevation, procedural levels and audio are outside this compact release. The animated browser presentation uses the shared C# engine; Unity's presenter remains the earlier IMGUI implementation.

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
python3 -m unittest discover -s Tools -p 'test_*.py'
dotnet run --project Tests/RulesKernel.Tests.csproj
dotnet run --project Tests/GameTests/GameTests.csproj
dotnet build Tools/Compatibility/Core.Compatibility.csproj
dotnet publish Web/DungeonCrawlerTactics.Web.csproj -c Release -o Web/publish
python3 Tools/prepare_unity_project.py
```

New classes and combinations of supported effects can be authored in JSON. New mechanical primitives require an explicit C# effect, validation, forecast support and scenario coverage. Keep presentation and character names out of combat logic.
