namespace DccRebuild;
public static class ContentValidator
{
    public static void Validate(ContentCatalog catalog)
    {
        EffectResolver.ValidateRules(catalog.Content.effectRules);
        PreparationService.ValidateOffers(catalog.Content, catalog.Content.resupplyOffers);
        var sources = new HashSet<string>();
        foreach (var source in catalog.Content.sources)
            if (source == null || string.IsNullOrWhiteSpace(source.id) || !sources.Add(source.id))
                throw new InvalidOperationException("content.sources: missing or duplicate source ID.");
        foreach (var (kind, d) in catalog.Entries)
        {
            string path = $"content.{kind}[{d.id}]";
            foreach (var field in d.GetType().GetFields())
                if ((field.FieldType.IsArray || field.FieldType.IsGenericType && field.FieldType.GetGenericTypeDefinition() == typeof(Dictionary<,>)) && field.GetValue(d) == null) Fail(path + "." + field.Name, "null collection");
            if (d.availability == null || d.availability.minFloor < 1 || d.availability.maxFloor < d.availability.minFloor)
                Fail(path + ".availability", "invalid floor range");
            if (d.sourceIds == null || d.sourceRefs == null || d.tags == null || d.references == null || d.availability.requiredEvents == null)
                Fail(path, "null metadata collection");
            if (string.IsNullOrWhiteSpace(d.adaptationStatus) || string.IsNullOrWhiteSpace(d.confidence)) Fail(path + ".provenance", "adaptation status and confidence are required");
            if (string.IsNullOrWhiteSpace(d.description)) Fail(path + ".description", "required description is missing");
            if (d.tags.Any(string.IsNullOrWhiteSpace) || d.tags.Distinct().Count() != d.tags.Length) Fail(path + ".tags", "empty or duplicate stable tag");
            if (d.tags.Length == 0) Fail(path + ".tags", "at least one stable tag is required");
            if (d.sourceRefs.Length == 0) Fail(path + ".sourceRefs", "at least one provenance reference is required");
            foreach (var reference in d.sourceRefs)
                if (reference == null || !sources.Contains(reference.sourceId) || string.IsNullOrWhiteSpace(reference.locator) || string.IsNullOrWhiteSpace(reference.confidence))
                    Fail(path + ".sourceRefs", "source, locator and confidence are required");
            if (d.ownerId != "" && catalog.Find("character", d.ownerId) == null)
                Fail(path + ".ownerId", "missing character " + d.ownerId);
            if (d.references.Any(r => r == null || string.IsNullOrWhiteSpace(r.kind) || string.IsNullOrWhiteSpace(r.id))) Fail(path + ".references", "null or empty typed reference");
            if (d.references.Select(r => r.kind + ":" + r.id).Distinct().Count() != d.references.Length)
                Fail(path + ".references", "duplicate typed reference");
            foreach (var id in d.sourceIds)
                if (!sources.Contains(id)) Fail(path + ".sourceIds", "missing source " + id);
            foreach (var r in References(kind, d))
                if (catalog.Find(r.kind, r.id) == null) Fail(path + ".references", $"missing {r.kind}:{r.id}");
            foreach (var id in d.availability.requiredEvents)
                if (catalog.Find("storyEvent", id) == null) Fail(path + ".availability.requiredEvents", "missing event " + id);
            if (d is CharacterDefinition characterDefinition && characterDefinition.deployable && characterDefinition.availability.active && characterDefinition.availability.minFloor == 1)
                foreach (var skillId in characterDefinition.skillIds)
                {
                    var startingSkill = catalog.Get<Skill>("skill", skillId);
                    if (!startingSkill.availability.Allows(1, [])) Fail(path + ".skillIds", "ineligible starting skill " + skillId);
                }
            if (d is Encounter effectEncounter)
            {
                var ids = new HashSet<string>();
                var arena = World.BuildArena(1, effectEncounter.id);
                foreach (var obj in effectEncounter.effectObjects)
                    if (obj == null || string.IsNullOrWhiteSpace(obj.id) || !ids.Add(obj.id) || obj.tags == null || obj.width < 1 || obj.height < 1 || obj.x < 0 || obj.y < 0 || obj.hp < 1 || obj.destroyed || obj.x + obj.width > arena.width || obj.y + obj.height > arena.height || obj.tags.Any(string.IsNullOrWhiteSpace)) Fail(path + ".effectObjects", "invalid or duplicate authored object");
                ids.Clear();
                foreach (var hazard in effectEncounter.hazards)
                    if (hazard == null || string.IsNullOrWhiteSpace(hazard.id) || string.IsNullOrWhiteSpace(hazard.tag) || hazard.x < 0 || hazard.y < 0 || !ids.Add(hazard.id) || hazard.x >= arena.width || hazard.y >= arena.height || hazard.duration < -1 || hazard.strength < 0) Fail(path + ".hazards", "invalid authored hazard");
            }
            if (d is Encounter rewardEncounter)
            {
                if (rewardEncounter.xpReward is < 0 or > 100000 || rewardEncounter.goldReward is < 0 or > 100000 || rewardEncounter.itemRewards.Any(r => r == null || r.count is < 1 or > 999) || rewardEncounter.itemRewards.Select(r => r.itemId).Distinct().Count() != rewardEncounter.itemRewards.Length) Fail(path + ".rewards", "invalid or duplicate rewards");
                foreach (var r in rewardEncounter.itemRewards)
                {
                    var rewardItem = catalog.Get<Item>("item", r.itemId);
                    if (!rewardItem.availability.active || rewardItem.availability.minFloor > rewardEncounter.availability.minFloor || rewardItem.availability.maxFloor < rewardEncounter.availability.maxFloor || rewardItem.availability.requiredEvents.Any(id => !rewardEncounter.availability.requiredEvents.Contains(id))) Fail(path + ".itemRewards", "ineligible reward item " + r.itemId);
                }
            }
            if (d is Encounter encounterDefinition && encounterDefinition.availability.active && encounterDefinition.enemyIds.Length == 0) Fail(path + ".enemyIds", "active encounter has no enemies");
            if (d is Encounter activeEncounter && activeEncounter.availability.active && activeEncounter.availability.minFloor == 1)
                foreach (var enemyId in activeEncounter.enemyIds)
                {
                    var enemy = catalog.Get<Enemy>("enemy", enemyId);
                    if (!enemy.availability.active || enemy.availability.minFloor > 1 || enemy.availability.requiredEvents.Any(id => !activeEncounter.availability.requiredEvents.Contains(id))) Fail(path + ".enemyIds", "ineligible Floor 1 enemy " + enemyId);
                }
            if (d is CharacterDefinition c && c.deployable && c.availability.active && c.availability.minFloor <= 1 && c.id is not ("crawler.carl" or "crawler.donut"))
                Fail(path, "only Carl and Donut may deploy on Floor 1");
            if (kind == "class" && d.availability.minFloor < 3) Fail(path + ".availability.minFloor", "classes require Floor 3");
            if (d is Item boundedItem && (boundedItem.kind is not ("weapon" or "armor" or "charm" or "consumable") || boundedItem.power is < 0 or > 1000 || boundedItem.armor is < 0 or > 1000 || boundedItem.heal is < 0 or > 1000 || boundedItem.mp is < 0 or > 1000)) Fail(path, "invalid item kind or tactical values");
            if (d is Item startingItem)
            {
                if (startingItem.startingCount is < 0 or > 999) Fail(path + ".startingCount", "starting count must be between 0 and 999");
                if (startingItem.startingCount > 0 && (!PreparationService.IsEquipment(startingItem) || !startingItem.availability.Allows(1, []) || !catalog.Deployable(1, []).Any(c => startingItem.ownerId == "" || startingItem.ownerId == c.id)))
                    Fail(path + ".startingCount", "starting equipment must be available on Floor 1 and owned by an eligible party member");
            }
            if (d is Item item && item.rankModifiers.Count > 0 && d.adaptationStatus != "adapted" && d.adaptationStatus != "source-approved")
                Fail(path + ".rankModifiers", "rank modifiers require adapted or source-approved status");
            if (d is TemporaryModifierDefinition temporary && (temporary.amount is < -20 or > 20 || temporary.duration is < 1 or > 100 || (temporary.adaptationStatus != "adapted" && temporary.adaptationStatus != "source-approved")))
                Fail(path, "invalid temporary rank modifier amount, duration or provenance");
            if (d is Item modifierItem)
                foreach (var modifier in modifierItem.rankModifiers)
                    if (catalog.Find("skill", modifier.Key) == null || modifier.Value is < -20 or > 20)
                        Fail(path + ".rankModifiers", "missing skill or invalid bonus " + modifier.Key);
            if (d is Skill effectSkill)
            {
                if (effectSkill.effectOperations == null) Fail(path + ".effectOperations", "null operations");
                foreach (var op in effectSkill.effectOperations) EffectResolver.ValidateOperation(op, path + ".effectOperations");
            }
            if (d is Skill skill && (skill.rankCapacity != 20 || skill.permissionMaxRank < skill.startingRank || skill.permissionMaxRank > 20))
                Fail(path, "invalid rank capacity or mastery permission");
        }
        var world = World.Build(1);
        foreach (var location in catalog.Content.locations)
            if (location.worldObjectId != "" && !world.objects.Any(o => o.id == location.worldObjectId)) Fail("content.location[" + location.id + "].worldObjectId", "missing world object " + location.worldObjectId);
        foreach (var ev in catalog.Content.storyEvents)
            if (ev.trigger != "" && (ev.trigger is not ("clear" or "interact") || !world.objects.Any(o => o.id == ev.triggerId))) Fail("content.storyEvent[" + ev.id + "].triggerId", "missing or invalid trigger " + ev.triggerId);
        var characters = catalog.Entries.Where(e => e.kind == "character").Select(e => (CharacterDefinition)e.definition).ToArray();
        var aliases = characters.Where(c => c.runtimeId != "").Select(c => c.runtimeId).ToArray();
        if (aliases.Distinct().Count() != aliases.Length) Fail("content.character.runtimeId", "duplicate runtime alias");
        foreach (string id in new[] { "crawler.carl", "crawler.donut" })
        {
            var character = characters.SingleOrDefault(c => c.id == id);
            if (character == null || !character.deployable || !character.availability.Allows(1, [])) Fail("content.character[" + id + "]", "required Floor 1 party member is not deployable");
        }
        var visiting = new HashSet<string>(); var visited = new HashSet<string>();
        foreach (var e in catalog.Content.storyEvents) Visit(e.id);
        void Visit(string id)
        {
            if (visited.Contains(id)) return;
            if (!visiting.Add(id)) Fail("content.storyEvent[" + id + "].availability.requiredEvents", "cyclic prerequisite");
            foreach (var dependency in catalog.Get<StoryEventDefinition>("storyEvent", id).availability.requiredEvents) Visit(dependency);
            visiting.Remove(id); visited.Add(id);
        }
    }
    static IEnumerable<ContentReference> References(string kind, CatalogDefinition d)
    {
        foreach (var r in d.references) yield return r;
        if (d is CharacterDefinition c) foreach (var id in c.skillIds) yield return new() { kind = "skill", id = id };
        if (d is Encounter e) foreach (var id in e.enemyIds) yield return new() { kind = "enemy", id = id };
        if (d is Encounter rewardEncounter) foreach (var reward in rewardEncounter.itemRewards) yield return new() { kind = "item", id = reward.itemId };
        if (d is ResupplyOffer offer) yield return new() { kind = "item", id = offer.itemId };
        if (d is RecipeDefinition recipe)
        {
            foreach (var id in recipe.ingredientIds) yield return new() { kind = "item", id = id };
            yield return new() { kind = "item", id = recipe.resultItemId };
        }
        if (d is FacilityDefinition f && f.locationId != "") yield return new() { kind = "location", id = f.locationId };
        if (d is StoryEventDefinition ev) foreach (var id in ev.unlockSkillIds) yield return new() { kind = "skill", id = id };
        if (d is TemporaryModifierDefinition modifier) yield return new() { kind = "skill", id = modifier.skillId };
        if (d is ClassDefinition cls) foreach (var id in cls.skillIds) yield return new() { kind = "skill", id = id };
    }
    static void Fail(string path, string message) => throw new InvalidOperationException(path + ": " + message + ".");
}
