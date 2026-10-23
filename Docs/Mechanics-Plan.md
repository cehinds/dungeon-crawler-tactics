# Mechanics implementation plan

The aim is a readable tactics game built around the books' improvisation, character identities and cruel game-show framing. The [feature checklist](Book-Fidelity-Checklist.md) separates implemented browser behavior from future work. [Lore review](Lore-Mechanics-Review.md) identifies primary versus secondary evidence. The [concept gallery](../Web/wwwroot/mechanics-review.html) is a visual target, not an implementation specification.

## Current changes

One move and one action are independent allowances. Either order is legal; using an ability does not finish the crawler. End Turn marks that crawler finished, chooses the next unfinished ally, then runs the enemy team after everyone finishes. A finished crawler cannot act or move. Existing saves migrate their previous activation semantics. Selecting an ability exposes its description and targeting rules immediately; selecting Shapeshift opens Katia's forms.

Three stances and four Katia forms are authored in `game-content.json`. Each shows a reversible stat package and a shared-core forecast. Changing stance/form costs the action, not the remaining movement. Increased caps do not heal or refill Mana; lowering a cap clamps the current resource. Defensive and Bulwark choices grant the existing Guarded protection for immediate usefulness. These presets are adaptations, not canonical form names or an implemented simulation of conserved mass. New form-specific sprite sets remain planned.

The character sheet covers each roster member's stats, XP, skills, gear and tactical choices. The narrator consumes committed presentation events, announces actors/actions/targets and impacts, and offers a history dialog. Achievement IDs live in the save and fire only on earned commits. Five initial milestones cover moving, reacting, shapechanging, first victory and first level. These award notices; they do not yet create loot boxes or audience currency.

The map and workshop use a shared 128×64 logical diamond footprint and measured PNG anchors. Ground surfaces stay below characters; fire/projectiles/hit effects/text render after units and walls. Piece orientation and camera orientation are distinct. The workshop supports painting, erasing, four views, recipe import/export and a game-compatible tile export. A recipe is not yet a runtime-importable campaign.

## Next milestone: meaningful crawler development

- Add five base stats and a saved unspent-point pool. Keep the compact current levels as a migration path; do not silently reinterpret old HP/Mana as canonical base stats.
- Choose a clear campaign milestone for race/class selection and point allocation. A chronological mode follows the later unlock; an accelerated mode must label the compression.
- Separate skill practice from crawler XP: per-skill use count/XP, level cap, practice sources, and class/race/gear modifiers. Prevent farmable canceled previews and duplicate reload rewards.
- Give every increase a before/after explanation tied to a supported effect. Do not invent a canonical damage formula from a fan summary.
- Add Katia's shape silhouettes, equipped-mass budget and later engineering/momentum actions only after the rules and footprint model can forecast them.

Acceptance: an earned level exposes spendable points at the correct location, allocation changes real resolver behavior, canceled allocation spends nothing, skill use advances only its own track, and migration/reload preserves all choices.

## Boss scenarios, in build order

All three are **planned**. The present campaign still uses its existing three encounters. Art depicts original adaptations of Book 1 settings; its costs, numbers and class labels are illustrative.

### Hoarder — first vertical slice

Source anchor: garbage stockpile, giant human-ish boss and Scatterers. Add an objective briefing, capped minion spawning, a visible emergence warning and destructible garbage lanes. Fire interruption and explosive counterplay are invented tactical rules. Let ordinary damage remain a viable route; do not require guessing the book solution. Separate a boss's footprint from its sprite size. Test full occupancy, blocked spawn fallback, hazard contact, phase persistence and retry.

### Juicer — spatial threat reading

Source anchor: scaly gym boss hurling flaming metal weight plates. Add deterministic throw lanes and an advance warning, cover interception, topplable equipment and a close-range fallback. Attack plans must be authored/resolved by C# and displayed from the same data used for execution. Test interrupted throws, moved targets, cover destruction, friendly fire rules and all four camera views.

### Ball of Swine — cooperative construction

Source anchor: rolling borough threat and Meadow Lark's Speedbump engineering. Add a rolling footprint, carryable components, shared construction progress, barricade durability, helper activations and a clear collision forecast. Construction competes with combat actions. Provide a recovery route if a part breaks or a builder falls. Test loops, partial construction saves, route obstruction, lost helpers, collision order and victory/defeat boundaries.

## Exploration and reward milestone

Introduce typed map objects for doors, levers, caches, destructible supports, workbenches and exits. Each has stable IDs, tags, interaction range/cost and serialized state. Narration explains an object on inspection; interaction previews explain what changes. Loot boxes are owned rewards opened in a safe room. Recipes reference item IDs and explicit quantities; crafting validates and consumes materials atomically. A countdown must pause in menus or use turns, with its rule stated clearly. Pet growth is separate from a crawler's class/stat allocation.

## Data and code boundaries

Keep the rules in the shared C# project. JSON authors classes, abilities, forms, stances, items, tag reactions, encounters and rewards. Stable IDs are never inferred from display names. UI reads views and issues commands; it does not calculate damage or bonuses.

For future boss work add small typed definitions: `ScenarioDef`, `ObjectiveDef`, `BossPhaseDef`, `IntentDef`, `InteractableDef`, `RecipeDef`, `LootBoxDef` and `SkillProgressionDef`. Each requires a schema, runtime validator, save version/defaults and a meaningful scenario test. Avoid a universal scripting language. Resolution order and event budgets remain deterministic.

A room recipe preserves placements `{asset,x,y,rotation}` and camera-independent world coordinates. The current game tile export provides `{width,height,tiles:[{x,y,blocked,tags}]}`. Merge those fields into an encounter, preserve or deliberately relocate its spawn records, clear blocked spawns, run the validator and rebuild. Decorative recipe art is not automatically persisted by that collision/surface export. A future runtime import must validate both layers and path connectivity before replacing a live run.

## Verification gates

- C# tests: both action orders, explicit party completion, enemy approach/attack, forms, exact forecasts, achievement uniqueness and mode/save migration.
- Browser tests: visible ability selection, form menu, preview/cancel/confirm, move after action, end every ally, enemy declarations and changing rendered frames, impact layer visibility, save/reload and touch inspection.
- Editor tests: paint/erase, piece and camera rotations, inverse picking, layer visibility, JSON roundtrip, real campaign validator acceptance and spawn warnings.
- Visual checks: screenshots at desktop, phone portrait and phone landscape; inspect alignment and actual effect overlap, not only DOM text.
- New boss gate: complete the scenario using ordinary legal commands, fail/retry it, reload mid-phase, rotate at each phase, and confirm objectives remain visible.
- Native Unity gate: port presentation, open Editor, compile, enter Play Mode and export Web. Reference compilation alone does not satisfy this gate.
