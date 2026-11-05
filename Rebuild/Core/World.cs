using System;
using System.Collections.Generic;
using System.Linq;
using System.Text.Json;

namespace DccRebuild;

public sealed class WorldObject
{
    public string id = "", kind = "", name = "", description = "", roomId = "";
    public int x, y;
}
public sealed class WorldRoom
{
    public string id = "", name = "", theme = "", objectId = "", kind = "", description = "";
    public int x, y, width, height;
    public bool safe;
}
public sealed class WorldMap
{
    public int width, height, spawnX, spawnY;
    public string[] tiles = Array.Empty<string>();
    public WorldObject[] objects = Array.Empty<WorldObject>();
    public WorldRoom[] rooms = Array.Empty<WorldRoom>();
    public string adaptation = "";
}
public static class World
{
    private sealed class Definition
    {
        public int width = 60, height = 38;
        public string adaptation = "";
        public WorldRoom[] rooms = Array.Empty<WorldRoom>();
    }
    // JSON is the authored source; the host embeds the same document shipped to the browser.
    public static WorldMap Build(int seed)
    {
        var assembly = typeof(World).Assembly;
        var resource = assembly.GetManifestResourceNames().SingleOrDefault(n => n.EndsWith("world-rooms.json", StringComparison.Ordinal));
        if (resource == null) throw new InvalidOperationException("Embed world-rooms.json in the core assembly.");
        using var stream = assembly.GetManifestResourceStream(resource)!;
        var definition = JsonSerializer.Deserialize<Definition>(stream, new JsonSerializerOptions { IncludeFields = true })!;
        var map = new WorldMap { width = definition.width, height = definition.height, rooms = definition.rooms, adaptation = definition.adaptation };
        map.tiles = Enumerable.Repeat("#", map.width * map.height).ToArray();
        uint random = unchecked((uint)seed) ^ 0xA341316Cu;
        int Next(int max) { random ^= random << 13; random ^= random >> 17; random ^= random << 5; return (int)(random % (uint)max); }
        void Floor(int x, int y) { if (x > 0 && y > 0 && x < map.width - 1 && y < map.height - 1) map.tiles[y * map.width + x] = "."; }
        void Line(int ax, int ay, int bx, int by)
        {
            while (ax != bx) { Floor(ax, ay); ax += Math.Sign(bx - ax); }
            while (ay != by) { Floor(ax, ay); ay += Math.Sign(by - ay); }
            Floor(bx, by);
        }
        foreach (var room in map.rooms)
            for (int y = room.y; y < room.y + room.height; y++)
                for (int x = room.x; x < room.x + room.width; x++) Floor(x, y);
        // A cardinal spine links each row; separate north/south streets create loops.
        for (int row = 0; row < 3; row++) Line(8, 7 + 12 * row, 50, 7 + 12 * row);
        Line(8, 7, 8, 31); Line(36, 7, 36, 31);
        var objects = new List<WorldObject>();
        foreach (var room in map.rooms)
        {
            objects.Add(new WorldObject { id = room.objectId, kind = room.kind, name = room.name, description = room.description, roomId = room.id, x = room.x + room.width / 2, y = room.y + room.height / 2 });
            // The west threshold is an inspectable door. It never blocks a route.
            objects.Add(new WorldObject { id = "door-" + room.id, kind = "door", name = room.name + " doorway", description = room.safe ? "A protected safe-room threshold. Rest inside." : "An open stone threshold leads into the chamber.", roomId = room.id, x = room.x, y = room.y + room.height / 2 });
        }
        // Seeded storage/service niches occupy the unused strips between anchor chambers.
        for (int col = 0; col < 4; col++)
        {
            int cx = 8 + 14 * col, y = 12 + Next(2), half = 1 + Next(2);
            for (int yy = 11; yy <= 14; yy++) for (int x = cx - half; x <= cx + half; x++) Floor(x, yy);
            objects.Add(new WorldObject { id = "cache-" + col, kind = "chest", name = new[] { "Rubbish salvage", "Maintenance cupboard", "Sealed supply crate", "Abandoned pantry" }[col], description = "A procedural Floor 1 service alcove. Search it for a modest supply cache.", x = cx + half, y = y });
        }
        // Shallow-looking sump water is explicitly impassable terrain; dry room lanes stay open.
        foreach (var index in new[] { 3, 5 })
        {
            var room = map.rooms[index];
            map.tiles[(room.y + 1) * map.width + room.x + 1] = "~";
            map.tiles[(room.y + 1) * map.width + room.x + 2] = "~";
        }
        objects.Add(new WorldObject { id = "exit", kind = "exit", name = "Floor 1 descending stair", description = "The stair beyond the Ball of Swine. Clear the borough boss before descending.", roomId = "ball-of-swine-complex", x = 41, y = 32 });
        map.spawnX = 6; map.spawnY = 7;
        map.objects = objects.ToArray();
        Validate(map);
        return map;
    }
    public static void Validate(WorldMap map)
    {
        var seen = new HashSet<int>(); var queue = new Queue<int>();
        int start = map.spawnY * map.width + map.spawnX;
        if (map.tiles.Length != map.width * map.height || map.tiles[start] != ".") throw new InvalidOperationException("Invalid world dimensions or spawn.");
        seen.Add(start); queue.Enqueue(start);
        while (queue.Count > 0)
        {
            int cell = queue.Dequeue(), x = cell % map.width, y = cell / map.width;
            foreach (var (dx, dy) in new[] { (1, 0), (-1, 0), (0, 1), (0, -1) })
            {
                int nx = x + dx, ny = y + dy, next = ny * map.width + nx;
                if (nx >= 0 && ny >= 0 && nx < map.width && ny < map.height && map.tiles[next] == "." && seen.Add(next)) queue.Enqueue(next);
            }
        }
        if (map.objects.Select(o => o.id).Distinct().Count() != map.objects.Length) throw new InvalidOperationException("Duplicate world object ID.");
        foreach (var obj in map.objects)
            if (obj.x < 1 || obj.y < 1 || obj.x >= map.width - 1 || obj.y >= map.height - 1 || !seen.Contains(obj.y * map.width + obj.x)) throw new InvalidOperationException("Unreachable world object: " + obj.id);
        for (int i = 0; i < map.tiles.Length; i++) if (map.tiles[i] == "." && !seen.Contains(i)) throw new InvalidOperationException("Disconnected floor tile.");
    }
}
