# Book fidelity and playability checklist

A source-linked mechanics review, seven generated concept sheets, and a status checklist. Checked means the behavior is implemented in shared source or browser UI; it does not mean screenshot-reviewed or verified in Unity. Unchecked means remaining or planned. See [Completion Checklist](Completion-Checklist.md) for end-to-end scope, evidence and screenshot tracking. Concept images are design targets, not screenshots or exact specifications.

The demo mixes early dungeon settings with later characters/classes. Lore examples stay within Books 1–4; linked fan pages may contain later spoilers. Form bonuses, stances, combat ranges and XP thresholds are tactical adaptations.

## Readable tactical combat

- [x] **Move and act in either order** — One move and one action per crawler; End Turn explicitly advances the party.
- [x] **Selected ability descriptions** — Persistent cost, range, target and effect text, plus a full details dialog for touch and keyboard.
- [x] **Complete ability book** — Expose personal, class, unlocked and equipment actions instead of relying on a few quick slots.
- [x] **Exact preview before committing** — Show HP, Mana, tags and stat-cap changes; cancel spends nothing.
- [x] **Enemy movement and declarations** — Play movement and action events with an enemy-phase banner and original narration.
- [x] **Impact layer above sprites** — Fire, projectiles, reaction effects and floating combat text draw after units and walls.
- [x] **Party turn state** — Separate move used, action used and turn finished; enemy team follows all finished allies.
- [x] **Scenario intent before the next round** — Scenario-specific warnings display the authored threat used by C# execution. A universal intent planner remains planned.
- [ ] **Area effects and chain reactions** — Shared resolver must preview all affected cells, friendly fire and bounded spread.
- [ ] **Potion cooldowns** — Add readable cooldown/overuse rules with book-grounded terminology and tested balance.

## Characters, shapes and progression

- [x] **Katia chooses a form** — Baseline, Bulwark, Strider and Focused presets with explicit HP/Mana/movement tradeoffs. Tactical adaptations.
- [x] **Every crawler has a character sheet** — Inspect stats, current stance, skills, equipment, party level and XP; Mordecai remains an advisor.
- [x] **Three tactical stances** — Balanced, Defensive and Mobile. These are game rules, not a canonical universal stance system.
- [x] **Party levels and skill unlocks** — Story progression reaches level 50; personal skills unlock at authored thresholds. Class-tree nodes extend through level 50. XP and class-tree values are tactical adaptations.
- [x] **Equipment changes actual stats** — Weapon, armor and charm ownership, granted abilities and save persistence.
- [x] **All eight characters have directional walking art** — Four directions with idle and walking frames; base identities retained.
- [x] **Distinct directional form sets** — Bulwark, Strider and Focused have 36 generated idle/walking frames with measured foot anchors, selected by actual form ID.
- [ ] **Distinct form attack frames** — Current alternate forms use a presentation lunge; dedicated attack/hit strips remain unfinished.
- [x] **Five stats and allocated points** — Strength, Intelligence, Constitution, Dexterity and Charisma modify real actions/stats. Three points per level per crawler; safe-room preview/confirm/cancel. Early unlock is an accelerated adaptation.
- [x] **Individual skill practice ranks** — Committed non-item ability uses train that crawler/ability; early thresholds are 3 and 8 uses, with authored ranks through 20 where eligible. Most abilities cap at 15; configured Primal eligibility reaches 20 after floor 3. Paid Training Room sessions are available. These are adaptations; broader guild simulation, companion growth and race/gear cap modifiers remain planned.
- [x] **Floor-3 class selection** — Story mode unlocks class changes and class-tree access on floor 3, with save validation and eligible-class checks. Class node milestones are authored at levels 1, 5, 10, 20, 30, 40 and 50; grants and effects are adaptations.
- [ ] **Race selection and milestones** — Add source-backed race choices, prerequisite previews and save-safe selection; race progression is not implemented.
- [ ] **Katia momentum and engineering** — Model equipped mass, Rush, bracing and carried platforms; verify timing and costs before authoring.
- [ ] **Expanded personal kits** — Current personal actions include Carl’s single-tile incendiary bomb, Donut’s missile/teleport/heal, Katia’s form and Mongo’s bite/pounce. Further trap kits, Donut spell/social progression and Mongo companion commands need separate source notes and mechanics.

## Narrator, exploration and rewards

- [x] **Compact original System narration** — Queue committed actor/action/target and impact messages; dismiss and revisit history.
- [x] **NEW ACHIEVEMENT notices** — Five first-time milestones are saved per run; previews and reloads do not repeatedly award them.
- [x] **Protected preparation hub** — Safe-room Rest, equipment and skills access; actual HP/Mana restoration.
- [x] **Objective journal and discoveries** — Floor progress, encounter door, optional caches/notes and enemy defeats reflect game state.
- [x] **Owned boxes and safe-room opening** — Earn fixed-content achievement and victory boxes; inspect rewards and opened state. Ownership and once-only opening persist; randomized rarity and pet rewards remain planned.
- [x] **Safe-room supply recipes** — Four authored recipes display ingredients/results; shared C# validates and consumes inputs atomically. Portable crafting and specialized workbenches remain planned.
- [ ] **Contextual audience/sponsor challenges** — Add visible bounded challenge offers tied to achievements and choices. Post-victory sponsor reward selection exists, but it is not contextual audience progression.
- [ ] **Companion progression** — Separate Mongo/pet growth, gear and commands from crawler race/class allocation.
- [ ] **Floor clock and descent pressure** — Communicate collapse risk and evacuation objectives without punishing time spent in menus.
- [x] **Bounded exploration interactions** — Required floor-4 route control and floor-5 beacon discoveries affect journey progress; Lantern Row has authored trap/store and rescue choices.
- [ ] **General environmental puzzle system** — Reusable levers, destructible supports, placeable traps and multi-step discovery/puzzle patterns are not broadly supported by these bounded authored interactions.

## Book-grounded boss scenarios — playable adaptations

- [x] **Hoarder: stockpile and Scatterers** — Capped Scatterer slots, visible emergence warnings, interrupting statuses and action-cost garbage clearing. Ordinary damage also works; mechanics are adaptations.
- [x] **Juicer: gym and flaming weight plates** — Locked throw lanes can be dodged or interrupted; action-cost toppled benches intercept one throw. Original tactical adaptation.
- [x] **Ball of Swine: cooperative Speedbump** — Eight-cell rolling route, three-cell warning, carried parts, a three-part barricade and recoverable helpers. Construction consumes actions; exact rules are adaptations.
- [x] **Scenario briefing and adaptation labels** — Choose a scenario at camp, inspect its objective and invented mechanics, and return to the preserved campaign afterwards.
- [ ] **Large-unit occupancy and boss phases** — All current bosses occupy one logical tile. Multi-cell occupancy, a universal phase system and general large-unit collision remain planned.

## Tile authoring and delivery

- [x] **Shared tile footprint and anchors** — Use measured room-kit PNG anchors in both runtime and workshop; one 128×64 logical diamond grid.
- [x] **Paint and erase room components** — Choose an asset and layer, place or erase cells, and rotate components.
- [x] **Four camera orientations** — Rotate the map while preserving world coordinates, picking and screen-relative movement.
- [x] **Room recipe import/export** — Keep visual placements and rotation in a validated JSON authoring recipe.
- [x] **Game-compatible tile export** — Export collision/surface data for authoring or a playable room with visual placements for runtime import.
- [x] **Play edited rooms without rebuilding** — Play this room or import playable JSON. C# validates bounds, assets, layers, actors and connectivity before starting a standalone room; full visual components persist in saves. A valid import replaces the active run.
- [ ] **Procedural playable campaign** — Generate connected rooms, objectives, enemy budgets and rewards through the same validated format.
- [ ] **Full Unity presentation parity** — Port the browser character sheets, effects, editor and narration UI into native Unity, then run Editor/Web export checks.

## Concept gallery

- [Choose a shape](../Web/wwwroot/assets/concepts/forms-and-stances.png) — Form selection, character sheets and stance tradeoffs. Illustrative names/bonuses may differ from the tested implementation.
- [Grow, equip, prepare](../Web/wwwroot/assets/concepts/progression-safe-room.png) — Concept treatment for now-playable stat allocation, separate skill practice, owned boxes and crafting. Consult the actual menus for supported numbers and recipes.
- [Every action has an answer](../Web/wwwroot/assets/concepts/combat-feedback.png) — Selected-ability information, separate move/action budgets, intent, impacts and compact AI feedback. Numbers are mock data.
- [Build the room](../Web/wwwroot/assets/concepts/tile-authoring.png) — Tile anchors, layers, piece rotation and camera rotation. Use the real exporter schema, not text drawn inside the concept image.
- [Hoarder](../Web/wwwroot/assets/concepts/boss-hoarder-concept.png) — Book 1 scenario concept: stockpile, giant human-ish boss and Scatterer minions. The separate playable scenario adapts this concept; art is not a screenshot or exact specification.
- [Juicer](../Web/wwwroot/assets/concepts/boss-juicer-concept.png) — Book 1 gym scenario concept: scaly boss and flaming weight plates. The separate playable scenario adapts this concept; art is not a screenshot or exact specification.
- [Ball of Swine](../Web/wwwroot/assets/concepts/boss-swine-concept.png) — Book 1 cooperative Speedbump scenario concept with Meadow Lark helpers. The separate playable scenario adapts this concept; art is not a screenshot or exact specification.

See [lore review](Lore-Mechanics-Review.md), [boss scenarios](Boss-Concepts.md), and [implementation plan](Mechanics-Plan.md).
