import {
  generateWholeObjectMap,
  validateWholeObjectMap,
  exportWholeObjectGameMap,
} from "./whole-object-map.js";

const copy = (value) => structuredClone(value);
const renderTheme = (theme) =>
  ({
    "safe-rest": "safe-rest",
    guild: "guild",
    "goblin-industrial": "machinery",
    gym: "machinery",
    "boss-complex": "machinery",
  })[theme] ?? "guild";
const key = (p) => `${p.x},${p.y}`;
const distance = (a, b) => Math.abs(a.x - b.x) + Math.abs(a.y - b.y);
const regionOf = (floor, id) => {
  const region = floor.regions.find((r) => r.id === id);
  if (!region) throw new Error("Unknown Floor 1 region.");
  return region;
};
const open = (map, p) =>
  Number.isInteger(p?.x) &&
  Number.isInteger(p?.y) &&
  Array.isArray(map?.cells) &&
  map.cells.some((c) => c.x === p.x && c.y === p.y && !c.blocked);

/** The topology is authored adaptation data; room geometry reuses the existing Foundry. */
export function generateBookOneFloor(
  library,
  options = {},
  rules,
  manifest,
  catalog,
) {
  validateCatalog(catalog);
  const seed = options.seed ?? "book-one-floor-one";
  if (typeof seed !== "string" || !seed.trim() || seed.length > 80)
    throw new Error("Floor seed must contain 1–80 characters.");
  const floor = {
    ...copy(catalog),
    kind: "book-one-floor",
    generationVersion: 1,
    seed,
    regions: [],
  };
  for (const definition of catalog.regions) {
    if (definition.physicalRegion === false) {
      const link = catalog.links.find(
        (l) => l.from === definition.id || l.to === definition.id,
      );
      floor.regions.push({
        ...copy(definition),
        anchorRegionId: link.from === definition.id ? link.to : link.from,
        map: null,
        objectivePoint: null,
        portals: [],
      });
      continue;
    }
    const map = generateWholeObjectMap(
      library,
      {
        seed: `${seed}:${definition.id}`.slice(0, 120),
        theme: renderTheme(definition.theme),
        width: 20,
        height: 16,
        roomCount: 3,
      },
      rules,
      manifest,
    );
    const candidates = [...map.clearRoute, ...map.reservedCells].filter((p) =>
      open(map, p),
    );
    const used = new Set();
    const choose = (preferred) => {
      const p = [preferred, ...candidates].find((p) => p && !used.has(key(p)));
      if (!p) throw new Error("Not enough reachable region markers.");
      used.add(key(p));
      return copy(p);
    };
    const objectivePoint = choose(map.rooms.at(-1).center);
    const incident = catalog.links.filter(
      (l) =>
        (l.from === definition.id || l.to === definition.id) &&
        catalog.regions.find(
          (r) => r.id === (l.from === definition.id ? l.to : l.from),
        ).physicalRegion !== false,
    );
    const portals = incident.map((link, index) => ({
      id: `${definition.id}:${link.id}`,
      linkId: link.id,
      targetRegionId: link.from === definition.id ? link.to : link.from,
      ...choose(index === 0 ? map.entrance : map.exit),
    }));
    floor.regions.push({ ...copy(definition), map, objectivePoint, portals });
  }
  const validation = validateBookOneFloor(floor, library);
  if (!validation.valid) throw new Error(validation.errors.join(" "));
  return floor;
}

function validateCatalog(catalog) {
  if (
    catalog?.schemaVersion !== 1 ||
    !Array.isArray(catalog.regions) ||
    catalog.regions.length < 2 ||
    catalog.regions.length > 30 ||
    !Array.isArray(catalog.links)
  )
    throw new Error("Unsupported Book 1 region catalog.");
  const ids = new Set(),
    objectives = new Set(),
    links = new Set();
  for (const r of catalog.regions) {
    if (
      typeof r.id !== "string" ||
      !r.id ||
      ids.has(r.id) ||
      typeof r.theme !== "string" ||
      !r.objective?.id ||
      objectives.has(r.objective.id)
    )
      throw new Error("Invalid or duplicate region/objective.");
    ids.add(r.id);
    objectives.add(r.objective.id);
  }
  if (
    catalog.regions.some(
      (r) =>
        r.physicalRegion === false &&
        (!r.optional ||
          catalog.links.filter((l) => l.from === r.id || l.to === r.id)
            .length !== 1),
    )
  )
    throw new Error("Reports require one host and must remain optional.");
  if (
    catalog.regions.some(
      (r) =>
        r.physicalRegion === false &&
        (r.id === catalog.entryRegionId || r.id === catalog.exitRegionId),
    )
  )
    throw new Error("Reports cannot be entrances or exits.");
  if (!ids.has(catalog.entryRegionId) || !ids.has(catalog.exitRegionId))
    throw new Error("Missing floor entry or exit.");
  for (const l of catalog.links) {
    if (
      !l.id ||
      links.has(l.id) ||
      !ids.has(l.from) ||
      !ids.has(l.to) ||
      l.from === l.to ||
      !Array.isArray(l.requiredObjectiveIds) ||
      l.requiredObjectiveIds.some((id) => !objectives.has(id))
    )
      throw new Error("Invalid floor link or objective gate.");
    links.add(l.id);
  }
  // Prove objective gates can be satisfied from the entrance, not merely that edges connect.
  const reached = new Set([catalog.entryRegionId]),
    done = new Set();
  let changed = true;
  while (changed) {
    changed = false;
    for (const r of catalog.regions)
      if (reached.has(r.id)) done.add(r.objective.id);
    for (const l of catalog.links)
      if (l.requiredObjectiveIds.every((id) => done.has(id))) {
        if (reached.has(l.from) && !reached.has(l.to)) {
          reached.add(l.to);
          changed = true;
        }
        if (reached.has(l.to) && !reached.has(l.from)) {
          reached.add(l.from);
          changed = true;
        }
      }
  }
  if (reached.size !== ids.size)
    throw new Error(
      "Floor graph is disconnected or its objective gates deadlock.",
    );
}

export function validateBookOneFloor(floor, library) {
  const errors = [];
  try {
    validateCatalog(floor);
  } catch (error) {
    return { valid: false, errors: [error.message] };
  }
  if (
    floor.kind !== "book-one-floor" ||
    floor.generationVersion !== 1 ||
    typeof floor.seed !== "string"
  )
    errors.push("Unsupported realized floor.");
  for (const region of floor.regions) {
    if (region.physicalRegion === false) {
      const host = floor.regions.find((r) => r.id === region.anchorRegionId);
      if (
        region.map !== null ||
        region.objectivePoint !== null ||
        region.portals?.length !== 0 ||
        !host ||
        host.physicalRegion === false
      )
        errors.push("Reports must be anchored metadata without a room.");
      continue;
    }
    let result;
    try {
      result = validateWholeObjectMap(region.map, library);
    } catch {
      result = { valid: false, errors: ["Malformed regional map."] };
    }
    if (!result.valid) {
      errors.push(`${region.id}: ${result.errors.join(" ")}`);
      continue;
    }
    const incident = floor.links.filter(
      (l) =>
        (l.from === region.id || l.to === region.id) &&
        regionOf(floor, l.from === region.id ? l.to : l.from).physicalRegion !==
          false,
    );
    if (
      !Array.isArray(region.portals) ||
      region.portals.length !== incident.length
    ) {
      errors.push("Region portals disagree with graph.");
      continue;
    }
    const used = new Set();
    for (const p of [region.objectivePoint, ...region.portals]) {
      if (!open(region.map, p) || used.has(key(p)))
        errors.push("Blocked or overlapping floor marker.");
      used.add(key(p));
    }
    for (const l of incident) {
      const p = region.portals.find((p) => p.linkId === l.id);
      if (
        !p ||
        p.targetRegionId !== (l.from === region.id ? l.to : l.from) ||
        p.id !== `${region.id}:${l.id}`
      )
        errors.push("Invalid reciprocal portal.");
    }
  }
  return { valid: errors.length === 0, errors: [...new Set(errors)] };
}

export function getBookOneRegionPlayable(floor, regionId) {
  const region = regionOf(floor, regionId);
  if (region.physicalRegion === false)
    throw new Error("Reported locations have no playable room.");
  const map = exportWholeObjectGameMap(region.map);
  map.label = `Book 1 / Floor 1 / ${region.label}`.slice(0, 100);
  return map;
}

function reveal(floor, state) {
  const region = regionOf(floor, state.regionId),
    seen = new Set(state.revealedCells[state.regionId] ?? []);
  for (const cell of region.map.cells)
    if (distance(cell, state.position) <= 3) seen.add(key(cell));
  state.revealedCells[state.regionId] = [...seen].sort();
  return state;
}
export function createBookOneExploration(floor) {
  const region = regionOf(floor, floor.entryRegionId);
  return reveal(floor, {
    schemaVersion: 1,
    seed: floor.seed,
    regionId: region.id,
    position: copy(region.map.entrance),
    visitedRegionIds: [region.id],
    completedObjectiveIds: [],
    revealedCells: {},
    complete: false,
  });
}
function checkedState(floor, state) {
  if (
    state?.schemaVersion !== 1 ||
    state.seed !== floor.seed ||
    !Array.isArray(state.visitedRegionIds) ||
    !Array.isArray(state.completedObjectiveIds) ||
    !state.revealedCells ||
    Array.isArray(state.revealedCells) ||
    typeof state.complete !== "boolean" ||
    !open(regionOf(floor, state.regionId).map, state.position)
  )
    throw new Error("Invalid Floor 1 exploration save.");
  const objectives = new Set(floor.regions.map((r) => r.objective.id));
  if (
    state.visitedRegionIds.some(
      (id) => !floor.regions.some((r) => r.id === id),
    ) ||
    state.completedObjectiveIds.some((id) => !objectives.has(id))
  )
    throw new Error("Unknown saved region or objective.");
  for (const [id, cells] of Object.entries(state.revealedCells)) {
    const region = regionOf(floor, id);
    if (
      !Array.isArray(cells) ||
      cells.length > region.map.width * region.map.height ||
      cells.some(
        (k) =>
          typeof k !== "string" || !region.map.cells.some((c) => key(c) === k),
      )
    )
      throw new Error("Invalid saved revealed cells.");
  }
  return copy(state);
}
export function moveBookOneExplorer(floor, state, point) {
  const next = checkedState(floor, state),
    region = regionOf(floor, next.regionId);
  if (distance(next.position, point) !== 1 || !open(region.map, point))
    throw new Error("Choose an adjacent open floor tile.");
  next.position = { x: point.x, y: point.y };
  return reveal(floor, next);
}
export function visitBookOneObjective(floor, state) {
  const next = checkedState(floor, state),
    region = regionOf(floor, next.regionId);
  if (distance(next.position, region.objectivePoint) > 1)
    throw new Error("Approach this region’s discovery marker first.");
  if (!next.completedObjectiveIds.includes(region.objective.id))
    next.completedObjectiveIds.push(region.objective.id);
  for (const report of floor.regions.filter(
    (r) => r.physicalRegion === false && r.anchorRegionId === region.id,
  )) {
    if (!next.completedObjectiveIds.includes(report.objective.id))
      next.completedObjectiveIds.push(report.objective.id);
  }
  next.complete =
    region.id === floor.exitRegionId &&
    floor.regions
      .filter((r) => !r.optional)
      .every((r) => next.completedObjectiveIds.includes(r.objective.id));
  return next;
}
export function travelBookOnePortal(floor, state, portalId) {
  const next = checkedState(floor, state),
    region = regionOf(floor, next.regionId),
    portal = region.portals.find((p) => p.id === portalId);
  if (!portal || distance(next.position, portal) > 1)
    throw new Error("Approach the connecting passage first.");
  const link = floor.links.find((l) => l.id === portal.linkId);
  if (
    !link.requiredObjectiveIds.every((id) =>
      next.completedObjectiveIds.includes(id),
    )
  )
    throw new Error(
      "Discover the required route markers before entering this passage.",
    );
  const target = regionOf(floor, portal.targetRegionId),
    arrival = target.portals.find((p) => p.linkId === portal.linkId);
  next.regionId = target.id;
  next.position = { x: arrival.x, y: arrival.y };
  if (!next.visitedRegionIds.includes(target.id))
    next.visitedRegionIds.push(target.id);
  return reveal(floor, next);
}
export function restoreBookOneExploration(floor, state) {
  return reveal(floor, checkedState(floor, state));
}
