# Progression, equipment and safe room

The browser starts in Mordecai's safe room. Its Rest, Equipment, Skills and dungeon-entrance stations invoke the shared C# session. Open the roster to change the four deployed crawlers or their optional classes. Mordecai remains an advisor.

The party shares experience, including reserves. Cumulative XP of 0, 30, 70 and 120 grants levels 1–4. Each level adds 3 maximum HP and 1 maximum Mana. Each deployable character unlocks a personal skill at levels 2 and 3. These are compact tactical adaptations, not a complete reproduction of book mechanics. The full catalog is generated in [PlayableContent.md](PlayableContent.md).

Equipment has weapon, armor and charm slots. Each authored item is a single owned copy; it can be equipped by one crawler at a time. Three pieces are available initially, two unlock after the first victory, and one after the second. Gear changes actual HP, Mana or movement and can grant abilities. Reinforced Wraps grant Heavy Blow, while Sponsor Edge grants Backstab. Equipping and unequipping are allowed only in the safe room. Rest restores HP and Mana to the new maximum; it does not create additional consumables.

The quest journal derives progress from actual cleared encounters, discovered doors, claimed discoveries and defeated enemies. It is not a separate quest scripting engine. The game remains one authored three-encounter floor, and the Room Kit workshop still exports authoring recipes separately.

## Editable data

`UnityPackage/Runtime/Data/game-content.json` contains `progression.xpThresholds`, per-level growth, `skillUnlocks` and `equipment`. Stable IDs reference abilities in `combat-content.json`. Equipment `unlockEncounter` counts completed victories. `abilityIds` grants existing resolver abilities; new combinations of existing effects need no new runtime primitive.

`GameSession.Progression.cs` owns effective stats, ownership, equipment validation, resting, quest views and save upgrades. Saves retain equipped IDs and a progression version; old content versions 1 and 2 upgrade without erasing earned XP. Browser presentation reads these views and sends commands rather than calculating combat bonuses itself.

## Movement and art

The map rotates through four camera views. Pointer picking uses the inverse projection, so rotating does not change world coordinates or movement allowance. Arrow keys and WASD follow the screen orientation; highlighted paths show grid steps. Exploration animates the party along the traversable path. Enemies use walkable path distance to approach players around walls, while enemies already able to attack may remain in place.

All eight deployable characters have four authored directional views with idle and two walking frames each. `Tools/build_directional_sprites.py` rebuilds normalized sheets and their manifest from retained GPT-generated source art using `Tools/art-requirements.txt`. Frames share a foot anchor; `bodyHeight` keeps health bars near the visible head. Southeast attacks retain compatible earlier action poses; other directions use directional art with motion and effects. Enemy art has the earlier walk/attack poses rather than four authored directional sets.

The browser locks player actions during enemy playback and labels the enemy phase. Explicit Skip animation remains available. The shared C# state and autosave commit independently of animation timing.

## Tactical forms and feedback update

Character sheets expose three stances and Katia's four shape presets. These choices preview and commit through C#, consume the action, preserve unused movement, and save their IDs. Increased caps do not heal or refill Mana; Defensive and Bulwark grant existing Guarded protection. Their tactical bonuses are invented adaptations of the character identity. New form silhouettes and a physical mass-budget simulation remain planned. Five committed achievement milestones are serialized per run; the UI narrator displays them without re-awarding on reload.

The lore review and future manual-stat/skill-practice plan are in [Mechanics-Plan.md](Mechanics-Plan.md). Current shared party levels remain the compact implementation.
