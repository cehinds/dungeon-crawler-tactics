using UnityEngine;

namespace DungeonCrawlerTactics.Unity
{
    public sealed partial class PlayableGame
    {
        private static readonly Color Background = new Color32(14, 19, 24, 255);
        private static readonly Color Panel = new Color32(25, 34, 40, 255);
        private static readonly Color PanelLight = new Color32(36, 47, 53, 255);
        private static readonly Color Gold = new Color32(244, 186, 94, 255);
        private static readonly Color Teal = new Color32(110, 223, 208, 255);
        private static readonly Color Muted = new Color32(164, 184, 187, 255);
        private GUIStyle titleStyle;
        private GUIStyle sectionStyle;
        private GUIStyle bodyStyle;
        private GUIStyle smallStyle;
        private GUIStyle buttonStyle;
        private GUIStyle selectedStyle;
        private GUIStyle unitLabelStyle;
        private GUIStyle textAreaStyle;

        private void EnsureStyles()
        {
            if (titleStyle != null) return;
            titleStyle = new GUIStyle(GUI.skin.label) { fontSize = 30, fontStyle = FontStyle.Bold, wordWrap = true };
            titleStyle.normal.textColor = Color.white;
            sectionStyle = new GUIStyle(GUI.skin.label) { fontSize = 18, fontStyle = FontStyle.Bold, wordWrap = true };
            sectionStyle.normal.textColor = Gold;
            bodyStyle = new GUIStyle(GUI.skin.label) { fontSize = 16, wordWrap = true, richText = false };
            bodyStyle.normal.textColor = new Color32(234, 240, 234, 255);
            smallStyle = new GUIStyle(bodyStyle) { fontSize = 13 };
            smallStyle.normal.textColor = Muted;
            buttonStyle = new GUIStyle(GUI.skin.button) { fontSize = 15, wordWrap = true, alignment = TextAnchor.MiddleCenter, padding = new RectOffset(10, 10, 6, 6) };
            selectedStyle = new GUIStyle(buttonStyle) { fontStyle = FontStyle.Bold };
            selectedStyle.normal.textColor = Gold;
            unitLabelStyle = new GUIStyle(smallStyle) { alignment = TextAnchor.MiddleCenter, fontSize = 11, fontStyle = FontStyle.Bold };
            unitLabelStyle.normal.textColor = Color.white;
            textAreaStyle = new GUIStyle(GUI.skin.textArea) { fontSize = 14, wordWrap = true, padding = new RectOffset(10, 10, 10, 10) };
        }

        private static void Fill(Rect rect, Color color)
        {
            Color old = GUI.color; GUI.color = color;
            GUI.DrawTexture(rect, Texture2D.whiteTexture);
            GUI.color = old;
        }

        private static void Border(Rect rect, Color color, float thickness = 2)
        {
            Fill(new Rect(rect.x, rect.y, rect.width, thickness), color);
            Fill(new Rect(rect.x, rect.yMax - thickness, rect.width, thickness), color);
            Fill(new Rect(rect.x, rect.y, thickness, rect.height), color);
            Fill(new Rect(rect.xMax - thickness, rect.y, thickness, rect.height), color);
        }

        private void Card(Rect rect, string heading)
        {
            Fill(rect, Panel);
            Fill(new Rect(rect.x, rect.y, 3, rect.height), PanelLight);
            if (!string.IsNullOrEmpty(heading)) GUI.Label(new Rect(rect.x + 16, rect.y + 12, rect.width - 32, 30), heading, sectionStyle);
        }

        private bool Button(Rect rect, string text, bool enabled = true, bool selected = false)
        {
            bool old = GUI.enabled;
            GUI.enabled = old && enabled && string.IsNullOrEmpty(modal);
            bool pressed = GUI.Button(rect, text, selected ? selectedStyle : buttonStyle);
            GUI.enabled = old;
            return pressed;
        }

        private bool ModalButton(Rect rect, string text, bool enabled = true)
        {
            bool old = GUI.enabled; GUI.enabled = old && enabled;
            bool pressed = GUI.Button(rect, text, buttonStyle);
            GUI.enabled = old; return pressed;
        }

        private void DrawHeader()
        {
            GUI.Label(new Rect(26, 16, 700, 38), "DUNGEON CRAWLER CARL", titleStyle);
            GUI.Label(new Rect(28, 58, 680, 28), "TACTICS  /  THE FIRST FLOOR", smallStyle);
            if (Button(new Rect(1000, 26, 126, 44), "How to play")) modal = "help";
            if (Button(new Rect(1136, 26, 126, 44), "Settings")) modal = "settings";
            if (Button(new Rect(1272, 26, 140, 44), "Save / Load")) { modal = "save"; saveText = JsonUtility.ToJson(session.ExportSave(), true); }
            Fill(new Rect(28, 88, 1384, 1), PanelLight);
        }

        private void DrawFooter()
        {
            Fill(new Rect(0, 850, 1440, 50), Panel);
            GUI.Label(new Rect(28, 859, 1160, 34), string.IsNullOrEmpty(notice) ? view.message : notice, bodyStyle);
            GUI.Label(new Rect(1210, 864, 200, 24), "FLOOR 01  /  " + view.xp + " XP", smallStyle);
        }

        private void DrawBootError()
        {
            Card(new Rect(260, 210, 920, 400), "CONTENT COULD NOT BE LOADED");
            GUI.Label(new Rect(290, 280, 860, 190), bootError, bodyStyle);
            if (GUI.Button(new Rect(290, 520, 220, 48), "Try loading again", buttonStyle)) Boot();
        }

        private static string Humanize(string id)
        {
            if (string.IsNullOrEmpty(id)) return "—";
            int dot = id.LastIndexOf('.');
            string value = dot >= 0 ? id.Substring(dot + 1) : id;
            value = value.Replace('_', ' ');
            return value.Length == 0 ? value : char.ToUpperInvariant(value[0]) + value.Substring(1);
        }

        private static string Tags(string[] values)
        {
            if (values == null || values.Length == 0) return "No conditions";
            string[] labels = new string[values.Length];
            for (int i = 0; i < values.Length; i++) labels[i] = Humanize(values[i]);
            return string.Join(" · ", labels);
        }

        private string ClassName(string id)
        {
            foreach (ClassView c in view.classes) if (c.id == id) return c.label;
            return Humanize(id);
        }
    }
}
