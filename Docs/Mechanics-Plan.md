# Mechanics implementation plan

The aim is a readable tactics game built around the books' improvisation, character identities and cruel game-show framing. The [feature checklist](Book-Fidelity-Checklist.md) separates implemented browser behavior from future work. [Lore review](Lore-Mechanics-Review.md) identifies primary versus secondary evidence. The [concept gallery](../Web/wwwroot/mechanics-review.html) is a visual target, not an implementation specification.

## Current changes

One move and one action are independent allowances. Either order is legal; using an ability does not finish the crawler. End Turn marks that crawler finished, chooses the next unfinished ally, then runs the enemy team after everyone finishes. A finished crawler cannot act or move. Existing saves migrate their previous activation semantics. Selecting an ability exposes its description and targeting rules immediately; selecting Shapeshift opens Katia's forms.

Three stances and four Katia forms are authored in `game-content.json`. Each shows a reversible stat package and a shared-core forecast. Changing stance/form costs the action, not the remaining movement. Increased caps do not heal or refill Mana; lowering a cap clamps the current resource. Defensive and Bulwark choices grant the existing Guarded protection for immediate usefulness. These presets are adaptations, not canonical form names or an implemented simulation of conserved mass. New form-specific sprite sets remain planned.

The character sheet covers each roster member's stats, XP, skills, gear and tactical choices. The narrator consumes committed presentation events, announces actors/actions/targets and impacts, and offers a history dialog. Achievement IDs live in the save and fire only on earned commits. Five initial milestones cover moving, reacting, shapechanging, first victory and first level. The first-move and first-form achievements now also grant owned deterministic boxes. An audience-currency economy remains planned.

The map and workshop use a shared 128×64 logical diamond footprint and measured PNG anchors. Ground surfaces stay below characters; fire/projectiles/hit effects/text render after units and walls. Piece orientation and camera orientation are distinct. The workshop supports painting, erasing, four views, recipe import/export and a game-compatible tile export. The workshop can now send a validated playable room to the game, preserving visual placements. It replaces the active run with a standalone room rather than inserting a new campaign chapter.

## Crawler development milestone

Five saved allocation tracks now affect direct ability damage/healing, HP/Mana caps and movement. Each party level grants every field crawler three points. Safe-room allocation previews compare actual values; confirm spends points and cancel spends none. Existing automatic level growth and checkpoint XP are retained. This is explicitly an accelerated mixed-timeline mode: chronological race/class selection and the later book unlock remain future work.

Committed non-item abilities train an individual crawler/ability track at use thresholds 0, 3 and 8. The three ranks modify direct damage/healing and Mana costs through the same resolver used by preview. Items and reactions do not receive practice bonuses. Safe-room recipes validate and consume inputs atomically. Earned achievement/victory boxes retain ownership and opened state and expose fixed contents. [Progression](Progression.md) documents exact adaptation formulas and recipes.

Remaining development work includes chronological race/class prerequisites, guild or other training sources, broader skill caps/modifiers, a separate companion progression system, and a physical equipped-mass/momentum model for Katia. Form silhouettes and carried platforms must wait for supported rules and matching art; the existing stat presets do not simulate them.

## Boss scenarios, in build order

All three now have separate playable adaptations selectable from the safe room. They preserve a campaign checkpoint and return to it afterwards; they do not replace the main three-encounter floor. Original concept art remains illustrative rather than a screenshot or exact specification. Scenario costs, damage, turn budgets and interactions are invented game rules. Multi-cell boss occupancy remains planned.

### Hoarder — stockpile scenario

Source anchor: garbage stockpile, giant human-ish boss and Scatterers. The playable adaptation has three authored Scatterer slots with at most two active at once, visible emergence warnings and destructible garbage lanes. Clear a lane from beside it by spending an action. Burning, Frozen and Shocked interrupt the special emergence behavior; the boss can still swipe nearby crawlers. Ordinary attacks remain a viable victory route. Capped authored minions and one-tile occupancy are implemented; general spawn placement, large footprints and a universal phase engine remain future work.

### Juicer — gym scenario

Source anchor: scaly gym boss hurling flaming metal weight plates. The playable adaptation locks a cardinal throw lane before execution; moving out of the shown lane avoids it. Frozen or Shocked interrupts the throw. Spend an action beside a bench to topple it into cover: it intercepts one throw and is destroyed. Scenario throws target player crawlers rather than friendly enemies. The warning comes from the same C# scenario intent used to execute damage. This authored lane mechanic is not a universal area-effect or line-of-sight system.

### Ball of Swine — Speedbump scenario

Source anchor: rolling borough threat and Meadow Lark's Speedbump engineering. The playable adaptation follows an eight-cell route and warns about the next three rolled cells. Crawlers use actions to collect reusable parts, carry them and build a three-part barrier. A completed barrier stops a roll and damages the boss, with limited barrier durability. Incomplete defenses can break and lose a helper; a reusable part source and rally interaction provide recovery. Helpers add progress/repair on alternating turns. Ordinary attacks also work. The boss still occupies one logical tile; a rolling multi-cell footprint, carried-unit platforms and a general construction simulation remain planned.

## Exploration and rewards

The main floor already has fogged corridors, encounter doors, optional supply caches and lore notes. Owned loot boxes and two atomic safe-room recipes are now playable. Broader typed environmental puzzles—levers, destructible supports, specialized workbenches and exits—remain planned beyond the scenario-specific objects below. A future floor countdown must pause in menus or use explicit turns; the current campaign has no real-time collapse clock. Pet growth remains separate future work.

## Data and code boundaries

Keep the rules in the shared C# project. JSON authors classes, abilities, forms, stances, items, tag reactions, encounters and rewards. Stable IDs are never inferred from display names. UI reads views and issues commands; it does not calculate damage or bonuses.

`ScenarioDef`, scenario intent/object state, `RecipeDef`, `LootBoxDef` and `SkillProgressionDef` now have concrete bounded implementations. Keep future objectives/phases/interactables typed and small, with strict schemas, runtime validation, save defaults and meaningful scenario tests. Avoid a universal scripting language. Resolution order and event budgets remain deterministic.

Room recipes preserve placements `{asset,x,y,rotation}` and camera-independent coordinates. The workshop exports authoring recipes, collision/surface tiles and a separate playable map. Runtime imports validate map limits, tags, components, asset/layer/rotation compatibility, actor placement and walkable connectivity before replacing the live run. A valid import deliberately starts a standalone room; export the campaign save first if it should be kept. The full custom map and its visual placements survive save/reload. Procedural campaigns and merging arbitrary workshop rooms into a live campaign remain future work.

## Verification gates

- C# tests: both action orders, explicit party completion, enemy approach/attack, forms, exact forecasts, achievement uniqueness and mode/save migration.
- Browser tests: visible ability selection, form menu, preview/cancel/confirm, move after action, end every ally, enemy declarations and changing rendered frames, impact layer visibility, save/reload and touch inspection.
- Editor tests: paint/erase, piece and camera rotations, inverse picking, layer visibility, JSON roundtrip, real campaign validator acceptance and spawn warnings.
- Visual checks: screenshots at desktop, phone portrait and phone landscape; inspect alignment and actual effect overlap, not only DOM text.
- New boss gate: complete the scenario using ordinary legal commands, fail/retry it, reload mid-phase, rotate at each phase, and confirm objectives remain visible.
- Native Unity gate: port presentation, open Editor, compile, enter Play Mode and export Web. Reference compilation alone does not satisfy this gate.
