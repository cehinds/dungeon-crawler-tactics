using UnityEngine;
namespace DungeonCrawlerTactics.Unity
{
    public sealed partial class PlayableGame
    {
        private bool neighborhoodOpen;
        private Vector2 neighborhoodScroll;
        private string neighborhoodCrawler;
        private void DrawNeighborhood()
        {
            if (view.neighborhood == null) return;
            if (Button(new Rect(1030, 820, 380, 36), "Neighborhood choices & history")) neighborhoodOpen = !neighborhoodOpen;
            if (!neighborhoodOpen) return;
            GUI.Box(new Rect(180, 110, 1080, 690), "");
            GUI.Label(new Rect(210, 125, 940, 30), view.neighborhood.label, sectionStyle);
            if (Button(new Rect(1150, 120, 80, 36), "Close")) { neighborhoodOpen = false; return; }
            float y = 0;
            neighborhoodScroll = GUI.BeginScrollView(new Rect(205, 170, 1030, 600), neighborhoodScroll, new Rect(0, 0, 990, 2800));
            if (view.neighborhood.standalone) { if (Button(new Rect(0, y, 470, 36), "Return to preserved campaign")) { Command("return_neighborhood"); neighborhoodOpen = false; } y += 42; }
            else if (view.screen == "camp") { if (Button(new Rect(0, y, 470, 36), "Try isolated neighborhood")) Command("start_neighborhood"); y += 42; }
            foreach (RosterView member in view.roster) if (member.selected) { if (string.IsNullOrEmpty(neighborhoodCrawler)) neighborhoodCrawler = member.id; if (Button(new Rect(0, y, 470, 32), (neighborhoodCrawler == member.id ? "Selected: " : "Choose: ") + member.label)) neighborhoodCrawler = member.id; y += 36; }
            foreach (NeighborhoodInteractionView interaction in view.neighborhood.interactions)
            {
                GUI.Label(new Rect(0, y, 970, 30), interaction.label + (interaction.completed ? " — completed" : ""), sectionStyle); y += 34;
                foreach (NeighborhoodOptionView option in interaction.options)
                {
                    GUI.Label(new Rect(0, y, 960, 42), option.description + (option.enabled ? "" : " " + option.disabledReason), smallStyle); y += 44;
                    if (Button(new Rect(0, y, 940, 34), "Preview " + option.label, option.enabled)) Submit(new GameCommand { type = "preview_neighborhood", targetId = interaction.id, nodeId = option.id, unitId = System.Array.IndexOf(option.eligibleUnitIds, neighborhoodCrawler) >= 0 ? neighborhoodCrawler : option.eligibleUnitIds.Length > 0 ? option.eligibleUnitIds[0] : neighborhoodCrawler }); y += 38;
                }
            }
            if (view.neighborhood.canConfirm)
            {
                GUI.Label(new Rect(0, y, 950, 44), "Forecast: " + view.neighborhood.forecast.description, smallStyle); y += 48;
                foreach (InventoryEntry item in view.neighborhood.forecast.afterItems) { InventoryEntry before = System.Array.Find(view.neighborhood.forecast.beforeItems, row => row.itemId == item.itemId); GUI.Label(new Rect(0, y, 950, 28), item.itemId + ": " + before.count + " → " + item.count, smallStyle); y += 30; }
                if (Button(new Rect(0, y, 450, 38), "Confirm approach")) Command("confirm_neighborhood");
                if (Button(new Rect(470, y, 450, 38), "Cancel")) Command("cancel_neighborhood"); y += 44;
            }
            foreach (NeighborhoodChallengeView challenge in view.neighborhood.challenges) { GUI.Label(new Rect(0, y, 970, 44), (challenge.earned ? "Earned: " : "Challenge: ") + challenge.label + " — " + challenge.description, smallStyle); y += 48; }
            foreach (string clue in view.neighborhood.clues) { GUI.Label(new Rect(0, y, 970, 54), "Clue: " + clue, smallStyle); y += 58; }
            GUI.EndScrollView();
        }
    }
}
