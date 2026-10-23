using System;

namespace DungeonCrawlerTactics
{
    public sealed partial class GameSession
    {
        // The sampler starts at the authored neighborhood with a fresh party. The player's
        // campaign stays in a separately validated snapshot and receives no sampler rewards.
        private bool TryNeighborhoodStandaloneCommand(GameCommand command)
        {
            bool standalone = neighborhoodState != null && neighborhoodState.campaign != null;
            if (command.type == "start_neighborhood")
            {
                Require(!standalone && screen == "camp" && ActiveExpeditionEncounter == null && ActiveScenarioEncounter == null && CustomEncounter(0) == null,
                    "Start the neighborhood from your campaign safe room.");
                Require(data.neighborhood != null && data.journey != null, "This content pack has no neighborhood.");
                int floorIndex = Array.FindIndex(data.journey.floors, f => f.available && f.encounter != null && f.encounter.exploration.id == data.neighborhood.sectorId);
                Require(floorIndex >= 0 && floorIndex < 8, "The neighborhood requires an available story floor.");
                GameSave campaign = ExportSave();
                Reset();
                journey = new JourneySave { id = data.journey.id, floorIndex = floorIndex };
                encounterIndex = floorIndex;
                // Use the same derived level and economy baseline as a migrated checkpoint
                // at this floor; these sampler resources never enter the preserved campaign.
                for (int i = 0; i < floorIndex; i++)
                    if (data.journey.floors[i].encounter != null) xp += data.journey.floors[i].encounter.xp;
                RefreshRosterStats(true);
                homeState = ValidateHome(new GameSave { journey = CaptureJourney(), encounterIndex = floorIndex, screen = "camp" });
                neighborhoodState.campaign = campaign;
                message = data.neighborhood.label + ": prepare supplies, explore, and face the encounter. Your original campaign is preserved; return at any time.";
                return true;
            }
            if (command.type == "return_neighborhood" || standalone && command.type == "continue")
            {
                Require(standalone, "No neighborhood sampler is active.");
                if (command.type == "continue") Require(screen == "victory", "Finish the neighborhood encounter before continuing.");
                GameSave campaign = neighborhoodState.campaign;
                GameView restored = ImportSave(campaign);
                Require(!restored.message.StartsWith("Save rejected:", StringComparison.Ordinal), "The neighborhood campaign backup could not be restored.");
                message = "Campaign restored exactly. Neighborhood sampler rewards and choices stay in the sampler; play story floor three for permanent progression.";
                return true;
            }
            if (standalone)
                Require(command.type != "start_journey" && command.type != "scenario_start" && command.type != "expedition_start" && command.type != "import_map" && command.type != "new_run",
                    "Return to your preserved campaign before starting another adventure.");
            return false;
        }
    }
}
