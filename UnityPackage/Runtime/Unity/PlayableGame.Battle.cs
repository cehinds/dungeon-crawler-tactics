using UnityEngine;

namespace DungeonCrawlerTactics.Unity
{
    public sealed partial class PlayableGame
    {
        private void DrawBattle()
        {
            GUI.Label(new Rect(28, 105, 1050, 40), view.encounterName, titleStyle);
            GUI.Label(new Rect(1080, 111, 330, 32), "ROUND " + view.round + "  /  " + (view.phase == "player" ? "YOUR TURN" : "ENEMY TURN"), sectionStyle);
            DrawParty();
            DrawBoard();
            DrawActions();
            DrawInspector();
            DrawLog();
        }

        private void DrawParty()
        {
            Card(new Rect(28, 165, 232, 664), "YOUR CRAWLERS");
            int index = 0;
            foreach (UnitView unit in view.units)
            {
                if (unit.team != "player") continue;
                float y = 218 + index * 128;
                Rect rect = new Rect(40, y, 208, 118);
                Fill(rect, unit.selected ? PanelLight : (Color)new Color32(19, 28, 33, 255));
                if (unit.selected) Border(rect, Teal);
                GUI.DrawTexture(new Rect(44, y + 8, 60, 65), UnitArt(unit.classId, unit.team, unit.id), ScaleMode.ScaleToFit);
                GUI.Label(new Rect(109, y + 10, 134, 26), unit.label, bodyStyle);
                GUI.Label(new Rect(109, y + 39, 134, 26), unit.hp + "/" + unit.maxHp + " HP", smallStyle);
                GUI.Label(new Rect(49, y + 77, 190, 26), unit.hp <= 0 ? "DOWNED" : (unit.moved ? "Move used" : "Move ready") + "  /  " + (unit.acted ? "Act used" : "Act ready"), smallStyle);
                bool enabled = GUI.enabled;
                GUI.enabled = enabled && string.IsNullOrEmpty(modal) && unit.hp > 0 && view.phase == "player";
                bool select = GUI.Button(new Rect(40, y, 208, 118), GUIContent.none, GUIStyle.none);
                GUI.enabled = enabled;
                if (select)
                    Submit(new GameCommand { type = "select", unitId = unit.id });
                index++;
            }
            if (Button(new Rect(43, 749, 202, 58), "End team turn", view.phase == "player" && !view.canConfirm)) Command("end_turn");
        }

        private void DrawBoard()
        {
            const float startX = 282, startY = 187;
            float cell = Mathf.Min(66, Mathf.Min(660f / Mathf.Max(1, view.width), 528f / Mathf.Max(1, view.height)));
            string hint = !string.IsNullOrEmpty(actionId) || !string.IsNullOrEmpty(itemId) ? "TARGET MODE  /  click a unit or tile" : "SELECT A CRAWLER  /  highlighted tiles are reachable";
            GUI.Label(new Rect(282, 151, 658, 30), hint, smallStyle);
            Fill(new Rect(startX - 6, startY - 6, cell * view.width + 12, cell * view.height + 12), new Color32(8, 12, 15, 255));
            foreach (TileView tile in view.tiles)
            {
                Rect rect = new Rect(startX + tile.x * cell, startY + tile.y * cell, cell - 2, cell - 2);
                GUI.DrawTexture(rect, TileArt(tile), ScaleMode.StretchToFill);
                if (view.canMove && string.IsNullOrEmpty(actionId) && string.IsNullOrEmpty(itemId) && Reachable(tile.x, tile.y))
                {
                    Fill(rect, new Color(0.21f, 0.8f, 0.72f, highContrast ? 0.36f : 0.16f));
                    Border(rect, highContrast ? Color.white : new Color(0.35f, 0.76f, 0.7f, 0.55f), 1);
                    Fill(new Rect(rect.center.x - 2, rect.center.y - 2, 4, 4), Teal);
                }
                string symbol = SurfaceSymbol(tile.tags);
                if (!string.IsNullOrEmpty(symbol)) GUI.Label(new Rect(rect.x + 4, rect.y + 3, rect.width - 8, 22), symbol, unitLabelStyle);
                if (showCoordinates) GUI.Label(new Rect(rect.x + 3, rect.yMax - 18, rect.width - 6, 18), tile.x + "," + tile.y, unitLabelStyle);
                if (inspectedId == tile.id) Border(rect, Gold, 3);
            }
            foreach (UnitView unit in view.units)
            {
                Rect rect = new Rect(startX + unit.x * cell, startY + unit.y * cell, cell - 2, cell - 2);
                if (unit.hp <= 0)
                {
                    GUI.Label(new Rect(rect.x + 6, rect.y + 20, rect.width - 12, 22), "DOWN", unitLabelStyle);
                    continue;
                }
                Fill(new Rect(rect.x + 9, rect.y + cell - 15, cell - 20, 7), new Color(0, 0, 0, 0.45f));
                GUI.DrawTexture(new Rect(rect.x - 3, rect.y - 9, cell + 4, cell + 4), UnitArt(unit.classId, unit.team, unit.id), ScaleMode.ScaleToFit);
                Color team = unit.team == "player" ? Teal : (Color)new Color32(248, 119, 111, 255);
                Fill(new Rect(rect.x + 5, rect.yMax - 10, rect.width - 10, 6), new Color32(15, 19, 23, 255));
                Fill(new Rect(rect.x + 5, rect.yMax - 10, (rect.width - 10) * unit.hp / Mathf.Max(1f, unit.maxHp), 6), team);
                if (unit.selected) Border(rect, reduceMotion ? Teal : Color.Lerp(Teal, Color.white, (Mathf.Sin(Time.realtimeSinceStartup * 3) + 1) * .25f), 3);
                else if (inspectedId == unit.id) Border(rect, Gold, 3);
                GUI.Label(new Rect(rect.x - 5, rect.y - 1, rect.width + 10, 18), unit.label, unitLabelStyle);
            }
            // One hit target per cell keeps occupied tiles targetable by tile abilities.
            foreach (TileView tile in view.tiles)
            {
                Rect rect = new Rect(startX + tile.x * cell, startY + tile.y * cell, cell - 2, cell - 2);
                GUI.enabled = string.IsNullOrEmpty(modal);
                if (GUI.Button(rect, GUIContent.none, GUIStyle.none)) ClickCell(tile);
                GUI.enabled = true;
            }
            GUI.Label(new Rect(283, 724, 655, 25), "OIL  ·  WATER  ·  FIRE  /  labels identify terrain conditions", smallStyle);
        }

        private void ClickCell(TileView tile)
        {
            UnitView occupant = null;
            foreach (UnitView unit in view.units) if (unit.x == tile.x && unit.y == tile.y && unit.hp > 0) { occupant = unit; break; }
            inspectedId = occupant != null ? occupant.id : tile.id;
            if (!string.IsNullOrEmpty(actionId) || !string.IsNullOrEmpty(itemId))
            {
                string targetKind = "";
                foreach (AbilityView ability in view.abilities) if (ability.id == actionId) targetKind = ability.target;
                foreach (ItemView item in view.items) if (item.id == itemId) targetKind = item.target;
                string target = targetKind == "tile" || occupant == null ? tile.id : occupant.id;
                if (targetKind == "self") target = view.selectedUnitId;
                Submit(new GameCommand { type = "preview", abilityId = actionId, itemId = itemId, targetId = target }, false);
                return;
            }
            if (occupant != null && occupant.team == "player") Submit(new GameCommand { type = "select", unitId = occupant.id });
            if (occupant == null && view.canMove && Reachable(tile.x, tile.y)) Submit(new GameCommand { type = "move", x = tile.x, y = tile.y });
            notice = occupant == null ? "Tile " + tile.x + "," + tile.y + ": " + (tile.blocked ? "Blocked" : Tags(tile.tags)) : occupant.label + ": " + Tags(occupant.tags);
        }

        private bool Reachable(int x, int y)
        {
            foreach (CellView cell in view.reachable) if (cell.x == x && cell.y == y) return true;
            return false;
        }

        private void DrawActions()
        {
            UnitView selected = null;
            foreach (UnitView unit in view.units) if (unit.id == view.selectedUnitId) selected = unit;
            Card(new Rect(962, 165, 450, 346), selected == null ? "SELECT A CRAWLER" : selected.label.ToUpperInvariant() + "  /  " + selected.energy + " ENERGY");
            if (selected == null) { GUI.Label(new Rect(980, 222, 410, 80), "Click a living crawler on the board or in your party to begin.", bodyStyle); return; }
            GUI.Label(new Rect(980, 207, 410, 27), ClassName(selected.classId) + "  ·  " + selected.hp + "/" + selected.maxHp + " HP", smallStyle);
            if (Button(new Rect(980, 241, 202, 44), "Move [M]", view.canMove && !view.canConfirm, string.IsNullOrEmpty(actionId) && string.IsNullOrEmpty(itemId))) { actionId = ""; itemId = ""; notice = "Click a highlighted cell to move."; }
            if (Button(new Rect(1192, 241, 202, 44), "Wait [W]", view.canAct && !view.canConfirm)) Command("wait");
            int count = view.abilities.Length + view.items.Length;
            actionScroll = GUI.BeginScrollView(new Rect(977, 298, 421, 196), actionScroll, new Rect(0, 0, 395, count * 54));
            int row = 0;
            foreach (AbilityView ability in view.abilities)
            {
                string label = ability.label + "   /   " + ability.cost + " E   /   R" + ability.range;
                if (Button(new Rect(0, row++ * 54, 392, 48), label, ability.enabled && view.canAct && !view.canConfirm, actionId == ability.id))
                {
                    actionId = ability.id; itemId = "";
                    notice = ability.description + " Select a " + ability.target + " target.";
                    if (ability.target == "self") Submit(new GameCommand { type = "preview", abilityId = ability.id, targetId = view.selectedUnitId }, false);
                }
            }
            foreach (ItemView item in view.items)
            {
                if (Button(new Rect(0, row++ * 54, 392, 48), item.label + "  ×" + item.count + "   /   R" + item.range, item.count > 0 && view.canAct && !view.canConfirm, itemId == item.id))
                {
                    itemId = item.id; actionId = ""; notice = "Select a " + item.target + " target for " + item.label + ".";
                    if (item.target == "self") Submit(new GameCommand { type = "preview", itemId = item.id, targetId = view.selectedUnitId }, false);
                }
            }
            GUI.EndScrollView();
        }

        private void DrawInspector()
        {
            Card(new Rect(962, 528, 450, 301), view.canConfirm ? "ACTION FORECAST" : "INSPECT & PLAN");
            if (view.canConfirm)
            {
                forecastScroll = GUI.BeginScrollView(new Rect(977, 573, 421, 173), forecastScroll,
                    new Rect(0, 0, 395, Mathf.Max(160, view.forecast.Length * 112)));
                float y = 0;
                foreach (ForecastView change in view.forecast)
                {
                    string values = change.label;
                    if (change.beforeHp != change.afterHp) values += "  HP " + change.beforeHp + " → " + change.afterHp;
                    if (change.beforeEnergy != change.afterEnergy) values += "  E " + change.beforeEnergy + " → " + change.afterEnergy;
                    GUI.Label(new Rect(2, y, 389, 42), values, bodyStyle);
                    GUI.Label(new Rect(2, y + 43, 389, 62), Tags(change.beforeTags) + " → " + Tags(change.afterTags), smallStyle);
                    y += 112;
                }
                if (view.forecast.Length == 0) GUI.Label(new Rect(2, 0, 389, 100), "No HP, energy, or condition changes. You can cancel and choose another target.", bodyStyle);
                GUI.EndScrollView();
                GUI.SetNextControlName("ConfirmAction");
                if (Button(new Rect(980, 762, 202, 48), "Confirm action", true)) Command("confirm");
                if (Button(new Rect(1192, 762, 202, 48), "Cancel [Esc]")) Command("cancel");
                return;
            }
            string title = "Read the room before you act.";
            string detail = "Move first: acting ends the crawler’s activation. Select an ability, then click a target to preview its exact result.";
            foreach (UnitView unit in view.units)
                if (unit.id == inspectedId) { title = unit.label + "  /  " + unit.hp + "/" + unit.maxHp + " HP"; detail = ClassName(unit.classId) + "\n" + Tags(unit.tags) + "\nEnergy: " + unit.energy + "/" + unit.maxEnergy; }
            foreach (TileView tile in view.tiles)
                if (tile.id == inspectedId) { title = "Tile " + tile.x + ", " + tile.y; detail = (tile.blocked ? "Blocked terrain" : "Traversable floor") + "\n" + Tags(tile.tags); }
            GUI.Label(new Rect(980, 577, 410, 48), title, bodyStyle);
            GUI.Label(new Rect(980, 630, 410, 130), detail, bodyStyle);
            if ((!string.IsNullOrEmpty(actionId) || !string.IsNullOrEmpty(itemId)) && Button(new Rect(980, 762, 414, 48), "Cancel targeting [Esc]")) Command("cancel");
        }

        private void DrawLog()
        {
            Card(new Rect(282, 760, 660, 69), "");
            int count = view.log.Length;
            logScroll = GUI.BeginScrollView(new Rect(294, 767, 636, 55), logScroll, new Rect(0, 0, 606, Mathf.Max(50, count * 24)));
            for (int i = 0; i < count; i++) GUI.Label(new Rect(2, i * 24, 600, 23), view.log[count - i - 1], smallStyle);
            GUI.EndScrollView();
        }
    }
}
