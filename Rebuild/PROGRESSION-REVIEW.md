# Floor One progression review

## Scope and evidence

This milestone adds progression data foundations for the current Floor One slice: 20 explicit crawler-level rows, the five currently authored skills with early rank rows, use-practice thresholds, and rewards for the five currently authored encounters. It does not complete a level 1–20 campaign. The current campaign has five encounters, including optional Hoarder and Juicer fights; more encounter and quest content is required to support a full run across all 20 levels.

`Rebuild/ReferenceData/sources/Ability-Rank-Audit.md` is an archived research artifact. Its “Implemented pass” section describes a prior, now-archived implementation and is not evidence of current runtime support. The active runtime source is `Web/wwwroot/data/floor-one-rpg.json`; this review records the current implemented runtime behavior and its remaining limits.

The publisher sample and retained research support use-based ability growth that slows at higher ranks, but they do not supply a complete 1–20 ability table or universal rank-20 access. Magic Missile's ranks 1–4 cost 5 mana and rank 5 supports 3/4/5/6 mana choices according to the cited secondary summaries; the rank-5 choice affordance is source-inspired, while this data's tactical power values and mana-to-power tuning are adaptations. Powerful Strike is reported at rank 3 in a secondary reference and described as multiplying unarmed damage; this data starts it at rank 3 but does not assert any exact canonical multiplier. All numeric level thresholds, stat gains, practice thresholds, tactical rank values, and encounter XP/gold rewards below are game adaptations.

## Authored progression choices

Crawler level thresholds are cumulative and explicitly listed from level 1 through 20. Level 1 is the starting baseline; subsequent rows apply small HP gains every level, occasional mana gains, and power gains on even levels. Armor does not grow through this table. The authored level-20 threshold is 12,160 XP. This curve is tuning for a future content expansion, not a claim that the present five-encounter slice awards enough XP to reach level 20.

Successful skill use advances the owning skill's practice tally by one. Skill rows provide explicit ranks 1–5 and increasing practice thresholds of 0, 3, 8, 15, and 24 uses from the start rank. Powerful Strike starts at rank 3 and provides rows 3–5 with 0, 6, and 16 uses. The practice rule and all exact thresholds are adapted pacing. Gear bonuses and effective rank remain separate from these authored trained-rank rows.

The authored encounter rewards preserve early pacing: false-guild 100 XP / 20 gold, workshop 160 / 30, Hoarder 220 / 15, Juicer 280 / 20, and Ball of Swine 340 / 45. These values are tuning, not canonical dungeon rewards. The current five-encounter route awards 1,100 XP and reaches level 6; the mandatory false-guild, workshop, and boss route awards 600 XP and reaches level 4. Five encounters cap this authored route at level 6; more content is needed for a complete level-1-to-20 progression arc.

## Migration and runtime limits

Version-1 saves rebase their XP onto the new cumulative curve while preserving crawler level and within-level progress; prior stats are preserved. There is no version-2 legacy-XP bypass. A legacy Powerful Strike rank below 3 is raised to 3 with a migration message. Legacy ranks above 5 remain recorded, but their available authored effects are capped at rank 5; this does not imply complete rank-20 effects.

Powerful Strike now derives its unarmed basis from Carl’s current Punch rank effect, then applies adapted rank-3/4/5 multipliers of 1.5/1.75/2 before target defenses. Strike root and rank power are zero; costs, starting rank, practice and Floor One permission remain unchanged. The multiplier identity follows secondary evidence; exact factors remain tactical tuning. Bomb already authored `effectRadius: 1`; the earlier single-target description was stale. Its radius-1 blast can hit allies, enemies and destructibles, now with explicit ground targeting alongside direct enemy/object IDs. Its 2-mana cost remains an adapted resource cost; charges and crafting remain outside this pass. Combat followthrough verification is tracked separately in `COMBAT-FOLLOWTHROUGH-CHECKLIST.md`.

## Review checklist

- [x] Exactly 20 explicit crawler-level rows with cumulative XP and stat gains.
- [x] Explicit rank rows for all five current skills; no later-book skills or classes added.
- [x] Magic Missile rank-5 mana choices represented; secondary evidence and tactical adaptations distinguished.
- [x] Powerful Strike begins at reported rank 3 without inventing a canonical multiplier.
- [x] XP and gold rewards authored for all five current encounters.
- [x] Archived 95-skill claims are not presented as current implementation.
- [x] Remaining campaign encounters needed for levels 1–20 are identified.
- [x] Version-1 XP rebasing and legacy rank handling are documented.
- [x] Current Powerful Strike multiplier tuning and Bomb area/resource scope are stated.
- [ ] Build enough additional encounters and quest content to support a full level-1-to-20 campaign.
- [x] Combat followthrough implements the described unarmed multiplier identity with explicitly adapted factors.
- [x] Correct the stale Bomb single-target description and expose ground targeting for its existing area blast.

## Prior progression milestone verification

These results belong to the earlier progression milestone; they do not verify the combat followthrough changes.

- [x] Core validation and progression/save migration tests passed, including all 20 XP rows, practiced ranks, rank-5 mana choices, bare-confirm behavior, migration, and rejected-save rollback.
- [x] Browser verification passed: natural first-victory progression reached level 2 and Punch rank 2 after three successful practices; canceled/invalid actions did not award practice. A migrated v1 fixture at Magic Missile rank 5 completed load, movement, enemy turns, and casts with 3- and 6-mana forecasts. Required floor-one browser controls, forecast, enemy turns, victory, save/load, responsive tabs, Node/inspector checks, and zero browser errors passed.
