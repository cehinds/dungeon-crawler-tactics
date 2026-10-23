using System;
using UnityEngine;

namespace DungeonCrawlerTactics.Unity
{
    public sealed partial class PlayableGame
    {
        private void DrawModal()
        {
            Fill(new Rect(0, 0, 1440, 900), new Color(0, 0, 0, .84f));
            Rect panel = new Rect(270, 108, 900, 696);
            Card(panel, modal == "audience" ? "AUDIENCE, FAVOR & CRAFTING" : modal == "help" ? "HOW TO SURVIVE THE SHOW" : modal == "save" ? "SAVE / LOAD" : modal == "reset" ? "START A NEW RUN?" : "SETTINGS");
            if (ModalButton(new Rect(1040, 124, 110, 44), "Close [Esc]")) { modal = ""; GUI.FocusControl(null); return; }
            if (modal == "audience") DrawAudienceModal();
            else if (modal == "help")
            {
                GUI.Label(new Rect(298, 189, 842, 490),
                    "1. Assemble four crawlers at camp. Select a crawler, choose a class, then enter the dungeon.\n\n" +
                    "2. Explore first: click reachable corridor tiles or use arrow keys. Approach caches and notes to interact. Enter the encounter door when ready.\n\n" +
                    "3. In battle, select a crawler and move on highlighted cells. Choose a class ability or item, click a legal target and review the forecast. Confirm to commit, or cancel without spending mana.\n\n" +
                    "4. Move before acting: an action ends that crawler’s activation. Wait ends that crawler's activation. End character turn advances to the next ready ally. Enemies respond after every ally finishes.\n\n" +
                    "5. Conditions create combinations: fire ignites oil; lightning conducts through a wet target; physical attacks shatter frozen targets. Tile effects and unit conditions are shown separately.\n\n" +
                    "6. Defeat the room's enemies, choose a sponsor reward, and prepare for the next room. Clear all three rooms to finish the floor.", bodyStyle);
                GUI.Label(new Rect(298, 702, 842, 65), "Keyboard: M chooses movement · W waits · Esc cancels or closes.\nTab moves UI focus; Enter confirms only when the Confirm button has focus.", smallStyle);
            }
            else if (modal == "settings")
            {
                bool oldCoordinates = showCoordinates, oldContrast = highContrast, oldMotion = reduceMotion;
                showCoordinates = GUI.Toggle(new Rect(304, 211, 804, 48), showCoordinates, "  Show board coordinates", buttonStyle);
                highContrast = GUI.Toggle(new Rect(304, 277, 804, 48), highContrast, "  Stronger reachable-cell contrast", buttonStyle);
                reduceMotion = GUI.Toggle(new Rect(304, 343, 804, 48), reduceMotion, "  Reduce presentation motion", buttonStyle);
                if (oldCoordinates != showCoordinates || oldContrast != highContrast || oldMotion != reduceMotion)
                {
                    PlayerPrefs.SetInt("DCT.coordinates", showCoordinates ? 1 : 0);
                    PlayerPrefs.SetInt("DCT.contrast", highContrast ? 1 : 0);
                    PlayerPrefs.SetInt("DCT.reduceMotion", reduceMotion ? 1 : 0);
                    PlayerPrefs.Save();
                }
                GUI.Label(new Rect(304, 436, 804, 132), "Terrain has text labels in addition to color. The game waits for your commands, so changing tabs never spends a turn.\n\nSettings and checkpoints are stored on this device. Export a save to move your run to another browser.", bodyStyle);
                if (ModalButton(new Rect(304, 666, 804, 54), "Start a new run")) modal = "reset";
                GUI.Label(new Rect(304, 739, 804, 34), "Unofficial fan game. Dungeon Crawler Carl belongs to its respective rights holders.", smallStyle);
            }
            else if (modal == "save") DrawSaveModal();
            else if (modal == "reset")
            {
                GUI.Label(new Rect(304, 225, 804, 140), "This replaces the active run with a fresh party at camp. Copy your save JSON first if you want to keep this run.", bodyStyle);
                if (ModalButton(new Rect(304, 440, 386, 60), "Keep playing")) modal = "";
                if (ModalButton(new Rect(714, 440, 386, 60), "Start new run")) { modal = ""; Command("new_run"); }
            }
        }

        private void DrawSaveModal()
        {
            GUI.Label(new Rect(298, 186, 840, 58), "Checkpoints save automatically after committed actions. Download a portable JSON backup, upload one to resume, or use the text field below.", smallStyle);
            if (ModalButton(new Rect(298, 258, 198, 48), "Save checkpoint")) StoreCheckpoint(true);
            if (ModalButton(new Rect(510, 258, 198, 48), "Load checkpoint", PlayerPrefs.HasKey(SaveKey))) LoadCheckpoint(SaveKey);
            if (ModalButton(new Rect(722, 258, 198, 48), "Previous backup", PlayerPrefs.HasKey(PreviousSaveKey))) LoadCheckpoint(PreviousSaveKey);
            if (ModalButton(new Rect(934, 258, 204, 48), "Refresh export")) saveText = JsonUtility.ToJson(session.ExportSave(), true);
            modalScroll = GUI.BeginScrollView(new Rect(298, 326, 840, 286), modalScroll, new Rect(0, 0, 814, Mathf.Max(266, textAreaStyle.CalcHeight(new GUIContent(saveText), 794))));
            GUI.SetNextControlName("SaveJson");
            saveText = GUI.TextArea(new Rect(0, 0, 814, Mathf.Max(266, textAreaStyle.CalcHeight(new GUIContent(saveText), 794))), saveText, 1000000, textAreaStyle);
            GUI.EndScrollView();
            if (ModalButton(new Rect(298, 626, 404, 44), "Download save JSON")) DownloadSave();
            if (ModalButton(new Rect(718, 626, 420, 44), "Upload save JSON")) ChooseSaveFile();
            if (ModalButton(new Rect(298, 682, 404, 44), "Copy JSON to clipboard"))
            {
                try { GUIUtility.systemCopyBuffer = saveText; notice = "Save JSON copied. Keep it in a text file as your portable backup."; }
                catch (Exception) { notice = "Clipboard is unavailable here. Select the JSON and use your browser's copy command."; }
            }
            if (ModalButton(new Rect(718, 682, 420, 44), "Import JSON")) { ImportCheckpoint(saveText); GUI.FocusControl(null); GUIUtility.ExitGUI(); }
            GUI.Label(new Rect(298, 730, 840, 56), notice, smallStyle);
        }
    }
}
