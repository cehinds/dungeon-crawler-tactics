using System;
using System.Collections.Generic;

namespace DungeonCrawlerTactics
{
    public sealed partial class GameSession
    {
        private GameCommand pendingMechanismCommand;
        private MechanismPreviewView pendingMechanismPreview;

        private sealed class MechanismTransition
        {
            public GeneratedDungeonState state;
            public EncounterDef encounter;
            public RosterView actor;
            public MechanismPreviewView preview;
        }

        private static MechanismReceipt[] CopyMechanismReceipts(MechanismReceipt[] receipts)
        {
            Require(receipts == null || receipts.Length <= 16, "Too many mechanism receipts.");
            return receipts == null
                ? new MechanismReceipt[0]
                : Array.ConvertAll(
                    receipts,
                    r =>
                        r == null
                            ? null
                            : new MechanismReceipt
                            {
                                mechanismId = r.mechanismId,
                                solutionId = r.solutionId,
                                unitId = r.unitId,
                                abilityId = r.abilityId,
                            }
                );
        }

        private static GeneratedMechanismDef[] CopyMechanisms(GeneratedMechanismDef[] definitions)
        {
            Require(definitions == null || definitions.Length <= 16, "Too many floor mechanisms.");
            return definitions == null
                ? new GeneratedMechanismDef[0]
                : Array.ConvertAll(
                    definitions,
                    m =>
                    {
                        Require(
                            m != null
                                && m.openCells != null
                                && m.openCells.Length >= 1
                                && m.openCells.Length <= 8
                                && m.solutions != null
                                && m.solutions.Length >= 1
                                && m.solutions.Length <= 3
                                && m.materialTags != null
                                && m.materialTags.Length <= 8,
                            "Invalid mechanism collections."
                        );
                        return new GeneratedMechanismDef
                        {
                            id = m.id,
                            label = m.label,
                            description = m.description,
                            x = m.x,
                            y = m.y,
                            materialTags = (string[])m.materialTags.Clone(),
                            openCells = Array.ConvertAll(m.openCells, CopyCell),
                            solutions = Array.ConvertAll(
                                m.solutions,
                                s =>
                                {
                                    Require(
                                        s != null
                                            && s.requiredMaterialTags != null
                                            && s.requiredMaterialTags.Length <= 8,
                                        "Invalid mechanism solution collections."
                                    );
                                    return new GeneratedMechanismSolutionDef
                                    {
                                        id = s.id,
                                        label = s.label,
                                        description = s.description,
                                        x = s.x,
                                        y = s.y,
                                        kind = s.kind,
                                        abilityTag = s.abilityTag,
                                        itemId = s.itemId,
                                        itemCount = s.itemCount,
                                        requiredMaterialTags = (string[])
                                            s.requiredMaterialTags.Clone(),
                                    };
                                }
                            ),
                        };
                    }
                );
        }

        private static bool MechanismsEqual(
            GeneratedMechanismDef[] first,
            GeneratedMechanismDef[] second
        )
        {
            GeneratedMechanismDef[] a = CopyMechanisms(first),
                b = CopyMechanisms(second);
            if (a.Length != b.Length)
                return false;
            for (int i = 0; i < a.Length; i++)
            {
                GeneratedMechanismDef x = a[i],
                    y = b[i];
                if (
                    x.id != y.id
                    || x.label != y.label
                    || x.description != y.description
                    || x.x != y.x
                    || x.y != y.y
                    || string.Join("|", x.materialTags) != string.Join("|", y.materialTags)
                    || x.openCells.Length != y.openCells.Length
                    || x.solutions.Length != y.solutions.Length
                )
                    return false;
                for (int j = 0; j < x.openCells.Length; j++)
                    if (
                        x.openCells[j] == null
                        || y.openCells[j] == null
                        || x.openCells[j].x != y.openCells[j].x
                        || x.openCells[j].y != y.openCells[j].y
                    )
                        return false;
                for (int j = 0; j < x.solutions.Length; j++)
                {
                    GeneratedMechanismSolutionDef p = x.solutions[j],
                        q = y.solutions[j];
                    if (
                        p.id != q.id
                        || p.label != q.label
                        || p.description != q.description
                        || p.kind != q.kind
                        || p.x != q.x
                        || p.y != q.y
                        || p.abilityTag != q.abilityTag
                        || p.itemId != q.itemId
                        || p.itemCount != q.itemCount
                        || string.Join("|", p.requiredMaterialTags)
                            != string.Join("|", q.requiredMaterialTags)
                    )
                        return false;
                }
            }
            return true;
        }

        private static bool StableMechanismId(string value)
        {
            if (string.IsNullOrEmpty(value) || value.Length > 100)
                return false;
            foreach (char c in value)
                if (
                    !(
                        c >= 'a' && c <= 'z'
                        || c >= '0' && c <= '9'
                        || c == '.'
                        || c == '_'
                        || c == '-'
                    )
                )
                    return false;
            return true;
        }

        private static void ValidateMechanismPassage(
            GeneratedMechanismDef mechanism,
            EncounterDef baseline,
            List<CellView> baselineReachable
        )
        {
            HashSet<string> passage = new HashSet<string>();
            foreach (CellView cell in mechanism.openCells)
            {
                Require(
                    cell.x > 0
                        && cell.y > 0
                        && cell.x < baseline.width - 1
                        && cell.y < baseline.height - 1,
                    "Mechanisms cannot open the floor boundary."
                );
                passage.Add(ExploreKey(cell.x, cell.y));
            }
            Queue<CellView> pending = new Queue<CellView>();
            pending.Enqueue(mechanism.openCells[0]);
            HashSet<string> visited = new HashSet<string>(),
                entrances = new HashSet<string>();
            while (pending.Count > 0)
            {
                CellView cell = pending.Dequeue();
                if (!visited.Add(ExploreKey(cell.x, cell.y)))
                    continue;
                foreach (
                    CellView neighbor in new[]
                    {
                        new CellView { x = cell.x - 1, y = cell.y },
                        new CellView { x = cell.x + 1, y = cell.y },
                        new CellView { x = cell.x, y = cell.y - 1 },
                        new CellView { x = cell.x, y = cell.y + 1 },
                    }
                )
                {
                    string key = ExploreKey(neighbor.x, neighbor.y);
                    if (passage.Contains(key))
                        pending.Enqueue(neighbor);
                    else if (baselineReachable.Exists(c => c.x == neighbor.x && c.y == neighbor.y))
                        entrances.Add(key);
                }
            }
            Require(
                visited.Count == passage.Count && entrances.Count >= 2,
                "A mechanism passage must be connected and join at least two baseline walkable cells."
            );
        }

        private static bool MechanismActionUnoccupied(
            GeneratedFloorPlan floor,
            EncounterDef baseline,
            int x,
            int y
        )
        {
            return !(floor.entrance.x == x && floor.entrance.y == y)
                && !(floor.exit.x == x && floor.exit.y == y)
                && !Array.Exists(baseline.enemies, e => e.x == x && e.y == y)
                && !Array.Exists(baseline.playerSpawns, e => e.x == x && e.y == y)
                && !Array.Exists(floor.discoveries, p => p.x == x && p.y == y)
                && !Array.Exists(floor.groups, g => g.x == x && g.y == y);
        }

        private void ValidateMechanisms(
            GeneratedFloorPlan floor,
            EncounterDef baseline,
            GeneratedDungeonState state
        )
        {
            GeneratedMechanismDef[] mechanisms = CopyMechanisms(floor.mechanisms);
            HashSet<string> ids = new HashSet<string>(),
                cells = new HashSet<string>();
            List<CellView> reachable = GeneratedCells(baseline, floor.entrance.x, floor.entrance.y);
            foreach (GeneratedMechanismDef mechanism in mechanisms)
            {
                Require(
                    StableMechanismId(mechanism.id)
                        && ids.Add(mechanism.id)
                        && !string.IsNullOrEmpty(mechanism.label)
                        && mechanism.label.Length <= 200
                        && (mechanism.description == null || mechanism.description.Length <= 1000),
                    "Invalid mechanism identity."
                );
                HashSet<string> materials = new HashSet<string>();
                foreach (string tag in mechanism.materialTags)
                    Require(
                        tag != null && catalog.HasTag(tag) && materials.Add(tag),
                        "Unknown or repeated mechanism material tag."
                    );
                foreach (CellView cell in mechanism.openCells)
                {
                    Require(
                        cell != null
                            && cell.x >= 0
                            && cell.y >= 0
                            && cell.x < baseline.width
                            && cell.y < baseline.height
                            && cells.Add(ExploreKey(cell.x, cell.y))
                            && Array.Exists(
                                baseline.tiles,
                                t => t.x == cell.x && t.y == cell.y && t.blocked
                            ),
                        "Mechanism must open unique authored walls."
                    );
                    Require(
                        !(cell.x == floor.entrance.x && cell.y == floor.entrance.y)
                            && !(cell.x == floor.exit.x && cell.y == floor.exit.y)
                            && !Array.Exists(baseline.enemies, e => e.x == cell.x && e.y == cell.y)
                            && !Array.Exists(
                                baseline.playerSpawns,
                                e => e.x == cell.x && e.y == cell.y
                            ),
                        "Mechanism opening conflicts with an occupant or endpoint."
                    );
                }
                Require(
                    mechanism.x == mechanism.openCells[0].x
                        && mechanism.y == mechanism.openCells[0].y,
                    "Mechanism marker must match its first opening."
                );
                ValidateMechanismPassage(mechanism, baseline, reachable);
                HashSet<string> solutions = new HashSet<string>();
                foreach (GeneratedMechanismSolutionDef solution in mechanism.solutions)
                {
                    Require(
                        StableMechanismId(solution.id)
                            && solutions.Add(solution.id)
                            && !string.IsNullOrEmpty(solution.label)
                            && solution.label.Length <= 200
                            && (solution.description == null || solution.description.Length <= 1000)
                            && reachable.Exists(c => c.x == solution.x && c.y == solution.y)
                            && MechanismActionUnoccupied(floor, baseline, solution.x, solution.y),
                        "Mechanism solution needs a reachable baseline action location."
                    );
                    HashSet<string> requirements = new HashSet<string>();
                    foreach (string tag in solution.requiredMaterialTags)
                        Require(
                            tag != null && materials.Contains(tag) && requirements.Add(tag),
                            "Mechanism solution material predicate does not match."
                        );
                    bool manual = solution.kind == "manual",
                        ability = solution.kind == "ability",
                        item = solution.kind == "item";
                    Require(manual || ability || item, "Unknown mechanism solution kind.");
                    Require(
                        manual
                            ? string.IsNullOrEmpty(solution.abilityTag)
                                && string.IsNullOrEmpty(solution.itemId)
                                && solution.itemCount == 0
                            : !string.IsNullOrEmpty(solution.abilityTag)
                                && catalog.HasTag(solution.abilityTag),
                        "Invalid mechanism capability tag."
                    );
                    Require(
                        !ability
                            || string.IsNullOrEmpty(solution.itemId) && solution.itemCount == 0,
                        "Ability mechanisms cannot declare item costs."
                    );
                    if (item)
                    {
                        ItemDef definition;
                        Require(
                            solution.itemId != null
                                && catalog.Items.TryGetValue(solution.itemId, out definition)
                                && solution.itemCount >= 1
                                && solution.itemCount <= 99,
                            "Invalid mechanism item cost."
                        );
                        definition = catalog.Items[solution.itemId];
                        Require(
                            Array.IndexOf(
                                catalog.Abilities[definition.abilityId].incomingTags,
                                solution.abilityTag
                            ) >= 0,
                            "Mechanism item does not supply its declared capability tag."
                        );
                    }
                }
            }
            HashSet<string> receipts = new HashSet<string>();
            foreach (MechanismReceipt receipt in CopyMechanismReceipts(state.mechanismReceipts))
            {
                Require(
                    receipt != null
                        && receipt.mechanismId != null
                        && receipt.solutionId != null
                        && receipt.unitId != null,
                    "Invalid mechanism receipt."
                );
                GeneratedMechanismDef mechanism = Array.Find(
                    mechanisms,
                    m => m.id == receipt.mechanismId
                );
                Require(
                    mechanism != null && receipts.Add(mechanism.id),
                    "Unknown or duplicated mechanism receipt."
                );
                GeneratedMechanismSolutionDef solution = Array.Find(
                    mechanism.solutions,
                    s => s.id == receipt.solutionId
                );
                RosterDef actor = Definition(receipt.unitId);
                Require(
                    solution != null && actor != null && actor.deployable,
                    "Unknown mechanism solution or actor receipt."
                );
                Require(
                    state.revealed != null
                        && Array.Exists(
                            state.revealed,
                            c => c != null && c.x == solution.x && c.y == solution.y
                        ),
                    "Solved mechanism action must have been discovered."
                );
                AbilityDef ability;
                Require(
                    solution.kind == "ability"
                        ? receipt.abilityId != null
                            && catalog.Abilities.TryGetValue(receipt.abilityId, out ability)
                            && Array.IndexOf(ability.incomingTags, solution.abilityTag) >= 0
                        : string.IsNullOrEmpty(receipt.abilityId),
                    "Mechanism receipt has an invalid capability."
                );
            }
        }

        private static void ApplyMechanismOpenings(
            EncounterDef encounter,
            GeneratedDungeonState state
        )
        {
            GeneratedMechanismDef[] mechanisms =
                state.floorPlan.mechanisms ?? new GeneratedMechanismDef[0];
            HashSet<string> opened = new HashSet<string>();
            foreach (MechanismReceipt receipt in state.mechanismReceipts ?? new MechanismReceipt[0])
            {
                Require(receipt != null, "Invalid mechanism receipt.");
                GeneratedMechanismDef mechanism = Array.Find(
                    mechanisms,
                    m => m != null && m.id == receipt.mechanismId
                );
                Require(mechanism != null, "Unknown mechanism receipt.");
                foreach (CellView cell in mechanism.openCells)
                    opened.Add(ExploreKey(cell.x, cell.y));
            }
            // Rebuild tiles rather than mutating the authored map or a cached navigation grid.
            if (opened.Count > 0)
                encounter.tiles = Array.ConvertAll(
                    encounter.tiles,
                    tile => new TileDef
                    {
                        x = tile.x,
                        y = tile.y,
                        blocked = tile.blocked && !opened.Contains(ExploreKey(tile.x, tile.y)),
                        tags = (string[])tile.tags.Clone(),
                    }
                );
            generatedWalkGrids.Remove(encounter);
        }

        private List<string> MechanismAbilities(RosterView member)
        {
            List<string> result = new List<string>();
            foreach (string id in catalog.Classes[member.classId].abilityIds)
                if (!result.Contains(id))
                    result.Add(id);
            foreach (string id in Grants(member.id, xp, equipped))
                if (!result.Contains(id))
                    result.Add(id);
            return result;
        }

        private int MechanismManaCost(string owner, string abilityId)
        {
            return Math.Max(
                0,
                AbilityScaling.Apply(catalog.Abilities[abilityId], Modifiers(owner, abilityId)).cost
            );
        }

        private MechanismTransition ResolveMechanism(GameCommand command)
        {
            Require(
                generatedDungeon != null
                    && generatedDungeon.floorPlan != null
                    && screen == "explore",
                "Use mechanisms while exploring a generated floor."
            );
            GeneratedMechanismDef mechanism = Array.Find(
                generatedDungeon.floorPlan.mechanisms ?? new GeneratedMechanismDef[0],
                m => m.id == command.targetId
            );
            Require(mechanism != null, "Unknown mechanism.");
            Require(
                !Array.Exists(
                    generatedDungeon.mechanismReceipts ?? new MechanismReceipt[0],
                    r => r.mechanismId == mechanism.id
                ),
                "This mechanism is already solved."
            );
            GeneratedMechanismSolutionDef solution = Array.Find(
                mechanism.solutions,
                s => s.id == command.solutionId
            );
            Require(solution != null, "Unknown mechanism solution.");
            Require(
                Near(generatedDungeon, solution.x, solution.y)
                    && Array.Exists(
                        generatedDungeon.revealed,
                        c => c.x == solution.x && c.y == solution.y
                    ),
                "Reach and discover the mechanism action first."
            );
            RosterView member = GetRoster(command.unitId);
            Require(
                Definition(member.id).deployable && member.selected && member.hp > 0,
                "Choose a living deployed crawler."
            );
            int mana = 0;
            string abilityId = null;
            if (solution.kind == "ability")
            {
                abilityId = command.abilityId;
                AbilityDef ability;
                Require(
                    abilityId != null
                        && catalog.Abilities.TryGetValue(abilityId, out ability)
                        && MechanismAbilities(member).Contains(abilityId),
                    "This crawler has not learned that ability."
                );
                ability = catalog.Abilities[abilityId];
                Require(
                    Array.IndexOf(ability.incomingTags, solution.abilityTag) >= 0,
                    "This ability does not supply the mechanism capability."
                );
                mana = MechanismManaCost(member.id, abilityId);
                Require(member.energy >= mana, "Insufficient mana for this mechanism solution.");
            }
            else
                Require(
                    string.IsNullOrEmpty(command.abilityId),
                    "Only ability solutions select a spell."
                );
            int itemBefore = 0,
                itemAfter = 0;
            if (solution.kind == "item")
            {
                itemBefore = inventory[solution.itemId];
                Require(
                    itemBefore >= solution.itemCount,
                    "Insufficient supplies for this mechanism solution."
                );
                itemAfter = itemBefore - solution.itemCount;
            }
            GeneratedDungeonState next = CopyGenerated(generatedDungeon);
            List<MechanismReceipt> receipts = new List<MechanismReceipt>(next.mechanismReceipts);
            receipts.Add(
                new MechanismReceipt
                {
                    mechanismId = mechanism.id,
                    solutionId = solution.id,
                    unitId = member.id,
                    abilityId = abilityId,
                }
            );
            next.mechanismReceipts = receipts.ToArray();
            EncounterDef nextEncounter = BuildCustomEncounter(CopyCustomMap(customMap), true);
            ValidateFloorSave(
                new GameSave
                {
                    generatedDungeon = next,
                    customMap = customMap,
                    screen = screen,
                },
                nextEncounter
            );
            return new MechanismTransition
            {
                state = next,
                encounter = nextEncounter,
                actor = member,
                preview = new MechanismPreviewView
                {
                    mechanismId = mechanism.id,
                    solutionId = solution.id,
                    unitId = member.id,
                    abilityId = abilityId,
                    label = mechanism.label,
                    description = solution.description,
                    manaBefore = member.energy,
                    manaAfter = member.energy - mana,
                    itemId = solution.kind == "item" ? solution.itemId : null,
                    itemCountBefore = itemBefore,
                    itemCountAfter = itemAfter,
                    openedCells = Array.ConvertAll(mechanism.openCells, CopyCell),
                    canConfirm = true,
                },
            };
        }

        private bool TryMechanismCommand(GameCommand command)
        {
            if (command.type == "cancel_mechanism")
            {
                pendingMechanismCommand = null;
                pendingMechanismPreview = null;
                message = "Mechanism choice canceled.";
                return true;
            }
            if (command.type == "preview_mechanism")
            {
                MechanismTransition transition = ResolveMechanism(command);
                pendingMechanismCommand = new GameCommand
                {
                    type = command.type,
                    targetId = command.targetId,
                    solutionId = command.solutionId,
                    unitId = command.unitId,
                    abilityId = command.abilityId,
                };
                pendingMechanismPreview = transition.preview;
                message = "Review the shortcut and its exact resource cost.";
                return true;
            }
            if (command.type != "confirm_mechanism")
                return false;
            GameCommand pending = pendingMechanismCommand;
            pendingMechanismCommand = null;
            pendingMechanismPreview = null;
            Require(
                pending != null,
                "Preview the mechanism again; its confirmation is missing or stale."
            );
            MechanismTransition committed = ResolveMechanism(pending);
            generatedDungeon = committed.state;
            customEncounter = committed.encounter;
            committed.actor.energy = committed.preview.manaAfter;
            if (committed.preview.itemId != null)
                inventory[committed.preview.itemId] = committed.preview.itemCountAfter;
            RevealFloor();
            message =
                committed.preview.label
                + " opened. The shortcut is permanent; every encounter still needs to be cleared.";
            presentationEvents.Add(
                new PresentationEvent
                {
                    type = "mechanism_open",
                    actorId = committed.actor.id,
                    targetId = committed.preview.mechanismId,
                    abilityId = committed.preview.abilityId,
                    amount = committed.preview.openedCells.Length,
                }
            );
            AddLog(message);
            return true;
        }

        private MechanismView[] MechanismViews()
        {
            if (generatedDungeon == null || generatedDungeon.floorPlan == null)
                return new MechanismView[0];
            List<MechanismView> result = new List<MechanismView>();
            foreach (
                GeneratedMechanismDef mechanism in generatedDungeon.floorPlan.mechanisms
                    ?? new GeneratedMechanismDef[0]
            )
            {
                bool solved = Array.Exists(
                    generatedDungeon.mechanismReceipts ?? new MechanismReceipt[0],
                    r => r.mechanismId == mechanism.id
                );
                List<MechanismSolutionView> solutions = new List<MechanismSolutionView>();
                foreach (GeneratedMechanismSolutionDef solution in mechanism.solutions)
                {
                    if (
                        !Array.Exists(
                            generatedDungeon.revealed,
                            c => c.x == solution.x && c.y == solution.y
                        )
                    )
                        continue;
                    string locationReason =
                        solved ? "Already solved"
                        : screen != "explore" ? "Available during exploration"
                        : !Near(generatedDungeon, solution.x, solution.y)
                            ? "Reach this action location"
                        : "";
                    List<MechanismCandidateView> candidates = new List<MechanismCandidateView>();
                    foreach (RosterDef definition in data.roster)
                    {
                        RosterView member = roster[definition.id];
                        if (!definition.deployable || !member.selected)
                            continue;
                        List<string> abilities =
                            solution.kind == "ability"
                                ? MechanismAbilities(member)
                                    .FindAll(id =>
                                        Array.IndexOf(
                                            catalog.Abilities[id].incomingTags,
                                            solution.abilityTag
                                        ) >= 0
                                    )
                                : new List<string> { null };
                        foreach (string ability in abilities)
                        {
                            int cost = ability == null ? 0 : MechanismManaCost(member.id, ability);
                            string reason = locationReason;
                            if (reason == "" && member.hp <= 0)
                                reason = "Crawler is defeated";
                            if (reason == "" && member.energy < cost)
                                reason = "Insufficient mana";
                            if (
                                reason == ""
                                && solution.kind == "item"
                                && inventory[solution.itemId] < solution.itemCount
                            )
                                reason = "Insufficient supplies";
                            candidates.Add(
                                new MechanismCandidateView
                                {
                                    unitId = member.id,
                                    unitLabel = member.label,
                                    abilityId = ability,
                                    abilityLabel =
                                        ability == null ? null : catalog.Abilities[ability].label,
                                    manaCost = cost,
                                    enabled = reason == "",
                                    disabledReason = reason,
                                }
                            );
                        }
                    }
                    bool enabled = candidates.Exists(c => c.enabled);
                    string disabled =
                        enabled ? ""
                        : locationReason != "" ? locationReason
                        : candidates.Count == 0 ? "No deployed crawler has the required ability tag"
                        : candidates[0].disabledReason;
                    solutions.Add(
                        new MechanismSolutionView
                        {
                            id = solution.id,
                            label = solution.label,
                            description = solution.description,
                            kind = solution.kind,
                            x = solution.x,
                            y = solution.y,
                            abilityTag = solution.abilityTag,
                            itemId = solution.itemId,
                            itemCount = solution.itemCount,
                            enabled = enabled,
                            disabledReason = disabled,
                            candidates = candidates.ToArray(),
                        }
                    );
                }
                if (solutions.Count > 0 || solved)
                    result.Add(
                        new MechanismView
                        {
                            id = mechanism.id,
                            label = mechanism.label,
                            description = mechanism.description,
                            x = mechanism.x,
                            y = mechanism.y,
                            solved = solved,
                            materialTags = (string[])mechanism.materialTags.Clone(),
                            openedCells = solved
                                ? Array.ConvertAll(mechanism.openCells, CopyCell)
                                : new CellView[0],
                            solutions = solutions.ToArray(),
                        }
                    );
            }
            return result.ToArray();
        }

        private void AddMechanismPoints(List<ExplorationPointView> points)
        {
            foreach (MechanismView mechanism in MechanismViews())
            {
                HashSet<string> locations = new HashSet<string>();
                foreach (MechanismSolutionView solution in mechanism.solutions)
                {
                    if (!locations.Add(ExploreKey(solution.x, solution.y)))
                        continue;
                    bool sharedLocation =
                        Array
                            .FindAll(
                                mechanism.solutions,
                                option => option.x == solution.x && option.y == solution.y
                            )
                            .Length > 1;
                    points.Add(
                        new ExplorationPointView
                        {
                            id = "mechanism:" + mechanism.id + ":" + solution.id,
                            mechanismId = mechanism.id,
                            solutionId = solution.id,
                            label = sharedLocation ? mechanism.label : solution.label,
                            description = sharedLocation
                                ? mechanism.description
                                : solution.description,
                            kind = "mechanism",
                            x = solution.x,
                            y = solution.y,
                            claimed = mechanism.solved,
                            canInteract =
                                screen == "explore"
                                && !mechanism.solved
                                && Near(generatedDungeon, solution.x, solution.y),
                        }
                    );
                }
            }
        }
    }
}
