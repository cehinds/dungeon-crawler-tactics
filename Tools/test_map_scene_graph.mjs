import assert from "node:assert/strict";
import { readFile } from "node:fs/promises";
const source = await readFile(
  new URL("../Web/wwwroot/map-scene-graph.js", import.meta.url),
  "utf8",
);
const {
  buildSceneGraph,
  rotatePorts,
  validatePlacement,
  validateConnection,
  validateSceneGraph,
  suggestPlacements,
} = await import(
  `data:text/javascript;base64,${Buffer.from(source).toString("base64")}`
);
const catalog = {
  objectTypes: [
    {
      id: "pipe",
      assetIds: ["industrial-pipe"],
      tags: ["pipe"],
      placement: { allowedSurfaceTags: ["wall"], allowedRotations: [0, 90] },
      ports: [{ id: "out", side: "north" }],
    },
  ],
};
const prop = (id, x, y, layer = "wallfixture") => ({
  id,
  assetId: "industrial-pipe",
  x,
  y,
  width: 1,
  height: 2,
  rotation: 0,
  blocksMovement: true,
  layer,
});
const map = {
  width: 5,
  height: 3,
  tiles: [..."##########....."],
  props: [prop("a", 0, 0), prop("b", 4, 0)],
  rooms: [],
};
const before = JSON.stringify(map),
  graph = buildSceneGraph(map, { catalog });
assert.equal(graph.connections.length, 1, "masonry header is joined");
assert.equal(JSON.stringify(map), before, "builder cannot mutate runtime map");
assert.deepEqual(
  buildSceneGraph(map, { catalog }),
  graph,
  "same inputs give stable graph",
);
const furnitureCatalog = {
  objectTypes: [
    {
      id: "table",
      assetIds: ["table"],
      placement: { allowedSurfaceTags: ["floor"] },
    },
  ],
};
const furnished = {
  width: 2,
  height: 1,
  tiles: ["#", "."],
  props: [
    {
      id: "table1",
      assetId: "table",
      layer: "object",
      x: 0,
      y: 0,
      width: 1,
      height: 1,
      blocksMovement: true,
    },
  ],
  objects: [],
};
assert.equal(
  validatePlacement(furnished.props[0], {
    map: furnished,
    catalog: furnitureCatalog,
    props: furnished.props,
  }).valid,
  true,
  "C# furniture collision is not masonry support",
);
assert.equal(
  buildSceneGraph(furnished, { catalog: furnitureCatalog }).nodes.find(
    (n) => n.id === "world/cell:0,0",
  ).collision.blocked,
  true,
  "support restoration cannot erase runtime collision",
);
assert.equal(
  validatePlacement(
    { ...furnished.props[0], x: 1 },
    {
      map: furnished,
      catalog: furnitureCatalog,
      reservedCells: [{ x: 1, y: 0 }],
    },
  ).valid,
  false,
  "reserved approach stays protected",
);
assert.equal(rotatePorts(catalog.objectTypes[0].ports, 90)[0].side, "east");
assert.equal(rotatePorts([{ side: "east" }], -90)[0].side, "north");
assert.equal(
  validatePlacement({ ...map.props[0], y: 2 }, { map, catalog }).valid,
  false,
  "unsupported floor and out-of-bounds footprint rejected",
);
assert.equal(
  validatePlacement(
    { ...map.props[0], x: 4 },
    { map, catalog, props: map.props },
  ).valid,
  false,
  "new solid overlap rejected",
);
const gated = { ...map, tiles: [...map.tiles] };
gated.tiles[2] = ".";
assert.equal(
  buildSceneGraph(gated, { catalog }).connections.length,
  0,
  "headers cannot create gate overlaps",
);
assert.ok(
  buildSceneGraph(
    { ...map, props: [{ ...prop("unknown", 1, 0), assetId: "unknown" }] },
    { catalog },
  ).diagnostics.some((d) => d.code === "unknown-asset"),
);
assert.ok(
  validateSceneGraph({
    nodes: [
      { id: "a", parentId: "b" },
      { id: "b", parentId: "a" },
    ],
    edges: [{ source: "a", target: "missing" }],
  }).some((d) => d.code === "cycle"),
);
assert.ok(
  validateSceneGraph({
    nodes: [{ id: "a" }],
    edges: [{ source: "a", target: "missing" }],
  }).some((d) => d.code === "dangling-edge"),
);
const placements = suggestPlacements(
  { ...prop("new", 0, 0), height: 1 },
  { map, catalog, props: map.props, reservedCells: [{ x: 2, y: 0 }] },
);
assert.ok(placements.length);
assert.ok(
  placements.every((p) => !(p.candidate.x === 2 && p.candidate.y === 0)),
  "reserved approach excluded",
);
// Portable geometry-only extracts from actual runtime captures.
const fixtures = JSON.parse(
  await readFile(
    new URL("./fixtures/object-scenes.json", import.meta.url),
    "utf8",
  ),
);
function expandMap(map) {
  const { tileRows, ...metadata } = map;
  return { ...metadata, tiles: tileRows.join("").split("") };
}
const scenes = fixtures.scenes.map((scene) => ({
  ...scene,
  world: expandMap(scene.world),
  battle: expandMap(scene.battle),
}));
const actual = scenes.find((scene) => scene.seed === 1337);
assert.ok(actual.world && actual.battle, "full actual battle fixture");
const worldGraph = buildSceneGraph(actual.world, { catalog });
const battleGraph = buildSceneGraph(actual.battle, {
  catalog,
  world: actual.world,
  battle: true,
});
const shared = actual.battle.props.find((p) =>
  actual.world.props.some((w) => w.id === p.id),
);
assert.ok(shared);
assert.equal(
  worldGraph.nodes.find((n) => n.id === `prop:${shared.id}`).worldX,
  battleGraph.nodes.find((n) => n.id === `prop:${shared.id}`).worldX,
  "world and battle canonical coordinates",
);
// Frozen connector implementation extracted before graph integration, independent oracle below.
function legacy(map, world, battle) {
  const runs = [],
    rows = new Map();
  for (const p of map.props.filter(
    (p) => p.assetId === "industrial-pipe" && p.layer === "wallfixture",
  )) {
    const row = rows.get(p.y) || [];
    row.push(p);
    rows.set(p.y, row);
  }
  for (const row of rows.values()) {
    row.sort((a, b) => a.x - b.x);
    for (let i = 1; i < row.length; i++) {
      const a = row[i - 1],
        b = row[i];
      if (b.x - a.x > 6) continue;
      let blocked = true;
      for (let x = a.x; x <= b.x; x++)
        if (map.tiles[a.y * map.width + x] !== "#") blocked = false;
      if (blocked)
        runs.push({ a, b, depth: a.y + Math.max(a.height, b.height) + 0.17 });
    }
  }
  const room =
    battle &&
    world.rooms.find(
      (r) =>
        r.objectId === map.encounterId &&
        r.width === map.width &&
        r.height === map.height,
    );
  const at = (x, y) => {
    if (x >= 0 && y >= 0 && x < map.width && y < map.height)
      return map.tiles[y * map.width + x];
    if (!room || x < -1 || y < -1 || x > map.width || y > map.height)
      return null;
    const gx = x + room.x,
      gy = y + room.y;
    return gx >= 0 && gy >= 0 && gx < world.width && gy < world.height
      ? world.tiles[gy * world.width + gx]
      : null;
  };
  for (const pipe of map.props.filter(
    (p) => p.assetId === "industrial-pipe" && p.layer !== "wallfixture",
  ))
    for (const direction of [1, -1])
      if (
        at(pipe.x + direction, pipe.y) === "#" &&
        at(pipe.x + direction, pipe.y + 1) === "#"
      ) {
        runs.push({ pipe, direction, depth: pipe.y + pipe.height + 0.18 });
        break;
      }
  return runs;
}
assert.deepEqual(
  battleGraph.connections,
  legacy(actual.battle, actual.world, true),
  "actual battle connector parity",
);
for (const { seed, world, battle } of scenes) {
  assert.deepEqual(
    buildSceneGraph(world, { catalog }).connections,
    legacy(world, world, false),
    `seed ${seed} world parity`,
  );
  assert.deepEqual(
    buildSceneGraph(battle, { catalog, world, battle: true }).connections,
    legacy(battle, world, true),
    `seed ${seed} battle parity`,
  );
}
assert.equal(
  buildSceneGraph(actual.battle, { catalog }).connections.filter(
    (c) => c.pipe && c.pipe.x === actual.battle.width - 1 && c.direction === 1,
  ).length,
  0,
  "generic battle cannot invent world border masonry",
);

const requiredCatalog = {
  objectTypes: [
    {
      id: "supported",
      assetIds: ["supported"],
      placement: { allowedSurfaceTags: ["floor"] },
      expectedRelations: [
        {
          relation: "near",
          targetTags: ["anchor"],
          required: true,
          description: "Requires an anchor nearby.",
        },
      ],
    },
  ],
};
const supportedCandidate = {
  id: "new",
  assetId: "supported",
  x: 0,
  y: 0,
  width: 1,
  height: 1,
  blocksMovement: false,
};
assert.equal(
  validatePlacement(supportedCandidate, {
    catalog: requiredCatalog,
    surfaceTags: ["floor"],
    nodes: [],
  }).valid,
  false,
  "required related object enforced",
);
assert.equal(
  validatePlacement(supportedCandidate, {
    catalog: requiredCatalog,
    surfaceTags: ["floor"],
    nodes: [{ id: "anchor", tags: ["anchor"], x: 1, y: 0 }],
  }).valid,
  true,
);
const actualArchitecture = buildSceneGraph(map, {
  catalog,
  architecture: [
    { kind: "corner", x: 0, y: 0, dx: 1, dy: 1 },
    { kind: "door", x: 1, y: 0, axis: 0 },
  ],
});
assert.ok(
  actualArchitecture.nodes.some(
    (n) => n.typeId === "wall-corner" && n.inferred === false,
  ),
);
assert.ok(
  actualArchitecture.nodes.some(
    (n) => n.typeId === "doorway-frame" && n.inferred === false,
  ),
);

const activeCatalog = JSON.parse(
  await readFile(
    new URL("../Web/wwwroot/data/map-object-rules.json", import.meta.url),
    "utf8",
  ),
);
const activeTypes = [
  ...activeCatalog.objectTypes,
  ...activeCatalog.terrainTypes,
  ...activeCatalog.worldObjectTypes,
];
const activeTags = new Set(activeTypes.flatMap((type) => type.tags || []));
for (const type of activeTypes)
  for (const relation of type.expectedRelations || [])
    for (const tag of relation.targetTags || [])
      assert.ok(
        activeTags.has(tag),
        `${type.id} references unknown relation tag ${tag}`,
      );

// Two open rooms share a two-cell doorway. A crate can cut the only route
// without covering a world object or overlapping any existing prop.
const corridorRows = [
  "#########",
  "#...#...#",
  "#.......#",
  "#.......#",
  "#...#...#",
  "#########",
];
const corridorMap = {
  width: 9,
  height: 6,
  tiles: corridorRows.join("").split(""),
  props: [],
  objects: [],
};
const crateCatalog = {
  objectTypes: [
    {
      id: "crate",
      assetIds: ["crate"],
      placement: { allowedSurfaceTags: ["floor"], allowedRotations: [0, 90] },
    },
  ],
};
const crate = {
  id: "new-crate",
  assetId: "crate",
  layer: "object",
  x: 4,
  y: 2,
  width: 1,
  height: 2,
  blocksMovement: true,
};
assert.ok(
  validatePlacement(crate, {
    map: corridorMap,
    catalog: crateCatalog,
  }).reasons.some((r) => r.code === "disconnected-route"),
  "doorway-blocking crate rejected without object overlap",
);
assert.equal(
  validatePlacement(
    { ...crate, x: 1, y: 1 },
    { map: corridorMap, catalog: crateCatalog },
  ).valid,
  true,
  "alternative room perimeter placement preserves route",
);
assert.ok(
  suggestPlacements(
    crate,
    { map: corridorMap, catalog: crateCatalog },
    { limit: 100 },
  ).every((s) => !(s.candidate.x === 4 && s.candidate.y === 2)),
  "suggestions exclude disconnected route",
);
const movingMap = {
  ...corridorMap,
  tiles: [...corridorMap.tiles],
  props: [{ ...crate, id: "moving", x: 1, y: 1 }],
};
for (let y = 1; y < 3; y++) movingMap.tiles[y * movingMap.width + 1] = "#";
assert.equal(
  validatePlacement(
    { ...crate, id: "moving", x: 2, y: 1 },
    { map: movingMap, catalog: crateCatalog, props: movingMap.props },
  ).valid,
  true,
  "moving known floor object vacates its original runtime footprint",
);

// Integrate the real narrowed catalog with every runtime prop, not just origins.
for (const { seed, world } of scenes) {
  const graph = buildSceneGraph(world, { catalog: activeCatalog });
  const nodesById = new Map(graph.nodes.map((node) => [node.id, node]));
  assert.equal(
    world.props.length,
    66,
    `seed ${seed} complete active prop fixture`,
  );
  for (const prop of world.props) {
    const node = nodesById.get(`prop:${prop.id}`);
    const result = validatePlacement(prop, {
      catalog: activeCatalog,
      map: world,
      props: world.props,
      nodes: graph.nodes,
      parent: nodesById.get(node.parentId),
    });
    assert.equal(
      result.valid,
      true,
      `seed ${seed} ${prop.id} self placement: ${JSON.stringify(result.reasons)}`,
    );
  }
  assert.equal(
    graph.diagnostics.filter((d) => d.code === "unknown-asset").length,
    0,
    `seed ${seed} active assets known`,
  );
}
const tableType = activeCatalog.objectTypes.find((type) =>
  type.tags.includes("table"),
);
assert.ok(tableType, "table catalog type exists");
const bareWall = {
  width: 2,
  height: 2,
  tiles: ["#", "#", "#", "#"],
  props: [],
  objects: [],
};
assert.equal(
  validatePlacement(
    {
      id: "new-table",
      assetId: tableType.assetIds[0],
      x: 0,
      y: 0,
      width: 1,
      height: 1,
      rotation: 0,
      layer: "object",
      blocksMovement: true,
    },
    { map: bareWall, catalog: activeCatalog },
  ).valid,
  false,
  "ordinary table cannot be placed on bare masonry",
);
const floorMap = {
  width: 2,
  height: 2,
  tiles: [".", ".", ".", "."],
  props: [],
  objects: [],
};
assert.ok(
  validatePlacement(
    { ...prop("new-mounted-pipe", 0, 0), height: 1 },
    { map: floorMap, catalog: activeCatalog },
  ).reasons.some((reason) => reason.code === "mounting"),
  "dual-purpose pipe mounted as wallfixture cannot use floor support",
);
// Real authored memberships survive the same origin translation as their props.
for (const { seed, world, battle } of scenes) {
  const snapshot = JSON.stringify({ world, battle });
  const worldGraph = buildSceneGraph(world, { catalog: activeCatalog });
  const battleGraph = buildSceneGraph(battle, { catalog: activeCatalog, world, battle: true });
  const assemblies = worldGraph.nodes.filter((node) => node.typeId === "assembly");
  assert.ok(assemblies.length > 0, `seed ${seed} has authored assemblies`);
  for (const roomId of ["goblin-workshop", "ball-of-swine-complex"]) {
    const machinery = assemblies.find((node) => node.roomId === roomId && node.groupId === "northwest-machinery");
    assert.ok(machinery, `seed ${seed} ${roomId} has authored machinery`);
    assert.equal(machinery.assemblyTypeId, "northwest-machinery", "shared template resolves by exact group ID in both industrial rooms");
    assert.equal(machinery.members.filter((member) => member.role === "machine" && member.typeId === "industrial-machine").length, 1);
    assert.equal(machinery.members.filter((member) => member.role === "pipe-fitting" && member.typeId === "industrial-pipe").length, 2);
    assert.equal(worldGraph.diagnostics.some((diagnostic) => diagnostic.nodeId === machinery.id && diagnostic.code === "unknown-assembly"), false);
  }
  for (const assembly of assemblies) {
    assert.equal(assembly.parentId, `room:${assembly.roomId}`);
    const members = worldGraph.nodes.filter((node) => assembly.memberIds.includes(node.id));
    assert.equal(assembly.x, Math.min(...members.map((member) => member.x)));
    assert.equal(assembly.width, Math.max(...members.map((member) => member.x + member.width)) - assembly.x);
    assert.ok(members.every((member) => member.parentId === assembly.id));
    assert.ok(members.every((member) => member.layer === member.runtime.layer));
    assert.ok(members.every((member) => member.runtime.groupId === assembly.groupId));
    assert.equal(worldGraph.edges.filter((edge) => edge.source === assembly.id && edge.relation === "authored-member").length, members.length);
  }
  for (const assembly of battleGraph.nodes.filter((node) => node.typeId === "assembly")) {
    const worldAssembly = assemblies.find((node) => node.id === assembly.id);
    assert.ok(worldAssembly, "world/battle assembly ID stable");
    assert.deepEqual(assembly.memberIds, worldAssembly.memberIds);
    assert.equal(assembly.worldX, worldAssembly.worldX);
    assert.equal(assembly.worldY, worldAssembly.worldY);
    assert.equal(assembly.worldGroupX, worldAssembly.worldGroupX);
    assert.equal(assembly.worldGroupY, worldAssembly.worldGroupY);
  }
  assert.equal(JSON.stringify({ world, battle }), snapshot, "assemblies cannot mutate imported worlds");
}
const declaredCatalog = {
  ...furnitureCatalog,
  assemblyTypes: [{ id: "lesson", groupId: "lesson", roomId: "room", label: "Lesson",
    members: [
      { role: "table", objectTypeId: "table", expectedCount: 2, required: true },
      { role: "optional-pipe", objectTypeId: "pipe", expectedCount: 1, required: false },
    ] }],
};
const declaredMap = {
  width: 4, height: 4, tiles: Array(16).fill("."),
  rooms: [{ id: "room", x: 0, y: 0, width: 4, height: 4 }],
  props: [{ id: "arbitrary", assetId: "table", roomId: "room", groupId: "lesson", groupX: 1, groupY: 1,
    x: 1, y: 1, width: 1, height: 1, layer: "underlay", blocksMovement: false },
    { id: "lesson-table-nearby", assetId: "table", roomId: "room", x: 2, y: 1, width: 1, height: 1 }],
};
const declaredGraph = buildSceneGraph(declaredMap, { catalog: declaredCatalog });
const lesson = declaredGraph.nodes.find((node) => node.typeId === "assembly");
assert.deepEqual(lesson.memberIds, ["prop:arbitrary"], "names and proximity cannot invent membership");
assert.equal(lesson.members[0].role, "table");
assert.ok(declaredGraph.diagnostics.some((d) => d.code === "missing-assembly-member" && d.severity === "error" && d.required));
assert.ok(declaredGraph.diagnostics.some((d) => d.code === "missing-assembly-member" && d.severity === "info" && !d.required));
const unknownMap = structuredClone(declaredMap);
unknownMap.props[0].groupId = "uncatalogued";
const unknownGraph = buildSceneGraph(unknownMap, { catalog: declaredCatalog });
assert.ok(unknownGraph.nodes.some((node) => node.typeId === "assembly" && node.groupId === "uncatalogued"));
assert.ok(unknownGraph.diagnostics.some((d) => d.code === "unknown-assembly"));
const portNode = (id, side, kind = "fluid") => ({ id, ports: [{ id: "p", side, kind, accepts: [kind] }] });
const portOptions = { sourcePort: "p", targetPort: "p" };
assert.ok(validateConnection(portNode("a", "east"), portNode("b", "west"), portOptions).valid);
assert.equal(validateConnection(portNode("a", "east"), portNode("b", "east"), portOptions).valid, false);
assert.equal(validateConnection(portNode("a", "east"), portNode("b", "west", "power"), portOptions).valid, false);
assert.equal(validateConnection(portNode("a", "east"), portNode("a", "west"), portOptions).valid, false);
assert.equal(validateConnection(portNode("a", "east"), portNode("b", "west"), { ...portOptions, targetPort: "absent" }).valid, false);
assert.equal(validateConnection(portNode("a", "east"), portNode("b", "north"), { ...portOptions, adapter: true }).valid, false);
assert.ok(validateConnection(portNode("a", "east"), portNode("b", "north"), {
  ...portOptions, adapter: { id: "elbow", kinds: ["fluid"], sidePairs: [["east", "north"]] },
}).valid, "explicit adapter permits only its declared side pair");
assert.equal(validateConnection(portNode("a", "east"), portNode("b", "south"), {
  ...portOptions, adapter: { id: "elbow", kinds: ["fluid"], sidePairs: [["east", "north"]] },
}).valid, false);
console.log(
  "Scene graph: actual seed 1337/42 assemblies and connector fixtures, 132 runtime self placements, member diagnostics, typed ports/adapters, mounting/support guards, route preservation, identity and immutability pass.",
);
