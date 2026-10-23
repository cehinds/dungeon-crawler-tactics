using System;

namespace DungeonCrawlerTactics
{
    [Serializable] public sealed class JourneyDef
    {
        public int schemaVersion = 1;
        public string id, label, description;
        public JourneyFloorDef[] floors = new JourneyFloorDef[0];
    }
    [Serializable] public sealed class JourneyFloorDef
    {
        public string id, label, description, kind, mechanic;
        public int number, captureCount;
        public bool available;
        public string[] requiredPointIds = new string[0];
        public EncounterDef encounter;
    }
    [Serializable] public sealed class JourneySave
    {
        public int version = 1, floorIndex;
        public string id;
        public string[] capturedIds = new string[0];
    }
    [Serializable] public sealed class JourneyFloorView
    {
        public string id, label, description, kind, mechanic, status;
        public int number;
        public bool available, current, complete;
    }
    [Serializable] public sealed class JourneyCaptureView
    {
        public string targetId, label, disabledReason;
        public int hp, maxHp, threshold, range = 3;
        public bool captured, canCapture;
    }
    [Serializable] public sealed class JourneyIntentView
    {
        public string actorId, targetId, abilityId, description;
        public int damage;
    }
    [Serializable] public sealed class JourneyView
    {
        public string id, label, description, floorId, floorLabel, mechanic, objective;
        public int floorNumber, implementedFloors = 8, totalFloors = 18, objectivesComplete, objectivesRequired, cardsCaptured, cardsRequired;
        public bool active, available, classesUnlocked, allocationUnlocked, canBypass, complete;
        public JourneyFloorView[] floors = new JourneyFloorView[0];
        public JourneyCaptureView[] captures = new JourneyCaptureView[0];
        public JourneyIntentView[] intents = new JourneyIntentView[0];
    }
}
