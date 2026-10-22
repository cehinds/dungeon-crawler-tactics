using System;
using System.Collections.Generic;

namespace DungeonCrawlerTactics
{
    // A deterministic application boundary shared by the Unity and browser presenters.
    // Presenters submit commands; only this class owns inventory, turns, movement and combat.
    public sealed partial class GameSession
    {
        private readonly Catalog catalog;
        private readonly GameData data;
        private readonly RulesEngine engine;
        private BattleState battle = new BattleState();
        private readonly Dictionary<string, SavedUnit> units = new Dictionary<string, SavedUnit>(StringComparer.Ordinal);
        private readonly Dictionary<string, RosterView> roster = new Dictionary<string, RosterView>(StringComparer.Ordinal);
        private readonly Dictionary<string, int> inventory = new Dictionary<string, int>(StringComparer.Ordinal);
        private readonly List<TimedTag> timed = new List<TimedTag>();
        private readonly List<string> log = new List<string>();
        private string screen = "camp", phase = "player", selected, message = "Choose four crawlers and their classes. Start when ready.";
        private int encounterIndex, round = 1, xp;
        private bool rewardChosen;
        private GameCommand pending;
        private ActionResult forecast;
        private EncounterDef Encounter { get { return data.encounters[Math.Min(encounterIndex, data.encounters.Length - 1)]; } }

        public GameSession(Content content, GameData gameData)
        {
            catalog = new Catalog(content);
            data = gameData ?? throw new ArgumentNullException(nameof(gameData));
            GameDataValidator.Validate(data, catalog);
            engine = new RulesEngine(catalog);
            Reset();
        }
        public GameView Handle(GameCommand command)
        {
            try
            {
                if (command == null) throw new ArgumentException("Missing command.");
                message = "";
                switch (command.type)
                {
                    case "new_run": Reset(); break;
                    case "toggle_party":
                        Require(screen == "camp", "Party can only change at camp.");
                        RosterView recruit = GetRoster(command.unitId);
                        Require(recruit.selected || PartyCount() < data.partySize, "Your party is full. Remove a crawler first.");
                        recruit.selected = !recruit.selected; break;
                    case "set_class":
                        Require(screen == "camp", "Classes can only change at camp.");
                        Require(command.classId != null && catalog.Classes.ContainsKey(command.classId), "Unknown class.");
                        RosterView trainee = GetRoster(command.unitId); trainee.classId = command.classId;
                        trainee.hp = trainee.maxHp = Stats(command.classId).hp; break;
                    case "start":
                        Require(screen == "camp", "Start an encounter from camp.");
                        Require(PartyCount() == data.partySize, "Choose exactly " + data.partySize + " crawlers.");
                        StartExploration(); break;
                    case "explore_move": ExploreMove(command.x, command.y); break;
                    case "explore_interact": ExploreInteract(command.targetId); break;
                    case "return_camp": Require(screen == "explore", "Return from exploration only."); screen = "camp"; break;
                    case "select":
                        RequirePlayer();
                        EntityState selection = GetUnit(command.unitId);
                        Require(selection.Team == "player" && selection.Hp > 0, "Select a living crawler.");
                        selected = selection.Id; ClearPreview(); break;
                    case "move":
                        RequirePlayer(); ClearPreview();
                        string moverId = command.unitId ?? selected;
                        Move(moverId, command.x, command.y); CheckOutcome();
                        if (battle.Entities[moverId].Hp == 0) FinishPlayerIfNeeded(); break;
                    case "preview":
                        RequirePlayer(); ClearPreview();
                        GameCommand proposed = CopyCommand(command); proposed.unitId = command.unitId ?? selected;
                        ActionResult candidate = ResolveAction(proposed);
                        pending = proposed; forecast = candidate; selected = proposed.unitId;
                        message = "Review the forecast, then confirm or cancel."; break;
                    case "confirm":
                        RequirePlayer(); Require(pending != null, "Preview an action first.");
                        GameCommand commit = pending;
                        ActionResult result = ResolveAction(commit); // Fresh validation, same resolver used by preview.
                        CommitAction(commit, result); ClearPreview();
                        CheckOutcome(); FinishPlayerIfNeeded(); break;
                    case "cancel": ClearPreview(); message = "Forecast canceled. Nothing was spent."; break;
                    case "wait":
                        RequirePlayer(); ClearPreview();
                        EntityState waiting = GetActor(command.unitId ?? selected);
                        Require(waiting.Team == phase, "This unit does not own the turn.");
                        EndActivation(waiting.Id); AddLog(Label(waiting.Id) + " waits.");
                        FinishPlayerIfNeeded(); break;
                    case "end_turn":
                        RequirePlayer(); ClearPreview();
                        foreach (SavedUnit unit in units.Values) if (unit.team == "player") { unit.moved = true; unit.acted = true; }
                        EnemyTurn(); break;
                    case "choose_reward":
                        Require(screen == "victory" && !rewardChosen, "No reward choice is available.");
                        RewardDef reward = null;
                        foreach (RewardDef option in data.rewards) if (option.id == command.rewardId) reward = option;
                        Require(reward != null, "Unknown reward.");
                        if (!string.IsNullOrEmpty(reward.itemId)) inventory[reward.itemId] += reward.count;
                        foreach (EntityState unit in battle.Entities.Values) if (!unit.IsTile && unit.Team == "player" && unit.Hp > 0) unit.Hp = Math.Min(unit.MaxHp, unit.Hp + reward.heal);
                        rewardChosen = true; AddLog("Sponsor delivery: " + reward.label + "."); break;
                    case "continue":
                        Require(screen == "victory", "Win the encounter to continue.");
                        Require(rewardChosen || data.rewards.Length == 0, "Choose a sponsor reward first.");
                        encounterIndex++;
                        screen = encounterIndex >= data.encounters.Length ? "complete" : "camp";
                        phase = "player";
                        if (screen == "camp") { battle = new BattleState(); units.Clear(); timed.Clear(); selected = null; }
                        message = screen == "complete" ? "Floor cleared. The audience demands another season." : "The camp medbay restored the party. Prepare for the next encounter.";
                        foreach (RosterView member in roster.Values) member.hp = member.maxHp;
                        break;
                    case "retry":
                        Require(screen == "defeat", "Retry is available after defeat.");
                        // A retry is a fresh attempt: restore the starting shared supply, keeping earned XP.
                        ResetInventory(); StartEncounter(); break;
                    default: throw new ArgumentException("Unknown command: " + command.type);
                }
            }
            catch (ArgumentException ex) { message = ex.Message; }
            catch (InvalidOperationException ex) { message = ex.Message; }
            return GetView();
        }
        private void Reset()
        {
            roster.Clear(); units.Clear(); timed.Clear(); log.Clear(); exploration.Clear(); battle = new BattleState();
            foreach (RosterDef member in data.roster)
            {
                int hp = Stats(member.classId).hp;
                roster.Add(member.id, new RosterView { id = member.id, label = member.label, classId = member.classId, selected = member.selected, hp = hp, maxHp = hp });
            }
            ResetInventory(); screen = "camp"; phase = "player"; encounterIndex = 0; round = 1; xp = 0; rewardChosen = false; selected = null; ClearPreview();
            message = "Choose " + data.partySize + " crawlers and their classes. The camp medbay restores everyone between rooms.";
        }
        private void ResetInventory()
        {
            inventory.Clear(); foreach (string id in catalog.Items.Keys) inventory.Add(id, 0);
            foreach (InventoryEntry entry in data.startingInventory) inventory[entry.itemId] = entry.count;
        }
        private void StartEncounter()
        {
            battle = new BattleState(); units.Clear(); timed.Clear(); ClearPreview(); log.Clear();
            EncounterDef encounter = Encounter;
            for (int y = 0; y < encounter.height; y++) for (int x = 0; x < encounter.width; x++)
            {
                EntityState tile = new EntityState { Id = TileId(x, y), IsTile = true, X = x, Y = y };
                foreach (TileDef authored in encounter.tiles) if (authored.x == x && authored.y == y) tile.Tags.UnionWith(authored.tags);
                battle.Entities.Add(tile.Id, tile);
            }
            int slot = 0;
            foreach (RosterDef definition in data.roster)
            {
                RosterView member = roster[definition.id]; if (!member.selected) continue;
                ClassStats stats = Stats(member.classId); CellView spawn = encounter.playerSpawns[slot++];
                AddUnit(member.id, member.label, member.classId, "player", spawn.x, spawn.y, stats.hp, stats.energy, stats.move, new string[0]);
            }
            foreach (SpawnDef enemy in encounter.enemies) AddUnit(enemy.id, enemy.label, enemy.classId, "enemy", enemy.x, enemy.y, enemy.hp, enemy.energy, enemy.move, enemy.tags);
            screen = "battle"; phase = "player"; round = 1; rewardChosen = false;
            selected = FirstAvailable(); message = encounter.description;
            AddLog(encounter.label + ": defeat all enemies. Move, then act. Actions end a crawler's activation.");
        }
        private void AddUnit(string id, string label, string classId, string team, int x, int y, int hp, int energy, int move, string[] tags)
        {
            EntityState unit = new EntityState { Id = id, ClassId = classId, Team = team, X = x, Y = y, Hp = hp, MaxHp = hp, Energy = energy };
            unit.Tags.UnionWith(tags); battle.Entities.Add(id, unit);
            units.Add(id, new SavedUnit { id = id, label = label, classId = classId, team = team, x = x, y = y, hp = hp, maxHp = hp, energy = energy, maxEnergy = energy, move = move, permanentTags = Sorted(unit.Tags) });
        }
        private void Move(string id, int x, int y)
        {
            EntityState actor = GetActor(id); Require(!units[id].moved, "This crawler already moved.");
            Require(actor.Team == phase, "This unit does not own the turn.");
            List<CellView> reachable = Reachable(id);
            Require(x != actor.X || y != actor.Y, "Choose a different tile.");
            bool found = false; foreach (CellView cell in reachable) if (cell.x == x && cell.y == y) found = true;
            Require(found, "That tile is blocked, occupied or outside movement range.");
            List<CellView> path = FindPath(actor.X, actor.Y, x, y, actor.Id);
            foreach (CellView cell in path)
            {
                actor.X = cell.x; actor.Y = cell.y;
                ApplyOccupancy(battle, actor, true, log);
                if (actor.Hp == 0) { AddLog(Label(id) + " fell to a floor hazard."); break; }
            }
            units[id].moved = true;
            AddLog(Label(id) + " moved to " + actor.X + "," + actor.Y + ".");
            ReconcileTags(null, battle, "terrain");
            TrimLog();
        }
        private ActionResult ResolveAction(GameCommand command)
        {
            EntityState actor = GetActor(command.unitId);
            Require(actor.Team == phase, "This unit does not own the turn.");
            string abilityId = command.abilityId;
            ActionResult resolved;
            if (!string.IsNullOrEmpty(command.itemId))
            {
                Require(actor.Team == "player", "Only crawlers use shared supplies.");
                Require(inventory.ContainsKey(command.itemId) && inventory[command.itemId] > 0, "No charges remain for that item.");
                abilityId = catalog.Items[command.itemId].abilityId;
                resolved = engine.ExecuteItem(battle, actor.Id, command.itemId, command.targetId);
            }
            else resolved = engine.Execute(battle, actor.Id, abilityId, command.targetId);
            List<string> events = new List<string>(resolved.Log);
            EntityState target = resolved.State.Entities[command.targetId];
            if (target.IsTile)
            {
                EntityState oldTile = battle.Entities[target.Id];
                foreach (EntityState occupant in resolved.State.Entities.Values)
                    if (!occupant.IsTile && occupant.Hp > 0 && occupant.X == target.X && occupant.Y == target.Y)
                    {
                        // Reactions on a surface immediately affect its occupant once, as well as future entrants.
                        foreach (TagRuleDef rule in data.tagRules)
                            if (target.Tags.Contains(rule.tag) && !oldTile.Tags.Contains(rule.tag) && rule.entryDamage > 0)
                                Damage(occupant, rule.entryDamage, rule.tag, events);
                        TransferSurfaceTags(resolved.State, occupant);
                    }
            }
            return new ActionResult(resolved.State, events);
        }
        private void CommitAction(GameCommand command, ActionResult result)
        {
            BattleState previous = battle; battle = result.State;
            ReconcileTags(previous, battle, string.IsNullOrEmpty(command.itemId) ? command.abilityId : command.itemId);
            if (!string.IsNullOrEmpty(command.itemId)) inventory[command.itemId]--;
            foreach (string entry in result.Log) AddLog(Label(command.unitId) + ": " + entry);
            EndActivation(command.unitId);
        }
        private void EndActivation(string id) { units[id].acted = true; units[id].moved = true; }
        private void ClearPreview() { pending = null; forecast = null; }
        private void FinishPlayerIfNeeded()
        {
            if (screen != "battle") return;
            selected = FirstAvailable();
            if (selected == null) EnemyTurn();
        }
        private void EnemyTurn()
        {
            if (screen != "battle") return;
            phase = "enemy"; ClearPreview(); AddLog("Enemy phase.");
            List<string> enemies = UnitIds("enemy");
            foreach (string id in enemies)
            {
                if (screen != "battle") break;
                EntityState enemy = battle.Entities[id]; if (enemy.Hp == 0) continue;
                // Deterministic bounded legal search: evaluate every granted ability against each living target.
                GameCommand best = BestEnemyAction(id);
                if (best == null)
                {
                    List<CellView> reachable = Reachable(id); CellView destination = null; int bestDistance = int.MaxValue;
                    foreach (CellView cell in reachable)
                    {
                        int distance = DistanceToPlayers(cell.x, cell.y);
                        if (distance < bestDistance) { bestDistance = distance; destination = cell; }
                    }
                    if (destination != null && (destination.x != enemy.X || destination.y != enemy.Y))
                    {
                        foreach (CellView step in FindPath(enemy.X, enemy.Y, destination.x, destination.y, enemy.Id))
                        {
                            enemy.X = step.x; enemy.Y = step.y;
                            ApplyOccupancy(battle, enemy, true, log);
                            if (enemy.Hp == 0) break;
                        }
                        ReconcileTags(null, battle, "terrain");
                        AddLog(Label(id) + " advances.");
                    }
                    best = enemy.Hp > 0 ? BestEnemyAction(id) : null;
                }
                if (best != null) CommitAction(best, ResolveAction(best));
                else { EndActivation(id); AddLog(Label(id) + " waits."); }
                CheckOutcome();
            }
            if (screen != "battle") return;
            // Hazards tick once per round; all tags are visible and deterministic.
            foreach (string id in SortedUnitIds())
            {
                EntityState unit = battle.Entities[id]; if (unit.Hp == 0) continue;
                ApplyOccupancy(battle, unit, false, log);
                foreach (TagRuleDef rule in data.tagRules) if (unit.Tags.Contains(rule.tag) && rule.turnDamage > 0) Damage(unit, rule.turnDamage, rule.tag, log);
            }
            ReconcileTags(null, battle, "terrain");
            TickTags(); CheckOutcome(); if (screen != "battle") return;
            round++; phase = "player";
            foreach (SavedUnit unit in units.Values)
            {
                unit.moved = false; unit.acted = false;
                EntityState entity = battle.Entities[unit.id];
                int penalty = 0; foreach (TagRuleDef rule in data.tagRules) if (entity.Tags.Contains(rule.tag)) penalty += rule.energyPenalty;
                entity.Energy = Math.Min(unit.maxEnergy, entity.Energy + Math.Max(0, data.energyPerRound - penalty));
            }
            selected = FirstAvailable(); AddLog("Round " + round + ": crawler phase.");
        }
        private GameCommand BestEnemyAction(string id)
        {
            GameCommand best = null; int bestScore = 0;
            ClassDef definition = catalog.Classes[battle.Entities[id].ClassId];
            foreach (string abilityId in definition.abilityIds)
            {
                AbilityDef ability = catalog.Abilities[abilityId]; if (ability.target == "tile") continue;
                foreach (string targetId in SortedUnitIds())
                {
                    GameCommand command = new GameCommand { unitId = id, abilityId = abilityId, targetId = targetId };
                    try
                    {
                        ActionResult result = ResolveAction(command); EntityState before = battle.Entities[targetId], after = result.State.Entities[targetId];
                        int score = before.Team == "player" ? (before.Hp - after.Hp) * 10 + (before.Hp > 0 && after.Hp == 0 ? 100 : 0) : (after.Hp - before.Hp) * 6;
                        score += before.Team == "player" ? Math.Max(0, after.Tags.Count - before.Tags.Count) * 2 : 0;
                        if (score > bestScore) { bestScore = score; best = command; }
                    }
                    catch (ArgumentException) { }
                }
            }
            return best;
        }
        private void ApplyOccupancy(BattleState state, EntityState unit, bool entry, List<string> events)
        {
            EntityState tile = state.Entities[TileId(unit.X, unit.Y)];
            foreach (TagRuleDef rule in data.tagRules) if (tile.Tags.Contains(rule.tag))
            {
                int amount = entry ? rule.entryDamage : rule.turnDamage;
                if (amount > 0) Damage(unit, amount, rule.tag, events);
            }
            TransferSurfaceTags(state, unit);
        }
        private void TransferSurfaceTags(BattleState state, EntityState unit)
        {
            EntityState tile = state.Entities[TileId(unit.X, unit.Y)];
            foreach (string tag in tile.Tags)
            {
                // Occupancy transfer is explicit data, independent from surface lifetime.
                TagRuleDef rule = TagRule(tag); if (rule != null && !string.IsNullOrEmpty(rule.occupantTag)) unit.Tags.Add(rule.occupantTag);
            }
        }
        private void Damage(EntityState target, int amount, string source, List<string> events)
        {
            target.Hp = Math.Max(0, target.Hp - amount); events.Add(Label(target.Id) + ": " + source + " deals " + amount + ".");
        }
        private void ReconcileTags(BattleState previous, BattleState next, string source)
        {
            foreach (EntityState entity in next.Entities.Values)
            {
                for (int i = timed.Count - 1; i >= 0; i--) if (timed[i].entityId == entity.Id && !entity.Tags.Contains(timed[i].tag)) timed.RemoveAt(i);
                foreach (string tag in entity.Tags)
                {
                    TagRuleDef rule = TagRule(tag); if (rule == null || rule.durationRounds == 0) continue;
                    bool existed = previous != null && previous.Entities.ContainsKey(entity.Id) && previous.Entities[entity.Id].Tags.Contains(tag);
                    bool permanent = units.ContainsKey(entity.Id) && Array.IndexOf(units[entity.Id].permanentTags, tag) >= 0;
                    if (permanent || existed) continue;
                    TimedTag layer = timed.Find(t => t.entityId == entity.Id && t.tag == tag);
                    if (layer == null) timed.Add(new TimedTag { entityId = entity.Id, tag = tag, source = source, remainingRounds = rule.durationRounds });
                }
                if (units.ContainsKey(entity.Id))
                {
                    List<string> permanent = new List<string>(units[entity.Id].permanentTags);
                    permanent.RemoveAll(tag => !entity.Tags.Contains(tag)); units[entity.Id].permanentTags = permanent.ToArray();
                }
            }
        }
        private void TickTags()
        {
            for (int i = timed.Count - 1; i >= 0; i--)
            {
                TimedTag layer = timed[i]; layer.remainingRounds--;
                if (layer.remainingRounds > 0) continue;
                bool permanent = units.ContainsKey(layer.entityId) && Array.IndexOf(units[layer.entityId].permanentTags, layer.tag) >= 0;
                if (!permanent) battle.Entities[layer.entityId].Tags.Remove(layer.tag);
                timed.RemoveAt(i);
            }
        }
        private void CheckOutcome()
        {
            if (screen != "battle") return;
            bool player = false, enemy = false;
            foreach (EntityState unit in battle.Entities.Values) if (!unit.IsTile && unit.Hp > 0) { if (unit.Team == "player") player = true; else enemy = true; }
            if (!player) { screen = "defeat"; message = "Your party fell. Retry this room or begin a new run."; ClearPreview(); AddLog("Party defeated."); }
            else if (!enemy)
            {
                screen = "victory"; xp += Encounter.xp; rewardChosen = false; ClearPreview();
                message = "Room cleared! Choose one sponsor reward."; AddLog("Victory: +" + Encounter.xp + " XP.");
            }
        }
        private List<CellView> Reachable(string id)
        {
            EntityState unit = battle.Entities[id]; int movement = units[id].move;
            foreach (TagRuleDef rule in data.tagRules) if (unit.Tags.Contains(rule.tag)) movement -= rule.movePenalty;
            movement = Math.Max(0, movement);
            List<CellView> cells = new List<CellView>(); Queue<CellView> queue = new Queue<CellView>(); HashSet<string> seen = new HashSet<string>();
            CellView start = new CellView { x = unit.X, y = unit.Y, cost = 0 }; queue.Enqueue(start); seen.Add(TileId(start.x, start.y));
            while (queue.Count > 0)
            {
                CellView current = queue.Dequeue(); cells.Add(current); if (current.cost >= movement) continue;
                foreach (CellView neighbor in Neighbors(current.x, current.y))
                    if (Passable(neighbor.x, neighbor.y, id) && seen.Add(TileId(neighbor.x, neighbor.y)))
                    { neighbor.cost = current.cost + 1; queue.Enqueue(neighbor); }
            }
            return cells;
        }
        private List<CellView> FindPath(int sx, int sy, int tx, int ty, string actorId)
        {
            Queue<CellView> queue = new Queue<CellView>(); Dictionary<string, CellView> parents = new Dictionary<string, CellView>();
            queue.Enqueue(new CellView { x = sx, y = sy }); parents.Add(TileId(sx, sy), null);
            while (queue.Count > 0)
            {
                CellView current = queue.Dequeue(); if (current.x == tx && current.y == ty) break;
                foreach (CellView cell in Neighbors(current.x, current.y)) if (Passable(cell.x, cell.y, actorId) && !parents.ContainsKey(TileId(cell.x, cell.y)))
                { parents.Add(TileId(cell.x, cell.y), current); queue.Enqueue(cell); }
            }
            List<CellView> path = new List<CellView>(); CellView cursor = new CellView { x = tx, y = ty };
            while (cursor.x != sx || cursor.y != sy) { path.Add(cursor); cursor = parents[TileId(cursor.x, cursor.y)]; }
            path.Reverse(); return path;
        }
        private IEnumerable<CellView> Neighbors(int x, int y)
        {
            // Up, left, right, down is the stable shortest-path tie break.
            yield return new CellView { x = x, y = y - 1 }; yield return new CellView { x = x - 1, y = y };
            yield return new CellView { x = x + 1, y = y }; yield return new CellView { x = x, y = y + 1 };
        }
        private bool Passable(int x, int y, string actorId)
        {
            if (x < 0 || y < 0 || x >= Encounter.width || y >= Encounter.height || Blocked(x, y)) return false;
            foreach (EntityState unit in battle.Entities.Values) if (!unit.IsTile && unit.Hp > 0 && unit.Id != actorId && unit.X == x && unit.Y == y) return false;
            return true;
        }
        private bool Blocked(int x, int y) { foreach (TileDef tile in Encounter.tiles) if (tile.x == x && tile.y == y) return tile.blocked; return false; }
        private int DistanceToPlayers(int x, int y)
        {
            int nearest = int.MaxValue; foreach (EntityState unit in battle.Entities.Values) if (!unit.IsTile && unit.Hp > 0 && unit.Team == "player") nearest = Math.Min(nearest, Math.Abs(unit.X - x) + Math.Abs(unit.Y - y)); return nearest;
        }
        private string FirstAvailable() { foreach (string id in UnitIds("player")) if (battle.Entities[id].Hp > 0 && !units[id].acted) return id; return null; }
        private List<string> UnitIds(string team) { List<string> ids = new List<string>(); foreach (SavedUnit unit in units.Values) if (unit.team == team) ids.Add(unit.id); ids.Sort(StringComparer.Ordinal); return ids; }
        private List<string> SortedUnitIds() { List<string> ids = new List<string>(units.Keys); ids.Sort(StringComparer.Ordinal); return ids; }
        private string Label(string id) { return id != null && units.ContainsKey(id) ? units[id].label : id; }
        private static string TileId(int x, int y) { return "tile." + x + "." + y; }
        private ClassStats Stats(string id) { foreach (ClassStats stats in data.classStats) if (stats.classId == id) return stats; throw new ArgumentException("Missing class stats: " + id); }
        private TagRuleDef TagRule(string tag) { foreach (TagRuleDef rule in data.tagRules) if (rule.tag == tag) return rule; return null; }
        private int PartyCount() { int count = 0; foreach (RosterView member in roster.Values) if (member.selected) count++; return count; }
        private RosterView GetRoster(string id) { Require(id != null && roster.ContainsKey(id), "Unknown crawler."); return roster[id]; }
        private EntityState GetUnit(string id) { Require(id != null && units.ContainsKey(id), "Unknown unit."); return battle.Entities[id]; }
        private EntityState GetActor(string id) { EntityState unit = GetUnit(id); Require(unit.Hp > 0 && !units[id].acted, "This unit is defeated or already acted."); return unit; }
        private void RequirePlayer() { Require(screen == "battle" && phase == "player", "Wait for the crawler phase in battle."); }
        private static void Require(bool condition, string error) { if (!condition) throw new ArgumentException(error); }
        private void AddLog(string entry) { log.Add(entry); TrimLog(); }
        private void TrimLog() { if (log.Count > 60) log.RemoveRange(0, log.Count - 60); }
        private static string[] Sorted(HashSet<string> tags) { string[] values = new string[tags.Count]; tags.CopyTo(values); Array.Sort(values, StringComparer.Ordinal); return values; }
        private static GameCommand CopyCommand(GameCommand c) { return new GameCommand { type = c.type, unitId = c.unitId, targetId = c.targetId, abilityId = c.abilityId, itemId = c.itemId, classId = c.classId, rewardId = c.rewardId, x = c.x, y = c.y }; }

        public GameView GetView()
        {
            GameView view = new GameView { screen = screen, message = message, phase = phase, encounterIndex = encounterIndex, encounterCount = data.encounters.Length, encounterName = Encounter.label, round = round, width = Encounter.width, height = Encounter.height, xp = xp, selectedUnitId = selected, partyCount = PartyCount(), partyCapacity = data.partySize, canConfirm = pending != null };
            List<RosterView> rosterViews = new List<RosterView>();
            foreach (RosterDef member in data.roster) { RosterView r = roster[member.id]; rosterViews.Add(new RosterView { id = r.id, label = r.label, classId = r.classId, selected = r.selected, hp = r.hp, maxHp = r.maxHp }); }
            view.roster = rosterViews.ToArray();
            List<ClassView> classes = new List<ClassView>(); foreach (ClassDef c in catalog.Classes.Values) classes.Add(new ClassView { id = c.id, label = c.label, abilityIds = (string[])c.abilityIds.Clone() }); view.classes = classes.ToArray();
            List<UnitView> unitViews = new List<UnitView>();
            foreach (string id in SortedUnitIds())
            {
                EntityState e = battle.Entities[id]; SavedUnit u = units[id];
                unitViews.Add(new UnitView { id = id, label = u.label, classId = e.ClassId, team = e.Team, x = e.X, y = e.Y, hp = e.Hp, maxHp = e.MaxHp, energy = e.Energy, maxEnergy = u.maxEnergy, move = u.move, selected = selected == id, moved = u.moved, acted = u.acted, tags = Sorted(e.Tags) });
            }
            view.units = unitViews.ToArray();
            List<TileView> tileViews = new List<TileView>();
            for (int y = 0; y < Encounter.height; y++) for (int x = 0; x < Encounter.width; x++)
            {
                string id = TileId(x, y); EntityState tile; battle.Entities.TryGetValue(id, out tile);
                tileViews.Add(new TileView { id = id, x = x, y = y, blocked = Blocked(x, y), tags = tile == null ? new string[0] : Sorted(tile.Tags) });
            }
            view.tiles = tileViews.ToArray();
            EntityState actor = null; if (selected != null && units.ContainsKey(selected)) actor = battle.Entities[selected];
            bool active = actor != null && screen == "battle" && phase == "player" && actor.Hp > 0 && !units[selected].acted;
            view.canAct = active; view.canMove = active && !units[selected].moved;
            if (view.canMove) view.reachable = Reachable(selected).ToArray();
            List<AbilityView> abilityViews = new List<AbilityView>();
            if (actor != null) foreach (string id in catalog.Classes[actor.ClassId].abilityIds)
            {
                AbilityDef a = catalog.Abilities[id]; abilityViews.Add(new AbilityView { id = id, label = a.label, target = a.target, range = a.range, cost = a.cost, enabled = active && actor.Energy >= a.cost, description = Describe(a), disabledReason = !active ? "Activation unavailable" : actor.Energy < a.cost ? "Insufficient energy" : "", targetIds = active && actor.Energy >= a.cost ? LegalTargets(actor, a, null) : new string[0] });
            }
            view.abilities = abilityViews.ToArray();
            List<ItemView> itemViews = new List<ItemView>(); foreach (ItemDef item in catalog.Items.Values)
            { AbilityDef a = catalog.Abilities[item.abilityId]; itemViews.Add(new ItemView { id = item.id, label = item.label, abilityId = item.abilityId, count = inventory[item.id], target = a.target, range = a.range, description = Describe(a), disabledReason = !active ? "Activation unavailable" : inventory[item.id] == 0 ? "No charges" : "", targetIds = active && inventory[item.id] > 0 ? LegalTargets(actor, a, item.id) : new string[0] }); }
            view.items = itemViews.ToArray();
            if (forecast != null)
            {
                List<ForecastView> changes = new List<ForecastView>();
                foreach (EntityState next in forecast.State.Entities.Values)
                {
                    EntityState before = battle.Entities[next.Id];
                    if (before.Hp != next.Hp || before.Energy != next.Energy || !before.Tags.SetEquals(next.Tags))
                        changes.Add(new ForecastView { targetId = next.Id, label = Label(next.Id), beforeHp = before.Hp, afterHp = next.Hp, beforeEnergy = before.Energy, afterEnergy = next.Energy, beforeTags = Sorted(before.Tags), afterTags = Sorted(next.Tags) });
                }
                changes.Sort((a, b) => StringComparer.Ordinal.Compare(a.targetId, b.targetId)); view.forecast = changes.ToArray();
            }
            List<string> visibleLog = new List<string>(log); if (forecast != null) foreach (string entry in forecast.Log) visibleLog.Add("Forecast: " + entry); view.log = visibleLog.ToArray();
            if (screen == "victory" && !rewardChosen)
            { List<RewardView> rewards = new List<RewardView>(); foreach (RewardDef reward in data.rewards) rewards.Add(new RewardView { id = reward.id, label = reward.label, description = reward.description }); view.rewards = rewards.ToArray(); }
            if (screen == "explore") view.exploration = ExplorationView();
            return view;
        }
        private string[] LegalTargets(EntityState actor, AbilityDef ability, string itemId)
        {
            List<string> targets = new List<string>();
            foreach (EntityState target in battle.Entities.Values)
            {
                if (Math.Abs(actor.X - target.X) + Math.Abs(actor.Y - target.Y) > ability.range) continue;
                if ((ability.target == "tile") != target.IsTile) continue;
                try { ResolveAction(new GameCommand { unitId = actor.Id, abilityId = ability.id, itemId = itemId, targetId = target.Id }); targets.Add(target.Id); }
                catch (ArgumentException) { }
                catch (InvalidOperationException) { }
            }
            targets.Sort(StringComparer.Ordinal); return targets.ToArray();
        }
        private string Describe(AbilityDef ability)
        {
            List<string> parts = new List<string>();
            foreach (EffectDef effect in ability.effects)
            {
                if (effect.op == "Damage") parts.Add(effect.amount + " damage");
                else if (effect.op == "Heal") parts.Add("Restore " + effect.amount + " HP");
                else
                {
                    string label = DisplayTag(effect.tag);
                    string protection = "";
                    if (effect.op == "AddTag") foreach (ReactionDef rule in catalog.Reactions)
                        if (rule.damageReduction > 0 && Array.IndexOf(rule.target.all, effect.tag) >= 0)
                        { protection = " (" + rule.damageReduction + " damage protection on a matching hit)"; break; }
                    parts.Add((effect.op == "AddTag" ? "Apply " : "Remove ") + label + protection);
                }
            }
            if (ability.incomingTags.Length > 0)
            {
                List<string> labels = new List<string>(); foreach (string tag in ability.incomingTags) labels.Add(DisplayTag(tag));
                parts.Add("Triggers " + string.Join(" / ", labels) + " reactions");
            }
            return string.Join(". ", parts) + ".";
        }
        private static string DisplayTag(string tag)
        {
            if (string.IsNullOrEmpty(tag)) return "condition";
            int dot = tag.LastIndexOf('.'); string name = tag.Substring(dot + 1).Replace('_', ' ');
            return char.ToUpperInvariant(name[0]) + name.Substring(1);
        }
        public GameSave ExportSave()
        {
            GameSave save = new GameSave { contentVersion = data.contentVersion, screen = screen, phase = phase, selectedUnitId = selected, encounterIndex = encounterIndex, round = round, xp = xp, rewardChosen = rewardChosen };
            save.roster = GetView().roster;
            List<InventoryEntry> entries = new List<InventoryEntry>(); foreach (ItemDef item in catalog.Items.Values) entries.Add(new InventoryEntry { itemId = item.id, count = inventory[item.id] }); save.inventory = entries.ToArray();
            List<SavedUnit> savedUnits = new List<SavedUnit>();
            foreach (string id in SortedUnitIds())
            {
                EntityState entity = battle.Entities[id]; SavedUnit unit = units[id];
                savedUnits.Add(new SavedUnit { id = id, label = unit.label, classId = entity.ClassId, team = entity.Team, x = entity.X, y = entity.Y, hp = entity.Hp, maxHp = entity.MaxHp, energy = entity.Energy, maxEnergy = unit.maxEnergy, move = unit.move, moved = unit.moved, acted = unit.acted, tags = Sorted(entity.Tags), permanentTags = (string[])unit.permanentTags.Clone() });
            }
            save.units = savedUnits.ToArray();
            if (battle.Entities.Count > 0) save.tiles = GetView().tiles;
            List<TimedTag> layers = new List<TimedTag>(); foreach (TimedTag layer in timed) layers.Add(new TimedTag { entityId = layer.entityId, tag = layer.tag, source = layer.source, remainingRounds = layer.remainingRounds }); save.timedTags = layers.ToArray();
            save.exploration = ExportExploration(); save.log = log.ToArray(); return save;
        }
        public GameView ImportSave(GameSave save)
        {
            try
            {
                Require(save != null && save.schemaVersion == 1 && save.contentVersion == data.contentVersion, "Save version does not match this content pack.");
                Require(save.screen == "camp" || save.screen == "explore" || save.screen == "battle" || save.screen == "victory" || save.screen == "defeat" || save.screen == "complete", "Invalid save screen.");
                Require(save.phase == "player" || (save.phase == "enemy" && (save.screen == "victory" || save.screen == "defeat")), "Invalid save phase.");
                Require(save.encounterIndex >= 0 && save.encounterIndex < data.encounters.Length + (save.screen == "complete" ? 1 : 0), "Invalid encounter index.");
                Require(save.screen != "complete" || save.encounterIndex == data.encounters.Length, "Incomplete floor marked complete.");
                Require((save.screen != "battle" && save.screen != "defeat") || !save.rewardChosen, "Reward cannot precede victory.");
                Require(save.screen != "complete" || save.rewardChosen || data.rewards.Length == 0, "Completed floor is missing its final reward choice.");
                Require(save.round > 0 && save.round <= 100000, "Invalid round.");
                Require(save.roster != null && save.units != null && save.tiles != null && save.inventory != null && save.timedTags != null && save.log != null, "Save arrays cannot be null.");
                Require(save.roster.Length == data.roster.Length && save.inventory.Length == catalog.Items.Count && save.log.Length <= 60, "Invalid save collection lengths.");
                int expectedXp = 0;
                for (int i = 0; i < Math.Min(save.encounterIndex, data.encounters.Length); i++) expectedXp += data.encounters[i].xp;
                if (save.screen == "victory") expectedXp += data.encounters[save.encounterIndex].xp;
                Require(save.xp == expectedXp, "Save XP does not match its completed encounters.");
                Dictionary<string, RosterView> nextRoster = new Dictionary<string, RosterView>(); int party = 0;
                foreach (RosterView member in save.roster)
                {
                    Require(member != null && member.id != null && roster.ContainsKey(member.id) && !nextRoster.ContainsKey(member.id) && member.classId != null && catalog.Classes.ContainsKey(member.classId), "Invalid saved roster.");
                    RosterDef definition = Array.Find(data.roster, r => r.id == member.id); ClassStats stats = Stats(member.classId);
                    Require(member.hp >= 0 && member.hp <= stats.hp && member.maxHp == stats.hp, "Invalid roster health.");
                    nextRoster.Add(member.id, new RosterView { id = member.id, label = definition.label, classId = member.classId, selected = member.selected, hp = member.hp, maxHp = member.maxHp }); if (member.selected) party++;
                }
                Require(party <= data.partySize && (save.screen == "camp" || party == data.partySize), "Invalid party size.");
                Dictionary<string, int> nextInventory = new Dictionary<string, int>();
                foreach (InventoryEntry item in save.inventory)
                {
                    Require(item != null && item.itemId != null && catalog.Items.ContainsKey(item.itemId) && !nextInventory.ContainsKey(item.itemId) && item.count >= 0 && item.count <= 10000, "Invalid saved inventory.");
                    nextInventory.Add(item.itemId, item.count);
                }
                List<ExplorationSave> nextExploration = ValidateExploration(save);
                bool hasBattle = save.screen != "camp" && save.screen != "explore";
                EncounterDef encounter = data.encounters[Math.Min(save.encounterIndex, data.encounters.Length - 1)];
                Require(save.units.Length == (hasBattle ? data.partySize + encounter.enemies.Length : 0), "Saved unit count does not match encounter.");
                Require(save.tiles.Length == (hasBattle ? encounter.width * encounter.height : 0), "Saved map size does not match encounter.");
                BattleState nextBattle = new BattleState(); Dictionary<string, SavedUnit> nextUnits = new Dictionary<string, SavedUnit>(); HashSet<string> occupied = new HashSet<string>();
                foreach (TileView tile in save.tiles)
                {
                    Require(tile != null && tile.id == TileId(tile.x, tile.y) && tile.x >= 0 && tile.y >= 0 && tile.x < encounter.width && tile.y < encounter.height && !nextBattle.Entities.ContainsKey(tile.id), "Invalid saved tile.");
                    TileDef authored = Array.Find(encounter.tiles, t => t.x == tile.x && t.y == tile.y);
                    Require(tile.blocked == (authored != null && authored.blocked), "Save changed authored walls.");
                    ValidateTags(tile.tags); EntityState entity = new EntityState { Id = tile.id, IsTile = true, X = tile.x, Y = tile.y }; entity.Tags.UnionWith(tile.tags); nextBattle.Entities.Add(tile.id, entity);
                }
                bool playerAlive = false, enemyAlive = false;
                foreach (SavedUnit unit in save.units)
                {
                    Require(unit != null && unit.id != null && !nextBattle.Entities.ContainsKey(unit.id) && unit.classId != null && catalog.Classes.ContainsKey(unit.classId), "Invalid saved unit.");
                    string label; int hp, energy, move;
                    if (unit.team == "player")
                    {
                        Require(nextRoster.ContainsKey(unit.id) && nextRoster[unit.id].selected && nextRoster[unit.id].classId == unit.classId, "Saved party member not deployed.");
                        ClassStats stats = Stats(unit.classId); hp = stats.hp; energy = stats.energy; move = stats.move; label = nextRoster[unit.id].label; if (unit.hp > 0) playerAlive = true;
                    }
                    else
                    {
                        SpawnDef spawn = Array.Find(encounter.enemies, e => e.id == unit.id);
                        Require(unit.team == "enemy" && spawn != null && spawn.classId == unit.classId, "Unknown saved enemy.");
                        hp = spawn.hp; energy = spawn.energy; move = spawn.move; label = spawn.label; if (unit.hp > 0) enemyAlive = true;
                    }
                    Require(unit.hp >= 0 && unit.hp <= hp && unit.maxHp == hp && unit.energy >= 0 && unit.energy <= energy && unit.maxEnergy == energy && unit.move == move, "Saved stats do not match content.");
                    Require(unit.x >= 0 && unit.y >= 0 && unit.x < encounter.width && unit.y < encounter.height, "Unit outside board.");
                    TileDef wall = Array.Find(encounter.tiles, t => t.x == unit.x && t.y == unit.y);
                    Require(wall == null || !wall.blocked, "Unit inside wall.");
                    if (unit.hp > 0) Require(occupied.Add(TileId(unit.x, unit.y)), "Living units overlap.");
                    Require(!unit.acted || unit.moved, "Invalid activation flags."); ValidateTags(unit.tags); ValidateTags(unit.permanentTags);
                    SpawnDef seed = Array.Find(encounter.enemies, e => e.id == unit.id);
                    foreach (string tag in unit.permanentTags) Require(seed != null && Array.IndexOf(seed.tags, tag) >= 0, "Saved permanent tag is not an authored unit seed.");
                    foreach (string tag in unit.permanentTags) Require(Array.IndexOf(unit.tags, tag) >= 0, "Permanent tag absent from saved unit.");
                    EntityState entity = new EntityState { Id = unit.id, ClassId = unit.classId, Team = unit.team, X = unit.x, Y = unit.y, Hp = unit.hp, MaxHp = hp, Energy = unit.energy };
                    entity.Tags.UnionWith(unit.tags); nextBattle.Entities.Add(unit.id, entity);
                    nextUnits.Add(unit.id, new SavedUnit { id = unit.id, label = label, classId = unit.classId, team = unit.team, maxEnergy = energy, move = move, moved = unit.moved, acted = unit.acted, permanentTags = (string[])unit.permanentTags.Clone() });
                }
                if (save.screen == "battle") Require(playerAlive && enemyAlive, "Battle outcome is inconsistent.");
                if (save.screen == "victory" || save.screen == "complete") Require(playerAlive && !enemyAlive, "Victory outcome is inconsistent.");
                if (save.screen == "defeat") Require(!playerAlive, "Defeat outcome is inconsistent.");
                Require(save.selectedUnitId == null || (nextUnits.ContainsKey(save.selectedUnitId) && nextUnits[save.selectedUnitId].team == "player"), "Invalid saved selection.");
                List<TimedTag> nextTimed = new List<TimedTag>(); HashSet<string> layerKeys = new HashSet<string>();
                Require(save.timedTags.Length <= (save.units.Length + save.tiles.Length) * data.tagRules.Length, "Too many timed tags.");
                foreach (TimedTag layer in save.timedTags)
                {
                    Require(layer != null && layer.entityId != null && layer.tag != null && nextBattle.Entities.ContainsKey(layer.entityId), "Unknown timed-tag entity.");
                    TagRuleDef rule = TagRule(layer.tag);
                    Require(rule != null && rule.durationRounds > 0 && layer.remainingRounds > 0 && layer.remainingRounds <= rule.durationRounds && nextBattle.Entities[layer.entityId].Tags.Contains(layer.tag) && layerKeys.Add(layer.entityId + ":" + layer.tag), "Invalid timed-tag layer.");
                    Require(!string.IsNullOrEmpty(layer.source) && layer.source.Length <= 150, "Invalid tag source.");
                    nextTimed.Add(new TimedTag { entityId = layer.entityId, tag = layer.tag, source = layer.source, remainingRounds = layer.remainingRounds });
                }
                foreach (SavedUnit unit in save.units)
                    foreach (string tag in unit.tags)
                    {
                        TagRuleDef rule = TagRule(tag);
                        if (rule != null && rule.durationRounds > 0)
                            Require(Array.IndexOf(unit.permanentTags, tag) >= 0 || layerKeys.Contains(unit.id + ":" + tag), "Timed unit tag is missing its duration layer.");
                    }
                foreach (TileView tile in save.tiles)
                    foreach (string tag in tile.tags)
                    {
                        TagRuleDef rule = TagRule(tag); TileDef authored = Array.Find(encounter.tiles, t => t.x == tile.x && t.y == tile.y);
                        if (rule != null && rule.durationRounds > 0)
                            Require((authored != null && Array.IndexOf(authored.tags, tag) >= 0) || layerKeys.Contains(tile.id + ":" + tag), "Timed tile tag is missing its duration layer.");
                    }
                foreach (string entry in save.log) Require(entry != null && entry.Length <= 1000, "Invalid saved log.");
                // All validation is complete before replacing any live state.
                exploration.Clear(); foreach (ExplorationSave sector in nextExploration) exploration.Add(sector.sectorId, sector);
                roster.Clear(); foreach (var pair in nextRoster) roster.Add(pair.Key, pair.Value);
                inventory.Clear(); foreach (var pair in nextInventory) inventory.Add(pair.Key, pair.Value);
                units.Clear(); foreach (var pair in nextUnits) units.Add(pair.Key, pair.Value);
                timed.Clear(); timed.AddRange(nextTimed); battle = nextBattle;
                screen = save.screen; phase = save.phase; selected = save.selectedUnitId; encounterIndex = save.encounterIndex; round = save.round; xp = save.xp; rewardChosen = save.rewardChosen;
                log.Clear(); log.AddRange(save.log); ClearPreview(); message = "Save restored.";
            }
            catch (ArgumentException ex) { message = "Save rejected: " + ex.Message; }
            return GetView();
        }
        private void ValidateTags(string[] tags)
        {
            Require(tags != null && tags.Length <= 100, "Invalid saved tags."); HashSet<string> seen = new HashSet<string>();
            foreach (string tag in tags) Require(catalog.HasTag(tag) && seen.Add(tag), "Unknown or duplicate saved tag.");
        }
    }
}
