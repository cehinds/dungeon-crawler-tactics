using System.Text.Json;
namespace DccRebuild;
public class Content
{
    public string title = "Dungeon Crawler Carl"; public Item[] items = []; public Skill[] skills = []; public Enemy[] enemies = []; public Encounter[] encounters = [];
}
public class Item
{
    public string id = "", name = "", kind = "", description = ""; public int power, armor, heal, mp;
}
public class Skill
{
    public string id = "", name = "", element = "physical", description = ""; public int cost, power, range = 1;
}
public class Encounter
{
    public string id = ""; public string[] enemyIds = [];
}
public class Enemy
{
    public string id = "", name = "", element = "physical"; public int hp = 20, power = 5, armor;
}
public class Command
{
    public string type = "", direction = "", targetId = "", actorId = "", skillId = "", itemId = ""; public int x, y;
}
public class Unit
{
    public string id = "", templateId = "", name = "", equipment = "", element = "physical"; public int x, y, hp, maxHp, mp, maxMp, level = 1, xp, power, armor; public bool moved, acted, ended; public string[] skills = []; public Dictionary<string, int> ranks = new();
}
public class Stack
{
    public string itemId = ""; public int count;
}
public class Point
{
    public int x, y;
}
public class Battle
{
    public string theme = "", composition = ""; public string[] tiles = []; public WorldProp[] props = [];
    public int width = 10, height = 8; public string phase = "party", encounterId = ""; public List<Unit> units = []; public List<Unit> enemies = []; public Point[] obstacles = [new() { x = 4, y = 2 }, new() { x = 4, y = 3 }, new() { x = 5, y = 5 }];
}
public class Forecast
{
    public string actorId = "", targetId = "", skillId = "", reaction = ""; public int damage, cost; public bool valid;
}
public class View
{
    public string mode = "explore", message = "", selectedId = "carl"; public int seed, turn = 1, questStage, gold, x, y; public List<Unit> party = []; public List<Stack> inventory = []; public WorldMap world; public Battle battle; public Forecast forecast; public List<string> journal = []; public List<string> cleared = [];
}
public class Save
{
    public int version = 1; public View state;
}
public static class Codec
{
    public static readonly JsonSerializerOptions Options = new() { IncludeFields = true }; public static string Write<T>(T value) => JsonSerializer.Serialize(value, Options); public static T Read<T>(string value) => JsonSerializer.Deserialize<T>(value, Options);
}
