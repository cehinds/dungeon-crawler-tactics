using System;
using System.Collections.Generic;
namespace DungeonCrawlerTactics
{
    [Serializable] public sealed class SponsorChallengeDef { public string id, label, description, eventType, rewardItemId; public int rewardCount; }
    [Serializable] public sealed class SponsorChallengeView { public string id, label, description, rewardItemId; public int rewardCount; public bool earned; }
    [Serializable] public sealed class AudienceSave { public int version = 1, favor, favorEarned; public string[] receipts = new string[0]; }
    [Serializable] public sealed class AudienceView { public InventoryEntry[] forecastRewards = new InventoryEntry[0]; public int forecastFavor; public int favor, favorEarned, favorCap = 1; public string[] favorItemIds = new string[0]; public SponsorChallengeView[] challenges = new SponsorChallengeView[0]; }
    public sealed partial class GameSession
    {
        private AudienceSave audienceState = new AudienceSave();
        private AudienceSave CaptureAudience() { return new AudienceSave { favor = audienceState.favor, favorEarned = audienceState.favorEarned, receipts = (string[])audienceState.receipts.Clone() }; }
        private AudienceSave ValidateAudience(AudienceSave source)
        {
            if (source == null) return new AudienceSave();
            Require(source.version == 1 && source.favorEarned >= 0 && source.favorEarned <= 1 && source.favor >= 0 && source.favor <= source.favorEarned && source.receipts != null && source.receipts.Length <= data.sponsorChallenges.Length, "Invalid audience save.");
            var unique = new HashSet<string>(); foreach (string id in source.receipts) Require(Array.Exists(data.sponsorChallenges, c => c.id == id) && unique.Add(id), "Unknown or repeated sponsor receipt.");
            return new AudienceSave { favor = source.favor, favorEarned = source.favorEarned, receipts = (string[])source.receipts.Clone() };
        }
        private AudienceView BuildAudienceView()
        {
            var offers = new List<SponsorChallengeView>(); var eligible = new List<string>();
            foreach (ItemDef item in catalog.Items.Values) if (item.favorEligible) eligible.Add(item.id); eligible.Sort(StringComparer.Ordinal);
            foreach (SponsorChallengeDef c in data.sponsorChallenges) offers.Add(new SponsorChallengeView { id = c.id, label = c.label, description = c.description, rewardItemId = c.rewardItemId, rewardCount = c.rewardCount, earned = Array.IndexOf(audienceState.receipts, c.id) >= 0 });
            bool reaction = forecast != null && Array.Exists(forecast.Events, e => e.type == "reaction");
            bool victory = forecast != null, survivor = false;
            if (forecast != null) foreach (EntityState e in forecast.State.Entities.Values)
            { if (!e.IsTile && e.Team != "player" && e.Hp > 0) victory = false; if (!e.IsTile && e.Team == "player" && e.Hp > 0) survivor = true; }
            victory = victory && survivor;
            // Resolve deliveries against the post-consumption inventory, then accumulate
            // shared reward IDs so several offers cannot each promise the same free capacity.
            var projected = new Dictionary<string, int>(inventory, StringComparer.Ordinal);
            if (pending != null && !string.IsNullOrEmpty(pending.itemId)) projected[pending.itemId]--;
            var totals = new Dictionary<string, int>(StringComparer.Ordinal); var rewardOrder = new List<string>();
            foreach (SponsorChallengeDef c in data.sponsorChallenges)
                if (Array.IndexOf(audienceState.receipts, c.id) < 0 && (c.eventType == "reaction" && reaction || c.eventType == "victory" && victory))
                {
                    int delivered = Math.Min(c.rewardCount, 10000 - projected[c.rewardItemId]);
                    projected[c.rewardItemId] += delivered;
                    if (!totals.ContainsKey(c.rewardItemId)) { totals.Add(c.rewardItemId, 0); rewardOrder.Add(c.rewardItemId); }
                    totals[c.rewardItemId] += delivered;
                }
            var rewards = new List<InventoryEntry>(); foreach (string id in rewardOrder) rewards.Add(new InventoryEntry { itemId = id, count = totals[id] });
            return new AudienceView { forecastRewards = rewards.ToArray(), forecastFavor = reaction && audienceState.favorEarned == 0 && !victory ? 1 : 0, favor = audienceState.favor, favorEarned = audienceState.favorEarned, challenges = offers.ToArray(), favorItemIds = eligible.ToArray() };
        }
        private string[] LegalFavorTargets(EntityState actor, ItemDef item)
        {
            var targets = new List<string>();
            if (actor == null || actor.Team != "player" || screen != "battle" || phase != "player" || audienceState.favor <= 0 || !item.favorEligible || inventory[item.id] <= 0) return targets.ToArray();
            foreach (EntityState target in battle.Entities.Values) if (target.IsTile)
                try { ResolveAction(new GameCommand { type = "preview_favor", unitId = actor.Id, itemId = item.id, targetId = target.Id }); targets.Add(target.Id); } catch (ArgumentException) { } catch (InvalidOperationException) { }
            targets.Sort(StringComparer.Ordinal); return targets.ToArray();
        }
        private bool IsTrapItem(string id) { foreach (EffectDef effect in catalog.Abilities[catalog.Items[id].abilityId].effects) if (effect.op == "AddTag" && TagRule(effect.tag) != null && TagRule(effect.tag).consumeOnEntry) return true; return false; }
        private void ValidateFavor(GameCommand command, EntityState actor)
        {
            Require(string.IsNullOrEmpty(command.stanceId) && string.IsNullOrEmpty(command.formId) && string.IsNullOrEmpty(command.abilityId), "Favor commands may only select an environmental supply, never a stance, form or ability.");
            Require(actor.Team == "player" && audienceState.favor > 0, "Earn AI Favor from a committed reaction first (one grant per encounter).");
            Require(command.itemId != null && catalog.Items.ContainsKey(command.itemId) && catalog.Items[command.itemId].favorEligible, "AI Favor only permits the listed environmental supplies.");
        }
        private void AudienceCommitted(string eventType, bool rewardApplied = false)
        {
            if (eventType == "reaction" && screen == "battle" && phase == "player" && audienceState.favorEarned == 0)
            { audienceState.favorEarned = 1; audienceState.favor = 1; presentationEvents.Add(new PresentationEvent { type = "favor", amount = 1 }); }
            foreach (SponsorChallengeDef c in data.sponsorChallenges)
            {
                if (c.eventType != eventType || Array.IndexOf(audienceState.receipts, c.id) >= 0) continue;
                // The receipt is permanent even at capacity; a full inventory cannot farm an offer.
                if (!rewardApplied) inventory[c.rewardItemId] = Math.Min(10000, inventory[c.rewardItemId] + c.rewardCount);
                var receipts = new List<string>(audienceState.receipts); receipts.Add(c.id); audienceState.receipts = receipts.ToArray();
                presentationEvents.Add(new PresentationEvent { type = "sponsor_challenge", tag = c.id, amount = c.rewardCount });
            }
        }
    }
}
