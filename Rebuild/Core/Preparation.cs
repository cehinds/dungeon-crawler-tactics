namespace DccRebuild;

/// <summary>Repeatable adapted supply purchase shared by every safe room; no finite stock or hidden receipts.</summary>
public class ResupplyOffer : CatalogDefinition
{
    public string itemId = "";
    public int quantity = 1, goldCost;
}
public class SafeRoomPreparation
{
    public string safeRoomId = "", reason = "";
    public bool restAllowed, saveAllowed, preparationAllowed, resupplyAllowed;
}
public class EquipmentPreview
{
    public string actorId = "", itemId = "", reason = "", equippedById = "";
    public bool available;
    public int count, powerDelta, armorDelta;
    public Dictionary<string, int> rankDeltas = new();
}
public class ConsumablePreview
{
    public string actorId = "", itemId = "", reason = "";
    public bool available;
    public int count, heal, mp;
}
public class ResupplyPreview
{
    public string offerId = "", itemId = "", name = "", reason = "";
    public bool available;
    public int quantity, goldCost, count;
}

/// <summary>Authoritative preparation previews and commits. Inventory counts include equipped items.</summary>
public static class PreparationService
{
    public const int InventoryCountCap = 999;
    public static SafeRoomPreparation SafeRoom(View state)
    {
        var room = state.world?.objects.FirstOrDefault(o => o.kind == "safe" && Math.Abs(state.x - o.x) + Math.Abs(state.y - o.y) <= 1);
        bool allowed = state.mode == "explore" && room != null;
        return new() { safeRoomId = room?.id ?? "", restAllowed = allowed, saveAllowed = allowed, preparationAllowed = allowed, resupplyAllowed = allowed,
            reason = allowed ? "Safe room services available." : "Visit a safe room between battles." };
    }
    public static bool IsEquipment(Item item) => item != null && (item.kind == "weapon" || item.kind == "armor" || item.kind == "charm");
    public static bool CanOwn(Content content, Unit actor, Item item)
    {
        if (actor == null || item == null) return false;
        if (item.ownerId == "") return true;
        return item.ownerId == actor.id ||
            content.characters.Concat(content.party).Any(c => c.id == item.ownerId && c.runtimeId == actor.id);
    }
    public static EquipmentPreview PreviewEquipment(Content content, View state, string actorId, string itemId)
    {
        var p = new EquipmentPreview { actorId = actorId, itemId = itemId };
        var actor = state.party.FirstOrDefault(u => u.id == actorId);
        var item = content.items.FirstOrDefault(i => i.id == itemId);
        var old = content.items.FirstOrDefault(i => i.id == actor?.equipment);
        p.count = state.inventory.FirstOrDefault(s => s.itemId == itemId)?.count ?? 0;
        p.equippedById = state.party.FirstOrDefault(u => u.equipment == itemId && itemId != "")?.id ?? "";
        if (state.mode != "explore") p.reason = "Equip between battles.";
        else if (actor == null) p.reason = "Choose a crawler.";
        else if (itemId != "" && (!IsEquipment(item) || p.count <= 0)) p.reason = "Choose owned equipment.";
        else if (itemId != "" && !item.availability.Allows(state.floor, state.unlockedEvents)) p.reason = "This equipment is not available yet.";
        else if (itemId != "" && !CanOwn(content, actor, item)) p.reason = "This personal equipment belongs to another crawler.";
        else if (itemId != "" && actor.id == "carl" && item.kind == "weapon") p.reason = "Carl fights with his bare hands and feet.";
        else if (itemId != "" && p.equippedById != "" && p.equippedById != actorId) p.reason = "That item is already equipped by the other crawler.";
        else
        {
            p.available = true;
            p.powerDelta = (item?.power ?? 0) - (old?.power ?? 0);
            p.armorDelta = (item?.armor ?? 0) - (old?.armor ?? 0);
            foreach (var id in (item?.rankModifiers.Keys ?? Enumerable.Empty<string>()).Union(old?.rankModifiers.Keys ?? Enumerable.Empty<string>()))
                p.rankDeltas[id] = (item?.rankModifiers.GetValueOrDefault(id) ?? 0) - (old?.rankModifiers.GetValueOrDefault(id) ?? 0);
            if ((long)actor.power + p.powerDelta < 0 || (long)actor.power + p.powerDelta > 1000 || (long)actor.armor + p.armorDelta < 0 || (long)actor.armor + p.armorDelta > 1000)
            { p.available = false; p.reason = "Equipment would exceed supported stat limits."; return p; }
            p.reason = itemId == "" ? "Remove current equipment." : actor.equipment == itemId ? "Already equipped." : "Ready to equip.";
        }
        return p;
    }
    public static EquipmentPreview Equip(Content content, View state, string actorId, string itemId)
    {
        var p = PreviewEquipment(content, state, actorId, itemId);
        if (!p.available) return p;
        var actor = state.party.Single(u => u.id == actorId);
        actor.power += p.powerDelta; actor.armor += p.armorDelta; actor.equipment = itemId;
        return p;
    }
    public static ConsumablePreview PreviewConsumable(Content content, View state, string actorId, string itemId)
    {
        var p = new ConsumablePreview { actorId = actorId, itemId = itemId, count = state.inventory.FirstOrDefault(s => s.itemId == itemId)?.count ?? 0 };
        var actor = (state.mode == "battle" ? state.battle?.units : state.party)?.FirstOrDefault(u => u.id == actorId);
        var item = content.items.FirstOrDefault(i => i.id == itemId);
        if (actor == null || item == null || item.kind != "consumable" || p.count <= 0) p.reason = "Choose an owned consumable.";
        else if (actor.hp <= 0) p.reason = "Rest at a safe room to revive this crawler.";
        else if (state.mode != "explore" && !(state.mode == "battle" && state.battle?.phase == "party" && !actor.acted && !actor.ended && actor.hp > 0)) p.reason = "This crawler cannot use an item now.";
        else if (!item.availability.Allows(state.floor, state.unlockedEvents)) p.reason = "This item is not available yet.";
        else if (item.heal <= 0 && item.mp <= 0) p.reason = "This item's effect is not implemented.";
        else
        {
            p.heal = Math.Min(Math.Max(0, actor.maxHp - actor.hp), item.heal);
            p.mp = Math.Min(Math.Max(0, actor.maxMp - actor.mp), item.mp);
            p.available = p.heal > 0 || p.mp > 0;
            p.reason = p.available ? "Ready to use." : "This crawler's resources are already full.";
        }
        return p;
    }
    public static ResupplyPreview PreviewResupply(Content content, View state, IEnumerable<ResupplyOffer> offers, string offerId)
    {
        var offer = offers.FirstOrDefault(o => o.id == offerId);
        var p = new ResupplyPreview { offerId = offerId };
        if (offer == null) { p.reason = "Choose a supply offer."; return p; }
        p.itemId = offer.itemId; p.name = offer.name; p.quantity = offer.quantity; p.goldCost = offer.goldCost;
        p.count = state.inventory.FirstOrDefault(s => s.itemId == offer.itemId)?.count ?? 0;
        var item = content.items.FirstOrDefault(i => i.id == offer.itemId);
        if (!SafeRoom(state).resupplyAllowed) p.reason = "Buy supplies at a safe room between battles.";
        else if (item == null || item.kind != "consumable" || (item.heal <= 0 && item.mp <= 0) || offer.quantity <= 0 || offer.goldCost <= 0) p.reason = "This supply offer is invalid.";
        else if (!offer.availability.Allows(state.floor, state.unlockedEvents) || !item.availability.Allows(state.floor, state.unlockedEvents)) p.reason = "This supply is not available yet.";
        else if (p.count < 0 || (long)p.count + offer.quantity > InventoryCountCap) p.reason = "Inventory count limit reached.";
        else if (state.gold < offer.goldCost) p.reason = "Not enough gold.";
        else { p.available = true; p.reason = "Ready to buy."; }
        return p;
    }
    public static ResupplyPreview Purchase(Content content, View state, IEnumerable<ResupplyOffer> offers, string offerId)
    {
        var p = PreviewResupply(content, state, offers, offerId);
        if (!p.available) return p;
        var stack = state.inventory.FirstOrDefault(s => s.itemId == p.itemId);
        if (stack == null) state.inventory.Add(new() { itemId = p.itemId, count = p.quantity });
        else stack.count += p.quantity;
        state.gold -= p.goldCost;
        return p;
    }
    public static void ValidateOffers(Content content, IEnumerable<ResupplyOffer> offers)
    {
        var ids = new HashSet<string>(StringComparer.Ordinal);
        foreach (var offer in offers)
        {
            if (offer == null || string.IsNullOrWhiteSpace(offer.id) || !ids.Add(offer.id)) throw new InvalidOperationException("content.resupplyOffers: missing or duplicate offer ID.");
            var item = content.items.FirstOrDefault(i => i.id == offer.itemId);
            if (item == null || item.kind != "consumable" || (item.heal <= 0 && item.mp <= 0)) throw new InvalidOperationException($"content.resupplyOffers[{offer.id}]: expected implemented restorative consumable.");
            if (offer.quantity < 1 || offer.quantity > InventoryCountCap || offer.goldCost < 1 || offer.goldCost > 100000) throw new InvalidOperationException($"content.resupplyOffers[{offer.id}]: invalid quantity or gold cost.");
        }
    }
}
