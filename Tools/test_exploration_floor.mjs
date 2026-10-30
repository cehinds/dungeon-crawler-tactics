import fs from 'node:fs';
import assert from 'node:assert/strict';
const { generateExplorationFloor, validateExplorationFloor } = await import(`data:text/javascript;base64,${Buffer.from(fs.readFileSync(new URL('../Web/wwwroot/exploration-floor.js', import.meta.url), 'utf8')).toString('base64')}`);
const manifest=JSON.parse(fs.readFileSync(new URL('../Web/wwwroot/assets/room-kit/manifest.json',import.meta.url)));
const rules=JSON.parse(fs.readFileSync(new URL('../Web/wwwroot/data/exploration-floor-rules.json',import.meta.url)));
for(let i=0;i<200;i++) {
  const {floorPlan,room}=generateExplorationFloor(manifest,rules,`fuzz-${i}`);
  const report=validateExplorationFloor(floorPlan,rules);
  assert.ok(report.walkableCells>400);
  assert.ok(report.exitDistance>30);
  assert.equal(floorPlan.groups.filter(g=>g.kind==='visible').length,3);
  assert.equal(floorPlan.groups.filter(g=>g.kind==='ambush').length,1);
  assert.deepEqual(floorPlan,generateExplorationFloor(manifest,rules,`fuzz-${i}`).floorPlan);
  for(const group of floorPlan.groups) for(const id of group.enemyIds) assert.ok(floorPlan.map.enemies.some(e=>e.id===id));
  const blocked=new Set(room.blockedCells.map(p=>`${p.x},${p.y}`));
  for(const corridor of room.corridors) for(const p of corridor.cells) assert.ok(!blocked.has(`${p.x},${p.y}`));
  for(const enemy of floorPlan.map.enemies) assert.ok(Math.abs(enemy.x-floorPlan.entrance.x)+Math.abs(enemy.y-floorPlan.entrance.y)>=rules.safeRadius);
}
console.log('Continuous floor: 200 deterministic seeds, connectivity, safe start, encounter spacing and wide paths passed.');
// Exercise the production directional tag fitter on the larger layout.
const moduleCache=new Map();
async function loadModule(path) {
  if(moduleCache.has(path))return moduleCache.get(path);
  let source=fs.readFileSync(new URL(path,import.meta.url),'utf8');
  const matches=[...source.matchAll(/from ['"](.+?)['"]/g)];
  for(const match of matches) {
    if(!match[1].startsWith('.'))continue;
    const child=new URL(match[1],new URL(path,import.meta.url));
    const childPath=child.pathname;
    const childURL=await loadModule(childPath);
    source=source.replace(match[0],`from ${JSON.stringify(childURL)}`);
  }
  const url=`data:text/javascript;base64,${Buffer.from(source).toString('base64')}`;
  moduleCache.set(path,url);return url;
}
const {buildArtScene}=await import(await loadModule('../Web/wwwroot/generator-art.js'));
const {serializeNativeVisuals}=await import(await loadModule('../Web/wwwroot/native-map-visuals.js'));
for(const styleId of ['pocket-dungeon','dungeon-after-dark','late-night-cartoons']) {
  const path=new URL(`../Web/wwwroot/assets/book-tiles/${styleId}/starter-dungeon/manifest.json`,import.meta.url);
  if(!fs.existsSync(path))continue;
  const art={manifest:JSON.parse(fs.readFileSync(path)),images:new Map()};
  const {room,floorPlan}=generateExplorationFloor(manifest,rules,'visual-floor');
  const scene=buildArtScene(room,art,true);
  const visuals=serializeNativeVisuals(scene,{styleId,kitId:'starter-dungeon',width:room.width,height:room.height,tiles:floorPlan.map.tiles});
  assert.ok(visuals.pieces.length>400);
  console.log(`Continuous floor: production art fitting and serialization passed (${styleId}).`);
}
const invalidRecipes=[
  r=>r.schemaVersion=2,
  r=>r.width=41,
  r=>r.height=7,
  r=>r.zones[1].x=39,
  r=>r.zones[0].x=6,
  r=>r.zones[1].id=r.zones[0].id,
  r=>r.connections[0]=[0,99],
  r=>r.connections=[[0,1]],
  r=>r.groups[0].zone=0,
  r=>r.groups[1].zone=r.groups[0].zone,
  r=>r.groups[0].kind='unknown',
  r=>r.discoveries[0].count=0,
  r=>r.discoveries[0].itemId=null,
  r=>r.discoveries[1].itemId='item.health_tonic',
  r=>r.enemyRecipe[0].hp=-1,
  r=>r.enemyRecipe=Array(10).fill(r.enemyRecipe[0]),
  r=>r.safeRadius=0,
  r=>r.propLabelPattern='['
];
for(const change of invalidRecipes) {
  const invalid=structuredClone(rules);change(invalid);
  assert.throws(()=>generateExplorationFloor(manifest,invalid,'invalid'),/Invalid exploration floor rules:/);
}
console.log(`Continuous floor: ${invalidRecipes.length} invalid authored recipes rejected clearly.`);
