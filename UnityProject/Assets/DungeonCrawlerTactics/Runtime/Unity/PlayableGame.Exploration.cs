using UnityEngine;

namespace DungeonCrawlerTactics.Unity
{
    // The shared session owns discovery, pathfinding and rewards; this is only a map presenter.
    public sealed partial class PlayableGame
    {
        private Vector2 explorationScroll;

        private void DrawExploration()
        {
            ExplorationView map = view.exploration;
            if (map == null) return;
            GUI.Label(new Rect(28, 108, 1120, 44), map.label, titleStyle);
            GUI.Label(new Rect(30, 154, 1100, 44), "Explore the corridors. Find supplies, then approach the encounter entrance.", bodyStyle);
            if (Button(new Rect(1182, 120, 230, 50), "Return to camp")) Command("return_camp");

            Rect board = new Rect(28, 218, 920, 594);
            Fill(board, Panel);
            float cell = Mathf.Min((board.width - 24) / map.width, (board.height - 24) / map.height);
            float left = board.x + (board.width - cell * map.width) / 2;
            float top = board.y + (board.height - cell * map.height) / 2;
            foreach (ExplorationTileView tile in map.tiles)
            {
                Rect rect = new Rect(left + tile.x * cell + 2, top + tile.y * cell + 2, cell - 4, cell - 4);
                Color color = !tile.revealed ? Background : tile.blocked ? (Color)new Color32(64, 67, 70, 255) : PanelLight;
                Fill(rect, color);
                if (tile.reachable) Border(rect, Teal, 1);
                if (tile.reachable && Button(rect, ""))
                    Submit(new GameCommand { type = "explore_move", x = tile.x, y = tile.y });
                if (!tile.revealed) continue;
                foreach (ExplorationPointView point in map.points)
                {
                    if (point.x != tile.x || point.y != tile.y) continue;
                    string glyph = point.claimed ? "✓" : point.kind == "encounter" ? "DOOR" : point.kind == "cache" ? "LOOT" : "NOTE";
                    GUI.Label(new Rect(rect.x, rect.y + cell * .22f, rect.width, cell * .55f), glyph, unitLabelStyle);
                    Border(rect, point.claimed ? Muted : Gold, 2);
                }
                if (tile.x == map.x && tile.y == map.y)
                {
                    RosterView leader = null;
                    foreach (RosterView member in view.roster) if (member.selected) { leader = member; break; }
                    if (leader != null) GUI.DrawTexture(rect, UnitArt(leader.classId, "player", leader.id), ScaleMode.ScaleToFit);
                    Border(rect, Teal, 3);
                }
            }

            Card(new Rect(968, 218, 444, 594), "DISCOVERIES");
            GUI.Label(new Rect(990, 270, 400, 66), map.description, bodyStyle);
            GUI.Label(new Rect(990, 342, 400, 54), "Click a reachable tile or use arrow keys. Move next to a discovery to interact.", smallStyle);
            explorationScroll = GUI.BeginScrollView(new Rect(986, 414, 408, 374), explorationScroll,
                new Rect(0, 0, 384, Mathf.Max(364, map.points.Length * 142)));
            for (int i = 0; i < map.points.Length; i++)
            {
                ExplorationPointView point = map.points[i];
                float y = i * 142;
                GUI.Label(new Rect(4, y, 376, 28), point.label, sectionStyle);
                GUI.Label(new Rect(4, y + 32, 376, 48), point.description, smallStyle);
                string action = point.claimed ? "Discovered" : point.kind == "encounter" ? "Enter encounter" : point.kind == "cache" ? "Open supply cache" : "Read discovery";
                if (Button(new Rect(4, y + 87, 376, 42), point.canInteract ? action : point.claimed ? action : "Move closer", point.canInteract && !point.claimed))
                    Submit(new GameCommand { type = "explore_interact", targetId = point.id });
            }
            GUI.EndScrollView();
        }
    }
}
