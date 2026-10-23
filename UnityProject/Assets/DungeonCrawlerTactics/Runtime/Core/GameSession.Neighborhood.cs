using System;
using System.Collections.Generic;
namespace DungeonCrawlerTactics
{
    public sealed partial class GameSession
    {
        private NeighborhoodSave neighborhoodState = new NeighborhoodSave();
        private GameCommand pendingNeighborhood;
        private NeighborhoodInteractionDef NeighborhoodInteraction(string id) { return data.neighborhood == null ? null : Array.Find(data.neighborhood.interactions, i => i.id == id); }
        private NeighborhoodOptionDef NeighborhoodOption(NeighborhoodInteractionDef interaction, string id) { return interaction == null ? null : Array.Find(interaction.options, o => o.id == id); }
        private int NeighborhoodFloorIndex { get { return data.neighborhood == null || data.journey == null ? -1 : Array.FindIndex(data.journey.floors, f => f.encounter != null && f.encounter.exploration.id == data.neighborhood.sectorId); } }
        private bool NeighborhoodActive { get { return data.neighborhood != null && journey != null && journey.floorIndex == NeighborhoodFloorIndex && expeditionState == null && Scenario == null && customMap == null; } }
        private string NeighborhoodReason(NeighborhoodInteractionDef interaction, NeighborhoodOptionDef option, string owner)
        {
            if (!NeighborhoodActive) return "Available in the Over City story neighborhood.";
            if (Array.Exists(neighborhoodState.receipts, r => r.interactionId == interaction.id)) return "This choice has already been resolved.";
            if (interaction.camp) { if (screen != "camp") return "Choose preparation in camp before exploring."; }
            else
            {
                if (screen != "explore" || Sector.id != data.neighborhood.sectorId) return "Visit this neighborhood discovery first.";
                ExplorationSave state = exploration[Sector.id]; ExplorationPointDef point = Array.Find(Sector.points, p => p.id == interaction.pointId);
                if (point == null || !Revealed(state).Contains(ExploreKey(point.x, point.y))) return "Discover this location first.";
                if (Math.Abs(state.x - point.x) + Math.Abs(state.y - point.y) > 1) return "Move beside this discovery first.";
                if (Array.IndexOf(state.claimed, point.id) >= 0) return "This discovery has already been resolved.";
            }
            if (!string.IsNullOrEmpty(option.abilityId))
            {
                RosterView member; if (owner == null || !roster.TryGetValue(owner, out member) || !member.selected) return "Choose a deployed crawler with the required skill.";
                bool knows = Array.IndexOf(catalog.Classes[member.classId].abilityIds, option.abilityId) >= 0 || Array.IndexOf(Grants(owner, xp, equipped), option.abilityId) >= 0;
                SkillPracticeSave practice = practices.Find(p => p.unitId == owner && p.abilityId == option.abilityId);
                if (!knows || PracticeView(owner, option.abilityId, practice == null ? 0 : practice.uses).rank < option.minimumRank) return "Requires the named skill at rank " + option.minimumRank + ".";
            }
            if (option.costCount > 0 && inventory[option.costItemId] < option.costCount) return "Not enough shared supplies for this approach.";
            Dictionary<string, int> changes = NeighborhoodChanges(interaction, option);
            foreach (var change in changes) if ((long)inventory[change.Key] + change.Value < 0 || (long)inventory[change.Key] + change.Value > 10000) return "Shared supply capacity would be exceeded.";
            return "";
        }
        private Dictionary<string, int> NeighborhoodChanges(NeighborhoodInteractionDef interaction, NeighborhoodOptionDef option)
        {
            Dictionary<string, int> result = new Dictionary<string, int>(StringComparer.Ordinal);
            Action<string, int> add = (id, count) => { if (count != 0) result[id] = (result.ContainsKey(id) ? result[id] : 0) + count; };
            add(option.costItemId, -option.costCount); add(option.rewardItemId, option.rewardCount);
            foreach (NeighborhoodChallengeDef c in data.neighborhood.challenges) if (c.interactionId == interaction.id && (string.IsNullOrEmpty(c.optionId) || c.optionId == option.id) && Array.IndexOf(neighborhoodState.challengeIds, c.id) < 0) add(c.rewardItemId, c.rewardCount);
            return result;
        }
        private NeighborhoodForecast ResolveNeighborhood(GameCommand command)
        {
            NeighborhoodInteractionDef interaction = NeighborhoodInteraction(command.targetId); NeighborhoodOptionDef option = NeighborhoodOption(interaction, command.nodeId);
            Require(interaction != null && option != null, "Unknown neighborhood approach."); string reason = NeighborhoodReason(interaction, option, command.unitId); Require(reason == "", reason);
            Dictionary<string, int> changes = NeighborhoodChanges(interaction, option); List<InventoryEntry> before = new List<InventoryEntry>(), after = new List<InventoryEntry>();
            foreach (ItemDef item in catalog.Items.Values) if (changes.ContainsKey(item.id)) { before.Add(new InventoryEntry { itemId = item.id, count = inventory[item.id] }); after.Add(new InventoryEntry { itemId = item.id, count = inventory[item.id] + changes[item.id] }); }
            List<string> challenges = new List<string>(); foreach (NeighborhoodChallengeDef c in data.neighborhood.challenges) if (c.interactionId == interaction.id && (string.IsNullOrEmpty(c.optionId) || c.optionId == option.id) && Array.IndexOf(neighborhoodState.challengeIds, c.id) < 0) challenges.Add(c.id);
            return new NeighborhoodForecast { interactionId = interaction.id, optionId = option.id, label = option.label, description = option.description, costItemId = option.costItemId, costCount = option.costCount, rewardItemId = option.rewardItemId, rewardCount = option.rewardCount, beforeCost = option.costCount > 0 ? inventory[option.costItemId] : 0, afterCost = option.costCount > 0 ? inventory[option.costItemId] + changes[option.costItemId] : 0, beforeReward = option.rewardCount > 0 ? inventory[option.rewardItemId] : 0, afterReward = option.rewardCount > 0 ? inventory[option.rewardItemId] + changes[option.rewardItemId] : 0, clue = option.clue, challengeIds = challenges.ToArray(), beforeItems = before.ToArray(), afterItems = after.ToArray() };
        }
        private bool TryNeighborhoodCommand(GameCommand command)
        {
            if (TryNeighborhoodStandaloneCommand(command)) return true;
            if (command.type != "preview_neighborhood" && command.type != "confirm_neighborhood" && command.type != "cancel_neighborhood") { pendingNeighborhood = null; return false; }
            if (command.type == "cancel_neighborhood") { pendingNeighborhood = null; message = "Neighborhood approach canceled. Nothing spent or awarded."; return true; }
            if (command.type == "preview_neighborhood") { pendingNeighborhood = null; ResolveNeighborhood(command); pendingNeighborhood = new GameCommand { targetId = command.targetId, nodeId = command.nodeId, unitId = command.unitId }; message = "Review the exact supply changes and challenge rewards, then confirm or cancel."; return true; }
            Require(pendingNeighborhood != null, "Preview a neighborhood approach first."); NeighborhoodForecast forecast = ResolveNeighborhood(pendingNeighborhood);
            foreach (InventoryEntry item in forecast.afterItems) inventory[item.itemId] = item.count;
            var receipts = new List<NeighborhoodReceipt>(neighborhoodState.receipts); receipts.Add(new NeighborhoodReceipt { interactionId = forecast.interactionId, optionId = forecast.optionId, unitId = pendingNeighborhood.unitId }); neighborhoodState.receipts = receipts.ToArray();
            var challenges = new List<string>(neighborhoodState.challengeIds); foreach (string id in forecast.challengeIds) { challenges.Add(id); presentationEvents.Add(new PresentationEvent { type = "achievement", tag = id }); } neighborhoodState.challengeIds = challenges.ToArray();
            NeighborhoodInteractionDef interaction = NeighborhoodInteraction(forecast.interactionId);
            if (!interaction.camp) { ExplorationSave state = exploration[data.neighborhood.sectorId]; var claimed = new List<string>(state.claimed); claimed.Add(interaction.pointId); state.claimed = claimed.ToArray(); }
            pendingNeighborhood = null; message = forecast.description + (string.IsNullOrEmpty(forecast.clue) ? "" : " Clue: " + forecast.clue); AddLog(interaction.label + ": " + message); return true;
        }
        private NeighborhoodView BuildNeighborhoodView()
        {
            if (data.neighborhood == null) return null;
            List<NeighborhoodInteractionView> interactions = new List<NeighborhoodInteractionView>(); List<string> clues = new List<string>();
            foreach (NeighborhoodReceipt r in neighborhoodState.receipts) { var option = NeighborhoodOption(NeighborhoodInteraction(r.interactionId), r.optionId); if (option != null && !string.IsNullOrEmpty(option.clue)) clues.Add(option.clue); }
            foreach (NeighborhoodInteractionDef i in data.neighborhood.interactions)
            {
                List<NeighborhoodOptionView> options = new List<NeighborhoodOptionView>(); foreach (NeighborhoodOptionDef o in i.options) { string reason = NeighborhoodReason(i, o, selected); if (!string.IsNullOrEmpty(o.abilityId) && reason != "") foreach (RosterView member in roster.Values) if (member.selected && NeighborhoodReason(i, o, member.id) == "") { reason = ""; break; } List<string> eligible = new List<string>(); foreach (RosterView member in roster.Values) if (member.selected && NeighborhoodReason(i, o, member.id) == "") eligible.Add(member.id); options.Add(new NeighborhoodOptionView { eligibleUnitIds = eligible.ToArray(), id = o.id, label = o.label, description = o.description, enabled = reason == "", disabledReason = reason, costItemId = o.costItemId, costCount = o.costCount, rewardItemId = o.rewardItemId, rewardCount = o.rewardCount, abilityId = o.abilityId, minimumRank = o.minimumRank, clue = o.clue }); }
                interactions.Add(new NeighborhoodInteractionView { id = i.id, pointId = i.pointId, label = i.label, description = i.description, camp = i.camp, completed = Array.Exists(neighborhoodState.receipts, r => r.interactionId == i.id), options = options.ToArray() });
            }
            List<NeighborhoodChallengeView> challenges = new List<NeighborhoodChallengeView>(); foreach (NeighborhoodChallengeDef c in data.neighborhood.challenges) challenges.Add(new NeighborhoodChallengeView { id = c.id, label = c.label, description = c.description, rewardItemId = c.rewardItemId, rewardCount = c.rewardCount, earned = Array.IndexOf(neighborhoodState.challengeIds, c.id) >= 0 });
            return new NeighborhoodView { id = data.neighborhood.id, label = data.neighborhood.label, description = data.neighborhood.description, interactions = interactions.ToArray(), challenges = challenges.ToArray(), clues = clues.ToArray(), canConfirm = pendingNeighborhood != null, forecast = pendingNeighborhood == null ? null : ResolveNeighborhood(pendingNeighborhood), active = NeighborhoodActive, standalone = neighborhoodState.campaign != null };
        }
        private static NeighborhoodSave CloneNeighborhood(NeighborhoodSave source) { return new NeighborhoodSave { version = source.version, receipts = Array.ConvertAll(source.receipts, r => new NeighborhoodReceipt { interactionId = r.interactionId, optionId = r.optionId, unitId = r.unitId }), challengeIds = (string[])source.challengeIds.Clone(), campaign = source.campaign }; }
        private NeighborhoodSave CaptureNeighborhood()
        {
            NeighborhoodSave copy = CloneNeighborhood(neighborhoodState);
            if (copy.campaign != null) { GameSession validator = new GameSession(scenarioValidationContent, data); GameView result = validator.ImportSave(copy.campaign); Require(!result.message.StartsWith("Save rejected:", StringComparison.Ordinal), "Invalid neighborhood backup."); copy.campaign = validator.ExportSave(); }
            return copy;
        }
        private static void ValidateNeighborhoodSaveGraph(GameSave save)
        {
            if (save == null) return;
            var visited = new HashSet<GameSave>(); var pending = new Queue<GameSave>(); pending.Enqueue(save);
            while (pending.Count > 0)
            {
                GameSave current = pending.Dequeue(); Require(visited.Add(current) && visited.Count <= 4, "Nested or cyclic campaign backups are invalid.");
                if (current.neighborhood != null && current.neighborhood.campaign != null) { Require(current.expedition == null && current.scenario == null && current.neighborhood.campaign.expedition == null && current.neighborhood.campaign.scenario == null && (current.neighborhood.campaign.neighborhood == null || current.neighborhood.campaign.neighborhood.campaign == null), "Nested neighborhood backups are invalid."); pending.Enqueue(current.neighborhood.campaign); }
                if (current.expedition != null && current.expedition.campaign != null) pending.Enqueue(current.expedition.campaign);
                if (current.scenario != null && current.scenario.campaign != null) pending.Enqueue(current.scenario.campaign);
            }
        }
        private NeighborhoodSave ValidateNeighborhood(GameSave save)
        {
            NeighborhoodSave source = save.neighborhood ?? new NeighborhoodSave();
            Require(save.exploration != null, "Missing exploration collection.");
            Require(source.version == 1 && source.receipts != null && source.challengeIds != null, "Invalid neighborhood save.");
            Require(data.neighborhood != null || (source.receipts.Length == 0 && source.challengeIds.Length == 0 && source.campaign == null), "No neighborhood definitions for these receipts.");
            if (data.neighborhood == null) return CloneNeighborhood(source);
            Require(source.receipts.Length <= data.neighborhood.interactions.Length && source.challengeIds.Length <= data.neighborhood.challenges.Length, "Too many neighborhood receipts.");
            HashSet<string> ids = new HashSet<string>(), expectedChallenges = new HashSet<string>();
            GameSave baseline = save.expedition != null ? save.expedition.campaign : save.scenario != null ? save.scenario.campaign : null;
            foreach (NeighborhoodReceipt r in source.receipts)
            {
                NeighborhoodInteractionDef i = r == null ? null : NeighborhoodInteraction(r.interactionId); NeighborhoodOptionDef o = r == null ? null : NeighborhoodOption(i, r.optionId);
                Require(i != null && o != null && ids.Add(i.id), "Unknown or duplicate neighborhood choice.");
                Require(save.journey != null && save.encounterIndex >= NeighborhoodFloorIndex, "Neighborhood receipt predates Over City.");
                Require(string.IsNullOrEmpty(o.abilityId) || (r.unitId != null && Array.Exists(data.roster, m => m.id == r.unitId && m.deployable)), "Invalid skilled neighborhood owner.");
                if (!i.camp && baseline == null) { ExplorationSave explored = Array.Find(save.exploration, s => s != null && s.sectorId == data.neighborhood.sectorId); Require(explored != null && explored.claimed != null && Array.IndexOf(explored.claimed, i.pointId) >= 0, "Neighborhood receipt is missing its claimed discovery."); }
                foreach (NeighborhoodChallengeDef c in data.neighborhood.challenges) if (c.interactionId == i.id && (string.IsNullOrEmpty(c.optionId) || c.optionId == o.id)) expectedChallenges.Add(c.id);
            }
            ids.Clear(); foreach (string id in source.challengeIds) Require(id != null && expectedChallenges.Contains(id) && ids.Add(id), "Unmatched neighborhood challenge reward."); Require(ids.Count == expectedChallenges.Count, "Missing neighborhood challenge receipt.");
            if (baseline != null)
            {
                Require(baseline.expedition == null && baseline.scenario == null, "Nested neighborhood backup is invalid."); NeighborhoodSave expected = ValidateNeighborhood(baseline);
                Require(SameNeighborhood(source, expected), "Standalone missions cannot change neighborhood receipts.");
            }
            if (source.campaign != null)
            {
                Require(save.journey != null && save.journey.floorIndex == NeighborhoodFloorIndex && save.encounterIndex == NeighborhoodFloorIndex && save.expedition == null && save.scenario == null && save.customMap == null && save.screen != "complete", "Invalid neighborhood sampler state.");
                Require(source.campaign.neighborhood == null || source.campaign.neighborhood.campaign == null, "Nested neighborhood campaigns are invalid.");
                Require(source.campaign.scenario == null && source.campaign.expedition == null, "Neighborhood backup cannot contain standalone missions.");
                GameSession validator = new GameSession(scenarioValidationContent, data); GameView result = validator.ImportSave(source.campaign); Require(!result.message.StartsWith("Save rejected:", StringComparison.Ordinal), "Invalid neighborhood campaign backup.");
                NeighborhoodSave copy = CloneNeighborhood(source); copy.campaign = validator.ExportSave(); return copy;
            }
            return CloneNeighborhood(source);
        }
        private static bool SameNeighborhood(NeighborhoodSave a, NeighborhoodSave b)
        {
            if (a.receipts.Length != b.receipts.Length || a.challengeIds.Length != b.challengeIds.Length) return false;
            for (int i = 0; i < a.receipts.Length; i++) if (a.receipts[i].interactionId != b.receipts[i].interactionId || a.receipts[i].optionId != b.receipts[i].optionId || a.receipts[i].unitId != b.receipts[i].unitId) return false;
            for (int i = 0; i < a.challengeIds.Length; i++) if (a.challengeIds[i] != b.challengeIds[i]) return false;
            return (a.campaign == null) == (b.campaign == null);
        }
    }
}
