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
    public string archetype = "", shape = "", composition = "", floorStyle = "";
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
        public string roomId = "", archetype = "", shape = "rectangular", composition = "", floorStyle = "";
        public bool sideChannels = false;
        public int reserveCenterWidth = 0, reserveCenterHeight = 0;
        public int minWidth = 8, maxWidth = 11, minHeight = 6, maxHeight = 8;
        public string[] tileRows = Array.Empty<string>();
        public WorldProp[] assemblies = Array.Empty<WorldProp>();
        public PropGroup[] groups = Array.Empty<PropGroup>();
    }
    private sealed class PropGroup
    {
        public string id = "", anchor = "northwest", zone = "";
        public int offsetX = 0, offsetY = 0, jitterX = 0, jitterY = 0;
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
    public static WorldMap Build(int seed) => BuildConcept(seed, 4);
    public static WorldMap BuildVersion2(int seed) => BuildConcept(seed, 2);
    public static WorldMap BuildVersion3(int seed) => BuildConcept(seed, 3);
    private static WorldMap BuildConcept(int seed, int version)
    {
        var definition = Read<Definition>("world-rooms.json");
        bool legacy = version == 2;
        var rules = legacy ? JsonSerializer.Deserialize<RuleSet>(LegacyConceptGrammar.Json, new JsonSerializerOptions { IncludeFields = true })! : version == 3 ? JsonSerializer.Deserialize<RuleSet>(Version3ConceptGrammar.Json, new JsonSerializerOptions { IncludeFields = true })! : Read<RuleSet>("concept-room-rules.json");
        int sectorWidth = version >= 4 ? 22 : 14, sectorHeight = version >= 4 ? 16 : 12;
        var map = new WorldMap { generationVersion = version, width = version >= 4 ? 90 : definition.width,
            height = version >= 4 ? 52 : definition.height, rooms = definition.rooms, adaptation = definition.adaptation };
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
            room.archetype = rule.archetype; room.shape = rule.shape; room.composition = rule.composition; room.floorStyle = rule.floorStyle;
            room.width = rule.minWidth + Next(rule.maxWidth - rule.minWidth + 1);
            room.height = rule.minHeight + Next(rule.maxHeight - rule.minHeight + 1);
            room.x = 2 + (i % 4) * sectorWidth + Next(sectorWidth - 1 - room.width);
            room.y = 2 + (i / 4) * sectorHeight + Next((version >= 4 ? 14 : 10) - room.height);
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
                var east = map.rooms[i + 1]; int gutter = sectorWidth + 1 + (i % 4) * sectorWidth;
                Line(cx, cy, gutter, cy); Line(gutter, cy, gutter, east.y + east.height / 2); Line(gutter, east.y + east.height / 2, east.x + east.width / 2, east.y + east.height / 2);
            }
            if (i < 8 && (i % 4 == 0 || i % 4 == 2))
            {
                var south = map.rooms[i + 4]; int gutter = sectorHeight + 1 + (i / 4) * sectorHeight;
                bool gatePort = version >= 4 && south.composition == "industrial-sewer";
                int southPort = south.x + south.width / 2 + (gatePort ? 3 : 0);
                // Turn outside the wall apron; the north opening must be directly
                // behind the authored gold gate rather than a second center door.
                if (gatePort) gutter = Math.Min(gutter, south.y - 2);
                Line(cx, cy, cx, gutter); Line(cx, gutter, southPort, gutter); Line(southPort, gutter, southPort, south.y + south.height / 2);
            }
        }
        var entry = map.rooms[0]; map.spawnX = entry.x + entry.width / 2 - 1; map.spawnY = entry.y + entry.height / 2;
        var boss = map.rooms.Single(r => r.objectId == "ball-of-swine");
        objects.Add(new WorldObject { id = "exit", kind = "exit", name = "Floor 1 descending stair", description = "The stair beyond the Ball of Swine. Clear the borough boss before descending.", roomId = boss.id, x = legacy ? boss.x + boss.width - 1 : boss.x + boss.width / 2 + (version >= 4 ? 3 : 0), y = legacy ? boss.y + boss.height / 2 : boss.y + (version >= 4 ? 2 : 1) });
        for (int col = 0; col < 4; col++)
        {
            var room = map.rooms[col]; int x = room.x + room.width / 2, y = sectorHeight + 1;
            Line(x, room.y + room.height / 2, x, y);
            objects.Add(new WorldObject { id = "cache-" + col, kind = "chest", name = new[] { "Rubbish salvage", "Maintenance cupboard", "Sealed supply crate", "Abandoned pantry" }[col], description = "A Floor 1 service cache along the connecting passage.", x = x, y = y });
        }
        map.objects = objects.ToArray();
        var props = new List<WorldProp>();
        foreach (var room in map.rooms)
        {
            var rule = rules.rooms.Single(r => r.roomId == room.id); int serial = 0;
            if (rule.reserveCenterWidth > 0)
                for (int yy = room.y + (room.height - rule.reserveCenterHeight) / 2; yy < room.y + (room.height + rule.reserveCenterHeight) / 2; yy++)
                    for (int xx = room.x + (room.width - rule.reserveCenterWidth) / 2; xx < room.x + (room.width + rule.reserveCenterWidth) / 2; xx++) reserved.Add(yy * map.width + xx);
            if (version >= 4 && rule.tileRows.Length > 0)
            {
                if (rule.tileRows.Length != room.height || rule.tileRows.Any(row => row.Length != room.width || row.Any(c => c is not ('#' or '.' or '~'))))
                    throw new InvalidOperationException("Invalid authored room footprint.");
                for (int yy = 0; yy < room.height; yy++) for (int xx = 0; xx < room.width; xx++)
                    map.tiles[(room.y + yy) * map.width + room.x + xx] = rule.tileRows[yy][xx].ToString();
            }
            if (rule.sideChannels && !(version >= 4 && rule.tileRows.Length > 0))
                foreach (int xx in new[] { room.x, room.x + room.width - 1 })
                    for (int yy = room.y + 2; yy < room.y + room.height - 2; yy++)
                    { int cell = yy * map.width + xx; if (!reserved.Contains(cell)) map.tiles[cell] = "~"; }

            // Authored groups keep meaningful relative relationships: teaching furniture,
            // a paired stair approach, and separated living/washroom zones.
            foreach (var group in rule.groups)
            {
                if (group.members.Length == 0) throw new InvalidOperationException("Empty furniture group.");
                int minX = group.members.Min(m => m.offsetX), minY = group.members.Min(m => m.offsetY);
                int gw = group.members.Max(m => m.offsetX + m.width) - minX, gh = group.members.Max(m => m.offsetY + m.height) - minY;
                int gx = room.x + (group.anchor.EndsWith("east", StringComparison.Ordinal) ? room.width - gw : 0) - minX;
                int gy = room.y + (group.anchor.StartsWith("south", StringComparison.Ordinal) ? room.height - gh : 0) - minY;
                if (group.anchor is "north" or "south" or "center") gx = room.x + (room.width - gw) / 2 - minX;
                if (group.anchor == "center") gy = room.y + (room.height - gh) / 2 - minY;
                gx += group.offsetX + (group.jitterX > 0 ? Next(group.jitterX + 1) * (group.anchor.EndsWith("east") ? -1 : 1) : 0);
                gy += group.offsetY + (group.jitterY > 0 ? Next(group.jitterY + 1) : 0);
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
                        bool wallFixture = version >= 4 && prop.layer == "wallfixture" && map.tiles[cell] == "#";
                        if ((!wallFixture && map.tiles[cell] != "." && !(map.tiles[cell] == "~" && !prop.blocksMovement)) || (prop.blocksMovement && (reserved.Contains(cell) || !blocked.Add(cell)))) throw new InvalidOperationException("Group crosses reserved route or furniture: " + room.id + "/" + group.id);
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
    // Combat and exploration share the resolved industrial composition, not parallel obstacle sketches.
    public static Battle BuildArena(int seed, string encounterId)
    {
        var battle = new Battle { encounterId = encounterId };
        if (encounterId is not ("goblin-workshop" or "ball-of-swine")) return battle;
        var world = Build(seed);
        var room = world.rooms.Single(r => r.objectId == encounterId);
        battle.width = room.width; battle.height = room.height;
        battle.theme = room.floorStyle; battle.composition = room.composition;
        battle.tiles = Enumerable.Range(0, room.width * room.height)
            .Select(n => world.tiles[(room.y + n / room.width) * world.width + room.x + n % room.width]).ToArray();
        battle.props = world.props.Where(p => p.roomId == room.id).Select(p => {
            var copy = JsonSerializer.Deserialize<WorldProp>(JsonSerializer.Serialize(p, Codec.Options), Codec.Options)!;
            copy.x -= room.x; copy.y -= room.y; copy.groupX -= room.x; copy.groupY -= room.y;
            return copy;
        }).ToArray();
        battle.obstacles = Enumerable.Range(0, battle.tiles.Length).Where(n => battle.tiles[n] != ".")
            .Select(n => new Point { x = n % battle.width, y = n / battle.width }).ToArray();
        return battle;
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
                if (prop.layer == "wallfixture" && map.tiles[cell] != "#") throw new InvalidOperationException("Wall fixture must occupy blocked masonry.");
                if (prop.blocksMovement && (!occupied.Add(cell) || map.tiles[cell] != "#")) throw new InvalidOperationException("Overlapping or inconsistent prop collision.");
            }
        }

    }
}
