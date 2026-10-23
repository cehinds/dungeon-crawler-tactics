using System;
using System.Collections.Generic;

namespace DungeonCrawlerTactics
{
    public sealed partial class GameSession
    {
        private HomeSave homeState;
        private string pendingHomeUpgrade;
        private GameCommand pendingHomeTraining;
        private GameCommand pendingHomeMembership;
        private const int MaximumGold = 2000000000;
        private void ResetHome()
        {
            HomeDefinitionValidator.Validate(data.home);
            if (data.home != null) foreach (string id in data.home.trainingAbilityIds) Require(catalog.Abilities.ContainsKey(id), "Unknown home training ability.");
            if (data.home != null) foreach (HomeClubDef club in data.home.clubs)
            {
                foreach (string id in club.eligibleClassIds) Require(catalog.Classes.ContainsKey(id) && catalog.Classes[id].playerSelectable, "Unknown or enemy-only club eligible class.");
                foreach (string id in club.excludedRosterIds) Require(Definition(id) != null, "Unknown excluded club crawler.");
            }
            homeState = data.home == null ? null : new HomeSave { gold = data.home.startingGold };
            pendingHomeUpgrade = null; pendingHomeTraining = null; pendingHomeMembership = null;
        }
        private HomeUpgradeDef HomeUpgrade(string id)
        {
            return data.home == null ? null : Array.Find(data.home.upgrades, u => u.id == id);
        }
        private bool HomeOwnsKind(string kind)
        {
            return homeState != null && Array.Exists(data.home.upgrades, u => u.kind == kind && Array.IndexOf(homeState.purchasedIds, u.id) >= 0);
        }
        private string HomeAvailabilityReason()
        {
            if (data.home == null) return "This content pack has no personal space.";
            if (screen != "camp" || ActiveExpeditionEncounter != null || ActiveScenarioEncounter != null || CustomEncounter(0) != null) return "Manage your home in the campaign safe room.";
            if (journey != null && journey.floorIndex + 1 < data.home.availableFromFloor) return "The shared party home opens on floor " + data.home.availableFromFloor + ".";
            return "";
        }
        // Existing three-encounter saves retain their free camp services. Housing gates apply
        // to the story campaign only; previously earned allocations never disappear.
        private string HomeTrainingReason()
        {
            return data.home != null && !HomeOwnsKind("training") ? "Install the Training Room for paid practice sessions. Normal class choices, skill trees and stat allocation keep their existing unlocks." : "";
        }
        private string HomeCraftingReason()
        {
            return data.home != null && JourneyActive && !HomeOwnsKind("crafting") ? "Purchase the Engineer's Table in your shared crafting room first." : "";
        }
        private int HomeCraftOutputBonus()
        {
            int total = 0;
            if (homeState != null)
                foreach (string id in homeState.purchasedIds) total += HomeUpgrade(id).craftOutputBonus;
            return total;
        }
        private ItemQuantity[] HomeRecipeOutputs(RecipeDef recipe)
        {
            int bonus = HomeCraftOutputBonus();
            return Array.ConvertAll(recipe.outputs, o => new ItemQuantity { itemId = o.itemId, count = o.count + bonus });
        }
        private string HomePurchaseReason(HomeUpgradeDef upgrade)
        {
            if (upgrade == null) return "Unknown home upgrade.";
            if (homeState != null && Array.IndexOf(homeState.purchasedIds, upgrade.id) >= 0) return "Already installed.";
            // A membership requirement cannot be bypassed by buying a generic pass.
            if (!upgrade.purchasable) return upgrade.eligibilityReason;
            string reason = HomeAvailabilityReason(); if (reason != "") return reason;
            if (!string.IsNullOrEmpty(upgrade.prerequisiteId) && Array.IndexOf(homeState.purchasedIds, upgrade.prerequisiteId) < 0) return "Requires " + HomeUpgrade(upgrade.prerequisiteId).label + ".";
            if (homeState.gold < upgrade.cost) return "Not enough gold.";
            return "";
        }
        private void ClearHomePreview(GameCommand command)
        {
            if (command.type != "preview_home_upgrade" && command.type != "confirm_home_upgrade" && command.type != "cancel_home_upgrade") pendingHomeUpgrade = null;
            if (command.type != "preview_home_training" && command.type != "confirm_home_training" && command.type != "cancel_home_training") pendingHomeTraining = null;
            if (command.type != "preview_home_membership" && command.type != "confirm_home_membership" && command.type != "cancel_home_membership") pendingHomeMembership = null;
        }
        private HomeClubDef HomeClub(string id) { return data.home == null ? null : Array.Find(data.home.clubs, c => c.id == id); }
        private string HomeClubEligibility(HomeClubDef club, string owner)
        {
            if (club == null) return "Unknown club.";
            RosterDef member = Definition(owner);
            if (member == null || !member.deployable) return "Club credentials belong to an individual field crawler.";
            if (Array.IndexOf(club.excludedRosterIds, owner) >= 0) return "Excluded by this club's admission rules. " + club.description;
            if (journey != null && journey.floorIndex + 1 < club.minimumFloor) return "This club's class-based access begins on floor " + club.minimumFloor + ".";
            if (Array.IndexOf(club.eligibleClassIds, roster[owner].classId) < 0) return "The crawler's current class does not grant this club's membership or entry.";
            return "";
        }
        private HomeMembershipView HomeMembershipOption(HomeClubDef club, string owner)
        {
            HomeMembershipSave earned = Array.Find(homeState.memberships, m => m.clubId == club.id && m.unitId == owner);
            string eligibility = HomeClubEligibility(club, owner);
            string reason = eligibility;
            if (reason == "" && earned != null) reason = "Personal membership already earned.";
            if (reason == "" && (screen != "camp" || ActiveExpeditionEncounter != null || ActiveScenarioEncounter != null || CustomEncounter(0) != null)) reason = "Claim class-based credentials in the campaign safe room.";
            return new HomeMembershipView { clubId = club.id, unitId = owner, label = club.label, description = club.description, minimumFloor = club.minimumFloor, earned = earned != null, earnedClassId = earned == null ? null : earned.earnedClassId, canClaim = reason == "", disabledReason = reason, entryEligible = earned != null && eligibility == "", entryDisabledReason = eligibility != "" ? eligibility : earned == null ? "Claim this crawler's personal class-based credential first." : "", sourceIds = (string[])club.sourceIds.Clone() };
        }
        private HomePurchaseForecast HomeMembershipForecast()
        {
            if (pendingHomeMembership == null) return null;
            HomeClubDef club = HomeClub(pendingHomeMembership.targetId);
            return new HomePurchaseForecast { type = "membership", clubId = club.id, unitId = pendingHomeMembership.unitId, label = club.label, benefit = "Record this crawler's class-granted personal membership. No purchase price is established and no gold is charged. Entry eligibility remains subject to current class and admission rules; this is an access record, not a playable club interior.", cost = 0, beforeGold = homeState.gold, afterGold = homeState.gold };
        }
        private HomeTrainingView HomeTrainingOption(string owner, string ability)
        {
            RosterDef member = Definition(owner);
            SkillPracticeSave practice = practices.Find(p => p.unitId == owner && p.abilityId == ability);
            int uses = practice == null ? 0 : practice.uses;
            string reason = HomeAvailabilityReason();
            if (reason == "" && !HomeOwnsKind("training")) reason = "Install the Training Room first.";
            if (reason == "" && (member == null || !member.deployable || Array.IndexOf(data.home.trainingAbilityIds, ability) < 0 || Array.IndexOf(Grants(owner, xp, equipped), ability) < 0 && Array.IndexOf(catalog.Classes[roster[owner].classId].abilityIds, ability) < 0)) reason = "Choose an authored training skill currently available to this crawler.";
            SkillPracticeView before = member == null || !catalog.Abilities.ContainsKey(ability ?? "") ? null : PracticeView(owner, ability, uses);
            int afterUses = before == null ? uses : Math.Min(before.ranks[before.maxRank - 1].requiredUses, uses + data.home.trainingUses);
            if (reason == "" && before.atCap) reason = "This skill is at its crawler's rank cap.";
            if (reason == "" && Array.Exists(homeState.training, t => t.unitId == owner && t.floorIndex == encounterIndex && t.story == (journey != null))) reason = "This crawler already trained on this floor. The once-per-floor limit is a game adaptation.";
            if (reason == "" && homeState.gold < data.home.trainingGoldCost) reason = "Not enough gold.";
            return new HomeTrainingView { unitId = owner, abilityId = ability, label = catalog.Abilities.ContainsKey(ability ?? "") ? catalog.Abilities[ability].label : ability, beforeUses = uses, afterUses = afterUses, beforeRank = before == null ? 0 : before.rank, afterRank = before == null ? 0 : PracticeView(owner, ability, afterUses).rank, cost = data.home.trainingGoldCost, enabled = reason == "", disabledReason = reason };
        }
        private HomePurchaseForecast HomeTrainingForecast()
        {
            if (pendingHomeTraining == null) return null;
            HomeTrainingView training = HomeTrainingOption(pendingHomeTraining.unitId, pendingHomeTraining.abilityId);
            return new HomePurchaseForecast { type = "training", unitId = training.unitId, abilityId = training.abilityId, label = training.label, cost = training.cost, beforeGold = homeState.gold, afterGold = homeState.gold - training.cost, beforeUses = training.beforeUses, afterUses = training.afterUses, beforeRank = training.beforeRank, afterRank = training.afterRank, benefit = "Paid practice in an authored nonmagical skill. Once per crawler per floor; gold cost, progress and timing are tactical adaptations." };
        }
        private bool TryHomeCommand(GameCommand command)
        {
            if (command.type == "cancel_home_membership") { pendingHomeMembership = null; message = "Membership claim canceled. No credential recorded or gold spent."; return true; }
            if (command.type == "preview_home_membership")
            {
                pendingHomeMembership = null;
                HomeClubDef club = HomeClub(command.targetId); Require(club != null, "Unknown club.");
                HomeMembershipView option = HomeMembershipOption(club, command.unitId); Require(option.canClaim, option.disabledReason);
                pendingHomeMembership = new GameCommand { unitId = command.unitId, targetId = club.id }; message = "Review this crawler's class-granted personal membership. No gold is charged."; return true;
            }
            if (command.type == "confirm_home_membership")
            {
                Require(pendingHomeMembership != null, "Preview a membership claim first.");
                HomeClubDef club = HomeClub(pendingHomeMembership.targetId); HomeMembershipView option = HomeMembershipOption(club, pendingHomeMembership.unitId); Require(option.canClaim, option.disabledReason);
                List<HomeMembershipSave> memberships = new List<HomeMembershipSave>(homeState.memberships);
                memberships.Add(new HomeMembershipSave { clubId = club.id, unitId = option.unitId, earnedClassId = roster[option.unitId].classId, earnedFloor = journey == null ? 0 : journey.floorIndex + 1, story = journey != null });
                homeState.memberships = memberships.ToArray(); pendingHomeMembership = null;
                presentationEvents.Add(new PresentationEvent { type = "club_membership", actorId = option.unitId, tag = club.id });
                message = "Personal " + club.label + " membership recorded for " + roster[option.unitId].label + ". No gold spent. Admission remains subject to the crawler's current eligibility."; return true;
            }
            if (command.type == "cancel_home_training") { pendingHomeTraining = null; message = "Training canceled. No gold or practice spent."; return true; }
            if (command.type == "preview_home_training")
            {
                pendingHomeTraining = null; Require(data.home != null, "This content pack has no home training.");
                HomeTrainingView option = HomeTrainingOption(command.unitId, command.abilityId); Require(option.enabled, option.disabledReason);
                pendingHomeTraining = new GameCommand { unitId = command.unitId, abilityId = command.abilityId }; message = "Review the exact gold and practice change, then confirm or cancel."; return true;
            }
            if (command.type == "confirm_home_training")
            {
                Require(pendingHomeTraining != null, "Preview a training session first.");
                HomeTrainingView option = HomeTrainingOption(pendingHomeTraining.unitId, pendingHomeTraining.abilityId); Require(option.enabled, option.disabledReason);
                SkillPracticeSave row = practices.Find(p => p.unitId == option.unitId && p.abilityId == option.abilityId);
                List<HomeTrainingSave> records = new List<HomeTrainingSave>(homeState.training); records.Add(new HomeTrainingSave { unitId = option.unitId, abilityId = option.abilityId, floorIndex = encounterIndex, story = journey != null });
                if (row == null) { row = new SkillPracticeSave { unitId = option.unitId, abilityId = option.abilityId }; practices.Add(row); }
                homeState.gold -= option.cost; row.uses = option.afterUses; homeState.training = records.ToArray(); pendingHomeTraining = null;
                presentationEvents.Add(new PresentationEvent { type = "skill_practice", actorId = option.unitId, abilityId = option.abilityId, amount = option.afterUses, before = option.beforeRank, after = option.afterRank });
                message = "Training complete: " + option.label + " practice " + option.beforeUses + " → " + option.afterUses + ". Spent " + option.cost + " gold."; return true;
            }
            if (command.type == "cancel_home_upgrade")
            {
                pendingHomeUpgrade = null; message = "Home purchase canceled. No gold spent."; return true;
            }
            if (command.type == "preview_home_upgrade")
            {
                pendingHomeUpgrade = null;
                HomeUpgradeDef upgrade = HomeUpgrade(command.targetId); string reason = HomePurchaseReason(upgrade); Require(reason == "", reason);
                pendingHomeUpgrade = upgrade.id; message = "Review the home upgrade and gold balance, then confirm or cancel."; return true;
            }
            if (command.type != "confirm_home_upgrade") return false;
            Require(pendingHomeUpgrade != null, "Preview a home upgrade first.");
            HomeUpgradeDef proposed = HomeUpgrade(pendingHomeUpgrade); string blocked = HomePurchaseReason(proposed); Require(blocked == "", blocked);
            List<string> installed = new List<string>(homeState.purchasedIds); installed.Add(proposed.id);
            // Fresh validation precedes both mutations: preview and commit use the same rule.
            homeState.gold -= proposed.cost; homeState.purchasedIds = installed.ToArray(); pendingHomeUpgrade = null;
            presentationEvents.Add(new PresentationEvent { type = "home_upgrade", tag = proposed.id, amount = proposed.cost });
            message = "Installed " + proposed.label + ". Spent " + proposed.cost + " gold."; return true;
        }
        private int HomeVictoryGold(int floor)
        {
            return (int)Math.Min(MaximumGold, (long)data.home.victoryGoldBase + (long)data.home.victoryGoldPerFloor * floor);
        }
        private void AwardHomeVictory()
        {
            if (homeState == null || ActiveExpeditionEncounter != null || ActiveScenarioEncounter != null || CustomEncounter(0) != null) return;
            string receipt = (JourneyActive ? "journey." + JourneyFloor.id : "legacy." + Encounter.id);
            if (Array.IndexOf(homeState.victoryReceiptIds, receipt) >= 0) return;
            int amount = HomeVictoryGold(encounterIndex + 1);
            Require((long)homeState.gold + amount <= MaximumGold, "Gold capacity exceeded.");
            List<string> receipts = new List<string>(homeState.victoryReceiptIds); receipts.Add(receipt);
            homeState.gold += amount; homeState.victoryReceiptIds = receipts.ToArray();
            AddLog("Safe-room deposit: +" + amount + " gold (adapted campaign reward).");
            presentationEvents.Add(new PresentationEvent { type = "gold_reward", amount = amount, tag = receipt });
        }
        private List<string> ExpectedHomeReceipts(GameSave save)
        {
            List<string> result = new List<string>();
            if (save.customMap != null) return result;
            int count = save.encounterIndex + (save.screen == "victory" ? 1 : 0);
            if (save.journey != null)
            {
                for (int i = 0; i < Math.Min(count, data.journey.floors.Length); i++)
                    if (data.journey.floors[i].encounter != null) result.Add("journey." + data.journey.floors[i].id);
            }
            else for (int i = 0; i < Math.Min(count, data.encounters.Length); i++) result.Add("legacy." + data.encounters[i].id);
            return result;
        }
        private long HomeEarnedGold(GameSave save)
        {
            long result = data.home.startingGold;
            int count = save.encounterIndex + (save.screen == "victory" ? 1 : 0);
            if (save.customMap != null) return result;
            for (int i = 0; i < Math.Min(count, save.journey == null ? data.encounters.Length : data.journey.floors.Length); i++)
                if (save.journey == null || data.journey.floors[i].encounter != null) result += HomeVictoryGold(i + 1);
            return result;
        }
        private static HomeSave CloneHome(HomeSave source)
        {
            return source == null ? null : new HomeSave { version = source.version, gold = source.gold, purchasedIds = (string[])source.purchasedIds.Clone(), victoryReceiptIds = (string[])source.victoryReceiptIds.Clone(), training = Array.ConvertAll(source.training, t => new HomeTrainingSave { unitId = t.unitId, abilityId = t.abilityId, floorIndex = t.floorIndex, story = t.story }), memberships = Array.ConvertAll(source.memberships, m => new HomeMembershipSave { clubId = m.clubId, unitId = m.unitId, earnedClassId = m.earnedClassId, earnedFloor = m.earnedFloor, story = m.story }) };
        }
        private HomeSave CaptureHome() { return CloneHome(homeState); }
        private HomeSave ValidateHome(GameSave save)
        {
            if (data.home == null) { Require(save.home == null, "This content pack has no home economy."); return null; }
            GameSave baseline = save.expedition != null ? save.expedition.campaign : save.scenario != null ? save.scenario.campaign : null;
            if (baseline != null)
            {
                Require(baseline.expedition == null && baseline.scenario == null, "Nested home backups are invalid.");
                HomeSave expected = ValidateHome(baseline);
                if (save.home == null) return expected; // Migrate the whole isolated mission together.
                Require(HomeSavesEqual(save.home, expected), "Standalone missions cannot change campaign gold or home upgrades.");
                return CloneHome(expected);
            }
            List<string> receipts = ExpectedHomeReceipts(save); long earned = HomeEarnedGold(save);
            Require(earned <= MaximumGold, "Campaign gold exceeds capacity.");
            HomeSave source = save.home ?? new HomeSave { gold = (int)earned, victoryReceiptIds = receipts.ToArray() };
            Require(source.version == 1 && source.gold >= 0 && source.gold <= MaximumGold && source.purchasedIds != null && source.victoryReceiptIds != null && source.training != null && source.memberships != null, "Invalid home save.");
            Require(source.purchasedIds.Length <= data.home.upgrades.Length && source.victoryReceiptIds.Length == receipts.Count, "Invalid home collections.");
            HashSet<string> seen = new HashSet<string>();
            foreach (string receipt in source.victoryReceiptIds) Require(receipt != null && receipts.Contains(receipt) && seen.Add(receipt), "Unmatched or duplicate gold victory receipt.");
            seen.Clear(); long spent = 0;
            foreach (string id in source.purchasedIds)
            {
                HomeUpgradeDef upgrade = HomeUpgrade(id);
                Require(upgrade != null && upgrade.purchasable && seen.Add(id), "Unknown, ineligible or duplicate home purchase.");
                Require(string.IsNullOrEmpty(upgrade.prerequisiteId) || Array.IndexOf(source.purchasedIds, upgrade.prerequisiteId) >= 0, "Home upgrade is missing its prerequisite.");
                spent += upgrade.cost;
            }
            Require(source.purchasedIds.Length == 0 || save.journey == null || save.encounterIndex + 1 >= data.home.availableFromFloor, "Home was purchased before the shared space opened.");
            Require(source.training.Length <= data.roster.Length * 8, "Too many home training records.");
            seen.Clear(); var trainedUses = new Dictionary<string, int>();
            foreach (HomeTrainingSave training in source.training)
            {
                Require(training != null && Definition(training.unitId) != null && Definition(training.unitId).deployable && Array.IndexOf(data.home.trainingAbilityIds, training.abilityId) >= 0 && training.story == (save.journey != null) && training.floorIndex >= (training.story ? data.home.availableFromFloor - 1 : 0) && training.floorIndex <= save.encounterIndex && training.floorIndex < (training.story ? 8 : data.encounters.Length) && seen.Add(training.unitId + ":" + training.floorIndex), "Invalid or repeated home training receipt.");
                Require(Array.Exists(data.home.upgrades, u => u.kind == "training" && Array.IndexOf(source.purchasedIds, u.id) >= 0), "Home practice requires an installed Training Room.");
                string key = training.unitId + ":" + training.abilityId;
                trainedUses[key] = trainedUses.ContainsKey(key) ? trainedUses[key] + 1 : 1;
                SkillPracticeSave practice = save.development == null || save.development.practice == null ? null : Array.Find(save.development.practice, p => p != null && p.unitId == training.unitId && p.abilityId == training.abilityId);
                Require(practice != null && practice.uses >= trainedUses[key], "Home practice receipt is missing its saved skill progress.");
                spent += data.home.trainingGoldCost;
            }
            Require(source.memberships.Length <= data.roster.Length * data.home.clubs.Length, "Too many personal club memberships.");
            seen.Clear();
            foreach (HomeMembershipSave membership in source.memberships)
            {
                HomeClubDef club = membership == null ? null : HomeClub(membership.clubId);
                RosterDef member = membership == null ? null : Definition(membership.unitId);
                Require(club != null && member != null && member.deployable && Array.IndexOf(club.excludedRosterIds, member.id) < 0 && Array.IndexOf(club.eligibleClassIds, membership.earnedClassId) >= 0 && seen.Add(membership.clubId + ":" + membership.unitId), "Invalid, ineligible or repeated personal club membership.");
                Require(membership.story == (save.journey != null) && (membership.story ? membership.earnedFloor >= club.minimumFloor && membership.earnedFloor <= Math.Min(8, save.encounterIndex + 1) : membership.earnedFloor == 0), "Club membership predates its class-granted admission floor.");
            }
            Require(earned - spent == source.gold, "Gold does not match earned deposits and installed upgrades.");
            return CloneHome(source);
        }
        private static bool HomeSavesEqual(HomeSave a, HomeSave b)
        {
            if (a == null || b == null) return a == b;
            if (a.version != b.version || a.gold != b.gold || a.purchasedIds == null || a.victoryReceiptIds == null || a.training == null || a.memberships == null || a.purchasedIds.Length != b.purchasedIds.Length || a.victoryReceiptIds.Length != b.victoryReceiptIds.Length || a.training.Length != b.training.Length || a.memberships.Length != b.memberships.Length) return false;
            // Order is part of the saved receipt and installation history.
            for (int i = 0; i < a.purchasedIds.Length; i++) if (a.purchasedIds[i] != b.purchasedIds[i]) return false;
            for (int i = 0; i < a.victoryReceiptIds.Length; i++) if (a.victoryReceiptIds[i] != b.victoryReceiptIds[i]) return false;
            for (int i = 0; i < a.training.Length; i++) if (a.training[i] == null || a.training[i].unitId != b.training[i].unitId || a.training[i].abilityId != b.training[i].abilityId || a.training[i].floorIndex != b.training[i].floorIndex || a.training[i].story != b.training[i].story) return false;
            for (int i = 0; i < a.memberships.Length; i++) if (a.memberships[i] == null || a.memberships[i].clubId != b.memberships[i].clubId || a.memberships[i].unitId != b.memberships[i].unitId || a.memberships[i].earnedClassId != b.memberships[i].earnedClassId || a.memberships[i].earnedFloor != b.memberships[i].earnedFloor || a.memberships[i].story != b.memberships[i].story) return false;
            return true;
        }
        private void CommitHome(HomeSave next) { homeState = CloneHome(next); pendingHomeUpgrade = null; pendingHomeTraining = null; pendingHomeMembership = null; }
        private HomeView HomeView()
        {
            if (data.home == null) return null;
            bool owned = HomeOwnsKind("space");
            List<HomeRoomView> rooms = new List<HomeRoomView>();
            foreach (RosterDef member in data.roster) if (member.deployable) rooms.Add(new HomeRoomView { id = "bedroom." + member.id, label = member.label + "'s bedroom", kind = "bedroom", ownerId = member.id, unlocked = owned, description = "A private bedroom in the party's shared personal space. Bedroom assignment is a game adaptation." });
            rooms.Add(new HomeRoomView { id = "room.training", label = "Training Room", kind = "training", unlocked = HomeOwnsKind("training"), description = "Paid practice sessions for authored nonmagical skills. Once per crawler per floor is an accelerated game adaptation; combat practice also comes from committed ability use." });
            rooms.Add(new HomeRoomView { id = "room.crafting", label = "Crafting room", kind = "crafting", unlocked = HomeOwnsKind("crafting"), description = "The Engineer's Table enables the authored supply recipes. Installed tools increase each output by the listed amount." });
            List<HomeUpgradeView> upgrades = new List<HomeUpgradeView>();
            foreach (HomeUpgradeDef row in data.home.upgrades)
            {
                string reason = HomePurchaseReason(row);
                upgrades.Add(new HomeUpgradeView { id = row.id, label = row.label, kind = row.kind, description = row.description, cost = row.cost, costNote = row.costNote, priceBasis = row.priceBasis, craftOutputBonus = row.craftOutputBonus, purchased = Array.IndexOf(homeState.purchasedIds, row.id) >= 0, purchasable = row.purchasable, enabled = reason == "", disabledReason = reason, sourceIds = (string[])row.sourceIds.Clone() });
            }
            HomeUpgradeDef pendingUpgrade = HomeUpgrade(pendingHomeUpgrade);
            List<HomeTrainingView> training = new List<HomeTrainingView>();
            foreach (RosterDef member in data.roster) if (member.deployable)
                foreach (string ability in data.home.trainingAbilityIds)
                    if (Array.IndexOf(Grants(member.id, xp, equipped), ability) >= 0 || Array.IndexOf(catalog.Classes[roster[member.id].classId].abilityIds, ability) >= 0) training.Add(HomeTrainingOption(member.id, ability));
            List<HomeMembershipView> memberships = new List<HomeMembershipView>();
            foreach (HomeClubDef club in data.home.clubs)
                foreach (RosterDef member in data.roster) if (member.deployable) memberships.Add(HomeMembershipOption(club, member.id));
            return new HomeView {
                label = data.home.label, description = data.home.description, economyNote = data.home.economyNote,
                gold = homeState.gold, availableFromFloor = data.home.availableFromFloor, available = HomeAvailabilityReason() == "", disabledReason = HomeAvailabilityReason(),
                owned = owned, trainingUnlocked = HomeOwnsKind("training"), craftingUnlocked = HomeCraftingReason() == "", trainingDisabledReason = HomeTrainingReason(), craftingDisabledReason = HomeCraftingReason(), craftOutputBonus = HomeCraftOutputBonus(),
                rooms = rooms.ToArray(), upgrades = upgrades.ToArray(), training = training.ToArray(), memberships = memberships.ToArray(), canConfirm = pendingUpgrade != null || pendingHomeTraining != null || pendingHomeMembership != null,
                forecast = pendingUpgrade == null ? (HomeTrainingForecast() ?? HomeMembershipForecast()) : new HomePurchaseForecast { type = "upgrade", upgradeId = pendingUpgrade.id, label = pendingUpgrade.label, benefit = pendingUpgrade.description, cost = pendingUpgrade.cost, beforeGold = homeState.gold, afterGold = homeState.gold - pendingUpgrade.cost },
                social = new HomeSocialView { unlocked = HomeOwnsKind("social"), description = "Local dungeon achievement history and campaign totals. This screen has no live network, viewer counts, or external posting.", achievementIds = HomeOwnsKind("social") ? achievementIds.ToArray() : new string[0], victories = homeState.victoryReceiptIds.Length, floorsComplete = journey == null ? encounterIndex : journey.floorIndex, cardsCaptured = journey == null ? 0 : journey.capturedIds.Length }
            };
        }
    }
}
