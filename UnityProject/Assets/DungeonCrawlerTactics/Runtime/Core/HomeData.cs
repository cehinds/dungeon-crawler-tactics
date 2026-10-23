using System;

namespace DungeonCrawlerTactics
{
    [Serializable] public sealed class HomeDef
    {
        public string label, description, economyNote;
        public int availableFromFloor = 4, startingGold, victoryGoldBase, victoryGoldPerFloor, trainingGoldCost;
        public int trainingUses = 1;
        public string[] trainingAbilityIds = new string[0];
        public HomeUpgradeDef[] upgrades = new HomeUpgradeDef[0];
        public HomeClubDef[] clubs = new HomeClubDef[0];
    }
    [Serializable] public sealed class HomeClubDef
    {
        public string id, label, description;
        public int minimumFloor = 3;
        public string[] eligibleClassIds = new string[0], excludedRosterIds = new string[0], sourceIds = new string[0];
    }
    [Serializable] public sealed class HomeMembershipSave { public string clubId, unitId, earnedClassId; public int earnedFloor; public bool story; }
    [Serializable] public sealed class HomeMembershipView
    {
        public string clubId, unitId, label, description, disabledReason, entryDisabledReason, earnedClassId;
        public int minimumFloor;
        public bool earned, canClaim, entryEligible;
        public string[] sourceIds = new string[0];
    }
    [Serializable] public sealed class HomeUpgradeDef
    {
        public string id, label, description, kind, prerequisiteId, costNote, priceBasis;
        // Club admission is personal and earned. Unknown prices never become a purchasable pass.
        public bool purchasable = true;
        public string eligibilityReason;
        public int cost, craftOutputBonus;
        public string[] sourceIds = new string[0];
    }
    [Serializable] public sealed class HomeSave
    {
        public int version = 1, gold;
        public string[] purchasedIds = new string[0], victoryReceiptIds = new string[0];
        public HomeTrainingSave[] training = new HomeTrainingSave[0];
        public HomeMembershipSave[] memberships = new HomeMembershipSave[0];
    }
    [Serializable] public sealed class HomeTrainingSave { public string unitId, abilityId; public int floorIndex; public bool story; }
    [Serializable] public sealed class HomeTrainingView { public string unitId, abilityId, label, disabledReason; public int cost, beforeUses, afterUses, beforeRank, afterRank; public bool enabled; }
    [Serializable] public sealed class HomeUpgradeView
    {
        public string id, label, description, kind, costNote, priceBasis, disabledReason;
        public int cost, craftOutputBonus;
        public bool purchased, enabled, purchasable;
        public string[] sourceIds = new string[0];
    }
    [Serializable] public sealed class HomeRoomView
    {
        public string id, label, kind, ownerId, description;
        public bool unlocked;
    }
    [Serializable] public sealed class HomePurchaseForecast
    {
        public string type, upgradeId, clubId, unitId, abilityId, label, benefit;
        public int cost, beforeGold, afterGold, beforeUses, afterUses, beforeRank, afterRank;
    }
    [Serializable] public sealed class HomeSocialView
    {
        public bool unlocked;
        public string description;
        public int victories, floorsComplete, cardsCaptured;
        public string[] achievementIds = new string[0];
    }
    [Serializable] public sealed class HomeView
    {
        public string label, description, economyNote, disabledReason, trainingDisabledReason, craftingDisabledReason;
        public int gold, availableFromFloor, craftOutputBonus;
        public bool available, owned, trainingUnlocked, craftingUnlocked, canConfirm;
        public HomeRoomView[] rooms = new HomeRoomView[0];
        public HomeUpgradeView[] upgrades = new HomeUpgradeView[0];
        public HomeTrainingView[] training = new HomeTrainingView[0];
        public HomeMembershipView[] memberships = new HomeMembershipView[0];
        public HomePurchaseForecast forecast;
        public HomeSocialView social;
    }

    public static class HomeDefinitionValidator
    {
        private static void Need(bool value, string message) { if (!value) throw new ArgumentException(message); }
        public static void Validate(HomeDef definition, Catalog catalog, RosterDef[] roster)
        {
            Validate(definition);
            if (definition == null) return;
            foreach (string id in definition.trainingAbilityIds) Need(catalog.Abilities.ContainsKey(id), "Unknown home training ability.");
            foreach (HomeClubDef club in definition.clubs)
            {
                foreach (string id in club.eligibleClassIds) Need(catalog.Classes.ContainsKey(id) && catalog.Classes[id].playerSelectable, "Unknown or enemy-only club eligible class.");
                foreach (string id in club.excludedRosterIds) Need(Array.Exists(roster, r => r.id == id), "Unknown excluded club crawler.");
            }
        }
        public static void Validate(HomeDef definition)
        {
            if (definition == null) return;
            Need(!string.IsNullOrEmpty(definition.label) && !string.IsNullOrEmpty(definition.description) && !string.IsNullOrEmpty(definition.economyNote), "Home identity and economy note are required.");
            Need(definition.availableFromFloor >= 1 && definition.availableFromFloor <= 8 && definition.startingGold >= 0 && definition.startingGold <= 100000000 && definition.victoryGoldBase >= 0 && definition.victoryGoldBase <= 10000000 && definition.victoryGoldPerFloor >= 0 && definition.victoryGoldPerFloor <= 1000000, "Unbounded home economy.");
            Need(definition.upgrades != null && definition.upgrades.Length <= 32, "Invalid home upgrades.");
            Need(definition.trainingGoldCost >= 0 && definition.trainingGoldCost <= 1000000 && definition.trainingUses >= 1 && definition.trainingUses <= 5 && definition.trainingAbilityIds != null && definition.trainingAbilityIds.Length <= 100, "Invalid home training rules.");
            var trainingIds = new System.Collections.Generic.HashSet<string>();
            foreach (string id in definition.trainingAbilityIds) Need(!string.IsNullOrEmpty(id) && trainingIds.Add(id), "Invalid home training ability.");
            Need(definition.clubs != null && definition.clubs.Length <= 8, "Invalid club eligibility catalog.");
            var clubIds = new System.Collections.Generic.HashSet<string>();
            foreach (HomeClubDef club in definition.clubs)
            {
                Need(club != null && club.id != null && System.Text.RegularExpressions.Regex.IsMatch(club.id, @"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$") && clubIds.Add(club.id) && !string.IsNullOrEmpty(club.label) && !string.IsNullOrEmpty(club.description), "Invalid club identity.");
                Need(club.minimumFloor >= 1 && club.minimumFloor <= 8 && club.eligibleClassIds != null && club.eligibleClassIds.Length > 0 && club.eligibleClassIds.Length <= 100 && club.excludedRosterIds != null && club.excludedRosterIds.Length <= 32 && club.sourceIds != null && club.sourceIds.Length > 0 && club.sourceIds.Length <= 8, "Invalid club admission requirements.");
                var references = new System.Collections.Generic.HashSet<string>();
                foreach (string id in club.eligibleClassIds) Need(!string.IsNullOrEmpty(id) && references.Add(id), "Invalid duplicate club class eligibility.");
                references.Clear();
                foreach (string id in club.excludedRosterIds) Need(!string.IsNullOrEmpty(id) && references.Add(id), "Invalid duplicate excluded club crawler.");
                references.Clear();
                foreach (string id in club.sourceIds) Need(!string.IsNullOrEmpty(id) && references.Add(id), "Invalid duplicate club source.");
            }
            var ids = new System.Collections.Generic.HashSet<string>();
            int spaces = 0;
            foreach (HomeUpgradeDef upgrade in definition.upgrades)
            {
                Need(upgrade != null && upgrade.id != null && System.Text.RegularExpressions.Regex.IsMatch(upgrade.id, @"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)+$") && ids.Add(upgrade.id) && !string.IsNullOrEmpty(upgrade.label) && !string.IsNullOrEmpty(upgrade.description), "Invalid home upgrade identity.");
                Need(upgrade.kind == "space" || upgrade.kind == "training" || upgrade.kind == "crafting" || upgrade.kind == "tools" || upgrade.kind == "social" || upgrade.kind == "club", "Unknown home upgrade kind.");
                Need(upgrade.cost >= 0 && upgrade.cost <= 100000000 && upgrade.craftOutputBonus >= 0 && upgrade.craftOutputBonus <= 5 && (upgrade.craftOutputBonus == 0 || upgrade.kind == "tools"), "Unbounded home upgrade benefit or cost.");
                Need(upgrade.priceBasis == "verified" || upgrade.priceBasis == "approximate" || upgrade.priceBasis == "adaptation" || upgrade.priceBasis == "unknown", "Home price needs an evidence classification.");
                Need(!string.IsNullOrEmpty(upgrade.costNote) && upgrade.sourceIds != null && upgrade.sourceIds.Length <= 8, "Home upgrade requires price context and sources.");
                foreach (string source in upgrade.sourceIds) Need(!string.IsNullOrEmpty(source), "Invalid home source reference.");
                Need(upgrade.purchasable || !string.IsNullOrEmpty(upgrade.eligibilityReason), "Unavailable upgrades require an eligibility explanation.");
                Need(upgrade.kind != "club" || !upgrade.purchasable && upgrade.priceBasis == "unknown" && upgrade.cost == 0, "Club admission is personal and cannot be sold as a generic home pass.");
                Need(upgrade.priceBasis != "unknown" || !upgrade.purchasable, "An unknown price cannot become a purchasable upgrade.");
                if (upgrade.kind == "space") spaces++;
            }
            Need(spaces == 1, "A housing catalog requires exactly one personal space.");
            foreach (HomeUpgradeDef upgrade in definition.upgrades)
            {
                var chain = new System.Collections.Generic.HashSet<string>();
                HomeUpgradeDef current = upgrade;
                while (!string.IsNullOrEmpty(current.prerequisiteId))
                {
                    Need(chain.Add(current.id), "Home prerequisite cycle.");
                    current = Array.Find(definition.upgrades, u => u.id == current.prerequisiteId);
                    Need(current != null && current.purchasable, "Unknown or ineligible home prerequisite.");
                }
                Need(upgrade.kind == "space" || !upgrade.purchasable || current.kind == "space", "Home upgrades must require the personal space.");
            }
        }
    }
}
