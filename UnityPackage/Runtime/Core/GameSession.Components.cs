using System;
using System.Collections.Generic;

namespace DungeonCrawlerTactics
{
    public sealed partial class GameSession
    {
        // Stable IDs from the pinned whole-object library. Asset paths and image
        // crop/pivot metadata are resolved by the browser manifest, never saves.
        private static readonly HashSet<string> NativeComponentAssetIds = new HashSet<string>(new[] {
            "ab-clean-barrel-wood-top",
            "ab-clean-crate-wood-cross",
            "ab-clean-plant-leafy-terracotta",
            "ab-clean-chair-wood-blue",
            "ab-clean-table-wood-empty",
            "ab-clean-cot-metal-green",
            "ab-clean-door-double-wood-brass",
            "ab-clean-wall-straight-navy",
            "ab-clean-bench-wood-plain",
            "ab-clean-cot-metal-blue",
            "ab-clean-wheelchair-blue",
            "ab-clean-shelf-wood-empty",
            "cd-gear",
            "cd-lever-plinth",
            "cd-rail-straight",
            "cd-rail-junction",
            "cd-torch",
            "cd-crate",
            "cd-explosive-cart",
            "cd-dozer",
            "cd-weight-bench",
            "cd-barbell",
            "cd-wall-straight",
            "cd-throne",
            "cd-red-carpet",
            "cd-pipe-elbow",
            "cd-pipe-straight",
            "cd-hay-trough",
            "cd-llama",
            "cd-swine-boss",
            "cd-trap-machine",
            "cd-stair-module",
            "cd-door-threshold",
            "cd-drain-grate",
            "ef-toilet",
            "ef-sink-counter",
            "ef-litter-tray",
            "ef-litter-scoop",
            "ef-vending-green",
            "ef-wood-bench",
            "ef-wood-table",
            "ef-chair-green",
            "ef-bed-red",
            "ef-rug-red",
            "ef-plant-green",
            "ef-lamp-table",
        }, StringComparer.Ordinal);

        private static NativeMapComponent CopyNativeComponent(NativeMapComponent component)
        {
            return component == null ? null : new NativeMapComponent {
                id = component.id, assetId = component.assetId, layer = component.layer,
                x = component.x, y = component.y, width = component.width,
                height = component.height, rotation = component.rotation,
                blocksMovement = component.blocksMovement
            };
        }

        private static void ValidateNativeComponents(CustomMapData map, HashSet<string> blocked, HashSet<string> floors)
        {
            NativeMapVisuals art = map.visuals;
            Require(art.components != null && art.components.Length <= 512, "Invalid map component collection.");
            Require(art.componentLibraryId == null || art.componentLibraryId == "top-down-object-kit", "Unknown map component library.");
            if (art.components.Length == 0) return;
            Require(art.componentLibraryId == "top-down-object-kit", "Map components need their known library.");
            HashSet<string> ids = new HashSet<string>(), occupied = new HashSet<string>();
            foreach (NativeMapComponent component in art.components)
            {
                Require(component != null && !string.IsNullOrEmpty(component.id) && component.id.Length <= 100 && ids.Add(component.id)
                    && component.assetId != null && NativeComponentAssetIds.Contains(component.assetId)
                    && component.x >= 0 && component.y >= 0 && component.width >= 1 && component.width <= 12
                    && component.height >= 1 && component.height <= 12 && component.x <= map.width - component.width
                    && component.y <= map.height - component.height && component.rotation >= 0 && component.rotation < 4
                    && (component.layer == "props" || component.layer == "underlay")
                    && (!component.blocksMovement || component.layer == "props"), "Invalid map component asset or footprint.");
                for (int y = component.y; y < component.y + component.height; y++)
                    for (int x = component.x; x < component.x + component.width; x++)
                    {
                        Require(floors.Contains(TileId(x * 2, y * 2)), "Map components need ground beneath their complete footprint.");
                        if (component.blocksMovement)
                            Require(blocked.Contains(TileId(x, y)) && occupied.Add(TileId(x, y)), "Component collision differs from canonical terrain or overlaps another component.");
                    }
            }
        }

        private static bool NativeVisualsEqual(NativeMapVisuals a, NativeMapVisuals b)
        {
            if (a == null || b == null) return a == b;
            if (a.schemaVersion != b.schemaVersion || a.styleId != b.styleId || a.kitId != b.kitId
                || a.componentLibraryId != b.componentLibraryId || a.pieces == null || b.pieces == null
                || a.components == null || b.components == null || a.pieces.Length != b.pieces.Length
                || a.components.Length != b.components.Length) return false;
            for (int index = 0; index < a.pieces.Length; index++)
            {
                NativeMapPiece x = a.pieces[index], y = b.pieces[index];
                if (x == null || y == null || x.cell != y.cell || x.x2 != y.x2 || x.y2 != y.y2 || x.rotation != y.rotation || x.layer != y.layer) return false;
            }
            for (int index = 0; index < a.components.Length; index++)
            {
                NativeMapComponent x = a.components[index], y = b.components[index];
                if (x == null || y == null || x.id != y.id || x.assetId != y.assetId || x.layer != y.layer
                    || x.x != y.x || x.y != y.y || x.width != y.width || x.height != y.height
                    || x.rotation != y.rotation || x.blocksMovement != y.blocksMovement) return false;
            }
            return true;
        }
    }
}
