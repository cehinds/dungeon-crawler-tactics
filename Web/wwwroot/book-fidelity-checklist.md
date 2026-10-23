# Book fidelity and playability checklist

A source-linked mechanics review, seven GPT-generated concept sheets, and an implementation checklist. Checked means implemented in the browser build; unchecked means planned. Concept images are design targets, not screenshots or exact specifications.

The demo mixes early dungeon settings with later characters/classes. Lore examples stay within Books 1–4; linked fan pages may contain later spoilers. Form bonuses, stances, combat ranges and XP thresholds are tactical adaptations.

## Readable tactical combat

- [x] **Move and act in either order** — One move and one action per crawler; End Turn explicitly advances the party.
- [x] **Selected ability descriptions** — Persistent cost, range, target and effect text, plus a full details dialog for touch and keyboard.
- [x] **Complete ability book** — Expose personal, class, unlocked and equipment actions instead of relying on a few quick slots.
- [x] **Exact preview before committing** — Show HP, Mana, tags and stat-cap changes; cancel spends nothing.
- [x] **Enemy movement and declarations** — Play movement and action events with an enemy-phase banner and original narration.
- [x] **Impact layer above sprites** — Fire, projectiles, reaction effects and floating combat text draw after units and walls.
- [x] **Party turn state** — Separate move used, action used and turn finished; enemy team follows all finished allies.
- [ ] **Enemy intent before the next round** — Show prospective target lanes and interrupt conditions, not just declarations during playback.
- [ ] **Area effects and chain reactions** — Shared resolver must preview all affected cells, friendly fire and bounded spread.
- [ ] **Potion cooldowns** — Add readable cooldown/overuse rules with book-grounded terminology and tested balance.

## Characters, shapes and progression

- [x] **Katia chooses a form** — Baseline, Bulwark, Strider and Focused presets with explicit HP/Mana/movement tradeoffs. Tactical adaptations.
- [x] **Every crawler has a character sheet** — Inspect stats, current stance, skills, equipment, party level and XP; Mordecai remains an advisor.
- [x] **Three tactical stances** — Balanced, Defensive and Mobile. These are game rules, not a canonical universal stance system.
- [x] **Party levels and skill unlocks** — Current compact demo reaches levels 1–4 and unlocks personal skills at authored thresholds.
- [x] **Equipment changes actual stats** — Weapon, armor and charm ownership, granted abilities and save persistence.
- [x] **All eight characters have directional walking art** — Four directions with idle and walking frames; base identities retained.
- [ ] **Distinct form animation sets** — Author a full directional/attack set per Katia shape, with a mass/silhouette budget. Current form stats do not imply new authored sprites.
- [ ] **Five core stats and allocated points** — Strength, Intelligence, Constitution, Dexterity, Charisma; separate saved points, with race/class timing made explicit.
- [ ] **Individual skill practice levels** — Track use/training separately from crawler XP; define caps and gear boosts without copying unexplained formulas.
- [ ] **Race and class milestone selection** — Introduce prerequisite previews and save-safe choices at a deliberate campaign stage.
- [ ] **Katia momentum and engineering** — Model equipped mass, Rush, bracing and carried platforms; verify timing and costs before authoring.
- [ ] **Expanded personal kits** — Carl traps/improvised explosives, Donut spell progression and social abilities, Mongo companion commands; each needs resolver support and source notes.

## Narrator, exploration and rewards

- [x] **Compact original System narration** — Queue committed actor/action/target and impact messages; dismiss and revisit history.
- [x] **NEW ACHIEVEMENT notices** — Five first-time milestones are saved per run; previews and reloads do not repeatedly award them.
- [x] **Protected preparation hub** — Safe-room Rest, equipment and skills access; actual HP/Mana restoration.
- [x] **Objective journal and discoveries** — Floor progress, encounter door, optional caches/notes and enemy defeats reflect game state.
- [ ] **Loot-box inventory and safe-room opening** — Pending boxes, rarity, deterministic rewards, collection preview and a visible empty state.
- [ ] **Crafting and workbench recipes** — Simple combinations versus specialized benches; materials, recipe previews and consumed inputs.
- [ ] **Audience and sponsor rewards** — Visible, bounded reward rules tied to achievements and choices; avoid hidden compulsory popularity gates.
- [ ] **Companion progression** — Separate Mongo/pet growth, gear and commands from crawler race/class allocation.
- [ ] **Floor clock and descent pressure** — Communicate collapse risk and evacuation objectives without punishing time spent in menus.
- [ ] **Interactive environmental puzzles** — Levers, doors, destructible supports, traps and discovery descriptions must affect shared state.

## Book-grounded boss scenarios — concepts, not playable yet

- [ ] **Hoarder: stockpile and Scatterers** — Book 1 boss identity; propose capped minions, garbage lanes, telegraphed emergence and explosive opportunities.
- [ ] **Juicer: gym and flaming weight plates** — Book 1 scaly gym boss; propose visible throw lanes, cover interception and equipment obstacles.
- [ ] **Ball of Swine: cooperative Speedbump** — Book 1 borough threat; propose rolling lanes, carried parts, shared barricade construction and Meadow Lark assistance.
- [ ] **Scenario briefing and adaptation labels** — Show source setting, current objective, special interaction and invented rules before entry.
- [ ] **Large-unit occupancy and boss phases** — Shared footprint/collision rules, deterministic phase transitions, clear defeat/retry and alternate recovery paths.

## Tile authoring and delivery

- [x] **Shared tile footprint and anchors** — Use measured room-kit PNG anchors in both runtime and workshop; one 128×64 logical diamond grid.
- [x] **Paint and erase room components** — Choose an asset and layer, place or erase cells, and rotate components.
- [x] **Four camera orientations** — Rotate the map while preserving world coordinates, picking and screen-relative movement.
- [x] **Room recipe import/export** — Keep visual placements and rotation in a validated JSON authoring recipe.
- [x] **Game-compatible tile export** — Export encounter width, height and tiles; merge into authored game data, validate spawns and rebuild.
- [ ] **Play edited maps without rebuilding** — A validated runtime map-import path and full visual recipe persistence are still needed.
- [ ] **Procedural playable campaign** — Generate connected rooms, objectives, enemy budgets and rewards through the same validated format.
- [ ] **Full Unity presentation parity** — Port the browser character sheets, effects, editor and narration UI into native Unity, then run Editor/Web export checks.

## Concept gallery

- [Choose a shape](assets/concepts/forms-and-stances.png) — Form selection, character sheets and stance tradeoffs. Illustrative names/bonuses may differ from the tested implementation.
- [Grow, equip, prepare](assets/concepts/progression-safe-room.png) — Future five-stat allocation, separate skill practice, loot boxes and crafting. These planned systems are not yet playable.
- [Every action has an answer](assets/concepts/combat-feedback.png) — Selected-ability information, separate move/action budgets, intent, impacts and compact AI feedback. Numbers are mock data.
- [Build the room](assets/concepts/tile-authoring.png) — Tile anchors, layers, piece rotation and camera rotation. Use the real exporter schema, not text drawn inside the concept image.
- [Hoarder](assets/concepts/boss-hoarder-concept.png) — Book 1 scenario concept: stockpile, giant human-ish boss and Scatterer minions. Not a playable encounter.
- [Juicer](assets/concepts/boss-juicer-concept.png) — Book 1 gym scenario concept: scaly boss and flaming weight plates. Not a playable encounter.
- [Ball of Swine](assets/concepts/boss-swine-concept.png) — Book 1 cooperative Speedbump scenario concept with Meadow Lark helpers. Not a playable encounter.

See [lore review](https://github.com/cehinds/dungeon-crawler-tactics/blob/main/Docs/Lore-Mechanics-Review.md), [boss scenarios](https://github.com/cehinds/dungeon-crawler-tactics/blob/main/Docs/Boss-Concepts.md), and [implementation plan](https://github.com/cehinds/dungeon-crawler-tactics/blob/main/Docs/Mechanics-Plan.md).
