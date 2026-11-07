namespace DccRebuild;
public sealed class Game
{
    readonly Dictionary<int, WorldMap> originalWorlds = new();
    WorldMap OriginalWorld(int seed)
    {
        if (!originalWorlds.TryGetValue(seed, out var world)) originalWorlds[seed] = world = World.Build(seed);
        return world;
    }
    string[] enemyOrder = []; int enemyIndex;
    readonly Content content; readonly ContentCatalog catalog; readonly Progression progression; View s; string checkpoint;
    public Game(string json, int seed = 1)
    {
        content = Codec.Read<Content>(json) ?? new();
        catalog = new(content);
        progression = new(content);
        s = new()
        {
            seed = seed,
            world = World.Build(seed)
        };
        s.x = s.world.spawnX;
        s.y = s.world.spawnY;
        s.party = [new() { id = "carl", name = "Carl", hp = 100, maxHp = 100, mp = 12, maxMp = 12, power = 14, armor = 3, skills = ["punch", "powerful-strike", "bomb"] }, new() { id = "donut", name = "Princess Donut", hp = 65, maxHp = 65, mp = 45, maxMp = 45, power = 10, armor = 2, skills = ["magic-missile", "claw"] }];
        foreach (var p in s.party)
        {
            var definition = catalog.Deployable(1, []).SingleOrDefault(c => (c.runtimeId == "" ? c.id.Replace("crawler.", "") : c.runtimeId) == p.id);
            if (definition != null)
            {
                p.name = definition.name;
                p.templateId = definition.id;
                p.skills = definition.skillIds;
            }
        }
        foreach (var p in s.party)
            foreach (var k in p.skills)
                p.ranks[k] = Skill(k).startingRank;
        foreach (var p in s.party)
        {
            foreach (var k in p.skills)
                p.skillPractice[k] = 0;
            progression.Refresh(p);
        }
        foreach (var i in content.items.Where(i => i.kind == "consumable" && i.availability.Allows(s.floor, s.unlockedEvents)).Take(2))
            s.inventory.Add(new()
            {
                itemId = i.id,
                count = 3
            });
        foreach (var item in content.items.Where(i => i.kind != "consumable" && i.startingCount > 0))
            Add(item.id, item.startingCount);
        s.message = "Survive the false Tutorial Guild. Move with the arrow keys and interact nearby.";
        checkpoint = Codec.Write(s);
    }
    public View GetView()
    {
        foreach (var u in s.party)
            progression.Refresh(u, s.mode == "battle");
        SelectLivingActor(s.mode == "battle");
        s.availability = catalog.Entries.Where(e => e.kind is "storyEvent" or "class" or "character" or "recipe" or "facility").Select(e => new AvailabilityView
        {
            kind = e.kind, id = e.definition.id, name = e.definition.name,
            available = e.definition.availability.Allows(s.floor, s.unlockedEvents),
            unlocked = s.unlockedEvents.Contains(e.definition.id),
            reason = e.definition.availability.Allows(s.floor, s.unlockedEvents) ? "Available" : e.definition.availability.reason != "" ? e.definition.availability.reason : $"Requires Floor {e.definition.availability.minFloor} and story prerequisites"
        }).ToArray();
        RefreshContext();
        return s;
    }
    void RefreshContext()
    {
        s.safeRoom = PreparationService.SafeRoom(s);
        var equipmentIds = s.inventory.Where(st => st.count > 0 && PreparationService.IsEquipment(content.items.FirstOrDefault(i => i.id == st.itemId))).Select(st => st.itemId).Prepend("").ToArray();
        s.equipmentPreviews = s.party.SelectMany(u => equipmentIds.Select(id => PreparationService.PreviewEquipment(content, s, u.id, id))).ToArray();
        var consumableIds = s.inventory.Where(st => content.items.Any(i => i.id == st.itemId && i.kind == "consumable")).Select(st => st.itemId).ToArray();
        s.consumablePreviews = s.party.SelectMany(u => consumableIds.Select(id => PreparationService.PreviewConsumable(content, s, u.id, id))).ToArray();
        s.resupplyOffers = content.resupplyOffers.Select(o => PreparationService.PreviewResupply(content, s, content.resupplyOffers, o.id)).ToArray();
        var objectiveId = s.questStage switch { 0 => "false-guild", 1 => "mordecai", 2 => "goblin-workshop", 3 => "ball-of-swine", _ => "exit" };
        var destination = s.world.objects.FirstOrDefault(o => o.id == objectiveId);
        s.objective = new() { id = objectiveId, name = destination?.name ?? objectiveId,
            description = s.mode == "complete" ? "Floor One complete." : s.questStage switch {
                0 => "Survive the false Tutorial Guild.", 1 => "Find Mordecai's real guildhall.",
                2 => "Clear the goblin workshop. Hoarder and Juicer are optional.", 3 => "Defeat the Ball of Swine.", _ => "Reach the descending stair." } };
        s.nearbyInteractions = s.world.objects.Where(Near).OrderBy(o => o.kind == "door" ? 1 : 0)
            .ThenBy(o => Distance(s.x, s.y, o.x, o.y)).ThenBy(o => o.id, StringComparer.Ordinal)
            .Select(o => {
                string reason = InteractionReason(o);
                return new InteractionView { id = o.id, kind = o.kind, name = o.name, available = reason == "", reason = reason };
            }).ToArray();
        s.nearestSafe = null;
        if (s.mode != "explore") return;
        var distances = new Dictionary<(int x, int y), (int distance, string first)> { [(s.x, s.y)] = (0, "here") };
        var queue = new Queue<(int x, int y)>(); queue.Enqueue((s.x, s.y));
        while (queue.Count > 0)
        {
            var tile = queue.Dequeue(); var route = distances[tile];
            var safe = s.world.objects.Where(o => o.kind == "safe" && Distance(tile.x, tile.y, o.x, o.y) <= 1).OrderBy(o => o.id, StringComparer.Ordinal).FirstOrDefault();
            if (safe != null) { s.nearestSafe = new() { id = safe.id, name = safe.name, distance = route.distance, direction = route.first }; break; }
            foreach (var d in new[] { (dx: 1, dy: 0, name: "east"), (dx: -1, dy: 0, name: "west"), (dx: 0, dy: 1, name: "south"), (dx: 0, dy: -1, name: "north") })
            {
                var next = (x: tile.x + d.dx, y: tile.y + d.dy);
                if (next.x < 0 || next.y < 0 || next.x >= s.world.width || next.y >= s.world.height || s.world.tiles[next.y * s.world.width + next.x] != "." || distances.ContainsKey(next)) continue;
                distances[next] = (route.distance + 1, route.distance == 0 ? d.name : route.first); queue.Enqueue(next);
            }
        }
    }
    string InteractionReason(WorldObject o)
    {
        if (s.mode != "explore") return "Finish the battle first.";
        if (o.kind is "encounter" or "boss" or "chest" && s.cleared.Contains(o.id)) return "Already cleared.";
        if (o.kind == "guide" && !s.cleared.Contains("false-guild")) return "Survive the false Tutorial Guild first.";
        if (o.kind == "exit" && s.questStage < 4) return "Defeat the floor guardian first.";
        if (o.kind is "encounter" or "boss")
        {
            int required = o.id == "false-guild" ? 0 : o.id == "goblin-workshop" ? 2 : o.kind == "boss" ? 3 : 2;
            if (s.questStage < required) return "Follow Mordecai's objectives first.";
            var encounter = catalog.Get<Encounter>("encounter", o.id);
            if (!encounter.availability.Allows(s.floor, s.unlockedEvents)) return "This encounter is not available yet.";
        }
        return "";
    }
    Unit Actor(string id) => s.party.FirstOrDefault(u => u.id == (id == "" ? s.selectedId : id));
    int Distance(int x, int y, int xx, int yy) => Math.Abs(x - xx) + Math.Abs(y - yy);
    bool Near(WorldObject o) => Distance(s.x, s.y, o.x, o.y) <= 1;
    public View Handle(Command c)
    {
        if (s.mode == "battle" && s.battle?.phase == "enemy" && c.type != "advanceEnemyTurn")
        {
            s.message = "Wait for the enemy phase to finish.";
            return GetView();
        }
        if (s.battle != null && c.type != "forecast") s.battle.effectEvents = [];
        var pending = s.forecast;
        if (c.type == "confirm" && pending != null)
        {
            if (c.actorId == "")
                c.actorId = pending.actorId;
            if (c.targetId == "")
                c.targetId = pending.targetId;
            if (c.skillId == "")
                c.skillId = pending.skillId;
            if (c.manaSpend == 0)
                c.manaSpend = pending.manaSpend;
            c.x = pending.x; c.y = pending.y;
        }
        s.forecast = null;
        try
        {
            switch (c.type)
            {
                case "acknowledgeReward":
                    s.reward = null;
                    break;
                case "advanceEnemyTurn":
                    Require(s.mode == "battle" && s.battle?.phase == "enemy", "No enemy phase is pending.");
                    AdvanceEnemyTurn();
                    break;
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
                            EnemyTurn(c.animateEnemyTurn);
                        SelectLivingActor(true);
                    }
                    break;
                case "endTurn":
                    if (s.mode == "battle" && s.battle != null)
                        EnemyTurn(c.animateEnemyTurn);
                    break;
                case "rest":
                    Rest();
                    break;
                case "buy":
                    var purchase = PreparationService.Purchase(content, s, content.resupplyOffers, c.targetId);
                    Require(purchase.available, purchase.reason);
                    s.message = "Purchased " + purchase.quantity + " × " + purchase.name + ".";
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
                        s.reward = null;
                        s.message = "Returned to your last safe checkpoint.";
                    }
                    break;
                default:
                    s.message = "Choose a valid command.";
                    break;
            }
        }
        catch (InvalidOperationException e) { s.message = e.Message; }
        foreach (var u in s.party)
            progression.Refresh(u, s.mode == "battle");
        return GetView();
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
            Unlock("interact", o.id);
        }
        else if (o.kind == "safe")
            Rest();
        else if (o.kind == "exit")
        {
            Require(s.questStage >= 4, "The stairwell is sealed. Defeat the floor guardian first.");
            s.mode = "complete";
            s.message = "Floor 1 cleared. Carl and Donut descend together.";
            Log(s.message);
            Unlock("interact", o.id);
        }
        else if (o.kind == "chest")
        {
            Require(!s.cleared.Contains(o.id), "This cache is empty.");
            s.cleared.Add(o.id);
            int beforeGold = s.gold;
            s.gold = Math.Min(100000, s.gold + 20);
            var awarded = new List<Stack>();
            var loot = content.items.Where(i => i.kind != "consumable" && i.availability.Allows(s.floor, s.unlockedEvents)).ToArray();
            if (loot.Length > 0)
            {
                int index = (int)((uint)(s.seed + s.cleared.Count * 17) % loot.Length);
                int granted = Add(loot[index].id, 1);
                if (granted > 0) awarded.Add(new() { itemId = loot[index].id, count = granted });
            }
            s.reward = new() { id = "reward:" + o.id, sourceId = o.id, sourceKind = "cache", name = o.name, gold = s.gold - beforeGold, items = awarded.ToArray() };
            s.message = "Supply cache opened. Rewards received.";
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
        var encounter = catalog.Get<Encounter>("encounter", o.id);
        Require(encounter.availability.Allows(s.floor, s.unlockedEvents), "This encounter is not available yet.");
        Require(encounter.enemyIds.All(id => catalog.Get<Enemy>("enemy", id).availability.Allows(s.floor, s.unlockedEvents)), "An encounter enemy is unavailable at this story stage.");
        s.mode = "battle";
        s.turn = 1;
        s.battle = World.BuildArena(s.seed, o.id);
        s.battle.units = s.party;
        s.battle.hazards = encounter.hazards.ToList();
        s.battle.effectObjects = Codec.Read<EffectObject[]>(Codec.Write(encounter.effectObjects)).Where(obj => !s.destroyedEncounterObjectIds.Contains(encounter.id + ":" + obj.id)).ToList();
        foreach (var prop in s.battle.props.Where(p => !s.destroyedPropIds.Contains(p.id) && Destructible(p) && !s.battle.effectObjects.Any(o => o.propId == p.id)))
            s.battle.effectObjects.Add(new() { id = prop.id, propId = prop.id, x = prop.x, y = prop.y, width = prop.width, height = prop.height, hp = 12, blocksMovement = prop.blocksMovement, tags = content.explosiveAssetIds.Contains(prop.assetId) ? ["destructible", "explosive"] : ["destructible"] });
        foreach (var prop in s.battle.props.Where(Destructible))
            for (int y = prop.y; y < prop.y + prop.height; y++)
                for (int x = prop.x; x < prop.x + prop.width; x++)
                {
                    if (s.battle.tiles.Length > 0) s.battle.tiles[y * s.battle.width + x] = ".";
                    s.battle.obstacles = s.battle.obstacles.Where(p => p.x != x || p.y != y).ToArray();
                }
        s.battle.props = s.battle.props.Where(p => !s.destroyedPropIds.Contains(p.id)).ToArray();
        for (int i = 0; i < s.party.Count; i++)
        {
            var u = s.party[i];
            u.x = s.battle.composition == "industrial-sewer" ? 4 : 1;
            u.y = (s.battle.composition == "industrial-sewer" ? 3 : 2) + i * 3;
            u.moved = u.acted = u.ended = false;
        }
        var ids = encounter.enemyIds;
        for (int i = 0; i < ids.Length; i++)
        {
            var e = catalog.Get<Enemy>("enemy", ids[i]);
            s.battle.enemies.Add(new()
            {
                id = "enemy-" + i,
                templateId = e.id,
                name = e.name,
                x = (s.battle.composition == "industrial-sewer" ? 10 : 7) + i % 2,
                y = (s.battle.composition == "industrial-sewer" ? 3 : 1) + i * 2,
                hp = e.hp,
                maxHp = e.hp,
                power = e.power,
                armor = e.armor,
                element = e.element,
                tags = e.tags
            });
        }
        SelectLivingActor();
        s.reward = null;
        s.message = "Party phase. Each crawler may move and act in either order.";
    }
    bool Free(int x, int y, Unit self) => x >= 0 && y >= 0 && x < s.battle.width && y < s.battle.height && !s.battle.obstacles.Any(o => o.x == x && o.y == y) && !s.battle.effectObjects.Any(o => !o.destroyed && o.blocksMovement && x >= o.x && x < o.x + o.width && y >= o.y && y < o.y + o.height) && !s.party.Concat(s.battle.enemies).Any(u => u != self && u.hp > 0 && u.x == x && u.y == y);
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
        ApplyEffects(new() { sourceId = u.id, targetId = u.id, x = c.x, y = c.y, operations = [new() { kind = "move", x = c.x, y = c.y }] });
        u.moved = true;
        s.message = u.name + " moved.";
    }
    Skill Skill(string id) => catalog.Get<Skill>("skill", id);
    Forecast Predict(Command c)
    {
        var u = Actor(c.actorId);
        var k = Skill(c.skillId == "" ? (u?.skills.FirstOrDefault() ?? "punch") : c.skillId);
        var targetUnits = k.targetKind is "ally" or "self" ? s.party : s.battle?.enemies;
        var t = k.targetKind == "self" ? u : targetUnits?.FirstOrDefault(e => e.id == c.targetId);
        var obj = k.targetKind is "object" or "enemyOrObject" ? s.battle?.effectObjects.FirstOrDefault(o => o.id == c.targetId && !o.destroyed) : null;
        if (obj != null) t = new Unit { id = obj.id, name = obj.id, hp = obj.hp, x = obj.x, y = obj.y, element = "", tags = obj.tags };
        if (k.targetKind == "cell" && s.battle != null && c.x >= 0 && c.y >= 0 && c.x < s.battle.width && c.y < s.battle.height) t = new Unit { id = "", hp = 1, x = c.x, y = c.y, element = "" };
        var row = progression.Row(k, u == null ? k.startingRank : progression.EffectiveRank(u, k));
        int spend = c.manaSpend == 0 ? row.cost : c.manaSpend;
        bool validSpend = spend == row.cost || row.manaOptions.Contains(spend);
        bool valid = validSpend && s.mode == "battle" && u != null && u.hp > 0 && !u.acted && !u.ended && t != null && t.hp > 0 && u.skills.Contains(k.id) && k.availability.Allows(s.floor, s.unlockedEvents) && u.mp >= spend && Distance(u.x, u.y, t.x, t.y) <= row.range;
        var bonus = content.effectRules.damageBonuses.FirstOrDefault(rule => rule.incomingTag == k.element && t != null && (rule.targetTag == t.element || t.tags.Contains(rule.targetTag)));
        int reactionBonus = bonus?.amount ?? 0;
        string reaction = bonus?.reaction ?? "";
        var forecast = new Forecast
        {
            actorId = u?.id ?? "",
            targetId = t?.id ?? "",
            skillId = k.id,
            cost = spend,
            manaSpend = spend,
            range = row.range,
            x = t?.x ?? c.x, y = t?.y ?? c.y,
            effectRank = row.rank,
            trainedRank = u?.ranks.GetValueOrDefault(k.id, k.startingRank) ?? k.startingRank,
            effectiveRank = u == null ? k.startingRank : progression.EffectiveRank(u, k),
            valid = valid,
            reaction = reaction,
            damage = valid && k.targetKind is "enemy" or "object" or "cell" or "enemyOrObject" ? Math.Max(1, (int)Math.Round(u.power * row.powerMultiplier, MidpointRounding.AwayFromZero) + row.power + (spend - row.cost) * row.manaPowerPerPoint - t.armor + reactionBonus) : 0
        };
        if (valid)
        {
            var resolved = EffectResolver.Resolve(s.battle, AttackRequest(u, t, k, forecast.damage, spend), content.effectRules);
            forecast.valid = resolved.valid;
            forecast.events = resolved.events;
        }
        return forecast;
    }
    EffectRequest AttackRequest(Unit actor, Unit target, Skill skill, int damage, int cost) => new()
    {
        sourceId = actor.id, targetId = target.id, x = target.x, y = target.y,
        operations = new[] { new EffectOperation { kind = "resource", targetId = actor.id, amount = -cost }, new EffectOperation { kind = "damage", amount = damage, tag = skill.effectTag == "" ? skill.element : skill.effectTag, area = skill.effectRadius > 0, radius = skill.effectRadius } }.Concat(skill.effectOperations).ToList()
    };
    void ApplyEffects(EffectRequest request)
    {
        var resolution = EffectResolver.Resolve(s.battle, request, content.effectRules);
        Require(resolution.valid, resolution.reason);
        // Preserve the live view's unit identities while applying the resolver's isolated result.
        foreach (var changed in resolution.state.units.Concat(resolution.state.enemies))
        {
            var live = s.battle.units.Concat(s.battle.enemies).Single(u => u.id == changed.id);
            live.hp = changed.hp; live.mp = changed.mp; live.x = changed.x; live.y = changed.y;
            live.statuses = changed.statuses; live.tags = changed.tags;
        }
        s.battle.effectObjects = resolution.state.effectObjects;
        s.battle.hazards = resolution.state.hazards;
        s.battle.effectEvents.AddRange(resolution.events);
        s.battle.effectRevision++;
        s.battle.obstacles = resolution.state.obstacles;
        s.battle.props = resolution.state.props;
        foreach (var destroyed in s.battle.effectObjects.Where(o => o.destroyed && o.propId == ""))
        {
            string receipt = s.battle.encounterId + ":" + destroyed.id;
            if (content.encounters.Any(e => e.id == s.battle.encounterId && e.effectObjects.Any(o => o.id == destroyed.id && o.tags.Contains("destructible"))) && !s.destroyedEncounterObjectIds.Contains(receipt)) s.destroyedEncounterObjectIds.Add(receipt);
        }
        foreach (var destroyed in s.battle.effectObjects.Where(o => o.destroyed && o.propId != ""))
        {
            var original = OriginalWorld(s.seed).props.SingleOrDefault(p => p.id == destroyed.propId);
            if (original != null && Destructible(original) && !s.destroyedPropIds.Contains(original.id)) s.destroyedPropIds.Add(original.id);
        }
        s.world = ApplyDestroyed(Codec.Read<WorldMap>(Codec.Write(OriginalWorld(s.seed))), s.destroyedPropIds);
    }
    bool Destructible(WorldProp prop) => Destructible(prop, OriginalWorld(s.seed));
    bool Destructible(WorldProp prop, WorldMap trusted)
    {
        if (prop.layer == "wallfixture" || !content.destructibleAssetIds.Contains(prop.assetId)) return false;
        var original = trusted.props.SingleOrDefault(p => p.id == prop.id);
        if (original == null) return false;
        // Solid non-fixture props are placed only on authored floor by World.Build.
        if (original.blocksMovement) return true;
        for (int y = original.y; y < original.y + original.height; y++)
            for (int x = original.x; x < original.x + original.width; x++)
                if (trusted.tiles[y * trusted.width + x] != ".") return false;
        return true;
    }
    WorldMap ApplyDestroyed(WorldMap world, List<string> receipts)
    {
        if (receipts == null || receipts.Count != receipts.Distinct().Count()) throw new InvalidOperationException("Invalid destroyed prop receipts.");
        foreach (var id in receipts)
        {
            var prop = world.props.SingleOrDefault(p => p.id == id);
            if (prop == null || !Destructible(prop, world)) throw new InvalidOperationException("Invalid destroyed prop receipt: " + id);
            for (int y = prop.y; y < prop.y + prop.height; y++)
                for (int x = prop.x; x < prop.x + prop.width; x++)
                    if (x >= 0 && y >= 0 && x < world.width && y < world.height)
                        world.tiles[y * world.width + x] = ".";
        }
        world.props = world.props.Where(p => !receipts.Contains(p.id)).ToArray();
        return world;
    }
    void Attack(Command c)
    {
        var f = Predict(c);
        Require(f.valid, "Choose a valid skill and target first.");
        var u = Actor(f.actorId);
        var t = new Unit { id = f.targetId, x = f.x, y = f.y };
        ApplyEffects(AttackRequest(u, t, Skill(f.skillId), f.damage, f.cost));
        u.acted = true;
        progression.Practice(Actor(f.actorId), Skill(f.skillId));
        s.message = $"{u.name} deals {f.damage} damage. {f.reaction}";
        if (s.party.All(unit => unit.hp <= 0))
        {
            s.mode = "defeat";
            s.message = "The run ends here. Retry from the safe checkpoint.";
        }
        else if (s.battle.enemies.All(e => e.hp <= 0)) Win();
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
    void SelectLivingActor(bool preferReady = false)
    {
        var current = Actor(s.selectedId);
        if (current?.hp > 0 && (!preferReady || !current.ended)) return;
        s.selectedId = s.party.FirstOrDefault(u => u.hp > 0 && (!preferReady || !u.ended))?.id
            ?? s.party.FirstOrDefault(u => u.hp > 0)?.id ?? s.selectedId;
    }
    void EnemyTurn(bool animate = false)
    {
        s.forecast = null;
        s.battle.phase = "enemy";
        enemyOrder = s.battle.enemies.Where(e => e.hp > 0).Select(e => e.id).ToArray();
        enemyIndex = 0;
        PrepareEnemyIntent();
        if (!animate)
            while (s.mode == "battle" && s.battle.phase == "enemy") AdvanceEnemyTurn();
    }
    void PrepareEnemyIntent()
    {
        while (enemyIndex < enemyOrder.Length)
        {
            var e = s.battle.enemies.First(u => u.id == enemyOrder[enemyIndex]);
            if (e.hp <= 0) { enemyIndex++; continue; }
            // A reachable target always takes precedence over an isolated nearest target.
            var candidates = s.party.Where(u => u.hp > 0).Select(u => new { unit = u, path = EnemyPath(e, u) })
                .Where(p => Distance(e.x, e.y, p.unit.x, p.unit.y) <= 1 || p.path.Count > 0)
                .OrderBy(p => p.path.Count).ThenBy(p => p.unit.id, StringComparer.Ordinal).ToArray();
            var target = candidates.FirstOrDefault();
            s.battle.enemyIntent = new()
            {
                actorId = e.id, targetId = target?.unit.id ?? "",
                path = target?.path.Take(3).Select(p => new Point { x = p.x, y = p.y }).ToArray() ?? [],
                stage = target == null ? "wait" : target.path.Count > 0 ? "move" : "attack"
            };
            s.message = target == null ? e.name + " cannot reach a crawler." : e.name + " targets " + target.unit.name + ".";
            return;
        }
        s.battle.enemyIntent = new() { stage = "tick" };
        s.message = "Enemy phase: resolving environmental effects.";
    }
    void AdvanceEnemyTurn()
    {
        var intent = s.battle.enemyIntent;
        if (intent.stage == "tick")
        {
            ApplyEffects(new() { operations = [new() { kind = "tick" }] });
            FinishEnemyTurn();
            return;
        }
        var e = s.battle.enemies.First(u => u.id == intent.actorId);
        if (intent.stage == "move" && e.hp > 0 && intent.step < intent.path.Length)
        {
            var step = intent.path[intent.step++];
            if (Free(step.x, step.y, e))
                ApplyEffects(new() { sourceId = e.id, targetId = e.id, x = step.x, y = step.y, operations = [new() { kind = "move", x = step.x, y = step.y }] });
            if (intent.step >= intent.path.Length) intent.stage = "attack";
            s.message = e.name + " advances.";
            return;
        }
        var target = s.party.FirstOrDefault(u => u.id == intent.targetId && u.hp > 0);
        if (e.hp > 0 && target != null && Distance(e.x, e.y, target.x, target.y) <= 1)
        {
            ApplyEffects(new() { sourceId = e.id, targetId = target.id, x = target.x, y = target.y, operations = [new() { kind = "damage", amount = Math.Max(1, e.power - target.armor), tag = e.element }] });
            s.message = e.name + " attacks " + target.name + ".";
        }
        enemyIndex++;
        PrepareEnemyIntent();
    }
    void FinishEnemyTurn()
    {
        if (s.battle.enemies.All(e => e.hp <= 0) && s.party.Any(u => u.hp > 0)) { Win(); return; }
        if (s.party.All(u => u.hp <= 0))
        {
            s.mode = "defeat";
            s.message = "The run ends here. Retry from the safe checkpoint.";
            return;
        }
        foreach (var u in s.party)
            u.moved = u.acted = u.ended = false;
        s.battle.phase = "party";
        s.battle.enemyIntent = null;
        SelectLivingActor(true);
        s.turn++;
        s.message = "Party phase. The enemies have advanced.";
    }
    void Win()
    {
        string id = s.battle.encounterId;
        s.cleared.Add(id);
        s.questStage = Math.Max(s.questStage, id == "false-guild" ? 1 : id == "goblin-workshop" ? 3 : id == "ball-of-swine" ? 4 : s.questStage);
        var reward = content.encounters.FirstOrDefault(e => e.id == id);
        int goldBefore = s.gold;
        s.gold = Math.Min(100000, s.gold + (reward?.goldReward ?? 25));
        var gains = s.party.Select(u => new RewardProgress { actorId = u.id, xp = u.xp, levelBefore = u.level }).ToArray();
        foreach (var u in s.party)
            progression.Reward(u, reward?.xpReward ?? 30);
        foreach (var gain in gains)
        {
            var u = Actor(gain.actorId);
            gain.xp = u.xp - gain.xp;
            gain.levelAfter = u.level;
        }
        var awardedItems = new List<Stack>();
        foreach (var item in reward?.itemRewards ?? [])
        {
            int granted = Add(item.itemId, item.count);
            if (granted > 0) awardedItems.Add(new() { itemId = item.itemId, count = granted });
        }
        s.reward = new() { id = "reward:" + id, sourceId = id, sourceKind = "encounter", name = reward?.name ?? id, gold = s.gold - goldBefore, items = awardedItems.ToArray(), party = gains };
        SelectLivingActor();
        s.mode = "explore";
        s.battle = null;
        s.message = id == "ball-of-swine" ? "Guardian defeated. Reach the stairwell to finish Floor 1." : "Victory. Rewards received; return to Mordecai or continue the objective.";
        Log("Cleared " + id + ".");
        Unlock("clear", id);
    }
    void Unlock(string trigger, string id)
    {
        foreach (var ev in content.storyEvents.Where(e => e.trigger == trigger && e.triggerId == id))
        {
            if (!ev.availability.Allows(s.floor, s.unlockedEvents) || s.unlockedEvents.Contains(ev.id)) continue;
            s.unlockedEvents.Add(ev.id);
            foreach (var skillId in ev.unlockSkillIds)
            {
                var skill = catalog.Get<Skill>("skill", skillId);
                var actor = s.party.SingleOrDefault(u => skill.ownerId == "crawler." + u.id);
                if (actor == null || actor.skills.Contains(skillId)) continue;
                actor.skills = actor.skills.Append(skillId).ToArray();
                actor.ranks[skillId] = skill.startingRank; actor.skillPractice[skillId] = 0;
            }
        }
    }
    void Rest()
    {
        Require(s.mode == "explore" && s.world.objects.Any(o => o.kind == "safe" && Near(o)), "Rest at the safe room.");
        foreach (var u in s.party)
        {
            u.hp = u.maxHp;
            u.mp = u.maxMp;
            u.statuses.Clear();
            u.temporaryRankModifiers.Clear();
            u.moved = u.acted = u.ended = false;
        }
        SelectLivingActor();
        s.message = "Safe room: party restored and checkpoint saved.";
        checkpoint = Codec.Write(s);
    }
    int Add(string id, int count)
    {
        var stack = s.inventory.FirstOrDefault(i => i.itemId == id);
        int granted = Math.Min(count, PreparationService.InventoryCountCap - (stack?.count ?? 0));
        if (granted <= 0) return 0;
        if (stack == null) s.inventory.Add(new() { itemId = id, count = granted });
        else stack.count += granted;
        return granted;
    }
    void Equip(Command c)
    {
        var u = Actor(c.actorId);
        var preview = PreparationService.Equip(content, s, u?.id ?? c.actorId, c.itemId);
        Require(preview.available, preview.reason);
        s.message = c.itemId == "" ? u.name + " removed equipment." : u.name + " equipped " + content.items.Single(i => i.id == c.itemId).name + ".";
    }
    void Use(Command c)
    {
        var u = Actor(c.actorId);
        var i = content.items.FirstOrDefault(i => i.id == c.itemId);
        var st = s.inventory.FirstOrDefault(v => v.itemId == c.itemId);
        var preview = PreparationService.PreviewConsumable(content, s, u?.id ?? c.actorId, c.itemId);
        Require(preview.available, preview.reason);
        if (s.mode == "battle")
        {
            ApplyEffects(new() { sourceId = u.id, targetId = u.id, x = u.x, y = u.y, operations = [new() { kind = "heal", amount = i.heal }, new() { kind = "resource", amount = i.mp }] });
            u = Actor(c.actorId);
        }
        else
        {
            var temporary = new Battle { units = s.party };
            var result = EffectResolver.Resolve(temporary, new() { sourceId = u.id, targetId = u.id, operations = [new() { kind = "heal", amount = i.heal }, new() { kind = "resource", amount = i.mp }] }, content.effectRules);
            Require(result.valid, result.reason);
            s.party = result.state.units;
            u = Actor(c.actorId);
        }
        st.count--;
        if (s.mode == "battle")
            u.acted = true;
        s.message = i.name + " used.";
    }
    public string GetSave()
    {
        Require(s.mode == "explore" && s.world.objects.Any(o => o.kind == "safe" && Near(o)), "Save at a safe room.");
        var persisted = Codec.Read<View>(Codec.Write(s));
        persisted.reward = null;
        persisted.nearbyInteractions = [];
        persisted.objective = null;
        persisted.nearestSafe = null;
        persisted.safeRoom = null;
        persisted.equipmentPreviews = [];
        persisted.consumablePreviews = [];
        persisted.resupplyOffers = [];
        return Codec.Write(new Save { state = persisted });
    }
    bool ValidSave(View v, WorldMap trustedWorld)
    {
        if (v == null || v.mode != "explore" || v.party == null || v.party.Count != 2 || v.party.Any(u => u == null) || v.party[0].id != "carl" || v.party[1].id != "donut" || v.inventory == null || v.cleared == null || v.journal == null || v.journal.Any(x => x == null) || v.questStage < 0 || v.questStage > 4 || v.gold < 0 || v.gold > 100000 || v.turn < 1 || !v.party.Any(u => u.id == v.selectedId))
            return false;
        if (v.inventory.Any(i => i == null || i.count < 0 || i.count > 999 || !content.items.Any(it => it.id == i.itemId && it.availability.Allows(1, v.unlockedEvents ?? []))) || v.inventory.Select(i => i.itemId).Distinct().Count() != v.inventory.Count)
            return false;
        foreach (var u in v.party)
        {
            var character = catalog.Deployable(1, v.unlockedEvents ?? []).SingleOrDefault(c => (c.runtimeId == "" ? c.id.Replace("crawler.", "") : c.runtimeId) == u.id);
            string[] expected = character?.skillIds ?? (u.id == "carl" ? ["punch", "powerful-strike", "bomb"] : ["magic-missile", "claw"]);
            expected = expected.Concat(content.storyEvents.Where(e => (v.unlockedEvents ?? []).Contains(e.id)).SelectMany(e => e.unlockSkillIds).Where(id => Skill(id).ownerId == "crawler." + u.id)).Distinct().ToArray();
            if (u.name == null || u.equipment == null || u.skills == null || !u.skills.SequenceEqual(expected) || u.ranks == null || u.ranks.Count != expected.Length || expected.Any(k => !u.ranks.TryGetValue(k, out var rank) || rank < 1 || rank > 20) || u.level < 1 || u.level > 20 || u.xp < 0 || u.xp > 100000 || u.maxHp <= 0 || u.maxHp > 1000 || u.maxMp < 0 || u.maxMp > 1000 || u.hp < 0 || u.hp > u.maxHp || u.mp < 0 || u.mp > u.maxMp || u.power < 0 || u.power > 1000 || u.armor < 0 || u.armor > 1000)
                return false;
            if (u.equipment != "" && !content.items.Any(i => i.id == u.equipment && i.availability.Allows(1, v.unlockedEvents ?? []) && (i.kind == "armor" || i.kind == "charm" || (i.kind == "weapon" && u.id != "carl")) && v.inventory.Any(st => st.itemId == i.id && st.count > 0)))
                return false;
        }
        if (v.party.Where(u => u.equipment != "").Select(u => u.equipment).Distinct().Count() != v.party.Count(u => u.equipment != ""))
            return false;
        v.world = trustedWorld;
        if (v.x < 0 || v.y < 0 || v.x >= v.world.width || v.y >= v.world.height || v.world.tiles[v.y * v.world.width + v.x] != "." || !v.world.objects.Any(o => o.kind == "safe" && Distance(v.x, v.y, o.x, o.y) <= 1))
            return false;
        if (v.cleared.Distinct().Count() != v.cleared.Count || v.cleared.Any(id => !v.world.objects.Any(o => o.id == id && (o.kind == "encounter" || o.kind == "boss" || o.kind == "chest"))))
            return false;
        bool first = v.cleared.Contains("false-guild"), workshop = v.cleared.Contains("goblin-workshop"), boss = v.cleared.Contains("ball-of-swine");
        if (first != (v.questStage >= 1) || workshop != (v.questStage >= 3) || boss != (v.questStage == 4) || v.cleared.Any(id => id is "hoarder" or "juicer") && v.questStage < 2)
            return false;
        return true;
    }
    bool ValidStatus(EffectStatus status, View state)
    {
        if (status == null || status.tags == null || status.tags.Length != 0 || status.duration is < 1 or > 100 || status.strength is < 0 or > 999 || status.stacking is not ("refresh" or "replace" or "add") || (status.sourceId != "" && !state.party.Any(u => u.id == status.sourceId) && !status.sourceId.StartsWith("enemy-", StringComparison.Ordinal))) return false;
        var temporary = content.temporaryModifiers.SingleOrDefault(d => d.id == status.id);
        if (temporary != null) return temporary.availability.Allows(state.floor, state.unlockedEvents) && status.duration <= temporary.duration;
        var operations = content.skills.SelectMany(k => k.effectOperations).Concat(content.effectRules.reactions.SelectMany(r => r.operations));
        return operations.Any(op => op.kind == "status" && op.statusId == status.id && status.duration <= op.duration && (op.stacking == "add" || status.strength <= op.strength))
            || status.id == content.effectRules.burningStatus && status.duration <= content.effectRules.burningDuration && status.strength <= content.effectRules.burningStrength;
    }
    public View LoadSave(string json)
    {
        try
        {
            var save = Codec.Read<Save>(json);
            if (save == null || (save.version != 1 && save.version != 2 && save.version != 3) || save.state?.world == null)
                throw new InvalidOperationException();
            var candidate = save.state;
            var sourceWorld = candidate.world;
            bool migrate = sourceWorld.generationVersion is 0 or 1 or 2 or 3;
            if (!migrate && sourceWorld.generationVersion != 4)
                throw new NotSupportedException();
            var trustedWorld = sourceWorld.generationVersion is 0 or 1 ? World.BuildLegacy(candidate.seed) : sourceWorld.generationVersion == 2 ? World.BuildVersion2(candidate.seed) : sourceWorld.generationVersion == 3 ? World.BuildVersion3(candidate.seed) : World.Build(candidate.seed);
            if (save.version >= 3)
                trustedWorld = ApplyDestroyed(trustedWorld, candidate.destroyedPropIds);
            else { candidate.destroyedPropIds = []; candidate.destroyedEncounterObjectIds = []; }
            if (candidate.destroyedEncounterObjectIds == null || candidate.destroyedEncounterObjectIds.Distinct().Count() != candidate.destroyedEncounterObjectIds.Count || candidate.destroyedEncounterObjectIds.Any(receipt => !content.encounters.Any(e => e.effectObjects.Any(obj => obj.tags.Contains("destructible") && obj.propId == "" && receipt == e.id + ":" + obj.id)))) throw new InvalidOperationException();
            // Legacy coordinates are meaningful only against the original authored map.
            // Compare the persisted geometry before validating any checkpoint or receipt.
            if (sourceWorld.width != trustedWorld.width || sourceWorld.height != trustedWorld.height ||
                sourceWorld.spawnX != trustedWorld.spawnX || sourceWorld.spawnY != trustedWorld.spawnY ||
                Codec.Write(sourceWorld.tiles) != Codec.Write(trustedWorld.tiles) ||
                Codec.Write(sourceWorld.objects) != Codec.Write(trustedWorld.objects) ||
                Codec.Write(sourceWorld.rooms) != Codec.Write(trustedWorld.rooms) ||
                Codec.Write(sourceWorld.props) != Codec.Write(trustedWorld.props) ||
                !ValidSave(candidate, trustedWorld))
                throw new InvalidOperationException();
            if (save.version == 1)
                foreach (var u in candidate.party)
                    progression.Migrate(u);
            else if (candidate.party.Any(u => !progression.ValidMastery(u)))
                throw new InvalidOperationException();
            if (save.version < 3)
            {
                candidate.floor = 1;
                candidate.unlockedEvents = [];
                foreach (var ev in content.storyEvents)
                    if ((ev.trigger == "clear" && candidate.cleared.Contains(ev.triggerId) || ev.trigger == "interact" && ev.triggerId == "mordecai" && candidate.questStage >= 2) && ev.availability.Allows(1, candidate.unlockedEvents)) candidate.unlockedEvents.Add(ev.id);
                foreach (var u in candidate.party) u.temporaryRankModifiers = new();
            }
            if (candidate.floor != 1 || candidate.unlockedEvents == null || candidate.unlockedEvents.Distinct().Count() != candidate.unlockedEvents.Count || candidate.unlockedEvents.Any(id => catalog.Find("storyEvent", id) == null) || candidate.party.Any(u => u.temporaryRankModifiers == null || u.temporaryRankModifiers.Count != 0))
                throw new InvalidOperationException();
            foreach (var eventId in candidate.unlockedEvents)
            {
                var ev = catalog.Get<StoryEventDefinition>("storyEvent", eventId);
                if (!ev.availability.Allows(candidate.floor, candidate.unlockedEvents) || (ev.trigger == "clear" && !candidate.cleared.Contains(ev.triggerId)) || (ev.trigger == "interact" && (ev.triggerId == "mordecai" ? candidate.questStage < 2 : true)))
                    throw new InvalidOperationException();
            }
            var equipmentNotices = new List<string>();
            foreach (var u in candidate.party)
            {
                if (u.tags == null || u.tags.Length != 0 || u.statuses == null || u.statuses.Select(status => status?.id).Distinct().Count() != u.statuses.Count || u.statuses.Any(status => !ValidStatus(status, candidate))) throw new InvalidOperationException();
                var character = catalog.Deployable(1, candidate.unlockedEvents).SingleOrDefault(c => (c.runtimeId == "" ? c.id.Replace("crawler.", "") : c.runtimeId) == u.id);
                u.templateId = character?.id ?? "crawler." + u.id;
                var equipped = content.items.FirstOrDefault(i => i.id == u.equipment);
                if (equipped != null && !PreparationService.CanOwn(content, u, equipped))
                {
                    // Older checkpoints permitted personal equipment on either crawler.
                    // Keep the owned item and explain the compatibility correction.
                    u.power -= equipped.power;
                    u.armor -= equipped.armor;
                    if (u.power < 0 || u.armor < 0) throw new InvalidOperationException();
                    u.equipment = "";
                    equipmentNotices.Add(u.name + " returned " + equipped.name + " to inventory because it belongs to the other crawler.");
                }
                progression.Refresh(u);
            }
            if (migrate)
            {
                var oldSafe = trustedWorld.objects.Where(o => o.kind == "safe" && Distance(candidate.x, candidate.y, o.x, o.y) <= 1)
                    .OrderBy(o => Distance(candidate.x, candidate.y, o.x, o.y)).ThenBy(o => o.id, StringComparer.Ordinal).First();
                var nextWorld = World.Build(candidate.seed);
                var nextSafe = nextWorld.objects.SingleOrDefault(o => o.kind == "safe" && o.id == oldSafe.id);
                if (nextSafe == null)
                    throw new InvalidOperationException();
                var destination = new[] { (x: nextSafe.x - 1, y: nextSafe.y), (x: nextSafe.x + 1, y: nextSafe.y),
                    (x: nextSafe.x, y: nextSafe.y - 1), (x: nextSafe.x, y: nextSafe.y + 1) }
                    .Where(p => p.x >= 0 && p.y >= 0 && p.x < nextWorld.width && p.y < nextWorld.height &&
                        nextWorld.tiles[p.y * nextWorld.width + p.x] == "." && !nextWorld.objects.Any(o => o.x == p.x && o.y == p.y))
                    .ToArray();
                if (destination.Length == 0)
                    throw new InvalidOperationException();
                candidate.world = nextWorld;
                candidate.x = destination[0].x;
                candidate.y = destination[0].y;
            }
            candidate.battle = null;
            candidate.forecast = null;
            candidate.reward = null;
            candidate.nearbyInteractions = [];
            candidate.objective = null;
            candidate.nearestSafe = null;
            candidate.safeRoom = null;
            candidate.equipmentPreviews = [];
            candidate.consumablePreviews = [];
            candidate.resupplyOffers = [];
            foreach (var u in candidate.party)
            {
                u.x = 0;
                u.y = 0;
                u.moved = u.acted = u.ended = false;
            }
            candidate.message = migrate ? "Safe-room save upgraded to the new map. Progress preserved." : "Safe-room save loaded.";
            if (save.version == 1)
                candidate.message += " Character XP rebased to the new curve; levels and stats preserved. Powerful Strike now starts at rank 3; legacy higher ranks retain capped early effects.";
            if (equipmentNotices.Count > 0) candidate.message += " " + string.Join(" ", equipmentNotices);
            var nextCheckpoint = Codec.Write(candidate);
            s = candidate;
            checkpoint = nextCheckpoint;
        }
        catch (NotSupportedException) { s.message = "Invalid save: incompatible map version. Start a fresh run or use a supported safe-room checkpoint. Your current run is unchanged."; }
        catch { s.message = "Invalid save. Your current run is unchanged."; }
        return GetView();
    }
}
