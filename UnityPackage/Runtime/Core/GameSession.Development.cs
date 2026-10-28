using System;
using System.Collections.Generic;
namespace DungeonCrawlerTactics
{
    public sealed partial class GameSession
    {
        private readonly List<StatAllocationSave> allocations = new List<StatAllocationSave>();
        private readonly List<SkillPracticeSave> practices = new List<SkillPracticeSave>();
        private readonly List<OwnedLootBoxSave> ownedBoxes = new List<OwnedLootBoxSave>();
        private GameCommand pendingDevelopment;
        private void ResetDevelopment()
        {
            allocations.Clear();
            practices.Clear();
            ownedBoxes.Clear();
            pendingDevelopment = null;
        }
        private int Allocated(string owner, string stat, List<StatAllocationSave> source)
        {
            StatAllocationSave row = source.Find(s => s.unitId == owner && s.statId == stat);
            return row == null ? 0 : row.points;
        }
        private int SpentPoints(string owner, List<StatAllocationSave> source)
        {
            int result = 0;
            foreach (StatAllocationSave row in source)
                if (row.unitId == owner)
                    result += row.points;
            return result;
        }
        private void ApplyAllocatedStats(ClassStats stats, string owner, List<StatAllocationSave> source)
        {
            foreach (StatDefinition definition in data.development.stats)
            {
                int points = Allocated(owner, definition.id, source);
                stats.hp += points * definition.hpPerPoint;
                stats.energy += points * definition.manaPerPoint;
                if (definition.moveEvery > 0)
                    stats.move += points / definition.moveEvery;
            }
        }
        private ActionModifiers AllocationModifiers(string owner, List<StatAllocationSave> source)
        {
            ActionModifiers result = new ActionModifiers();
            foreach (StatDefinition definition in data.development.stats)
            {
                int points = Allocated(owner, definition.id, source);
                if (definition.damageEvery > 0)
                    result.damageBonus += points / definition.damageEvery;
                if (definition.healEvery > 0)
                    result.healBonus += points / definition.healEvery;
            }
            return result;
        }
        private ActionModifiers Modifiers(string owner, string ability)
        {
            if (!roster.ContainsKey(owner)) return new ActionModifiers();
            ActionModifiers result = AllocationModifiers(owner, allocations);
            ActionModifiers tree = TreeModifiers(owner, unlockedSkillNodes);
            SkillPracticeSave row = practices.Find(p => p.unitId == owner && p.abilityId == ability);
            SkillRankView rank = CurrentPracticeRank(owner, ability, row == null ? 0 : row.uses);
            result.damageBonus = Math.Min(100, result.damageBonus + tree.damageBonus + rank.damageBonus);
            result.healBonus = Math.Min(100, result.healBonus + tree.healBonus + rank.healBonus);
            result.rangeBonus = rank.rangeBonus; result.pushBonus = rank.pushBonus; result.summonHpBonus = rank.summonHpBonus; result.summonMoveBonus = rank.summonMoveBonus; result.summonRoundsBonus = rank.summonRoundsBonus;
            result.tagReplacements = rank.tagReplacements; result.addTags = rank.addTags; result.removeTags = rank.removeTags;
            result.costReduction = rank.costReduction;
            return result;
        }
        private void PracticeCommitted(GameCommand command)
        {
            string abilityId = ModePracticeAbility(command);
            if (!string.IsNullOrEmpty(command.itemId) || string.IsNullOrEmpty(abilityId) || !roster.ContainsKey(command.unitId))
                return;
            SkillPracticeSave row = practices.Find(p => p.unitId == command.unitId && p.abilityId == abilityId);
            if (row == null)
            {
                row = new SkillPracticeSave { unitId = command.unitId, abilityId = abilityId };
                practices.Add(row);
            }
            SkillPracticeView before = PracticeView(row.unitId, row.abilityId, row.uses);
            if (before.atCap) return;
            int capUses = before.ranks[before.maxRank - 1].requiredUses;
            row.uses = Math.Min(capUses, row.uses + 1);
            presentationEvents.Add(new PresentationEvent { type = "skill_practice", actorId = row.unitId, abilityId = row.abilityId, amount = row.uses, before = before.rank, after = PracticeView(row.unitId, row.abilityId, row.uses).rank });
        }
        private List<StatAllocationSave> ProposedAllocations(GameCommand command)
        {
            Require(screen == "camp", "Allocate stats in the safe room.");
            Require(JourneyAllocationUnlocked, "Stat allocation unlocks on floor 3; earned points remain banked.");
            RosterView member = GetRoster(command.unitId);
            Require(Definition(member.id).deployable, "Advisors do not allocate crawler stats.");
            Require(Array.Exists(data.development.stats, s => s.id == command.statId) && command.points > 0 && command.points <= 100, "Choose a supported stat and positive point count.");
            Require(SpentPoints(member.id, allocations) + command.points <= (LevelAt(xp) - 1) * data.development.pointsPerLevel, "Not enough unspent stat points.");
            List<StatAllocationSave> result = CloneAllocations(allocations);
            StatAllocationSave row = result.Find(s => s.unitId == member.id && s.statId == command.statId);
            if (row == null)
                result.Add(new StatAllocationSave { unitId = member.id, statId = command.statId, points = command.points });
            else
                row.points += command.points;
            return result;
        }
        private static List<StatAllocationSave> CloneAllocations(List<StatAllocationSave> source)
        {
            return source.ConvertAll(s => new StatAllocationSave { unitId = s.unitId, statId = s.statId, points = s.points });
        }
        private void PreviewAllocation(GameCommand command)
        {
            pendingDevelopment = null;
            ProposedAllocations(command);
            pendingDevelopment = new GameCommand { unitId = command.unitId, statId = command.statId, points = command.points };
            message = "Review the stat change; confirm or cancel without spending.";
        }
        private void ConfirmAllocation()
        {
            Require(pendingDevelopment != null, "Preview a stat allocation first.");
            List<StatAllocationSave> next = ProposedAllocations(pendingDevelopment);
            string owner = pendingDevelopment.unitId;
            allocations.Clear();
            allocations.AddRange(next);
            pendingDevelopment = null;
            RefreshRosterStats(false);
            presentationEvents.Add(new PresentationEvent { type = "stat_allocation", actorId = owner });
            message = "Stat points allocated. New caps do not refill HP or mana; rest to recover.";
        }
        private RecipeDef Recipe(string id)
        {
            RecipeDef recipe = Array.Find(data.development.recipes, r => r.id == id);
            Require(recipe != null, "Unknown recipe.");
            return recipe;
        }
        private string CraftReason(RecipeDef recipe)
        {
            if (screen != "camp")
                return "Craft in the safe room.";
            string homeReason = HomeCraftingReason();
            if (homeReason != "") return homeReason;
            foreach (ItemQuantity ingredient in recipe.ingredients)
                if (inventory[ingredient.itemId] < ingredient.count)
                    return "Missing ingredients.";
            foreach (ItemQuantity output in HomeRecipeOutputs(recipe))
                if (inventory[output.itemId] + output.count > 10000)
                    return "Inventory capacity exceeded.";
            return "";
        }
        private void Craft(string id)
        {
            RecipeDef recipe = Recipe(id);
            string reason = CraftReason(recipe);
            Require(reason == "", reason);
            foreach (ItemQuantity ingredient in recipe.ingredients)
                inventory[ingredient.itemId] -= ingredient.count;
            foreach (ItemQuantity output in HomeRecipeOutputs(recipe))
                inventory[output.itemId] += output.count;
            presentationEvents.Add(new PresentationEvent { type = "craft", tag = recipe.id });
            message = "Crafted " + recipe.label + ".";
        }
        private void GrantLoot(string source, bool victory)
        {
            if (ActiveExpeditionEncounter != null)
                return;
            foreach (LootBoxDef definition in data.development.lootBoxes)
                if ((victory && definition.fromVictory) || (!victory && definition.achievementId == source))
                {
                    string id = definition.id + ":" + source;
                    if (ownedBoxes.Exists(b => b.id == id))
                        continue;
                    ownedBoxes.Add(new OwnedLootBoxSave { id = id, definitionId = definition.id, sourceId = source });
                    presentationEvents.Add(new PresentationEvent { type = "loot_box_earned", tag = id });
                }
        }
        private void OpenLootBox(string id)
        {
            Require(screen == "camp", "Open loot boxes in the safe room.");
            OwnedLootBoxSave owned = ownedBoxes.Find(b => b.id == id);
            Require(owned != null && !owned.opened, "This loot box is unavailable or already open.");
            LootBoxDef definition = Array.Find(data.development.lootBoxes, b => b.id == owned.definitionId);
            foreach (ItemQuantity reward in definition.rewards)
                Require(inventory[reward.itemId] + reward.count <= 10000, "Inventory capacity exceeded.");
            foreach (ItemQuantity reward in definition.rewards)
                inventory[reward.itemId] += reward.count;
            owned.opened = true;
            presentationEvents.Add(new PresentationEvent { type = "loot_box_opened", tag = id });
            message = "Opened " + definition.label + ". Rewards added to shared supplies.";
        }
        private DevelopmentForecast AllocationForecast()
        {
            if (pendingDevelopment == null)
                return null;
            List<StatAllocationSave> next = ProposedAllocations(pendingDevelopment);
            string owner = pendingDevelopment.unitId;
            ClassStats before = PlayerStats(owner, roster[owner].classId), after = PlayerStats(owner, roster[owner].classId, xp, equipped);
            ApplyAllocatedStats(after, owner, next);
            ApplyTreeStats(after, owner, unlockedSkillNodes);
            ApplyModes(after, owner, roster[owner].stanceId, roster[owner].formId);
            ActionModifiers oldModifiers = AllocationModifiers(owner, allocations), newModifiers = AllocationModifiers(owner, next);
            return new DevelopmentForecast { unitId = owner, statId = pendingDevelopment.statId, points = pendingDevelopment.points, beforeHp = before.hp, afterHp = after.hp, beforeMana = before.energy, afterMana = after.energy, beforeMove = before.move, afterMove = after.move, beforeDamageBonus = oldModifiers.damageBonus, afterDamageBonus = newModifiers.damageBonus, beforeHealBonus = oldModifiers.healBonus, afterHealBonus = newModifiers.healBonus };
        }
        private string[] KnownPracticeAbilities(string owner)
        {
            List<string> ids = new List<string>(Grants(owner, xp, equipped));
            if (JourneyAllocationUnlocked) foreach (string id in catalog.Classes[roster[owner].classId].abilityIds) if (!ids.Contains(id)) ids.Add(id);
            ids.Sort(StringComparer.Ordinal); return ids.ToArray();
        }
        private void PopulateDevelopment(GameView view)
        {
            List<CrawlerDevelopmentView> crawlers = new List<CrawlerDevelopmentView>();
            List<SkillPracticeView> skillViews = new List<SkillPracticeView>();
            foreach (RosterDef member in data.roster)
                if (member.deployable)
                {
                    crawlers.Add(new CrawlerDevelopmentView { unitId = member.id, maxSkillRank = MaximumSkillRank(member.id), unspentPoints = (LevelAt(xp) - 1) * data.development.pointsPerLevel - SpentPoints(member.id, allocations), allocated = CloneAllocations(allocations.FindAll(a => a.unitId == member.id)).ToArray() });
                    foreach (string abilityId in KnownPracticeAbilities(member.id))
                    {
                        SkillPracticeSave row = practices.Find(p => p.unitId == member.id && p.abilityId == abilityId);
                        skillViews.Add(PracticeView(member.id, abilityId, row == null ? 0 : row.uses));
                    }
                }
            List<RecipeView> recipes = new List<RecipeView>();
            foreach (RecipeDef recipe in data.development.recipes)
            {
                string reason = CraftReason(recipe);
                recipes.Add(new RecipeView { id = recipe.id, label = recipe.label, description = recipe.description, ingredients = recipe.ingredients, outputs = HomeRecipeOutputs(recipe), enabled = reason == "", disabledReason = reason });
            }
            List<OwnedLootBoxView> boxes = new List<OwnedLootBoxView>();
            foreach (OwnedLootBoxSave row in ownedBoxes)
            {
                LootBoxDef definition = Array.Find(data.development.lootBoxes, b => b.id == row.definitionId);
                boxes.Add(new OwnedLootBoxView { id = row.id, label = definition.label, description = definition.description, sourceId = row.sourceId, opened = row.opened, enabled = screen == "camp" && !row.opened, rewards = definition.rewards });
            }
            view.development = new DevelopmentView { available = screen == "camp", description = data.development.description, stats = data.development.stats, crawlers = crawlers.ToArray(), practice = skillViews.ToArray(), rankCatalog = screen == "camp" ? RankCatalog() : new SkillRankCatalogView[0], recipes = recipes.ToArray(), lootBoxes = boxes.ToArray(), forecast = AllocationForecast(), canConfirm = pendingDevelopment != null };
        }
        private DevelopmentSave CaptureDevelopment()
        {
            return new DevelopmentSave { allocated = CloneAllocations(allocations).ToArray(), practice = practices.ConvertAll(p => new SkillPracticeSave { unitId = p.unitId, abilityId = p.abilityId, uses = p.uses }).ToArray(), lootBoxes = ownedBoxes.ConvertAll(b => new OwnedLootBoxSave { id = b.id, definitionId = b.definitionId, sourceId = b.sourceId, opened = b.opened }).ToArray() };
        }
        private DevelopmentSave ValidateDevelopment(GameSave save)
        {
            DevelopmentSave source = save.development ?? new DevelopmentSave();
            Require(source.version == 1 && source.allocated != null && source.practice != null && source.lootBoxes != null, "Invalid development save.");
            Require(source.allocated.Length <= data.roster.Length * data.development.stats.Length && source.practice.Length <= data.roster.Length * catalog.Abilities.Count && source.lootBoxes.Length <= 100, "Development collection exceeds limits.");
            HashSet<string> keys = new HashSet<string>();
            List<StatAllocationSave> next = new List<StatAllocationSave>();
            foreach (StatAllocationSave row in source.allocated)
            {
                Require(row != null && Definition(row.unitId) != null && Definition(row.unitId).deployable && Array.Exists(data.development.stats, d => d.id == row.statId) && row.points > 0 && row.points <= 100 && keys.Add(row.unitId + ":" + row.statId), "Invalid allocated stat.");
                next.Add(new StatAllocationSave { unitId = row.unitId, statId = row.statId, points = row.points });
            }
            foreach (RosterDef member in data.roster)
                Require(SpentPoints(member.id, next) <= (LevelAt(save.xp) - 1) * data.development.pointsPerLevel, "Allocated points exceed earned levels.");
            keys.Clear();
            List<SkillPracticeSave> practice = new List<SkillPracticeSave>();
            foreach (SkillPracticeSave row in source.practice)
            {
                Require(row != null && Definition(row.unitId) != null && Definition(row.unitId).deployable && row.abilityId != null && catalog.Abilities.ContainsKey(row.abilityId) && row.uses > 0 && row.uses <= 100000 && keys.Add(row.unitId + ":" + row.abilityId), "Invalid skill practice.");
                practice.Add(new SkillPracticeSave { unitId = row.unitId, abilityId = row.abilityId, uses = row.uses });
            }
            keys.Clear();
            List<OwnedLootBoxSave> boxes = new List<OwnedLootBoxSave>();
            foreach (OwnedLootBoxSave row in source.lootBoxes)
            {
                Require(row != null && !string.IsNullOrEmpty(row.id) && keys.Add(row.id), "Invalid owned loot box.");
                LootBoxDef definition = Array.Find(data.development.lootBoxes, b => b.id == row.definitionId);
                Require(definition != null && row.id == definition.id + ":" + row.sourceId, "Unknown loot box definition.");
                bool earned = !string.IsNullOrEmpty(definition.achievementId) && definition.achievementId == row.sourceId && Array.IndexOf(save.achievementIds, row.sourceId) >= 0;
                if (definition.fromVictory)
                    for (int i = 0; i < SaveVictories(save); i++)
                        if (row.sourceId == "victory." + data.encounters[i].id)
                            earned = true;
                Require(earned, "Loot box source was not earned.");
                boxes.Add(new OwnedLootBoxSave { id = row.id, definitionId = row.definitionId, sourceId = row.sourceId, opened = row.opened });
            }
            return new DevelopmentSave { allocated = next.ToArray(), practice = practice.ToArray(), lootBoxes = boxes.ToArray() };
        }
        private void CommitDevelopment(DevelopmentSave next)
        {
            allocations.Clear();
            allocations.AddRange(next.allocated);
            practices.Clear();
            practices.AddRange(next.practice);
            ownedBoxes.Clear();
            ownedBoxes.AddRange(next.lootBoxes);
            pendingDevelopment = null;
        }
    }
}
