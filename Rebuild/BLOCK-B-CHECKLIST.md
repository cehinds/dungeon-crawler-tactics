# Block B: explore, prepare and continue

Scope is exactly M05, M06, M08, M09 and M11. The acceptance loop is **Explore → encounter → rewards → safe room → prepare → continue** on the existing compact Floor One route.

## Authored content

- [x] Preserve the five active encounter IDs and enemy rosters: `false-guild`, `goblin-workshop`, `hoarder`, `juicer`, `ball-of-swine`. Required story order and optional branches are unchanged.
- [x] Add explicit, adapted item rewards: false Guild gives one Health Tonic and one Mana Draught; workshop one Health Tonic; Hoarder one Mega Tonic; Juicer one Mana Draught; boss one Health Tonic. Existing authored XP/gold rewards remain unchanged.
- [x] Reuse existing restorative item IDs. Safe-room offers provide one Health Tonic for 8 gold and one Mana Draught for 10 gold. First-encounter gold (20) permits another of each with 2 gold remaining.
- [x] Retain Carl and Donut only, source-grounded personal starting gear (one copy each in new-game inventory, no auto-equip or old-save backfill) with zero combat bonuses, owner restrictions as adaptations, and Carl’s unarmed constraint. Gear supports inspection/equip/unequip; this content does not deliver combat gear builds.
- [x] Mark service rules, prices, rewards and numeric effects as adaptations. Named safe-room settings, the survivor camp and mentioned-only locations retain distinct evidence. Existing `safe` object rest/save behavior is extended with preparation, not newly invented as absent before this block.
- [x] Preserve existing item IDs and references. No generic armor/charm loot, duplicate potion definitions, crafting/research activation, Floor 3 class activation or later house mechanics.

## Integrated acceptance evidence

The integrated Release build passed 15 C# test groups and the content validator CLI. Published-browser checks below exercised the final preparation loop; the final five-encounter route and exit also passed with zero browser errors.

- [x] Explore with reachable interactions, a current objective and a route back to a safe room; enter the first encounter and observe enemy responses.
- [x] Review the first victory’s XP, gold and items, then use Continue exactly once. Core regression covers reward-once behavior and save/load rejection paths.
- [x] Reach an actual `safe` object, rest, save, buy a Health Tonic for 8 gold and load the resulting checkpoint. Camp/source evidence alone does not grant services.
- [x] Select a crawler using native keyboard controls; inspect personal gear, equip/unequip it and verify owner restrictions. Gear remains cosmetic in combat.
- [x] Continue into the workshop and use the purchased tonic: inventory falls from 5 to 4, an actual core heal event restores 3 HP to reach 105, and `acted` becomes true. Core checks cover rejected ineffective, unavailable and exhausted use.
- [x] Validate both authored offers and atomic purchase rejection for insufficient funds, remote/battle purchase and inventory overflow in core regression; the published loop directly exercises the 8-gold Health Tonic offer.
- [x] Complete the final published five-encounter route and exit, including optional branches; all five reward receipts verified, zero browser errors. The separate required Floor One smoke also passed.
- [x] Pass the full Release core regression (15 groups) and content validation, including supported saves, starting-gear behavior, ownership, preparation and reward protections.
- [x] Check the final loop at desktop 1280 × 720 and mobile 390 × 844 with zero overflow.
- [x] Separately exercise the real defeat UI using a disclosed fixture: enemy-caused defeat, Retry button, quiet post-retry timer and subsequent walking. This fixture is separate evidence from the natural preparation loop.

Evidence is retained in the [external Block B bundle](https://github.com/cehinds/AI-Art/tree/dev/dungeon-crawler-tactics/block-b/), published after the game commit. The bundle is outside the game repository; links below identify the delivery destination.

| Evidence | Result / bundle path |
| --- | --- |
| Core Release regression and content validator CLI | Passed: 15 test groups and content validation; `core-tests.log`. |
| Final published preparation loop | Passed with two verified reward receipts: first victory, Continue, safe-room rest/shop/save/load, keyboard actor/gear controls and workshop tonic use; [report](https://github.com/cehinds/AI-Art/blob/dev/dungeon-crawler-tactics/block-b/after-final/report.json). |
| Desktop and mobile layout | Passed at 1280 × 720 and 390 × 844 with zero overflow; `after-final/`. |
| Defeat and retry fixture | Passed separately: enemy defeat, Retry, quiet timer and walking; `defeat-retry/`. |
| Final five-encounter route and exit | Passed: complete, five reward receipts verified, zero errors, 130 gold at completion; [report](https://github.com/cehinds/AI-Art/blob/dev/dungeon-crawler-tactics/block-b/full-route/report.json). |
| Aggregate QA report | Passed: final route, preparation loop, required smoke and separate defeat fixture; [QA summary](https://github.com/cehinds/AI-Art/blob/dev/dungeon-crawler-tactics/block-b/qa-summary.json). |

This is a compact Floor One slice reaching level 6 with skill training through rank 5 and cosmetic personal gear. It does not complete Book 1, a level 1–20 campaign, crafting, housing or future class systems.

Browser evidence covers seed 1337 and the stated responsive viewports; broader deterministic rules/connectivity coverage comes from C# regression. The preparation and full-route runs are fixture-free. The defeat-only fixture changes party HP before loading through the UI. No Unity Editor validation is claimed.
