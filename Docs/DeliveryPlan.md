> Historical planning/starter reference. For the implemented playable game, current content and setup, see [PlayableGame.md](PlayableGame.md). The original starter fixture is retained for regression tests.

# Delivery plan — Dungeon Crawler Tactics

Target: Unity 6, Web build, single-player. Working title for a Dungeon Crawler Carl fan adaptation. The first release is one complete floor, not a simulation of every book. The rules and content should also support another setting through a separate narrative pack.

## Product promise

Lead four crawlers through a lethal televised dungeon. Read the room, combine abilities with terrain, rescue your party, and earn an absurd sponsor reward. Every dangerous interaction has an inspectable explanation and a forecast before commitment.

## Milestones and finish lines

These are ordered work packages, not delivery-date promises. Complete and playtest each gate before widening the content catalog.

| Gate | Deliverable | Acceptance test | Assigned role |
|---|---|---|---|
| 0: rules proof — this starter | Readable content, deterministic reaction kernel, tests, clickable screen wireframes, implementation plan | Sample content validates; oil/fire, wet/lightning, frost/shatter outcomes are reproducible; preview does not mutate live state | Sol implementation; coordinator review |
| 1: playable room | One 10×8 board, four crawlers, three enemies, movement, turn controller, basic enemy AI, objective, win/lose/restart, actual Unity HUD | Finish a 10–15 minute encounter in a browser using movement, an item, and two different combos; enemy turn always terminates | Sol gameplay + Sol Unity UI |
| 2: a complete run | Camp → loadout → two encounters → boss → rewards → camp; save/resume | Reload at each checkpoint; continue with identical party, inventory, map, and content version | Sol integration; Luna fixtures and copy |
| 3: maintainable content | Validated import, content browser, class/ability/reaction templates, provenance inspector | Add one class and two abilities using existing operations without changing C#; invalid references block the build with paths | Sol editor; Luna content |
| 4: first release | One floor with 6 classes, 18 active abilities, 8 consumables, 6 enemies and 1 boss, tutorial, settings, sound, credits | Full run completes on supported desktop browsers; save export/import works; no blocked paths or softlocks | Coordinator acceptance + Sol fixes |
| Later | Remaining 6 classes, summons, push/pull, heights, destructible cover, secondary jobs, more floors | Each new primitive brings an independent scenario test and forecast support before content uses it | Sol primitive; Luna content |

The catalog contains additional expansion ideas. Its size is not the release scope. Items, summons, a full roster, movement, durations, AI, UI Toolkit screens and saves are **planned integrations**, unless the root README explicitly lists them as implemented.

## First room: Service Corridor 13

Use a small authored board, orthogonal movement, no elevation. Spawn four allies behind a low barrier and three enemies around a leaking coolant pipe and oil slick. Objective: disable the exit lock and reach the extraction tile with all surviving crawlers. There are two safe routes; no consumable is required to win. An optional sponsor challenge rewards a two-step reaction, never blocks progression.

1. Teach movement and tile inspection with an unthreatened first activation.
2. Place an oil-coated enemy near a clearly outlined spill. Preview fire on the enemy and fire on the tile separately.
3. Introduce wet plus lightning as an alternative route. Initial implementation damages the selected wet target; spreading through connected wet tiles is a later explicit spatial rule.
4. Let the last enemy guard the exit console. Freeze then shatter offers a third solution. A normal physical attack remains viable.
5. Award fixed XP and one sponsor-choice reward. Return to camp, save, and offer replay.

## Small implementation tickets

Each ticket should be reviewable on its own. Dependencies are explicit.

| ID | Task | Depends on | Done when |
|---|---|---|---|
| T01 | Validate content and resolve sample commands | — | Regression suite passes; unknown fields and references fail clearly |
| T02 | Grid state + obstacle-aware flood fill | T01 | Reachable cells and path cost agree; occupied/blocked cells cannot be entered |
| T03 | Team phases + activation budgets | T02 | Each living ally moves at most its budget and takes at most one action; commit ends activation; cancel spends nothing |
| T04 | Effect origins, durations and unit/tile occupancy hooks | T03 | Start/end timing documented; entering fire produces one event; expired buffs remove only their own contribution |
| T05 | Battle presenter + forecast | T03 | Highlight and confirmation reflect the exact submitted command; stale state invalidates a preview |
| T06 | Enemy decision scoring | T04 | Fixed candidates sorted deterministically; fallback Wait; no illegal commands; no endless turn |
| T07 | Party, class unlocks, equipment and item charges | T03 | Owned abilities and item availability checked at command boundary, not only in UI |
| T08 | Mission states and restart | T05, T06 | Victory, defeat, retreat and retry produce explicit states and correct rewards |
| T09 | Versioned saves and browser persistence | T07, T08 | Refresh recovery, migration, corrupted save handling and export/import verified |
| T10 | Floor route + hub + reward choice | T09 | Three encounters form a complete run with no dead-end route |
| T11 | Content inspector + build validation | T01 | Source file and offending field shown; hard errors block build |
| T12 | Browser release verification | T10, T11 | Published-origin smoke test, cache refresh, audio unlock, focus loss and download budget checked |

## Six-agent working model

The coordinator owns the contracts, merges, scope and acceptance decisions. Activate only the specialists needed for the current gate; six agents do not mean six concurrent edits to one system.

| Specialist | Model | Ownership | Boundary |
|---|---|---|---|
| Rules engineer | GPT-6.1 Sol | Core resolver, queries, deterministic tests | No Unity UI references |
| Unity integration engineer | GPT-6.1 Sol | Input, rendering, board, Web build, saves | Submits commands; never duplicates combat calculations |
| UI engineer | GPT-6.1 Sol | Wireframes, UI Toolkit views, interaction tests | Reads view models and forecasts |
| Content designer | GPT-6 Luna | JSON records, ability descriptions, balance fixtures | Uses registered effects; requests new primitives from Sol |
| Encounter designer | GPT-6 Luna | Map records, tutorial beats, enemy loadouts | No special-case code by unit or class ID |
| Verification assistant | GPT-6 Luna | Content lint, scenario matrix, docs and test reports | Reports defects; coordinator assigns code changes |

Every assignment names owned files, inputs, outputs, dependencies, validation command and unsupported cases. Parallelize independent content and UI only after the schema is fixed. One owner changes the schema; others migrate through a reviewed version bump. The coordinator reruns integration checks after combining work.

## Scope controls

- Ship authored encounters first; procedural generation follows a proven encounter vocabulary.
- Ship single-player first. Multiplayer, full mod scripting, freeform formulas and a custom ECS are outside this plan.
- Use four deployed characters, eight roster slots, one active class and a small active-ability bar. Secondary jobs are a later gate.
- Start with deterministic damage and explicit enemy intentions. Add hit/crit RNG only with seeded preview semantics and tests.
- Budget initial release content before producing full animation sets. A class is finished when its role works across the whole floor, not when its portrait exists.

## Release acceptance

An unfamiliar player can identify turn ownership, move, forecast, cancel, confirm, use a potion, inspect a reaction, win, lose, restart and resume without developer help. A content author can add an ability composed of supported operations and see validation failures before playing. The same command sequence and content version produce the same battle state. No successful build alone counts as a completed gameplay milestone.
