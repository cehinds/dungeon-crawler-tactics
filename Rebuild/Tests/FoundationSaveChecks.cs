using DccRebuild;
using System.Text.Json.Nodes;

static class FoundationSaveChecks
{
    static void Check(bool value, string label) { if (!value) throw new Exception("foundation save: " + label); }
    public static void Run(string json)
    {
        var content = Codec.Read<Content>(json);
        var story = Codec.Read<StoryEventDefinition>(Codec.Write(content.skills[0]));
        story.id = "event.fixture-first-clear"; story.ownerId = ""; story.trigger = "clear"; story.triggerId = "false-guild";
        content.storyEvents = content.storyEvents.Append(story).ToArray();
        var modifier = Codec.Read<TemporaryModifierDefinition>(Codec.Write(content.skills[0]));
        modifier.id = "status.fixture-rank"; modifier.ownerId = ""; modifier.skillId = "punch"; modifier.amount = 1; modifier.duration = 2;
        content.temporaryModifiers = content.temporaryModifiers.Append(modifier).ToArray();
        content.destructibleAssetIds = World.BuildArena(71, "goblin-workshop").props.Where(p => p.layer != "wallfixture").Select(p => p.assetId).Distinct().ToArray();
        content.encounters.Single(e => e.id == "false-guild").effectObjects = [new() { id = "fixture-authored-crate", x = 3, y = 4, hp = 1, tags = ["destructible"] }];
        content.skills.Single(k => k.id == "punch").effectOperations = [new() { kind = "object", area = true, radius = 32, amount = 100 }];
        var fixture = Codec.Write(content); var game = new Game(fixture, 71); var view = game.GetView();
        var door = view.world.objects.Single(o => o.id == "false-guild"); view.x = door.x; view.y = door.y;
        game.Handle(new() { type = "interact", targetId = door.id });
        var actor = view.party[0]; var target = view.battle.enemies[0]; actor.x = 1; actor.y = 2; target.x = 2; target.y = 2; target.hp = 1;
        foreach (var enemy in view.battle.enemies.Skip(1)) enemy.hp = 0;
        game.Handle(new() { type = "confirm", actorId = actor.id, targetId = target.id, skillId = "punch" });
        Check(view.mode == "explore" && view.unlockedEvents.Contains(story.id), "real victory unlocks authored story receipt: " + view.mode + " " + view.message);
        var guide = view.world.objects.Single(o => o.id == "mordecai"); view.x = guide.x; view.y = guide.y;
        game.Handle(new() { type = "interact", targetId = guide.id });
        var workshop = view.world.objects.Single(o => o.id == "goblin-workshop"); view.x = workshop.x; view.y = workshop.y;
        game.Handle(new() { type = "interact", targetId = workshop.id });
        Check(view.battle.effectObjects.Count > 0, "authored destructible props enter battle resolver");
        target = view.battle.enemies[0]; actor.x = 5; actor.y = 3; target.x = 6; target.y = 3; target.hp = 1;
        foreach (var enemy in view.battle.enemies.Skip(1)) enemy.hp = 0;
        game.Handle(new() { type = "confirm", actorId = actor.id, targetId = target.id, skillId = "punch" });
        Check(view.mode == "explore" && view.destroyedPropIds.Count > 0 && view.destroyedPropIds.All(id => !view.world.props.Any(p => p.id == id)), "real resolver destruction persists exploration receipts");
        actor.statuses.Add(new() { id = modifier.id, duration = 2, strength = 1 });
        var safe = view.world.objects.First(o => o.kind == "safe"); view.x = safe.x - 1; view.y = safe.y;
        var save = game.GetSave(); var restored = new Game(fixture); restored.LoadSave(save); var loaded = restored.GetView();
        Check(!loaded.message.StartsWith("Invalid save") && loaded.floor == 1 && loaded.unlockedEvents.Contains(story.id), "v3 floor/story state roundtrips");
        Check(view.destroyedEncounterObjectIds.Contains("false-guild:fixture-authored-crate") && loaded.destroyedEncounterObjectIds.SequenceEqual(view.destroyedEncounterObjectIds), "v3 authored encounter object destruction receipts roundtrip");
        Check(loaded.destroyedPropIds.SequenceEqual(view.destroyedPropIds) && loaded.destroyedPropIds.All(id => !loaded.world.props.Any(p => p.id == id)), "v3 destroyed prop receipts and mutated world roundtrip");
        Check(loaded.party[0].skillProgress.Single(p => p.skillId == "punch").effectiveRank == loaded.party[0].ranks["punch"] + 1 && loaded.party[0].statuses.Any(s => s.id == modifier.id && s.duration == 2), "v3 temporary rank modifier and status roundtrip");
        var broken = JsonNode.Parse(save); broken["state"]["party"][0]["temporaryRankModifiers"]["punch"] = 20;
        var prior = Codec.Write(new { loaded.party, loaded.unlockedEvents, loaded.floor, loaded.inventory, loaded.cleared });
        restored.LoadSave(broken.ToJsonString());
        Check(loaded.message.StartsWith("Invalid save") && Codec.Write(new { loaded.party, loaded.unlockedEvents, loaded.floor, loaded.inventory, loaded.cleared }) == prior, "forged temporary modifier rolls back entire load");
        var unknownReceipt = JsonNode.Parse(save); unknownReceipt["state"]["destroyedPropIds"].AsArray().Add("prop.forged-unknown");
        restored.LoadSave(unknownReceipt.ToJsonString());
        Check(loaded.message.StartsWith("Invalid save") && Codec.Write(new { loaded.party, loaded.unlockedEvents, loaded.floor, loaded.inventory, loaded.cleared }) == prior, "unknown destruction receipt rolls back load");
        Console.WriteLine("PASS: v3 story/floor/status/temporary-rank/destruction roundtrip; forged modifier and destruction rollback.");
    }
}
