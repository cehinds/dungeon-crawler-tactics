using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using DungeonCrawlerTactics;

static class RankTests
{
    static readonly JsonSerializerOptions Json = new JsonSerializerOptions { IncludeFields = true };
    static Content content;
    static GameData data;
    static int checks;
    static T Clone<T>(T value) { return JsonSerializer.Deserialize<T>(JsonSerializer.Serialize(value, Json), Json); }
    static void Check(bool value, string label) { if (!value) throw new Exception("FAILED: " + label); checks++; Console.WriteLine("PASS " + label); }
    static string Snapshot(GameSession game) { return JsonSerializer.Serialize(game.ExportSave(), Json); }
    static GameView Command(GameSession game, string type, string owner = null, string ability = null, string target = null, string node = null, string classId = null)
    {
        GameView view = game.Handle(new GameCommand { type = type, unitId = owner, abilityId = ability, targetId = target, nodeId = node, classId = classId });
        if (type != "start") return view;
        for (int attempt = 0; view.screen == "explore" && attempt < 100; attempt++)
        {
            ExplorationView map = view.exploration;
            ExplorationPointView door = map.points.FirstOrDefault(p => p.kind == "encounter" && p.canInteract);
            if (door != null) return game.Handle(new GameCommand { type = "explore_interact", targetId = door.id });
            ExplorationTileView tile = map.tiles.Where(t => t.reachable && !t.revealed).OrderBy(t => Math.Abs(t.x - map.x) + Math.Abs(t.y - map.y)).ThenBy(t => t.y).ThenBy(t => t.x).FirstOrDefault();
            if (tile == null) { door = map.points.First(p => p.kind == "encounter"); tile = map.tiles.Where(t => t.reachable).OrderBy(t => Math.Abs(t.x - door.x) + Math.Abs(t.y - door.y)).First(); }
            view = game.Handle(new GameCommand { type = "explore_move", x = tile.x, y = tile.y });
        }
        return view;
    }
    static void Main()
    {
        content = JsonSerializer.Deserialize<Content>(File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "combat-content.json")), Json);
        data = JsonSerializer.Deserialize<GameData>(File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "game-content.json")), Json);
        Tables(); DefinitionValidation(); ClassPointBudget(); TrainingAndResolver(); ClassOwnershipAndCheckpoints();
        Console.WriteLine(checks + " rank/class progression checks passed.");
    }
    static void Tables()
    {
        SkillProgressionDef config = new SkillProgressionDef();
        SkillRankView[] table = SkillRankProgression.Table(config, "ability.fixture");
        Check(table.Length == 20 && table[0].requiredUses == 0 && table[1].requiredUses == 3 && table[2].requiredUses == 8, "rank 1–20 retains the established first three training thresholds");
        Check(table.Zip(table.Skip(1), (a, b) => b.requiredUses > a.requiredUses).All(x => x) && table[10].requiredUses - table[9].requiredUses > table[9].requiredUses - table[8].requiredUses, "training thresholds increase and slow more sharply beyond rank ten");
        Check(SkillRankProgression.Rank(config, "ability.fixture", 100000, 15) == 15 && SkillRankProgression.Rank(config, "ability.fixture", 100000, 20) == 20 && table.Count(r => r.trainable) == 15, "normal eligibility caps training at fifteen while eligible profiles reach twenty");
        config.abilityProfiles = new[] { new AbilityRankProfile { abilityId = "ability.fixture", practiceMultiplierPercent = 200, damagePerRank = 2, healPerRank = 0, costReductionCap = 1, milestones = new[] { new RankMilestoneDef { rank = 10, damageBonus = 3, description = "Adapted mastery" } } } };
        SkillRankView[] tuned = SkillRankProgression.Table(config, "ability.fixture", 20);
        Check(tuned[1].requiredUses == 6 && tuned[1].damageBonus == 2 && tuned[1].healBonus == 0 && tuned[19].damageBonus == 20 && tuned[19].costReduction == 1 && tuned[9].milestones.Single() == "Adapted mastery", "per-ability training, effect caps, and milestone descriptions use one bounded table");
    }
    static bool RejectsData(Action<GameData> change)
    {
        GameData candidate = Clone(data); change(candidate);
        try { GameDataValidator.Validate(candidate, new Catalog(Clone(content))); return false; }
        catch (ArgumentException) { return true; }
    }
    static bool RejectsProfile(Action<AbilityRankProfile> change)
    {
        return RejectsData(candidate => {
            AbilityRankProfile profile = new AbilityRankProfile { abilityId = content.abilities[0].id };
            candidate.development.practice.abilityProfiles = new[] { profile }; change(profile);
        });
    }
    static void DefinitionValidation()
    {
        GameDataValidator.Validate(Clone(data), new Catalog(Clone(content)));
        Check(RejectsData(d => d.roster[0].maxSkillRank = 14) && RejectsData(d => d.roster[0].maxSkillRank = 21), "rank eligibility rejects values outside the supported fifteen-to-twenty interval");
        Check(RejectsProfile(p => p.abilityId = "ability.unknown") && RejectsData(d => d.development.practice.abilityProfiles = new[] { new AbilityRankProfile { abilityId = content.abilities[0].id }, new AbilityRankProfile { abilityId = content.abilities[0].id } }), "rank definitions reject unknown and duplicate ability profiles");
        Check(RejectsProfile(p => p.practiceMultiplierPercent = 0) && RejectsProfile(p => p.damagePerRank = -2) && RejectsProfile(p => p.healBonusCap = 101), "rank definitions reject malformed training rates and effects beyond resolver limits");
        Check(RejectsProfile(p => p.milestones = new[] { new RankMilestoneDef { rank = 21, damageBonus = 1, description = "Invalid" } }) && RejectsProfile(p => p.milestones = new[] { new RankMilestoneDef { rank = 10, damageBonus = 1, description = "First" }, new RankMilestoneDef { rank = 10, healBonus = 1, description = "Duplicate" } }) && RejectsProfile(p => p.milestones = new[] { new RankMilestoneDef { rank = 10, damageBonus = -1, description = "Negative" } }), "rank milestones reject unsupported ranks, duplicate tiers, and negative effects");
        Check(RejectsData(d => d.classSkillTrees[0].classId = content.classes.First(c => !c.playerSelectable).id) && RejectsData(d => d.classSkillTrees[0].rosterId = d.roster[0].id), "class trees require a selectable class and cannot claim a personal-tree owner");
        Check(RejectsData(d => d.classSkillTrees[1].classId = d.classSkillTrees[0].classId) && RejectsData(d => d.classSkillTrees[0].nodes[0].id = d.skillTrees[0].nodes[0].id), "class trees reject repeated class profiles and node IDs shared with personal trees");
        Check(RejectsData(d => { SkillNodeDef first = d.classSkillTrees[0].nodes[0], second = d.classSkillTrees[0].nodes[1]; first.prerequisiteIds = new[] { second.id }; second.prerequisiteIds = new[] { first.id }; first.level = second.level = 1; }) && RejectsData(d => d.classSkillTrees[0].nodes[0].prerequisiteIds = new[] { d.classSkillTrees[1].nodes[0].id }), "class graphs reject cycles and prerequisites owned by another class");
        Check(RejectsData(d => d.classSkillTrees[0].nodes[0].level = 51) && RejectsData(d => d.classSkillTrees[0].nodes[0].hpBonus = 7) && RejectsData(d => d.classSkillTrees[0].nodes[0].abilityIds = new[] { "ability.unknown" }), "class nodes reject unsupported levels, excessive effects, and unknown ability grants");
        Content invalidClasses = Clone(content); invalidClasses.classes[0].minimumFloor = 19;
        bool rejected = false; try { GameDataValidator.Validate(Clone(data), new Catalog(invalidClasses)); } catch (ArgumentException) { rejected = true; }
        Check(rejected, "class availability cannot point beyond the eighteenth floor");
    }
    static void ClassPointBudget()
    {
        Content definitions = Clone(content); GameData config = Clone(data); config.journey = null; config.neighborhood = null;
        GameSession game = new GameSession(definitions, config);
        var tree = game.GetView().skillTree.classTrees.First();
        Check(tree.nodes.Length == 14 && tree.unspentPoints == 1, "fourteen-node class starts with one point for its two root choices");
        Command(game, "preview_skill_node", tree.rosterId, node: tree.nodes.First(n => n.enabled).id);
        GameView view = Command(game, "confirm_skill_node");
        tree = view.skillTree.classTrees.First(t => t.rosterId == tree.rosterId);
        Check(tree.unspentPoints == 0 && tree.nodes.Where(n => n.level == 1 && !n.unlocked).All(n => !n.enabled), "buying one class root spends the shared tier point and blocks its alternative");
        Check(config.classSkillTrees.All(t => t.nodes.Select(n => n.level).Distinct().Count() == 7), "each authored class offers seven earned tiers for fourteen nodes through level fifty");
    }
    static GameData Fixture(Content definitions)
    {
        GameData config = Clone(data); config.journey = null; config.neighborhood = null; config.classSkillTrees = new SkillTreeDef[0];
        config.progression.xpThresholds = new[] { 0, 30, 70, 120 };
        config.development.practice.abilityProfiles = new AbilityRankProfile[0];
        config.development.practice.useThresholds = new[] { 0, 3, 8 };
        config.roster.Single(r => r.id == "crawler.carl").maxSkillRank = 20;
        AbilityDef ability = new AbilityDef { id = "ability.rank_fixture", label = "Rank fixture", target = "ally", range = 0, cost = 3, incomingTags = new string[0], effects = new[] { new EffectDef { op = "Heal", amount = 1 } } };
        definitions.abilities = definitions.abilities.Concat(new[] { ability }).ToArray();
        config.roster.Single(r => r.id == "crawler.carl").innateAbilityIds = new[] { ability.id };
        EncounterDef room = config.encounters[0]; room.tiles = new TileDef[0];
        room.enemies = new[] { new SpawnDef { id = "enemy.rank_fixture", label = "Rank fixture opponent", classId = "class.brawler", x = 8, y = 7, hp = 100, energy = 0, move = 1 } };
        return config;
    }
    static void TrainingAndResolver()
    {
        Content definitions = Clone(content); GameData config = Fixture(definitions);
        GameSession game = new GameSession(definitions, config);
        GameSave save = game.ExportSave(); int threshold = SkillRankProgression.Thresholds(config.development.practice, "ability.rank_fixture")[19];
        save.development.practice = new[] { new SkillPracticeSave { unitId = "crawler.carl", abilityId = "ability.rank_fixture", uses = threshold - 1 } };
        Check(!game.ImportSave(save).message.StartsWith("Save rejected"), "training checkpoint just below rank twenty validates");
        Command(game, "start"); save = game.ExportSave(); save.units.Single(u => u.id == "crawler.carl").hp = 1; Check(!game.ImportSave(save).message.StartsWith("Save rejected"), "wounded rank fixture validates");
        string before = Snapshot(game); GameView view = Command(game, "preview", "crawler.carl", "ability.rank_fixture", "crawler.carl");
        Check(view.canConfirm && before == Snapshot(game), "high-rank action forecast is side-effect free");
        ForecastView forecast = view.forecast.Single(f => f.targetId == "crawler.carl");
        Check(forecast.afterHp - forecast.beforeHp == 19 && forecast.beforeEnergy - forecast.afterEnergy == 1, "rank nineteen applies actual healing and bounded mana discount in shared resolver");
        Command(game, "cancel"); Check(before == Snapshot(game), "canceling high-rank forecast grants no training");
        Command(game, "preview", "crawler.carl", "ability.rank_fixture", "crawler.carl"); view = Command(game, "confirm");
        SkillPracticeView trained = view.development.practice.Single(p => p.abilityId == "ability.rank_fixture");
        Check(view.units.Single(u => u.id == "crawler.carl").hp == forecast.afterHp && trained.rank == 20 && trained.atCap && trained.uses == threshold && trained.nextRankUses == 0, "confirmed forecast matches commit and the committed use reaches rank twenty");
        int round = view.round;
        for (int i = 0; i < config.partySize && game.GetView().round == round; i++) Command(game, "end_turn");
        Command(game, "preview", "crawler.carl", "ability.rank_fixture", "crawler.carl"); view = Command(game, "confirm");
        Check(view.development.practice.Single().uses == threshold && view.events.All(e => e.type != "skill_practice"), "further committed uses at the rank cap grant no extra training");
        round = view.round;
        for (int i = 0; i < config.partySize && game.GetView().round == round; i++) Command(game, "end_turn");
        view = game.Handle(new GameCommand { type = "preview", unitId = "crawler.carl", itemId = "item.health_tonic", targetId = "crawler.carl" });
        Check(view.canConfirm, "item fixture has a legal committed use");
        view = Command(game, "confirm");
        Check(view.development.practice.Length == 1 && view.development.practice.Single().uses == threshold && view.events.All(e => e.type != "skill_practice"), "committed item use creates no ability training");
        GameSession restored = new GameSession(Clone(definitions), Clone(config));
        Check(!restored.ImportSave(Clone(game.ExportSave())).message.StartsWith("Save rejected") && restored.GetView().development.practice.Single().rank == 20, "rank twenty persists through checkpoint reload");
        config.roster.Single(r => r.id == "crawler.carl").maxSkillRank = 15;
        restored = new GameSession(Clone(definitions), config); view = restored.ImportSave(Clone(game.ExportSave()));
        Check(!view.message.StartsWith("Save rejected") && view.development.practice.Single().rank == 15, "eligibility changes safely cap a legacy over-trained checkpoint");
    }
    static void ClassOwnershipAndCheckpoints()
    {
        Content definitions = Clone(content); GameData config = Fixture(definitions);
        string classId = config.roster.Single(r => r.id == "crawler.carl").classId;
        config.encounters[0].xp = 4900;
        string granted = definitions.abilities.First(a => a.target == "enemy" && !definitions.classes.Single(c => c.id == classId).abilityIds.Contains(a.id)).id;
        config.classSkillTrees = new[] { new SkillTreeDef { id = "classtree.fixture", classId = classId, label = "Fixture class", description = "Adapted class progression", nodes = new[] {
            new SkillNodeDef { id = "classnode.fixture_root", label = "Root", description = "Damage training", damageBonus = 1, abilityIds = new[] { granted } },
            new SkillNodeDef { id = "classnode.fixture_child", label = "Child", description = "HP training", level = 5, hpBonus = 2, prerequisiteIds = new[] { "classnode.fixture_root" } },
            new SkillNodeDef { id = "classnode.fixture_capstone", label = "Capstone", description = "Level fifty training", level = 50, hpBonus = 2, prerequisiteIds = new[] { "classnode.fixture_child" } }
        } } };
        if (config.progression.xpThresholds.Length < 50) config.progression.xpThresholds = Enumerable.Range(0, 50).Select(i => i * 100).ToArray();
        GameSession game = new GameSession(definitions, config); string before = Snapshot(game);
        GameView view = Command(game, "preview_skill_node", "crawler.carl", node: "classnode.fixture_root");
        Check(view.skillTree.canConfirm && view.skillTree.forecast.afterDamageBonus == view.skillTree.forecast.beforeDamageBonus + 1 && before == Snapshot(game), "selected class-node preview reports the same runtime modifier without spending");
        Command(game, "cancel_skill_node"); Check(before == Snapshot(game), "canceling class-node learning preserves checkpoint");
        Command(game, "preview_skill_node", "crawler.carl", node: "classnode.fixture_root"); view = Command(game, "confirm_skill_node");
        Check(game.ExportSave().skillTree.unlockedIds.Contains("crawler.carl::classnode.fixture_root") && view.skillTree.classTrees.Single(t => t.rosterId == "crawler.carl").nodes.First().unlocked, "class-node learning saves explicit per-crawler ownership");
        before = Snapshot(game); view = Command(game, "preview_skill_node", "crawler.donut", node: "classnode.fixture_root");
        Check(!view.skillTree.canConfirm && before == Snapshot(game), "a different selected class cannot buy another class profile");
        GameSave forged = Clone(game.ExportSave()); forged.skillTree.unlockedIds = new[] { "crawler.donut::classnode.fixture_child" };
        Check(game.ImportSave(forged).message.StartsWith("Save rejected") && before == Snapshot(game), "class checkpoint prerequisites must belong to the same crawler");
        forged = Clone(game.ExportSave()); forged.skillTree.unlockedIds = new[] { "classnode.fixture_root" };
        Check(game.ImportSave(forged).message.StartsWith("Save rejected"), "class checkpoint cannot omit its crawler owner");
        view = Command(game, "preview_skill_node", "crawler.carl", node: "classnode.fixture_capstone"); Check(!view.skillTree.canConfirm, "level fifty class capstone remains locked at the starting level");
        GameSave learned = Clone(game.ExportSave()); GameSession restored = new GameSession(Clone(definitions), Clone(config));
        Check(!restored.ImportSave(learned).message.StartsWith("Save rejected") && restored.GetView().skillTree.classTrees.Single(t => t.rosterId == "crawler.carl").nodes.First().unlocked, "owned class skills round-trip through save validation");
        string replacement = definitions.classes.First(c => c.playerSelectable && c.id != classId).id;
        Command(game, "set_class", "crawler.carl", classId: replacement); Check(game.ExportSave().skillTree.unlockedIds.Contains("crawler.carl::classnode.fixture_root") && !game.GetView().skillTree.classTrees.Any(t => t.rosterId == "crawler.carl"), "class switching preserves learned ownership while deactivating its profile");
        Command(game, "set_class", "crawler.carl", classId: classId); Check(game.GetView().skillTree.classTrees.Single(t => t.rosterId == "crawler.carl").nodes.First().unlocked, "returning to a class restores its learned profile");
        Command(game, "start"); GameSave battle = Clone(game.ExportSave()); SavedUnit enemy = battle.units.Single(u => u.id == "enemy.rank_fixture"); enemy.x = 2; enemy.y = 1; enemy.hp = 1;
        Check(!game.ImportSave(battle).message.StartsWith("Save rejected"), "level fifty reward fixture validates before battle");
        Command(game, "preview", "crawler.carl", "ability.carl_powerful_strike", "enemy.rank_fixture"); view = Command(game, "confirm");
        Check(view.screen == "victory" && view.progression.level == 50, "an earned encounter reward reaches actual runtime level fifty");
        game.Handle(new GameCommand { type = "choose_reward", rewardId = config.rewards[0].id }); Command(game, "continue");
        Command(game, "preview_skill_node", "crawler.carl", node: "classnode.fixture_child"); Command(game, "confirm_skill_node");
        int beforeHp = game.GetView().roster.Single(r => r.id == "crawler.carl").maxHp;
        view = Command(game, "preview_skill_node", "crawler.carl", node: "classnode.fixture_capstone");
        Check(view.skillTree.canConfirm && view.skillTree.forecast.afterHp == beforeHp + 2, "level fifty capstone previews its actual stat effect after prerequisites");
        view = Command(game, "confirm_skill_node");
        Check(view.roster.Single(r => r.id == "crawler.carl").maxHp == beforeHp + 2 && view.skillTree.classTrees.Single(t => t.rosterId == "crawler.carl").nodes.Last().unlocked, "level fifty capstone commits its real stat effect");
        restored = new GameSession(Clone(definitions), Clone(config));
        Check(!restored.ImportSave(Clone(game.ExportSave())).message.StartsWith("Save rejected"), "earned level fifty class build round-trips with derived stat validation");
        Command(game, "start"); restored = new GameSession(Clone(definitions), Clone(config));
        GameView imported = restored.ImportSave(Clone(game.ExportSave()));
        Check(!imported.message.StartsWith("Save rejected") && imported.units.Single(u => u.id == "crawler.carl").abilityIds.Contains(granted), "imported active class profile grants its learned ability through the shared progression path");
    }
}
