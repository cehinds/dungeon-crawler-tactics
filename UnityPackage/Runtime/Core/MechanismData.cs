using System;

namespace DungeonCrawlerTactics
{
    [Serializable]
    public sealed class GeneratedMechanismDef
    {
        public string id,
            label,
            description;
        public int x,
            y;
        public string[] materialTags = new string[0];
        public CellView[] openCells = new CellView[0];
        public GeneratedMechanismSolutionDef[] solutions = new GeneratedMechanismSolutionDef[0];
    }

    [Serializable]
    public sealed class GeneratedMechanismSolutionDef
    {
        public string id,
            label,
            description,
            kind,
            abilityTag,
            itemId;
        public int x,
            y,
            itemCount;
        public string[] requiredMaterialTags = new string[0];
    }

    [Serializable]
    public sealed class MechanismReceipt
    {
        public string mechanismId,
            solutionId,
            unitId,
            abilityId;
    }

    [Serializable]
    public sealed class MechanismCandidateView
    {
        public string unitId,
            unitLabel,
            abilityId,
            abilityLabel,
            disabledReason;
        public int manaCost;
        public bool enabled;
    }

    [Serializable]
    public sealed class MechanismSolutionView
    {
        public string id,
            label,
            description,
            kind,
            abilityTag,
            itemId,
            disabledReason;
        public int x,
            y,
            itemCount;
        public bool enabled;
        public MechanismCandidateView[] candidates = new MechanismCandidateView[0];
    }

    [Serializable]
    public sealed class MechanismView
    {
        public string id,
            label,
            description;
        public int x,
            y;
        public bool solved;
        public string[] materialTags = new string[0];
        public CellView[] openedCells = new CellView[0];
        public MechanismSolutionView[] solutions = new MechanismSolutionView[0];
    }

    [Serializable]
    public sealed class MechanismPreviewView
    {
        public string mechanismId,
            solutionId,
            unitId,
            abilityId,
            label,
            description,
            itemId;
        public int manaBefore,
            manaAfter,
            itemCountBefore,
            itemCountAfter;
        public bool canConfirm;
        public CellView[] openedCells = new CellView[0];
    }
}
