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
    }
    [Serializable]
    public sealed class MapPlacement
    {
        public string id, assetId, layer;
        public int x, y, rotation;
        public bool blocksMovement;
    }
}
