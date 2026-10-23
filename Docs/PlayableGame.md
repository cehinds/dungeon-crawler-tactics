# Playable game — current implementation

This document supersedes the earlier planning and starter-kit descriptions. The current source contains the original three-encounter campaign plus a separate eight-floor story route, six training expeditions and three boss scenarios. The story adds class/stat selection on floor 3, progression through level 50, ranks through 20 where eligible, and gold-funded personal housing. See [the current journey and housing guide](Journey-and-Home.md) for controls, formulas and adaptation boundaries.

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

- At camp, deploy four of eight field characters. Mordecai is a ninth, nondeployable advisor. Carl, Donut, Katia and Mongo are the default party. Their personal abilities remain available when changing the optional class loadout.
- Leaving camp enters exploration. Click a reachable corridor tile or use arrow keys to move the party and reveal fog. Approach a supply cache or note and interact; each cache can be claimed once. The encounter door starts combat only when you choose to enter it. Returning to camp preserves discoveries.
- In battle, select a living crawler. Highlighted cells are reachable. Click a cell to move once, up to that class's movement allowance. Walls and living occupants block paths. Movement uses a stable shortest path; crossing hazards hurts on every affected step.
- The browser draws an isometric map with generated tile, prop, character, enemy, portrait, icon and effect atlases. The retained canvas plays walking, attack, hit, projectile and reaction events from the shared resolver. Drag to pan; use the zoom and Center controls on small screens. The compact HUD shows HP, Mana/MP, effective movement, conditions and the selected action's cost/range.
- The Actions button opens a responsive ability/item chooser with costs, ranges, legal-target counts and unavailable reasons. Selecting a legal target opens the exact forecast confirmation dialog. End character turn opens a dialog naming the next ready ally or enemy phase. Category colors and explicit labels distinguish physical, fire, arcane, healing and item actions. Help, supplies and saves also use responsive dialogs. Escape cancels targeting without spending resources. The party strip shows who is ready or finished; End character turn advances to the next ready party member, and enemies act only after all living party members finish. Confirming an ability spends its action but preserves an unused move; explicitly end the character's turn to advance.
- Dismissible toasts confirm class changes, discovered supplies, committed actions and save operations. Warnings and errors have distinct styling and accessible announcements. Up to three notifications appear at once, duplicates are combined, and hovering or focusing a notification pauses its expiry. Routine movement and autosaves stay quiet.
- Select an ability or consumable, then its legal unit or tile target. Legal targets come from the shared C# resolver; the UI shows effects, range, mana costs and reasons an action is unavailable. Review HP, MP and tag changes before confirming. Cancel spends nothing. Terrain abilities can target the tile beneath a unit.
- One move and one action may be used in either order. Confirming an ability or item spends the action; it leaves an unused move available. End character turn marks the current activation finished. The enemy team acts after all living party members finish.
- The character sheet exposes three data-driven stances and four Katia shapes. Shapeshift opens the form chooser. A mode change uses the action and previews HP/Mana caps, movement and Guarded. Caps do not restore resources; saves retain choices. These are tactical adaptations.
- Persistent selected-ability details and a full details dialog explain cost, range, target and effects on touch or keyboard. Narration follows each committed presentation event during playback, including individual enemy movement/actions and impacts, with history and five once-per-run achievement IDs.
- Enemy actions are deterministic, including movement and target choice. They use the same range, MP and effect checks as player commands. Enemy turns complete without relying on animation timing.
- Defeat every hostile to win. Choose one sponsor reward and continue. Use the safe-room Rest station to restore the party; consumables carry forward. Three victories finish the floor.
- Defeat offers a fresh attempt at the same room, with restored starting supplies, while preserving earned XP. New run resets progression.
- Shared party XP grants levels 1–4 at cumulative thresholds 0, 30, 70 and 120, including reserves. Each level increases maximum HP and Mana; each character gains personal skills at levels 2 and 3. Six equipment pieces alter actual stats or grant abilities. Manage loadouts, inspect skills and rest at safe-room stations. The quest journal tracks discoveries, doors and encounter objectives. See [Progression.md](Progression.md).
- Use safe-room development to preview, confirm or cancel five-stat allocation. Each earned party level grants each field crawler three points; existing automatic growth remains. Committed non-item abilities train individual practice tracks at 3 and 8 uses. Craft two fixed recipes and open earned achievement/victory boxes at camp. These early unlocks and numeric benefits are accelerated adaptation rules; see [Progression.md](Progression.md).
- Safe-room scenario choices open separate Hoarder, Juicer and Ball of Swine battles with briefings and visible objectives. Their checkpoint preserves the campaign; returning restores it. Scenario rules and numbers are adaptations, and bosses still occupy one logical tile.
- Rotate left/right through four map views. Pointer picking and screen-relative arrow/WASD movement follow the rotated projection. Movement previews show the grid path; enemies navigate by walkable distance around walls and visibly play their movement before player controls unlock.

## Room authoring kit

Open `room-kit.html` or use Save & options → Room kit. The workshop assembles rooms from 25 separate transparent PNGs, supports manual painting/erasing, piece/camera rotation, layer toggles, validated recipe import/export and individual/ZIP downloads. **Play this room** transfers a playable map directly into a standalone battle. Save & options also imports exported playable JSON maps.

Runtime maps are limited to 6–20 columns and 6–16 rows. The shared core validates tile tags, bounded object counts, known assets, layers, rotations, blocking, unique legal actor spawns and connected walkable paths before replacing the current run. If spawn/enemy records are omitted, deterministic defaults supply four party starts and three enemies. An invalid import leaves the current run intact. A valid import starts a new standalone room: export the current campaign save first to preserve it. Saved custom games retain the map, components, rotations and current combat state; New run clears the custom override.

The game and workshop share a 128×64 logical diamond grid and measured PNG anchors. Floors/surfaces render below units, while fire and combat feedback render above them. This is a placement convention, not a guarantee that every decorative silhouette perfectly fills a tile or that large boss sprites occupy multiple cells. PNGs and the manifest are included under Unity `Resources/RoomKit`; see [RoomKit.md](RoomKit.md). Runtime workshop import and its browser presentation do not establish native Unity editor parity.

## Actual content

Eight deployable roster members plus Mordecai as advisor, four deployed, twenty selectable class kits, 66 ability definitions (including consumable actions), eight consumables, six equipment pieces and three authored 10×8 maps. All eight field characters have four directional idle/walking views: 96 distinct frames in normalized atlases. Earlier character action, enemy, effect, terrain and icon atlases remain in use. Enemy art has walking and attack poses but not four authored directional sets. See `PlayableContent.md` for the generated catalog.

Carl's Compensated Anarchist kit has Powerful Strike with knockback and a single-tile incendiary bomb. Donut's Former Child Actor kit has Magic Missile, Puddle Jumper and Heal Critter. Katia's Doppelganger kit has Shapeshift protection, Heavy Blow and New Look cleansing. Mongo is a raptor companion with Bite and Pounce. Exact costs/ranges and conversions are game adaptations; see `Revamp-Research.md` for book sources. Names such as Beastmaster and Necromancer do not imply a summon system.

## Reactions and hazards

The core catalog controls incoming/target tag queries, rule priority, tag consumption, emitted tags and effect lists. The game config adds explicit contact mappings, damage and durations.

- Oil tile + Ignite Surface consumes oil and creates burning terrain. A newly created burning surface damages its occupant once. Entering burning tiles hurts; standing in fire hurts again at round end.
- Water tiles explicitly apply `status.wet` through `occupantTag`. Surface tags are not automatically copied onto creatures.
- Lightning against wet consumes wet and deals reaction damage; cold against wet creates frozen. Shatter consumes frozen for bonus damage.
- Guarded from Bulwark Recovery, Rallying Song or Siphon Ward prevents up to 6 damage from the next physical/fire/cold/lightning event, then is consumed. Unused Guarded expires after two full rounds. It prevents damage before HP loss and can prevent a lethal hit; it does not protect against untagged attacks or terrain hazards.
- Frozen reduces movement according to `tagRules`; shocked reduces MP recovery. Effects expire at the full-round boundary. The forecast describes immediate command results; the help and tag rules describe later hazard ticks.
- Reactions remain single-target within one action. Fire does not spread across the map and lightning does not jump between neighboring units in this version.

Timed tags have a recorded origin and remaining full rounds. Current stacking policy is one active timed instance per entity/tag, without accumulating strength. Boolean tags and source metadata are distinct. Multiple independent overlapping buff sources are outside this compact model.

## Saves

The browser client autosaves committed state in localStorage and supports downloadable/importable JSON. The Unity client uses PlayerPrefs checkpoints with a prior backup; its WebGL bridge provides browser file download/upload plus text fallback. Storage belongs to the current browser/origin and is not cloud sync.

Saves contain exploration position, revealed cells and claimed discoveries as well as XP, equipped gear, allocated stats, per-ability practice, owned/opened loot boxes, roster, inventory, positions, HP/MP, activation state, tile tags, timed effects, encounter progress and reward state. Custom-room saves retain visual map components; scenario saves retain their isolated campaign checkpoint and scenario state. Preview is temporary and is not committed into a save. Import validates versions, IDs, occupancy, authored walls and status bookkeeping before replacing live state. Invalid import leaves the current run intact. Existing v1 checkpoints without exploration fields remain supported; existing battles resume normally and exploration becomes available at the next camp. Content versions 1 and 2 upgrade to the current progression model while preserving XP. Missing development records initialize empty while earned levels provide their unspent points; old HP/Mana caps are not reinterpreted as base stats. Unknown content versions are rejected.

## Update the game

Edit `UnityPackage/Runtime/Data/combat-content.json` for classes, abilities, tags, reactions and item links. Edit `game-content.json` for roster, stats, inventory, maps, enemies, rewards and tag rules. Stable IDs connect the two files. Run:

```sh
python3 Tools/validate_content.py UnityPackage/Runtime/Data/combat-content.json
python3 Tools/validate_game_data.py
dotnet run --project Tests/RulesKernel.Tests.csproj
dotnet run --project Tests/GameTests/GameTests.csproj
python3 Tools/prepare_unity_project.py
```

New classes grant existing ability IDs and need one matching stats record. New abilities combine `Damage`, `Heal`, `AddTag`, `RemoveTag`, `Push` and `Teleport` with explicit target/range/cost. Push checks walls, occupants and terrain along its path; Teleport checks the destination. New reactions combine registered tag queries with those operations. New items reference an existing ability and need a starting supply or reward source. Effects with fundamentally new behavior require a typed C# extension and tests.

Strict schemas in `Tools/` catch misspelled keys and bad references. Runtime validators also guard loaded content and saves. Unity's JsonUtility does not itself reject unknown fields, so run strict authoring validation before importing content.

## Code ownership

`Content.cs` owns mechanical records/catalog validation. `RulesEngine.cs` resolves a single command and its bounded reaction chain. `GameData.cs` declares configuration, view and save DTOs. `GameDataValidator.cs` checks campaign integrity. `GameSession.cs` owns the playable loop, movement, inventory, AI, timed tags and saves. `GameSession.Progression.cs` owns levels, effective stats, equipment, safe-room commands, quest views and progression save upgrades. `GameSession.Exploration.cs` owns fog discovery, exploration pathfinding, interactions and save validation. `GameSession.Development.cs` owns allocation, practice, crafting and box ownership; the custom-map and scenario partials own their bounded import/state flows. `PlayableGame.*.cs` presents these results in Unity. `Web/Program.cs` exposes the same core to the browser, while `Web/wwwroot/` handles UI and local storage only.

## Known limits

This is a small complete game, not a full series adaptation. There are no universal area chains, line-of-sight/elevation rules, procedural campaigns, race milestone choices, physical mass-based forms, separate companion progression, online play or audio soundtrack. Scenario lanes are specific authored mechanics; they do not imply a general area-effect engine. The new isometric animated presentation is browser-specific; Unity still uses the earlier IMGUI presenter with the updated shared rules, data and Mana labels. Mobile Unity Web support has not been established. Only the shared-C# browser build has been exercised as an actual browser application here. Unity Editor integration and Web export must be verified on a machine with Unity installed.
