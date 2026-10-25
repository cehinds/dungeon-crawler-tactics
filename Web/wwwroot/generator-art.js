import { planFloorMaterials, selectOpenDoor, portalRotation } from './tile-generation-plan.js';
import { validateFloorConnections } from './tile-edge-tags.js';
import { fitFloorTiles } from './tile-edge-solver.js';
// Native square art is a visual authoring layer. Runtime exports use the canonical room kit.
export function revisionURL(path, base, metadata) {
  let hash = 2166136261;
  for (const character of JSON.stringify(metadata)) hash = Math.imul(hash ^ character.charCodeAt(0), 16777619);
  const url = new URL(path, base); url.searchParams.set('v', (hash >>> 0).toString(16)); return url.href;
}
export async function fetchJSON(url) {
  const response = await fetch(url, { cache: 'no-cache' });
  if (!response.ok) throw new Error(`Could not load map resources (HTTP ${response.status}).`);
  return response.json();
}
const manifestCache = new Map(), imageCache = new Map();
function imageFor(url) {
  const cached = imageCache.get(url);
  if (cached) { imageCache.delete(url); imageCache.set(url, cached); return cached; }
  const pending = new Promise((resolve, reject) => {
    const image = new Image(); image.onload = () => resolve(image);
    image.onerror = () => { if (imageCache.get(url) === pending) imageCache.delete(url); reject(new Error('A map tile could not load. Try loading the art again.')); };
    image.src = url;
  });
  imageCache.set(url, pending);
  while (imageCache.size > 96) imageCache.delete(imageCache.keys().next().value);
  return pending;
}
export async function loadArtKit(catalog, catalogURL, kitId, styleId) {
  const kit = catalog.kits.find(item => item.id === kitId), variant = kit?.variants[styleId];
  if (!variant) throw new Error('This environment is unavailable in the selected style.');
  const url = new URL(variant.manifest, catalogURL).href;
  let manifest = manifestCache.get(url);
  if (!manifest) { manifest = await fetchJSON(url); manifestCache.set(url, manifest); }
  if (manifest.grid.projection !== 'orthogonal' || manifest.grid.tileWidth !== 128 || manifest.grid.tileHeight !== 128) throw new Error('This preview needs the square 128 × 128 art kit.');
  const entries = await Promise.all(manifest.assets.map(async asset => [asset.id, await imageFor(revisionURL(asset.file, url, [asset.source, asset.derived]))]));
  return { kit, manifest, images: new Map(entries), manifestURL: url };
}
const key = (x, y) => `${x},${y}`;
export function buildArtScene(room, art, varied = true) {
  const assets = art.manifest.assets;
  const { floorAssets, roomStyles, owner, protectedCells, floorAt } = planFloorMaterials(room, assets, varied);
  const north = assets.find(asset => asset.squareLayout === 'north-wall' && asset.role === 'wall');
  const west = assets.find(asset => asset.squareLayout === 'west-wall');
  const door = selectOpenDoor(assets);
  const stairs = assets.find(asset => asset.role === 'stairs' && asset.cell === 15) || assets.find(asset => asset.role === 'stairs');
  const props = assets.filter(asset => asset.role === 'prop');
  const solidProps = props.filter(asset => !/rug|carpet|threshold|stairwell|stairs|footprint|paving|floor|trail|mist|path/i.test(asset.label));
  const obstacles = solidProps.length ? solidProps : props;
  const walls = new Set(room.placements.filter(piece => piece.kind === 'wall').map(piece => key(piece.x, piece.y)));
  let floor = [];
  const boundaries = [], structures = [], decorations = [], used = new Set();
  const add = (list, asset, x, y, angle = 0, kind = '') => { if (asset) list.push({ asset, px: x, py: y, angle, kind }); };
  for (let y = 0; y < room.height; y++) for (let x = 0; x < room.width; x++) {
    if (walls.has(key(x, y))) continue;
    add(floor, floorAt(x, y), x * 128, y * 128);
    const solid = (dx, dy) => x + dx < 0 || y + dy < 0 || x + dx >= room.width || y + dy >= room.height || walls.has(key(x + dx, y + dy));
    for (const [side, dx, dy, asset, rotation] of [['north', 0, -1, north, 0], ['west', -1, 0, west, 0], ['east', 1, 0, west, 2], ['south', 0, 1, west, 3]]) {
      if (solid(dx, dy) && asset) {
        const candidates = assets.filter(candidate => candidate.role === 'wall' && candidate.squareLayout === asset.squareLayout)
          .map(candidate => ({ asset: candidate, rotation }));
        boundaries.push({ x, y, side, asset, rotation, candidates });
        const offsets = { north: [0,-64], west: [-64,0], east: [64,0], south: [0,64] };
        const [ox, oy] = offsets[side];
        add(structures, asset, x * 128 + ox, y * 128 + oy, rotation === 3 ? -Math.PI / 2 : rotation * Math.PI / 2);
      }
    }
  }
  const { floor: fittedFloor, boundaries: fittedBoundaries = boundaries, ...edgeFit } = fitFloorTiles(floor, floorAssets, { seed: room.seed, boundaries });
  floor = fittedFloor;
  fittedBoundaries.forEach((boundary, index) => {
    structures[index].asset = boundary.asset;
    structures[index].angle = boundary.rotation === 3 ? -Math.PI / 2 : boundary.rotation * Math.PI / 2;
  });
  {
    for (const style of roomStyles) {
      const counts = new Map();
      for (const piece of floor) {
        if (owner(piece.px / 128, piece.py / 128) !== style) continue;
        const entry = counts.get(piece.asset.id) || { asset: piece.asset, count: 0 };
        entry.count++; counts.set(piece.asset.id, entry);
      }
      const dominant = [...counts.values()].sort((a, b) => b.count - a.count || (a.asset.id < b.asset.id ? -1 : a.asset.id > b.asset.id ? 1 : 0))[0];
      if (dominant) style.asset = dominant.asset;
    }
  }
  const conflicts = validateFloorConnections(floor);
  if (conflicts.length) {
    const first = conflicts[0];
    throw new Error(`Incompatible floor edges at (${first.x}, ${first.y}) ${first.side}: ${first.tags.join(', ')} versus ${first.neighborTags.join(', ')} (${conflicts.length} conflicting seams).`);
  }
  const candidates = room.placements.filter(piece => piece.kind === 'decoration');
  const blockedObjects = candidates.filter(piece => piece.blocksMovement);
  // Every canonical obstacle remains visible at its exact gameplay cell.
  blockedObjects.forEach((piece, index) => {
    used.add(key(piece.x, piece.y));
    add(decorations, obstacles[index % obstacles.length], piece.x * 128, piece.y * 128, 0, 'obstacle');
    Object.assign(decorations.at(-1), { cell: { x: piece.x, y: piece.y }, canonicalPlacementId: piece.id });
  });
  const blockedCells = new Set(room.blockedCells.map(cell => key(cell.x, cell.y)));
  // A small set of actual kit landmarks replaces repeated moss/decal scatter.
  for (const style of roomStyles) {
    let positions = candidates.filter(piece => !piece.blocksMovement && owner(piece.x, piece.y)?.index === style.index);
    if (!positions.length) {
      for (let y = style.region.y; y < style.region.y + style.region.height; y++) for (let x = style.region.x; x < style.region.x + style.region.width; x++) if (!blockedCells.has(key(x, y)) && !protectedCells.has(key(x, y)) && !used.has(key(x, y))) positions.push({ x, y });
    }
    positions = positions.filter(p => !protectedCells.has(key(p.x, p.y))).sort((a, b) => a.y - b.y || a.x - b.x);
    const existingObstacles = blockedObjects.filter(piece => owner(piece.x, piece.y)?.index === style.index).length;
    const count = Math.min(positions.length, Math.max(0, (room.density > .27 ? 2 : room.density > 0 ? 1 : 0) - existingObstacles));
    for (let i = 0; i < count; i++) {
      const position = positions[Math.floor((i + .5) * positions.length / count)];
      if (used.has(key(position.x, position.y))) continue;
      used.add(key(position.x, position.y)); add(decorations, props[(style.index * 2 + i) % props.length], position.x * 128, position.y * 128, 0, 'landmark');
    }
  }
  const entrance = room.entrance || room.start;
  add(decorations, door, entrance.x * 128, entrance.y * 128, portalRotation(room, door, entrance), 'entrance');
  add(decorations, stairs, room.exit.x * 128, room.exit.y * 128, 0, 'exit');
  structures.sort((a, b) => a.py - b.py || a.px - b.px);
  decorations.sort((a, b) => a.py - b.py || a.px - b.px);
  return { floor, structures, decorations, roomStyles, wallCells: walls, edgeFit, edgeBoundaries: fittedBoundaries };
}
export function drawPiece(context, piece, art) {
  const image = art.images.get(piece.asset.id); if (!image) return;
  const display = pieceDisplayGeometry(piece.asset);
  context.save(); context.translate(piece.px, piece.py); context.rotate(piece.angle);
  context.scale(display.scale, display.scale);
  context.drawImage(image, display.x, display.y, 256, 256); context.restore();
}

// Upright sprite anchors describe feet, not the center of a square map cell.
// Center props and portals by their visible bounds so they cannot cover the
// neighboring row. Floors and repeating walls retain their exact grid anchors.
export function pieceDisplayGeometry(asset) {
  const box = asset.derived, anchor = asset.anchor || { x: 128, y: 192 };
  if (asset.role === 'prop' || asset.role === 'door') {
    const limit = asset.role === 'prop' ? 112 : 128;
    return { x: -box.offset.x - box.width / 2, y: -box.offset.y - box.height / 2,
      scale: Math.min(1, limit / box.width, limit / box.height) };
  }
  return { x: -anchor.x, y: -anchor.y, scale: 1 };
}

// Authored ambience metadata changes the surrounding light, never the tile pixels.
const moods = {
  'surface-entry': ['#0b1829', '#233c51', 'Winter streets'],
  'starter-dungeon': ['#111a1c', '#394034', 'Warm lantern light'],
  'early-arenas': ['#21180f', '#57412a', 'Dust and arena fire'],
  'industry-menagerie': ['#20140e', '#513222', 'Furnaces and soot'],
  'over-city': ['#111e1c', '#35483c', 'Overgrown city light'],
  'over-city-venues': ['#201b14', '#514534', 'Warm civic interiors'],
  'clubs-guilds': ['#20121f', '#4a2d43', 'Velvet and candlelight'],
  'personal-space': ['#1d1a13', '#4c4935', 'A quiet hearth'],
  'iron-tracks': ['#101821', '#304250', 'Cold tunnel light'],
  'iron-stations': ['#111b24', '#354c59', 'Platform lights'],
  'iron-trains': ['#111a26', '#2e455c', 'Steel and steam'],
  'bubble-desert': ['#2b1a0d', '#80572c', 'Desert sun and sand'],
  'bubble-airship': ['#20180e', '#5f4930', 'Wasteland haze'],
  'bubble-glass': ['#11232a', '#376873', 'Glass and reflected light'],
  'bubble-sea': ['#06172c', '#164c67', 'Deep sea blue'],
  'bubble-necropolis': ['#1a1029', '#48335c', 'Violet grave light'],
  'hunting-jungle': ['#071d13', '#265338', 'Deep jungle shade'],
  'hunting-zockau': ['#102317', '#3c5131', 'Sun through ruined streets'],
  'hunting-river': ['#082124', '#2b5860', 'Cool river light'],
  'hunting-shrines': ['#1a2314', '#4d5930', 'Shrines in the forest'],
  'masquerade': ['#251225', '#62404f', 'A candlelit masquerade'],
  'broadcast-portals': ['#11172b', '#3c466c', 'Studio and portal light'],
  'safe-services': ['#211b12', '#62503b', 'A warm place to rest'],
  'thresholds': ['#10232a', '#3a626e', 'Light beyond the threshold'],
  'great-race-transition': ['#0c202b', '#25647a', 'Blue transition light'],
  'ghost-havana': ['#16102a', '#514064', 'Ghosts in violet dusk'],
  'ghost-cemetery': ['#100e22', '#35324e', 'Moonlit cemetery'],
  'faction-larracos': ['#1c1824', '#51445b', 'A city under siege'],
  'faction-battlefield': ['#251a12', '#64503c', 'Smoke over the battlefield'],
  'race-circuits': ['#101b25', '#315166', 'Circuit floodlights'],
  'parade-horribles': ['#28121b', '#693446', 'A dangerous parade'],
};
export function environmentMood(kitId) {
  const [background, glow, label] = moods[kitId] || moods['starter-dungeon'];
  return { background, glow, label };
}
export function visibleSceneCorners(scene) {
  return [...scene.floor, ...scene.structures, ...scene.decorations].flatMap(piece => {
    const box = piece.asset.derived, display = pieceDisplayGeometry(piece.asset);
    const left = (box.offset.x + display.x) * display.scale, top = (box.offset.y + display.y) * display.scale;
    const width = box.width * display.scale, height = box.height * display.scale;
    const cosine = Math.round(Math.cos(piece.angle)), sine = Math.round(Math.sin(piece.angle));
    return [[left, top], [left + width, top], [left, top + height], [left + width, top + height]].map(([x, y]) => ({ x: piece.px + x * cosine - y * sine, y: piece.py + x * sine + y * cosine }));
  });
}
