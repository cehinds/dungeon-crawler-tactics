using System.Text.Json;
namespace DccRebuild;
public class Content
{
    public string title = "Dungeon Crawler Carl";
    public SourceDefinition[] sources = [];
    public CharacterDefinition[] party = [], characters = [];
    public LocationDefinition[] locations = [];
    public RumorDefinition[] rumors = [];
    public RecipeDefinition[] recipes = [];
    public StoryEventDefinition[] storyEvents = [];
    public FacilityDefinition[] facilities = [];
    public ClassDefinition[] classes = [];
    public TemporaryModifierDefinition[] temporaryModifiers = [];
    public Item[] items = [];
    public Skill[] skills = [];
    public Enemy[] enemies = [];
    public Encounter[] encounters = [];
    public ProgressionRules progression = new();
    public EffectRules effectRules = new();
    public string[] destructibleAssetIds = [], explosiveAssetIds = [];
}
public class Item : CatalogDefinition
{
    public string kind = "";
    public Dictionary<string, int> rankModifiers = new();
    public int power, armor, heal, mp;
}
public class Skill : CatalogDefinition
{
    public string element = "physical";
    public int permissionMaxRank = 5, rankCapacity = 20;
    public string effectTag = "", targetKind = "enemy";
    public int effectRadius;
    public EffectOperation[] effectOperations = [];
    public int cost, power, range = 1;
    public int startingRank = 1;
    public SkillRank[] ranks = [];
}
public class Encounter : CatalogDefinition
{
    public string[] enemyIds = [];
    public int xpReward = 30, goldReward = 25;
    public EffectHazard[] hazards = [];
    public EffectObject[] effectObjects = [];
}
public class Enemy : CatalogDefinition
{
    public string element = "physical";
    public int hp = 20, power = 5, armor;
    }
public class Command
{
    public string type = "", direction = "", targetId = "", actorId = "", skillId = "", itemId = "";
    public int x, y, manaSpend;
}
public class Unit
{
    public string id = "", templateId = "", name = "", equipment = "", element = "physical";
    public int x, y, hp, maxHp, mp, maxMp, level = 1, xp, power, armor;
    public bool moved, acted, ended;
    public string[] tags = [];
    public List<EffectStatus> statuses = [];
    public string[] skills = [];
    public Dictionary<string, int> ranks = new();
    public Dictionary<string, int> temporaryRankModifiers = new();
    public Dictionary<string, int> skillPractice = new();
    public SkillProgress[] skillProgress = [];
    public int xpToNext, maxLevel = 20;
    public double xpProgressPercent;
    public string nextLevelEffect = "";
}
public class Stack
{
    public string itemId = "";
    public int count;
}
public class Point
{
    public int x, y;
}
public class Battle
{
    public string theme = "", composition = "";
    public string[] tiles = [];
    public WorldProp[] props = [];
    public int width = 10, height = 8;
    public string phase = "party", encounterId = "";
    public List<EffectObject> effectObjects = [];
    public List<EffectHazard> hazards = [];
    public List<EffectEvent> effectEvents = [];
    public int effectRevision;
    public List<Unit> units = [];
    public List<Unit> enemies = [];
    public Point[] obstacles = [new() { x = 4, y = 2 }, new() { x = 4, y = 3 }, new() { x = 5, y = 5 }];
}
public class Forecast
{
    public string actorId = "", targetId = "", skillId = "", reaction = "";
    public int damage, cost, manaSpend, trainedRank, effectiveRank, effectRank, range, x, y;
    public bool valid;
    public List<EffectEvent> events = [];
}
public class View
{
    public string mode = "explore", message = "", selectedId = "carl";
    public int seed, turn = 1, questStage, gold, x, y;
    public List<Unit> party = [];
    public List<Stack> inventory = [];
    public WorldMap world;
    public Battle battle;
    public Forecast forecast;
    public List<string> journal = [];
    public List<string> cleared = [];
    public List<string> unlockedEvents = [];
    public List<string> destroyedPropIds = [];
    public List<string> destroyedEncounterObjectIds = [];
    public int floor = 1;
    public AvailabilityView[] availability = [];
}
public class Save
{
    public int version = 3;
    public View state;
}
public static class Codec
{
    public static readonly JsonSerializerOptions Options = new() { IncludeFields = true };
    public static string Write<T>(T value) => JsonSerializer.Serialize(value, Options);
    public static T Read<T>(string value) => JsonSerializer.Deserialize<T>(value, Options);
}

public class AvailabilityView
{
    public string kind = "", id = "", name = "", reason = "";
    public bool available, unlocked;
}
