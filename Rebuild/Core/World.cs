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
    public string archetype = "", shape = "";
    public int x, y, width, height;
    public bool safe;
}
public sealed class WorldProp
{
    public string id = "", assetId = "", roomId = "", groupId = "", zone = "", anchor = "", layer = "object";
    public int offsetX, offsetY, groupX, groupY;
    public int x, y, width, height, rotation;
    public bool blocksMovement = true;
}
public sealed class WorldMap
{
    public int width, height, spawnX, spawnY;
    public string[] tiles = Array.Empty<string>();
    public WorldObject[] objects = Array.Empty<WorldObject>();
    public WorldRoom[] rooms = Array.Empty<WorldRoom>();
    public WorldProp[] props = Array.Empty<WorldProp>();
    public int generationVersion;
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
    private sealed class RuleSet { public RoomRule[] rooms = Array.Empty<RoomRule>(); }
    private sealed class RoomRule
    {
        public string roomId = "", archetype = "", shape = "rectangular";
        public int minWidth = 8, maxWidth = 11, minHeight = 6, maxHeight = 8;
        public WorldProp[] assemblies = Array.Empty<WorldProp>();
        public PropGroup[] groups = Array.Empty<PropGroup>();
    }
    private sealed class PropGroup
    {
        public string id = "", anchor = "northwest", zone = "";
        public WorldProp[] members = Array.Empty<WorldProp>();
    }
    private static T Read<T>(string name)
    {
        var assembly = typeof(World).Assembly;
        var resource = assembly.GetManifestResourceNames().Single(n => n.EndsWith(name, StringComparison.Ordinal));
        using var stream = assembly.GetManifestResourceStream(resource)!;
        return JsonSerializer.Deserialize<T>(stream, new JsonSerializerOptions { IncludeFields = true })!;
    }
    // C# alone resolves the authored concept grammar into tiles and whole-object footprints.
    public static WorldMap Build(int seed)
    {
        var definition = Read<Definition>("world-rooms.json");
        var rules = Read<RuleSet>("concept-room-rules.json");
        var map = new WorldMap { generationVersion = 2, width = definition.width, height = definition.height, rooms = definition.rooms, adaptation = definition.adaptation };
        map.tiles = Enumerable.Repeat("#", map.width * map.height).ToArray();
        uint random = unchecked((uint)seed) ^ 0xA341316Cu;
        if (random == 0) random = 1;
        int Next(int max) { random ^= random << 13; random ^= random >> 17; random ^= random << 5; return (int)(random % (uint)max); }
        var reserved = new HashSet<int>();
        void Floor(int x, int y, bool reserve = false)
        {
            if (x <= 0 || y <= 0 || x >= map.width - 1 || y >= map.height - 1) return;
            int cell = y * map.width + x; map.tiles[cell] = "."; if (reserve) reserved.Add(cell);
        }
        void Line(int ax, int ay, int bx, int by)
        {
            while (ax != bx) { Floor(ax, ay, true); ax += Math.Sign(bx - ax); }
            while (ay != by) { Floor(ax, ay, true); ay += Math.Sign(by - ay); }
            Floor(bx, by, true);
        }
        for (int i = 0; i < map.rooms.Length; i++)
        {
            var room = map.rooms[i]; var rule = rules.rooms.Single(r => r.roomId == room.id);
            room.archetype = rule.archetype; room.shape = rule.shape;
            room.width = rule.minWidth + Next(rule.maxWidth - rule.minWidth + 1);
            room.height = rule.minHeight + Next(rule.maxHeight - rule.minHeight + 1);
            room.x = 2 + (i % 4) * 14 + Next(13 - room.width);
            room.y = 2 + (i / 4) * 12 + Next(10 - room.height);
            for (int y = 0; y < room.height; y++) for (int x = 0; x < room.width; x++)
            {
                bool corner = (x == 0 || x == room.width - 1) && (y < 2 || y >= room.height - 2);
                bool inset = rule.shape == "split" && x > room.width / 2 && y == 0;
                if (!(rule.shape == "rounded" && corner) && !inset) Floor(room.x + x, room.y + y);
            }
        }
        var objects = new List<WorldObject>();
        for (int i = 0; i < map.rooms.Length; i++)
        {
            var room = map.rooms[i]; int cx = room.x + room.width / 2, cy = room.y + room.height / 2;
            // Door ports and their axial lanes remain clear through every furniture assembly.
            Line(room.x, cy, room.x + room.width - 1, cy);
            Line(cx, room.y, cx, room.y + room.height - 1);
            objects.Add(new WorldObject { id = room.objectId, kind = room.kind, name = room.name, description = room.description, roomId = room.id, x = cx, y = cy });
            objects.Add(new WorldObject { id = "door-" + room.id, kind = "door", name = room.name + " doorway", description = room.safe ? "A protected safe-room threshold. Rest inside." : "An open threshold leads into the chamber.", roomId = room.id, x = room.x, y = cy });
            if (i % 4 < 3)
            {
                var east = map.rooms[i + 1]; int gutter = 15 + (i % 4) * 14;
                Line(cx, cy, gutter, cy); Line(gutter, cy, gutter, east.y + east.height / 2); Line(gutter, east.y + east.height / 2, east.x + east.width / 2, east.y + east.height / 2);
            }
            if (i < 8 && (i % 4 == 0 || i % 4 == 2))
            {
                var south = map.rooms[i + 4]; int gutter = 13 + (i / 4) * 12;
                Line(cx, cy, cx, gutter); Line(cx, gutter, south.x + south.width / 2, gutter); Line(south.x + south.width / 2, gutter, south.x + south.width / 2, south.y + south.height / 2);
            }
        }
        var entry = map.rooms[0]; map.spawnX = entry.x + entry.width / 2 - 1; map.spawnY = entry.y + entry.height / 2;
        var boss = map.rooms.Single(r => r.objectId == "ball-of-swine");
        objects.Add(new WorldObject { id = "exit", kind = "exit", name = "Floor 1 descending stair", description = "The stair beyond the Ball of Swine. Clear the borough boss before descending.", roomId = boss.id, x = boss.x + boss.width - 1, y = boss.y + boss.height / 2 });
        for (int col = 0; col < 4; col++)
        {
            var room = map.rooms[col]; int x = room.x + room.width / 2, y = 13;
            Line(x, room.y + room.height / 2, x, y);
            objects.Add(new WorldObject { id = "cache-" + col, kind = "chest", name = new[] { "Rubbish salvage", "Maintenance cupboard", "Sealed supply crate", "Abandoned pantry" }[col], description = "A Floor 1 service cache along the connecting passage.", x = x, y = y });
        }
        map.objects = objects.ToArray();
        var props = new List<WorldProp>();
        foreach (var room in map.rooms)
        {
            var rule = rules.rooms.Single(r => r.roomId == room.id); int serial = 0;
            // Authored groups keep meaningful relative relationships: teaching furniture,
            // a paired stair approach, and separated living/washroom zones.
            foreach (var group in rule.groups)
            {
                if (group.members.Length == 0) throw new InvalidOperationException("Empty furniture group.");
                int minX = group.members.Min(m => m.offsetX), minY = group.members.Min(m => m.offsetY);
                int gw = group.members.Max(m => m.offsetX + m.width) - minX, gh = group.members.Max(m => m.offsetY + m.height) - minY;
                int gx = room.x + (group.anchor.EndsWith("east", StringComparison.Ordinal) ? room.width - gw : 0) - minX;
                int gy = room.y + (group.anchor.StartsWith("south", StringComparison.Ordinal) ? room.height - gh : 0) - minY;
                var candidates = group.members.Select((m, n) => new WorldProp { id = room.id + "-" + group.id + "-" + n, roomId = room.id, assetId = m.assetId,
                    x = gx + m.offsetX, y = gy + m.offsetY, width = m.width, height = m.height, rotation = m.rotation, blocksMovement = m.blocksMovement,
                    groupId = group.id, zone = group.zone, anchor = group.anchor, layer = m.layer, groupX = gx, groupY = gy, offsetX = m.offsetX, offsetY = m.offsetY }).ToArray();
                var blocked = new HashSet<int>();
                foreach (var prop in candidates)
                {
                    if (prop.x < room.x || prop.y < room.y || prop.x + prop.width > room.x + room.width || prop.y + prop.height > room.y + room.height) throw new InvalidOperationException("Group exceeds room: " + group.id);
                    for (int dy = 0; dy < prop.height; dy++) for (int dx = 0; dx < prop.width; dx++)
                    {
                        int cell = (prop.y + dy) * map.width + prop.x + dx;
                        if (map.tiles[cell] != "." || (prop.blocksMovement && (reserved.Contains(cell) || !blocked.Add(cell)))) throw new InvalidOperationException("Group crosses reserved route or furniture: " + room.id + "/" + group.id);
                    }
                }
                foreach (var cell in blocked) map.tiles[cell] = "#";
                Validate(map); // The complete assembly is accepted atomically, never a partial scatter.
                props.AddRange(candidates);
            }
            foreach (var assembly in rule.assemblies)
            {
                int w = assembly.width, h = assembly.height;
                if (w < 1 || h < 1 || w > room.width - 2 || h > room.height - 2) throw new InvalidOperationException("Invalid assembly footprint.");
                for (int attempt = 0; attempt < 48; attempt++)
                {
                    int x = room.x + Next(room.width - w + 1), y = room.y + Next(room.height - h + 1);
                    var cells = Enumerable.Range(0, w * h).Select(n => (y + n / w) * map.width + x + n % w).ToArray();
                    if (cells.Any(c => reserved.Contains(c) || map.tiles[c] != ".")) continue;
                    foreach (var c in cells) map.tiles[c] = "#";
                    // Reject a placement that strands a floor pocket or an interaction.
                    try { Validate(map); } catch (InvalidOperationException) { foreach (var c in cells) map.tiles[c] = "."; continue; }
                    props.Add(new WorldProp { id = room.id + "-prop-" + serial++, roomId = room.id, assetId = assembly.assetId, x = x, y = y, width = w, height = h, rotation = assembly.rotation });
                    break;
                }
            }
        }
        map.props = props.ToArray(); Validate(map); return map;
    }
    public static WorldMap BuildLegacy(int seed)
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
        map.generationVersion = 1;
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
        var occupied = new HashSet<int>();
        foreach (var prop in map.props)
        {
            if (prop.width < 1 || prop.height < 1 || string.IsNullOrWhiteSpace(prop.assetId) || !new[] { 0, 90, 180, 270 }.Contains(prop.rotation)) throw new InvalidOperationException("Invalid world prop.");
            var room = map.rooms.Single(r => r.id == prop.roomId);
            if (prop.x < room.x || prop.y < room.y || prop.x + prop.width > room.x + room.width || prop.y + prop.height > room.y + room.height) throw new InvalidOperationException("Prop outside room.");
            for (int dy = 0; dy < prop.height; dy++) for (int dx = 0; dx < prop.width; dx++)
            {
                int cell = (prop.y + dy) * map.width + prop.x + dx;
                if (prop.blocksMovement && (!occupied.Add(cell) || map.tiles[cell] != "#")) throw new InvalidOperationException("Overlapping or inconsistent prop collision.");
            }
        }

    }
}
