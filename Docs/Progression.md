# Progression, equipment and safe room

The browser starts in Mordecai's safe room. Its Rest, Equipment, Skills and dungeon-entrance stations invoke the shared C# session. Open the roster to change the four deployed crawlers or their optional classes. Mordecai remains an advisor.

The party shares experience, including reserves. Cumulative XP of 0, 30, 70 and 120 retains legacy levels 1–4; the story track now extends to level 50 at 59,431 XP, before the final battle. Each level adds 3 maximum HP and 1 maximum Mana. Each deployable character unlocks a personal skill at levels 2 and 3. These are compact tactical adaptations, not a complete reproduction of book mechanics. The full catalog is generated in [PlayableContent.md](PlayableContent.md).

Equipment has weapon, armor and charm slots. Each authored item is a single owned copy; it can be equipped by one crawler at a time. Three pieces are available initially, two unlock after the first victory, and one after the second. Gear changes actual HP, Mana or movement and can grant abilities. Reinforced Wraps grant Heavy Blow, while Sponsor Edge grants Backstab. Equipping and unequipping are allowed only in the safe room. Rest restores HP and Mana to the new maximum; it does not create additional consumables.

The quest journal derives progress from actual cleared encounters, discovered doors, claimed discoveries and defeated enemies. It is not a separate quest scripting engine. The legacy campaign remains one authored three-encounter floor. The optional story campaign implements seven tactical battles over floors 1–8, including the floor-7 bypass. Optional boss scenarios and imported workshop rooms are separate play modes; see [PlayableGame.md](PlayableGame.md).

## Stat allocation and skill practice

This is an **accelerated, mixed-timeline adaptation**. Every earned party level grants each field crawler three points, spendable in the safe room; story mode banks them until floor 3. Legacy mode retains immediate allocation. In the books, manual allocation waits until the Third Floor race/class selection. The game keeps its existing automatic HP/Mana growth for compatibility and adds an independent saved allocation pool. These formulas are invented game rules:

| Allocated stat | Actual benefit |
|---|---|
| Strength | +1 direct ability damage per two points |
| Dexterity | +1 movement per three points |
| Constitution | +3 maximum HP per point |
| Intelligence | +2 maximum Mana per point |
| Charisma | +1 direct ability healing per point |

Preview allocation to compare the resulting caps, movement, damage and healing bonuses, then confirm or cancel. Cancellation spends nothing. Increasing a cap does not restore resources; rest to fill it. Allocations belong to each crawler, including reserves, and survive class changes and saves.

Skill practice is separate from party XP and skill unlocks. A committed learned ability adds one use to that crawler’s track; previews, cancellations, consumable casts and temporary-copy actions do not train the owner. Authored Katia form changes now train Shapeshift too. The original early thresholds (rank 2 at three uses, rank 3 at eight) and saved use counts are preserved. The deterministic curve slows after rank 10. Normal eligibility stops at 15; Carl’s configured Primal permission reaches 20 after story floor 3. All 20 rows remain inspectable even when permission locks the upper ranks. Full race/class-specific cap selection is not implemented.

All 95 authored abilities have explicit profiles in `development.practice.abilityProfiles`. The pure C# effective-ability transformation is used by targeting, descriptions, forecasts and commits. Damage/healing, Mana reduction, range, push distance and temporary summon HP/movement/lifetime can scale. Profiles may also define `abilityProfiles[].castModes`, with stable `id`, `label`, `minimumRank`, `manaCost` and `damageBonus` fields for rank-gated cast choices. Milestone tags provide stronger Rush, protection and shock traps. Ranked tags form exclusive families: recasting replaces sibling tiers rather than stacking them, and removing a base tag removes its variants. Existing duration/reapplication rules remain: an already present identical timed tag does not refresh merely from another cast.

| Signature ability | Implemented rank behavior | Book fidelity boundary |
|---|---|---|
| Powerful Strike | Damage progression with later push refinements | Bounded tactics conversion of unarmed amplification, not the novel’s literal multiplier. |
| Magic Missile | Baseline cost is 5 Mana, with no automatic rank-based cost reduction. At rank 5, choose explicit 3/4/5/6 Mana modes; their damage offsets are -4/-2/0/+4 after normal rank and stat bonuses. Rank 10 adds a two-round Burning status. | Chapter-cited secondary source reports the rank-5 cost choice and ignition at 10. Mode offsets and guaranteed Burning are tactical adaptations. |
| Puddle Jumper | Range increases at authored milestones | Instant single-unit board teleport; group transport, casting delay and cooldown remain unimplemented. |
| Heal Critter | Healing/range growth; requires the Pet tag | Pet target restriction matches the cited identity. Numeric rank table is extrapolated. |
| Clockwork Triplicate | Two copies gain HP, movement and lifetime by rank | Duplicate count remains two. All numeric scaling is extrapolated. |
| Katia’s Shapeshift / Rush | Committed form changes train Shapeshift; guarded forms use its protection tier. Rush gains movement/duration tiers. | Preset form stats stay fixed. Mass-based shaping and copying powers are not claimed. |
| Mongo’s actions | Bite potency and leap range scale | Independent companion practice is a game adaptation. |

Rank descriptions and source notes appear in Actions and Character → Abilities. A collapsed inspector exposes ranks 1–20 without adding a permanent long list, including details for rank-locked modes. It shows the base ability with rank benefits; the current description also includes the crawler’s allocated-stat and skill-tree modifiers. Magic Missile uses a compact cast-mode chooser backed by authoritative C# summaries; it offers a cheaper mode when the crawler can afford that mode, even when the default cost is unaffordable. Preview and cancellation spend no Mana and award no practice; confirming the action spends the selected cost, trains once, and preserves remaining movement. Consumable casts keep their authored effects and do not receive learned-ability rank bonuses. Some utility ranks share the same effect between milestones. No complete 20-rank novel table is claimed: see [Ability rank audit](Ability-Rank-Audit.md).

The purchased training room retains its limited paid-practice service. Equipment skill-level bonuses, arbitrary race/class cap permissions, skill potions, guild simulation, Character Actor’s separate floor-based leveling and companion growth remain incomplete.

## Recipes and owned loot boxes

The safe room offers two invented recipes: two Health Tonics make one Mega Tonic; one Oil Flask plus one Frost Vial makes one Fire Bomb. The menu shows ingredients, outputs and missing-supply reasons. The shared core checks the entire transaction before consuming ingredients and granting output. This designated crafting service does not imply that every canonical safe room has a workbench.

Earned loot boxes are owned records with visible fixed contents and an opened flag. The first tactical move earns a Bronze Crawler Box containing one Health Tonic; the first committed shapechange earns a Bronze Improviser Box containing one Cleansing Tonic. Each campaign victory earns a Silver Survivor Box containing a Health Tonic and a Water Bomb. Open boxes in the safe room. Reopening an opened box cannot grant a second reward, and saves retain ownership and opening state. These are deterministic adaptation rewards, without random rarity rolls, an audience economy or pet rewards.

## Editable data

`UnityPackage/Runtime/Data/game-content.json` contains `progression.xpThresholds`, per-level growth, `skillUnlocks`, `equipment` and the `development` definitions for stats, practice thresholds, recipes and box sources. Stable IDs reference abilities in `combat-content.json`. Equipment `unlockEncounter` counts completed victories. `abilityIds` grants existing resolver abilities; new combinations of existing effects need no new runtime primitive.

`GameSession.Progression.cs` owns effective stats, ownership, equipment validation, resting, quest views and save upgrades. `GameSession.Development.cs` owns allocation previews, per-ability practice, atomic crafting and owned-box state. `RankProgressionData.cs` constructs the twenty-row tables, and `AbilityScaling.cs` applies their effects without mutating authored definitions. `Tools/build_ability_ranks.py` is an optional reproducible authoring helper for the JSON profiles and registered tag variants. Saves retain these records alongside equipped IDs; older checkpoints initialize missing development records while preserving earned XP and existing party state. Browser presentation reads these views and sends commands rather than calculating combat bonuses itself.

## Movement and art

The map rotates through four camera views. Pointer picking uses the inverse projection, so rotating does not change world coordinates or movement allowance. Arrow keys and WASD follow the screen orientation; highlighted paths show grid steps. Exploration animates the party along the traversable path. Enemies use walkable path distance to approach players around walls, while enemies already able to attack may remain in place.

All eight deployable characters have four authored directional views with idle and two walking frames each. `Tools/build_directional_sprites.py` rebuilds normalized sheets and their manifest from retained GPT-generated source art using `Tools/art-requirements.txt`. Frames share a foot anchor; `bodyHeight` keeps health bars near the visible head. Southeast attacks retain compatible earlier action poses; other directions use directional art with motion and effects. Enemy art has the earlier walk/attack poses rather than four authored directional sets.

The browser locks player actions during enemy playback and labels the enemy phase. Explicit Skip animation remains available. The shared C# state and autosave commit independently of animation timing.

## Tactical forms and feedback update

Character sheets expose three stances and Katia's four shape presets. These choices preview and commit through C#, consume the action, preserve unused movement, and save their IDs. Increased caps do not heal or refill Mana; Defensive and Bulwark grant existing Guarded protection. Their tactical bonuses are invented adaptations of the character identity. New form silhouettes and a physical mass-budget simulation remain planned. Five committed achievement milestones are serialized per run; the UI narrator displays them without re-awarding on reload.

The [lore review](Lore-Mechanics-Review.md) and [implementation plan](Mechanics-Plan.md) distinguish these accelerated rules from remaining race-selection mechanics, mass-based shaping, companion progression and broader skill training.

## Current class trees and personal space

Each selectable kit now has a two-branch class tree with fourteen nodes across levels 1, 5, 10, 20, 30, 40 and 50. One class point is earned per authored tier, so seven points cannot purchase both full branches. Class-node ownership is per crawler; switching classes preserves learned nodes but activates only the selected class’s benefits. Personal crawler trees keep their separate one-point-per-level pool. All numerical trees are explicit tactical adaptations.

See [Journey and home](Journey-and-Home.md) for gold, room purchases, crafting, paid training and earned club credentials. The runtime rank inspector uses the same C# table as action forecasting and resolution; the public codex separately labels its research extrapolations.
