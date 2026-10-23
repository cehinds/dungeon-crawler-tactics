using System;
using System.Collections.Generic;
namespace DungeonCrawlerTactics
{
    public sealed partial class GameSession
    {
        private readonly List<string> unlockedSkillNodes = new List<string>();
        private GameCommand pendingSkillNode;
        private bool IsClassTree(SkillTreeDef tree) { return !string.IsNullOrEmpty(tree.classId); }
        private string SkillKey(SkillTreeDef tree, SkillNodeDef node, string owner) { return IsClassTree(tree) ? owner + "::" + node.id : node.id; }
        private string SelectedTreeClass(string owner, string selectedClassId = null)
        {
            if (!string.IsNullOrEmpty(selectedClassId)) return selectedClassId;
            RosterView member;
            return roster.TryGetValue(owner, out member) ? member.classId : Definition(owner).classId;
        }
        private IEnumerable<SkillTreeDef> AllSkillTrees()
        {
            foreach (SkillTreeDef tree in data.skillTrees) yield return tree;
            foreach (SkillTreeDef tree in data.classSkillTrees) yield return tree;
        }
        private IEnumerable<SkillTreeDef> ActiveSkillTrees(string owner, string selectedClassId = null)
        {
            string classId = SelectedTreeClass(owner, selectedClassId);
            foreach (SkillTreeDef tree in AllSkillTrees())
                if (IsClassTree(tree) ? tree.classId == classId : tree.rosterId == owner) yield return tree;
        }
        private SkillNodeDef TreeNode(string id, out SkillTreeDef tree)
        {
            foreach (SkillTreeDef definition in AllSkillTrees())
            {
                SkillNodeDef node = Array.Find(definition.nodes, n => n.id == id);
                if (node != null) { tree = definition; return node; }
            }
            tree = null;
            throw new ArgumentException("Unknown skill-tree node.");
        }
        private SkillNodeDef SavedTreeNode(string key, out SkillTreeDef tree, out string owner)
        {
            Require(!string.IsNullOrEmpty(key), "Invalid learned skill key.");
            int separator = key.IndexOf("::", StringComparison.Ordinal);
            string id = separator < 0 ? key : key.Substring(separator + 2);
            SkillNodeDef node = TreeNode(id, out tree);
            if (IsClassTree(tree))
            {
                Require(separator > 0, "Class skills require a crawler owner.");
                owner = key.Substring(0, separator);
                RosterDef member = Definition(owner);
                Require(member != null && member.deployable && key == SkillKey(tree, node, owner), "Invalid class-skill owner.");
            }
            else
            {
                Require(separator < 0, "Personal skill has an invalid owner prefix.");
                owner = tree.rosterId;
            }
            return node;
        }
        private int SkillPointsSpent(SkillTreeDef tree, string owner, List<string> unlocked)
        {
            int count = 0;
            foreach (SkillNodeDef node in tree.nodes)
                if (unlocked.Contains(SkillKey(tree, node, owner))) count += node.pointCost;
            return count;
        }
        private int SkillPointBudget(SkillTreeDef tree, int experience)
        {
            int level = LevelAt(experience);
            if (!IsClassTree(tree)) return level;
            // One point per authored tier keeps the two branches a meaningful choice.
            HashSet<int> earnedTiers = new HashSet<int>();
            foreach (SkillNodeDef node in tree.nodes)
                if (node.level <= level) earnedTiers.Add(node.level);
            return earnedTiers.Count;
        }
        private string NodeDisabledReason(SkillTreeDef tree, SkillNodeDef node, string owner, List<string> unlocked, int experience, bool safeRoom)
        {
            RosterDef member = Definition(owner);
            if (member == null || !member.deployable || (!IsClassTree(tree) && tree.rosterId != owner)) return "This node belongs to another crawler.";
            if (IsClassTree(tree) && tree.classId != SelectedTreeClass(owner)) return "Select this class before learning its skills.";
            if (unlocked.Contains(SkillKey(tree, node, owner))) return "Already learned.";
            if (!safeRoom) return "Learn skills in the safe room.";
            if (IsClassTree(tree) && !JourneyAllocationUnlocked) return "Class skills unlock on floor 3.";
            if (LevelAt(experience) < node.level) return "Requires party level " + node.level + ".";
            foreach (string parent in node.prerequisiteIds)
                if (!unlocked.Contains(IsClassTree(tree) ? owner + "::" + parent : parent)) return "Learn prerequisite skills first.";
            if (SkillPointsSpent(tree, owner, unlocked) + node.pointCost > SkillPointBudget(tree, experience)) return "Not enough unspent skill points.";
            return "";
        }
        private List<string> ProposedSkillNodes(GameCommand command)
        {
            SkillTreeDef tree;
            SkillNodeDef node = TreeNode(command.nodeId, out tree);
            string reason = NodeDisabledReason(tree, node, command.unitId, unlockedSkillNodes, xp, screen == "camp");
            Require(reason == "", reason);
            List<string> next = new List<string>(unlockedSkillNodes);
            next.Add(SkillKey(tree, node, command.unitId));
            return next;
        }
        private void PreviewSkillNode(GameCommand command)
        {
            pendingSkillNode = null;
            ProposedSkillNodes(command);
            pendingSkillNode = new GameCommand { unitId = command.unitId, nodeId = command.nodeId };
            message = "Review the skill and stat changes, then confirm or cancel.";
        }
        private void ConfirmSkillNode()
        {
            Require(pendingSkillNode != null, "Preview a skill-tree node first.");
            List<string> next = ProposedSkillNodes(pendingSkillNode);
            string owner = pendingSkillNode.unitId, node = pendingSkillNode.nodeId;
            unlockedSkillNodes.Clear(); unlockedSkillNodes.AddRange(next); pendingSkillNode = null;
            RefreshRosterStats(false);
            presentationEvents.Add(new PresentationEvent { type = "skill_node_learned", actorId = owner, tag = node });
            message = "Skill learned. Granted abilities are ready; rest to fill increased HP or mana caps.";
        }
        private void ApplyTreeStats(ClassStats stats, string owner, List<string> unlocked)
        {
            foreach (SkillTreeDef tree in ActiveSkillTrees(owner, stats.classId))
                foreach (SkillNodeDef node in tree.nodes)
                    if (unlocked.Contains(SkillKey(tree, node, owner))) { stats.hp += node.hpBonus; stats.energy += node.manaBonus; stats.move += node.moveBonus; }
        }
        private ActionModifiers TreeModifiers(string owner, List<string> unlocked)
        {
            ActionModifiers result = new ActionModifiers();
            foreach (SkillTreeDef tree in ActiveSkillTrees(owner))
                foreach (SkillNodeDef node in tree.nodes)
                    if (unlocked.Contains(SkillKey(tree, node, owner))) { result.damageBonus += node.damageBonus; result.healBonus += node.healBonus; }
            return result;
        }
        private void AddTreeGrants(string owner, List<string> unlocked, List<string> grants, string selectedClassId = null)
        {
            foreach (SkillTreeDef tree in ActiveSkillTrees(owner, selectedClassId))
                foreach (SkillNodeDef node in tree.nodes)
                    if (unlocked.Contains(SkillKey(tree, node, owner)))
                        foreach (string ability in node.abilityIds) if (!grants.Contains(ability)) grants.Add(ability);
        }
        private SkillTreeForecast SkillNodeForecast()
        {
            if (pendingSkillNode == null) return null;
            List<string> next = ProposedSkillNodes(pendingSkillNode);
            string owner = pendingSkillNode.unitId;
            SkillTreeDef tree; SkillNodeDef node = TreeNode(pendingSkillNode.nodeId, out tree);
            ClassStats before = PlayerStats(owner, roster[owner].classId), after = PlayerStats(owner, roster[owner].classId, xp, equipped);
            ApplyAllocatedStats(after, owner, allocations); ApplyTreeStats(after, owner, next); ApplyModes(after, owner, roster[owner].stanceId, roster[owner].formId);
            ActionModifiers oldModifiers = TreeModifiers(owner, unlockedSkillNodes), newModifiers = TreeModifiers(owner, next);
            return new SkillTreeForecast { nodeId = node.id, unitId = owner, beforeHp = before.hp, afterHp = after.hp, beforeMana = before.energy, afterMana = after.energy, beforeMove = before.move, afterMove = after.move, beforeDamageBonus = oldModifiers.damageBonus, afterDamageBonus = newModifiers.damageBonus, beforeHealBonus = oldModifiers.healBonus, afterHealBonus = newModifiers.healBonus, abilityIds = (string[])node.abilityIds.Clone() };
        }
        private CrawlerSkillTreeView TreeView(SkillTreeDef tree, string owner)
        {
            List<SkillNodeView> nodes = new List<SkillNodeView>();
            foreach (SkillNodeDef node in tree.nodes)
            {
                string reason = NodeDisabledReason(tree, node, owner, unlockedSkillNodes, xp, screen == "camp");
                nodes.Add(new SkillNodeView { id = node.id, unitId = owner, label = node.label, description = node.description, disabledReason = reason, level = node.level, pointCost = node.pointCost, prerequisiteIds = (string[])node.prerequisiteIds.Clone(), abilityIds = (string[])node.abilityIds.Clone(), hpBonus = node.hpBonus, manaBonus = node.manaBonus, moveBonus = node.moveBonus, damageBonus = node.damageBonus, healBonus = node.healBonus, unlocked = unlockedSkillNodes.Contains(SkillKey(tree, node, owner)), enabled = reason == "" });
            }
            return new CrawlerSkillTreeView { id = tree.id, rosterId = owner, classId = tree.classId, isClassTree = IsClassTree(tree), label = tree.label, description = tree.description, unspentPoints = SkillPointBudget(tree, xp) - SkillPointsSpent(tree, owner, unlockedSkillNodes), nodes = nodes.ToArray() };
        }
        private void PopulateSkillTree(GameView view)
        {
            List<CrawlerSkillTreeView> trees = new List<CrawlerSkillTreeView>(), classTrees = new List<CrawlerSkillTreeView>();
            foreach (SkillTreeDef tree in data.skillTrees) trees.Add(TreeView(tree, tree.rosterId));
            foreach (RosterDef member in data.roster)
                if (member.deployable)
                    foreach (SkillTreeDef tree in data.classSkillTrees)
                        if (tree.classId == SelectedTreeClass(member.id)) classTrees.Add(TreeView(tree, member.id));
            view.skillTree = new SkillTreeView { available = screen == "camp", canConfirm = pendingSkillNode != null, trees = trees.ToArray(), classTrees = classTrees.ToArray(), forecast = SkillNodeForecast() };
        }
        private SkillTreeSave CaptureSkillTree() { return new SkillTreeSave { unlockedIds = unlockedSkillNodes.ToArray() }; }
        private List<string> ValidateSkillTree(GameSave save)
        {
            if (save.skillTree == null) return new List<string>();
            int maximum = 0;
            foreach (SkillTreeDef tree in AllSkillTrees()) maximum += tree.nodes.Length * (IsClassTree(tree) ? data.roster.Length : 1);
            Require(save.skillTree.version == 1 && save.skillTree.unlockedIds != null && save.skillTree.unlockedIds.Length <= maximum, "Invalid skill-tree checkpoint.");
            List<string> result = new List<string>();
            foreach (string key in save.skillTree.unlockedIds)
            {
                SkillTreeDef tree; string owner; SkillNodeDef node = SavedTreeNode(key, out tree, out owner);
                Require(!result.Contains(key) && LevelAt(save.xp) >= node.level, "Duplicate or level-locked skill node.");
                Require(!IsClassTree(tree) || save.journey == null || save.journey.floorIndex >= 2, "Class skills are unavailable before floor 3.");
                result.Add(key);
            }
            foreach (string key in result)
            {
                SkillTreeDef tree; string owner; SkillNodeDef node = SavedTreeNode(key, out tree, out owner);
                foreach (string parent in node.prerequisiteIds) Require(result.Contains(IsClassTree(tree) ? owner + "::" + parent : parent), "Learned skill is missing its prerequisite.");
                Require(SkillPointsSpent(tree, owner, result) <= SkillPointBudget(tree, save.xp), "Learned skills exceed earned skill points.");
            }
            return result;
        }
        private void CommitSkillTree(List<string> next) { unlockedSkillNodes.Clear(); unlockedSkillNodes.AddRange(next); pendingSkillNode = null; }
    }
}
