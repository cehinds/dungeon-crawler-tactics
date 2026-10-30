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
    static int checks; static bool claimGear;
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
        RewardView offered = game.GetView().rewards.FirstOrDefault(r => !string.IsNullOrEmpty(r.equipmentId));
        if (offered != null)
        {
            Check(game.GetView().rewards.Count(r => !string.IsNullOrEmpty(r.equipmentId)) == 3 && game.GetView().rewards.Any(r => r.id == data.rewards[0].id), "third battle offers three gear choices alongside supplies");
            GameSession supplies = Session(); supplies.ImportSave(Clone(game.ExportSave()));
            supplies.Handle(new GameCommand { type = "choose_reward", rewardId = data.rewards[0].id });
            Check(supplies.ExportSave().equipmentRewardClaims.Length == 0 && supplies.GetView().rewards.Length == 0, "supplies consume the single choice without claiming gear");
        }
        game.Handle(new GameCommand { type = "choose_reward", rewardId = claimGear && offered != null ? offered.id : data.rewards[0].id });
        if (claimGear && offered != null)
        {
            Check(game.ExportSave().equipmentRewardClaims.Length == 1 && game.GetView().equipment.First(g => g.id == offered.equipmentId).owned, "equipment claim grants ownership");
            game.Handle(new GameCommand { type = "choose_reward", rewardId = offered.id });
            Check(game.ExportSave().equipmentRewardClaims.Length == 1, "duplicate choice cannot reclaim equipment");
            Reject(game, save => save.equipmentRewardClaims = new[] { save.equipmentRewardClaims[0], save.equipmentRewardClaims[0] }, "duplicate tier claims rejected");
            Reject(game, save => save.rewardChosen = false, "active victory claim requires chosen receipt");
        }
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
        GameSession game = Session(); string unit = game.GetView().roster.First(r => r.deployable).id;
        string gear = data.equipment.First(g => !g.rewardOnly && g.unlockEncounter == 0).id;
        GameView preview = game.Handle(new GameCommand { type = "preview_equipment", unitId = unit, equipmentId = gear });
        Check(preview.equipmentPreview != null, "equipment preview available");
        EquipmentStatsView predicted = preview.equipmentPreview.after;
        game.Handle(new GameCommand { type = "confirm_equipment" });
        RosterView member = game.GetView().roster.First(r => r.id == unit);
        Check(member.maxHp == predicted.maxHp && member.maxEnergy == predicted.maxEnergy && member.hp == predicted.hp && member.energy == predicted.energy && member.move == predicted.move, "preview equals commit without healing");
        game.Handle(new GameCommand { type = "preview_unequip", unitId = unit, equipmentId = gear });
        EquipmentPreviewView removal = game.GetView().equipmentPreview;
        game.Handle(new GameCommand { type = "confirm_equipment" });
        member = game.GetView().roster.First(r => r.id == unit);
        Check(member.maxHp == removal.after.maxHp && member.maxEnergy == removal.after.maxEnergy && member.hp == removal.after.hp && member.energy == removal.after.energy, "unequip preview matches caps and clamps without healing");
        game.Handle(new GameCommand { type = "equip", unitId = unit, equipmentId = gear });
        game.Handle(new GameCommand { type = "preview_unequip", unitId = unit, equipmentId = gear });
        game.Handle(new GameCommand { type = "cancel_equipment" });
        Check(game.GetView().equipmentPreview == null && game.ExportSave().equipped.Any(e => e.equipmentId == gear), "cancel preserves loadout");
        game.Handle(new GameCommand { type = "preview_unequip", unitId = unit, equipmentId = gear });
        game.Handle(new GameCommand { type = "safe_room_rest" });
        game.Handle(new GameCommand { type = "confirm_equipment" });
        Check(game.ExportSave().equipped.Any(e => e.equipmentId == gear), "intervening command invalidates preview");
        Reject(game, s => s.equipmentRewardClaims = new[] { new EquipmentRewardClaim { tierId = data.equipmentRewardTiers[0].id, equipmentId = data.equipmentRewardTiers[0].equipmentIds[0] } }, "forged early reward claim rejected");
        Roundtrip(game, "equipment save exact");
        GameSave legacy = Clone(game.ExportSave()); legacy.equipmentRewardClaims = null;
        Check(!Session().ImportSave(legacy).message.StartsWith("Save rejected:"), "missing legacy claims accepted");
        GeneratedCampaignPlan plan = Plan(); for (int i = 0; i < plan.floors.Length; i++) plan.floors[i].groups[0].rewardXp = 30 + i * 10;
        game = Session(); game.Handle(new GameCommand { type = "import_campaign", campaignPlan = plan });
        // The public campaign command keeps the realized plan and explicit XP in save receipts.
        if (game.ExportSave().generatedCampaign == null) game.Handle(new GameCommand { type = "import_campaign", campaignPlan = plan });
        Check(game.ExportSave().generatedCampaign != null, "explicit XP campaign starts");
        claimGear = true; int total = 0;
        for (int depth = 0; depth < 3; depth++)
        {
            ClearFloor(game); total += 30 + depth * 10;
            Check(game.GetView().xp == total, "explicit depth XP milestone " + depth);
            Reject(game, s => s.xp++, "forged XP rejected " + depth);
            if (depth < 2) { game.Handle(new GameCommand { type = "preview_descent" }); game.Handle(new GameCommand { type = "confirm_descent" }); }
        }
        string earned = game.ExportSave().equipmentRewardClaims[0].equipmentId;
        string ability = data.equipment.First(g => g.id == earned).abilityIds[0];
        GameView equipView = game.Handle(new GameCommand { type = "preview_equipment", unitId = unit, equipmentId = earned });
        Check(equipView.equipmentPreview.gainedAbilityIds.Contains(ability), "earned gear previews its granted ability");
        game.Handle(new GameCommand { type = "confirm_equipment" });
        GameView removeView = game.Handle(new GameCommand { type = "preview_unequip", unitId = unit, equipmentId = earned });
        Check(removeView.equipmentPreview.lostAbilityIds.Contains(ability), "removing gear previews lost granted ability");
        EquipmentStatsView removalStats = removeView.equipmentPreview.after;
        game.Handle(new GameCommand { type = "confirm_equipment" });
        member = game.GetView().roster.First(r => r.id == unit);
        Check(member.hp == removalStats.hp && member.energy == removalStats.energy && !game.ExportSave().equipped.Any(e => e.equipmentId == earned), "earned gear removal commits without healing");
        Console.WriteLine(checks + " equipment progression checks passed.");
    }
}
