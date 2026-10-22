> Historical planning/starter reference. For the implemented playable game, current content and setup, see [PlayableGame.md](PlayableGame.md). The original starter fixture is retained for regression tests.

# Dungeon Crawler Tactics — Game Design

## Product direction

**Dungeon Crawler Tactics** is a single-player Unity 6 Web tactics game and fan adaptation of *Dungeon Crawler Carl*. Lead Carl, Donut, and recruited companions through a lethal televised dungeon. Positioning, explicit enemy intent, and interactions between abilities and tagged terrain create the tactical puzzle. The combat should be approachable to fans of *Final Fantasy Tactics* and *Fire Emblem*: a small party on a square grid, distinct roles, and meaningful choices with readable outcomes.

The initial release is one complete floor with a short camp intermission and three encounters ending in a boss. It is scoped for 10–15 minute fights and short browser sessions. Carl and Donut are core characters; the other recruits can be original dungeon crawlers, with more companion content added later. Keep the data-driven combat usable by a future setting pack, while making the first game clearly a DCC fan adaptation.

## Release scope

### First room and playable milestone

- One authored 10×8 orthogonal grid, no elevation.
- Four deployed crawlers and three enemies; movement, turn controller, basic deterministic enemy AI, one primary objective, win/lose/restart, and an actual Unity HUD.
- A visible oil/fire interaction, wet/lightning and wet/cold reactions, and a freeze/shatter puzzle. The same command sequence must always resolve the same way.
- Mouse and keyboard controls, touch-friendly targets and selection, clear cancel/confirm behavior, combat log, and preview that does not mutate the battle state.
- A 10–15 minute encounter that can be completed without a consumable. Optional sponsor goal rewards a two-step reaction without gating progress.

### First release

The first release target is one complete floor: camp, loadout, three encounters (the third is the boss), reward choice, and return to camp. Budget for **6 classes, 18 active abilities, 8 consumables, 6 enemies and 1 boss**, plus a tutorial, settings, sound, and credits. This is the release scope from the delivery plan. The current starter JSON is a rules proof and contains nine abilities and a single item; it is not the complete first release.

### Later expansion

The other six classes, the broader 12-class / 34-plus-ability catalog, summons, push/pull, elevation, destructible cover, secondary jobs, and additional floors are later content. The larger catalog is a proposal and must be reconciled with supported effect operations before import. Do not treat catalog entries as implemented mechanics. Destructible cover is not part of the initial room or release scope.

## Core loop

1. **Camp:** choose four crawlers from the available roster, select class-granted abilities and carried items, and read the next encounter objective.
2. **Encounter:** inspect board tags, enemy intent, and ability forecast; move and act through deterministic team rounds.
3. **Reward:** earn fixed XP and a clearly described sponsor-choice reward, then save and return to camp.
4. **Complete the floor:** play three encounters, ending with the boss, with camp/loadout checkpoints between them.

### Turn and activation rules

The player and enemy teams alternate rounds. Every living unit may activate once per round. The player chooses the order of allied activations; enemy activations use a stable deterministic order. On an activation, a unit may **move up to its movement budget and then use one action**, or use one action without moving. In the MVP, an action commits and ends that unit's activation; **there is no movement after acting**. A unit may also move and explicitly end activation without acting. Cancellation before commit spends nothing. Once all eligible allies have activated, the enemy team takes its turn; the same rule applies to enemy activations.

Movement is orthogonal on a square grid. Occupied and blocked cells cannot be entered; height, diagonal movement, push/pull, and destructible cover are later additions. Ability target, range, and cost come from content. The MVP kernel models an energy cost, not separate AP/MP; costs and per-activation permissions are distinct design systems and must not be inferred from each other.

### Readability and determinism

- Show legal target, range, cost, outgoing/incoming tags, estimated damage/heal, and known reaction results before commit.
- There is no hit or damage randomness in the MVP. Enemy intent and target selection are explicit; deterministic tie-breaking gives stable outcomes.
- A preview and committed command must use the same resolver. Preview operates on a clone and cannot change live state.
- The rules kernel resolves one selected target per action. Reactions are checked against incoming event tags and the target's persistent tags. Reactions sort by descending priority then ordinal ID, consume tags when scheduled, and fire at most once per rule per action chain. An event budget prevents unbounded chains; a failed chain rolls back.
- The current kernel has no status durations, turn skips, automatic damage over time, tile occupancy hooks, area/spatial chaining, or damage to tile HP. Those behaviors require later systems and must be forecast before any content uses them.

## The authored rules kernel and the full game

The working starter is schema version 1 JSON with registered tags, classes granting ability IDs, abilities with target/range/cost/incoming tags/effects, priority-sorted reactions, and items referencing abilities. Supported effect operations are `Damage`, `Heal`, `AddTag`, and `RemoveTag`. Classes, abilities, and items are data; no behavior should be selected by display name or class ID. The actual seed content and supported reaction outcomes are listed in [ContentCatalog.md](ContentCatalog.md).

This kernel is a focused rules proof, not a complete game. Grid movement, activation budgets, party/recruitment, AI, objectives, effect origins, durations, tile occupancy hooks, presenter/forecast, inventory charges, browser saves, and Unity UI are separate planned integrations in [DeliveryPlan.md](DeliveryPlan.md). Avoid describing these as implemented until they are present and verified. Adding combinations of registered tags and supported operations should be data work. A new effect primitive needs code, validation, forecast support, and an independent scenario test.

## Party and progression

The player deploys four crawlers. The target roster grows to eight; recruit and rotate party members at camp. Carl and Donut are core playable characters. Additional recruits can be original dungeon survivors whose short stories, roles, and bonds add personality without relying on copied prose. Recruitment scenes and dialogue should be original fan adaptation content.

First-release progression is intentionally modest: a unit has one active class and a small ability bar. Class unlocks and ability grants are explicit data. Cross-class jobs and branching skill trees are later. The proposed expanded class list is Brawler, Guardian, Rogue, Ranger, Pyromancer, Cryomancer, Stormcaller, Cleric, Alchemist, Bard, Necromancer, and Beastmaster; the exact first six are detailed in the catalog. Do not imply that every class or ability is available in the seed.

A crawler at zero HP is downed for the encounter; the intended game can offer a revive path and return the crawler wounded to camp if the encounter ends first. No permanent character death in the first release. Retreat or party defeat returns to camp with an explicit retry route and no roster softlock. These are game-loop requirements to implement, not behavior provided by the rules kernel.

The first-release inventory target is eight consumables. Items refer to abilities and should use the shared effect pipeline; item charges, carry limits, restocking, and use permissions belong to the planned inventory/command systems. Keep the initial item economy small enough to explain before a fight.

## Audience, sponsors, and narrative

Optional audience goals should reward expressive play: trigger a reaction, take a risky route, rescue a downed ally, or finish an objective efficiently. Sponsor rewards are shown before the encounter and can be earned once; failure should not require grinding or replay for basic progression. Rewards should be fixed or clearly bounded, with no hidden score requirement.

Use the source setting's televised dungeon and absurd sponsor pressure as tone, with new dialogue and encounter scenarios for this adaptation. Avoid turning audience favor into a repetitive meter. Companion bonds can be short optional scenes or small unlocks in a later content pack; they are not required to prove the first room.

## Sample interaction puzzle

The Service Corridor 13 board has an oil slick, a coolant pipe, a leaking wet enemy, and an exit lock. The player can preview a fire hit on an enemy and fire applied to a tile separately. The current seed's `ability.fire_surface` targets an oil-coated tile: `reaction.oil_ignites` consumes `surface.oil` and adds `surface.burning` to that tile. It does not automatically damage or burn an occupant, spread to neighboring tiles, or deal damage over time. Those spatial and occupancy hooks are future work.

For an enemy-target route, use Douse to add `status.wet`, then Spark to trigger `reaction.wet_conducts` for its fixed bonus damage and `status.shocked` marker, or Frostbite to consume wet and add `status.frozen`. A Brawler's Shatter applies `impact.shatter` and physical damage; the frozen reaction consumes `status.frozen` and adds its fixed bonus damage. Every step has a deterministic forecast. A normal strike and route to the exit remain valid alternatives.

## Web sessions, controls, and saves

Target a Unity 6 Web build with fights designed for 10–15 minutes. Support mouse and keyboard, touch-friendly selection and target buttons, readable text, scalable/high-contrast UI, and color-independent tag icons. Controller support is optional for the first release. Tactical play has no timer; every targeting state supports cancel and confirm. Provide adjustable text size, an animation-speed/reduced-motion option, and a combat log.

Persist roster, loadouts, inventory, encounter completion, and floor progress locally in the browser at camp/checkpoint boundaries. The release should support save export/import and versioned migration. Mid-encounter resume is desirable if reliable on the Web target. Browser storage may be cleared; do not imply cloud sync. Save behavior is a planned integration until verified in the build.

## Success and failure

Each encounter has one primary objective, such as disable the exit lock and extract surviving crawlers. Optional sponsor goals never gate the floor. Winning reports objective completion, downed/revived allies, and rewards. Defeat or retreat gives a clear retry path. The full run must have no dead-end route or softlock, and all required encounters must remain completable without optional consumables.

## Production guardrails

Build the 10×8 room end-to-end, then complete the three encounters including the boss before widening content. Put damage, energy cost, range, rewards, enemy order, and encounter tuning in data wherever supported. Validate every referenced ID and tag. Do not add custom per-class branches for content. Use compact GBA-inspired silhouettes and strong color blocks; target 128×128 source pixels for character art where appropriate, not 128 screen pixels for every tile. Current rules are deliberately small; proposed mechanics must be delivered with their implementation, forecast, and scenario coverage.
