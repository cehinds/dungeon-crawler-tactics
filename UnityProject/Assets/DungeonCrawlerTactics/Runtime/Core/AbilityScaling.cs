using System;
namespace DungeonCrawlerTactics
{
    // One bounded transformation shared by targeting, descriptions, forecasts and commits.
    public static class AbilityScaling
    {
        public static ActionModifiers Modifiers(SkillRankView rank)
        {
            return new ActionModifiers { damageBonus = rank.damageBonus, healBonus = rank.healBonus, costReduction = rank.costReduction,
                rangeBonus = rank.rangeBonus, pushBonus = rank.pushBonus, summonHpBonus = rank.summonHpBonus, summonMoveBonus = rank.summonMoveBonus, summonRoundsBonus = rank.summonRoundsBonus, tagReplacements = rank.tagReplacements, addTags = rank.addTags, removeTags = rank.removeTags };
        }
        public static AbilityDef Apply(AbilityDef ability, ActionModifiers m)
        {
            if (m == null) return ability;
            if (m.damageBonus < 0 || m.damageBonus > 100 || m.healBonus < 0 || m.healBonus > 100 || m.costReduction < 0 || m.costReduction > 100 || m.rangeBonus < 0 || m.rangeBonus > 12 || m.pushBonus < 0 || m.pushBonus > 12 || m.summonHpBonus < 0 || m.summonHpBonus > 100 || m.summonMoveBonus < 0 || m.summonMoveBonus > 6 || m.summonRoundsBonus < 0 || m.summonRoundsBonus > 10) throw new ArgumentException("Action modifiers exceed bounded limits.");
            AbilityDef result = new AbilityDef { id = ability.id, label = ability.label, target = ability.target, requiredTargetTag = ability.requiredTargetTag, cost = Math.Max(0, ability.cost - m.costReduction), range = ability.range + m.rangeBonus, incomingTags = ability.incomingTags, effects = new EffectDef[ability.effects.Length] };
            for (int i = 0; i < result.effects.Length; i++)
            {
                EffectDef e = ability.effects[i]; string tag = e.tag;
                if (e.op == "AddTag" && m.tagReplacements != null) foreach (TagReplacementDef replacement in m.tagReplacements) if (replacement.fromTag == e.tag) tag = replacement.toTag;
                result.effects[i] = new EffectDef { op = e.op, tag = tag, amount = e.amount + (e.op == "Damage" ? m.damageBonus : e.op == "Heal" ? m.healBonus : e.op == "Push" ? m.pushBonus : 0), summonHp = e.summonHp + (e.op == "DuplicatePet" ? m.summonHpBonus : 0), summonMove = e.summonMove + (e.op == "DuplicatePet" ? m.summonMoveBonus : 0), summonRounds = e.summonRounds + (e.op == "DuplicatePet" ? m.summonRoundsBonus : 0) };
            }
            var effects = new System.Collections.Generic.List<EffectDef>(result.effects);
            foreach (string tag in m.removeTags) effects.Add(new EffectDef { op = "RemoveTag", tag = tag });
            foreach (string tag in m.addTags) effects.Add(new EffectDef { op = "AddTag", tag = tag });
            result.effects = effects.ToArray();
            return result;
        }
    }
}
