> Historical planning/starter reference. For the implemented playable game, current content and setup, see [PlayableGame.md](PlayableGame.md). The original starter fixture is retained for regression tests.

# Starter architecture: Unity 6 Web

This is a new, standalone rules prototype, not a complete Unity project or a finished combat game. Copy `UnityPackage` into the `Assets/DungeonCrawlerTactics` folder of a Unity 6 project. Unity generates asset metadata on import. No package installation, scene YAML, settings changes, or external runtime dependencies are required.

## What is executable

`Runtime/Core/Content.cs` defines serializable content records and a fail-fast `Catalog`. `RulesEngine.cs` handles class ability grants, living actor/target checks, team targeting, Manhattan range, energy costs, damage/healing, tag mutations, immunity, and bounded reaction chains. Both files use conservative C# and APIs available to .NET Standard 2.1; the core assembly explicitly has no Unity engine references.

`Runtime/Data/starter-content.json` is the single authored source for class grants, abilities, item-to-ability references, tags, and reaction definitions. It contains twelve named class seeds and nine abilities. Most class kits deliberately grant only Strike until their unique mechanics are implemented. The JSON is content, not scripting: four operations are permitted (`Damage`, `Heal`, `AddTag`, `RemoveTag`).

`Runtime/Unity/RulesDemo.cs` loads a serialized `TextAsset` with `JsonUtility`, previews Ignite Surface against oil, commits the same command, and prints the outcome. Create an empty GameObject, add `RulesDemo`, assign `starter-content.json`, and enter Play Mode. Expected result: burning tile, oil removed, hero energy 8. This adapter is a console demonstration; it does not render a tactical board.

## State ownership and integration

The battle controller owns one `BattleState`. Each `EntityState` is either a unit or a tile. Units carry a class ID, team, position, HP, max HP, energy, tag set, and immunity tag set. Tiles carry coordinates and their own tags. Commands name actor, ability, and target IDs. A successful `Execute` returns a new state; commit by replacing the controller's state with `result.State`. The input is never changed, including on invalid commands or queue overflow. `Preview` uses the identical transition function and returns a disposable copy, so highlights and damage forecasts can use the future combat result directly.

Treat loaded content/catalogs as immutable during a battle. Public DTO fields exist for Unity serialization, and public runtime fields keep this starter small; application code should route gameplay changes through commands. A production layer can expose read-only state views after the surrounding turn controller is designed. Do not mutate state while previewing or executing it. This starter is single-threaded and has no global singletons or event subscriptions.

A unit's `ClassId` currently grants its complete ability list. Items are validated catalog references only: no inventory, equipment permissions, charges, or item-use command is implemented. Tile and unit tags are distinct; standing on oil does not automatically copy oil onto a unit. Surface propagation and unit occupancy effects require explicit future rules. There is no inferred area effect.

## Human-readable content extension

To add an ability, append its definition, use registered tag IDs, and add its ID to a class's `abilityIds`. To add a class, append a class record and its grants. To add a reactive interaction, append a reaction with explicit tag queries and effects; see [TagRules.md](TagRules.md). Labels are presentation text, IDs are stable references. Abilities have one target kind: `self`, `ally` (includes self), `enemy`, or `tile`. Each resolves exactly one entity. `range` is inclusive Manhattan distance; `cost` is energy paid once for a valid cast, including an immune target. A self ability must still satisfy range, so range 0 is conventional.

Root `schemaVersion` must be 1. The validator rejects duplicate IDs within each record type, malformed namespaced IDs, unknown referenced tags/abilities, null required arrays, unknown operations or targets, and negative numeric configuration. Arrays and query fields should be explicit in authored JSON. `Catalog` validates known DTO values and references after loading; `JsonUtility` ignores unknown JSON keys and can supply defaults for omitted fields. Run the separate strict JSON authoring validator/schema before importing content to catch typos, unknown keys, and missing required fields that the runtime deserializer cannot detect. Damage/heal clamp HP to [0, max HP]. Dead targets cannot be selected, but already queued effects finish resolving; there is no death trigger system. Healing does not revive, including when an earlier effect in the same chain reduced HP to zero. No random source or wall-clock time affects resolution.

The kernel schema deliberately does not promise arbitrary user code in data. Add a new typed operation to the core, validator, tests, and schema documentation when the design truly needs one. Do not put class behavior in a growing class-inheritance tree.

## Unity Web constraints

The adapter reads an Inspector-assigned `TextAsset`; runtime code has no filesystem APIs, dynamic code generation, network requirement, worker-thread requirement, or reflection-based registration. Unity's serializable public fields and arrays are compatible with `JsonUtility` and IL2CPP stripping rules. Build through Unity 6's Web build profile after importing and compiling. Browser storage, remote content downloads, Addressables, persistent saves, touch controls, audio activation, deployment headers, memory budget, and Web build size are future integration work. The console harness uses .NET JSON/filesystem APIs only outside the Unity package.

## Verification

`Tests/RulesKernel.Tests.csproj` is a dependency-free .NET 8 console harness linking the actual core files and copying the canonical JSON fixture. Run `dotnet run --project Tests/RulesKernel.Tests.csproj` from the starter directory. It covers preview parity, state isolation, oil ignition, wet conduction, immunity, freeze/shatter, range/resources/targeting/class permission, heal clamping, tag query semantics, invalid data, cycle prevention, queue budget rollback, deterministic tag consumption, data-only class/ability/reaction extension, multi-rule event chains, dead-target rejection, clone collection isolation, maximum-value HP clamping, separate priority ordering, and non-retroactive matching. This validates plain C# behavior; Unity import, `JsonUtility` parsing, Play Mode, and an actual browser Web build must also be checked in Unity before delivery to players.

## Deliberately deferred systems

The next thin playable slice needs a turn/action economy, board movement/pathfinding and occupancy, camera/input selection, UI integration with previews, enemy AI, mission win/loss, and a real Unity scene. Later work includes FFT-style initiative/elevation/line of sight, Fire Emblem-style follow-ups/counters, area targeting, equipment and inventory execution, class unlocks and progression, cooldowns, timed statuses, periodic damage, party saves/recruitment, AI personality, map authoring, procedural content, animations/VFX/audio, accessibility, multiplayer, and balance. None of these is silently simulated by tags in this kernel.
