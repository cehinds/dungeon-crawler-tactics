using UnityEngine;

namespace DungeonCrawlerTactics.Unity
{
    public sealed partial class PlayableGame
    {
        private string campUnitId = "";

        private void DrawCamp()
        {
            GUI.Label(new Rect(28, 108, 1020, 44), "THE GREEN ROOM", titleStyle);
            GUI.Label(new Rect(30, 153, 1150, 32), "Build your cast. Pick your crawlers, then choose a class for each before the next room.", bodyStyle);
            Card(new Rect(28, 208, 648, 594), "YOUR ROSTER  /  " + view.partyCount + " OF " + view.partyCapacity + " DEPLOYED");
            Card(new Rect(696, 208, 716, 442), "CLASS & LOADOUT");
            RosterView selected = null;
            foreach (RosterView unit in view.roster) if (unit.id == campUnitId) selected = unit;
            if (selected == null && view.roster.Length > 0) { selected = view.roster[0]; campUnitId = selected.id; }
            rosterScroll = GUI.BeginScrollView(new Rect(42, 254, 620, 528), rosterScroll, new Rect(0, 0, 595, view.roster.Length * 102));
            for (int i = 0; i < view.roster.Length; i++)
            {
                RosterView unit = view.roster[i];
                Rect row = new Rect(0, i * 102, 591, 94);
                Fill(row, campUnitId == unit.id ? PanelLight : (Color)new Color32(21, 29, 35, 255));
                GUI.DrawTexture(new Rect(10, row.y + 8, 74, 74), UnitArt(unit.classId, "player", unit.id), ScaleMode.ScaleToFit);
                if (Button(new Rect(92, row.y + 8, 314, 46), unit.label, true, campUnitId == unit.id)) campUnitId = unit.id;
                GUI.Label(new Rect(103, row.y + 58, 310, 28), ClassName(unit.classId) + "  /  " + unit.hp + "/" + unit.maxHp + " HP", smallStyle);
                if (Button(new Rect(421, row.y + 23, 156, 46), unit.selected ? "Deployed  ✓" : "Add to party", unit.selected || view.partyCount < view.partyCapacity, unit.selected))
                { campUnitId = unit.id; Submit(new GameCommand { type = "toggle_party", unitId = unit.id }); }
            }
            GUI.EndScrollView();
            if (selected != null)
            {
                GUI.Label(new Rect(716, 254, 670, 34), selected.label + "  /  " + ClassName(selected.classId), sectionStyle);
                GUI.Label(new Rect(716, 292, 670, 28), "Class changes are free at camp. Your role determines your abilities.", smallStyle);
                for (int i = 0; i < view.classes.Length; i++)
                {
                    ClassView role = view.classes[i];
                    float x = 716 + (i % 3) * 222;
                    float y = 334 + (i / 3) * 68;
                    if (y + 58 > 632) break;
                    if (Button(new Rect(x, y, 210, 58), role.label, true, selected.classId == role.id))
                        Submit(new GameCommand { type = "set_class", unitId = selected.id, classId = role.id });
                }
            }
            Card(new Rect(696, 670, 716, 132), "NEXT ON THE SHOW");
            GUI.Label(new Rect(716, 713, 410, 65), "Room " + (view.encounterIndex + 1) + " of " + view.encounterCount + "\n" + view.encounterName, bodyStyle);
            if (Button(new Rect(1142, 714, 248, 62), "Enter dungeon  →", view.partyCount == view.partyCapacity)) Command("start");
        }

        private void DrawOutcome()
        {
            bool win = view.screen == "victory";
            bool complete = view.screen == "complete";
            string title = complete ? "YOU SURVIVED THE FLOOR." : win ? "ROOM CLEARED." : "THE SHOW CLAIMED YOUR PARTY.";
            GUI.Label(new Rect(110, 135, 1220, 72), title, titleStyle);
            GUI.Label(new Rect(112, 209, 1180, 64), complete ? "Three rooms. One impossible cast. The exit is yours." : view.message, bodyStyle);
            Card(new Rect(110, 292, 1220, 408), win ? "SPONSOR REWARD" : "RUN REPORT");
            if (win && view.rewards.Length > 0)
            {
                GUI.Label(new Rect(138, 339, 1160, 40), "Pick a reward to bring back to camp.", bodyStyle);
                for (int i = 0; i < view.rewards.Length; i++)
                {
                    RewardView reward = view.rewards[i];
                    float width = Mathf.Min(365, 1150f / view.rewards.Length - 12);
                    Rect card = new Rect(138 + i * (width + 18), 400, width, 222);
                    Fill(card, PanelLight);
                    GUI.Label(new Rect(card.x + 18, card.y + 18, card.width - 36, 48), reward.label, sectionStyle);
                    GUI.Label(new Rect(card.x + 18, card.y + 72, card.width - 36, 80), reward.description, bodyStyle);
                    if (Button(new Rect(card.x + 18, card.y + 164, card.width - 36, 44), "Choose reward")) Submit(new GameCommand { type = "choose_reward", rewardId = reward.id });
                }
            }
            else
            {
                GUI.Label(new Rect(138, 350, 1140, 80), complete ? "The first-floor run is complete. Build another party and try different classes and terrain combinations." : win ? "Your reward is packed. The next room is waiting." : "Retry this encounter with your party restored, or start a new run from camp.", bodyStyle);
                GUI.Label(new Rect(138, 461, 1140, 60), "Experience earned: " + view.xp + " XP", sectionStyle);
            }
            if (win && view.rewards.Length == 0 && Button(new Rect(110, 738, 350, 60), "Continue  →")) Command("continue");
            if (view.screen == "defeat" && Button(new Rect(110, 738, 350, 60), "Retry encounter")) Command("retry");
            if ((complete || view.screen == "defeat") && Button(new Rect(488, 738, 350, 60), "Start a new run")) modal = "reset";
        }
    }
}
