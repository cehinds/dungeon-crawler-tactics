using DccRebuild;

static class CombatFollowthroughChecks
{
    static void Check(bool ok, string message) { if (!ok) throw new Exception("combat followthrough: " + message); }
    static (Game game, View view, Unit actor, Unit target) Arena(string json)
    {
        var game = new Game(json, 71); var view = game.GetView();
        var door = view.world.objects.Single(o => o.id == "false-guild");
        view.x = door.x; view.y = door.y; game.Handle(new() { type = "interact", targetId = door.id });
        var actor = view.party.Single(u => u.id == "carl"); actor.x = 2; actor.y = 2; actor.mp = actor.maxMp = 100;
        view.party.Single(u => u.id == "donut").x = 0; view.party.Single(u => u.id == "donut").y = 5;
        var target = view.battle.enemies[0]; target.x = 3; target.y = 2; target.hp = target.maxHp = 1000; target.armor = 0; target.tags = []; target.element = "physical";
        foreach (var other in view.battle.enemies.Skip(1)) other.hp = 0;
        view.battle.effectObjects.Clear(); view.battle.hazards.Clear(); view.battle.effectEvents.Clear(); view.battle.obstacles = [];
        return (game, view, actor, target);
    }
    static Forecast Predict(Game game, Unit actor, string skill, string targetId = "", int x = 0, int y = 0) =>
        game.Handle(new() { type = "forecast", actorId = actor.id, skillId = skill, targetId = targetId, x = x, y = y }).forecast;
    // Command event receipts are transient and may clear on rejected commands.
    static string State(View view)
    {
        var battle = Codec.Read<Battle>(Codec.Write(view.battle)); battle.effectEvents = [];
        return Codec.Write(new { view.party, battle, view.inventory, view.gold, view.questStage });
    }
    public static void Run(string json)
    {
        Blast(json); Unarmed(json); PendingSkill(json); SupportSkills(json); InvalidContent(json);
        Console.WriteLine("PASS: ground blast per-target defense, clipped cells, chained friendly fire, immutable preview/commit parity, unarmed rank/baseline scaling, ally/self support parity and invalid content rejection.");
    }
    static void Blast(string json)
    {
        var content = Codec.Read<Content>(json);
        content.effectRules.damageBonuses = [new() { incomingTag = "fire", targetTag = "fixture-weak", amount = 7, reaction = "Fixture weakness" }];
        var (game, view, actor, target) = Arena(Codec.Write(content));
        var other = new Unit { id = "fixture-armored", x = 4, y = 2, hp = 1000, maxHp = 1000, armor = 8 };
        view.battle.enemies.Add(other); target.armor = 2; target.tags = ["fixture-weak"];
        view.battle.effectObjects.Add(new() { id = "fixture-weak-object", x = 3, y = 3, hp = 1000, tags = ["destructible", "fixture-weak"] });
        view.battle.effectObjects.Add(new() { id = "fixture-plain-object", x = 3, y = 1, hp = 1000, tags = ["destructible"] });
        var before = State(view);
        var forecast = Predict(game, actor, "bomb", target.id);
        Check(forecast.valid && forecast.cost == 2 && forecast.x == 3 && forecast.y == 2, "legacy direct ID resolves bomb center and adapted mana cost");
        Check(State(view) == before, "forecast cannot mutate combat/resources/practice");
        Check(forecast.damage == Math.Max(1, forecast.baseDamage - 2 + 7), "primary forecast uses primary defense");
        Check(forecast.events.Where(e => e.kind == "damage" && e.targetId == other.id).Sum(e => e.amount) == Math.Max(1, forecast.baseDamage - 8), "collateral armor uses its own defense without primary weakness leaking");
        Check(forecast.events.Where(e => e.kind == "objectDamaged" && e.targetId == "fixture-weak-object").Sum(e => e.amount) == forecast.baseDamage + 7, "collateral object receives its own weakness");
        Check(forecast.events.Where(e => e.kind == "objectDamaged" && e.targetId == "fixture-plain-object").Sum(e => e.amount) == forecast.baseDamage, "plain collateral object does not inherit another target weakness");
        Check(forecast.friendlyFire && forecast.affectedCells.Length == 5, "radius-one cross includes adjacent actor and warns");
        int mp = actor.mp, practice = actor.skillPractice["bomb"];
        game.Handle(new() { type = "confirm" });
        Check(actor.mp == mp - forecast.cost && actor.acted && actor.skillPractice["bomb"] == practice + content.progression.practicePerUse, "multi-target commit charges mana/action/practice once");
        Check(Codec.Write(view.battle.effectEvents) == Codec.Write(forecast.events), "all initial and reaction events match preview");
        Check(other.hp == 1000 - Math.Max(1, forecast.baseDamage - 8), "collateral commit matches its defended preview");
        var after = State(view); game.Handle(new() { type = "confirm" }); Check(State(view) == after, "repeat confirm cannot charge or damage twice");

        var (edgeGame, edgeView, edgeActor, _) = Arena(json); edgeActor.x = 1; edgeActor.y = 0;
        var edge = Predict(edgeGame, edgeActor, "bomb", x: 0, y: 0);
        Check(edge.valid && edge.affectedCells.Length == 3 && edge.affectedCells.All(p => p.x >= 0 && p.y >= 0 && p.x < edgeView.battle.width && p.y < edgeView.battle.height), "corner blast footprint clips to board");
        foreach (var cell in new[] { (-1, 0), (0, -1), (edgeView.battle.width, 0), (0, edgeView.battle.height), (9, 7) })
        {
            var snapshot = State(edgeView); Check(!Predict(edgeGame, edgeActor, "bomb", x: cell.Item1, y: cell.Item2).valid, "invalid coordinate or range rejects");
            edgeGame.Handle(new() { type = "confirm" }); Check(State(edgeView) == snapshot, "invalid ground attack changes no combat state");
        }
        var (chainGame, chainView, chainActor, _) = Arena(json); chainActor.x = 1; chainActor.y = 2;
        var ally = chainView.party.Single(u => u.id == "donut"); ally.x = 5; ally.y = 2;
        chainView.battle.effectObjects.Add(new() { id = "fixture-chain-a", x = 3, y = 2, hp = 1, tags = ["destructible", "explosive"] });
        chainView.battle.effectObjects.Add(new() { id = "fixture-chain-b", x = 4, y = 2, hp = 1, tags = ["destructible", "explosive"] });
        var chain = Predict(chainGame, chainActor, "bomb", x: 3, y: 2);
        Check(chain.valid && chain.friendlyFire && chain.events.Any(e => e.kind == "damage" && e.targetId == ally.id), "chain outside initial footprint warns of ally damage");
        Check(chain.affectedCells.Any(p => p.x == ally.x && p.y == ally.y), "affected cells include chained explosion reach beyond initial blast");
    }
    static void Unarmed(string json)
    {
        var (game, view, actor, target) = Arena(json);
        foreach (var rank in new[] { 3, 4, 5 })
        {
            actor.ranks["powerful-strike"] = rank;
            var punch = Predict(game, actor, "punch", target.id); var strike = Predict(game, actor, "powerful-strike", target.id);
            double multiplier = rank == 3 ? 1.5 : rank == 4 ? 1.75 : 2;
            Check(strike.valid && strike.baseDamage == (int)Math.Round(punch.baseDamage * multiplier, MidpointRounding.AwayFromZero), "strike scales current unarmed baseline at rank " + rank);
        }
        var beforeGain = Predict(game, actor, "powerful-strike", target.id).baseDamage;
        actor.ranks["punch"] = 5; actor.power += 3;
        var baseline = Predict(game, actor, "punch", target.id); var improved = Predict(game, actor, "powerful-strike", target.id);
        Check(improved.baseDamage == baseline.baseDamage * 2 && improved.baseDamage > beforeGain, "Punch rank and crawler power gains feed unarmed baseline");
        var (dryGame, dryView, dryActor, dryTarget) = Arena(json); dryActor.mp = 0; dryGame.GetView();
        var dryState = State(dryView); Check(!Predict(dryGame, dryActor, "powerful-strike", dryTarget.id).valid, "strike rejects insufficient mana");
        dryGame.Handle(new() { type = "confirm" }); Check(State(dryView) == dryState, "insufficient mana consumes no action/resources/practice");
        var content = Codec.Read<Content>(json); var weapon = content.items.First(); weapon.kind = "weapon";
        var (armedGame, armedView, armedActor, armedTarget) = Arena(Codec.Write(content)); armedActor.equipment = weapon.id; armedGame.GetView();
        var snapshot = State(armedView); Check(!Predict(armedGame, armedActor, "powerful-strike", armedTarget.id).valid, "unarmed strike rejects a weapon even in imported runtime state");
        armedGame.Handle(new() { type = "confirm" }); Check(State(armedView) == snapshot, "weapon rejection consumes no action/resources/practice");
    }
    static void PendingSkill(string json)
    {
        var (game, view, actor, target) = Arena(json);
        var strike = Predict(game, actor, "powerful-strike", target.id);
        Predict(game, actor, "bomb", target.id);
        int mp = actor.mp, hp = target.hp;
        game.Handle(new() { type = "confirm", actorId = actor.id, skillId = "powerful-strike", targetId = target.id });
        Check(actor.acted && actor.mp == mp - strike.cost && target.hp == hp - strike.damage,
            "explicit different skill confirm uses its default mana rather than stale pending Bomb cost");
    }
    static void SupportSkills(string json)
    {
        foreach (var targetKind in new[] { "ally", "self" })
        {
            var content = Codec.Read<Content>(json);
            var support = content.skills.Single(s => s.id == "punch");
            support.targetKind = targetKind;
            support.effectOperations = [new() { kind = "heal", amount = 7 }];
            foreach (var rank in support.ranks) rank.cost = 1;
            var (game, view, actor, _) = Arena(Codec.Write(content));
            var target = targetKind == "self" ? actor : view.party.Single(u => u.id == "donut");
            target.x = targetKind == "self" ? actor.x : actor.x + 1; target.y = actor.y;
            target.hp = target.maxHp - 10; target.armor = 100;
            game.GetView();
            var snapshot = State(view); int hp = target.hp, mp = actor.mp, practice = actor.skillPractice[support.id];
            var forecast = Predict(game, actor, support.id, target.id);
            Check(forecast.valid && forecast.baseDamage == 0 && forecast.damage == 0 && forecast.cost == 1,
                targetKind + " support has zero initial damage despite offensive authored power and target armor");
            Check(State(view) == snapshot && !forecast.events.Any(e => e.kind == "damage" && e.amount > 0),
                targetKind + " support preview is immutable and cannot introduce minimum damage");
            Check(forecast.events.Any(e => e.kind == "heal" && e.targetId == target.id && e.amount == 7),
                targetKind + " authored heal targets intended crawler");
            game.Handle(new() { type = "confirm" });
            Check(target.hp == hp + 7 && actor.mp == mp - 1 && actor.acted && actor.skillPractice[support.id] == practice + content.progression.practicePerUse,
                targetKind + " support heals and spends mana/action/practice once");
            Check(Codec.Write(view.battle.effectEvents) == Codec.Write(forecast.events), targetKind + " support preview and commit events agree");
        }
    }
    static void InvalidContent(string json)
    {
        foreach (var kind in new[] { "missing", "cycle", "wrong" })
        {
            var content = Codec.Read<Content>(json); var strike = content.skills.Single(s => s.id == "powerful-strike");
            strike.damageBasis = "unarmed";
            strike.baseSkillId = kind == "missing" ? "absent-skill" : kind == "cycle" ? strike.id : "magic-missile";
            bool rejected = false; try { _ = new Game(Codec.Write(content)); } catch { rejected = true; }
            Check(rejected, "reject " + kind + " unarmed baseline reference");
        }
    }
}
