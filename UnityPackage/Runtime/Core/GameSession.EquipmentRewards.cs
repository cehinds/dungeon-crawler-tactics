using System;
using System.Collections.Generic;
namespace DungeonCrawlerTactics
{
    public sealed partial class GameSession
    {
        private readonly List<EquipmentRewardClaim> equipmentRewardClaims = new List<EquipmentRewardClaim>();
        private EquipmentPreviewView pendingEquipment;
        private int EquipmentWins(GameSave save)
        {
            if (save.expedition != null) return EquipmentWins(save.expedition.campaign);
            if (save.scenario != null) return 0;
            if (save.generatedDungeon != null && save.generatedDungeon.floorPlan != null) return CampaignWins(save.generatedCampaign, save.generatedDungeon, save.screen);
            if (save.generatedDungeon != null) return save.generatedDungeon.cleared || save.screen == "victory" ? 1 : 0;
            if (save.journey != null) { int wins = 0; for (int i = 0; i < Math.Min(save.encounterIndex, 8); i++) if (data.journey.floors[i].encounter != null) wins++; return wins + (save.screen == "victory" ? 1 : 0); }
            return Victories(save.screen, save.encounterIndex);
        }
        private bool EquipmentOwned(EquipmentDef gear) { return gear.rewardOnly ? equipmentRewardClaims.Exists(c => c.equipmentId == gear.id) : gear.unlockEncounter <= LiveVictories(); }
        private string EquipmentUnlockReason(EquipmentDef gear) { EquipmentRewardTierDef tier = Array.Find(data.equipmentRewardTiers, t => Array.IndexOf(t.equipmentIds, gear.id) >= 0); return tier == null ? "Earned after " + gear.unlockEncounter + " victories." : "Choose after " + tier.requiredWins + " completed battles: " + tier.label + "."; }
        private static string EquipmentRewardId(string tier, string gear) { return "equipment:" + tier + ":" + gear; }
        private void AddEquipmentRewards(List<RewardView> rewards)
        {
            if (Scenario != null || ExpeditionCampaign != null) return;
            int wins = EquipmentWins(new GameSave { screen = screen, encounterIndex = encounterIndex, generatedDungeon = generatedDungeon, generatedCampaign = generatedCampaign, journey = journey });
            foreach (EquipmentRewardTierDef tier in data.equipmentRewardTiers) if (tier.requiredWins == wins && !equipmentRewardClaims.Exists(c => c.tierId == tier.id))
                foreach (string id in tier.equipmentIds) { EquipmentDef gear = Gear(id); rewards.Add(new RewardView { id = EquipmentRewardId(tier.id, id), equipmentId = id, tierId = tier.id, label = gear.label, description = gear.description ?? EquipmentUnlockReason(gear) }); }
        }
        private void ChooseReward(string id)
        {
            List<RewardView> options = new List<RewardView>(); AddEquipmentRewards(options);
            RewardView choice = options.Find(o => o.id == id);
            if (choice != null) { equipmentRewardClaims.Add(new EquipmentRewardClaim { tierId = choice.tierId, equipmentId = choice.equipmentId }); rewardChosen = true; message = "Equipment earned: " + choice.label + ". Equip it outside combat."; AddLog(message); return; }
            RewardDef reward = Array.Find(data.rewards, r => r.id == id); Require(reward != null, "Unknown or unavailable reward.");
            if (!string.IsNullOrEmpty(reward.itemId)) inventory[reward.itemId] += reward.count;
            foreach (EntityState unit in battle.Entities.Values) if (!unit.IsTile && unit.Team == "player" && unit.Hp > 0) unit.Hp = Math.Min(unit.MaxHp, unit.Hp + reward.heal);
            rewardChosen = true; message = "Sponsor delivery: " + reward.label + "."; AddLog(message);
        }
        private void ValidateEquipmentClaims(GameSave save)
        {
            HashSet<string> tiers = new HashSet<string>(), items = new HashSet<string>();
            foreach (EquipmentRewardClaim claim in save.equipmentRewardClaims ?? new EquipmentRewardClaim[0])
            {
                Require(claim != null, "Invalid equipment reward claim."); EquipmentRewardTierDef tier = Array.Find(data.equipmentRewardTiers, t => t.id == claim.tierId);
                Require(tier != null && Array.IndexOf(tier.equipmentIds, claim.equipmentId) >= 0 && tier.requiredWins <= EquipmentWins(save) && tiers.Add(tier.id) && items.Add(claim.equipmentId), "Invalid, duplicate or unearned equipment reward claim.");
                Require(save.screen != "victory" || tier.requiredWins != EquipmentWins(save) || save.rewardChosen, "Active victory claim requires its reward choice receipt.");
            }
        }
        private EquipmentStatsView EquipmentStats(RosterView member, List<EquipmentSlotSave> loadout)
        {
            ClassStats stats = LoadoutStats(member.id, member.classId, loadout);
            return new EquipmentStatsView { maxHp = stats.hp, maxEnergy = stats.energy, move = stats.move, hp = Math.Min(member.hp, stats.hp), energy = Math.Min(member.energy, stats.energy) };
        }
        private void PreviewEquipment(GameCommand command, bool remove)
        {
            Require(screen == "camp" || screen == "explore", "Change equipment outside combat."); RosterView member = GetRoster(command.unitId); Require(Definition(member.id).deployable, "Advisors do not equip field gear."); EquipmentDef gear = Gear(command.equipmentId); Require(EquipmentOwned(gear), "This equipment has not been earned yet.");
            EquipmentSlotSave owner = equipped.Find(e => e.equipmentId == gear.id), previous = equipped.Find(e => e.unitId == member.id && Gear(e.equipmentId).slot == gear.slot);
            Require(remove ? owner != null && owner.unitId == member.id : owner == null || owner.unitId == member.id, "Equipment is not available for this crawler.");
            List<EquipmentSlotSave> next = new List<EquipmentSlotSave>(equipped); next.RemoveAll(e => e.unitId == member.id && Gear(e.equipmentId).slot == gear.slot); if (!remove) next.Add(new EquipmentSlotSave { unitId = member.id, equipmentId = gear.id });
            List<string> before = new List<string>(Grants(member.id, xp, equipped)), after = new List<string>(Grants(member.id, xp, next)); before.AddRange(catalog.Classes[member.classId].abilityIds); after.AddRange(catalog.Classes[member.classId].abilityIds);
            pendingEquipment = new EquipmentPreviewView { unitId = member.id, equipmentId = gear.id, previousGearId = previous == null ? null : previous.equipmentId, remove = remove, canConfirm = true, before = EquipmentStats(member, equipped), after = EquipmentStats(member, next), gainedAbilityIds = after.FindAll(a => !before.Contains(a)).ToArray(), lostAbilityIds = before.FindAll(a => !after.Contains(a)).ToArray() };
        }
        private void ConfirmEquipment() { EquipmentPreviewView preview = pendingEquipment; pendingEquipment = null; Require(preview != null, "Preview equipment first."); Equip(new GameCommand { unitId = preview.unitId, equipmentId = preview.equipmentId }, preview.remove); }
        private int FloorXp(GeneratedDungeonState state, string atScreen)
        {
            int result = 0; foreach (GeneratedEncounterGroup group in state.floorPlan.groups) if (Has(state.defeatedGroupIds, group.id) || atScreen == "victory" && group.id == state.activeGroupId) result += group.rewardXp == 0 ? data.encounters[0].xp : group.rewardXp; return result;
        }
        private int CampaignXp(GeneratedCampaignState campaign, GeneratedDungeonState current, string atScreen)
        {
            int result = FloorXp(current, atScreen); if (campaign != null) for (int i = 0; i < campaign.archives.Length; i++) { GeneratedDungeonState archive = CopyGenerated(campaign.archives[i]); if (archive.floorPlan == null) archive.floorPlan = campaign.plan.floors[i]; result += FloorXp(archive, "explore"); } return result;
        }
    }
}
