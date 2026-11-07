namespace DccRebuild;

// Rules use stable tags and operation kinds, never display names or skill IDs.
public sealed class EffectStatus
{
    public string id = "", sourceId = "", stacking = "refresh";
    public int duration = 1, strength = 1;
    public string[] tags = [];
}
public sealed class EffectObject
{
    public string id = "", propId = "", assetId = "";
    public int x, y, width = 1, height = 1, hp = 10;
    public bool blocksMovement = true, blocksSight = true, destroyed;
    public string[] tags = [];
}
public sealed class EffectHazard
{
    public string id = "", tag = "";
    public int x, y, duration = -1, strength = 2;
}
public sealed class EffectOperation
{
    // damage, heal, status, removeStatus, move, displace, resource, object, tick
    public string kind = "damage", targetId = "", tag = "", statusId = "", resource = "mp", stacking = "refresh";
    public int amount, radius, x, y, dx, dy, duration = 2, strength = 2;
    public bool area, resolveDefense;
    public string damageElement = "";
}
public sealed class EffectRequest
{
    public string sourceId = "", targetId = "";
    public int x, y;
    public List<EffectOperation> operations = [];
}
public sealed class EffectEvent
{
    public string kind = "", sourceId = "", targetId = "", tag = "", detail = "";
    public int amount, x, y, radius;
}
public sealed class EffectResolution
{
    public Battle state;
    public Point[] affectedCells = [];
    public List<EffectEvent> events = [];
    public bool valid;
    public string reason = "";
}
public sealed class EffectRules
{
    public List<TagReactionDefinition> reactions = [];
    public DamageBonusDefinition[] damageBonuses =
    [
        new() { incomingTag = "arcane", targetTag = "physical", amount = 2, reaction = "Arcane impact: +2 damage." },
        new() { incomingTag = "fire", targetTag = "physical", amount = 3, reaction = "Blast shock: +3 damage." }
    ];
    public int maximumReactionSteps = 128;
    public string[] ignitionTags = ["fire", "ignition", "explosion"];
    public string[] extinguishTags = ["water", "suppressant"];
    public string fuelTag = "oil", burningStatus = "burning", explosiveTag = "explosive";
    public int burningDuration = 2, burningStrength = 2, explosionDamage = 6, explosionRadius = 1;
}
public sealed class TagReactionDefinition
{
    public string id = "", targetKind = "unit", trigger = "effect";
    public string[] triggerTags = [], requiredTargetTags = [], excludedTargetTags = [], removeTags = [];
    public EffectOperation[] operations = [];
    public int priority;
}

public sealed class DamageBonusDefinition
{
    public string incomingTag = "", targetTag = "", reaction = "";
    public int amount;
}
