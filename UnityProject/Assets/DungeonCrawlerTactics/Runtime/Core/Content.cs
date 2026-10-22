using System;
using System.Collections.Generic;
using System.Text.RegularExpressions;

namespace DungeonCrawlerTactics
{
    // Public fields are intentional: this boundary is shared by JsonUtility and console JSON loading.
    [Serializable] public sealed class Content
    {
        public int schemaVersion;
        public TagDef[] tags = new TagDef[0];
        public ClassDef[] classes = new ClassDef[0];
        public AbilityDef[] abilities = new AbilityDef[0];
        public ReactionDef[] reactions = new ReactionDef[0];
        public ItemDef[] items = new ItemDef[0];
    }
    [Serializable] public sealed class TagDef { public string id; public string label; }
    [Serializable] public sealed class ClassDef { public string id; public string label; public string[] abilityIds = new string[0]; }
    [Serializable] public sealed class ItemDef { public string id; public string label; public string abilityId; }
    [Serializable] public sealed class EffectDef { public string op; public int amount; public string tag; }
    [Serializable] public sealed class TagQuery
    {
        public string[] all = new string[0];
        public string[] any = new string[0];
        public string[] none = new string[0];
        public bool Matches(HashSet<string> tags)
        {
            foreach (string tag in all) if (!tags.Contains(tag)) return false;
            foreach (string tag in none) if (tags.Contains(tag)) return false;
            if (any.Length == 0) return true;
            foreach (string tag in any) if (tags.Contains(tag)) return true;
            return false;
        }
    }
    [Serializable] public sealed class AbilityDef
    {
        public string id; public string label; public string target;
        public int range; public int cost;
        public string[] incomingTags = new string[0];
        public EffectDef[] effects = new EffectDef[0];
    }
    [Serializable] public sealed class ReactionDef
    {
        public string id; public int priority;
        // A reaction may prevent this much damage from its triggering event, before HP changes.
        public int damageReduction;
        public TagQuery incoming = new TagQuery();
        public TagQuery target = new TagQuery();
        public string[] consumeTags = new string[0];
        public EffectDef[] effects = new EffectDef[0];
        public string[] emitTags = new string[0];
    }

    public sealed class Catalog
    {
        public readonly Dictionary<string, AbilityDef> Abilities = new Dictionary<string, AbilityDef>(StringComparer.Ordinal);
        public readonly Dictionary<string, ClassDef> Classes = new Dictionary<string, ClassDef>(StringComparer.Ordinal);
        public readonly Dictionary<string, ItemDef> Items = new Dictionary<string, ItemDef>(StringComparer.Ordinal);
        public readonly List<ReactionDef> Reactions = new List<ReactionDef>();
        private readonly HashSet<string> tags = new HashSet<string>(StringComparer.Ordinal);
        public Catalog(Content content)
        {
            if (content == null || content.schemaVersion != 1) throw new ArgumentException("Expected content schemaVersion 1.");
            Require(content.tags != null && content.classes != null && content.abilities != null && content.reactions != null && content.items != null, "Content arrays cannot be null.");
            foreach (TagDef t in content.tags) { Require(t != null && ValidId(t.id) && tags.Add(t.id), "Invalid or duplicate tag."); }
            foreach (AbilityDef a in content.abilities)
            {
                Require(a != null && ValidId(a.id) && !Abilities.ContainsKey(a.id), "Invalid or duplicate ability.");
                Require(a.target == "self" || a.target == "ally" || a.target == "enemy" || a.target == "tile", "Invalid ability target: " + a.id);
                Require(a.range >= 0 && a.cost >= 0, "Negative range/cost: " + a.id);
                CheckTags(a.incomingTags); CheckEffects(a.effects); Abilities.Add(a.id, a);
            }
            foreach (ClassDef c in content.classes)
            {
                Require(c != null && ValidId(c.id) && !Classes.ContainsKey(c.id) && c.abilityIds != null, "Invalid or duplicate class.");
                foreach (string id in c.abilityIds) Require(id != null && Abilities.ContainsKey(id), "Unknown class ability: " + id);
                Classes.Add(c.id, c);
            }
            HashSet<string> ids = new HashSet<string>(StringComparer.Ordinal);
            foreach (ReactionDef r in content.reactions)
            {
                Require(r != null && ValidId(r.id) && ids.Add(r.id), "Invalid or duplicate reaction.");
                Require(r.damageReduction >= 0, "Reaction damage reduction cannot be negative.");
                CheckQuery(r.incoming); CheckQuery(r.target); CheckTags(r.consumeTags); CheckTags(r.emitTags); CheckEffects(r.effects); Reactions.Add(r);
            }
            Reactions.Sort((a, b) => { int priority = b.priority.CompareTo(a.priority); return priority != 0 ? priority : StringComparer.Ordinal.Compare(a.id, b.id); });
            ids.Clear();
            foreach (ItemDef item in content.items)
            {
                Require(item != null && ValidId(item.id) && ids.Add(item.id) && item.abilityId != null && Abilities.ContainsKey(item.abilityId), "Invalid item or unknown item ability.");
                Items.Add(item.id, item);
            }
        }
        public bool HasTag(string id) { return id != null && tags.Contains(id); }
        private static bool ValidId(string id) { return id != null && Regex.IsMatch(id, @"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$"); }
        private static void Require(bool valid, string message) { if (!valid) throw new ArgumentException(message); }
        private void CheckTags(string[] values) { Require(values != null, "Tag arrays cannot be null."); foreach (string t in values) Require(HasTag(t), "Unknown tag: " + t); }
        private void CheckQuery(TagQuery q) { Require(q != null, "Missing tag query."); CheckTags(q.all); CheckTags(q.any); CheckTags(q.none); }
        private void CheckEffects(EffectDef[] effects)
        {
            Require(effects != null, "Effects cannot be null.");
            foreach (EffectDef e in effects)
            {
                Require(e != null, "Null effect.");
                Require(e.amount >= 0, "Effect amount cannot be negative.");
                if (e.op != "Damage" && e.op != "Heal")
                    Require((e.op == "AddTag" || e.op == "RemoveTag") && HasTag(e.tag), "Invalid operation or tag.");
            }
        }
    }
}
