# Story progression pacing

The current playable story covers floors 1–8; floors 9–18 are reserved, with no encounters or promised XP rewards. Its party level cap remains 50. This pacing revision changes **future story victory rewards**, leaving the existing XP thresholds, automatic stat growth, allocation points and skill-rank permissions intact.

## Audit and chosen adaptation

Before this revision, cumulative story XP reached levels 4, 10, 18, 27, 39 and 50 after floors 1–6. Floor 8 awarded another 55,615 XP after the cap was already reached. This exhausted level growth before the current story ended and left none for the reserved floors.

The revised schedule deliberately ends the current story at level 25. It preserves early skill access, the floor-3 class/allocation gate and later class-tree tiers for future content. These numbers are **game tuning**, not canonical crawler levels or a reconstruction of the novels' XP curve.

| Floor cleared | Victory XP | Cumulative XP | Party level |
|---|---:|---:|---:|
| 1 | 120 | 120 | 4 |
| 2 | 131 | 251 | 6 |
| 3 | 253 | 504 | 9 |
| 4 | 464 | 968 | 12 |
| 5 | 1,088 | 2,056 | 16 |
| 6 | 1,800 | 3,856 | 20 |
| 7 bypass | 0 | 3,856 | 20 |
| 8 | 3,544 | 7,400 | 25 |

The cap still requires 59,431 cumulative XP. A fresh completed story has 52,031 XP of headroom, twenty-five remaining levels and a next threshold at 8,311 XP. This reserves growth without inventing rewards for unimplemented floors. Optional training and standalone encounters keep their existing progression rules.

## Evidence boundaries

The published Book 2 sample and chapter-located sources support use-based skill growth, slower high-rank practice, Primal permission for rank 20, and specific ability milestones. They do not establish these party XP thresholds, stat gains or floor-level targets. See [Ability rank audit](Ability-Rank-Audit.md) for the source-by-source distinction. Party levels remain separate from learned skill ranks; changing victory XP neither trains skills nor grants universal rank-20 access.

## Existing checkpoints

XP thresholds and per-level HP/Mana remain unchanged. Previously earned XP, levels, stats, allocated points and skill-tree purchases are retained, including level-50 checkpoints. They continue earning the revised rewards; they are never downgraded to the fresh-run schedule.

Checkpoint validation recognizes the finite combinations of the original and revised reward for each actually completed story encounter. This permits an older run to continue after the update and save again, while rejecting arbitrary intermediate XP. The original reward list is retained only as a compatibility record in `GameSession.Journey.cs`; authored current rewards remain in `game-content.json`. No save schema change is required.

## Player feedback and verification

The level-up presenter shows the before/after level, actual gains in maximum HP/Mana and allocation points, all skills unlocked across a multi-level jump, floor-locked skills whose level requirement was met, and XP to the next level. Early allocation points are explicitly banked. Development also shows current level, cumulative XP, next-level distance and total level bonuses. These values come from authoritative session views.

`Tests/JourneyTests` exercises the complete fresh story from default stats and supplies with legal preview/commit actions, camp rests and naturally earned rewards (no inflated stats, seeded supplies, purchased nodes or allocated stats), checks each revised victory level and future headroom, round-trips checkpoints, continues an original-reward checkpoint into the revised schedule and rejects forged XP atomically. `Tests/RankTests` independently checks ability rank permissions and progression behavior. This establishes deterministic controller viability, not comprehensive balance across party builds or human play styles. Test results belong in the delivery report; this document does not claim Unity Editor validation.
