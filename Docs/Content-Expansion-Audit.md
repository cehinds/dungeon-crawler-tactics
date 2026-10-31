# Content expansion audit: runtime inventory and source gaps

Updated 2026-10-30. This is a planning audit only; no runtime data was changed. The complete machine-readable mapping is [broadcast-content-audit.json](../Research/broadcast-content-audit.json).

## Status key

- [x] **Implemented:** behavior exists in the shared runtime.
- [x] **Adapted:** game-authored behavior inspired by source material; numbers and rules are not asserted as canon.
- [ ] **Proposed:** planner candidate, not implemented.
- [ ] **Unknown:** available evidence does not establish the ability, weakness, rank value, or rule.

## Full runtime inventory

The recursive inventory covers every class-bearing enemy object in `game-content.json`: 64 unique definitions across 10 legacy encounter entries, 6 scenario units, 22 expedition units, and 26 journey-floor units. It records each definition's data path, class abilities with their target/range/cost/tags/effects, authored unit tags, and source provenance. The 18 journey-floor records are listed separately; several reserved floors have no enemy objects yet. All six expeditions and all three scenarios are represented.

Neighborhood data has four interaction records with eight options, including merchant, trap, rescue, and preparation interactions. It contains no class-bearing hostile unit definitions. The audit includes that domain explicitly so the enemy count does not silently omit neighborhood content.

The machine inventory reports 95 combat abilities, 148 combat classes, and 142 selectable class trees. Its runtime rank audit confirms that all 95 abilities have `development.practice.abilityProfiles` and can progress through rank 20. The 88-entry `Research/classes-skills.json` mapping and its 1,760 proposed rank rows are a documentation coverage set, not a count of runtime profiles. Seven unmapped research IDs each have their actual runtime profile, milestone rows, game tuning, and source/unknown notes included in the JSON. They are a research-mapping gap, not missing rank implementation.

## Weaknesses, interrupts, and scenario objectives

Legacy encounter units have no authored elemental weakness or damage-vulnerability multiplier. `RulesEngine` can check `EntityState.Immunities` against incoming action tags, but the current authored enemy definitions do not populate such immunities. An attack tag, an enemy's `status.wet`, and a source-described weakness are different things.

The three boss scenarios do have special mechanics; these should not be lost under the legacy-enemy finding:

- **Hoarder — implemented adaptation:** visible emergence, a cap on active Scatterers, interrupt through Burning/Frozen/Shocked or burning terrain, and an adjacent garbage-lane action. These interrupt summoning pressure; they do not increase damage against the Hoarder.
- **Juicer — implemented adaptation:** a locked flaming-plate lane, interruption through Frozen/Shocked or displacement, and a toppled bench that intercepts one plate. The source-described vulnerable veins are **not** implemented as a weak-point target or damage bonus.
- **Ball of Swine — implemented adaptation:** a warned rolling route and buildable Speedbump that stops and damages the boss. This is a scenario objective interaction, not an elemental weakness.

These behaviors are supported by [Boss-Concepts.md](Boss-Concepts.md) and `GameSession.Scenarios.cs`. The separate research catalog still records source-described weakness-like situations—Juicer veins, the Ball of Swine Speedbump, Brindle Grub corpse destruction, Pestiferous Vine poison, and Station Mimic mass loss—as source notes, not as runtime weakness flags.

## Rank and source evidence

- [x] **Implemented/adapted:** 95 runtime profiles with rank 1–20 progression, bounded per-rank effects, and authored milestone rows. These values are game balance.
- [x] **Documented:** 88 research mappings with 1,760 proposed rank rows. The seven absent mappings and exact runtime profile records are in the machine-readable audit.
- [ ] **Unknown:** complete canonical 1–20 tables and universal rank-20 permission. Existing evidence only supports selected breakpoints and examples.
- [ ] **Proposed:** expand research coverage for the seven omitted ability IDs, preserving each runtime profile separately from canonical evidence.

The source catalog and per-enemy provenance use references already recorded in [Research-Floors-Enemies.md](Research-Floors-Enemies.md), [Research-Classes-Skills.md](Research-Classes-Skills.md), and [Ability-Rank-Audit.md](Ability-Rank-Audit.md). Fresh retrieval attempts for selected fan and publisher URLs returned a 403 from the network tunnel; no fresh page text is claimed here.

Publisher-series labels are corrected here: *The Butcher’s Masquerade* is novel 5 (associated with Floor 6); *The Eye of the Bedlam Bride* is novel 6 (associated with Floor 8). The cited publisher catalog pages identify the works, while the pre-existing floor/source research supplies the floor association. The audit does not infer novel number from a publisher catalog number.

## Prioritized planner batch

The first three proposals from the previous version were already present as playable scenario adaptations, so they now show their implemented status and exact boundary. The remaining entries are structured in the JSON with proposed role, candidate behavior, telegraph, tags/effect family, source IDs, and explicit unknowns.

| Priority | Candidate | Status | Evidence boundary |
|---:|---|---|---|
| 1 | Hoarder emergence pressure | [x] Implemented adaptation | Scatterer emergence is source-described; cap, warning, and interruption are game rules. [Hoarder](https://www.dccdatabase.com/wiki/hoarder/) |
| 2 | Juicer lane pressure / optional weak-point follow-up | [x] Lane/cover adaptation; [ ] weak point proposed | Flaming plates and vulnerable veins are described; lane forecast and cover are adapted; vein vulnerability does not resolve in game. [Juicer](https://www.dccdatabase.com/wiki/juicer/) |
| 3 | Ball of Swine Speedbump | [x] Implemented adaptation | Speedbump collaboration is described; route and construction values are game tuning. [Ball of Swine](https://dungeon-crawler-carl.fandom.com/wiki/Ball_of_Swine) |
| 4 | Brindle Grub growth clock | [ ] Proposed | Corpse destruction inhibits growth but does not stop spawning; timing and stages are unknown. [Brindle Grub](https://www.dccdatabase.com/wiki/brindle_grub/) |
| 5 | Pestiferous Vine poison/cure tradeoff | [ ] Proposed | Delayed poison and cure interaction are source-described; exact timing and effects are unknown. [Vine](https://www.dccdatabase.com/wiki/pestiferous_vine/) |
| 6 | Station Mimic mass threshold | [ ] Proposed | Mass removal stopping healing/transformation is described; game rule and numeric threshold mapping remain unknown. [Mimic](https://www.dccdatabase.com/wiki/station_mimic/) |
| 7 | Danger Dingo pack flanker | [ ] Proposed | Dingoes and occasional Kobold riders are described; pounce/pack actions are invention. [Dingo](https://www.dccdatabase.com/wiki/danger_dingo/) |
| 8 | Janitor Ghoul provocation | [ ] Proposed | Bleeding, litter, and trespass are described as triggers; tactical thresholds are unknown. [Ghoul](https://www.dccdatabase.com/wiki/jikininki_janitor_ghouls/) |
| 9 | Hunter equipment pressure | [ ] Proposed | Hunters pursuing equipment are described; ability kits and weaknesses are unknown. [Hunters](https://dungeon-crawler-carl.fandom.com/wiki/Hunters), [publisher novel 5](https://www.penguinrandomhouse.com/books/788552/the-butchers-masquerade-by-matt-dinniman/paperback/) |
| 10 | Floor 8 T’Ghee capture objective | [ ] Proposed | Publisher description says six monsters are collected as cards; capture rules, odds, and stats are unknown. [Publisher novel 6](https://www.penguinrandomhouse.com/books/788703/the-eye-of-the-bedlam-bride-by-matt-dinniman/hardcover/), [floor summary](https://www.dccdatabase.com/wiki/eighth_floor/) |
| 11 | Floor 5 air/water roster research | [ ] Proposed research | Night Fright and Concierge Shark placements are recorded; attacks and weaknesses need fuller evidence. [Floor 5](https://dungeon-crawler-carl.fandom.com/wiki/Fifth_Floor) |
| 12 | Magic Missile breakpoint mapping | [ ] Proposed research | Rank-5 spend choices and possible rank-10 ignition are cited; exact damage and ignition chance are unknown. [DCC Database](https://www.dccdatabase.com/wiki/magic_missile/), [publisher novel 2 sample](https://cdn.penguin.co.uk/dam-assets/books/9780241816219/9780241816219-sample.pdf) |

For the next implementation batch, choose one item whose telegraph and outcome can be expressed with existing resolver effects. Any proposed damage weakness, mass threshold, growth clock, capture state, or poison cure interaction should be called out as a separate mechanic if it requires new resolver support.
