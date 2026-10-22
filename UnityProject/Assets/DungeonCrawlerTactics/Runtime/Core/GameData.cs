using System;

namespace DungeonCrawlerTactics
{
    [Serializable] public sealed class GameData
    {
        public int schemaVersion = 1;
        public string contentVersion;
        public int partySize = 4;
        public int energyPerRound = 3;
        public RosterDef[] roster = new RosterDef[0];
        public ClassStats[] classStats = new ClassStats[0];
        public EncounterDef[] encounters = new EncounterDef[0];
        public InventoryEntry[] startingInventory = new InventoryEntry[0];
        public RewardDef[] rewards = new RewardDef[0];
        public TagRuleDef[] tagRules = new TagRuleDef[0];
    }
    [Serializable] public sealed class RosterDef { public string id, label, classId; public bool selected; }
    [Serializable] public sealed class ClassStats { public string classId; public int hp = 30, energy = 10, move = 3; }
    [Serializable] public sealed class SpawnDef { public string id, label, classId; public int x, y, hp = 18, energy = 10, move = 2; public string[] tags = new string[0]; }
    [Serializable] public sealed class TileDef { public int x, y; public bool blocked; public string[] tags = new string[0]; }
    [Serializable] public sealed class EncounterDef
    {
        public string id, label, description;
        public int width = 10, height = 8, xp = 30;
        public ExplorationDef exploration;
        public CellView[] playerSpawns = new CellView[0];
        public TileDef[] tiles = new TileDef[0];
        public SpawnDef[] enemies = new SpawnDef[0];
    }
    [Serializable] public sealed class ExplorationDef
    {
        public string id, label, description; public int width, height, startX, startY, discoveryRadius = 1;
        public CellView[] walls = new CellView[0]; public ExplorationPointDef[] points = new ExplorationPointDef[0];
    }
    [Serializable] public sealed class ExplorationPointDef { public string id, label, description, kind, itemId; public int x, y, count; }
    [Serializable] public sealed class ExplorationTileView { public int x, y; public bool revealed, blocked, reachable; }
    [Serializable] public sealed class ExplorationPointView { public string id, label, description, kind; public int x, y; public bool claimed, canInteract; }
    [Serializable] public sealed class ExplorationView { public string id, label, description; public int width, height, x, y; public ExplorationTileView[] tiles; public ExplorationPointView[] points; }
    [Serializable] public sealed class ExplorationSave { public string sectorId; public int x, y; public CellView[] revealed = new CellView[0]; public string[] claimed = new string[0]; }
    [Serializable] public sealed class InventoryEntry { public string itemId; public int count; }
    [Serializable] public sealed class RewardDef { public string id, label, description, itemId; public int count, heal; }
    // Duration is counted at the end of a full round; 0 means persistent.
    [Serializable] public sealed class TagRuleDef { public string tag, occupantTag; public int durationRounds, entryDamage, turnDamage, movePenalty, energyPenalty; }
    [Serializable] public sealed class GameCommand { public string type, unitId, targetId, abilityId, itemId, classId, rewardId; public int x, y; }
    [Serializable] public sealed class CellView { public int x, y, cost; }
    [Serializable] public sealed class UnitView
    {
        public string id, label, classId, team; public int x, y, hp, maxHp, energy, maxEnergy, move;
        public bool selected, moved, acted; public string[] tags = new string[0];
    }
    [Serializable] public sealed class TileView { public string id; public int x, y; public bool blocked; public string[] tags = new string[0]; }
    [Serializable] public sealed class AbilityView { public string id, label, target, description, disabledReason; public string[] targetIds = new string[0]; public int range, cost; public bool enabled; }
    [Serializable] public sealed class ItemView { public string id, label, abilityId, target, description, disabledReason; public string[] targetIds = new string[0]; public int count, range; }
    [Serializable] public sealed class RosterView { public string id, label, classId; public bool selected; public int hp, maxHp; }
    [Serializable] public sealed class ClassView { public string id, label; public string[] abilityIds = new string[0]; }
    [Serializable] public sealed class ForecastView
    {
        public string targetId, label; public int beforeHp, afterHp, beforeEnergy, afterEnergy;
        public string[] beforeTags = new string[0], afterTags = new string[0];
    }
    [Serializable] public sealed class RewardView { public string id, label, description; }
    [Serializable] public sealed class GameView
    {
        public ExplorationView exploration;
        public string screen, message, encounterName, phase, selectedUnitId;
        public int encounterIndex, encounterCount, round, width, height, xp, partyCount, partyCapacity;
        public bool canConfirm, canMove, canAct;
        public RosterView[] roster = new RosterView[0]; public UnitView[] units = new UnitView[0];
        public TileView[] tiles = new TileView[0]; public AbilityView[] abilities = new AbilityView[0];
        public ItemView[] items = new ItemView[0]; public CellView[] reachable = new CellView[0];
        public ForecastView[] forecast = new ForecastView[0]; public string[] log = new string[0];
        public RewardView[] rewards = new RewardView[0]; public ClassView[] classes = new ClassView[0];
    }
    [Serializable] public sealed class SavedUnit
    {
        public string id, label, classId, team; public int x, y, hp, maxHp, energy, maxEnergy, move;
        public bool moved, acted; public string[] tags = new string[0]; public string[] permanentTags = new string[0];
    }
    [Serializable] public sealed class TimedTag { public string entityId, tag, source; public int remainingRounds; }
    [Serializable] public sealed class GameSave
    {
        public ExplorationSave[] exploration = new ExplorationSave[0];
        public int schemaVersion = 1; public string contentVersion, screen, phase, selectedUnitId;
        public int encounterIndex, round, xp; public bool rewardChosen;
        public RosterView[] roster = new RosterView[0]; public InventoryEntry[] inventory = new InventoryEntry[0];
        public SavedUnit[] units = new SavedUnit[0]; public TileView[] tiles = new TileView[0];
        public TimedTag[] timedTags = new TimedTag[0]; public string[] log = new string[0];
    }
}
