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
        private readonly Dictionary<string, SkillRankView[]> rawRankTables = new Dictionary<string, SkillRankView[]>(StringComparer.Ordinal);
        private SkillRankView CurrentPracticeRank(string owner, string ability, int uses)
        {
            SkillRankView[] table;
            if (!rawRankTables.TryGetValue(ability, out table)) { table = SkillRankProgression.Table(data.development.practice, ability); rawRankTables.Add(ability, table); }
            int rank = 1, cap = MaximumSkillRank(owner);
            for (int i = 1; i < cap; i++) if (uses >= table[i].requiredUses) rank = i + 1;
            return table[rank - 1];
        }
        private SkillPracticeView PracticeView(string owner, string ability, int uses)
        {
            int cap = MaximumSkillRank(owner);
            SkillRankView[] table = SkillRankProgression.Table(data.development.practice, ability, cap);
            int rank = SkillRankProgression.Rank(data.development.practice, ability, uses, cap);
            AbilityDef definition = catalog.Abilities[ability];
            foreach (SkillRankView row in table)
            {
                AbilityDef effective = AbilityScaling.Apply(definition, AbilityScaling.Modifiers(row));
                row.cost = effective.cost; row.range = effective.range; row.effectSummary = Describe(effective);
                if (!Array.Exists(definition.effects, e => e.op == "Damage")) row.damageBonus = 0;
                if (!Array.Exists(definition.effects, e => e.op == "Heal")) row.healBonus = 0;
            }
            SkillRankView current = table[rank - 1];
            ActionModifiers currentModifiers = AbilityScaling.Modifiers(current);
            if (roster.ContainsKey(owner))
            {
                ActionModifiers allocated = AllocationModifiers(owner, allocations), tree = TreeModifiers(owner, unlockedSkillNodes);
                currentModifiers.damageBonus = Math.Min(100, currentModifiers.damageBonus + allocated.damageBonus + tree.damageBonus);
                currentModifiers.healBonus = Math.Min(100, currentModifiers.healBonus + allocated.healBonus + tree.healBonus);
            }
            AbilityDef effectiveCurrent = AbilityScaling.Apply(definition, currentModifiers);
            AbilityRankProfile profile = SkillRankProgression.Profile(data.development.practice, ability);
            return new SkillPracticeView { unitId = owner, abilityId = ability, uses = uses, rank = rank, maxRank = cap, atCap = rank >= cap,
                castModes = CastModeViews(owner, ability, rank, currentModifiers),
                canonNotes = profile == null ? "" : profile.canonNotes, sourceUrls = profile == null ? new string[0] : profile.sourceUrls, description = Describe(effectiveCurrent), cost = effectiveCurrent.cost, range = effectiveCurrent.range, nextRankUses = rank < cap ? table[rank].requiredUses : 0, damageBonus = current.damageBonus, healBonus = current.healBonus, costReduction = current.costReduction, ranks = table };
        }
        private SkillRankCatalogView[] RankCatalog()
        {
            List<SkillRankCatalogView> result = new List<SkillRankCatalogView>();
            foreach (AbilityDef ability in catalog.Abilities.Values)
            {
                AbilityRankProfile profile = SkillRankProgression.Profile(data.development.practice, ability.id);
                SkillRankView[] rows = PracticeView(data.roster[0].id, ability.id, 0).ranks;
                foreach (SkillRankView row in rows) row.trainable = row.rank <= SkillRankProgression.NormalRankCap;
                result.Add(new SkillRankCatalogView { abilityId = ability.id, label = ability.label, ranks = rows, description = profile == null ? "" : profile.description, canonNotes = profile == null ? "" : profile.canonNotes, sourceUrls = profile == null ? new string[0] : profile.sourceUrls });
            }
            result.Sort((a, b) => StringComparer.Ordinal.Compare(a.abilityId, b.abilityId));
            return result.ToArray();
        }
    }
}
