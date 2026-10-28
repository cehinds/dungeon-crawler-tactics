using System;
using System.Collections.Generic;
namespace DungeonCrawlerTactics
{
    public sealed partial class GameSession
    {
        private ActionModifiers CastModifiers(string owner, string ability, string modeId)
        {
            ActionModifiers result = Modifiers(owner, ability);
            if (string.IsNullOrEmpty(modeId)) return result;
            AbilityRankProfile profile = SkillRankProgression.Profile(data.development.practice, ability);
            AbilityCastModeDef mode = profile == null ? null : Array.Find(profile.castModes, m => m.id == modeId);
            Require(mode != null, "Unknown cast mode.");
            SkillPracticeSave practice = practices.Find(p => p.unitId == owner && p.abilityId == ability);
            Require(roster.ContainsKey(owner) && CurrentPracticeRank(owner, ability, practice == null ? 0 : practice.uses).rank >= mode.minimumRank, "Cast mode requires rank " + mode.minimumRank + ".");
            result.hasCastMode = true; result.castModeCost = mode.manaCost; result.castModeDamageBonus = mode.damageBonus;
            return result;
        }
        private AbilityCastModeView[] CastModeViews(string owner, string ability, int rank, ActionModifiers modifiers, EntityState actor = null, bool canAct = true, bool includeTargets = false)
        {
            AbilityRankProfile profile = SkillRankProgression.Profile(data.development.practice, ability);
            if (profile == null) return new AbilityCastModeView[0];
            List<AbilityCastModeView> result = new List<AbilityCastModeView>();
            foreach (AbilityCastModeDef mode in profile.castModes)
            {
                // This modifier instance belongs to this view and never mutates authored data.
                modifiers.hasCastMode = true; modifiers.castModeCost = mode.manaCost; modifiers.castModeDamageBonus = mode.damageBonus;
                AbilityDef effective = AbilityScaling.Apply(catalog.Abilities[ability], modifiers);
                string reason = rank < mode.minimumRank ? "Requires rank " + mode.minimumRank : !canAct ? "Action unavailable" : actor != null && actor.Energy < effective.cost ? "Insufficient mana" : "";
                result.Add(new AbilityCastModeView { id = mode.id, label = mode.label, minimumRank = mode.minimumRank, cost = effective.cost, range = effective.range, description = Describe(effective), enabled = reason == "", disabledReason = reason, targetIds = includeTargets && actor != null && reason == "" ? LegalTargets(actor, catalog.Abilities[ability], null, mode.id) : new string[0] });
            }
            modifiers.hasCastMode = false;
            return result.ToArray();
        }
    }
}
