import assert from 'node:assert/strict';
import fs from 'node:fs';
import {bookOneSeedNumber} from '../Web/wwwroot/book-one-playable-floor.js';
import {planBookOneEntry, createBookOneEntry, shouldResumeBookOneFloor} from '../Web/wwwroot/book-one-entry.js';
const original = JSON.stringify({customMap:{label:'Other campaign'},generatedDungeon:null});
assert.deepEqual(planBookOneEntry(null),{kind:'start',seed:'book-one-floor-one',needsConfirmation:false});
assert.equal(planBookOneEntry(original).needsConfirmation,true,'Unrelated progress requires replacement confirmation');
assert.equal(planBookOneEntry('{broken').needsConfirmation,true,'Malformed storage also requires confirmation before replacement');
assert.throws(()=>planBookOneEntry(null,''),/seed/);
assert.throws(()=>planBookOneEntry(null,'a'.repeat(81)),/seed/);
const label='Book 1 / Floor 1 / saved-seed';
const floorPlan={map:{label},seed:bookOneSeedNumber('saved-seed')&0x7fffffff,groups:[{id:'book1.false-guild-alley'}],discoveries:[{id:'visit-entry'}]};
const saved=JSON.stringify({customMap:{label},generatedDungeon:{floorPlan,x:12,y:13,claimedIds:['visit-entry']}});
assert.deepEqual(planBookOneEntry(saved),{kind:'resume'},'Existing Book 1 entry resumes without regeneration');
assert.deepEqual(planBookOneEntry(saved,'saved-seed'),{kind:'resume'});
assert.equal(planBookOneEntry(saved,'new-seed').needsConfirmation,true,'Different seed explicitly replaces the old floor');
assert.equal(JSON.parse(saved).generatedDungeon.x,12,'Entry decision does not modify saved movement or receipts');
const packet=await createBookOneEntry('direct-entry-test',async path=>JSON.parse(fs.readFileSync(new URL(`../Web/wwwroot/${path}`,import.meta.url),'utf8')));
assert.equal(packet.floorPlan.map.width,40);
assert.equal(packet.floorPlan.map.label,'Book 1 / Floor 1 / direct-entry-test');
assert(packet.generatedLocations.length>=4&&packet.generatedLocations.length<=8,'New direct entry loads the archetype catalog and generates optional places');
assert(packet.generatedLocations.every(room=>packet.floorPlan.discoveries.some(point=>point.id===room.objective.id&&point.kind==='cache')));
assert.equal(packet.floorPlan.entrance.x,packet.floorPlan.map.playerSpawns[0].x);
console.log('Direct Book 1 entry: fresh start, exact resume, unrelated/malformed save protection, seed validation and real floor generation passed.');

const camp={screen:'camp',generatedDungeon:{floorPlan}};
assert.equal(shouldResumeBookOneFloor(camp),true);
for(const screen of ['battle','victory','defeat','complete','explore'])assert.equal(shouldResumeBookOneFloor({...camp,screen}),false,'Existing combat and completion phases stay unchanged');

const renamed=JSON.parse(saved);renamed.customMap.label='A translated display title';renamed.generatedDungeon.floorPlan.map.label='A translated display title';
assert.deepEqual(planBookOneEntry(JSON.stringify(renamed)),{kind:'resume'},'Display text does not control mode identity');
assert.equal(planBookOneEntry(JSON.stringify({customMap:{label},generatedDungeon:{floorPlan:{map:{label}}}})).needsConfirmation,true,'A title alone cannot identify a Book 1 run');

assert.deepEqual(planBookOneEntry(saved),{kind:'resume'},'Pre-expansion realized Book 1 saves remain eligible for exact resume');
assert.equal(JSON.stringify(JSON.parse(saved).generatedDungeon.floorPlan),JSON.stringify(floorPlan),'Old realized geometry is never regenerated or upgraded by entry planning');
