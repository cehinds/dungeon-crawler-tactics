using System;
using System.Collections.Generic;

namespace DungeonCrawlerTactics
{
    public sealed partial class GameSession
    {
        private JourneySave journey;
        private bool JourneyAllocationUnlocked { get { return journey == null || journey.floorIndex >= 2; } }
        private bool JourneyActive { get { return journey != null && ActiveExpeditionEncounter == null && ActiveScenarioEncounter == null && CustomEncounter(0) == null; } }
        private JourneyFloorDef JourneyFloor { get { return journey == null ? null : data.journey.floors[Math.Min(journey.floorIndex, 7)]; } }
        private EncounterDef ActiveJourneyEncounter { get { return JourneyActive ? JourneyEncounterAt(journey.floorIndex) : null; } }
        private EncounterDef JourneyEncounterAt(int index)
        {
            // The destroyed seventh floor is a story stop, never a fabricated race encounter.
            int at = Math.Min(index, 7); if (at == 6) at = 5;
            return data.journey.floors[at].encounter;
        }
        private EncounterDef[] CampaignEncounters(GameSave save = null)
        {
            if ((save == null ? journey : save.journey) == null) return data.encounters;
            List<EncounterDef> result = new List<EncounterDef>();
            foreach (JourneyFloorDef floor in data.journey.floors) if (floor.number <= 8 && floor.encounter != null) result.Add(floor.encounter);
            return result.ToArray();
        }
        private JourneySave CaptureJourney() { return journey == null ? null : new JourneySave { id = journey.id, floorIndex = journey.floorIndex, capturedIds = (string[])journey.capturedIds.Clone() }; }
        private int JourneyExpectedXp(GameSave save)
        {
            int total = 0;
            for (int i = 0; i < Math.Min(save.encounterIndex, 8); i++) if (data.journey.floors[i].encounter != null) total += data.journey.floors[i].encounter.xp;
            if (save.screen == "victory" && save.expedition == null && save.scenario == null) total += data.journey.floors[save.encounterIndex].encounter.xp;
            return total;
        }
        // Pacing revision changes only unearned rewards. A checkpoint may contain any
        // combination of original and revised floor rewards after continuing an old run.
        private bool JourneyXpMatchesCompletedEncounters(GameSave save)
        {
            int[] originalRewards = { 120, 550, 2400, 7000, 18000, 35000, 0, 55615 };
            HashSet<int> totals = new HashSet<int> { 0 };
            int cleared = Math.Min(save.encounterIndex, 8);
            if (save.screen == "victory" && save.expedition == null && save.scenario == null) cleared++;
            for (int i = 0; i < Math.Min(cleared, 8); i++)
            {
                JourneyFloorDef floor = data.journey.floors[i];
                if (floor.encounter == null) continue;
                HashSet<int> next = new HashSet<int>();
                foreach (int total in totals)
                {
                    next.Add(total + floor.encounter.xp);
                    next.Add(total + originalRewards[i]);
                }
                totals = next;
            }
            return totals.Contains(save.xp);
        }
        private EncounterDef ValidateJourney(GameSave save)
        {
            if (save.journey == null) return null;
            JourneySave state = save.journey;
            Require(data.journey != null && state.version == 1 && state.id == data.journey.id && state.floorIndex == save.encounterIndex && state.floorIndex >= 0 && state.floorIndex <= 8 && state.capturedIds != null && state.capturedIds.Length <= 6, "Invalid story campaign state.");
            Require(save.customMap == null && save.scenario == null, "A story campaign cannot combine standalone maps.");
            bool suspended = save.expedition != null;
            Require(state.floorIndex != 6 || save.screen == "camp" || suspended, "The destroyed race is a safe-room story bypass only.");
            Require(state.floorIndex != 8 || save.screen == "complete" || suspended, "The eight-floor story is incomplete.");
            JourneyFloorDef floor = data.journey.floors[Math.Min(state.floorIndex, 7)];
            Require(state.capturedIds.Length == 0 || floor.mechanic == "capture", "Cards belong only to the capture floor.");
            HashSet<string> seen = new HashSet<string>();
            foreach (string id in state.capturedIds)
            {
                Require(id != null && seen.Add(id) && floor.encounter != null && Array.Exists(floor.encounter.enemies, e => e.id == id), "Unknown or duplicate captured card.");
                if (!suspended) Require(Array.Exists(save.units, u => u != null && u.id == id && u.team == "enemy" && u.hp == 0), "Captured monster remains on the board.");
            }
            if (!suspended && floor.mechanic == "capture")
            {
                Require((save.screen != "victory" && save.screen != "complete") || state.capturedIds.Length == floor.captureCount, "Capture victory requires every card.");
                foreach (SavedUnit unit in save.units) if (unit != null && unit.team == "enemy" && unit.hp == 0) Require(seen.Contains(unit.id), "An uncaptured ghost cannot remain defeated.");
            }
            if (state.floorIndex < 2)
            {
                foreach (RosterView member in save.roster) Require(member != null && Definition(member.id) != null && member.classId == Definition(member.id).classId, "Classes unlock on floor three.");
                if (save.development != null && save.development.allocated != null) Require(save.development.allocated.Length == 0, "Stat points stay banked until floor three.");
            }
            return suspended ? null : JourneyEncounterAt(state.floorIndex);
        }
        private bool TryJourneyCommand(GameCommand command)
        {
            if (command.type == "start_journey")
            {
                Require(screen == "camp" && ActiveExpeditionEncounter == null && ActiveScenarioEncounter == null && CustomEncounter(0) == null, "Start the story campaign from the campaign safe room.");
                Require(data.journey != null, "This content pack has no story campaign.");
                Reset(); journey = new JourneySave { id = data.journey.id }; message = "Story campaign started. Floors one and two teach innate abilities; classes and banked stat allocation unlock on floor three."; return true;
            }
            if (!JourneyActive) return false;
            if (command.type == "journey_bypass" || (command.type == "start" && JourneyFloor.kind == "bypass"))
            {
                Require(screen == "camp" && JourneyFloor.kind == "bypass", "No destroyed floor bypass is available.");
                AdvanceJourney(); message = "The Great Race was destroyed before normal traversal. You bypass its ruins without combat or XP and descend to Ghosts of Earth."; return true;
            }
            if (command.type == "preview_capture")
            {
                RequirePlayer(); ClearPreview();
                GameCommand capture = new GameCommand { type = "journey_capture", unitId = command.unitId ?? selected, targetId = command.targetId };
                forecast = ResolveAction(capture); pending = capture; selected = capture.unitId; message = "Capture forecast: seal this weakened monster into a card. Confirm spends this crawler's action; cancel spends nothing."; return true;
            }
            if (command.type == "confirm_capture") { Require(pending != null && pending.type == "journey_capture", "Preview a capture first."); command.type = "confirm"; }
            if (command.type == "cancel_capture") { ClearPreview(); message = "Capture canceled. Nothing was spent."; return true; }
            if (command.type == "continue")
            {
                Require(screen == "victory", "Win the encounter to continue."); Require(rewardChosen || data.rewards.Length == 0, "Choose a sponsor reward first.");
                SyncRosterFromBattle(); AdvanceJourney(); return true;
            }
            return false;
        }
        private void AdvanceJourney()
        {
            journey.floorIndex++; encounterIndex = journey.floorIndex;
            foreach (RosterView member in roster.Values) { member.specialtyClassId = null; member.specialtyFloor = 0; }
            // Captured cards stay visible in the final checkpoint, never leak into another floor.
            if (journey.floorIndex < 8) journey.capturedIds = new string[0];
            screen = journey.floorIndex >= 8 ? "complete" : "camp"; phase = "player";
            if (screen == "camp") { battle = new BattleState(); units.Clear(); timed.Clear(); selected = null; }
            ClearPreview(); message = screen == "complete" ? "Eight-floor story complete. Six monster cards secured; floors nine through eighteen remain locked." : JourneyFloor.description;
            if (journey.floorIndex == 2) message += " Classes and banked stat allocation are now unlocked in the safe room.";
        }
        private bool JourneyDoorUnlocked(ExplorationSave state)
        {
            if (!JourneyActive) return true;
            foreach (string id in JourneyFloor.requiredPointIds) if (Array.IndexOf(state.claimed, id) < 0) return false;
            return true;
        }
        private ActionResult ResolveCapture(GameCommand command, EntityState actor)
        {
            Require(JourneyActive && JourneyFloor.mechanic == "capture", "Monster cards can only be captured on Ghosts of Earth.");
            EntityState target = GetUnit(command.targetId);
            Require(actor.Team == "player" && target.Team == "enemy" && target.Hp > 0 && Array.IndexOf(journey.capturedIds, target.Id) < 0, "Choose an uncaptured living monster.");
            Require(target.Hp <= Math.Max(1, target.MaxHp / 2), "Weaken this monster to half HP or below before capture.");
            Require(Math.Abs(actor.X - target.X) + Math.Abs(actor.Y - target.Y) <= 3, "Move within three tiles to capture.");
            BattleState next = battle.Clone(); next.Entities[target.Id].Hp = 0;
            return new ActionResult(next, new List<string> { "Capture " + Label(target.Id) + " as monster card " + (journey.capturedIds.Length + 1) + "/" + JourneyFloor.captureCount + "." }, new List<PresentationEvent> { new PresentationEvent { type = "capture", actorId = actor.Id, targetId = target.Id, before = target.Hp, after = 0 } });
        }
        private void JourneyCommittedAction(GameCommand command)
        {
            if (command.type != "journey_capture") return;
            List<string> cards = new List<string>(journey.capturedIds); cards.Add(command.targetId); journey.capturedIds = cards.ToArray();
        }
        private void ReformJourneyGhosts(BattleState state, List<string> entries)
        {
            if (!JourneyActive || JourneyFloor.mechanic != "capture") return;
            foreach (SpawnDef spawn in JourneyFloor.encounter.enemies)
            {
                EntityState enemy;
                if (state.Entities.TryGetValue(spawn.id, out enemy) && enemy.Hp == 0 && Array.IndexOf(journey.capturedIds, spawn.id) < 0)
                { enemy.Hp = Math.Max(1, enemy.MaxHp / 2); entries.Add(spawn.label + " reforms at half HP. Use Capture to secure its card."); }
            }
        }
        private JourneyView JourneyView()
        {
            if (data.journey == null) return null;
            JourneyView view = new JourneyView { id = data.journey.id, label = data.journey.label, description = data.journey.description, available = true, active = JourneyActive, classesUnlocked = JourneyAllocationUnlocked, allocationUnlocked = JourneyAllocationUnlocked };
            List<JourneyFloorView> floors = new List<JourneyFloorView>();
            foreach (JourneyFloorDef floor in data.journey.floors) floors.Add(new JourneyFloorView { id = floor.id, number = floor.number, label = floor.label, description = floor.description, kind = floor.kind, mechanic = floor.mechanic, available = floor.available, current = journey != null && floor.number == journey.floorIndex + 1, complete = journey != null && floor.number <= journey.floorIndex, status = !floor.available ? "locked" : journey == null ? "available" : floor.number <= journey.floorIndex ? (floor.kind == "bypass" ? "bypassed" : "complete") : floor.number == journey.floorIndex + 1 ? "current" : "ahead" });
            view.floors = floors.ToArray(); if (journey == null) return view;
            JourneyFloorDef current = JourneyFloor; view.floorNumber = Math.Min(8, journey.floorIndex + 1); view.floorId = current.id; view.floorLabel = current.label; view.mechanic = current.mechanic; view.complete = journey.floorIndex == 8; view.canBypass = JourneyActive && screen == "camp" && current.kind == "bypass"; view.cardsCaptured = journey.capturedIds.Length; view.cardsRequired = current.captureCount;
            view.objectivesRequired = current.requiredPointIds.Length;
            ExplorationSave sector; if (current.encounter != null && exploration.TryGetValue(current.encounter.exploration.id, out sector)) foreach (string id in current.requiredPointIds) if (Array.IndexOf(sector.claimed, id) >= 0) view.objectivesComplete++;
            view.objective = current.kind == "bypass" ? "Bypass the destroyed Great Race; no battle or XP." : current.mechanic == "capture" ? "Weaken and capture six monsters as cards. Capture uses an action within three tiles at half HP or below; defeated uncaptured ghosts reform." : current.requiredPointIds.Length > 0 ? "Claim every marked route objective before entering the encounter (" + view.objectivesComplete + "/" + view.objectivesRequired + ")." : "Explore, defeat the floor's enemies, choose a sponsor reward, and descend.";
            if (JourneyActive && current.mechanic == "capture")
            {
                List<JourneyCaptureView> captures = new List<JourneyCaptureView>(); EntityState actor = selected != null && battle.Entities.ContainsKey(selected) ? battle.Entities[selected] : null;
                foreach (SpawnDef spawn in current.encounter.enemies)
                {
                    EntityState target; bool found = battle.Entities.TryGetValue(spawn.id, out target); bool captured = Array.IndexOf(journey.capturedIds, spawn.id) >= 0;
                    string reason = captured ? "Card secured" : !found ? "Enter the encounter first" : target.Hp > Math.Max(1, target.MaxHp / 2) ? "Weaken to half HP" : actor == null || screen != "battle" || phase != "player" || units[actor.Id].acted || units[actor.Id].finished || actor.Hp == 0 ? "Action unavailable" : Math.Abs(actor.X - target.X) + Math.Abs(actor.Y - target.Y) > 3 ? "Move within three tiles" : "";
                    captures.Add(new JourneyCaptureView { targetId = spawn.id, label = spawn.label, hp = found ? target.Hp : spawn.hp, maxHp = spawn.hp, threshold = Math.Max(1, spawn.hp / 2), captured = captured, canCapture = reason.Length == 0, disabledReason = reason });
                }
                view.captures = captures.ToArray();
            }
            if (JourneyActive && current.mechanic == "hunt" && screen == "battle")
            {
                List<JourneyIntentView> intents = new List<JourneyIntentView>();
                foreach (string id in UnitIds("enemy"))
                {
                    EntityState hunter = battle.Entities[id]; if (hunter.Hp == 0) continue;
                    // This is the same legal action resolver used by enemy AI, evaluated in enemy phase.
                    string oldPhase = phase; phase = "enemy"; GameCommand intent; try { intent = BestEnemyAction(id); } finally { phase = oldPhase; }
                    if (intent == null) intents.Add(new JourneyIntentView { actorId = id, description = "Advance toward the nearest crawler; attack if a legal target enters range." });
                    else
                    {
                        oldPhase = phase; phase = "enemy"; ActionResult result; try { result = ResolveAction(intent); } finally { phase = oldPhase; }
                        int damage = battle.Entities[intent.targetId].Hp - result.State.Entities[intent.targetId].Hp;
                        intents.Add(new JourneyIntentView { actorId = id, targetId = intent.targetId, abilityId = intent.abilityId, damage = Math.Max(0, damage), description = catalog.Abilities[intent.abilityId].label + " targets " + Label(intent.targetId) + "; current-position forecast " + Math.Max(0, damage) + " damage. Movement may change this intent." });
                    }
                }
                view.intents = intents.ToArray();
            }
            return view;
        }
    }
}
