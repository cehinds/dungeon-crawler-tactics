using System;
using System.Collections.Generic;

namespace DungeonCrawlerTactics
{
    public sealed partial class GameSession
    {
        // Only explicitly allowlisted content versions can enter this migration. The incoming save
        // is copied: failed validation must not mutate either the caller's file or the live session.
        private GameSave MigrateCompatibleSave(GameSave source)
        {
            if (source.contentVersion == data.contentVersion) return source;
            Require(source.roster != null && source.units != null && source.timedTags != null, "Missing migration collections.");
            Dictionary<string, RosterView> oldRoster = new Dictionary<string, RosterView>();
            foreach (RosterView old in source.roster)
            {
                Require(old != null && old.id != null && Definition(old.id) != null && !oldRoster.ContainsKey(old.id), "Invalid legacy roster.");
                Require(old.classId != null && catalog.Classes.ContainsKey(old.classId), "Invalid legacy class.");
                ClassStats legacyStats = Stats(old.classId);
                Require(old.maxHp == legacyStats.hp && old.hp >= 0 && old.hp <= old.maxHp, "Invalid legacy roster health.");
                oldRoster.Add(old.id, old);
            }
            Dictionary<string, string> replaced = new Dictionary<string, string>();
            List<RosterView> migratedRoster = new List<RosterView>();
            foreach (RosterDef definition in data.roster)
            {
                RosterView old; oldRoster.TryGetValue(definition.id, out old);
                bool replacement = false;
                if (old == null && !string.IsNullOrEmpty(definition.replacesId))
                {
                    oldRoster.TryGetValue(definition.replacesId, out old);
                    replacement = old != null;
                    if (replacement && old.selected) replaced.Add(definition.replacesId, definition.id);
                }
                Require(old != null || !string.IsNullOrEmpty(definition.replacesId), "Legacy roster is missing a known member.");
                string classId = replacement || old == null || old.classId == definition.legacyClassId ? definition.classId : old.classId;
                bool normalized = old != null && (replacement || classId != old.classId);
                ClassStats stats = Stats(classId);
                migratedRoster.Add(new RosterView { id = definition.id, label = definition.label, classId = classId,
                    selected = definition.deployable && old != null && old.selected, hp = old == null ? stats.hp : normalized ? ScaleHealth(old.hp, old.maxHp, stats.hp) : old.hp,
                    maxHp = stats.hp });
            }
            List<SavedUnit> migratedUnits = new List<SavedUnit>();
            foreach (SavedUnit old in source.units)
            {
                Require(old != null, "Invalid legacy unit.");
                string replacementId; bool renamed = replaced.TryGetValue(old.id ?? "", out replacementId);
                if (!renamed) replacementId = old.id;
                RosterView destination = migratedRoster.Find(r => r.id == replacementId);
                bool changed = renamed || old.team == "player" && destination != null && destination.classId != old.classId;
                if (!changed) { migratedUnits.Add(old); continue; }
                Require(old.id != null && oldRoster.ContainsKey(old.id) && oldRoster[old.id].selected && oldRoster[old.id].classId == old.classId, "Legacy actor does not match deployed roster.");
                RosterDef definition = Definition(replacementId); ClassStats stats = Stats(destination.classId);
                ClassStats legacyStats = Stats(old.classId);
                Require(old.maxHp == legacyStats.hp && old.maxEnergy == legacyStats.energy && old.move == legacyStats.move, "Invalid legacy actor stats.");
                Require(old.team == "player" && old.maxHp > 0 && old.hp >= 0 && old.hp <= old.maxHp && old.energy >= 0 && old.energy <= old.maxEnergy, "Invalid legacy replacement stats.");
                migratedUnits.Add(new SavedUnit { id = replacementId, label = definition.label, classId = destination.classId, team = "player",
                    x = old.x, y = old.y, hp = ScaleHealth(old.hp, old.maxHp, stats.hp), maxHp = stats.hp,
                    energy = Math.Min(stats.energy, old.energy), maxEnergy = stats.energy, move = stats.move, moved = old.moved, acted = old.acted,
                    tags = old.tags, permanentTags = old.permanentTags });
            }
            List<TimedTag> migratedTags = new List<TimedTag>();
            foreach (TimedTag old in source.timedTags)
            {
                Require(old != null, "Invalid legacy timed tag."); string replacementId;
                migratedTags.Add(new TimedTag { entityId = old.entityId != null && replaced.TryGetValue(old.entityId, out replacementId) ? replacementId : old.entityId,
                    tag = old.tag, source = old.source, remainingRounds = old.remainingRounds });
            }
            string selection;
            return new GameSave { battleLayoutVersion = source.battleLayoutVersion, schemaVersion = source.schemaVersion, contentVersion = data.contentVersion, screen = source.screen, phase = source.phase,
                selectedUnitId = source.selectedUnitId != null && replaced.TryGetValue(source.selectedUnitId, out selection) ? selection : source.selectedUnitId,
                encounterIndex = source.encounterIndex, round = source.round, xp = source.xp, rewardChosen = source.rewardChosen, roster = migratedRoster.ToArray(),
                units = migratedUnits.ToArray(), timedTags = migratedTags.ToArray(), tiles = source.tiles, inventory = source.inventory, exploration = MigrateExploration(source), log = source.log };
        }
        private static int ScaleHealth(int hp, int oldMax, int newMax) { return hp == 0 ? 0 : Math.Max(1, (int)((long)hp * newMax / oldMax)); }
        private ExplorationSave[] MigrateExploration(GameSave save)
        {
            // Authored passage layouts changed. Reconnect remembered cells to the new entrance,
            // retain claimed discovery IDs, and move an invalid old position to the entrance.
            Require(save.exploration != null && save.exploration.Length <= data.encounters.Length, "Invalid legacy exploration.");
            List<ExplorationSave> result = new List<ExplorationSave>(); HashSet<string> sectors = new HashSet<string>();
            foreach (ExplorationSave old in save.exploration)
            {
                Require(old != null && old.sectorId != null && sectors.Add(old.sectorId), "Invalid legacy sector.");
                int index = Array.FindIndex(data.encounters, e => e.exploration.id == old.sectorId);
                Require(index >= 0 && index <= save.encounterIndex, "Unknown or future legacy sector.");
                ExplorationDef map = data.encounters[index].exploration;
                Require(old.revealed != null && old.claimed != null && old.revealed.Length <= map.width * map.height && old.claimed.Length <= map.points.Length && ExploreInside(map, old.x, old.y), "Invalid legacy discoveries.");
                HashSet<string> seen = new HashSet<string>();
                foreach (CellView cell in old.revealed) Require(cell != null && ExploreInside(map, cell.x, cell.y) && seen.Add(ExploreKey(cell.x, cell.y)), "Invalid legacy revealed tile.");
                Require(seen.Contains(ExploreKey(old.x, old.y)), "Legacy position was not discovered.");
                HashSet<string> claims = new HashSet<string>();
                foreach (string id in old.claimed) Require(id != null && claims.Add(id) && Array.Exists(map.points, p => p.id == id && p.kind != "encounter"), "Invalid legacy claim.");
                Dictionary<string, CellView> parents = new Dictionary<string, CellView>(); Queue<CellView> pending = new Queue<CellView>();
                CellView start = new CellView { x = map.startX, y = map.startY }; pending.Enqueue(start); parents.Add(ExploreKey(start.x, start.y), null);
                while (pending.Count > 0)
                {
                    CellView current = pending.Dequeue();
                    foreach (CellView next in Neighbors(current.x, current.y))
                        if (ExploreInside(map, next.x, next.y) && !ExploreWall(map, next.x, next.y) && !parents.ContainsKey(ExploreKey(next.x, next.y))) { parents.Add(ExploreKey(next.x, next.y), current); pending.Enqueue(next); }
                }
                ExplorationSave migrated = new ExplorationSave { sectorId = old.sectorId, x = start.x, y = start.y, claimed = (string[])old.claimed.Clone() }; Reveal(map, migrated);
                List<CellView> targets = new List<CellView>(old.revealed); foreach (ExplorationPointDef point in map.points) if (claims.Contains(point.id)) targets.Add(new CellView { x = point.x, y = point.y });
                foreach (CellView target in targets)
                {
                    if (!parents.ContainsKey(ExploreKey(target.x, target.y))) continue;
                    CellView cursor = target;
                    while (cursor != null) { migrated.x = cursor.x; migrated.y = cursor.y; Reveal(map, migrated); cursor = parents[ExploreKey(cursor.x, cursor.y)]; }
                }
                bool keepPosition = parents.ContainsKey(ExploreKey(old.x, old.y)); migrated.x = keepPosition ? old.x : start.x; migrated.y = keepPosition ? old.y : start.y;
                result.Add(migrated);
            }
            return result.ToArray();
        }
    }
}
