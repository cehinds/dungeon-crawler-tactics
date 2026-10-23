using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using DungeonCrawlerTactics;

static class HomeTests
{
    static readonly JsonSerializerOptions Json = new JsonSerializerOptions { IncludeFields = true };
    static Content content;
    static GameData data;
    static int checks;
    static T Clone<T>(T value) { return JsonSerializer.Deserialize<T>(JsonSerializer.Serialize(value, Json), Json); }
    static GameSession Session() { return new GameSession(Clone(content), Clone(data)); }
    static string Save(GameSession game) { return JsonSerializer.Serialize(game.ExportSave(), Json); }
    static GameView Command(GameSession game, string type, string target = null, string unit = null, string ability = null)
    {
        return game.Handle(new GameCommand { type = type, targetId = target, unitId = unit, abilityId = ability });
    }
    static void Check(bool pass, string label) { if (!pass) throw new Exception(label); checks++; Console.WriteLine("PASS " + label); }
    static void Buy(GameSession game, string id)
    {
        string before = Save(game);
        GameView preview = Command(game, "preview_home_upgrade", id);
        Check(preview.home.canConfirm && Save(game) == before, id + " preview spends nothing");
        int expected = preview.home.forecast.afterGold;
        GameView committed = Command(game, "confirm_home_upgrade");
        Check(committed.home.gold == expected && committed.home.upgrades.Any(u => u.id == id && u.purchased), id + " commits exact forecast");
    }
    static HomeUpgradeDef Upgrade(string id, string kind, int cost, string parent = "home.space", int bonus = 0)
    {
        return new HomeUpgradeDef { id = id, label = id, description = "Synthetic economy test fixture.", kind = kind, cost = cost, prerequisiteId = parent, craftOutputBonus = bonus, priceBasis = "adaptation", costNote = "Test fixture, not a canonical price." };
    }
    static void Main()
    {
        content = JsonSerializer.Deserialize<Content>(File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "combat-content.json")), Json);
        data = JsonSerializer.Deserialize<GameData>(File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "game-content.json")), Json);
        data.home = new HomeDef { label = "Test home", description = "Home behavior fixture", economyNote = "All fixture gold values are adaptations.", startingGold = 1000, victoryGoldBase = 100, victoryGoldPerFloor = 10, trainingGoldCost = 10, trainingUses = 1, trainingAbilityIds = new[] { "ability.carl_powerful_strike" }, clubs = new[] {
            new HomeClubDef { id = "club.desperado", label = "Desperado Club", description = "Personal class-based membership; pets excluded. This fixture records admission information only.", minimumFloor = 3, eligibleClassIds = new[] { "class.compensated_anarchist", "class.lore_compensated_anarchist" }, excludedRosterIds = new[] { "crawler.mongo" }, sourceIds = new[] { "source.desperado" } }
        }, upgrades = new[] {
            Upgrade("home.space", "space", 100, null), Upgrade("home.training", "training", 200), Upgrade("home.table", "crafting", 50), Upgrade("home.tools", "tools", 50, "home.table", 1), Upgrade("home.social", "social", 50),
            new HomeUpgradeDef { id = "home.club", label = "Desperado membership", description = "Personal earned membership, never a universal pass.", kind = "club", purchasable = false, eligibilityReason = "Requires a personal earned membership tattoo; pets cannot enter. A purchasable party pass is unavailable.", priceBasis = "unknown", costNote = "No established purchase price." }
        } };
        foreach (EncounterDef encounter in data.encounters)
        {
            encounter.tiles = new TileDef[0]; encounter.playerSpawns = new[] { new CellView { x = 1, y = 1 }, new CellView { x = 1, y = 2 }, new CellView { x = 2, y = 1 }, new CellView { x = 2, y = 2 } };
            SpawnDef enemy = encounter.enemies[0]; enemy.x = 3; enemy.y = 1; enemy.hp = 1; encounter.enemies = new[] { enemy };
            encounter.exploration = new ExplorationDef { id = encounter.exploration.id, label = "Test passage", width = 4, height = 4, startX = 0, startY = 0, points = new[] { new ExplorationPointDef { id = "point.test_door", label = "Door", description = "Fixture door", kind = "encounter", x = 0, y = 0 } } };
        }
        GameSession game = Session();
        Check(game.GetView().home.rooms.Count(r => r.kind == "bedroom") == data.roster.Count(r => r.deployable), "Every deployable crawler has an assigned private bedroom");
        Check(!game.GetView().home.rooms.Any(r => r.unlocked), "Bedrooms and shared rooms begin unowned");
        string original = Save(game);
        Check(Command(game, "preview_home_upgrade", "home.tools").message.Contains("Requires") && Save(game) == original, "Missing crafting-table prerequisite is atomic");
        Check(Command(game, "preview_home_upgrade", "home.club").message.Contains("tattoo") && Save(game) == original, "Unknown-price club access is blocked by its real membership requirement");
        Command(game, "preview_home_upgrade", "home.space"); Command(game, "cancel_home_upgrade");
        Check(Save(game) == original && !game.GetView().home.canConfirm, "Cancel leaves gold and installed upgrades unchanged");
        Check(Command(game, "preview_home_membership", "club.desperado", "crawler.donut").message.Contains("current class") && Save(game) == original, "A nonqualifying class cannot claim a club credential");
        Check(Command(game, "preview_home_membership", "club.desperado", "crawler.mongo").message.Contains("pets") && Save(game) == original, "Club pet exclusion blocks Mongo before any credential is issued");
        GameView membershipPreview = Command(game, "preview_home_membership", "club.desperado", "crawler.carl");
        Check(membershipPreview.home.forecast.type == "membership" && membershipPreview.home.forecast.cost == 0 && membershipPreview.home.forecast.beforeGold == membershipPreview.home.forecast.afterGold && Save(game) == original, "Class-granted personal membership has a pure zero-gold forecast");
        Command(game, "cancel_home_membership"); Check(Save(game) == original, "Cancel membership leaves the crawler and gold unchanged");
        Command(game, "preview_home_membership", "club.desperado", "crawler.carl"); Command(game, "confirm_home_membership");
        Check(game.ExportSave().home.memberships.Length == 1 && game.GetView().home.memberships.Single(m => m.earned).unitId == "crawler.carl" && game.GetView().home.memberships.Single(m => m.earned).entryEligible && game.GetView().home.gold == 1000 && !game.GetView().home.owned, "A qualifying class earns only that crawler's credential without buying the shared home or a party pass");
        GameSave credential = Clone(game.ExportSave()); string credentialSave = Save(game);
        Command(game, "confirm_home_membership"); Check(Save(game) == credentialSave, "Repeated membership confirmation cannot duplicate a credential");
        game.Handle(new GameCommand { type = "set_class", unitId = "crawler.carl", classId = "class.guardian" });
        Check(game.GetView().home.memberships.Single(m => m.earned).earned && !game.GetView().home.memberships.Single(m => m.earned).entryEligible && game.GetView().home.memberships.Single(m => m.earned).entryDisabledReason.Contains("current class"), "Switching class retains the credential while current admission becomes blocked");
        GameSession switchedReload = Session(); Check(!switchedReload.ImportSave(Clone(game.ExportSave())).message.StartsWith("Save rejected:") && !switchedReload.GetView().home.memberships.Single(m => m.earned).entryEligible, "Historical membership provenance survives reload after class eligibility changes");
        game.ImportSave(credential);
        GameSave petForgery = Clone(game.ExportSave()); petForgery.home.memberships[0].unitId = "crawler.mongo"; string beforePetForgery = Save(game);
        Check(game.ImportSave(petForgery).message.StartsWith("Save rejected:") && Save(game) == beforePetForgery, "Import cannot assign a personal club credential to an excluded pet");
        Buy(game, "home.space"); Buy(game, "home.training"); Buy(game, "home.table"); Buy(game, "home.tools"); Buy(game, "home.social");
        Check(game.GetView().home.rooms.All(r => r.unlocked), "Purchased home exposes private bedrooms plus real training and crafting rooms");
        string installed = Save(game);
        Command(game, "confirm_home_upgrade"); Command(game, "preview_home_upgrade", "home.tools");
        Check(Save(game) == installed, "Repeat confirm and duplicate purchase cannot spend gold twice");
        GameView previewTraining = Command(game, "preview_home_training", unit: "crawler.carl", ability: "ability.carl_powerful_strike");
        Check(previewTraining.home.forecast.type == "training" && previewTraining.home.forecast.afterUses == 1 && Save(game) == installed, "Paid training previews exact practice and gold without mutation");
        Command(game, "cancel_home_training"); Check(Save(game) == installed, "Cancel training is free");
        Command(game, "preview_home_training", unit: "crawler.carl", ability: "ability.carl_powerful_strike"); Command(game, "confirm_home_training");
        Check(game.ExportSave().development.practice.Any(p => p.unitId == "crawler.carl" && p.uses == 1) && game.GetView().home.gold == 540, "Training purchase grants actual saved skill practice");
        string trained = Save(game); Command(game, "preview_home_training", unit: "crawler.carl", ability: "ability.carl_powerful_strike");
        Check(Save(game) == trained && game.GetView().message.Contains("already trained"), "Training cannot be repeated by the same crawler on one floor");
        RecipeView recipe = game.GetView().development.recipes.First(r => r.enabled);
        int outputBefore = game.ExportSave().inventory.First(i => i.itemId == recipe.outputs[0].itemId).count;
        GameView crafted = game.Handle(new GameCommand { type = "craft", recipeId = recipe.id });
        Check(recipe.outputs[0].count == data.development.recipes.First(r => r.id == recipe.id).outputs[0].count + 1 && game.ExportSave().inventory.First(i => i.itemId == recipe.outputs[0].itemId).count == outputBefore + recipe.outputs[0].count, "Installed tools change the exact displayed and committed recipe output");
        GameSave checkpoint = Clone(game.ExportSave()); GameSession reload = Session();
        Check(!reload.ImportSave(checkpoint).message.StartsWith("Save rejected:") && Save(reload) == Save(game), "Home purchases, gold and training roundtrip exactly");
        string beforeInvalid = Save(game); GameSave forged = Clone(game.ExportSave()); forged.home.gold++;
        Check(game.ImportSave(forged).message.StartsWith("Save rejected:") && Save(game) == beforeInvalid, "Unfunded gold import is rejected without changing live state");
        forged = Clone(game.ExportSave()); forged.home.training = forged.home.training.Concat(forged.home.training).ToArray();
        Check(game.ImportSave(forged).message.StartsWith("Save rejected:") && Save(game) == beforeInvalid, "Repeated training receipts cannot forge practice or gold accounting");
        string campaign = Save(game); Command(game, "expedition_start", data.expeditions[0].id);
        Check(game.GetView().expedition != null, "An equipped home campaign can enter an isolated expedition");
        GameSave expedition = Clone(game.ExportSave()); reload = Session();
        Check(!reload.ImportSave(expedition).message.StartsWith("Save rejected:") && Save(reload) == Save(game), "Nested expedition saves preserve the home ledger exactly");
        expedition.home.gold++;
        Check(reload.ImportSave(expedition).message.StartsWith("Save rejected:"), "Expedition cannot edit its campaign gold ledger");
        Command(game, "expedition_return"); Check(Save(game) == campaign, "Returning from expedition restores purchases, gold and training exactly");
        Command(game, "scenario_start", data.scenarios[0].id);
        Check(game.GetView().scenario != null && game.GetView().home.gold == 540, "An isolated boss scenario preserves the campaign home ledger");
        reload = Session(); Check(!reload.ImportSave(Clone(game.ExportSave())).message.StartsWith("Save rejected:"), "A nested boss scenario can reload after paid home training");
        GameSave oldScenario = Clone(game.ExportSave()); oldScenario.home = null; oldScenario.scenario.campaign.home = null; reload = Session();
        Check(!reload.ImportSave(oldScenario).message.StartsWith("Save rejected:") && reload.GetView().home.gold == 1000, "Pre-home scenario files migrate their campaign ledger without invented paid training receipts");
        Command(game, "scenario_return"); Check(Save(game) == campaign, "Returning from boss scenario restores purchases, gold and training exactly");
        Command(game, "start"); Command(game, "explore_interact", "point.test_door");
        Check(game.GetView().screen == "battle", "Legal fixture exploration enters combat");
        int balance = game.GetView().home.gold;
        Command(game, "preview", data.encounters[0].enemies[0].id, "crawler.donut", "ability.donut_magic_missile"); Command(game, "confirm");
        Check(game.GetView().screen == "victory" && game.GetView().home.gold == balance + 110 && game.ExportSave().home.victoryReceiptIds.Length == 1, "A real committed victory awards its authored gold deposit once");
        balance = game.GetView().home.gold; Command(game, "confirm"); Command(game, "wait", unit: "crawler.donut");
        Check(game.GetView().home.gold == balance, "Further commands cannot farm the settled victory deposit");
        reload = Session(); Check(!reload.ImportSave(Clone(game.ExportSave())).message.StartsWith("Save rejected:"), "Victory receipt and ledger survive reload");
        forged = Clone(game.ExportSave()); forged.home.victoryReceiptIds = forged.home.victoryReceiptIds.Concat(forged.home.victoryReceiptIds).ToArray(); beforeInvalid = Save(game);
        Check(game.ImportSave(forged).message.StartsWith("Save rejected:") && Save(game) == beforeInvalid, "A duplicate victory receipt cannot duplicate its gold award");
        foreach (RewardView reward in game.GetView().rewards.Take(1)) game.Handle(new GameCommand { type = "choose_reward", rewardId = reward.id });
        Command(game, "continue");
        Check(game.GetView().screen == "camp" && game.GetView().home.owned && game.GetView().home.gold == balance && game.GetView().home.training.Any(t => t.enabled), "Home and gold persist to the next encounter and unlock the next floor's training allowance");
        GameSave legacy = Clone(game.ExportSave()); legacy.home = null; reload = Session();
        Check(!reload.ImportSave(legacy).message.StartsWith("Save rejected:") && reload.GetView().home.gold == 1110 && reload.ExportSave().home.victoryReceiptIds.Length == 1, "Legacy saves migrate existing victories into a single funded ledger");
        GameSession story = Session(); Command(story, "start_journey"); string storyBefore = Save(story);
        Check(Command(story, "preview_home_upgrade", "home.space").message.Contains("floor 4") && Save(story) == storyBefore, "The party shared house unlocks on the authored story floor");
        Check(Command(story, "preview_home_membership", "club.desperado", "crawler.carl").message.Contains("floor 3") && Save(story) == storyBefore, "Class-based club credentials respect their independent floor-three requirement");
        Check(story.GetView().development.recipes.All(r => !r.enabled && r.disabledReason.Contains("Table")), "Story crafting requires the actual purchased Engineer's Table");
        Console.WriteLine("PASS " + checks + " home checks.");
    }
}
