using DccRebuild;
void Assert(bool ok, string label) { if (!ok) throw new Exception(label); }
var json = File.ReadAllText(Path.Combine(AppContext.BaseDirectory, "floor-one-rpg.json"));
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
                foreach (var p in Enumerable.Range(0, 80).Select(i => (x: i % 10, y: i / 10)).OrderBy(p => Math.Abs(p.x - enemy.x) + Math.Abs(p.y - enemy.y)))
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
    Assert(world.generationVersion == 2 && world.props.Length >= 12, "concept generation and furniture populated");
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
    foreach (var prop in world.props)
    {
        Assert(!world.objects.Any(o => o.x >= prop.x && o.x < prop.x + prop.width && o.y >= prop.y && o.y < prop.y + prop.height), "furniture reserves every interaction");
        Assert(!(world.spawnX >= prop.x && world.spawnX < prop.x + prop.width && world.spawnY >= prop.y && world.spawnY < prop.y + prop.height), "furniture reserves player spawn");
    }
}
Assert(layouts.Count > 90 && footprints.Count >= 6, "seed varies actual room positions and footprints");
World.Validate(World.Build(int.MinValue)); World.Validate(World.Build(int.MaxValue));
Console.WriteLine("PASS: 102 concept worlds; repeatable geometry, footprint collision, reachable interactions, distinct room layouts.");
SaveMigrationChecks.Run(json);
