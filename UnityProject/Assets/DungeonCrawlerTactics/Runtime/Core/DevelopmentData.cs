using System;
namespace DungeonCrawlerTactics
{
    [Serializable]
    public sealed class DevelopmentDef
    {
        public string description;
        public int pointsPerLevel = 3;
        public StatDefinition[] stats = new StatDefinition[0];
        public SkillProgressionDef practice = new SkillProgressionDef();
        public RecipeDef[] recipes = new RecipeDef[0];
        public LootBoxDef[] lootBoxes = new LootBoxDef[0];
    }
    [Serializable]
    public sealed class StatDefinition
    {
        public string id, label, description;
        public int hpPerPoint, manaPerPoint, moveEvery, damageEvery, healEvery;
    }
    [Serializable]
    public sealed class SkillProgressionDef
    {
        public int[] useThresholds = new[] { 0, 3, 8 };
        public int damagePerRank = 1, healPerRank = 1, costReductionPerRank = 1;
        public AbilityRankProfile[] abilityProfiles = new AbilityRankProfile[0];
    }
    [Serializable]
    public sealed class ItemQuantity
    {
        public string itemId;
        public int count;
    }
    [Serializable]
    public sealed class RecipeDef
    {
        public string id, label, description;
        public ItemQuantity[] ingredients = new ItemQuantity[0], outputs = new ItemQuantity[0];
    }
    [Serializable]
    public sealed class LootBoxDef
    {
        public string id, label, description, achievementId;
        public bool fromVictory;
        public ItemQuantity[] rewards = new ItemQuantity[0];
    }
    [Serializable]
    public sealed class StatAllocationSave
    {
        public string unitId, statId;
        public int points;
    }
    [Serializable]
    public sealed class SkillPracticeSave
    {
        public string unitId, abilityId;
        public int uses;
    }
    [Serializable]
    public sealed class OwnedLootBoxSave
    {
        public string id, definitionId, sourceId;
        public bool opened;
    }
    [Serializable]
    public sealed class DevelopmentSave
    {
        public int version = 1;
        public StatAllocationSave[] allocated = new StatAllocationSave[0];
        public SkillPracticeSave[] practice = new SkillPracticeSave[0];
        public OwnedLootBoxSave[] lootBoxes = new OwnedLootBoxSave[0];
    }
    [Serializable]
    public sealed class CrawlerDevelopmentView
    {
        public string unitId;
        public int unspentPoints, maxSkillRank;
        public StatAllocationSave[] allocated = new StatAllocationSave[0];
    }
    [Serializable]
    public sealed class SkillPracticeView
    {
        public string unitId, abilityId;
        public string description, canonNotes;
        public string[] sourceUrls = new string[0];
        public int cost, range;
        public int uses, rank, maxRank, nextRankUses, damageBonus, healBonus, costReduction;
        public bool atCap;
        public SkillRankView[] ranks;
        public AbilityCastModeView[] castModes = new AbilityCastModeView[0];
    }
    [Serializable]
    public sealed class RecipeView
    {
        public string id, label, description, disabledReason;
        public ItemQuantity[] ingredients, outputs;
        public bool enabled;
    }
    [Serializable]
    public sealed class OwnedLootBoxView
    {
        public string id, label, description, sourceId;
        public bool opened, enabled;
        public ItemQuantity[] rewards;
    }
    [Serializable]
    public sealed class DevelopmentForecast
    {
        public string unitId, statId;
        public int points, beforeHp, afterHp, beforeMana, afterMana, beforeMove, afterMove, beforeDamageBonus, afterDamageBonus, beforeHealBonus, afterHealBonus;
    }
    [Serializable]
    public sealed class DevelopmentView
    {
        public bool available, canConfirm;
        public string description;
        public StatDefinition[] stats;
        public CrawlerDevelopmentView[] crawlers;
        public SkillPracticeView[] practice;
        public SkillRankCatalogView[] rankCatalog;
        public RecipeView[] recipes;
        public OwnedLootBoxView[] lootBoxes;
        public DevelopmentForecast forecast;
    }
    // Optional per-command modifiers are applied by the same pure resolver in previews and commits.
    public sealed class ActionModifiers
    {
        public int damageBonus, healBonus, costReduction;
        public bool hasCastMode; public int castModeCost, castModeDamageBonus;
        public int rangeBonus, pushBonus, summonHpBonus, summonMoveBonus, summonRoundsBonus;
        public string[] addTags = new string[0], removeTags = new string[0];
        public TagReplacementDef[] tagReplacements = new TagReplacementDef[0];
    }
}
