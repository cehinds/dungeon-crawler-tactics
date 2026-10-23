using System;
namespace DungeonCrawlerTactics
{
    [Serializable]
    public sealed class ScenarioDef
    {
        public string id, label, description, objective, kind, bossId, conceptArt;
        public EncounterDef encounter;
        public int damage = 8, minionCap = 2, helperCount = 2, constructionTotal = 3, barrierDurability = 2;
        public string[] minionIds = new string[0];
        public CellView[] route = new CellView[0];
        public MapPlacement[] decorations = new MapPlacement[0];
        public InteractableDef[] interactables = new InteractableDef[0];
    }
    [Serializable]
    public sealed class InteractableDef
    {
        public string id, label, description, kind;
        public int x, y, hp = 2;
    }
    [Serializable]
    public sealed class ScenarioOptionView
    {
        public string id, label, description, objective, kind, conceptArt;
    }
    [Serializable]
    public sealed class IntentView
    {
        public string id, label, description, actorId;
        public int damage, originX, originY, turns = 1;
        public CellView[] cells = new CellView[0];
    }
    [Serializable]
    public sealed class ScenarioObjectSave
    {
        public string id;
        public int hp;
        public bool used;
    }
    [Serializable]
    public sealed class ScenarioSave
    {
        public int version = 1, progress, barrierHp, helpers, routeIndex, turns;
        public bool emergenceInterrupted;
        public string id;
        public string[] carryingUnitIds = new string[0];
        public ScenarioObjectSave[] objects = new ScenarioObjectSave[0];
        public IntentView intent;
        public GameSave campaign;
    }
    [Serializable]
    public sealed class ScenarioInteractableView
    {
        public string id, label, description, action;
        public int x, y, hp, maxHp, progress, total;
        public bool enabled, used, destroyed;
    }
    [Serializable]
    public sealed class ScenarioView
    {
        public string id, label, objective, description, conceptArt;
        public IntentView intent;
        public int progress, total, barrierHp, helpers;
        public string[] carryingUnitIds = new string[0];
        public MapPlacement[] decorations = new MapPlacement[0];
        public ScenarioInteractableView[] interactables = new ScenarioInteractableView[0];
    }
}
namespace DungeonCrawlerTactics
{
    public static class ScenarioDefinitionValidator
    {
        private static void Need(bool value, string text)
        {
            if (!value)
                throw new ArgumentException(text);
        }
        private static bool Id(string id)
        {
            return id != null && id.IndexOf('.') > 0 && System.Text.RegularExpressions.Regex.IsMatch(id, @"^[a-z][a-z0-9_]*(\.[a-z][a-z0-9_]*)*$");
        }
        public static void Validate(GameData data, Catalog catalog)
        {
            Need(data.scenarios != null && data.scenarios.Length <= 16, "Invalid scenario array.");
            var ids = new System.Collections.Generic.HashSet<string>();
            foreach (var s in data.scenarios)
            {
                Need(s != null && Id(s.id) && ids.Add(s.id) && !string.IsNullOrEmpty(s.label) && !string.IsNullOrEmpty(s.description) && !string.IsNullOrEmpty(s.objective), "Invalid scenario identity.");
                Need(s.kind == "hoarder" || s.kind == "juicer" || s.kind == "swine", "Unknown scenario primitive.");
                Need(s.damage >= 1 && s.damage <= 100 && s.minionCap >= 0 && s.minionCap <= 8 && s.helperCount >= 0 && s.helperCount <= 8 && s.constructionTotal >= 1 && s.constructionTotal <= 8 && s.barrierDurability >= 1 && s.barrierDurability <= 8, "Unbounded scenario rule.");
                var e = s.encounter;
                Need(e != null && Id(e.id) && !string.IsNullOrEmpty(e.label) && e.description != null && e.width >= 4 && e.height >= 4 && e.width <= 30 && e.height <= 30 && e.xp == 0, "Invalid scenario encounter.");
                Need(e.tiles != null && e.tiles.Length <= e.width * e.height && e.playerSpawns != null && e.playerSpawns.Length == data.partySize && e.enemies != null && e.enemies.Length >= 1 && e.enemies.Length <= 16, "Invalid scenario map arrays.");
                Func<int, int, bool> inside = (x, y) => x >= 0 && y >= 0 && x < e.width && y < e.height;
                var blocked = new System.Collections.Generic.HashSet<string>();
                var tiles = new System.Collections.Generic.HashSet<string>();
                var occupied = new System.Collections.Generic.HashSet<string>();
                var enemies = new System.Collections.Generic.HashSet<string>();
                foreach (var t in e.tiles)
                {
                    Need(t != null && inside(t.x, t.y) && tiles.Add(t.x + ":" + t.y) && t.tags != null, "Invalid scenario tile.");
                    foreach (var tag in t.tags)
                        Need(catalog.HasTag(tag), "Unknown scenario tag.");
                    if (t.blocked)
                        blocked.Add(t.x + ":" + t.y);
                }
                foreach (var p in e.playerSpawns)
                    Need(p != null && inside(p.x, p.y) && !blocked.Contains(p.x + ":" + p.y) && occupied.Add(p.x + ":" + p.y), "Invalid scenario player spawn.");
                foreach (var u in e.enemies)
                {
                    Need(u != null && Id(u.id) && !u.id.StartsWith("tile.", StringComparison.Ordinal) && !Array.Exists(data.roster, r => r.id == u.id) && enemies.Add(u.id) && !string.IsNullOrEmpty(u.label) && u.classId != null && catalog.Classes.ContainsKey(u.classId) && u.hp > 0 && u.hp <= 1000 && u.energy >= 0 && u.energy <= 100 && u.move >= 0 && u.move <= 10 && u.tags != null, "Invalid scenario enemy.");
                    Need(inside(u.x, u.y) && !blocked.Contains(u.x + ":" + u.y) && occupied.Add(u.x + ":" + u.y), "Invalid scenario enemy spawn.");
                    foreach (var tag in u.tags)
                        Need(catalog.HasTag(tag), "Unknown scenario enemy tag.");
                }
                Need(s.bossId != null && enemies.Contains(s.bossId) && s.minionIds != null && s.minionIds.Length <= 8, "Missing scenario boss or minion definitions.");
                var minions = new System.Collections.Generic.HashSet<string>();
                foreach (var id in s.minionIds)
                    Need(id != s.bossId && enemies.Contains(id) && minions.Add(id), "Invalid scenario minion.");
                Need(s.kind != "hoarder" || (s.minionCap > 0 && s.minionCap <= s.minionIds.Length), "Invalid Hoarder cap.");
                Need(s.route != null && s.route.Length <= 64 && s.interactables != null && s.interactables.Length <= 32, "Unbounded scenario objects.");
                var routeCells = new System.Collections.Generic.HashSet<string>();
                foreach (var c in s.route)
                    Need(c != null && inside(c.x, c.y) && !blocked.Contains(c.x + ":" + c.y) && routeCells.Add(c.x + ":" + c.y), "Invalid rolling route.");
                if (s.kind == "swine")
                {
                    Need(s.route.Length >= 4, "Rolling route is too short.");
                    for (int i = 0; i < s.route.Length; i++)
                    {
                        var a = s.route[i];
                        var b = s.route[(i + 1) % s.route.Length];
                        Need(Math.Abs(a.x - b.x) + Math.Abs(a.y - b.y) == 1, "Rolling route must be a contiguous loop.");
                    }
                    var boss = Array.Find(e.enemies, u => u.id == s.bossId);
                    Need(boss.x == s.route[0].x && boss.y == s.route[0].y, "Rolling boss must start on its route.");
                }
                var objects = new System.Collections.Generic.HashSet<string>();
                var objectCells = new System.Collections.Generic.HashSet<string>();
                foreach (var o in s.interactables)
                {
                    Need(o != null && Id(o.id) && objects.Add(o.id) && !string.IsNullOrEmpty(o.label) && o.description != null && inside(o.x, o.y) && !blocked.Contains(o.x + ":" + o.y) && !occupied.Contains(o.x + ":" + o.y) && objectCells.Add(o.x + ":" + o.y) && o.hp >= 1 && o.hp <= 10, "Invalid scenario interaction.");
                    Need(o.kind == "garbage" || o.kind == "cover" || o.kind == "parts" || o.kind == "barrier" || o.kind == "helper", "Unknown scenario interaction primitive.");
                    if (o.kind == "barrier")
                        Need(s.kind == "swine" && routeCells.Contains(o.x + ":" + o.y), "Barrier must lie on rolling route.");
                }
                var reached = new System.Collections.Generic.HashSet<string>();
                var queue = new System.Collections.Generic.Queue<CellView>();
                queue.Enqueue(e.playerSpawns[0]);
                reached.Add(e.playerSpawns[0].x + ":" + e.playerSpawns[0].y);
                while (queue.Count > 0)
                {
                    var c = queue.Dequeue();
                    int[] dx = { 0, -1, 1, 0 }, dy = { -1, 0, 0, 1 };
                    for (int i = 0; i < 4; i++)
                    {
                        int x = c.x + dx[i], y = c.y + dy[i];
                        if (inside(x, y) && !blocked.Contains(x + ":" + y) && reached.Add(x + ":" + y))
                            queue.Enqueue(new CellView { x = x, y = y });
                    }
                }
                foreach (var cell in occupied)
                    Need(reached.Contains(cell), "Disconnected scenario spawn.");
                foreach (var cell in objectCells)
                    Need(reached.Contains(cell), "Disconnected scenario interaction.");
                Need(s.decorations != null && s.decorations.Length <= 200, "Invalid scenario decoration array.");
                var decorIds = new System.Collections.Generic.HashSet<string>();
                foreach (var d in s.decorations)
                    Need(d != null && Id(d.id) && decorIds.Add(d.id) && !string.IsNullOrEmpty(d.assetId) && d.assetId.Length <= 80 && inside(d.x, d.y) && d.rotation >= 0 && d.rotation < 4 && !d.blocksMovement && (d.layer == "ground" || d.layer == "prop" || d.layer == "wall"), "Invalid scenario decoration.");
                if (s.kind == "swine")
                    Need(Array.Exists(s.interactables, o => o.kind == "parts") && Array.Exists(s.interactables, o => o.kind == "barrier") && Array.Exists(s.interactables, o => o.kind == "helper"), "Construction scenario requires parts, barrier and recovery helper.");
            }
        }
    }
}
