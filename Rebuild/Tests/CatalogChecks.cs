using DccRebuild;
using System.Text.Json.Nodes;

static class CatalogChecks
{
    static void Check(bool condition, string label) { if (!condition) throw new Exception("catalog: " + label); }
    static Content Read(string json) => new ContentCatalog(Codec.Read<Content>(json)).Content;
    static void Reject(string json, Action<Content> change, string diagnostic)
    {
        var content = Read(json); change(content);
        try { _ = new ContentCatalog(content); throw new Exception("catalog: accepted invalid fixture " + diagnostic); }
        catch (InvalidOperationException e) { Check(e.Message.Contains(diagnostic, StringComparison.OrdinalIgnoreCase), "actionable diagnostic for " + diagnostic + ": " + e.Message); }
    }
    static T Definition<T>(Content content, string id) where T : CatalogDefinition
    { var definition = Codec.Read<T>(Codec.Write(content.skills[0])); definition.id = id; definition.ownerId = ""; return definition; }
    public static void Run(string json)
    {
        var catalog = new ContentCatalog(Read(json));
        Check(catalog.Get<Skill>("skill", "punch").id == "punch", "typed lookup uses stable IDs");
        Check(catalog.Deployable(1, []).Select(c => c.id).Order().SequenceEqual(new[] { "crawler.carl", "crawler.donut" }), "Floor One deploys only Carl and Donut");
        Reject(json, c => c.skills = c.skills.Concat(new[] { c.skills[0] }).ToArray(), "duplicate");
        Reject(json, c => c.skills[0].references = [new() { kind = "item", id = "missing-item" }], "missing item:missing-item");
        Reject(json, c => c.skills[0].references = [new() { kind = "enemy", id = "punch" }], "missing enemy:punch");
        Reject(json, c => c.skills[0].sourceIds = ["unregistered-source"], "missing source");
        Reject(json, c => { var cls = Definition<ClassDefinition>(c, "class.too-early"); cls.availability = new() { minFloor = 1 }; c.classes = [cls]; }, "Floor 3");
        Reject(json, c => { var a = Definition<StoryEventDefinition>(c, "event.a"); var b = Definition<StoryEventDefinition>(c, "event.b"); a.availability.requiredEvents = [b.id]; b.availability.requiredEvents = [a.id]; c.storyEvents = c.storyEvents.Concat(new[] { a, b }).ToArray(); }, "cyclic");
        Reject(json, c => { var intruder = Codec.Read<CharacterDefinition>(Codec.Write((c.characters.Length > 0 ? c.characters : c.party)[0])); intruder.id = "crawler.forbidden"; intruder.deployable = true; intruder.availability.requiredEvents = c.storyEvents.Take(1).Select(e => e.id).ToArray(); c.characters = (c.characters.Length > 0 ? c.characters : c.party).Concat(new[] { intruder }).ToArray(); }, "only Carl and Donut");
        Reject(json, c => c.sources = c.sources.Concat(new[] { c.sources[0] }).ToArray(), "duplicate source");
        Reject(json, c => c.skills[0].ownerId = "crawler.missing", "ownerId");
        Reject(json, c => { c.items[0].adaptationStatus = "adapted"; c.items[0].rankModifiers["missing-skill"] = 1; }, "rankModifiers");
        Reject(json, c => c.skills[0].tags = null, "null");
        Reject(json, c => c.skills[0].references = [null], "typed reference");
        Reject(json, c => c.skills = null, "skill");
        Reject(json, c => { var location = Definition<LocationDefinition>(c, "location.fixture"); location.worldObjectId = "world.missing"; c.locations = c.locations.Append(location).ToArray(); }, "worldObjectId");
        Reject(json, c => { var ev = Definition<StoryEventDefinition>(c, "event.bad-trigger"); ev.trigger = "clear"; ev.triggerId = "world.missing"; c.storyEvents = c.storyEvents.Append(ev).ToArray(); }, "triggerId");
        Reject(json, c => c.skills[0].description = "", "description");
        Reject(json, c => c.skills[0].tags = [], "tags");
        Reject(json, c => c.skills[0].sourceRefs = [], "sourceRefs");
        Reject(json, c => c.skills[0].sourceRefs[0].locator = "", "locator");
        var uncertain = Read(json); uncertain.skills[0].sourceRefs[0].locator = "unverified: exact chapter locator unknown"; uncertain.skills[0].sourceRefs[0].confidence = "unverified";
        Check(new ContentCatalog(uncertain).Get<Skill>("skill", uncertain.skills[0].id).sourceRefs[0].confidence == "unverified", "honestly labeled unverified locator retained without invented evidence");
        var extended = Read(json);
        var addedItem = Codec.Read<Item>(Codec.Write(extended.items[0])); addedItem.id = "item.fixture-added-without-code";
        extended.items = extended.items.Concat(new[] { addedItem }).ToArray();
        Check(new ContentCatalog(extended).Get<Item>("item", addedItem.id).id == addedItem.id, "new valid authored entry needs no registry code");
        var addedSkill = Codec.Read<Skill>(Codec.Write(extended.skills.Single(k => k.id == "punch")));
        addedSkill.id = "skill.fixture-added-without-code";
        extended.skills = extended.skills.Concat(new[] { addedSkill }).ToArray();
        var character = (extended.characters.Length > 0 ? extended.characters : extended.party).Single(c => c.id == "crawler.carl");
        character.skillIds = character.skillIds.Concat(new[] { addedSkill.id }).ToArray();
        var game = new Game(Codec.Write(extended), 71); var view = game.GetView();
        Check(view.party[0].skills.Contains(addedSkill.id), "data-only skill acquired through character registry");
        var safe = view.world.objects.First(o => o.kind == "safe"); view.x = safe.x - 1; view.y = safe.y;
        var save = game.GetSave(); var restored = new Game(Codec.Write(extended)); restored.LoadSave(save);
        Check(!restored.GetView().message.StartsWith("Invalid save") && restored.GetView().party[0].skills.Contains(addedSkill.id), "data-only skill save roundtrip");
        var encounter = view.world.objects.Single(o => o.id == "false-guild"); view.x = encounter.x; view.y = encounter.y;
        game.Handle(new() { type = "interact", targetId = encounter.id });
        var actor = view.party[0]; var enemy = view.battle.enemies[0]; actor.x = 1; actor.y = 2; enemy.x = 2; enemy.y = 2;
        var forecast = game.Handle(new() { type = "forecast", actorId = actor.id, targetId = enemy.id, skillId = addedSkill.id }).forecast;
        Check(forecast.valid, "data-only skill usable through resolver"); int hp = enemy.hp;
        game.Handle(new() { type = "confirm" });
        Check(enemy.hp == Math.Max(0, hp - forecast.damage), "data-only skill commit equals forecast");
        var gate = new Availability { minFloor = 2, maxFloor = 3, requiredEvents = ["event.fixture"] };
        Check(!gate.Allows(1, ["event.fixture"]) && !gate.Allows(2, []) && gate.Allows(2, ["event.fixture"]) && !gate.Allows(4, ["event.fixture"]), "floor and story gates both required");
        Console.WriteLine("PASS: typed content registry, duplicate/missing references/source/cycle/class gates, deployable party and data-only additions.");
    }
    public static int ValidateFile(string path)
    {
        try
        {
            var catalog = new ContentCatalog(Read(File.ReadAllText(path)));
            foreach (int seed in new[] { 0, 42, 1337 }) World.Validate(World.Build(seed));
            Console.WriteLine(Codec.Write(new { valid = true, file = Path.GetFullPath(path), entries = catalog.Entries.Count(), worldSeeds = new[] { 0, 42, 1337 }, diagnostics = Array.Empty<string>() }));
            return 0;
        }
        catch (Exception e)
        {
            Console.WriteLine(Codec.Write(new { valid = false, file = Path.GetFullPath(path), diagnostics = new[] { e.Message } }));
            return 1;
        }
    }
}
