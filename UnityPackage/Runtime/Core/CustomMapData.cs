using System;
namespace DungeonCrawlerTactics
{
    [Serializable]
    public sealed class CustomMapData
    {
        public int schemaVersion = 1, width, height;
        public string label = "Workshop encounter";
        public TileDef[] tiles = new TileDef[0];
        public CellView[] playerSpawns = new CellView[0];
        public SpawnDef[] enemies = new SpawnDef[0];
        public MapPlacement[] placements = new MapPlacement[0];
        // Optional presentation only. Combat legality still comes from tiles and placements.
        public NativeMapVisuals visuals;
    }
    [Serializable]
    public sealed class NativeMapVisuals
    {
        public int schemaVersion = 1;
        public string styleId, kitId;
        public NativeMapPiece[] pieces = new NativeMapPiece[0];
    }
    [Serializable]
    public sealed class NativeMapPiece
    {
        public int cell, x2, y2, rotation;
        public string layer;
    }
    [Serializable]
    public sealed class MapPlacement
    {
        public string id, assetId, layer;
        public int x, y, rotation;
        public bool blocksMovement;
    }
}
