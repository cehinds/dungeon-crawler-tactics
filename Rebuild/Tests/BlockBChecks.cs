using DccRebuild;

static class BlockBChecks
{
    static void Check(bool ok, string label) { if (!ok) throw new Exception("Block B: " + label); }
    static void Near(Game game, string id)
    {
        var v = game.GetView(); var o = v.world.objects.Single(o => o.id == id);
        v.x = o.x; v.y = o.y;
    }
    static Game Encounter(string json)
    {
        var game = new Game(json, 71); Near(game, "false-guild");
        game.Handle(new() { type = "interact", targetId = "false-guild" }); return game;
    }
    static string Economy(View v) => Codec.Write(new { v.gold, v.inventory, party = v.party.Select(u => new { u.id, u.xp, u.level, u.power, u.armor, u.equipment }) });
    static void Win(Game game)
    {
        var v = game.GetView(); var actor = v.party[0]; var enemy = v.battle.enemies[0];
        v.battle.obstacles = []; v.battle.effectObjects.Clear();
        actor.x = 1; actor.y = 1; enemy.x = 2; enemy.y = 1; enemy.hp = 1;
        foreach (var other in v.battle.enemies.Skip(1)) other.hp = 0;
        game.Handle(new() { type = "confirm", actorId = actor.id, targetId = enemy.id, skillId = "punch" });
        Check(v.mode == "explore", "fixture resolves a real victory");
    }
    public static void Run(string json)
    {
        Rewards(json); EnemyPhases(json); Consumables(json); Preparation(json); StartingGear(json); ContentContracts(json);
        Console.WriteLine("PASS: Block B reward exact-once/save/retry, contextual navigation, consumable validity, enemy reachability and animated parity/input locks.");
    }
    static void Rewards(string json)
    {
        var game = Encounter(json); var v = game.GetView(); int gold = v.gold;
        var initialInventory = v.inventory.ToDictionary(s => s.itemId, s => s.count);
        var xp = v.party.Select(u => u.xp).ToArray(); Win(game);
        var receipt = v.reward;
        Check(receipt?.sourceId == "false-guild" && receipt.sourceKind == "encounter", "victory exposes encounter receipt");
        Check(receipt.gold == v.gold - gold && receipt.party.Length == 2 && receipt.party.All(p => p.xp == v.party.Single(u => u.id == p.actorId).xp - xp[Array.FindIndex(v.party.ToArray(), u => u.id == p.actorId)]), "receipt reports actual gold and per-actor XP");
        Check(receipt.items.Length > 0 && receipt.items.All(s => v.inventory.Single(i => i.itemId == s.itemId).count - initialInventory.GetValueOrDefault(s.itemId) == s.count), "encounter item receipt reports exact inventory delta");
        var earned = Economy(v); game.Handle(new() { type = "acknowledgeReward" }); game.Handle(new() { type = "acknowledgeReward" });
        Check(v.reward == null && Economy(v) == earned, "acknowledgement is idempotent and grants nothing");
        game.Handle(new() { type = "interact", targetId = "false-guild" });
        Check(v.mode == "explore" && Economy(v) == earned, "cleared encounter cannot grant twice");
        Near(game, "mordecai"); game.Handle(new() { type = "interact", targetId = "mordecai" });
        Check(game.GetView().objective != null && v.nearestSafe?.distance >= 0 && v.nearestSafe.id != "", "objective and reachable safe route are contextual views");
        var cache = v.world.objects.First(o => o.kind == "chest"); Near(game, cache.id); game.Handle(new() { type = "interact", targetId = cache.id });
        Check(v.reward?.sourceId == cache.id && v.reward.sourceKind == "cache" && v.reward.items.Length > 0, "cache exposes actual item receipt");
        earned = Economy(v); game.Handle(new() { type = "interact", targetId = cache.id });
        Check(Economy(v) == earned, "cache cannot grant twice");
        Near(game, "safe-room"); game.GetView();
        Check(v.nearbyInteractions.Any(i => i.id == "safe-room" && i.available), "nearby safe action exposes eligibility");
        v.party[0].hp = 1; v.party[0].mp = 0; v.party[0].moved = v.party[0].acted = v.party[0].ended = true;
        game.Handle(new() { type = "rest" });
        Check(v.party.All(u => u.hp == u.maxHp && u.mp == u.maxMp && !u.moved && !u.acted && !u.ended), "rest restores resources and clears combat flags");
        var save = game.GetSave(); var loaded = new Game(json); loaded.LoadSave(save); var restored = loaded.GetView();
        Check(!restored.message.StartsWith("Invalid save") && Economy(restored) == Economy(v) && restored.reward == null, "save preserves earnings without replaying transient receipt");
        var checkpoint = Economy(v); Near(game, "goblin-workshop"); game.Handle(new() { type = "interact", targetId = "goblin-workshop" });
        foreach (var u in v.party) u.hp = 0;
        game.Handle(new() { type = "endTurn" }); Check(v.mode == "defeat", "real phase resolves defeat");
        game.Handle(new() { type = "retry" }); v = game.GetView();
        Check(v.mode == "explore" && Economy(v) == checkpoint && v.reward == null && v.party.All(u => u.hp == u.maxHp && !u.moved && !u.acted && !u.ended), "retry restores safe checkpoint and earned state without stale reward");
        var capped = Encounter(json); capped.GetView().gold = 100000;
        capped.GetView().inventory.Single(s => s.itemId == "item.health_tonic").count = PreparationService.InventoryCountCap;
        Win(capped);
        Check(capped.GetView().reward.gold == 0 && capped.GetView().gold == 100000, "receipt reports capped actual gold rather than authored amount");
        Check(capped.GetView().inventory.Single(s => s.itemId == "item.health_tonic").count == PreparationService.InventoryCountCap && !capped.GetView().reward.items.Any(s => s.itemId == "item.health_tonic" && s.count > 0), "capped item reward never overstates actual grant");
    }
    static void Consumables(string json)
    {
        var game = new Game(json); var v = game.GetView(); var id = "item.health_tonic";
        int count = v.inventory.Single(i => i.itemId == id).count;
        game.Handle(new() { type = "useItem", actorId = "carl", itemId = id });
        Check(v.inventory.Single(i => i.itemId == id).count == count, "full-health tonic does not consume inventory");
        v.party[0].hp = 0; game.Handle(new() { type = "useItem", actorId = "carl", itemId = id });
        Check(v.party[0].hp == 0 && v.inventory.Single(i => i.itemId == id).count == count, "tonic cannot revive dead crawler");
        v.party[0].hp = 1; game.Handle(new() { type = "useItem", actorId = "carl", itemId = id });
        Check(v.party[0].hp > 1 && v.inventory.Single(i => i.itemId == id).count == count - 1, "valid tonic consumes exactly one");
        game.Handle(new() { type = "useItem", actorId = "unknown", itemId = id });
        Check(v.inventory.Single(i => i.itemId == id).count == count - 1, "invalid actor cannot consume inventory");
    }
    static void Preparation(string json)
    {
        var content = Codec.Read<Content>(json); var game = new Game(json); var v = game.GetView();
        // Deliberate tactical fixture bonuses exercise replacement arithmetic even though personal authored gear is cosmetic.
        content.items.Single(i => i.id == "gear.carl-underpants").armor = 3;
        content.items.Single(i => i.id == "gear.carl-backpack").power = 2;
        content.items.Single(i => i.id == "gear.carl-backpack").rankModifiers["punch"] = 1;
        var carl = v.party[0]; var donut = v.party[1];
        foreach (var actor in v.party)
        foreach (var item in content.items.Where(i => PreparationService.IsEquipment(i)))
        {
            var preview = PreparationService.PreviewEquipment(content, v, actor.id, item.id);
            var before = Economy(v); int power = actor.power, armor = actor.armor;
            var result = PreparationService.Equip(content, v, actor.id, item.id);
            Check(result.available == preview.available, "equipment preview agrees with commit " + actor.id + "/" + item.id);
            if (!preview.available) Check(Economy(v) == before, "ineligible equipment commit is atomic");
            else Check(actor.power == power + preview.powerDelta && actor.armor == armor + preview.armorDelta && actor.equipment == item.id, "equipment applies exact preview deltas");
        }
        Check(!PreparationService.PreviewEquipment(content, v, "donut", "gear.carl-underpants").available && !PreparationService.PreviewEquipment(content, v, "carl", "gear.donut-tiara").available, "personal gear owner restrictions");
        PreparationService.Equip(content, v, "carl", "gear.carl-backpack"); var equipped = Economy(v);
        Check(PreparationService.PreviewEquipment(content, v, "carl", "").rankDeltas.GetValueOrDefault("punch") == -1, "stat comparison includes removal of gear rank bonus");
        PreparationService.Equip(content, v, "carl", "gear.carl-backpack");
        Check(Economy(v) == equipped, "repeated equip does not stack bonuses");
        var remove = PreparationService.PreviewEquipment(content, v, "carl", ""); int oldPower = carl.power, oldArmor = carl.armor;
        PreparationService.Equip(content, v, "carl", "");
        Check(carl.equipment == "" && carl.power == oldPower + remove.powerDelta && carl.armor == oldArmor + remove.armorDelta, "unequip reverses current slot bonuses");
        var offers = new[] { new ResupplyOffer { id = "fixture.tonic", name = "Test tonic", itemId = "item.health_tonic", quantity = 2, goldCost = 7 } };
        v.gold = 20;
        var beforePurchase = Economy(v); Check(!PreparationService.Purchase(content, v, offers, offers[0].id).available && Economy(v) == beforePurchase, "out-of-room purchase rejected atomically");
        Near(game, "safe-room"); var service = PreparationService.SafeRoom(v);
        Check(service.restAllowed && service.saveAllowed && service.resupplyAllowed, "safe room exposes service permissions");
        int count = v.inventory.Single(i => i.itemId == "item.health_tonic").count;
        var previewBuy = PreparationService.PreviewResupply(content, v, offers, offers[0].id);
        Check(previewBuy.available && PreparationService.Purchase(content, v, offers, offers[0].id).available && v.gold == 13 && v.inventory.Single(i => i.itemId == "item.health_tonic").count == count + 2, "purchase costs gold and grants exact quantity matching preview");
        foreach (var denial in new[] { "gold", "cap", "availability", "unknown", "battle" })
        {
            v.gold = denial == "gold" ? 0 : 20; v.inventory.Single(i => i.itemId == "item.health_tonic").count = denial == "cap" ? PreparationService.InventoryCountCap : 3;
            offers[0].availability.active = denial != "availability"; v.mode = denial == "battle" ? "battle" : "explore";
            string before = Economy(v); var id = denial == "unknown" ? "missing" : offers[0].id;
            Check(!PreparationService.PreviewResupply(content, v, offers, id).available && !PreparationService.Purchase(content, v, offers, id).available && Economy(v) == before, "denied purchase rolls back: " + denial);
        }
        var live = new Game(json); var liveView = live.GetView(); Near(live, "safe-room"); liveView.gold = 30;
        var actualOffer = live.GetView().resupplyOffers.First(o => o.available);
        int initialCount = liveView.inventory.FirstOrDefault(s => s.itemId == actualOffer.itemId)?.count ?? 0;
        live.Handle(new() { type = "buy", targetId = actualOffer.offerId });
        Check(liveView.gold == 30 - actualOffer.goldCost && liveView.inventory.Single(s => s.itemId == actualOffer.itemId).count == initialCount + actualOffer.quantity, "authored offer view and buy command agree");
        live.Handle(new() { type = "equip", actorId = "donut", itemId = "gear.carl-backpack" });
        Check(liveView.party[1].equipment == "", "equip bridge obeys ownership/possession eligibility");
        liveView.party[1].equipment = "gear.carl-backpack";
        liveView.party[1].templateId = "crawler.carl";
        var oldSave = live.GetSave(); var migrated = new Game(json); migrated.LoadSave(oldSave); var migratedView = migrated.GetView();
        Check(!migratedView.message.StartsWith("Invalid save") && migratedView.party[1].equipment == "" && migratedView.party[1].templateId == "crawler.donut" && migratedView.inventory.Any(s => s.itemId == "gear.carl-backpack" && s.count == 1), "legacy wrong-owner cosmetic equipment normalizes without losing inventory or accepting spoofed identity");
        Check(migratedView.message.Contains("belongs", StringComparison.OrdinalIgnoreCase), "legacy equipment normalization gives explicit notice");
        migrated.Handle(new() { type = "equip", actorId = "donut", itemId = "gear.carl-backpack" });
        Check(migratedView.party[1].equipment == "", "normalized save cannot re-equip other crawler's personal gear");
        Console.WriteLine("PASS: Block B preparation preview/commit parity, owner restrictions, equip idempotence/unequip, safe resupply exact costs and atomic denials.");
    }
    static string Combat(View v) => Codec.Write(new { v.mode, v.turn, v.selectedId, v.party, v.battle.enemies, v.battle.hazards, v.battle.effectObjects, v.battle.phase });
    static void StartingGear(string json)
    {
        var content = new ContentCatalog(Codec.Read<Content>(json)).Content;
        var game = new Game(json); var v = game.GetView();
        foreach (var id in new[] { "gear.carl-underpants", "gear.carl-backpack", "gear.donut-tiara" })
        {
            var item = content.items.Single(i => i.id == id);
            Check(item.startingCount == 1 && v.inventory.Count(s => s.itemId == id) == 1 && v.inventory.Single(s => s.itemId == id).count == 1, "new party owns exactly one starting personal item " + id);
            var owner = v.party.Single(u => item.ownerId == "crawler." + u.id);
            Check(PreparationService.PreviewEquipment(content, v, owner.id, id).available && !PreparationService.PreviewEquipment(content, v, v.party.First(u => u != owner).id, id).available, "starting gear is eligible only for its actual owner");
        }
        Check(v.party.All(u => u.equipment == "") && v.party[0].power == 14 && v.party[0].armor == 3 && v.party[1].power == 10 && v.party[1].armor == 2, "starting ownership neither auto-equips nor changes combat statistics");
        Check(v.inventory.Where(s => content.items.Single(i => i.id == s.itemId).kind == "consumable").Count() == 2 && v.inventory.Where(s => content.items.Single(i => i.id == s.itemId).kind == "consumable").All(s => s.count == 3), "starting consumable grants remain unchanged");
        var historical = Codec.Read<Save>(File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "Fixtures", "earned-safe-v2.json")));
        var receiver = new Game(json); receiver.LoadSave(Codec.Write(historical)); var loaded = receiver.GetView();
        Check(!loaded.message.StartsWith("Invalid save") && Codec.Write(loaded.inventory) == Codec.Write(historical.state.inventory), "earned v2 inventory migrates exactly without starting gear backfill");
        Console.WriteLine("PASS: starting personal gear ownership, unchanged combat/consumable grants, earned-v2 inventory preserved without backfill.");
    }
    static void ContentContracts(string json)
    {
        foreach (var change in new Action<Content>[] {
            c => c.items[0].startingCount = -1,
            c => c.items[0].startingCount = 1000,
            c => c.items.First(i => i.kind == "consumable").startingCount = 1,
            c => { c.items[0].startingCount = 1; c.items[0].availability.active = false; },
            c => { c.items[0].startingCount = 1; c.items[0].ownerId = "npc.mordecai"; },
            c => c.resupplyOffers[0].itemId = "missing.item",
            c => c.resupplyOffers[0].quantity = 0,
            c => c.resupplyOffers[0].goldCost = 0,
            c => c.resupplyOffers = [c.resupplyOffers[0], c.resupplyOffers[0]],
            c => c.encounters[0].itemRewards = [new() { itemId = "missing.item", count = 1 }],
            c => c.encounters[0].itemRewards = [new() { itemId = "item.health_tonic", count = -1 }]
        })
        {
            var content = Codec.Read<Content>(json); change(content); bool rejected = false;
            try { _ = new ContentCatalog(content); } catch (InvalidOperationException) { rejected = true; }
            Check(rejected, "invalid resupply/reward content rejected before gameplay");
        }
    }
    static void EnemyPhases(string json)
    {
        var sync = Encounter(json); var animated = Encounter(json);
        sync.Handle(new() { type = "endTurn" }); var v = animated.Handle(new() { type = "endTurn", animateEnemyTurn = true });
        Check(v.battle.phase == "enemy" && v.battle.enemyIntent != null, "animated end turn exposes pending enemy intent");
        foreach (var command in new[] { new Command { type = "moveUnit", actorId = "carl", x = 2, y = 2 }, new Command { type = "select", actorId = "donut" }, new Command { type = "endTurn" }, new Command { type = "useItem", actorId = "carl", itemId = "item.health_tonic" }, new Command { type = "retry" }, new Command { type = "forecast", actorId = "donut", targetId = v.battle.enemies[0].id, skillId = "magic-missile" } })
        {
            string before = Combat(v), inventory = Codec.Write(v.inventory); animated.Handle(command);
            Check(Combat(v) == before && Codec.Write(v.inventory) == inventory && v.forecast == null, "enemy phase denies player command " + command.type);
        }
        int steps = 0; while (v.mode == "battle" && v.battle.phase == "enemy" && steps++ < 100) animated.Handle(new() { type = "advanceEnemyTurn" });
        Check(steps < 100 && Combat(sync.GetView()) == Combat(animated.GetView()), "animated and synchronous enemy turns have identical final state");
        var game = Encounter(json); v = game.GetView(); v.battle.obstacles = []; v.battle.effectObjects.Clear();
        var carl = v.party[0]; var donut = v.party[1]; var enemy = v.battle.enemies[0];
        carl.x = 0; carl.y = 0; donut.x = 5; donut.y = 1; enemy.x = 2; enemy.y = 1;
        v.battle.obstacles = [new() { x = 1, y = 0 }, new() { x = 0, y = 1 }];
        foreach (var other in v.battle.enemies.Skip(1)) other.hp = 0;
        game.Handle(new() { type = "endTurn", animateEnemyTurn = true });
        Check(v.battle.enemyIntent.targetId == "donut", "enemy chooses reachable alternative over isolated nearer crawler");
        while (v.battle.phase == "enemy") game.Handle(new() { type = "advanceEnemyTurn" });
        Check(v.party[1].hp < v.party[1].maxHp && v.party[0].hp == v.party[0].maxHp, "reachable alternative is attacked");
        v.party[0].hp = 0; game.Handle(new() { type = "select", actorId = "carl" });
        Check(v.selectedId == "donut", "selection remains on living actor");
    }
}
