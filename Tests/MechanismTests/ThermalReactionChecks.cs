using System;
using System.Linq;
using System.Text.Json;
using DungeonCrawlerTactics;

// Exercise the authored rule through the same kernel used by forecasts and commits.
static class ThermalReactionChecks
{
    static readonly JsonSerializerOptions Json = new JsonSerializerOptions { IncludeFields = true };
    static int checks;
    static string Snapshot(object value) { return JsonSerializer.Serialize(value, Json); }
    static void Check(bool condition, string message)
    {
        if (!condition) throw new Exception(message);
        checks++;
        Console.WriteLine("PASS " + message);
    }
    static BattleState Frozen()
    {
        BattleState state = new BattleState();
        EntityState actor = new EntityState { Id = "actor", ClassId = "class.brawler", Team = "party", Hp = 60, MaxHp = 60, Energy = 20 };
        actor.GrantedAbilities.UnionWith(new[] { "ability.firebolt", "ability.spark", "ability.frostbite", "ability.shatter", "ability.enemy_cinder_shot" });
        EntityState target = new EntityState { Id = "target", ClassId = "class.brawler", Team = "enemy", X = 1, Hp = 60, MaxHp = 60 };
        target.Tags.Add("status.frozen");
        state.Entities.Add(actor.Id, actor); state.Entities.Add(target.Id, target);
        return state;
    }
    public static void Run(Content content)
    {
        RulesEngine engine = new RulesEngine(new Catalog(content));
        BattleState original = Frozen(); string before = Snapshot(original);
        ActionResult preview = engine.Preview(original, "actor", "ability.firebolt", "target");
        ActionResult commit = engine.Execute(original, "actor", "ability.firebolt", "target");
        Check(Snapshot(original) == before, "thermal previews and commits preserve source state");
        Check(Snapshot(preview) == Snapshot(commit), "thermal forecast equals commit including ordered events and log");
        EntityState target = commit.State.Entities["target"];
        Check(target.Hp == 50 && !target.Tags.Contains("status.frozen") && target.Tags.Contains("status.wet") && commit.State.Entities["actor"].Energy == 18,
            "fire thaws frozen target into wet with ordinary damage and mana cost");
        Check(commit.Events.Count(e => e.type == "reaction" && e.reactionId == "reaction.fire_thaws_frozen") == 1
            && commit.Events.Any(e => e.type == "tag_remove" && e.tag == "status.frozen")
            && commit.Events.Any(e => e.type == "tag_add" && e.tag == "status.wet"), "thaw emits a single reaction and both condition changes");
        ActionResult shocked = engine.Execute(commit.State, "actor", "ability.spark", "target");
        Check(shocked.State.Entities["target"].Hp == 37 && shocked.State.Entities["target"].Tags.Contains("status.shocked")
            && !shocked.State.Entities["target"].Tags.Contains("status.wet"), "thawed water enables the next lightning conductivity reaction");
        ActionResult refrozen = engine.Execute(commit.State, "actor", "ability.frostbite", "target");
        Check(refrozen.State.Entities["target"].Tags.Contains("status.frozen") && !refrozen.State.Entities["target"].Tags.Contains("status.wet"),
            "thawed water can instead be frozen by a later cold action");
        ActionResult shatter = engine.Execute(commit.State, "actor", "ability.shatter", "target");
        Check(!shatter.Events.Any(e => e.reactionId == "reaction.frozen_shatters"), "thaw removes the physical shatter bonus prerequisite");
        original = Frozen(); original.Entities["target"].Immunities.Add("element.fire");
        commit = engine.Execute(original, "actor", "ability.firebolt", "target");
        Check(commit.State.Entities["target"].Hp == 60 && commit.State.Entities["target"].Tags.Contains("status.frozen")
            && !commit.State.Entities["target"].Tags.Contains("status.wet"), "fire immunity also prevents thaw");
        original = Frozen(); original.Entities["target"].Tags.Clear();
        commit = engine.Execute(original, "actor", "ability.firebolt", "target");
        Check(!commit.State.Entities["target"].Tags.Contains("status.wet") && !commit.Log.Contains("reaction.fire_thaws_frozen"), "ordinary fire does not create water on an unfrozen target");
        commit = engine.Execute(Frozen(), "actor", "ability.spark", "target");
        Check(commit.State.Entities["target"].Tags.Contains("status.frozen") && !commit.State.Entities["target"].Tags.Contains("status.wet"), "non-fire damage does not thaw");
        commit = engine.ExecuteItem(Frozen(), "actor", "item.fire_bomb", "target");
        Check(commit.State.Entities["target"].Hp == 48 && commit.State.Entities["target"].Tags.Contains("status.wet")
            && commit.State.Entities["actor"].Energy == 20, "fire consumables use the same thaw rule without mana cost");
        original = Frozen(); original.Entities["actor"].Team = "enemy"; original.Entities["target"].Team = "party";
        commit = engine.Execute(original, "actor", "ability.enemy_cinder_shot", "target");
        Check(commit.State.Entities["target"].Tags.Contains("status.wet") && !commit.State.Entities["target"].Tags.Contains("status.frozen"),
            "enemy fire has symmetric thermal behavior");
        original = Frozen(); original.Entities["target"].Tags.Add("surface.oil");
        commit = engine.Execute(original, "actor", "ability.firebolt", "target");
        Check(commit.State.Entities["target"].Tags.Contains("surface.burning") && commit.State.Entities["target"].Tags.Contains("status.wet")
            && !commit.State.Entities["target"].Tags.Contains("surface.oil") && !commit.State.Entities["target"].Tags.Contains("status.frozen"),
            "thaw composes with existing oil ignition without implicit water extinguishing");
        ActionResult again = engine.Execute(commit.State, "actor", "ability.firebolt", "target");
        Check(!again.Events.Any(e => e.reactionId == "reaction.fire_thaws_frozen") && again.State.Entities["target"].Tags.Contains("status.wet"),
            "repeat fire cannot thaw an already thawed target or implicitly evaporate wetness");
        // A multi-element action must not retroactively match wet in its original event.
        Content mixed = JsonSerializer.Deserialize<Content>(Snapshot(content), Json);
        mixed.abilities.Single(a => a.id == "ability.firebolt").incomingTags = new[] { "element.fire", "element.lightning" };
        commit = new RulesEngine(new Catalog(mixed)).Execute(Frozen(), "actor", "ability.firebolt", "target");
        Check(commit.State.Entities["target"].Hp == 50 && commit.State.Entities["target"].Tags.Contains("status.wet")
            && !commit.Events.Any(e => e.reactionId == "reaction.wet_conducts"), "newly thawed wetness cannot retroactively conduct the triggering event");
        Console.WriteLine(checks + " thermal reaction checks passed.");
    }
}
