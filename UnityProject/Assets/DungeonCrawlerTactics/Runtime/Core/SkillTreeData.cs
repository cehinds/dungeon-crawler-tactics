using System;
namespace DungeonCrawlerTactics
{
    [Serializable]
    public sealed class SkillTreeDef
    {
        public string id, rosterId, classId, label, description; public SkillNodeDef[] nodes = new SkillNodeDef[0];
    }
    [Serializable]
    public sealed class SkillNodeDef
    {
        public string id, label, description; public int level = 1, pointCost = 1, hpBonus, manaBonus, moveBonus, damageBonus, healBonus; public string[] prerequisiteIds = new string[0], abilityIds = new string[0];
    }
    [Serializable]
    public sealed class SkillTreeSave
    {
        public int version = 1; public string[] unlockedIds = new string[0];
    }
    [Serializable]
    public sealed class SkillNodeView
    {
        public string id, unitId, label, description, disabledReason; public int level, pointCost, hpBonus, manaBonus, moveBonus, damageBonus, healBonus; public string[] prerequisiteIds, abilityIds; public bool unlocked, enabled;
    }
    [Serializable]
    public sealed class CrawlerSkillTreeView
    {
        public string id, rosterId, classId, label, description; public bool isClassTree; public int unspentPoints; public SkillNodeView[] nodes;
    }
    [Serializable]
    public sealed class SkillTreeForecast
    {
        public string nodeId, unitId; public int beforeHp, afterHp, beforeMana, afterMana, beforeMove, afterMove, beforeDamageBonus, afterDamageBonus, beforeHealBonus, afterHealBonus; public string[] abilityIds;
    }
    [Serializable]
    public sealed class SkillTreeView
    {
        public bool available, canConfirm; public CrawlerSkillTreeView[] trees; public CrawlerSkillTreeView[] classTrees; public SkillTreeForecast forecast;
    }
}
