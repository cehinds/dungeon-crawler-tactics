using System;
using System.Collections.Generic;

namespace DungeonCrawlerTactics
{
    public sealed partial class GameSession
    {
        private readonly List<EquipmentSlotSave> equipped = new List<EquipmentSlotSave>();
        private int LevelAt(int experience) { int level = 1; for (int i = 1; i < data.progression.xpThresholds.Length; i++) if (experience >= data.progression.xpThresholds[i]) level = i + 1; return level; }
        private int Victories(string atScreen, int index) { return Math.Min(data.encounters.Length, index + (atScreen == "victory" ? 1 : 0)); }
        private ClassStats PlayerStats(string id, string classId, int experience, List<EquipmentSlotSave> loadout)
        {
            ClassStats basic = Stats(classId); int growth = LevelAt(experience) - 1;
            ClassStats result = new ClassStats { classId = classId, hp = basic.hp + growth * data.progression.hpPerLevel, energy = basic.energy + growth * data.progression.manaPerLevel, move = basic.move + growth * data.progression.movePerLevel };
            foreach (EquipmentSlotSave slot in loadout) if (slot.unitId == id) { EquipmentDef gear = Gear(slot.equipmentId); result.hp += gear.hpBonus; result.energy += gear.manaBonus; result.move += gear.moveBonus; }
            return result;
        }
        private ClassStats PlayerStats(string id, string classId) { return PlayerStats(id, classId, xp, equipped); }
        private EquipmentDef Gear(string id) { EquipmentDef result = Array.Find(data.equipment, e => e.id == id); Require(result != null, "Unknown equipment."); return result; }
        private string[] Grants(string id, int experience, List<EquipmentSlotSave> loadout)
        {
            List<string> grants = new List<string>(); RosterDef definition = Definition(id); if (definition == null) return grants.ToArray();
            foreach (string ability in definition.innateAbilityIds) if (!grants.Contains(ability)) grants.Add(ability);
            foreach (SkillUnlockDef skill in data.progression.skillUnlocks) if ((string.IsNullOrEmpty(skill.rosterId) || skill.rosterId == id) && LevelAt(experience) >= skill.level && !grants.Contains(skill.abilityId)) grants.Add(skill.abilityId);
            foreach (EquipmentSlotSave slot in loadout) if (slot.unitId == id) foreach (string ability in Gear(slot.equipmentId).abilityIds) if (!grants.Contains(ability)) grants.Add(ability);
            return grants.ToArray();
        }
        private void SyncRosterFromBattle()
        {
            foreach (RosterDef definition in data.roster)
            {
                EntityState unit; if (!battle.Entities.TryGetValue(definition.id, out unit)) continue;
                RosterView member = roster[definition.id]; member.hp = unit.Hp; member.maxHp = unit.MaxHp; member.energy = unit.Energy; member.maxEnergy = units[unit.Id].maxEnergy;
            }
        }
        private void RefreshRosterStats(bool restore)
        {
            foreach (RosterDef definition in data.roster)
            {
                RosterView member = roster[definition.id]; ClassStats stats = PlayerStats(member.id, member.classId);
                member.hp = restore ? stats.hp : Math.Min(stats.hp, member.hp); member.maxHp = stats.hp;
                member.energy = restore ? stats.energy : Math.Min(stats.energy, member.energy); member.maxEnergy = stats.energy; member.move = member.effectiveMove = stats.move; member.level = LevelAt(xp);
            }
        }
        private void Rest()
        {
            Require(screen == "camp", "Rest in the safe room between encounters.");
            RefreshRosterStats(true); message = "The safe room restores every crawler's HP and mana. Equipment and skills are ready.";
        }
        private void Equip(GameCommand command, bool remove)
        {
            Require(screen == "camp", "Change equipment in the safe room.");
            RosterView member = GetRoster(command.unitId); Require(Definition(member.id).deployable, "Advisors do not equip field gear.");
            EquipmentDef gear = Gear(command.equipmentId);
            Require(gear.unlockEncounter <= Victories(screen, encounterIndex), "This equipment has not been earned yet.");
            EquipmentSlotSave owner = equipped.Find(e => e.equipmentId == gear.id);
            if (remove) { Require(owner != null && owner.unitId == member.id, "That crawler does not have this equipment."); equipped.Remove(owner); }
            else
            {
                Require(owner == null || owner.unitId == member.id, "This single-copy item is equipped by another crawler.");
                equipped.RemoveAll(e => e.unitId == member.id && Gear(e.equipmentId).slot == gear.slot);
                equipped.Add(new EquipmentSlotSave { unitId = member.id, equipmentId = gear.id });
            }
            RefreshRosterStats(false); message = member.label + (remove ? " unequipped " : " equipped ") + gear.label + ". Rest to restore HP and mana up to the new maximum.";
        }
        private void AwardProgression(int oldXp)
        {
            int before = LevelAt(oldXp), after = LevelAt(xp);
            if (after > before)
            {
                foreach (string id in SortedUnitIds())
                {
                    EntityState unit = battle.Entities[id]; if (unit.Team != "player") continue;
                    ClassStats stats = PlayerStats(id, unit.ClassId); int hpGain = stats.hp - unit.MaxHp, manaGain = stats.energy - units[id].maxEnergy;
                    unit.MaxHp = stats.hp; if (unit.Hp > 0) unit.Hp = Math.Min(stats.hp, unit.Hp + Math.Max(0, hpGain));
                    unit.Energy = Math.Min(stats.energy, unit.Energy + Math.Max(0, manaGain)); units[id].maxEnergy = stats.energy; units[id].move = stats.move;
                    unit.GrantedAbilities.Clear(); unit.GrantedAbilities.UnionWith(Grants(id, xp, equipped));
                }
                presentationEvents.Add(new PresentationEvent { type = "level_up", before = before, after = after, amount = after });
                AddLog("Party reached level " + after + ". Stats increased and eligible skills unlocked.");
            }
            SyncRosterFromBattle(); RefreshRosterStats(false);
            foreach (EquipmentDef gear in data.equipment) if (gear.unlockEncounter == encounterIndex + 1) { presentationEvents.Add(new PresentationEvent { type = "equipment_unlock", tag = gear.id }); AddLog("Equipment earned: " + gear.label + ". Equip it in the safe room."); }
        }
        private void PopulateProgression(GameView view)
        {
            int level = LevelAt(xp), next = level < data.progression.xpThresholds.Length ? data.progression.xpThresholds[level] : xp;
            List<SkillView> skills = new List<SkillView>(); foreach (SkillUnlockDef skill in data.progression.skillUnlocks) skills.Add(new SkillView { id = skill.id, label = skill.label, unitId = skill.rosterId, abilityId = skill.abilityId, level = skill.level, unlocked = level >= skill.level });
            view.progression = new ProgressionView { level = level, xp = xp, nextLevelXp = next, xpIntoLevel = xp - data.progression.xpThresholds[level - 1], xpToNextLevel = Math.Max(0, next - xp), maxLevel = data.progression.xpThresholds.Length, hpBonus = (level - 1) * data.progression.hpPerLevel, manaBonus = (level - 1) * data.progression.manaPerLevel, moveBonus = (level - 1) * data.progression.movePerLevel, skills = skills.ToArray() };
            List<EquipmentView> gearViews = new List<EquipmentView>();
            foreach (EquipmentDef gear in data.equipment) { EquipmentSlotSave owner = equipped.Find(e => e.equipmentId == gear.id); gearViews.Add(new EquipmentView { id = gear.id, label = gear.label, slot = gear.slot, hpBonus = gear.hpBonus, manaBonus = gear.manaBonus, moveBonus = gear.moveBonus, abilityIds = gear.abilityIds, unlockEncounter = gear.unlockEncounter, owned = gear.unlockEncounter <= Victories(screen, encounterIndex), equippedUnitId = owner == null ? null : owner.unitId }); }
            view.equipment = gearViews.ToArray(); bool rested = true;
            foreach (RosterView member in view.roster) if (member.deployable && (member.hp < member.maxHp || member.energy < member.maxEnergy)) rested = false;
            view.safeRoom = new SafeRoomView { available = screen == "camp", rested = rested, label = "Safe Room", description = "Rest to restore HP and mana, change equipment, and inspect skills before exploring." };
            List<QuestView> quests = new List<QuestView>();
            int wins = Victories(screen, encounterIndex); quests.Add(Quest("quest.floor", "Reach the floor exit", "Clear all encounters to open the exit.", wins, data.encounters.Length));
            ExplorationSave sector; if (encounterIndex < data.encounters.Length && exploration.TryGetValue(Sector.id, out sector))
            {
                HashSet<string> revealed = Revealed(sector); ExplorationPointDef door = Array.Find(Sector.points, p => p.kind == "encounter");
                quests.Add(Quest("quest.door", "Find the encounter door", "Explore the passages and discover the marked door.", revealed.Contains(ExploreKey(door.x, door.y)) ? 1 : 0, 1));
                int total = 0; foreach (ExplorationPointDef point in Sector.points) if (point.kind != "encounter") total++;
                quests.Add(Quest("quest.discoveries", "Inspect optional discoveries", "Claim caches and read notes in this sector.", sector.claimed.Length, total));
            }
            if (units.Count > 0) { int total = 0, defeated = 0; foreach (string id in UnitIds("enemy")) { total++; if (battle.Entities[id].Hp == 0) defeated++; } quests.Add(Quest("quest.encounter", "Clear " + Encounter.label, "Defeat the enemies guarding this room.", defeated, total)); }
            view.quests = quests.ToArray();
        }
        private static QuestView Quest(string id, string label, string description, int progress, int total) { return new QuestView { id = id, label = label, description = description, progress = progress, total = total, complete = progress >= total }; }
        private GameSave UpgradeProgressionSave(GameSave source)
        {
            Require(source.progressionVersion == 0 || source.progressionVersion == 1, "Unknown progression save version.");
            if (source.progressionVersion == 1) return source;
            Require(source.equipped != null && source.equipped.Length == 0, "Legacy saves cannot declare equipped gear.");
            List<RosterView> members = new List<RosterView>(); List<EquipmentSlotSave> empty = new List<EquipmentSlotSave>();
            foreach (RosterView old in source.roster)
            {
                Require(old != null && old.id != null && Definition(old.id) != null && old.classId != null && catalog.Classes.ContainsKey(old.classId), "Invalid legacy progression roster.");
                ClassStats basic = Stats(old.classId), stats = PlayerStats(old.id, old.classId, source.xp, empty);
                Require(old.maxHp == basic.hp && old.hp >= 0 && old.hp <= old.maxHp, "Invalid legacy progression health.");
                members.Add(new RosterView { id = old.id, label = old.label, classId = old.classId, selected = old.selected, hp = ScaleHealth(old.hp, basic.hp, stats.hp), maxHp = stats.hp,
                    energy = old.maxEnergy == 0 ? stats.energy : Math.Min(stats.energy, old.energy), maxEnergy = stats.energy, move = stats.move, level = LevelAt(source.xp) });
            }
            List<SavedUnit> snapshots = new List<SavedUnit>();
            foreach (SavedUnit old in source.units)
            {
                Require(old != null, "Invalid legacy progression unit.");
                if (old.team != "player") { snapshots.Add(old); continue; }
                Require(old.id != null && Definition(old.id) != null && old.classId != null && catalog.Classes.ContainsKey(old.classId), "Unknown legacy progression unit.");
                ClassStats basic = Stats(old.classId), stats = PlayerStats(old.id, old.classId, source.xp, empty);
                Require(old.maxHp == basic.hp && old.maxEnergy == basic.energy && old.move == basic.move && old.hp >= 0 && old.hp <= old.maxHp && old.energy >= 0 && old.energy <= old.maxEnergy, "Invalid legacy progression stats.");
                snapshots.Add(new SavedUnit { id = old.id, label = old.label, classId = old.classId, team = old.team, x = old.x, y = old.y, hp = ScaleHealth(old.hp, basic.hp, stats.hp), maxHp = stats.hp,
                    energy = Math.Min(stats.energy, old.energy), maxEnergy = stats.energy, move = stats.move, moved = old.moved, acted = old.acted, tags = old.tags, permanentTags = old.permanentTags });
            }
            return new GameSave { schemaVersion = source.schemaVersion, contentVersion = source.contentVersion, progressionVersion = 1, equipped = new EquipmentSlotSave[0],
                screen = source.screen, phase = source.phase, selectedUnitId = source.selectedUnitId, encounterIndex = source.encounterIndex, round = source.round, xp = source.xp, rewardChosen = source.rewardChosen,
                roster = members.ToArray(), units = snapshots.ToArray(), tiles = source.tiles, inventory = source.inventory, timedTags = source.timedTags, exploration = source.exploration, log = source.log };
        }
        private List<EquipmentSlotSave> ValidateEquipment(GameSave save)
        {
            Require(save.progressionVersion == 1 && save.equipped != null && save.equipped.Length <= data.roster.Length * 3, "Invalid progression equipment collection.");
            List<EquipmentSlotSave> result = new List<EquipmentSlotSave>(); HashSet<string> owned = new HashSet<string>(), slots = new HashSet<string>();
            foreach (EquipmentSlotSave record in save.equipped)
            {
                Require(record != null && record.unitId != null && Definition(record.unitId) != null && Definition(record.unitId).deployable, "Invalid equipment owner.");
                EquipmentDef gear = Gear(record.equipmentId);
                Require(gear.unlockEncounter <= Victories(save.screen, save.encounterIndex) && owned.Add(gear.id) && slots.Add(record.unitId + ":" + gear.slot), "Unearned, duplicated, or conflicting equipment.");
                result.Add(new EquipmentSlotSave { unitId = record.unitId, equipmentId = gear.id });
            }
            return result;
        }
    }
}
