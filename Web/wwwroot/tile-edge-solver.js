import { edgeTagsForRotation, validateFloorConnections, sharedEdgeCompatibility, SIDES } from './tile-edge-tags.js';

// A bounded constraint solver for visual floors. It never changes gameplay cells.
export function fitFloorTiles(floor, candidateAssets, { seed = '', maxSearchSteps = 20000, boundaries = [] } = {}) {
  if (!Number.isInteger(maxSearchSteps) || maxSearchSteps < 0) throw new Error('Floor fitting search budget must be a nonnegative integer.');
  const connectors = (asset, rotation) => {
    const tags = edgeTagsForRotation(asset, rotation);
    return SIDES.map(side => tags[side].find(tag => tag.startsWith('join.')));
  };
  const eligible = candidateAssets.filter(asset => {
    const edges = connectors(asset, 0);
    return asset.role === 'ground' && edges.every(tag => tag !== 'join.manual' && tag !== 'join.overlay');
  });
  const conflicts = validateFloorConnections(floor);
  const cells = new Map(), links = [];
  floor.forEach((piece, index) => {
    if (piece.asset.role !== 'ground') throw new Error('Floor fitting requires full ground tiles.');
    const cell = `${piece.px / 128},${piece.py / 128}`;
    if (cells.has(cell)) throw new Error(`Duplicate floor cell ${cell}.`);
    cells.set(cell, index);
  });
  floor.forEach((piece, index) => {
    const x = piece.px / 128, y = piece.py / 128;
    for (const [side, dx, dy] of [[1, 1, 0], [2, 0, 1]]) {
      const neighbor = cells.get(`${x + dx},${y + dy}`);
      if (neighbor !== undefined) links.push([index, neighbor, side]);
    }
  });
  const boundaryConstraints = boundaries.map(boundary => {
    const index = cells.get(`${boundary.x},${boundary.y}`), side = SIDES.indexOf(boundary.side);
    if (index === undefined || side < 0) throw new Error('Floor fitting boundary requires an existing floor cell and valid side.');
    const edges = connectors(boundary.asset, boundary.rotation ?? 0);
    return { ...boundary, index, sideIndex: side, connector: edges[(side + 2) % 4] };
  });
  const boundaryCompatible = boundary => sharedEdgeCompatibility(floor[boundary.index].asset, boundary.side, boundary.asset, {
    a: Math.round((floor[boundary.index].angle || 0) / (Math.PI / 2)), b: boundary.rotation ?? 0
  }).compatible;
  const stats = { adjustedTiles: 0, rotatedTiles: 0, checkedJoins: links.length, checkedBoundaries: boundaries.length, searchSteps: 0 };
  const automaticFloor = floor.every(piece => connectors(piece.asset, 0).every(tag => tag !== 'join.manual' && tag !== 'join.overlay'));
  if (automaticFloor && !conflicts.length && boundaryConstraints.every(boundaryCompatible)) return { floor, ...stats };
  if (!eligible.length) throw new Error('Floor fitting is unsatisfiable: no automatic full-floor candidates.');
  const variants = eligible.flatMap(asset => Array.from({ length: 4 }, (_, rotation) => ({ asset, rotation, edges: connectors(asset, rotation) })));
  let hash = 2166136261;
  for (const char of String(seed)) hash = Math.imul(hash ^ char.charCodeAt(0), 16777619);
  const rank = value => { let n = (value ^ hash) >>> 0; n = Math.imul(n ^ n >>> 16, 0x45d9f3b); return (n ^ n >>> 16) >>> 0; };
  const domains = floor.map((piece, index) => variants.map((_, i) => i).sort((a, b) => {
    const cost = v => (v.asset.id === piece.asset.id ? 0 : 2) + (v.rotation === (((Math.round((piece.angle || 0) / (Math.PI / 2)) % 4) + 4) % 4) ? 0 : 1);
    return cost(variants[a]) - cost(variants[b]) || rank(a + index * variants.length) - rank(b + index * variants.length) || a - b;
  }));
  for (const boundary of boundaryConstraints) {
    domains[boundary.index] = domains[boundary.index].filter(v => variants[v].edges[boundary.sideIndex] === boundary.connector && !['join.manual', 'join.overlay'].includes(boundary.connector));
    if (!domains[boundary.index].length) throw new Error('Floor fitting is unsatisfiable: no candidate matches a wall boundary.');
  }
  const adjacency = floor.map(() => []);
  links.forEach(([a, b, side]) => { adjacency[a].push([b, side]); adjacency[b].push([a, (side + 2) % 4]); });
  let steps = 0;
  const spend = () => { if (++steps > maxSearchSteps) throw new Error(`Floor fitting search budget exhausted (${maxSearchSteps} steps).`); };
  function propagate(state, queue) {
    for (let cursor = 0; cursor < queue.length; cursor++) {
      const changed = queue[cursor];
      for (const [neighbor, side] of adjacency[changed]) {
        spend();
        const opposite = (side + 2) % 4;
        const supported = new Set(state[changed].map(v => variants[v].edges[side]));
        const next = state[neighbor].filter(v => supported.has(variants[v].edges[opposite]));
        if (!next.length) return false;
        if (next.length !== state[neighbor].length) { state[neighbor] = next; queue.push(neighbor); }
      }
    }
    return true;
  }
  function solve(state) {
    let target = -1;
    for (let i = 0; i < state.length; i++) if (state[i].length > 1 && (target < 0 || state[i].length < state[target].length)) target = i;
    if (target < 0) return state;
    for (const variant of state[target]) {
      spend();
      const next = state.slice(); next[target] = [variant];
      if (propagate(next, [target])) { const result = solve(next); if (result) return result; }
    }
    return null;
  }
  const solution = propagate(domains, floor.map((_, i) => i)) && solve(domains);
  if (!solution) throw new Error('Floor fitting is unsatisfiable: no compatible arrangement of candidate tiles and rotations.');
  const fitted = floor.map((piece, index) => {
    const variant = variants[solution[index][0]], angle = variant.rotation * Math.PI / 2;
    const rotationChanged = Math.abs(Math.sin(((piece.angle || 0) - angle) / 2)) > 1e-8;
    const changed = variant.asset.id !== piece.asset.id || rotationChanged;
    if (changed) stats.adjustedTiles++;
    if (rotationChanged) stats.rotatedTiles++;
    return changed ? { ...piece, asset: variant.asset, angle } : piece;
  });
  return { floor: fitted, ...stats, searchSteps: steps };
}
