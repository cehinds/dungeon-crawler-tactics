using System;
namespace DungeonCrawlerTactics
{
    // All numbers here are the game's adaptation, not canonical book formulas.
    [Serializable]
    public sealed class AbilityRankProfile
    {
        public string abilityId;
        public int practiceMultiplierPercent = 100;
        public int damagePerRank = -1, healPerRank = -1, costReductionPerRank = -1;
        public int damageBonusCap = 20, healBonusCap = 20, costReductionCap = 2;
        public RankMilestoneDef[] milestones = new RankMilestoneDef[0];
    }
    [Serializable]
    public sealed class RankMilestoneDef
    {
        public int rank, damageBonus, healBonus, costReduction;
        public string description;
    }
    [Serializable]
    public sealed class SkillRankView
    {
        public int rank, requiredUses, damageBonus, healBonus, costReduction;
        public bool trainable;
        public string[] milestones = new string[0];
    }
    [Serializable]
    public sealed class SkillRankCatalogView
    {
        public string abilityId, label;
        public SkillRankView[] ranks;
    }
    public static class SkillRankProgression
    {
        public const int NormalRankCap = 15, AbsoluteRankCap = 20, MaximumUses = 100000;
        public static AbilityRankProfile Profile(SkillProgressionDef config, string abilityId)
        {
            return config.abilityProfiles == null ? null : Array.Find(config.abilityProfiles, p => p.abilityId == abilityId);
        }
        public static int[] Thresholds(SkillProgressionDef config, string abilityId)
        {
            int[] result = new int[AbsoluteRankCap];
            int[] seed = config.useThresholds;
            AbilityRankProfile profile = Profile(config, abilityId);
            int multiplier = profile == null ? 100 : profile.practiceMultiplierPercent;
            long cumulative = 0;
            for (int i = 0; i < result.Length; i++)
            {
                if (seed != null && i < seed.Length) cumulative = seed[i];
                else if (i > 0) cumulative += i * i * (i >= 10 ? 4 : 1);
                long scaled = (cumulative * multiplier + 99) / 100;
                result[i] = i == 0 ? 0 : (int)Math.Min(MaximumUses - (AbsoluteRankCap - 1 - i), Math.Max(result[i - 1] + 1L, scaled));
            }
            return result;
        }
        public static int Rank(SkillProgressionDef config, string abilityId, int uses, int maximumRank)
        {
            int cap = Math.Max(1, Math.Min(AbsoluteRankCap, maximumRank)), rank = 1;
            int[] thresholds = Thresholds(config, abilityId);
            for (int i = 1; i < cap; i++) if (uses >= thresholds[i]) rank = i + 1;
            return rank;
        }
        public static SkillRankView[] Table(SkillProgressionDef config, string abilityId, int maximumRank = NormalRankCap)
        {
            int[] thresholds = Thresholds(config, abilityId);
            SkillRankView[] result = new SkillRankView[AbsoluteRankCap];
            AbilityRankProfile profile = Profile(config, abilityId);
            for (int i = 0; i < result.Length; i++)
            {
                int damage = i * (profile == null || profile.damagePerRank < 0 ? config.damagePerRank : profile.damagePerRank);
                int heal = i * (profile == null || profile.healPerRank < 0 ? config.healPerRank : profile.healPerRank);
                int cost = i * (profile == null || profile.costReductionPerRank < 0 ? config.costReductionPerRank : profile.costReductionPerRank);
                System.Collections.Generic.List<string> milestones = new System.Collections.Generic.List<string>();
                if (profile != null && profile.milestones != null)
                    foreach (RankMilestoneDef milestone in profile.milestones)
                        if (milestone.rank <= i + 1)
                        {
                            damage += milestone.damageBonus; heal += milestone.healBonus; cost += milestone.costReduction;
                            if (milestone.rank == i + 1 && !string.IsNullOrEmpty(milestone.description)) milestones.Add(milestone.description);
                        }
                result[i] = new SkillRankView { rank = i + 1, requiredUses = thresholds[i], trainable = i < maximumRank,
                    damageBonus = Math.Min(profile == null ? 20 : profile.damageBonusCap, damage),
                    healBonus = Math.Min(profile == null ? 20 : profile.healBonusCap, heal),
                    costReduction = Math.Min(profile == null ? 2 : profile.costReductionCap, cost), milestones = milestones.ToArray() };
            }
            return result;
        }
    }
}
