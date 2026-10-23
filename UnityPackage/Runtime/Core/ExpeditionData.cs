using System;
using System.Collections.Generic;
using System.Text.RegularExpressions;
namespace DungeonCrawlerTactics
{
    [Serializable] public sealed class ExpeditionDef
    {
        public string id, label, description, objective, theme, difficulty;
        public EncounterDef encounter;
        public MapPlacement[] decorations = new MapPlacement[0];
    }
    [Serializable] public sealed class ExpeditionSave { public int version = 1; public string id; public GameSave campaign; }
    [Serializable] public sealed class ExpeditionOptionView
    {
        public string id, label, description, objective, theme, difficulty;
        public string[] enemyTypes = new string[0];
    }
    [Serializable] public sealed class ExpeditionView
    {
        public string id, label, description, objective, theme, difficulty;
        public MapPlacement[] decorations = new MapPlacement[0];
    }
    public static class ExpeditionDefinitionValidator
    {
        private static void Need(bool value, string message) { if (!value) throw new ArgumentException(message); }
        private static bool Id(string value) { return value != null && Regex.IsMatch(value, @"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$"); }
        public static void Validate(GameData data, Catalog catalog)
        {
            Need(data.expeditions != null && data.expeditions.Length <= 24, "Invalid expedition collection.");
            HashSet<string> ids = new HashSet<string>();
            foreach (ExpeditionDef expedition in data.expeditions)
            {
                Need(expedition != null && Id(expedition.id) && ids.Add(expedition.id) && !string.IsNullOrEmpty(expedition.label) && expedition.label.Length <= 100 && !string.IsNullOrEmpty(expedition.description) && expedition.description.Length <= 1000 && !string.IsNullOrEmpty(expedition.objective), "Invalid expedition identity.");
                EncounterDef encounter = expedition.encounter;
                Need(encounter != null && Id(encounter.id) && !string.IsNullOrEmpty(encounter.label) && encounter.description != null && encounter.width >= 6 && encounter.width <= 20 && encounter.height >= 6 && encounter.height <= 16 && encounter.xp == 0, "Invalid expedition encounter dimensions or rewards.");
                Need(encounter.tiles != null && encounter.tiles.Length <= encounter.width * encounter.height && encounter.playerSpawns != null && encounter.playerSpawns.Length == data.partySize && encounter.enemies != null && encounter.enemies.Length > 0 && encounter.enemies.Length <= 12, "Invalid expedition map collections.");
                Func<int, int, bool> inside = (x, y) => x >= 0 && y >= 0 && x < encounter.width && y < encounter.height;
                HashSet<string> walls = new HashSet<string>(), cells = new HashSet<string>(), occupied = new HashSet<string>(), enemyIds = new HashSet<string>();
                foreach (TileDef tile in encounter.tiles)
                {
                    Need(tile != null && inside(tile.x, tile.y) && cells.Add(tile.x + ":" + tile.y) && tile.tags != null, "Duplicate or invalid expedition tile.");
                    HashSet<string> tags = new HashSet<string>(); foreach (string tag in tile.tags) Need(tag != null && catalog.HasTag(tag) && tags.Add(tag), "Unknown or duplicate expedition terrain tag.");
                    if (tile.blocked) walls.Add(tile.x + ":" + tile.y);
                }
                foreach (CellView spawn in encounter.playerSpawns) Need(spawn != null && inside(spawn.x, spawn.y) && !walls.Contains(spawn.x + ":" + spawn.y) && occupied.Add(spawn.x + ":" + spawn.y), "Invalid expedition player spawn.");
                foreach (SpawnDef enemy in encounter.enemies)
                {
                    Need(enemy != null && Id(enemy.id) && !Array.Exists(data.roster, r => r.id == enemy.id) && enemyIds.Add(enemy.id) && !string.IsNullOrEmpty(enemy.label) && enemy.classId != null && catalog.Classes.ContainsKey(enemy.classId) && enemy.hp > 0 && enemy.hp <= 1000 && enemy.energy >= 0 && enemy.energy <= 100 && enemy.move > 0 && enemy.move <= 12 && enemy.tags != null, "Invalid expedition enemy kit or stats.");
                    Need(inside(enemy.x, enemy.y) && !walls.Contains(enemy.x + ":" + enemy.y) && occupied.Add(enemy.x + ":" + enemy.y), "Invalid expedition enemy spawn.");
                    foreach (string tag in enemy.tags) Need(catalog.HasTag(tag), "Unknown expedition enemy tag.");
                    Need(Array.IndexOf(new[] { "sludge", "cinder", "frost", "spore", "sentry", "mauler", "rat", "guard", "boss", "scatterer" }, enemy.artId) >= 0, "Unknown expedition enemy art.");
                }
                HashSet<string> reached = new HashSet<string>(); List<CellView> queue = new List<CellView> { encounter.playerSpawns[0] }; reached.Add(queue[0].x + ":" + queue[0].y);
                for (int i = 0; i < queue.Count; i++) foreach (CellView next in new[] { new CellView { x = queue[i].x + 1, y = queue[i].y }, new CellView { x = queue[i].x - 1, y = queue[i].y }, new CellView { x = queue[i].x, y = queue[i].y + 1 }, new CellView { x = queue[i].x, y = queue[i].y - 1 } }) if (inside(next.x, next.y) && !walls.Contains(next.x + ":" + next.y) && reached.Add(next.x + ":" + next.y)) queue.Add(next);
                foreach (string cell in occupied) Need(reached.Contains(cell), "Expedition spawns are disconnected.");
                Need(expedition.decorations != null && expedition.decorations.Length <= 96, "Invalid expedition decoration collection.");
                HashSet<string> decorIds = new HashSet<string>();
                string[] assets = { "wall-ne", "wall-nw", "wall-corner", "pillar", "door-closed-nw", "door-open-nw", "door-closed-ne", "door-open-ne", "torch", "lever", "grate", "oil-overlay", "water-overlay", "moss", "rubble", "stairs", "stone-a", "stone-b", "water-floor", "oil-floor", "crate", "barrel", "chest", "exit", "fire-overlay", "scenario.garbage", "scenario.bench", "scenario.barrier", "scenario.parts" };
                foreach (MapPlacement piece in expedition.decorations) Need(piece != null && Id(piece.id) && decorIds.Add(piece.id) && Array.IndexOf(assets, piece.assetId) >= 0 && inside(piece.x, piece.y) && !piece.blocksMovement && piece.rotation >= 0 && piece.rotation < 4 && (piece.layer == "ground" || piece.layer == "prop" || piece.layer == "wall"), "Invalid expedition decoration reference or anchor.");
            }
        }
    }
}
