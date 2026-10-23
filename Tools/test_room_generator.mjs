import assert from 'node:assert/strict';
import { readFile, access } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
// The browser module stays .js for static hosting; a data URL imports its pure exports in Node
// without changing package settings or installing a DOM shim.
const source = await readFile(resolve(root, 'Web/wwwroot/room-kit.js'), 'utf8');
const { generateRoom, findRoute, validateManifest, seededRandom } = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
const manifest = JSON.parse(await readFile(resolve(root, 'Web/wwwroot/assets/room-kit/manifest.json'), 'utf8'));
validateManifest(manifest);
for (const asset of manifest.assets) await access(resolve(root, 'Web/wwwroot/assets/room-kit', asset.file));
let checks = 0;
const check = (condition, message) => { assert.ok(condition, message); checks++; };
const options = { seed: 'crawler-13', width: 10, height: 8, density: 0.3 };
const baseline = generateRoom(manifest, options);
check(JSON.stringify(baseline) === JSON.stringify(generateRoom(manifest, options)), 'same inputs produce byte-for-byte deterministic placement data');
check(JSON.stringify(baseline.placements) !== JSON.stringify(generateRoom(manifest, { ...options, seed: 'another-room' }).placements), 'another seed changes the assembled room');
check(baseline.placements.filter(p => p.layer === 'floor').length === options.width * options.height, 'every grid cell receives exactly one floor');
check(new Set(baseline.placements.map(p => p.id)).size === baseline.placements.length, 'placement IDs remain unique');
check(baseline.kind === 'dungeon-room-authoring' && baseline.schemaVersion === 1, 'export explicitly identifies authoring data');
const randomA = seededRandom('unicode-🐈'), randomB = seededRandom('unicode-🐈');
check(Array.from({ length: 40 }, () => randomA()).every(value => value === randomB() && value >= 0 && value < 1), 'seeded RNG handles Unicode seeds deterministically within [0,1)');
const assets = new Map(manifest.assets.map(asset => [asset.id, asset]));
for (const size of [[6, 6], [8, 6], [10, 8], [14, 10], [20, 16]]) for (const density of [0, 0.24, 0.55]) for (let seed = 0; seed < 30; seed++) {
  const room = generateRoom(manifest, { seed: `case-${seed}`, width: size[0], height: size[1], density });
  assert.ok(findRoute(room).length > 0, `start/exit connected: ${seed}/${size}/${density}`);
  for (const door of room.doors) assert.ok(findRoute(room, door, room.start).length > 0, 'both boundary doors connect to the playable entrance');
  const occupied = new Set(room.blockedCells.map(cell => `${cell.x},${cell.y}`));
  for (const point of [room.start, room.exit, ...room.doors, ...room.clearRoute]) assert.ok(!occupied.has(`${point.x},${point.y}`), 'reserved route and endpoints never blocked');
  for (const placement of room.placements) {
    assert.ok(assets.has(placement.assetId), 'placement references a real PNG');
    assert.ok(placement.x >= 0 && placement.x < room.width && placement.y >= 0 && placement.y < room.height, 'placement remains inside room bounds');
    assert.equal(placement.layer, assets.get(placement.assetId).layer, 'placement layer matches manifest semantics');
    if (placement.layer === 'prop' && placement.kind !== 'exit') for (const endpoint of [room.start, room.exit]) assert.ok(Math.abs(placement.x - endpoint.x) > 1 || Math.abs(placement.y - endpoint.y) > 1, 'props keep clearance around interaction points');
  }
  checks++;
}
check(generateRoom(manifest, { density: 0 }).placements.every(p => p.layer !== 'prop' || p.kind === 'exit'), 'zero density removes decorative props');
const minimal = { version: 1, tile: { width: 128, height: 64 }, assets: [{ id: 'plain', file: 'plain.png', label: 'Plain', layer: 'floor', width: 128, height: 64, anchor: { x: 64, y: 32 }, footprint: { width: 1, height: 1 }, tags: [], blocksMovement: false }] };
check(findRoute(generateRoom(minimal)).length > 0, 'partial kits still assemble accessible rooms without optional decorations');
const bad = structuredClone(manifest); bad.assets[1].id = bad.assets[0].id;
assert.throws(() => validateManifest(bad), /Invalid asset/); checks++;
const unsafe = structuredClone(manifest); unsafe.assets[0].file = '../outside.png';
assert.throws(() => validateManifest(unsafe), /Invalid asset/); checks++;
const unreachable = { width: 3, height: 3, start: { x: 0, y: 0 }, exit: { x: 2, y: 2 }, blockedCells: [{ x: 1, y: 0 }, { x: 0, y: 1 }] };
check(findRoute(unreachable).length === 0, 'connectivity checker detects a genuinely isolated start');
console.log(`PASS ${checks} room generator checks (450 seeded layouts, PNG references, route clearance and deterministic exports).`);
