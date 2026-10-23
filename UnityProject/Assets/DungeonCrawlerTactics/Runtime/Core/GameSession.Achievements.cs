using System;
using System.Collections.Generic;
namespace DungeonCrawlerTactics
{
    public sealed partial class GameSession
    {
        private readonly List<string> achievementIds = new List<string>();
        private static readonly string[] KnownAchievements = { "achievement.first_move", "achievement.first_reaction", "achievement.first_form", "achievement.first_victory", "achievement.first_level" };
        private void AwardAchievement(string id)
        {
            if (achievementIds.Contains(id)) return;
            achievementIds.Add(id); presentationEvents.Add(new PresentationEvent { type = "achievement", tag = id });
        }
        private void AwardCommittedAchievements(GameCommand command)
        {
            if (command.type == "preview" || command.type == "cancel") return;
            PresentationEvent[] committed = presentationEvents.ToArray();
            foreach (PresentationEvent ev in committed)
            {
                if (ev.type == "move" && ev.actorId != null && units.ContainsKey(ev.actorId) && units[ev.actorId].team == "player") AwardAchievement("achievement.first_move");
                if (ev.type == "reaction") AwardAchievement("achievement.first_reaction");
                if (ev.type == "adaptation" && ev.tag != null && Array.Exists(data.forms, f => f.id == ev.tag)) AwardAchievement("achievement.first_form");
                if (ev.type == "level_up") AwardAchievement("achievement.first_level");
            }
            if (command.type == "confirm" && screen == "victory") AwardAchievement("achievement.first_victory");
        }
        private void ValidateAchievements(string[] ids)
        {
            Require(ids != null && ids.Length <= KnownAchievements.Length, "Invalid achievement collection.");
            HashSet<string> unique = new HashSet<string>(); foreach (string id in ids) Require(Array.IndexOf(KnownAchievements, id) >= 0 && unique.Add(id), "Unknown or duplicated achievement.");
        }
    }
}
