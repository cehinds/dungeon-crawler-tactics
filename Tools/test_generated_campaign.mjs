import fs from 'node:fs';
import assert from 'node:assert/strict';
const read=p=>JSON.parse(fs.readFileSync(new URL(p,import.meta.url)));
const manifest=read('../Web/wwwroot/assets/room-kit/manifest.json');
const base=read('../Web/wwwroot/data/exploration-floor-rules.json');
const rules=read('../Web/wwwroot/data/generated-campaign-rules.json');
const mechanismRecipe={id:'mechanism.test',label:'Test shortcut',description:'A sealed shortcut.',materialTags:['surface.oil'],solutions:[
 {id:'solution.manual',label:'Lever',description:'Pull the remote lever.',kind:'manual',requiredMaterialTags:[]},
 {id:'solution.ability',label:'Ignite',description:'Burn the barrier.',kind:'ability',abilityTag:'fire',requiredMaterialTags:['surface.oil']},
 {id:'solution.item',label:'Flask',description:'Burn with a flask.',kind:'item',abilityTag:'fire',itemId:'item.fire_flask',itemCount:1,requiredMaterialTags:['surface.oil']} ]};
const legacy=structuredClone(rules);for(const d of legacy.depths)delete d.mechanisms;
const withMechanisms=structuredClone(rules);for(const d of withMechanisms.depths)d.mechanisms??=[structuredClone(mechanismRecipe)];
const catalog=read('../Web/wwwroot/assets/book-tiles/catalog.json');
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

const {validateGeneratedCampaignRules,generateCampaignFloor,campaignDepthRules,validateExplorationFloor}=await import(await loadModule('../Web/wwwroot/exploration-floor.js'));
const {buildArtScene}=await import(await loadModule('../Web/wwwroot/generator-art.js'));
const {serializeNativeVisuals}=await import(await loadModule('../Web/wwwroot/native-map-visuals.js'));
validateGeneratedCampaignRules(rules,base,catalog);
assert.equal(new Set(rules.depths.map(d=>d.familyId)).size,3);
for(let seed=0;seed<100;seed++) {
 const fingerprints=new Set();
 for(let depth=0;depth<rules.depths.length;depth++) {
  const {room,floorPlan}=generateCampaignFloor(manifest,base,withMechanisms,depth,seed);
  assert.deepEqual(floorPlan,generateCampaignFloor(manifest,base,withMechanisms,depth,seed).floorPlan);
  validateExplorationFloor(floorPlan,campaignDepthRules(base,withMechanisms,withMechanisms.depths[depth]));
  assert.equal(floorPlan.mechanisms.length,withMechanisms.depths[depth].mechanisms.length);
  const original=generateCampaignFloor(manifest,base,legacy,depth,seed).floorPlan;
  assert.deepEqual(original.map,floorPlan.map,'mechanisms preserve all immutable map cells and enemies');
  assert.equal(original.mechanisms,undefined);
  fingerprints.add(JSON.stringify(floorPlan.map.tiles));
  const blocked=new Set(room.blockedCells.map(p=>`${p.x},${p.y}`));
  for(const p of room.generation.protectedCells) assert.ok(!blocked.has(`${p.x},${p.y}`));
  assert.equal(floorPlan.discoveries.filter(d=>d.kind==='objective').length,depth+1);
  assert.ok(floorPlan.groups.every(g=>g.rewardXp===[30,40,50][depth]));
 }
 assert.equal(fingerprints.size,3);
}
for(const style of catalog.styles) for(const depth of rules.depths.keys()) {
 const kitId=rules.depths[depth].kitId;
 const art={manifest:read(`../Web/wwwroot/assets/book-tiles/${style.id}/${kitId}/manifest.json`),images:new Map()};
 assert.equal(art.manifest.grid.tileWidth,128);assert.equal(art.manifest.grid.tileHeight,128);
 const {room,floorPlan}=generateCampaignFloor(manifest,base,rules,depth,42);
 const scene=buildArtScene(room,art,true);
 const visuals=serializeNativeVisuals(scene,{styleId:style.id,kitId,width:room.width,height:room.height,tiles:floorPlan.map.tiles});
 assert.ok(visuals.pieces.length>400);assert.deepEqual(JSON.parse(JSON.stringify(visuals)),visuals);
}
const mutations=[r=>r.depths[0].groups[0].rewardXp=-1,r=>r.depths[1].groups[0].rewardXp=501,r=>r.depths[2].groups[0].rewardXp=1.5,r=>r.schemaVersion=2,r=>r.depths=[],r=>r.depths[0].familyId='missing',r=>r.depths[0].kitId='missing',r=>r.depths[1].id=r.depths[0].id,r=>r.families[0].connections=[[0,1]],r=>r.depths[0].enemyRecipe[0].hp=-1,r=>r.depths[0].discoveries[0].zone=4,r=>r.depths[0].groups.forEach(g=>g.kind='visible'),r=>r.depths[0].propLabelPattern='[',r=>r.surprise=true];
for(const mutate of mutations){const invalid=structuredClone(rules);mutate(invalid);assert.throws(()=>validateGeneratedCampaignRules(invalid,base,catalog));}
console.log('Generated campaign: 300 deterministic connected floors, distinct graphs, reserved routes, all 9 square theme/style fits, serialization and 14 invalid recipes passed.');

for(const mutate of [m=>m.id='Bad ID',m=>m.id='x'.repeat(101),m=>m.solutions[0].id='Bad ID',m=>m.solutions[0].id='x'.repeat(101),m=>m.materialTags=Array.from({length:9},(_,i)=>`material.${i}`),m=>{m.materialTags=Array.from({length:8},(_,i)=>`material.${i}`);m.solutions[0].requiredMaterialTags=Array.from({length:9},(_,i)=>`material.${i}`);},m=>m.surprise=true,m=>m.solutions[0].abilityTag='fire',m=>m.solutions[1].requiredMaterialTags=['missing'],m=>m.solutions[2].itemCount=0,m=>m.solutions[2].abilityTag=undefined,m=>m.solutions[1].kind='manual']) {
 const invalid=structuredClone(withMechanisms);mutate(invalid.depths[0].mechanisms[0]);
 assert.throws(()=>validateGeneratedCampaignRules(invalid,base,catalog),/Invalid exploration floor rules:/);
}
console.log('Mechanisms: 300 deterministic shortcuts preserve baseline maps, reduce path distance, reserve reachable actions and reject invalid recipes.');

const impossible=campaignDepthRules(base,withMechanisms,withMechanisms.depths[0]);
for(const zone of impossible.zones)Object.assign(zone,{x:1,y:1,width:impossible.width-2,height:impossible.height-2});
const {generateExplorationFloor}=await import(await loadModule('../Web/wwwroot/exploration-floor.js'));
assert.throws(()=>generateExplorationFloor(manifest,impossible,'no-closed-shortcuts'),/Cannot place meaningful floor mechanism/);
const missing=generateCampaignFloor(manifest,base,withMechanisms,0,17).floorPlan;
missing.mechanisms=[];
assert.throws(()=>validateExplorationFloor(missing,campaignDepthRules(base,withMechanisms,withMechanisms.depths[0])),/Missing authored floor mechanism/);
