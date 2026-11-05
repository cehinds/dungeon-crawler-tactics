namespace DccRebuild;
public sealed class Game
{
    readonly Content content; View s; string checkpoint;
    public Game(string json, int seed = 1)
    {
        content = Codec.Read<Content>(json) ?? new();
        s = new()
        {
            seed = seed,
            world = World.Build(seed)
        };
        s.x = s.world.spawnX;
        s.y = s.world.spawnY;
        s.party = [new() { id = "carl", name = "Carl", hp = 100, maxHp = 100, mp = 12, maxMp = 12, power = 14, armor = 3, skills = ["punch", "powerful-strike", "bomb"] }, new() { id = "donut", name = "Princess Donut", hp = 65, maxHp = 65, mp = 45, maxMp = 45, power = 10, armor = 2, skills = ["magic-missile", "claw"] }];
        foreach (var p in s.party)
            foreach (var k in p.skills)
                p.ranks[k] = 1;
        foreach (var i in content.items.Where(i => i.kind == "consumable").Take(2))
            s.inventory.Add(new()
            {
                itemId = i.id,
                count = 3
            });
        s.message = "Survive the false Tutorial Guild. Move with the arrow keys and interact nearby.";
        checkpoint = Codec.Write(s);
    }
    public View GetView() => s;
    Unit Actor(string id) => s.party.FirstOrDefault(u => u.id == (id == "" ? s.selectedId : id));
    int Distance(int x, int y, int xx, int yy) => Math.Abs(x - xx) + Math.Abs(y - yy);
    bool Near(WorldObject o) => Distance(s.x, s.y, o.x, o.y) <= 1;
    public View Handle(Command c)
    {
        var pending = s.forecast;
        if (c.type == "confirm" && pending != null)
        {
            if (c.actorId == "")
                c.actorId = pending.actorId;
            if (c.targetId == "")
                c.targetId = pending.targetId;
            if (c.skillId == "")
                c.skillId = pending.skillId;
        }
        s.forecast = null;
        try
        {
            switch (c.type)
            {
                case "move":
                    Move(c);
                    break;
                case "interact":
                    Interact(c);
                    break;
                case "select":
                    if (Actor(c.actorId)?.hp > 0)
                        s.selectedId = c.actorId;
                    break;
                case "moveUnit":
                    MoveUnit(c);
                    break;
                case "forecast":
                    s.forecast = Predict(c);
                    s.message = s.forecast.valid ? "Confirm this attack or choose another target." : "That target is out of range or the action is unavailable.";
                    break;
                case "confirm":
                    Attack(c);
                    break;
                case "endUnit":
                    if (s.mode == "battle" && s.battle != null)
                    {
                        var u = Actor(c.actorId);
                        if (u != null && u.hp > 0 && !u.ended)
                            u.ended = true;
                        else
                            break;
                        if (s.party.All(u => u.ended || u.hp <= 0))
                            EnemyTurn();
                    }
                    break;
                case "endTurn":
                    if (s.mode == "battle" && s.battle != null)
                        EnemyTurn();
                    break;
                case "rest":
                    Rest();
                    break;
                case "equip":
                    Equip(c);
                    break;
                case "useItem":
                    Use(c);
                    break;
                case "retry":
                    if (s.mode == "defeat")
                    {
                        s = Codec.Read<View>(checkpoint);
                        s.message = "Returned to your last safe checkpoint.";
                    }
                    break;
                default:
                    s.message = "Choose a valid command.";
                    break;
            }
        }
        catch (InvalidOperationException e) { s.message = e.Message; }
        return s;
    }
    void Require(bool condition, string message)
    {
        if (!condition)
            throw new InvalidOperationException(message);
    }
    void Move(Command c)
    {
        Require(s.mode == "explore", "Finish the battle first.");
        int dx = c.direction == "east" || c.direction == "right" ? 1 : c.direction == "west" || c.direction == "left" ? -1 : 0, dy = c.direction == "south" || c.direction == "down" ? 1 : c.direction == "north" || c.direction == "up" ? -1 : 0;
        int x = s.x + dx, y = s.y + dy;
        Require(dx != 0 || dy != 0, "Use a cardinal direction.");
        Require(x >= 0 && y >= 0 && x < s.world.width && y < s.world.height && s.world.tiles[y * s.world.width + x] == ".", "A wall blocks the way.");
        s.x = x;
        s.y = y;
        s.message = "Explore Floor 1. Approach a marker to interact.";
    }
    void Interact(Command c)
    {
        Require(s.mode == "explore", "Finish the battle first.");
        var o = string.IsNullOrEmpty(c.targetId) ? s.world.objects.Where(Near).OrderBy(o => o.kind == "door" ? 1 : 0).ThenBy(o => Distance(s.x, s.y, o.x, o.y)).ThenBy(o => o.id).FirstOrDefault() : s.world.objects.FirstOrDefault(o => o.id == c.targetId);
        Require(o != null && Near(o), "Move next to that location first.");
        if (o.kind == "guide")
        {
            Require(s.cleared.Contains("false-guild"), "Survive the false Tutorial Guild before seeking Mordecai.");
            s.questStage = Math.Max(2, s.questStage);
            s.message = "Mordecai: That false guild was a trap. Find supplies and learn to fight together. The goblin workshop stands between you and the Ball of Swine. Hoarder and Juicer are optional challenges. Classes unlock on Floor 3.";
            Log("Met Mordecai: a guide, not a party member.");
        }
        else if (o.kind == "safe")
            Rest();
        else if (o.kind == "exit")
        {
            Require(s.questStage >= 4, "The stairwell is sealed. Defeat the floor guardian first.");
            s.mode = "complete";
            s.message = "Floor 1 cleared. Carl and Donut descend together.";
            Log(s.message);
        }
        else if (o.kind == "chest")
        {
            Require(!s.cleared.Contains(o.id), "This cache is empty.");
            s.cleared.Add(o.id);
            s.gold += 20;
            var loot = content.items.Where(i => i.kind != "consumable").ToArray();
            if (loot.Length > 0)
            {
                int index = (int)((uint)(s.seed + s.cleared.Count * 17) % loot.Length);
                Add(loot[index].id, 1);
            }
            s.message = "Supply cache opened. Equipment added to inventory.";
        }
        else if (o.kind == "door" || o.kind == "discovery")
        {
            s.message = o.description;
            Log(o.name + ": " + o.description);
        }
        else
        {
            Require(!s.cleared.Contains(o.id), "This encounter is already cleared.");
            int required = o.id == "false-guild" ? 0 : o.id == "goblin-workshop" ? 2 : o.kind == "boss" ? 3 : 2;
            Require(s.questStage >= required, "Follow Mordecai's objectives before taking this encounter.");
            Start(o);
        }
    }
    void Log(string m)
    {
        if (!s.journal.Contains(m))
            s.journal.Add(m);
    }
    void Start(WorldObject o)
    {
        s.mode = "battle";
        s.turn = 1;
        s.battle = new()
        {
            encounterId = o.id,
            units = s.party
        };
        for (int i = 0; i < s.party.Count; i++)
        {
            var u = s.party[i];
            u.x = 1;
            u.y = 2 + i * 3;
            u.moved = u.acted = u.ended = false;
        }
        var ids = content.encounters.FirstOrDefault(e => e.id == o.id)?.enemyIds;
        if (ids == null || ids.Length == 0)
            ids = o.id switch
            {
                "false-guild" => ["enemy.goblin", "enemy.murder-dozer"],
                "hoarder" => ["enemy.hoarder-elite", "enemy.scatterer"],
                "juicer" => ["enemy.juicer"],
                "ball-of-swine" => ["enemy.ball-of-swine"],
                _ => ["enemy.goblin", "enemy.goblin-bomber"]
            };
        for (int i = 0; i < ids.Length; i++)
        {
            var e = content.enemies.FirstOrDefault(e => e.id == ids[i]) ?? content.enemies.FirstOrDefault() ?? new()
            {
                name = "Dungeon rat"
            };
            s.battle.enemies.Add(new()
            {
                id = "enemy-" + i,
                templateId = e.id,
                name = e.name,
                x = 7 + i % 2,
                y = 1 + i * 2,
                hp = e.hp,
                maxHp = e.hp,
                power = e.power,
                armor = e.armor,
                element = e.element
            });
        }
        s.message = "Party phase. Each crawler may move and act in either order.";
    }
    bool Free(int x, int y, Unit self) => x >= 0 && y >= 0 && x < 10 && y < 8 && !s.battle.obstacles.Any(o => o.x == x && o.y == y) && !s.party.Concat(s.battle.enemies).Any(u => u != self && u.hp > 0 && u.x == x && u.y == y);
    bool Reach(Unit u, int x, int y, int range)
    {
        var q = new Queue<(int x, int y, int n)>();
        var seen = new HashSet<(int, int)>();
        q.Enqueue((u.x, u.y, 0));
        while (q.Count > 0)
        {
            var p = q.Dequeue();
            if (!seen.Add((p.x, p.y)))
                continue;
            if (p.x == x && p.y == y)
                return true;
            if (p.n >= range)
                continue;
            foreach (var d in new[] { (1, 0), (-1, 0), (0, 1), (0, -1) })
                if (Free(p.x + d.Item1, p.y + d.Item2, u))
                    q.Enqueue((p.x + d.Item1, p.y + d.Item2, p.n + 1));
        }
        return false;
    }
    void MoveUnit(Command c)
    {
        Require(s.mode == "battle", "No active battle.");
        var u = Actor(c.actorId);
        Require(u != null && u.hp > 0 && !u.ended && !u.moved, "This crawler cannot move.");
        Require(Free(c.x, c.y, u) && Reach(u, c.x, c.y, 3), "Choose a reachable empty tile within three steps.");
        u.x = c.x;
        u.y = c.y;
        u.moved = true;
        s.message = u.name + " moved.";
    }
    Skill Skill(string id) => content.skills.FirstOrDefault(k => k.id == id) ?? new() { id = id, name = id, power = id == "punch" ? 4 : 8, range = id == "punch" ? 1 : 6, cost = id == "punch" ? 0 : 3, element = id == "fire-bolt" ? "fire" : id == "punch" ? "physical" : "arcane" };
    Forecast Predict(Command c)
    {
        var u = Actor(c.actorId);
        var t = s.battle?.enemies.FirstOrDefault(e => e.id == c.targetId);
        var k = Skill(c.skillId == "" ? (u?.skills.FirstOrDefault() ?? "punch") : c.skillId);
        bool valid = s.mode == "battle" && u != null && u.hp > 0 && !u.acted && !u.ended && t != null && t.hp > 0 && u.skills.Contains(k.id) && u.mp >= k.cost && Distance(u.x, u.y, t.x, t.y) <= k.range;
        int reactionBonus = k.element == "arcane" && t?.element == "physical" ? 2 : k.element == "fire" && t?.element == "physical" ? 3 : 0;
        string reaction = reactionBonus == 2 ? "Arcane impact: +2 damage (tactical adaptation)." : reactionBonus == 3 ? "Blast shock: +3 damage (tactical adaptation)." : "";
        return new()
        {
            actorId = u?.id ?? "",
            targetId = t?.id ?? "",
            skillId = k.id,
            cost = k.cost,
            valid = valid,
            reaction = reaction,
            damage = valid ? Math.Max(1, u.power + k.power + u.ranks.GetValueOrDefault(k.id, 1) - t.armor + reactionBonus) : 0
        };
    }
    void Attack(Command c)
    {
        var f = Predict(c);
        Require(f.valid, "Choose a valid skill and target first.");
        var u = Actor(f.actorId);
        var t = s.battle.enemies.First(e => e.id == f.targetId);
        u.mp -= f.cost;
        u.acted = true;
        t.hp = Math.Max(0, t.hp - f.damage);
        u.ranks[f.skillId] = Math.Min(20, u.ranks.GetValueOrDefault(f.skillId, 1) + 1);
        s.message = $"{u.name} deals {f.damage} damage. {f.reaction}";
        if (s.battle.enemies.All(e => e.hp <= 0))
            Win();
    }
    List<(int x, int y)> EnemyPath(Unit enemy, Unit target)
    {
        var start = (enemy.x, enemy.y);
        var queue = new Queue<(int x, int y)>();
        var previous = new Dictionary<(int x, int y), (int x, int y)> { [start] = start };
        queue.Enqueue(start);
        while (queue.Count > 0)
        {
            var tile = queue.Dequeue();
            if (Distance(tile.x, tile.y, target.x, target.y) <= 1)
            {
                var path = new List<(int x, int y)>();
                while (tile != start)
                {
                    path.Add(tile);
                    tile = previous[tile];
                }
                path.Reverse();
                return path;
            }
            foreach (var delta in new[] { (1, 0), (-1, 0), (0, 1), (0, -1) })
            {
                var next = (tile.x + delta.Item1, tile.y + delta.Item2);
                if (!previous.ContainsKey(next) && Free(next.Item1, next.Item2, enemy))
                {
                    previous[next] = tile;
                    queue.Enqueue(next);
                }
            }
        }
        return [];
    }
    void EnemyTurn()
    {
        foreach (var e in s.battle.enemies.Where(e => e.hp > 0))
        {
            var target = s.party.Where(u => u.hp > 0).OrderBy(u => Distance(e.x, e.y, u.x, u.y)).ThenBy(u => u.id).FirstOrDefault();
            if (target == null)
                break;
            // Search once per enemy, preserving deterministic cardinal neighbor order.
            // The goal is any free square adjacent to the target, never its occupied tile.
            var path = EnemyPath(e, target);
            foreach (var step in path.Take(3))
            {
                e.x = step.x;
                e.y = step.y;
            }
            if (Distance(e.x, e.y, target.x, target.y) <= 1)
                target.hp = Math.Max(0, target.hp - Math.Max(1, e.power - target.armor));
        }
        if (s.party.All(u => u.hp <= 0))
        {
            s.mode = "defeat";
            s.message = "The run ends here. Retry from the safe checkpoint.";
            return;
        }
        foreach (var u in s.party)
            u.moved = u.acted = u.ended = false;
        s.turn++;
        s.message = "Party phase. The enemies have advanced.";
    }
    void Win()
    {
        string id = s.battle.encounterId;
        s.cleared.Add(id);
        s.questStage = Math.Max(s.questStage, id == "false-guild" ? 1 : id == "goblin-workshop" ? 3 : id == "ball-of-swine" ? 4 : s.questStage);
        s.gold += 25;
        foreach (var u in s.party)
        {
            u.xp += 30;
            if (u.xp >= u.level * 30 && u.level < 20)
            {
                u.level++;
                u.maxHp += 8;
                u.hp = Math.Min(u.maxHp, u.hp + 20);
                u.power += 2;
            }
        }
        s.mode = "explore";
        s.battle = null;
        s.message = id == "ball-of-swine" ? "Guardian defeated. Reach the stairwell to finish Floor 1." : "Victory. Rewards received; return to Mordecai or continue the objective.";
        Log("Cleared " + id + ".");
    }
    void Rest()
    {
        Require(s.mode == "explore" && s.world.objects.Any(o => o.kind == "safe" && Near(o)), "Rest at the safe room.");
        foreach (var u in s.party)
        {
            u.hp = u.maxHp;
            u.mp = u.maxMp;
        }
        s.message = "Safe room: party restored and checkpoint saved.";
        checkpoint = Codec.Write(s);
    }
    void Add(string id, int count)
    {
        var stack = s.inventory.FirstOrDefault(i => i.itemId == id);
        if (stack == null)
            s.inventory.Add(new()
            {
                itemId = id,
                count = count
            });
        else
            stack.count += count;
    }
    void Equip(Command c)
    {
        Require(s.mode == "explore", "Equip between battles.");
        var u = Actor(c.actorId);
        var i = content.items.FirstOrDefault(i => i.id == c.itemId);
        Require(u != null && i != null && (i.kind == "weapon" || i.kind == "armor" || i.kind == "charm") && s.inventory.Any(v => v.itemId == i.id && v.count > 0), "Choose owned equipment.");
        Require(!s.party.Any(p => p != u && p.equipment == i.id), "That item is already equipped by the other crawler.");
        Require(u.id != "carl" || i.kind != "weapon", "Carl fights with his bare hands and feet.");
        if (u.equipment != "")
        {
            var old = content.items.FirstOrDefault(v => v.id == u.equipment);
            if (old != null)
            {
                u.power -= old.power;
                u.armor -= old.armor;
            }
        }
        u.equipment = i.id;
        u.power += i.power;
        u.armor += i.armor;
        s.message = u.name + " equipped " + i.name + ".";
    }
    void Use(Command c)
    {
        var u = Actor(c.actorId);
        var i = content.items.FirstOrDefault(i => i.id == c.itemId);
        var st = s.inventory.FirstOrDefault(v => v.itemId == c.itemId);
        Require(u != null && i != null && i.kind == "consumable" && st != null && st.count > 0, "Choose an owned consumable.");
        Require(s.mode == "explore" || (s.mode == "battle" && !u.acted && !u.ended && u.hp > 0), "This crawler cannot use an item now.");
        st.count--;
        u.hp = Math.Min(u.maxHp, u.hp + i.heal);
        u.mp = Math.Min(u.maxMp, u.mp + i.mp);
        if (s.mode == "battle")
            u.acted = true;
        s.message = i.name + " used.";
    }
    public string GetSave()
    {
        Require(s.mode == "explore" && s.world.objects.Any(o => o.kind == "safe" && Near(o)), "Save at a safe room.");
        return Codec.Write(new Save { state = s });
    }
    bool ValidSave(View v)
    {
        if (v == null || v.mode != "explore" || v.party == null || v.party.Count != 2 || v.party.Any(u => u == null) || v.party[0].id != "carl" || v.party[1].id != "donut" || v.inventory == null || v.cleared == null || v.journal == null || v.journal.Any(x => x == null) || v.questStage < 0 || v.questStage > 4 || v.gold < 0 || v.gold > 100000 || v.turn < 1 || !v.party.Any(u => u.id == v.selectedId))
            return false;
        if (v.inventory.Any(i => i == null || i.count < 0 || i.count > 999 || !content.items.Any(it => it.id == i.itemId)) || v.inventory.Select(i => i.itemId).Distinct().Count() != v.inventory.Count)
            return false;
        foreach (var u in v.party)
        {
            string[] expected = u.id == "carl" ? ["punch", "powerful-strike", "bomb"] : ["magic-missile", "claw"];
            if (u.name == null || u.equipment == null || u.skills == null || !u.skills.SequenceEqual(expected) || u.ranks == null || u.ranks.Count != expected.Length || expected.Any(k => !u.ranks.TryGetValue(k, out var rank) || rank < 1 || rank > 20) || u.level < 1 || u.level > 20 || u.xp < 0 || u.xp > 100000 || u.maxHp <= 0 || u.maxHp > 1000 || u.maxMp < 0 || u.maxMp > 1000 || u.hp < 0 || u.hp > u.maxHp || u.mp < 0 || u.mp > u.maxMp || u.power < 0 || u.power > 1000 || u.armor < 0 || u.armor > 1000)
                return false;
            if (u.equipment != "" && !content.items.Any(i => i.id == u.equipment && (i.kind == "armor" || i.kind == "charm" || (i.kind == "weapon" && u.id != "carl")) && v.inventory.Any(st => st.itemId == i.id && st.count > 0)))
                return false;
        }
        if (v.party.Where(u => u.equipment != "").Select(u => u.equipment).Distinct().Count() != v.party.Count(u => u.equipment != ""))
            return false;
        v.world = World.Build(v.seed);
        if (v.x < 0 || v.y < 0 || v.x >= v.world.width || v.y >= v.world.height || v.world.tiles[v.y * v.world.width + v.x] != "." || !v.world.objects.Any(o => o.kind == "safe" && Distance(v.x, v.y, o.x, o.y) <= 1))
            return false;
        if (v.cleared.Distinct().Count() != v.cleared.Count || v.cleared.Any(id => !v.world.objects.Any(o => o.id == id && (o.kind == "encounter" || o.kind == "boss" || o.kind == "chest"))))
            return false;
        bool first = v.cleared.Contains("false-guild"), workshop = v.cleared.Contains("goblin-workshop"), boss = v.cleared.Contains("ball-of-swine");
        if (first != (v.questStage >= 1) || workshop != (v.questStage >= 3) || boss != (v.questStage == 4) || v.cleared.Any(id => id is "hoarder" or "juicer") && v.questStage < 2)
            return false;
        return true;
    }
    public View LoadSave(string json)
    {
        try
        {
            var save = Codec.Read<Save>(json);
            if (save?.version != 1 || !ValidSave(save.state))
                throw new InvalidOperationException();
            var candidate = save.state;
            candidate.battle = null;
            candidate.forecast = null;
            foreach (var u in candidate.party)
            {
                u.x = 0;
                u.y = 0;
                u.moved = u.acted = u.ended = false;
            }
            candidate.message = "Safe-room save loaded.";
            var nextCheckpoint = Codec.Write(candidate);
            s = candidate;
            checkpoint = nextCheckpoint;
        }
        catch { s.message = "Invalid save. Your current run is unchanged."; }
        return s;
    }
}
