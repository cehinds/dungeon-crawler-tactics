using System;
using UnityEngine;

namespace DungeonCrawlerTactics.Unity
{
    /// <summary>Composition root and command adapter. Combat state belongs exclusively to GameSession.</summary>
    public sealed partial class PlayableGame : MonoBehaviour
    {
        [SerializeField] private TextAsset combatContent;
        [SerializeField] private TextAsset gameContent;
        private const string SaveKey = "DungeonCrawlerTactics.save.v1";
        private const string PreviousSaveKey = "DungeonCrawlerTactics.previousSave.v1";
        private GameSession session;
        private GameView view;
        private string bootError;
        private string notice = "Select four crawlers, choose their classes, and enter the dungeon.";
        private string actionId = "";
        private string itemId = "";
        private string inspectedId = "";
        private string modal = "";
        private string saveText = "";
        private bool showCoordinates;
        private bool highContrast;
        private bool reduceMotion;
        private Vector2 logScroll;
        private Vector2 rosterScroll;
        private Vector2 actionScroll;
        private Vector2 modalScroll;
        private Vector2 forecastScroll;
        
        public void Configure(TextAsset combat, TextAsset game)
        {
            combatContent = combat;
            gameContent = game;
        }

        private void Start()
        {
            showCoordinates = PlayerPrefs.GetInt("DCT.coordinates", 0) != 0;
            highContrast = PlayerPrefs.GetInt("DCT.contrast", 0) != 0;
            reduceMotion = PlayerPrefs.GetInt("DCT.reduceMotion", 0) != 0;
            Boot();
        }

        private void Boot()
        {
            try
            {
                if (combatContent == null || gameContent == null)
                    throw new InvalidOperationException("Missing content. Use Dungeon Crawler > Create Playable Scene in the Unity Editor, or assign combat-content.json and game-content.json in the Inspector.");
                session = new GameSession(JsonUtility.FromJson<Content>(combatContent.text), JsonUtility.FromJson<GameData>(gameContent.text));
                view = session.GetView();
                bootError = null;
                if (PlayerPrefs.HasKey(SaveKey)) notice = "A local checkpoint is available. Open Save / Load to resume it, or start a new party.";
            }
            catch (Exception ex) { bootError = ex.Message; Debug.LogException(ex, this); }
        }

        private void Submit(GameCommand command, bool clearTarget = true)
        {
            try
            {
                view = session.Handle(command);
                notice = AudienceNotice(view.message);
                if (clearTarget) { actionId = ""; itemId = ""; }
                if (command.type != "preview" && command.type != "preview_favor" && command.type != "cancel" && command.type != "select") StoreCheckpoint(false);
            }
            catch (Exception ex) { notice = "Action rejected: " + ex.Message; }
            GUI.FocusControl(null);
            GUIUtility.ExitGUI();
        }

        private void Command(string type)
        {
            Submit(new GameCommand { type = type });
        }

        private void StoreCheckpoint(bool acknowledge)
        {
            try
            {
                string json = JsonUtility.ToJson(session.ExportSave(), true);
                if (PlayerPrefs.HasKey(SaveKey) && PlayerPrefs.GetString(SaveKey) == json)
                { if (acknowledge) notice = "Your checkpoint is already up to date."; return; }
                if (PlayerPrefs.HasKey(SaveKey)) PlayerPrefs.SetString(PreviousSaveKey, PlayerPrefs.GetString(SaveKey));
                PlayerPrefs.SetString(SaveKey, json);
                PlayerPrefs.Save();
                if (acknowledge) notice = "Checkpoint stored in this browser or device. Export JSON for a portable backup.";
            }
            catch (Exception ex) { notice = "Local save could not be stored: " + ex.Message + ". Export JSON to keep a backup."; }
        }

        private void LoadCheckpoint(string key)
        {
            if (!PlayerPrefs.HasKey(key)) { notice = "No checkpoint has been stored yet."; return; }
            ImportCheckpoint(PlayerPrefs.GetString(key));
        }

        private void ImportCheckpoint(string json)
        {
            try
            {
                if (string.IsNullOrWhiteSpace(json) || json.Length > 1000000) throw new ArgumentException("Paste a save JSON file under 1 MB.");
                GameSave save = JsonUtility.FromJson<GameSave>(json);
                if (save == null) throw new ArgumentException("Save JSON is empty.");
                view = session.ImportSave(save);
                if (!string.IsNullOrEmpty(view.message) && view.message.StartsWith("Save rejected", StringComparison.Ordinal))
                { notice = view.message; return; }
                actionId = ""; itemId = ""; inspectedId = "";
                notice = "Checkpoint loaded.";
                modal = "";
                StoreCheckpoint(false);
            }
            catch (Exception ex) { notice = "Save rejected; your current run is still available. " + ex.Message; }
        }

        private void OnApplicationPause(bool paused)
        {
            if (paused && session != null) StoreCheckpoint(false);
        }

        private void OnApplicationQuit()
        {
            if (session != null) StoreCheckpoint(false);
        }

        private void OnDestroy()
        {
            ReleaseArt();
        }

        private void OnGUI()
        {
            EnsureStyles();
            float scale = Mathf.Min(Screen.width / 1440f, Screen.height / 900f);
            if (scale <= 0) return;
            Matrix4x4 previous = GUI.matrix;
            GUI.matrix = Matrix4x4.TRS(new Vector3((Screen.width - 1440 * scale) / 2, (Screen.height - 900 * scale) / 2, 0), Quaternion.identity, Vector3.one * scale);
            GUI.DrawTexture(new Rect(0, 0, 1440, 900), Texture2D.whiteTexture, ScaleMode.StretchToFill, false, 0, Background, 0, 0);
            try
            {
                if (bootError != null) DrawBootError();
                else if (view != null)
                {
                    HandleKeyboard();
                    DrawHeader();
                    if (view.screen == "camp") DrawCamp();
                    else if (view.screen == "explore") DrawExploration();
                    else if (view.screen == "battle") DrawBattle();
                    else DrawOutcome();
                    DrawFooter();
                    if (!string.IsNullOrEmpty(modal)) DrawModal();
                    DrawNeighborhood();
                }
            }
            finally { GUI.matrix = previous; }
        }

        private void HandleKeyboard()
        {
            Event ev = Event.current;
            if (ev.type != EventType.KeyDown) return;
            if (!string.IsNullOrEmpty(modal))
            {
                if (ev.keyCode == KeyCode.Escape) { modal = ""; GUI.FocusControl(null); ev.Use(); }
                return;
            }
            if (view.screen == "explore" && view.exploration != null)
            {
                int dx = 0, dy = 0;
                if (ev.keyCode == KeyCode.LeftArrow) dx = -1;
                if (ev.keyCode == KeyCode.RightArrow) dx = 1;
                if (ev.keyCode == KeyCode.UpArrow) dy = -1;
                if (ev.keyCode == KeyCode.DownArrow) dy = 1;
                if (dx != 0 || dy != 0)
                {
                    ev.Use();
                    Submit(new GameCommand { type = "explore_move", x = view.exploration.x + dx, y = view.exploration.y + dy });
                }
                return;
            }
            if (view.screen != "battle") return;
            if (ev.keyCode == KeyCode.Escape) { ev.Use(); Command("cancel"); }
            if (ev.keyCode == KeyCode.Return && view.canConfirm && GUI.GetNameOfFocusedControl() == "ConfirmAction") { ev.Use(); Command("confirm"); }
            if (ev.keyCode == KeyCode.W && view.canAct && !view.canConfirm && !string.IsNullOrEmpty(view.selectedUnitId)) { ev.Use(); Command("wait"); }
            if (ev.keyCode == KeyCode.M && view.canMove && !view.canConfirm) { actionId = ""; itemId = ""; notice = "Click a highlighted cell to move."; ev.Use(); }
        }
    }
}
