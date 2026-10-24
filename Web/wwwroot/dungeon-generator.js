import { generateDungeon, getPlayableMap } from './procedural-map.js';
import { projectCell } from './room-kit.js';
const $ = id => document.getElementById(id);
const canvas = $('map'), ctx = canvas.getContext('2d'), images = new Map();
let manifest, rules, assets, room, playable, rotation = 0, blueprint = false;
const directions = ['NORTH', 'EAST', 'SOUTH', 'WEST'];
function status(message, error = false) { $('status').textContent = message; $('status').classList.toggle('error', error); }
function safely(action) { try { action(); } catch (error) { status(error.message, true); } }
function settings() {
  for (const [id, max] of [['width',20],['height',16]]) { const n = Number($(id).value); if (!Number.isInteger(n) || n < 6 || n > max) throw new Error(`${id === 'width' ? 'Width' : 'Height'} must be a whole number from 6 to ${max}.`); }
  return {seed:$('seed').value,width:Number($('width').value),height:Number($('height').value),layout:$('layout').value,biome:$('biome').value,roomCount:Number($('rooms').value),density:Number($('density').value)/100};
}
function generate() {
  const next = generateDungeon(manifest, settings(), rules), map = getPlayableMap(next, manifest);
  room = next; playable = map;
  $('map-title').textContent = `${$('biome').selectedOptions[0].text} / ${room.seed || 'untitled'}`;
  $('counts').textContent = `${room.rooms.length} rooms · ${room.corridors.length} connections · ${room.clearRoute.length} route cells`;
  canvas.setAttribute('aria-label', `${room.width} by ${room.height} dungeon, ${room.rooms.length} rooms and ${room.clearRoute.length} route cells. Party markers are mint; enemies are coral; exit is gold.`);
  status(`${room.width} × ${room.height} cells · ${room.placements.length} PNG placements · All party and enemy spawns share a connected route.`);
  draw();
}
function draw() {
  if (!room) return;
  const bounds = $('canvas-wrap').getBoundingClientRect(), dpr = Math.min(devicePixelRatio || 1, 2);
  canvas.width = Math.round(bounds.width*dpr); canvas.height = Math.round(bounds.height*dpr);
  ctx.setTransform(dpr,0,0,dpr,0,0); ctx.clearRect(0,0,bounds.width,bounds.height); const background=ctx.createRadialGradient(bounds.width/2,bounds.height/2,0,bounds.width/2,bounds.height/2,Math.max(bounds.width,bounds.height)*.6); background.addColorStop(0,'#243331'); background.addColorStop(1,'#162021'); ctx.fillStyle=background; ctx.fillRect(0,0,bounds.width,bounds.height); ctx.imageSmoothingEnabled = false;
  const rotate = (x,y) => rotation===1?[-y,x]:rotation===2?[-x,-y]:rotation===3?[y,-x]:[x,y];
  const project = (x,y) => { if (!blueprint) return projectCell(x,y,rotation); const [a,b]=rotate(x,y); return {x:a*64,y:b*64}; };
  const corners = [[0,0],[room.width-1,0],[0,room.height-1],[room.width-1,room.height-1]].map(([x,y])=>project(x,y));
  const minX=Math.min(...corners.map(p=>p.x))-70, maxX=Math.max(...corners.map(p=>p.x))+70,minY=Math.min(...corners.map(p=>p.y))-(blueprint?40:110),maxY=Math.max(...corners.map(p=>p.y))+50;
  const scale=Math.max(.01,Math.min((bounds.width-32)/(maxX-minX),(bounds.height-55)/(maxY-minY),1.8));
  ctx.translate((bounds.width-(maxX-minX)*scale)/2-minX*scale,(bounds.height-(maxY-minY)*scale)/2-minY*scale);ctx.scale(scale,scale);
  const blocked = new Set(room.blockedCells.map(p=>`${p.x},${p.y}`));
  if (blueprint) {
    for(let y=0;y<room.height;y++)for(let x=0;x<room.width;x++) { const p=project(x,y),solid=blocked.has(`${x},${y}`);ctx.fillStyle=solid?'#263938':'#668579';ctx.fillRect(p.x-30,p.y-30,60,60);ctx.strokeStyle='#8fa89925';ctx.lineWidth=1;ctx.strokeRect(p.x-30,p.y-30,60,60); }
    for (const r of room.rooms) { const p=project(r.center.x,r.center.y);ctx.fillStyle='#e4eddb70';ctx.font='16px monospace';ctx.textAlign='center';ctx.fillText(r.id.replace('room.','R'),p.x,p.y+5); }
  } else {
    const rank = layer => layer==='floor'?0:layer==='surface'?1:2;
    const layers=['floor','surface','structure','prop','overlay'];
    const sorted=[...room.placements].sort((a,b)=>rank(a.layer)-rank(b.layer)||project(a.x,a.y).y-project(b.x,b.y).y||a.y-b.y||layers.indexOf(a.layer)-layers.indexOf(b.layer));
    for (const placement of sorted) {
      const asset=assets.get(placement.assetId),p=project(placement.x,placement.y),q=((placement.rotation??0)+rotation)%4;
      const variantId=q%2?asset.id.replace(/-ne$/,'-TEMP').replace(/-nw$/,'-ne').replace(/-TEMP$/,'-nw'):asset.id;
      const variant=assets.get(variantId)??asset;
      ctx.save();ctx.translate(p.x,p.y);
      if(['floor','surface'].includes(asset.layer)||asset.tags.includes('decal')) { if(q===1)ctx.transform(0,.5,-2,0,0,0);else if(q===2)ctx.scale(-1,-1);else if(q===3)ctx.transform(0,-.5,2,0,0,0); }
      else if(q>=2&&!asset.tags.includes('wall')&&!asset.tags.includes('door'))ctx.scale(-1,1);
      ctx.drawImage(images.get(variant.id),-variant.anchor.x,-variant.anchor.y,variant.width,variant.height);ctx.restore();
    }
  }
  if($('route').checked&&room.clearRoute.length) {ctx.beginPath();room.clearRoute.forEach((cell,i)=>{const p=project(cell.x,cell.y);if(i)ctx.lineTo(p.x,p.y);else ctx.moveTo(p.x,p.y);});ctx.strokeStyle='#e4bf7e';ctx.lineWidth=4;ctx.setLineDash([7,6]);ctx.stroke();ctx.setLineDash([]);}
  function marker(cell,color,label) {if(!cell)return;const p=project(cell.x,cell.y),r=blueprint?14:12;ctx.beginPath();ctx.arc(p.x,p.y,r,0,Math.PI*2);ctx.fillStyle='#101c1c';ctx.fill();ctx.lineWidth=3;ctx.strokeStyle=color;ctx.stroke();ctx.font='bold 12px monospace';ctx.textAlign='center';ctx.fillStyle=color;ctx.fillText(label,p.x,p.y+4);}
  const parties=playable.playerSpawns??room.playerSpawns??[], enemies=playable.enemies??room.enemies??[];
  parties.forEach((p,i)=>marker(p.position??p,'#a8dac7',`${i+1}`));
  enemies.forEach(p=>marker(p.position??p,'#ee9789','!'));
  marker(room.exit,'#e5c27a','E');
  $('view-label').textContent=`${blueprint?'BLUEPRINT':'ISOMETRIC'} / ${directions[rotation]}`;
}
function download(data,name,type='application/json') {const blob=data instanceof Blob?data:new Blob([typeof data==='string'?data:JSON.stringify(data,null,2)],{type});const url=URL.createObjectURL(blob),a=document.createElement('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
$('generate').onclick=()=>safely(generate);
$('reroll').onclick=()=>{const values=new Uint32Array(1);crypto.getRandomValues(values);$('seed').value=`dungeon-${values[0].toString(36)}`;safely(generate);};
for(const id of ['rooms','density'])$(id).oninput=()=>{$(`${id}-value`).textContent=$(id).value+(id==='density'?'%':'');};
$('iso').onclick=()=>{blueprint=false;$('iso').setAttribute('aria-pressed','true');$('blueprint').setAttribute('aria-pressed','false');draw();};
$('blueprint').onclick=()=>{blueprint=true;$('iso').setAttribute('aria-pressed','false');$('blueprint').setAttribute('aria-pressed','true');draw();};
$('rotate-left').onclick=()=>{rotation=(rotation+3)%4;draw();};$('rotate-right').onclick=()=>{rotation=(rotation+1)%4;draw();};$('fit').onclick=draw;$('route').onchange=draw;
$('recipe').onclick=()=>safely(()=>download(room,'dungeon-recipe.json'));
$('map-json').onclick=()=>safely(()=>download(playable,'dungeon-playable-map.json'));
$('png').onclick=()=>canvas.toBlob(blob=>{if(blob)download(blob,'dungeon-snapshot.png');else status('Could not create snapshot.',true);},'image/png');
$('edit').onclick=()=>safely(()=>{localStorage.setItem('dct.workshop-recipe',JSON.stringify(room));location.href='room-kit.html?import=generator';});
$('play').onclick=()=>$('play-dialog').showModal();
$('play-dialog').addEventListener('close',()=>{if($('play-dialog').returnValue==='play')safely(()=>{localStorage.setItem('dct.workshop-map',JSON.stringify(playable));location.href='index.html?workshop=1';});});
new ResizeObserver(draw).observe($('canvas-wrap'));
async function load() {
  try {
    const manifestUrl=new URL('assets/room-kit/manifest.json',location.href);
    [manifest,rules]=await Promise.all([fetch(manifestUrl),fetch('assets/map-generation-rules.json')].map(async request=>{const response=await request;if(!response.ok)throw new Error(`Could not load dungeon data (${response.status}).`);return response.json();}));
    assets=new Map(manifest.assets.map(a=>[a.id,a]));
    await Promise.all(manifest.assets.map(asset=>new Promise((resolve,reject)=>{const image=new Image();image.onload=()=>{images.set(asset.id,image);resolve();};image.onerror=()=>reject(new Error(`Could not load ${asset.file}. Reload to retry.`));image.src=new URL(asset.file,manifestUrl);}))); 
    generate();$('loading').hidden=true;$('settings').disabled=false;document.querySelectorAll('.workspace button,.workspace input').forEach(element=>element.disabled=false);
  } catch(error) {$('loading').textContent='The dungeon could not be loaded.';status(error.message,true);}
}
load();
