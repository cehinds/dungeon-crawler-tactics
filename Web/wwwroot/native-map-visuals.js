// Portable presentation metadata; this never changes combat tiles or legality.
export const NATIVE_TILE_SIZE = 128;
const layers = new Set(['ground', 'structures', 'props']);
const slug = value => typeof value === 'string' && value.length <= 64 && /^[a-z0-9]+(?:-[a-z0-9]+)*$/.test(value);
const require = (value, message) => { if (!value) throw new Error(message); };
const quarter = value => ((value % 4) + 4) % 4;

export function nativeProject(x, y, rotation = 0) {
  const q = quarter(rotation);
  const point = q === 1 ? { x: -y * 128, y: x * 128 } : q === 2 ? { x: -x * 128, y: -y * 128 }
    : q === 3 ? { x: y * 128, y: -x * 128 } : { x: x * 128, y: y * 128 };
  return { x: point.x || 0, y: point.y || 0 };
}

export function nativePick(px, py, width, height, rotation = 0) {
  const point = nativeProject(px / 128, py / 128, quarter(4 - rotation));
  const x = Math.round(point.x / 128), y = Math.round(point.y / 128);
  return x >= 0 && y >= 0 && x < width && y < height ? { x: x || 0, y: y || 0 } : null;
}

export function validateNativeVisuals(visuals, width, height, tiles) {
  require(Number.isInteger(width) && width >= 6 && width <= 20 && Number.isInteger(height) && height >= 6 && height <= 16, 'Invalid native map dimensions.');
  require(visuals?.schemaVersion === 1 && slug(visuals.styleId) && slug(visuals.kitId), 'Invalid native map art identifier.');
  require(Array.isArray(visuals.pieces) && visuals.pieces.length > 0 && visuals.pieces.length <= width * height * 12, 'Invalid native map art count.');
  const floors = new Set();
  for (const piece of visuals.pieces) {
    require(piece && Number.isInteger(piece.cell) && piece.cell >= 0 && piece.cell < 24
      && Number.isInteger(piece.x2) && piece.x2 >= -1 && piece.x2 < width * 2
      && Number.isInteger(piece.y2) && piece.y2 >= -1 && piece.y2 < height * 2
      && Number.isInteger(piece.rotation) && piece.rotation >= 0 && piece.rotation < 4 && layers.has(piece.layer), 'Invalid native map art placement.');
    require((piece.cell < 6) === (piece.layer === 'ground'), 'Native floor art must use the ground layer.');
    if (piece.layer === 'ground') {
      const key = `${piece.x2},${piece.y2}`;
      require(piece.x2 >= 0 && piece.y2 >= 0 && piece.x2 % 2 === 0 && piece.y2 % 2 === 0 && !floors.has(key), 'Invalid or duplicate native floor position.');
      floors.add(key);
    }
  }
  require(floors.size > 0, 'Native map art needs a floor.');
  if (tiles) {
    const blocked = new Set(tiles.filter(tile => tile.blocked).map(tile => `${tile.x},${tile.y}`));
    for (let y = 0; y < height; y++) for (let x = 0; x < width; x++) require(blocked.has(`${x},${y}`) || floors.has(`${x * 2},${y * 2}`), 'Native map art must cover every walkable cell.');
  }
  return visuals;
}

export function serializeNativeVisuals(scene, { styleId, kitId, width, height, tiles }) {
  const pieces = [];
  for (const [group, layer] of [['floor', 'ground'], ['structures', 'structures'], ['decorations', 'props']]) {
    require(Array.isArray(scene?.[group]), 'The preview scene is incomplete.');
    for (const piece of scene[group]) {
      const turns = (piece.angle || 0) / (Math.PI / 2);
      require(Math.abs(turns - Math.round(turns)) < 1e-7, 'Native map art must use quarter turns.');
      pieces.push({ cell: piece.asset.cell, x2: piece.px / 64, y2: piece.py / 64, rotation: quarter(Math.round(turns)), layer });
    }
  }
  return validateNativeVisuals({ schemaVersion: 1, styleId, kitId, pieces }, width, height, tiles);
}

export function nativeSceneFromVisuals(visuals, art, width, height, tiles) {
  validateNativeVisuals(visuals, width, height, tiles);
  const assets = new Map(art.manifest.assets.map(asset => [asset.cell, asset]));
  const scene = { floor: [], structures: [], decorations: [] };
  for (const piece of visuals.pieces) {
    const asset = assets.get(piece.cell);
    require(asset && art.images.has(asset.id), 'This dungeon’s tile art is incomplete.');
    const group = piece.layer === 'ground' ? scene.floor : piece.layer === 'structures' ? scene.structures : scene.decorations;
    group.push({ asset, px: piece.x2 * 64, py: piece.y2 * 64, angle: piece.rotation * Math.PI / 2 });
  }
  return scene;
}
