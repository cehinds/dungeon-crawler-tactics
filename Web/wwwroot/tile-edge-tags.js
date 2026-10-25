// Visual seam metadata only; these helpers never change gameplay collision.
export const SIDES = Object.freeze(['north', 'east', 'south', 'west']);
const TAG = /^[a-z][a-z0-9]*(?:-[a-z0-9]+)*(?:\.[a-z][a-z0-9]*(?:-[a-z0-9]+)*)+$(?![\s\S])/;
const isConnector = tag => TAG.test(tag) && tag.startsWith('join.');
function turns(value) {
  if (!Number.isInteger(value)) throw new Error('Tile edge rotation must be an integer number of quarter turns.');
  return ((value % 4) + 4) % 4;
}
export function edgeTagsForRotation(asset, quarterTurns = 0) {
  const rotation = turns(quarterTurns), edges = asset?.edges;
  if (!edges || Object.keys(edges).length !== 4 || SIDES.some(side => !Object.hasOwn(edges, side))) throw new Error(`Tile ${asset?.id || '(unknown)'} is missing valid north/east/south/west edge metadata.`);
  const result = {};
  for (let index = 0; index < 4; index++) {
    const tags = edges[SIDES[index]];
    if (!Array.isArray(tags) || tags.some(tag => typeof tag !== 'string' || !TAG.test(tag)) || new Set(tags).size !== tags.length || tags.filter(tag => isConnector(tag)).length !== 1 || tags.some(tag => tag.startsWith('join.') && !isConnector(tag))) throw new Error(`Tile ${asset.id || '(unknown)'} has invalid ${SIDES[index]} edge tags: expected exactly one valid join.<name> connector.`);
    result[SIDES[(index + rotation) % 4]] = [...tags];
  }
  return result;
}
// Rotations are clockwise quarter turns for each asset, before testing opposite sides.
export function sharedEdgeCompatibility(a, side, b, rotations = {}) {
  const index = SIDES.indexOf(side);
  if (index < 0) throw new Error(`Unknown tile edge side: ${side}.`);
  const tags = edgeTagsForRotation(a, rotations.a ?? 0)[side];
  const neighborTags = edgeTagsForRotation(b, rotations.b ?? 0)[SIDES[(index + 2) % 4]];
  const connector = tags.find(tag => isConnector(tag)), neighborConnector = neighborTags.find(tag => isConnector(tag));
  const ignored = connector === 'join.overlay' || neighborConnector === 'join.overlay';
  const compatible = !ignored && connector !== 'join.manual' && neighborConnector !== 'join.manual' && connector === neighborConnector;
  return { compatible, ignored, reason: ignored ? 'overlay' : compatible ? 'matching connectors' : connector === 'join.manual' || neighborConnector === 'join.manual' ? 'manual connection requires review' : 'different connectors', tags, neighborTags };
}
export function validateFloorConnections(floor) {
  const cells = new Map(), conflicts = [];
  for (const piece of floor) {
    if (piece.asset?.role !== 'ground') continue;
    const x = piece.px / 128, y = piece.py / 128, rotation = (piece.angle || 0) / (Math.PI / 2);
    if (!Number.isInteger(x) || !Number.isInteger(y)) throw new Error('Floor seam validation requires positions on the 128 pixel grid.');
    const quarterTurns = Math.round(rotation);
    if (Math.abs(rotation - quarterTurns) > 1e-8) throw new Error('Floor seam validation requires quarter-turn rotations.');
    edgeTagsForRotation(piece.asset, quarterTurns);
    cells.set(`${x},${y}`, { piece, x, y, quarterTurns });
  }
  for (const { piece, x, y, quarterTurns } of cells.values()) {
    for (const [side, dx, dy] of [['east', 1, 0], ['south', 0, 1]]) {
      const neighbor = cells.get(`${x + dx},${y + dy}`);
      if (!neighbor) continue;
      const result = sharedEdgeCompatibility(piece.asset, side, neighbor.piece.asset, { a: quarterTurns, b: neighbor.quarterTurns });
      if (!result.compatible && !result.ignored) conflicts.push({ x, y, side, neighborX: neighbor.x, neighborY: neighbor.y, tags: result.tags, neighborTags: result.neighborTags });
    }
  }
  return conflicts;
}
