import {
  validateManifest,
  seededRandom,
  findRoute,
  exportGameTiles,
} from "./room-kit.js";

const key = (p) => `${p.x},${p.y}`;
const neighbors = (p) =>
  [
    [1, 0],
    [-1, 0],
    [0, 1],
    [0, -1],
  ].map(([dx, dy]) => ({ x: p.x + dx, y: p.y + dy }));
const DEFAULT_RULES = {
  schemaVersion: 1,
  biomes: {
    stone: {
      floorTags: ["stone"],
      surfaceTags: ["grate"],
      propTags: ["crate", "pillar", "rubble"],
      detailTags: ["moss"],
    },
    sewer: {
      floorTags: ["stone"],
      surfaceTags: ["water", "grate"],
      propTags: ["barrel", "crate"],
      detailTags: ["moss"],
    },
    crypt: {
      floorTags: ["stone"],
      surfaceTags: ["grate"],
      propTags: ["pillar", "chest", "rubble"],
      detailTags: ["moss"],
    },
  },
};

/** Seeded authoring only: combat remains in the shared C# runtime. Inputs are never modified. */
export function generateDungeon(manifest, options = {}, rules = DEFAULT_RULES) {
  validateManifest(manifest);
  if (!options || typeof options !== "object" || Array.isArray(options))
    throw new Error("Options must be an object.");
  const integer = (name, fallback, min, max) => {
    const n = options[name] ?? fallback;
    if (!Number.isInteger(n) || n < min || n > max)
      throw new Error(`${name} must be an integer from ${min} to ${max}.`);
    return n;
  };
  const width = integer("width", 14, 6, 20),
    height = integer("height", 10, 6, 16),
    requestedRooms = integer("roomCount", 4, 2, 6);
  const density = options.density ?? 0.2,
    seed = options.seed ?? "crawler-13",
    layout = options.layout ?? "chambers",
    biome = options.biome ?? "stone";
  if (
    typeof seed !== "string" ||
    seed.length > 120 ||
    !Number.isFinite(density) ||
    density < 0 ||
    density > 0.4 ||
    !["chambers", "cavern", "hall"].includes(layout) ||
    !["stone", "sewer", "crypt"].includes(biome)
  )
    throw new Error("Invalid seed, density, layout or biome.");
  const rule = rules?.schemaVersion === 1 && rules.biomes?.[biome];
  if (
    !rule ||
    !["floorTags", "surfaceTags", "propTags", "detailTags"].every(
      (n) =>
        Array.isArray(rule[n]) && rule[n].every((t) => typeof t === "string"),
    )
  )
    throw new Error("Invalid biome rules.");
  const random = seededRandom(seed),
    pick = (a) => a[Math.floor(random() * a.length)];
  // Only the canonical runtime kit is accepted; a different manifest needs its own runtime adapter.
  const canonical = new Set([
    "wall-ne",
    "wall-nw",
    "wall-corner",
    "pillar",
    "door-closed-nw",
    "door-open-nw",
    "door-closed-ne",
    "door-open-ne",
    "torch",
    "lever",
    "grate",
    "oil-overlay",
    "water-overlay",
    "moss",
    "rubble",
    "stairs",
    "stone-a",
    "stone-b",
    "water-floor",
    "oil-floor",
    "crate",
    "barrel",
    "chest",
    "exit",
    "fire-overlay",
  ]);
  const assets = manifest.assets.filter(
    (a) =>
      canonical.has(a.id) &&
      a.footprint.width === 1 &&
      a.footprint.height === 1,
  );
  const pool = (layer, tags) =>
    assets.filter(
      (a) => a.layer === layer && a.tags.some((t) => tags.includes(t)),
    );
  const floors = pool("floor", rule.floorTags).filter(
      (a) =>
        !a.blocksMovement &&
        !a.tags.some((t) => ["water", "oil", "burning"].includes(t)),
    ),
    walls = pool("structure", ["wall"]).filter((a) => a.blocksMovement);
  if (!floors.length || !walls.length)
    throw new Error("Canonical dry floors and blocking walls are required.");
  const leaves = [{ x: 1, y: 1, width: width - 2, height: height - 2 }];
  while (leaves.length < requestedRooms) {
    const candidates = leaves
      .filter((r) => r.width >= 4 || r.height >= 4)
      .sort((a, b) => b.width * b.height - a.width * a.height);
    if (!candidates.length) break;
    const r = candidates[0],
      vertical =
        r.width >= 4 &&
        (r.height < 4 ||
          (layout === "hall"
            ? r.width >= r.height
            : r.width / r.height > 0.8 + random() * 0.4));
    const length = vertical ? r.width : r.height,
      min = length >= 5 ? 2 : 1,
      cut = min + Math.floor(random() * (length - 2 * min));
    const a = { ...r },
      b = { ...r };
    if (vertical) {
      a.width = cut;
      b.x += cut + 1;
      b.width -= cut + 1;
    } else {
      a.height = cut;
      b.y += cut + 1;
      b.height -= cut + 1;
    }
    leaves.splice(leaves.indexOf(r), 1, a, b);
  }
  const open = new Set(),
    carve = (p) => open.add(key(p));
  const rooms = leaves.map((r, i) => {
    const room = { id: `room.${i}`, ...r };
    if (layout === "hall" && room.width > 3) {
      room.x++;
      room.width -= 2;
    }
    room.center = {
      x: room.x + Math.floor((room.width - 1) / 2),
      y: room.y + Math.floor((room.height - 1) / 2),
    };
    for (let y = room.y; y < room.y + room.height; y++)
      for (let x = room.x; x < room.x + room.width; x++) carve({ x, y });
    return room;
  });
  const corridors = [];
  for (let i = 1; i < rooms.length; i++) {
    const a = rooms[i - 1].center,
      b = rooms[i].center,
      cells = [],
      p = { ...a };
    const horizontal = random() < 0.5;
    const walk = (axis) => {
      while (p[axis] !== b[axis]) {
        p[axis] += Math.sign(b[axis] - p[axis]);
        cells.push({ ...p });
        carve(p);
      }
    };
    cells.push({ ...p });
    walk(horizontal ? "x" : "y");
    walk(horizontal ? "y" : "x");
    corridors.push({ from: rooms[i - 1].id, to: rooms[i].id, cells });
  }
  if (layout === "cavern")
    for (let pass = 0; pass < 2; pass++) {
      const additions = [];
      for (let y = 1; y < height - 1; y++)
        for (let x = 1; x < width - 1; x++) {
          const p = { x, y };
          if (
            !open.has(key(p)) &&
            neighbors(p).filter((n) => open.has(key(n))).length >= 2 &&
            random() < 0.45
          )
            additions.push(p);
        }
      additions.forEach(carve);
    }
  const cells = [...open]
    .map((k) => {
      const [x, y] = k.split(",").map(Number);
      return { x, y };
    })
    .sort((a, b) => a.y - b.y || a.x - b.x);
  if (cells.length < 7)
    throw new Error("Layout does not have enough spawn space.");
  const start = { ...rooms[0].center },
    exit = { ...rooms.at(-1).center };
  const distance = (p) => Math.abs(p.x - start.x) + Math.abs(p.y - start.y);
  const ordered = [...cells].sort(
      (a, b) => distance(a) - distance(b) || a.y - b.y || a.x - b.x,
    ),
    playerSpawns = ordered.slice(0, 4).map((p) => ({ ...p }));
  const used = new Set(playerSpawns.map(key));
  const enemies = ordered
    .slice()
    .reverse()
    .filter((p) => !used.has(key(p)))
    .slice(0, 3)
    .map((p, i) => ({
      id: `custom.enemy.generated${i}`,
      label: ["Maintenance Rat", "Coolant Rat", "Security Sentry"][i],
      classId: ["class.brawler", "class.rogue", "class.ranger"][i],
      artId: "rat",
      ...p,
      hp: i === 2 ? 20 : 18,
      energy: 12,
      move: 3,
      tags: [],
    }));
  const blocked = () => {
    const result = [];
    for (let y = 0; y < height; y++)
      for (let x = 0; x < width; x++)
        if (!open.has(`${x},${y}`)) result.push({ x, y });
    return result;
  };
  const geometry = { width, height, start, exit, blockedCells: blocked() };
  const clearRoute = findRoute(geometry),
    protectedCells = new Set(
      [
        ...clearRoute,
        ...playerSpawns,
        ...enemies,
        ...corridors.flatMap((c) => c.cells),
      ].map(key),
    );
  // Reserve a dry connected route to every spawn and room center before any decoration.
  for (const p of [...playerSpawns, ...enemies, ...rooms.map((r) => r.center)])
    for (const step of findRoute(geometry, start, p))
      protectedCells.add(key(step));
  const placements = [],
    add = (a, p, kind) =>
      placements.push({
        id: `placement.${placements.length}`,
        assetId: a.id,
        layer: a.layer,
        x: p.x,
        y: p.y,
        rotation: 0,
        blocksMovement: a.blocksMovement,
        ...(kind ? { kind } : {}),
      });
  const props = pool("prop", rule.propTags).filter(
      (a) => !a.tags.includes("exit"),
    ),
    surfaces = pool("surface", rule.surfaceTags).filter(
      (a) => !a.blocksMovement,
    ),
    details = pool("overlay", rule.detailTags).filter((a) => !a.blocksMovement);
  const connected = () => {
    const seen = new Set([key(start)]),
      queue = [start];
    for (let i = 0; i < queue.length; i++)
      for (const n of neighbors(queue[i]))
        if (open.has(key(n)) && !seen.has(key(n))) {
          seen.add(key(n));
          queue.push(n);
        }
    return seen.size === open.size;
  };
  for (let y = 0; y < height; y++)
    for (let x = 0; x < width; x++) {
      const p = { x, y },
        k = key(p);
      add(pick(floors), p);
      if (!open.has(k)) {
        add(pick(walls), p, "wall");
        continue;
      }
      if (protectedCells.has(k)) continue;
      if (random() < density && props.length) {
        const a = pick(props);
        if (a.blocksMovement) {
          open.delete(k);
          if (!connected()) {
            open.add(k);
            continue;
          }
        }
        add(a, p, "decoration");
      } else if (random() < density && surfaces.length) add(pick(surfaces), p);
      else if (random() < density && details.length) add(pick(details), p);
    }
  // Match wall faces to the final walkable geometry. Corners belong only at
  // intersections of two exposed faces, never at arbitrary filled rock cells.
  const wallByTag = new Map(
    ["nw", "ne", "corner"].map((tag) => [
      tag,
      walls.find((a) => a.tags.includes(tag)),
    ]),
  );
  for (const placement of placements.filter((p) => p.kind === "wall")) {
    const { x, y } = placement;
    const eastOpen = open.has(`${x + 1},${y}`);
    const southOpen = open.has(`${x},${y + 1}`);
    const westOpen = open.has(`${x - 1},${y}`);
    const northOpen = open.has(`${x},${y - 1}`);
    const direction =
      eastOpen && southOpen
        ? "corner"
        : eastOpen
          ? "nw"
          : southOpen
            ? "ne"
            : westOpen
              ? "nw"
              : northOpen
                ? "ne"
                : x === 0 || x === width - 1
                  ? "nw"
                  : "ne";
    placement.assetId = (wallByTag.get(direction) || walls[0]).id;
  }
  const marker = assets.find(
    (a) => a.tags.includes("stairs") && !a.blocksMovement,
  );
  if (marker) add(marker, exit, "exit");
  return {
    schemaVersion: 1,
    kind: "dungeon-room-authoring",
    manifest: "assets/room-kit/manifest.json",
    seed,
    width,
    height,
    density,
    layout,
    biome,
    tile: { ...manifest.tile },
    start,
    exit,
    doors: [],
    clearRoute,
    blockedCells: blocked(),
    placements,
    rooms,
    corridors,
    playerSpawns,
    enemies,
    generation: {
      version: 1,
      algorithm: "partition-chain",
      requestedRooms,
      roomCount: rooms.length,
      protectedCells: [...protectedCells].map((k) => {
        const [x, y] = k.split(",").map(Number);
        return { x, y };
      }),
    },
  };
}

export function getPlayableMap(room, manifest) {
  return {
    schemaVersion: 1,
    label: `Generated ${room.biome} / ${room.seed}`.slice(0, 100),
    ...exportGameTiles(room, manifest),
    placements: room.placements.map(
      ({ id, assetId, layer, x, y, rotation = 0, blocksMovement }) => ({
        id,
        assetId,
        layer,
        x,
        y,
        rotation,
        blocksMovement,
      }),
    ),
    playerSpawns: structuredClone(room.playerSpawns),
    enemies: structuredClone(room.enemies),
  };
}
