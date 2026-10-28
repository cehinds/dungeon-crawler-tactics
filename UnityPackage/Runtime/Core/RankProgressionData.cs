using System;
namespace DungeonCrawlerTactics
{
    // All numbers here are the game's adaptation, not canonical book formulas.
    [Serializable]
    public sealed class AbilityRankProfile
    {
        public string abilityId;
        public string description, canonNotes;
        public string[] sourceUrls = new string[0];
        public int practiceMultiplierPercent = 100;
        public int damagePerRank = -1, healPerRank = -1, costReductionPerRank = -1;
        public int damageBonusCap = 20, healBonusCap = 20, costReductionCap = 2;
        public int rangePerRank, rangeBonusCap = 12;
        public int pushPerRank, pushBonusCap = 12;
        public int summonHpPerRank, summonHpBonusCap = 100;
        public int summonMovePerRank, summonMoveBonusCap = 6;
        public int summonRoundsPerRank, summonRoundsBonusCap = 10;
        public RankMilestoneDef[] milestones = new RankMilestoneDef[0];
    }
    [Serializable]
    public sealed class RankMilestoneDef
    {
        public int rank, damageBonus, healBonus, costReduction;
        public string description;
        public string[] addTags = new string[0], removeTags = new string[0];
        public TagReplacementDef[] tagReplacements = new TagReplacementDef[0];
        public int rangeBonus, pushBonus, summonHpBonus, summonMoveBonus, summonRoundsBonus;
    }
    [Serializable] public sealed class TagReplacementDef { public string fromTag, toTag; }
    [Serializable]
    public sealed class SkillRankView
    {
        public int rank, requiredUses, damageBonus, healBonus, costReduction;
        public int rangeBonus, pushBonus, summonHpBonus, summonMoveBonus, summonRoundsBonus;
        public int cost, range;
        public string effectSummary;
        public string[] addTags = new string[0], removeTags = new string[0];
        public TagReplacementDef[] tagReplacements = new TagReplacementDef[0];
        public bool trainable;
        public string[] milestones = new string[0];
    }
    [Serializable]
    public sealed class SkillRankCatalogView
    {
        public string abilityId, label, description, canonNotes;
        public string[] sourceUrls = new string[0];
        public SkillRankView[] ranks;
    }
    public static class SkillRankProgression
    {
        private static string[] SortedTags(System.Collections.Generic.HashSet<string> tags) { string[] rows = new string[tags.Count]; tags.CopyTo(rows); Array.Sort(rows, StringComparer.Ordinal); return rows; }
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
            RankMilestoneDef[] orderedMilestones = profile == null ? new RankMilestoneDef[0] : (RankMilestoneDef[])profile.milestones.Clone();
            Array.Sort(orderedMilestones, (a,b) => a.rank.CompareTo(b.rank));
            for (int i = 0; i < result.Length; i++)
            {
                int range = i * (profile == null ? 0 : profile.rangePerRank);
                int push = i * (profile == null ? 0 : profile.pushPerRank);
                int summonHp = i * (profile == null ? 0 : profile.summonHpPerRank);
                int summonMove = i * (profile == null ? 0 : profile.summonMovePerRank);
                int summonRounds = i * (profile == null ? 0 : profile.summonRoundsPerRank);
                System.Collections.Generic.HashSet<string> addTags = new System.Collections.Generic.HashSet<string>(StringComparer.Ordinal), removeTags = new System.Collections.Generic.HashSet<string>(StringComparer.Ordinal);
                System.Collections.Generic.Dictionary<string, string> replacements = new System.Collections.Generic.Dictionary<string, string>(StringComparer.Ordinal);
                int damage = i * (profile == null || profile.damagePerRank < 0 ? config.damagePerRank : profile.damagePerRank);
                int heal = i * (profile == null || profile.healPerRank < 0 ? config.healPerRank : profile.healPerRank);
                int cost = i * (profile == null || profile.costReductionPerRank < 0 ? config.costReductionPerRank : profile.costReductionPerRank);
                System.Collections.Generic.List<string> milestones = new System.Collections.Generic.List<string>();
                if (profile != null && profile.milestones != null)
                    foreach (RankMilestoneDef milestone in orderedMilestones)
                        if (milestone.rank <= i + 1)
                        {
                            range += milestone.rangeBonus; push += milestone.pushBonus; summonHp += milestone.summonHpBonus; summonMove += milestone.summonMoveBonus; summonRounds += milestone.summonRoundsBonus; addTags.UnionWith(milestone.addTags); removeTags.UnionWith(milestone.removeTags);
                            foreach (TagReplacementDef replacement in milestone.tagReplacements) replacements[replacement.fromTag] = replacement.toTag;
                            damage += milestone.damageBonus; heal += milestone.healBonus; cost += milestone.costReduction;
                            if (milestone.rank == i + 1 && !string.IsNullOrEmpty(milestone.description)) milestones.Add(milestone.description);
                        }
                System.Collections.Generic.List<TagReplacementDef> replacementRows = new System.Collections.Generic.List<TagReplacementDef>();
                foreach (var replacement in replacements) replacementRows.Add(new TagReplacementDef { fromTag = replacement.Key, toTag = replacement.Value });
                replacementRows.Sort((a,b) => StringComparer.Ordinal.Compare(a.fromTag,b.fromTag));
                result[i] = new SkillRankView { rank = i + 1, requiredUses = thresholds[i], trainable = i < maximumRank,
                    rangeBonus = Math.Min(profile == null ? 12 : profile.rangeBonusCap, range),
                    pushBonus = Math.Min(profile == null ? 12 : profile.pushBonusCap, push),
                    summonHpBonus = Math.Min(profile == null ? 100 : profile.summonHpBonusCap, summonHp),
                    summonMoveBonus = Math.Min(profile == null ? 6 : profile.summonMoveBonusCap, summonMove),
                    summonRoundsBonus = Math.Min(profile == null ? 10 : profile.summonRoundsBonusCap, summonRounds),
                    addTags = SortedTags(addTags), removeTags = SortedTags(removeTags), tagReplacements = replacementRows.ToArray(),
                    damageBonus = Math.Min(profile == null ? 20 : profile.damageBonusCap, damage),
                    healBonus = Math.Min(profile == null ? 20 : profile.healBonusCap, heal),
                    costReduction = Math.Min(profile == null ? 2 : profile.costReductionCap, cost), milestones = milestones.ToArray() };
            }
            return result;
        }
    }
}
