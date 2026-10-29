using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using DungeonCrawlerTactics;
static class CampaignTests
{
    static readonly JsonSerializerOptions Json = new JsonSerializerOptions { IncludeFields = true };
    static Content content;
    static GameData data;
    static int checks;
    static T Clone<T>(T value) { return JsonSerializer.Deserialize<T>(JsonSerializer.Serialize(value, Json), Json); }
    static GameSession Session() { return new GameSession(Clone(content), Clone(data)); }
    static string Save(GameSession game) { return JsonSerializer.Serialize(game.ExportSave(), Json); }
    static void Check(bool condition, string label) { if (!condition) throw new Exception(label); checks++; Console.WriteLine("PASS " + label); }
    static void Roundtrip(GameSession game, string label)
    {
        GameSession copy = Session();
        GameView view = copy.ImportSave(Clone(game.ExportSave()));
        Check(!view.message.StartsWith("Save rejected:") && Save(copy) == Save(game), label);
    }
    static GeneratedFloorPlan Floor(int depth)
    {
        return new GeneratedFloorPlan {
            seed = depth,
            map = new CustomMapData { label = "Adapted expedition depth " + depth, width = 8, height = 6,
                enemies = new[] { new SpawnDef { id = "custom.enemy.guard", label = "Guard", classId = "class.brawler", artId = "rat", x = 4, y = 0, hp = 1, energy = 1, move = 1 } } },
            entrance = new CellView { x = 0, y = 0 }, exit = new CellView { x = 7, y = 0 },
            groups = new[] { new GeneratedEncounterGroup { id = "watch", label = "Watch", kind = "visible", x = 3, y = 0, enemyIds = new[] { "custom.enemy.guard" } } },
            discoveries = new[] { new ExplorationPointDef { id = "seal", label = "Seal", description = "Seal recovered.", kind = "objective", x = 0, y = 0 } }
        };
    }
    static GeneratedCampaignPlan Plan() { return new GeneratedCampaignPlan { id = "test.route", label = "Adapted depths", floors = new[] { Floor(1), Floor(2), Floor(3) } }; }
    static void ClearFloor(GameSession game)
    {
        game.Handle(new GameCommand { type = "explore_interact", targetId = "seal" });
        game.Handle(new GameCommand { type = "explore_step", x = 1 });
        Check(game.GetView().screen == "battle", "approach enters existing tactical combat");
        Roundtrip(game, "battle checkpoint exact");
        bool struck = false;
        foreach (UnitView unit in game.GetView().units.Where(u => u.team == "player").ToArray())
        {
            GameView view = game.Handle(new GameCommand { type = "select", unitId = unit.id });
            AbilityView hit = view.abilities.FirstOrDefault(a => a.enabled && a.targetIds.Contains("custom.enemy.guard"));
            if (hit == null) continue;
            game.Handle(new GameCommand { type = "preview", abilityId = hit.id, targetId = "custom.enemy.guard" });
            game.Handle(new GameCommand { type = "confirm" });
            struck = true;
            break;
        }
        Check(struck && game.GetView().screen == "victory", "combat resolves normally");
        Roundtrip(game, "victory checkpoint exact");
        game.Handle(new GameCommand { type = "choose_reward", rewardId = data.rewards[0].id });
        game.Handle(new GameCommand { type = "continue" });
        Roundtrip(game, "reward return checkpoint exact");
        while (game.GetView().generatedDungeon.x < 7) game.Handle(new GameCommand { type = "explore_step", x = 1 });
        while (game.GetView().generatedDungeon.y > 0) game.Handle(new GameCommand { type = "explore_step", y = -1 });
    }
    static void Reject(GameSession game, Action<GameSave> corrupt, string label)
    {
        string before = Save(game);
        GameSave candidate = Clone(game.ExportSave());
        corrupt(candidate);
        Check(game.ImportSave(candidate).message.StartsWith("Save rejected:") && Save(game) == before, label);
    }
    static void Main()
    {
        content = JsonSerializer.Deserialize<Content>(File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "combat-content.json")), Json);
        data = JsonSerializer.Deserialize<GameData>(File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "game-content.json")), Json);
        GameSession game = Session();
        GameView initial = game.Handle(new GameCommand { type = "import_campaign", campaignPlan = Plan() });
        Check(initial.generatedCampaign != null && initial.generatedCampaign.totalFloors == 3, "three generated depths import upfront");
        Roundtrip(game, "new run checkpoint exact");
        string before = Save(game);
        GeneratedCampaignPlan bad = Plan(); bad.floors[2].exit.x = -1;
        game.Handle(new GameCommand { type = "import_campaign", campaignPlan = bad });
        Check(Save(game) == before, "invalid future map rejects whole new run");
        foreach (string command in new[] { "scenario_start", "expedition_start", "start_neighborhood" })
        {
            game.Handle(new GameCommand { type = command }); Check(Save(game) == before, "optional mode rejects before mutation: " + command);
        }
        for (int depth = 0; depth < 3; depth++)
        {
            ClearFloor(game);
            if (depth == 0)
            {
                EquipmentDef gear = data.equipment.First(e => e.unlockEncounter <= 1);
                game.Handle(new GameCommand { type = "equip", equipmentId = gear.id, unitId = game.ExportSave().roster.First(r => r.selected).id });
                Check(game.ExportSave().equipped.Any(e => e.equipmentId == gear.id), "earned gear equipped before descent");
                Roundtrip(game, "equipped generated campaign checkpoint exact");
            }
            before = Save(game);
            game.Handle(new GameCommand { type = "explore_interact", targetId = "generated.exit" });
            Check(Save(game) == before, "exit interaction only announces readiness");
            game.Handle(new GameCommand { type = "preview_descent" });
            Check(game.GetView().generatedCampaign.canConfirmDescent && Save(game) == before, "descent preview leaves authoritative state unchanged");
            game.Handle(new GameCommand { type = "cancel_descent" });
            Check(Save(game) == before && !game.GetView().generatedCampaign.canConfirmDescent, "cancel clears preview without mutation");
            game.Handle(new GameCommand { type = "confirm_descent" }); Check(Save(game) == before, "canceled confirmation rejects");
            game.Handle(new GameCommand { type = "preview_descent" });
            game.Handle(new GameCommand { type = "explore_step", x = 9 });
            game.Handle(new GameCommand { type = "confirm_descent" }); Check(Save(game) == before, "intervening command invalidates descent");
            game.Handle(new GameCommand { type = "return_safe" }); Roundtrip(game, "home checkpoint exact");
            game.Handle(new GameCommand { type = "resume_floor" }); Check(Save(game) == before, "home resume keeps same depth");
            GameSave shortParty = Clone(game.ExportSave()); shortParty.screen = "camp";
            shortParty.roster.First(r => r.selected).selected = false;
            GameSession partial = Session(); partial.ImportSave(shortParty);
            string partialBefore = Save(partial);
            partial.Handle(new GameCommand { type = "preview_descent" });
            Check(Save(partial) == partialBefore && !partial.GetView().generatedCampaign.canDescend, "descent requires full selected party");
            GameSave checkpoint = Clone(game.ExportSave());
            checkpoint.roster.First(r => r.selected).hp = 1;
            checkpoint.roster.First(r => r.selected).energy = 0;
            Check(!game.ImportSave(checkpoint).message.StartsWith("Save rejected:"), "wounded checkpoint valid");
            game.Handle(new GameCommand { type = "preview_descent" });
            GameSession reloadedPreview = Session();
            reloadedPreview.ImportSave(Clone(game.ExportSave()));
            string reloadedBefore = Save(reloadedPreview);
            reloadedPreview.Handle(new GameCommand { type = "confirm_descent" });
            Check(Save(reloadedPreview) == reloadedBefore, "reload requires a fresh descent preview");
            GameSave state = game.ExportSave();
            game.Handle(new GameCommand { type = "confirm_descent" });
            Check(game.ExportSave().roster.Select(r => r.hp + ":" + r.energy).SequenceEqual(state.roster.Select(r => r.hp + ":" + r.energy)), "descent grants no healing or mana");
            Check(JsonSerializer.Serialize(game.ExportSave().inventory, Json) == JsonSerializer.Serialize(state.inventory, Json) && JsonSerializer.Serialize(game.ExportSave().development, Json) == JsonSerializer.Serialize(state.development, Json) && JsonSerializer.Serialize(game.ExportSave().equipped, Json) == JsonSerializer.Serialize(state.equipped, Json), "descent preserves supplies gear and practice");
            before = Save(game); game.Handle(new GameCommand { type = "confirm_descent" }); Check(Save(game) == before, "duplicate descent rejects");
            Roundtrip(game, "post-descent checkpoint exact");
            Reject(game, s => s.generatedCampaign.floorIndex = -1, "negative campaign index rejected");
            Reject(game, s => s.xp++, "forged cumulative XP rejected");
            Reject(game, s => s.generatedCampaign.plan.floors[s.generatedCampaign.floorIndex].map.enemies[0].hp++, "plan mutation rejected");
            if (depth > 0) Reject(game, s => s.generatedCampaign.archives[0].defeatedGroupIds = new string[0], "incomplete archive rejected");
        }
        Check(game.GetView().screen == "complete" && game.GetView().generatedCampaign.completedFloors == 3, "final exit completes generated expedition");
        GameSession legacy = Session(); Check(legacy.Handle(new GameCommand { type = "import_floor", floorPlan = Floor(1) }).generatedCampaign == null, "standalone floor remains supported");
        Console.WriteLine("PASS " + checks + " generated campaign checks.");
    }
}
