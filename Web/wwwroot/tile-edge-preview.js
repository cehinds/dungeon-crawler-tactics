import { SIDES, listFloorConnections, sharedEdgeCompatibility } from './tile-edge-tags.js';

const reports = new WeakMap();
export const EDGE_DIRECTIONS = Object.freeze({ north: [0, -1], east: [1, 0], south: [0, 1], west: [-1, 0] });
const key = (x, y) => `${x},${y}`;
const quarterTurns = piece => Math.round((piece.angle || 0) / (Math.PI / 2));

export function sceneConnections(scene) {
  if (reports.has(scene)) return reports.get(scene);
  const cells = new Map(scene.floor.map(piece => [key(piece.px / 128, piece.py / 128), piece]));
  const connections = listFloorConnections(scene.floor).map(join => ({ ...join, kind: 'floor' }));
  for (const wall of scene.edgeBoundaries || []) {
    const piece = cells.get(key(wall.x, wall.y));
    if (!piece) continue;
    connections.push({ x: wall.x, y: wall.y, side: wall.side, kind: 'wall',
      ...sharedEdgeCompatibility(piece.asset, wall.side, wall.asset, { a: quarterTurns(piece), b: wall.rotation }) });
  }
  const report = { cells, connections };
  reports.set(scene, report);
  return report;
}

export function inspectPlacedTile(scene, x, y) {
  const { cells } = sceneConnections(scene), piece = cells.get(key(x, y));
  if (!piece) return null;
  const edges = SIDES.map(side => {
    const [dx, dy] = EDGE_DIRECTIONS[side], neighbor = cells.get(key(x + dx, y + dy));
    const wall = (scene.edgeBoundaries || []).find(item => item.x === x && item.y === y && item.side === side);
    if (!neighbor && !wall) return { side, kind: 'boundary', compatible: false, reason: 'No adjacent floor or wall' };
    return { side, kind: neighbor ? 'floor' : 'wall',
      ...sharedEdgeCompatibility(piece.asset, side, neighbor?.asset || wall.asset,
        { a: quarterTurns(piece), b: neighbor ? quarterTurns(neighbor) : wall.rotation }) };
  });
  return { piece, edges };
}

// Pointer coordinates are CSS pixels, using the same camera transform as drawing.
export function pickPreviewCell(px, py, camera) {
  if (!camera || camera.scale <= 0) return null;
  const x = (px - camera.offsetX) / camera.scale, y = (py - camera.offsetY) / camera.scale;
  const cosine = Math.round(Math.cos(camera.angle)), sine = Math.round(Math.sin(camera.angle));
  return { x: Math.round((x * cosine + y * sine) / 128) || 0, y: Math.round((-x * sine + y * cosine) / 128) || 0 };
}
