import assert from "node:assert/strict";
import { readFile, writeFile } from "node:fs/promises";
import { spawnSync } from "node:child_process";
import { fileURLToPath } from "node:url";
import { dirname, resolve } from "node:path";
const root = resolve(dirname(fileURLToPath(import.meta.url)), "..");
const read = (p) => readFile(resolve(root, p), "utf8");
const moduleURL = (s) =>
  `data:text/javascript;base64,${Buffer.from(s).toString("base64")}`;
const kitURL = moduleURL(await read("Web/wwwroot/room-kit.js"));
const kit = await import(kitURL);
const { generateDungeon, getPlayableMap } = await import(
  moduleURL(
    (await read("Web/wwwroot/procedural-map.js")).replace(
      /['"]\.\/room-kit\.js['"]/,
      JSON.stringify(kitURL),
    ),
  )
);
const manifest = JSON.parse(
  await read("Web/wwwroot/assets/room-kit/manifest.json"),
);
const rules = JSON.parse(
  await read("Web/wwwroot/assets/map-generation-rules.json"),
);
const content = JSON.parse(
  await read("UnityPackage/Runtime/Data/combat-content.json"),
);
const classes = new Set(content.classes.map((c) => c.id)),
  assets = new Map(manifest.assets.map((a) => [a.id, a]));
const key = (p) => `${p.x},${p.y}`;
let cases = 0;
const schemaMaps = [];
for (const [width, height] of [
  [6, 6],
  [8, 6],
  [10, 8],
  [14, 10],
  [20, 16],
])
  for (const layout of ["chambers", "cavern", "hall"])
    for (const biome of ["stone", "sewer", "crypt"])
      for (const density of [0, 0.4])
        for (let seed = 0; seed < 8; seed++) {
          const options = {
            width,
            height,
            layout,
            biome,
            density,
            seed: `test-${seed}`,
            roomCount: 2 + (seed % 5),
          };
          const room = generateDungeon(manifest, options, rules),
            before = JSON.stringify(room);
          assert.equal(
            JSON.stringify(generateDungeon(manifest, options, rules)),
            before,
          );
          const checked = kit.validateRoom(structuredClone(room), manifest),
            map = getPlayableMap(room, manifest);
          assert.equal(
            JSON.stringify(room),
            before,
            "validation/export never mutates source",
          );
          assert.deepEqual(
            map.tiles,
            kit.exportGameTiles(room, manifest).tiles,
          );
          assert.notEqual(key(room.start), key(room.exit), "entrance and exit are distinct");
          assert.deepEqual(room.entrance, room.start);
          assert.deepEqual(room.doors, [{...room.start,kind:"entrance"},{...room.exit,kind:"exit"}]);
          for (const [point,kind] of [[room.start,"entrance"],[room.exit,"exit-door"],[room.exit,"exit"]]) {
            const marker = room.placements.find((p) => p.kind===kind && key(p)===key(point));
            assert.ok(marker, `visible canonical ${kind} placement exists`);
            assert.equal(marker.blocksMovement,false);
            assert.ok(room.generation.protectedCells.some((p) => key(p)===key(point)));
            assert.ok(!room.enemies.some((p) => key(p)===key(point)));
          }
          assert.ok(!room.playerSpawns.some((p) => key(p)===key(room.exit)));
          assert.ok(room.placements.every((p) => p.rotation===0), "native art never receives random rotations");
          assert.ok(new Set(room.rooms.map((r) => r.theme.id)).size >= 2, "rooms offer distinct material themes");
          const themeIds = new Set(room.rooms.map((r) => r.theme.id));
          for (const p of room.placements.filter((p) => p.roomId)) {
            assert.ok(themeIds.has(p.themeId));
            assert.equal(p.layer,"floor");
            assert.ok(p.material.length);
          }
          const blocked = new Set(room.blockedCells.map(key)),
            slots = new Set(),
            spawnKeys = new Set();
          for (let y = 0; y < height; y++)
            for (let x = 0; x < width; x++)
              if (!x || !y || x === width - 1 || y === height - 1)
                assert.ok(blocked.has(`${x},${y}`));
          for (const p of room.placements) {
            const asset = assets.get(p.assetId);
            assert.ok(asset);
            assert.equal(asset.layer, p.layer);
            assert.equal(asset.blocksMovement, p.blocksMovement);
            const slot = `${key(p)}:${p.layer}`;
            assert.ok(!slots.has(slot), "one component per layer/cell");
            slots.add(slot);
          }
          const queue = [room.start],
            seen = new Set(queue.map(key));
          for (let i = 0; i < queue.length; i++)
            for (const [dx, dy] of [
              [1, 0],
              [-1, 0],
              [0, 1],
              [0, -1],
            ]) {
              const n = { x: queue[i].x + dx, y: queue[i].y + dy };
              if (
                n.x >= 0 &&
                n.y >= 0 &&
                n.x < width &&
                n.y < height &&
                !blocked.has(key(n)) &&
                !seen.has(key(n))
              ) {
                seen.add(key(n));
                queue.push(n);
              }
            }
          assert.equal(
            seen.size,
            width * height - blocked.size,
            "every free cell is connected",
          );
          assert.ok(
            checked.clearRoute.length &&
              room.rooms.length >= 2 &&
              room.rooms.length <= options.roomCount,
          );
          assert.equal(room.corridors.length, room.rooms.length - 1);
          for (let i = 0; i < room.rooms.length; i++)
            for (let j = i + 1; j < room.rooms.length; j++) {
              const a = room.rooms[i],
                b = room.rooms[j];
              assert.ok(
                a.x + a.width <= b.x ||
                  b.x + b.width <= a.x ||
                  a.y + a.height <= b.y ||
                  b.y + b.height <= a.y,
              );
            }
          assert.equal(map.playerSpawns.length, 4);
          assert.equal(map.enemies.length, 3);
          for (const p of [...map.playerSpawns, ...map.enemies]) {
            assert.ok(seen.has(key(p)));
            assert.ok(!spawnKeys.has(key(p)));
            spawnKeys.add(key(p));
            assert.ok(
              !map.tiles.some((t) => key(t) === key(p) && t.tags.length),
            );
          }
          for (const e of map.enemies) {
            assert.ok(e.id.startsWith("custom.enemy."));
            assert.ok(classes.has(e.classId));
            assert.equal(e.artId, "rat");
            assert.ok(e.hp > 0 && e.move > 0);
          }
          for (const p of room.generation.protectedCells)
            assert.ok(
              !map.tiles.some(
                (t) => key(t) === key(p) && (t.blocked || t.tags.length),
              ),
            );
          for (let q = 0; q < 4; q++)
            for (const p of [...room.playerSpawns, room.exit]) {
              const screen = kit.projectCell(p.x, p.y, q);
              assert.deepEqual(kit.pickCell(screen.x, screen.y, q), {
                x: p.x,
                y: p.y,
              });
            }
          schemaMaps.push(map);
          cases++;
        }
const a = generateDungeon(manifest, { seed: "one" }),
  b = generateDungeon(manifest, { seed: "two" });
assert.notEqual(JSON.stringify(a.placements), JSON.stringify(b.placements));
for (const options of [
  { width: 5 },
  { height: 17 },
  { width: "12" },
  { density: NaN },
  { density: 0.41 },
  { layout: "bad" },
  { biome: "bad" },
  { roomCount: 7 },
  { seed: 42 },
  null,
])
  assert.throws(() => generateDungeon(manifest, options));
assert.throws(() => generateDungeon(manifest, {}, {}));
const invalidThemes = structuredClone(rules);
invalidThemes.biomes.stone.themes = [];
assert.throws(() => generateDungeon(manifest, {}, invalidThemes), /theme/);
console.log(
  `PASS ${cases} procedural maps: deterministic seeds, all-cell connectivity, solid boundaries, canonical placements, runtime spawn records, dry paths, explicit walkable portals, varied room materials and four camera rotations.`,
);

const longSeedMap = getPlayableMap(
  generateDungeon(manifest, { seed: "x".repeat(120), width: 20, height: 16 }),
  manifest,
);
assert.equal(longSeedMap.label.length, 100);
assert.ok(
  longSeedMap.placements.every(
    (p) =>
      Object.keys(p).join(",") ===
      "id,assetId,layer,x,y,rotation,blocksMovement",
  ),
);
schemaMaps.push(longSeedMap);
const validation = spawnSync(
  "python3",
  [
    "-c",
    "import json,sys,jsonschema; schema=json.load(open('Tools/custom-map.schema.json')); validator=jsonschema.Draft202012Validator(schema); [validator.validate(m) for m in json.load(sys.stdin)]",
  ],
  {
    cwd: root,
    input: JSON.stringify(schemaMaps),
    encoding: "utf8",
    maxBuffer: 1024 * 1024,
  },
);
assert.equal(
  validation.status,
  0,
  `Generated runtime exports must pass actual custom-map schema: ${validation.stderr}`,
);
await writeFile(
  "/tmp/dct-procedural-runtime-map.json",
  JSON.stringify(longSeedMap, null, 2) + "\n",
);
console.log(
  "PASS 721 actual custom-map JSON Schema validations, 120-character seeds and strict placement properties. Runtime fixture: /tmp/dct-procedural-runtime-map.json",
);

// The zero-density map makes every wall/open adjacency explicit and stable.
const orientationRoom = generateDungeon(manifest, {
  seed: "wall-orientation",
  width: 14,
  height: 10,
  density: 0,
});
const orientationBlocked = new Set(orientationRoom.blockedCells.map(key));
const walkable = (x, y) =>
  x >= 0 &&
  y >= 0 &&
  x < orientationRoom.width &&
  y < orientationRoom.height &&
  !orientationBlocked.has(`${x},${y}`);
let exposedWalls = 0;
for (const p of orientationRoom.placements.filter((p) => p.kind === "wall")) {
  const east = walkable(p.x + 1, p.y),
    south = walkable(p.x, p.y + 1),
    west = walkable(p.x - 1, p.y),
    north = walkable(p.x, p.y - 1);
  const direction =
    east && south
      ? "corner"
      : east
        ? "nw"
        : south
          ? "ne"
          : west
            ? "nw"
            : north
              ? "ne"
              : p.x === 0 || p.x === orientationRoom.width - 1
                ? "nw"
                : "ne";
  assert.ok(
    assets.get(p.assetId).tags.includes(direction),
    "wall face follows adjacent walkable cells or a consistent boundary axis",
  );
  if (east || south) exposedWalls++;
  if (p.assetId === "wall-corner")
    assert.ok(east && south, "corners only join two exposed faces");
}
assert.ok(exposedWalls > 0);
console.log(
  "PASS wall orientations follow exposed east/south faces and continuous boundary axes.",
);
