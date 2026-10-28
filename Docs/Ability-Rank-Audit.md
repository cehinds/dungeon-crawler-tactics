# Ability rank audit

Research scope: published samples and chapter-cited secondary references. This audit separates book-backed rules from game tuning. The novels do not provide a complete 1–20 table for each ability, so exact missing ranks remain unknown. Existing sourced proposals in [Research/classes-skills.json](../Research/classes-skills.json) correctly label their 1–20 rows as adaptations; do not present interpolated values as canon.

## What the books establish

The publisher’s authorized [Book 2 sample](https://cdn.penguin.co.uk/dam-assets/books/9780241816219/9780241816219-sample.pdf) establishes use-based growth that slows at high ranks and Primal access to rank 20 (PDF pp.29–30). It also describes a class-specific Dodge exception (p.16), distinct Cockroach milestones (p.20), and an exceptional Fireball power increase above 15 (pp.29–30). These support permission gates and ability-specific milestones, not universal rank-20 access or a universal damage multiplier.

| Ability / rule | Evidence and rank anchors | Evidence class |
|---|---|---|
| Magic Missile | Ranks 1–4 cost 5 MP; rank 5 allows a 3–6 MP cast choice; rank 10 may ignite the target. Donut's rank 9 on Floor 3 is also stated in the publisher sample. No verified rank-15 effect table. | Ranks 5/10 and early cost are secondary DCC Database summaries citing Book 1 ch.23 and Book 2 ch.6; rank 9 is explicit primary sample (p.29/printed19). |
| Powerful Strike | A secondary reference reports Carl receives it at rank 3, gains +1 from gear, later reaches 13 from an upgraded item, and gets further rank increases from equipment. The skill multiplies unarmed damage by skill level in its cited description. Exact rank-by-rank breakpoints, especially 15–20, are not verified. | Secondary, chapter-located; no direct authorized excerpt for those numeric anchors in this research. |
| Puddle Jumper | Secondary summaries report rank 1's 10-second delay, rank 5's 2-second delay and altered line-of-sight condition, and rank 15 approaching Teleport strength. Its base 20 MP, five-hour cooldown, and transport of caster plus up to three others are also secondary summaries, not verified here from a primary excerpt. | Secondary Fandom page; explicit rank anchors, but lower confidence than publisher sample. Treat exact timing as provisional pending primary-text check. |
| Heal Critter | Rank 1 is reported at the start of Floor 3; it heals a nearby pet-class mob or dungeon familiar. No healing amount or later-rank changes established. It can be learned from a tome; the Book 1 scroll is single-use. | Secondary DCC Database citing Book 2 ch.5 and Book 1; target restriction is well-supported, rank progression unknown. |
| Clockwork Triplicate | Donut receives it on Floor 3 and uses it on Mongo. It duplicates pets/minions. No numeric rank progression or scaling table verified. | Secondary index / chapter locators; the current game's copies, HP, lifespan, and control are adaptation. |
| Katia Shapeshift; Mongo | Katia's shapeshifting is a race ability, constrained by mass and does not grant copied powers; no rank table verified. Mongo is Donut's pet/companion, not a crawler skill progression case. Bite/Pounce values and independent combat ranks are game-authored. | Secondary character summaries and existing [signature-moves audit](Signature-Moves-Audit.md); explicit gaps. |

Sources for ability-specific anchors: [Magic Missile](https://www.dccdatabase.com/wiki/magic_missile/), [Powerful Strike](https://dungeon-crawler-carl.fandom.com/wiki/Powerful_Strike_Skill), [Puddle Jumper](https://dungeon-crawler-carl.fandom.com/wiki/Puddle_Jumper_Spell), [Heal Critter](https://www.dccdatabase.com/wiki/heal_critter/), [Clockwork Triplicate](https://www.dccfansite.com/entry/clockwork-triplicate/), and [Katia](https://www.novelpantheon.com/novels/dungeon-crawler-carl/characters/katia). Fan indexes are secondary and chapter references do not replace checking the text.

## Corrections and design implications

- Keep skill rank, crawler level, class level, equipped-item bonuses, temporary bonuses, and effective cast level as distinct values. Later material shows displayed Magic Missile at 15 resolving effectively at 16 through a separate benefit; that is not ordinary trained rank progression ([secondary guide](https://manatoastmedia.com/levels-stats-races-classes/)).
- Gate rank 16–20 behind an explicit race/class or item permission, or a deliberate game-wide adaptation. Primal is a race, and select classes can unlock individual skills to 20. Do not infer that every character or every spell can reach 20.
- Reconcile “practice raises use-trained abilities” with the current game's action ownership: repeated successful uses can advance an ability slowly, while training rooms, gear, potions, or grants give direct progression. Avoid making consumable use train its own item-action rank unless that is an explicit game rule.
- Preserve target and action identity: Heal Critter is pet/familiar-specific; Puddle Jumper transports a small group with delay/cooldown in cited canon; Clockwork Triplicate targets pets/minions; Katia's shift changes form without copied powers. Current broader targeting and instant tile movement must be labeled as tactical adaptations.
- Powerful Strike's canonical scale is a damage multiplier, while the current game action has fixed damage and push. A matched name does not validate that tactical effect.

## Recommended 20-rank tactical adaptation

Use twenty explicit authored rows per ability, with `provenance: proposed_game_adaptation` and canonical-effect evidence kept in a separate optional field. Rank 1 is the current game baseline, not a claimed canonical value. Use this shared pacing as a content-authoring guide, then express numbers in data rather than a hidden universal multiplier:

| Rank rows | Tactical adaptation guidance |
|---|---|
| 1–4 | Baseline then small, bounded potency gains; no new target types or free area attacks. Successful practice is the ordinary route to these ranks. |
| 5 | First named feature tier. Magic Missile may gain a selectable expenditure mode; Puddle Jumper may shorten cast delay. Apply those as source-inspired adaptations only to the matching abilities. |
| 6–9 | Gradual potency/cost improvements; retain each ability's existing action and target contract. |
| 10 | Second feature tier. Magic Missile may add a low-probability ignition rider; use a data-driven status chance and do not claim a canonical formula. |
| 11–14 | Slower gains to reflect the documented training slog after roughly 10–11. Keep effects legible and avoid stacking new mechanics every rank. |
| 15 | Ordinary mastery ceiling. Tune this as a strong tactical endpoint, but leave the exact effect ability-specific; the novels do not define a universal rank-15 effect. |
| 16 | Require a specific cap unlock. Reserve any dramatic discontinuity for a supported matching ability; Fireball's fourfold example is not evidence for Magic Missile, Punch, healing, or all skills. |
| 17–19 | Rare improvements under the same permission, with small increments or one ability-specific refinement. Keep these rows distinct and reviewable. |
| 20 | Primal/explicit-unlock endpoint. Give each ability an authored capstone that preserves its established tactical identity; do not apply the Fireball volcano example to unrelated skills. |

If a fully algorithmic curve is needed for all twenty rows, keep the existing bounded curve in the JSON as a clearly labelled balance adaptation, and add typed, ability-specific rank-5/10/16/20 overrides only where desired. Do not claim that generated ranks 2–4, 6–9, 11–14, or 17–19 reproduce novel values. A rank increase should resolve through one shared effective-rank calculation for preview, combat, AI, saves, and tooltips; equipment and temporary bonuses should not silently train or double-apply to that rank.

## Implemented pass

- [x] Explicit profiles cover all 95 authored abilities; the shared engine supplies twenty rank rows.
- [x] Learned ability use and authored form changes earn saved practice; cancellation and consumable use do not.
- [x] Range, push, summon statistics and exclusive ranked-tag families can change at milestones.
- [x] Magic Missile has an adapted rank-10 Burning rider; Heal Critter enforces pet-only targeting.
- [x] Current rank, cap, progress and per-rank effects are visible in the game, with source notes separated from tuning.
- [ ] Exact missing novel ranks, selectable Missile Mana power, group teleport/cooldowns, mass-based shapeshifting and a complete race/class permission system.

See [Progression](Progression.md) for actual behavior and explicit limits. The development tables are effect summaries from the shared resolver model, not copied book descriptions.
