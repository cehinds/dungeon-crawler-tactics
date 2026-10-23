using System;
using System.Collections.Generic;
namespace DungeonCrawlerTactics
{
    public static class NeighborhoodDefinitionValidator
    {
        private static void Need(bool condition, string message) { if (!condition) throw new ArgumentException(message); }
        public static void Validate(GameData data, Catalog catalog)
        {
            NeighborhoodDef n = data.neighborhood; if (n == null) return;
            Need(!string.IsNullOrEmpty(n.id) && !string.IsNullOrEmpty(n.label) && n.description != null && n.interactions != null && n.interactions.Length > 0 && n.interactions.Length <= 16 && n.challenges != null && n.challenges.Length <= 16, "Invalid neighborhood definition.");
            int floorIndex = data.journey == null || data.journey.floors == null ? -1 : Array.FindIndex(data.journey.floors, f => f != null && f.available && f.encounter != null && f.encounter.exploration != null && f.encounter.exploration.id == n.sectorId);
            Need(floorIndex >= 0, "Neighborhood must reference an available story exploration sector.");
            ValidateLegacy(n.legacyExploration, n.sectorId, catalog);
            ExplorationDef map = data.journey.floors[floorIndex].encounter.exploration; HashSet<string> ids = new HashSet<string>(), points = new HashSet<string>();
            foreach (NeighborhoodInteractionDef i in n.interactions)
            {
                Need(i != null && !string.IsNullOrEmpty(i.id) && ids.Add(i.id) && !string.IsNullOrEmpty(i.label) && i.description != null && i.options != null && i.options.Length > 0 && i.options.Length <= 8, "Invalid neighborhood interaction.");
                Need(i.camp ? string.IsNullOrEmpty(i.pointId) : points.Add(i.pointId ?? "") && Array.Exists(map.points, p => p.id == i.pointId && p.kind == "lore"), "Neighborhood discovery must be a unique lore point.");
                HashSet<string> options = new HashSet<string>(); bool fallback = false;
                foreach (NeighborhoodOptionDef o in i.options)
                {
                    Need(o != null && !string.IsNullOrEmpty(o.id) && options.Add(o.id) && !string.IsNullOrEmpty(o.label) && o.description != null && o.minimumRank >= 1 && o.minimumRank <= 20, "Invalid neighborhood approach.");
                    Quantity(o.costItemId, o.costCount, catalog); Quantity(o.rewardItemId, o.rewardCount, catalog);
                    Need(string.IsNullOrEmpty(o.abilityId) || catalog.Abilities.ContainsKey(o.abilityId), "Unknown neighborhood skill.");
                    Need(o.clue == null || o.clue.Length <= 1000, "Neighborhood clue is too long.");
                    if (string.IsNullOrEmpty(o.abilityId) && o.costCount == 0) fallback = true;
                }
                Need(fallback, "Every neighborhood interaction needs a free unskilled fallback.");
            }
            ids.Clear(); foreach (NeighborhoodChallengeDef c in n.challenges)
            {
                NeighborhoodInteractionDef i = c == null ? null : Array.Find(n.interactions, x => x.id == c.interactionId);
                Need(c != null && !string.IsNullOrEmpty(c.id) && ids.Add(c.id) && !string.IsNullOrEmpty(c.label) && c.description != null && i != null && (string.IsNullOrEmpty(c.optionId) || Array.Exists(i.options, o => o.id == c.optionId)), "Invalid neighborhood challenge."); Quantity(c.rewardItemId, c.rewardCount, catalog); Need(c.rewardCount > 0, "Neighborhood challenges require a concrete reward.");
            }
        }
        private static void ValidateLegacy(ExplorationDef map, string sectorId, Catalog catalog)
        {
            if (map == null) return;
            Need(map.id == sectorId && map.width >= 4 && map.height >= 4 && map.width <= 30 && map.height <= 30 && map.discoveryRadius >= 1 && map.discoveryRadius <= 3 && map.walls != null && map.points != null && map.points.Length <= 100, "Invalid legacy neighborhood layout.");
            Func<int, int, string> key = (x, y) => x + "," + y; Func<int, int, bool> inside = (x, y) => x >= 0 && y >= 0 && x < map.width && y < map.height;
            var walls = new HashSet<string>(); foreach (CellView wall in map.walls) Need(wall != null && inside(wall.x, wall.y) && walls.Add(key(wall.x, wall.y)), "Invalid legacy neighborhood wall.");
            Need(inside(map.startX, map.startY) && !walls.Contains(key(map.startX, map.startY)), "Invalid legacy neighborhood start.");
            var connected = new HashSet<string>(); var queue = new Queue<CellView>(); queue.Enqueue(new CellView { x = map.startX, y = map.startY }); connected.Add(key(map.startX, map.startY)); int[] dx = { 0, -1, 1, 0 }, dy = { -1, 0, 0, 1 };
            while (queue.Count > 0) { CellView c = queue.Dequeue(); for (int i = 0; i < 4; i++) { int x = c.x + dx[i], y = c.y + dy[i]; if (inside(x, y) && !walls.Contains(key(x, y)) && connected.Add(key(x, y))) queue.Enqueue(new CellView { x = x, y = y }); } }
            var ids = new HashSet<string>(); var cells = new HashSet<string>(); int doors = 0;
            foreach (ExplorationPointDef point in map.points)
            {
                Need(point != null && !string.IsNullOrEmpty(point.id) && ids.Add(point.id) && cells.Add(key(point.x, point.y)) && connected.Contains(key(point.x, point.y)) && (point.kind == "encounter" || point.kind == "cache" || point.kind == "lore"), "Invalid legacy neighborhood point.");
                if (point.kind == "encounter") doors++;
                Quantity(point.itemId, point.count, catalog); Need(point.kind == "cache" ? point.count > 0 : point.count == 0, "Invalid legacy neighborhood supplies.");
            }
            Need(doors == 1, "Legacy neighborhood requires one encounter door.");
        }
        private static void Quantity(string id, int count, Catalog catalog) { Need(count >= 0 && count <= 100 && (count == 0 ? string.IsNullOrEmpty(id) : id != null && catalog.Items.ContainsKey(id)), "Invalid neighborhood item quantity."); }
    }
}
