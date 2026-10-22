using System;
using System.IO;
using System.Collections.Generic;
using DungeonCrawlerTactics.Unity;
using UnityEditor;
using UnityEditor.Build;
using UnityEditor.Build.Reporting;
using UnityEditor.SceneManagement;
using UnityEngine;
using UnityEngine.SceneManagement;

namespace DungeonCrawlerTactics.Editor
{
    /// <summary>Creates real Unity scene assets through Editor APIs; never writes scene YAML.</summary>
    public static class PlayableSceneBuilder
    {
        public const string Root = "Assets/DungeonCrawlerTactics";
        public const string ScenePath = Root + "/Scenes/Playable.unity";
        public const string CombatPath = Root + "/Runtime/Data/combat-content.json";
        public const string GamePath = Root + "/Runtime/Data/game-content.json";

        [MenuItem("Dungeon Crawler/Create Playable Scene", priority = 0)]
        public static void CreatePlayableScene()
        {
            try
            {
                ValidateContent();
                if (!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) return;
                SceneAsset existing = AssetDatabase.LoadAssetAtPath<SceneAsset>(ScenePath);
                if (existing != null)
                {
                    EditorSceneManager.OpenScene(ScenePath, OpenSceneMode.Single);
                    Debug.Log("Opened existing playable scene: " + ScenePath);
                    return;
                }
                EnsureFolder(Root + "/Scenes");
                Scene scene = EditorSceneManager.NewScene(NewSceneSetup.EmptyScene, NewSceneMode.Single);
                GameObject cameraObject = new GameObject("Presentation Camera");
                Undo.RegisterCreatedObjectUndo(cameraObject, "Create presentation camera");
                Camera camera = cameraObject.AddComponent<Camera>();
                camera.orthographic = true;
                camera.orthographicSize = 5;
                camera.clearFlags = CameraClearFlags.SolidColor;
                camera.backgroundColor = new Color32(14, 19, 24, 255);
                cameraObject.transform.position = new Vector3(0, 0, -10);
                GameObject root = new GameObject("Dungeon Crawler Tactics");
                Undo.RegisterCreatedObjectUndo(root, "Create playable game");
                PlayableGame game = root.AddComponent<PlayableGame>();
                game.Configure(AssetDatabase.LoadAssetAtPath<TextAsset>(CombatPath), AssetDatabase.LoadAssetAtPath<TextAsset>(GamePath));
                EditorUtility.SetDirty(game);
                if (!EditorSceneManager.SaveScene(scene, ScenePath)) throw new InvalidOperationException("Could not save playable scene.");
                List<EditorBuildSettingsScene> scenes = new List<EditorBuildSettingsScene>(EditorBuildSettings.scenes);
                scenes.Add(new EditorBuildSettingsScene(ScenePath, true));
                EditorBuildSettings.scenes = scenes.ToArray();
                Selection.activeGameObject = root;
                Debug.Log("Playable scene created. Press Play to choose your party. Web build: Dungeon Crawler > Build Web Player.", game);
            }
            catch (Exception ex) { Debug.LogException(ex); EditorUtility.DisplayDialog("Dungeon Crawler", ex.Message, "OK"); }
        }

        [MenuItem("Dungeon Crawler/Validate Content", priority = 10)]
        public static void ValidateContentMenu()
        {
            try { ValidateContent(); Debug.Log("Dungeon Crawler combat and game content validated."); }
            catch (Exception ex) { Debug.LogException(ex); EditorUtility.DisplayDialog("Content validation failed", ex.Message, "OK"); }
        }

        public static void ValidateContent()
        {
            TextAsset combat = AssetDatabase.LoadAssetAtPath<TextAsset>(CombatPath);
            TextAsset game = AssetDatabase.LoadAssetAtPath<TextAsset>(GamePath);
            if (combat == null || game == null) throw new BuildFailedException("Missing authored content. Expected " + CombatPath + " and " + GamePath + ". Copy UnityPackage contents into " + Root + ".");
            try { new GameSession(JsonUtility.FromJson<Content>(combat.text), JsonUtility.FromJson<GameData>(game.text)); }
            catch (Exception ex) { throw new BuildFailedException("Combat or game content is invalid: " + ex.Message); }
        }

        [MenuItem("Dungeon Crawler/Build Web Player", priority = 20)]
        public static void BuildWebPlayer()
        {
            try
            {
                ValidateContent();
                if (!BuildPipeline.IsBuildTargetSupported(BuildTargetGroup.WebGL, BuildTarget.WebGL)) throw new InvalidOperationException("Install Web Build Support for this Unity Editor in Unity Hub.");
                if (AssetDatabase.LoadAssetAtPath<SceneAsset>(ScenePath) == null) CreatePlayableScene();
                if (AssetDatabase.LoadAssetAtPath<SceneAsset>(ScenePath) == null) return;
                if (!EditorSceneManager.SaveCurrentModifiedScenesIfUserWantsTo()) return;
                string output = EditorUtility.SaveFolderPanel("Choose Web player output folder", "Builds", "Web");
                if (string.IsNullOrEmpty(output)) return;
                BuildReport report = BuildPipeline.BuildPlayer(new BuildPlayerOptions
                {
                    scenes = new[] { ScenePath }, locationPathName = output,
                    target = BuildTarget.WebGL, options = BuildOptions.None
                });
                if (report.summary.result != BuildResult.Succeeded) throw new BuildFailedException("Web build " + report.summary.result + ". Check the Unity Console for details.");
                Debug.Log("Web player built: " + output + ". Serve over HTTP with the compression headers configured in Player Settings.");
                EditorUtility.RevealInFinder(output);
            }
            catch (Exception ex) { Debug.LogException(ex); EditorUtility.DisplayDialog("Web build could not finish", ex.Message, "OK"); }
        }

        private static void EnsureFolder(string path)
        {
            if (AssetDatabase.IsValidFolder(path)) return;
            string parent = Path.GetDirectoryName(path).Replace('\\', '/');
            EnsureFolder(parent);
            AssetDatabase.CreateFolder(parent, Path.GetFileName(path));
        }
    }

    public sealed class GameContentBuildCheck : IPreprocessBuildWithReport
    {
        public int callbackOrder { get { return 0; } }
        public void OnPreprocessBuild(BuildReport report) { PlayableSceneBuilder.ValidateContent(); }
    }

    public sealed class PixelArtImporter : AssetPostprocessor
    {
        private void OnPreprocessTexture()
        {
            if (!assetPath.StartsWith(PlayableSceneBuilder.Root + "/Runtime/Resources/Art/", StringComparison.Ordinal)) return;
            TextureImporter importer = (TextureImporter)assetImporter;
            importer.textureType = TextureImporterType.Default;
            importer.filterMode = FilterMode.Point;
            importer.mipmapEnabled = false;
            importer.wrapMode = TextureWrapMode.Clamp;
            importer.alphaIsTransparency = true;
            importer.textureCompression = TextureImporterCompression.Uncompressed;
            importer.maxTextureSize = 256;
        }
    }
}
