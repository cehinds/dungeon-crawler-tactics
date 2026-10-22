using System;
using System.Collections.Generic;

namespace DungeonCrawlerTactics
{
    public sealed class EntityState
    {
        public string Id; public string ClassId; public string Team;
        public bool IsTile; public int X; public int Y;
        public int Hp; public int MaxHp; public int Energy;
        public readonly HashSet<string> Tags = new HashSet<string>(StringComparer.Ordinal);
        public readonly HashSet<string> Immunities = new HashSet<string>(StringComparer.Ordinal);
        public EntityState Clone()
        {
            EntityState copy = new EntityState { Id = Id, ClassId = ClassId, Team = Team, IsTile = IsTile, X = X, Y = Y, Hp = Hp, MaxHp = MaxHp, Energy = Energy };
            copy.Tags.UnionWith(Tags); copy.Immunities.UnionWith(Immunities); return copy;
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
        internal ActionResult(BattleState state, List<string> log) { State = state; Log = log.ToArray(); }
    }
    // This kernel is a pure state transition. Callers explicitly replace their state after Execute.
    public sealed class RulesEngine
    {
        private readonly Catalog catalog;
        private readonly int maxEvents;
        private sealed class RuleEvent { public string[] Tags; public EffectDef[] Effects; public string Label; }
        public RulesEngine(Catalog catalog, int maxEvents = 64)
        {
            if (catalog == null) throw new ArgumentNullException(nameof(catalog));
            if (maxEvents < 1) throw new ArgumentOutOfRangeException(nameof(maxEvents));
            this.catalog = catalog; this.maxEvents = maxEvents;
        }
        public ActionResult Preview(BattleState state, string actorId, string abilityId, string targetId) { return Execute(state, actorId, abilityId, targetId); }
        public ActionResult Execute(BattleState state, string actorId, string abilityId, string targetId)
        { return Resolve(state, actorId, abilityId, targetId, true); }
        // Inventory and activation ownership are enforced by GameSession. Item definitions grant their linked ability.
        public ActionResult ExecuteItem(BattleState state, string actorId, string itemId, string targetId)
        {
            ItemDef item;
            if (itemId == null || !catalog.Items.TryGetValue(itemId, out item)) throw new ArgumentException("Unknown item.");
            return Resolve(state, actorId, item.abilityId, targetId, false);
        }
        private ActionResult Resolve(BattleState state, string actorId, string abilityId, string targetId, bool requireGrant)
        {
            ValidateState(state);
            EntityState actor; EntityState target; AbilityDef ability;
            if (actorId == null || !state.Entities.TryGetValue(actorId, out actor) || actor.IsTile || actor.Hp == 0) throw new ArgumentException("Actor must be a living unit.");
            if (targetId == null || !state.Entities.TryGetValue(targetId, out target)) throw new ArgumentException("Unknown target.");
            if (abilityId == null || !catalog.Abilities.TryGetValue(abilityId, out ability)) throw new ArgumentException("Unknown ability.");
            ClassDef actorClass = catalog.Classes[actor.ClassId];
            if (requireGrant && Array.IndexOf(actorClass.abilityIds, abilityId) < 0) throw new ArgumentException("Actor class does not grant ability.");
            bool validTarget = ability.target == "tile" ? target.IsTile : !target.IsTile && target.Hp > 0 &&
                (ability.target == "self" ? actorId == targetId : ability.target == "ally" ? target.Team == actor.Team : target.Team != actor.Team);
            if (!validTarget) throw new ArgumentException("Invalid target for ability.");
            long distance = Math.Abs((long)actor.X - target.X) + Math.Abs((long)actor.Y - target.Y);
            if (distance > ability.range || actor.Energy < ability.cost) throw new ArgumentException("Target out of range or insufficient energy.");
            BattleState next = state.Clone(); actor = next.Entities[actorId]; target = next.Entities[targetId]; actor.Energy -= ability.cost;
            List<string> log = new List<string>();
            Queue<RuleEvent> queue = new Queue<RuleEvent>();
            HashSet<string> fired = new HashSet<string>(StringComparer.Ordinal);
            queue.Enqueue(new RuleEvent { Tags = ability.incomingTags, Effects = ability.effects, Label = ability.id });
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
                Apply(target, current.Effects); log.Add(current.Label);
                foreach (ReactionDef rule in matched)
                {
                    // Earlier rules can consume a prerequisite and suppress later rules.
                    if (!rule.target.Matches(target.Tags)) continue;
                    fired.Add(rule.id);
                    foreach (string tag in rule.consumeTags) target.Tags.Remove(tag);
                    queue.Enqueue(new RuleEvent { Tags = rule.emitTags, Effects = rule.effects, Label = rule.id });
                }
            }
            return new ActionResult(next, log);
        }
        private static void Apply(EntityState target, EffectDef[] effects)
        {
            foreach (EffectDef effect in effects)
            {
                switch (effect.op)
                {
                    case "Damage": if (!target.IsTile) target.Hp = (int)Math.Max(0L, (long)target.Hp - effect.amount); break;
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
