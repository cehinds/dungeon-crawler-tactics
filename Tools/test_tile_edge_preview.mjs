import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const source = path => readFile(new URL(`../Web/wwwroot/${path}`, import.meta.url), 'utf8');
const moduleURL = text => `data:text/javascript;base64,${Buffer.from(text).toString('base64')}`;
const edgeURL = moduleURL(await source('tile-edge-tags.js'));
const { sceneConnections, inspectPlacedTile, pickPreviewCell } = await import(moduleURL(
  (await source('tile-edge-preview.js')).replace("'./tile-edge-tags.js'", JSON.stringify(edgeURL))));
const sides = ['north', 'east', 'south', 'west'];
const asset = (id, tags, role = 'ground') => ({ id, role, edges: Object.fromEntries(sides.map((side, i) => [side, [tags[i]]])) });
const floor = asset('floor', sides.map(() => 'join.floor'));
const wall = asset('wall', ['join.exterior', 'join.wall', 'join.floor', 'join.wall'], 'wall');
const scene = {
  floor: [{ asset: floor, px: 0, py: 0, angle: 0 }, { asset: floor, px: 128, py: 0, angle: Math.PI / 2 }],
  edgeBoundaries: [{ x: 0, y: 0, side: 'north', asset: wall, rotation: 0 },
    { x: 0, y: 0, side: 'west', asset: wall, rotation: 3 }]
};
const report = sceneConnections(scene);
assert.equal(report.connections.length, 3);
assert.ok(report.connections.every(join => join.compatible));
assert.strictEqual(sceneConnections(scene), report, 'Unchanged scene reuses its connection report');
const inspected = inspectPlacedTile(scene, 0, 0);
assert.equal(inspected.edges.find(edge => edge.side === 'north').kind, 'wall');
assert.equal(inspected.edges.find(edge => edge.side === 'east').kind, 'floor');
assert.equal(inspected.edges.find(edge => edge.side === 'south').reason, 'No adjacent floor or wall');
assert.equal(inspectPlacedTile(scene, 9, 9), null);
const badScene = { floor: [scene.floor[0], { ...scene.floor[1], asset: asset('other', sides.map(() => 'join.water')) }] };
assert.equal(sceneConnections(badScene).connections[0].compatible, false);
assert.throws(() => sceneConnections({ floor: [scene.floor[0], scene.floor[0]] }), /duplicate/);
for (let rotation = 0; rotation < 4; rotation++) {
  for (const scale of [.17, .8, 2.4]) {
    const angle = rotation * Math.PI / 2, camera = { scale, angle, offsetX: 313, offsetY: 207 };
    for (const cell of [{ x: 0, y: 0 }, { x: 13, y: 11 }, { x: -2, y: 3 }]) {
      // Test points away from centers as well, including camera offsets and zoom.
      const x = cell.x * 128 + 41, y = cell.y * 128 - 37;
      const px = camera.offsetX + (x * Math.cos(angle) - y * Math.sin(angle)) * scale;
      const py = camera.offsetY + (x * Math.sin(angle) + y * Math.cos(angle)) * scale;
      assert.deepEqual(pickPreviewCell(px, py, camera), cell);
    }
  }
}
assert.equal(pickPreviewCell(0, 0, null), null);
assert.equal(pickPreviewCell(0, 0, { scale: 0 }), null);
console.log('PASS connection reports, placed floor/wall inspection, mismatches and picking through four camera rotations and three zoom scales.');
