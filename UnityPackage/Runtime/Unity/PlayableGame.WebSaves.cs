using UnityEngine;
#if UNITY_WEBGL && !UNITY_EDITOR
using System.Runtime.InteropServices;
#endif

namespace DungeonCrawlerTactics.Unity
{
    public sealed partial class PlayableGame
    {
#if UNITY_WEBGL && !UNITY_EDITOR
        [DllImport("__Internal")] private static extern void DCT_DownloadSave(string json);
        [DllImport("__Internal")] private static extern void DCT_ImportSave(string objectName);
#endif
        private void DownloadSave()
        {
            saveText = JsonUtility.ToJson(session.ExportSave(), true);
#if UNITY_WEBGL && !UNITY_EDITOR
            DCT_DownloadSave(saveText);
            notice = "Save JSON download requested.";
#else
            notice = "File download is available in the Web player. Copy the JSON below to export from the Editor.";
#endif
        }

        private void ChooseSaveFile()
        {
#if UNITY_WEBGL && !UNITY_EDITOR
            DCT_ImportSave(gameObject.name);
#else
            notice = "File upload is available in the Web player. Paste JSON below to import from the Editor.";
#endif
        }

        // Unity's WebGL SendMessage entry points. These do not mutate state until core validation succeeds.
        public void ReceiveSaveJson(string json) { ImportCheckpoint(json); }
        public void ReceiveSaveError(string error) { notice = "Save import failed: " + error; }
    }
}
