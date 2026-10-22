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
        Check(Content.classes.All(c => c.abilityIds.Length >= 3), "all twelve classes have functional kits");
        Check(Content.items.Length == 8 && Content.abilities.Length >= 18, "release inventory and ability breadth");
        Exploration(); ConfigurableParty(); PartyAndMovement(); PreviewItemsAndTags(); Saves(); TerrainAndDurations(); CompleteFloor(); DefeatRetry();
        Console.WriteLine(checks + " game checks passed.");
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
        int supply = view.items.First(i => i.id == "item.health_tonic").count;
        view = RawCommand(game, "explore_interact", target: cache); view = RawCommand(game, "explore_interact", target: cache);
        Check(view.items.First(i => i.id == "item.health_tonic").count == supply + 1, "optional cache grants supply exactly once");
        GameSave checkpoint = Clone(game.ExportSave()); GameSession restored = Session(); restored.ImportSave(checkpoint);
        Check(restored.GetView().screen == "explore" && restored.GetView().exploration.x == 3 && restored.GetView().exploration.tiles.Count(t => t.revealed) == view.exploration.tiles.Count(t => t.revealed) && restored.GetView().exploration.points.First(p => p.id == cache).claimed, "exploration position fog and claims persist");
        string before = JsonSerializer.Serialize(restored.ExportSave(), Json); checkpoint.exploration[0].x = 0;
        restored.ImportSave(checkpoint); Check(JsonSerializer.Serialize(restored.ExportSave(), Json) == before, "wall exploration save rejected atomically");
        checkpoint = Clone(game.ExportSave()); checkpoint.exploration[0].claimed = new[] { cache, cache };
        restored.ImportSave(checkpoint); Check(JsonSerializer.Serialize(restored.ExportSave(), Json) == before, "duplicate exploration claims rejected atomically");
        checkpoint = Clone(game.ExportSave()); checkpoint.exploration[0].sectorId = Data.encounters[1].exploration.id;
        restored.ImportSave(checkpoint); Check(JsonSerializer.Serialize(restored.ExportSave(), Json) == before, "future sector checkpoint rejected atomically");
        RawCommand(game, "return_camp"); game.Handle(new GameCommand { type = "set_class", unitId = "crawler.carl", classId = "class.ranger" }); RawCommand(game, "start");
        Check(game.GetView().exploration.x == 3, "camp revisit preserves exploration progress");
        view = EnterDoor(game); Check(view.units.First(u => u.id == "crawler.carl").classId == "class.ranger", "chosen class persists through exploration into combat");
        GameSave legacy = Clone(game.ExportSave()); legacy.exploration = new ExplorationSave[0]; restored.ImportSave(legacy); Check(restored.GetView().screen == "battle", "legacy battle checkpoint resumes without exploration history");
    }
    static void ConfigurableParty()
    {
        GameData config = Clone(Data);
        config.partySize = 2;
        for (int i = 0; i < config.roster.Length; i++) config.roster[i].selected = i < 2;
        foreach (EncounterDef encounter in config.encounters) encounter.playerSpawns = encounter.playerSpawns.Take(2).ToArray();
        GameSession game = new GameSession(Clone(Content), config);
        GameView view = Command(game, "start");
        Check(view.partyCapacity == 2 && view.partyCount == 2 && view.screen == "battle" && view.units.Count(u => u.team == "player") == 2, "party capacity and deployment remain data driven");
    }
    static void PartyAndMovement()
    {
        GameSession game = Session(); GameView view = game.GetView();
        Check(view.screen == "camp" && view.roster.Length == 8 && view.partyCount == 4, "eight roster / four deployment camp");
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
        Command(game, "wait", hero.id); view = Command(game, "end_turn"); Check(view.round == 2 && view.phase == "player", "bounded enemy phase always returns");
    }
    static void PreviewItemsAndTags()
    {
        GameSession game = Session(); Command(game, "start");
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
        Command(game, "end_turn"); Check(game.ExportSave().timedTags.Any(t => t.entityId == "crawler.carl" && t.remainingRounds == 2), "status duration ticks at full-round end");
        Command(game, "move", "crawler.carl", x: 0, y: 0); Command(game, "end_turn"); Command(game, "end_turn");
        Check(!game.GetView().units.First(u => u.id == "crawler.carl").tags.Contains("status.wet"), "timed tag expires after leaving its authored surface");
        game = new GameSession(Clone(Content), Clone(custom)); Command(game, "start"); Command(game, "move", "crawler.carl", x: 1, y: 0);
        for (int i = 0; i < 4; i++) Command(game, "end_turn");
        Check(game.ExportSave().timedTags.Any(t => t.entityId == "crawler.carl" && t.tag == "status.wet"), "standing on water reapplies wet with a valid duration layer");
        GameSession restored = new GameSession(Clone(Content), Clone(custom)); Check(!restored.ImportSave(Clone(game.ExportSave())).message.StartsWith("Save rejected"), "reapplied occupancy status survives validated save roundtrip");
        // An enemy also walks the complete path rather than teleporting past intermediate hazards.
        custom.encounters[0].playerSpawns = new[] { new CellView { x = 1, y = 1 }, new CellView { x = 1, y = 3 }, new CellView { x = 1, y = 5 }, new CellView { x = 2, y = 3 } };
        custom.encounters[0].enemies[0].x = 6; custom.encounters[0].enemies[0].y = 1; custom.encounters[0].enemies[0].move = 3;
        custom.encounters[0].tiles = new[] { new TileDef { x = 5, y = 1, tags = new[] { "surface.burning" } }, new TileDef { x = 4, y = 1, tags = new[] { "surface.burning" } } };
        game = new GameSession(Clone(Content), custom); Command(game, "start"); view = Command(game, "end_turn");
        UnitView walker = view.units.First(u => u.id == "enemy.walker");
        Check(walker.x == 3 && walker.y == 1 && walker.hp == 22, "enemy BFS path takes intermediate hazard entry damage");
    }
    static void CompleteFloor()
    {
        GameSession game = Session(); int commands = 0; bool usedPotion = false, moved = false; int victories = 0;
        while (game.GetView().screen != "complete" && commands++ < 700)
        {
            GameView view = game.GetView();
            if (view.screen == "camp") { Command(game, "start"); continue; }
            if (view.screen == "defeat") throw new Exception("Autoplay party defeated on encounter " + view.encounterIndex);
            if (view.screen == "victory")
            {
                victories++; if (view.rewards.Length > 0) game.Handle(new GameCommand { type = "choose_reward", rewardId = view.rewards[0].id });
                GameSave checkpoint = Clone(game.ExportSave()); game.ImportSave(checkpoint); view = Command(game, "continue");
                if (view.screen == "camp") { view = RawCommand(game, "start"); Check(view.screen == "explore" && view.exploration.x == 1 && view.exploration.y == 1, "next victory opens a fresh exploration sector"); EnterDoor(game); }
                continue;
            }
            UnitView actor = view.units.FirstOrDefault(u => u.team == "player" && u.hp > 0 && !u.acted);
            if (actor == null) { Command(game, "end_turn"); continue; }
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
            foreach (AbilityView ability in view.abilities.Where(a => a.enabled)) foreach (UnitView target in view.units.Where(u => u.hp > 0))
            {
                GameView preview = Command(game, "preview", actor.id, target.id, ability.id);
                if (!preview.canConfirm) continue;
                int value = preview.forecast.Sum(f => view.units.Any(u => u.id == f.targetId && u.team == "enemy") ? (f.beforeHp - f.afterHp) * 10 + (f.beforeHp > 0 && f.afterHp == 0 ? 200 : 0) : (f.afterHp - f.beforeHp) * 5);
                if (value > score) { score = value; best = new GameCommand { type = "preview", unitId = actor.id, targetId = target.id, abilityId = ability.id }; }
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
        Check(moved, "full-floor traversal uses legal BFS movement");
        Check(usedPotion, "full-floor traversal uses a shared health potion");
        GameSession restored = Session(); restored.ImportSave(Clone(game.ExportSave())); Check(restored.GetView().screen == "complete", "completed floor can save and resume");
        Command(game, "new_run"); Check(game.GetView().screen == "camp" && game.GetView().xp == 0, "new run resets progression");
    }
    static void DefeatRetry()
    {
        GameSession game = Session(); Command(game, "start"); int turns = 0;
        while (game.GetView().screen == "battle" && turns++ < 80) Command(game, "end_turn");
        Check(game.GetView().screen == "defeat" && turns < 80, "passive party reaches defeat without AI softlock");
        GameSession restored = Session(); restored.ImportSave(Clone(game.ExportSave())); Check(restored.GetView().screen == "defeat", "defeat checkpoint restores");
        GameView view = Command(game, "retry"); Check(view.screen == "battle" && view.round == 1 && view.units.Where(u => u.team == "player").All(u => u.hp == u.maxHp), "retry restores playable encounter");
    }
}
