import { edgeTagsForRotation, SIDES } from './tile-edge-tags.js';

const key = (x, y) => `${x},${y}`;
function hash(value) { let n = 2166136261; for (const c of String(value)) n = Math.imul(n ^ c.charCodeAt(0), 16777619); return n >>> 0; }
const connectors = asset => SIDES.map(side => edgeTagsForRotation(asset)[side].find(tag => tag.startsWith('join.')));
export function eligibleFloorAssets(assets) {
  return assets.filter(asset => asset.role === 'ground' && connectors(asset).every(tag => !['join.manual', 'join.overlay'].includes(tag)));
}
export function planFloorMaterials(room, assets, varied = true) {
  const floorAssets = eligibleFloorAssets(assets);
  if (!floorAssets.length) throw new Error('Floor fitting is unsatisfiable: no automatic full-floor candidates.');
  const baseAsset = floorAssets[0], baseEdges = connectors(baseAsset);
  // Authored transition tiles connect material names; reachability only guides
  // preferences. The fitter still has to prove an arrangement fits this room.
  const graph = new Map();
  for (const asset of floorAssets) {
    const names = connectors(asset);
    for (const name of names) {
      if (!graph.has(name)) graph.set(name, new Set());
      for (const neighbor of names) graph.get(name).add(neighbor);
    }
  }
  const reachable = new Set(baseEdges), queue = [...reachable];
  for (let i = 0; i < queue.length; i++) for (const name of graph.get(queue[i]) || []) {
    if (!reachable.has(name)) { reachable.add(name); queue.push(name); }
  }
  const compatible = floorAssets.filter(asset => {
    const names = connectors(asset);
    return names.every(name => name === names[0]) && reachable.has(names[0]);
  });
  const materials = compatible.length ? compatible : [baseAsset];
  const protectedCells = new Set([...(room.generation?.protectedCells || []), ...(room.clearRoute || []), room.entrance || room.start, room.exit].filter(Boolean).map(p => key(p.x, p.y)));
  const roomStyles = room.rooms.map((region, index) => ({ region, index, asset: varied ? materials[hash(`${room.seed}:room:${index}:${region.theme?.id || ''}`) % materials.length] : baseAsset }));
  const owner = (x, y) => roomStyles.find(({ region: r }) => x >= r.x && x < r.x + r.width && y >= r.y && y < r.y + r.height);
  const floorAt = (x, y) => {
    const style = owner(x, y);
    if (!varied || !style || protectedCells.has(key(x, y))) return baseAsset;
    const patchX = Math.floor((x - style.region.x) / 2), patchY = Math.floor((y - style.region.y) / 2);
    const patch = hash(`${room.seed}:wear:${style.index}:${patchX},${patchY}`);
    return patch % 13 === 0 ? materials[patch % materials.length] : style.asset;
  };
  return { floorAssets, baseAsset, roomStyles, owner, protectedCells, floorAt };
}
function openAxis(edges, side) {
  const opposite = SIDES[(SIDES.indexOf(side) + 2) % 4];
  const connector = edges[side].find(tag => tag.startsWith('join.'));
  return edges[side].includes('portal.open') && edges[opposite].includes('portal.open')
    && !['join.manual', 'join.overlay', 'join.wall', 'join.exterior'].includes(connector)
    && edges[opposite].includes(connector);
}
export function selectOpenDoor(assets) {
  let taggedOpen = false;
  const door = assets.find(asset => {
    if (asset.role !== 'door') return false;
    const edges = edgeTagsForRotation(asset);
    if (SIDES.some(side => edges[side].includes('portal.open'))) taggedOpen = true;
    return SIDES.some(side => openAxis(edges, side));
  });
  if (!door) throw new Error(taggedOpen
    ? 'The portal.open entrance door needs opposite open edges with matching walk-through join.<name> connectors.'
    : 'This art kit needs an open entrance door tagged portal.open; closed portals cannot mark a walkable entrance.');
  return door;
}
export function portalRotation(room, door, portal) {
  const blocked = new Set((room.blockedCells || []).map(p => key(p.x, p.y)));
  const route = new Set((room.clearRoute || []).map(p => key(p.x, p.y)));
  const neighbors = [[0,-1],[1,0],[0,1],[-1,0]].map(([dx,dy], side) => ({ x: portal.x + dx, y: portal.y + dy, side }))
    .filter(p => p.x >= 0 && p.y >= 0 && p.x < room.width && p.y < room.height && !blocked.has(key(p.x,p.y)))
    .sort((a,b) => Number(route.has(key(b.x,b.y))) - Number(route.has(key(a.x,a.y))) || a.side-b.side);
  const approach = neighbors[0];
  if (!approach) throw new Error('The entrance portal has no legal approach cell.');
  for (let rotation = 0; rotation < 4; rotation++) {
    const edges = edgeTagsForRotation(door, rotation);
    if (openAxis(edges, SIDES[approach.side])) return rotation * Math.PI / 2;
  }
  throw new Error('The portal.open entrance door needs opposite open edges with matching walk-through join.<name> connectors for its approach.');
}
