using System;
using System.IO;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;
using DungeonCrawlerTactics;
static class BookOneFloorTests
{
    static readonly JsonSerializerOptions Json = new JsonSerializerOptions { IncludeFields = true };
    static T Read<T>(string path) { return JsonSerializer.Deserialize<T>(File.ReadAllText(path), Json); }
    static void Check(bool okay, string message) { if (!okay) throw new Exception(message); Console.WriteLine("PASS " + message); }
    static void Main(string[] args)
    {
        string fixture = args.Length > 0 ? args[0] : "/tmp/book-one-floor-plan.json";
        GeneratedFloorPlan floor = Read<GeneratedFloorPlan>(fixture);
        Func<GameSession> session = () => new GameSession(Read<Content>(Path.Combine(AppContext.BaseDirectory, "combat-content.json")), Read<GameData>(Path.Combine(AppContext.BaseDirectory, "game-content.json")));
        GameSession game = session();
        GameView view = game.Handle(new GameCommand { type = "import_floor", floorPlan = floor });
        Check(view.screen == "explore" && view.generatedDungeon != null && view.width == 40 && view.height == 32, "Complete 40 x 32 Book 1 floor imports into shared C# exploration: " + view.message);
        Check(view.customMap.tiles.Length == floor.map.tiles.Length && view.customMap.tiles.Zip(floor.map.tiles, (a,b) => a.x==b.x && a.y==b.y && a.blocked==b.blocked && a.tags.SequenceEqual(b.tags)).All(x=>x), "Preview collision survives exact floor import");
        Check(view.generatedDungeon.floorPlan.groups.Length == floor.groups.Length && view.generatedDungeon.floorPlan.discoveries.Length == floor.discoveries.Length, "Every encounter and discovery enters authoritative state");
        string saved = JsonSerializer.Serialize(game.ExportSave(), Json);
        GameSession restored = session(); GameView loaded = restored.ImportSave(JsonSerializer.Deserialize<GameSave>(saved, Json));
        Check(loaded.screen == "explore" && JsonSerializer.Serialize(restored.ExportSave(), Json) == saved, "Complete realized floor and party save roundtrip exactly");
        GameSave nearExit = JsonSerializer.Deserialize<GameSave>(saved, Json);
        nearExit.generatedDungeon.x = floor.exit.x;
        nearExit.generatedDungeon.y = floor.exit.y;
        nearExit.generatedDungeon.revealed = nearExit.generatedDungeon.revealed.Concat(new[] { floor.exit }).GroupBy(c => c.x + "," + c.y).Select(g => g.First()).ToArray();
        GameSession gated = session();
        Check(gated.ImportSave(nearExit).screen == "explore", "Valid checkpoint can stand at the still-locked exit");
        string gatedSave = JsonSerializer.Serialize(gated.ExportSave(), Json);
        GameView locked = gated.Handle(new GameCommand { type = "explore_interact", targetId = "generated.exit" });
        Check(locked.screen == "explore" && JsonSerializer.Serialize(gated.ExportSave(), Json) == gatedSave, "Standing at the exit still requires encounter and objective completion");
        GeneratedFloorPlan invalid = Read<GeneratedFloorPlan>(fixture); invalid.groups[0].enemyIds = new[] { "custom.enemy.missing" };
        game.Handle(new GameCommand { type = "import_floor", floorPlan = invalid });
        Check(JsonSerializer.Serialize(game.ExportSave(), Json) == saved, "Invalid group reference preserves the active floor");
        GameSave corrupt = JsonSerializer.Deserialize<GameSave>(saved, Json); corrupt.generatedDungeon.claimedIds = new[] { "not-an-objective" };
        restored.ImportSave(corrupt);
        Check(JsonSerializer.Serialize(restored.ExportSave(), Json) == saved, "Unknown claimed objective is rejected transactionally");
        // Walk the actual realized corridors until C# detects the first visible group.
        CellView goal = new CellView { x = floor.groups[0].x, y = floor.groups[0].y };
        var queue = new List<CellView> { floor.entrance };
        var parents = new Dictionary<string, CellView> { [floor.entrance.x + "," + floor.entrance.y] = null };
        var open = new HashSet<string>(floor.map.tiles.Where(t => !t.blocked).Select(t => t.x + "," + t.y));
        for (int index = 0; index < queue.Count; index++) {
            CellView current = queue[index];
            if (current.x == goal.x && current.y == goal.y) break;
            foreach (CellView next in new[] { new CellView { x=current.x+1,y=current.y }, new CellView { x=current.x-1,y=current.y }, new CellView { x=current.x,y=current.y+1 }, new CellView { x=current.x,y=current.y-1 } }) {
                string key = next.x + "," + next.y;
                if (open.Contains(key) && !parents.ContainsKey(key)) { parents[key]=current; queue.Add(next); }
            }
        }
        var path = new List<CellView>();
        for (CellView cursor=goal; parents[cursor.x + "," + cursor.y]!=null; cursor=parents[cursor.x + "," + cursor.y]) path.Add(cursor);
        path.Reverse();
        foreach (CellView step in path) {
            view=game.Handle(new GameCommand { type="explore_move", x=step.x, y=step.y });
            if (view.screen=="battle") break;
        }
        Check(view.screen=="battle" && view.generatedDungeon.activeGroupId==floor.groups[0].id, "Walking the canonical corridor starts the first existing tactical encounter");
        string battleSave=JsonSerializer.Serialize(game.ExportSave(),Json);
        restored=session(); loaded=restored.ImportSave(JsonSerializer.Deserialize<GameSave>(battleSave,Json));
        Check(loaded.screen=="battle" && JsonSerializer.Serialize(restored.ExportSave(),Json)==battleSave, "Reload resumes the exact active tactical encounter and party");
        for (int turn=0; turn<160 && game.GetView().screen=="battle"; turn++) {
            view=game.GetView();
            UnitView actor=view.units.FirstOrDefault(u=>u.team=="player" && u.hp>0 && !u.finished);
            if(actor==null) {game.Handle(new GameCommand{type="end_turn"});continue;}
            view=game.Handle(new GameCommand{type="select",unitId=actor.id});
            if(view.canMove) {
                UnitView target=view.units.Where(u=>u.team=="enemy"&&u.hp>0).OrderBy(u=>Math.Abs(u.x-actor.x)+Math.Abs(u.y-actor.y)).First();
                CellView move=view.reachable.OrderBy(c=>Math.Abs(c.x-target.x)+Math.Abs(c.y-target.y)).ThenBy(c=>c.cost).FirstOrDefault();
                if(move!=null)view=game.Handle(new GameCommand{type="move",x=move.x,y=move.y});
            }
            var enemyIds=new HashSet<string>(view.units.Where(u=>u.team=="enemy"&&u.hp>0).Select(u=>u.id));
            AbilityView ability=view.abilities.FirstOrDefault(a=>a.enabled&&a.targetIds.Any(enemyIds.Contains));
            if(ability!=null) {
                game.Handle(new GameCommand{type="preview",abilityId=ability.id,targetId=ability.targetIds.First(enemyIds.Contains)});
                view=game.Handle(new GameCommand{type="confirm"});
            }
            if(view.screen=="battle")game.Handle(new GameCommand{type="end_turn"});
        }
        Check(game.GetView().screen=="victory", "The adapted first encounter resolves through existing movement and ability commands");
        view=game.GetView();
        if(view.rewards.Length>0)game.Handle(new GameCommand{type="choose_reward",rewardId=view.rewards[0].id});
        view=game.Handle(new GameCommand{type="continue"});
        Check(view.screen=="explore" && view.generatedDungeon.defeatedGroupIds.Contains(floor.groups[0].id), "Victory and reward return the same party to the continuous floor");
        string resumed=JsonSerializer.Serialize(game.ExportSave(),Json);
        restored=session();loaded=restored.ImportSave(JsonSerializer.Deserialize<GameSave>(resumed,Json));
        Check(loaded.screen=="explore"&&JsonSerializer.Serialize(restored.ExportSave(),Json)==resumed,"Post-battle floor receipts, resources and party resume exactly");
        Console.WriteLine("Book 1 complete-floor shared C# contract passed.");
    }
}
