using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using DungeonCrawlerTactics;
static class ExpeditionTests
{
    static readonly JsonSerializerOptions Json = new JsonSerializerOptions { IncludeFields = true };
    static Content content;
    static GameData data;
    static int checks;
    static T Clone<T>(T source) { return JsonSerializer.Deserialize<T>(JsonSerializer.Serialize(source, Json), Json); }
    static GameSession Session() { return new GameSession(Clone(content), Clone(data)); }
    static string Save(GameSession game) { return JsonSerializer.Serialize(game.ExportSave(), Json); }
    static GameView Command(GameSession game, string type, string unit = null, string target = null, string ability = null, string item = null, int x = 0, int y = 0) { return game.Handle(new GameCommand { type = type, unitId = unit, targetId = target, abilityId = ability, itemId = item, x = x, y = y }); }
    static void Check(bool pass, string label) { if (!pass) throw new Exception(label); checks++; Console.WriteLine("PASS " + label); }
    static void PlayBattle(GameSession game)
    {
        int commands = 0;
        while (game.GetView().screen == "battle" && commands++ < 700)
        {
            GameView view = game.GetView();
            UnitView actor = view.units.FirstOrDefault(u => u.team == "player" && u.hp > 0 && !u.finished);
            if (actor == null) { Command(game, "end_turn"); continue; }
            Command(game, "select", actor.id); view = game.GetView();
            int range = view.abilities.Where(a => a.target == "enemy").Select(a => a.range).DefaultIfEmpty(1).Max();
            Func<int, int, int> distance = (x, y) => view.units.Where(u => u.team == "enemy" && u.hp > 0).Select(u => Math.Abs(u.x - x) + Math.Abs(u.y - y)).DefaultIfEmpty(0).Min();
            if (view.canMove && distance(actor.x, actor.y) > range)
            {
                CellView advance = view.reachable.Where(c => c.cost > 0).OrderBy(c => distance(c.x, c.y) + (view.tiles.Any(t => t.x == c.x && t.y == c.y && t.tags.Contains("surface.burning")) ? 6 : 0)).ThenBy(c => c.cost).FirstOrDefault();
                if (advance != null) { Command(game, "move", actor.id, x: advance.x, y: advance.y); view = game.GetView(); }
            }
            UnitView wounded = view.units.Where(u => u.team == "player" && u.hp > 0 && u.maxHp - u.hp >= 10).OrderBy(u => u.hp).FirstOrDefault();
            if (wounded != null && view.items.Any(i => i.id == "item.health_tonic" && i.count > 0))
            {
                if (Command(game, "preview", actor.id, wounded.id, item: "item.health_tonic").canConfirm) { Command(game, "confirm"); continue; }
            }
            int score = -1; GameCommand best = null;
            foreach (AbilityView ability in view.abilities.Where(a => a.enabled)) foreach (string target in ability.targetIds)
            {
                GameView preview = Command(game, "preview", actor.id, target, ability.id); if (!preview.canConfirm) continue;
                int value = preview.forecast.Sum(f => view.units.Any(u => u.id == f.targetId && u.team == "enemy") ? (f.beforeHp - f.afterHp) * 10 + (f.beforeHp > 0 && f.afterHp == 0 ? 200 : 0) : (f.afterHp - f.beforeHp) * 5);
                if (value > score) { score = value; best = new GameCommand { type = "preview", unitId = actor.id, targetId = target, abilityId = ability.id }; }
            }
            if (best != null && score > 0) { game.Handle(best); Command(game, "confirm"); continue; }
            Command(game, "cancel"); view = game.GetView();
            if (view.canMove)
            {
                CellView move = view.reachable.Where(c => c.cost > 0).OrderBy(c => distance(c.x, c.y)).ThenBy(c => c.cost).FirstOrDefault();
                if (move != null) { Command(game, "move", actor.id, x: move.x, y: move.y); continue; }
            }
            Command(game, "wait", actor.id);
        }
        Check(game.GetView().screen == "victory", "Legal forecast/commit controller clears " + game.GetView().encounterName + " in " + commands + " activations");
    }
    static void Main()
    {
        content = JsonSerializer.Deserialize<Content>(File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "combat-content.json")), Json);
        data = JsonSerializer.Deserialize<GameData>(File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "game-content.json")), Json);
        Check(data.expeditions.Length == 6, "Six authored expeditions are available");
        foreach (ExpeditionDef expedition in data.expeditions)
        {
            GameSession game = Session(); string campaign = Save(game);
            GameView view = Command(game, "expedition_start", target: expedition.id);
            Check(view.screen == "battle" && view.expedition.id == expedition.id && view.width == expedition.encounter.width && view.units.Count(u => u.team == "enemy") == expedition.encounter.enemies.Length, expedition.id + " uses authored map and enemy lineup");
            GameSave checkpoint = Clone(game.ExportSave()); GameSession reload = Session(); GameView loaded = reload.ImportSave(checkpoint);
            Check(loaded.expedition != null && Save(reload) == Save(game), expedition.id + " battle save roundtrip");
            PlayBattle(game);
            Check(game.GetView().xp == checkpoint.xp && game.ExportSave().rewardChosen && game.ExportSave().development.lootBoxes.Length == checkpoint.development.lootBoxes.Length, expedition.id + " grants no campaign XP or reward farm");
            reload = Session(); Check(reload.ImportSave(Clone(game.ExportSave())).screen == "victory", expedition.id + " victory save roundtrip");
            Command(game, "expedition_retry"); Check(game.GetView().screen == "battle" && game.GetView().round == 1 && game.GetView().xp == checkpoint.xp, expedition.id + " replay resets the mission only");
            Command(game, "expedition_return"); Check(Save(game) == campaign, expedition.id + " return restores exact campaign snapshot");
        }
        Console.WriteLine("PASS " + checks + " expedition checks.");
    }
}
