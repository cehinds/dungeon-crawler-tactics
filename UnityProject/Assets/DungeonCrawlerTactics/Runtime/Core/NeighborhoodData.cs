using System;
namespace DungeonCrawlerTactics
{
    [Serializable] public sealed class NeighborhoodDef { public string id, label, description, sectorId; public ExplorationDef legacyExploration; public NeighborhoodInteractionDef[] interactions = new NeighborhoodInteractionDef[0]; public NeighborhoodChallengeDef[] challenges = new NeighborhoodChallengeDef[0]; }
    [Serializable] public sealed class NeighborhoodInteractionDef { public string id, pointId, label, description; public bool camp; public NeighborhoodOptionDef[] options = new NeighborhoodOptionDef[0]; }
    [Serializable] public sealed class NeighborhoodOptionDef { public string id, label, description, costItemId, rewardItemId, abilityId, clue; public int costCount, rewardCount, minimumRank = 1; }
    [Serializable] public sealed class NeighborhoodChallengeDef { public string id, label, description, interactionId, optionId, rewardItemId; public int rewardCount; }
    [Serializable] public sealed class NeighborhoodReceipt { public string interactionId, optionId, unitId; }
    [Serializable] public sealed class NeighborhoodSave { public int version = 1; public NeighborhoodReceipt[] receipts = new NeighborhoodReceipt[0]; public string[] challengeIds = new string[0]; public GameSave campaign; }
    [Serializable] public sealed class NeighborhoodOptionView { public string id, label, description, disabledReason, costItemId, rewardItemId, abilityId, clue; public int costCount, rewardCount, minimumRank; public string[] eligibleUnitIds = new string[0]; public bool enabled; }
    [Serializable] public sealed class NeighborhoodInteractionView { public string id, pointId, label, description; public bool camp, completed; public NeighborhoodOptionView[] options; }
    [Serializable] public sealed class NeighborhoodChallengeView { public string id, label, description, rewardItemId; public int rewardCount; public bool earned; }
    [Serializable] public sealed class NeighborhoodForecast { public string interactionId, optionId, label, description, costItemId, rewardItemId, clue; public int costCount, rewardCount, beforeCost, afterCost, beforeReward, afterReward; public string[] challengeIds = new string[0]; public InventoryEntry[] beforeItems, afterItems; }
    [Serializable] public sealed class NeighborhoodView { public string id, label, description; public bool canConfirm, standalone, active; public NeighborhoodInteractionView[] interactions; public NeighborhoodChallengeView[] challenges; public string[] clues; public NeighborhoodForecast forecast; }
}
