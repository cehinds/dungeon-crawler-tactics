using System;
using System.Collections.Generic;
namespace DungeonCrawlerTactics
{
    public sealed partial class GameSession
    {
        private ExpeditionSave expeditionState;
        private EncounterDef expeditionEncounter;
        private GameSave ExpeditionCampaign { get { return expeditionState == null ? null : expeditionState.campaign; } }
        private ExpeditionDef Expedition { get { return expeditionState == null ? null : Array.Find(data.expeditions, e => e.id == expeditionState.id); } }
        private EncounterDef ActiveExpeditionEncounter { get { return expeditionEncounter; } }
        private void ClearExpedition() { expeditionState = null; expeditionEncounter = null; }
        private ExpeditionOptionView[] ExpeditionOptions()
        {
            List<ExpeditionOptionView> result = new List<ExpeditionOptionView>();
            foreach (ExpeditionDef expedition in data.expeditions)
            {
                List<string> enemies = new List<string>(); foreach (SpawnDef enemy in expedition.encounter.enemies) { string label = catalog.Classes[enemy.classId].label; if (!enemies.Contains(label)) enemies.Add(label); }
                result.Add(new ExpeditionOptionView { id = expedition.id, label = expedition.label, description = expedition.description, objective = expedition.objective, theme = expedition.theme, difficulty = expedition.difficulty, enemyTypes = enemies.ToArray() });
            }
            return result.ToArray();
        }
        private ExpeditionView ExpeditionView()
        {
            ExpeditionDef expedition = Expedition;
            return expedition == null ? null : new ExpeditionView { id = expedition.id, label = expedition.label, description = expedition.description, objective = expedition.objective, theme = expedition.theme, difficulty = expedition.difficulty, decorations = Array.ConvertAll(expedition.decorations, p => new MapPlacement { id = p.id, assetId = p.assetId, layer = p.layer, x = p.x, y = p.y, rotation = p.rotation, blocksMovement = p.blocksMovement }) };
        }
        private bool TryExpeditionCommand(GameCommand command)
        {
            if (command.type == "expedition_start")
            {
                Require(expeditionState == null && Scenario == null, "Return to your campaign before starting another expedition.");
                ExpeditionDef expedition = Array.Find(data.expeditions, e => e.id == command.targetId);
                Require(expedition != null, "Unknown expedition."); Require(PartyCount() == data.partySize, "Choose exactly " + data.partySize + " crawlers before entering an expedition.");
                GameSave campaign = ExportSave();
                StartExpedition(expedition, campaign);
                return true;
            }
            if (expeditionState == null) return false;
            if (command.type == "expedition_return" || command.type == "continue")
            {
                GameSave campaign = expeditionState.campaign;
                GameView restored = ImportSave(campaign);
                Require(!restored.message.StartsWith("Save rejected:", StringComparison.Ordinal), "The expedition campaign backup could not be restored.");
                message = "Campaign restored exactly. Expedition training grants no campaign loot or XP."; return true;
            }
            if (command.type == "expedition_retry" || command.type == "retry")
            {
                Require(screen == "defeat" || screen == "victory", "Finish the expedition before retrying.");
                ExpeditionDef expedition = Expedition; GameSave campaign = expeditionState.campaign;
                StartExpedition(expedition, campaign); return true;
            }
            Require(command.type != "scenario_start" && command.type != "import_map", "Return to the campaign before entering another standalone map.");
            Require(command.type != "craft" && command.type != "open_loot_box" && command.type != "preview_allocate" && command.type != "preview_skill_node" && command.type != "confirm_skill_node" && command.type != "confirm_development", "Develop your build in the campaign before starting an expedition.");
            return false;
        }
        private void StartExpedition(ExpeditionDef expedition, GameSave campaign)
        {
            // Restore the validated baseline before every attempt; training consumes nothing in the campaign.
            GameSave baseline = CopyExpeditionCampaign(campaign);
            GameView restored = ImportSave(baseline);
            Require(!restored.message.StartsWith("Save rejected:", StringComparison.Ordinal), "Invalid expedition campaign backup.");
            ClearScenario(); ResetCustomMap();
            expeditionState = new ExpeditionSave { id = expedition.id, campaign = baseline };
            expeditionEncounter = BuildExpeditionEncounter(expedition);
            RefreshRosterStats(true); StartEncounter();
            message = expedition.label + ": " + expedition.objective + " Your campaign build is preserved; no campaign rewards are granted.";
        }
        private GameSave CopyExpeditionCampaign(GameSave source)
        {
            Require(source != null && source.expedition == null && source.scenario == null, "Expedition backup cannot contain another standalone mission.");
            GameSession validator = new GameSession(scenarioValidationContent, data);
            GameView view = validator.ImportSave(source);
            Require(!view.message.StartsWith("Save rejected:", StringComparison.Ordinal), "Invalid expedition campaign backup.");
            return validator.ExportSave();
        }
        private ExpeditionSave CaptureExpedition()
        {
            return expeditionState == null ? null : new ExpeditionSave { version = expeditionState.version, id = expeditionState.id, campaign = CopyExpeditionCampaign(expeditionState.campaign) };
        }
        private EncounterDef ValidateExpedition(GameSave save)
        {
            if (save.expedition == null) return null;
            Require(save.scenario == null && save.customMap == null && save.expedition.version == 1, "Invalid expedition save version or combined mission.");
            ExpeditionDef expedition = Array.Find(data.expeditions, e => e.id == save.expedition.id);
            Require(expedition != null && (save.screen == "battle" || save.screen == "victory" || save.screen == "defeat"), "Unknown expedition or invalid expedition screen.");
            GameSave campaign = CopyExpeditionCampaign(save.expedition.campaign);
            Require(save.xp == campaign.xp && save.encounterIndex == campaign.encounterIndex, "Expedition cannot change campaign XP or progression.");
            Require(save.roster != null && save.roster.Length == campaign.roster.Length, "Expedition roster is incomplete.");
            foreach (RosterView member in save.roster)
            {
                RosterView original = member == null ? null : Array.Find(campaign.roster, r => r.id == member.id);
                Require(original != null && member.classId == original.classId && member.selected == original.selected, "Expedition cannot change the campaign party build.");
            }
            Require(save.equipped != null && save.equipped.Length == campaign.equipped.Length, "Expedition equipment differs from its campaign build.");
            foreach (EquipmentSlotSave equipment in save.equipped) Require(equipment != null && Array.Exists(campaign.equipped, e => e.unitId == equipment.unitId && e.equipmentId == equipment.equipmentId), "Expedition equipment differs from its campaign build.");
            Require(save.development != null && campaign.development != null && save.development.allocated != null && save.development.allocated.Length == campaign.development.allocated.Length, "Expedition stat allocations differ from its campaign build.");
            foreach (StatAllocationSave row in save.development.allocated) Require(row != null && Array.Exists(campaign.development.allocated, a => a.unitId == row.unitId && a.statId == row.statId && a.points == row.points), "Expedition stat allocations differ from its campaign build.");
            string[] savedNodes = save.skillTree == null ? new string[0] : save.skillTree.unlockedIds;
            string[] baselineNodes = campaign.skillTree == null ? new string[0] : campaign.skillTree.unlockedIds;
            Require(savedNodes != null && baselineNodes != null && savedNodes.Length == baselineNodes.Length, "Expedition learned skills differ from its campaign build.");
            foreach (string node in savedNodes) Require(Array.IndexOf(baselineNodes, node) >= 0, "Expedition learned skills differ from its campaign build.");
            return BuildExpeditionEncounter(expedition);
        }
        private EncounterDef BuildExpeditionEncounter(ExpeditionDef definition)
        {
            EncounterDef source = definition.encounter;
            return new EncounterDef { id = source.id, label = source.label, description = source.description, width = source.width, height = source.height, xp = 0, exploration = source.exploration ?? data.encounters[0].exploration, playerSpawns = source.playerSpawns, enemies = source.enemies, tiles = source.tiles, layoutVersion = source.layoutVersion, legacyTiles = source.legacyTiles, decorations = source.decorations };
        }
        private void CommitExpedition(GameSave save)
        {
            expeditionEncounter = save.expedition == null ? null : BuildExpeditionEncounter(Array.Find(data.expeditions, e => e.id == save.expedition.id));
            expeditionState = save.expedition == null ? null : new ExpeditionSave { version = save.expedition.version, id = save.expedition.id, campaign = CopyExpeditionCampaign(save.expedition.campaign) };
        }
    }
}
