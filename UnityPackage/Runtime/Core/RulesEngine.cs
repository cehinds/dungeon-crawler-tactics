using System;
using System.Collections.Generic;

namespace DungeonCrawlerTactics
{
    public sealed class EntityState
    {
        public string DuplicateSourceId, DuplicateCasterId; public int DuplicateRounds, DuplicateMove; public string Id; public string ClassId; public string Team;
        public bool IsTile; public bool Blocked; public int X; public int Y;
        public int Hp; public int MaxHp; public int Energy;
        public readonly HashSet<string> GrantedAbilities = new HashSet<string>(StringComparer.Ordinal);
        public readonly HashSet<string> Tags = new HashSet<string>(StringComparer.Ordinal);
        public readonly HashSet<string> Immunities = new HashSet<string>(StringComparer.Ordinal);
        public EntityState Clone()
        {
            EntityState copy = new EntityState { DuplicateSourceId = DuplicateSourceId, DuplicateCasterId = DuplicateCasterId, DuplicateRounds = DuplicateRounds, DuplicateMove = DuplicateMove, Id = Id, ClassId = ClassId, Team = Team, IsTile = IsTile, Blocked = Blocked, X = X, Y = Y, Hp = Hp, MaxHp = MaxHp, Energy = Energy };
            copy.GrantedAbilities.UnionWith(GrantedAbilities); copy.Tags.UnionWith(Tags); copy.Immunities.UnionWith(Immunities); return copy;
        }
    }
    public sealed class BattleState
    {
        public readonly Dictionary<string, EntityState> Entities = new Dictionary<string, EntityState>(StringComparer.Ordinal);
        public BattleState Clone() { BattleState copy = new BattleState(); foreach (var pair in Entities) copy.Entities.Add(pair.Key, pair.Value.Clone()); return copy; }
    }
    public sealed class ActionResult
    {
        public BattleState State { get; private set; }
        public string[] Log { get; private set; }
        public PresentationEvent[] Events { get; private set; }
        internal ActionResult(BattleState state, List<string> log, List<PresentationEvent> events = null) { State = state; Log = log.ToArray(); Events = events == null ? new PresentationEvent[0] : events.ToArray(); }
    }
    // This kernel is a pure state transition. Callers explicitly replace their state after Execute.
    public sealed class RulesEngine
    {
        private readonly Catalog catalog;
        private readonly int maxEvents;
        private readonly Action<BattleState, EntityState, List<string>, List<PresentationEvent>> onEntry;
        private sealed class RuleEvent { public string[] Tags; public EffectDef[] Effects; public string Label; }
        public RulesEngine(Catalog catalog, int maxEvents = 64, Action<BattleState, EntityState, List<string>, List<PresentationEvent>> onEntry = null)
        {
            if (catalog == null) throw new ArgumentNullException(nameof(catalog));
            if (maxEvents < 1) throw new ArgumentOutOfRangeException(nameof(maxEvents));
            this.catalog = catalog; this.maxEvents = maxEvents; this.onEntry = onEntry;
        }
        public ActionResult Preview(BattleState state, string actorId, string abilityId, string targetId) { return Execute(state, actorId, abilityId, targetId); }
        public ActionResult Execute(BattleState state, string actorId, string abilityId, string targetId, ActionModifiers modifiers = null)
        { return Resolve(state, actorId, abilityId, targetId, true, modifiers); }
        // Inventory and activation ownership are enforced by GameSession. Item definitions grant their linked ability.
        public ActionResult ExecuteItem(BattleState state, string actorId, string itemId, string targetId)
        {
            ItemDef item;
            if (itemId == null || !catalog.Items.TryGetValue(itemId, out item)) throw new ArgumentException("Unknown item.");
            return Resolve(state, actorId, item.abilityId, targetId, false);
        }
        private ActionResult Resolve(BattleState state, string actorId, string abilityId, string targetId, bool requireGrant, ActionModifiers modifiers = null)
        {
            ValidateState(state);
            if (modifiers != null && (modifiers.damageBonus < 0 || modifiers.damageBonus > 100 || modifiers.healBonus < 0 || modifiers.healBonus > 100 || modifiers.costReduction < 0 || modifiers.costReduction > 100)) throw new ArgumentException("Action modifiers exceed bounded limits.");
            EntityState actor; EntityState target; AbilityDef ability;
            if (actorId == null || !state.Entities.TryGetValue(actorId, out actor) || actor.IsTile || actor.Hp == 0) throw new ArgumentException("Actor must be a living unit.");
            if (targetId == null || !state.Entities.TryGetValue(targetId, out target)) throw new ArgumentException("Unknown target.");
            if (abilityId == null || !catalog.Abilities.TryGetValue(abilityId, out ability)) throw new ArgumentException("Unknown ability.");
            ClassDef actorClass = catalog.Classes[actor.ClassId];
            if (requireGrant && Array.IndexOf(actorClass.abilityIds, abilityId) < 0 && !actor.GrantedAbilities.Contains(abilityId)) throw new ArgumentException("Actor class does not grant ability.");
            bool validTarget = ability.target == "tile" ? target.IsTile : !target.IsTile && target.Hp > 0 &&
                (ability.target == "self" ? actorId == targetId : ability.target == "ally" ? target.Team == actor.Team : target.Team != actor.Team);
            if (!validTarget) throw new ArgumentException("Invalid target for ability.");
            long distance = Math.Abs((long)actor.X - target.X) + Math.Abs((long)actor.Y - target.Y);
            int effectiveCost = Math.Max(0, ability.cost - (modifiers == null ? 0 : modifiers.costReduction));
            if (distance > ability.range || actor.Energy < effectiveCost) throw new ArgumentException("Target out of range or insufficient mana.");
            BattleState next = state.Clone(); actor = next.Entities[actorId]; target = next.Entities[targetId]; actor.Energy -= effectiveCost;
            List<string> log = new List<string>();
            List<PresentationEvent> events = new List<PresentationEvent>();
            events.Add(new PresentationEvent { type = "attack", actorId = actorId, targetId = targetId, abilityId = abilityId });
            Queue<RuleEvent> queue = new Queue<RuleEvent>();
            HashSet<string> fired = new HashSet<string>(StringComparer.Ordinal);
            EffectDef[] effectiveEffects = new EffectDef[ability.effects.Length];
            for (int i = 0; i < effectiveEffects.Length; i++) { EffectDef e = ability.effects[i]; effectiveEffects[i] = new EffectDef { op = e.op, tag = e.tag, summonHp = e.summonHp, summonMove = e.summonMove, summonRounds = e.summonRounds, amount = e.amount + (modifiers == null ? 0 : e.op == "Damage" ? modifiers.damageBonus : e.op == "Heal" ? modifiers.healBonus : 0) }; }
            queue.Enqueue(new RuleEvent { Tags = ability.incomingTags, Effects = effectiveEffects, Label = ability.id });
            int processed = 0;
            while (queue.Count > 0)
            {
                if (++processed > maxEvents) throw new InvalidOperationException("Reaction event budget exceeded; input state is unchanged.");
                RuleEvent current = queue.Dequeue();
                HashSet<string> incoming = new HashSet<string>(current.Tags, StringComparer.Ordinal);
                if (target.Immunities.Overlaps(incoming)) { log.Add(current.Label + ": immune"); continue; }
                // Snapshot eligibility before event effects: adding wet cannot retroactively satisfy this event.
                List<ReactionDef> matched = new List<ReactionDef>();
                foreach (ReactionDef rule in catalog.Reactions)
                    if (!fired.Contains(rule.id) && rule.incoming.Matches(incoming) && rule.target.Matches(target.Tags)) matched.Add(rule);
                // Defensive reactions resolve before damage, so protection can prevent lethal hits.
                // Their single budget is shared across every Damage effect in this event.
                long reduction = 0;
                bool damaging = Array.Exists(current.Effects, effect => effect.op == "Damage" && effect.amount > 0);
                foreach (ReactionDef rule in matched)
                {
                    if (rule.damageReduction == 0 || !damaging || !rule.target.Matches(target.Tags)) continue;
                    fired.Add(rule.id);
                    foreach (string tag in rule.consumeTags) if (target.Tags.Remove(tag)) events.Add(new PresentationEvent { type = "tag_remove", actorId = actorId, targetId = targetId, tag = tag });
                    events.Add(new PresentationEvent { type = "reaction", actorId = actorId, targetId = targetId, reactionId = rule.id, abilityId = abilityId });
                    reduction = Math.Min(int.MaxValue, reduction + rule.damageReduction);
                    queue.Enqueue(new RuleEvent { Tags = rule.emitTags, Effects = rule.effects, Label = rule.id });
                }
                foreach (EffectDef effect in current.Effects)
                {
                    int hp = target.Hp; bool had = effect.tag != null && target.Tags.Contains(effect.tag);
                    if (effect.op == "DuplicatePet")
                    {
                        DuplicatePet(next, actor, target, effect, abilityId, events); continue;
                    }
                    if (effect.op == "Teleport")
                    {
                        if (!target.IsTile || !Passable(next, target.X, target.Y, actorId)) throw new ArgumentException("Teleport destination is blocked or occupied.");
                        events.Add(new PresentationEvent { type = "teleport", actorId = actorId, targetId = actorId, abilityId = abilityId, fromX = actor.X, fromY = actor.Y, toX = target.X, toY = target.Y });
                        actor.X = target.X; actor.Y = target.Y; if (onEntry != null) onEntry(next, actor, log, events); continue;
                    }
                    if (effect.op == "Push")
                    {
                        if (target.IsTile) throw new ArgumentException("Push requires a unit target.");
                        int dx = target.X - actor.X, dy = target.Y - actor.Y;
                        if (Math.Abs(dx) >= Math.Abs(dy)) { dx = Math.Sign(dx); dy = 0; } else { dy = Math.Sign(dy); dx = 0; }
                        for (int step = 0; step < effect.amount && target.Hp > 0 && (dx != 0 || dy != 0); step++)
                        {
                            int nx = target.X + dx, ny = target.Y + dy; if (!Passable(next, nx, ny, targetId)) break;
                            events.Add(new PresentationEvent { type = "push", actorId = actorId, targetId = targetId, abilityId = abilityId, fromX = target.X, fromY = target.Y, toX = nx, toY = ny });
                            target.X = nx; target.Y = ny; if (onEntry != null) onEntry(next, target, log, events);
                        }
                        continue;
                    }
                    Apply(target, new[] { effect }, reduction);
                    if (effect.op == "Damage") { int prevented = (int)Math.Min(reduction, effect.amount); reduction -= prevented; if (prevented > 0) events.Add(new PresentationEvent { type = "guard", actorId = actorId, targetId = targetId, amount = prevented }); }
                    if (hp != target.Hp) events.Add(new PresentationEvent { type = target.Hp < hp ? "damage" : "heal", actorId = actorId, targetId = targetId, abilityId = abilityId, before = hp, after = target.Hp, amount = Math.Abs(target.Hp - hp) });
                    if (effect.tag != null && had != target.Tags.Contains(effect.tag)) events.Add(new PresentationEvent { type = had ? "tag_remove" : "tag_add", actorId = actorId, targetId = targetId, tag = effect.tag, abilityId = abilityId });
                }
                log.Add(current.Label);
                foreach (ReactionDef rule in matched)
                {
                    // Earlier rules can consume a prerequisite and suppress later rules.
                    if (rule.damageReduction > 0 || !rule.target.Matches(target.Tags)) continue;
                    fired.Add(rule.id);
                    foreach (string tag in rule.consumeTags) if (target.Tags.Remove(tag)) events.Add(new PresentationEvent { type = "tag_remove", actorId = actorId, targetId = targetId, tag = tag });
                    events.Add(new PresentationEvent { type = "reaction", actorId = actorId, targetId = targetId, reactionId = rule.id, abilityId = abilityId });
                    queue.Enqueue(new RuleEvent { Tags = rule.emitTags, Effects = rule.effects, Label = rule.id });
                }
            }
            return new ActionResult(next, log, events);
        }
        private void DuplicatePet(BattleState state, EntityState actor, EntityState target, EffectDef effect, string abilityId, List<PresentationEvent> events)
        {
            if (target.IsTile || target.Team != actor.Team || !target.Tags.Contains(effect.tag) || target.DuplicateSourceId != null) throw new ArgumentException("Choose a living allied pet, not a clockwork copy.");
            foreach (EntityState entity in state.Entities.Values) if (entity.DuplicateCasterId == actor.Id) throw new ArgumentException("This caster already has clockwork copies on the board.");
            List<EntityState> spaces = new List<EntityState>();
            foreach (EntityState tile in state.Entities.Values) if (tile.IsTile && Math.Abs(tile.X - target.X) + Math.Abs(tile.Y - target.Y) == 1 && Passable(state, tile.X, tile.Y, null)) spaces.Add(tile);
            spaces.Sort((a, b) => a.Y == b.Y ? a.X.CompareTo(b.X) : a.Y.CompareTo(b.Y));
            if (spaces.Count < effect.amount) throw new ArgumentException("Two open tiles adjacent to the pet are required.");
            for (int i = 0; i < effect.amount; i++)
            {
                EntityState copy = new EntityState { Id = "clockwork." + actor.Id + "." + i, ClassId = target.ClassId, Team = actor.Team, X = spaces[i].X, Y = spaces[i].Y, Hp = effect.summonHp, MaxHp = effect.summonHp, Energy = 0, DuplicateSourceId = target.Id, DuplicateCasterId = actor.Id, DuplicateRounds = effect.summonRounds, DuplicateMove = effect.summonMove };
                foreach (string grant in target.GrantedAbilities) if (catalog.Abilities[grant].cost == 0 && !Array.Exists(catalog.Abilities[grant].effects, e => e.op == "DuplicatePet")) copy.GrantedAbilities.Add(grant);
                foreach (string grant in catalog.Classes[target.ClassId].abilityIds) if (catalog.Abilities[grant].cost == 0 && !Array.Exists(catalog.Abilities[grant].effects, e => e.op == "DuplicatePet")) copy.GrantedAbilities.Add(grant);
                copy.Tags.Add("status.clockwork");
                state.Entities.Add(copy.Id, copy);
                events.Add(new PresentationEvent { type = "summon", actorId = actor.Id, targetId = copy.Id, abilityId = abilityId, tag = target.Id, toX = copy.X, toY = copy.Y });
                if (onEntry != null) onEntry(state, copy, new List<string>(), events);
            }
        }
        private static bool Passable(BattleState state, int x, int y, string actorId)
        {
            bool tile = false;
            foreach (EntityState entity in state.Entities.Values)
            {
                if (entity.X != x || entity.Y != y) continue;
                if (entity.IsTile) { if (entity.Blocked) return false; tile = true; }
                else if (entity.Id != actorId && entity.Hp > 0) return false;
            }
            return tile;
        }
        private static void Apply(EntityState target, EffectDef[] effects, long reduction)
        {
            foreach (EffectDef effect in effects)
            {
                switch (effect.op)
                {
                    case "Damage":
                        long prevented = Math.Min(reduction, effect.amount); reduction -= prevented;
                        if (!target.IsTile) target.Hp = (int)Math.Max(0L, (long)target.Hp - (effect.amount - prevented));
                        break;
                    case "Heal": if (!target.IsTile && target.Hp > 0) target.Hp = (int)Math.Min((long)target.MaxHp, (long)target.Hp + effect.amount); break;
                    case "AddTag": target.Tags.Add(effect.tag); break;
                    case "RemoveTag": target.Tags.Remove(effect.tag); break;
                }
            }
        }
        private void ValidateState(BattleState state)
        {
            if (state == null) throw new ArgumentNullException(nameof(state));
            foreach (var pair in state.Entities)
            {
                EntityState e = pair.Value;
                if (e == null || string.IsNullOrEmpty(e.Id) || pair.Key != e.Id || e.Hp < 0 || e.MaxHp < e.Hp || e.Energy < 0 ||
                    (!e.IsTile && (e.ClassId == null || !catalog.Classes.ContainsKey(e.ClassId) || string.IsNullOrEmpty(e.Team)))) throw new ArgumentException("Invalid battle entity: " + pair.Key);
                foreach (string tag in e.Tags) if (!catalog.HasTag(tag)) throw new ArgumentException("Unknown state tag: " + tag);
                foreach (string tag in e.Immunities) if (!catalog.HasTag(tag)) throw new ArgumentException("Unknown immunity: " + tag);
            }
        }
    }
}
