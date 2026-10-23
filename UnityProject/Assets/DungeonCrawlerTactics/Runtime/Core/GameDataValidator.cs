using System;
using System.Collections.Generic;

namespace DungeonCrawlerTactics
{
    public static class GameDataValidator
    {
        public static void Validate(GameData data, Catalog catalog)
        {
            ValidateDevelopmentDefinitions(data, catalog);
            Need(data.schemaVersion == 1 && !string.IsNullOrEmpty(data.contentVersion), "Expected game schemaVersion 1 and a content version.");
            Need(data.compatibleContentVersions != null, "Compatible versions cannot be null.");
            Need(data.roster != null && data.classStats != null && data.encounters != null && data.startingInventory != null && data.rewards != null && data.tagRules != null, "Game arrays cannot be null.");
            Need(data.partySize > 0 && data.partySize <= 8 && data.roster.Length >= data.partySize && data.roster.Length <= 32 && data.encounters.Length > 0 && data.encounters.Length <= 100 && data.energyPerRound >= 0 && data.energyPerRound <= 100, "Invalid game limits.");
            Need(data.stances != null && data.forms != null, "Tactical adaptation arrays cannot be null.");
            foreach (TacticalModeDef[] modes in new[] { data.stances, data.forms })
            {
                HashSet<string> ids = new HashSet<string>(); Need(modes.Length <= 16, "Too many tactical adaptations.");
                foreach (TacticalModeDef mode in modes)
                {
                    Need(mode != null && !string.IsNullOrEmpty(mode.id) && ids.Add(mode.id) && !string.IsNullOrEmpty(mode.label) && !string.IsNullOrEmpty(mode.description), "Invalid tactical adaptation.");
                    Need(string.IsNullOrEmpty(mode.grantTag) || catalog.HasTag(mode.grantTag), "Unknown tactical adaptation tag.");
                    Need(Math.Abs(mode.hpBonus) <= 10 && Math.Abs(mode.manaBonus) <= 3 && Math.Abs(mode.moveBonus) <= 1, "Tactical adaptation exceeds bounded stats.");
                    Need(string.IsNullOrEmpty(mode.rosterId) || Array.Exists(data.roster, r => r.id == mode.rosterId && r.deployable), "Unknown tactical adaptation owner.");
                    Need(modes != data.forms || !string.IsNullOrEmpty(mode.rosterId), "Forms require a roster owner.");
                }
            }
            HashSet<string> stats = new HashSet<string>();
            foreach (ClassStats entry in data.classStats)
                Need(entry != null && entry.classId != null && catalog.Classes.ContainsKey(entry.classId) && stats.Add(entry.classId) && entry.hp > 0 && entry.hp <= 10000 && entry.energy >= 0 && entry.energy <= 1000 && entry.move > 0 && entry.move <= 20, "Invalid class stats.");
            foreach (string id in catalog.Classes.Keys) Need(stats.Contains(id), "Missing class stats: " + id);
            HashSet<string> roster = new HashSet<string>(); int selected = 0;
            foreach (RosterDef member in data.roster)
            {
                Need(member != null && !string.IsNullOrEmpty(member.id) && !member.id.StartsWith("tile.", StringComparison.Ordinal) && roster.Add(member.id) && !string.IsNullOrEmpty(member.label) && member.classId != null && catalog.Classes.ContainsKey(member.classId), "Invalid roster member.");
                Need(string.IsNullOrEmpty(member.legacyClassId) || catalog.Classes.ContainsKey(member.legacyClassId), "Unknown legacy class.");
                Need(member.innateAbilityIds != null, "Innate abilities cannot be null.");
                HashSet<string> grants = new HashSet<string>(); foreach (string id in member.innateAbilityIds) Need(id != null && catalog.Abilities.ContainsKey(id) && grants.Add(id), "Unknown or duplicate innate ability.");
                Need(!member.selected || member.deployable, "Advisor cannot be selected.");
                if (member.selected) selected++;
            }
            HashSet<string> replacements = new HashSet<string>(); foreach (RosterDef member in data.roster) if (!string.IsNullOrEmpty(member.replacesId)) Need(member.replacesId != member.id && roster.Contains(member.replacesId) && replacements.Add(member.replacesId), "Invalid roster replacement.");
            Need(selected <= data.partySize, "Too many default party members.");
            Need(data.progression != null && data.progression.xpThresholds != null && data.progression.xpThresholds.Length > 0 && data.progression.xpThresholds.Length <= 20 && data.progression.xpThresholds[0] == 0 && data.progression.skillUnlocks != null && data.equipment != null, "Invalid progression configuration.");
            for (int i = 1; i < data.progression.xpThresholds.Length; i++) Need(data.progression.xpThresholds[i] > data.progression.xpThresholds[i - 1] && data.progression.xpThresholds[i] <= 1000000, "XP thresholds must increase from zero.");
            Need(data.progression.hpPerLevel >= 0 && data.progression.hpPerLevel <= 100 && data.progression.manaPerLevel >= 0 && data.progression.manaPerLevel <= 100 && data.progression.movePerLevel >= 0 && data.progression.movePerLevel <= 2, "Invalid progression stat growth.");
            HashSet<string> skillIds = new HashSet<string>();
            foreach (SkillUnlockDef skill in data.progression.skillUnlocks) Need(skill != null && StableId(skill.id) && skillIds.Add(skill.id) && !string.IsNullOrEmpty(skill.label) && (string.IsNullOrEmpty(skill.rosterId) || roster.Contains(skill.rosterId)) && skill.abilityId != null && catalog.Abilities.ContainsKey(skill.abilityId) && skill.level >= 1 && skill.level <= data.progression.xpThresholds.Length, "Invalid skill unlock.");
            HashSet<string> gearIds = new HashSet<string>();
            foreach (EquipmentDef gear in data.equipment)
            {
                Need(gear != null && StableId(gear.id) && gearIds.Add(gear.id) && !string.IsNullOrEmpty(gear.label) && (gear.slot == "weapon" || gear.slot == "armor" || gear.slot == "charm") && gear.hpBonus >= 0 && gear.hpBonus <= 1000 && gear.manaBonus >= 0 && gear.manaBonus <= 1000 && gear.moveBonus >= 0 && gear.moveBonus <= 5 && gear.unlockEncounter >= 0 && gear.unlockEncounter <= data.encounters.Length && gear.abilityIds != null, "Invalid equipment.");
                HashSet<string> grants = new HashSet<string>(); foreach (string ability in gear.abilityIds) Need(ability != null && catalog.Abilities.ContainsKey(ability) && grants.Add(ability), "Invalid equipment ability grant.");
            }
            HashSet<string> encounters = new HashSet<string>(), sectors = new HashSet<string>();
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
                ExplorationDef map = encounter.exploration;
                Need(map != null && !string.IsNullOrEmpty(map.id) && !string.IsNullOrEmpty(map.label) && map.width >= 4 && map.height >= 4 && map.width <= 30 && map.height <= 30 && map.discoveryRadius >= 1 && map.discoveryRadius <= 3 && map.walls != null && map.points != null && map.points.Length > 0 && map.points.Length <= 100, "Invalid exploration sector.");
                Func<int, int, bool> inside = (x, y) => x >= 0 && y >= 0 && x < map.width && y < map.height;
                HashSet<string> mapWalls = new HashSet<string>(), pointIds = new HashSet<string>(), pointCells = new HashSet<string>();
                foreach (CellView wall in map.walls) Need(wall != null && inside(wall.x, wall.y) && mapWalls.Add(Key(wall.x, wall.y)), "Invalid exploration wall.");
                Need(inside(map.startX, map.startY) && !mapWalls.Contains(Key(map.startX, map.startY)), "Invalid exploration start.");
                HashSet<string> mapReached = new HashSet<string>(); Queue<CellView> mapQueue = new Queue<CellView>(); mapQueue.Enqueue(new CellView { x = map.startX, y = map.startY }); mapReached.Add(Key(map.startX, map.startY));
                while (mapQueue.Count > 0) { CellView c = mapQueue.Dequeue(); int[] dx = { 0, -1, 1, 0 }, dy = { -1, 0, 0, 1 }; for (int i = 0; i < 4; i++) { int x = c.x + dx[i], y = c.y + dy[i]; if (inside(x, y) && !mapWalls.Contains(Key(x, y)) && mapReached.Add(Key(x, y))) mapQueue.Enqueue(new CellView { x = x, y = y }); } }
                int doors = 0;
                foreach (ExplorationPointDef point in map.points)
                {
                    Need(point != null && !string.IsNullOrEmpty(point.id) && pointIds.Add(point.id) && !string.IsNullOrEmpty(point.label) && point.description != null && inside(point.x, point.y) && pointCells.Add(Key(point.x, point.y)) && mapReached.Contains(Key(point.x, point.y)), "Invalid or unreachable exploration discovery.");
                    Need(point.kind == "encounter" || point.kind == "cache" || point.kind == "lore", "Unknown discovery kind.");
                    if (point.kind == "encounter") doors++;
                    Need(point.kind == "cache" ? point.itemId != null && catalog.Items.ContainsKey(point.itemId) && point.count > 0 && point.count <= 100 : string.IsNullOrEmpty(point.itemId) && point.count == 0, "Invalid discovery supplies.");
                }
                Need(doors == 1, "Exploration requires exactly one encounter door.");
                Need(sectors.Add(map.id), "Duplicate exploration sector ID.");
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
            ScenarioDefinitionValidator.Validate(data, catalog);
        }
        private static bool StableId(string id) { return id != null && System.Text.RegularExpressions.Regex.IsMatch(id, @"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$"); }
        private static bool Inside(int x, int y, EncounterDef encounter) { return x >= 0 && y >= 0 && x < encounter.width && y < encounter.height; }
        private static string Key(int x, int y) { return x + "," + y; }
        private static void Tags(string[] tags, Catalog catalog) { Need(tags != null, "Null authored tags."); HashSet<string> seen = new HashSet<string>(); foreach (string tag in tags) Need(catalog.HasTag(tag) && seen.Add(tag), "Unknown or duplicate authored tag."); }
        private static void ValidateDevelopmentDefinitions(GameData data, Catalog catalog)
        {
            DevelopmentDef config = data.development;
            Need(config != null && config.stats != null && config.practice != null && config.recipes != null && config.lootBoxes != null && config.pointsPerLevel >= 0 && config.pointsPerLevel <= 3, "Invalid development configuration.");
            Need(config.stats.Length == 0 || config.stats.Length == 5, "Development defines exactly five stats.");
            HashSet<string> ids = new HashSet<string>();
            foreach (StatDefinition stat in config.stats)
            {
                Need(stat != null && StableId(stat.id) && ids.Add(stat.id) && !string.IsNullOrEmpty(stat.label) && !string.IsNullOrEmpty(stat.description), "Invalid stat definition.");
                Need(stat.hpPerPoint >= 0 && stat.hpPerPoint <= 5 && stat.manaPerPoint >= 0 && stat.manaPerPoint <= 3 && stat.moveEvery >= 0 && stat.moveEvery <= 10 && stat.damageEvery >= 0 && stat.damageEvery <= 10 && stat.healEvery >= 0 && stat.healEvery <= 10, "Invalid stat formula.");
                Need(stat.hpPerPoint + stat.manaPerPoint + stat.moveEvery + stat.damageEvery + stat.healEvery > 0, "A stat must have a real effect.");
            }
            SkillProgressionDef practice = config.practice; Need(practice.useThresholds != null && practice.useThresholds.Length > 0 && practice.useThresholds.Length <= 3 && practice.useThresholds[0] == 0, "Invalid skill rank thresholds.");
            for (int i = 1; i < practice.useThresholds.Length; i++) Need(practice.useThresholds[i] > practice.useThresholds[i - 1] && practice.useThresholds[i] <= 100000, "Skill thresholds must increase.");
            Need(practice.damagePerRank >= 0 && practice.damagePerRank <= 1 && practice.healPerRank >= 0 && practice.healPerRank <= 1 && practice.costReductionPerRank >= 0 && practice.costReductionPerRank <= 1, "Skill bonuses exceed bounded adaptation.");
            Need(config.recipes.Length <= 32 && config.lootBoxes.Length <= 16, "Too many recipes or loot definitions."); ids.Clear();
            foreach (RecipeDef recipe in config.recipes)
            {
                Need(recipe != null && StableId(recipe.id) && ids.Add(recipe.id) && !string.IsNullOrEmpty(recipe.label) && !string.IsNullOrEmpty(recipe.description), "Invalid recipe.");
                ValidateQuantities(recipe.ingredients, catalog); ValidateQuantities(recipe.outputs, catalog);
            }
            ids.Clear(); string[] achievements = { "achievement.first_move", "achievement.first_reaction", "achievement.first_form", "achievement.first_victory", "achievement.first_level" };
            foreach (LootBoxDef box in config.lootBoxes)
            {
                Need(box != null && StableId(box.id) && ids.Add(box.id) && !string.IsNullOrEmpty(box.label) && !string.IsNullOrEmpty(box.description), "Invalid loot definition.");
                Need(box.fromVictory != !string.IsNullOrEmpty(box.achievementId) && (string.IsNullOrEmpty(box.achievementId) || Array.IndexOf(achievements, box.achievementId) >= 0), "A loot box needs one known earning source.");
                ValidateQuantities(box.rewards, catalog);
            }
        }
        private static void ValidateQuantities(ItemQuantity[] quantities, Catalog catalog)
        {
            Need(quantities != null && quantities.Length > 0 && quantities.Length <= 8, "Invalid item quantities."); HashSet<string> ids = new HashSet<string>();
            foreach (ItemQuantity row in quantities) Need(row != null && row.itemId != null && catalog.Items.ContainsKey(row.itemId) && ids.Add(row.itemId) && row.count > 0 && row.count <= 100, "Unknown, duplicate or invalid item quantity.");
        }
        private static void Need(bool valid, string message) { if (!valid) throw new ArgumentException(message); }
    }
}
