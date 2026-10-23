using System;
using System.Collections.Generic;
namespace DungeonCrawlerTactics
{
    public sealed partial class GameSession
    {
        private CustomMapData customMap;
        private EncounterDef customEncounter;
        private void ResetCustomMap()
        {
            customMap = null;
            customEncounter = null;
        }
        private EncounterDef CustomEncounter(int index)
        {
            return customEncounter;
        }
        private CustomMapData ExportCustomMap()
        {
            return customMap == null ? null : CopyCustomMap(customMap);
        }
        private void PopulateCustomMap(GameView view)
        {
            view.customMap = ExportCustomMap();
        }
        private EncounterDef ValidateCustomMap(GameSave save)
        {
            if (save.customMap == null)
                return null;
            Require(save.scenario == null, "A save cannot combine a boss scenario and a workshop map.");
            Require(save.encounterIndex == 0 || save.screen == "complete", "Custom encounter index is invalid.");
            return BuildCustomEncounter(CopyCustomMap(save.customMap));
        }
        private void CommitCustomMap(GameSave save)
        {
            customMap = save.customMap == null ? null : CopyCustomMap(save.customMap);
            customEncounter = customMap == null ? null : BuildCustomEncounter(customMap);
        }
        private void ImportCustomMap(GameCommand command)
        {
            Require(command.customMap != null, "Choose a workshop map JSON file.");
            CustomMapData candidate = CopyCustomMap(command.customMap);
            EncounterDef encounter = BuildCustomEncounter(candidate); // All validation precedes state changes.
            Reset();
            customMap = candidate;
            customEncounter = encounter;
            StartEncounter();
            message = "Workshop map loaded. Defeat its enemies to complete this custom encounter.";
        }
        private static CustomMapData CopyCustomMap(CustomMapData map)
        {
            Require(map != null && map.tiles != null && map.playerSpawns != null && map.enemies != null && map.placements != null, "Custom map arrays cannot be null.");
            CustomMapData copy = new CustomMapData { schemaVersion = map.schemaVersion, width = map.width, height = map.height, label = map.label };
            copy.tiles = Array.ConvertAll(map.tiles, t => t == null ? null : new TileDef { x = t.x, y = t.y, blocked = t.blocked, tags = t.tags == null ? null : (string[])t.tags.Clone() });
            copy.playerSpawns = Array.ConvertAll(map.playerSpawns, p => p == null ? null : new CellView { x = p.x, y = p.y });
            copy.enemies = Array.ConvertAll(map.enemies, e => e == null ? null : new SpawnDef { id = e.id, label = e.label, classId = e.classId, artId = e.artId, x = e.x, y = e.y, hp = e.hp, energy = e.energy, move = e.move, tags = e.tags == null ? null : (string[])e.tags.Clone() });
            copy.placements = Array.ConvertAll(map.placements, p => p == null ? null : new MapPlacement { id = p.id, assetId = p.assetId, layer = p.layer, x = p.x, y = p.y, rotation = p.rotation, blocksMovement = p.blocksMovement });
            return copy;
        }
        private EncounterDef BuildCustomEncounter(CustomMapData map)
        {
            Require(map.schemaVersion == 1 && map.width >= 6 && map.width <= 20 && map.height >= 6 && map.height <= 16, "Workshop maps must be 6–20 cells wide and 6–16 cells high.");
            Require(map.label != null && map.label.Length <= 100 && map.tiles.Length <= map.width * map.height && map.placements.Length <= map.width * map.height * 5, "Custom map exceeds collection limits.");
            HashSet<string> coordinates = new HashSet<string>(), walls = new HashSet<string>();
            foreach (TileDef tile in map.tiles)
            {
                Require(tile != null && InCustomBounds(map, tile.x, tile.y) && coordinates.Add(TileId(tile.x, tile.y)), "Duplicate or invalid custom tile.");
                ValidateTags(tile.tags);
                foreach (string tag in tile.tags)
                    Require(tag == "surface.water" || tag == "surface.oil" || tag == "surface.burning", "Unsupported workshop terrain tag.");
                if (tile.blocked)
                    walls.Add(TileId(tile.x, tile.y));
            }
            string[] assetIds = { "wall-ne", "wall-nw", "wall-corner", "pillar", "door-closed-nw", "door-open-nw", "door-closed-ne", "door-open-ne", "torch", "lever", "grate", "oil-overlay", "water-overlay", "moss", "rubble", "stairs", "stone-a", "stone-b", "water-floor", "oil-floor", "crate", "barrel", "chest", "exit", "fire-overlay" };
            string[] layers = { "structure", "structure", "structure", "prop", "structure", "structure", "structure", "structure", "prop", "prop", "surface", "surface", "surface", "overlay", "prop", "prop", "floor", "floor", "floor", "floor", "prop", "prop", "prop", "structure", "overlay" };
            HashSet<string> placementIds = new HashSet<string>(), slots = new HashSet<string>();
            foreach (MapPlacement placement in map.placements)
            {
                int asset = placement == null ? -1 : Array.IndexOf(assetIds, placement.assetId);
                Require(asset >= 0 && placement.id != null && placement.id.Length <= 100 && placementIds.Add(placement.id) && InCustomBounds(map, placement.x, placement.y) && placement.rotation >= 0 && placement.rotation < 4 && placement.layer == layers[asset] && slots.Add(TileId(placement.x, placement.y) + ":" + placement.layer), "Invalid custom component, layer, duplicate slot or rotation.");
                bool blocks = asset == 0 || asset == 1 || asset == 2 || asset == 3 || asset == 4 || asset == 6 || asset == 14 || asset == 20 || asset == 21 || asset == 22 || asset == 23;
                Require(placement.blocksMovement == blocks && (!blocks || walls.Contains(TileId(placement.x, placement.y))), "Component blocking disagrees with map tiles.");
                string requiredTag = placement.assetId == "water-floor" || placement.assetId == "water-overlay" ? "surface.water" : placement.assetId == "oil-floor" || placement.assetId == "oil-overlay" ? "surface.oil" : placement.assetId == "fire-overlay" ? "surface.burning" : null;
                TileDef logical = Array.Find(map.tiles, tile => tile.x == placement.x && tile.y == placement.y);
                Require(requiredTag == null || logical != null && Array.IndexOf(logical.tags, requiredTag) >= 0, "Component terrain disagrees with map tiles.");
            }
            List<CellView> free = new List<CellView>();
            for (int y = 0; y < map.height; y++)
                for (int x = 0; x < map.width; x++)
                    if (!walls.Contains(TileId(x, y)))
                        free.Add(new CellView { x = x, y = y });
            Require(free.Count >= data.partySize + 3, "Workshop map needs room for the party and three enemies.");
            // Choose the lowest-left free cells for the party and highest-right cells for enemies.
            if (map.playerSpawns.Length == 0)
                map.playerSpawns = free.GetRange(0, data.partySize).ToArray();
            Require(map.playerSpawns.Length == data.partySize, "Custom map must have exactly four player spawns.");
            HashSet<string> occupied = new HashSet<string>();
            foreach (CellView spawn in map.playerSpawns)
                Require(spawn != null && InCustomBounds(map, spawn.x, spawn.y) && !walls.Contains(TileId(spawn.x, spawn.y)) && occupied.Add(TileId(spawn.x, spawn.y)), "Invalid, blocked or duplicate player spawn.");
            if (map.enemies.Length == 0)
            {
                List<SpawnDef> generated = new List<SpawnDef>();
                for (int i = free.Count - 1; i >= 0 && generated.Count < 3; i--)
                {
                    CellView cell = free[i];
                    if (occupied.Contains(TileId(cell.x, cell.y)))
                        continue;
                    SpawnDef source = data.encounters[0].enemies[generated.Count % data.encounters[0].enemies.Length];
                    generated.Add(new SpawnDef { id = "custom.enemy.add" + generated.Count, label = source.label, classId = source.classId, artId = source.artId, x = cell.x, y = cell.y, hp = source.hp, energy = source.energy, move = source.move, tags = (string[])source.tags.Clone() });
                }
                map.enemies = generated.ToArray();
            }
            Require(map.enemies.Length > 0 && map.enemies.Length <= 12, "Custom map needs one to twelve enemies.");
            HashSet<string> ids = new HashSet<string>();
            foreach (SpawnDef enemy in map.enemies)
            {
                Require(enemy != null && enemy.id != null && enemy.id.StartsWith("custom.enemy.", StringComparison.Ordinal) && enemy.id.Length <= 100 && ids.Add(enemy.id) && enemy.label != null && enemy.label.Length <= 100 && enemy.classId != null && catalog.Classes.ContainsKey(enemy.classId) && InCustomBounds(map, enemy.x, enemy.y) && !walls.Contains(TileId(enemy.x, enemy.y)) && occupied.Add(TileId(enemy.x, enemy.y)) && enemy.hp > 0 && enemy.hp <= 1000 && enemy.energy >= 0 && enemy.energy <= 100 && enemy.move > 0 && enemy.move <= 12, "Invalid enemy ID, stats, class or spawn.");
                Require(string.IsNullOrEmpty(enemy.artId) || enemy.artId == "rat" || enemy.artId == "guard" || enemy.artId == "boss", "Unknown custom enemy art.");
                ValidateTags(enemy.tags);
            }
            HashSet<string> reached = new HashSet<string>();
            List<CellView> queue = new List<CellView> { map.playerSpawns[0] };
            reached.Add(TileId(queue[0].x, queue[0].y));
            for (int i = 0; i < queue.Count; i++)
                foreach (CellView step in new[] { new CellView { x = queue[i].x + 1, y = queue[i].y }, new CellView { x = queue[i].x - 1, y = queue[i].y }, new CellView { x = queue[i].x, y = queue[i].y + 1 }, new CellView { x = queue[i].x, y = queue[i].y - 1 } })
                    if (InCustomBounds(map, step.x, step.y) && !walls.Contains(TileId(step.x, step.y)) && reached.Add(TileId(step.x, step.y)))
                        queue.Add(step);
            foreach (string cell in occupied)
                Require(reached.Contains(cell), "Workshop spawns must share a connected walkable region.");
            return new EncounterDef { id = "encounter.workshop", label = string.IsNullOrWhiteSpace(map.label) ? "Workshop encounter" : map.label, description = "A custom room imported from the tile workshop.", width = map.width, height = map.height, tiles = map.tiles, playerSpawns = map.playerSpawns, enemies = map.enemies, xp = data.encounters[0].xp, exploration = data.encounters[0].exploration };
        }
        private static bool InCustomBounds(CustomMapData map, int x, int y)
        {
            return x >= 0 && y >= 0 && x < map.width && y < map.height;
        }
    }
}
