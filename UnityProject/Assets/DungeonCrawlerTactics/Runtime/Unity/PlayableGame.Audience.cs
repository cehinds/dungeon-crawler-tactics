using System;
using UnityEngine;
namespace DungeonCrawlerTactics.Unity
{
    public sealed partial class PlayableGame
    {
        private Vector2 audienceScroll;
        private string AudienceItemName(string id)
        {
            foreach (ItemView item in view.items) if (item.id == id) return item.label;
            return id;
        }
        private string AudienceNotice(string current)
        {
            foreach (PresentationEvent ev in view.events)
            {
                if (ev.preview) continue;
                if (ev.type == "achievement") current += " NEW ACHIEVEMENT: " + (ev.tag ?? "").Replace("achievement.", "").Replace('_', ' ') + ".";
                if (ev.type == "favor") current += " +" + ev.amount + " AI Favor.";
                if (ev.type == "sponsor_challenge" && view.audience != null) foreach (SponsorChallengeView offer in view.audience.challenges) if (offer.id == ev.tag) current += " Sponsor offer completed: " + offer.label + ".";
            }
            return current;
        }
        private void DrawAudienceModal()
        {
            AudienceView audience = view.audience;
            if (audience == null) return;
            int targetRows = 0; foreach (ItemView item in view.items) if (item.favorTargetIds.Length > 0) targetRows += 3 + (item.favorTargetIds.Length + 5) / 6;
            int recipeCount = view.development == null || view.development.recipes == null ? 0 : view.development.recipes.Length;
            float contentHeight = 510 + audience.challenges.Length * 100 + view.achievementIds.Length * 28 + targetRows * 42 + recipeCount * 170;
            audienceScroll = GUI.BeginScrollView(new Rect(298, 181, 842, 594), audienceScroll, new Rect(0, 0, 815, contentHeight));
            float y = 0;
            GUI.Label(new Rect(0, y, 795, 32), "AI Favor " + audience.favor + " / " + audience.favorCap + "  ·  grants this encounter " + audience.favorEarned, sectionStyle); y += 38;
            GUI.Label(new Rect(0, y, 795, 70), "First committed player reaction earns one Favor per encounter. Spend one Favor plus a listed supply for an extra environmental utility. Movement, normal action and turn order remain intact. Adapted game rules.", smallStyle); y += 76;
            foreach (SponsorChallengeView challenge in audience.challenges)
            {
                GUI.Label(new Rect(0, y, 795, 30), (challenge.earned ? "EARNED — " : "OFFER — ") + challenge.label, sectionStyle); y += 32;
                GUI.Label(new Rect(0, y, 795, 60), challenge.description + " Reward: " + challenge.rewardCount + " × " + AudienceItemName(challenge.rewardItemId) + ". Saved once per run.", smallStyle); y += 66;
            }
            GUI.Label(new Rect(0, y, 795, 30), "FAVOR: CHOOSE A CRAWLER, SUPPLY AND LEGAL TILE", sectionStyle); y += 36;
            if (view.screen == "battle")
            {
                int slot = 0;
                foreach (UnitView unit in view.units) if (unit.team == "player" && unit.hp > 0 && !unit.finished)
                {
                    if (ModalButton(new Rect((slot % 4) * 200, y + (slot / 4) * 42, 194, 36), (unit.id == view.selectedUnitId ? "✓ " : "") + unit.label)) Submit(new GameCommand { type = "select", unitId = unit.id });
                    slot++;
                }
                y += ((slot + 3) / 4) * 42;
                bool available = false;
                foreach (ItemView item in view.items) if (item.favorTargetIds.Length > 0)
                {
                    available = true;
                    GUI.Label(new Rect(0, y, 795, 32), item.label + " ×" + item.count + " — cost: 1 Favor + 1 supply", bodyStyle); y += 36;
                    GUI.Label(new Rect(0, y, 795, 64), item.description, smallStyle); y += 68;
                    for (int i = 0; i < item.favorTargetIds.Length; i++)
                    {
                        string target = item.favorTargetIds[i]; TileView tile = Array.Find(view.tiles, t => t.id == target);
                        string label = tile == null ? target : "Tile " + tile.x + "," + tile.y;
                        if (ModalButton(new Rect((i % 6) * 132, y + (i / 6) * 42, 126, 36), label))
                        { modal = ""; Submit(new GameCommand { type = "preview_favor", unitId = view.selectedUnitId, itemId = item.id, targetId = target }); }
                    }
                    y += ((item.favorTargetIds.Length + 5) / 6) * 42 + 12;
                }
                if (!available) { GUI.Label(new Rect(0, y, 795, 64), "No legal Favor utility available. Earn Favor, keep a crawler's turn unfinished and carry an eligible environmental supply. Legal targets come from the shared rules resolver.", smallStyle); y += 70; }
            }
            else { GUI.Label(new Rect(0, y, 795, 40), "Favor utilities become available during battle.", smallStyle); y += 46; }
            GUI.Label(new Rect(0, y, 795, 32), "SAFE-ROOM RECIPES", sectionStyle); y += 38;
            if (view.development != null && view.development.recipes != null) foreach (RecipeView recipe in view.development.recipes)
            {
                GUI.Label(new Rect(0, y, 795, 60), recipe.label + ": " + recipe.description, smallStyle); y += 64;
                string materials = "Use: "; foreach (ItemQuantity ingredient in recipe.ingredients) materials += ingredient.count + " × " + AudienceItemName(ingredient.itemId) + "; ";
                materials += " Output: "; foreach (ItemQuantity output in recipe.outputs) materials += output.count + " × " + AudienceItemName(output.itemId) + "; ";
                GUI.Label(new Rect(0, y, 795, 44), materials, smallStyle); y += 48;
                if (ModalButton(new Rect(0, y, 790, 38), recipe.enabled ? "Craft " + recipe.label : recipe.disabledReason, recipe.enabled)) Submit(new GameCommand { type = "craft", recipeId = recipe.id }); y += 46;
            }
            GUI.Label(new Rect(0, y, 795, 32), "ACHIEVEMENT HISTORY", sectionStyle); y += 38;
            foreach (string id in view.achievementIds) { GUI.Label(new Rect(0, y, 795, 26), "Earned: " + id.Replace("achievement.", "").Replace('_', ' '), smallStyle); y += 28; }
            GUI.EndScrollView();
        }
        private void DrawAudienceForecast(ref float y)
        {
            if (view.audience == null) return;
            if (view.audience.forecastFavor > 0) { GUI.Label(new Rect(2, y, 389, 30), "+" + view.audience.forecastFavor + " AI Favor on confirmation", smallStyle); y += 34; }
            foreach (InventoryEntry reward in view.audience.forecastRewards)
            { GUI.Label(new Rect(2, y, 389, 48), "Sponsor delivery: +" + reward.count + " " + AudienceItemName(reward.itemId), smallStyle); y += 52; }
        }
    }
}
