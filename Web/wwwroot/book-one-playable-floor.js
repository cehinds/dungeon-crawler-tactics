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

function seedNumber(seed) {
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

export function getBookOneFloorPlayable(floor, library) {
  if (!floor?.regions?.length || floor.regions.length > 16) throw new Error('Unsupported First Floor regions.');
  const tiles = Array.from({length: WIDTH * HEIGHT}, (_, index) => ({
    x: index % WIDTH, y: Math.floor(index / WIDTH), blocked: true, tags: [],
  }));
  const hash = seedNumber(floor.seed);
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
  const map = {
    schemaVersion: 1, width: WIDTH, height: HEIGHT,
    label: `Book 1 / Floor 1 / ${floor.seed}`.slice(0, 100),
    tiles, placements: [], playerSpawns, enemies,
  };
  const floorPlan = {
    schemaVersion: 1, seed: hash & 0x7fffffff, map, entrance, exit,
    groups, discoveries, mechanisms: [],
  };
  return {
    floorPlan, regionBounds, links, presentationObjects,
    adaptationNote: 'Continuous 40 × 32 tactical scale: compact chambers and inferred connecting passages. District positions stay fixed; seeds vary corridor bends and regional enemy templates. Existing enemy kits stand in for Book 1 encounters; this does not run the separate boss scenarios. All required discoveries and tactical encounters unlock the exit. Atlas passage objective locks are not applied in this combat map. Whole PNG objects decorate this atlas; Play retains their exact blocked cells and uses the existing game art. The optional roster is a gameplay adaptation.',
  };
}
