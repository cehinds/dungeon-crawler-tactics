using DccRebuild;
using System.Text.Json.Nodes;

static class SaveMigrationChecks
{
    public static void Run(string content)
    {
        void Check(bool condition, string label) { if (!condition) throw new Exception(label); }
        var original = new Game(content, 71);
        var state = original.GetView();
        state.world = World.BuildLegacy(state.seed);
        var safe = state.world.objects.First(o => o.kind == "safe");
        state.x = safe.x - 1; state.y = safe.y;
        state.questStage = 2; state.cleared.Add("false-guild");
        state.gold = 47; state.party[0].level = 6; state.party[0].xp = 150; state.party[0].maxHp = 140; state.party[0].power = 24; state.party[0].ranks["punch"] = 3;
        state.journal.Add("Legacy checkpoint progress");
        var oldSave = original.GetSave();
        var oldNode = JsonNode.Parse(oldSave);
        oldNode["version"] = 1;
        oldNode["state"]["world"].AsObject().Remove("generationVersion");
        oldSave = oldNode.ToJsonString();
        string Progress(View v) => Codec.Write(new { party = v.party.Select(u => new { u.id, u.name, u.hp, u.maxHp, u.mp, u.maxMp, u.level, u.xp, u.power, u.armor, u.equipment, u.skills, u.ranks }), v.inventory, v.cleared, v.journal, v.questStage, v.gold, v.turn });
        state.party[0].xp = 1100; // v1 level-six floor 150 rebases to the authored level-six floor.
        var expected = Progress(state);
        var receiver = new Game(content, 9);
        receiver.LoadSave(oldSave);
        var migrated = receiver.GetView();
        Check(migrated.world.generationVersion == 4 && migrated.message.Contains("upgraded"), "legacy checkpoint upgrades");
        Check(Progress(migrated) == expected, "legacy progress preserved exactly");
        var nextSafe = migrated.world.objects.Single(o => o.id == safe.id);
        Check(Math.Abs(migrated.x - nextSafe.x) + Math.Abs(migrated.y - nextSafe.y) == 1, "migration retains safe room identity");
        Check(!migrated.world.objects.Any(o => o.x == migrated.x && o.y == migrated.y), "migration destination unoccupied");
        var currentSave = receiver.GetSave();
        var second = new Game(content, 3);
        second.LoadSave(currentSave);
        Check(second.GetView().x == migrated.x && second.GetView().y == migrated.y && Progress(second.GetView()) == expected, "current checkpoint roundtrip");
        Check(migrated.world.props.Length > 0 && migrated.world.props.Any(p => p.groupId != ""), "generated checkpoint has assembly groups");
        Check(Codec.Write(second.GetView().world.props) == Codec.Write(migrated.world.props), "checkpoint roundtrip retains full assembly metadata");
        foreach (var field in new[] { "groupId", "zone", "anchor", "layer", "offsetX", "groupX", "blocksMovement" })
        {
            var broken = JsonNode.Parse(currentSave);
            var prop = broken["state"]["world"]["props"][0];
            if (field == "blocksMovement") prop[field] = !prop[field].GetValue<bool>();
            else if (field is "offsetX" or "groupX") prop[field] = prop[field].GetValue<int>() + 1;
            else prop[field] = prop[field].GetValue<string>() + "-forged";
            var previous = second.GetView();
            var beforeProps = Codec.Write(previous.world.props);
            second.LoadSave(broken.ToJsonString());
            Check(ReferenceEquals(previous, second.GetView()) && Codec.Write(previous.world.props) == beforeProps && previous.message.StartsWith("Invalid save"), "reject forged assembly " + field);
        }
        foreach (var corruption in new[] { "world", "coordinates", "battle", "geometry", "quest", "version" })
        {
            var broken = JsonNode.Parse(oldSave);
            var b = broken["state"];
            switch (corruption)
            {
                case "world": b["world"] = null; break;
                case "coordinates": b["x"] = 0; b["y"] = 0; break;
                case "battle": b["mode"] = "battle"; break;
                case "geometry": b["world"]["objects"][0]["x"] = 0; break;
                case "quest": b["questStage"] = 4; break;
                case "version": b["world"]["generationVersion"] = 99; break;
            }
            var previous = receiver.GetView();
            var progress = Progress(previous); var x = previous.x; var y = previous.y;
            receiver.LoadSave(broken.ToJsonString());
            Check(ReferenceEquals(previous, receiver.GetView()) && Progress(previous) == progress && previous.x == x && previous.y == y && previous.message.StartsWith("Invalid save"), "transactional rejected legacy " + corruption);
        }
        var v3 = new Game(content, 1337);
        var v3state = v3.GetView(); v3state.world = World.BuildVersion3(1337);
        Check(v3state.world.generationVersion == 3 && v3state.world.width == 60 && v3state.world.height == 38 &&
            v3state.world.rooms.Single(r => r.objectId == "ball-of-swine").width == 11, "frozen version 3 remains historical geometry");
        var v3safe = v3state.world.objects.First(o => o.kind == "safe");
        v3state.x = v3safe.x - 1; v3state.y = v3safe.y;
        v3state.gold = 83;
        var v3progress = Progress(v3state);
        var v3receiver = new Game(content, 1); v3receiver.LoadSave(v3.GetSave());
        Check(v3receiver.GetView().world.generationVersion == 4 && Progress(v3receiver.GetView()) == v3progress,
            "version 3 checkpoint validates frozen rules and preserves exact progress");
        var forgedV3 = JsonNode.Parse(v3.GetSave());
        forgedV3["state"]["world"]["tiles"][0] = ".";
        var priorV3 = v3receiver.GetView();
        v3receiver.LoadSave(forgedV3.ToJsonString());
        Check(ReferenceEquals(priorV3, v3receiver.GetView()) && priorV3.message.StartsWith("Invalid save"),
            "forged version 3 geometry rejected before migration");
        var v2 = new Game(content, 71);
        var v2state = v2.GetView(); v2state.world = World.BuildVersion2(71);
        var v2safe = v2state.world.objects.First(o => o.kind == "safe");
        v2state.x = v2safe.x - 1; v2state.y = v2safe.y;
        v2state.questStage = 2; v2state.cleared.Add("false-guild"); v2state.gold = 99;
        var v2progress = Progress(v2state);
        // Historical generation-2 saves predate these room presentation fields.
        var historicalV2 = JsonNode.Parse(v2.GetSave());
        foreach (var room in historicalV2["state"]["world"]["rooms"].AsArray())
        {
            room.AsObject().Remove("composition");
            room.AsObject().Remove("floorStyle");
        }
        var v2receiver = new Game(content, 1); v2receiver.LoadSave(historicalV2.ToJsonString());
        Check(v2receiver.GetView().world.generationVersion == 4 && v2receiver.GetView().message.Contains("upgraded"), "version 2 checkpoints migrate explicitly");
        Check(Progress(v2receiver.GetView()) == v2progress, "version 2 exact progress retained");
        historicalV2["state"]["world"]["objects"][0]["x"] = 0;
        var priorV2 = v2receiver.GetView();
        var priorV2Progress = Progress(priorV2);
        var priorV2Geometry = Codec.Write(priorV2.world);
        v2receiver.LoadSave(historicalV2.ToJsonString());
        Check(ReferenceEquals(priorV2, v2receiver.GetView()) && Progress(priorV2) == priorV2Progress &&
            Codec.Write(priorV2.world) == priorV2Geometry && priorV2.message.StartsWith("Invalid save"),
            "forged historical version 2 geometry rejected transactionally");
        Console.WriteLine("PASS: legacy checkpoint migration preserves progress; current roundtrip; forged checkpoints rejected.");
    }
}
