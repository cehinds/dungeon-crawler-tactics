using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using DungeonCrawlerTactics;
static class AudienceTests
{
    static readonly JsonSerializerOptions Json = new JsonSerializerOptions { IncludeFields = true };
    static Content content; static GameData data; static int checks;
    static T Clone<T>(T value) { return JsonSerializer.Deserialize<T>(JsonSerializer.Serialize(value, Json), Json); }
    static void Check(bool ok, string label) { if (!ok) throw new Exception(label); checks++; Console.WriteLine("PASS " + label); }
    static string Save(GameSession game) { return JsonSerializer.Serialize(game.ExportSave(), Json); }
    static GameSession Session() { return new GameSession(Clone(content), Clone(data)); }
    static GameView Cmd(GameSession game, string type, string item = null, string target = null, int x = 0, int y = 0) { return game.Handle(new GameCommand { type = type, unitId = "crawler.carl", itemId = item, targetId = target, x = x, y = y }); }
    static void CappedRewards(CustomMapData source)
    {
        var config = Clone(data);
        config.sponsorChallenges = new[] {
            new SponsorChallengeDef { id = "sponsor.cap_one", label = "One", description = "One", eventType = "victory", rewardItemId = "item.fire_bomb", rewardCount = 2 },
            new SponsorChallengeDef { id = "sponsor.cap_two", label = "Two", description = "Two", eventType = "victory", rewardItemId = "item.fire_bomb", rewardCount = 3 } };
        var game = new GameSession(Clone(content), config); var map = Clone(source); map.enemies[0].x = 2; map.enemies[0].y = 1; map.enemies[0].hp = 1;
        game.Handle(new GameCommand { type = "import_map", customMap = map });
        var save = Clone(game.ExportSave()); save.inventory.Single(i => i.itemId == "item.fire_bomb").count = 10000; game.ImportSave(save);
        string stable = Save(game); var view = Cmd(game, "preview", "item.fire_bomb", map.enemies[0].id);
        Check(view.canConfirm && view.audience.forecastRewards.Length == 1 && view.audience.forecastRewards[0].itemId == "item.fire_bomb" && view.audience.forecastRewards[0].count == 1 && Save(game) == stable, "Duplicate reward IDs aggregate against capacity after pending supply consumption");
        Cmd(game, "cancel"); Check(Save(game) == stable, "Capped reward preview cancel is free");
        Cmd(game, "preview", "item.fire_bomb", map.enemies[0].id); view = Cmd(game, "confirm");
        Check(view.screen == "victory" && view.items.Single(i => i.id == "item.fire_bomb").count == 10000 && view.audience.challenges.All(c => c.earned), "Capped duplicate deliveries commit the exact combined forecast with both receipts");
        var legacy = Clone(new GameSession(Clone(content), config).ExportSave()); legacy.audience = null; legacy.inventory = legacy.inventory.Where(i => i.itemId != "item.health_tonic").ToArray();
        stable = Save(game); game.ImportSave(legacy); Check(Save(game) == stable, "Legacy inventory migration still requires every nontrap supply");
    }
    static void Main()
    {
        content = JsonSerializer.Deserialize<Content>(File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "combat-content.json")), Json);
        data = JsonSerializer.Deserialize<GameData>(File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "game-content.json")), Json);
        data.startingInventory = content.items.Select(i => new InventoryEntry { itemId = i.id, count = 5 }).ToArray();
        GameSession game = Session();
        string camp = Save(game); var old = Clone(game.ExportSave()); old.audience = null; old.inventory = old.inventory.Where(i => i.itemId != "item.coolant_snare" && i.itemId != "item.shock_snare").ToArray();
        Check(!game.ImportSave(old).message.StartsWith("Save rejected") && game.GetView().items.Single(i => i.id == "item.shock_snare").count == 0, "Pre-feature inventory migrates missing traps to zero");
        game = Session(); game.Handle(new GameCommand { type = "craft", recipeId = "recipe.shock_snare" });
        Check(game.GetView().items.Single(i => i.id == "item.shock_snare").count == 6 && game.GetView().items.Single(i => i.id == "item.thunder_flask").count == 4, "Authored recipe consumes material and creates trap");
        var map = new CustomMapData { width = 10, height = 8, tiles = new[] { new TileDef { x = 2, y = 2, tags = new[] { "surface.oil" } } }, playerSpawns = new[] { new CellView { x = 1, y = 1 }, new CellView { x = 1, y = 3 }, new CellView { x = 1, y = 5 }, new CellView { x = 2, y = 4 } }, enemies = new[] { new SpawnDef { id = "custom.enemy.watch", label = "Watcher", classId = data.encounters[0].enemies[0].classId, x = 8, y = 6, hp = 100, energy = 0, move = 1 } } };
        game.Handle(new GameCommand { type = "import_map", customMap = map });
        string stable = Save(game); var view = Cmd(game, "preview_favor", "item.oil_flask", "tile.2.1");
        Check(!view.canConfirm && Save(game) == stable, "Cannot spend unearned Favor");
        view = game.Handle(new GameCommand { type = "preview", unitId = "crawler.carl", abilityId = "ability.carl_bomb", targetId = "tile.2.2" });
        Check(view.canConfirm && Save(game) == stable && view.audience.favor == 0 && view.audience.forecastFavor == 1 && view.audience.forecastRewards.Any(r => r.itemId == "item.oil_flask" && r.count == 1), "Reaction preview changes no audience or save state");
        Cmd(game, "cancel"); Check(Save(game) == stable, "Reaction cancel changes nothing");
        game.Handle(new GameCommand { type = "preview", unitId = "crawler.carl", abilityId = "ability.carl_bomb", targetId = "tile.2.2" }); view = Cmd(game, "confirm");
        Check(view.audience.favor == 1 && view.audience.favorEarned == 1 && view.audience.challenges.Single(c => c.id == "sponsor.reaction").earned, "Committed player reaction grants bounded Favor and sponsor receipt");
        Check(view.units.Single(u => u.id == "crawler.carl").acted && view.items.Single(i => i.id == "item.shock_snare").favorTargetIds.Contains("tile.2.1"), "Favor targets remain legal after action spent");
        stable = Save(game); view = Cmd(game, "preview_favor", "item.fire_bomb", "tile.3.1"); Check(!view.canConfirm && Save(game) == stable, "Favor rejects attack supplies");
        foreach (string extra in new[] { "stance", "form", "ability" })
        {
            var malformed = new GameCommand { type = "preview_favor", unitId = "crawler.carl", itemId = "item.oil_flask", targetId = "tile.2.1", stanceId = extra == "stance" ? data.stances[0].id : null, formId = extra == "form" ? data.forms[0].id : null, abilityId = extra == "ability" ? "ability.carl_bomb" : null };
            view = game.Handle(malformed); Check(!view.canConfirm && Save(game) == stable, "Favor rejects mixed " + extra + " command atomically");
        }
        view = Cmd(game, "preview_favor", "item.shock_snare", "tile.1.1"); Check(!view.canConfirm && Save(game) == stable, "Trap rejects occupied tile without spending");
        view = Cmd(game, "preview_favor", "item.shock_snare", "tile.2.1"); Check(view.canConfirm && Save(game) == stable && view.forecast.Any(f => f.afterTags.Contains("surface.trap_shock")), "Trap preview shows exact placed surface without spending");
        Cmd(game, "cancel"); Check(Save(game) == stable, "Favor trap cancel preserves resource and inventory");
        Cmd(game, "preview_favor", "item.shock_snare", "tile.2.1"); view = Cmd(game, "confirm");
        Check(view.audience.favor == 0 && view.audience.favorEarned == 1 && view.units.Single(u => u.id == "crawler.carl").acted && !view.units.Single(u => u.id == "crawler.carl").moved, "Favor consumes exactly one utility opportunity and preserves budgets");
        var saved = Clone(game.ExportSave()); var loaded = Session(); Check(!loaded.ImportSave(saved).message.StartsWith("Save rejected") && Save(game) == Save(loaded), "Reload preserves Favor receipt and placed trap exactly");
        int hp = view.units.Single(u => u.id == "crawler.carl").hp; view = Cmd(game, "move", x: 2, y: 1); Cmd(loaded, "move", x: 2, y: 1);
        Check(view.units.Single(u => u.id == "crawler.carl").hp == hp - 5 && view.units.Single(u => u.id == "crawler.carl").tags.Contains("status.shocked") && !view.tiles.Single(t => t.id == "tile.2.1").tags.Contains("surface.trap_shock"), "First entrant takes exact trap damage and status and consumes trap");
        Check(Save(game) == Save(loaded), "Trap triggering is deterministic across reload");
        saved = Clone(game.ExportSave()); saved.audience.favor = 2; stable = Save(game); game.ImportSave(saved); Check(Save(game) == stable, "Malformed Favor rejected atomically");
        saved = Clone(game.ExportSave()); saved.audience.receipts = new[] { "sponsor.reaction", "sponsor.reaction" }; game.ImportSave(saved); Check(Save(game) == stable, "Duplicate sponsor receipt rejected atomically");
        saved = Clone(game.ExportSave()); saved.units.Single(u => u.id == "crawler.carl").acted = false; saved.units.Single(u => u.id == "crawler.carl").energy = saved.units.Single(u => u.id == "crawler.carl").maxEnergy; saved.tiles.Single(t => t.id == "tile.2.2").tags = new[] { "surface.oil" };
        game.ImportSave(saved); int oil = game.GetView().items.Single(i => i.id == "item.oil_flask").count;
        game.Handle(new GameCommand { type = "preview", unitId = "crawler.carl", abilityId = "ability.carl_bomb", targetId = "tile.2.2" }); view = Cmd(game, "confirm");
        Check(view.audience.favor == 0 && view.audience.favorEarned == 1 && view.items.Single(i => i.id == "item.oil_flask").count == oil && view.audience.challenges.Count(c => c.earned) == 1, "Further reactions after reload cannot farm Favor or sponsor supplies");
        var bad = Clone(content); bad.items.Single(i => i.id == "item.fire_bomb").favorEligible = true; bool rejected = false; try { new GameSession(bad, Clone(data)); } catch (ArgumentException) { rejected = true; } Check(rejected, "Authoring validation rejects Favor damage primitives");
        CappedRewards(map);
        Console.WriteLine("PASS " + checks + " audience and trap checks.");
    }
}
