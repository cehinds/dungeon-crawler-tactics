using System;
using System.Collections.Generic;

namespace DungeonCrawlerTactics
{
    [Serializable] public sealed class GeneratedCampaignPlan
    {
        public int schemaVersion = 1, seed;
        public string id, label;
        public GeneratedFloorPlan[] floors = new GeneratedFloorPlan[0];
    }
    [Serializable] public sealed class GeneratedCampaignState
    {
        public int schemaVersion = 1, floorIndex;
        public GeneratedCampaignPlan plan;
        public GeneratedDungeonState[] archives = new GeneratedDungeonState[0];
    }
    [Serializable] public sealed class GeneratedCampaignView
    {
        public string id, label, nextFloorLabel;
        public int floorIndex, floorNumber, totalFloors, completedFloors;
        public bool canDescend, canConfirmDescent, complete;
    }
    public sealed partial class GameSession
    {
        private GeneratedCampaignState generatedCampaign;
        private bool pendingDescent;

        private static GeneratedCampaignPlan CopyCampaignPlan(GeneratedCampaignPlan plan)
        {
            Require(plan != null && plan.schemaVersion == 1 && !string.IsNullOrEmpty(plan.id) && plan.id.Length <= 100 && !string.IsNullOrEmpty(plan.label) && plan.label.Length <= 200, "Invalid generated campaign identity or version.");
            Require(plan.floors != null && plan.floors.Length >= 2 && plan.floors.Length <= 8, "A generated campaign needs two to eight depths.");
            return new GeneratedCampaignPlan { id = plan.id, label = plan.label, seed = plan.seed, floors = Array.ConvertAll(plan.floors, CopyFloor) };
        }
        private static GeneratedCampaignState CopyCampaign(GeneratedCampaignState state)
        {
            if (state == null) return null;
            Require(state.archives != null && state.archives.Length <= 7, "Invalid campaign archives.");
            GeneratedCampaignPlan plan = CopyCampaignPlan(state.plan);
            GeneratedDungeonState[] archives = Array.ConvertAll(state.archives, CopyGenerated);
            for (int i = 0; i < archives.Length; i++)
            {
                Require(archives[i] != null && i < plan.floors.Length, "Invalid campaign archive.");
                if (archives[i].floorPlan == null) archives[i].floorPlan = CopyFloor(plan.floors[i]);
            }
            return new GeneratedCampaignState { schemaVersion = state.schemaVersion, floorIndex = state.floorIndex, plan = plan, archives = archives };
        }
        private GeneratedCampaignState CaptureCampaign()
        {
            GeneratedCampaignState copy = CopyCampaign(generatedCampaign);
            if (copy != null) foreach (GeneratedDungeonState archive in copy.archives) archive.floorPlan = null;
            return copy;
        }
        private static GeneratedDungeonState FreshCampaignFloor(GeneratedFloorPlan floor)
        {
            Require(floor != null && floor.entrance != null && floor.exit != null, "Campaign depth needs endpoints.");
            return new GeneratedDungeonState { floorPlan = CopyFloor(floor), x = floor.entrance.x, y = floor.entrance.y, entrance = CopyCell(floor.entrance), exit = CopyCell(floor.exit), revealed = new[] { CopyCell(floor.entrance) } };
        }
        private void ValidateCampaignFloor(GeneratedDungeonState state, GeneratedFloorPlan expected, bool archived)
        {
            Require(state != null && state.floorPlan != null && FloorPlansEqual(state.floorPlan, expected), "Campaign depth differs from its realized plan.");
            CustomMapData map = CopyCustomMap(expected.map);
            EncounterDef encounter = BuildCustomEncounter(map, true);
            ValidateFloorSave(new GameSave { customMap = map, generatedDungeon = state, screen = archived ? "complete" : "explore" }, encounter);
        }
        private static bool FloorPlansEqual(GeneratedFloorPlan a, GeneratedFloorPlan b)
        {
            // Compare every authoritative field; optional presentation metadata is carried by the plan.
            if (a == null || b == null || a.schemaVersion != b.schemaVersion || a.seed != b.seed || !FloorMapEqual(a.map, b.map) || a.entrance == null || b.entrance == null || a.exit == null || b.exit == null || a.entrance.x != b.entrance.x || a.entrance.y != b.entrance.y || a.exit.x != b.exit.x || a.exit.y != b.exit.y || a.groups == null || b.groups == null || a.groups.Length != b.groups.Length || a.discoveries == null || b.discoveries == null || a.discoveries.Length != b.discoveries.Length) return false;
            if (a.map.schemaVersion != b.map.schemaVersion || a.map.playerSpawns == null || b.map.playerSpawns == null || a.map.playerSpawns.Length != b.map.playerSpawns.Length || a.map.placements == null || b.map.placements == null || a.map.placements.Length != b.map.placements.Length) return false;
            for (int i = 0; i < a.map.playerSpawns.Length; i++)
            {
                CellView x = a.map.playerSpawns[i], y = b.map.playerSpawns[i];
                if (x == null || y == null || x.x != y.x || x.y != y.y) return false;
            }
            for (int i = 0; i < a.map.placements.Length; i++)
            {
                MapPlacement x = a.map.placements[i], y = b.map.placements[i];
                if (x == null || y == null || x.id != y.id || x.assetId != y.assetId || x.layer != y.layer || x.x != y.x || x.y != y.y || x.rotation != y.rotation || x.blocksMovement != y.blocksMovement) return false;
            }
            for (int i = 0; i < a.groups.Length; i++)
            {
                GeneratedEncounterGroup x = a.groups[i], y = b.groups[i];
                if (x == null || y == null || x.enemyIds == null || y.enemyIds == null || x.id != y.id || x.label != y.label || x.kind != y.kind || x.x != y.x || x.y != y.y || string.Join("|", x.enemyIds) != string.Join("|", y.enemyIds)) return false;
            }
            for (int i = 0; i < a.discoveries.Length; i++)
            {
                ExplorationPointDef x = a.discoveries[i], y = b.discoveries[i];
                if (x == null || y == null || x.id != y.id || x.label != y.label || x.description != y.description || x.kind != y.kind || x.itemId != y.itemId || x.count != y.count || x.x != y.x || x.y != y.y) return false;
            }
            return true;
        }
        private void ValidateCampaignSave(GameSave save)
        {
            if (save.generatedCampaign == null) return;
            GeneratedCampaignState state = CopyCampaign(save.generatedCampaign);
            Require(state.schemaVersion == 1 && state.floorIndex >= 0 && state.floorIndex < state.plan.floors.Length && state.archives.Length == state.floorIndex, "Invalid campaign depth index or archive count.");
            Require(save.generatedDungeon != null && save.generatedDungeon.floorPlan != null && save.customMap != null && save.journey == null && save.scenario == null && save.expedition == null, "Generated campaign cannot combine other run modes.");
            Require(save.screen != "complete" || state.floorIndex == state.plan.floors.Length - 1, "Only the final depth completes the campaign.");
            for (int i = 0; i < state.plan.floors.Length; i++)
            {
                GeneratedFloorPlan floor = state.plan.floors[i];
                ValidateCampaignFloor(FreshCampaignFloor(floor), floor, false);
                if (i < state.floorIndex) ValidateCampaignFloor(state.archives[i], floor, true);
            }
            Require(FloorPlansEqual(save.generatedDungeon.floorPlan, state.plan.floors[state.floorIndex]), "Current depth differs from campaign plan.");
        }
        private static int CampaignWins(GeneratedCampaignState campaign, GeneratedDungeonState current, string atScreen)
        {
            int wins = FloorWins(current, atScreen);
            if (campaign != null) foreach (GeneratedDungeonState archive in campaign.archives) wins += FloorWins(archive, "explore");
            return wins;
        }
        private bool CampaignExitReady()
        {
            return generatedCampaign != null && screen == "explore" && FloorExitReady(generatedDungeon) && Near(generatedDungeon, generatedDungeon.exit.x, generatedDungeon.exit.y) && PartyCount() == data.partySize;
        }
        private GeneratedCampaignView CampaignView()
        {
            if (generatedCampaign == null) return null;
            int index = generatedCampaign.floorIndex;
            return new GeneratedCampaignView { id = generatedCampaign.plan.id, label = generatedCampaign.plan.label, floorIndex = index, floorNumber = index + 1, totalFloors = generatedCampaign.plan.floors.Length, completedFloors = index + (screen == "complete" ? 1 : 0), complete = screen == "complete", canDescend = CampaignExitReady(), canConfirmDescent = pendingDescent && CampaignExitReady(), nextFloorLabel = index + 1 < generatedCampaign.plan.floors.Length ? generatedCampaign.plan.floors[index + 1].map.label : null };
        }
        private void PrepareCampaignCommand(GameCommand command)
        {
            // Any intervening command invalidates the preview, even when it fails. No token survives reload.
            if (command.type != "confirm_descent" && command.type != "preview_descent") pendingDescent = false;
            if (generatedCampaign != null && (command.type == "scenario_start" || command.type == "expedition_start" || command.type == "start_neighborhood"))
                throw new InvalidOperationException("Finish or export this generated campaign before starting an optional run.");
        }
        private bool TryCampaignCommand(GameCommand command)
        {
            if (command.type == "import_campaign")
            {
                GeneratedCampaignPlan plan = CopyCampaignPlan(command.campaignPlan);
                foreach (GeneratedFloorPlan floor in plan.floors) ValidateCampaignFloor(FreshCampaignFloor(floor), floor, false);
                GeneratedDungeonState first = FreshCampaignFloor(plan.floors[0]);
                Reset();
                generatedCampaign = new GeneratedCampaignState { plan = plan };
                EnterCampaignFloor(first);
                message = "Generated expedition started. Its realized depths are saved for this run.";
                return true;
            }
            if (command.type != "preview_descent" && command.type != "confirm_descent" && command.type != "cancel_descent") return false;
            Require(generatedCampaign != null, "Descent requires a generated campaign.");
            if (command.type == "cancel_descent") { pendingDescent = false; message = "Descent canceled. Nothing changed."; return true; }
            Require(CampaignExitReady(), "Clear this depth, recover its objective, and reach the exit with a full party.");
            if (command.type == "preview_descent") { pendingDescent = true; message = "Confirm departure. Party resources and supplies carry forward without healing."; return true; }
            Require(pendingDescent, "Preview descent again; the previous confirmation is missing or stale.");
            pendingDescent = false;
            if (generatedCampaign.floorIndex + 1 == generatedCampaign.plan.floors.Length)
            {
                screen = "complete"; rewardChosen = true; message = "Generated expedition completed."; return true;
            }
            // Construct and validate before changing either the archive or the current floor.
            GeneratedDungeonState next = FreshCampaignFloor(generatedCampaign.plan.floors[generatedCampaign.floorIndex + 1]);
            ValidateCampaignFloor(next, next.floorPlan, false);
            List<GeneratedDungeonState> archives = new List<GeneratedDungeonState>(generatedCampaign.archives);
            archives.Add(CopyGenerated(generatedDungeon));
            generatedCampaign.archives = archives.ToArray();
            generatedCampaign.floorIndex++;
            EnterCampaignFloor(next);
            message = "The party descends. HP, mana, gear, practice and supplies carry forward.";
            return true;
        }
        private void EnterCampaignFloor(GeneratedDungeonState state)
        {
            generatedDungeon = state;
            customMap = CopyCustomMap(state.floorPlan.map);
            customEncounter = BuildCustomEncounter(customMap, true);
            FilterFloorEnemies(customEncounter, state);
            battle = new BattleState(); units.Clear(); timed.Clear();
            encounterIndex = 0; round = 1; rewardChosen = false;
            RevealFloor(); ResumeGenerated();
        }
    }
}
