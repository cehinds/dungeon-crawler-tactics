// Presentation metadata only. Runtime tiles and footprints remain authoritative.
const SIDES = ["north", "east", "south", "west"];
const surfaceTags = (tile) =>
  tile === "#"
    ? ["wall", "masonry", "blocked"]
    : tile === "~"
      ? ["water", "blocked"]
      : tile === "."
        ? ["floor", "walkable"]
        : ["unknown"];
const catalogIndexes = new WeakMap();
const emptyCatalog = {};
function indexCatalog(catalog = emptyCatalog) {
  let index = catalogIndexes.get(catalog);
  if (index) return index;
  index = new Map();
  const types = [
    ...(catalog.objectTypes || []),
    ...(catalog.terrainTypes || []),
    ...(catalog.worldObjectTypes || []),
  ];
  for (const type of types) {
    index.set(type.id, type);
    for (const assetId of type.assetIds || []) index.set(assetId, type);
  }
  catalogIndexes.set(catalog, index);
  return index;
}
const lookup = (catalog, value) => indexCatalog(catalog).get(value);
export function rotatePorts(ports = [], rotation = 0) {
  const turns = ((Math.round(rotation / 90) % 4) + 4) % 4;
  return ports.map((p) => ({
    ...p,
    tags: [...(p.tags || [])],
    accepts: [...(p.accepts || [])],
    side: SIDES.includes(p.side)
      ? SIDES[(SIDES.indexOf(p.side) + turns) % 4]
      : p.side,
  }));
}
// C# marks solid furniture cells '#'; known furniture restores visual support only.
function restoredSupportCells(map, catalog) {
  const restored = new Set();
  for (const prop of map.props || []) {
    if (prop.layer === "wallfixture" || !lookup(catalog, prop.assetId))
      continue;
    for (let y = prop.y; y < prop.y + prop.height; y++) {
      for (let x = prop.x; x < prop.x + prop.width; x++)
        restored.add(y * map.width + x);
    }
  }
  return restored;
}
function supportTile(map, x, y, restored) {
  const index = y * map.width + x;
  const tile = map.tiles?.[index];
  return tile === "#" && restored.has(index) ? "." : tile;
}
function preparePlacementContext(context) {
  if (context.prepared) return context;
  return {
    ...context,
    prepared: true,
    reachabilityByObject: new Map(),
    restored: context.map
      ? restoredSupportCells(context.map, context.catalog)
      : new Set(),
    reserved: new Set(
      (context.reservedCells || []).map((p) => `${p.x},${p.y}`),
    ),
    protectedCells: new Set(
      (context.objects || context.map?.objects || []).map(
        (p) => `${p.x},${p.y}`,
      ),
    ),
  };
}
// Four-neighbor routing matches the authoritative orthogonal movement grid.
function adjacentCells(index, map) {
  const x = index % map.width,
    y = Math.floor(index / map.width),
    neighbors = [];
  if (x > 0) neighbors.push(index - 1);
  if (x + 1 < map.width) neighbors.push(index + 1);
  if (y > 0) neighbors.push(index - map.width);
  if (y + 1 < map.height) neighbors.push(index + map.width);
  return neighbors;
}
function prepareReachability(candidate, context) {
  const key = candidate.id || "__new-object";
  if (context.reachabilityByObject.has(key))
    return context.reachabilityByObject.get(key);
  const map = context.map;
  const walkable = new Set();
  for (let i = 0; i < map.width * map.height; i++)
    if (map.tiles[i] === ".") walkable.add(i);
  // Moving a known floor prop vacates only its own old footprint. Wall fixtures
  // and other furniture retain their authoritative blocked tiles.
  const original = (map.props || []).find((p) => p.id === candidate.id);
  if (
    original &&
    original.layer !== "wallfixture" &&
    lookup(context.catalog, original.assetId)
  ) {
    for (let y = original.y; y < original.y + original.height; y++)
      for (let x = original.x; x < original.x + original.width; x++) {
        if (
          x >= 0 &&
          y >= 0 &&
          x < map.width &&
          y < map.height &&
          map.tiles[y * map.width + x] === "#"
        )
          walkable.add(y * map.width + x);
      }
  }
  const components = new Int32Array(map.width * map.height);
  let componentId = 0;
  for (const start of walkable) {
    if (components[start]) continue;
    componentId++;
    components[start] = componentId;
    const queue = [start];
    for (let i = 0; i < queue.length; i++)
      for (const next of adjacentCells(queue[i], map))
        if (walkable.has(next) && !components[next]) {
          components[next] = componentId;
          queue.push(next);
        }
  }
  const baseline = { walkable, components, results: new Map() };
  context.reachabilityByObject.set(key, baseline);
  return baseline;
}
function preservesReachability(candidate, context) {
  const map = context.map,
    baseline = prepareReachability(candidate, context);
  // Rotation does not alter authoritative runtime width/height. Reuse the result
  // for equivalent proposals while suggestions try allowed art rotations.
  const key = `${candidate.x},${candidate.y},${candidate.width || 1},${candidate.height || 1}`;
  if (baseline.results.has(key)) return baseline.results.get(key);
  const removed = new Set();
  for (let y = candidate.y; y < candidate.y + (candidate.height || 1); y++)
    for (let x = candidate.x; x < candidate.x + (candidate.width || 1); x++) {
      const index = y * map.width + x;
      if (baseline.walkable.has(index)) removed.add(index);
    }
  const boundary = new Set();
  for (const cell of removed)
    for (const next of adjacentCells(cell, map))
      if (baseline.walkable.has(next) && !removed.has(next)) boundary.add(next);
  // Every newly split component borders the removed footprint. Compare only
  // those boundary cells that were connected before this proposal.
  let valid = true;
  while (boundary.size && valid) {
    const start = boundary.values().next().value;
    const targets = new Set(
      [...boundary].filter(
        (cell) => baseline.components[cell] === baseline.components[start],
      ),
    );
    for (const cell of targets) boundary.delete(cell);
    if (targets.size < 2) continue;
    const visited = new Set([start]),
      queue = [start];
    targets.delete(start);
    for (let i = 0; i < queue.length && targets.size; i++)
      for (const next of adjacentCells(queue[i], map))
        if (
          baseline.walkable.has(next) &&
          !removed.has(next) &&
          !visited.has(next)
        ) {
          visited.add(next);
          queue.push(next);
          targets.delete(next);
        }
    valid = targets.size === 0;
  }
  baseline.results.set(key, valid);
  return valid;
}
export function validatePlacement(candidate, context = {}) {
  context = preparePlacementContext(context);
  const type = lookup(context.catalog, candidate.typeId || candidate.assetId);
  const reasons = [];
  if (!type)
    reasons.push({
      code: "unknown-type",
      message: `Unknown object type: ${candidate.typeId || candidate.assetId}`,
    });
  const rules = type?.placement || {};
  if (
    rules.allowedRotations?.length &&
    !rules.allowedRotations.includes(candidate.rotation || 0)
  )
    reasons.push({
      code: "rotation",
      message: "Rotation is not supported by this object type.",
    });
  for (const tag of rules.requiredParentTags || [])
    if (!context.parent?.tags?.includes(tag))
      reasons.push({ code: "parent", message: `Parent requires tag ${tag}.` });
  const tags =
    context.surfaceTags ||
    (context.map
      ? surfaceTags(
          supportTile(context.map, candidate.x, candidate.y, context.restored),
        )
      : []);
  if (
    rules.allowedSurfaceTags?.length &&
    !rules.allowedSurfaceTags.some((t) => tags.includes(t))
  )
    reasons.push({
      code: "support",
      message: `Requires surface: ${rules.allowedSurfaceTags.join(", ")}.`,
    });
  const reserved = context.reserved;
  if (candidate.blocksMovement)
    for (let y = candidate.y; y < candidate.y + (candidate.height || 1); y++)
      for (let x = candidate.x; x < candidate.x + (candidate.width || 1); x++)
        if (
          reserved.has(`${x},${y}`) ||
          context.protectedCells.has(`${x},${y}`)
        )
          reasons.push({
            code: "reserved",
            message: `Reserved interaction or approach at ${x},${y}.`,
          });
  if (context.map) {
    const map = context.map;
    for (let y = candidate.y; y < candidate.y + (candidate.height || 1); y++)
      for (let x = candidate.x; x < candidate.x + (candidate.width || 1); x++) {
        if (x < 0 || y < 0 || x >= map.width || y >= map.height)
          reasons.push({
            code: "bounds",
            message: `Footprint outside map at ${x},${y}.`,
          });
        else if (
          candidate.layer === "wallfixture" &&
          map.tiles[y * map.width + x] !== "#"
        ) {
          reasons.push({
            code: "mounting",
            message: `Wall fixture requires runtime masonry at ${x},${y}.`,
          });
        } else if (
          rules.allowedSurfaceTags?.length &&
          !rules.allowedSurfaceTags.some((t) =>
            surfaceTags(supportTile(map, x, y, context.restored)).includes(t),
          )
        )
          reasons.push({
            code: "support",
            message: `Unsupported footprint at ${x},${y}.`,
          });
      }
  }
  // This reports proposed overlaps; it never changes runtime collision flags.
  if (candidate.blocksMovement)
    for (const other of context.props || []) {
      if (other.id === candidate.id || !other.blocksMovement) continue;
      if (
        candidate.x < other.x + other.width &&
        candidate.x + (candidate.width || 1) > other.x &&
        candidate.y < other.y + other.height &&
        candidate.y + (candidate.height || 1) > other.y
      )
        reasons.push({
          code: "overlap",
          message: `Overlaps runtime solid ${other.id}.`,
        });
    }
  for (const relation of type?.expectedRelations || [])
    if (
      relation.required &&
      !(context.nodes || []).some(
        (n) =>
          n.runtimeId !== candidate.id &&
          relation.targetTags?.some((t) => n.tags?.includes(t)) &&
          Number.isFinite(n.x) &&
          Math.max(Math.abs(n.x - candidate.x), Math.abs(n.y - candidate.y)) <=
            Math.max(candidate.width || 1, candidate.height || 1) + 1,
      )
    )
      reasons.push({
        code: "required-relation",
        message: relation.description || `Requires ${relation.relation}.`,
      });
  if (
    reasons.length === 0 &&
    context.map &&
    context.preserveReachability !== false &&
    candidate.blocksMovement &&
    candidate.layer !== "wallfixture" &&
    rules.allowedSurfaceTags?.includes("floor") &&
    !preservesReachability(candidate, context)
  ) {
    reasons.push({
      code: "disconnected-route",
      message:
        "This solid footprint would disconnect an existing walkable route.",
    });
  }
  return { valid: reasons.length === 0, reasons };
}
export function validateSceneGraph(graph) {
  const diagnostics = [],
    ids = new Set(graph.nodes.map((n) => n.id)),
    parents = new Map(graph.nodes.map((n) => [n.id, n.parentId]));
  if (ids.size !== graph.nodes.length)
    diagnostics.push({
      code: "duplicate-id",
      severity: "error",
      message: "Node IDs must be unique.",
    });
  for (const node of graph.nodes) {
    if (node.parentId && !ids.has(node.parentId))
      diagnostics.push({
        code: "dangling-parent",
        nodeId: node.id,
        severity: "error",
      });
    const seen = new Set([node.id]);
    let id = node.parentId;
    while (id && ids.has(id)) {
      if (seen.has(id)) {
        diagnostics.push({ code: "cycle", nodeId: node.id, severity: "error" });
        break;
      }
      seen.add(id);
      id = parents.get(id);
    }
  }
  for (const edge of graph.edges)
    if (!ids.has(edge.source) || !ids.has(edge.target))
      diagnostics.push({ code: "dangling-edge", severity: "error", edge });
  return diagnostics;
}
export function buildSceneGraph(
  map,
  {
    catalog = {},
    world = map,
    battle = false,
    seed = 0,
    origin,
    architecture,
  } = {},
) {
  const restored = restoredSupportCells(map, catalog);
  const matchedRoom =
    battle &&
    world?.rooms?.find(
      (r) =>
        r.objectId === map.encounterId &&
        r.width === map.width &&
        r.height === map.height,
    );
  // Only a verified room allows world-border lookup; arbitrary origins cannot enable it.
  const offset = matchedRoom
    ? { x: matchedRoom.x, y: matchedRoom.y }
    : origin || { x: 0, y: 0 };
  const scope =
    battle && !matchedRoom ? `battle:${map.encounterId || "arena"}` : "world";
  const nodes = [],
    edges = [],
    diagnostics = [],
    byId = new Map();
  const add = (node) => {
    const n = {
      tags: [],
      children: [],
      ports: [],
      expectedRelations: [],
      ...node,
    };
    nodes.push(n);
    byId.set(n.id, n);
    if (n.parentId) {
      byId.get(n.parentId)?.children.push(n.id);
      edges.push({ source: n.parentId, target: n.id, relation: "contains" });
    }
    return n;
  };
  const root = add({
    id: scope,
    typeId: "world",
    label: battle ? "Battle scene" : "World",
    tags: ["world"],
    seed,
  });
  const rooms = matchedRoom ? [matchedRoom] : battle ? [] : map.rooms || [];
  const roomNodes = rooms.map((r) =>
    add({
      id: `room:${r.id}`,
      typeId: "room",
      label: r.name || r.id,
      parentId: root.id,
      tags: ["room", r.kind, r.theme].filter(Boolean),
      runtime: { ...r },
      x: r.x - offset.x,
      y: r.y - offset.y,
      width: r.width,
      height: r.height,
    }),
  );
  const group = (parent, kind) =>
    byId.get(`${parent.id}/${kind}`) ||
    add({
      id: `${parent.id}/${kind}`,
      typeId: "group",
      label: kind,
      parentId: parent.id,
      tags: [kind],
    });
  const roomAt = (x, y, roomId) =>
    roomNodes.find((r) => r.runtime.id === roomId) ||
    roomNodes.find(
      (r) => x >= r.x && y >= r.y && x < r.x + r.width && y < r.y + r.height,
    ) ||
    root;
  const tileNodes = new Map();
  for (let y = 0; y < map.height; y++)
    for (let x = 0; x < map.width; x++) {
      const tile = map.tiles?.[y * map.width + x],
        support = supportTile(map, x, y, restored),
        tags = surfaceTags(support),
        typeId =
          support === "#"
            ? "masonry-wall"
            : support === "~"
              ? "channel-water"
              : support === "."
                ? "floor"
                : "unknown-surface";
      const parent = group(
        roomAt(x, y),
        support === "#" ? "structure" : "surfaces",
      );
      const n = add({
        id: `${scope}/cell:${x + offset.x},${y + offset.y}`,
        typeId,
        label: `${typeId} ${x},${y}`,
        parentId: parent.id,
        tags: [...new Set([...tags, ...(lookup(catalog, typeId)?.tags || [])])],
        x,
        y,
        worldX: x + offset.x,
        worldY: y + offset.y,
        width: 1,
        height: 1,
        layer: tile === "#" ? "structure" : "surface",
        collision: { source: "runtime-tile", blocked: tile !== ".", tile },
      });
      tileNodes.set(`${x},${y}`, n);
    }
  for (const prop of map.props || []) {
    const type = lookup(catalog, prop.assetId),
      parent = group(
        roomAt(prop.x, prop.y, prop.roomId),
        prop.layer === "wallfixture" ? "structure" : "props",
      );
    const n = add({
      id: `prop:${prop.id}`,
      runtimeId: prop.id,
      typeId: type?.id || "unknown",
      label: type?.label || prop.assetId,
      assetId: prop.assetId,
      parentId: parent.id,
      tags: [...(type?.tags || [])],
      x: prop.x,
      y: prop.y,
      worldX: prop.x + offset.x,
      worldY: prop.y + offset.y,
      width: prop.width,
      height: prop.height,
      rotation: prop.rotation,
      layer: prop.layer,
      collision: { source: "runtime-prop", blocked: prop.blocksMovement },
      runtime: { ...prop },
      properties: type?.properties || {},
      placement: type?.placement || {},
      ports: rotatePorts(type?.ports, prop.rotation),
      expectedRelations: type?.expectedRelations || [],
    });
    if (!type)
      diagnostics.push({
        code: "unknown-asset",
        severity: "warning",
        nodeId: n.id,
        assetId: prop.assetId,
        message: `No catalog type for ${prop.assetId}.`,
      });
    for (let y = prop.y; y < prop.y + prop.height; y++)
      for (let x = prop.x; x < prop.x + prop.width; x++) {
        const cell = tileNodes.get(`${x},${y}`);
        if (cell)
          edges.push({
            source: n.id,
            target: cell.id,
            relation:
              prop.layer === "wallfixture" ? "mounted-on" : "supported-by",
          });
      }
  }
  for (const obj of map.objects || []) {
    const type =
        lookup(catalog, `world-${obj.kind}`) || lookup(catalog, obj.kind),
      parent = group(roomAt(obj.x, obj.y, obj.roomId), "objects");
    add({
      id: `object:${obj.id}`,
      runtimeId: obj.id,
      typeId: type?.id || `world-${obj.kind}`,
      label: obj.name || obj.id,
      parentId: parent.id,
      tags: type?.tags || ["world-object", obj.kind],
      x: obj.x,
      y: obj.y,
      worldX: obj.x + offset.x,
      worldY: obj.y + offset.y,
      layer: "object",
      collision: { source: "runtime-object", blocked: null },
      runtime: { ...obj },
      expectedRelations: type?.expectedRelations || [],
    });
  }
  const at = (x, y) =>
    x < 0 || y < 0 || x >= map.width || y >= map.height
      ? "#"
      : supportTile(map, x, y, restored);
  const attach = (parent, typeId, suffix, extra = {}) => {
    const type = lookup(catalog, typeId);
    return add({
      id: `${parent.id}/${suffix}`,
      typeId,
      label: type?.label || typeId,
      parentId: parent.id,
      tags: type?.tags || [],
      x: parent.x,
      y: parent.y,
      width: 1,
      height: 1,
      layer: "attachment",
      collision: { source: "presentation", blocked: false },
      derived: true,
      inferred: true,
      ...extra,
    });
  };
  // Derived architecture retains the supporting runtime cell as its parent.
  if (!architecture)
    for (const cell of tileNodes.values()) {
      const { x, y } = cell;
      if (at(x, y) === "#")
        for (const [dx, dy] of [
          [0, 1],
          [0, -1],
          [1, 0],
          [-1, 0],
        ])
          if (at(x + dx, y + dy) !== "#")
            attach(
              cell,
              dy === 1 ? "wall-face" : "wall-cap",
              `edge:${dx},${dy}`,
              { dx, dy },
            );
      if (
        at(x, y) === "." &&
        ((at(x, y - 1) === "~" && at(x, y + 1) === "~") ||
          (at(x - 1, y) === "~" && at(x + 1, y) === "~"))
      )
        attach(cell, "bridge-deck", "bridge", {
          rotation: at(x - 1, y) === "~" ? 90 : 0,
        });
      if (at(x, y) === "~" && at(x, y - 1) === "#")
        attach(cell, "hanging-moss", "water-edge-moss");
    }
  if (architecture) {
    const kinds = {
      front: "wall-face",
      cap: "wall-cap",
      corner: "wall-corner",
      door: "doorway-frame",
      moss: "hanging-moss",
    };
    architecture.forEach((part, index) => {
      const parent =
        tileNodes.get(`${part.x},${part.y}`) ||
        group(roomAt(part.x, part.y), "structure");
      const typeId = kinds[part.kind] || "unknown-architecture";
      attach(
        parent,
        typeId,
        `architecture:${part.x},${part.y}:${part.kind}:${index}`,
        { ...part, x: part.x, y: part.y, inferred: false },
      );
    });
  }
  for (const prop of map.props || [])
    if (
      [
        "industrial-exit",
        "industrial-torch",
        "industrial-machine",
        "industrial-outlet",
      ].includes(prop.assetId)
    )
      attach(byId.get(`prop:${prop.id}`), "surface-lighting", "light");
  const bankAt = (x, y) => {
    if (x >= 0 && y >= 0 && x < map.width && y < map.height)
      return map.tiles?.[y * map.width + x];
    if (!matchedRoom || x < -1 || y < -1 || x > map.width || y > map.height)
      return null;
    const gx = x + matchedRoom.x,
      gy = y + matchedRoom.y;
    return gx >= 0 && gy >= 0 && gx < world.width && gy < world.height
      ? world.tiles?.[gy * world.width + gx]
      : null;
  };
  const config = catalog.connectors || {},
    pipeAssetIds = config.pipeAssetIds || ["industrial-pipe"],
    header = config.header || {},
    returns = config.return || {};
  const connections = [],
    rows = new Map();
  for (const p of map.props || [])
    if (
      pipeAssetIds.includes(p.assetId) &&
      p.layer === (header.layer || "wallfixture")
    ) {
      const row = rows.get(p.y) || [];
      row.push(p);
      rows.set(p.y, row);
    }
  for (const row of rows.values()) {
    row.sort((a, b) => a.x - b.x);
    for (let i = 1; i < row.length; i++) {
      const a = row[i - 1],
        b = row[i];
      if (b.x - a.x > (header.maxGap ?? 6)) continue;
      let blocked = true;
      for (let x = a.x; x <= b.x; x++)
        if (map.tiles?.[a.y * map.width + x] !== (header.requiredTile || "#"))
          blocked = false;
      if (blocked) {
        connections.push({
          a,
          b,
          depth:
            a.y + Math.max(a.height, b.height) + (header.depthOffset ?? 0.17),
        });
        edges.push({
          source: `prop:${a.id}`,
          target: `prop:${b.id}`,
          relation: "pipe-header",
        });
      }
    }
  }
  for (const pipe of map.props || [])
    if (
      pipeAssetIds.includes(pipe.assetId) &&
      pipe.layer !== (returns.excludedLayer || "wallfixture")
    )
      for (const direction of returns.directions || [1, -1])
        if (
          Array.from({ length: returns.bankHeight || 2 }, (_, dy) =>
            bankAt(pipe.x + direction, pipe.y + dy),
          ).every((t) => t === (returns.requiredTile || "#"))
        ) {
          connections.push({
            pipe,
            direction,
            depth: pipe.y + pipe.height + (returns.depthOffset ?? 0.18),
          });
          const target = tileNodes.get(`${pipe.x + direction},${pipe.y}`);
          if (target)
            edges.push({
              source: `prop:${pipe.id}`,
              target: target.id,
              relation: "pipe-return",
            });
          break;
        }
  // Relations only inspect nearby cells; avoid scanning the whole world per prop.
  const nodesByCell = new Map();
  for (const node of nodes) {
    if (!Number.isFinite(node.x) || !Number.isFinite(node.y)) continue;
    const key = `${Math.floor(node.x)},${Math.floor(node.y)}`;
    const bucket = nodesByCell.get(key) || [];
    bucket.push(node);
    nodesByCell.set(key, bucket);
  }
  for (const node of nodes.filter((n) => n.runtimeId))
    for (const relation of node.expectedRelations) {
      const radius = Math.max(node.width || 1, node.height || 1) + 1;
      const targets = [];
      for (let y = Math.floor(node.y - radius); y <= node.y + radius; y++) {
        for (let x = Math.floor(node.x - radius); x <= node.x + radius; x++) {
          for (const target of nodesByCell.get(`${x},${y}`) || []) {
            if (
              target.id !== node.id &&
              relation.targetTags?.some((tag) => target.tags.includes(tag)) &&
              Math.max(
                Math.abs(target.x - node.x),
                Math.abs(target.y - node.y),
              ) <= radius
            )
              targets.push(target);
          }
        }
      }
      for (const target of targets)
        edges.push({
          source: node.id,
          target: target.id,
          relation: relation.relation,
          advisory: true,
        });
      if (relation.required && !targets.length)
        diagnostics.push({
          code: "missing-relation",
          severity: "warning",
          nodeId: node.id,
          relation: relation.relation,
          message: relation.description,
        });
    }
  const graph = {
    schemaVersion: 1,
    nodes,
    roots: [root.id],
    edges,
    connections,
    diagnostics,
    origin: offset,
  };
  diagnostics.push(...validateSceneGraph(graph));
  return graph;
}

// Proposals are read-only authoring advice, never placed runtime objects.
export function suggestPlacements(candidate, context = {}, { limit = 8 } = {}) {
  context = preparePlacementContext(context);
  const map = context.map;
  if (!map) return [];
  const type = lookup(context.catalog, candidate.typeId || candidate.assetId);
  if (!type) return [];
  const bounds = context.bounds || {
    x: 0,
    y: 0,
    width: map.width,
    height: map.height,
  };
  // Resolve semantic targets once for the entire candidate search.
  const relatedNodes = (type.expectedRelations || []).flatMap((relation) =>
    (context.nodes || []).filter(
      (node) =>
        Number.isFinite(node.x) &&
        node.runtimeId !== candidate.id &&
        relation.targetTags?.some((tag) => node.tags?.includes(tag)),
    ),
  );
  const reserved = context.reserved,
    suggestions = [];
  for (let y = bounds.y; y < bounds.y + bounds.height; y++)
    for (let x = bounds.x; x < bounds.x + bounds.width; x++)
      for (const rotation of type.placement?.allowedRotations || [
        candidate.rotation || 0,
      ]) {
        const proposal = { ...candidate, x, y, rotation };
        let reservedOverlap = false;
        for (let dy = 0; dy < (proposal.height || 1); dy++)
          for (let dx = 0; dx < (proposal.width || 1); dx++)
            if (reserved.has(`${x + dx},${y + dy}`)) reservedOverlap = true;
        if (reservedOverlap) continue;
        const validation = validatePlacement(proposal, {
          ...context,
          surfaceTags: surfaceTags(supportTile(map, x, y, context.restored)),
        });
        if (!validation.valid) continue;
        let score = 0;
        for (const node of relatedNodes) {
          score += 1 / (1 + Math.abs(node.x - x) + Math.abs(node.y - y));
        }
        suggestions.push({
          candidate: proposal,
          score,
          validation,
          recommendation: true,
        });
      }
  return suggestions
    .sort(
      (a, b) =>
        b.score - a.score ||
        a.candidate.y - b.candidate.y ||
        a.candidate.x - b.candidate.x ||
        a.candidate.rotation - b.candidate.rotation,
    )
    .slice(0, Math.max(0, limit));
}
