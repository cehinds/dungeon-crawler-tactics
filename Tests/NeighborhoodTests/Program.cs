using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using DungeonCrawlerTactics;
static class Tests
{
    static int checks;
    static JsonSerializerOptions json = new JsonSerializerOptions { IncludeFields = true };
    static string Save(GameSession game) { return JsonSerializer.Serialize(game.ExportSave(), json); }
    static T Clone<T>(T value) { return JsonSerializer.Deserialize<T>(JsonSerializer.Serialize(value, json), json); }
    static void Check(bool value, string message) { if (!value) throw new Exception(message); checks++; Console.WriteLine("PASS " + message); }
    static GameView Cmd(GameSession game, string type, string target = null, string option = null, string unit = null) { return game.Handle(new GameCommand { type = type, targetId = target, nodeId = option, unitId = unit }); }
    static GameView Command(GameSession game, string type, string unit = null, string target = null, string ability = null, string item = null, int x = 0, int y = 0) { return game.Handle(new GameCommand { type = type, unitId = unit, targetId = target, abilityId = ability, itemId = item, x = x, y = y }); }
    static void Walk(GameSession game, ExplorationDef map, int x, int y)
    {
        var view = game.GetView().exploration; var pending = new System.Collections.Generic.Queue<CellView>(); var previous = new System.Collections.Generic.Dictionary<string, CellView>(); Func<int,int,string> key = (a,b) => a + "," + b;
        pending.Enqueue(new CellView { x = view.x, y = view.y }); previous[key(view.x, view.y)] = null; int[] dx = {0,-1,1,0}, dy={-1,0,0,1};
        while(pending.Count > 0) { var c=pending.Dequeue(); for(int i=0;i<4;i++) { int a=c.x+dx[i],b=c.y+dy[i]; if(a<0||b<0||a>=map.width||b>=map.height||map.walls.Any(w=>w.x==a&&w.y==b)||previous.ContainsKey(key(a,b))) continue; previous[key(a,b)]=c;pending.Enqueue(new CellView{x=a,y=b}); } }
        var path=new System.Collections.Generic.List<CellView>(); var step=new CellView{x=x,y=y}; while(step!=null) {path.Add(step);step=previous[key(step.x,step.y)];} path.Reverse(); foreach(var c in path) Command(game,"explore_move",x:c.x,y:c.y);
        Check(game.GetView().exploration.x == x && game.GetView().exploration.y == y, "legal passage path reaches " + x + "," + y);
    }
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
    static void Main()
    {
        var content = JsonSerializer.Deserialize<Content>(File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "combat-content.json")), json);
        var data = JsonSerializer.Deserialize<GameData>(File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "game-content.json")), json);
        var game = new GameSession(content, data); string campaign = Save(game);
        Check(Cmd(game, "start_neighborhood").neighborhood.standalone, "isolated neighborhood starts from fresh campaign");
        var prep = data.neighborhood.interactions.Single(i => i.camp); var option = prep.options.First(o => o.costCount == 0 && string.IsNullOrEmpty(o.abilityId));
        string before = Save(game); var preview = Cmd(game, "preview_neighborhood", prep.id, option.id);
        Check(preview.neighborhood.canConfirm && Save(game) == before, "preview leaves serialized state unchanged");
        Cmd(game, "cancel_neighborhood"); Check(Save(game) == before, "cancel spends and awards nothing");
        preview = Cmd(game, "preview_neighborhood", prep.id, option.id); var expected = preview.neighborhood.forecast.afterItems;
        var committed = Cmd(game, "confirm_neighborhood");
        Check(expected.All(e => game.ExportSave().inventory.Single(i => i.itemId == e.itemId).count == e.count), "confirmation matches combined exact supply forecast");
        string once = Save(game); Cmd(game, "preview_neighborhood", prep.id, prep.options.Last().id); Cmd(game, "confirm_neighborhood"); Check(Save(game) == once, "cannot farm a repeated or alternative preparation choice");
        var checkpoint = game.ExportSave(); var restored = new GameSession(content, data); var loaded = restored.ImportSave(Clone(checkpoint)); Check(!loaded.message.StartsWith("Save rejected:"), "sampler checkpoint reloads: " + loaded.message); Check(Save(restored) == once, "sampler receipts survive reload exactly");
        var corrupt = Clone(checkpoint); corrupt.neighborhood.challengeIds = new[] { "unknown.challenge" }; Check(restored.ImportSave(corrupt).message.StartsWith("Save rejected:") && Save(restored) == once, "unmatched challenge rejected atomically");
        corrupt = Clone(checkpoint); corrupt.neighborhood.receipts = new[] { checkpoint.neighborhood.receipts[0], checkpoint.neighborhood.receipts[0] }; Check(restored.ImportSave(corrupt).message.StartsWith("Save rejected:"), "duplicate choice receipt rejected");
        corrupt = Clone(checkpoint); corrupt.neighborhood.campaign = corrupt; Check(restored.ImportSave(corrupt).message.StartsWith("Save rejected:"), "cyclic sampler backup rejected before recursion");
        Cmd(restored, "return_neighborhood"); Check(Save(restored) == campaign, "return restores original campaign byte for byte");
        var old = restored.ExportSave(); old.neighborhood = null; Check(!restored.ImportSave(old).message.StartsWith("Save rejected:") && restored.GetView().neighborhood.clues.Length == 0, "old saves default to empty neighborhood receipts");
        var invalidData = Clone(data); invalidData.neighborhood.interactions[0].options[0].rewardItemId = "unknown.item"; invalidData.neighborhood.interactions[0].options[0].rewardCount = 1; bool rejected = false; try { new GameSession(content, invalidData); } catch (ArgumentException) { rejected = true; } Check(rejected, "unknown authored item reference rejected");
        Cmd(restored, "start_neighborhood"); var legacySave = restored.ExportSave(); legacySave.screen = "explore";
        var legacy = data.neighborhood.legacyExploration;
        var oldCells = Enumerable.Range(0, legacy.height).SelectMany(y => Enumerable.Range(0, legacy.width).Select(x => new CellView { x = x, y = y })).ToArray();
        legacySave.exploration = new[] { new ExplorationSave { sectorId = legacy.id, x = 9, y = 4, revealed = oldCells, claimed = legacy.points.Where(p => p.kind != "encounter").Select(p => p.id).ToArray() } };
        string inputBefore = JsonSerializer.Serialize(legacySave, json); var oldInventory = JsonSerializer.Serialize(legacySave.inventory, json);
        var migrated = restored.ImportSave(legacySave); Check(!migrated.message.StartsWith("Save rejected:"), "published Over City layout migrates: " + migrated.message);
        Check(JsonSerializer.Serialize(legacySave, json) == inputBefore, "legacy migration does not mutate supplied checkpoint");
        Check(restored.ExportSave().exploration.Single().layoutVersion == 1 && restored.ExportSave().exploration.Single().claimed.SequenceEqual(legacySave.exploration[0].claimed) && JsonSerializer.Serialize(restored.ExportSave().inventory, json) == oldInventory, "migration preserves claims and inventory without new rewards");
        string migratedSave = Save(restored); corrupt = Clone(legacySave); corrupt.exploration[0].claimed = new[] { "unknown.legacy" }; Check(restored.ImportSave(corrupt).message.StartsWith("Save rejected:") && Save(restored) == migratedSave, "invalid legacy claim rejected atomically");
        corrupt = Clone(restored.ExportSave()); corrupt.exploration[0].x = -1; Check(restored.ImportSave(corrupt).message.StartsWith("Save rejected:"), "corrupt current layout never enters legacy migration");
        Cmd(restored, "return_neighborhood"); string originalCampaign = Save(restored); Cmd(restored, "start_neighborhood");
        string alternateClass = restored.GetView().classes.First(c => c.enabled && !c.abilityIds.Contains("ability.katia_heavy_blow")).id;
        var changedClass = restored.Handle(new GameCommand { type = "set_class", unitId = "crawler.katia", classId = alternateClass });
        Check(changedClass.roster.Single(r => r.id == "crawler.katia").classId == alternateClass, "Katia selects an alternate optional class before rescue");
        Cmd(restored, "preview_neighborhood", prep.id, "preparation.engineering"); Cmd(restored, "confirm_neighborhood"); Command(restored, "start");
        var map = data.journey.floors.Single(f => f.encounter != null && f.encounter.exploration.id == data.neighborhood.sectorId).encounter.exploration;
        foreach (var interaction in data.neighborhood.interactions.Where(i => !i.camp))
        {
            var point = map.points.Single(p => p.id == interaction.pointId); Walk(restored, map, point.x, point.y);
            string choice = interaction.options.First().id;
            if (interaction.options.Any(o => o.id == "rescue.trained"))
            {
                string intact = Save(restored); var unqualified = Cmd(restored, "preview_neighborhood", interaction.id, choice, "crawler.mongo");
                Check(!unqualified.neighborhood.canConfirm && Save(restored) == intact, "unqualified rescue preview is rejected without mutation");
                var trained = Cmd(restored, "preview_neighborhood", interaction.id, choice, "crawler.katia");
                Check(trained.neighborhood.canConfirm && trained.neighborhood.forecast.rewardCount == 2 && Save(restored) == intact, "innate rescue skill works after optional class change and forecasts trained benefit");
                Cmd(restored, "cancel_neighborhood"); Check(Save(restored) == intact, "trained rescue cancellation changes no supplies or receipts");
            }
            var approach = Cmd(restored, "preview_neighborhood", interaction.id, choice, "crawler.katia"); Check(approach.neighborhood.canConfirm, "optional interaction previews legally " + interaction.id);
            var exact = approach.neighborhood.forecast.afterItems; Cmd(restored, "confirm_neighborhood"); Check(exact.All(e => restored.ExportSave().inventory.Single(i => i.itemId == e.itemId).count == e.count), "optional interaction commits exact combined rewards " + interaction.id);
            string receiptSave = Save(restored); var reload = new GameSession(content,data); Check(!reload.ImportSave(Clone(restored.ExportSave())).message.StartsWith("Save rejected:") && Save(reload)==receiptSave, "optional receipt reloads exactly " + interaction.id);
            Cmd(reload,"preview_neighborhood",interaction.id,choice,"crawler.katia");Cmd(reload,"confirm_neighborhood");Check(Save(reload)==receiptSave,"optional receipt cannot farm after reload " + interaction.id);
        }
        Check(restored.GetView().neighborhood.challenges.Count(c=>c.earned)==3 && restored.GetView().neighborhood.clues.Length>0,"all three committed challenges and useful clue recorded");
        foreach(var point in map.points.Where(p=>p.kind=="lore"&&!data.neighborhood.interactions.Any(i=>i.pointId==p.id))) {Walk(restored,map,point.x,point.y);Command(restored,"explore_interact",target:point.id);}
        var door=map.points.Single(p=>p.kind=="encounter");Walk(restored,map,door.x,door.y);Command(restored,"explore_interact",target:door.id);Check(restored.GetView().screen=="battle","completed neighborhood enters original turn-based encounter");
        PlayBattle(restored);Cmd(restored,"continue");Check(Save(restored)==originalCampaign,"victory continue restores original campaign exactly");
        Console.WriteLine(checks + " neighborhood checks passed.");
    }
}
