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
        Check(Content.items.Length == 8 && Content.abilities.Length >= 18, "release inventory and ability breadth");
        RevampContracts(); Exploration(); ConfigurableParty(); PartyAndMovement(); PreviewItemsAndTags(); Saves(); TerrainAndDurations(); CompleteFloor(); DefeatRetry();
        Console.WriteLine(checks + " game checks passed.");
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
        Check(previewEvents == string.Join("|", view.events.Select(ev => ev.type + ":" + ev.targetId + ":" + ev.tag + ":" + ev.toX + ":" + ev.toY)), "preview and committed event sequence agree");
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

        GameData legacyData = Clone(Data); legacyData.contentVersion = "fixture-legacy"; legacyData.compatibleContentVersions = new string[0];
        legacyData.roster = legacyData.roster.Where(r => string.IsNullOrEmpty(r.replacesId)).ToArray();
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
                if (view.screen == "camp") { view = RawCommand(game, "start"); Check(view.screen == "explore" && view.exploration.x == Data.encounters[view.encounterIndex].exploration.startX && view.exploration.y == Data.encounters[view.encounterIndex].exploration.startY, "next victory opens a fresh exploration sector"); EnterDoor(game); }
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
        Check(moved, "full-floor traversal uses legal BFS movement");
        Check(usedPotion, "full-floor traversal uses a shared health potion");
        GameSession restored = Session(); restored.ImportSave(Clone(game.ExportSave())); Check(restored.GetView().screen == "complete", "completed floor can save and resume");
        Command(game, "new_run"); Check(game.GetView().screen == "camp" && game.GetView().xp == 0, "new run resets progression");
    }
    static void DefeatRetry()
    {
        GameSession game = Session(); Command(game, "start"); int turns = 0;
        while (game.GetView().screen == "battle" && turns++ < 80) EndRound(game);
        Check(game.GetView().screen == "defeat" && turns < 80, "passive party reaches defeat without AI softlock");
        GameSession restored = Session(); restored.ImportSave(Clone(game.ExportSave())); Check(restored.GetView().screen == "defeat", "defeat checkpoint restores");
        GameView view = Command(game, "retry"); Check(view.screen == "battle" && view.round == 1 && view.units.Where(u => u.team == "player").All(u => u.hp == u.maxHp), "retry restores playable encounter");
    }
}
