/**
 * Build the exact continuous floor shown by the atlas and imported by C#.
 * Authored district positions stay fixed. The seed changes corridor bends and
 * selects the existing regional enemy templates; it does not invent a new graph.
 */
const WIDTH = 40;
const HEIGHT = 32;
const COMBAT_REGIONS = new Set([
  'false-guild-alley', 'hoarder-lair', 'goblin-workshop',
  'juicer-gym', 'ball-of-swine-complex',
]);
const DISTRICT_OBJECTS = {
  entry: ['cd-door-threshold', 'cd-torch'],
  alley: ['cd-dozer', 'cd-trap-machine'],
  guild: ['ab-clean-table-wood-empty', 'ab-clean-chair-wood-blue'],
  'garbage-lair': ['ab-clean-barrel-wood-top', 'cd-crate'],
  'safe-rest': ['ab-clean-table-wood-empty', 'ab-clean-chair-wood-blue'],
  'goblin-industrial': ['cd-gear', 'cd-lever-plinth'],
  gym: ['cd-weight-bench', 'cd-barbell'],
  'boss-complex': ['cd-lever-plinth', 'cd-stair-module'],
};
const cellKey = point => `${point.x},${point.y}`;

export function bookOneSeedNumber(seed) {
  let hash = 2166136261;
  for (const character of seed) hash = Math.imul(hash ^ character.charCodeAt(0), 16777619) >>> 0;
  return hash;
}

function createDistricts(floor, tiles) {
  const centers = new Map();
  const regionBounds = [];
  for (const region of floor.regions.filter(region => region.physicalRegion !== false)) {
    const x = 2 + 5 * region.position.x;
    const y = 3 + 6 * region.position.y;
    if (x < 1 || x > 37 || y < 2 || y > 28) throw new Error('Region exceeds tactical floor bounds.');
    centers.set(region.id, {x, y});
    regionBounds.push({
      id: region.id, label: region.label, x: x - 1, y: y - 2,
      width: 4, height: 5, center: {x, y},
      safeZone: region.safeZone, canonStatus: region.canonStatus,
    });
    for (let dy = -2; dy <= 2; dy++) {
      for (let dx = -1; dx <= 2; dx++) tiles[(y + dy) * WIDTH + x + dx].blocked = false;
    }
  }
  return {centers, regionBounds};
}

function carveConnections(floor, centers, tiles, hash) {
  return floor.links.filter(link => centers.has(link.from) && centers.has(link.to)).map(link => {
    const start = centers.get(link.from);
    const end = centers.get(link.to);
    const path = [];
    let {x, y} = start;
    const walk = (axis, target) => {
      while ((axis === 'x' ? x : y) !== target) {
        if (axis === 'x') x += Math.sign(target - x);
        else y += Math.sign(target - y);
        tiles[y * WIDTH + x].blocked = false;
        path.push({x, y});
      }
    };
    if ((hash + link.id.length) & 1) {
      walk('x', end.x);
      walk('y', end.y);
    } else {
      walk('y', end.y);
      walk('x', end.x);
    }
    return {...link, path};
  });
}

function createEncountersAndDiscoveries(floor, centers, regionBounds) {
  const enemies = [];
  const groups = [];
  const discoveries = [];
  for (const region of floor.regions) {
    const physical = region.physicalRegion !== false;
    const center = centers.get(physical ? region.id : 'tutorial-guildhall');
    const point = {x: center.x + (physical ? 0 : 1), y: center.y - 1};
    const optional = region.optional === true || region.canonStatus === 'mentioned';
    discoveries.push({
      id: region.objective.id, label: region.objective.label,
      description: `${region.description} ${optional ? 'Optional route lead; supplies are a tactical adaptation.' : ''}`,
      kind: optional ? 'cache' : 'objective',
      ...(optional ? {itemId: 'item.health_tonic', count: 1} : {}),
      ...point,
    });
    const bounds = regionBounds.find(bounds => bounds.id === region.id);
    if (bounds) bounds.objective = {...point, id: region.objective.id, label: region.objective.label};
    if (!COMBAT_REGIONS.has(region.id)) continue;
    const templates = region.map?.canonicalMap?.enemies;
    if (!templates?.length) throw new Error(`Missing existing combat templates for ${region.id}.`);
    const enemyIds = [];
    for (let index = 0; index < 2; index++) {
      const id = `custom.enemy.book1.${region.id}.${index}`;
      enemies.push({
        ...structuredClone(templates[index % templates.length]),
        id, x: center.x + index, y: center.y + 2,
      });
      enemyIds.push(id);
    }
    groups.push({
      id: `book1.${region.id}`, label: `${region.label} · tactical encounter`,
      kind: 'visible', x: center.x, y: center.y + 2, enemyIds, rewardXp: 30,
    });
  }
  return {enemies, groups, discoveries};
}

function placeWholeObjects(floor, library, centers, tiles, reservedPoints) {
  const reserved = new Set(reservedPoints.map(cellKey));
  const presentationObjects = [];
  for (const region of floor.regions.filter(region => centers.has(region.id))) {
    const center = centers.get(region.id);
    const objectIds = DISTRICT_OBJECTS[region.theme] ?? ['cd-torch', 'ab-clean-crate-wood-cross'];
    const corners = [
      {x: center.x - 1, y: center.y - 2}, {x: center.x + 2, y: center.y - 2},
      {x: center.x - 1, y: center.y + 2}, {x: center.x + 2, y: center.y + 2},
    ];
    for (const [index, objectId] of objectIds.entries()) {
      const asset = library?.objects?.find(object => object.id === objectId);
      const source = region.map.objects.find(object => object.assetId === objectId)
        ?? region.map.objects.find(object => object.width === 1 && object.height === 1);
      if (!asset && !source) continue;
      const point = corners.find(point => !reserved.has(cellKey(point)));
      if (!point) continue;
      reserved.add(cellKey(point));
      tiles[point.y * WIDTH + point.x].blocked = true;
      const bounds = asset?.visibleBounds;
      presentationObjects.push({
        ...structuredClone(source ?? {}), id: `book1.object.${region.id}.${index}`,
        assetId: asset?.id ?? source.assetId, assetPath: asset?.asset.path ?? source.assetPath,
        ...point, width: 1, height: 1, rotationDegrees: 0, blocksMovement: true,
        regionId: region.id,
        ...(bounds ? {sourceVisibleBounds: [bounds[0], bounds[1], bounds[2] - bounds[0], bounds[3] - bounds[1]]} : {}),
      });
    }
  }
  return presentationObjects;
}

function seededRandom(seed) {
  let state = seed >>> 0;
  return () => {
    state = (state + 0x6d2b79f5) >>> 0;
    let value = Math.imul(state ^ state >>> 15, state | 1);
    value ^= value + Math.imul(value ^ value >>> 7, value | 61);
    return ((value ^ value >>> 14) >>> 0) / 4294967296;
  };
}

function shuffled(values, random) {
  const result = [...values];
  for (let index = result.length - 1; index > 0; index--) {
    const other = Math.floor(random() * (index + 1));
    [result[index], result[other]] = [result[other], result[index]];
  }
  return result;
}

function insideBounds(point, bounds) {
  return point.x >= bounds.x && point.y >= bounds.y
    && point.x < bounds.x + bounds.width && point.y < bounds.y + bounds.height;
}

function roomCells(bounds, shape) {
  const cells = [];
  for (let y = 0; y < bounds.height; y++) {
    for (let x = 0; x < bounds.width; x++) {
      if (shape === 'alcove' && x >= Math.ceil(bounds.width / 2) && y < Math.floor(bounds.height / 2)) continue;
      if (shape === 'cross' && (x < Math.floor(bounds.width / 2) - 1 || x > Math.floor(bounds.width / 2))
        && (y < Math.floor(bounds.height / 2) - 1 || y > Math.floor(bounds.height / 2))) continue;
      cells.push({x: bounds.x + x, y: bounds.y + y});
    }
  }
  return cells;
}

// Route only through unused stone and the chosen anchor chamber. A branch cannot
// punch through another district, old corridor, or previously generated room.
function branchPath(start, anchor, bounds, footprint, tiles, mainBounds, objects, random) {
  const local = new Set(footprint.map(cellKey));
  const solidObjects = new Set(objects.flatMap(object => {
    const cells = [];
    for (let y = 0; y < object.height; y++) for (let x = 0; x < object.width; x++) cells.push(cellKey({x: object.x + x, y: object.y + y}));
    return cells;
  }));
  const directions = shuffled([[0, -1], [-1, 0], [1, 0], [0, 1]], random);
  const queue = [start], parents = new Map([[cellKey(start), null]]);
  for (let index = 0; index < queue.length; index++) {
    const point = queue[index];
    if (point.x === anchor.center.x && point.y === anchor.center.y) {
      const path = [];
      for (let cursor = point; cursor; cursor = parents.get(cellKey(cursor))) path.push(cursor);
      return path.reverse();
    }
    for (const [dx, dy] of directions) {
      const next = {x: point.x + dx, y: point.y + dy}, key = cellKey(next);
      if (next.x < 1 || next.x >= WIDTH - 1 || next.y < 1 || next.y >= HEIGHT - 1 || parents.has(key) || solidObjects.has(key)) continue;
      const anchorCell = insideBounds(next, anchor);
      if (insideBounds(next, bounds) && !local.has(key)) continue;
      if (!anchorCell && (!tiles[next.y * WIDTH + next.x].blocked || mainBounds.some(room => insideBounds(next, room)))) continue;
      parents.set(key, point); queue.push(next);
    }
  }
  return null;
}

function allOpenConnected(tiles, entrance) {
  const seen = new Set([cellKey(entrance)]), queue = [entrance];
  for (let index = 0; index < queue.length; index++) {
    const point = queue[index];
    for (const [dx, dy] of [[0, -1], [-1, 0], [1, 0], [0, 1]]) {
      const next = {x: point.x + dx, y: point.y + dy}, key = cellKey(next);
      if (next.x < 0 || next.x >= WIDTH || next.y < 0 || next.y >= HEIGHT || seen.has(key) || tiles[next.y * WIDTH + next.x].blocked) continue;
      seen.add(key); queue.push(next);
    }
  }
  return tiles.filter(tile => !tile.blocked).every(tile => seen.has(cellKey(tile)));
}

function addBranchObjects(location, archetype, library, tiles, reserved, entrance, random) {
  const objects = [];
  for (const objectId of shuffled(archetype.allowedAssetIds ?? archetype.objectIds, random).slice(0, 3)) {
    const asset = library.objects.find(object => object.id === objectId);
    if (!asset) throw new Error(`Unknown optional-room object: ${objectId}`);
    const native = asset.gridFootprint.map(Math.ceil);
    const rotations = shuffled([0, 90], random);
    let placed = false;
    for (const rotationDegrees of rotations) {
      const [width, height] = rotationDegrees ? [native[1], native[0]] : native;
      for (const point of shuffled(location.cells, random)) {
        if (placed) break;
        const footprint = [];
        for (let y = 0; y < height; y++) for (let x = 0; x < width; x++) footprint.push({x: point.x + x, y: point.y + y});
        if (footprint.some(cell => !insideBounds(cell, location) || !location.cells.some(open => cellKey(open) === cellKey(cell)) || reserved.has(cellKey(cell)) || tiles[cell.y * WIDTH + cell.x].blocked)) continue;
        for (const cell of footprint) tiles[cell.y * WIDTH + cell.x].blocked = true;
        if (!allOpenConnected(tiles, entrance)) {
          for (const cell of footprint) tiles[cell.y * WIDTH + cell.x].blocked = false;
          continue;
        }
        const bounds = asset.visibleBounds;
        objects.push({id: `${location.id}.object.${objects.length}`, assetId: asset.id, assetPath: asset.asset.path,
          ...point, width, height, rotationDegrees, blocksMovement: true, regionId: location.id,
          sourceVisibleBounds: [bounds[0], bounds[1], bounds[2] - bounds[0], bounds[3] - bounds[1]], fit: 'contain-uniform'});
        footprint.forEach(cell => reserved.add(cellKey(cell))); placed = true;
      }
      if (placed) break;
    }
  }
  return objects;
}

function addOptionalLocations(floor, library, catalog, tiles, regionBounds, presentationObjects, entrance, discoveries, hash) {
  if (!catalog) return {generatedLocations: [], branchLinks: [], branchObjects: []};
  if (catalog.schemaVersion !== 1 || !Array.isArray(catalog.archetypes) || catalog.minRooms < 4 || catalog.maxRooms > 8 || catalog.minRooms > catalog.maxRooms) throw new Error('Invalid optional First Floor location catalog.');
  const random = seededRandom(hash ^ 0x51de1001);
  const target = catalog.minRooms + Math.floor(random() * (catalog.maxRooms - catalog.minRooms + 1));
  const generatedLocations = [], branchLinks = [], branchObjects = [];
  const mainBounds = [...regionBounds];
  for (const archetype of shuffled(catalog.archetypes, random)) {
    if (generatedLocations.length >= target) break;
    if (!archetype.id || !Array.isArray(archetype.anchorRegionIds) || !Array.isArray(archetype.allowedAssetIds ?? archetype.objectIds) || !archetype.loot?.itemId) throw new Error('Invalid optional location archetype.');
    const anchors = shuffled(mainBounds.filter(room => archetype.anchorRegionIds.includes(room.id)), random);
    for (let attempt = 0; attempt < 240 && anchors.length; attempt++) {
      const anchor = anchors[attempt % anchors.length];
      const width = archetype.minWidth + Math.floor(random() * (archetype.maxWidth - archetype.minWidth + 1));
      const height = archetype.minHeight + Math.floor(random() * (archetype.maxHeight - archetype.minHeight + 1));
      if (width < 3 || width > 9 || height < 3 || height > 8) throw new Error('Optional room exceeds footprint bounds.');
      const bounds = {x: 1 + Math.floor(random() * (WIDTH - width - 2)), y: 1 + Math.floor(random() * (HEIGHT - height - 2)), width, height};
      const center = {x: bounds.x + Math.floor(width / 2), y: bounds.y + Math.floor(height / 2)};
      if (Math.abs(center.x - anchor.center.x) + Math.abs(center.y - anchor.center.y) > 18) continue;
      let unused = true;
      for (let y = bounds.y - 1; y <= bounds.y + height; y++) for (let x = bounds.x - 1; x <= bounds.x + width; x++) {
        if (!tiles[y * WIDTH + x].blocked || regionBounds.some(room => insideBounds({x, y}, room))) unused = false;
      }
      if (!unused) continue;
      const shape = archetype.shape ?? 'rect', cells = roomCells(bounds, shape);
      const path = branchPath(center, anchor, bounds, cells, tiles, regionBounds, [...presentationObjects, ...branchObjects], random);
      if (!path || path.length > 32) continue;
      const id = `book1.side.${archetype.id}`;
      const objective = {id: `${id}.cache`, label: archetype.label, ...center};
      const location = {...bounds, id, label: archetype.label, description: archetype.description, center,
        generated: true, optional: true, archetypeId: archetype.id, anchorRegionId: anchor.id,
        canonStatus: archetype.canonStatus ?? 'inferred-game-adaptation', evidenceStatus: archetype.evidenceStatus, sourceIds: archetype.sourceIds, shape, cells, objective};
      for (const cell of [...cells, ...path]) tiles[cell.y * WIDTH + cell.x].blocked = false;
      if (!allOpenConnected(tiles, entrance)) throw new Error('Optional room carving disconnected the floor.');
      const reserved = new Set([center, ...path].map(cellKey));
      branchObjects.push(...addBranchObjects(location, archetype, library, tiles, reserved, entrance, random));
      discoveries.push({id: objective.id, label: archetype.label, description: `${archetype.description} Optional, procedurally placed game adaptation; exact rooms and supplies are invented.`,
        kind: 'cache', itemId: archetype.loot.itemId, count: archetype.loot.count ?? 1, ...center});
      generatedLocations.push(location); regionBounds.push(location);
      branchLinks.push({id: `${id}.passage`, from: anchor.id, to: id, path,
        requiredObjectiveIds: [], relation: 'game-adaptation', generated: true});
      break;
    }
  }
  if (generatedLocations.length < catalog.minRooms) throw new Error('Unable to place enough connected optional First Floor locations.');
  return {generatedLocations, branchLinks, branchObjects};
}

/** Persist the actual reusable tile and whole-object components in one descriptor. */
function createPlayableVisuals(tiles, objects) {
  const componentCells = new Set();
  const components = objects.map(object => {
    for (let y = 0; y < object.height; y++) for (let x = 0; x < object.width; x++) {
      componentCells.add(cellKey({x: object.x + x, y: object.y + y}));
    }
    return {
      id: object.id, assetId: object.assetId, x: object.x, y: object.y,
      width: object.width, height: object.height,
      rotation: ((object.rotationDegrees ?? 0) / 90 + 4) % 4,
      layer: object.layer === 'underlay' ? 'underlay' : 'props',
      blocksMovement: object.blocksMovement === true,
    };
  });
  // Solid props still occupy canonical blocked cells, but stand on ground rather
  // than becoming synthetic walls. Structural walls bound the remaining floor.
  const floors = tiles.filter(tile => !tile.blocked || componentCells.has(cellKey(tile)));
  const floorKeys = new Set(floors.map(cellKey));
  const pieces = [];
  for (const floor of floors) {
    pieces.push({cell: 0, x2: floor.x * 2, y2: floor.y * 2, rotation: 0, layer: 'ground'});
    for (const [dx, dy, cell, rotation] of [[0, -1, 6, 0], [-1, 0, 7, 0], [1, 0, 7, 2], [0, 1, 7, 3]]) {
      if (!floorKeys.has(cellKey({x: floor.x + dx, y: floor.y + dy}))) {
        pieces.push({cell, x2: floor.x * 2 + dx, y2: floor.y * 2 + dy, rotation, layer: 'structures'});
      }
    }
  }
  return {schemaVersion: 1, styleId: 'pocket-dungeon', kitId: 'starter-dungeon', pieces,
    componentLibraryId: 'top-down-object-kit', components};
}

export function getBookOneFloorPlayable(floor, library, archetypes) {
  if (!floor?.regions?.length || floor.regions.length > 16) throw new Error('Unsupported First Floor regions.');
  const tiles = Array.from({length: WIDTH * HEIGHT}, (_, index) => ({
    x: index % WIDTH, y: Math.floor(index / WIDTH), blocked: true, tags: [],
  }));
  const hash = bookOneSeedNumber(floor.seed);
  const {centers, regionBounds} = createDistricts(floor, tiles);
  const links = carveConnections(floor, centers, tiles, hash);
  const entrance = {...centers.get(floor.entryRegionId)};
  const exit = {...centers.get(floor.exitRegionId)};
  const playerSpawns = [
    {...entrance}, {x: entrance.x + 1, y: entrance.y},
    {x: entrance.x, y: entrance.y + 1}, {x: entrance.x + 1, y: entrance.y + 1},
  ];
  const {enemies, groups, discoveries} = createEncountersAndDiscoveries(floor, centers, regionBounds);
  const presentationObjects = placeWholeObjects(floor, library, centers, tiles, [
    entrance, exit, ...playerSpawns, ...enemies, ...discoveries, ...links.flatMap(link => link.path),
  ]);
  const {generatedLocations, branchLinks, branchObjects} = addOptionalLocations(
    floor, library, archetypes, tiles, regionBounds, presentationObjects, entrance, discoveries, hash,
  );
  links.push(...branchLinks);
  presentationObjects.push(...branchObjects);
  const map = {
    schemaVersion: 1, width: WIDTH, height: HEIGHT,
    label: `Book 1 / Floor 1 / ${floor.seed}`.slice(0, 100),
    tiles, placements: [], playerSpawns, enemies,
    visuals: createPlayableVisuals(tiles, presentationObjects),
  };
  const floorPlan = {
    schemaVersion: 1, seed: hash & 0x7fffffff, map, entrance, exit,
    groups, discoveries, mechanisms: [],
  };
  return {
    floorPlan, regionBounds, links, presentationObjects, generatedLocations,
    adaptationNote: 'Continuous 40 × 32 tactical scale: compact chambers and inferred connecting passages. The source-linked district route stays fixed. Seeds add optional chambers with varied positions, footprints, shapes, thematic anchor passages and supplies; these extra locations are inferred game adaptations, not newly discovered canonical places. Existing enemy kits stand in for Book 1 encounters; this does not run the separate boss scenarios. All required discoveries and tactical encounters unlock the exit. Atlas passage objective locks are not applied in this combat map. The playable game uses these same saved whole-object components over reusable ground and wall tiles; terrain and component footprints share canonical collision. The optional roster is a gameplay adaptation.',
  };
}
