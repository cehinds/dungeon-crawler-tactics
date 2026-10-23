using System;
namespace DungeonCrawlerTactics
{
    public sealed partial class GameSession
    {
        // Character Actor supplies a temporary specialty without replacing the permanent class.
        // The curated kits and one-choice-per-floor rule are tactical adaptations.
        private void SetSpecialty(GameCommand command)
        {
            Require(screen == "camp" && JourneyAllocationUnlocked, "Choose a specialty in the safe room from floor three.");
            RosterView member = GetRoster(command.unitId); RosterDef definition = Definition(member.id);
            Require(member.specialtyFloor == 0, "A specialty has already been chosen for this floor.");
            Require(command.classId != null && Array.IndexOf(definition.specialtyClassIds, command.classId) >= 0, "Unknown specialty for this crawler.");
            Require(journey == null || catalog.Classes[command.classId].minimumFloor <= journey.floorIndex + 1, "This specialty requires a later floor.");
            member.specialtyClassId = command.classId; member.specialtyFloor = journey == null ? 1 : journey.floorIndex + 1;
            message = "Character Actor: " + catalog.Classes[command.classId].label + " specialty selected for this floor. Its kit is a tactical adaptation.";
        }
        private void ValidateSpecialty(RosterView member, RosterDef definition, GameSave save)
        {
            if (string.IsNullOrEmpty(member.specialtyClassId)) { Require(member.specialtyFloor == 0, "Specialty receipt has no selection."); return; }
            int floor = save.journey == null ? 1 : save.journey.floorIndex + 1;
            Require(Array.IndexOf(definition.specialtyClassIds, member.specialtyClassId) >= 0 && member.specialtyFloor == floor, "Unknown or expired specialty.");
            Require(save.journey == null || floor >= 3 && catalog.Classes[member.specialtyClassId].minimumFloor <= floor, "Specialty requires a later story floor.");
        }
    }
}
