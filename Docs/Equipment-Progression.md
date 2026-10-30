# Equipment and campaign rewards

The equipment additions in `UnityPackage/Runtime/Data/game-content.json` are original tactical adaptations, not verified items from the books. The existing six equipment records remain intact; the nine additions use stable IDs and are marked `rewardOnly`, so they cannot be auto-owned through the ordinary encounter unlock path. Each has a short description, bounded HP, mana and movement bonuses, and may grant an existing generic authored ability.

## Milestone caches

At cumulative wins 3, 6 and 9, victory offers the corresponding cache. Each cache contains a weapon, armor piece and charm. The victory reward presents six choices: the three cache items and the three existing supply options. Claim one; the other choices remain unavailable, and later caches do not reopen earlier choices. Claimed gear and ownership persist in the same save as the campaign. Tier data lives in `equipmentRewardTiers` under the stable `equipment.reward_tier.*` IDs.

| Cumulative wins | Cache | Weapon | Armor | Charm |
| ---: | --- | --- | --- | --- |
| 3 | First Depth Cache | Siltglass Edge | Riveted Coat | Blue Thread Knot |
| 6 | Second Depth Cache | Switchback Blade | Stoneweave Harness | Wellspring Locket |
| 9 | Third Depth Cache | Cinderline Pike | Wayfarer Plate | Starling Compass |

The campaign adaptation groups twelve battles into three depths of four battles. Battle XP is 30 per battle in the first depth, 40 in the second and 50 in the third: cumulative totals of 120, 280 and 480 XP. Under the current XP threshold table, those totals correspond to levels 4, 6 and 8. This is a local accelerated campaign curve, not a claim about a global book progression curve. Plans or saves without the new per-group reward values retain the 30 XP group default.

## Equipment choices

The first cache introduces modest single-stat and skill choices. The second offers specialized profiles: a mobile flanker, a defensive lane holder or a support focused on mana and healing. The third adds strong endurance, movement or mana profiles while preserving slot tradeoffs. These are not strict upgrades across every fight; equipment bonuses do not add random affixes or rarity.

The inventory surface filters equipment by weapon, armor and charm, and compares owned gear with currently equipped gear. Equipment-change preview and confirmation run through the shared core; equipping or removing gear does not heal the party or refill Mana. The comparison shows current and maximum resources, movement, and abilities gained or lost. An intervening command invalidates a preview; confirmation then requires a fresh preview. These behaviors passed 39 focused shared-core checks. Browser checks exercised three actual victories to earn gear, claim/save/reload, slot and ownership filters, preview/cancel/stale/reload rejection, confirmed equip and removal, and the granted ability in a fourth battle. A crawler with injured HP and depleted Mana retained both resources after equipping. Character-sheet compare/cancel was checked in exploration. At 320×740, 390×844, 844×390 and 1440×1000, comparison controls remained visible without horizontal overflow. The existing continuous-floor and generated-campaign browser regressions also passed. No new item affixes, random rarity rolls or body overlays are implemented by these records.

## Validation and remaining work

- [x] All shared-core regression suites and the .NET Standard compatibility build passed.
- [x] Content validation, 172 Python tool regressions and eight validator checks passed.
- [x] Generator validation passed for 300 campaign floors and 200 standalone floors, including malformed XP rejection.
- [x] Unity source/data mirror refreshed; no Unity Editor build is claimed.
- [ ] Full-route build balance, randomized item instances, companion-specific equipment rules, and a separate story XP rebalance remain future work.

The configuration files now live under `Web/wwwroot/data/`, separate from art metadata. This fixes the prior strict attachment-scanner failure without relaxing the scanner; the full pinned-art check remains part of release CI.
