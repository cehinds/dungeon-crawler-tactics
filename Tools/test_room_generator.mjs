import assert from 'node:assert/strict';
import { spawnSync } from 'node:child_process';
import { readFile, access } from 'node:fs/promises';
import { dirname, resolve } from 'node:path';
import { fileURLToPath } from 'node:url';

const root = resolve(dirname(fileURLToPath(import.meta.url)), '..');
// The browser module stays .js for static hosting; a data URL imports its pure exports in Node
// without changing package settings or installing a DOM shim.
const source = await readFile(resolve(root, 'Web/wwwroot/room-kit.js'), 'utf8');
const { generateRoom, findRoute, validateManifest, seededRandom, projectCell, pickCell, paintCell, validateRoom, exportGameTiles } = await import(`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`);
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

for(let q=0;q<4;q++)for(let y=0;y<8;y++)for(let x=0;x<10;x++){
  const p=projectCell(x,y,q);assert.deepEqual(pickCell(p.x,p.y,q),{x,y});
  assert.deepEqual(pickCell(p.x+10,p.y+4,q),{x,y},'interior click stays on rotated cell');
}
const edited=structuredClone(baseline);
paintCell(edited,manifest,'crate',3,3,3);
assert.equal(edited.placements.filter(p=>p.x===3&&p.y===3&&p.layer==='prop').length,1);
assert.equal(edited.placements.find(p=>p.x===3&&p.y===3&&p.layer==='prop').rotation,3);
assert.ok(edited.blockedCells.some(p=>p.x===3&&p.y===3));
paintCell(edited,manifest,'crate',3,3,0,true);
assert.ok(!edited.placements.some(p=>p.x===3&&p.y===3&&p.layer==='prop'));
assert.deepEqual(validateRoom(JSON.parse(JSON.stringify(edited)),manifest),edited,'JSON roundtrip preserves authored layers and grid positions');
const broken=structuredClone(edited);broken.placements[0].rotation=7;
assert.throws(()=>validateRoom(broken,manifest),/Invalid placement/);
const renderSource=await readFile(resolve(root,'Web/wwwroot/battlefield.js'),'utf8');
const legacyRender=renderSource.slice(renderSource.indexOf('  function draw(time)'),renderSource.indexOf('  function eventUnit('));
const nativeRender=renderSource.slice(renderSource.indexOf('  function drawNative('),renderSource.indexOf('  function draw(time)'));
const transientRender=renderSource.slice(renderSource.indexOf('  function drawTransient('),renderSource.indexOf('  function drawNative('));
assert.ok(legacyRender.indexOf('drawables.sort')<legacyRender.indexOf('for(const tile of tiles)if((!explore||tile.revealed)'),'legacy burning composited after scene');
assert.ok(legacyRender.indexOf('drawTransient(time)')>legacyRender.indexOf('drawables.sort'),'legacy transient impacts called after scene');
assert.ok(nativeRender.indexOf('drawTransient(time)')>nativeRender.indexOf('nativeScene.decorations.forEach'),'native transient impacts called after scene');
assert.ok(nativeRender.indexOf('drawTransient(time)')>nativeRender.indexOf('forEach(unit=>sprite'),'native transient impacts called after units');
assert.ok(transientRender.includes('for(const e of effects)')&&transientRender.includes('for(const m of missiles)'),'shared transient pass retains impacts and projectiles');
assert.ok(!renderSource.includes('cell*.273'),'runtime uses manifest anchors instead of guessed floor crop');
console.log('PASS editor JSON/paint/erase, 640 rotated projection/picking checks, manifest anchors and effect compositing order.');

const mapRoom=generateRoom(manifest,{density:0});
paintCell(mapRoom,manifest,'water-floor',4,4);paintCell(mapRoom,manifest,'oil-overlay',5,4);paintCell(mapRoom,manifest,'fire-overlay',6,4);paintCell(mapRoom,manifest,'crate',4,3);
const mapExport=exportGameTiles(mapRoom,manifest);
assert.deepEqual(Object.keys(mapExport),['width','height','tiles']);
assert.deepEqual(mapExport.tiles.find(t=>t.x===4&&t.y===4),{x:4,y:4,blocked:false,tags:['surface.water']});
assert.ok(mapExport.tiles.find(t=>t.x===4&&t.y===3).blocked);
assert.deepEqual(mapExport.tiles.find(t=>t.x===5&&t.y===4).tags,['surface.oil']);
assert.deepEqual(mapExport.tiles.find(t=>t.x===6&&t.y===4).tags,['surface.burning']);
assert.ok(mapExport.tiles.every(t=>Object.keys(t).join(',')==='x,y,blocked,tags'));
console.log('PASS campaign EncounterDef export: exact width/height/tiles fields, blocking and water/oil/burning tags.');

const canonical=JSON.parse(await readFile(resolve(root,'UnityPackage/Runtime/Data/game-content.json'),'utf8'));
Object.assign(canonical.encounters[0],mapExport);
// The documented merge preserves authored actors and requires their cells to stay walkable.
const spawnCells=new Set([...canonical.encounters[0].playerSpawns,...canonical.encounters[0].enemies].map(p=>`${p.x},${p.y}`));
for(const tile of canonical.encounters[0].tiles)if(spawnCells.has(`${tile.x},${tile.y}`))tile.blocked=false;
const validation=spawnSync('python3',['-c',"import sys,json; sys.path.insert(0,'Tools'); from validate_game_data import validate_game; content=json.load(open('UnityPackage/Runtime/Data/combat-content.json')); errors=validate_game(json.load(sys.stdin),content); print('\\n'.join(errors)); sys.exit(bool(errors))"],{cwd:root,input:JSON.stringify(canonical),encoding:'utf8'});
assert.equal(validation.status,0,`Campaign merge must pass actual validator: ${validation.stdout} ${validation.stderr}`);
console.log('PASS exported tile patch merged into canonical encounter and accepted by validate_game_data.validate_game.');
