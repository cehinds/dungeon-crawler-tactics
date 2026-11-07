using DccRebuild;
if (args.Length > 0 && args[0] == "--validate-content")
{
    Environment.ExitCode = CatalogChecks.ValidateFile(args.Length > 1 ? args[1] : Path.Combine(AppContext.BaseDirectory, "floor-one-rpg.json"));
    return;
}
void Assert(bool ok, string label) { if (!ok) throw new Exception(label); }
var json = File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "floor-one-rpg.json"));
EffectChecks.Run();
var g = new Game(json, 71);
var v = g.GetView();
void Walk(string id) { var o = v.world.objects.First(o => o.id == id); var q = new Queue<(int x, int y)>(); var prev = new Dictionary<(int, int), (int, int)>(); var start = (v.x, v.y); q.Enqueue(start); prev[start] = start; var goal = start; while (q.Count > 0) { var p = q.Dequeue(); if (Math.Abs(p.x - o.x) + Math.Abs(p.y - o.y) <= 1) { goal = p; break; } foreach (var d in new[] { (1, 0), (-1, 0), (0, 1), (0, -1) }) { var n = (p.x + d.Item1, p.y + d.Item2); if (n.Item1 >= 0 && n.Item2 >= 0 && n.Item1 < v.world.width && n.Item2 < v.world.height && v.world.tiles[n.Item2 * v.world.width + n.Item1] == "." && !prev.ContainsKey(n)) { prev[n] = p; q.Enqueue(n); } } } var path = new List<(int, int)>(); while (goal != start) { path.Add(goal); goal = prev[goal]; } path.Reverse(); foreach (var p in path) g.Handle(new() { type = "move", direction = p.Item1 > v.x ? "east" : p.Item1 < v.x ? "west" : p.Item2 > v.y ? "south" : "north" }); }
void Interact(string id) { Walk(id); g.Handle(new() { type = "interact", targetId = id }); }
void Fight()
{
    for (int round = 0; round < 80 && v.mode == "battle"; round++)
    {
        foreach (var u in v.party.Where(u => u.hp > 0))
        {
            var enemy = v.battle.enemies.FirstOrDefault(e => e.hp > 0);
            if (enemy == null)
                break;
            Forecast Best() => u.skills.Select(skill => g.Handle(new() { type = "forecast", actorId = u.id, targetId = enemy.id, skillId = skill }).forecast).Where(f => f.valid).OrderByDescending(f => f.damage).FirstOrDefault();
            var f = Best();
            if (f == null)
            {
                foreach (var p in Enumerable.Range(0, v.battle.width * v.battle.height).Select(i => (x: i % v.battle.width, y: i / v.battle.width)).OrderBy(p => Math.Abs(p.x - enemy.x) + Math.Abs(p.y - enemy.y)))
                {
                    g.Handle(new()
                    {
                        type = "moveUnit",
                        actorId = u.id,
                        x = p.x,
                        y = p.y
                    });
                    if (u.moved)
                        break;
                }
                f = Best();
            }
            if (f != null)
            {
                int hp = enemy.hp;
                g.Handle(new()
                {
                    type = "confirm",
                    actorId = u.id,
                    targetId = enemy.id,
                    skillId = f.skillId
                });
                Assert(enemy.hp == Math.Max(0, hp - f.damage), "forecast matches commit");
            }
            if (v.mode != "battle")
                break;
        }
        if (v.mode == "battle")
            g.Handle(new()
            {
                type = "endTurn"
            });
    }
    Assert(v.mode == "explore", "battle victory");
}
Assert(v.party.Count == 2 && v.party.All(u => u.level == 1), "party");
g.Handle(new() { type = "interact", targetId = "mordecai" });
Assert(v.questStage == 0, "proximity gated");
Interact("false-guild");
Assert(v.mode == "battle", "first encounter");
Fight();
Assert(v.party.All(u => u.level == 2), "first encounter preserves level-two milestone");
Interact("mordecai");
Assert(v.questStage == 2, "guide progression");
Interact("safe-room");
var save = g.GetSave();
var before = Codec.Write(v.party);
g.LoadSave("{}");
Assert(Codec.Write(v.party) == before, "invalid save unchanged");
g.LoadSave(save);
v = g.GetView();
Assert(v.questStage == 2, "save roundtrip");
Interact("goblin-workshop");
Fight();
Interact("safe-room");
Interact("hoarder");
Fight();
Interact("safe-room");
Interact("juicer");
Fight();
Interact("safe-room");
Interact("ball-of-swine");
Fight();
Interact("exit");
Assert(v.mode == "complete", "floor complete");
Assert(v.party.All(u => u.level == 6), "all five Floor One encounters preserve level-six milestone");
for (int seed = 0; seed < 50; seed++) World.Validate(World.Build(seed));
Console.WriteLine("PASS: full Floor 1 route, combat forecast/commit, save validation, 50 connected worlds.");
// Malformed nested save fields must never replace the current session.
var validator = new Game(json, 71);
validator.LoadSave(save);
foreach (var field in new[] { "skills", "ranks", "equipment" })
{
    var broken = System.Text.Json.Nodes.JsonNode.Parse(save);
    broken["state"]["party"][0][field] = null;
    var beforeState = Codec.Write(validator.GetView().party);
    validator.LoadSave(broken.ToJsonString());
    Assert(validator.GetView().message.StartsWith("Invalid save"), "reject null unit " + field);
    Assert(Codec.Write(validator.GetView().party) == beforeState, "transactional unit " + field);
}
foreach (var field in new[] { "inventory", "journal", "cleared" })
{
    var broken = System.Text.Json.Nodes.JsonNode.Parse(save);
    broken["state"][field] = null;
    validator.LoadSave(broken.ToJsonString());
    Assert(validator.GetView().message.StartsWith("Invalid save"), "reject null " + field);
}
var inconsistent = System.Text.Json.Nodes.JsonNode.Parse(save);
inconsistent["state"]["questStage"] = 4;
validator.LoadSave(inconsistent.ToJsonString());
Assert(validator.GetView().message.StartsWith("Invalid save"), "reject inconsistent boss receipt");
var ai = new Game(json, 2);
var av = ai.GetView();
var entry = av.world.objects.First(o => o.id == "false-guild");
av.x = entry.x;
av.y = entry.y;
ai.Handle(new() { type = "interact" });
Assert(av.mode == "battle", "bare nearby interact");
Assert(av.battle.enemies.Any(e=>e.templateId=="enemy.murder-dozer"),"authored enemy template retained for art");
av.party[0].x = 3;
av.party[0].y = 2;
av.party[0].armor = 0;
av.party[1].hp = 0;
var foe = av.battle.enemies[0];
foe.x = 5;
foe.y = 2;
foreach (var other in av.battle.enemies.Skip(1)) other.hp = 0;
int initialHp = av.party[0].hp;
for (int turn = 0; turn < 4; turn++) ai.Handle(new() { type = "endTurn" });
Assert(av.party[0].hp < initialHp, "enemy BFS routes around obstacle");
av.party[0].hp = 0;
ai.Handle(new() { type = "endTurn" });
Assert(av.mode == "defeat", "defeat reached");
var defeated = Codec.Write(av);
ai.Handle(new() { type = "endTurn" });
ai.Handle(new() { type = "endUnit", actorId = "carl" });
Assert(Codec.Write(av) == defeated, "defeat commands cannot advance battle");
Console.WriteLine("PASS: null/inconsistent saves rejected transactionally; bare interact; obstacle BFS; defeat immutable.");

// Whole-object concept furniture is authoritative collision, with seed-specific room geometry.
var layouts = new HashSet<string>();
var footprints = new HashSet<string>();
for (int seed = -25; seed < 75; seed++)
{
    var world = World.Build(seed);
    World.Validate(world);
    Assert(Codec.Write(world) == Codec.Write(World.Build(seed)), "same seed reproduces concept assembly");
    Assert(world.generationVersion == 4 && world.props.Length >= 12, "concept generation and furniture populated");
    Assert(world.rooms.Length == 12 && world.rooms.Select(r => r.objectId).Distinct().Count() == 12, "lore anchors retained");
    Assert(world.rooms.All(r => r.archetype.Length > 0), "authored room archetypes");
    var classroom = world.props.Where(p => p.roomId == "tutorial-guildhall" && p.groupId == "teaching-table").ToArray();
    Assert(classroom.Length >= 5 && classroom.Count(p => p.assetId == "ef-chair-green") >= 3, "complete teaching assembly exists for every seed");
    var table = classroom.Single(p => p.assetId == "ef-wood-table");
    var rug = classroom.Single(p => p.assetId == "ef-rug-red");
    var chairs = classroom.Where(p => p.assetId == "ef-chair-green").ToArray();
    Assert(chairs.Any(p => p.x == table.x - 1 && p.y == table.y) && chairs.Any(p => p.x == table.x + table.width && p.y == table.y)
        && chairs.Any(p => p.x == table.x + 1 && p.y == table.y + table.height), "chairs stay beside authored table edges");
    Assert(!rug.blocksMovement && rug.layer == "underlay" && rug.x == table.x && rug.y == table.y, "rug authored beneath teaching table");
    foreach (var prop in world.props.Where(p => p.groupId.Length > 0))
        Assert(prop.x == prop.groupX + prop.offsetX && prop.y == prop.groupY + prop.offsetY, "authored relative furniture offsets remain exact");
    foreach (var safeId in new[] { "sebastian-safe-room" })
    {
        var living = world.props.Where(p => p.roomId == safeId && p.groupId == "rest-bedroom").ToArray();
        var wash = world.props.Where(p => p.roomId == safeId && p.groupId == "washroom-fixtures").ToArray();
        Assert(living.Length == 3 && wash.Length == 2, "complete opposing safe-room assemblies");
        Assert(living.Max(p => p.x + p.width) <= wash.Min(p => p.x), "bedroom lies left of washroom with clear circulation");
        Assert(living.All(p => p.anchor == "northwest" && p.zone == "living") && wash.All(p => p.anchor == "northeast" && p.zone == "washroom"), "authored safe-room zones");
    }
    var dining = world.props.Where(p => p.roomId == "tally-safe-room").ToArray();
    Assert(dining.Any(p => p.groupId == "dining-cluster" && p.assetId == "ef-wood-table") && dining.Count(p => p.assetId == "ef-chair-green") == 2, "restaurant keeps dining furniture");
    Assert(!dining.Any(p => p.assetId.Contains("bed") || p.assetId.Contains("toilet")), "restaurant identity excludes bedroom fixtures");
    var waiting = world.props.Where(p => p.roomId == "dmv-safe-room" && p.groupId == "waiting-area").ToArray();
    Assert(waiting.Length == 2 && waiting.Any(p => p.assetId == "ef-vending-green") && waiting.Any(p => p.assetId == "ef-wood-bench"), "DMV keeps waiting bench and vending machine");
    var approach = world.props.Where(p => p.roomId == "entry-landing" && p.groupId == "stair-approach").ToArray();
    Assert(approach.Length == 3 && approach.Count(p => p.assetId == "cd-torch") == 2, "stair approach preserves paired torches");
    var stair = approach.Single(p => p.assetId == "cd-stair-module");
    Assert(approach.Where(p => p.assetId == "cd-torch").All(p => p.x == stair.x + stair.width)
        && approach.Where(p => p.assetId == "cd-torch").Select(p => p.y - stair.y).Order().SequenceEqual(new[] { 0, 2 }), "paired torches frame same stair approach");
    layouts.Add(string.Join("|", world.rooms.Select(r => $"{r.x},{r.y},{r.width},{r.height}")));
    foreach (var r in world.rooms) footprints.Add($"{r.width}x{r.height}");
    foreach (var prop in world.props.Where(p => p.blocksMovement))
    {
        Assert(!world.objects.Any(o => o.x >= prop.x && o.x < prop.x + prop.width && o.y >= prop.y && o.y < prop.y + prop.height), "furniture reserves every interaction");
        Assert(!(world.spawnX >= prop.x && world.spawnX < prop.x + prop.width && world.spawnY >= prop.y && world.spawnY < prop.y + prop.height), "furniture reserves player spawn");
    }
}
Assert(layouts.Count > 90 && footprints.Count >= 6, "seed varies actual room positions and footprints");
World.Validate(World.Build(int.MinValue)); World.Validate(World.Build(int.MaxValue));
Console.WriteLine("PASS: 102 concept worlds; repeatable geometry, footprint collision, reachable interactions, distinct room layouts.");
SaveMigrationChecks.Run(json);

// Recognizable industrial composition and authoritative combat collision share one grammar.
for (int seed = 0; seed < 30; seed++)
{
    var map = World.Build(seed);
    foreach (var id in new[] { "goblin-workshop", "ball-of-swine" })
    {
        var room = map.rooms.Single(r => r.objectId == id);
        var arena = World.BuildArena(seed, id);
        Assert(room.composition == "industrial-sewer" && arena.width == room.width, "industrial identity shared in combat");
        Assert(Codec.Write(arena) == Codec.Write(World.BuildArena(seed, id)), "arena deterministic");
        Assert(arena.tiles.Count(t => t == "~") >= 2, "industrial side gutters present");
        Assert(arena.width == 18 && arena.height == 11, "source-sized industrial arena");
        for (int y = 0; y < 2; y++) for (int x = 0; x < 15; x++)
            Assert(arena.tiles[y * arena.width + x] == (x is >= 11 and <= 13 ? "." : "#"),
                "north machinery bank is masonry with only the gold gate passage open");
        foreach (var fixture in arena.props.Where(p => p.layer == "wallfixture"))
            for (int y = fixture.y; y < fixture.y + fixture.height; y++) for (int x = fixture.x; x < fixture.x + fixture.width; x++)
                Assert(arena.tiles[y * arena.width + x] == "#", "wall fixtures retain actual blocked masonry");
        foreach (int x in new[] { 0, 1, 2, 15, 16, 17 })
        {
            Assert(arena.tiles[5 * arena.width + x] == ".", "wide water crossing is real traversable floor");
            Assert(arena.tiles[4 * arena.width + x] == "~" && arena.tiles[6 * arena.width + x] == "~", "water continuous beneath crossing");
        }
        Assert(arena.tiles[9 * arena.width + 16] == "~" && arena.tiles[9 * arena.width + 1] == "#", "asymmetric lower east basin");
        for (int x = 0; x < arena.width; x++)
            Assert(arena.tiles[(arena.height - 1) * arena.width + x] == (x is 9 or 10 ? "." : "#"), "southern platform has tapered entrance");
        Assert(!arena.props.Any(p => p.assetId == "industrial-crate"), "source platform avoids oversized corner crates");
        for (int y = 2; y < 8; y++) for (int x = 3; x < 15; x++)
            Assert(arena.tiles[y * arena.width + x] == ".", "twelve by six central fighting floor stays clear");
        var encounterGame = new Game(json, seed); var encounterView = encounterGame.GetView();
        var encounterObject = encounterView.world.objects.Single(o => o.id == id);
        encounterView.questStage = id == "goblin-workshop" ? 2 : 3;
        encounterView.x = encounterObject.x - 1; encounterView.y = encounterObject.y;
        encounterGame.Handle(new() { type = "interact", targetId = id });
        Assert(encounterView.mode == "battle", "industrial encounter starts");
        var combatants = encounterView.party.Concat(encounterView.battle.enemies).ToArray();
        Assert(combatants.Select(u => (u.x, u.y)).Distinct().Count() == combatants.Length &&
            combatants.All(u => u.x >= 0 && u.x < arena.width && u.y >= 0 && u.y < arena.height && arena.tiles[u.y * arena.width + u.x] == "."),
            "all industrial party and enemy spawns are distinct reachable floor");
        var reached = new HashSet<(int x, int y)>(); var frontier = new Queue<(int x, int y)>();
        frontier.Enqueue((combatants[0].x, combatants[0].y));
        while (frontier.TryDequeue(out var cell))
        {
            if (!reached.Add(cell)) continue;
            foreach (var d in new[] { (1, 0), (-1, 0), (0, 1), (0, -1) })
            {
                var next = (x: cell.x + d.Item1, y: cell.y + d.Item2);
                if (next.x >= 0 && next.x < arena.width && next.y >= 0 && next.y < arena.height && arena.tiles[next.y * arena.width + next.x] == "." && !reached.Contains(next)) frontier.Enqueue(next);
            }
        }
        Assert(reached.Count == arena.tiles.Count(t => t == ".") && combatants.All(u => reached.Contains((u.x, u.y))),
            "battle floor, wide crossings, gate and all combatants share one connected navigation graph");
        foreach (var prop in arena.props.Where(p => p.blocksMovement))
            for (int y = prop.y; y < prop.y + prop.height; y++) for (int x = prop.x; x < prop.x + prop.width; x++)
                Assert(arena.obstacles.Any(o => o.x == x && o.y == y), "combat prop footprints match collision");
        Assert(arena.props.Any(p => p.zone == "machinery" && p.x == 3 && p.y == 0), "northwest machinery focal group");
    }
    var exit = map.objects.Single(o => o.id == "exit");
    var stair = map.props.Single(p => p.assetId == "industrial-exit");
    var bossRoom = map.rooms.Single(r => r.objectId == "ball-of-swine");
    Assert(map.tiles[(bossRoom.y - 1) * map.width + exit.x] == ".", "north port aligns with gate");
    Assert(map.tiles[(bossRoom.y - 1) * map.width + bossRoom.x + bossRoom.width / 2] == "#", "no duplicate north doorway left of gate");
    Assert(exit.x >= stair.x && exit.x < stair.x + stair.width && exit.y >= stair.y && exit.y < stair.y + stair.height, "functional exit occupies visible stair");
    Assert(!map.props.Any(p => p.roomId == "goblin-workshop" && p.assetId == "industrial-exit"), "workshop does not imply a false descending exit");
}
Console.WriteLine("PASS: industrial grammar, open fighting floor, water gutters, shared arena collision and functional stair.");

ProgressionChecks.Run(json);

CatalogChecks.Run(json);


FoundationSaveChecks.Run(json);

EffectChecks.ResourceAndMovement(json);

EffectChecks.GameFlows(json);

EffectChecks.AuthoredDamageBonus(json);

BlockBChecks.Run(json);
