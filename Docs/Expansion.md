# Expeditions, enemy kits and branching skills

The current source contains 148 class kits (142 player-selectable and six enemy-only), 88 abilities, eight personal skill trees with 48 nodes, and 142 class trees with 1,988 nodes (122 catalog profiles plus 20 preserved-kit profiles). It adds six expedition rooms and an optional eighteen-floor journey registry: Floors 1–8 have seven battle maps and a Floor 7 bypass; Floors 9–18 remain locked. The rooms, enemy designs, skill names, bonuses, costs and progression are original tactical adaptations. They are not claims about specific book scenes, named canonical skills or exact novel formulas. The original three-encounter campaign and its stable content IDs remain in place. The source-linked class names do not make their invented kits or numerical progression canonical.

## Expedition board

Choose an expedition from the mission board using the party and build prepared in the safe room. The game preserves a campaign checkpoint, restores the party for the attempt and opens a separate battle. Defeat every hostile to win; retry starts a fresh attempt. Returning restores the saved campaign, including its inventory and progression. Expeditions grant no campaign XP, loot or permanent practice progress, so replaying them cannot farm campaign rewards. Mid-battle saves retain the selected expedition and campaign backup.

| Expedition | Size | Enemy mix | Tactical layout |
|---|---|---|---|
| Flooded Service Sewers | 12×9 | Coolant Sludges, Arc Sentry | A service spine divides wet basins. Sludges apply Wet, making the sentry's lightning more dangerous. |
| Oil-Line Foundry | 13×10 | Cinder Stalkers, Arena Mauler | Oil channels meet burning crucible tiles; dry outer routes offer an alternative approach. |
| Rimebound Crypt | 12×10 | Crypt Rimeguards, Arena Mauler | Staggered burial rows and wet crossings support cold/frozen/shatter combinations. |
| Overgrown Pump Chamber | 14×10 | Spore Wardens, Coolant Sludge, Arena Mauler | A broken central pump creates branching pursuit routes. Shocked reduces Mana recovery; there is no poison damage-over-time. |
| Arc-Sentry Security Works | 14×11 | Arc Sentries, Arena Mauler | Staggered partitions constrain walking, while wet crossways reward careful positioning. Walls do not add an unimplemented line-of-sight rule. |
| Broken Ring Gauntlet | 15×11 | Arena Maulers, Cinder Stalker, Crypt Rimeguard, Spore Warden | A central obstacle ring and open gates combine close pressure with mixed elemental threats. |

There are 22 enemy placements across these six maps. Terrain uses the existing Water, Oil and Burning tags; enemy abilities use existing direct damage, status, push and reaction primitives. Decorative props do not secretly add interactive-object rules. Boss scenario lanes and custom-map imports remain separate features.

## Six enemy kits

Enemy classes have `playerSelectable: false`, keeping them out of crawler loadouts. Their stable IDs reference ordinary ability definitions; display names do not select behavior. Every kit also has a basic adjacent Strike.

| Enemy | Stable class ID | Distinct action |
|---|---|---|
| Coolant Sludge | `class.enemy_sludge` | Coolant Spit: ranged damage plus Wet setup |
| Cinder Stalker | `class.enemy_cinder` | Cinder Shot: ranged Fire damage, interacting with existing terrain/reactions |
| Crypt Rimeguard | `class.enemy_frost` | Frost Grasp: ranged Cold damage plus Frozen |
| Spore Warden | `class.enemy_spore` | Spore Sap: ranged damage plus Shocked, with no invented poison subsystem |
| Arc Sentry | `class.enemy_sentry` | Security Arc: longer-range Lightning damage |
| Arena Mauler | `class.enemy_mauler` | Mauler Slam: adjacent physical/shatter damage and a one-cell push |

Spawn records use art IDs `sludge`, `cinder`, `frost`, `spore`, `sentry` and `mauler`. Sprite size and appearance do not change occupancy: these units use the existing one-cell tactical rules. Native Unity presentation and new-art parity require their own verification.

## Branching character skills

Each of the eight deployable characters has two independent three-tier branches, for **48 nodes** total. Each node costs one skill point. Every crawler begins with one skill point and receives one more at each party level; party progression now extends to level 50. Skill points are separate from the three stat-allocation points awarded per earned level. This is accelerated game progression; it does not reproduce chronological race/class unlocks from the books.

Both branch roots are available at level 1; their children require level 2 and their own root. One branch's capstone requires level 3, the other level 4; both require the preceding node in that branch. Early levels require a choice between branch depth and broader passive benefits. Higher party levels can eventually fund all six personal nodes; this is not a permanent four-point cap. Preview a node in the safe room, compare the real stat/ability changes, then confirm or cancel. Only confirmation spends points. Passive HP/Mana cap increases require rest to refill. Learned nodes persist in saves and add to innate, class, equipment and existing level-unlocked abilities.

| Character | Branches | Two new capstone actions |
|---|---|---|
| Carl | Improviser / Scrapper | Breach Kick combines physical/shatter damage and a two-cell push; Scrap Brace heals, guards and clears Shocked. |
| Princess Donut | Headliner / Royal Support | Spotlight Missile combines Arcane damage and Guarded removal; Royal Recovery heals an ally and removes Frozen/Shocked. |
| Katia | Momentum / Resilience | Braced Ram combines physical damage and a two-cell push; Reshape and Rally clears Frozen/Shocked, heals and guards herself. These are body-control adaptations, not copied creature magic. |
| Mongo | Leaper / Hunter | Wingbound Leap is a longer tile-targeted reposition; Raking Bite combines physical/shatter damage and Guarded removal. Mongo remains a feathered, winged raptor; the leap does not implement sustained flight. |
| Elle | Winter Control / Cold Care | Winter Needle delivers longer-range Cold damage and Frozen; Thawing Touch cleanses Frozen/Wet and heals an ally. |
| Imani | Caregiver / Protector | Stabilize heals and cleanses Shocked/Frozen; Warmth Guard heals, clears Frozen and grants Guarded to an ally. |
| Louis | Coolant Rig / Electrical Rig | Coolant Nozzle applies Wet with damage; Arc Prod combines Lightning/physical damage and a one-cell push. |
| Britney | Club Technique / Ring Survival | Hooking Club combines physical/shatter damage and a two-cell push; Ringside Grit heals and guards herself. |

The four non-capstone nodes per tree grant bounded HP, Mana, movement, direct-damage or direct-healing bonuses. Exact numbers and action costs are listed in [the generated catalog](PlayableContent.md) and the shared-core menus. Mordecai remains a nondeployable advisor with no crawler skill tree. Existing automatic personal unlocks remain available; the trees add choices without replacing character identity.

## Lore class trees through level 50

The 122 source-attested class names have separate runtime kits under `class.lore_*`, preserving the original 20 selectable kits and six enemy kits. Their 122 catalog class trees each have two seven-node chains at levels 1, 5, 10, 20, 30, 40 and 50. Every node grants supported existing abilities or bounded stat bonuses. The name is source-attested; its representative role, branch grants and numbers are tactical adaptations, not a copied canonical class description.

Node requirements follow party XP level rather than a separately earned class-XP track. The selected class exposes its own tree, with a saved per-crawler ownership key and a point budget derived from party level. Inactive class bonuses do not apply; learned choices remain available when the class is selected again. At level 50 the budget can cover both branches, so the meaningful early choices concern order and access rather than permanently exclusive capstones.

Story classes and stat allocation unlock on Floor 3. Source-reported later class options retain their minimum floor, including four Floor 9 and four verified Book 8 Floor 10 options outside the implemented story scope. A level-50 class-tree endpoint does not mean that crawler level 50 is required to choose a class. Duplicate display names can exist between the preserved original kits and the adapted lore catalog; their stable IDs and trees distinguish them.

The first four cumulative XP thresholds remain 0, 30, 70 and 120. Level 5 requires 200; the authored curve rises to 59,431 at level 50. This accelerated curve and automatic stat growth are game formulas, not novel XP tables.

## Ability practice through rank 20

All 88 abilities have an authored rank profile and a displayed 1–20 table. Normal field crawlers train to rank 15. Carl's authored cap is 20 once story allocation/class access opens on Floor 3; before that, his effective cap is 15. Rank permissions are explicit data, not rules keyed to his name. Items do not gain training from consumable use.

The first practice thresholds remain 0, 3 and 8 uses. Later thresholds increase with rank, with a larger training step above rank 10. Profiles apply bounded bonuses to the action's actual direct damage/healing and Mana cost; they do not add damage to status-only actions, grow reaction damage, invent new area effects or silently copy every qualitative book breakpoint. These runtime additive profiles differ from the separate research artifact's suggested multiplicative curve. The shared resolver uses the same effective bonuses for preview and commit.

## Optional journey and home

The journey has a distinct entry command and retains an eighteen-floor registry. Its first two battles teach innate abilities before class selection; reserves without a personal innate action receive basic Strike. Floor 4 requires a route-lever discovery, Floor 5 requires four lore beacons, Floor 6 exposes bounded hunter threats, and Floor 8 requires six weakened-monster captures. These are small grid adaptations of the researched themes. Floor 7 deliberately bypasses the destroyed Great Race rather than inventing a normal canonical race run. Rewards through Floor 8 total the level-50 threshold.

The authored home catalog opens from Floor 4 with a shared personal space, separately priced training/crafting services, tools and social facilities. Its gold income and service limits are adaptations. Unknown club-admission prices remain unavailable rather than becoming purchasable generic passes. Home purchase/training previews and their economic state are governed by shared C# validation; native Unity interface parity requires separate verification.

## Authored data and limits

`game-content.json` contains `skillTrees`, `classSkillTrees`, `expeditions`, `journey`, `home` and the practice `abilityProfiles`; `combat-content.json` contains the 16 new crawler actions, six enemy actions and six enemy class kits. Content versions and legacy IDs remain unchanged. Older saves initialize missing tree records with unspent points derived from their party level; no existing HP/Mana values are reinterpreted.

Trees use stable node IDs, explicit level/point requirements and prerequisites within their own tree. Expedition encounters author tiles, walls, party spawns, enemy classes/stats and decorative placements. Schemas and runtime validators check references, bounded bonuses, prerequisite graphs, map connectivity and spawn legality. `Tools/build_lore_catalog.py` reproducibly builds the 122 adapted lore class kits/trees and 20 preserved-kit trees while preserving unrelated content. Adding another combination of supported effects requires data; new mechanical primitives still require code and scenario tests.

Full race selection, a physical mass budget for Katia, separate companion growth, universal area/chain effects, procedural campaigns and native Unity presentation parity remain future work. Separate class XP and a full canonical rank-effect simulation are also outside these bounded class/rank adaptations. The expedition library is authored, not procedural. See [lore boundaries](Lore-Mechanics-Review.md) and [progression](Progression.md) for the distinction between source anchors and tactical adaptation.
