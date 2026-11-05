import assert from 'node:assert/strict';
import fs from 'node:fs';
import {generateBookOneFloor} from '../Web/wwwroot/book-one-floor.js';
import {getBookOneFloorPlayable} from '../Web/wwwroot/book-one-playable-floor.js';
const read=p=>JSON.parse(fs.readFileSync(new URL(p,import.meta.url),'utf8'));
const library=read('../Web/wwwroot/assets/top-down-object-kit/manifest.json'),rules=read('../Web/wwwroot/data/procedural-object-room-rules.json'),manifest=read('../Web/wwwroot/assets/room-kit/manifest.json'),catalog=read('../Web/wwwroot/data/book-one-floor-one.json');
const content=read('../UnityPackage/Runtime/Data/combat-content.json');
for(const seed of ['floor-one-behavior','second-seed','third-seed']){
 const floor=generateBookOneFloor(library,{seed},rules,manifest,catalog),packet=getBookOneFloorPlayable(floor,library),f=packet.floorPlan,m=f.map;
 assert.deepEqual(getBookOneFloorPlayable(floor,library),packet,'Exact seed produces identical preview/import packet');
 assert.equal(m.width,40);assert.equal(m.height,32);assert.equal(packet.regionBounds.length,catalog.regions.filter(r=>r.physicalRegion!==false).length);
 const open=new Set(m.tiles.filter(t=>!t.blocked).map(p=>`${p.x},${p.y}`)),seen=new Set([`${f.entrance.x},${f.entrance.y}`]),queue=[f.entrance];
 for(let i=0;i<queue.length;i++)for(const[dx,dy]of[[1,0],[-1,0],[0,1],[0,-1]]){const p={x:queue[i].x+dx,y:queue[i].y+dy},key=`${p.x},${p.y}`;if(open.has(key)&&!seen.has(key)){seen.add(key);queue.push(p);}}
 for(const p of [f.exit,...m.playerSpawns,...m.enemies,...f.discoveries])assert(seen.has(`${p.x},${p.y}`),'Every tactical marker and actor connects');
 const actorCells=new Set();for(const p of [...m.playerSpawns,...m.enemies]){const k=`${p.x},${p.y}`;assert(!actorCells.has(k));actorCells.add(k);}
 assert(f.groups.length<=16&&m.enemies.length<=48&&f.discoveries.length<=64);
 assert.deepEqual(f.groups.flatMap(g=>g.enemyIds).sort(),m.enemies.map(e=>e.id).sort());
 for(const p of f.discoveries)if(p.kind==='cache')assert(content.items.some(i=>i.id===p.itemId),'Cache refers to real item');
 for(const r of packet.regionBounds.filter(r=>r.safeZone))assert(!m.enemies.some(e=>e.x>=r.x&&e.x<r.x+r.width&&e.y>=r.y&&e.y<r.y+r.height),'Safe rooms have no hostile spawns');
 if(process.argv.includes('--fixture'))fs.writeFileSync('/tmp/book-one-floor-plan.json',JSON.stringify(f));
}
console.log('Continuous Book 1 floor: three seeds, canonical collision, all actors/objectives reachable, encounter ownership and safe rooms passed.');
