# Completion checklist

Use this as the working status list for the current playable scope. It is intentionally more specific than the overview in `README.md`. **Implemented** means the shared source or browser UI contains the behavior; it does not mean it was visually inspected in a screenshot or verified in Unity. **Verified** means a named check or playthrough was actually run and recorded. Keep those claims separate. Checkbox items marked pending are planned or need follow-up evidence; do not check anticipated work.

The live shared-C# source and authored JSON are the implementation reference. `Docs/PlayableGame.md` describes current behavior and delivery limits; `Docs/Book-Fidelity-Checklist.md` tracks fidelity-oriented mechanics. This checklist captures the full active finish scope, including the defined floors 1–8 story route. Floors 9–18 are outside the current playable scope.

## Reference fidelity and adaptation boundaries

- [x] Source-linked survey of classes, floors, enemies, skills and housing is published in the lore codex and research documents.
- [x] Tabletop research distinguishes official product descriptions from secondary reports and labels game adaptations.
- [x] Current design documentation identifies invented formulas, mixed timelines, and unsupported book systems instead of presenting them as canon.
- [ ] Recheck source citations and spoiler boundaries when expanding beyond the current Books 1–4 lore examples.
- [ ] Verify reported tabletop mechanics against the primary rules before implementing them as faithful rules.
- [ ] Add race selection/milestone choices with source-backed prerequisites and save-safe forecasts. Floor-3 class selection is already implemented; this item is the remaining race progression work.

## Browser battle readability and animation

- [x] Shared C# resolves movement, actions, exact previews, confirmation/cancellation, party turns, enemy turns and bounded tag reactions.
- [x] Browser battle presentation displays the isometric map, party/enemy sprites, four map rotations, path preview, responsive action menu, target counts, confirmation forecasts, turn banners, and narration.
- [x] Character sprites include four-direction idle and walking frames for all eight field characters; attacks, hits, projectiles, reactions and floating feedback are animated/presented in browser source.
- [x] Compact HUD surfaces HP, Mana, movement, conditions, range and forecasts; action selection exposes costs, categories and legal-target counts.
- [x] Capture and review HUD, ability chooser, target forecast/cancel, enemy phase, safe-room, equipment, skills and form menus at 1440×900 and 390×844. See [release QA](https://github.com/cehinds/dungeon-crawler-tactics/blob/main/Docs/Finish-QA.md).
- [ ] Complete the same current-build visual walkthrough for every house upgrade and every story floor.
- [x] Compare the current HUD/menu captures with the reference; enlarge actions and sprites, replace the confusing Powerful Strike icon, and fix camp advisor overlap. This is an improved playable rendering, not pixel-for-pixel screenshot parity.
- [x] Author and validate three alternate Katia directional idle/walk sets: 36 distinct frames, measured anchors, actual form-ID selection and committed-form browser checks.
- [ ] Author separate alternate-form attack/hit frames; current form attacks use presentation lunges.
- [ ] Add generic multi-cell bosses, wide area effects, line of sight/elevation, and spreading reaction chains; current scenarios have bounded hand-authored lanes and one-tile bosses.
- [ ] Add usable potion cooldown/overuse rules and a universal enemy-intent planner if retained in product scope.

## Level and training progression through level 50

- [x] Shared cumulative XP thresholds are data-authored for levels 1–50: the legacy levels keep 0, 30, 70 and 120 XP; the full table ends at 59,431 XP for level 50.
- [x] Each party level adds +3 maximum HP and +1 maximum Mana; each deployable crawler earns three stat points per level, banked until story floor 3. These formulas are adaptations.
- [x] Every crawler has personal abilities authored at levels 2 and 3. Available class abilities also depend on the selected class; personal abilities persist through class changes.
- [x] Personal skill trees, per-crawler class trees, node prerequisites/forecasts and saved purchases are implemented. Each class tree has two branches and nodes at levels 1, 5, 10, 20, 30, 40 and 50; seven points total cannot fill both branches.
- [x] Committed non-item ability uses increase that crawler's individual practice rank. Rank 2 starts at 3 uses and rank 3 at 8; later thresholds rise. Most abilities cap at 15, while configured Primal eligibility reaches 20 after floor 3. Paid Training Room practice is limited by floor and crawler.
- [x] Equipment, shapes, stances and allocated stats affect actual shared-core forecasts/resolution; development purchases and training persist in saves.
- [ ] Play and record the level after every floor reward. Current XP arithmetic jumps from level 4 after floor 1 to level 50 by floor 6; decide whether to rebalance rewards/thresholds so each milestone has room to matter. The source threshold table alone is not a pacing test.
- [ ] Verify levels 1–50, each personal unlock, all seven class-node milestone tiers, stat-point banking/spending, rank progression to 20 where eligible, save/reload and paid training against actual browser UI.
- [x] Add a character-sheet Progress section with next-level XP, personal unlock, class milestones, banked/spendable points and closest practiced ranks. Verified desktop/phone.
- [ ] Audit class tree node effects and ability availability for all selectable kits; class tree data can be authored without guaranteeing that every branch is balanced, meaningful or well explained.
- [ ] Decide whether all 50 levels need authored story/reward beats, class-node grants or quests. Current implementation has a numeric XP curve and seven class-node tiers, not fifty individually scripted level chapters.

## Party, progression and house

- [x] Story party progression supports shared XP through level 50; class-tree progression has authored nodes through level 50. Numerical curves and grants are game adaptations.
- [x] Story class changes and manual stat allocation unlock on floor 3; earlier floors bank allocation points. The existing legacy campaign remains available.
- [x] Personal trees and per-ability practice ranks are saved; configured skill eligibility can reach rank 20 after floor 3, while most skills cap at 15.
- [x] Equipment, forms, stances, stat allocation, class trees, crafting, fixed-content boxes and party save/import/export are implemented in shared source/browser flows.
- [x] Shared party house supports floor-4 purchase, eight private bedrooms, facilities, social history and eligible personal club credentials. Gold and tactical benefits are identified as adaptations.
- [ ] Add separate Mongo/companion growth, equipment and command progression.
- [ ] Complete screenshot review of class choice at floor 3, class tree node forecasts, level-up notices, house purchase, room/facility states, and social/club displays.
- [ ] Decide whether additional personal kits (Carl traps/explosives, Donut spell/social progression, Mongo commands) are needed for the scoped story, then author source notes and mechanics where they are.

## Story route: floors 1–8

- [x] Expand six approaches (floors 1, 2, 4, 5, 6, 8) to distinct connected 17×13 maps with 24 additional discovery points, including 12 functional caches. Preserve floor 3 and existing story objectives. [Level details](https://github.com/cehinds/dungeon-crawler-tactics/blob/main/Docs/Story-Levels.md).

- [x] Eight-floor journey registry is authored; floors 9–18 are visibly reserved/locked with no encounters.
- [x] Current data defines seven battles plus the deliberate floor-7 bypass. Each battle has one authored encounter board, a fixed enemy roster and an XP award; floors 4 and 5 add required route/beacon discovery gates, and floor 8 adds capture objectives. Victory uses the general sponsor-reward selection flow; per-floor bespoke loot/reward scenes are not authored.
- [x] Current floor themes, adaptations and enemy counts are in `game-content.json`; see the floor-by-floor inventory below. These are authored definitions, not proof of a complete story adaptation or a completed playthrough.
- [x] Floor 3 gates class changes and banked stat allocation; floor 4 gates house purchase; Lantern Row is an optional floor-3 discovery and a separate safe-room launch.
- [x] One shared safe-room/camp supports party changes, rest, equipment, skills, development and journey entry. Optional modes preserve and restore the campaign checkpoint.
- [x] Three separate boss scenarios (Hoarder, Juicer, Ball of Swine), six optional training expeditions and Lantern Row are authored as isolated playable modes. The seven story battles do not currently define a separate named boss encounter for each floor.
- [ ] Complete a fresh end-to-end browser playthrough of floors 1–8, including floor-7 bypass, floor-8 captures, reloads, progression/house gates and Lantern Row return. Record build/date and blockers.
- [ ] Review every floor's board geometry, enemy movement, encounter difficulty, objectives, safe-room transition, supplies, sponsor rewards and level pacing in actual play; the current JSON contains one board and one battle per encounter, not a fully written/QAed multi-room adventure per floor.
- [ ] Make a deliberate floor-level content plan for any missing exploration rooms, named bosses, dialogue, dedicated safe-room scenes, side quests and reward beats. The shared safe-room hub is implemented, but no separate safe room is authored inside each floor; the story boards are single encounters. Do not infer missing content from a floor label or enemy roster.
- [ ] Expand to floors 9–18 only if scope changes; do not imply they are part of the playable route now.

### Current floor data and remaining authoring/QA

| Floor | What is actually authored | What still needs a design/QA decision |
|---|---|---|
| 1 — First Floor | One 10×8 tutorial battle; three adapted maintenance/coolant rats and a sentry; 120 XP. | Verify movement/action teaching, text clarity, supplies and that difficulty supports a new party. No separate story boss is authored here. |
| 2 — Second Floor | One 12×9 sewer battle; two coolant sludges and one arc sentry; 550 XP. | Verify this teaches the next mechanics and bridges level gains; canonical grub spawning is explicitly not simulated. |
| 3 — Third Floor | One 14×10 Over City battle; two spore wardens, sludge and mauler; 2,400 XP. Class changes/stat spending unlock; optional Lantern Row and a saved clue are authored. | Play through class unlock, optional neighborhood discovery/return, clue, supplies and encounter. Determine whether this floor needs a named story boss or more neighborhood content. |
| 4 — Fourth Floor | One 14×11 Iron Tangle battle; three sentries and a mauler; required route-lever discovery; 7,000 XP. House becomes purchasable. | Verify route lever visibility/approach, transition, first house purchase economy and encounter challenge. No railway simulation or six-hour clock exists. |
| 5 — Fifth Floor | One 12×10 Four Beacon Bubble battle; two rimeguards and a mauler; four required exploration beacons; 18,000 XP. | Verify that all four beacons are discoverable and the objective reads clearly. This is not four authored castle campaigns. |
| 6 — Sixth Floor | One 13×10 Hunting Grounds battle; two cinder stalkers and a mauler; 35,000 XP. | Verify pursuit/intent readability, enemy roster balance and how the XP award interacts with level 50. Enemies are adaptations, not identified canonical hunters. |
| 7 — Seventh Floor | Explicit destroyed Great Race bypass; no battle or XP award. | Verify the narrative transition and floor 8 unlock in a real run. Do not add a fabricated Great Race battle. |
| 8 — Eighth Floor | One 15×11 capture battle; six adapted enemies; capture six weakened targets within three tiles; defeated targets reform weakened; 55,615 XP. | Verify all six captures and reload/resume, final reward and campaign completion. This is not the full T’Ghee card game or a multi-encounter finale. |

The seven XP awards sum to 118,685. Applying the authored cumulative thresholds to a fresh party yields levels 4, 10, 18, 27, 39 and 50 after victories on floors 1–6; floors 7–8 leave the party at 50. This arithmetic is visible directly in the JSON, but the steep jumps may overwhelm the intended progression. Decide whether those awards are intentional, then test actual XP granting, level notices, stat points, class points and challenge pacing after each victory. The source values are implemented; the progression experience is not yet accepted as balanced.

## Content authoring and data quality

- [x] Stable IDs connect JSON-authored classes, abilities, tags/reactions, roster, stats, maps, enemies, rewards, equipment, progression, journey and housing.
- [x] Strict schemas, content validators, runtime validation and authoring documentation define supported extension paths.
- [x] Existing class/skill trees, floor data, enemies and housing research are represented in authored data; new combinations of existing effects can be data-authored.
- [x] Run shared C# tests (598), Python checks (83), strict content validators, form art checks and story connectivity checks. See `Docs/Validation.md`.
- [x] Regenerate the playable catalog: 90 abilities, 10 consumables, four recipes; verify researched catalog output and 36 new form frames.
- [ ] Keep data/copy aligned when mechanics change; remove historical planning statements that now contradict implementation.
- [ ] Add a typed shared-core effect only when necessary, including validation, preview support, save implications and meaningful behavior coverage.

## Tabletop-inspired work still planned

- [x] Saved, bounded AI Favor with exact spend preview and no phase-order changes. Earn/spend/cancel/reload verified through actual browser UI at both widths.
- [x] Three contextual sponsor offers with explicit conditions, rewards, repeat limits, saved receipts and forecast delivery amounts.
- [ ] Broader skill-based noncombat interactions with a fallback route where a skill is unavailable.
- [x] Placeable Coolant and Shock snares: safe-room recipes, empty-tile placement, any-team single-entry effects, saved surfaces, visible armed markers and activation feedback.
- [ ] Material-tag recipe combinations and arbitrary improvised inventions; current four recipes have fixed ingredients and outputs.
- [ ] Exploration clues tied to visible, multi-solution boss mechanisms and round-based consequences.
- [x] House social display includes actual sponsor delivery receipts and local challenge history.
- [ ] Audience popularity progression, viewer/follower counts, talk shows and tiered sponsor consequences.

## Unity parity and delivery

- [x] Canonical shared rules/data are in `UnityPackage`; `UnityProject` is generated from that source. Browser delivery runs the same C# rules through WebAssembly.
- [x] Native Unity source and scene/build tooling exist; Unity presenter has the updated shared rules and Mana labels.
- [ ] Port the current browser isometric battle, animation/effects, HUD/modals, house, journey, narration and room-authoring flows to Unity. The Unity presenter remains the earlier IMGUI implementation with original texture fallbacks.
- [ ] Open the project in Unity 6, generate/open the playable scene, run Play Mode across battle and progression flows, and record the editor version and results.
- [ ] Build and launch a Unity Web export with installed Web Build Support; record browser/runtime checks. A shared-C# browser build is not evidence of a Unity Web export.
- [ ] Verify native/mobile layouts only on the relevant Unity targets; current browser responsiveness does not establish Unity mobile support.

## Evidence and screenshot status

- [x] Capture fresh Chromium desktop/phone screenshots for this tested release source; see [release QA](https://github.com/cehinds/dungeon-crawler-tactics/blob/main/Docs/Finish-QA.md). Deployment status is recorded separately.
- [ ] Compare screenshots against the concept gallery in `Docs/Book-Fidelity-Checklist.md`. Those images are illustrative mockups, not evidence that the product currently matches them pixel-for-pixel.
- [ ] Record current Unity screenshots separately after actual Editor runs; browser screenshots cannot establish Unity parity.
- [ ] Update checked statuses only after inspecting the current behavior or running the stated validation. Keep implementation claims and visual/test evidence distinct.
