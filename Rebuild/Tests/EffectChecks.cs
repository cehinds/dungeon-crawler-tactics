using DccRebuild;

static class EffectChecks
{
    static void Check(bool value, string label) { if (!value) throw new Exception("effects: " + label); }
    static Battle Board() => new() { width = 8, height = 6, units = [new() { id = "ally", hp = 20, maxHp = 30, mp = 5, maxMp = 10, x = 2, y = 2 }], enemies = [new() { id = "foe", hp = 20, maxHp = 20, x = 4, y = 2 }] };
    static EffectResolution Resolve(Battle b, params EffectOperation[] operations) => EffectResolver.Resolve(b, new() { sourceId = "ally", targetId = "ally", operations = operations.ToList() });
    public static void GameFlows(string json)
    {
        var game = new Game(json, 71); var view = game.GetView(); var entrance = view.world.objects.Single(o => o.id == "false-guild");
        view.x = entrance.x; view.y = entrance.y; game.Handle(new() { type = "interact", targetId = entrance.id });
        var item = Codec.Read<Content>(json).items.First(i => i.kind == "consumable" && i.heal > 0);
        var owner = view.party[0]; owner.hp -= 20; var hp = owner.hp;
        int count = view.inventory.Single(s => s.itemId == item.id).count;
        game.Handle(new() { type = "useItem", actorId = owner.id, itemId = item.id });
        Check(owner.hp == Math.Min(owner.maxHp, hp + item.heal) && owner.acted && view.inventory.Single(s => s.itemId == item.id).count == count - 1, "item uses shared resolver and consumes one item/action");
        Check(view.battle.effectEvents.Any(e => e.kind == "heal" && e.targetId == owner.id), "item effect emits structured shared event");
        var enemy = view.battle.enemies[0]; owner.x = 1; owner.y = 2; enemy.x = 2; enemy.y = 2;
        view.party[1].hp = 0; foreach (var other in view.battle.enemies.Skip(1)) other.hp = 0;
        hp = owner.hp; game.Handle(new() { type = "endTurn" });
        Check(owner.hp < hp && view.battle.effectEvents.Any(e => e.kind == "damage" && e.sourceId == enemy.id && e.targetId == owner.id), "enemy attacks emit structured shared damage event");
        Console.WriteLine("PASS: item and enemy commands use shared structured effect events.");
    }
    public static void ResourceAndMovement(string json)
    {
        var content = Codec.Read<Content>(json); var spell = content.skills.Single(k => k.id == "magic-missile");
        spell.effectOperations = [new() { kind = "resource", targetId = "donut", amount = 10 }];
        var game = new Game(Codec.Write(content), 71); var view = game.GetView(); var door = view.world.objects.Single(o => o.id == "false-guild");
        view.x = door.x; view.y = door.y; game.Handle(new() { type = "interact", targetId = door.id });
        var mage = view.party.Single(u => u.id == "donut"); var enemy = view.battle.enemies[0];
        mage.x = 1; mage.y = 2; enemy.x = 2; enemy.y = 2; enemy.hp = 1000; mage.mp = mage.maxMp - 1;
        var forecast = game.Handle(new() { type = "forecast", actorId = mage.id, targetId = enemy.id, skillId = spell.id }).forecast;
        Check(forecast.valid, "resource parity fixture forecasts"); var expectedEvents = Codec.Write(forecast.events);
        game.Handle(new() { type = "confirm" });
        Check(mage.mp == mage.maxMp && Codec.Write(view.battle.effectEvents) == expectedEvents, "mana restoration forecast includes casting cost before capped restore");
        var walker = view.party[0]; walker.x = 1; walker.y = 4; walker.statuses.Add(new() { id = "burning", duration = 2, strength = 2 });
        view.battle.hazards.Add(new() { id = "fixture-water", tag = "water", x = 2, y = 4 });
        game.Handle(new() { type = "moveUnit", actorId = walker.id, x = 2, y = 4 });
        Check(walker.x == 2 && walker.y == 4 && !walker.statuses.Any(s => s.id == "burning"), "ordinary player movement enters water through reaction resolver");
        walker.moved = false; view.battle.effectObjects.Add(new() { id = "fixture-blocker", x = 3, y = 4 });
        game.Handle(new() { type = "moveUnit", actorId = walker.id, x = 3, y = 4 });
        Check(walker.x == 2 && walker.y == 4 && !walker.moved, "standalone effect object blocks ordinary movement");
        Console.WriteLine("PASS: capped mana restoration forecast/commit parity, water movement reaction, standalone object collision.");
    }
    public static void AuthoredDamageBonus(string json)
    {
        var content = Codec.Read<Content>(json);
        content.effectRules.damageBonuses = [new() { incomingTag = "arcane", targetTag = "fixture-bonus-target", amount = 7, reaction = "Authored fixture bonus" }];
        var game = new Game(Codec.Write(content), 71); var view = game.GetView(); var entrance = view.world.objects.Single(o => o.id == "false-guild");
        view.x = entrance.x; view.y = entrance.y; game.Handle(new() { type = "interact", targetId = entrance.id });
        var mage = view.party.Single(u => u.id == "donut"); var enemy = view.battle.enemies[0]; mage.x = 1; mage.y = 2; enemy.x = 2; enemy.y = 2; enemy.hp = 1000;
        var command = new Command { type = "forecast", actorId = mage.id, targetId = enemy.id, skillId = "magic-missile" };
        var baseline = game.Handle(command).forecast;
        enemy.tags = ["fixture-bonus-target"]; var boosted = game.Handle(command).forecast;
        Check(boosted.valid && boosted.damage == baseline.damage + 7 && boosted.reaction == "Authored fixture bonus", "authored numeric tag bonus changes damage and explanation without code changes");
        int hp = enemy.hp; game.Handle(new() { type = "confirm" });
        Check(enemy.hp == hp - boosted.damage, "authored damage bonus forecast matches commit");
        Console.WriteLine("PASS: authored numeric damage bonus lookup and forecast/commit agreement.");
    }
    public static void Run()
    {
        var original = Board(); var before = Codec.Write(original);
        var preview = Resolve(original, new EffectOperation { kind = "damage", amount = 4 }, new EffectOperation { kind = "heal", amount = 2 }, new EffectOperation { kind = "resource", amount = 100 }, new EffectOperation { kind = "move", x = 2, y = 3 }, new EffectOperation { kind = "displace", dx = 1 });
        Check(preview.valid && Codec.Write(original) == before, "forecast clone leaves complete input immutable");
        var actor = preview.state.units[0];
        Check(actor.hp == 18 && actor.mp == 10 && actor.x == 3 && actor.y == 3, "damage heal resource move displacement execute in order");
        var again = Resolve(original, new EffectOperation { kind = "damage", amount = 4 }, new EffectOperation { kind = "heal", amount = 2 }, new EffectOperation { kind = "resource", amount = 100 }, new EffectOperation { kind = "move", x = 2, y = 3 }, new EffectOperation { kind = "displace", dx = 1 });
        Check(Codec.Write(again) == Codec.Write(preview), "same resolver request reproduces preview exactly");
        var statuses = Resolve(original, new EffectOperation { kind = "status", statusId = "fixture", duration = 2, strength = 2 }, new EffectOperation { kind = "status", statusId = "fixture", duration = 1, strength = 1 }, new EffectOperation { kind = "status", statusId = "fixture", stacking = "add", strength = 3 });
        Check(statuses.state.units[0].statuses.Single().strength == 5 && statuses.state.units[0].statuses.Single().duration == 2, "refresh and additive stacking");
        statuses = Resolve(statuses.state, new EffectOperation { kind = "status", statusId = "fixture", stacking = "replace", duration = 1, strength = 1 }, new EffectOperation { kind = "tick" });
        Check(statuses.state.units[0].statuses.Count == 0, "replacement duration expires at turn tick");
        var burning = Resolve(original, new EffectOperation { kind = "status", statusId = "oil" }, new EffectOperation { kind = "damage", tag = "fire", amount = 1 });
        Check(burning.events.Select(e => e.kind).SequenceEqual(new[] { "statusApplied", "damage", "statusRemoved", "statusApplied" }), "oil ignition event order explicit");
        Check(burning.state.units[0].statuses.Single().id == "burning", "oil becomes burning");
        var tick = Resolve(burning.state, new EffectOperation { kind = "tick" });
        Check(tick.state.units[0].hp == 17, "burning damages on tick");
        var water = Resolve(tick.state, new EffectOperation { kind = "damage", amount = 0, tag = "water" });
        Check(water.state.units[0].statuses.Count == 0, "water extinguishes");
        var removed = Resolve(burning.state, new EffectOperation { kind = "removeStatus", statusId = "burning" });
        Check(removed.state.units[0].statuses.Count == 0, "explicit status removal");
        var objects = Board(); objects.units[0].x = 2; objects.enemies[0].x = 4;
        objects.effectObjects = [new() { id = "barrel", x = 3, y = 2, hp = 1, tags = ["explosive"] }];
        objects.obstacles = [new() { x = 3, y = 2 }];
        var blocked = Resolve(objects, new EffectOperation { kind = "displace", dx = 1 });
        Check(blocked.state.units[0].x == 2 && blocked.events.Single().kind == "blocked", "displacement checks crossed destructible collision");
        var blast = Resolve(objects, new EffectOperation { kind = "object", targetId = "barrel", amount = 1 });
        Check(blast.state.units[0].hp == 14 && blast.state.enemies[0].hp == 14, "explosion applies friendly fire to both teams");
        Check(blast.state.effectObjects[0].destroyed && !blast.state.effectObjects[0].blocksMovement && !blast.state.effectObjects[0].blocksSight && blast.state.obstacles.Length == 0, "destruction clears collision and sight");
        var move = Resolve(blast.state, new EffectOperation { kind = "move", x = 3, y = 2 });
        Check(move.state.units[0].x == 3, "destroyed object permits subsequent movement");
        var terrain = Board(); terrain.tiles = Enumerable.Repeat(".", terrain.width * terrain.height).ToArray(); terrain.tiles[2 * terrain.width + 3] = "~";
        terrain.effectObjects = [new() { id = "fixture-water-prop", x = 3, y = 2, hp = 1 }]; terrain.obstacles = [new() { x = 3, y = 2 }];
        var retainedTerrain = Resolve(terrain, new EffectOperation { kind = "object", targetId = "fixture-water-prop", amount = 1 });
        Check(retainedTerrain.state.tiles[2 * terrain.width + 3] == "~" && retainedTerrain.state.obstacles.Any(p => p.x == 3 && p.y == 2), "destroying an object never opens blocked underlying terrain");
        var conductive = Board(); conductive.units[0].tags = ["fixture-conductive"];
        var customRules = new EffectRules { reactions = [new() { id = "fixture-lightning", triggerTags = ["fixture-lightning"], requiredTargetTags = ["fixture-conductive"], operations = [new() { kind = "status", statusId = "fixture-stunned", duration = 1, strength = 1 }] }] };
        var custom = EffectResolver.Resolve(conductive, new() { sourceId = "foe", targetId = "ally", operations = [new() { kind = "damage", amount = 1, tag = "fixture-lightning" }] }, customRules);
        Check(custom.valid && custom.state.units[0].statuses.Single().id == "fixture-stunned", "new authored tag reaction executes without code changes");
        var fanoutRules = new EffectRules { reactions = Enumerable.Range(0, EffectResolver.MaximumReactionSteps).Select(i => new TagReactionDefinition { id = "fixture-fanout-" + i, triggerTags = ["fixture-fanout"], operations = [new() { kind = "status", statusId = "fixture-status-" + i, duration = 1 }] }).ToList() };
        var fanout = EffectResolver.Resolve(original, new() { targetId = "ally", operations = [new() { kind = "damage", amount = 1, tag = "fixture-fanout" }] }, fanoutRules);
        Check(!fanout.valid && fanout.reason.Contains("limit", StringComparison.OrdinalIgnoreCase) && fanout.events.Count == 0 && Codec.Write(fanout.state) == before, "reaction expansion limit rolls back damage and queued statuses");
        var invalidRules = new EffectRules { reactions = null };
        var invalidConfig = EffectResolver.Resolve(original, new() { operations = [new() { kind = "damage", targetId = "ally", amount = 1 }] }, invalidRules);
        Check(!invalidConfig.valid && Codec.Write(invalidConfig.state) == before && invalidConfig.events.Count == 0, "null authored reaction configuration rejects atomically");
        var duplicateRules = new EffectRules { reactions = [new() { id = "duplicate", triggerTags = ["fire"] }, new() { id = "duplicate", triggerTags = ["fire"] }] };
        var duplicateConfig = EffectResolver.Resolve(original, new() { operations = [] }, duplicateRules);
        Check(!duplicateConfig.valid && duplicateConfig.reason.Contains("duplicate", StringComparison.OrdinalIgnoreCase), "duplicate authored reaction IDs reject with diagnostic");
        var chainBoard = Board(); chainBoard.effectObjects = [new() { id = "chain-a", x = 2, y = 3, hp = 1, tags = ["destructible", "fixture-explosive"] }, new() { id = "chain-b", x = 3, y = 3, hp = 1, tags = ["destructible", "fixture-explosive"] }];
        var chainRules = new EffectRules { reactions = [new() { id = "fixture-object-chain", targetKind = "object", trigger = "destroyed", requiredTargetTags = ["fixture-explosive"], operations = [new() { kind = "damage", area = true, radius = 1, amount = 6, tag = "fixture-blast" }] }] };
        var chain = EffectResolver.Resolve(chainBoard, new() { sourceId = "ally", targetId = "chain-a", operations = [new() { kind = "object", amount = 1 }] }, chainRules);
        Check(chain.valid && chain.state.effectObjects.All(o => o.destroyed) && chain.events.Count(e => e.kind == "objectDestroyed") == 2, "authored object destruction reaction chains exactly once per object");
        var excessive = Resolve(original, Enumerable.Range(0, EffectResolver.MaximumReactionSteps + 1).Select(_ => new EffectOperation { kind = "damage", amount = 1 }).ToArray());
        Check(!excessive.valid && Codec.Write(excessive.state) == before && excessive.events.Count == 0, "reaction request limit rejects atomically");
        Console.WriteLine("PASS: deterministic immutable effect preview, ordered operations, status stacking/expiry/reactions, destructible collision and friendly fire.");
    }
}
