using System;
using System.Collections.Generic;

namespace DungeonCrawlerTactics
{
    [Serializable] public sealed class GeneratedDungeonState
    {
        public GeneratedFloorPlan floorPlan;
        public string activeGroupId;
        public string[] defeatedGroupIds = new string[0], claimedIds = new string[0];
        public CellView[] revealed = new CellView[0];
        public int steps;
        public int x, y;
        public CellView entrance, exit;
        public bool cleared;
    }

    public sealed partial class GameSession
    {
        private GeneratedDungeonState generatedDungeon;
        private static GeneratedDungeonState CopyGenerated(GeneratedDungeonState s)
        {
            return s == null ? null : new GeneratedDungeonState { x = s.x, y = s.y, cleared = s.cleared, floorPlan = CopyFloor(s.floorPlan), activeGroupId = s.activeGroupId, steps = s.steps, defeatedGroupIds = s.defeatedGroupIds == null ? null : (string[])s.defeatedGroupIds.Clone(), claimedIds = s.claimedIds == null ? null : (string[])s.claimedIds.Clone(), revealed = s.revealed == null ? null : Array.ConvertAll(s.revealed, CopyCell),
                entrance = s.entrance == null ? null : new CellView { x = s.entrance.x, y = s.entrance.y },
                exit = s.exit == null ? null : new CellView { x = s.exit.x, y = s.exit.y } };
        }
        // Encounter geometry is authored once; exploration checks it many times per step.
        // Weak keys release imported floor grids when a run is replaced.
        private sealed class GeneratedWalkGrid
        {
            public readonly bool[,] blocked;
            public GeneratedWalkGrid(EncounterDef map)
            {
                blocked = new bool[map.width, map.height];
                foreach (TileDef tile in map.tiles) if (tile.blocked) blocked[tile.x, tile.y] = true;
            }
        }
        private static readonly System.Runtime.CompilerServices.ConditionalWeakTable<EncounterDef, GeneratedWalkGrid> generatedWalkGrids = new System.Runtime.CompilerServices.ConditionalWeakTable<EncounterDef, GeneratedWalkGrid>();
        private static bool GeneratedOpen(EncounterDef map, int x, int y)
        {
            return x >= 0 && y >= 0 && x < map.width && y < map.height && !generatedWalkGrids.GetValue(map, m => new GeneratedWalkGrid(m)).blocked[x, y];
        }
        // Stable breadth-first order supplies both walkable detection distance and nearby party deployment.
        private static List<CellView> GeneratedCells(EncounterDef map, int x, int y, int maximumDistance = int.MaxValue)
        {
            List<CellView> cells = new List<CellView>(); HashSet<string> seen = new HashSet<string>();
            if (!GeneratedOpen(map, x, y)) return cells;
            cells.Add(new CellView { x = x, y = y }); seen.Add(ExploreKey(x, y));
            for (int i = 0; i < cells.Count; i++)
            {
                if (cells[i].cost >= maximumDistance) continue;
                int[] dx = { 0, -1, 1, 0 }, dy = { -1, 0, 0, 1 };
                for (int d = 0; d < 4; d++)
                {
                    int nx = cells[i].x + dx[d], ny = cells[i].y + dy[d];
                    if (GeneratedOpen(map, nx, ny) && seen.Add(ExploreKey(nx, ny))) cells.Add(new CellView { x = nx, y = ny, cost = cells[i].cost + 1 });
                }
            }
            return cells;
        }
        private void ValidateGenerated(GameSave save, EncounterDef map)
        {
            GeneratedDungeonState s = save.generatedDungeon; if (s == null) return;
            if (s.floorPlan != null) { ValidateFloorSave(save, map); return; }
            Require(save.journey == null && save.scenario == null && save.expedition == null && save.exploration != null && save.exploration.Length == 0, "Generated exploration cannot combine campaign state.");
            Require(s.entrance != null && s.exit != null && GeneratedOpen(map, s.x, s.y) && GeneratedOpen(map, s.entrance.x, s.entrance.y) && GeneratedOpen(map, s.exit.x, s.exit.y), "Invalid generated dungeon position.");
            List<CellView> cells = GeneratedCells(map, s.entrance.x, s.entrance.y);
            Require(cells.Exists(c => c.x == s.x && c.y == s.y) && cells.Exists(c => c.x == s.exit.x && c.y == s.exit.y), "Generated route must be connected.");
            foreach (SpawnDef enemy in map.enemies) Require(cells.Exists(c => c.x == enemy.x && c.y == enemy.y), "Generated enemies must connect to the entrance.");
            Require(!Array.Exists(map.enemies, e => e.x == s.entrance.x && e.y == s.entrance.y), "Generated entrance overlaps an enemy.");
            Require(!s.cleared || save.rewardChosen, "Cleared dungeon is missing its reward choice.");
            SetGeneratedSpawns(map, s);
            Require(save.encounterIndex == 0 && (!s.cleared || save.screen == "explore" || save.screen == "camp" || save.screen == "complete"), "Invalid generated dungeon phase.");
            Require(save.screen != "complete" || s.cleared && Math.Abs(s.x - s.exit.x) + Math.Abs(s.y - s.exit.y) <= 1, "Reach the cleared exit before completing the dungeon.");
            Require(s.cleared || !Array.Exists(map.enemies, e => e.x == s.x && e.y == s.y), "Generated leader overlaps an enemy.");
        }
        private void SetGeneratedSpawns(EncounterDef map, GeneratedDungeonState state)
        {
            List<CellView> nearby = GeneratedCells(map, state.x, state.y);
            nearby.RemoveAll(c => Array.Exists(map.enemies, e => e.x == c.x && e.y == c.y));
            Require(nearby.Count >= data.partySize, "Not enough connected space to deploy the party.");
            map.playerSpawns = nearby.GetRange(0, data.partySize).ToArray();
        }
        private void ResumeGenerated()
        {
            screen = "explore"; phase = "player"; selected = null; ClearPreview();
            message = generatedDungeon.cleared ? "Dungeon cleared. Reach the exit." : "Explore freely. Approaching enemies begins turn-based combat.";
        }
        private bool TryGeneratedCommand(GameCommand command)
        {
            if (TryFloorCommand(command)) return true;
            if (command.type == "import_generated")
            {
                Require(command.customMap != null, "Choose a generated map.");
                CustomMapData map = CopyCustomMap(command.customMap); EncounterDef encounter = BuildCustomEncounter(map);
                CellView entrance = command.entrance ?? map.playerSpawns[0];
                List<CellView> cells = GeneratedCells(encounter, entrance.x, entrance.y);
                Require(cells.Count > 0, "Entrance must be walkable.");
                CellView exit = command.exit ?? cells[cells.Count - 1];
                GeneratedDungeonState state = new GeneratedDungeonState { x = entrance.x, y = entrance.y, entrance = entrance, exit = exit };
                GameSave check = new GameSave { generatedDungeon = state, screen = "explore" };
                ValidateGenerated(check, encounter); SetGeneratedSpawns(encounter, state);
                Reset(); customMap = map; customEncounter = encounter; generatedDungeon = CopyGenerated(state); ResumeGenerated(); return true;
            }
            if (generatedDungeon == null) return false;
            if (command.type == "continue")
            {
                Require(screen == "victory", "Win the encounter to continue.");
                Require(rewardChosen || data.rewards.Length == 0, "Choose a sponsor reward first.");
                FinishGeneratedBattle(); return true;
            }
            if (command.type == "explore_move" || command.type == "explore_step")
            {
                Require(screen == "explore", "Move during exploration.");
                int x = command.type == "explore_step" ? generatedDungeon.x + command.x : command.x;
                int y = command.type == "explore_step" ? generatedDungeon.y + command.y : command.y;
                Require(Math.Abs((long)x - generatedDungeon.x) + Math.Abs((long)y - generatedDungeon.y) == 1, "Choose one cardinal step.");
                Require(GeneratedOpen(customEncounter, x, y) && (generatedDungeon.cleared || !Array.Exists(customMap.enemies, e => e.x == x && e.y == y)), "That passage is blocked.");
                generatedDungeon.x = x; generatedDungeon.y = y;
                message = "The party advances.";
                if (!generatedDungeon.cleared && GeneratedCells(customEncounter, x, y).Exists(c => c.cost <= 3 && Array.Exists(customMap.enemies, e => e.x == c.x && e.y == c.y))) StartEncounter();
                return true;
            }
            if (command.type == "explore_interact")
            {
                Require(screen == "explore" && command.targetId == "generated.exit", "Choose the dungeon exit during exploration.");
                Require(generatedDungeon.cleared, "Defeat the enemies before leaving.");
                Require(Math.Abs(generatedDungeon.x - generatedDungeon.exit.x) + Math.Abs(generatedDungeon.y - generatedDungeon.exit.y) <= 1, "Move beside the exit first.");
                screen = "complete"; message = "Generated dungeon completed."; return true;
            }
            return false;
        }
        private void FinishGeneratedBattle()
        {
            SyncRosterFromBattle();
            if (generatedDungeon.floorPlan != null) { FinishFloorBattle(); return; }
            foreach (RosterDef member in data.roster)
            {
                EntityState actor;
                if (battle.Entities.TryGetValue(member.id, out actor) && actor.Hp > 0) { generatedDungeon.x = actor.X; generatedDungeon.y = actor.Y; break; }
            }
            generatedDungeon.cleared = true; rewardChosen = true; battle = new BattleState(); units.Clear(); timed.Clear(); ResumeGenerated();
        }
        private ExplorationView GeneratedExplorationView()
        {
            if (generatedDungeon.floorPlan != null) return FloorExplorationView();
            List<ExplorationTileView> tiles = new List<ExplorationTileView>();
            for (int y = 0; y < customMap.height; y++) for (int x = 0; x < customMap.width; x++)
                tiles.Add(new ExplorationTileView { x = x, y = y, revealed = true, blocked = !GeneratedOpen(customEncounter, x, y), reachable = GeneratedOpen(customEncounter, x, y) && Math.Abs(x - generatedDungeon.x) + Math.Abs(y - generatedDungeon.y) == 1 });
            List<ExplorationPointView> points = new List<ExplorationPointView> {
                new ExplorationPointView { id = "generated.entrance", label = "Entrance", kind = "entrance", x = generatedDungeon.entrance.x, y = generatedDungeon.entrance.y },
                new ExplorationPointView { id = "generated.exit", label = "Exit", kind = "exit", description = "Defeat the enemies, then leave the dungeon.", x = generatedDungeon.exit.x, y = generatedDungeon.exit.y, canInteract = generatedDungeon.cleared && Math.Abs(generatedDungeon.x - generatedDungeon.exit.x) + Math.Abs(generatedDungeon.y - generatedDungeon.exit.y) <= 1 } };
            if (!generatedDungeon.cleared) foreach (SpawnDef enemy in customMap.enemies) points.Add(new ExplorationPointView { id = enemy.id, label = enemy.label, kind = "enemy", description = "Approach to begin turn-based combat.", x = enemy.x, y = enemy.y });
            return new ExplorationView { id = "generated.dungeon", label = customMap.label, description = "Free exploration; nearby enemies trigger combat.", width = customMap.width, height = customMap.height, x = generatedDungeon.x, y = generatedDungeon.y, tiles = tiles.ToArray(), points = points.ToArray() };
        }
    }
}
