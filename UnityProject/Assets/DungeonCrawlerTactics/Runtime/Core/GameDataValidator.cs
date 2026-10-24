using System;
using System.Collections.Generic;

namespace DungeonCrawlerTactics
{
    public static class GameDataValidator
    {
        public static void Validate(GameData data, Catalog catalog)
        {
            Need(data != null && catalog != null, "Game data and catalog are required.");
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
            foreach (ClassDef definition in catalog.Classes.Values)
            {
                Need(stats.Contains(definition.id), "Missing class stats: " + definition.id);
                Need(definition.minimumFloor >= 1 && definition.minimumFloor <= 18, "Class availability must be within floors 1–18.");
            }
            HashSet<string> roster = new HashSet<string>(); int selected = 0;
            foreach (RosterDef member in data.roster)
            {
                Need(member != null && !string.IsNullOrEmpty(member.id) && !member.id.StartsWith("tile.", StringComparison.Ordinal) && roster.Add(member.id) && !string.IsNullOrEmpty(member.label) && member.classId != null && catalog.Classes.ContainsKey(member.classId) && catalog.Classes[member.classId].playerSelectable, "Invalid roster member.");
                Need(string.IsNullOrEmpty(member.legacyClassId) || catalog.Classes.ContainsKey(member.legacyClassId), "Unknown legacy class.");
                Need(member.combatTags != null, "Combat tags cannot be null."); foreach (string tag in member.combatTags) Need(catalog.HasTag(tag), "Unknown roster combat tag.");
                Need(member.specialtyClassIds != null, "Specialty classes cannot be null.");
                HashSet<string> specialties = new HashSet<string>(); foreach (string id in member.specialtyClassIds) Need(id != null && catalog.Classes.ContainsKey(id) && catalog.Classes[id].playerSelectable && specialties.Add(id), "Unknown or duplicate specialty class.");
                Need(member.innateAbilityIds != null, "Innate abilities cannot be null.");
                Need(member.maxSkillRank >= SkillRankProgression.NormalRankCap && member.maxSkillRank <= SkillRankProgression.AbsoluteRankCap, "Crawler skill rank eligibility must be within ranks 15–20.");
                HashSet<string> grants = new HashSet<string>(); foreach (string id in member.innateAbilityIds) Need(id != null && catalog.Abilities.ContainsKey(id) && grants.Add(id), "Unknown or duplicate innate ability.");
                Need(!member.selected || member.deployable, "Advisor cannot be selected.");
                if (member.selected) selected++;
            }
            HashSet<string> replacements = new HashSet<string>(); foreach (RosterDef member in data.roster) if (!string.IsNullOrEmpty(member.replacesId)) Need(member.replacesId != member.id && roster.Contains(member.replacesId) && replacements.Add(member.replacesId), "Invalid roster replacement.");
            Need(selected <= data.partySize, "Too many default party members.");
            Need(data.progression != null && data.progression.xpThresholds != null && data.progression.xpThresholds.Length > 0 && data.progression.xpThresholds.Length <= 50 && data.progression.xpThresholds[0] == 0 && data.progression.skillUnlocks != null && data.equipment != null, "Invalid progression configuration.");
            for (int i = 1; i < data.progression.xpThresholds.Length; i++) Need(data.progression.xpThresholds[i] > data.progression.xpThresholds[i - 1] && data.progression.xpThresholds[i] <= 1000000, "XP thresholds must increase from zero.");
            Need(data.progression.hpPerLevel >= 0 && data.progression.hpPerLevel <= 100 && data.progression.manaPerLevel >= 0 && data.progression.manaPerLevel <= 100 && data.progression.movePerLevel >= 0 && data.progression.movePerLevel <= 2, "Invalid progression stat growth.");
            HashSet<string> skillIds = new HashSet<string>();
            foreach (SkillUnlockDef skill in data.progression.skillUnlocks) Need(skill != null && StableId(skill.id) && skillIds.Add(skill.id) && !string.IsNullOrEmpty(skill.label) && (string.IsNullOrEmpty(skill.rosterId) || roster.Contains(skill.rosterId)) && skill.abilityId != null && catalog.Abilities.ContainsKey(skill.abilityId) && skill.minimumFloor >= 1 && skill.minimumFloor <= 18 && skill.level >= 1 && skill.level <= data.progression.xpThresholds.Length, "Invalid skill unlock.");
            HashSet<string> gearIds = new HashSet<string>();
            foreach (EquipmentDef gear in data.equipment)
            {
                Need(gear != null && StableId(gear.id) && gearIds.Add(gear.id) && !string.IsNullOrEmpty(gear.label) && (gear.slot == "weapon" || gear.slot == "armor" || gear.slot == "charm") && gear.hpBonus >= 0 && gear.hpBonus <= 1000 && gear.manaBonus >= 0 && gear.manaBonus <= 1000 && gear.moveBonus >= 0 && gear.moveBonus <= 5 && gear.unlockEncounter >= 0 && gear.unlockEncounter <= data.encounters.Length && gear.abilityIds != null, "Invalid equipment.");
                HashSet<string> grants = new HashSet<string>(); foreach (string ability in gear.abilityIds) Need(ability != null && catalog.Abilities.ContainsKey(ability) && grants.Add(ability), "Invalid equipment ability grant.");
            }
            HashSet<string> encounters = new HashSet<string>(), sectors = new HashSet<string>();
            List<EncounterDef> allEncounters = new List<EncounterDef>(data.encounters);
            ValidateJourneyDefinitions(data, allEncounters);
            foreach (EncounterDef encounter in allEncounters)
            {
                Need(encounter != null && !string.IsNullOrEmpty(encounter.id) && encounters.Add(encounter.id) && !string.IsNullOrEmpty(encounter.label) && encounter.width >= 4 && encounter.height >= 4 && encounter.width <= 30 && encounter.height <= 30 && encounter.xp >= 0 && encounter.xp <= 1000000, "Invalid encounter.");
                ValidateBattleLayout(encounter, catalog);
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
            Need(data.sponsorChallenges != null && data.sponsorChallenges.Length <= 16, "Invalid sponsor challenges.");
            HashSet<string> sponsorIds = new HashSet<string>();
            foreach (SponsorChallengeDef c in data.sponsorChallenges) Need(c != null && !string.IsNullOrEmpty(c.id) && sponsorIds.Add(c.id) && !string.IsNullOrEmpty(c.label) && !string.IsNullOrEmpty(c.description) && (c.eventType == "reaction" || c.eventType == "rescue" || c.eventType == "victory") && c.rewardItemId != null && catalog.Items.ContainsKey(c.rewardItemId) && c.rewardCount > 0 && c.rewardCount <= 100, "Invalid sponsor challenge.");
            HashSet<string> rules = new HashSet<string>();
            foreach (TagRuleDef rule in data.tagRules) Need(rule != null && catalog.HasTag(rule.tag) && rules.Add(rule.tag) && rule.durationRounds >= 0 && rule.durationRounds <= 100 && rule.entryDamage >= 0 && rule.entryDamage <= 10000 && rule.turnDamage >= 0 && rule.turnDamage <= 10000 && rule.moveBonus >= 0 && rule.moveBonus <= 12 && rule.movePenalty >= 0 && rule.movePenalty <= 100 && rule.energyPenalty >= 0 && rule.energyPenalty <= 100, "Invalid tag rule.");
            foreach (TagRuleDef rule in data.tagRules) Need(string.IsNullOrEmpty(rule.occupantTag) || catalog.HasTag(rule.occupantTag), "Unknown occupant tag.");
            foreach (TagRuleDef rule in data.tagRules) Need(!rule.consumeOnEntry || rule.durationRounds == 0 && rule.turnDamage == 0 && !string.IsNullOrEmpty(rule.occupantTag), "Traps require persistent single-entry effects and no round damage.");
            ValidateSkillTreeDefinitions(data, catalog);
            ScenarioDefinitionValidator.Validate(data, catalog);
            ExpeditionDefinitionValidator.Validate(data, catalog);
            HomeDefinitionValidator.Validate(data.home, catalog, data.roster);
            NeighborhoodDefinitionValidator.Validate(data, catalog);
            if (data.home != null) foreach (string ability in data.home.trainingAbilityIds) Need(catalog.Abilities.ContainsKey(ability), "Unknown home training ability.");
        }
        internal static void ValidateBattleLayout(EncounterDef encounter, Catalog catalog)
        {
            Need(encounter.layoutVersion == 1 && encounter.legacyTiles != null && encounter.legacyTiles.Length <= encounter.width * encounter.height, "Invalid battle layout version or legacy tiles.");
            HashSet<string> cells = new HashSet<string>();
            foreach (TileDef tile in encounter.legacyTiles)
            {
                Need(tile != null && Inside(tile.x, tile.y, encounter) && cells.Add(Key(tile.x, tile.y)), "Invalid legacy battle tile.");
                Tags(tile.tags, catalog);
            }
            Need(encounter.decorations != null && encounter.decorations.Length <= 200, "Invalid battle decorations.");
            HashSet<string> ids = new HashSet<string>();
            foreach (MapPlacement piece in encounter.decorations)
                Need(piece != null && StableId(piece.id) && ids.Add(piece.id) && !string.IsNullOrEmpty(piece.assetId) && piece.assetId.Length <= 80 && Inside(piece.x, piece.y, encounter) && piece.rotation >= 0 && piece.rotation < 4 && !piece.blocksMovement && (piece.layer == "ground" || piece.layer == "prop" || piece.layer == "wall"), "Invalid battle decoration.");
        }

        private static void ValidateJourneyDefinitions(GameData data, List<EncounterDef> encounters)
        {
            if (data.journey == null) return;
            JourneyDef journey = data.journey;
            Need(journey.schemaVersion == 1 && StableId(journey.id) && !string.IsNullOrEmpty(journey.label) && !string.IsNullOrEmpty(journey.description) && journey.floors != null && journey.floors.Length == 18, "Story campaign requires an eighteen-floor registry.");
            HashSet<string> ids = new HashSet<string>();
            string[] mechanics = { "none", "tutorial", "classes", "route", "beacons", "hunt", "capture" };
            for (int i = 0; i < journey.floors.Length; i++)
            {
                JourneyFloorDef floor = journey.floors[i];
                Need(floor != null && StableId(floor.id) && ids.Add(floor.id) && floor.number == i + 1 && !string.IsNullOrEmpty(floor.label) && !string.IsNullOrEmpty(floor.description) && Array.IndexOf(mechanics, floor.mechanic) >= 0 && floor.requiredPointIds != null, "Invalid story floor registry entry.");
                Need(floor.available == (i < 8) && floor.kind == (i >= 8 ? "locked" : i == 6 ? "bypass" : "battle"), "Story floor availability must preserve the destroyed seventh floor and locked later floors.");
                Need(floor.kind == "battle" ? floor.encounter != null : floor.encounter == null && floor.requiredPointIds.Length == 0 && floor.captureCount == 0, "Only playable story floors contain encounters.");
                if (floor.encounter == null) continue;
                Need(floor.encounter.exploration != null && floor.encounter.exploration.points != null, "Story floors require exploration.");
                encounters.Add(floor.encounter);
                HashSet<string> required = new HashSet<string>();
                foreach (string id in floor.requiredPointIds) Need(id != null && required.Add(id) && Array.Exists(floor.encounter.exploration.points, p => p != null && p.id == id && p.kind == "lore"), "Unknown or duplicate story route objective.");
                Need(floor.mechanic != "route" || floor.requiredPointIds.Length == 1, "The railway requires one route lever.");
                Need(floor.mechanic != "beacons" || floor.requiredPointIds.Length == 4, "The bubble requires four quadrant beacons.");
                Need(floor.mechanic == "capture" ? floor.captureCount == 6 && floor.encounter.enemies != null && floor.encounter.enemies.Length == 6 : floor.captureCount == 0, "Ghosts of Earth requires six authored capturable monsters.");
            }
            Need(journey.floors[0].mechanic == "tutorial" && journey.floors[1].mechanic == "tutorial" && journey.floors[2].mechanic == "classes" && journey.floors[3].mechanic == "route" && journey.floors[4].mechanic == "beacons" && journey.floors[5].mechanic == "hunt" && journey.floors[7].mechanic == "capture", "Story floors require their explicit bounded mechanics.");
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
            SkillProgressionDef practice = config.practice; Need(practice.useThresholds != null && practice.useThresholds.Length > 0 && practice.useThresholds.Length <= SkillRankProgression.AbsoluteRankCap && practice.useThresholds[0] == 0, "Invalid skill rank thresholds.");
            for (int i = 1; i < practice.useThresholds.Length; i++) Need(practice.useThresholds[i] > practice.useThresholds[i - 1] && practice.useThresholds[i] <= 100000, "Skill thresholds must increase.");
            Need(practice.damagePerRank >= 0 && practice.damagePerRank <= 1 && practice.healPerRank >= 0 && practice.healPerRank <= 1 && practice.costReductionPerRank >= 0 && practice.costReductionPerRank <= 1, "Skill bonuses exceed bounded adaptation.");
            Need(practice.abilityProfiles != null && practice.abilityProfiles.Length <= catalog.Abilities.Count, "Invalid ability rank profiles.");
            HashSet<string> profileIds = new HashSet<string>();
            foreach (AbilityRankProfile profile in practice.abilityProfiles)
            {
                Need(profile != null && profile.abilityId != null && catalog.Abilities.ContainsKey(profile.abilityId) && profileIds.Add(profile.abilityId), "Unknown or duplicate ability rank profile.");
                Need(profile.practiceMultiplierPercent >= 1 && profile.practiceMultiplierPercent <= 1000 && profile.damagePerRank >= -1 && profile.damagePerRank <= 5 && profile.healPerRank >= -1 && profile.healPerRank <= 5 && profile.costReductionPerRank >= -1 && profile.costReductionPerRank <= 5, "Invalid ability rank training or per-rank effect.");
                Need(profile.damageBonusCap >= 0 && profile.damageBonusCap <= 100 && profile.healBonusCap >= 0 && profile.healBonusCap <= 100 && profile.costReductionCap >= 0 && profile.costReductionCap <= 100 && profile.milestones != null && profile.milestones.Length < SkillRankProgression.AbsoluteRankCap, "Invalid ability rank caps or milestones.");
                HashSet<int> milestoneRanks = new HashSet<int>();
                foreach (RankMilestoneDef milestone in profile.milestones)
                {
                    Need(milestone != null && milestone.rank >= 2 && milestone.rank <= SkillRankProgression.AbsoluteRankCap && milestoneRanks.Add(milestone.rank) && !string.IsNullOrEmpty(milestone.description), "Invalid or duplicate rank milestone.");
                    Need(milestone.damageBonus >= 0 && milestone.damageBonus <= 100 && milestone.healBonus >= 0 && milestone.healBonus <= 100 && milestone.costReduction >= 0 && milestone.costReduction <= 100 && milestone.damageBonus + milestone.healBonus + milestone.costReduction > 0, "Rank milestones require bounded supported effects.");
                }
            }
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
        private static void ValidateSkillTreeDefinitions(GameData data, Catalog catalog)
        {
            Need(data.skillTrees != null && data.skillTrees.Length <= data.roster.Length && data.classSkillTrees != null && data.classSkillTrees.Length <= catalog.Classes.Count, "Invalid skill-tree collection.");
            HashSet<string> trees = new HashSet<string>(), owners = new HashSet<string>(), classes = new HashSet<string>(), nodeIds = new HashSet<string>();
            foreach (SkillTreeDef tree in data.skillTrees)
            {
                Need(tree != null && tree.rosterId != null && Array.Exists(data.roster, r => r.id == tree.rosterId && r.deployable) && owners.Add(tree.rosterId) && string.IsNullOrEmpty(tree.classId), "Invalid personal skill-tree owner.");
                ValidateSkillTree(tree, catalog, trees, nodeIds, Math.Min(50, data.progression.xpThresholds.Length));
            }
            foreach (SkillTreeDef tree in data.classSkillTrees)
            {
                Need(tree != null && tree.classId != null && catalog.Classes.ContainsKey(tree.classId) && catalog.Classes[tree.classId].playerSelectable && classes.Add(tree.classId) && string.IsNullOrEmpty(tree.rosterId), "Invalid class skill-tree owner.");
                ValidateSkillTree(tree, catalog, trees, nodeIds, 50);
            }
            if (data.skillTrees.Length > 0) foreach (RosterDef member in data.roster) Need(!member.deployable || owners.Contains(member.id), "Every deployable crawler needs an authored skill tree.");
        }
        private static void ValidateSkillTree(SkillTreeDef tree, Catalog catalog, HashSet<string> treeIds, HashSet<string> nodeIds, int maximumLevel)
        {
            Need(StableId(tree.id) && treeIds.Add(tree.id) && !string.IsNullOrEmpty(tree.label) && !string.IsNullOrEmpty(tree.description), "Invalid skill-tree identity.");
            Need(tree.nodes != null && tree.nodes.Length > 0 && tree.nodes.Length <= 32, "Invalid skill-tree nodes.");
            Dictionary<string, SkillNodeDef> nodes = new Dictionary<string, SkillNodeDef>();
            foreach (SkillNodeDef node in tree.nodes)
            {
                Need(node != null && StableId(node.id) && nodeIds.Add(node.id) && !string.IsNullOrEmpty(node.label) && !string.IsNullOrEmpty(node.description) && node.level >= 1 && node.level <= maximumLevel && node.pointCost == 1 && node.prerequisiteIds != null && node.abilityIds != null, "Invalid skill-tree node.");
                Need(node.hpBonus >= 0 && node.hpBonus <= 6 && node.manaBonus >= 0 && node.manaBonus <= 3 && node.moveBonus >= 0 && node.moveBonus <= 1 && node.damageBonus >= 0 && node.damageBonus <= 1 && node.healBonus >= 0 && node.healBonus <= 1, "Skill-tree bonus exceeds bounded adaptation.");
                Need(node.abilityIds.Length <= 4 && node.prerequisiteIds.Length <= 4 && node.abilityIds.Length + node.hpBonus + node.manaBonus + node.moveBonus + node.damageBonus + node.healBonus > 0, "A skill-tree node must have a supported benefit.");
                HashSet<string> grants = new HashSet<string>(); foreach (string ability in node.abilityIds) Need(ability != null && catalog.Abilities.ContainsKey(ability) && grants.Add(ability), "Unknown or duplicate skill-tree ability.");
                nodes.Add(node.id, node);
            }
            foreach (SkillNodeDef node in tree.nodes)
            {
                HashSet<string> parents = new HashSet<string>(); foreach (string parent in node.prerequisiteIds) Need(parent != null && nodes.ContainsKey(parent) && parents.Add(parent) && nodes[parent].level <= node.level, "Invalid skill-tree prerequisite.");
            }
            HashSet<string> visiting = new HashSet<string>(), visited = new HashSet<string>(); foreach (SkillNodeDef node in tree.nodes) VisitSkillNode(node.id, nodes, visiting, visited);
        }
        private static void VisitSkillNode(string id, Dictionary<string, SkillNodeDef> nodes, HashSet<string> visiting, HashSet<string> visited)
        {
            if (visited.Contains(id)) return; Need(visiting.Add(id), "Skill-tree prerequisite cycle."); foreach (string parent in nodes[id].prerequisiteIds) VisitSkillNode(parent, nodes, visiting, visited); visiting.Remove(id); visited.Add(id);
        }
        private static void Need(bool valid, string message) { if (!valid) throw new ArgumentException(message); }
    }
}
