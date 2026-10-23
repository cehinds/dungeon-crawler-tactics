using System.Collections.Generic;
using UnityEngine;

namespace DungeonCrawlerTactics.Unity
{
    public sealed partial class PlayableGame
    {
        private readonly Dictionary<string, Texture2D> unitArt = new Dictionary<string, Texture2D>();
        private readonly Dictionary<string, Texture2D> tileArt = new Dictionary<string, Texture2D>();
        private readonly List<Texture2D> generatedArt = new List<Texture2D>();

        private Texture2D UnitArt(string classId, string team, string unitId = null)
        {
            string key = (classId ?? "") + "/" + team + "/" + unitId;
            Texture2D texture;
            if (unitArt.TryGetValue(key, out texture)) return texture;
            string artId = team == "enemy" ? (classId != null && classId.Contains("boss") ? "boss" : "enemy") : (classId ?? "brawler").Replace("class.", "");
            if (unitId == "crawler.donut") artId = "donut";
            if (unitId == "enemy.retention_engine") artId = "boss";
            texture = Resources.Load<Texture2D>("Art/" + artId);
            if (texture == null) texture = CreateUnitPixels(classId, team);
            texture.filterMode = FilterMode.Point;
            unitArt.Add(key, texture);
            return texture;
        }

        private Texture2D CreateUnitPixels(string classId, string team)
        {
            Color clear = Color.clear;
            Color outline = new Color32(13, 20, 24, 255);
            Color suit = team == "enemy" ? (Color)new Color32(168, 76, 75, 255) : ClassTint(classId);
            Color light = Color.Lerp(suit, Color.white, .38f);
            Color skin = team == "enemy" ? new Color32(164, 185, 130, 255) : new Color32(226, 181, 143, 255);
            Texture2D texture = new Texture2D(24, 28, TextureFormat.RGBA32, false) { filterMode = FilterMode.Point, name = "Crawler pixel silhouette" };
            Color[] pixels = new Color[24 * 28];
            for (int i = 0; i < pixels.Length; i++) pixels[i] = clear;
            Paint(pixels, 24, 5, 2, 6, 5, outline); Paint(pixels, 24, 13, 2, 6, 5, outline);
            Paint(pixels, 24, 6, 7, 12, 11, outline); Paint(pixels, 24, 7, 8, 10, 10, suit);
            Paint(pixels, 24, 3, 10, 4, 8, outline); Paint(pixels, 24, 17, 10, 4, 8, outline);
            Paint(pixels, 24, 4, 11, 3, 6, light); Paint(pixels, 24, 17, 11, 3, 6, light);
            Paint(pixels, 24, 7, 18, 10, 8, outline); Paint(pixels, 24, 8, 19, 8, 6, skin);
            Paint(pixels, 24, 8, 24, 8, 2, suit); Paint(pixels, 24, 10, 21, 1, 1, outline); Paint(pixels, 24, 14, 21, 1, 1, outline);
            Paint(pixels, 24, 7, 9, 10, 2, light); Paint(pixels, 24, 7, 7, 10, 2, new Color32(76, 57, 45, 255));
            texture.SetPixels(pixels); texture.Apply(false, true); generatedArt.Add(texture); return texture;
        }

        private Texture2D TileArt(TileView tile)
        {
            string key = tile.blocked ? "wall" : "floor";
            if (!tile.blocked)
            {
                if (HasTag(tile.tags, "surface.burning")) key = "fire";
                else if (HasTag(tile.tags, "surface.oil")) key = "oil";
                else if ((HasTag(tile.tags, "surface.water") || HasTag(tile.tags, "surface.wet") || HasTag(tile.tags, "status.wet"))) key = "wet";
                else if ((HasTag(tile.tags, "surface.frozen") || HasTag(tile.tags, "status.frozen"))) key = "ice";
            }
            Texture2D texture;
            if (tileArt.TryGetValue(key, out texture)) return texture;
            Color baseColor = key == "wall" ? new Color32(70, 79, 84, 255) : key == "oil" ? new Color32(77, 66, 85, 255) : key == "wet" ? new Color32(39, 85, 106, 255) : key == "fire" ? new Color32(153, 71, 38, 255) : key == "ice" ? new Color32(91, 149, 165, 255) : new Color32(53, 63, 65, 255);
            texture = new Texture2D(32, 32, TextureFormat.RGBA32, false) { filterMode = FilterMode.Point, name = "Dungeon " + key };
            Color[] pixels = new Color[1024];
            for (int y = 0; y < 32; y++) for (int x = 0; x < 32; x++)
            {
                bool edge = x < 2 || y < 2 || x > 29 || y > 29;
                float grain = ((x * 7 + y * 13) % 17 == 0) ? .07f : 0;
                pixels[y * 32 + x] = Color.Lerp(baseColor, edge ? Color.black : Color.white, edge ? .28f : grain);
            }
            if (key == "wall") { Paint(pixels, 32, 2, 16, 28, 2, new Color32(32, 43, 48, 255)); Paint(pixels, 32, 15, 2, 2, 14, new Color32(32, 43, 48, 255)); Paint(pixels, 32, 7, 18, 2, 12, new Color32(32, 43, 48, 255)); }
            if (key == "wet" || key == "ice") { Paint(pixels, 32, 5, 9, 12, 1, new Color32(107, 175, 190, 255)); Paint(pixels, 32, 15, 21, 10, 1, new Color32(107, 175, 190, 255)); }
            if (key == "oil") { Paint(pixels, 32, 5, 8, 18, 10, new Color32(40, 34, 51, 255)); Paint(pixels, 32, 11, 6, 14, 15, new Color32(40, 34, 51, 255)); }
            if (key == "fire") { Paint(pixels, 32, 7, 8, 5, 12, Gold); Paint(pixels, 32, 17, 5, 5, 17, new Color32(251, 132, 46, 255)); }
            texture.SetPixels(pixels); texture.Apply(false, true); generatedArt.Add(texture); tileArt.Add(key, texture); return texture;
        }

        private static Color ClassTint(string id)
        {
            int hash = 0;
            if (id != null) foreach (char ch in id) hash = (hash * 31 + ch) & 0x7fffffff;
            return Color.HSVToRGB((hash % 360) / 360f, .42f, .83f);
        }

        private static void Paint(Color[] pixels, int width, int x, int y, int w, int h, Color color)
        {
            for (int row = y; row < y + h; row++) for (int col = x; col < x + w; col++) pixels[row * width + col] = color;
        }

        private static bool HasTag(string[] tags, string id)
        {
            if (tags != null) foreach (string tag in tags) if (tag == id) return true;
            return false;
        }

        private static string SurfaceSymbol(string[] tags)
        {
            if (HasTag(tags, "surface.trap_shock")) return "SHOCK TRAP";
            if (HasTag(tags, "surface.trap_coolant")) return "WET TRAP";
            if (HasTag(tags, "surface.burning")) return "FIRE";
            if (HasTag(tags, "surface.oil")) return "OIL";
            if (HasTag(tags, "surface.water")) return "WATER";
            if ((HasTag(tags, "surface.wet") || HasTag(tags, "status.wet"))) return "WET";
            if ((HasTag(tags, "surface.frozen") || HasTag(tags, "status.frozen"))) return "ICE";
            return "";
        }

        private void ReleaseArt()
        {
            foreach (Texture2D texture in generatedArt) if (texture != null) Destroy(texture);
            generatedArt.Clear(); unitArt.Clear(); tileArt.Clear();
        }
    }
}
