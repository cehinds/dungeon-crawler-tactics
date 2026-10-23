# Progression, equipment and safe room

The browser starts in Mordecai's safe room. Its Rest, Equipment, Skills and dungeon-entrance stations invoke the shared C# session. Open the roster to change the four deployed crawlers or their optional classes. Mordecai remains an advisor.

The party shares experience, including reserves. Cumulative XP of 0, 30, 70 and 120 grants levels 1–4. Each level adds 3 maximum HP and 1 maximum Mana. Each deployable character unlocks a personal skill at levels 2 and 3. These are compact tactical adaptations, not a complete reproduction of book mechanics. The full catalog is generated in [PlayableContent.md](PlayableContent.md).

Equipment has weapon, armor and charm slots. Each authored item is a single owned copy; it can be equipped by one crawler at a time. Three pieces are available initially, two unlock after the first victory, and one after the second. Gear changes actual HP, Mana or movement and can grant abilities. Reinforced Wraps grant Heavy Blow, while Sponsor Edge grants Backstab. Equipping and unequipping are allowed only in the safe room. Rest restores HP and Mana to the new maximum; it does not create additional consumables.

The quest journal derives progress from actual cleared encounters, discovered doors, claimed discoveries and defeated enemies. It is not a separate quest scripting engine. The main campaign remains one authored three-encounter floor. Optional boss scenarios and imported workshop rooms are separate play modes; see [PlayableGame.md](PlayableGame.md).

## Stat allocation and skill practice

This is an **accelerated, mixed-timeline adaptation**. Every earned party level grants each field crawler three points, spendable in the safe room without a race/class milestone. In the books, manual allocation waits until the Third Floor race/class selection. The game keeps its existing automatic HP/Mana growth for compatibility and adds an independent saved allocation pool. These formulas are invented game rules:

| Allocated stat | Actual benefit |
|---|---|
| Strength | +1 direct ability damage per two points |
| Dexterity | +1 movement per three points |
| Constitution | +3 maximum HP per point |
| Intelligence | +2 maximum Mana per point |
| Charisma | +1 direct ability healing per point |

Preview allocation to compare the resulting caps, movement, damage and healing bonuses, then confirm or cancel. Cancellation spends nothing. Increasing a cap does not restore resources; rest to fill it. Allocations belong to each crawler, including reserves, and survive class changes and saves.

Skill practice is separate from party XP and personal-skill unlocks. A committed non-item ability adds one use to that crawler's ability track. Rank 2 requires three uses; rank 3 requires eight. Each rank above 1 adds one direct damage, one direct healing and one Mana-cost reduction where relevant. Reaction damage and consumable actions do not gain these bonuses. Previews and cancellations do not train skills. This is a bounded three-rank adaptation, without guild training, race-specific caps or companion growth.

## Recipes and owned loot boxes

The safe room offers two invented recipes: two Health Tonics make one Mega Tonic; one Oil Flask plus one Frost Vial makes one Fire Bomb. The menu shows ingredients, outputs and missing-supply reasons. The shared core checks the entire transaction before consuming ingredients and granting output. This designated crafting service does not imply that every canonical safe room has a workbench.

Earned loot boxes are owned records with visible fixed contents and an opened flag. The first tactical move earns a Bronze Crawler Box containing one Health Tonic; the first committed shapechange earns a Bronze Improviser Box containing one Cleansing Tonic. Each campaign victory earns a Silver Survivor Box containing a Health Tonic and a Water Bomb. Open boxes in the safe room. Reopening an opened box cannot grant a second reward, and saves retain ownership and opening state. These are deterministic adaptation rewards, without random rarity rolls, an audience economy or pet rewards.

## Editable data

`UnityPackage/Runtime/Data/game-content.json` contains `progression.xpThresholds`, per-level growth, `skillUnlocks`, `equipment` and the `development` definitions for stats, practice thresholds, recipes and box sources. Stable IDs reference abilities in `combat-content.json`. Equipment `unlockEncounter` counts completed victories. `abilityIds` grants existing resolver abilities; new combinations of existing effects need no new runtime primitive.

`GameSession.Progression.cs` owns effective stats, ownership, equipment validation, resting, quest views and save upgrades. `GameSession.Development.cs` owns allocation previews, per-ability practice, atomic crafting and owned-box state. Saves retain these records alongside equipped IDs; older checkpoints initialize missing development records while preserving earned XP and existing party state. Browser presentation reads these views and sends commands rather than calculating combat bonuses itself.

## Movement and art

The map rotates through four camera views. Pointer picking uses the inverse projection, so rotating does not change world coordinates or movement allowance. Arrow keys and WASD follow the screen orientation; highlighted paths show grid steps. Exploration animates the party along the traversable path. Enemies use walkable path distance to approach players around walls, while enemies already able to attack may remain in place.

All eight deployable characters have four authored directional views with idle and two walking frames each. `Tools/build_directional_sprites.py` rebuilds normalized sheets and their manifest from retained GPT-generated source art using `Tools/art-requirements.txt`. Frames share a foot anchor; `bodyHeight` keeps health bars near the visible head. Southeast attacks retain compatible earlier action poses; other directions use directional art with motion and effects. Enemy art has the earlier walk/attack poses rather than four authored directional sets.

The browser locks player actions during enemy playback and labels the enemy phase. Explicit Skip animation remains available. The shared C# state and autosave commit independently of animation timing.

## Tactical forms and feedback update

Character sheets expose three stances and Katia's four shape presets. These choices preview and commit through C#, consume the action, preserve unused movement, and save their IDs. Increased caps do not heal or refill Mana; Defensive and Bulwark grant existing Guarded protection. Their tactical bonuses are invented adaptations of the character identity. New form silhouettes and a physical mass-budget simulation remain planned. Five committed achievement milestones are serialized per run; the UI narrator displays them without re-awarding on reload.

The [lore review](Lore-Mechanics-Review.md) and [implementation plan](Mechanics-Plan.md) distinguish these accelerated rules from future chronological race/class milestones, mass-based shaping, companion progression and broader skill training.
