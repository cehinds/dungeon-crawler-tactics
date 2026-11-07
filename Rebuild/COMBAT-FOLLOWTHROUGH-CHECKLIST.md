# Combat followthrough checklist

This pass covers Powerful Strike’s unarmed multiplier, Improvised Bomb aiming, per-target skill defenses and combat previews in the existing Floor One slice. Bomb’s 2-mana cost remains an adaptation; charge inventory and crafting remain unfinished future work. It adds no skills, later-floor permissions, crafting, charges, loot, or campaign encounters.

## Content and contract

- [x] Preserve stable skill IDs, costs, starting ranks, practice thresholds and Floor One rank-5 permission.
- [x] Powerful Strike uses `damageBasis: "unarmed"` and `baseSkillId: "punch"`, with zero additive power. Its rank-3/4/5 factors are 1.5/1.75/2.
- [x] Distinguish the secondary-source unarmed multiplier identity and reported rank 3 from adapted numerical factors.
- [x] Correct stale single-target Bomb documentation: authored `effectRadius: 1` already existed.
- [x] Bomb retains `targetKind: "enemyOrObject"` and adds `allowGroundTarget: true` for coordinates while preserving direct IDs.
- [x] Label Bomb radius, damage, range, friendly fire and 2-mana resource cost as `adaptation-design`. Publisher sample references do not prove this numerical design.
- [x] Document blast allies/enemies/destructibles, chain footprints, per-target defense and forecast fields. Existing environmental fixed-damage semantics remain unchanged; no new burning rider is added.

## Acceptance evidence

Only completed checks with actual results should be marked below. Historical progression or Block B results do not verify this pass.

- [x] Core tests: Punch-baseline growth, Strike rank multipliers, armor/reaction resolution, invalid/no-mana actions and forecast/commit parity.
- [x] Core tests: Bomb empty-cell targeting, direct-ID compatibility, range rejection, per-target defenses, friendly fire, destructibles and chained explosions.
- [x] Full C# regression suite: 16 test groups passed, including stale pending-forecast mana and ally/self support-skill forecast/commit parity regressions. The final support correction keeps initial support damage at zero while offensive skill hits receive per-target defenses. Content validator passed 55 entries with seeds 0, 42 and 1337.
- [x] Published browser: real pointer/keyboard ground targeting, blast footprint and ally warning, cancel/confirm behavior and resource spending; `after/targeted/report.json` passed.
- [x] Required Floor One gameplay smoke (`smoke.log`), preparation loop (`after/preparation/report.json`) and full route (`after/full-route/report.json`) passed on the final support-corrected runtime. The full route reached complete with five cleared encounters, five verified reward receipts and no browser errors.
- [x] Desktop 1280 × 720 and mobile viewport 390 × 844 captures and logs reviewed: zero map overlap; full board and all three controls visible. Mobile checks used pointer input and do not claim touchscreen-device validation.

The first targeted browser run and Floor One smoke passed their mechanical checks, but visual review rejected the forecast overlay because it obscured the board and buttons. This is a rejected iteration, not final browser acceptance. The compact forecast dock with reserved space passed the final rerun and review. The rejected iteration remains alongside final evidence.

Run the targeted acceptance harness against the published host:

```sh
python3 Tools/playtest_combat_followthrough.py --url http://localhost:8765 --browser /usr/bin/chromium --output Rebuild/CombatFollowthroughComparison/after/targeted
```

The external [combat followthrough evidence bundle](https://github.com/cehinds/AI-Art/tree/dev/dungeon-crawler-tactics/combat-followthrough/) holds the comparison gallery, screenshots and reports; its `after/` directory contains final verification. `qa-summary.json` reports `status: "passed"`, with unchanged source/published SHA guards. The previous passing run remains under `pre-support-fix-passing/` and the rejected overlay remains under `rejected-overlay-iteration/`; these are historical evidence. Final browser flows used real inputs without injected gameplay commands, state, saves or camera overrides; read-only public view assertions and preparation-loop event observers are disclosed in the summary. The natural targeted scenario covers first-encounter Bomb, while core tests cover varied defenses, chain footprints and Strike formulas.
