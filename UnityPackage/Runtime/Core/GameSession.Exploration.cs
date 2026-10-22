using System;
using System.Collections.Generic;

namespace DungeonCrawlerTactics
{
    public sealed partial class GameSession
    {
        private readonly Dictionary<string, ExplorationSave> exploration = new Dictionary<string, ExplorationSave>(StringComparer.Ordinal);
        private ExplorationDef Sector { get { return Encounter.exploration; } }
        private static string ExploreKey(int x, int y) { return x + "," + y; }
        private static bool ExploreInside(ExplorationDef map, int x, int y) { return x >= 0 && y >= 0 && x < map.width && y < map.height; }
        private static bool ExploreWall(ExplorationDef map, int x, int y) { return Array.Exists(map.walls, c => c.x == x && c.y == y); }
        private static HashSet<string> Revealed(ExplorationSave state) { HashSet<string> result = new HashSet<string>(); foreach (CellView c in state.revealed) result.Add(ExploreKey(c.x, c.y)); return result; }
        private static void Reveal(ExplorationDef map, ExplorationSave state)
        {
            HashSet<string> seen = Revealed(state); List<CellView> cells = new List<CellView>(state.revealed);
            Queue<CellView> pending = new Queue<CellView>(); HashSet<string> visited = new HashSet<string>();
            pending.Enqueue(new CellView { x = state.x, y = state.y, cost = 0 }); visited.Add(ExploreKey(state.x, state.y));
            while (pending.Count > 0)
            {
                CellView c = pending.Dequeue(); if (seen.Add(ExploreKey(c.x, c.y))) cells.Add(new CellView { x = c.x, y = c.y });
                if (c.cost >= map.discoveryRadius || ExploreWall(map, c.x, c.y)) continue;
                int[] dx = { 0, -1, 1, 0 }, dy = { -1, 0, 0, 1 };
                for (int i = 0; i < 4; i++) { int x = c.x + dx[i], y = c.y + dy[i]; if (ExploreInside(map, x, y) && visited.Add(ExploreKey(x, y))) pending.Enqueue(new CellView { x = x, y = y, cost = c.cost + 1 }); }
            }
            state.revealed = cells.ToArray();
        }
        private void StartExploration()
        {
            if (!exploration.ContainsKey(Sector.id))
            {
                ExplorationSave state = new ExplorationSave { sectorId = Sector.id, x = Sector.startX, y = Sector.startY };
                Reveal(Sector, state); exploration.Add(Sector.id, state);
            }
            screen = "explore"; ClearPreview(); message = "Explore the passages, inspect discoveries, and find the encounter door.";
        }
        // Only revealed cells can be transit nodes. A single unrevealed neighbor may be a destination.
        private Dictionary<string, CellView> ExplorePaths(ExplorationDef map, ExplorationSave state)
        {
            HashSet<string> seen = Revealed(state); Dictionary<string, CellView> previous = new Dictionary<string, CellView>();
            Queue<CellView> queue = new Queue<CellView>(); queue.Enqueue(new CellView { x = state.x, y = state.y }); previous.Add(ExploreKey(state.x, state.y), null);
            int[] dx = { 0, -1, 1, 0 }, dy = { -1, 0, 0, 1 };
            while (queue.Count > 0)
            {
                CellView current = queue.Dequeue();
                for (int i = 0; i < 4; i++)
                {
                    int x = current.x + dx[i], y = current.y + dy[i]; string key = ExploreKey(x, y);
                    if (!ExploreInside(map, x, y) || ExploreWall(map, x, y) || previous.ContainsKey(key)) continue;
                    previous.Add(key, current); if (seen.Contains(key)) queue.Enqueue(new CellView { x = x, y = y });
                }
            }
            return previous;
        }
        private void ExploreMove(int x, int y)
        {
            Require(screen == "explore", "Move through the dungeon during exploration.");
            ExplorationSave state = exploration[Sector.id]; Dictionary<string, CellView> paths = ExplorePaths(Sector, state);
            Require(paths.ContainsKey(ExploreKey(x, y)), "Choose a reachable passage or its adjacent frontier.");
            List<CellView> path = new List<CellView>(); CellView step = new CellView { x = x, y = y };
            while (step != null) { path.Add(step); step = paths[ExploreKey(step.x, step.y)]; }
            path.Reverse(); foreach (CellView cell in path) { state.x = cell.x; state.y = cell.y; Reveal(Sector, state); }
            message = "The party advances through the passages.";
        }
        private void ExploreInteract(string id)
        {
            Require(screen == "explore", "Interact during exploration."); ExplorationSave state = exploration[Sector.id];
            ExplorationPointDef point = Array.Find(Sector.points, p => p.id == id);
            Require(point != null && Revealed(state).Contains(ExploreKey(point.x, point.y)), "Discover that location first.");
            Require(Math.Abs(state.x - point.x) + Math.Abs(state.y - point.y) <= 1, "Move beside the discovery first.");
            if (point.kind == "encounter") { StartEncounter(); return; }
            Require(Array.IndexOf(state.claimed, id) < 0, "This discovery has already been claimed.");
            if (point.kind == "cache") { Require(inventory[point.itemId] <= 10000 - point.count, "Shared supplies are full."); inventory[point.itemId] += point.count; }
            List<string> claimed = new List<string>(state.claimed); claimed.Add(id); state.claimed = claimed.ToArray();
            message = point.description; AddLog(point.label + ": " + point.description);
        }
        private ExplorationView ExplorationView()
        {
            ExplorationSave state = exploration[Sector.id]; HashSet<string> seen = Revealed(state); Dictionary<string, CellView> paths = ExplorePaths(Sector, state);
            List<ExplorationTileView> tiles = new List<ExplorationTileView>();
            for (int y = 0; y < Sector.height; y++) for (int x = 0; x < Sector.width; x++)
            {
                bool visible = seen.Contains(ExploreKey(x, y));
                tiles.Add(new ExplorationTileView { x = x, y = y, revealed = visible, blocked = visible && ExploreWall(Sector, x, y), reachable = paths.ContainsKey(ExploreKey(x, y)) });
            }
            List<ExplorationPointView> points = new List<ExplorationPointView>(); foreach (ExplorationPointDef p in Sector.points)
                if (seen.Contains(ExploreKey(p.x, p.y))) { bool claimed = Array.IndexOf(state.claimed, p.id) >= 0; points.Add(new ExplorationPointView { id = p.id, label = p.label, description = p.description, kind = p.kind, x = p.x, y = p.y, claimed = claimed, canInteract = !claimed && Math.Abs(state.x - p.x) + Math.Abs(state.y - p.y) <= 1 }); }
            return new ExplorationView { id = Sector.id, label = Sector.label, description = Sector.description, width = Sector.width, height = Sector.height, x = state.x, y = state.y, tiles = tiles.ToArray(), points = points.ToArray() };
        }
        private ExplorationSave[] ExportExploration()
        {
            List<ExplorationSave> states = new List<ExplorationSave>(); foreach (EncounterDef e in data.encounters)
            { ExplorationSave s; if (!exploration.TryGetValue(e.exploration.id, out s)) continue; List<CellView> cells = new List<CellView>(); foreach (CellView c in s.revealed) cells.Add(new CellView { x = c.x, y = c.y }); states.Add(new ExplorationSave { sectorId = s.sectorId, x = s.x, y = s.y, revealed = cells.ToArray(), claimed = (string[])s.claimed.Clone() }); }
            return states.ToArray();
        }
        private List<ExplorationSave> ValidateExploration(GameSave save)
        {
            List<ExplorationSave> result = new List<ExplorationSave>(); HashSet<string> ids = new HashSet<string>();
            // Older v1 checkpoints omit exploration. Battle checkpoints resume unchanged.
            Require(save.exploration != null && save.exploration.Length <= data.encounters.Length, "Invalid exploration collection.");
            foreach (ExplorationSave s in save.exploration)
            {
                Require(s != null && s.sectorId != null && ids.Add(s.sectorId), "Duplicate or missing sector.");
                int index = Array.FindIndex(data.encounters, e => e.exploration.id == s.sectorId); Require(index >= 0 && index <= save.encounterIndex, "Unknown or future sector."); ExplorationDef map = data.encounters[index].exploration;
                Require(ExploreInside(map, s.x, s.y) && !ExploreWall(map, s.x, s.y) && s.revealed != null && s.claimed != null && s.revealed.Length <= map.width * map.height && s.claimed.Length <= map.points.Length, "Invalid exploration state.");
                HashSet<string> cells = new HashSet<string>(); foreach (CellView c in s.revealed) Require(c != null && ExploreInside(map, c.x, c.y) && cells.Add(ExploreKey(c.x, c.y)), "Invalid revealed tile.");
                Require(cells.Contains(ExploreKey(s.x, s.y)) && cells.Contains(ExploreKey(map.startX, map.startY)), "Exploration position must be discovered.");
                // All visible walkable cells must connect back to the start through visible passages.
                Queue<CellView> queue = new Queue<CellView>(); HashSet<string> connected = new HashSet<string>(); queue.Enqueue(new CellView { x = map.startX, y = map.startY }); connected.Add(ExploreKey(map.startX, map.startY));
                while (queue.Count > 0) { CellView c = queue.Dequeue(); int[] dx = { 0, -1, 1, 0 }, dy = { -1, 0, 0, 1 }; for (int i = 0; i < 4; i++) { int x = c.x + dx[i], y = c.y + dy[i]; string k = ExploreKey(x, y); if (cells.Contains(k) && !ExploreWall(map, x, y) && connected.Add(k)) queue.Enqueue(new CellView { x = x, y = y }); } }
                foreach (CellView c in s.revealed) Require(ExploreWall(map, c.x, c.y) || connected.Contains(ExploreKey(c.x, c.y)), "Disconnected exploration discovery.");
                HashSet<string> claimed = new HashSet<string>(); foreach (string id in s.claimed) { ExplorationPointDef p = Array.Find(map.points, point => point.id == id); Require(p != null && p.kind != "encounter" && claimed.Add(id) && cells.Contains(ExploreKey(p.x, p.y)), "Invalid claimed discovery."); }
                List<CellView> copy = new List<CellView>(); foreach (CellView c in s.revealed) copy.Add(new CellView { x = c.x, y = c.y }); result.Add(new ExplorationSave { sectorId = s.sectorId, x = s.x, y = s.y, revealed = copy.ToArray(), claimed = (string[])s.claimed.Clone() });
            }
            Require(save.screen != "explore" || ids.Contains(data.encounters[save.encounterIndex].exploration.id), "Exploration screen is missing its sector."); return result;
        }
    }
}
