using System;
using System.Collections.Generic;
namespace DungeonCrawlerTactics
{
    public sealed partial class GameSession
    {
        private TacticalModeDef Mode(TacticalModeDef[] definitions, string id, string owner)
        {
            if (string.IsNullOrEmpty(id)) return null;
            TacticalModeDef mode = Array.Find(definitions, m => m.id == id);
            Require(mode != null && (string.IsNullOrEmpty(mode.rosterId) || mode.rosterId == owner), "Unknown or unavailable tactical adaptation.");
            return mode;
        }
        private void ApplyModes(ClassStats stats, string owner, string stance, string form)
        {
            foreach (TacticalModeDef mode in new[] { Mode(data.stances, stance, owner), Mode(data.forms, form, owner) })
                if (mode != null) { stats.hp += mode.hpBonus; stats.energy += mode.manaBonus; stats.move += mode.moveBonus; }
            Require(stats.hp > 0 && stats.energy >= 0 && stats.move >= 0, "Invalid tactical adaptation stats.");
        }
        private ClassStats ProposedModeStats(GameCommand command, out TacticalModeDef mode)
        {
            RosterView member = GetRoster(command.unitId);
            bool form = !string.IsNullOrEmpty(command.formId);
            Require(form != !string.IsNullOrEmpty(command.stanceId), "Choose one form or stance.");
            mode = Mode(form ? data.forms : data.stances, form ? command.formId : command.stanceId, member.id);
            Require(!ModeSelected(mode, form ? member.formId : member.stanceId), "That tactical adaptation is already selected.");
            ClassStats stats = PlayerStats(member.id, member.classId, xp, equipped); ApplyAllocatedStats(stats, member.id, allocations); ApplyTreeStats(stats, member.id, unlockedSkillNodes);
            ApplyModes(stats, member.id, form ? member.stanceId : command.stanceId, form ? command.formId : member.formId);
            return stats;
        }
        private ActionResult ResolveMode(GameCommand command, EntityState actor)
        {
            Require(actor.Team == "player" && phase == "player", "Only crawlers choose tactical adaptations.");
            command.targetId = actor.Id;
            TacticalModeDef mode; ClassStats stats = ProposedModeStats(command, out mode);
            BattleState next = battle.Clone(); EntityState changed = next.Entities[actor.Id];
            // Preserve damage and spent mana; changing shape never restores resources.
            if (!string.IsNullOrEmpty(mode.grantTag)) changed.Tags.Add(mode.grantTag);
            changed.MaxHp = stats.hp; changed.Hp = Math.Min(changed.Hp, stats.hp); changed.Energy = Math.Min(changed.Energy, stats.energy);
            return new ActionResult(next, new List<string> { mode.label + ": " + mode.description + " (tactical adaptation)." }, new List<PresentationEvent> { new PresentationEvent { type = "adaptation", actorId = actor.Id, targetId = actor.Id, tag = mode.id } });
        }
        private void CommitMode(GameCommand command)
        {
            if (string.IsNullOrEmpty(command.formId) && string.IsNullOrEmpty(command.stanceId)) return;
            RosterView member = roster[command.unitId];
            if (!string.IsNullOrEmpty(command.formId)) member.formId = command.formId; else member.stanceId = command.stanceId;
            ClassStats stats = PlayerStats(member.id, member.classId); units[member.id].maxEnergy = stats.energy; units[member.id].move = stats.move;
            SyncRosterFromBattle();
        }
        private int ForecastModeStat(string id, bool mana)
        {
            if (!units.ContainsKey(id)) return 0;
            if (pending == null || pending.unitId != id || (string.IsNullOrEmpty(pending.formId) && string.IsNullOrEmpty(pending.stanceId))) return mana ? units[id].maxEnergy : EffectiveMove(forecast != null && forecast.State.Entities.ContainsKey(id) ? forecast.State.Entities[id] : battle.Entities[id], units[id].move);
            TacticalModeDef mode; ClassStats stats = ProposedModeStats(pending, out mode); return mana ? stats.energy : EffectiveMove(forecast != null && forecast.State.Entities.ContainsKey(id) ? forecast.State.Entities[id] : battle.Entities[id], stats.move);
        }
        private void PopulateModes(GameView view)
        {
            string owner = view.selectedUnitId; if (owner == null || !roster.ContainsKey(owner)) return;
            RosterView member = roster[owner];
            view.stances = ModeViews(data.stances, owner, member.stanceId, view.canAct);
            view.forms = ModeViews(data.forms, owner, member.formId, view.canAct);
        }
        private static bool ModeSelected(TacticalModeDef mode, string current) { return current == mode.id || (string.IsNullOrEmpty(current) && mode.hpBonus == 0 && mode.manaBonus == 0 && mode.moveBonus == 0 && string.IsNullOrEmpty(mode.grantTag)); }
        private TacticalModeView[] ModeViews(TacticalModeDef[] definitions, string owner, string current, bool enabled)
        {
            List<TacticalModeView> result = new List<TacticalModeView>();
            foreach (TacticalModeDef mode in definitions) if (string.IsNullOrEmpty(mode.rosterId) || mode.rosterId == owner)
                result.Add(new TacticalModeView { id = mode.id, label = mode.label, description = mode.description, unitId = owner, grantTag = mode.grantTag, hpBonus = mode.hpBonus, manaBonus = mode.manaBonus, moveBonus = mode.moveBonus, selected = ModeSelected(mode, current), enabled = enabled && !ModeSelected(mode, current) });
            return result.ToArray();
        }
    }
}
