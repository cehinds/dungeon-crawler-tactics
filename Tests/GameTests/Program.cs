using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Text.Json;
using DungeonCrawlerTactics;

static class GameTests
{
    static readonly JsonSerializerOptions Json = new JsonSerializerOptions { IncludeFields = true };
    static Content Content;
    static GameData Data;
    static int checks;
    static void Check(bool value, string name) { if (!value) throw new Exception("FAILED: " + name); checks++; Console.WriteLine("PASS " + name); }
    static T Clone<T>(T value) { return JsonSerializer.Deserialize<T>(JsonSerializer.Serialize(value, Json), Json); }
    static GameSession Session() { return new GameSession(Clone(Content), Clone(Data)); }
    static GameView RawCommand(GameSession game, string type, string unit = null, string target = null, string ability = null, string item = null, int x = 0, int y = 0) { return game.Handle(new GameCommand { type = type, unitId = unit, targetId = target, abilityId = ability, itemId = item, x = x, y = y }); }
    static GameView Command(GameSession game, string type, string unit = null, string target = null, string ability = null, string item = null, int x = 0, int y = 0)
    {
        GameView view = RawCommand(game, type, unit, target, ability, item, x, y);
        if (type == "start" && view.screen == "explore") return EnterDoor(game);
        return view;
    }
    static GameView EndRound(GameSession game)
    {
        GameView view = game.GetView(); int round = view.round;
        for (int i = 0; i < Data.partySize && view.screen == "battle" && view.round == round; i++) view = RawCommand(game, "end_turn");
        return view;
    }
    static GameView EnterDoor(GameSession game)
    {
        GameView view = game.GetView(); int attempts = 0;
        while (view.screen == "explore" && attempts++ < 100)
        {
            ExplorationView map = view.exploration;
            ExplorationPointView door = map.points.FirstOrDefault(p => p.kind == "encounter" && p.canInteract);
            if (door != null) return RawCommand(game, "explore_interact", target: door.id);
            // Test driver explores nearest frontier in stable order; it cannot see hidden POIs.
            ExplorationTileView next = map.tiles.Where(t => t.reachable && !t.revealed).OrderBy(t => Math.Abs(t.x-map.x)+Math.Abs(t.y-map.y)).ThenBy(t => t.y).ThenBy(t => t.x).FirstOrDefault();
            if (next == null)
            {
                door = map.points.First(p => p.kind == "encounter");
                next = map.tiles.Where(t => t.reachable).OrderBy(t => Math.Abs(t.x-door.x)+Math.Abs(t.y-door.y)).First();
            }
            view = RawCommand(game, "explore_move", x: next.x, y: next.y);
        }
        throw new Exception("Exploration driver did not reach door: " + view.message);
    }
    static void Main()
    {
        Content = JsonSerializer.Deserialize<Content>(File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "combat-content.json")), Json);
        Data = JsonSerializer.Deserialize<GameData>(File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "game-content.json")), Json);
        GameDataValidator.Validate(Data, new Catalog(Content));
        Check(Content.classes.All(c => c.abilityIds.Length > 0), "all optional and identity classes have functional kits");
        Check(Content.items.Length == 10 && Content.abilities.Length >= 90, "release inventory and ability breadth");
        BranchingSkillTrees(); AuthoredMechanicsValidation(); CrawlerDevelopment(); IndependentActionsAndModes(); EnemyMovementRegression(); ProgressionAndEquipment(); RevampContracts(); Exploration(); ConfigurableParty(); PartyAndMovement(); PreviewItemsAndTags(); Saves(); BattleLayoutCompatibility(); TerrainAndDurations(); CompleteFloor(); DefeatRetry();
        Console.WriteLine(checks + " game checks passed.");
    }
    static GameView TreeCommand(GameSession game, string type, string owner = null, string node = null) { return game.Handle(new GameCommand { type = type, unitId = owner, nodeId = node }); }
    static void BranchingSkillTrees()
    {
        Check(Data.skillTrees.Length == 8 && Data.skillTrees.Sum(t => t.nodes.Length) == 48 && Data.skillTrees.All(t => t.nodes.Count(n => n.prerequisiteIds.Length == 0) == 2), "eight authored trees provide 48 nodes and two distinct branches each");
        Check(RejectsGameData(d => { d.skillTrees[0].nodes[0].prerequisiteIds = new[] { d.skillTrees[0].nodes[1].id }; d.skillTrees[0].nodes[1].level = 1; }), "runtime tree validation rejects prerequisite cycles");
        Check(RejectsGameData(d => d.skillTrees[0].nodes[0].abilityIds = new[] { "ability.unknown" }), "runtime tree validation rejects unknown granted ability");
        Check(RejectsGameData(d => d.skillTrees[0].nodes[1].prerequisiteIds = new[] { d.skillTrees[1].nodes[0].id }), "runtime tree validation rejects cross-character prerequisites");
        GameData config = Clone(Data); config.progression.xpThresholds = new[] { 0, 1, 2, 3 };
        for (int i = 0; i < config.encounters.Length; i++) { config.encounters[i].xp = 1; config.encounters[i].tiles = new TileDef[0]; config.encounters[i].enemies = new[] { new SpawnDef { id = "enemy.tree_fixture", label = "Tree opponent", classId = "class.brawler", x = 2, y = 1, hp = 100, energy = 0, move = 1 } }; }
        GameSession game = new GameSession(Clone(Content), config); GameView view = game.GetView();
        Check(view.skillTree.trees.All(t => t.unspentPoints == 1) && view.development.crawlers.All(c => c.unspentPoints == 0), "initial skill point is separate from manually allocated stat points");
        string original = JsonSerializer.Serialize(game.ExportSave(), Json);
        view = TreeCommand(game, "preview_skill_node", "crawler.carl", "skill.carl_a_1");
        Check(view.skillTree.canConfirm && view.skillTree.forecast.afterDamageBonus == view.skillTree.forecast.beforeDamageBonus + 1 && original == JsonSerializer.Serialize(game.ExportSave(), Json), "skill-node preview reports exact bonus without spending points or altering save");
        TreeCommand(game, "cancel_skill_node"); Check(original == JsonSerializer.Serialize(game.ExportSave(), Json), "canceling skill choice spends no points and grants no ability");
        view = TreeCommand(game, "preview_skill_node", "crawler.carl", "skill.carl_a_2"); Check(!view.skillTree.canConfirm && original == JsonSerializer.Serialize(game.ExportSave(), Json), "level gate and missing prerequisite reject without spending");
        view = TreeCommand(game, "preview_skill_node", "crawler.donut", "skill.carl_a_1"); Check(!view.skillTree.canConfirm && original == JsonSerializer.Serialize(game.ExportSave(), Json), "one crawler cannot spend points on another crawler's tree");
        TreeCommand(game, "preview_skill_node", "crawler.carl", "skill.carl_a_1"); view = TreeCommand(game, "confirm_skill_node");
        Check(view.skillTree.trees.Single(t => t.rosterId == "crawler.carl").unspentPoints == 0 && view.events.Any(e => e.type == "skill_node_learned" && e.tag == "skill.carl_a_1"), "confirmed root spends exactly one skill point and emits committed learning event");
        original = JsonSerializer.Serialize(game.ExportSave(), Json); view = TreeCommand(game, "preview_skill_node", "crawler.carl", "skill.carl_a_1");
        Check(!view.skillTree.canConfirm && original == JsonSerializer.Serialize(game.ExportSave(), Json), "learned node cannot be purchased twice");
        view = TreeCommand(game, "preview_skill_node", "crawler.carl", "skill.carl_b_1"); Check(!view.skillTree.canConfirm, "unspent skill-point limit prevents buying both roots initially");
        GameSession restored = new GameSession(Clone(Content), Clone(config)); Check(!restored.ImportSave(Clone(game.ExportSave())).message.StartsWith("Save rejected") && restored.GetView().skillTree.trees.Single(t => t.rosterId == "crawler.carl").unspentPoints == 0, "reload preserves learned node without duplicating skill points");
        GameSave oldSave = Clone(new GameSession(Clone(Content), Clone(config)).ExportSave()); oldSave.skillTree = null;
        Check(!restored.ImportSave(oldSave).message.StartsWith("Save rejected") && restored.GetView().skillTree.trees.All(t => t.unspentPoints == 1), "existing saves migrate to empty trees with one derived initial point");
        Command(game, "start"); view = Command(game, "preview", "crawler.carl", "enemy.tree_fixture", "ability.carl_powerful_strike"); int baseDamage = Content.abilities.Single(a => a.id == "ability.carl_powerful_strike").effects.Where(e => e.op == "Damage").Sum(e => e.amount);
        Check(view.forecast.Single(f => f.targetId == "enemy.tree_fixture").beforeHp - view.forecast.Single(f => f.targetId == "enemy.tree_fixture").afterHp == baseDamage + 1, "learned damage root changes actual shared-resolver forecast"); Command(game, "cancel");
        for (int room = 0; room < 2; room++)
        {
            GameSave wounded = Clone(game.ExportSave()); wounded.units.Single(u => u.id == "enemy.tree_fixture").hp = 1; game.ImportSave(wounded);
            Command(game, "preview", "crawler.carl", "enemy.tree_fixture", "ability.carl_powerful_strike"); view = Command(game, "confirm");
            game.Handle(new GameCommand { type = "choose_reward", rewardId = config.rewards[0].id }); Command(game, "continue");
            if (room == 0)
            {
                int beforeMove = game.GetView().roster.Single(r => r.id == "crawler.carl").move;
                TreeCommand(game, "preview_skill_node", "crawler.carl", "skill.carl_a_2"); view = TreeCommand(game, "confirm_skill_node");
                Check(view.roster.Single(r => r.id == "crawler.carl").move == beforeMove + 1 && view.skillTree.trees.Single(t => t.rosterId == "crawler.carl").unspentPoints == 0, "earned level adds one separate point and learned child changes real movement");
                Command(game, "safe_room_rest"); Command(game, "start");
            }
        }
        TreeCommand(game, "preview_skill_node", "crawler.carl", "skill.carl_a_3"); view = TreeCommand(game, "confirm_skill_node");
        Check(view.skillTree.trees.Single(t => t.rosterId == "crawler.carl").nodes.Single(n => n.id == "skill.carl_a_3").unlocked && view.skillTree.trees.Single(t => t.rosterId == "crawler.carl").unspentPoints == 0, "earned level-three capstone requires and preserves its complete branch");
        original = JsonSerializer.Serialize(game.ExportSave(), Json); GameSave forged = Clone(game.ExportSave()); forged.skillTree.unlockedIds = new[] { "skill.carl_a_3" };
        Check(game.ImportSave(forged).message.StartsWith("Save rejected") && original == JsonSerializer.Serialize(game.ExportSave(), Json), "forged capstone without parents rejects atomically");
        forged = Clone(game.ExportSave()); forged.skillTree.unlockedIds = forged.skillTree.unlockedIds.Concat(new[] { "skill.carl_b_1" }).ToArray();
        Check(game.ImportSave(forged).message.StartsWith("Save rejected") && original == JsonSerializer.Serialize(game.ExportSave(), Json), "forged overspent learned build rejects without replacing state");
        Command(game, "safe_room_rest"); view = Command(game, "start");
        Check(view.abilities.Any(a => a.id == "ability.carl_advanced_a" && a.targetIds.Contains("enemy.tree_fixture")) && view.units.Single(u => u.id == "crawler.carl").abilityIds.Contains("ability.carl_advanced_a"), "capstone grants a real usable targeted action while retaining personal kit");
        restored = new GameSession(Clone(Content), Clone(config)); Check(!restored.ImportSave(Clone(game.ExportSave())).message.StartsWith("Save rejected") && restored.GetView().abilities.Any(a => a.id == "ability.carl_advanced_a"), "battle reload reconstructs learned engine ability grants");
        view = Command(restored, "preview", "crawler.carl", "enemy.tree_fixture", "ability.carl_advanced_a"); ForecastView advanced = view.forecast.Single(f => f.targetId == "enemy.tree_fixture"); view = Command(restored, "confirm");
        Check(view.units.Single(u => u.id == "enemy.tree_fixture").hp == advanced.afterHp && view.units.Single(u => u.id == "enemy.tree_fixture").x == advanced.afterX && view.units.Single(u => u.id == "crawler.carl").acted, "new learned capstone commits exact resolver damage, push and action spending");
        GameSession protection = Session(); int oldMax = protection.GetView().roster.Single(r => r.id == "crawler.carl").maxHp;
        TreeCommand(protection, "preview_skill_node", "crawler.carl", "skill.carl_b_1"); view = TreeCommand(protection, "confirm_skill_node");
        Check(view.roster.Single(r => r.id == "crawler.carl").maxHp == oldMax + 4 && view.roster.Single(r => r.id == "crawler.carl").hp == oldMax, "HP tree node raises real cap without silently healing");
        TreeCommand(protection, "preview_skill_node", "crawler.donut", "skill.donut_b_1"); TreeCommand(protection, "confirm_skill_node"); Command(protection, "start"); GameSave injured = Clone(protection.ExportSave()); injured.units.Single(u => u.id == "crawler.mongo").hp -= 20; protection.ImportSave(injured);
        view = Command(protection, "preview", "crawler.donut", "crawler.mongo", "ability.donut_heal_critter"); ForecastView heal = view.forecast.Single(f => f.targetId == "crawler.mongo"); Check(heal.afterHp - heal.beforeHp == 11, "support branch healing bonus changes actual ability result");
        original = JsonSerializer.Serialize(protection.ExportSave(), Json); view = TreeCommand(protection, "preview_skill_node", "crawler.donut", "skill.donut_a_1"); Check(!view.skillTree.canConfirm && original == JsonSerializer.Serialize(protection.ExportSave(), Json), "learning a node outside safe room rejects without changing build");
        string enemyClass = Content.classes.First(c => !c.playerSelectable).id; GameSession camp = Session(); original = JsonSerializer.Serialize(camp.ExportSave(), Json); view = camp.Handle(new GameCommand { type = "set_class", unitId = "crawler.carl", classId = enemyClass });
        Check(!view.classes.Any(c => c.id == enemyClass) && original == JsonSerializer.Serialize(camp.ExportSave(), Json), "enemy-only class flag hides kits and rejects player selection atomically");
    }
    static bool RejectsGameData(Action<GameData> mutate)
    {
        GameData config = Clone(Data); mutate(config); try { new GameSession(Clone(Content), config); return false; } catch (ArgumentException) { return true; }
    }
    static void AuthoredMechanicsValidation()
    {
        Check(RejectsGameData(d => d.scenarios[0].bossId = "boss.unknown"), "runtime authored scenario rejects unknown boss reference");
        Check(RejectsGameData(d => d.scenarios[2].route[1].x = 0), "runtime authored scenario rejects noncardinal rolling route");
        Check(RejectsGameData(d => d.scenarios[0].encounter.playerSpawns[0].x = -1), "runtime authored scenario rejects out-of-bounds player spawn");
        Check(RejectsGameData(d =>  { d.scenarios[0].encounter.enemies[0].x = d.scenarios[0].encounter.playerSpawns[0].x; d.scenarios[0].encounter.enemies[0].y = d.scenarios[0].encounter.playerSpawns[0].y; }), "runtime authored scenario rejects overlapping boss and player spawn");
        Check(RejectsGameData(d => d.scenarios[0].kind = "scripted"), "runtime authored scenario rejects unknown mechanical kind");
        Check(RejectsGameData(d => d.scenarios[0].minionIds[0] = d.scenarios[0].bossId), "runtime authored scenario rejects boss as minion");
        Check(RejectsGameData(d => d.scenarios[0].route = null), "runtime authored scenario rejects null route collection");
        Check(RejectsGameData(d => d.scenarios[0].encounter.tiles = Enumerable.Range(0, d.scenarios[0].encounter.height).Select(y => new TileDef { x = 5, y = y, blocked = true }).ToArray()), "runtime authored scenario rejects wall-disconnected spawn regions");
        Check(RejectsGameData(d => { d.scenarios[0].interactables[0].x = d.scenarios[0].encounter.playerSpawns[0].x; d.scenarios[0].interactables[0].y = d.scenarios[0].encounter.playerSpawns[0].y; }), "runtime authored scenario rejects object and spawn overlap");
        Check(RejectsGameData(d => d.development.stats[0].id = "unstable"), "runtime stat definitions require stable dotted IDs");
        Check(RejectsGameData(d => d.development.practice.damagePerRank = 2), "runtime skill progression rejects excessive rank bonuses");
        Check(RejectsGameData(d => d.development.recipes[0].ingredients[0].itemId = "item.unknown"), "runtime crafting rejects unknown ingredient references");
    }
    static void CrawlerDevelopment()
    {
        GameData config = Clone(Data); Content content = Clone(Content);
        var practiceAbility = new AbilityDef { id = "ability.practice_fixture", label = "Practice Mend", target = "self", range = 0, cost = 2, effects = new[] { new EffectDef { op = "Heal", amount = 3 } } };
        content.abilities = content.abilities.Concat(new[] { practiceAbility }).ToArray(); config.roster.Single(r => r.id == "crawler.carl").innateAbilityIds = config.roster.Single(r => r.id == "crawler.carl").innateAbilityIds.Concat(new[] { practiceAbility.id }).ToArray();
        config.roster.Single(r => r.id == "crawler.katia").innateAbilityIds = config.roster.Single(r => r.id == "crawler.katia").innateAbilityIds.Concat(new[] { practiceAbility.id }).ToArray();
        config.encounters[0].tiles = new TileDef[0]; config.encounters[0].enemies = new[] { new SpawnDef { id = "enemy.development", label = "Training opponent", classId = "class.brawler", x = 2, y = 1, hp = 1, energy = 0, move = 1 } };
        config.encounters[1].tiles = new TileDef[0]; config.encounters[1].enemies = new[] { new SpawnDef { id = "enemy.practice", label = "Distant opponent", classId = "class.brawler", x = 8, y = 6, hp = 1000, energy = 0, move = 1 } };
        GameSession game = new GameSession(content, config); Command(game, "start"); Command(game, "preview", "crawler.carl", "enemy.development", "ability.carl_powerful_strike"); GameView view = Command(game, "confirm");
        Check(view.development.crawlers.All(c => c.unspentPoints == 3) && view.development.lootBoxes.Any(b => b.sourceId == "victory." + config.encounters[0].id), "earned level gives every crawler three manual points and one owned victory box");
        Command(game, "choose_reward", target: null); game.Handle(new GameCommand { type = "choose_reward", rewardId = config.rewards[0].id }); view = Command(game, "continue");
        Check(view.screen == "camp", "development station is reached through actual victory reward and continue");
        GameSave legacy = Clone(game.ExportSave()); legacy.development = null; GameSession migrated = new GameSession(Clone(content), Clone(config));
        Check(!migrated.ImportSave(legacy).message.StartsWith("Save rejected") && migrated.GetView().development.crawlers.All(c => c.unspentPoints == 3), "old checkpoints retain caps and receive derived unspent points without reinterpreting stats");
        string unchanged = JsonSerializer.Serialize(game.ExportSave(), Json);
        view = game.Handle(new GameCommand { type = "preview_allocate", unitId = "crawler.carl", statId = "stat.constitution", points = 1 });
        Check(view.development.canConfirm && view.development.forecast.afterHp == view.development.forecast.beforeHp + 3 && unchanged == JsonSerializer.Serialize(game.ExportSave(), Json), "allocation exact forecast changes no committed stats or point pool");
        Command(game, "cancel_development"); Check(unchanged == JsonSerializer.Serialize(game.ExportSave(), Json), "cancel allocation spends no points");
        foreach (var choice in new[] { new { owner = "crawler.carl", stat = "stat.strength", points = 2 }, new { owner = "crawler.carl", stat = "stat.constitution", points = 1 }, new { owner = "crawler.donut", stat = "stat.dexterity", points = 3 }, new { owner = "crawler.katia", stat = "stat.intelligence", points = 2 }, new { owner = "crawler.katia", stat = "stat.charisma", points = 1 } })
        { game.Handle(new GameCommand { type = "preview_allocate", unitId = choice.owner, statId = choice.stat, points = choice.points }); view = Command(game, "confirm_development"); }
        Check(view.development.crawlers.Where(c => c.unitId == "crawler.carl" || c.unitId == "crawler.donut" || c.unitId == "crawler.katia").All(c => c.unspentPoints == 0), "all five stat formulas consume only their owner's earned points");
        unchanged = JsonSerializer.Serialize(game.ExportSave(), Json); game.Handle(new GameCommand { type = "preview_allocate", unitId = "crawler.carl", statId = "stat.strength", points = 1 });
        Check(unchanged == JsonSerializer.Serialize(game.ExportSave(), Json), "overspending allocation rejects atomically");
        view = game.GetView();
        Check(view.roster.Single(r => r.id == "crawler.donut").move == config.classStats.Single(c => c.classId == view.roster.Single(r => r.id == "crawler.donut").classId).move + 1 && view.roster.Single(r => r.id == "crawler.katia").maxEnergy == config.classStats.Single(c => c.classId == view.roster.Single(r => r.id == "crawler.katia").classId).energy + config.progression.manaPerLevel + 4, "Dexterity and Intelligence change real movement and mana caps");
        GameSession restored = new GameSession(Clone(content), Clone(config)); Check(!restored.ImportSave(Clone(game.ExportSave())).message.StartsWith("Save rejected"), "all allocations and effective stats roundtrip through validated checkpoint");
        GameSave forged = Clone(game.ExportSave()); forged.development.allocated[0].points = 99;
        Check(restored.ImportSave(forged).message.StartsWith("Save rejected"), "forged unearned stat points reject before replacing session");
        GameSave badBox = Clone(game.ExportSave()); badBox.development.lootBoxes[0].sourceId = "victory.unearned"; string restoredBefore = JsonSerializer.Serialize(restored.ExportSave(), Json);
        Check(restored.ImportSave(badBox).message.StartsWith("Save rejected") && restoredBefore == JsonSerializer.Serialize(restored.ExportSave(), Json), "unearned loot source rejects without replacing inventory or allocations");
        string boxId = view.development.lootBoxes.First().id; int tonicBefore = game.ExportSave().inventory.Single(i => i.itemId == "item.health_tonic").count;
        view = game.Handle(new GameCommand { type = "open_loot_box", lootBoxId = boxId }); int tonicAfter = game.ExportSave().inventory.Single(i => i.itemId == "item.health_tonic").count;
        Check(view.development.lootBoxes.Single(b => b.id == boxId).opened && tonicAfter == tonicBefore + 1, "owned deterministic box opens once into actual inventory");
        unchanged = JsonSerializer.Serialize(game.ExportSave(), Json); game.Handle(new GameCommand { type = "open_loot_box", lootBoxId = boxId }); Check(unchanged == JsonSerializer.Serialize(game.ExportSave(), Json), "opened loot box cannot duplicate supplies");
        int beforeTonics = tonicAfter, beforeMega = game.ExportSave().inventory.Single(i => i.itemId == "item.mega_tonic").count;
        view = game.Handle(new GameCommand { type = "craft", recipeId = "recipe.mega_tonic" });
        Check(game.ExportSave().inventory.Single(i => i.itemId == "item.health_tonic").count == beforeTonics - 2 && game.ExportSave().inventory.Single(i => i.itemId == "item.mega_tonic").count == beforeMega + 1, "recipe atomically consumes exact materials and grants authored output");
        while (game.ExportSave().inventory.Single(i => i.itemId == "item.health_tonic").count >= 2) game.Handle(new GameCommand { type = "craft", recipeId = "recipe.mega_tonic" });
        unchanged = JsonSerializer.Serialize(game.ExportSave(), Json); game.Handle(new GameCommand { type = "craft", recipeId = "recipe.mega_tonic" }); Check(unchanged == JsonSerializer.Serialize(game.ExportSave(), Json), "missing crafting ingredients reject with no partial consume or reward");
        game.Handle(new GameCommand { type = "preview_allocate", unitId = "crawler.mongo", statId = "stat.constitution", points = 1 });
        view = game.Handle(new GameCommand { type = "set_class", unitId = "crawler.mongo", classId = game.GetView().roster.Single(r => r.id == "crawler.mongo").classId });
        Check(!view.development.canConfirm && view.development.forecast == null, "loadout changes invalidate pending stat forecasts");
        Command(game, "safe_room_rest"); Command(game, "start"); GameSave wounded = Clone(game.ExportSave()); wounded.units.Single(u => u.id == "crawler.carl").hp -= 25; wounded.units.Single(u => u.id == "crawler.katia").hp -= 10; game.ImportSave(wounded);
        view = Command(game, "preview", "crawler.katia", "crawler.katia", practiceAbility.id); ForecastView charismaHeal = view.forecast.Single(f => f.targetId == "crawler.katia");
        Check(charismaHeal.afterHp - charismaHeal.beforeHp == 4, "allocated Charisma increases actual shared-resolver healing"); Command(game, "cancel");
        Command(game, "select", "crawler.carl"); unchanged = JsonSerializer.Serialize(game.ExportSave(), Json); Command(game, "preview", "crawler.carl", "crawler.carl", practiceAbility.id); Command(game, "cancel"); Check(unchanged == JsonSerializer.Serialize(game.ExportSave(), Json), "canceled skill use grants no practice or loot");
        for (int i = 0; i < 3; i++) { Command(game, "select", "crawler.carl"); Command(game, "preview", "crawler.carl", "crawler.carl", practiceAbility.id); view = Command(game, "confirm"); if (i < 2) EndRound(game); }
        SkillPracticeView practice = view.development.practice.Single(p => p.unitId == "crawler.carl" && p.abilityId == practiceAbility.id);
        Check(practice.uses == 3 && practice.rank == 2 && practice.damageBonus == 0 && practice.healBonus == 1 && practice.costReduction == 1, "only committed uses advance their own bounded skill rank");
        EndRound(game); view = Command(game, "select", "crawler.carl"); Check(view.abilities.Single(a => a.id == practiceAbility.id).cost == 1, "practice changes real displayed and resolved mana cost");
        Check(view.abilities.Single(a => a.id == practiceAbility.id).description.Contains("Restore 4 HP"), "selected ability tooltip includes earned practice bonuses");
        view = Command(game, "preview", "crawler.carl", "crawler.carl", practiceAbility.id); ForecastView healing = view.forecast.Single(f => f.targetId == "crawler.carl");
        Check(healing.afterHp - healing.beforeHp == 4 && healing.beforeEnergy - healing.afterEnergy == 1, "shared resolver forecasts practiced healing and mana discount exactly");
        Command(game, "cancel"); GameSave practiceSave = Clone(game.ExportSave()); restored = new GameSession(Clone(content), Clone(config));
        Check(!restored.ImportSave(practiceSave).message.StartsWith("Save rejected") && restored.GetView().development.practice.Single(p => p.unitId == "crawler.carl" && p.abilityId == practiceAbility.id).uses == 3, "practice, allocation, opened boxes and crafting supplies persist on reload");
        practiceSave.units.Single(u => u.id == "enemy.practice").x = 2; practiceSave.units.Single(u => u.id == "enemy.practice").y = 1;
        game.ImportSave(practiceSave); view = Command(game, "preview", "crawler.carl", "enemy.practice", "ability.carl_powerful_strike");
        int rawDamage = content.abilities.Single(a => a.id == "ability.carl_powerful_strike").effects.Where(e => e.op == "Damage").Sum(e => e.amount);
        ForecastView damage = view.forecast.Single(f => f.targetId == "enemy.practice"); Check(damage.beforeHp - damage.afterHp == rawDamage + 1, "allocated Strength changes actual direct ability damage in shared forecast");
        unchanged = JsonSerializer.Serialize(game.ExportSave(), Json); game.Handle(new GameCommand { type = "craft", recipeId = "recipe.fire_bomb" }); Check(unchanged == JsonSerializer.Serialize(game.ExportSave(), Json), "crafting outside safe room rejects atomically");
    }
    static void IndependentActionsAndModes()
    {
        GameSession game = Session(); GameView view = Command(game, "start");
        string katia = Data.forms[0].rosterId;
        view = Command(game, "select", katia); string before = JsonSerializer.Serialize(game.ExportSave(), Json);
        Check(view.forms.Single(f => f.id == "form.baseline").selected && !view.forms.Single(f => f.id == "form.baseline").enabled, "implicit baseline mode is selected and disabled");
        view = game.Handle(new GameCommand { type = "preview", unitId = katia, formId = "form.baseline" });
        Check(!view.canConfirm && JsonSerializer.Serialize(game.ExportSave(), Json) == before, "preview rejects unchanged baseline without spending or mutating save");
        view = game.Handle(new GameCommand { type = "preview", unitId = katia, formId = "form.strider" });
        Check(view.canConfirm && JsonSerializer.Serialize(game.ExportSave(), Json) == before && view.forecast.Single().afterMove == view.forecast.Single().beforeMove + 1, "form forecast reports movement tradeoff without mutating save");
        view = Command(game, "confirm"); UnitView unit = view.units.Single(u => u.id == katia);
        Check(unit.acted && !unit.moved && !unit.finished && view.canMove && !view.canAct && view.selectedUnitId == katia && unit.formId == "form.strider", "form spends action while retaining movement and current actor");
        CellView cell = view.reachable.First(c => c.cost > 0); view = Command(game, "move", katia, x: cell.x, y: cell.y);
        Check(view.units.Single(u => u.id == katia).moved && view.phase == "player" && view.selectedUnitId == katia, "action then move waits for explicit end turn");
        GameSession loaded = Session();
        Check(!loaded.ImportSave(Clone(game.ExportSave())).message.StartsWith("Save rejected") && loaded.GetView().units.Single(u => u.id == katia).formId == "form.strider", "form stats and independent activation survive save validation");
        Check(view.achievementIds.Contains("achievement.first_form") && view.achievementIds.Contains("achievement.first_move"), "committed form and movement award persistent achievement IDs");
        view = loaded.GetView(); Check(view.achievementIds.Contains("achievement.first_form") && !view.events.Any(e => e.type == "achievement"), "restoring achievement ledger does not announce unlock again");
        view = Command(game, "end_turn", katia);
        Check(view.selectedUnitId != katia && view.units.Single(u => u.id == katia).finished, "explicit end turn advances after both resources spent");
        view = Command(game, "select", view.selectedUnitId); string actor = view.selectedUnitId;
        view = game.Handle(new GameCommand { type = "preview", unitId = actor, stanceId = "stance.defensive" }); view = Command(game, "confirm");
        Check(view.units.Single(u => u.id == actor).stanceId == "stance.defensive" && view.stances.Length == 3, "all characters expose real persistent tactical stances");
        Check(view.units.Single(u => u.id == actor).tags.Contains("status.guarded") && game.ExportSave().timedTags.Any(t => t.entityId == actor && t.tag == "status.guarded"), "defensive stance grants existing real single-hit protection with timed bookkeeping");
        Check(!Session().ImportSave(Clone(game.ExportSave())).message.StartsWith("Save rejected") && game.ExportSave().timedTags.Any(t => t.entityId == actor && t.source == "stance.defensive"), "guarded stance checkpoint roundtrips with authored source ID");
        GameSession bulwarkGame = Session(); Command(bulwarkGame, "start");
        bulwarkGame.Handle(new GameCommand { type = "preview", unitId = katia, formId = "form.bulwark" }); Command(bulwarkGame, "confirm");
        GameSave bulwarkSave = Clone(bulwarkGame.ExportSave()); GameSession bulwarkLoaded = Session();
        Check(!bulwarkLoaded.ImportSave(bulwarkSave).message.StartsWith("Save rejected") && bulwarkLoaded.GetView().units.Single(u => u.id == katia).tags.Contains("status.guarded") && bulwarkSave.timedTags.Any(t => t.entityId == katia && t.source == "form.bulwark"), "guarded Bulwark form restores exact stats, protection and valid form source");
        GameSave forged = Clone(game.ExportSave()); forged.roster.Single(r => r.id == actor).formId = "form.bulwark";
        Check(loaded.ImportSave(forged).message.StartsWith("Save rejected"), "nonowner cannot forge a shapeshift form in save");
        GameSession itemGame = Session(); view = Command(itemGame, "start"); string itemActor = view.selectedUnitId;
        ItemView supply = view.items.First(i => i.count > 0 && i.targetIds.Contains(itemActor));
        view = Command(itemGame, "preview", itemActor, itemActor, item: supply.id); view = Command(itemGame, "confirm");
        Check(view.canMove && !view.canAct && !view.units.Single(u => u.id == itemActor).finished, "consumable spends action independently of movement and end turn");
        GameSave badLedger = Clone(game.ExportSave()); badLedger.achievementIds = new[] { "achievement.forged" };
        Check(loaded.ImportSave(badLedger).message.StartsWith("Save rejected"), "unknown achievement save rejects atomically");
        view = Command(game, "new_run"); Check(view.achievementIds.Length == 0, "new run resets achievement ledger");
    }
    static void EnemyMovementRegression()
    {
        GameData config = Clone(Data); config.encounters[0].tiles = new TileDef[0];
        config.encounters[0].enemies = new[] { new SpawnDef { id = "enemy.mover", label = "Mover", classId = "class.brawler", x = 8, y = 1, hp = 200, energy = 20, move = 3 } };
        GameSession game = new GameSession(Clone(Content), config); Command(game, "start");
        GameView view = EndRound(game); UnitView enemy = view.units.Single(u => u.id == "enemy.mover");
        Check(enemy.x < 8 && view.events.Any(e => e.type == "move" && e.actorId == "enemy.mover") && view.events.First(e => e.type == "phase").tag == "enemy", "enemy outside attack range advances after all four crawler activations and emits ordered movement");
        view = EndRound(game);
        Check(view.events.Any(e => e.type == "attack" && e.actorId == "enemy.mover") && view.events.Where(e => e.type == "move").All(e => e.actorId == "enemy.mover"), "enemy attacks after approaching and events retain enemy actor IDs");
        config.encounters[0].enemies[0].x = 2; game = new GameSession(Clone(Content), config); Command(game, "start"); view = EndRound(game);
        Check(view.events.Any(e => e.type == "attack" && e.actorId == "enemy.mover") && !view.events.Any(e => e.type == "move" && e.actorId == "enemy.mover"), "enemy already in range attacks in place rather than taking an unnecessary move");
        config.encounters[0].playerSpawns = new[] { new CellView { x = 5, y = 1 }, new CellView { x = 6, y = 1 }, new CellView { x = 7, y = 1 }, new CellView { x = 8, y = 1 } };
        config.encounters[0].tiles = Enumerable.Range(0, 6).Select(y => new TileDef { x = 3, y = y, blocked = true }).ToArray();
        config.encounters[0].enemies[0].x = 2; config.encounters[0].enemies[0].y = 1; config.encounters[0].enemies[0].move = 2;
        game = new GameSession(Clone(Content), config); Command(game, "start"); view = EndRound(game); enemy = view.units.Single(u => u.id == "enemy.mover");
        Check(enemy.y > 1 && view.events.Any(e => e.type == "move" && e.actorId == "enemy.mover"), "enemy takes a wall detour that initially increases Manhattan distance");
    }
    static GameView GearCommand(GameSession game, string type, string unit, string gear) { return game.Handle(new GameCommand { type = type, unitId = unit, equipmentId = gear }); }
    static void ProgressionAndEquipment()
    {
        GameData config = Clone(Data); config.progression = new ProgressionDef { xpThresholds = new[] { 0, 30, 60, 90 }, hpPerLevel = 3, manaPerLevel = 2, movePerLevel = 1,
            skillUnlocks = new[] { new SkillUnlockDef { id = "skill.fixture_healing", label = "Healing", rosterId = "crawler.carl", abilityId = "ability.mend", level = 2 } } };
        config.equipment = new[] {
            new EquipmentDef { id = "equipment.fixture_vest", label = "Vest", slot = "armor", hpBonus = 10 },
            new EquipmentDef { id = "equipment.fixture_focus", label = "Focus", slot = "charm", manaBonus = 4, abilityIds = new[] { "ability.spark" } },
            new EquipmentDef { id = "equipment.fixture_boots", label = "Boots", slot = "charm", moveBonus = 1 },
            new EquipmentDef { id = "equipment.fixture_reward", label = "Prize", slot = "weapon", unlockEncounter = 1, abilityIds = new[] { "ability.shatter" } }
        };
        config.encounters[0].xp = 30; config.encounters[0].tiles = new TileDef[0];
        config.encounters[0].enemies = new[] { new SpawnDef { id = "enemy.fixture", label = "Fixture", classId = "class.brawler", x = 2, y = 1, hp = 1, energy = 0, move = 1 } };
        GameSession game = new GameSession(Clone(Content), config); GameView view = game.GetView();
        int basicHp = view.roster.Single(r => r.id == "crawler.carl").maxHp, basicMana = view.roster.Single(r => r.id == "crawler.carl").maxEnergy;
        Check(view.progression.level == 1 && view.progression.xpToNextLevel == 30 && view.safeRoom.available, "shared party progression begins at exact authored threshold and safe room is available");
        GearCommand(game, "equip", "crawler.carl", "equipment.fixture_vest"); view = GearCommand(game, "equip", "crawler.carl", "equipment.fixture_focus");
        Check(view.roster.Single(r => r.id == "crawler.carl").maxHp == basicHp + 10 && view.roster.Single(r => r.id == "crawler.carl").maxEnergy == basicMana + 4, "equipped armor and charm change real roster HP and mana caps");
        string equippedSave = JsonSerializer.Serialize(game.ExportSave(), Json);
        view = GearCommand(game, "equip", "crawler.donut", "equipment.fixture_vest");
        Check(view.message.Contains("another") && equippedSave == JsonSerializer.Serialize(game.ExportSave(), Json), "single-copy equipment cannot be duplicated across characters");
        view = GearCommand(game, "equip", "crawler.carl", "equipment.fixture_reward");
        Check(view.message.Contains("earned") && equippedSave == JsonSerializer.Serialize(game.ExportSave(), Json), "unearned gear rejects atomically");
        view = Command(game, "safe_room_rest"); Check(view.safeRoom.rested && view.roster.Single(r => r.id == "crawler.carl").hp == basicHp + 10, "safe-room rest fills equipped HP and mana maxima");
        GameSession restored = new GameSession(Clone(Content), Clone(config));
        Check(!restored.ImportSave(Clone(game.ExportSave())).message.StartsWith("Save rejected") && restored.GetView().equipment.Single(e => e.id == "equipment.fixture_focus").equippedUnitId == "crawler.carl", "equipment and modified stats survive validated save roundtrip");
        view = Command(game, "start");
        Check(view.abilities.Any(a => a.id == "ability.spark") && !view.abilities.Any(a => a.id == "ability.mend"), "equipped ability works in combat while future skill remains locked");
        string battleSave = JsonSerializer.Serialize(game.ExportSave(), Json);
        view = GearCommand(game, "unequip", "crawler.carl", "equipment.fixture_focus");
        Check(view.message.Contains("safe room") && battleSave == JsonSerializer.Serialize(game.ExportSave(), Json), "equipment cannot change during battle");
        GameSave wounded = Clone(game.ExportSave()); SavedUnit actor = wounded.units.Single(u => u.id == "crawler.carl"); actor.hp -= 12; actor.energy = 3; game.ImportSave(wounded);
        view = Command(game, "preview", "crawler.carl", "enemy.fixture", "ability.carl_powerful_strike");
        string beforeCancel = JsonSerializer.Serialize(game.ExportSave(), Json); Command(game, "cancel");
        Check(beforeCancel == JsonSerializer.Serialize(game.ExportSave(), Json) && game.GetView().progression.level == 1, "canceling forecast changes no XP, gear or skill unlock state");
        Command(game, "preview", "crawler.carl", "enemy.fixture", "ability.carl_powerful_strike"); view = Command(game, "confirm");
        Check(view.screen == "victory" && view.progression.level == 2 && view.xp == 30 && view.progression.xpIntoLevel == 0 && view.events.Any(e => e.type == "level_up"), "victory awards exact threshold level-up once with ordered event");
        Check(view.units.Single(u => u.id == "crawler.carl").maxHp == basicHp + 13 && view.units.Single(u => u.id == "crawler.carl").maxEnergy == basicMana + 6 && view.progression.skills.Single().unlocked, "level growth changes real HP, mana and skill grant state");
        Check(view.equipment.Single(e => e.id == "equipment.fixture_reward").owned && view.events.Any(e => e.type == "equipment_unlock") && view.quests.Single(q => q.id == "quest.floor").progress == 1 && view.quests.Single(q => q.id == "quest.encounter").complete, "gear rewards and quest objectives derive from actual victory and enemy state");
        GameSave victory = Clone(game.ExportSave()); restored = new GameSession(Clone(Content), Clone(config));
        Check(!restored.ImportSave(victory).message.StartsWith("Save rejected") && restored.GetView().progression.level == 2, "leveled checkpoint saves actual modified stats");
        GameSave v2 = Clone(victory); v2.contentVersion = "floor-one-2.0.0"; v2.progressionVersion = 0; v2.equipped = new EquipmentSlotSave[0];
        foreach (RosterView member in v2.roster)
        {
            RosterDef definition = config.roster.Single(r => r.id == member.id); if (!string.IsNullOrEmpty(definition.legacyClassId)) member.classId = definition.legacyClassId;
            ClassStats oldStats = config.classStats.Single(c => c.classId == member.classId); member.hp = member.hp == 0 ? 0 : Math.Max(1, (int)((long)member.hp * oldStats.hp / member.maxHp)); member.maxHp = oldStats.hp; member.energy = member.maxEnergy = 0;
        }
        foreach (SavedUnit old in v2.units.Where(u => u.team == "player"))
        {
            old.classId = v2.roster.Single(r => r.id == old.id).classId; ClassStats oldStats = config.classStats.Single(c => c.classId == old.classId);
            old.hp = old.hp == 0 ? 0 : Math.Max(1, (int)((long)old.hp * oldStats.hp / old.maxHp)); old.maxHp = oldStats.hp; old.energy = Math.Min(old.energy, oldStats.energy); old.maxEnergy = oldStats.energy; old.move = oldStats.move;
        }
        string oldFile = JsonSerializer.Serialize(v2, Json); GameSession upgraded = new GameSession(Clone(Content), Clone(config)); GameView upgradedView = upgraded.ImportSave(v2);
        Check(!upgradedView.message.StartsWith("Save rejected") && upgradedView.progression.level == 2 && upgradedView.units.Single(u => u.id == "crawler.carl").maxHp == basicHp + 3 && upgraded.ExportSave().progressionVersion == 1, "existing floor-one-2 checkpoint upgrades base stats to earned progression without requiring new gear fields");
        Check(oldFile == JsonSerializer.Serialize(v2, Json), "progression migration preserves original v2 save object");
        GameSave forgedProgression = Clone(victory); forgedProgression.progressionVersion = 99;
        Check(restored.ImportSave(forgedProgression).message.StartsWith("Save rejected"), "unknown progression versions reject");
        game.Handle(new GameCommand { type = "choose_reward", rewardId = view.rewards[0].id }); view = Command(game, "continue");
        Check(view.safeRoom.available && !view.safeRoom.rested && view.roster.Single(r => r.id == "crawler.carl").hp < view.roster.Single(r => r.id == "crawler.carl").maxHp, "return to safe room preserves battle wounds until actual rest");
        view = Command(game, "safe_room_rest"); Check(view.safeRoom.rested && view.roster.Single(r => r.id == "crawler.carl").energy == basicMana + 6, "rest restores HP and mana after victory");
        GearCommand(game, "equip", "crawler.carl", "equipment.fixture_boots"); view = game.GetView();
        Check(view.equipment.Single(e => e.id == "equipment.fixture_focus").equippedUnitId == null && view.roster.Single(r => r.id == "crawler.carl").move == Data.classStats.Single(c => c.classId == view.roster.Single(r => r.id == "crawler.carl").classId).move + 2, "same-slot replacement returns old gear and applies real movement bonus");
        GearCommand(game, "unequip", "crawler.carl", "equipment.fixture_boots"); view = Command(game, "start");
        Check(view.abilities.Any(a => a.id == "ability.mend") && !view.abilities.Any(a => a.id == "ability.spark"), "earned skill persists while unequipped ability is removed");
        GameSave invalid = Clone(game.ExportSave()); invalid.equipped = new[] { new EquipmentSlotSave { unitId = "crawler.carl", equipmentId = "equipment.fixture_vest" }, new EquipmentSlotSave { unitId = "crawler.donut", equipmentId = "equipment.fixture_vest" } };
        string stable = JsonSerializer.Serialize(game.ExportSave(), Json);
        Check(game.ImportSave(invalid).message.StartsWith("Save rejected") && stable == JsonSerializer.Serialize(game.ExportSave(), Json), "forged duplicate equipment save rejects without replacing session");
    }
    static void RevampContracts()
    {
        GameSession game = Session(); GameView view = Command(game, "start");
        string[] order = Data.roster.Where(r => r.selected).Select(r => r.id).ToArray();
        Check(view.partyOrder.SequenceEqual(order) && view.selectedUnitId == order[0], "party order and initial selection use authored roster order");
        for (int i = 0; i < order.Length - 1; i++)
        {
            view = RawCommand(game, "end_turn");
            Check(view.round == 1 && view.selectedUnitId == order[i + 1] && view.units.Single(u => u.id == order[i]).acted && !view.events.Any(ev => ev.type == "phase"), "end turn spends only current character and selects next ready");
        }
        view = RawCommand(game, "end_turn");
        Check(view.round == 2 && view.events.Count(ev => ev.type == "phase") == 2 && view.events.First(ev => ev.type == "phase").tag == "enemy" && view.events.Last(ev => ev.type == "phase").tag == "player", "enemy phase starts only after last party activation");
        Check(view.events.Select(ev => ev.sequence).SequenceEqual(Enumerable.Range(0, view.events.Length)), "presentation events have contiguous deterministic order");
        Check(RawCommand(game, "cancel").events.Length == 0, "events are scoped to one dispatch");
        GameSession identities = Session(); GameView identityView = Command(identities, "start");
        Check(identityView.units.Where(u => u.team == "player").Select(u => u.classId).Distinct().Count() == 4 && identityView.units.Single(u => u.id == "crawler.carl").maxHp != identityView.units.Single(u => u.id == "crawler.donut").maxHp, "default crawlers expose distinct identity classes and stats");
        identityView = RawCommand(identities, "select", "crawler.katia");
        Check(!identityView.abilities.Any(a => a.id == "ability.firebolt") && identityView.abilities.Any(a => a.id == "ability.katia_shapeshift"), "default Katia has doppelganger kit without pyromancer firebolt");
        AbilityDef missile = Content.abilities.Single(a => a.id == "ability.donut_magic_missile");
        Check(missile.incomingTags.Contains("element.arcane") && !missile.incomingTags.Contains("element.lightning"), "Donut Magic Missile is arcane rather than lightning");

        Content fixture = Clone(Content);
        fixture.abilities = fixture.abilities.Concat(new[] {
            new AbilityDef { id = "ability.fixture_jump", label = "Jump", target = "tile", range = 4, cost = 1, effects = new[] { new EffectDef { op = "Teleport" } } },
            new AbilityDef { id = "ability.fixture_push", label = "Push", target = "enemy", range = 2, cost = 1, effects = new[] { new EffectDef { op = "Damage", amount = 2 }, new EffectDef { op = "Push", amount = 3 } } }
        }).ToArray();
        GameData config = Clone(Data); RosterDef hero = config.roster.First(r => r.selected); hero.artId = "art.fixture";
        hero.innateAbilityIds = new[] { "ability.fixture_jump", "ability.fixture_push" };
        EncounterDef room = config.encounters[0];
        room.playerSpawns = new[] { new CellView { x = 1, y = 1 }, new CellView { x = 1, y = 3 }, new CellView { x = 1, y = 5 }, new CellView { x = 2, y = 3 } };
        room.tiles = new[] { new TileDef { x = 4, y = 1, tags = new[] { "surface.water" } }, new TileDef { x = 5, y = 1, tags = new[] { "surface.burning" } }, new TileDef { x = 6, y = 1, blocked = true }, new TileDef { x = 4, y = 2, blocked = true } };
        room.enemies = new[] { new SpawnDef { id = "enemy.fixture", label = "Fixture", artId = "art.guard", classId = "class.brawler", x = 3, y = 1, hp = 100, energy = 0, move = 1 } };
        game = new GameSession(Clone(fixture), Clone(config)); view = Command(game, "start");
        Check(view.abilities.Any(a => a.id == "ability.fixture_jump") && view.units.Single(u => u.id == hero.id).artId == "art.fixture", "character art and innate grants survive class presentation");
        string before = JsonSerializer.Serialize(game.ExportSave(), Json);
        view = RawCommand(game, "preview", hero.id, "tile.4.2", "ability.fixture_jump");
        Check(!view.canConfirm && before == JsonSerializer.Serialize(game.ExportSave(), Json), "teleport rejects authored walls without state changes");
        view = RawCommand(game, "preview", hero.id, "tile.1.3", "ability.fixture_jump");
        Check(!view.canConfirm, "teleport rejects occupied destination");
        view = RawCommand(game, "preview", hero.id, "tile.4.1", "ability.fixture_jump");
        string previewEvents = string.Join("|", view.events.Select(ev => ev.type + ":" + ev.targetId + ":" + ev.tag + ":" + ev.toX + ":" + ev.toY));
        Check(view.canConfirm && view.events.All(ev => ev.preview) && before == JsonSerializer.Serialize(game.ExportSave(), Json) && view.forecast.Any(f => f.targetId == hero.id && f.afterX == 4 && f.afterY == 1), "teleport preview reports position events and leaves save untouched");
        view = RawCommand(game, "confirm"); UnitView jumped = view.units.Single(u => u.id == hero.id);
        Check(jumped.x == 4 && jumped.y == 1 && jumped.tags.Contains("status.wet") && jumped.statuses.Any(t => t.tag == "status.wet" && t.remainingRounds == 3) && view.events.All(ev => !ev.preview), "teleport commits position and terrain status with duration");
        Check(previewEvents == string.Join("|", view.events.Where(ev => ev.type != "skill_practice").Select(ev => ev.type + ":" + ev.targetId + ":" + ev.tag + ":" + ev.toX + ":" + ev.toY)), "preview and committed combat event sequence agree");
        game = new GameSession(Clone(fixture), Clone(config)); Command(game, "start");
        view = RawCommand(game, "preview", hero.id, "enemy.fixture", "ability.fixture_push");
        Check(view.canConfirm && view.forecast.Any(f => f.targetId == "enemy.fixture" && f.afterX == 5 && f.afterHp == 94), "push preview includes bounded path and entry hazard damage");
        view = RawCommand(game, "confirm");
        Check(view.events.Where(ev => ev.type == "push").Select(ev => ev.toX).SequenceEqual(new[] { 4, 5 }) && view.events.Any(ev => ev.type == "damage" && ev.tag == "surface.burning" && ev.amount == 4), "push emits each traversed step and stops at wall");
        GameSession restored = new GameSession(Clone(fixture), Clone(config));
        Check(!restored.ImportSave(Clone(game.ExportSave())).message.StartsWith("Save rejected"), "positional ability state survives validated save roundtrip");
        GameData occupiedPush = Clone(config); occupiedPush.encounters[0].playerSpawns[1] = new CellView { x = 4, y = 1 };
        game = new GameSession(Clone(fixture), occupiedPush); Command(game, "start");
        view = RawCommand(game, "preview", hero.id, "enemy.fixture", "ability.fixture_push");
        Check(view.canConfirm && !view.events.Any(ev => ev.type == "push") && view.forecast.Single(f => f.targetId == "enemy.fixture").afterHp == 98, "push stops before living occupant while preserving attack damage");
        GameData lethalPush = Clone(config); lethalPush.encounters[0].enemies[0].hp = 5;
        game = new GameSession(Clone(fixture), lethalPush); Command(game, "start");
        view = RawCommand(game, "preview", hero.id, "enemy.fixture", "ability.fixture_push");
        Check(view.canConfirm && view.forecast.Single(f => f.targetId == "enemy.fixture").afterHp == 0 && view.events.Count(ev => ev.type == "push") == 2, "lethal pushed terrain damage stops traversal deterministically");
        game = new GameSession(Clone(fixture), Clone(config));
        game.Handle(new GameCommand { type = "set_class", unitId = hero.id, classId = "class.ranger" }); Command(game, "start");
        Check(game.GetView().abilities.Any(a => a.id == "ability.fixture_jump"), "changing optional class preserves innate abilities");

        GameData legacyData = Clone(Data); legacyData.home = null; legacyData.skillTrees = new SkillTreeDef[0]; legacyData.contentVersion = "fixture-legacy"; legacyData.compatibleContentVersions = new string[0];
        legacyData.roster = legacyData.roster.Where(r => string.IsNullOrEmpty(r.replacesId)).ToArray();
        legacyData.progression.skillUnlocks = legacyData.progression.skillUnlocks.Where(s => legacyData.roster.Any(r => r.id == s.rosterId)).ToArray();
        foreach (RosterDef member in legacyData.roster) if (!string.IsNullOrEmpty(member.legacyClassId)) member.classId = member.legacyClassId;
        RosterDef advisor = legacyData.roster.First(r => !r.deployable); advisor.deployable = true; advisor.selected = true;
        foreach (RosterDef member in legacyData.roster.Where(r => r.selected).Skip(legacyData.partySize)) member.selected = false;
        // Select exactly the original three leads and the former field advisor.
        foreach (RosterDef member in legacyData.roster) member.selected = member.id == advisor.id || Data.roster.Take(3).Any(r => r.id == member.id);
        GameSession legacy = new GameSession(Clone(Content), Clone(legacyData)); Command(legacy, "start");
        GameSave legacySave = Clone(legacy.ExportSave()); SavedUnit woundedLegacy = legacySave.units.Single(u => u.id == "crawler.carl"); woundedLegacy.hp = woundedLegacy.maxHp / 2; string original = JsonSerializer.Serialize(legacySave, Json);
        GameData migrationTarget = Clone(Data); migrationTarget.compatibleContentVersions = new[] { "fixture-legacy" };
        GameSession migrated = new GameSession(Clone(Content), migrationTarget); view = migrated.ImportSave(legacySave);
        Check(!view.message.StartsWith("Save rejected") && view.units.Any(u => u.id == Data.roster.Single(r => r.replacesId == advisor.id).id) && !view.units.Any(u => u.id == advisor.id) && !view.roster.Single(r => r.id == advisor.id).selected, "allowlisted legacy advisor is replaced by new companion without losing encounter");
        Check(view.units.Where(u => u.team == "player").All(u => u.classId == Data.roster.Single(r => r.id == u.id).classId), "legacy default classes normalize to canonical character identities");
        UnitView normalizedCarl = view.units.Single(u => u.id == "crawler.carl"); ClassStats canonicalCarl = Data.classStats.Single(c => c.classId == normalizedCarl.classId);
        Check(normalizedCarl.hp == (int)((long)woundedLegacy.hp * canonicalCarl.hp / woundedLegacy.maxHp) && normalizedCarl.maxHp == canonicalCarl.hp && normalizedCarl.maxEnergy == canonicalCarl.energy && normalizedCarl.move == canonicalCarl.move, "identity migration scales current HP and applies canonical mana and movement limits");
        GameSave customClass = Clone(legacySave); RosterView oldCarl = customClass.roster.Single(r => r.id == "crawler.carl"); oldCarl.classId = "class.ranger";
        ClassStats ranger = Data.classStats.Single(c => c.classId == "class.ranger"); oldCarl.hp = oldCarl.maxHp = ranger.hp;
        SavedUnit oldActor = customClass.units.Single(u => u.id == "crawler.carl"); oldActor.classId = "class.ranger"; oldActor.hp = oldActor.maxHp = ranger.hp; oldActor.energy = oldActor.maxEnergy = ranger.energy; oldActor.move = ranger.move;
        GameView customClassView = new GameSession(Clone(Content), migrationTarget).ImportSave(customClass);
        Check(!customClassView.message.StartsWith("Save rejected") && customClassView.units.Single(u => u.id == "crawler.carl").classId == "class.ranger", "migration preserves a player-chosen nondefault legacy class");
        Check(original == JsonSerializer.Serialize(legacySave, Json), "migration does not mutate incoming save object");
        GameSave oldExploration = Clone(legacySave); oldExploration.screen = "explore"; oldExploration.units = new SavedUnit[0]; oldExploration.tiles = new TileView[0]; oldExploration.timedTags = new TimedTag[0]; oldExploration.selectedUnitId = null;
        oldExploration.exploration[0].x = 4; oldExploration.exploration[0].y = 1;
        oldExploration.exploration[0].revealed = oldExploration.exploration[0].revealed.Concat(new[] { new CellView { x = 4, y = 1 } }).GroupBy(c => c.x + "," + c.y).Select(g => g.First()).ToArray();
        view = new GameSession(Clone(Content), migrationTarget).ImportSave(oldExploration);
        Check(!view.message.StartsWith("Save rejected") && view.exploration.x == migrationTarget.encounters[0].exploration.startX && view.exploration.y == migrationTarget.encounters[0].exploration.startY, "legacy exploration position inside changed wall safely returns to entrance");
        GameSave migratedSave = Clone(migrated.ExportSave());
        Check(!Session().ImportSave(migratedSave).message.StartsWith("Save rejected"), "migrated checkpoint roundtrips in current content");
    }
    static void Exploration()
    {
        GameData wider = Clone(Data); wider.encounters[0].exploration.discoveryRadius = 3;
        GameSession wide = new GameSession(Clone(Content), wider); RawCommand(wide, "start");
        GameSave wideSave = Clone(wide.ExportSave()); wide.ImportSave(wideSave);
        Check(wide.GetView().screen == "explore" && !wide.GetView().message.Contains("rejected"), "larger discovery radius roundtrips without revealing through walls");
        GameSession game = Session(); GameView view = RawCommand(game, "start");
        Check(view.screen == "explore" && view.units.Length == 0 && view.exploration.points.All(p => p.kind != "encounter"), "camp opens fogged exploration without exposing encounter door");
        int revealed = view.exploration.tiles.Count(t => t.revealed);
        view = RawCommand(game, "explore_move", x: 7, y: 5);
        Check(view.exploration.x == 1 && view.exploration.y == 1, "cannot path directly to hidden goal");
        view = RawCommand(game, "explore_move", x: 0, y: 1);
        Check(view.exploration.x == 1, "exploration walls block movement");
        view = RawCommand(game, "explore_move", x: 3, y: 1);
        Check(view.exploration.x == 3 && view.exploration.tiles.Count(t => t.revealed) > revealed, "BFS walking reveals traversed passage");
        string cache = view.exploration.points.First(p => p.kind == "cache").id;
        ExplorationPointDef cacheDefinition = Data.encounters[0].exploration.points.First(p => p.id == cache);
        view = RawCommand(game, "explore_move", x: 2, y: 2);
        int supply = view.items.First(i => i.id == cacheDefinition.itemId).count;
        view = RawCommand(game, "explore_interact", target: cache); view = RawCommand(game, "explore_interact", target: cache);
        Check(view.items.First(i => i.id == cacheDefinition.itemId).count == supply + cacheDefinition.count, "optional cache grants supply exactly once");
        GameSave checkpoint = Clone(game.ExportSave()); GameSession restored = Session(); restored.ImportSave(checkpoint);
        Check(restored.GetView().screen == "explore" && restored.GetView().exploration.x == 2 && restored.GetView().exploration.tiles.Count(t => t.revealed) == view.exploration.tiles.Count(t => t.revealed) && restored.GetView().exploration.points.First(p => p.id == cache).claimed, "exploration position fog and claims persist");
        string before = JsonSerializer.Serialize(restored.ExportSave(), Json); checkpoint.exploration[0].x = 0;
        restored.ImportSave(checkpoint); Check(JsonSerializer.Serialize(restored.ExportSave(), Json) == before, "wall exploration save rejected atomically");
        checkpoint = Clone(game.ExportSave()); checkpoint.exploration[0].claimed = new[] { cache, cache };
        restored.ImportSave(checkpoint); Check(JsonSerializer.Serialize(restored.ExportSave(), Json) == before, "duplicate exploration claims rejected atomically");
        checkpoint = Clone(game.ExportSave()); checkpoint.exploration[0].sectorId = Data.encounters[1].exploration.id;
        restored.ImportSave(checkpoint); Check(JsonSerializer.Serialize(restored.ExportSave(), Json) == before, "future sector checkpoint rejected atomically");
        RawCommand(game, "return_camp"); game.Handle(new GameCommand { type = "set_class", unitId = "crawler.carl", classId = "class.ranger" }); RawCommand(game, "start");
        Check(game.GetView().exploration.x == 2, "camp revisit preserves exploration progress");
        view = EnterDoor(game); Check(view.units.First(u => u.id == "crawler.carl").classId == "class.ranger", "chosen class persists through exploration into combat");
        GameSave legacy = Clone(game.ExportSave()); legacy.exploration = new ExplorationSave[0]; restored.ImportSave(legacy); Check(restored.GetView().screen == "battle", "legacy battle checkpoint resumes without exploration history");
    }
    static void ConfigurableParty()
    {
        GameData config = Clone(Data);
        config.journey = null; config.neighborhood = null;
        config.partySize = 2;
        for (int i = 0; i < config.roster.Length; i++) config.roster[i].selected = i < 2;
        foreach (EncounterDef encounter in config.encounters) encounter.playerSpawns = encounter.playerSpawns.Take(2).ToArray();
        foreach (ScenarioDef scenario in config.scenarios) scenario.encounter.playerSpawns = scenario.encounter.playerSpawns.Take(2).ToArray();
        foreach (ExpeditionDef expedition in config.expeditions) expedition.encounter.playerSpawns = expedition.encounter.playerSpawns.Take(2).ToArray();
        GameSession game = new GameSession(Clone(Content), config);
        GameView view = Command(game, "start");
        Check(view.partyCapacity == 2 && view.partyCount == 2 && view.screen == "battle" && view.units.Count(u => u.team == "player") == 2, "party capacity and deployment remain data driven");
    }
    static void PartyAndMovement()
    {
        GameSession game = Session(); GameView view = game.GetView();
        Check(view.screen == "camp" && view.roster.Length == Data.roster.Length && view.partyCount == 4, "authored roster / four deployment camp");
        view = Command(game, "toggle_party", "crawler.elle"); Check(view.partyCount == 4 && view.message.Contains("full"), "fifth crawler rejected");
        Command(game, "toggle_party", "crawler.carl"); view = Command(game, "start"); Check(view.screen == "camp", "undersized party cannot deploy");
        game.Handle(new GameCommand { type = "set_class", unitId = "crawler.elle", classId = "class.ranger" });
        Command(game, "toggle_party", "crawler.elle"); view = Command(game, "start"); Check(view.screen == "battle" && view.units.Any(u => u.id == "crawler.elle" && u.classId == "class.ranger"), "roster and class changes deployed");
        string enemy = view.units.First(u => u.team == "enemy").id;
        GameSave before = game.ExportSave(); Command(game, "move", enemy, x: 8, y: 7); Command(game, "wait", enemy);
        GameSave after = game.ExportSave(); Check(JsonSerializer.Serialize(before, Json) == JsonSerializer.Serialize(after, Json), "enemy command ownership enforced for movement and wait");
        UnitView hero = view.units.First(u => u.team == "player"); Command(game, "select", hero.id);
        UnitView occupied = view.units.First(u => u.team == "player" && u.id != hero.id);
        view = Command(game, "move", hero.id, x: occupied.x, y: occupied.y); Check(!view.units.First(u => u.id == hero.id).moved, "occupied movement rejected without spending");
        view = Command(game, "move", hero.id, x: 4, y: 2); Check(!view.units.First(u => u.id == hero.id).moved, "wall movement rejected");
        CellView destination = view.reachable.First(c => c.cost > 0);
        view = Command(game, "move", hero.id, x: destination.x, y: destination.y); Check(view.units.First(u => u.id == hero.id).moved, "BFS move spends single move");
        UnitView moved = view.units.First(u => u.id == hero.id);
        view = Command(game, "move", hero.id, x: 0, y: 0); Check(view.units.First(u => u.id == hero.id).x == moved.x, "second move blocked");
        Command(game, "wait", hero.id); view = EndRound(game); Check(view.round == 2 && view.phase == "player", "bounded enemy phase always returns");
    }
    static void PreviewItemsAndTags()
    {
        GameSession game = Session(); game.Handle(new GameCommand { type = "set_class", unitId = "crawler.katia", classId = "class.pyromancer" }); game.Handle(new GameCommand { type = "set_class", unitId = "crawler.donut", classId = "class.stormcaller" }); Command(game, "start");
        string actor = "crawler.donut", target = "enemy.goblin_two";
        Command(game, "move", actor, x: 3, y: 3); Command(game, "select", actor);
        GameSave before = game.ExportSave(); GameView legal = game.GetView();
        Check(legal.abilities.First(a => a.id == "ability.spark").targetIds.Contains(target) && legal.abilities.All(a => a.targetIds.All(id => legal.units.Any(u => u.id == id) || legal.tiles.Any(t => t.id == id))), "core exposes authoritative legal action targets");
        Check(JsonSerializer.Serialize(before, Json) == JsonSerializer.Serialize(game.ExportSave(), Json), "legal target view does not mutate committed state");
        GameView view = Command(game, "preview", actor, target, "ability.spark");
        Check(view.canConfirm && view.forecast.Any(f => f.targetId == target && f.beforeHp - f.afterHp == 13), "wet lightning exact reaction forecast");
        Check(JsonSerializer.Serialize(before, Json) == JsonSerializer.Serialize(game.ExportSave(), Json), "preview leaves live state unchanged");
        GameView predicted = view; view = Command(game, "confirm");
        Check(view.units.First(u => u.id == target).hp == predicted.forecast.First(f => f.targetId == target).afterHp, "commit equals forecast");
        Check(view.units.First(u => u.id == actor).acted && view.units.First(u => u.id == actor).moved, "action ends activation including move");
        Command(game, "move", "crawler.katia", x: 3, y: 4);
        Command(game, "preview", "crawler.katia", "enemy.goblin_one", "ability.firebolt");
        view = Command(game, "preview", "crawler.katia", "unknown", "ability.firebolt"); Check(!view.canConfirm, "invalid replacement preview clears stale confirmation");
        view = Command(game, "preview", "crawler.katia", "tile.5.3", "ability.fire_surface");
        Check(view.forecast.Any(f => f.targetId == "tile.5.3" && f.afterTags.Contains("surface.burning") && !f.afterTags.Contains("surface.oil")), "oil surface ignition forecast consumes oil");
        Check(view.forecast.Any(f => f.targetId == "enemy.goblin_one" && f.beforeHp - f.afterHp == 4), "new burning surface damages current occupant once");
        Command(game, "confirm");
        Command(game, "move", "crawler.carl", x: 2, y: 2);
        int count = game.GetView().items.First(i => i.id == "item.frost_vial").count;
        view = Command(game, "preview", "crawler.carl", "enemy.goblin_one", item: "item.frost_vial"); Check(view.canConfirm, "item grants linked action outside class kit");
        Command(game, "cancel"); Check(game.GetView().items.First(i => i.id == "item.frost_vial").count == count, "canceled item spends no charges");
        Command(game, "preview", "crawler.carl", "enemy.goblin_one", item: "item.frost_vial"); Command(game, "confirm");
        Check(game.GetView().items.First(i => i.id == "item.frost_vial").count == count - 1, "committed item consumes exactly one shared charge");
        Check(game.ExportSave().timedTags.Any(t => t.tag == "status.frozen" && t.source == "item.frost_vial"), "timed statuses preserve source and lifetime");
        // Data-defined primitive composition: freeze then shatter is resolved by the unchanged kernel.
        Catalog catalog = new Catalog(Content); RulesEngine engine = new RulesEngine(catalog); BattleState state = new BattleState();
        state.Entities.Add("a", new EntityState { Id = "a", ClassId = "class.brawler", Team = "player", Hp = 30, MaxHp = 30, Energy = 10 });
        EntityState victim = new EntityState { Id = "b", ClassId = "class.rogue", Team = "enemy", X = 1, Hp = 30, MaxHp = 30, Energy = 10 }; victim.Tags.Add("status.frozen"); state.Entities.Add("b", victim);
        Check(engine.Preview(state, "a", "ability.shatter", "b").State.Entities["b"].Hp == 15, "freeze shatter deals base plus reaction damage");
    }
    static void Saves()
    {
        GameSession game = Session(); Command(game, "start"); Command(game, "move", "crawler.carl", x: 2, y: 2); Command(game, "preview", "crawler.carl", "enemy.goblin_one", item: "item.frost_vial"); Command(game, "confirm");
        GameSave save = Clone(game.ExportSave()); GameSession restored = Session(); restored.ImportSave(save);
        Check(JsonSerializer.Serialize(save, Json) == JsonSerializer.Serialize(restored.ExportSave(), Json), "save roundtrip preserves full deterministic state");
        string baseline = JsonSerializer.Serialize(restored.ExportSave(), Json);
        GameSave bad = Clone(save); bad.units[0].hp = -1;
        Check(restored.ImportSave(bad).message.StartsWith("Save rejected") && baseline == JsonSerializer.Serialize(restored.ExportSave(), Json), "invalid save rejected atomically");
        bad = Clone(save); bad.contentVersion = "old"; Check(restored.ImportSave(bad).message.Contains("version"), "content version mismatch rejected");
        bad = Clone(save); bad.timedTags = new TimedTag[0]; Check(restored.ImportSave(bad).message.StartsWith("Save rejected"), "missing timed-status layer rejected");
        bad = Clone(save); SavedUnit frozen = bad.units.First(u => u.tags.Contains("status.frozen")); frozen.permanentTags = new[] { "status.frozen" };
        Check(restored.ImportSave(bad).message.StartsWith("Save rejected"), "forged permanent status rejected");
        bad = Clone(save); bad.tiles[0].blocked = !bad.tiles[0].blocked; Check(restored.ImportSave(bad).message.StartsWith("Save rejected"), "save cannot change authored walls");
        bad = Clone(save); bad.units[0].classId = "class.missing"; Check(restored.ImportSave(bad).message.StartsWith("Save rejected"), "unknown class rejected");
        bad = Clone(save); bad.rewardChosen = true; Check(restored.ImportSave(bad).message.StartsWith("Save rejected"), "unearned battle reward flag rejected");
    }
    static void BattleLayoutCompatibility()
    {
        // Build the old release from its preserved authored tiles, then create a real
        // active save through the engine instead of rewriting a new map's saved tiles.
        GameData oldContent = Clone(Data);
        EncounterDef oldRoom = oldContent.encounters[0];
        Check(oldRoom.legacyTiles.Length > 0, "refined first room preserves its old authored tile provenance");
        oldRoom.tiles = Clone(oldRoom.legacyTiles); oldRoom.legacyTiles = new TileDef[0]; oldRoom.decorations = new MapPlacement[0];
        GameSession oldGame = new GameSession(Clone(Content), oldContent); Command(oldGame, "start");
        Command(oldGame, "move", "crawler.carl", x: 2, y: 2);
        Command(oldGame, "preview", "crawler.carl", "enemy.goblin_one", item: "item.frost_vial"); Command(oldGame, "confirm");
        Check(oldGame.ExportSave().timedTags.Length > 0 && oldGame.ExportSave().units.Any(u => u.moved), "old-content fixture includes committed movement and timed status");
        GameSave oldSave = Clone(oldGame.ExportSave());
        // Pre-version release files omitted this field, which deserializes as zero.
        oldSave.battleLayoutVersion = 0;
        string oldJson = JsonSerializer.Serialize(oldSave, Json).Replace("\"battleLayoutVersion\":0,", "");
        oldSave = JsonSerializer.Deserialize<GameSave>(oldJson, Json);
        GameSession restored = Session(); GameView view = restored.ImportSave(oldSave);
        Check(!view.message.StartsWith("Save rejected"), "pre-version active battle restores against original authored walls");
        Check(JsonSerializer.Serialize(oldSave, Json) == JsonSerializer.Serialize(restored.ExportSave(), Json), "old battle preserves positions health conditions flags tiles and full save state");
        Check(view.decorations.Length == 0 && view.tiles.All(t => t.blocked == oldSave.tiles.First(o => o.id == t.id).blocked), "legacy view preserves old topology and hides new decorations");
        string baseline = JsonSerializer.Serialize(restored.ExportSave(), Json);
        GameSave forged = Clone(oldSave); forged.tiles[0].blocked = !forged.tiles[0].blocked;
        Check(restored.ImportSave(forged).message.StartsWith("Save rejected") && baseline == JsonSerializer.Serialize(restored.ExportSave(), Json), "legacy authored wall forgery rejected atomically");
        forged = Clone(oldSave); forged.battleLayoutVersion = 2;
        Check(restored.ImportSave(forged).message.StartsWith("Save rejected") && baseline == JsonSerializer.Serialize(restored.ExportSave(), Json), "unknown battle layout version rejected atomically");
        Command(restored, "expedition_start", target: Data.expeditions[0].id);
        Check(restored.ExportSave().battleLayoutVersion == 1 && restored.ExportSave().expedition.campaign.battleLayoutVersion == 0, "new expedition keeps legacy campaign layout in its snapshot");
        GameSave mission = Clone(restored.ExportSave()); GameSession missionReload = Session();
        Check(!missionReload.ImportSave(mission).message.StartsWith("Save rejected"), "mission with legacy campaign snapshot reloads");
        Command(missionReload, "expedition_return");
        Check(baseline == JsonSerializer.Serialize(missionReload.ExportSave(), Json), "return from expedition restores legacy active battle exactly");
        mission.expedition.campaign.battleLayoutVersion = 2;
        Check(missionReload.ImportSave(mission).message.StartsWith("Save rejected") && baseline == JsonSerializer.Serialize(missionReload.ExportSave(), Json), "unknown nested campaign layout version rejected atomically");
        Command(restored, "expedition_return");
        Command(restored, "scenario_start", target: Data.scenarios[0].id);
        GameSave scenario = Clone(restored.ExportSave()); GameSession scenarioReload = Session();
        Check(scenario.scenario != null && scenario.scenario.campaign.battleLayoutVersion == 0 && !scenarioReload.ImportSave(scenario).message.StartsWith("Save rejected"), "scenario snapshot retains legacy battle layout through reload");
        Command(scenarioReload, "scenario_return");
        Check(baseline == JsonSerializer.Serialize(scenarioReload.ExportSave(), Json), "return from scenario restores legacy active battle exactly");
        GameData oldStoryData = Clone(Data); EncounterDef storyRoom = oldStoryData.journey.floors[0].encounter;
        storyRoom.tiles = Clone(storyRoom.legacyTiles); storyRoom.legacyTiles = new TileDef[0]; storyRoom.decorations = new MapPlacement[0];
        GameSession oldStory = new GameSession(Clone(Content), oldStoryData); Command(oldStory, "start_journey"); Command(oldStory, "start");
        GameSave storySave = Clone(oldStory.ExportSave()); storySave.battleLayoutVersion = 0;
        GameSession storyReload = Session();
        Check(storySave.screen == "battle" && !storyReload.ImportSave(storySave).message.StartsWith("Save rejected") && JsonSerializer.Serialize(storySave, Json) == JsonSerializer.Serialize(storyReload.ExportSave(), Json), "old story first battle restores exact original topology and saved state");
        GameData oldExpeditionData = Clone(Data); ExpeditionDef sewers = oldExpeditionData.expeditions.First(e => e.encounter.legacyTiles.Length > 0);
        sewers.encounter.tiles = Clone(sewers.encounter.legacyTiles); sewers.encounter.legacyTiles = new TileDef[0]; sewers.encounter.decorations = new MapPlacement[0];
        GameSession oldExpedition = new GameSession(Clone(Content), oldExpeditionData); Command(oldExpedition, "expedition_start", target: sewers.id);
        GameSave expeditionSave = Clone(oldExpedition.ExportSave()); expeditionSave.battleLayoutVersion = 0;
        GameSession expeditionReload = Session();
        Check(!expeditionReload.ImportSave(expeditionSave).message.StartsWith("Save rejected") && JsonSerializer.Serialize(expeditionSave, Json) == JsonSerializer.Serialize(expeditionReload.ExportSave(), Json), "old sewers expedition restores exact original topology and snapshot");
        Command(restored, "new_run"); Command(restored, "start");
        Check(restored.ExportSave().battleLayoutVersion == 1 && restored.GetView().decorations.Length == Data.encounters[0].decorations.Length, "new battle selects current layout and decorations after old save");
    }
    static void TerrainAndDurations()
    {
        GameData custom = Clone(Data);
        EncounterDef encounter = custom.encounters[0];
        encounter.tiles = new[] { new TileDef { x = 2, y = 1, tags = new[] { "surface.burning" } }, new TileDef { x = 3, y = 1, tags = new[] { "surface.burning" } }, new TileDef { x = 1, y = 0, tags = new[] { "surface.water" } } };
        encounter.enemies = new[] { new SpawnDef { id = "enemy.walker", label = "Hazard Walker", classId = "class.brawler", x = 8, y = 7, hp = 30, energy = 0, move = 1 } };
        GameSession game = new GameSession(Clone(Content), custom); Command(game, "start");
        int beforeHp = game.GetView().units.First(u => u.id == "crawler.carl").hp;
        GameView view = Command(game, "move", "crawler.carl", x: 4, y: 1);
        Check(view.units.First(u => u.id == "crawler.carl").hp == beforeHp - 8, "movement applies every traversed burning tile exactly once");
        Check(!view.units.First(u => u.id == "crawler.carl").tags.Contains("surface.burning"), "surface fire is not copied into unit status layer");
        game = new GameSession(Clone(Content), Clone(custom)); Command(game, "start");
        Command(game, "move", "crawler.carl", x: 1, y: 0);
        Check(game.ExportSave().timedTags.Any(t => t.entityId == "crawler.carl" && t.tag == "status.wet" && t.remainingRounds == 3), "authored surface occupancy grants timed wet status");
        EndRound(game); Check(game.ExportSave().timedTags.Any(t => t.entityId == "crawler.carl" && t.remainingRounds == 2), "status duration ticks at full-round end");
        Command(game, "move", "crawler.carl", x: 0, y: 0); EndRound(game); EndRound(game);
        Check(!game.GetView().units.First(u => u.id == "crawler.carl").tags.Contains("status.wet"), "timed tag expires after leaving its authored surface");
        game = new GameSession(Clone(Content), Clone(custom)); Command(game, "start"); Command(game, "move", "crawler.carl", x: 1, y: 0);
        for (int i = 0; i < 4; i++) EndRound(game);
        Check(game.ExportSave().timedTags.Any(t => t.entityId == "crawler.carl" && t.tag == "status.wet"), "standing on water reapplies wet with a valid duration layer");
        GameSession restored = new GameSession(Clone(Content), Clone(custom)); Check(!restored.ImportSave(Clone(game.ExportSave())).message.StartsWith("Save rejected"), "reapplied occupancy status survives validated save roundtrip");
        // An enemy also walks the complete path rather than teleporting past intermediate hazards.
        custom.encounters[0].playerSpawns = new[] { new CellView { x = 1, y = 1 }, new CellView { x = 1, y = 3 }, new CellView { x = 1, y = 5 }, new CellView { x = 2, y = 3 } };
        custom.encounters[0].enemies[0].x = 6; custom.encounters[0].enemies[0].y = 1; custom.encounters[0].enemies[0].move = 3;
        custom.encounters[0].tiles = new[] { new TileDef { x = 5, y = 1, tags = new[] { "surface.burning" } }, new TileDef { x = 4, y = 1, tags = new[] { "surface.burning" } } };
        game = new GameSession(Clone(Content), custom); Command(game, "start"); view = EndRound(game);
        UnitView walker = view.units.First(u => u.id == "enemy.walker");
        Check(walker.x == 3 && walker.y == 1 && walker.hp == 22, "enemy BFS path takes intermediate hazard entry damage");
    }
    static void CompleteFloor()
    {
        GameSession game = Session(); int commands = 0; bool usedPotion = false, moved = false; int victories = 0; int highestLevel = 1;
        while (game.GetView().screen != "complete" && commands++ < 700)
        {
            GameView view = game.GetView();
            if (view.screen == "camp") { Command(game, "safe_room_rest"); Command(game, "start"); continue; }
            if (view.screen == "defeat") throw new Exception("Autoplay party defeated on encounter " + view.encounterIndex);
            if (view.screen == "victory")
            {
                victories++; highestLevel = Math.Max(highestLevel, view.progression.level); if (view.rewards.Length > 0) game.Handle(new GameCommand { type = "choose_reward", rewardId = view.rewards[0].id });
                GameSave checkpoint = Clone(game.ExportSave()); game.ImportSave(checkpoint); view = Command(game, "continue");
                if (view.screen == "camp") { Command(game, "safe_room_rest"); view = RawCommand(game, "start"); Check(view.screen == "explore" && view.exploration.x == Data.encounters[view.encounterIndex].exploration.startX && view.exploration.y == Data.encounters[view.encounterIndex].exploration.startY, "next victory opens a fresh exploration sector"); EnterDoor(game); }
                continue;
            }
            UnitView actor = view.units.FirstOrDefault(u => u.team == "player" && u.hp > 0 && !u.acted);
            if (actor == null) { EndRound(game); continue; }
            Command(game, "select", actor.id); view = game.GetView();
            // A melee crawler advances before considering a self heal; ranged crawlers seek range.
            int desiredRange = view.abilities.Where(a => a.target == "enemy").Max(a => a.range);
            int nearestDistance = view.units.Where(u => u.team == "enemy" && u.hp > 0).Min(u => Math.Abs(u.x - actor.x) + Math.Abs(u.y - actor.y));
            if (view.canMove && nearestDistance > desiredRange)
            {
                CellView advance = view.reachable.OrderBy(c => view.units.Where(u => u.team == "enemy" && u.hp > 0).Min(u => Math.Abs(u.x - c.x) + Math.Abs(u.y - c.y)) + (view.tiles.Any(t => t.x == c.x && t.y == c.y && t.tags.Contains("surface.burning")) ? 4 : 0)).ThenBy(c => c.cost).FirstOrDefault(c => c.cost > 0);
                if (advance != null) { Command(game, "move", actor.id, x: advance.x, y: advance.y); moved = true; view = game.GetView(); }
            }
            UnitView wounded = view.units.Where(u => u.team == "player" && u.hp > 0 && u.maxHp - u.hp >= 10).OrderBy(u => u.hp).FirstOrDefault();
            if (wounded != null && view.items.Any(i => i.id == "item.health_tonic" && i.count > 0))
            {
                GameView potion = Command(game, "preview", actor.id, wounded.id, item: "item.health_tonic");
                if (potion.canConfirm) { Command(game, "confirm"); usedPotion = true; continue; }
            }
            GameCommand best = null; int score = -1;
            foreach (AbilityView ability in view.abilities.Where(a => a.enabled)) foreach (string targetId in ability.targetIds)
            {
                GameView preview = Command(game, "preview", actor.id, targetId, ability.id);
                if (!preview.canConfirm) continue;
                int value = preview.forecast.Sum(f => view.units.Any(u => u.id == f.targetId && u.team == "enemy") ? (f.beforeHp - f.afterHp) * 10 + (f.beforeHp > 0 && f.afterHp == 0 ? 200 : 0) : (f.afterHp - f.beforeHp) * 5);
                if (value > score) { score = value; best = new GameCommand { type = "preview", unitId = actor.id, targetId = targetId, abilityId = ability.id }; }
            }
            if (best != null && score > 0) { game.Handle(best); Command(game, "confirm"); continue; }
            Command(game, "cancel"); view = game.GetView();
            if (view.canMove)
            {
                CellView cell = view.reachable.OrderBy(c => view.units.Where(u => u.team == "enemy" && u.hp > 0).Min(u => Math.Abs(u.x - c.x) + Math.Abs(u.y - c.y))).ThenBy(c => c.cost).FirstOrDefault(c => c.cost > 0);
                if (cell != null) { Command(game, "move", actor.id, x: cell.x, y: cell.y); moved = true; continue; }
            }
            Command(game, "wait", actor.id);
        }
        Check(game.GetView().screen == "complete" && victories == 3 && commands < 700, "default party clears all three authored encounters including boss");
        Check(game.GetView().xp == Data.encounters.Sum(e => e.xp), "victory XP awarded exactly once per encounter");
        Check(highestLevel == Data.progression.xpThresholds.Count(threshold => threshold <= Data.encounters.Sum(e => e.xp)) && game.GetView().progression.level == highestLevel && game.GetView().quests.Single(q => q.id == "quest.floor").complete, "three encounters reach their earned shared level and complete the actual floor quest");
        Check(moved, "full-floor traversal uses legal BFS movement");
        Check(usedPotion, "full-floor traversal uses a shared health potion");
        GameSession restored = Session(); restored.ImportSave(Clone(game.ExportSave())); Check(restored.GetView().screen == "complete", "completed floor can save and resume");
        string completedCampaign = JsonSerializer.Serialize(game.ExportSave(), Json);
        game.Handle(new GameCommand { type = "scenario_start", targetId = "scenario.hoarder" });
        Check(game.GetView().scenario != null && game.GetView().screen == "battle", "completed campaign can enter a standalone boss without restarting");
        game.Handle(new GameCommand { type = "scenario_return" });
        Check(JsonSerializer.Serialize(game.ExportSave(), Json) == completedCampaign, "scenario return preserves the completed level-four campaign exactly");
        Command(game, "new_run"); Check(game.GetView().screen == "camp" && game.GetView().xp == 0, "new run resets progression");
    }
    static void DefeatRetry()
    {
        GameSession game = Session(); Command(game, "start"); int turns = 0; bool defaultEnemyAttacked = false;
        while (game.GetView().screen == "battle" && turns++ < 80)
        {
            GameView roundView = EndRound(game); defaultEnemyAttacked |= roundView.events.Any(e => e.type == "attack" && e.actorId != null && e.actorId.StartsWith("enemy."));
        }
        Check(defaultEnemyAttacked, "actual authored enemies emit attack events while a passive party waits");
        Check(game.GetView().screen == "defeat" && turns < 80, "passive party reaches defeat without AI softlock");
        GameSession restored = Session(); restored.ImportSave(Clone(game.ExportSave())); Check(restored.GetView().screen == "defeat", "defeat checkpoint restores");
        GameView view = Command(game, "retry"); Check(view.screen == "battle" && view.round == 1 && view.units.Where(u => u.team == "player").All(u => u.hp == u.maxHp), "retry restores playable encounter");
    }
}
