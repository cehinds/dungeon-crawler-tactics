using DccRebuild;
using System.Text.Json.Nodes;

static class ProgressionChecks
{
    static void Check(bool condition, string label) { if (!condition) throw new Exception("progression: " + label); }
    // Combat fixtures enter through the real encounter command. Durable, harmless targets
    // isolate practice/commit behavior without claiming a simulated campaign to level 20.
    static (Game game, View view, Unit actor, Unit target) Arena(string json, string actorId = "carl")
    {
        var game = new Game(json, 71); var view = game.GetView();
        var door = view.world.objects.Single(o => o.id == "false-guild");
        view.x = door.x; view.y = door.y;
        game.Handle(new() { type = "interact", targetId = door.id });
        Check(view.mode == "battle", "fixture encounter starts normally");
        var actor = view.party.Single(u => u.id == actorId);
        actor.x = 1; actor.y = 2; actor.mp = actor.maxMp = 1000;
        var other = view.party.Single(u => u != actor); other.x = 1; other.y = 5;
        var target = view.battle.enemies[0]; target.x = 2; target.y = 2;
        target.hp = target.maxHp = 10000; target.power = target.armor = 0;
        foreach (var enemy in view.battle.enemies.Skip(1)) enemy.hp = 0;
        return (game, view, actor, target);
    }
    static Forecast Forecast(Game g, Unit a, Unit t, string skill, int spend = 0) =>
        g.Handle(new() { type = "forecast", actorId = a.id, targetId = t.id, skillId = skill, manaSpend = spend }).forecast;
    static void Cast(Game g, Unit a, Unit t, string skill, int spend = 0, bool bare = false)
    {
        var f = Forecast(g, a, t, skill, spend); Check(f.valid, "cast is available " + skill);
        int hp = t.hp, mp = a.mp;
        g.Handle(bare ? new() { type = "confirm" } : new() { type = "confirm", actorId = a.id, targetId = t.id, skillId = skill, manaSpend = spend });
        Check(t.hp == hp - f.damage && a.mp == mp - f.cost, "forecast/commit damage and cost " + skill + "/" + spend);
    }
    static string SafeSave(Game game)
    {
        var v = game.GetView(); var safe = v.world.objects.First(o => o.kind == "safe");
        var cell = new[] { (safe.x - 1, safe.y), (safe.x + 1, safe.y), (safe.x, safe.y - 1), (safe.x, safe.y + 1) }
            .First(p => v.world.tiles[p.Item2 * v.world.width + p.Item1] == ".");
        v.x = cell.Item1; v.y = cell.Item2;
        return game.GetSave();
    }
    public static void Run(string json)
    {
        var data = JsonNode.Parse(json);
        var fresh = new Game(json).GetView();
        Check(fresh.party[0].ranks["powerful-strike"] == 3, "authored starting mastery rank");
        var (g, v, a, t) = Arena(json);
        for (int i = 0; i < 8; i++) Forecast(g, a, t, "punch");
        Check(a.skillPractice["punch"] == 0 && a.ranks["punch"] == 1, "repeated forecasts give no practice");
        int hp = t.hp, mp = a.mp;
        g.Handle(new() { type = "confirm", actorId = a.id, targetId = t.id, skillId = "unknown" });
        Check(t.hp == hp && a.mp == mp && !a.acted && a.skillPractice["punch"] == 0, "invalid confirm spends no resources/practice/action");
        Cast(g, a, t, "punch");
        Check(a.ranks["punch"] == 1 && a.skillPractice["punch"] == 1, "one hit does not grant a rank");
        g.Handle(new() { type = "endTurn" }); Cast(g, a, t, "punch");
        g.Handle(new() { type = "endTurn" });
        var boundary = Forecast(g, a, t, "punch");
        Check(boundary.trainedRank == 1, "threshold hit forecasts old trained rank");
        Cast(g, a, t, "punch", bare: true);
        Check(a.ranks["punch"] == 2 && a.skillPractice["punch"] == 3, "exact practice boundary grants rank");
        g.Handle(new() { type = "endTurn" });
        var next = Forecast(g, a, t, "punch");
        Check(next.trainedRank == 2 && next.effectiveRank == 2 && next.damage > boundary.damage, "next attack uses new rank");

        var (mg, mv, mage, mt) = Arena(json, "donut");
        var locked = Forecast(mg, mage, mt, "magic-missile", 3);
        Check(!locked.valid, "mana choice locked before mastery rank 5");
        int lockedMp = mage.mp, lockedHp = mt.hp;
        mg.Handle(new() { type = "confirm" });
        Check(mage.mp == lockedMp && mt.hp == lockedHp && !mage.acted && mage.skillPractice["magic-missile"] == 0, "locked mana confirm has no effects");
        for (int i = 0; i < 24; i++) { Cast(mg, mage, mt, "magic-missile"); mg.Handle(new() { type = "endTurn" }); }
        Check(mage.ranks["magic-missile"] == 5 && mage.skillPractice["magic-missile"] == 24, "normal committed casts unlock mana choices");
        int previousDamage = -1;
        foreach (int spend in new[] { 3, 4, 5, 6 })
        {
            var f = Forecast(mg, mage, mt, "magic-missile", spend);
            Check(f.valid && f.cost == spend && f.manaSpend == spend && f.trainedRank == 5 && f.effectiveRank == 5 && f.effectRank == 5, "rank 5 mana option " + spend);
            Check(f.damage > previousDamage, "extra mana increases damage"); previousDamage = f.damage;
            foreach (bool bare in new[] { false, true })
            { Cast(mg, mage, mt, "magic-missile", spend, bare: bare); mg.Handle(new() { type = "endTurn" }); }
        }
        Check(Forecast(mg, mage, mt, "magic-missile").cost == 3, "rank-five default spend is base mana cost");
        foreach (int spend in new[] { -1, 1, 2, 7, 100 })
        {
            int beforeMp = mage.mp, beforeHp = mt.hp, practice = mage.skillPractice["magic-missile"];
            Check(!Forecast(mg, mage, mt, "magic-missile", spend).valid, "unsupported mana amount rejected " + spend);
            mg.Handle(new() { type = "confirm" });
            Check(mage.mp == beforeMp && mt.hp == beforeHp && !mage.acted && mage.skillPractice["magic-missile"] == practice, "invalid spend is transactional " + spend);
        }
        mage.mp = 2;
        Check(!Forecast(mg, mage, mt, "magic-missile", 3).valid, "insufficient chosen mana rejected");
        ModifierAndLevelBoundaries(json);
        Saves(json);
        Levels(json, data);
        Console.WriteLine("PASS: mastery thresholds, old-rank boundary hits, mana choices and commit parity; progression save migration/validation; level table rewards.");
    }
    static void ModifierAndLevelBoundaries(string json)
    {
        var content = Codec.Read<Content>(json);
        var skill = content.skills.Single(s => s.id == "punch");
        var gear = content.items[0]; gear.rankModifiers[skill.id] = 2;
        var progression = new Progression(content);
        var unit = new Game(json).GetView().party[0];
        unit.ranks[skill.id] = 1; unit.equipment = gear.id; unit.temporaryRankModifiers[skill.id] = 1;
        progression.Refresh(unit);
        var first = unit.skillProgress.Single(p => p.skillId == skill.id);
        Check(first.trainedRank == 1 && first.gearBonusRank == 2 && first.effectiveRank == 4, "trained/gear/temporary ranks stay distinct and apply once");
        progression.Refresh(unit);
        Check(unit.ranks[skill.id] == 1 && unit.skillProgress.Single(p => p.skillId == skill.id).effectiveRank == 4, "repeated refresh never adds rank modifiers again");
        unit.temporaryRankModifiers[skill.id] = 100;
        Check(progression.EffectiveRank(unit, skill) == skill.permissionMaxRank, "effective rank respects permission cap");
        unit.equipment = ""; unit.temporaryRankModifiers.Clear();
        Check(progression.EffectiveRank(unit, skill) == 1, "removing modifiers restores trained rank");
        foreach (var row in content.progression.levels.Skip(1))
        {
            var below = new Game(json).GetView().party[0];
            progression.Reward(below, row.totalXp - 1);
            Check(below.level == row.level - 1, "one XP below level threshold " + row.level);
            progression.Reward(below, 1);
            Check(below.level == row.level, "exact level threshold " + row.level);
        }
        Check(content.skills.Select(s => s.id).Order().SequenceEqual(new[] { "bomb", "claw", "magic-missile", "powerful-strike", "punch" }), "all five existing authored skills retained");
    }
    static void Levels(string json, JsonNode data)
    {
        var levels = data["progression"]["levels"].AsArray();
        Check(levels.Count == 20 && levels[0]["totalXp"].GetValue<int>() == 0 && levels.Select(r => r["totalXp"].GetValue<int>()).SequenceEqual(levels.Select(r => r["totalXp"].GetValue<int>()).Order()), "explicit cumulative level 1–20 table");
        foreach (int reward in new[] { 99, 100, 480, 20000 })
        {
            var fixture = JsonNode.Parse(json);
            fixture["encounters"].AsArray().Single(e => e["id"].GetValue<string>() == "false-guild")["xpReward"] = reward;
            var (game, view, actor, target) = Arena(fixture.ToJsonString());
            actor.maxMp = new Game(json).GetView().party.Single(u => u.id == actor.id).maxMp;
            actor.mp = actor.maxMp;
            var baseStats = view.party.Select(u => (u.maxHp, u.maxMp, u.power, u.armor)).ToArray();
            target.hp = 1;
            game.Handle(new() { type = "confirm", actorId = actor.id, targetId = target.id, skillId = "punch" });
            Check(view.mode == "explore", "isolated reward fixture wins via normal commit");
            int expectedLevel = levels.Last(r => r["totalXp"].GetValue<int>() <= reward)["level"].GetValue<int>();
            var gains = levels.Where(r => r["level"].GetValue<int>() <= expectedLevel).ToArray();
            for (int i = 0; i < view.party.Count; i++)
            {
                var u = view.party[i]; var b = baseStats[i];
                Check(u.level == expectedLevel && u.xp == reward, "reward crosses every attained level " + reward);
                Check(u.maxHp == b.maxHp + gains.Sum(r => r["hpGain"].GetValue<int>()) && u.maxMp == b.maxMp + gains.Sum(r => r["manaGain"].GetValue<int>()) && u.power == b.power + gains.Sum(r => r["powerGain"].GetValue<int>()) && u.armor == b.armor + gains.Sum(r => r["armorGain"].GetValue<int>()), "every authored level gain applied exactly once " + reward);
                Check(u.level <= 20 && (u.level < 20 || u.xpToNext == 0), "level cap has no next XP target");
            }
            var receipt = Codec.Write(new { view.party, view.gold, view.cleared });
            game.Handle(new() { type = "interact", targetId = "false-guild" });
            game.Handle(new() { type = "confirm", actorId = actor.id, targetId = target.id, skillId = "punch" });
            Check(Codec.Write(new { view.party, view.gold, view.cleared }) == receipt, "repeat encounter/confirm cannot reclaim XP or gold");
        }
    }
    static void Saves(string json)
    {
        var source = new Game(json, 71); var sv = source.GetView();
        var item = Codec.Read<Content>(json).items.First(i => i.kind == "armor" || i.kind == "charm");
        if (!sv.inventory.Any(s => s.itemId == item.id && s.count > 0))
            sv.inventory.Add(new() { itemId = item.id, count = 1 });
        source.Handle(new() { type = "equip", actorId = "carl", itemId = item.id });
        Check(sv.party[0].equipment == item.id, "roundtrip equipment fixture equipped normally");
        var save = SafeSave(source); Check(JsonNode.Parse(save)["version"].GetValue<int>() == 3, "new saves are foundation version 3");
        var receiver = new Game(json, 2); receiver.LoadSave(save);
        Check(!receiver.GetView().message.StartsWith("Invalid save"), "valid v2 loads");
        var versionTwo = JsonNode.Parse(save); versionTwo["version"] = 2;
        versionTwo["state"].AsObject().Remove("unlockedEvents");
        versionTwo["state"].AsObject().Remove("floor");
        foreach (var oldUnit in versionTwo["state"]["party"].AsArray()) oldUnit.AsObject().Remove("temporaryRankModifiers");
        receiver.LoadSave(versionTwo.ToJsonString());
        Check(!receiver.GetView().message.StartsWith("Invalid save") && receiver.GetView().floor == 1 && receiver.GetView().unlockedEvents != null && receiver.GetView().party.All(u => u.temporaryRankModifiers != null), "v2 migrates foundation state into v3");
        Check(JsonNode.Parse(SafeSave(receiver))["version"].GetValue<int>() == 3, "migrated v2 writes v3 envelope");
        var loaded = receiver.GetView().party[0]; var equipped = sv.party[0];
        Check(loaded.power == equipped.power && loaded.armor == equipped.armor && loaded.equipment == equipped.equipment && Codec.Write(loaded.skillPractice) == Codec.Write(equipped.skillPractice), "v2 equipment/stat/practice roundtrip without doubled bonuses");
        receiver.LoadSave(SafeSave(receiver));
        Check(receiver.GetView().party[0].power == equipped.power && receiver.GetView().party[0].armor == equipped.armor, "repeated v2 roundtrip does not add equipment again");
        foreach (var corruption in new[] { "negative-practice", "NaN-practice", "unknown-practice", "null-practice", "negative-rank", "unknown-rank", "inconsistent-rank", "negative-xp", "NaN-xp", "forged-legacy-flag" })
        {
            var broken = JsonNode.Parse(save); var u = broken["state"]["party"][0];
            switch (corruption)
            {
                case "negative-practice": u["skillPractice"]["punch"] = -1; break;
                case "NaN-practice": u["skillPractice"]["punch"] = "NaN"; break;
                case "unknown-practice": u["skillPractice"]["unlearned"] = 0; break;
                case "null-practice": u["skillPractice"] = null; break;
                case "negative-rank": u["ranks"]["punch"] = -1; break;
                case "unknown-rank": u["ranks"]["unlearned"] = 1; break;
                case "inconsistent-rank": u["ranks"]["punch"] = 3; break;
                case "negative-xp": u["xp"] = -1; break;
                case "NaN-xp": u["xp"] = "NaN"; break;
                case "forged-legacy-flag": u["legacyProgression"] = true; u["xp"] = 200; break;
            }
            var previous = receiver.GetView(); var before = Codec.Write(new { previous.party, previous.inventory, previous.cleared, previous.world, previous.x, previous.y });
            receiver.LoadSave(broken.ToJsonString());
            Check(ReferenceEquals(previous, receiver.GetView()) && previous.message.StartsWith("Invalid save") && Codec.Write(new { previous.party, previous.inventory, previous.cleared, previous.world, previous.x, previous.y }) == before, "malformed progression rejected transactionally " + corruption);
        }
        var legacy = JsonNode.Parse(save); legacy["version"] = 1;
        var legacyUnit = legacy["state"]["party"][0];
        legacyUnit["ranks"]["punch"] = 20; legacyUnit["level"] = 6; legacyUnit["xp"] = 150; legacyUnit["ranks"]["powerful-strike"] = 1;
        legacyUnit.AsObject().Remove("skillPractice");
        receiver.LoadSave(legacy.ToJsonString());
        var lv = receiver.GetView(); var lu = lv.party[0];
        Check(!lv.message.StartsWith("Invalid save") && lu.ranks["punch"] == 20 && lu.xp == 1100 && lu.level == 6 && lu.ranks["powerful-strike"] == 3 && lu.equipment == item.id && lu.power == equipped.power && lu.armor == equipped.armor, "v1 preserves level/high rank/equipment/stats, rebases XP and raises unavailable early PS rank");
        var progress = lu.skillProgress.Single(p => p.skillId == "punch");
        Check(progress.trainedRank == 20 && progress.gearBonusRank == 0 && progress.effectRank == 5, "legacy trained rank retained with authored effect cap and explicit gear distinction");
        legacyUnit["xp"] = 165; receiver.LoadSave(legacy.ToJsonString());
        Check(receiver.GetView().party[0].level == 6 && receiver.GetView().party[0].xp == 1300, "v1 rebases half of old level progress to half of authored interval");
        var legacyRoundtrip = SafeSave(receiver); receiver.LoadSave(legacyRoundtrip);
        Check(!receiver.GetView().message.StartsWith("Invalid save") && receiver.GetView().party[0].ranks["punch"] == 20, "migrated high mastery remains loadable in v2");
        var migratedView = receiver.GetView();
        var door = migratedView.world.objects.Single(o => o.id == "false-guild");
        migratedView.x = door.x; migratedView.y = door.y;
        receiver.Handle(new() { type = "interact", targetId = door.id });
        var veteran = migratedView.party[0]; var target = migratedView.battle.enemies[0];
        veteran.x = 1; veteran.y = 2; target.x = 2; target.y = 2;
        var legacyForecast = Forecast(receiver, veteran, target, "punch");
        Check(legacyForecast.valid && legacyForecast.trainedRank == 20 && legacyForecast.effectRank == 5, "legacy forecast discloses trained rank and capped effect rank");
    }
}
