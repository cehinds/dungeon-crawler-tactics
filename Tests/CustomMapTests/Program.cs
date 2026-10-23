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
    static void Check(bool condition, string message) { if (!condition) throw new Exception(message); checks++; Console.WriteLine("PASS " + message); }
    static string Save(GameSession game) { return JsonSerializer.Serialize(game.ExportSave(), Json); }
    static void Reject(GameSession game, CustomMapData map, string message) { string before = Save(game); game.Handle(new GameCommand { type = "import_map", customMap = map }); Check(Save(game) == before, message + " preserves live run"); }
    static void Main()
    {
        content = JsonSerializer.Deserialize<Content>(File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "combat-content.json")), Json);
        data = JsonSerializer.Deserialize<GameData>(File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "game-content.json")), Json);
        GameSession game = Session(); CustomMapData map = Map();
        GameView view = game.Handle(new GameCommand { type = "import_map", customMap = map });
        Check(view.screen == "battle" && view.width == 10 && view.units.Length == data.partySize + 3, "Valid map starts direct custom battle with deterministic actors");
        Check(view.tiles.Single(t => t.x == 3 && t.y == 3).blocked && view.tiles.Single(t => t.x == 4 && t.y == 4).tags.Contains("surface.water"), "Blocking and terrain tags reach actual resolver state");
        Check(view.customMap.placements[0].rotation == 3, "Component rotation reaches renderer view");
        GameSession second = Session(); second.Handle(new GameCommand { type = "import_map", customMap = Map() });
        Check(Save(game) == Save(second), "Identical maps produce deterministic spawns and state");
        map.tiles[0].blocked = false; map.placements[0].rotation = 0;
        Check(game.ExportSave().customMap.tiles[0].blocked && game.ExportSave().customMap.placements[0].rotation == 3, "Imported map is isolated from caller mutations");
        GameSave saved = Clone(game.ExportSave()); GameSession loaded = Session(); view = loaded.ImportSave(saved);
        Check(view.screen == "battle" && view.customMap != null && Save(loaded) == Save(game), "Custom map save roundtrip retains encounter, actors, components and rotation");
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
        Console.WriteLine("PASS " + checks + " custom map checks.");
    }
}
