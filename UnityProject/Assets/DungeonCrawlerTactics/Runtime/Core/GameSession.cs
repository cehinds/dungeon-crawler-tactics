using System;
using System.Collections.Generic;

namespace DungeonCrawlerTactics
{
    // A deterministic application boundary shared by the Unity and browser presenters.
    // Presenters submit commands; only this class owns inventory, turns, movement and combat.
    public sealed partial class GameSession
    {
        private readonly Catalog catalog;
        private readonly Content scenarioValidationContent;
        private readonly GameData data;
        private readonly RulesEngine engine;
        private BattleState battle = new BattleState();
        private readonly Dictionary<string, SavedUnit> units = new Dictionary<string, SavedUnit>(StringComparer.Ordinal);
        private readonly Dictionary<string, RosterView> roster = new Dictionary<string, RosterView>(StringComparer.Ordinal);
        private readonly Dictionary<string, int> inventory = new Dictionary<string, int>(StringComparer.Ordinal);
        private readonly List<TimedTag> timed = new List<TimedTag>();
        private readonly List<PresentationEvent> presentationEvents = new List<PresentationEvent>();
        private readonly List<string> log = new List<string>();
        private string screen = "camp", phase = "player", selected, message = "Choose four crawlers and their classes. Start when ready.";
        private int encounterIndex, round = 1, xp, battleLayoutVersion;
        private bool rewardChosen;
        private GameCommand pending;
        private ActionResult forecast;
        private EncounterDef Encounter { get { return ActiveExpeditionEncounter ?? ActiveScenarioEncounter ?? CustomEncounter(encounterIndex) ?? ActiveJourneyEncounter ?? data.encounters[Math.Min(encounterIndex, data.encounters.Length - 1)]; } }

        public GameSession(Content content, GameData gameData)
        {
            scenarioValidationContent = content;
            catalog = new Catalog(content);
            data = gameData ?? throw new ArgumentNullException(nameof(gameData));
            GameDataValidator.Validate(data, catalog);
            catalog.ConfigureRankTags(data.development.practice);
            engine = new RulesEngine(catalog, 64, (state, moving, entries, visual) => ApplyOccupancy(state, moving, true, entries, visual));
            Reset();
        }
        public GameView Handle(GameCommand command) { return HandleCommand(command, false); }
        private GameView HandleCommand(GameCommand command, bool compactExploration)
        {
            presentationEvents.Clear();
            try
            {
                if (command == null) throw new ArgumentException("Missing command.");
                PrepareCampaignCommand(command);
                ClearHomePreview(command);
                message = "";
                if (command.type != "preview_allocate" && command.type != "confirm_development" && command.type != "cancel_development") pendingDevelopment = null;
                if (command.type != "preview_skill_node" && command.type != "confirm_skill_node" && command.type != "cancel_skill_node") pendingSkillNode = null;
                if (TryNeighborhoodCommand(command)) { return GetView(); }
                if (TryHomeCommand(command)) { AwardCommittedAchievements(command); return GetView(); }
                if (TryJourneyCommand(command)) { AwardCommittedAchievements(command); return GetView(); }
                if (TryExpeditionCommand(command)) { AwardCommittedAchievements(command); return GetView(); }
                if (TryScenarioCommand(command)) { AwardCommittedAchievements(command); return GetView(); }
                if (TryGeneratedCommand(command)) return CommandView(compactExploration);
                switch (command.type)
                {
                    case "preview_skill_node": PreviewSkillNode(command); break;
                    case "confirm_skill_node": ConfirmSkillNode(); break;
                    case "cancel_skill_node": pendingSkillNode = null; message = "Skill choice canceled. No points spent."; break;
                    case "preview_allocate": Require(JourneyAllocationUnlocked, "Stat points remain banked until floor three."); PreviewAllocation(command); break;
                    case "confirm_development": Require(JourneyAllocationUnlocked, "Stat points remain banked until floor three."); ConfirmAllocation(); break;
                    case "cancel_development": pendingDevelopment = null; message = "Allocation canceled. No points spent."; break;
                    case "craft": Craft(command.recipeId); break;
                    case "open_loot_box": OpenLootBox(command.lootBoxId); break;
                    case "import_map": ImportCustomMap(command); break;
                    case "new_run": Reset(); break;
                    case "safe_room_rest": Rest(); break;
                    case "equip": Equip(command, false); break;
                    case "unequip": Equip(command, true); break;
                    case "toggle_party":
                        Require(screen == "camp", "Party can only change at camp.");
                        RosterView recruit = GetRoster(command.unitId);
                        Require(Definition(recruit.id).deployable, "This character is an advisor and cannot deploy.");
                        Require(recruit.selected || PartyCount() < data.partySize, "Your party is full. Remove a crawler first.");
                        recruit.selected = !recruit.selected; break;
                    case "set_specialty": SetSpecialty(command); break;
                    case "set_class":
                        Require(screen == "camp", "Classes can only change at camp.");
                        Require(JourneyAllocationUnlocked, "Classes unlock on floor three; innate abilities remain available.");
                        Require(command.classId != null && catalog.Classes.ContainsKey(command.classId) && catalog.Classes[command.classId].playerSelectable, "Unknown or enemy-only class.");
                        Require(journey == null || catalog.Classes[command.classId].minimumFloor <= journey.floorIndex + 1, "This class requires story floor " + catalog.Classes[command.classId].minimumFloor + ".");
                        RosterView trainee = GetRoster(command.unitId); trainee.classId = command.classId;
                        ClassStats trained = PlayerStats(trainee.id, trainee.classId); trainee.hp = Math.Min(trainee.hp, trained.hp); trainee.maxHp = trained.hp; trainee.energy = Math.Min(trainee.energy, trained.energy); trainee.maxEnergy = trained.energy; trainee.move = trained.move; break;
                    case "start":
                        Require(screen == "camp", "Start an encounter from camp.");
                        Require(PartyCount() == data.partySize, "Choose exactly " + data.partySize + " crawlers.");
                        foreach (RosterView member in roster.Values) Require(!member.selected || member.hp > 0, "Rest in the safe room to revive fallen party members first.");
                        if (generatedDungeon != null) ResumeGenerated(); else StartExploration(); break;
                    case "explore_step": Require(Math.Abs((long)command.x) + Math.Abs((long)command.y) == 1, "Choose one cardinal step."); Require(screen == "explore", "Move during exploration."); ExplorationSave cursor = exploration[Sector.id]; ExploreMove(cursor.x + command.x, cursor.y + command.y); break;
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
                    case "preview_favor":
                    case "preview":
                        RequirePlayer(); ClearPreview();
                        GameCommand proposed = CopyCommand(command); proposed.unitId = command.unitId ?? selected;
                        ActionResult candidate = ResolveAction(proposed);
                        pending = proposed; forecast = candidate; selected = proposed.unitId;
                        message = proposed.type == "preview_favor" ? "Spend 1 AI Favor and one supply. No action or movement spent. Confirm or cancel." : "Review the forecast, then confirm or cancel."; break;
                    case "confirm":
                        RequirePlayer(); Require(pending != null, "Preview an action first.");
                        GameCommand commit = pending;
                        ActionResult result = ResolveAction(commit); // Fresh validation, same resolver used by preview.
                        CommitAction(commit, result); ClearPreview();
                        CheckOutcome(); break;
                    case "cancel": ClearPreview(); message = "Forecast canceled. Nothing was spent."; break;
                    case "end_turn":
                    case "wait":
                        RequirePlayer(); ClearPreview();
                        EntityState waiting = GetActor(command.unitId ?? selected);
                        Require(waiting.Team == phase, "This unit does not own the turn.");
                        EndActivation(waiting.Id); AddLog(Label(waiting.Id) + " waits.");
                        FinishPlayerIfNeeded(); break;
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
                        SyncRosterFromBattle();
                        encounterIndex++;
                        screen = encounterIndex >= (CustomEncounter(0) != null ? 1 : data.encounters.Length) ? "complete" : "camp";
                        phase = "player";
                        if (screen == "camp") { battle = new BattleState(); units.Clear(); timed.Clear(); selected = null; }
                        message = screen == "complete" ? "Floor cleared. The audience demands another season." : "Return to the safe room: rest, equip earned gear, and inspect new skills before the next encounter.";
                        break;
                    case "retry":
                        Require(screen == "defeat", "Retry is available after defeat.");
                        // A retry is a fresh attempt: restore the starting shared supply, keeping earned XP.
                        ResetInventory(); RefreshRosterStats(true); StartEncounter(); break;
                    default: throw new ArgumentException("Unknown command: " + command.type);
                }
                AwardCommittedAchievements(command);
            }
            catch (ArgumentException ex) { message = ex.Message; }
            catch (InvalidOperationException ex) { message = ex.Message; }
            return CommandView(compactExploration);
        }
        private void Reset()
        {
            neighborhoodState = new NeighborhoodSave(); pendingNeighborhood = null; journey = null; unlockedSkillNodes.Clear(); pendingSkillNode = null; ResetDevelopment(); ResetCustomMap(); ClearScenario(); ClearExpedition(); xp = 0; audienceState = new AudienceSave(); achievementIds.Clear(); equipped.Clear(); roster.Clear(); units.Clear(); timed.Clear(); log.Clear(); exploration.Clear(); battle = new BattleState();
            foreach (RosterDef member in data.roster)
            {
                ClassStats initial = PlayerStats(member.id, member.classId); int hp = initial.hp;
                roster.Add(member.id, new RosterView { id = member.id, label = member.label, classId = member.classId, selected = member.selected && member.deployable, hp = hp, maxHp = hp, energy = initial.energy, maxEnergy = initial.energy, move = initial.move, effectiveMove = initial.move, level = 1 });
            }
            ResetHome(); ResetInventory(); battleLayoutVersion = 1; screen = "camp"; phase = "player"; encounterIndex = 0; round = 1; xp = 0; rewardChosen = false; selected = null; ClearPreview();
            message = "Choose " + data.partySize + " crawlers and their classes. Rest in the safe room to restore HP and mana between rooms.";
        }
        private void ResetInventory()
        {
            inventory.Clear(); foreach (string id in catalog.Items.Keys) inventory.Add(id, 0);
            foreach (InventoryEntry entry in data.startingInventory) inventory[entry.itemId] = entry.count;
        }
        private void StartEncounter()
        {
            battle = new BattleState(); units.Clear(); timed.Clear(); ClearPreview(); pendingDevelopment = null; pendingSkillNode = null; log.Clear();
            audienceState.favor = 0; audienceState.favorEarned = 0;
            EncounterDef encounter = Encounter;
            if (generatedDungeon != null) SetGeneratedSpawns(encounter, generatedDungeon);
            battleLayoutVersion = encounter.layoutVersion;
            if (JourneyActive && JourneyFloor.mechanic == "capture") journey.capturedIds = new string[0];
            for (int y = 0; y < encounter.height; y++) for (int x = 0; x < encounter.width; x++)
            {
                EntityState tile = new EntityState { Id = TileId(x, y), IsTile = true, Blocked = Blocked(x, y), X = x, Y = y };
                foreach (TileDef authored in encounter.tiles) if (authored.x == x && authored.y == y) tile.Tags.UnionWith(authored.tags);
                battle.Entities.Add(tile.Id, tile);
            }
            int slot = 0;
            foreach (RosterDef definition in data.roster)
            {
                RosterView member = roster[definition.id]; if (!member.selected) continue;
                ClassStats stats = PlayerStats(member.id, member.classId); CellView spawn = encounter.playerSpawns[slot++];
                AddUnit(member.id, member.label, member.classId, "player", spawn.x, spawn.y, stats.hp, stats.energy, stats.move, new string[0]);
                battle.Entities[member.id].Hp = member.hp; battle.Entities[member.id].Energy = member.energy;
            }
            foreach (SpawnDef enemy in encounter.enemies) AddUnit(enemy.id, enemy.label, enemy.classId, "enemy", enemy.x, enemy.y, enemy.hp, enemy.energy, enemy.move, enemy.tags);
            screen = "battle"; phase = "player"; round = 1; rewardChosen = false;
            selected = FirstAvailable(); message = encounter.description; ScenarioOnStart();
            AddLog(encounter.label + ": defeat all enemies. Move and act in either order, then end the crawler's turn.");
        }
        private void AddUnit(string id, string label, string classId, string team, int x, int y, int hp, int energy, int move, string[] tags)
        {
            EntityState unit = new EntityState { Id = id, ClassId = classId, Team = team, X = x, Y = y, Hp = hp, MaxHp = hp, Energy = energy };
            unit.Tags.UnionWith(tags); RosterDef definition = Definition(id); if (definition != null) { unit.GrantedAbilities.UnionWith(Grants(id, xp, equipped)); unit.Tags.UnionWith(definition.combatTags); } battle.Entities.Add(id, unit);
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
                presentationEvents.Add(new PresentationEvent { type = "move", actorId = id, targetId = id, fromX = actor.X, fromY = actor.Y, toX = cell.x, toY = cell.y });
                actor.X = cell.x; actor.Y = cell.y;
                ApplyOccupancy(battle, actor, true, log, presentationEvents);
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
            Require(string.IsNullOrEmpty(command.castModeId) || (actor.Team == "player" && string.IsNullOrEmpty(command.itemId) && string.IsNullOrEmpty(command.formId) && string.IsNullOrEmpty(command.stanceId) && command.type != "journey_capture"), "Cast modes require a learned ability cast.");
            bool favor = command.type == "preview_favor";
            if (favor) ValidateFavor(command, actor);
            Require(favor || !units[actor.Id].acted, "This crawler already used its action.");
            if (command.type == "journey_capture") return ResolveCapture(command, actor);
            if (!string.IsNullOrEmpty(command.stanceId) || !string.IsNullOrEmpty(command.formId)) return ResolveMode(command, actor);
            Require(actor.Team == phase, "This unit does not own the turn.");
            string abilityId = command.abilityId;
            ActionResult resolved;
            if (!string.IsNullOrEmpty(command.itemId))
            {
                Require(string.IsNullOrEmpty(command.castModeId), "Consumables cannot select a cast mode.");
                Require(actor.Team == "player", "Only crawlers use shared supplies.");
                Require(inventory.ContainsKey(command.itemId) && inventory[command.itemId] > 0, "No charges remain for that item.");
                abilityId = catalog.Items[command.itemId].abilityId;
                resolved = engine.ExecuteItem(battle, actor.Id, command.itemId, command.targetId);
            }
            else
            {
                Require(actor.Team != "player" || Array.IndexOf(AbilityIds(actor), abilityId) >= 0, "This ability is not unlocked for this crawler.");
                resolved = engine.Execute(battle, actor.Id, abilityId, command.targetId, actor.Team == "player" ? CastModifiers(actor.Id, abilityId, command.castModeId) : null);
            }
            if (IsTrapAbility(abilityId))
            {
                EntityState trapTile = battle.Entities[command.targetId];
                Require(trapTile.IsTile && !trapTile.Blocked, "Place traps on an open tile.");
                foreach (EntityState occupant in battle.Entities.Values) Require(occupant.IsTile || occupant.Hp <= 0 || occupant.X != trapTile.X || occupant.Y != trapTile.Y, "Place traps on an unoccupied tile.");
                foreach (TagRuleDef rule in data.tagRules) Require(!rule.consumeOnEntry || !trapTile.Tags.Contains(rule.tag), "This tile already contains a trap.");
            }
            List<string> events = new List<string>(resolved.Log);
            List<PresentationEvent> visual = new List<PresentationEvent>(resolved.Events);
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
                                Damage(occupant, rule.entryDamage, rule.tag, events, visual);
                        TransferSurfaceTags(resolved.State, occupant, visual);
                    }
            }
            ReformJourneyGhosts(resolved.State, events);
            return new ActionResult(resolved.State, events, visual);
        }
        private void CommitAction(GameCommand command, ActionResult result)
        {
            presentationEvents.AddRange(result.Events);
            BattleState previous = battle; battle = result.State; RegisterDuplicates();
            ReconcileTags(previous, battle, !string.IsNullOrEmpty(command.formId) ? command.formId : !string.IsNullOrEmpty(command.stanceId) ? command.stanceId : string.IsNullOrEmpty(command.itemId) ? command.abilityId : command.itemId);
            if (!string.IsNullOrEmpty(command.itemId)) inventory[command.itemId]--;
            foreach (string entry in result.Log) AddLog(Label(command.unitId) + ": " + entry);
            if (command.type == "preview_favor") audienceState.favor--; else units[command.unitId].acted = true;
            CommitMode(command); if (command.type != "journey_capture") PracticeCommitted(command); JourneyCommittedAction(command);
        }
        private void EndActivation(string id) { units[id].acted = true; units[id].moved = true; units[id].finished = true; }
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
            phase = "enemy"; presentationEvents.Add(new PresentationEvent { type = "phase", tag = "enemy" }); ClearPreview(); AddLog("Enemy phase.");
            RunScenarioEnemyTurn();
            List<string> enemies = UnitIds("enemy");
            foreach (string id in enemies)
            {
                if (screen != "battle") break;
                EntityState enemy = battle.Entities[id]; if (IsScenarioBoss(id)) continue; if (enemy.Hp == 0) continue;
                // Deterministic bounded legal search: evaluate every granted ability against each living target.
                GameCommand best = BestEnemyAction(id);
                if (best == null)
                {
                    Dictionary<string, int> distances = DistancesToPlayers(id);
                    List<CellView> reachable = Reachable(id); CellView destination = null; int bestDistance = int.MaxValue;
                    foreach (CellView cell in reachable)
                    {
                        int distance; if (!distances.TryGetValue(TileId(cell.x, cell.y), out distance)) continue;
                        if (distance < bestDistance) { bestDistance = distance; destination = cell; }
                    }
                    if (destination != null && (destination.x != enemy.X || destination.y != enemy.Y))
                    {
                        foreach (CellView step in FindPath(enemy.X, enemy.Y, destination.x, destination.y, enemy.Id))
                        {
                            presentationEvents.Add(new PresentationEvent { type = "move", actorId = id, targetId = id, fromX = enemy.X, fromY = enemy.Y, toX = step.x, toY = step.y });
                            enemy.X = step.x; enemy.Y = step.y;
                            ApplyOccupancy(battle, enemy, true, log, presentationEvents);
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
                ApplyOccupancy(battle, unit, false, log, presentationEvents);
                foreach (TagRuleDef rule in data.tagRules) if (unit.Tags.Contains(rule.tag) && rule.turnDamage > 0) Damage(unit, rule.turnDamage, rule.tag, log, presentationEvents);
            }
            ReconcileTags(null, battle, "terrain");
            TickTags(); TickDuplicates(); CheckOutcome(); if (screen != "battle") return;
            round++; phase = "player"; presentationEvents.Add(new PresentationEvent { type = "phase", tag = "player" });
            foreach (SavedUnit unit in units.Values)
            {
                unit.moved = false; unit.acted = false; unit.finished = false;
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
        private void ApplyOccupancy(BattleState state, EntityState unit, bool entry, List<string> events, List<PresentationEvent> visual = null)
        {
            EntityState tile = state.Entities[TileId(unit.X, unit.Y)];
            foreach (TagRuleDef rule in data.tagRules) if (tile.Tags.Contains(rule.tag))
            {
                int amount = entry ? rule.entryDamage : rule.turnDamage;
                if (amount > 0) Damage(unit, amount, rule.tag, events, visual);
            }
            TransferSurfaceTags(state, unit, visual);
            if (entry) foreach (TagRuleDef rule in data.tagRules) if (rule.consumeOnEntry && tile.Tags.Remove(rule.tag) && visual != null) visual.Add(new PresentationEvent { type = "trap_trigger", targetId = unit.Id, tag = rule.tag, toX = tile.X, toY = tile.Y });
        }
        private void TransferSurfaceTags(BattleState state, EntityState unit, List<PresentationEvent> visual = null)
        {
            EntityState tile = state.Entities[TileId(unit.X, unit.Y)];
            foreach (string tag in tile.Tags)
            {
                // Occupancy transfer is explicit data, independent from surface lifetime.
                TagRuleDef rule = TagRule(tag); if (rule != null && !string.IsNullOrEmpty(rule.occupantTag)) { if (unit.Tags.Add(rule.occupantTag) && visual != null) visual.Add(new PresentationEvent { type = "tag_add", targetId = unit.Id, tag = rule.occupantTag }); }
            }
        }
        private void Damage(EntityState target, int amount, string source, List<string> events, List<PresentationEvent> visual = null)
        {
            int before = target.Hp; target.Hp = Math.Max(0, target.Hp - amount); if (visual != null && before != target.Hp) visual.Add(new PresentationEvent { type = "damage", targetId = target.Id, tag = source, before = before, after = target.Hp, amount = before - target.Hp }); events.Add(Label(target.Id) + ": " + source + " deals " + amount + ".");
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
                if (!permanent && battle.Entities[layer.entityId].Tags.Remove(layer.tag)) presentationEvents.Add(new PresentationEvent { type = "tag_remove", targetId = layer.entityId, tag = layer.tag });
                timed.RemoveAt(i);
            }
        }
        private void CheckOutcome()
        {
            if (screen != "battle") return;
            ReformJourneyGhosts(battle, log);
            bool player = false, enemy = false;
            foreach (EntityState unit in battle.Entities.Values) if (!unit.IsTile && unit.Hp > 0) { if (unit.Team == "player") { if (unit.DuplicateSourceId == null) player = true; } else enemy = true; }
            if (!player) { screen = "defeat"; message = "Your party fell. Retry this room or begin a new run."; ClearPreview(); AddLog("Party defeated."); }
            else if (!enemy)
            {
                int oldXp = xp; screen = "victory";
                if (ActiveExpeditionEncounter != null)
                {
                    SyncRosterFromBattle(); rewardChosen = true; message = "Expedition cleared! Return to your campaign; training grants no campaign XP or loot.";
                    AddLog("Expedition victory. Your campaign build is preserved.");
                }
                else
                {
                    xp += Encounter.xp; if (ActiveScenarioEncounter == null) AwardProgression(oldXp); else SyncRosterFromBattle();
                    if (ActiveScenarioEncounter == null && !JourneyActive) GrantLoot("victory." + (CustomEncounter(0) != null ? data.encounters[0].id : Encounter.id), true);
                    AwardHomeVictory(); rewardChosen = false; message = "Room cleared! Choose one sponsor reward."; AddLog("Victory: +" + Encounter.xp + " XP.");
                }
                AudienceCommitted("victory");

                ClearPreview();
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
            if (!ScenarioPassable(x, y, actorId)) return false;
            if (x < 0 || y < 0 || x >= Encounter.width || y >= Encounter.height || Blocked(x, y)) return false;
            foreach (EntityState unit in battle.Entities.Values) if (!unit.IsTile && unit.Hp > 0 && unit.Id != actorId && unit.X == x && unit.Y == y) return false;
            return true;
        }
        private static TileDef[] BattleTiles(EncounterDef encounter, int version)
        {
            Require(version == 0 || version == encounter.layoutVersion, "Unknown encounter layout version.");
            return version == 0 && encounter.legacyTiles.Length > 0 ? encounter.legacyTiles : encounter.tiles;
        }
        private bool Blocked(int x, int y) { foreach (TileDef tile in BattleTiles(Encounter, battleLayoutVersion)) if (tile.x == x && tile.y == y) return tile.blocked; return false; }
        private Dictionary<string, int> DistancesToPlayers(string actorId)
        {
            // Reverse BFS from walkable attack-adjacent cells gives route distance around walls.
            // Manhattan distance could leave an enemy stuck when the route first leads away.
            Dictionary<string, int> result = new Dictionary<string, int>(); Queue<CellView> queue = new Queue<CellView>();
            foreach (string id in UnitIds("player"))
            {
                EntityState player = battle.Entities[id]; if (player.Hp == 0) continue;
                foreach (CellView cell in Neighbors(player.X, player.Y)) if (Passable(cell.x, cell.y, actorId) && !result.ContainsKey(TileId(cell.x, cell.y))) { result.Add(TileId(cell.x, cell.y), 0); queue.Enqueue(cell); }
            }
            while (queue.Count > 0)
            {
                CellView cell = queue.Dequeue(); int distance = result[TileId(cell.x, cell.y)];
                foreach (CellView next in Neighbors(cell.x, cell.y)) if (Passable(next.x, next.y, actorId) && !result.ContainsKey(TileId(next.x, next.y))) { result.Add(TileId(next.x, next.y), distance + 1); queue.Enqueue(next); }
            }
            return result;
        }
        private RosterDef Definition(string id) { return Array.Find(data.roster, r => r.id == id); }
        private List<string> PartyOrder() { List<string> result = new List<string>(); foreach (RosterDef member in data.roster) if (units.ContainsKey(member.id) && units[member.id].team == "player") result.Add(member.id); foreach (string id in UnitIds("player")) if (battle.Entities[id].DuplicateSourceId != null) result.Add(id); return result; }
        private string ArtId(string id) { if (battle.Entities.ContainsKey(id) && battle.Entities[id].DuplicateSourceId != null) return ArtId(battle.Entities[id].DuplicateSourceId); RosterDef member = Definition(id); if (member != null) return member.artId; SpawnDef enemy = Array.Find(Encounter.enemies, e => e.id == id); return enemy == null ? null : enemy.artId; }
        private int EffectiveMove(string id) { return EffectiveMove(battle.Entities[id], units[id].move); }
        private int EffectiveMove(EntityState entity, int baseMove) { int value = baseMove; foreach (TagRuleDef rule in data.tagRules) if (entity.Tags.Contains(rule.tag)) value += rule.moveBonus - rule.movePenalty; return Math.Max(0, value); }
        private StatusView[] Statuses(string id) { List<StatusView> result = new List<StatusView>(); foreach (string tag in Sorted(battle.Entities[id].Tags)) { TimedTag layer = timed.Find(t => t.entityId == id && t.tag == tag); result.Add(new StatusView { tag = tag, source = layer == null ? "" : layer.source, remainingRounds = battle.Entities[id].DuplicateSourceId != null && tag == "status.clockwork" ? battle.Entities[id].DuplicateRounds : layer == null ? 0 : layer.remainingRounds }); } return result.ToArray(); }
        private string[] AbilityIds(EntityState actor) { if (actor.DuplicateSourceId != null) return Sorted(actor.GrantedAbilities); List<string> result = new List<string>(actor.Team == "player" && !JourneyAllocationUnlocked ? new string[0] : catalog.Classes[actor.ClassId].abilityIds); RosterDef definition = Definition(actor.Id); if (definition != null) foreach (string id in Grants(actor.Id, xp, equipped)) if (!result.Contains(id)) result.Add(id); return result.ToArray(); }
        private string FirstAvailable() { foreach (string id in PartyOrder()) if (battle.Entities[id].Hp > 0 && !units[id].finished) return id; return null; }
        private List<string> UnitIds(string team) { List<string> ids = new List<string>(); foreach (SavedUnit unit in units.Values) if (unit.team == team) ids.Add(unit.id); ids.Sort(StringComparer.Ordinal); return ids; }
        private List<string> SortedUnitIds() { List<string> ids = new List<string>(units.Keys); ids.Sort(StringComparer.Ordinal); return ids; }
        private string Label(string id) { return id != null && units.ContainsKey(id) ? units[id].label : id; }
        private static string TileId(int x, int y) { return "tile." + x + "." + y; }
        private ClassStats Stats(string id) { foreach (ClassStats stats in data.classStats) if (stats.classId == id) return stats; throw new ArgumentException("Missing class stats: " + id); }
        private TagRuleDef TagRule(string tag) { foreach (TagRuleDef rule in data.tagRules) if (rule.tag == tag) return rule; return null; }
        private int PartyCount() { int count = 0; foreach (RosterView member in roster.Values) if (member.selected) count++; return count; }
        private RosterView GetRoster(string id) { Require(id != null && roster.ContainsKey(id), "Unknown crawler."); return roster[id]; }
        private EntityState GetUnit(string id) { Require(id != null && units.ContainsKey(id), "Unknown unit."); return battle.Entities[id]; }
        private EntityState GetActor(string id) { EntityState unit = GetUnit(id); Require(unit.Hp > 0 && !units[id].finished, "This unit is defeated or already acted."); return unit; }
        private void RequirePlayer() { Require(screen == "battle" && phase == "player", "Wait for the crawler phase in battle."); }
        private static void Require(bool condition, string error) { if (!condition) throw new ArgumentException(error); }
        private void AddLog(string entry) { log.Add(entry); TrimLog(); }
        private void TrimLog() { if (log.Count > 60) log.RemoveRange(0, log.Count - 60); }
        private static string[] Sorted(HashSet<string> tags) { string[] values = new string[tags.Count]; tags.CopyTo(values); Array.Sort(values, StringComparer.Ordinal); return values; }
        private static GameCommand CopyCommand(GameCommand c) { return new GameCommand { type = c.type, unitId = c.unitId, targetId = c.targetId, abilityId = c.abilityId, castModeId = c.castModeId, itemId = c.itemId, classId = c.classId, rewardId = c.rewardId, equipmentId = c.equipmentId, stanceId = c.stanceId, formId = c.formId, x = c.x, y = c.y }; }

        public GameView GetView(bool includeTargets = true)
        {
            GameView view = new GameView { screen = screen, message = message, phase = phase, encounterIndex = encounterIndex, encounterCount = data.encounters.Length, encounterName = Encounter.label, round = round, width = Encounter.width, height = Encounter.height, xp = xp, selectedUnitId = selected, partyCount = PartyCount(), partyCapacity = data.partySize, canConfirm = pending != null };
            view.decorations = battleLayoutVersion == 0 && Encounter.legacyTiles.Length > 0 ? new MapPlacement[0] : Array.ConvertAll(Encounter.decorations, p => new MapPlacement { id = p.id, assetId = p.assetId, layer = p.layer, x = p.x, y = p.y, rotation = p.rotation, blocksMovement = p.blocksMovement });
            view.audience = BuildAudienceView(); view.achievementIds = achievementIds.ToArray();
            view.partyOrder = PartyOrder().ToArray();
            List<PresentationEvent> output = new List<PresentationEvent>(presentationEvents); if (forecast != null) foreach (PresentationEvent ev in forecast.Events) { ev.preview = true; output.Add(ev); }
            for (int i = 0; i < output.Count; i++) output[i].sequence = i; view.events = output.ToArray();
            List<RosterView> rosterViews = new List<RosterView>();
            foreach (RosterDef member in data.roster) { RosterView r = roster[member.id]; rosterViews.Add(new RosterView { id = r.id, label = r.label, classId = r.classId, stanceId = r.stanceId, formId = r.formId, specialtyClassId = r.specialtyClassId, specialtyFloor = r.specialtyFloor, specialtyClassIds = member.specialtyClassIds, specialtyAvailable = screen == "camp" && JourneyAllocationUnlocked && r.specialtyFloor == 0 && member.specialtyClassIds.Length > 0, artId = member.artId, deployable = member.deployable, innateAbilityIds = member.innateAbilityIds, selected = r.selected, hp = battle.Entities.ContainsKey(r.id) ? battle.Entities[r.id].Hp : r.hp, maxHp = PlayerStats(r.id, r.classId).hp, energy = battle.Entities.ContainsKey(r.id) ? battle.Entities[r.id].Energy : r.energy, maxEnergy = PlayerStats(r.id, r.classId).energy, move = PlayerStats(r.id, r.classId).move, effectiveMove = battle.Entities.ContainsKey(r.id) ? EffectiveMove(r.id) : PlayerStats(r.id, r.classId).move, level = LevelAt(xp), equippedIds = equipped.FindAll(g => g.unitId == r.id).ConvertAll(g => g.equipmentId).ToArray() }); }
            view.roster = rosterViews.ToArray();
            List<ClassView> classes = new List<ClassView>(); foreach (ClassDef c in catalog.Classes.Values) if (c.playerSelectable) classes.Add(new ClassView { id = c.id, label = c.label, minimumFloor = c.minimumFloor, enabled = JourneyAllocationUnlocked && (journey == null || c.minimumFloor <= journey.floorIndex + 1), disabledReason = !JourneyAllocationUnlocked ? "Classes unlock on floor three" : journey != null && c.minimumFloor > journey.floorIndex + 1 ? "Requires floor " + c.minimumFloor : "", abilityIds = (string[])c.abilityIds.Clone() }); view.classes = classes.ToArray();
            List<UnitView> unitViews = new List<UnitView>();
            foreach (string id in SortedUnitIds())
            {
                EntityState e = battle.Entities[id]; SavedUnit u = units[id];
                unitViews.Add(new UnitView { duplicateSourceId = e.DuplicateSourceId, duplicateCasterId = e.DuplicateCasterId, duplicateRounds = e.DuplicateRounds, id = id, label = u.label, classId = e.ClassId, stanceId = roster.ContainsKey(id) ? roster[id].stanceId : null, formId = roster.ContainsKey(id) ? roster[id].formId : null, team = e.Team, x = e.X, y = e.Y, hp = e.Hp, maxHp = e.MaxHp, energy = e.Energy, maxEnergy = u.maxEnergy, move = u.move, effectiveMove = EffectiveMove(e.Id), level = e.Team == "player" ? LevelAt(xp) : 1, artId = ArtId(e.Id), abilityIds = AbilityIds(e), statuses = Statuses(e.Id), selected = selected == id, moved = u.moved, acted = u.acted, finished = u.finished, tags = Sorted(e.Tags) });
            }
            view.units = unitViews.ToArray();
            List<TileView> tileViews = new List<TileView>();
            for (int y = 0; y < Encounter.height; y++) for (int x = 0; x < Encounter.width; x++)
            {
                string id = TileId(x, y); EntityState tile; battle.Entities.TryGetValue(id, out tile);
                tileViews.Add(new TileView { id = id, x = x, y = y, blocked = Blocked(x, y), tags = tile == null ? (generatedDungeon == null ? new string[0] : Array.Find(Encounter.tiles, t => t.x == x && t.y == y)?.tags ?? new string[0]) : Sorted(tile.Tags) });
            }
            view.tiles = tileViews.ToArray();
            EntityState actor = null; if (selected != null && units.ContainsKey(selected)) actor = battle.Entities[selected];
            bool active = actor != null && screen == "battle" && phase == "player" && actor.Hp > 0 && !units[selected].finished;
            view.canAct = active && !units[selected].acted; view.canMove = active && !units[selected].moved;
            if (includeTargets && view.canMove) view.reachable = Reachable(selected).ToArray();
            List<AbilityView> abilityViews = new List<AbilityView>();
            if (actor != null) foreach (string id in AbilityIds(actor))
            {
                AbilityDef a = catalog.Abilities[id]; SkillPracticeSave savedPractice = practices.Find(p => p.unitId == actor.Id && p.abilityId == id); SkillPracticeView practice = PracticeView(actor.Id, id, savedPractice == null ? 0 : savedPractice.uses); int effectiveCost = Math.Max(0, a.cost - Modifiers(actor.Id, id).costReduction); abilityViews.Add(new AbilityView { id = id, label = a.label, target = a.target, range = AbilityScaling.Apply(a, Modifiers(actor.Id, id)).range, rank = practice.rank, maxRank = practice.maxRank, uses = practice.uses, nextRankUses = practice.nextRankUses, cost = effectiveCost, enabled = view.canAct && actor.Energy >= effectiveCost, description = Describe(a, Modifiers(actor.Id, id)), disabledReason = !view.canAct ? "Action unavailable" : actor.Energy < effectiveCost ? "Insufficient mana" : "", targetIds = includeTargets && view.canAct && actor.Energy >= effectiveCost ? LegalTargets(actor, a, null) : new string[0] });
            }
            foreach (AbilityView abilityView in abilityViews)
            {
                abilityView.castModes = CastModeViews(actor.Id, abilityView.id, abilityView.rank, Modifiers(actor.Id, abilityView.id), actor, view.canAct, includeTargets);
                foreach (AbilityCastModeView mode in abilityView.castModes) if (mode.enabled) { abilityView.enabled = true; abilityView.disabledReason = ""; }
            }
            view.abilities = abilityViews.ToArray();
            List<ItemView> itemViews = new List<ItemView>(); foreach (ItemDef item in catalog.Items.Values)
            { AbilityDef a = catalog.Abilities[item.abilityId]; itemViews.Add(new ItemView { favorTargetIds = includeTargets ? LegalFavorTargets(actor, item) : new string[0], id = item.id, label = item.label, abilityId = item.abilityId, count = inventory[item.id], target = a.target, range = a.range, description = Describe(a), disabledReason = !view.canAct ? "Action unavailable" : inventory[item.id] == 0 ? "No charges" : "", targetIds = includeTargets && view.canAct && inventory[item.id] > 0 ? LegalTargets(actor, a, item.id) : new string[0] }); }
            view.items = itemViews.ToArray();
            if (forecast != null)
            {
                List<ForecastView> changes = new List<ForecastView>();
                foreach (EntityState next in forecast.State.Entities.Values)
                {
                    EntityState before;
                    if (!battle.Entities.TryGetValue(next.Id, out before)) { changes.Add(new ForecastView { targetId = next.Id, label = "Clockwork " + Label(next.DuplicateSourceId), afterHp = next.Hp, afterMaxHp = next.MaxHp, afterX = next.X, afterY = next.Y, afterMove = next.DuplicateMove }); continue; }
                    if (before.MaxHp != next.MaxHp || (pending != null && next.Id == pending.unitId && (!string.IsNullOrEmpty(pending.formId) || !string.IsNullOrEmpty(pending.stanceId))) || before.Hp != next.Hp || before.Energy != next.Energy || before.X != next.X || before.Y != next.Y || !before.Tags.SetEquals(next.Tags))
                        changes.Add(new ForecastView { targetId = next.Id, label = Label(next.Id), beforeHp = before.Hp, afterHp = next.Hp, beforeMaxHp = before.MaxHp, afterMaxHp = next.MaxHp, beforeMaxEnergy = units.ContainsKey(next.Id) ? units[next.Id].maxEnergy : 0, afterMaxEnergy = ForecastModeStat(next.Id, true), beforeMove = units.ContainsKey(next.Id) ? EffectiveMove(next.Id) : 0, afterMove = ForecastModeStat(next.Id, false), beforeX = before.X, beforeY = before.Y, afterX = next.X, afterY = next.Y, beforeEnergy = before.Energy, afterEnergy = next.Energy, beforeTags = Sorted(before.Tags), afterTags = Sorted(next.Tags) });
                }
                changes.Sort((a, b) => StringComparer.Ordinal.Compare(a.targetId, b.targetId)); view.forecast = changes.ToArray();
            }
            List<string> visibleLog = new List<string>(log); if (forecast != null) foreach (string entry in forecast.Log) visibleLog.Add("Forecast: " + entry); view.log = visibleLog.ToArray();
            if (screen == "victory" && !rewardChosen)
            { List<RewardView> rewards = new List<RewardView>(); foreach (RewardDef reward in data.rewards) rewards.Add(new RewardView { id = reward.id, label = reward.label, description = reward.description }); view.rewards = rewards.ToArray(); }
            if (screen == "explore") view.exploration = generatedDungeon == null ? ExplorationView() : GeneratedExplorationView();
            view.home = HomeView(); view.journey = JourneyView(); if (JourneyActive) view.encounterCount = 8;
            view.neighborhood = BuildNeighborhoodView(); PopulateProgression(view); PopulateModes(view); PopulateDevelopment(view); PopulateSkillTree(view); PopulateCustomMap(view); view.scenarios = ScenarioOptions(); view.scenario = ScenarioView(); view.expeditions = ExpeditionOptions(); view.expedition = ExpeditionView();
            return view;
        }
        private string[] LegalTargets(EntityState actor, AbilityDef ability, string itemId, string castModeId = null)
        {
            int effectiveRange = string.IsNullOrEmpty(itemId) ? AbilityScaling.Apply(ability, Modifiers(actor.Id, ability.id)).range : ability.range;
            List<string> targets = new List<string>();
            foreach (EntityState target in battle.Entities.Values)
            {
                if (Math.Abs(actor.X - target.X) + Math.Abs(actor.Y - target.Y) > effectiveRange) continue;
                if ((ability.target == "tile") != target.IsTile) continue;
                try { ResolveAction(new GameCommand { unitId = actor.Id, abilityId = ability.id, itemId = itemId, castModeId = castModeId, targetId = target.Id }); targets.Add(target.Id); }
                catch (ArgumentException) { }
                catch (InvalidOperationException) { }
            }
            targets.Sort(StringComparer.Ordinal); return targets.ToArray();
        }
        private string Describe(AbilityDef ability, ActionModifiers modifiers = null)
        {
            ability = AbilityScaling.Apply(ability, modifiers); modifiers = null;
            List<string> parts = new List<string>();
            foreach (EffectDef effect in ability.effects)
            {
                if (effect.op == "Damage") parts.Add((effect.amount + (modifiers == null ? 0 : modifiers.damageBonus)) + " damage");
                else if (effect.op == "DuplicatePet") parts.Add("Create two controllable clockwork pet copies on adjacent open tiles for " + effect.summonRounds + " rounds; each has " + effect.summonHp + " HP, " + effect.summonMove + " movement, no Mana and the pet’s free attacks. Only allied pets are eligible; one active pair per caster. Tactical adaptation");
                else if (effect.op == "Teleport") parts.Add("Teleport to an unoccupied tile");
                else if (effect.op == "Push") parts.Add("Push " + effect.amount + " tile(s)");
                else if (effect.op == "Heal") parts.Add("Restore " + (effect.amount + (modifiers == null ? 0 : modifiers.healBonus)) + " HP");
                else
                {
                    string label = DisplayTag(effect.tag);
                    TagRuleDef placement = TagRule(effect.tag);
                    if (effect.op == "AddTag" && placement != null && placement.consumeOnEntry) { parts.Add("One-use trap on empty tile: next entrant (ally or enemy) takes " + placement.entryDamage + " damage and gains " + DisplayTag(placement.occupantTag) + "; trap consumed"); continue; }
                    string protection = "";
                    if (effect.op == "AddTag") foreach (ReactionDef rule in catalog.Reactions)
                        if (rule.damageReduction > 0 && Array.IndexOf(rule.target.all, effect.tag) >= 0)
                        { protection = " (" + rule.damageReduction + " damage protection on a matching hit)"; break; }
                    if (effect.op == "AddTag" && placement != null && placement.moveBonus > 0) protection += " (+" + placement.moveBonus + " movement for " + placement.durationRounds + " rounds; tactical Mana/turn cadence, not the novel’s daily cooldown)";
                    if (effect.op == "AddTag" && placement != null)
                    {
                        if (placement.durationRounds > 0 && placement.moveBonus == 0) protection += " (" + placement.durationRounds + " rounds)";
                        if (placement.turnDamage > 0) protection += " (" + placement.turnDamage + " damage each round)";
                        if (placement.movePenalty > 0) protection += " (-" + placement.movePenalty + " movement)";
                        if (placement.energyPenalty > 0) protection += " (-" + placement.energyPenalty + " Mana each round)";
                    }
                    parts.Add((effect.op == "AddTag" ? "Apply " : "Remove ") + label + protection);
                }
            }
            if (ability.incomingTags.Length > 0)
            {
                List<string> labels = new List<string>(); foreach (string tag in ability.incomingTags) labels.Add(DisplayTag(tag));
                parts.Add("Triggers " + string.Join(" / ", labels) + " reactions");
            }
            if (!string.IsNullOrEmpty(ability.requiredTargetTag)) parts.Add("Requires target: " + DisplayTag(ability.requiredTargetTag));
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
            GameSave save = new GameSave { battleLayoutVersion = battleLayoutVersion, audience = CaptureAudience(), neighborhood = CaptureNeighborhood(), home = CaptureHome(), journey = CaptureJourney(), expedition = CaptureExpedition(), skillTree = CaptureSkillTree(), development = CaptureDevelopment(), customMap = ExportCustomMap(), generatedDungeon = CopyGenerated(generatedDungeon), generatedCampaign = CaptureCampaign(), scenario = CaptureScenario(), achievementIds = achievementIds.ToArray(), activationVersion = 1, progressionVersion = 1, equipped = equipped.ConvertAll(g => new EquipmentSlotSave { unitId = g.unitId, equipmentId = g.equipmentId }).ToArray(), contentVersion = data.contentVersion, screen = screen, phase = phase, selectedUnitId = selected, encounterIndex = encounterIndex, round = round, xp = xp, rewardChosen = rewardChosen };
            save.roster = GetView(false).roster;
            List<InventoryEntry> entries = new List<InventoryEntry>(); foreach (ItemDef item in catalog.Items.Values) entries.Add(new InventoryEntry { itemId = item.id, count = inventory[item.id] }); save.inventory = entries.ToArray();
            List<SavedUnit> savedUnits = new List<SavedUnit>();
            foreach (string id in SortedUnitIds())
            {
                EntityState entity = battle.Entities[id]; SavedUnit unit = units[id];
                savedUnits.Add(new SavedUnit { duplicateSourceId = entity.DuplicateSourceId, duplicateCasterId = entity.DuplicateCasterId, duplicateRounds = entity.DuplicateRounds, id = id, label = unit.label, classId = entity.ClassId, team = entity.Team, x = entity.X, y = entity.Y, hp = entity.Hp, maxHp = entity.MaxHp, energy = entity.Energy, maxEnergy = unit.maxEnergy, move = unit.move, moved = unit.moved, acted = unit.acted, finished = unit.finished, tags = Sorted(entity.Tags), permanentTags = (string[])unit.permanentTags.Clone() });
            }
            save.units = savedUnits.ToArray();
            if (battle.Entities.Count > 0) save.tiles = GetView(false).tiles;
            List<TimedTag> layers = new List<TimedTag>(); foreach (TimedTag layer in timed) layers.Add(new TimedTag { entityId = layer.entityId, tag = layer.tag, source = layer.source, remainingRounds = layer.remainingRounds }); save.timedTags = layers.ToArray();
            save.exploration = ExportExploration(); save.log = log.ToArray(); return save;
        }
        public GameView ImportSave(GameSave save)
        {
            presentationEvents.Clear();
            try
            {
                ValidateNeighborhoodSaveGraph(save);
                Require(save != null && save.schemaVersion == 1 && (save.contentVersion == data.contentVersion || Array.IndexOf(data.compatibleContentVersions, save.contentVersion) >= 0), "Save version does not match this content pack.");
                Require(save.battleLayoutVersion >= 0 && save.battleLayoutVersion <= 1, "Unknown battle layout version.");
                Require(save.progressionVersion == 0 || save.progressionVersion == 1, "Unknown progression save version.");
                save = MigrateCompatibleSave(save);
                ValidateCampaignSave(save);
                Require(save.screen == "camp" || save.screen == "explore" || save.screen == "battle" || save.screen == "victory" || save.screen == "defeat" || save.screen == "complete", "Invalid save screen.");
                Require(save.phase == "player" || (save.phase == "enemy" && (save.screen == "victory" || save.screen == "defeat")), "Invalid save phase.");
                int campaignLength = save.journey == null ? data.encounters.Length : 8;
                Require(save.encounterIndex >= 0 && save.encounterIndex < campaignLength + (save.screen == "complete" || save.expedition != null ? 1 : 0), "Invalid encounter index.");
                Require(save.screen != "complete" || save.generatedDungeon != null || save.encounterIndex == (save.customMap != null ? 1 : campaignLength), "Incomplete floor marked complete.");
                Require((save.screen != "battle" && save.screen != "defeat") || !save.rewardChosen, "Reward cannot precede victory.");
                Require(save.screen != "complete" || save.rewardChosen || data.rewards.Length == 0, "Completed floor is missing its final reward choice.");
                Require(save.round > 0 && save.round <= 100000, "Invalid round.");
                Require(save.activationVersion >= 0 && save.activationVersion <= 1, "Unknown activation save version.");
                Require(save.roster != null && save.units != null && save.tiles != null && save.inventory != null && save.timedTags != null && save.log != null, "Save arrays cannot be null.");
                Require(save.roster.Length == data.roster.Length && save.inventory.Length <= catalog.Items.Count && save.log.Length <= 60, "Invalid save collection lengths.");
                EncounterDef candidateJourney = ValidateJourney(save);
                int expectedXp = 0;
                if (save.journey != null) expectedXp = JourneyExpectedXp(save);
                else
                {
                    for (int i = 0; i < Math.Min(save.encounterIndex, data.encounters.Length); i++) expectedXp += data.encounters[i].xp;
                    if (save.screen == "victory" && save.expedition == null && save.scenario == null) expectedXp += data.encounters[save.encounterIndex].xp;
                }
                if (save.generatedDungeon != null && save.generatedDungeon.floorPlan != null) expectedXp = CampaignWins(save.generatedCampaign, save.generatedDungeon, save.screen) * data.encounters[0].xp;
                else if (save.generatedDungeon != null && save.generatedDungeon.cleared) expectedXp = data.encounters[0].xp;
                Require(save.scenario != null || save.expedition != null || save.xp == expectedXp, "Save XP does not match its completed encounters.");
                ValidateAchievements(save.achievementIds);
                AudienceSave nextAudience = ValidateAudience(save.audience);
                string[] nextAchievements = (string[])save.achievementIds.Clone();
                save = UpgradeProgressionSave(save);
                List<EquipmentSlotSave> nextEquipment = ValidateEquipment(save);
                List<string> nextSkillNodes = ValidateSkillTree(save);
                NeighborhoodSave nextNeighborhood = ValidateNeighborhood(save);
                HomeSave nextHome = ValidateHome(save);
                DevelopmentSave nextDevelopment = ValidateDevelopment(save); List<StatAllocationSave> nextAllocations = new List<StatAllocationSave>(nextDevelopment.allocated);
                EncounterDef candidateExpedition = ValidateExpedition(save);
                EncounterDef candidateScenario = ValidateScenario(save); EncounterDef candidateCustom = ValidateCustomMap(save);
                Require((candidateScenario == null ? 0 : 1) + (candidateCustom == null ? 0 : 1) + (candidateExpedition == null ? 0 : 1) <= 1, "A save cannot combine standalone missions.");
                Dictionary<string, RosterView> nextRoster = new Dictionary<string, RosterView>(); int party = 0;
                foreach (RosterView member in save.roster)
                {
                    Require(member != null && member.id != null && roster.ContainsKey(member.id) && !nextRoster.ContainsKey(member.id) && member.classId != null && catalog.Classes.ContainsKey(member.classId) && catalog.Classes[member.classId].playerSelectable, "Invalid saved roster.");
                    RosterDef definition = Array.Find(data.roster, r => r.id == member.id);
                    Require(save.journey == null || member.classId == definition.classId || catalog.Classes[member.classId].minimumFloor <= save.journey.floorIndex + 1, "Saved class requires a later story floor.");
                    ValidateSpecialty(member, definition, save);
                    ClassStats stats = PlayerStats(member.id, member.classId, save.xp, nextEquipment); ApplyAllocatedStats(stats, member.id, nextAllocations); ApplyTreeStats(stats, member.id, nextSkillNodes); ApplyModes(stats, member.id, member.stanceId, member.formId);
                    Require(member.hp >= 0 && member.hp <= stats.hp && member.maxHp == stats.hp && member.energy >= 0 && member.energy <= stats.energy && member.maxEnergy == stats.energy, "Invalid roster health or mana.");
                    nextRoster.Add(member.id, new RosterView { id = member.id, label = definition.label, classId = member.classId, stanceId = member.stanceId, formId = member.formId, specialtyClassId = member.specialtyClassId, specialtyFloor = member.specialtyFloor, selected = member.selected, hp = member.hp, maxHp = member.maxHp, energy = member.energy, maxEnergy = member.maxEnergy, move = stats.move, level = LevelAt(save.xp) }); Require(!member.selected || definition.deployable, "Advisor cannot deploy."); if (member.selected) party++;
                }
                Require(party <= data.partySize && (save.screen == "camp" || party == data.partySize), "Invalid party size.");
                Dictionary<string, int> nextInventory = new Dictionary<string, int>();
                foreach (InventoryEntry item in save.inventory)
                {
                    Require(item != null && item.itemId != null && catalog.Items.ContainsKey(item.itemId) && !nextInventory.ContainsKey(item.itemId) && item.count >= 0 && item.count <= 10000, "Invalid saved inventory.");
                    nextInventory.Add(item.itemId, item.count);
                }
                foreach (ItemDef item in catalog.Items.Values) if (!nextInventory.ContainsKey(item.id)) { Require(save.audience == null && IsTrapItem(item.id), "Missing saved supply."); nextInventory.Add(item.id, 0); }
                Require(save.generatedDungeon == null || save.customMap != null, "Generated dungeon requires a custom map.");
                List<ExplorationSave> nextExploration = save.generatedDungeon == null ? ValidateExploration(save) : new List<ExplorationSave>();
                bool hasBattle = save.screen != "camp" && save.screen != "explore" && !(save.generatedDungeon != null && save.screen == "complete");
                EncounterDef encounter = candidateExpedition ?? candidateScenario ?? candidateCustom ?? candidateJourney ?? data.encounters[Math.Min(save.encounterIndex, data.encounters.Length - 1)];
                TileDef[] authoredTiles = BattleTiles(encounter, save.battleLayoutVersion);
                ValidateDuplicatePairs(save);
                int duplicateCount = 0; foreach (SavedUnit candidate in save.units) if (candidate != null && candidate.duplicateSourceId != null) duplicateCount++;
                Require(duplicateCount <= data.partySize * 2 && save.units.Length == (hasBattle ? data.partySize + encounter.enemies.Length + duplicateCount : 0), "Saved unit count does not match encounter.");
                Require(save.tiles.Length == (hasBattle ? encounter.width * encounter.height : 0), "Saved map size does not match encounter.");
                BattleState nextBattle = new BattleState(); Dictionary<string, SavedUnit> nextUnits = new Dictionary<string, SavedUnit>(); HashSet<string> occupied = new HashSet<string>();
                foreach (TileView tile in save.tiles)
                {
                    Require(tile != null && tile.id == TileId(tile.x, tile.y) && tile.x >= 0 && tile.y >= 0 && tile.x < encounter.width && tile.y < encounter.height && !nextBattle.Entities.ContainsKey(tile.id), "Invalid saved tile.");
                    TileDef authored = Array.Find(authoredTiles, t => t.x == tile.x && t.y == tile.y);
                    Require(tile.blocked == (authored != null && authored.blocked), "Save changed authored walls.");
                    ValidateTags(tile.tags); EntityState entity = new EntityState { Id = tile.id, IsTile = true, Blocked = tile.blocked, X = tile.x, Y = tile.y }; entity.Tags.UnionWith(tile.tags); nextBattle.Entities.Add(tile.id, entity);
                }
                bool playerAlive = false, enemyAlive = false;
                foreach (SavedUnit unit in save.units)
                {
                    Require(unit != null && unit.id != null && !nextBattle.Entities.ContainsKey(unit.id) && unit.classId != null && catalog.Classes.ContainsKey(unit.classId), "Invalid saved unit.");
                    string label; int hp, energy, move;
                    Require(unit.duplicateSourceId != null || unit.duplicateCasterId == null && unit.duplicateRounds == 0, "Orphaned duplicate metadata.");
                    if (unit.duplicateSourceId != null)
                        ValidateDuplicate(unit, save, nextRoster, nextEquipment, nextAllocations, nextSkillNodes, out hp, out energy, out move, out label);
                    else if (unit.team == "player")
                    {
                        Require(nextRoster.ContainsKey(unit.id) && nextRoster[unit.id].selected && nextRoster[unit.id].classId == unit.classId, "Saved party member not deployed.");
                        ClassStats stats = PlayerStats(unit.id, unit.classId, save.xp, nextEquipment); ApplyAllocatedStats(stats, unit.id, nextAllocations); ApplyTreeStats(stats, unit.id, nextSkillNodes); ApplyModes(stats, unit.id, nextRoster[unit.id].stanceId, nextRoster[unit.id].formId); hp = stats.hp; energy = stats.energy; move = stats.move; label = nextRoster[unit.id].label; if (unit.hp > 0) playerAlive = true;
                    }
                    else
                    {
                        SpawnDef spawn = Array.Find(encounter.enemies, e => e.id == unit.id);
                        Require(unit.team == "enemy" && spawn != null && spawn.classId == unit.classId, "Unknown saved enemy.");
                        hp = spawn.hp; energy = spawn.energy; move = spawn.move; label = spawn.label; if (unit.hp > 0) enemyAlive = true;
                    }
                    Require(unit.hp >= 0 && unit.hp <= hp && unit.maxHp == hp && unit.energy >= 0 && unit.energy <= energy && unit.maxEnergy == energy && unit.move == move, "Saved stats do not match content.");
                    Require(unit.x >= 0 && unit.y >= 0 && unit.x < encounter.width && unit.y < encounter.height, "Unit outside board.");
                    TileDef wall = Array.Find(authoredTiles, t => t.x == unit.x && t.y == unit.y);
                    Require(wall == null || !wall.blocked, "Unit inside wall.");
                    if (unit.hp > 0) Require(occupied.Add(TileId(unit.x, unit.y)), "Living units overlap.");
                    Require(!unit.finished || (unit.acted && unit.moved), "Invalid activation flags."); ValidateTags(unit.tags); ValidateTags(unit.permanentTags);
                    SpawnDef seed = Array.Find(encounter.enemies, e => e.id == unit.id);
                    foreach (string tag in unit.permanentTags) Require(seed != null && Array.IndexOf(seed.tags, tag) >= 0 || Definition(unit.id) != null && Array.IndexOf(Definition(unit.id).combatTags, tag) >= 0, "Saved permanent tag is not an authored unit seed.");
                    foreach (string tag in unit.permanentTags) Require(Array.IndexOf(unit.tags, tag) >= 0, "Permanent tag absent from saved unit.");
                    EntityState entity = new EntityState { DuplicateSourceId = unit.duplicateSourceId, DuplicateCasterId = unit.duplicateCasterId, DuplicateRounds = unit.duplicateRounds, DuplicateMove = unit.move, Id = unit.id, ClassId = unit.classId, Team = unit.team, X = unit.x, Y = unit.y, Hp = unit.hp, MaxHp = hp, Energy = unit.energy };
                    entity.Tags.UnionWith(unit.tags); RosterDef memberDefinition = Definition(unit.id); if (memberDefinition != null) { entity.Tags.UnionWith(memberDefinition.combatTags); } if (memberDefinition != null) entity.GrantedAbilities.UnionWith(Grants(unit.id, save.xp, nextEquipment, nextSkillNodes, unit.classId, nextRoster[unit.id].specialtyClassId ?? "", save.journey == null ? 18 : save.journey.floorIndex + 1)); nextBattle.Entities.Add(unit.id, entity);
                    nextUnits.Add(unit.id, new SavedUnit { id = unit.id, label = label, classId = unit.classId, team = unit.team, maxEnergy = energy, move = move, moved = unit.moved, acted = unit.acted, finished = save.activationVersion == 0 ? unit.acted : unit.finished, permanentTags = (string[])unit.permanentTags.Clone() });
                }
                foreach (EntityState copy in nextBattle.Entities.Values) if (copy.DuplicateSourceId != null) { EntityState source = nextBattle.Entities[copy.DuplicateSourceId]; foreach (string grant in catalog.Classes[source.ClassId].abilityIds) if (catalog.Abilities[grant].cost == 0) copy.GrantedAbilities.Add(grant); foreach (string grant in Grants(source.Id, save.xp, nextEquipment, nextSkillNodes, source.ClassId, nextRoster[source.Id].specialtyClassId ?? "", save.journey == null ? 18 : save.journey.floorIndex + 1)) if (catalog.Abilities[grant].cost == 0) copy.GrantedAbilities.Add(grant); }
                if (save.screen == "battle") Require(playerAlive && enemyAlive, "Battle outcome is inconsistent.");
                if (save.screen == "victory" || (save.screen == "complete" && save.generatedDungeon == null)) Require(playerAlive && !enemyAlive, "Victory outcome is inconsistent.");
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
                        TagRuleDef rule = TagRule(tag); TileDef authored = Array.Find(authoredTiles, t => t.x == tile.x && t.y == tile.y);
                        if (rule != null && rule.durationRounds > 0)
                            Require((authored != null && Array.IndexOf(authored.tags, tag) >= 0) || layerKeys.Contains(tile.id + ":" + tag), "Timed tile tag is missing its duration layer.");
                    }
                foreach (string entry in save.log) Require(entry != null && entry.Length <= 1000, "Invalid saved log.");
                // All validation is complete before replacing any live state.
                journey = save.journey == null ? null : new JourneySave { id = save.journey.id, floorIndex = save.journey.floorIndex, capturedIds = (string[])save.journey.capturedIds.Clone() };
                neighborhoodState = nextNeighborhood; pendingNeighborhood = null; CommitHome(nextHome); CommitSkillTree(nextSkillNodes); CommitDevelopment(nextDevelopment); CommitCustomMap(save); generatedCampaign = CopyCampaign(save.generatedCampaign); pendingDescent = false; CommitScenario(save); CommitExpedition(save);
                audienceState = nextAudience; achievementIds.Clear(); achievementIds.AddRange(nextAchievements);
                equipped.Clear(); equipped.AddRange(nextEquipment);
                exploration.Clear(); foreach (ExplorationSave sector in nextExploration) exploration.Add(sector.sectorId, sector);
                roster.Clear(); foreach (var pair in nextRoster) roster.Add(pair.Key, pair.Value);
                inventory.Clear(); foreach (var pair in nextInventory) inventory.Add(pair.Key, pair.Value);
                units.Clear(); foreach (var pair in nextUnits) units.Add(pair.Key, pair.Value);
                timed.Clear(); timed.AddRange(nextTimed); battle = nextBattle;
                battleLayoutVersion = save.battleLayoutVersion; screen = save.screen; phase = save.phase; selected = save.selectedUnitId; encounterIndex = save.encounterIndex; round = save.round; xp = save.xp; rewardChosen = save.rewardChosen;
                log.Clear(); log.AddRange(save.log); ClearPreview(); message = "Save restored.";
            }
            catch (ArgumentException ex) { message = "Save rejected: " + ex.Message; }
            return GetView();
        }
        private void ValidateTags(string[] tags)
        {
            Require(tags != null && tags.Length <= 100, "Invalid saved tags."); HashSet<string> seen = new HashSet<string>();
            Require(!catalog.HasStackedRankTags(tags), "Saved tags stack mutually exclusive ranked variants.");
            foreach (string tag in tags) Require(catalog.HasTag(tag) && seen.Add(tag), "Unknown or duplicate saved tag.");
        }
    }
}
