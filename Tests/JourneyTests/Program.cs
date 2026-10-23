using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using DungeonCrawlerTactics;
static class JourneyTests
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
            JourneyCaptureView capture = view.journey != null ? view.journey.captures.FirstOrDefault(c => c.canCapture) : null;
            if (capture != null)
            {
                string beforeCapture = Save(game);
                GameView previewCapture = Command(game, "preview_capture", actor.id, capture.targetId);
                Check(previewCapture.canConfirm && Save(game) == beforeCapture, "Capture preview is pure");
                Check(previewCapture.forecast.Any(f => f.targetId == capture.targetId && f.afterHp == 0), "Capture forecast seals the chosen monster");
                Command(game, "cancel_capture"); Check(Save(game) == beforeCapture, "Cancel capture spends no action or card");
                Command(game, "preview_capture", actor.id, capture.targetId);
                Command(game, "confirm_capture"); continue;
            }
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
    static void Roundtrip(GameSession game, string label)
    {
        string before = Save(game); GameSession reload = Session(); GameView loaded = reload.ImportSave(Clone(game.ExportSave()));
        Check(!loaded.message.StartsWith("Save rejected:") && Save(reload) == before, label + " save restores exactly: " + loaded.message);
    }
    static void Explore(GameSession game)
    {
        Command(game, "start");
        for (int steps = 0; steps < 400 && game.GetView().screen == "explore"; steps++)
        {
            GameView view = game.GetView();
            ExplorationPointView next = view.exploration.points.FirstOrDefault(p => p.canInteract && p.kind != "encounter" && (view.neighborhood == null || !view.neighborhood.interactions.Any(i => i.pointId == p.id)));
            if (next != null) { Command(game, "explore_interact", target: next.id); continue; }
            ExplorationPointView door = view.exploration.points.FirstOrDefault(p => p.canInteract && p.kind == "encounter");
            if (door != null && view.journey.objectivesComplete == view.journey.objectivesRequired) { Command(game, "explore_interact", target: door.id); break; }
            ExplorationTileView tile = view.exploration.tiles.Where(t => t.reachable && !t.blocked && !t.revealed).OrderBy(t => Math.Abs(t.x - view.exploration.x) + Math.Abs(t.y - view.exploration.y)).ThenBy(t => t.y).ThenBy(t => t.x).FirstOrDefault();
            if (tile != null) { Command(game, "explore_move", x: tile.x, y: tile.y); continue; }
            ExplorationPointView point = view.exploration.points.FirstOrDefault(p => !p.claimed && p.kind != "encounter" && (view.neighborhood == null || !view.neighborhood.interactions.Any(i => i.pointId == p.id))) ?? view.exploration.points.FirstOrDefault(p => p.kind == "encounter");
            if (point != null) { Command(game, "explore_move", x: point.x, y: point.y); continue; }
        }
        Check(game.GetView().screen == "battle", "Exploration reaches a legal encounter after required objectives");
    }
    static void Main()
    {
        content = JsonSerializer.Deserialize<Content>(File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "combat-content.json")), Json);
        data = JsonSerializer.Deserialize<GameData>(File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "game-content.json")), Json);
        GameSession game = Session();
        Check(game.GetView().journey != null && game.GetView().journey.floors.Length == 18 && !game.GetView().journey.active, "Story is explicit and exposes eighteen-floor registry");
        Check(game.GetView().encounterCount == 3 && game.ExportSave().journey == null, "Legacy three-encounter mode remains default");
        string legacy = Save(game); Roundtrip(game, "Legacy camp");
        Command(game, "start_journey"); Check(game.GetView().journey.active && game.GetView().journey.floorNumber == 1, "Explicit story start initializes floor one");
        Check(!game.GetView().journey.classesUnlocked && !game.GetView().journey.allocationUnlocked, "Early floors lock classes and bank allocation");
        GameSave bad = Clone(game.ExportSave()); bad.journey.floorIndex = 10;
        string intact = Save(game); Check(game.ImportSave(bad).message.StartsWith("Save rejected:") && Save(game) == intact, "Invalid future story save is rejected atomically");
        int previousXp = 0;
        for (int floor = 1; floor <= 8; floor++)
        {
            Check(game.GetView().journey.floorNumber == floor, "Continuous story reaches floor " + floor);
            Roundtrip(game, "Floor " + floor + " camp");
            if (floor == 7)
            {
                Check(game.GetView().journey.canBypass && game.GetView().journey.floors[6].kind == "bypass", "Destroyed race is an explicit bypass");
                Command(game, "journey_bypass"); Check(game.GetView().xp == previousXp, "Destroyed race awards no fabricated battle XP"); continue;
            }
            if (floor == 2)
            {
                string banked = Save(game);
                GameView locked = game.Handle(new GameCommand { type = "preview_allocate", unitId = "crawler.carl", statId = data.development.stats[0].id, points = 1 });
                Check(Save(game) == banked && locked.message.IndexOf("floor", StringComparison.OrdinalIgnoreCase) >= 0, "Earned stat points remain banked on floor two");
            }
            if (floor == 3) Check(game.GetView().journey.classesUnlocked && game.GetView().journey.allocationUnlocked, "Over City unlocks classes and allocation");
            if (floor == 3) { game.Handle(new GameCommand { type = "set_specialty", unitId = "crawler.donut", classId = "class.cryomancer" }); Check(game.GetView().roster.Single(r => r.id == "crawler.donut").specialtyClassId == "class.cryomancer", "Character Actor selects a temporary specialty on floor three"); }
            if (floor == 4) Check(game.GetView().roster.Single(r => r.id == "crawler.donut").specialtyClassId == null && game.GetView().roster.Single(r => r.id == "crawler.donut").specialtyAvailable, "Story descent clears the specialty and permits a fresh choice");
            Command(game, "safe_room_rest"); Explore(game);
            if (floor == 3) Check(game.GetView().units.Single(u => u.id == "crawler.donut").abilityIds.Contains("ability.ice_lance"), "Temporary specialty supplies its actual combat kit");
            if (floor == 4) Check(!game.GetView().units.Single(u => u.id == "crawler.donut").abilityIds.Contains("ability.ice_lance"), "Expired specialty abilities do not leak into the next floor"); Roundtrip(game, "Floor " + floor + " battle");
            if (floor == 4 || floor == 5)
            {
                GameSave missingRoute = Clone(game.ExportSave());
                JourneyFloorDef authored = data.journey.floors[floor - 1];
                missingRoute.exploration.First(e => e.sectorId == authored.encounter.exploration.id).claimed = new string[0];
                string beforeBadRoute = Save(game);
                Check(game.ImportSave(missingRoute).message.StartsWith("Save rejected:") && Save(game) == beforeBadRoute, "Saved battle cannot bypass floor " + floor + " route objectives");
            }
            if (floor == 6) Check(game.GetView().journey.intents.Length > 0, "Hunting Grounds declares deterministic hunter intentions");
            PlayBattle(game); Roundtrip(game, "Floor " + floor + " victory");
            if (floor == 8) Check(game.GetView().journey.cardsCaptured == 6, "Six weakened monsters were captured through real actions");
            GameView view = game.GetView(); if (view.rewards.Length > 0) game.Handle(new GameCommand { type = "choose_reward", rewardId = view.rewards[0].id });
            previousXp = game.GetView().xp; Command(game, "continue");
        }
        Check(game.GetView().screen == "complete" && game.GetView().journey.complete, "Eight-floor campaign completes after capture");
        Check(game.GetView().journey.floors.Skip(8).All(f => f.status == "locked"), "Floors nine through eighteen remain visibly locked");
        Roundtrip(game, "Completed story");
        Check(!game.ImportSave(JsonSerializer.Deserialize<GameSave>(legacy, Json)).journey.active && game.GetView().encounterCount == 3, "Legacy save restores after story play");
        Console.WriteLine("Journey checks: " + checks);
    }
}
