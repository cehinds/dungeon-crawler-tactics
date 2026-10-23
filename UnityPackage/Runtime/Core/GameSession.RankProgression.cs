using System;
using System.Collections.Generic;
namespace DungeonCrawlerTactics
{
    public sealed partial class GameSession
    {
        private int MaximumSkillRank(string owner)
        {
            RosterDef definition = Definition(owner);
            return definition == null || !JourneyAllocationUnlocked ? SkillRankProgression.NormalRankCap : definition.maxSkillRank;
        }
        private SkillPracticeView PracticeView(string owner, string ability, int uses)
        {
            int cap = MaximumSkillRank(owner);
            SkillRankView[] table = SkillRankProgression.Table(data.development.practice, ability, cap);
            int rank = SkillRankProgression.Rank(data.development.practice, ability, uses, cap);
            SkillRankView current = table[rank - 1];
            return new SkillPracticeView { unitId = owner, abilityId = ability, uses = uses, rank = rank, maxRank = cap, atCap = rank >= cap,
                nextRankUses = rank < cap ? table[rank].requiredUses : 0, damageBonus = current.damageBonus, healBonus = current.healBonus, costReduction = current.costReduction, ranks = table };
        }
        private SkillRankCatalogView[] RankCatalog()
        {
            List<SkillRankCatalogView> result = new List<SkillRankCatalogView>();
            foreach (AbilityDef ability in catalog.Abilities.Values)
                result.Add(new SkillRankCatalogView { abilityId = ability.id, label = ability.label, ranks = SkillRankProgression.Table(data.development.practice, ability.id) });
            result.Sort((a, b) => StringComparer.Ordinal.Compare(a.abilityId, b.abilityId));
            return result.ToArray();
        }
    }
}
