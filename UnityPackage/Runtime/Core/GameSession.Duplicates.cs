using System;
using System.Collections.Generic;
namespace DungeonCrawlerTactics
{
    public sealed partial class GameSession
    {
        private void RegisterDuplicates()
        {
            foreach (EntityState entity in battle.Entities.Values)
                if (entity.DuplicateSourceId != null && !units.ContainsKey(entity.Id))
                    units.Add(entity.Id, new SavedUnit { id = entity.Id, label = "Clockwork " + Label(entity.DuplicateSourceId), classId = entity.ClassId, team = entity.Team, maxEnergy = 0, move = entity.DuplicateMove });
        }
        private void TickDuplicates()
        {
            foreach (string id in SortedUnitIds())
            {
                EntityState entity = battle.Entities[id]; if (entity.DuplicateSourceId == null) continue;
                entity.DuplicateRounds--;
                if (entity.DuplicateRounds > 0) continue;
                presentationEvents.Add(new PresentationEvent { type = "despawn", actorId = id, targetId = id });
                battle.Entities.Remove(id); units.Remove(id); timed.RemoveAll(t => t.entityId == id);
            }
        }
        private void ValidateDuplicatePairs(GameSave save)
        {
            foreach (SavedUnit copy in save.units)
            {
                if (copy == null || copy.duplicateSourceId == null) continue;
                int count = 0;
                foreach (SavedUnit sibling in save.units) if (sibling != null && sibling.duplicateCasterId == copy.duplicateCasterId) { count++; Require(sibling.duplicateSourceId == copy.duplicateSourceId && sibling.duplicateRounds == copy.duplicateRounds, "Clockwork pair source or lifetime disagrees."); }
                Require(count == 2, "Clockwork copies require a complete pair.");
            }
        }
        private void ValidateDuplicate(SavedUnit unit, GameSave save, Dictionary<string, RosterView> savedRoster, List<EquipmentSlotSave> gear, List<StatAllocationSave> allocated, List<string> nodes, out int hp, out int energy, out int move, out string label)
        {
            Require(unit.team == "player" && unit.duplicateSourceId != null && unit.duplicateCasterId != null && unit.duplicateRounds >= 1 && unit.duplicateRounds <= 20 && (unit.id == "clockwork." + unit.duplicateCasterId + ".0" || unit.id == "clockwork." + unit.duplicateCasterId + ".1"), "Invalid clockwork duplicate identity or duration.");
            Require(savedRoster.ContainsKey(unit.duplicateSourceId) && savedRoster[unit.duplicateSourceId].selected && savedRoster.ContainsKey(unit.duplicateCasterId) && savedRoster[unit.duplicateCasterId].selected, "Clockwork source or caster is not deployed.");
            RosterDef source = Definition(unit.duplicateSourceId); RosterView sourceView = savedRoster[source.id];
            Require(unit.classId == sourceView.classId, "Clockwork copy changed its pet class.");
            RosterView caster = savedRoster[unit.duplicateCasterId]; bool allowed = false; hp = energy = move = 0;
            List<string> summonAbilities = new List<string>(Grants(caster.id, save.xp, gear, nodes, caster.classId, caster.specialtyClassId ?? "", save.journey == null ? 18 : save.journey.floorIndex + 1));
            if (save.journey == null || save.journey.floorIndex >= 2) foreach (string id in catalog.Classes[caster.classId].abilityIds) if (!summonAbilities.Contains(id)) summonAbilities.Add(id);
            foreach (string id in summonAbilities)
            {
                SkillPracticeSave practice = save.development == null || save.development.practice == null ? null : Array.Find(save.development.practice, p => p.unitId == caster.id && p.abilityId == id);
                int savedCap = save.journey != null && save.journey.floorIndex < 2 ? SkillRankProgression.NormalRankCap : Definition(caster.id).maxSkillRank;
                int rank = SkillRankProgression.Rank(data.development.practice, id, practice == null ? 0 : practice.uses, savedCap);
                SkillRankView[] rows = SkillRankProgression.Table(data.development.practice, id);
                // Summoning grants practice after resolution, and surviving copies retain their creation rank.
                for (int r = 0; r < rank; r++)
                    foreach (EffectDef effect in AbilityScaling.Apply(catalog.Abilities[id], AbilityScaling.Modifiers(rows[r])).effects)
                        if (effect.op == "DuplicatePet" && Array.IndexOf(source.combatTags, effect.tag) >= 0 && unit.maxHp == effect.summonHp && unit.move == effect.summonMove && unit.duplicateRounds <= effect.summonRounds) { allowed = true; hp = effect.summonHp; move = effect.summonMove; }
            }
            Require(allowed, "Clockwork duplicate has no eligible spell or pet source.");
            label = "Clockwork " + source.label;
            Require(unit.permanentTags != null && unit.permanentTags.Length == 0, "Clockwork copies have no permanent traits.");
        }
    }
}
