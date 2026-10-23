using System;
using System.Collections.Generic;
namespace DungeonCrawlerTactics
{
    public sealed partial class GameSession
    {
        // Version zero is the published pre-neighborhood sector. Validate it against its
        // authored snapshot before reconnecting remembered discoveries in the expanded map.
        private ExplorationSave MigrateNeighborhoodExploration(ExplorationSave old, GameSave save)
        {
            if (old == null || data.neighborhood == null || old.sectorId != data.neighborhood.sectorId || old.layoutVersion != 0) return old;
            ExplorationDef legacy = data.neighborhood.legacyExploration;
            Require(legacy != null && legacy.id == old.sectorId && old.revealed != null && old.claimed != null, "Missing legacy neighborhood layout.");
            Require(save.neighborhood == null || save.neighborhood.receipts != null && save.neighborhood.receipts.Length == 0, "New neighborhood receipts require the current layout version.");
            Require(ExploreInside(legacy, old.x, old.y) && !ExploreWall(legacy, old.x, old.y) && old.revealed.Length <= legacy.width * legacy.height && old.claimed.Length <= legacy.points.Length, "Invalid legacy neighborhood position.");
            HashSet<string> cells = new HashSet<string>(); foreach (CellView c in old.revealed) Require(c != null && ExploreInside(legacy, c.x, c.y) && cells.Add(ExploreKey(c.x, c.y)), "Invalid legacy neighborhood discovery.");
            Require(cells.Contains(ExploreKey(old.x, old.y)) && cells.Contains(ExploreKey(legacy.startX, legacy.startY)), "Legacy neighborhood position was not discovered.");
            HashSet<string> connected = new HashSet<string>(); Queue<CellView> queue = new Queue<CellView>(); queue.Enqueue(new CellView { x = legacy.startX, y = legacy.startY }); connected.Add(ExploreKey(legacy.startX, legacy.startY));
            int[] dx = { 0, -1, 1, 0 }, dy = { -1, 0, 0, 1 };
            while (queue.Count > 0) { CellView c = queue.Dequeue(); for (int i = 0; i < 4; i++) { int x = c.x + dx[i], y = c.y + dy[i]; string key = ExploreKey(x, y); if (cells.Contains(key) && !ExploreWall(legacy, x, y) && connected.Add(key)) queue.Enqueue(new CellView { x = x, y = y }); } }
            foreach (CellView c in old.revealed) Require(ExploreWall(legacy, c.x, c.y) || connected.Contains(ExploreKey(c.x, c.y)), "Disconnected legacy neighborhood discovery.");
            HashSet<string> claimed = new HashSet<string>(); foreach (string id in old.claimed) { ExplorationPointDef p = Array.Find(legacy.points, point => point.id == id); Require(p != null && p.kind != "encounter" && claimed.Add(id) && cells.Contains(ExploreKey(p.x, p.y)), "Invalid legacy neighborhood claim."); }
            ExplorationDef map = data.journey.floors[NeighborhoodFloorIndex].encounter.exploration;
            ExplorationSave next = new ExplorationSave { sectorId = old.sectorId, layoutVersion = 1, x = ExploreInside(map, old.x, old.y) && !ExploreWall(map, old.x, old.y) ? old.x : map.startX, y = ExploreInside(map, old.x, old.y) && !ExploreWall(map, old.x, old.y) ? old.y : map.startY, claimed = (string[])old.claimed.Clone() };
            // A breadth-first tree supplies deterministic connecting paths, never new rewards.
            var previous = new Dictionary<string, CellView>(); queue.Enqueue(new CellView { x = map.startX, y = map.startY }); previous.Add(ExploreKey(map.startX, map.startY), null);
            while (queue.Count > 0) { CellView c = queue.Dequeue(); for (int i = 0; i < 4; i++) { int x = c.x + dx[i], y = c.y + dy[i]; string key = ExploreKey(x, y); if (ExploreInside(map, x, y) && !ExploreWall(map, x, y) && !previous.ContainsKey(key)) { previous.Add(key, c); queue.Enqueue(new CellView { x = x, y = y }); } } }
            var revealed = new List<CellView>(); cells.Clear();
            Action<int, int> connect = (x, y) => { CellView c = new CellView { x = x, y = y }; while (c != null) { if (cells.Add(ExploreKey(c.x, c.y))) revealed.Add(new CellView { x = c.x, y = c.y }); c = previous[ExploreKey(c.x, c.y)]; } };
            if (!previous.ContainsKey(ExploreKey(next.x, next.y))) { next.x = map.startX; next.y = map.startY; }
            connect(next.x, next.y);
            foreach (CellView c in old.revealed) if (ExploreInside(map, c.x, c.y)) { if (ExploreWall(map, c.x, c.y)) { if (cells.Add(ExploreKey(c.x, c.y))) revealed.Add(new CellView { x = c.x, y = c.y }); } else if (previous.ContainsKey(ExploreKey(c.x, c.y))) connect(c.x, c.y); }
            foreach (string id in next.claimed) { ExplorationPointDef p = Array.Find(map.points, point => point.id == id); Require(p != null, "Legacy neighborhood claim no longer exists."); connect(p.x, p.y); }
            next.revealed = revealed.ToArray(); Reveal(map, next); return next;
        }
    }
}
