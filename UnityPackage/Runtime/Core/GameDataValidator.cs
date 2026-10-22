using System;
using System.Collections.Generic;

namespace DungeonCrawlerTactics
{
    public static class GameDataValidator
    {
        public static void Validate(GameData data, Catalog catalog)
        {
            Need(data.schemaVersion == 1 && !string.IsNullOrEmpty(data.contentVersion), "Expected game schemaVersion 1 and a content version.");
            Need(data.roster != null && data.classStats != null && data.encounters != null && data.startingInventory != null && data.rewards != null && data.tagRules != null, "Game arrays cannot be null.");
            Need(data.partySize > 0 && data.partySize <= 8 && data.roster.Length >= data.partySize && data.roster.Length <= 32 && data.encounters.Length > 0 && data.encounters.Length <= 100 && data.energyPerRound >= 0 && data.energyPerRound <= 100, "Invalid game limits.");
            HashSet<string> stats = new HashSet<string>();
            foreach (ClassStats entry in data.classStats)
                Need(entry != null && entry.classId != null && catalog.Classes.ContainsKey(entry.classId) && stats.Add(entry.classId) && entry.hp > 0 && entry.hp <= 10000 && entry.energy >= 0 && entry.energy <= 1000 && entry.move > 0 && entry.move <= 20, "Invalid class stats.");
            foreach (string id in catalog.Classes.Keys) Need(stats.Contains(id), "Missing class stats: " + id);
            HashSet<string> roster = new HashSet<string>(); int selected = 0;
            foreach (RosterDef member in data.roster)
            {
                Need(member != null && !string.IsNullOrEmpty(member.id) && !member.id.StartsWith("tile.", StringComparison.Ordinal) && roster.Add(member.id) && !string.IsNullOrEmpty(member.label) && member.classId != null && catalog.Classes.ContainsKey(member.classId), "Invalid roster member.");
                if (member.selected) selected++;
            }
            Need(selected <= data.partySize, "Too many default party members.");
            HashSet<string> encounters = new HashSet<string>();
            foreach (EncounterDef encounter in data.encounters)
            {
                Need(encounter != null && !string.IsNullOrEmpty(encounter.id) && encounters.Add(encounter.id) && !string.IsNullOrEmpty(encounter.label) && encounter.width >= 4 && encounter.height >= 4 && encounter.width <= 30 && encounter.height <= 30 && encounter.xp >= 0 && encounter.xp <= 10000, "Invalid encounter.");
                Need(encounter.tiles != null && encounter.playerSpawns != null && encounter.enemies != null && encounter.playerSpawns.Length == data.partySize && encounter.enemies.Length > 0 && encounter.enemies.Length <= 30, "Invalid encounter arrays.");
                HashSet<string> tiles = new HashSet<string>(), walls = new HashSet<string>(), occupied = new HashSet<string>(), enemies = new HashSet<string>();
                foreach (TileDef tile in encounter.tiles)
                {
                    Need(tile != null && Inside(tile.x, tile.y, encounter) && tiles.Add(Key(tile.x, tile.y)), "Invalid or duplicate tile.");
                    Tags(tile.tags, catalog); if (tile.blocked) walls.Add(Key(tile.x, tile.y));
                }
                foreach (CellView spawn in encounter.playerSpawns)
                    Need(spawn != null && Inside(spawn.x, spawn.y, encounter) && !walls.Contains(Key(spawn.x, spawn.y)) && occupied.Add(Key(spawn.x, spawn.y)), "Invalid player spawn.");
                foreach (SpawnDef spawn in encounter.enemies)
                {
                    Need(spawn != null && !string.IsNullOrEmpty(spawn.id) && !spawn.id.StartsWith("tile.", StringComparison.Ordinal) && !roster.Contains(spawn.id) && enemies.Add(spawn.id) && !string.IsNullOrEmpty(spawn.label) && spawn.classId != null && catalog.Classes.ContainsKey(spawn.classId) && spawn.hp > 0 && spawn.hp <= 10000 && spawn.energy >= 0 && spawn.energy <= 1000 && spawn.move > 0 && spawn.move <= 20, "Invalid enemy.");
                    Need(Inside(spawn.x, spawn.y, encounter) && !walls.Contains(Key(spawn.x, spawn.y)) && occupied.Add(Key(spawn.x, spawn.y)), "Invalid enemy spawn."); Tags(spawn.tags, catalog);
                }
                // Every starting cell must share a connected walkable board; this prevents authored softlocks.
                HashSet<string> reached = new HashSet<string>(); Queue<CellView> pending = new Queue<CellView>();
                pending.Enqueue(encounter.playerSpawns[0]); reached.Add(Key(encounter.playerSpawns[0].x, encounter.playerSpawns[0].y));
                while (pending.Count > 0)
                {
                    CellView cell = pending.Dequeue(); int[] dx = { 0, -1, 1, 0 }, dy = { -1, 0, 0, 1 };
                    for (int i = 0; i < 4; i++)
                    {
                        int x = cell.x + dx[i], y = cell.y + dy[i]; string key = Key(x, y);
                        if (Inside(x, y, encounter) && !walls.Contains(key) && reached.Add(key)) pending.Enqueue(new CellView { x = x, y = y });
                    }
                }
                foreach (string position in occupied) Need(reached.Contains(position), "Spawn isolated by walls in " + encounter.id);
            }
            HashSet<string> inventory = new HashSet<string>();
            foreach (InventoryEntry item in data.startingInventory) Need(item != null && item.itemId != null && catalog.Items.ContainsKey(item.itemId) && inventory.Add(item.itemId) && item.count >= 0 && item.count <= 1000, "Invalid starting inventory.");
            HashSet<string> rewards = new HashSet<string>();
            foreach (RewardDef reward in data.rewards) Need(reward != null && !string.IsNullOrEmpty(reward.id) && rewards.Add(reward.id) && !string.IsNullOrEmpty(reward.label) && reward.count >= 0 && reward.count <= 100 && reward.heal >= 0 && reward.heal <= 10000 && (string.IsNullOrEmpty(reward.itemId) ? reward.count == 0 : catalog.Items.ContainsKey(reward.itemId)), "Invalid reward.");
            HashSet<string> rules = new HashSet<string>();
            foreach (TagRuleDef rule in data.tagRules) Need(rule != null && catalog.HasTag(rule.tag) && rules.Add(rule.tag) && rule.durationRounds >= 0 && rule.durationRounds <= 100 && rule.entryDamage >= 0 && rule.entryDamage <= 10000 && rule.turnDamage >= 0 && rule.turnDamage <= 10000 && rule.movePenalty >= 0 && rule.movePenalty <= 100 && rule.energyPenalty >= 0 && rule.energyPenalty <= 100, "Invalid tag rule.");
            foreach (TagRuleDef rule in data.tagRules) Need(string.IsNullOrEmpty(rule.occupantTag) || catalog.HasTag(rule.occupantTag), "Unknown occupant tag.");
        }
        private static bool Inside(int x, int y, EncounterDef encounter) { return x >= 0 && y >= 0 && x < encounter.width && y < encounter.height; }
        private static string Key(int x, int y) { return x + "," + y; }
        private static void Tags(string[] tags, Catalog catalog) { Need(tags != null, "Null authored tags."); HashSet<string> seen = new HashSet<string>(); foreach (string tag in tags) Need(catalog.HasTag(tag) && seen.Add(tag), "Unknown or duplicate authored tag."); }
        private static void Need(bool valid, string message) { if (!valid) throw new ArgumentException(message); }
    }
}
