using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using DungeonCrawlerTactics;
static class CustomMapTests
{
    static readonly JsonSerializerOptions Json = new JsonSerializerOptions { IncludeFields = true };
    static Content content;
    static GameData data;
    static int checks;
    static T Clone<T>(T value) { return JsonSerializer.Deserialize<T>(JsonSerializer.Serialize(value, Json), Json); }
    static GameSession Session() { return new GameSession(Clone(content), Clone(data)); }
    static CustomMapData Map() { return new CustomMapData { width = 10, height = 8, label = "Painted test", tiles = new[] { new TileDef { x = 3, y = 3, blocked = true }, new TileDef { x = 4, y = 4, tags = new[] { "surface.water" } } }, placements = new[] { new MapPlacement { id = "crate.0", assetId = "crate", layer = "prop", x = 3, y = 3, rotation = 3, blocksMovement = true } } }; }
    static CustomMapData NativeMap()
    {
        CustomMapData map = Map();
        map.visuals = new NativeMapVisuals { styleId = "dungeon-after-dark", kitId = "ghost-havana", pieces = new[] {
            new NativeMapPiece { cell = 6, x2 = 0, y2 = -1, rotation = 2, layer = "structures" },
            new NativeMapPiece { cell = 7, x2 = -1, y2 = 0, rotation = 3, layer = "structures" },
            new NativeMapPiece { cell = 12, x2 = 0, y2 = 0, rotation = 0, layer = "props" },
            new NativeMapPiece { cell = 16, x2 = 4, y2 = 4, rotation = 1, layer = "props" } } };
        map.visuals.pieces = Enumerable.Range(0, map.width * map.height).Select(i => new NativeMapPiece {
            cell = i % 4, x2 = (i % map.width) * 2, y2 = (i / map.width) * 2, rotation = i % 4, layer = "ground"
        }).Concat(map.visuals.pieces).ToArray();
        return map;
    }
    static void Check(bool condition, string message) { if (!condition) throw new Exception(message); checks++; Console.WriteLine("PASS " + message); }
    static string Save(GameSession game) { return JsonSerializer.Serialize(game.ExportSave(), Json); }
    static void Reject(GameSession game, CustomMapData map, string message) { string before = Save(game); game.Handle(new GameCommand { type = "import_map", customMap = map }); Check(Save(game) == before, message + " preserves live run"); }
    static void GeneratedChecks()
    {
        GameSession legacy = Session(); GameView legacyView = legacy.Handle(new GameCommand { type = "start" });
        Check(legacyView.exploration.tiles.All(t => t.blocked == data.encounters[0].exploration.walls.Any(w => w.x == t.x && w.y == t.y)), "Exploration collision stays canonical while visibility changes");
        GameSession game = Session(); CustomMapData map = NativeMap();
        GameView view = game.Handle(new GameCommand { type = "import_generated", customMap = map, entrance = new CellView { x = 0, y = 0 }, exit = new CellView { x = 9, y = 0 } });
        Check(view.screen == "explore" && view.exploration.width == map.width && view.customMap.visuals.kitId == map.visuals.kitId, "Generated run explores the exact native map before combat");
        string before = Save(game);
        game.Handle(new GameCommand { type = "explore_step", x = 1, y = 1 }); Check(Save(game) == before, "Diagonal generated movement rejected transactionally");
        game.Handle(new GameCommand { type = "explore_step", x = -1 }); Check(Save(game) == before, "Out of bounds generated movement rejected");
        for (int i = 0; i < 30; i++) { game.Handle(new GameCommand { type = "explore_step", x = 1 }); game.Handle(new GameCommand { type = "explore_step", x = -1 }); }
        Check(game.GetView().screen == "explore" && game.GetView().generatedDungeon.x == 0, "Exploration permits unlimited steps without actions or movement points");
        GameSession restored = Session(); restored.ImportSave(Clone(game.ExportSave())); Check(Save(restored) == Save(game), "Generated exploration save roundtrip");
        game.Handle(new GameCommand { type = "return_camp" }); game.Handle(new GameCommand { type = "start" }); Check(game.GetView().exploration.id == "generated.dungeon", "Camp returns to generated map");
        game.Handle(new GameCommand { type = "explore_move", x = 1, y = 0 }); game.Handle(new GameCommand { type = "explore_move", x = 2, y = 0 }); game.Handle(new GameCommand { type = "explore_move", x = 2, y = 1 }); game.Handle(new GameCommand { type = "explore_move", x = 2, y = 2 }); game.Handle(new GameCommand { type = "explore_move", x = 2, y = 3 });
        before = Save(game); game.Handle(new GameCommand { type = "explore_step", x = 1 }); Check(Save(game) == before, "Canonical blocked tiles prevent exploration movement");
        game.Handle(new GameCommand { type = "explore_move", x = 2, y = 4 }); game.Handle(new GameCommand { type = "explore_move", x = 2, y = 5 }); game.Handle(new GameCommand { type = "explore_move", x = 3, y = 5 }); game.Handle(new GameCommand { type = "explore_move", x = 4, y = 5 });
        game.Handle(new GameCommand { type = "explore_move", x = 5, y = 5 });
        view = game.Handle(new GameCommand { type = "explore_move", x = 6, y = 5 });
        Check(view.screen == "battle" && view.units.First(u => u.team == "player").x == view.generatedDungeon.x && view.units.First(u => u.team == "player").y == view.generatedDungeon.y, "Nearby enemies trigger battle at exploration leader instead of entrance");
        Check(view.units.Where(u => u.hp > 0).Select(u => u.x + "," + u.y).Distinct().Count() == view.units.Length, "Nearby party deployment does not overlap enemies or allies");
        restored = Session(); restored.ImportSave(Clone(game.ExportSave())); Check(Save(restored) == Save(game), "Generated battle save roundtrip");
        GameSave defeat = Clone(game.ExportSave()); defeat.screen = "defeat"; defeat.selectedUnitId = null;
        foreach (SavedUnit unit in defeat.units.Where(u => u.team == "player")) unit.hp = 0;
        GameSession retry = Session(); Check(retry.ImportSave(defeat).screen == "defeat", "Generated defeat checkpoint validates");
        GameView retried = retry.Handle(new GameCommand { type = "retry" });
        Check(retried.screen == "battle" && retried.units.First(u => u.team == "player").x == view.generatedDungeon.x && retried.units.First(u => u.team == "player").y == view.generatedDungeon.y, "Retry deploys at saved encounter approach instead of original entrance");
        GameSave invalidReward = Clone(game.ExportSave()); invalidReward.generatedDungeon.cleared = true;
        before = Save(game); game.ImportSave(invalidReward); Check(Save(game) == before, "Forged cleared flag cannot skip a generated battle");
        GameSave invalid = Clone(game.ExportSave()); invalid.generatedDungeon.x = 3; invalid.generatedDungeon.y = 3; before = Save(game); game.ImportSave(invalid); Check(Save(game) == before, "Invalid generated position preserves active battle");
        GameSession duel = Session(); CustomMapData duelMap = new CustomMapData { width = 10, height = 8, enemies = new[] { new SpawnDef { id = "custom.enemy.duel", label = "Rat", classId = data.encounters[0].enemies[0].classId, x = 2, y = 1, hp = 1, move = 1 } } };
        duel.Handle(new GameCommand { type = "import_generated", customMap = duelMap, entrance = new CellView { x = 0, y = 1 }, exit = new CellView { x = 1, y = 1 } });
        view = duel.Handle(new GameCommand { type = "explore_step", x = 1 });
        AbilityView strike = view.abilities.First(a => a.enabled && a.targetIds.Contains("custom.enemy.duel"));
        duel.Handle(new GameCommand { type = "preview", abilityId = strike.id, targetId = "custom.enemy.duel" }); duel.Handle(new GameCommand { type = "confirm" });
        Check(duel.GetView().screen == "victory", "Generated battle retains sponsor reward flow");
        restored = Session(); Check(restored.ImportSave(Clone(duel.ExportSave())).screen == "victory", "Generated victory roundtrip");
        duel.Handle(new GameCommand { type = "choose_reward", rewardId = data.rewards[0].id }); view = duel.Handle(new GameCommand { type = "continue" });
        Check(view.screen == "explore" && view.generatedDungeon.cleared && view.units.Length == 0, "Reward continuation returns to cleared generated exploration");
        restored = Session(); Check(restored.ImportSave(Clone(duel.ExportSave())).generatedDungeon.cleared, "Cleared generated exploration save roundtrip");
        Check(duel.Handle(new GameCommand { type = "explore_interact", targetId = "generated.exit" }).screen == "complete", "Cleared exit completes generated dungeon");
        restored = Session(); Check(restored.ImportSave(Clone(duel.ExportSave())).screen == "complete", "Generated completion save roundtrip");
    }
    static void Main()
    {
        content = JsonSerializer.Deserialize<Content>(File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "combat-content.json")), Json);
        data = JsonSerializer.Deserialize<GameData>(File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "game-content.json")), Json);
        GameSession game = Session(); CustomMapData map = Map();
        GameView view = game.Handle(new GameCommand { type = "import_map", customMap = map });
        Check(view.screen == "battle" && view.width == 10 && view.units.Length == data.partySize + 3, "Valid map starts direct custom battle with deterministic actors");
        Check(view.tiles.Single(t => t.x == 3 && t.y == 3).blocked && view.tiles.Single(t => t.x == 4 && t.y == 4).tags.Contains("surface.water"), "Blocking and terrain tags reach actual resolver state");
        Check(view.customMap.placements[0].rotation == 3, "Component rotation reaches renderer view");
        Check(view.customMap.visuals == null, "Legacy custom maps retain their original presentation");
        GameSession second = Session(); second.Handle(new GameCommand { type = "import_map", customMap = Map() });
        Check(Save(game) == Save(second), "Identical maps produce deterministic spawns and state");
        map.tiles[0].blocked = false; map.placements[0].rotation = 0;
        Check(game.ExportSave().customMap.tiles[0].blocked && game.ExportSave().customMap.placements[0].rotation == 3, "Imported map is isolated from caller mutations");
        GameSave saved = Clone(game.ExportSave()); GameSession loaded = Session(); view = loaded.ImportSave(saved);
        Check(view.screen == "battle" && view.customMap != null && Save(loaded) == Save(game), "Custom map save roundtrip retains encounter, actors, components and rotation");
        GameSession native = Session(); CustomMapData authored = NativeMap();
        string authoredVisuals = JsonSerializer.Serialize(authored.visuals, Json);
        GameView nativeView = native.Handle(new GameCommand { type = "import_map", customMap = authored });
        Check(JsonSerializer.Serialize(nativeView.customMap.visuals, Json) == authoredVisuals, "Every native preview tile, half-cell boundary, layer and quarter rotation reaches battle unchanged");
        Check(nativeView.tiles.Single(t => t.x == 3 && t.y == 3).blocked, "Native presentation preserves canonical blocking");
        authored.visuals.kitId = "changed"; authored.visuals.pieces[0].cell = 5;
        nativeView.customMap.visuals.pieces[1].rotation = 3;
        GameSave nativeSave = native.ExportSave();
        Check(JsonSerializer.Serialize(nativeSave.customMap.visuals, Json) == authoredVisuals, "Native art metadata is deep copied from both caller and renderer view");
        GameSession nativeReload = Session(); nativeReload.ImportSave(Clone(nativeSave));
        Check(Save(nativeReload) == Save(native), "Portable native map save roundtrip preserves exact visual placements and run state");
        nativeSave.customMap.visuals.pieces[0].x2 = 18;
        Check(JsonSerializer.Serialize(native.ExportSave().customMap.visuals, Json) == authoredVisuals, "Exported native metadata cannot mutate the live map");
        foreach (string field in new[] { "version", "style", "kit", "count", "null", "piece", "cell", "negative", "bounds", "rotation", "layer", "ground", "duplicate", "coverage" })
        {
            CustomMapData invalid = NativeMap();
            if (field == "version") invalid.visuals.schemaVersion = 2;
            if (field == "style") invalid.visuals.styleId = "../escape";
            if (field == "kit") invalid.visuals.kitId = new string('a', 65);
            if (field == "count") invalid.visuals.pieces = new NativeMapPiece[3841];
            if (field == "null") invalid.visuals.pieces = null;
            if (field == "piece") invalid.visuals.pieces[0] = null;
            if (field == "cell") invalid.visuals.pieces[0].cell = 24;
            if (field == "negative") invalid.visuals.pieces[2].y2 = -2;
            if (field == "bounds") invalid.visuals.pieces[2].x2 = invalid.width * 2;
            if (field == "rotation") invalid.visuals.pieces[2].rotation = 4;
            if (field == "layer") invalid.visuals.pieces[2].layer = "unknown";
            if (field == "ground") invalid.visuals.pieces[0].x2 = 1;
            if (field == "duplicate") invalid.visuals.pieces[1].x2 = 0;
            if (field == "coverage") invalid.visuals.pieces = invalid.visuals.pieces.Where(p => p.layer != "ground" || p.x2 != 2 || p.y2 != 2).ToArray();
            Reject(native, invalid, "Invalid native art " + field);
        }
        CustomMapData missingDefaultCell = NativeMap(); missingDefaultCell.tiles = new TileDef[0]; missingDefaultCell.placements = new MapPlacement[0];
        missingDefaultCell.visuals.pieces = missingDefaultCell.visuals.pieces.Where(p => p.layer != "ground" || p.x2 != 18 || p.y2 != 14).ToArray();
        Reject(native, missingDefaultCell, "Missing floor on an implicit walkable cell");
        GameSave invalidNativeSave = Clone(native.ExportSave()); invalidNativeSave.customMap.visuals.kitId = "unsafe/path";
        string nativeBefore = Save(native); native.ImportSave(invalidNativeSave);
        Check(Save(native) == nativeBefore, "Invalid native art in a save preserves the live run");
        CustomMapData bad = Map(); bad.width = 21; Reject(game, bad, "Oversized map");
        bad = Map(); bad.tiles[0].tags = new[] { "unknown.tag" }; Reject(game, bad, "Unknown tags");
        bad = Map(); bad.tiles = new[] { new TileDef { x = 3, y = 3 }, new TileDef { x = 3, y = 3 } }; Reject(game, bad, "Duplicate tile");
        bad = Map(); bad.placements[0].assetId = "../../invalid"; Reject(game, bad, "Unknown component");
        bad = Map(); bad.placements[0].rotation = 4; Reject(game, bad, "Invalid component rotation");
        bad = Map(); bad.tiles[0].blocked = false; Reject(game, bad, "Component/tile blocking mismatch");
        bad = Map(); bad.playerSpawns = new[] { new CellView { x = 3, y = 3 }, new CellView { x = 1, y = 1 }, new CellView { x = 2, y = 1 }, new CellView { x = 3, y = 1 } }; Reject(game, bad, "Blocked actor spawn");
        bad = Map(); bad.placements = new MapPlacement[0]; bad.tiles = Enumerable.Range(0, 10).Select(x => new TileDef { x = x, y = 4, blocked = true }).ToArray(); Reject(game, bad, "Disconnected generated spawns");
        string stable = Save(game); saved.customMap.width = 21; game.ImportSave(saved); Check(Save(game) == stable, "Invalid map inside imported save preserves live run");
        GameSession duel = Session(); CustomMapData duelMap = new CustomMapData { width = 10, height = 8, playerSpawns = new[] { new CellView { x = 1, y = 1 }, new CellView { x = 1, y = 3 }, new CellView { x = 1, y = 5 }, new CellView { x = 2, y = 3 } }, enemies = new[] { new SpawnDef { id = "custom.enemy.duel", label = "Test rat", classId = data.encounters[0].enemies[0].classId, artId = "rat", x = 2, y = 1, hp = 1, energy = 0, move = 1 } } };
        view = duel.Handle(new GameCommand { type = "import_map", customMap = duelMap });
        AbilityView strike = view.abilities.First(a => a.enabled && a.targetIds.Contains("custom.enemy.duel"));
        duel.Handle(new GameCommand { type = "preview", abilityId = strike.id, targetId = "custom.enemy.duel" });
        view = duel.Handle(new GameCommand { type = "confirm" });
        Check(view.screen == "victory", "Imported map resolves real action through victory");
        GameSession victoryReload = Session(); Check(victoryReload.ImportSave(Clone(duel.ExportSave())).screen == "victory", "Custom victory save roundtrip");
        duel.Handle(new GameCommand { type = "choose_reward", rewardId = data.rewards[0].id });
        view = duel.Handle(new GameCommand { type = "continue" });
        Check(view.screen == "complete" && view.width == duelMap.width && view.customMap != null, "Custom encounter completes after one victory with its map retained");
        GameSession completeReload = Session(); Check(completeReload.ImportSave(Clone(duel.ExportSave())).screen == "complete", "Completed custom run save roundtrip");
        game.Handle(new GameCommand { type = "new_run" }); Check(game.GetView().customMap == null && game.GetView().screen == "camp", "New campaign clears custom encounter override");
        GeneratedChecks();
        Console.WriteLine("PASS " + checks + " custom map checks.");
    }
}
