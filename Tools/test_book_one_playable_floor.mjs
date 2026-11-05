import assert from 'node:assert/strict';
import fs from 'node:fs';
import {generateBookOneFloor} from '../Web/wwwroot/book-one-floor.js';
import {getBookOneFloorPlayable} from '../Web/wwwroot/book-one-playable-floor.js';

const read = path => JSON.parse(fs.readFileSync(new URL(path, import.meta.url), 'utf8'));
const library = read('../Web/wwwroot/assets/top-down-object-kit/manifest.json');
const rules = read('../Web/wwwroot/data/procedural-object-room-rules.json');
const manifest = read('../Web/wwwroot/assets/room-kit/manifest.json');
const catalog = read('../Web/wwwroot/data/book-one-floor-one.json');
const archetypes = read('../Web/wwwroot/data/book-one-location-archetypes.json');
const content = read('../UnityPackage/Runtime/Data/combat-content.json');
const key = point => `${point.x},${point.y}`;
const overlap = (a, b) => a.x < b.x + b.width && b.x < a.x + a.width
  && a.y < b.y + b.height && b.y < a.y + a.height;
const signatures = new Set();
const shapes = new Set();
const base = generateBookOneFloor(library, {seed: 'floor-one-behavior'}, rules, manifest, catalog);
const original = getBookOneFloorPlayable(base, library);

for (let index = 0; index < 12; index++) {
  const floor = {...base, seed: `optional-floor-${index}`};
  const packet = getBookOneFloorPlayable(floor, library, archetypes);
  const {floorPlan: plan, generatedLocations: locations} = packet;
  const map = plan.map;
  assert.deepEqual(getBookOneFloorPlayable(floor, library, archetypes), packet, 'Seed reproduces exact preview/import packet');
  assert.deepEqual(packet.regionBounds.filter(room => !room.generated), original.regionBounds, 'Existing district bounds and objectives remain unchanged');
  assert.equal(map.width, 40); assert.equal(map.height, 32);
  assert(locations.length >= 4 && locations.length <= 8, 'Seed produces four to eight additional places');
  assert.equal(plan.groups.length, 5, 'Optional rooms add no required combat groups');
  assert.equal(map.enemies.length, 10);
  assert.deepEqual(plan.discoveries.filter(point => point.kind === 'objective'), original.floorPlan.discoveries.filter(point => point.kind === 'objective'), 'No additional required objectives');

  const open = new Set(map.tiles.filter(tile => !tile.blocked).map(key));
  const seen = new Set([key(plan.entrance)]), queue = [plan.entrance];
  for (let cursor = 0; cursor < queue.length; cursor++) {
    for (const [dx, dy] of [[1, 0], [-1, 0], [0, 1], [0, -1]]) {
      const point = {x: queue[cursor].x + dx, y: queue[cursor].y + dy};
      if (open.has(key(point)) && !seen.has(key(point))) { seen.add(key(point)); queue.push(point); }
    }
  }
  assert.equal(seen.size, open.size, 'Every open cell stays connected after object collision');
  for (const point of [plan.exit, ...map.playerSpawns, ...map.enemies, ...plan.discoveries]) assert(seen.has(key(point)), 'Every actor, objective and reward is reachable');
  const actorsAndCaches = [...map.playerSpawns, ...map.enemies, ...plan.discoveries];
  assert.equal(new Set(actorsAndCaches.map(key)).size, actorsAndCaches.length, 'Actors and discovery markers never overlap');

  for (const room of locations) {
    const archetype = archetypes.archetypes.find(type => type.id === room.archetypeId);
    assert(archetype.anchorRegionIds.includes(room.anchorRegionId), 'Attachment obeys thematic anchors');
    assert(room.optional && room.generated);
    assert(room.width >= archetype.minWidth && room.width <= archetype.maxWidth);
    assert(room.height >= archetype.minHeight && room.height <= archetype.maxHeight);
    assert(packet.regionBounds.every(other => other.id === room.id || !overlap(room, other)), 'Additional room bounds never overlap districts or each other');
    const discovery = plan.discoveries.find(point => point.id === room.objective.id);
    assert.equal(discovery.kind, 'cache');
    assert.equal(discovery.itemId, archetype.loot.itemId);
    shapes.add(room.shape);
  }
  for (const object of packet.presentationObjects.filter(object => locations.some(room => room.id === object.regionId))) {
    const asset = library.objects.find(asset => asset.id === object.assetId);
    const [width, height] = asset.gridFootprint.map(Math.ceil);
    assert.deepEqual([object.width, object.height], object.rotationDegrees === 90 ? [height, width] : [width, height], 'Optional props retain their complete native grid footprint');
    for (let y = 0; y < object.height; y++) for (let x = 0; x < object.width; x++) assert(!open.has(key({x: object.x + x, y: object.y + y})), 'Prop footprint matches canonical blocking');
  }
  for (const point of plan.discoveries.filter(point => point.kind === 'cache')) assert(content.items.some(item => item.id === point.itemId), 'Reward uses a real supply item');
  assert(plan.groups.length <= 16 && map.enemies.length <= 48 && plan.discoveries.length <= 64);
  assert.deepEqual(plan.groups.flatMap(group => group.enemyIds).sort(), map.enemies.map(enemy => enemy.id).sort());
  signatures.add(JSON.stringify(locations.map(room => [room.id, room.x, room.y, room.width, room.height, room.shape, room.anchorRegionId])));
  if (process.argv.includes('--fixture')) fs.writeFileSync('/tmp/book-one-floor-plan.json', JSON.stringify(plan));
}
assert(signatures.size >= 10, 'Seeds produce meaningfully different additional room positions and footprints');
assert(shapes.size >= 2, 'Additional room layouts vary beyond rectangle size');
console.log(`Continuous Book 1 floor: 12 seeds, ${signatures.size} distinct side-room layouts, optional caches, full connectivity and native object footprints passed.`);
