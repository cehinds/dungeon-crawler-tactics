namespace DccRebuild;

public class SourceDefinition
{
    public string id = "", title = "", url = "", kind = "", locator = "", confidence = "";
}
public class ContentReference
{
    public string kind = "", id = "";
}
public class Availability
{
    public int minFloor = 1, maxFloor = 99;
    public bool active = true;
    public string reason = "";
    public string[] requiredEvents = [];
    public bool Allows(int floor, IEnumerable<string> events) => active && floor >= minFloor && floor <= maxFloor && requiredEvents.All(events.Contains);
}
public class TemporaryModifierDefinition : CatalogDefinition
{
    public string skillId = "";
    public int amount, duration = 2;
}
public class SourceReference
{
    public string sourceId = "", locator = "", confidence = "";
}
public class CatalogDefinition
{
    public string id = "", name = "", ownerId = "", loreStatus = "", sourceNote = "", confidence = "", adaptationStatus = "";
    public string[] sourceIds = [], tags = [];
    public string description = "";
    public SourceReference[] sourceRefs = [];
    public ContentReference[] references = [];
    public Availability availability = new();
}
public class CharacterDefinition : CatalogDefinition
{
    public string runtimeId = "", role = "", race = "", appearance = "";
    public bool deployable;
    public string[] skillIds = [];
}
public class RumorDefinition : CatalogDefinition { public string locationId = ""; }
public class LocationDefinition : CatalogDefinition { public string worldObjectId = "", visitStatus = ""; }
public class RecipeDefinition : CatalogDefinition { public string[] ingredientIds = []; public string resultItemId = ""; }
public class StoryEventDefinition : CatalogDefinition { public string trigger = "", triggerId = ""; public string[] unlockSkillIds = []; }
public class FacilityDefinition : CatalogDefinition { public string locationId = ""; }
public class ClassDefinition : CatalogDefinition { public string[] skillIds = []; }

/// <summary>Typed indexes retain authored IDs; runtime IDs are a separate compatibility boundary.</summary>
public sealed class ContentCatalog
{
    public readonly Content Content;
    readonly Dictionary<string, Dictionary<string, CatalogDefinition>> indexes = new(StringComparer.Ordinal);
    public ContentCatalog(Content content)
    {
        if (content == null) throw new InvalidOperationException("content: missing root.");
        foreach (var field in typeof(Content).GetFields().Where(f => f.FieldType.IsArray))
            if (field.GetValue(content) == null) throw new InvalidOperationException("content." + field.Name + ": null collection.");
        var resource = typeof(ContentCatalog).Assembly.GetManifestResourceNames().SingleOrDefault(n => n.EndsWith("content-catalog.json", StringComparison.Ordinal));
        if (resource != null && content.characters.Length == 0 && content.locations.Length == 0)
        {
            using var stream = typeof(ContentCatalog).Assembly.GetManifestResourceStream(resource);
            using var reader = new System.IO.StreamReader(stream!);
            var supplement = Codec.Read<Content>(reader.ReadToEnd());
            content.explosiveAssetIds = content.explosiveAssetIds.Concat(supplement.explosiveAssetIds).ToArray();
            content.destructibleAssetIds = content.destructibleAssetIds.Concat(supplement.destructibleAssetIds).ToArray();
            content.characters = content.characters.Concat(supplement.characters).ToArray(); content.locations = content.locations.Concat(supplement.locations).ToArray();
            content.rumors = content.rumors.Concat(supplement.rumors).ToArray();
            content.recipes = content.recipes.Concat(supplement.recipes).ToArray(); content.storyEvents = content.storyEvents.Concat(supplement.storyEvents).ToArray();
            content.temporaryModifiers = content.temporaryModifiers.Concat(supplement.temporaryModifiers).ToArray();
            content.facilities = content.facilities.Concat(supplement.facilities).ToArray(); content.classes = content.classes.Concat(supplement.classes).ToArray();
            content.resupplyOffers = content.resupplyOffers.Concat(supplement.resupplyOffers).ToArray();
            content.sources = content.sources.Concat(supplement.sources).ToArray();
        }
        Content = content;
        Add("character", content.characters.Length > 0 ? content.characters : content.party);
        Add("location", content.locations); Add("rumor", content.rumors); Add("item", content.items); Add("skill", content.skills);
        Add("resupplyOffer", content.resupplyOffers);
        Add("enemy", content.enemies); Add("recipe", content.recipes); Add("encounter", content.encounters);
        Add("temporaryModifier", content.temporaryModifiers); Add("storyEvent", content.storyEvents); Add("facility", content.facilities); Add("class", content.classes);
        ContentValidator.Validate(this);
    }
    void Add(string kind, IEnumerable<CatalogDefinition> definitions)
    {
        var index = new Dictionary<string, CatalogDefinition>(StringComparer.Ordinal);
        foreach (var definition in definitions)
        {
            if (definition == null || string.IsNullOrWhiteSpace(definition.id))
                throw new InvalidOperationException($"content.{kind}: missing stable ID.");
            if (!index.TryAdd(definition.id, definition))
                throw new InvalidOperationException($"content.{kind}[{definition.id}]: duplicate ID.");
        }
        indexes.Add(kind, index);
    }
    public IEnumerable<(string kind, CatalogDefinition definition)> Entries => indexes.SelectMany(pair => pair.Value.Values.Select(d => (pair.Key, d)));
    public CatalogDefinition Find(string kind, string id) => indexes.GetValueOrDefault(kind)?.GetValueOrDefault(id);
    public T Get<T>(string kind, string id) where T : CatalogDefinition => Find(kind, id) as T ?? throw new InvalidOperationException($"content.{kind}[{id}]: missing definition.");
    public CharacterDefinition[] Deployable(int floor, IEnumerable<string> events) => indexes["character"].Values.Cast<CharacterDefinition>().Where(c => c.deployable && c.availability.Allows(floor, events)).ToArray();
}
