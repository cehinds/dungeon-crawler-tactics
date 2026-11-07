namespace DccRebuild;

/// <summary>Deterministic, copy-on-resolve rules shared by forecasts and committed actions.</summary>
public static class EffectResolver
{
    public const int MaximumReactionSteps = 128;
    public static void ValidateRules(EffectRules rules)
    {
        const string path = "content.effectRules";
        void Require(bool valid, string field, string message)
        { if (!valid) throw new InvalidOperationException(path + field + ": " + message); }
        void Tags(string[] tags, string field)
        {
            Require(tags != null, field, "missing tag array.");
            Require(tags.Length <= 128 && tags.All(tag => !string.IsNullOrWhiteSpace(tag)) && tags.Distinct(StringComparer.Ordinal).Count() == tags.Length, field, "tags must be unique nonempty IDs (maximum 128).");
        }
        Require(rules != null, "", "missing rules.");
        Require(rules.maximumReactionSteps is >= 1 and <= MaximumReactionSteps, ".maximumReactionSteps", "expected 1..128.");
        Tags(rules.ignitionTags, ".ignitionTags"); Tags(rules.extinguishTags, ".extinguishTags");
        Require(!string.IsNullOrWhiteSpace(rules.fuelTag) && !string.IsNullOrWhiteSpace(rules.burningStatus) && !string.IsNullOrWhiteSpace(rules.explosiveTag), "", "fallback tag IDs must be nonempty.");
        Require(rules.burningDuration is >= 1 and <= 100 && rules.burningStrength is >= 0 and <= 999 && rules.explosionDamage is >= 0 and <= 10000 && rules.explosionRadius is >= 0 and <= 32, "", "invalid fallback reaction bounds.");
        Require(rules.reactions != null && rules.reactions.Count <= MaximumReactionSteps, ".reactions", "missing array or more than 128 reactions.");
        Require(rules.damageBonuses != null && rules.damageBonuses.Length <= 128, ".damageBonuses", "missing array or more than 128 entries.");
        var bonusPairs = new HashSet<string>(StringComparer.Ordinal);
        for (int i = 0; i < rules.damageBonuses.Length; i++)
        {
            var bonus = rules.damageBonuses[i]; string field = $".damageBonuses[{i}]";
            Require(bonus != null, field, "missing bonus.");
            Require(!string.IsNullOrWhiteSpace(bonus.incomingTag) && !string.IsNullOrWhiteSpace(bonus.targetTag), field, "incomingTag and targetTag are required.");
            Require(bonusPairs.Add(bonus.incomingTag + ":" + bonus.targetTag), field, "duplicate incoming/target tag pair.");
            Require(bonus.amount is >= -1000 and <= 1000 && bonus.reaction != null, field, "invalid amount or reaction text.");
        }
        var ids = new HashSet<string>(StringComparer.Ordinal);
        for (int i = 0; i < rules.reactions.Count; i++)
        {
            var rule = rules.reactions[i]; string field = $".reactions[{i}]";
            Require(rule != null, field, "missing reaction.");
            Require(!string.IsNullOrWhiteSpace(rule.id) && ids.Add(rule.id), field + ".id", "missing or duplicate stable ID.");
            Require(rule.targetKind is "unit" or "object", field + ".targetKind", "expected unit or object.");
            Require(rule.trigger == "effect" || rule.trigger == "destroyed" && rule.targetKind == "object", field + ".trigger", "supported triggers: effect; object additionally supports destroyed.");
            Tags(rule.triggerTags, field + ".triggerTags"); Tags(rule.requiredTargetTags, field + ".requiredTargetTags");
            Tags(rule.excludedTargetTags, field + ".excludedTargetTags"); Tags(rule.removeTags, field + ".removeTags");
            Require(rule.trigger != "effect" || rule.triggerTags.Length > 0, field + ".triggerTags", "effect triggers need at least one tag.");
            Require(rule.priority is >= -10000 and <= 10000, field + ".priority", "expected -10000..10000.");
            Require(rule.operations != null && rule.operations.Length <= MaximumReactionSteps, field + ".operations", "missing array or more than 128 operations.");
            for (int j = 0; j < rule.operations.Length; j++) ValidateOperation(rule.operations[j], path + field + $".operations[{j}]");
        }
    }
    public static void ValidateOperation(EffectOperation operation, string path)
    {
        void Require(bool valid, string field, string message)
        { if (!valid) throw new InvalidOperationException(path + field + ": " + message); }
        Require(operation != null, "", "missing operation.");
        Require(operation.kind is "damage" or "heal" or "status" or "removeStatus" or "move" or "displace" or "resource" or "object" or "tick", ".kind", "unknown operation kind.");
        Require(operation.targetId != null && operation.tag != null && operation.statusId != null, "", "IDs cannot be null.");
        Require(operation.amount is >= -10000 and <= 10000 && (operation.kind is "resource" || operation.amount >= 0), ".amount", "amount outside supported bounds.");
        Require(operation.radius is >= 0 and <= 32, ".radius", "expected 0..32.");
        Require(operation.x is >= -128 and <= 128 && operation.y is >= -128 and <= 128 && operation.dx is >= -128 and <= 128 && operation.dy is >= -128 and <= 128, "", "coordinates/displacement outside -128..128.");
        Require(operation.duration is >= -1 and <= 100 && operation.strength is >= 0 and <= 999, "", "invalid duration or strength.");
        if (operation.kind == "status") Require(!string.IsNullOrWhiteSpace(operation.statusId) && operation.duration != 0 && operation.stacking is "refresh" or "add" or "replace", ".statusId", "status requires ID, nonzero duration, and refresh/add/replace stacking.");
        if (operation.kind == "removeStatus") Require(!string.IsNullOrWhiteSpace(operation.statusId), ".statusId", "missing status ID.");
        if (operation.kind == "resource") Require(operation.resource == "mp", ".resource", "only mp is supported.");
    }
    public static EffectResolution Resolve(Battle source, EffectRequest request, EffectRules rules = null)
    {
        rules ??= new();
        var result = new EffectResolution { state = source == null ? null : Codec.Read<Battle>(Codec.Write(source)) };
        try
        {
            ValidateRules(rules);
            if (source == null) throw new InvalidOperationException("effectRequest.source: missing battle.");
            if (request == null || request.operations == null || request.operations.Count > rules.maximumReactionSteps)
                throw new InvalidOperationException("effectRequest.operations: missing or exceeds reaction limit.");
            for (int i = 0; i < request.operations.Count; i++) ValidateOperation(request.operations[i], $"effectRequest.operations[{i}]");
        }
        catch (InvalidOperationException error) { result.reason = error.Message; return result; }
        int stepLimit = rules.maximumReactionSteps;
        var state = result.state;
        var queue = new Queue<(EffectOperation operation, string source, string target, int x, int y)>();
        foreach (var operation in request.operations) queue.Enqueue((operation, request.sourceId, request.targetId, request.x, request.y));
        var reactions = new HashSet<string>();
        int steps = 0;
        IEnumerable<Unit> Units() => state.units.Concat(state.enemies);
        void Emit(string kind, string sourceId, string targetId, int amount, int x, int y, string tag = "") =>
            result.events.Add(new() { kind = kind, sourceId = sourceId, targetId = targetId, amount = amount, x = x, y = y, tag = tag });
        void Remove(Unit unit, string id, string sourceId)
        {
            if (unit.statuses.RemoveAll(status => status.id == id || status.tags.Contains(id)) > 0)
                Emit("statusRemoved", sourceId, unit.id, 0, unit.x, unit.y, id);
        }
        void Status(Unit unit, EffectOperation operation, string sourceId)
        {
            var existing = unit.statuses.FirstOrDefault(status => status.id == operation.statusId);
            if (existing != null && operation.stacking == "replace") unit.statuses.Remove(existing);
            else if (existing != null)
            {
                existing.duration = existing.duration == -1 || operation.duration == -1 ? -1 : Math.Max(existing.duration, operation.duration);
                existing.strength = operation.stacking == "add" ? Math.Min(999, existing.strength + operation.strength) : Math.Max(existing.strength, operation.strength);
                existing.sourceId = sourceId;
                Emit("statusApplied", sourceId, unit.id, existing.strength, unit.x, unit.y, operation.statusId);
                return;
            }
            unit.statuses.Add(new() { id = operation.statusId, sourceId = sourceId, duration = operation.duration, strength = Math.Max(0, operation.strength), stacking = operation.stacking, tags = string.IsNullOrEmpty(operation.tag) ? [] : [operation.tag] });
            Emit("statusApplied", sourceId, unit.id, operation.strength, unit.x, unit.y, operation.statusId);
        }
        void ObjectReactions(EffectObject obj, string trigger, string operationTag, string sourceId)
        {
            foreach (var rule in rules.reactions.Where(rule => rule.targetKind == "object" && rule.trigger == trigger)
                .OrderBy(rule => rule.priority).ThenBy(rule => rule.id, StringComparer.Ordinal))
            {
                if (rule.triggerTags.Length > 0 && !rule.triggerTags.Contains(operationTag)
                    || !rule.requiredTargetTags.All(obj.tags.Contains) || rule.excludedTargetTags.Any(obj.tags.Contains)
                    || !reactions.Add(rule.id + ":object:" + obj.id)) continue;
                obj.tags = obj.tags.Where(tag => !rule.removeTags.Contains(tag)).ToArray();
                Emit("reaction", sourceId, obj.id, 0, obj.x, obj.y, rule.id);
                foreach (var operation in rule.operations)
                {
                    if (operation.area && operation.tag == "explosion")
                        Emit("explosion", obj.id, obj.id, operation.amount, obj.x, obj.y, operation.tag);
                    queue.Enqueue((operation, obj.id, obj.id, obj.x, obj.y));
                }
            }
        }
        bool Walkable(int x, int y, Unit moving) => x >= 0 && y >= 0 && x < state.width && y < state.height
            && !state.obstacles.Any(p => p.x == x && p.y == y)
            && !state.effectObjects.Any(o => !o.destroyed && o.blocksMovement && x >= o.x && x < o.x + o.width && y >= o.y && y < o.y + o.height)
            && !Units().Any(u => u != moving && u.hp > 0 && u.x == x && u.y == y);
        while (queue.Count > 0 && steps++ < stepLimit)
        {
            var entry = queue.Dequeue();
            var op = entry.operation;
            string targetId = string.IsNullOrEmpty(op.targetId) ? entry.target : op.targetId;
            var targets = Units().Where(u => op.area ? Math.Abs(u.x - entry.x) + Math.Abs(u.y - entry.y) <= Math.Max(0, op.radius) : u.id == targetId).OrderBy(u => u.id, StringComparer.Ordinal).ToArray();
            if (op.kind == "tick") targets = Units().OrderBy(u => u.id, StringComparer.Ordinal).ToArray();
            foreach (var unit in targets)
            {
                if (op.kind == "tick")
                {
                    if (state.hazards.Any(h => h.x == unit.x && h.y == unit.y && rules.extinguishTags.Contains(h.tag)))
                        Remove(unit, rules.burningStatus, entry.source);
                    foreach (var status in unit.statuses.ToArray())
                    {
                        if (status.id == rules.burningStatus && unit.hp > 0)
                        {
                            int damage = Math.Min(unit.hp, Math.Max(0, status.strength)); unit.hp -= damage;
                            Emit("damage", status.sourceId, unit.id, damage, unit.x, unit.y, "burning");
                        }
                        if (status.duration > 0 && --status.duration == 0) Remove(unit, status.id, status.sourceId);
                    }
                    continue;
                }
                if (op.kind == "damage")
                {
                    int damage = Math.Min(unit.hp, Math.Max(0, op.amount)); unit.hp -= damage;
                    Emit("damage", entry.source, unit.id, damage, unit.x, unit.y, op.tag);
                }
                else if (op.kind == "heal") { int heal = Math.Min(unit.maxHp - unit.hp, Math.Max(0, op.amount)); unit.hp += heal; Emit("heal", entry.source, unit.id, heal, unit.x, unit.y); }
                else if (op.kind == "resource")
                {
                    int before = unit.mp; unit.mp = op.amount <= 0 ? Math.Max(0, unit.mp + op.amount) : Math.Clamp(unit.mp + op.amount, 0, unit.maxMp);
                    Emit("resource", entry.source, unit.id, unit.mp - before, unit.x, unit.y, op.resource);
                }
                else if (op.kind == "status") Status(unit, op, entry.source);
                else if (op.kind == "removeStatus") Remove(unit, op.statusId, entry.source);
                else if (op.kind is "move" or "displace")
                {
                    int x = op.kind == "move" ? op.x : unit.x + op.dx, y = op.kind == "move" ? op.y : unit.y + op.dy;
                    // Displacement checks every crossed cell, so it cannot jump through a wall.
                    int distance = Math.Abs(x - unit.x) + Math.Abs(y - unit.y);
                    bool allowed = op.kind == "move" || op.dx == 0 || op.dy == 0;
                    if (op.kind == "displace") for (int i = 1; i <= distance; i++) allowed &= Walkable(unit.x + Math.Sign(op.dx) * i, unit.y + Math.Sign(op.dy) * i, unit);
                    if (allowed && Walkable(x, y, unit)) { unit.x = x; unit.y = y; Emit(op.kind, entry.source, unit.id, distance, x, y); }
                    else Emit("blocked", entry.source, unit.id, 0, unit.x, unit.y);
                }
                if (rules.reactions.Count > 0)
                {
                    var targetTags = unit.tags.Concat(unit.statuses.Select(status => status.id))
                        .Concat(unit.statuses.SelectMany(status => status.tags))
                        .Concat(state.hazards.Where(hazard => hazard.x == unit.x && hazard.y == unit.y).Select(hazard => hazard.tag))
                        .ToHashSet(StringComparer.Ordinal);
                    var triggers = new HashSet<string>(StringComparer.Ordinal) { op.tag };
                    foreach (var hazard in state.hazards.Where(hazard => hazard.x == unit.x && hazard.y == unit.y)) triggers.Add(hazard.tag);
                    foreach (var rule in rules.reactions.OrderBy(rule => rule.priority).ThenBy(rule => rule.id, StringComparer.Ordinal))
                    {
                        if (rule.targetKind != "unit" || rule.trigger != "effect" || !rule.triggerTags.Any(triggers.Contains) || !rule.requiredTargetTags.All(targetTags.Contains) || rule.excludedTargetTags.Any(targetTags.Contains)
                            || !reactions.Add(rule.id + ":" + unit.id)) continue;
                        foreach (string tag in rule.removeTags)
                        {
                            Remove(unit, tag, entry.source);
                            unit.tags = unit.tags.Where(value => value != tag).ToArray();
                        }
                        // Later priority rules see consumed tags rather than the initial snapshot.
                        targetTags = unit.tags.Concat(unit.statuses.Select(status => status.id))
                            .Concat(unit.statuses.SelectMany(status => status.tags))
                            .Concat(state.hazards.Where(hazard => hazard.x == unit.x && hazard.y == unit.y).Select(hazard => hazard.tag))
                            .ToHashSet(StringComparer.Ordinal);
                        Emit("reaction", entry.source, unit.id, 0, unit.x, unit.y, rule.id);
                        foreach (var operation in rule.operations)
                            queue.Enqueue((operation, entry.source, unit.id, unit.x, unit.y));
                    }
                }
                else
                {
                    bool water = rules.extinguishTags.Contains(op.tag) || state.hazards.Any(h => h.x == unit.x && h.y == unit.y && rules.extinguishTags.Contains(h.tag));
                    if (water) Remove(unit, rules.burningStatus, entry.source);
                    bool oil = unit.tags.Contains(rules.fuelTag) || unit.statuses.Any(s => s.id == rules.fuelTag) || state.hazards.Any(h => h.x == unit.x && h.y == unit.y && h.tag == rules.fuelTag);
                    if (!water && oil && rules.ignitionTags.Contains(op.tag) && reactions.Add("ignite:" + unit.id))
                    { Remove(unit, rules.fuelTag, entry.source); Status(unit, new() { statusId = rules.burningStatus, duration = rules.burningDuration, strength = rules.burningStrength }, entry.source); }
                }
            }
            foreach (var obj in state.effectObjects.Where(o => !o.destroyed && (op.area ? Math.Max(0, Math.Max(o.x - entry.x, entry.x - (o.x + o.width - 1))) + Math.Max(0, Math.Max(o.y - entry.y, entry.y - (o.y + o.height - 1))) <= Math.Max(0, op.radius) : o.id == targetId)).OrderBy(o => o.id, StringComparer.Ordinal))
            {
                if (op.kind is not ("damage" or "object")) continue;
                if (rules.reactions.Count > 0 && !obj.tags.Contains("destructible")) continue;
                int objectDamage = Math.Min(obj.hp, Math.Max(0, op.amount));
                obj.hp -= objectDamage;
                Emit("objectDamaged", entry.source, obj.id, objectDamage, obj.x, obj.y, op.tag);
                ObjectReactions(obj, "effect", op.tag, entry.source);
                if (obj.hp > 0) continue;
                obj.destroyed = true; obj.blocksMovement = false; obj.blocksSight = false;
                state.props = state.props.Where(p => p.id != obj.propId).ToArray();
                state.obstacles = state.obstacles.Where(p =>
                    !(p.x >= obj.x && p.x < obj.x + obj.width && p.y >= obj.y && p.y < obj.y + obj.height)
                    || state.tiles.Length == state.width * state.height && state.tiles[p.y * state.width + p.x] != "."
                    || state.effectObjects.Any(other => !other.destroyed && other.blocksMovement && p.x >= other.x && p.x < other.x + other.width && p.y >= other.y && p.y < other.y + other.height)).ToArray();
                Emit("objectDestroyed", entry.source, obj.id, 0, obj.x, obj.y);
                ObjectReactions(obj, "destroyed", op.tag, entry.source);
                if (rules.reactions.Count == 0 && obj.tags.Contains(rules.explosiveTag) && reactions.Add("explode:" + obj.id))
                {
                    Emit("explosion", entry.source, obj.id, rules.explosionDamage, obj.x, obj.y, "explosion");
                    queue.Enqueue((new() { kind = "damage", area = true, radius = Math.Clamp(rules.explosionRadius, 0, 32), amount = Math.Max(0, rules.explosionDamage), tag = "explosion" }, obj.id, "", obj.x, obj.y));
                }
            }
        }
        if (queue.Count > 0) { result.reason = "Reaction limit exceeded."; result.state = Codec.Read<Battle>(Codec.Write(source)); result.events.Clear(); return result; }
        if (request.operations.Any(operation => operation.kind == "tick"))
        {
            foreach (var hazard in state.hazards.Where(hazard => hazard.duration > 0)) hazard.duration--;
            state.hazards.RemoveAll(hazard => hazard.duration == 0);
        }
        state.effectEvents = result.events;
        result.valid = true;
        return result;
    }
}
