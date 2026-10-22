> Historical planning/starter reference. For the implemented playable game, current content and setup, see [PlayableGame.md](PlayableGame.md). The original starter fixture is retained for regression tests.

# Dungeon Crawler Tactics — Content Catalog

This document distinguishes **seed data already in the starter JSON** from **proposed content**. Only the nine abilities, one item, registered tags, and five reactions in the seed table below are import-ready against the current schema without further edits. Proposed content is a design backlog, not an assertion that the IDs, mechanics, balance, UI, or encounter systems exist in code. Stable lowercase IDs are recommended; numeric values are starter tuning suggestions.

The catalog follows the version 1 schema in [TagRules.md](TagRules.md): abilities use `target`, `range`, `cost`, `incomingTags`, and effects; an effect is `{op, amount, tag}`; a reaction has `{id, priority, incoming:{all,any,none}, target:{all,any,none}, consumeTags, effects, emitTags}`; an item refers to an ability by `abilityId`. Supported operations are `Damage`, `Heal`, `AddTag`, and `RemoveTag`. The kernel is deterministic and single-target. It does not provide classes' stats, per-turn status durations, tile occupancy effects, AI, map movement, inventory charges, or action permissions.

## Current seed content (schema version 1)

Costs below are energy costs from the seed JSON. They are not AP/MP and do not define the separate game rule that committing one action ends activation. Range is the authored integer. Targets are the actual schema values: `self`, `ally`, `enemy`, or `tile`.

| Ability ID | Label | Target | Range | Cost | Incoming tags | Current effect/result |
|---|---|---|---:|---:|---|---|
| `ability.strike` | Strike | enemy | 1 | 0 | `damage.physical` | Deal 6 damage |
| `ability.firebolt` | Firebolt | enemy | 4 | 2 | `element.fire` | Deal 8 damage; reactions may also resolve |
| `ability.spark` | Spark | enemy | 4 | 2 | `element.lightning` | Deal 5 damage; wet reaction may add 5 damage and `status.shocked` |
| `ability.oil_flask` | Oil Flask | tile | 3 | 1 | — | Add `surface.oil` to selected tile |
| `ability.frostbite` | Frostbite | enemy | 3 | 2 | `element.cold` | Deal 4 damage; wet reaction can consume `status.wet` and add `status.frozen` |
| `ability.mend` | Mend | ally | 3 | 2 | — | Heal 8 |
| `ability.douse` | Douse | enemy | 3 | 1 | `element.water` | Add `status.wet` to selected enemy |
| `ability.shatter` | Shatter | enemy | 1 | 1 | `impact.shatter`, `damage.physical` | Deal 5 damage; frozen reaction can consume `status.frozen` and add 10 damage |
| `ability.fire_surface` | Ignite Surface | tile | 4 | 2 | `element.fire` | No direct effect; oil reaction consumes `surface.oil` and adds `surface.burning` |

| Item ID | Label | Ability reference | Current status |
|---|---|---|---|
| `item.oil_flask` | Oil Flask | `ability.oil_flask` | Present in seed JSON; item ownership/charges are not yet a battle inventory system |

### Current registered tags

| Tag ID | Meaning in current rules |
|---|---|
| `element.fire` | Fire event marker |
| `element.cold` | Cold event marker |
| `element.lightning` | Lightning event marker |
| `element.water` | Water event marker |
| `damage.physical` | Physical event marker |
| `impact.shatter` | Shatter event marker |
| `surface.oil` | Persistent tag on a tile targeted by Oil Flask |
| `surface.burning` | Persistent tile marker; no automatic damage or spread |
| `status.wet` | Persistent target marker queried by lightning/cold reactions |
| `status.frozen` | Persistent target marker queried by Shatter; does not skip a turn |
| `status.shocked` | Marker only; no additional action penalty |

### Current seed reactions

| Reaction ID / priority | Incoming query | Target query | Consumed tags | Effects |
|---|---|---|---|---|
| `reaction.oil_ignites` / 100 | all `element.fire` | all `surface.oil` | `surface.oil` | Add `surface.burning` to target tile |
| `reaction.wet_conducts` / 90 | all `element.lightning` | all `status.wet` | `status.wet` | +5 damage; add `status.shocked` |
| `reaction.wet_freezes` / 90 | all `element.cold` | all `status.wet` | `status.wet` | Add `status.frozen` |
| `reaction.frozen_shatters` / 100 | all `impact.shatter` | all `status.frozen` | `status.frozen` | +10 damage |
| `reaction.water_extinguishes` / 100 | all `element.water` | all `surface.burning` | `surface.burning` | No further effect |

The current tile resolver can add/consume tags on a selected tile, but there are no occupancy or neighboring-tile hooks. Ignition does **not** burn a unit standing on oil, cause damage over time, or spread. Wet/lightning resolves against the selected wet enemy; it does not jump to other units or adjacent wet tiles. Water extinguishing is a generic registered rule, but the seed has no water-on-tile ability to apply it to a burning tile. Frostbite/Shatter reactions operate on the selected enemy. These are the exact seed interactions; spatial versions are proposed future work.

## First-release content target

The delivery plan sets the target at six classes, 18 active abilities, eight consumables, six enemies, and one boss for a complete floor. The current JSON's twelve class records are grants/stubs; they are not evidence that twelve fully designed classes are in the first release. Candidate first-release classes that support the existing corridor puzzle are Brawler, Pyromancer, Cryomancer, Stormcaller, Cleric, and Alchemist. Treat this selection as a content recommendation until the coordinator locks the release roster.

Carl and Donut are the core characters in this fan adaptation. Their class/ability assignments, stats, and progression are not encoded in the current kernel. Recruited companions can be original characters. The complete 12-class list below is a later catalog direction.

## Proposed class catalog (12 total direction)

Classes only grant ability IDs in schema v1. Roles, stats, movement, and unlock progression are future game data, not class-specific code behavior.

| Class ID | Name | Role direction | Proposed signature ability IDs |
|---|---|---|---|
| `class.brawler` | Brawler | Close-range finisher; Carl's natural combat direction | `ability.strike`, `ability.shatter`, `ability.heavy_swing` |
| `class.guardian` | Guardian | Protects allies and holds a lane | `ability.shield_bash`, `ability.interpose`, `ability.guard_stance` |
| `class.rogue` | Rogue | Flanks and punishes exposed targets | `ability.backstab`, `ability.smoke_bomb`, `ability.dash_strike` |
| `class.ranger` | Ranger | Focused ranged control | `ability.pin_shot`, `ability.volley`, `ability.mark_target` |
| `class.pyromancer` | Pyromancer | Fire attacks and oil interaction | `ability.firebolt`, `ability.fire_surface`, `ability.flame_wave` |
| `class.cryomancer` | Cryomancer | Cold attacks and freeze/shatter setup | `ability.frostbite`, `ability.frost_patch`, `ability.freeze_burst` |
| `class.stormcaller` | Stormcaller | Lightning and wet interaction | `ability.spark`, `ability.chain_lightning`, `ability.rain_call` |
| `class.cleric` | Cleric | Healing, cleanse, and protection; a direction for Donut's regal caster identity if desired | `ability.mend`, `ability.cleanse`, `ability.sanctuary` |
| `class.alchemist` | Alchemist | Flexible item use and surface manipulation | `ability.oil_flask`, `ability.douse`, `ability.acid_vial` |
| `class.bard` | Bard | Ally support and disruption | `ability.rally`, `ability.discordant_note`, `ability.encore` |
| `class.necromancer` | Necromancer | Drains vitality and summons a temporary ally | `ability.life_drain`, `ability.bone_bolt`, `ability.raise_thrall` |
| `class.beastmaster` | Beastmaster | Companion attacks and team setup | `ability.command_bite`, `ability.pack_mark`, `ability.guard_companion` |

## Proposed ability expansion

Only the nine entries in the seed table are presently import-ready. These additional IDs are proposed for a 34-plus ability direction; they need registered tags, schema-valid data, tuning, and implementation of any required game-system hooks. Proposed tags below are not registered unless they appear in the current-tag table above. No ability grants an extra action; action/activation rules live outside this content schema.

| Ability ID | Label / role | Cost and range proposal | Proposed tag/effect direction |
|---|---|---|---|
| `ability.heavy_swing` | Heavy Swing; melee | energy 1, range 1 | `damage.physical`; bonus query for proposed `status.exposed` |
| `ability.taunt` | Look at Me; control | energy 1, range 3 | Add proposed `status.taunted`; requires AI target-priority hook |
| `ability.guard_stance` | Guard Stance; defense | energy 1, self | Add proposed `status.guarding`; needs damage-reduction resolution |
| `ability.shield_bash` | Shield Bash; control | energy 1, range 1 | `damage.physical`; add proposed `status.staggered` |
| `ability.interpose` | Get Behind Me; protection | energy 1, range 2 | Add proposed `status.protected`; needs damage-redirection hook |
| `ability.backstab` | Cheap Shot; flanking | energy 1, range 1 | `damage.physical`; query proposed `status.exposed` |
| `ability.smoke_bomb` | Smoke Bomb; area control | energy 1, range 3 | Add proposed `surface.smoke`; needs area/line-of-sight support |
| `ability.dash_strike` | Dash and Slash; mobility | energy 1, range 4 | Requires path/attack compound command; not supported by seed kernel |
| `ability.pin_shot` | Pinning Shot; control | energy 1, range 5 | `damage.physical`; add proposed `status.rooted` |
| `ability.volley` | Volley; area damage | energy 2, range 5 | `damage.physical`; requires multi-target spatial resolution |
| `ability.mark_target` | You're Next; setup | energy 1, range 6 | Add proposed `status.marked`; requires ally-hit bonus rule |
| `ability.flame_wave` | Flame Wave; line area | energy 2, range 4 | `element.fire`; area/range pattern and unit occupancy hooks required |
| `ability.frost_patch` | Cold Snap; terrain control | energy 1, range 4 | Add proposed `surface.ice`; requires movement terrain rule |
| `ability.freeze_burst` | Deep Freeze; area control | energy 2, range 3 | `element.cold`; area target support; wet reaction already exists only for one target |
| `ability.chain_lightning` | Chain Lightning; chain damage | energy 2, range 5 | `element.lightning`; connected-target selection is future spatial support |
| `ability.rain_call` | Rain on Parade; surface setup | energy 2, range 4 | `element.water`; requires tile target and `surface.water` registration |
| `ability.cleanse` | Cleanse; support | energy 1, range 3 | Remove proposed negative status tags; register each tag first |
| `ability.sanctuary` | Tiny Safe Zone; area defense | energy 2, range 3 | Requires area targets and proposed `status.warded` |
| `ability.acid_vial` | Acid Vial; debuff | energy 1, range 4 | Add proposed `status.corroded`; register tag and define armor system |
| `ability.transmute_surface` | Make It Worse; terrain utility | energy 1, range 3 | Requires tile conversion rules and registered surface tags |
| `ability.rally` | Hype Them Up; support | energy 1, range 4 | Add proposed `status.rallied`; next-hit bonus needs a reaction rule |
| `ability.discordant_note` | Bad Vibes; disruption | energy 1, range 5 | Add proposed `status.disoriented`; enemy intent fallback is future AI work |
| `ability.encore` | One More Time; setup | energy 2, range 3 | Add proposed `status.primed`; next-ability bonus needs a rule |
| `ability.life_drain` | Borrowed Time; damage/heal | energy 1, range 4 | Damage the target then heal the caster; requires effect-source targeting and actual-damage tracking, since current effects all affect one target |
| `ability.bone_bolt` | Bone to Pick; ranged | energy 1, range 5 | Add proposed `status.exposed` |
| `ability.raise_thrall` | Temporary Associate; summon | energy 2, range 3 | Summon/temporary units require roster and duration systems |
| `ability.command_bite` | Sic 'Em; companion attack | energy 1, range 4 | Requires companion actor and team relation rules |
| `ability.pack_mark` | Pack Tactics; setup | energy 1, range 5 | Add proposed `status.marked`; bonus requires an ally adjacency hook |
| `ability.guard_companion` | Stay Close; protection | energy 1, range 2 | Add proposed `status.guarding`; reaction/targeting needs implementation |

This table lists 29 additions to the nine seed abilities, for a 38-ability proposal. The release gate remains 18 abilities; choose and tune only the required subset for that gate. Higher-complexity entries such as area attacks, compound movement, summons, and status-duration effects should stay out of the first release unless their game-system hooks and forecasts are implemented.

## Consumable target (8)

The first-release target is eight items. Only Oil Flask exists in the seed JSON. The following are a proposed selection; each item references a corresponding ability record. Add the corresponding ability and tags before importing any proposed item.

| Item ID | Label | Ability ID | Status |
|---|---|---|---|
| `item.oil_flask` | Oil Flask | `ability.oil_flask` | In seed JSON |
| `item.potion_small` | Small Health Potion | `ability.potion_small` | Proposed; add registered `effect.healing` only if using it as a tag, otherwise use `Heal` |
| `item.potion_mana` | Mana Tonic | `ability.potion_mana` | Proposed; requires a defined resource recovery effect beyond current ops |
| `item.antidote` | Questionable Antidote | `ability.antidote` | Proposed; requires a registered status and `RemoveTag` effect |
| `item.fire_flask` | Sponsor's Fire Flask | `ability.fire_flask` | Proposed; can reuse `element.fire` and current oil reaction on a tile target |
| `item.water_bomb` | Hydration Grenade | `ability.water_bomb` | Proposed; uses `element.water`, with surface tag/target behavior still to define |
| `item.smoke_pellet` | Smoke Pellet | `ability.smoke_pellet` | Proposed; needs `surface.smoke` registration and LOS hooks |
| `item.revive_kit` | Emergency Associate Kit | `ability.revive_kit` | Proposed; downed/revive and healing rules are not in kernel |

Item count, carry limit, restocking, and whether an item consumes an activation belong to the future inventory/command contract. Do not infer that `ItemDef` currently implements usable inventory; it only links an item ID and label to an ability ID.

## Proposed status and surface ideas

Tags are boolean identities, not status objects. The kernel does not track duration, stacks, source, strength, or expiry. Keep this table as design direction only; each future tag must be registered in `tags[]`, and each status that needs time or stacking must also get an explicit status/lifecycle model.

| Proposed tag | Intended use | Required future rule/system |
|---|---|---|
| `status.burning` | Periodic fire harm | Status duration/tick boundary and water removal; not `surface.burning` |
| `status.poisoned` | Periodic poison harm | Duration and periodic damage |
| `status.rooted` | Restrict movement | Movement permission hook |
| `status.slowed` | Reduce movement budget | Turn budget modifier |
| `status.taunted` | Prioritize source | Enemy AI target scoring |
| `status.exposed` | Increase next physical hit | Damage modifier and consume timing |
| `status.marked` | Ally follow-up bonus | Bonus/consumption reaction |
| `status.guarding` | Reduce/redirect hit | Damage event mitigation or redirection |
| `status.protected` | Redirect eligible hit | Multi-entity targeting/event origin |
| `status.warded` | Reduce ability damage | Damage mitigation |
| `status.staggered` | Disrupt intent | Enemy action/intent hook |
| `status.blinded` | Restrict targeting | LOS/targeting hook; no random accuracy in MVP |
| `status.disoriented` | Alter intent | Deterministic fallback AI |
| `status.corroded` | Reduce armor | Armor system |
| `status.rallied` | Improve next ally action | Modifier and consumption rule |
| `status.primed` | Improve a later ability | Modifier and consumption rule |
| `status.downed` | Cannot act at zero HP | Battle state and revive system |
| `status.summoned` | Mark temporary actor | Summon roster and expiry |
| `status.wounded` | Camp recovery flag | Campaign save/progression |
| `surface.water` | Wet tile / dousing source | Tile system and occupancy hooks |
| `surface.ice` | Alter movement | Path cost/blocked-cell rule |
| `surface.smoke` | Obscure LOS | Spatial LOS rule |

`status.frozen` is already registered but only enables the current Shatter reaction. It does **not** skip a turn. `surface.burning` is already registered as a persistent surface marker; it does **not** apply automatic damage over time. Do not conflate either with the proposed `status.burning` lifecycle effect.

## Enemy and encounter content direction

The first room in the delivery plan is **Service Corridor 13**: four crawlers face three enemies around a leaking coolant pipe and oil slick, then disable the exit lock and reach extraction. The release target is six enemies plus a boss. Enemy behavior profiles, intent, pathing, and mission objectives are not in the rules kernel and remain encounter/gameplay implementation work. Design each enemy in terms of visible intent and legal deterministic actions; avoid class- or display-name-specific resolver behavior.

Audience/sponsor goals should reward first-time tactical choices such as completing a two-step reaction. Rewards are shown before the fight, do not gate core progress, and do not require repetition or grind. Exact XP and sponsor reward values are editable balance data.
