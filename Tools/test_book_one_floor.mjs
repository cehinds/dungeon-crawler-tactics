import assert from "node:assert/strict";
import fs from "node:fs";
import {
  generateBookOneFloor,
  validateBookOneFloor,
  getBookOneRegionPlayable,
  createBookOneExploration,
  moveBookOneExplorer,
  visitBookOneObjective,
  travelBookOnePortal,
  restoreBookOneExploration,
} from "../Web/wwwroot/book-one-floor.js";
const read = (p) =>
  JSON.parse(fs.readFileSync(new URL(p, import.meta.url), "utf8"));
const library = read("../Web/wwwroot/assets/top-down-object-kit/manifest.json"),
  rules = read("../Web/wwwroot/data/procedural-object-room-rules.json"),
  manifest = read("../Web/wwwroot/assets/room-kit/manifest.json");
const catalog = read("../Web/wwwroot/data/book-one-floor-one.json");
const snapshot = JSON.stringify({ library, rules, manifest, catalog });
const floor = generateBookOneFloor(
  library,
  { seed: "floor-one-behavior" },
  rules,
  manifest,
  catalog,
);
assert.deepEqual(
  generateBookOneFloor(library, { seed: floor.seed }, rules, manifest, catalog),
  floor,
  "Seed reproduces entire serialized floor",
);
assert.equal(
  validateBookOneFloor(JSON.parse(JSON.stringify(floor)), library).valid,
  true,
);
assert.equal(
  JSON.stringify({ library, rules, manifest, catalog }),
  snapshot,
  "Generation leaves authored sources untouched",
);
const other = generateBookOneFloor(
  library,
  { seed: "floor-one-alternate" },
  rules,
  manifest,
  catalog,
);
assert.notDeepEqual(
  other.regions[0].map.blockedCells,
  floor.regions[0].map.blockedCells,
  "Seeds change local layout",
);
assert.deepEqual(other.links, floor.links, "Seeds preserve authored topology");
function approach(state, point) {
  const map = floor.regions.find((r) => r.id === state.regionId).map,
    open = new Set(
      map.cells.filter((c) => !c.blocked).map((c) => `${c.x},${c.y}`),
    );
  const queue = [state.position],
    parent = new Map([[`${state.position.x},${state.position.y}`, null]]);
  let destination;
  for (let i = 0; i < queue.length; i++) {
    const p = queue[i];
    if (Math.abs(p.x - point.x) + Math.abs(p.y - point.y) <= 1) {
      destination = p;
      break;
    }
    for (const [dx, dy] of [
      [1, 0],
      [-1, 0],
      [0, 1],
      [0, -1],
    ]) {
      const q = { x: p.x + dx, y: p.y + dy },
        k = `${q.x},${q.y}`;
      if (open.has(k) && !parent.has(k)) {
        parent.set(k, p);
        queue.push(q);
      }
    }
  }
  assert(destination, "Marker has a reachable approach");
  const path = [];
  for (
    let p = destination;
    parent.get(`${p.x},${p.y}`);
    p = parent.get(`${p.x},${p.y}`)
  )
    path.push(p);
  for (const p of path.reverse()) state = moveBookOneExplorer(floor, state, p);
  return state;
}
let state = createBookOneExploration(floor);
assert.equal(state.complete, false);
assert.throws(() => moveBookOneExplorer(floor, state, { x: -1, y: -1 }));
assert.throws(() =>
  restoreBookOneExploration(floor, { ...state, seed: "different" }),
);
// A reachable doorway still rejects travel until its authored discovery is visited.
const firstPortal = floor.regions.find((r) => r.id === state.regionId)
  .portals[0];
let gated = travelBookOnePortal(
  floor,
  approach(state, firstPortal),
  firstPortal.id,
);
const locked = floor.regions
  .find((r) => r.id === gated.regionId)
  .portals.find(
    (p) =>
      floor.links.find((l) => l.id === p.linkId).requiredObjectiveIds.length,
  );
assert(locked);
gated = approach(gated, locked);
assert.throws(
  () => travelBookOnePortal(floor, gated, locked.id),
  /required route markers/,
);
// Traverse reachable passages, checking gates at each step and discovering only by walking.
const visited = new Set();
function explore(regionId) {
  let region = floor.regions.find((r) => r.id === regionId);
  state = approach(state, region.objectivePoint);
  state = visitBookOneObjective(floor, state);
  visited.add(regionId);
  for (const portal of region.portals) {
    if (visited.has(portal.targetRegionId)) continue;
    const link = floor.links.find((l) => l.id === portal.linkId);
    if (
      !link.requiredObjectiveIds.every((id) =>
        state.completedObjectiveIds.includes(id),
      )
    )
      continue;
    state = approach(state, portal);
    const old = JSON.stringify(state);
    state = travelBookOnePortal(floor, state, portal.id);
    assert.notEqual(JSON.stringify(state), old);
    explore(portal.targetRegionId);
    const arrival = floor.regions
      .find((r) => r.id === state.regionId)
      .portals.find((p) => p.linkId === portal.linkId);
    state = approach(state, arrival);
    state = travelBookOnePortal(floor, state, arrival.id);
  }
}
// Repeat exploration as other branches unlock additional gates.
for (let pass = 0; pass < floor.regions.length; pass++)
  explore(floor.entryRegionId);
assert.equal(
  visited.size,
  floor.regions.filter((r) => r.physicalRegion !== false).length,
  "Every authored region is traversable through actual marker interactions",
);
assert.equal(new Set(state.completedObjectiveIds).size, floor.regions.length);
// Walk the now-unlocked graph to the descent marker, then complete the atlas route.
const routes = [[state.regionId]],
  routeSeen = new Set([state.regionId]);
let exitRoute;
for (let i = 0; i < routes.length; i++) {
  const route = routes[i],
    id = route.at(-1);
  if (id === floor.exitRegionId) {
    exitRoute = route;
    break;
  }
  for (const p of floor.regions.find((r) => r.id === id).portals)
    if (!routeSeen.has(p.targetRegionId)) {
      routeSeen.add(p.targetRegionId);
      routes.push([...route, p.targetRegionId]);
    }
}
for (const id of exitRoute.slice(1)) {
  const p = floor.regions
    .find((r) => r.id === state.regionId)
    .portals.find((p) => p.targetRegionId === id);
  state = travelBookOnePortal(floor, approach(state, p), p.id);
}
state = visitBookOneObjective(
  floor,
  approach(
    state,
    floor.regions.find((r) => r.id === state.regionId).objectivePoint,
  ),
);
assert.equal(state.complete, true);

assert.deepEqual(
  restoreBookOneExploration(floor, JSON.parse(JSON.stringify(state))),
  state,
  "Serializable progress resumes exactly",
);
for (const report of floor.regions.filter((r) => r.physicalRegion === false)) {
  assert.equal(
    report.anchorRegionId,
    "tutorial-guildhall",
    "Reported rest stops stay anchored to the guild briefing",
  );
  assert.equal(report.map, null);
  assert.equal(report.objectivePoint, null);
  assert.deepEqual(report.portals, []);
  assert.throws(
    () => getBookOneRegionPlayable(floor, report.id),
    /no playable room/,
  );
  assert(
    !floor.regions.some((r) =>
      r.portals.some((p) => p.targetRegionId === report.id),
    ),
  );
}
for (const region of floor.regions.filter((r) => r.physicalRegion !== false)) {
  const playable = getBookOneRegionPlayable(floor, region.id);
  assert.equal(playable.width, 20);
  assert.equal(playable.height, 16);
  assert(playable.tiles.length);
  const blocked = new Set(
    playable.tiles.filter((t) => t.blocked).map((t) => `${t.x},${t.y}`),
  );
  for (const cell of region.map.cells)
    assert.equal(
      blocked.has(`${cell.x},${cell.y}`),
      cell.blocked,
      "Handoff collision agrees with exploration",
    );
}
const broken = structuredClone(floor);
broken.regions[0].portals[0].targetRegionId = "missing";
assert.equal(validateBookOneFloor(broken, library).valid, false);
const deadlocked = structuredClone(catalog);
deadlocked.links = deadlocked.links.map((l) => ({
  ...l,
  requiredObjectiveIds: [
    deadlocked.regions.find((r) => r.id === deadlocked.exitRegionId).objective
      .id,
  ],
}));
assert.throws(
  () => generateBookOneFloor(library, {}, rules, manifest, deadlocked),
  /deadlock/,
);
console.log(
  `Book 1 Floor 1: ${floor.regions.filter((r) => r.physicalRegion !== false).length} physical maps + ${floor.regions.filter((r) => r.physicalRegion === false).length} report records, ${floor.links.length} reciprocal passages; deterministic generation, traversal, gates, resume and collision handoff passed.`,
);
