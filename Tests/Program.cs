using System;
using System.IO;
using System.Linq;
using System.Text.Json;
using DungeonCrawlerTactics;

internal static class Program
{
    private static int passed;
    private static Content Load() { return JsonSerializer.Deserialize<Content>(File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "starter-content.json")), new JsonSerializerOptions { IncludeFields = true }); }
    private static BattleState Battle(string actorClass = "class.pyromancer")
    {
        BattleState s = new BattleState();
        s.Entities.Add("hero", new EntityState { Id = "hero", ClassId = actorClass, Team = "party", Hp = 30, MaxHp = 30, Energy = 10 });
        s.Entities.Add("enemy", new EntityState { Id = "enemy", ClassId = "class.brawler", Team = "enemy", Hp = 30, MaxHp = 30, X = 1 });
        s.Entities.Add("tile", new EntityState { Id = "tile", IsTile = true, X = 1 }); return s;
    }
    private static void Check(bool ok, string name) { if (!ok) throw new Exception("FAIL: " + name); passed++; Console.WriteLine("PASS: " + name); }
    private static bool Rejects(Action action) { try { action(); return false; } catch (ArgumentException) { return true; } }
    private static string Snapshot(BattleState s) { return string.Join("|", s.Entities.OrderBy(p => p.Key, StringComparer.Ordinal).Select(p => p.Key + ":" + p.Value.Hp + ":" + p.Value.Energy + ":" + string.Join(",",p.Value.Tags.OrderBy(t => t,StringComparer.Ordinal)))); }
    private static void Main()
    {
        Content content = Load(); Catalog catalog = new Catalog(content); RulesEngine engine = new RulesEngine(catalog);
        BattleState state = Battle(); state.Entities["tile"].Tags.Add("surface.oil"); string before = Snapshot(state);
        ActionResult preview = engine.Preview(state,"hero","ability.fire_surface","tile");
        ActionResult commit = engine.Execute(state,"hero","ability.fire_surface","tile");
        Check(Snapshot(preview.State) == Snapshot(commit.State) && preview.Log.SequenceEqual(commit.Log), "preview equals commit");
        Check(Snapshot(state) == before, "preview and execute leave input untouched");
        Check(commit.State.Entities["tile"].Tags.Contains("surface.burning") && !commit.State.Entities["tile"].Tags.Contains("surface.oil") && commit.State.Entities["hero"].Energy == 8, "oil ignition consumes oil and energy");
        state = Battle("class.stormcaller"); state.Entities["enemy"].Tags.Add("status.wet");
        commit = engine.Execute(state,"hero","ability.spark","enemy");
        Check(commit.State.Entities["enemy"].Hp == 20 && commit.State.Entities["enemy"].Tags.Contains("status.shocked") && !commit.State.Entities["enemy"].Tags.Contains("status.wet"),"wet conducts bonus damage");
        state.Entities["enemy"].Immunities.Add("element.lightning"); commit = engine.Execute(state,"hero","ability.spark","enemy");
        Check(commit.State.Entities["enemy"].Hp == 30 && commit.State.Entities["enemy"].Tags.Contains("status.wet") && commit.State.Entities["hero"].Energy == 8,"immunity prevents event and reactions; cast spends energy");
        state = Battle("class.cryomancer"); state.Entities["enemy"].Tags.Add("status.wet");
        state = engine.Execute(state,"hero","ability.frostbite","enemy").State; state.Entities["hero"].ClassId = "class.brawler";
        commit = engine.Execute(state,"hero","ability.shatter","enemy");
        Check(commit.State.Entities["enemy"].Hp == 11 && !commit.State.Entities["enemy"].Tags.Contains("status.frozen"),"freeze then shatter");
        state = Battle(); state.Entities["enemy"].X = 5;
        Check(Rejects(() => engine.Execute(state,"hero","ability.firebolt","enemy")),"range rejection");
        state.Entities["enemy"].X = 1; state.Entities["hero"].Energy = 1;
        Check(Rejects(() => engine.Execute(state,"hero","ability.firebolt","enemy")),"resource rejection");
        state.Entities["hero"].Energy = 10;
        Check(Rejects(() => engine.Execute(state,"hero","ability.firebolt","hero")) && Rejects(() => engine.Execute(state,"hero","ability.firebolt","tile")),"target faction and kind rejection");
        Check(Rejects(() => engine.Execute(state,"hero","ability.mend","hero")),"class ownership rejection");
        state = Battle("class.cleric"); state.Entities["hero"].Hp = 28;
        Check(engine.Execute(state,"hero","ability.mend","hero").State.Entities["hero"].Hp == 30,"ally includes self and healing clamps");
        TagQuery query = new TagQuery { all = new[]{"status.wet"}, any = new[]{"element.fire","element.cold"}, none = new[]{"surface.oil"} };
        var tags = new System.Collections.Generic.HashSet<string>(new[]{"status.wet","element.fire"});
        Check(query.Matches(tags),"all any none positive"); tags.Add("surface.oil"); Check(!query.Matches(tags),"none excludes");
        Check(new TagQuery().Matches(new System.Collections.Generic.HashSet<string>()),"empty queries are unconstrained");
        Content bad = Load(); bad.abilities[0].effects[0].op = "ExecuteCode"; Check(Rejects(() => new Catalog(bad)),"unknown operation rejected");
        bad = Load(); bad.abilities[0].incomingTags = new[]{"missing.tag"}; Check(Rejects(() => new Catalog(bad)),"unknown tag rejected");
        // Deliberate cycle: one rule emits its own trigger. Once per chain guarantees termination.
        Content cycle = Load(); cycle.reactions = new[]{new ReactionDef { id="reaction.cycle", incoming = new TagQuery{ all=new[]{"element.fire"}}, effects = new[]{new EffectDef{op="Damage",amount=1}}, emitTags=new[]{"element.fire"} }};
        RulesEngine cyc = new RulesEngine(new Catalog(cycle)); state = Battle();
        commit = cyc.Execute(state,"hero","ability.firebolt","enemy");
        Check(commit.State.Entities["enemy"].Hp == 21 && commit.Log.Length == 2,"duplicate rule prevented within chain");
        bool budgetFailed = false; before = Snapshot(state);
        try { new RulesEngine(new Catalog(cycle),1).Execute(state,"hero","ability.firebolt","enemy"); } catch (InvalidOperationException) { budgetFailed = true; }
        Check(budgetFailed && Snapshot(state) == before,"budget failure is atomic");
        // Same priority: ordinal ID decides who consumes the shared prerequisite.
        Content ordering = Load(); ordering.reactions = new[]{
            new ReactionDef{id="reaction.z",priority=5,incoming=new TagQuery{all=new[]{"element.fire"}},target=new TagQuery{all=new[]{"status.wet"}},consumeTags=new[]{"status.wet"},effects=new[]{new EffectDef{op="Damage",amount=9}}},
            new ReactionDef{id="reaction.a",priority=5,incoming=new TagQuery{all=new[]{"element.fire"}},target=new TagQuery{all=new[]{"status.wet"}},consumeTags=new[]{"status.wet"},effects=new[]{new EffectDef{op="Damage",amount=1}}}};
        state = Battle(); state.Entities["enemy"].Tags.Add("status.wet"); commit = new RulesEngine(new Catalog(ordering)).Execute(state,"hero","ability.firebolt","enemy");
        Check(commit.State.Entities["enemy"].Hp == 21 && commit.Log[1] == "reaction.a","stable ID order and consumed prerequisite suppression");
        // An author can add a new class, ability, tag, and reaction without a rules-code change.
        Content extension = Load();
        extension.tags = extension.tags.Concat(new[]{new TagDef{id="element.echo",label="Echo"}}).ToArray();
        extension.abilities = extension.abilities.Concat(new[]{new AbilityDef{id="ability.echo",label="Echo",target="enemy",range=2,cost=1,incomingTags=new[]{"element.echo"},effects=new[]{new EffectDef{op="Damage",amount=2}}}}).ToArray();
        extension.classes = extension.classes.Concat(new[]{new ClassDef{id="class.echo_knight",label="Echo Knight",abilityIds=new[]{"ability.echo"}}}).ToArray();
        extension.reactions = extension.reactions.Concat(new[]{new ReactionDef{id="reaction.echo_wet",incoming=new TagQuery{all=new[]{"element.echo"}},target=new TagQuery{all=new[]{"status.wet"}},effects=new[]{new EffectDef{op="Damage",amount=3}}}}).ToArray();
        state = Battle("class.echo_knight"); state.Entities["enemy"].Tags.Add("status.wet");
        commit = new RulesEngine(new Catalog(extension)).Execute(state,"hero","ability.echo","enemy");
        Check(commit.State.Entities["enemy"].Hp == 25 && commit.State.Entities["hero"].Energy == 9 && commit.Log.Contains("reaction.echo_wet"),"data-only new class ability tag and reaction extension");
        Content chain = Load(); chain.reactions = new[]{
            new ReactionDef{id="reaction.first",incoming=new TagQuery{all=new[]{"element.fire"}},effects=new[]{new EffectDef{op="Damage",amount=2}},emitTags=new[]{"element.lightning"}},
            new ReactionDef{id="reaction.second",incoming=new TagQuery{all=new[]{"element.lightning"}},effects=new[]{new EffectDef{op="Damage",amount=3}}}};
        state = Battle(); commit = new RulesEngine(new Catalog(chain)).Execute(state,"hero","ability.firebolt","enemy");
        Check(commit.State.Entities["enemy"].Hp == 17 && commit.Log.SequenceEqual(new[]{"ability.firebolt","reaction.first","reaction.second"}),"different rules chain through emitted event tags");
        state = Battle("class.cleric"); state.Entities["enemy"].Team = "party"; state.Entities["enemy"].Hp = 0;
        Check(Rejects(() => engine.Execute(state,"hero","ability.mend","enemy")),"dead allies cannot be healed or revived");
        state = Battle(); state.Entities["enemy"].Hp = 0;
        Check(Rejects(() => engine.Execute(state,"hero","ability.firebolt","enemy")),"dead enemies cannot be targeted");
        state = Battle(); state.Entities["enemy"].Tags.Add("status.wet"); state.Entities["enemy"].Immunities.Add("element.cold");
        BattleState clone = state.Clone(); clone.Entities["enemy"].Tags.Remove("status.wet"); clone.Entities["enemy"].Tags.Add("status.frozen"); clone.Entities["enemy"].Immunities.Clear();
        Check(state.Entities["enemy"].Tags.Contains("status.wet") && !state.Entities["enemy"].Tags.Contains("status.frozen") && state.Entities["enemy"].Immunities.Contains("element.cold"),"clone tag and immunity collections are isolated");
        Content magnitude = Load(); magnitude.abilities.Single(a=>a.id=="ability.firebolt").effects[0].amount = int.MaxValue;
        magnitude.abilities.Single(a=>a.id=="ability.mend").effects[0].amount = int.MaxValue;
        RulesEngine huge = new RulesEngine(new Catalog(magnitude)); state = Battle();
        Check(huge.Execute(state,"hero","ability.firebolt","enemy").State.Entities["enemy"].Hp == 0,"maximum damage clamps without underflow");
        state = Battle("class.cleric"); state.Entities["hero"].MaxHp = int.MaxValue; state.Entities["hero"].Hp = int.MaxValue-1;
        Check(huge.Execute(state,"hero","ability.mend","hero").State.Entities["hero"].Hp == int.MaxValue,"maximum healing clamps without overflow");
        ordering.reactions[0].priority = 10; // reaction.z must beat reaction.a despite its later ordinal ID.
        state = Battle(); state.Entities["enemy"].Tags.Add("status.wet"); commit = new RulesEngine(new Catalog(ordering)).Execute(state,"hero","ability.firebolt","enemy");
        Check(commit.State.Entities["enemy"].Hp == 13 && commit.Log[1] == "reaction.z","descending priority precedes ordinal ID");
        Content retroactive = Load(); retroactive.reactions = new[]{new ReactionDef{id="reaction.must_already_be_wet",incoming=new TagQuery{all=new[]{"element.water"}},target=new TagQuery{all=new[]{"status.wet"}},effects=new[]{new EffectDef{op="Damage",amount=10}}}};
        state = Battle("class.alchemist"); commit = new RulesEngine(new Catalog(retroactive)).Execute(state,"hero","ability.douse","enemy");
        Check(commit.State.Entities["enemy"].Hp == 30 && commit.State.Entities["enemy"].Tags.Contains("status.wet") && commit.Log.Length == 1,"event effects cannot retroactively enable reaction");
        bad = Load(); bad.abilities.Single(a=>a.id=="ability.oil_flask").effects[0].amount = -1;
        Check(Rejects(() => new Catalog(bad)),"negative amount rejected even for tag operations");
        Content noRevive = Load();
        noRevive.abilities.Single(a=>a.id=="ability.firebolt").effects = new[]{new EffectDef{op="Damage",amount=30},new EffectDef{op="Heal",amount=30}};
        state = Battle(); commit = new RulesEngine(new Catalog(noRevive)).Execute(state,"hero","ability.firebolt","enemy");
        Check(commit.State.Entities["enemy"].Hp == 0,"lethal damage followed by healing in one event cannot revive");
        Content combat = JsonSerializer.Deserialize<Content>(File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "combat-content.json")), new JsonSerializerOptions { IncludeFields = true });
        RulesEngine playable = new RulesEngine(new Catalog(combat));
        foreach (var kit in new[]{("class.guardian", "ability.bulwark"), ("class.bard", "ability.rally"), ("class.necromancer", "ability.siphon_ward")})
        {
            state = Battle(kit.Item1); state.Entities["hero"].Hp = 5;
            commit = playable.Execute(state, "hero", kit.Item2, "hero");
            Check(commit.State.Entities["hero"].Hp > 5 && commit.State.Entities["hero"].Tags.Contains("status.guarded"), kit.Item1 + " support heals and grants protection");
        }
        state = Battle(); state.Entities["enemy"].Hp = 5; state.Entities["enemy"].Tags.Add("status.guarded");
        before = Snapshot(state); preview = playable.Preview(state, "hero", "ability.firebolt", "enemy"); commit = playable.Execute(state, "hero", "ability.firebolt", "enemy");
        Check(commit.State.Entities["enemy"].Hp == 1 && !commit.State.Entities["enemy"].Tags.Contains("status.guarded"), "guard prevents lethal damage and consumes on hit");
        Check(Snapshot(preview.State) == Snapshot(commit.State) && Snapshot(state) == before, "guard forecast matches commit without mutation");
        state.Entities["enemy"].Hp = 30; state.Entities["enemy"].Immunities.Add("element.fire");
        Check(playable.Execute(state, "hero", "ability.firebolt", "enemy").State.Entities["enemy"].Tags.Contains("status.guarded"), "immune attacks preserve guard");
        state = Battle("class.cleric"); state.Entities["hero"].Hp = 5; state.Entities["hero"].Tags.Add("status.guarded");
        Check(playable.Execute(state, "hero", "ability.mend", "hero").State.Entities["hero"].Tags.Contains("status.guarded"), "healing preserves guard");
        combat.abilities.Single(a => a.id == "ability.firebolt").effects = new[]{new EffectDef{op="AddTag",tag="status.wet"},new EffectDef{op="Damage",amount=0}};
        state = Battle(); state.Entities["enemy"].Tags.Add("status.guarded");
        commit = new RulesEngine(new Catalog(combat)).Execute(state,"hero","ability.firebolt","enemy");
        Check(commit.State.Entities["enemy"].Tags.Contains("status.guarded") && !commit.Log.Contains("reaction.guarded_blocks"), "tag-only event with matching element and zero damage preserves guard");
        combat.abilities.Single(a => a.id == "ability.firebolt").effects = new[]{new EffectDef{op="Damage",amount=4},new EffectDef{op="Damage",amount=4}};
        playable = new RulesEngine(new Catalog(combat)); state = Battle(); state.Entities["enemy"].Tags.Add("status.guarded");
        commit = playable.Execute(state,"hero","ability.firebolt","enemy");
        Check(commit.State.Entities["enemy"].Hp == 28, "guard budget shared across multiple damage effects");
        commit = playable.Execute(commit.State,"hero","ability.firebolt","enemy");
        Check(commit.State.Entities["enemy"].Hp == 20, "consumed guard does not protect a second attack");
        ReactionDef guard = combat.reactions.Single(r => r.id == "reaction.guarded_blocks");
        combat.reactions = new[]{guard,new ReactionDef{id="reaction.lower_guard",priority=100,damageReduction=20,incoming=new TagQuery{all=new[]{"element.fire"}},target=new TagQuery{all=new[]{"status.guarded"}},consumeTags=new[]{"status.guarded"}}};
        state = Battle(); state.Entities["enemy"].Tags.Add("status.guarded"); commit = new RulesEngine(new Catalog(combat)).Execute(state,"hero","ability.firebolt","enemy");
        Check(commit.State.Entities["enemy"].Hp == 28 && !commit.Log.Contains("reaction.lower_guard"), "higher priority protection consumes shared prerequisite");
        guard.damageReduction = -1;
        Check(Rejects(() => new Catalog(combat)), "negative damage reduction rejected");
        Console.WriteLine(passed + " semantic checks passed.");
    }
}
