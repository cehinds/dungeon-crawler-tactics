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
function hashText(value) { let hash = 2166136261; for (const character of value) hash = Math.imul(hash ^ character.charCodeAt(0), 16777619); return hash >>> 0; }
const key = (x, y) => `${x},${y}`;
export function buildArtScene(room, art, varied = true) {
  const assets = art.manifest.assets, floorAssets = assets.filter(asset => asset.role === 'ground').slice(0, 4);
  const north = assets.find(asset => asset.squareLayout === 'north-wall' && asset.role === 'wall');
  const west = assets.find(asset => asset.squareLayout === 'west-wall');
  const door = assets.find(asset => asset.role === 'door' && asset.cell === 12);
  const stairs = assets.find(asset => asset.role === 'stairs' && asset.cell === 15) || assets.find(asset => asset.role === 'stairs');
  const props = assets.filter(asset => asset.role === 'prop');
  const solidProps = props.filter(asset => !/rug|carpet|threshold|stairwell|stairs|footprint|paving|floor|trail|mist|path/i.test(asset.label));
  const obstacles = solidProps.length ? solidProps : props;
  const walls = new Set(room.placements.filter(piece => piece.kind === 'wall').map(piece => key(piece.x, piece.y)));
  const floor = [], structures = [], decorations = [], used = new Set();
  const roomStyles = room.rooms.map((region, index) => ({ region, index, asset: floorAssets[varied ? index % floorAssets.length : 0] }));
  const owner = (x, y) => roomStyles.find(({ region }) => x >= region.x && x < region.x + region.width && y >= region.y && y < region.y + region.height);
  const add = (list, asset, x, y, angle = 0, kind = '') => { if (asset) list.push({ asset, px: x, py: y, angle, kind }); };
  for (let y = 0; y < room.height; y++) for (let x = 0; x < room.width; x++) {
    if (walls.has(key(x, y))) continue;
    const style = owner(x, y), base = style?.asset || floorAssets[0];
    // Contiguous two-cell patches add wear without scrambling every floor tile.
    const patch = varied && style && hashText(`${room.seed}:${style.region.theme?.id || style.index}:${Math.floor(x / 2)},${Math.floor(y / 2)}`) % 11 === 0;
    const tile = patch ? floorAssets[(style.index + 1) % floorAssets.length] : base;
    add(floor, tile, x * 128, y * 128);
    const solid = (dx, dy) => x + dx < 0 || y + dy < 0 || x + dx >= room.width || y + dy >= room.height || walls.has(key(x + dx, y + dy));
    if (solid(0, -1)) add(structures, north, x * 128, y * 128 - 64);
    if (solid(-1, 0)) add(structures, west, x * 128 - 64, y * 128);
    if (solid(1, 0)) add(structures, west, x * 128 + 64, y * 128, Math.PI);
    if (solid(0, 1)) add(structures, west, x * 128, y * 128 + 64, -Math.PI / 2);
  }
  const protectedCells = new Set([...(room.generation?.protectedCells || []), ...(room.clearRoute || []), room.entrance || room.start, room.exit].filter(Boolean).map(p => key(p.x, p.y)));
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
  add(decorations, door, entrance.x * 128, entrance.y * 128, 0, 'entrance');
  add(decorations, stairs, room.exit.x * 128, room.exit.y * 128, 0, 'exit');
  structures.sort((a, b) => a.py - b.py || a.px - b.px);
  decorations.sort((a, b) => a.py - b.py || a.px - b.px);
  return { floor, structures, decorations, roomStyles, wallCells: walls };
}
export function drawPiece(context, piece, art) {
  const image = art.images.get(piece.asset.id); if (!image) return;
  const anchor = piece.asset.anchor || { x: 128, y: 192 };
  context.save(); context.translate(piece.px, piece.py); context.rotate(piece.angle);
  context.drawImage(image, -anchor.x, -anchor.y, 256, 256); context.restore();
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
    const box = piece.asset.derived, anchor = piece.asset.anchor || { x: 128, y: 192 };
    const left = box.offset.x - anchor.x, top = box.offset.y - anchor.y;
    const cosine = Math.round(Math.cos(piece.angle)), sine = Math.round(Math.sin(piece.angle));
    return [[left, top], [left + box.width, top], [left, top + box.height], [left + box.width, top + box.height]].map(([x, y]) => ({ x: piece.px + x * cosine - y * sine, y: piece.py + x * sine + y * cosine }));
  });
}
