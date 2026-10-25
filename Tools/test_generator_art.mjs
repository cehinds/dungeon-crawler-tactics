import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';
const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
const read = path => readFile(resolve(root, path), 'utf8');
const moduleURL = source => `data:text/javascript;base64,${Buffer.from(source).toString('base64')}`;
const kitURL = moduleURL(await read('Web/wwwroot/room-kit.js'));
const { generateDungeon } = await import(moduleURL((await read('Web/wwwroot/procedural-map.js')).replace(/['"]\.\/room-kit\.js['"]/, JSON.stringify(kitURL))));
const edgeURL = moduleURL(await read('Web/wwwroot/tile-edge-tags.js'));
const { validateFloorConnections } = await import(edgeURL);
const solverURL = moduleURL((await read('Web/wwwroot/tile-edge-solver.js')).replace(/['"]\.\/tile-edge-tags\.js['"]/, JSON.stringify(edgeURL)));
const { buildArtScene, visibleSceneCorners, environmentMood } = await import(moduleURL((await read('Web/wwwroot/generator-art.js')).replace(/['\"]\.\/tile-edge-tags\.js['\"]/, JSON.stringify(edgeURL)).replace(/['"]\.\/tile-edge-solver\.js['"]/, JSON.stringify(solverURL))));
const manifest = JSON.parse(await read('Web/wwwroot/assets/room-kit/manifest.json'));
const catalog = JSON.parse(await read('Web/wwwroot/assets/book-tiles/catalog.json'));
const rules = JSON.parse(await read('Web/wwwroot/assets/map-generation-rules.json'));
const key = p => `${p.x},${p.y}`;
let scenes = 0;
for (const kit of catalog.kits) {
  assert.notEqual(environmentMood(kit.id).label, undefined);
  for (const style of catalog.styles) {
    const art = { manifest: JSON.parse(await read(`Web/wwwroot/assets/book-tiles/${kit.variants[style.id].manifest}`)) };
    for (const asset of art.manifest.assets.filter(a => ['prop', 'door'].includes(a.role))) {
      for (let rotation = 0; rotation < 4; rotation++) {
        const corners = visibleSceneCorners({ floor: [], structures: [], decorations: [
          { asset, px: 0, py: 0, angle: rotation * Math.PI / 2 }
        ] });
        const limit = asset.role === 'prop' ? 56 : 64;
        assert(corners.every(p => Math.abs(p.x) <= limit + 1e-6 && Math.abs(p.y) <= limit + 1e-6),
          `${asset.id}: decoration must stay within its own cell at every rotation`);
      }
    }
    for (const layout of ['chambers', 'cavern', 'hall']) for (const size of [6, 16]) {
      const room = generateDungeon(manifest, { seed: `preview-${size}`, width: size, height: size === 6 ? 6 : 12, density: .4, roomCount: 6, layout, biome: 'sewer' }, rules);
      const scene = buildArtScene(room, art, true);
      if (scenes === 0) {
        const broken = structuredClone(art);
        for (const tile of broken.manifest.assets.filter(asset => asset.role === 'ground')) tile.edges = { north: ['join.manual'], east: ['join.manual'], south: ['join.manual'], west: ['join.manual'] };
        assert.throws(() => buildArtScene(room, broken, true), /unsatisfiable/, 'Bad visual seams prevent map generation');
        const mixed = structuredClone(art);
        const firstFloors = mixed.manifest.assets.filter(asset => asset.role === 'ground').slice(0, 4);
        for (const side of ['north', 'east', 'south', 'west']) firstFloors[1].edges[side] = ['join.alternative'];
        const repaired = buildArtScene(room, mixed, true);
        assert.deepEqual(validateFloorConnections(repaired.floor), [], 'Satisfiable material mismatch is fitted');
        assert(repaired.edgeFit.adjustedTiles > 0, 'Fitting reports changed floor pieces');
        let changedLegend = false;
        for (const style of repaired.roomStyles) {
          const counts = new Map();
          for (const piece of repaired.floor) {
            const x = piece.px / 128, y = piece.py / 128;
            const region = style.region;
            if (x < region.x || x >= region.x + region.width || y < region.y || y >= region.y + region.height) continue;
            counts.set(piece.asset.id, (counts.get(piece.asset.id) || 0) + 1);
          }
          const dominant = [...counts].sort((a,b)=>b[1]-a[1] || (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0))[0];
          if (dominant) assert.equal(style.asset.id, dominant[0], 'Legend shows the dominant fitted material');
          if (style.asset.id !== firstFloors[style.index % firstFloors.length].id) changedLegend = true;
        }
        assert(changedLegend, 'Custom connectors change an actual legend material');
        const missing = structuredClone(art);
        for (const tile of missing.manifest.assets.filter(asset => asset.role === 'ground')) delete tile.edges;
        assert.throws(() => buildArtScene(room, missing, true), /edge metadata/, 'Missing metadata fails clearly');
      }
      assert.equal(scene.edgeFit.adjustedTiles, 0, 'Existing compatible art preferences stay unchanged');
      assert.deepEqual(validateFloorConnections(scene.floor), [], 'Generated floors have compatible visual seams');
      const floorCells = new Set(scene.floor.map(p => key({ x: p.px / 128, y: p.py / 128 })));
      assert.equal(floorCells.size, scene.floor.length, 'No duplicate floor cells');
      for (const p of room.clearRoute) assert(floorCells.has(key(p)), 'Entire route has a visible floor');
      const obstacles = room.placements.filter(p => p.kind === 'decoration' && p.blocksMovement);
      assert.equal(scene.decorations.filter(p => p.kind === 'obstacle').length, obstacles.length);
      for (const obstacle of obstacles) {
        const visual = scene.decorations.find(p => p.canonicalPlacementId === obstacle.id);
        assert(visual, 'Every blocking object is visible');
        assert.deepEqual([visual.px, visual.py, visual.angle], [obstacle.x * 128, obstacle.y * 128, 0]);
      }
      for (const kind of ['entrance', 'exit']) assert.equal(scene.decorations.filter(p => p.kind === kind).length, 1, 'Both portals visible');
      const blocked = new Set(room.blockedCells.map(key));
      const reserved = new Set(room.generation.protectedCells.map(key));
      for (const p of scene.decorations.filter(p => p.kind === 'landmark')) {
        const cell = key({ x: p.px / 128, y: p.py / 128 });
        assert(!blocked.has(cell) && !reserved.has(cell), 'Landmarks preserve collision and routes');
        assert.equal(p.angle, 0, 'No skewed props');
      }
      for (const corner of visibleSceneCorners(scene)) assert(Number.isFinite(corner.x) && Number.isFinite(corner.y));
      const plain = buildArtScene(room, art, false);
      assert.equal(new Set(plain.floor.map(p => p.asset.id)).size, 1, 'Uniform floor option works');
      assert.deepEqual(buildArtScene(room, art, true), scene, 'Art placement is deterministic');
      scenes++;
    }
  }
}
assert.notDeepEqual(environmentMood('bubble-desert'), environmentMood('bubble-sea'));
console.log(`PASS ${scenes} native-art scenes: visible obstacles match collision, portals and routes render, props align, material variation toggles and placement is deterministic.`);
