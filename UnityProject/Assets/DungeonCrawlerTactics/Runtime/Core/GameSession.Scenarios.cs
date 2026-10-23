using System;
using System.Collections.Generic;
namespace DungeonCrawlerTactics
{
    public sealed partial class GameSession
    {
        private ScenarioSave scenarioState;
        private ScenarioDef Scenario
        {
            get
            {
                return scenarioState == null ? null : Array.Find(data.scenarios, s => s.id == scenarioState.id);
            }
        }
        private EncounterDef ActiveScenarioEncounter
        {
            get
            {
                return Scenario == null ? null : Scenario.encounter;
            }
        }
        private void ClearScenario()
        {
            scenarioState = null;
        }
        private ScenarioOptionView[] ScenarioOptions()
        {
            var result = new List<ScenarioOptionView>();
            foreach (var s in data.scenarios)
                result.Add(new ScenarioOptionView { id = s.id, label = s.label, description = s.description, objective = s.objective, kind = s.kind, conceptArt = s.conceptArt });
            return result.ToArray();
        }
        private bool TryScenarioCommand(GameCommand command)
        {
            if (command.type == "scenario_start")
            {
                Require(scenarioState == null, "Return to your campaign before starting another scenario.");
                var def = Array.Find(data.scenarios, s => s.id == command.targetId);
                Require(def != null, "Unknown scenario.");
                GameSave campaign = ExportSave();
                Reset();
                scenarioState = NewScenario(def, campaign);
                // The accelerated roster is explicitly an adaptation; preserve the player's selected party.
                int count = 0;
                foreach (var r in roster.Values)
                {
                    r.selected = false;
                }
                foreach (var r in campaign.roster)
                    if (r.selected && roster.ContainsKey(r.id) && Definition(r.id).deployable && count < data.partySize)
                    {
                        roster[r.id].selected = true;
                        count++;
                    }
                foreach (var r in data.roster)
                    if (count < data.partySize && r.deployable && !roster[r.id].selected)
                    {
                        roster[r.id].selected = true;
                        count++;
                    }
                StartEncounter();
                return true;
            }
            if (scenarioState == null)
                return false;
            if (command.type == "scenario_return" || command.type == "continue")
            {
                GameSave campaign = scenarioState.campaign;
                ClearScenario();
                ImportSave(campaign);
                message = "Campaign restored. Scenario progress was isolated.";
                return true;
            }
            if (command.type == "retry")
            {
                Require(screen == "defeat" || screen == "victory", "Finish the scenario before retrying.");
                var def = Scenario;
                var campaign = scenarioState.campaign;
                ResetInventory();
                RefreshRosterStats(true);
                scenarioState = NewScenario(def, campaign);
                StartEncounter();
                return true;
            }
            if (command.type != "scenario_interact")
                return false;
            RequirePlayer();
            ClearPreview();
            var actor = GetActor(command.unitId ?? selected);
            Require(!units[actor.Id].acted, "This crawler already used its action.");
            var obj = Array.Find(Scenario.interactables, o => o.id == command.targetId);
            Require(obj != null, "Unknown scenario interaction.");
            var state = ObjectState(obj.id);
            Require(state.hp > 0, "This object is broken.");
            Require(Math.Abs(actor.X - obj.x) + Math.Abs(actor.Y - obj.y) <= 1, "Move adjacent to interact.");
            if (obj.kind == "parts")
            {
                Require(Array.IndexOf(scenarioState.carryingUnitIds, actor.Id) < 0, "Already carrying a component.");
                var ids = new List<string>(scenarioState.carryingUnitIds);
                ids.Add(actor.Id);
                ids.Sort(StringComparer.Ordinal);
                scenarioState.carryingUnitIds = ids.ToArray();
                AddLog(Label(actor.Id) + " collects a replacement-ready construction component.");
            }
            else if (obj.kind == "barrier")
            {
                Require(Array.IndexOf(scenarioState.carryingUnitIds, actor.Id) >= 0, "Collect a component first.");
                Require(scenarioState.progress < Scenario.constructionTotal, "The Speedbump is fully built.");
                var ids = new List<string>(scenarioState.carryingUnitIds);
                ids.Remove(actor.Id);
                scenarioState.carryingUnitIds = ids.ToArray();
                scenarioState.progress++;
                scenarioState.barrierHp = Math.Min(Scenario.barrierDurability, scenarioState.barrierHp + 1);
                AddLog(Label(actor.Id) + " braces the Speedbump (" + scenarioState.progress + "/" + Scenario.constructionTotal + ").");
            }
            else if (obj.kind == "helper")
            {
                Require(scenarioState.helpers < Scenario.helperCount, "All helpers are already active.");
                scenarioState.helpers++;
                AddLog("A Meadow Lark helper returns to construction duty.");
            }
            else
            {
                state.hp = 0;
                state.used = true;
                AddLog(Label(actor.Id) + (obj.kind == "cover" ? " topples gym equipment into cover." : " clears a garbage lane."));
            }
            units[actor.Id].acted = true;
            presentationEvents.Add(new PresentationEvent { type = "scenario_interact", actorId = actor.Id, targetId = obj.id, toX = obj.x, toY = obj.y, amount = scenarioState.progress });
            message = "Interaction committed. Movement remains available.";
            return true;
        }
        private ScenarioSave NewScenario(ScenarioDef def, GameSave campaign)
        {
            var objects = new List<ScenarioObjectSave>();
            foreach (var o in def.interactables)
                objects.Add(new ScenarioObjectSave { id = o.id, hp = o.hp });
            return new ScenarioSave { id = def.id, helpers = def.helperCount, objects = objects.ToArray(), campaign = campaign };
        }
        private void ScenarioOnStart()
        {
            if (Scenario == null)
                return;
            foreach (var id in Scenario.minionIds)
                battle.Entities[id].Hp = 0;
            PlanScenarioIntent();
            message = Scenario.description + " Mixed timeline roster: later allies and progression are an adaptation.";
        }
        private void ScenarioAfterPlayerAction(GameCommand command)
        {
            if (Scenario == null || Scenario.kind != "hoarder" || command == null)
                return;
            string abilityId = command.abilityId;
            if (!string.IsNullOrEmpty(command.itemId))
                abilityId = catalog.Items[command.itemId].abilityId;
            AbilityDef ability;
            if (abilityId == null || !catalog.Abilities.TryGetValue(abilityId, out ability) || Array.IndexOf(ability.incomingTags, "element.fire") < 0)
                return;
            var boss = battle.Entities[Scenario.bossId];
            if (command.targetId == boss.Id || command.targetId == TileId(boss.X, boss.Y))
            {
                scenarioState.emergenceInterrupted = true;
                AddLog("Fire interrupts the next Scatterer emergence.");
            }
        }
        private bool IsScenarioBoss(string id)
        {
            return Scenario != null && Scenario.bossId == id;
        }
        private ScenarioObjectSave ObjectState(string id)
        {
            return Array.Find(scenarioState.objects, o => o.id == id);
        }
        private void PlanScenarioIntent()
        {
            if (Scenario == null)
                return;
            var s = Scenario;
            var boss = battle.Entities[s.bossId];
            var cells = new List<CellView>();
            string label, description;
            if (s.kind == "hoarder")
            {
                foreach (var id in s.minionIds)
                {
                    var e = Array.Find(s.encounter.enemies, u => u.id == id);
                    cells.Add(new CellView { x = e.x, y = e.y });
                }
                label = "Scatterer emergence";
                description = "Up to " + s.minionCap + " living Scatterers. Burning or Frozen interrupts this emergence.";
            }
            else if (s.kind == "juicer")
            {
                EntityState target = null;
                foreach (var id in UnitIds("player"))
                {
                    var e = battle.Entities[id];
                    if (e.Hp > 0 && (target == null || Math.Abs(e.X - boss.X) + Math.Abs(e.Y - boss.Y) < Math.Abs(target.X - boss.X) + Math.Abs(target.Y - boss.Y)))
                        target = e;
                }
                int dx = target == null ? -1 : target.X - boss.X, dy = target == null ? 0 : target.Y - boss.Y;
                int sx = Math.Abs(dx) >= Math.Abs(dy) ? Math.Sign(dx) : 0, sy = Math.Abs(dx) >= Math.Abs(dy) ? 0 : Math.Sign(dy);
                if (sx == 0 && sy == 0)
                    sx = -1;
                int x = boss.X + sx, y = boss.Y + sy;
                while (x >= 0 && y >= 0 && x < s.encounter.width && y < s.encounter.height)
                {
                    cells.Add(new CellView { x = x, y = y });
                    x += sx;
                    y += sy;
                }
                label = "Flaming plate";
                description = "Locked lane: moving away avoids the throw. Cover intercepts. Frozen or Shocked interrupts.";
            }
            else
            {
                cells.AddRange(RollingCells(s, scenarioState.routeIndex, boss.X, boss.Y));
                label = "Rolling impact";
                description = "Rolls three marked tiles; a completed Speedbump stops and damages the boss. Incomplete barriers break; helpers recover parts.";
            }
            scenarioState.intent = new IntentView { id = s.id + ".intent." + scenarioState.turns, label = label, description = description, actorId = s.bossId, damage = s.damage, originX = boss.X, originY = boss.Y, cells = cells.ToArray(), turns = 1 };
        }
        private static CellView[] RollingCells(ScenarioDef s, int routeIndex, int x, int y)
        {
            var result = new List<CellView>();
            var anchor = s.route[routeIndex];
            if (x == anchor.x && y == anchor.y)
            {
                for (int i = 1; i <= 3; i++)
                    result.Add(s.route[(routeIndex + i) % s.route.Length]);
            }
            else
                for (int i = 0; i < 3 && (x != anchor.x || y != anchor.y); i++)
                {
                    if (x != anchor.x)
                        x += Math.Sign(anchor.x - x);
                    else
                        y += Math.Sign(anchor.y - y);
                    result.Add(new CellView { x = x, y = y });
                }
            return result.ToArray();
        }
        private bool Interrupted(EntityState boss)
        {
            return boss.Tags.Contains("status.frozen") || boss.Tags.Contains("status.shocked");
        }
        private void RunScenarioEnemyTurn()
        {
            if (Scenario == null)
                return;
            var s = Scenario;
            var boss = battle.Entities[s.bossId];
            if (boss.Hp <= 0)
                return;
            var intent = scenarioState.intent;
            Require(intent != null, "Scenario intent is missing.");
            scenarioState.turns++;
            presentationEvents.Add(new PresentationEvent { type = "scenario_intent", actorId = boss.Id, tag = intent.id, amount = intent.damage });
            if (s.kind == "hoarder")
            {
                var tile = battle.Entities[TileId(boss.X, boss.Y)];
                if (scenarioState.emergenceInterrupted || Interrupted(boss) || boss.Tags.Contains("surface.burning") || tile.Tags.Contains("surface.burning"))
                    AddLog("The Hoarder's emergence is interrupted.");
                else
                {
                    int living = 0;
                    foreach (var id in s.minionIds)
                        if (battle.Entities[id].Hp > 0)
                            living++;
                    foreach (var id in s.minionIds)
                    {
                        if (living >= s.minionCap)
                            break;
                        var e = battle.Entities[id];
                        if (e.Hp > 0)
                            continue;
                        CellView open = null;
                        foreach (var c in intent.cells)
                            if (Passable(c.x, c.y, id))
                            {
                                open = c;
                                break;
                            }
                        if (open == null)
                        {
                            AddLog("Scatterer emergence blocked: no free nest tile.");
                            break;
                        }
                        e.X = open.x;
                        e.Y = open.y;
                        e.Hp = e.MaxHp;
                        living++;
                        ApplyOccupancy(battle, e, true, log, presentationEvents);
                        presentationEvents.Add(new PresentationEvent { type = "scenario_spawn", actorId = boss.Id, targetId = id, toX = e.X, toY = e.Y });
                    }
                }
                scenarioState.emergenceInterrupted = false;
                // Ordinary damage remains valid; the boss also pressures adjacent crawlers.
                foreach (var id in UnitIds("player"))
                {
                    var e = battle.Entities[id];
                    if (e.Hp > 0 && Math.Abs(e.X - boss.X) + Math.Abs(e.Y - boss.Y) <= 1)
                    {
                        Damage(e, s.damage, "Hoarder swipe", log, presentationEvents);
                        break;
                    }
                }
            }
            else if (s.kind == "juicer")
            {
                if (Interrupted(boss) || boss.X != intent.originX || boss.Y != intent.originY)
                    AddLog("The Juicer's flaming throw is interrupted by control or displacement.");
                else
                    foreach (var cell in intent.cells)
                    {
                        if (Blocked(cell.x, cell.y))
                            break;
                        bool intercepted = false;
                        foreach (var o in s.interactables)
                            if (o.kind == "cover" && o.x == cell.x && o.y == cell.y)
                            {
                                var st = ObjectState(o.id);
                                if (st.used && st.hp == 0)
                                {
                                    st.hp = -1;
                                    AddLog("The plate destroys the toppled bench and stops.");
                                    intercepted = true;
                                    break;
                                }
                            }
                        presentationEvents.Add(new PresentationEvent { type = "projectile", actorId = boss.Id, fromX = boss.X, fromY = boss.Y, toX = cell.x, toY = cell.y, tag = "element.fire" });
                        if (intercepted)
                            break;
                        foreach (var id in UnitIds("player"))
                        {
                            var e = battle.Entities[id];
                            if (e.Hp > 0 && e.X == cell.x && e.Y == cell.y)
                                Damage(e, s.damage, "Flaming plate", log, presentationEvents);
                        }
                    }
            }
            else
            {
                if (boss.X != intent.originX || boss.Y != intent.originY)
                {
                    AddLog("The rolling charge is interrupted by displacement.");
                    PlanScenarioIntent();
                    return;
                }
                foreach (var cell in intent.cells)
                {
                    bool stopped = false;
                    foreach (var o in s.interactables)
                        if (o.kind == "barrier" && o.x == cell.x && o.y == cell.y && scenarioState.progress > 0)
                        {
                            if (scenarioState.progress >= s.constructionTotal && scenarioState.barrierHp > 0)
                            {
                                Damage(boss, 18, "Speedbump collision", log, presentationEvents);
                                scenarioState.barrierHp--;
                                AddLog("The completed Speedbump stops the rolling boss.");
                                stopped = true;
                                if (scenarioState.barrierHp == 0)
                                    scenarioState.progress = 0;
                            }
                            else
                            {
                                scenarioState.progress = 0;
                                scenarioState.barrierHp = 0;
                                scenarioState.helpers = Math.Max(0, scenarioState.helpers - 1);
                                AddLog("The incomplete Speedbump breaks. Parts remain available; rally a helper to recover.");
                            }
                        }
                    if (stopped)
                        break;
                    foreach (var id in UnitIds("player"))
                    {
                        var e = battle.Entities[id];
                        if (e.Hp > 0 && e.X == cell.x && e.Y == cell.y)
                            Damage(e, s.damage, "Rolling collision", log, presentationEvents);
                    }
                    if (!Passable(cell.x, cell.y, boss.Id))
                    {
                        AddLog("The rolling path is obstructed; the boss stops at its current tile.");
                        break;
                    }
                    if (Passable(cell.x, cell.y, boss.Id))
                    {
                        presentationEvents.Add(new PresentationEvent { type = "move", actorId = boss.Id, targetId = boss.Id, fromX = boss.X, fromY = boss.Y, toX = cell.x, toY = cell.y });
                        boss.X = cell.x;
                        boss.Y = cell.y;
                    }
                    for (int i = 0; i < s.route.Length; i++)
                        if (s.route[i].x == cell.x && s.route[i].y == cell.y)
                            scenarioState.routeIndex = i;
                }
                if (scenarioState.helpers > 0 && scenarioState.progress < s.constructionTotal && scenarioState.turns % 2 == 0)
                {
                    scenarioState.progress++;
                    scenarioState.barrierHp = Math.Min(s.barrierDurability, scenarioState.barrierHp + 1);
                    AddLog("Meadow Lark helpers recover and brace a replacement part.");
                }
            }
            if (s.kind == "juicer" && boss.Hp > 0)
            {
                EntityState nearest = null;
                foreach (var id in UnitIds("player"))
                {
                    var e = battle.Entities[id];
                    if (e.Hp > 0 && (nearest == null || Math.Abs(e.X - boss.X) + Math.Abs(e.Y - boss.Y) < Math.Abs(nearest.X - boss.X) + Math.Abs(nearest.Y - boss.Y)))
                        nearest = e;
                }
                if (nearest != null && !Interrupted(boss))
                {
                    // Advance after resolving the declared throw, then publish the next locked lane.
                    int dx = Math.Sign(nearest.X - boss.X), dy = Math.Sign(nearest.Y - boss.Y);
                    int nx = boss.X + dx, ny = boss.Y;
                    if (dx == 0 || !Passable(nx, ny, boss.Id))
                    {
                        nx = boss.X;
                        ny = boss.Y + dy;
                    }
                    if ((nx != boss.X || ny != boss.Y) && Passable(nx, ny, boss.Id))
                    {
                        presentationEvents.Add(new PresentationEvent { type = "move", actorId = boss.Id, targetId = boss.Id, fromX = boss.X, fromY = boss.Y, toX = nx, toY = ny });
                        boss.X = nx;
                        boss.Y = ny;
                        ApplyOccupancy(battle, boss, true, log, presentationEvents);
                        AddLog("The Juicer advances before winding up the next throw.");
                    }
                }
            }
            CheckOutcome();
            PlanScenarioIntent();
        }
        private ScenarioView ScenarioView()
        {
            if (Scenario == null)
                return null;
            var s = Scenario;
            var list = new List<ScenarioInteractableView>();
            foreach (var o in s.interactables)
            {
                var st = ObjectState(o.id);
                EntityState actor = null;
                if (selected != null)
                    battle.Entities.TryGetValue(selected, out actor);
                bool enabled = actor != null && actor.Hp > 0 && phase == "player" && screen == "battle" && !units[actor.Id].acted && !units[actor.Id].finished && Math.Abs(actor.X - o.x) + Math.Abs(actor.Y - o.y) <= 1 && st.hp > 0;
                if (o.kind == "parts")
                    enabled = enabled && Array.IndexOf(scenarioState.carryingUnitIds, selected) < 0;
                if (o.kind == "barrier")
                    enabled = enabled && Array.IndexOf(scenarioState.carryingUnitIds, selected) >= 0 && scenarioState.progress < s.constructionTotal;
                if (o.kind == "helper")
                    enabled = enabled && scenarioState.helpers < s.helperCount;
                list.Add(new ScenarioInteractableView { id = o.id, label = o.label, description = o.description, action = o.kind, x = o.x, y = o.y, hp = Math.Max(0, st.hp), maxHp = o.hp, progress = scenarioState.progress, total = s.constructionTotal, enabled = enabled, used = st.used, destroyed = st.hp < 0 });
            }
            return new ScenarioView { id = s.id, label = s.label, description = s.description, objective = s.objective, conceptArt = s.conceptArt, decorations = s.decorations, intent = scenarioState.intent, interactables = list.ToArray(), progress = s.kind == "swine" ? scenarioState.progress : (screen == "victory" ? 1 : 0), total = s.kind == "swine" ? s.constructionTotal : 1, barrierHp = scenarioState.barrierHp, helpers = scenarioState.helpers, carryingUnitIds = (string[])scenarioState.carryingUnitIds.Clone() };
        }
        private ScenarioSave CaptureScenario()
        {
            return CloneScenario(scenarioState);
        }
        private ScenarioSave CloneScenario(ScenarioSave source)
        {
            if (source == null)
                return null;
            var objects = new List<ScenarioObjectSave>();
            foreach (var o in source.objects)
                objects.Add(new ScenarioObjectSave { id = o.id, hp = o.hp, used = o.used });
            IntentView intent = null;
            if (source.intent != null)
            {
                var cells = new List<CellView>();
                foreach (var c in source.intent.cells)
                    cells.Add(new CellView { x = c.x, y = c.y });
                intent = new IntentView { id = source.intent.id, label = source.intent.label, description = source.intent.description, actorId = source.intent.actorId, damage = source.intent.damage, originX = source.intent.originX, originY = source.intent.originY, turns = source.intent.turns, cells = cells.ToArray() };
            }
            var backup = new GameSession(scenarioValidationContent, data);
            backup.ImportSave(source.campaign);
            return new ScenarioSave { emergenceInterrupted = source.emergenceInterrupted, id = source.id, version = source.version, progress = source.progress, barrierHp = source.barrierHp, helpers = source.helpers, routeIndex = source.routeIndex, turns = source.turns, carryingUnitIds = (string[])source.carryingUnitIds.Clone(), objects = objects.ToArray(), intent = intent, campaign = backup.ExportSave() };
        }
        private bool ScenarioPassable(int x, int y, string actorId)
        {
            if (Scenario == null)
                return true;
            foreach (var o in Scenario.interactables)
                if (o.kind == "garbage" && o.x == x && o.y == y && ObjectState(o.id).hp > 0)
                    return false;
            return true;
        }
        private EncounterDef ValidateScenario(GameSave save)
        {
            var state = save.scenario;
            if (state == null)
                return null;
            var s = Array.Find(data.scenarios, d => d.id == state.id);
            Require(s != null && state.version == 1 && state.campaign != null && state.campaign.scenario == null, "Unknown scenario save or nested campaign.");
            Require(state.progress >= 0 && state.progress <= s.constructionTotal && state.barrierHp >= 0 && state.barrierHp <= s.barrierDurability && state.helpers >= 0 && state.helpers <= s.helperCount && state.routeIndex >= 0 && state.routeIndex < Math.Max(1, s.route.Length) && state.turns >= 0 && state.turns <= 100000, "Invalid scenario progress.");
            Require(state.objects != null && state.objects.Length == s.interactables.Length && state.carryingUnitIds != null && state.carryingUnitIds.Length <= data.partySize, "Invalid scenario objects.");
            Require(save.units != null && save.roster != null, "Missing scenario save arrays.");
            foreach (var u in save.units)
                Require(u != null, "Null scenario unit.");
            foreach (var r in save.roster)
                Require(r != null, "Null scenario roster member.");
            var seen = new HashSet<string>();
            foreach (var o in state.objects)
            {
                Require(o != null, "Null scenario object.");
                var def = Array.Find(s.interactables, d => d.id == o.id);
                Require(def != null && seen.Add(o.id) && o.hp >= -1 && o.hp <= def.hp, "Invalid scenario object state.");
            }
            seen.Clear();
            foreach (var id in state.carryingUnitIds)
                Require(Array.Exists(save.roster, r => r.id == id && r.selected) && seen.Add(id), "Invalid component carrier.");
            Require(state.intent != null && state.intent.actorId == s.bossId && state.intent.damage == s.damage && state.intent.cells != null && state.intent.cells.Length <= s.encounter.width + s.encounter.height, "Invalid scenario intent.");
            foreach (var c in state.intent.cells)
                Require(c != null && c.x >= 0 && c.y >= 0 && c.x < s.encounter.width && c.y < s.encounter.height, "Intent outside map.");
            Require(state.intent.originX >= 0 && state.intent.originY >= 0 && state.intent.originX < s.encounter.width && state.intent.originY < s.encounter.height, "Invalid intent origin.");
            Require(state.intent.id == s.id + ".intent." + state.turns && state.intent.turns == 1, "Invalid intent identity.");
            Require(save.units != null && save.roster != null, "Missing scenario save arrays.");
            foreach (var u in save.units)
                Require(u != null, "Null scenario unit.");
            foreach (var r in save.roster)
                Require(r != null, "Null scenario roster member.");
            var boss = Array.Find(save.units, u => u.id == s.bossId);
            Require(boss != null, "Missing scenario boss.");
            if (s.kind == "swine")
            {
                var expected = RollingCells(s, state.routeIndex, state.intent.originX, state.intent.originY);
                Require(state.intent.cells.Length == expected.Length, "Invalid rolling lane length.");
                for (int i = 0; i < expected.Length; i++)
                {
                    var c = expected[i];
                    Require(state.intent.cells[i].x == c.x && state.intent.cells[i].y == c.y, "Forged rolling lane.");
                }
            }
            else if (s.kind == "hoarder")
            {
                Require(state.intent.cells.Length == s.minionIds.Length, "Invalid emergence nests.");
                for (int i = 0; i < s.minionIds.Length; i++)
                {
                    var e = Array.Find(s.encounter.enemies, u => u.id == s.minionIds[i]);
                    Require(state.intent.cells[i].x == e.x && state.intent.cells[i].y == e.y, "Forged emergence nest.");
                }
                int living = 0;
                foreach (var id in s.minionIds)
                {
                    var e = Array.Find(save.units, u => u.id == id);
                    if (e != null && e.hp > 0)
                        living++;
                }
                Require(living <= s.minionCap, "Too many living Scatterers.");
            }
            else
            {
                Require(state.intent.cells.Length > 0, "Missing plate lane.");
                Require(state.intent.originX >= 0 && state.intent.originY >= 0 && state.intent.originX < s.encounter.width && state.intent.originY < s.encounter.height, "Invalid intent origin.");
                int dx = state.intent.cells[0].x - state.intent.originX, dy = state.intent.cells[0].y - state.intent.originY;
                Require(Math.Abs(dx) + Math.Abs(dy) == 1, "Invalid plate direction.");
                int x = state.intent.originX + dx, y = state.intent.originY + dy, index = 0;
                while (x >= 0 && y >= 0 && x < s.encounter.width && y < s.encounter.height)
                {
                    Require(index < state.intent.cells.Length && state.intent.cells[index].x == x && state.intent.cells[index].y == y, "Forged plate lane.");
                    index++;
                    x += dx;
                    y += dy;
                }
                Require(index == state.intent.cells.Length, "Truncated plate lane.");
            }
            var campaignValidator = new GameSession(scenarioValidationContent, data);
            Require(!campaignValidator.ImportSave(state.campaign).message.StartsWith("Save rejected:", StringComparison.Ordinal), "Invalid saved campaign backup.");
            return s.encounter;
        }
        private void CommitScenario(GameSave save)
        {
            scenarioState = CloneScenario(save.scenario);
        }
    }
}
