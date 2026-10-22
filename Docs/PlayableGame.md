# Playable game — current implementation

This document supersedes the earlier planning and starter-kit descriptions. The current source implements a small complete floor: choose a four-person party, explore three authored corridor sectors, play three tactical encounters ending in a boss, collect sponsor supplies, and finish or restart the run.

## Two presentations, one game

- **Unity:** a complete source project under `UnityProject/`, generated from the canonical `UnityPackage/` source. Its runtime presenter uses Unity IMGUI and original pixel textures. An Editor command creates the actual scene and another builds a Unity Web player. The source was compiled against Unity runtime reference assemblies; no Unity Editor was available to run Play Mode or export a Unity build here.
- **Playable browser delivery:** `Web/publish/wwwroot/` contains a real compiled .NET WebAssembly game. Its browser presentation calls the same C# `GameSession` and `RulesEngine`. It is an executable game, not a wireframe, and it is **not a Unity Web export**. No duplicate JavaScript combat rules exist.

## Play locally

The archive includes the published browser files. Install Python 3 if needed, then run `./play.sh` on macOS/Linux or `Play-Windows.bat` on Windows. Open `http://localhost:8000`. Alternatively run `python3 Tools/serve_game.py`. Keep the terminal open while playing. Static WebAssembly files require HTTP, so opening `index.html` directly is not supported.

To rebuild the browser game after source changes, install .NET 8 SDK and run:

```sh
dotnet publish Web/DungeonCrawlerTactics.Web.csproj -c Release -o Web/publish
```

Initial browser download includes an untrimmed .NET runtime. It favors reproducible builds and debugging over a minimal download. Production compression and trimming are optimization work, not prerequisites for this local release.

## Play in Unity

1. Open `UnityProject/` in Unity Hub with Unity 6. The generated version file names 6000.0.23f1; use an installed Unity 6 LTS patch and let Unity update its local settings if needed.
2. Let Unity import source, data and textures. Open **Dungeon Crawler → Create Playable Scene**. It creates and wires a real scene using Editor APIs. If the scene already exists, it opens it.
3. Press Play. Choose your party and enter the encounter.
4. To export Unity Web, install matching Web Build Support, then use **Dungeon Crawler → Build Web Player**. Select an output folder and serve the resulting build over HTTP with Unity's required compression headers.

The Editor build hook validates the content before building. `UnityPackage` is the editable source of truth; after changes run `python3 Tools/prepare_unity_project.py` to refresh managed files in `UnityProject/Assets/DungeonCrawlerTactics`. Existing scenes, metadata and project settings are preserved. Do not independently edit the generated source copy and the canonical source.

## Controls and rules

- At camp, select a crawler, choose a class, and deploy exactly four of the eight roster members. All classes are available immediately in this compact version.
- Leaving camp enters exploration. Click a reachable corridor tile or use arrow keys to move the party and reveal fog. Approach a supply cache or note and interact; each cache can be claimed once. The encounter door starts combat only when you choose to enter it. Returning to camp preserves discoveries.
- In battle, select a living crawler. Highlighted cells are reachable. Click a cell to move once, up to that class's movement allowance. Walls and living occupants block paths. Movement uses a stable shortest path; crossing hazards hurts on every affected step.
- The browser battle view keeps the board, compact party strip and action dock in one viewport. Inventory and log are optional panels; forecasts keep confirm/cancel beside the map.
- Select an ability or consumable, then its legal unit or tile target. Legal targets come from the shared C# resolver; the UI shows effects, range, energy and reasons an action is unavailable. Review HP, energy and tag changes before confirming. Cancel spends nothing. Terrain abilities can target the tile beneath a unit.
- An action ends that crawler's activation. Moving without acting remains allowed; Wait ends the activation. The enemy team acts after all crawlers finish, or when End party turn is chosen.
- Enemy actions are deterministic, including movement and target choice. They use the same range, energy and effect checks as player commands. Enemy turns complete without relying on animation timing.
- Defeat every hostile to win. Choose one sponsor reward and continue. Camp restores the party; consumables carry forward. Three victories finish the floor.
- Defeat offers a fresh attempt at the same room, with restored starting supplies, while preserving earned XP. New run resets progression.
- XP records floor progress; level-up trees, equipment progression, summoning, elevation and procedural floors are not implemented in this version.

## Actual content

Eight roster members, four deployed, twelve selectable class kits, 36 ability definitions (including consumable actions), eight consumables, three authored 10×8 maps, and fifteen original 128×128 sprite assets. These are a compact fan adaptation, with class assignments and encounters invented for the game. See `PlayableContent.md` for the actual generated catalog.

Carl favors melee finishing, Donut starts as a Stormcaller, Katia supplies fire, and Mordecai begins with healing. Roster and class choices can be changed at camp. Every class has multiple usable actions, but names such as Beastmaster and Necromancer do not imply an unimplemented summon system.

## Reactions and hazards

The core catalog controls incoming/target tag queries, rule priority, tag consumption, emitted tags and effect lists. The game config adds explicit contact mappings, damage and durations.

- Oil tile + Ignite Surface consumes oil and creates burning terrain. A newly created burning surface damages its occupant once. Entering burning tiles hurts; standing in fire hurts again at round end.
- Water tiles explicitly apply `status.wet` through `occupantTag`. Surface tags are not automatically copied onto creatures.
- Lightning against wet consumes wet and deals reaction damage; cold against wet creates frozen. Shatter consumes frozen for bonus damage.
- Guarded from Bulwark Recovery, Rallying Song or Siphon Ward prevents up to 6 damage from the next physical/fire/cold/lightning event, then is consumed. Unused Guarded expires after two full rounds. It prevents damage before HP loss and can prevent a lethal hit; it does not protect against untagged attacks or terrain hazards.
- Frozen reduces movement according to `tagRules`; shocked reduces energy recovery. Effects expire at the full-round boundary. The forecast describes immediate command results; the help and tag rules describe later hazard ticks.
- Reactions remain single-target within one action. Fire does not spread across the map and lightning does not jump between neighboring units in this version.

Timed tags have a recorded origin and remaining full rounds. Current stacking policy is one active timed instance per entity/tag, without accumulating strength. Boolean tags and source metadata are distinct. Multiple independent overlapping buff sources are outside this compact model.

## Saves

The browser client autosaves committed state in localStorage and supports downloadable/importable JSON. The Unity client uses PlayerPrefs checkpoints with a prior backup; its WebGL bridge provides browser file download/upload plus text fallback. Storage belongs to the current browser/origin and is not cloud sync.

Saves contain exploration position, revealed cells and claimed discoveries as well as roster, inventory, positions, HP/energy, activation state, tile tags, timed effects, encounter progress and reward state. Preview is temporary and is not committed into a save. Import validates versions, IDs, occupancy, authored walls and status bookkeeping before replacing live state. Invalid import leaves the current run intact. Existing v1 checkpoints without exploration fields remain supported; existing battles resume normally and exploration becomes available at the next camp. Unknown content versions are rejected.

## Update the game

Edit `UnityPackage/Runtime/Data/combat-content.json` for classes, abilities, tags, reactions and item links. Edit `game-content.json` for roster, stats, inventory, maps, enemies, rewards and tag rules. Stable IDs connect the two files. Run:

```sh
python3 Tools/validate_content.py UnityPackage/Runtime/Data/combat-content.json
python3 Tools/validate_game_data.py
dotnet run --project Tests/RulesKernel.Tests.csproj
dotnet run --project Tests/GameTests/GameTests.csproj
python3 Tools/prepare_unity_project.py
```

New classes grant existing ability IDs and need one matching stats record. New abilities combine the supported `Damage`, `Heal`, `AddTag`, and `RemoveTag` operations, with explicit target/range/cost. New reactions combine registered tag queries with those operations. New items reference an existing ability and need a starting supply or reward source. Effects with fundamentally new behavior require a typed C# extension and tests.

Strict schemas in `Tools/` catch misspelled keys and bad references. Runtime validators also guard loaded content and saves. Unity's JsonUtility does not itself reject unknown fields, so run strict authoring validation before importing content.

## Code ownership

`Content.cs` owns mechanical records/catalog validation. `RulesEngine.cs` resolves a single command and its bounded reaction chain. `GameData.cs` declares configuration, view and save DTOs. `GameDataValidator.cs` checks campaign integrity. `GameSession.cs` owns the playable loop, movement, inventory, AI, timed tags and saves. `GameSession.Exploration.cs` owns fog discovery, exploration pathfinding, interactions and save validation. `PlayableGame.*.cs` presents these results in Unity. `Web/Program.cs` exposes the same core to the browser, while `Web/wwwroot/` handles UI and local storage only.

## Known limits

This is a small complete game, not a full series adaptation. There are no area chains, line-of-sight/elevation rules, procedural maps, online play, animated combat sequences or audio soundtrack. Unity's presenter scales a desktop reference layout; touch menus are usable, but mobile Unity Web support has not been established. Only the shared-C# browser build has been exercised as an actual browser application here. The Unity Editor integration and Web export must be verified on a machine with Unity installed.
