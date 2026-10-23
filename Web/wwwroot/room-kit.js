const LAYERS = ['floor', 'surface', 'structure', 'prop', 'overlay'];
const key = (x, y) => `${x},${y}`;
const clamp = (value, lo, hi) => Math.max(lo, Math.min(hi, value));

/** A local seeded PRNG: generation never depends on rendering time or browser state. */
export function seededRandom(seed) {
  let state = 2166136261;
  for (const char of String(seed)) { state ^= char.codePointAt(0); state = Math.imul(state, 16777619); }
  return () => { state += 0x6D2B79F5; let value = state; value = Math.imul(value ^ value >>> 15, value | 1); value ^= value + Math.imul(value ^ value >>> 7, value | 61); return ((value ^ value >>> 14) >>> 0) / 4294967296; };
}

export function validateManifest(manifest) {
  if (manifest?.version !== 1 || !Number.isFinite(manifest.tile?.width) || !Number.isFinite(manifest.tile?.height) || manifest.tile.width <= 0 || manifest.tile.height <= 0 || !Array.isArray(manifest.assets)) throw new Error('Unsupported or missing PNG kit manifest.');
  const ids = new Set();
  for (const asset of manifest.assets) {
    if (!asset || typeof asset.id !== 'string' || !asset.id || ids.has(asset.id) || typeof asset.file !== 'string' || !asset.file.endsWith('.png') || asset.file.includes('..') || /^(?:[a-z]+:|\/)/i.test(asset.file) || !LAYERS.includes(asset.layer) || !Number.isFinite(asset.width) || !Number.isFinite(asset.height) || asset.width <= 0 || asset.height <= 0 || !Number.isFinite(asset.anchor?.x) || !Number.isFinite(asset.anchor?.y) || !Number.isInteger(asset.footprint?.width) || !Number.isInteger(asset.footprint?.height) || asset.footprint.width < 1 || asset.footprint.height < 1 || !Array.isArray(asset.tags) || typeof asset.blocksMovement !== 'boolean') throw new Error(`Invalid asset: ${asset?.id ?? '(missing ID)'}`);
    ids.add(asset.id);
  }
  if (!manifest.assets.some(asset => asset.layer === 'floor' && !asset.blocksMovement)) throw new Error('The kit needs a walkable floor.');
  return manifest;
}

/** Visual authoring data only. These placements do not resolve combat or alter campaign maps. */
export function generateRoom(manifest, options = {}) {
  validateManifest(manifest);
  const width = clamp(Math.round(Number(options.width) || 10), 6, 20);
  const height = clamp(Math.round(Number(options.height) || 8), 6, 16);
  const density = clamp(Number.isFinite(Number(options.density)) ? Number(options.density) : 0.24, 0, 0.55);
  const seed = String(options.seed ?? 'crawler-13').slice(0, 120);
  const random = seededRandom(seed);
  const oneCell = manifest.assets.filter(asset => asset.footprint.width === 1 && asset.footprint.height === 1);
  const has = (asset, tag) => asset.tags.includes(tag);
  const pick = values => values.length ? values[Math.floor(random() * values.length)] : null;
  const floors = oneCell.filter(asset => asset.layer === 'floor' && !asset.blocksMovement && (has(asset, 'stone') || has(asset, 'normal')));
  if (!floors.length) floors.push(...oneCell.filter(asset => asset.layer === 'floor' && !asset.blocksMovement));
  if (!floors.length) throw new Error('The assembler needs a one-cell floor asset.');
  const walls = oneCell.filter(asset => asset.layer === 'structure' && has(asset, 'wall'));
  const doors = oneCell.filter(asset => asset.layer === 'structure' && has(asset, 'door') && !asset.blocksMovement);
  const surfaces = oneCell.filter(asset => asset.layer === 'surface' && !asset.blocksMovement);
  const props = oneCell.filter(asset => asset.layer === 'prop' && !has(asset, 'exit') && !has(asset, 'stairs'));
  const details = oneCell.filter(asset => asset.layer === 'overlay' && !asset.blocksMovement && !has(asset, 'exit') && !has(asset, 'stairs'));
  const start = { x: 1, y: height - 2 }, exit = { x: width - 2, y: 1 };
  const entrance = { x: 0, y: start.y }, exitDoor = { x: exit.x, y: 0 };
  const clearRoute = [entrance, start];
  for (let x = start.x + 1; x <= exit.x; x++) clearRoute.push({ x, y: start.y });
  for (let y = start.y - 1; y >= exit.y; y--) clearRoute.push({ x: exit.x, y });
  clearRoute.push(exitDoor);
  const reserved = new Set(clearRoute.map(cell => key(cell.x, cell.y)));
  // Keep space around the two interaction points, not just their exact cell.
  for (const point of [start, exit]) for (let dy = -1; dy <= 1; dy++) for (let dx = -1; dx <= 1; dx++) reserved.add(key(point.x + dx, point.y + dy));
  const placements = [], blocked = new Set();
  const add = (asset, x, y, kind) => {
    if (!asset) return;
    placements.push({ id: `placement.${placements.length}`, assetId: asset.id, layer: asset.layer, x, y, ...(kind ? { kind } : {}), blocksMovement: asset.blocksMovement });
    if (asset.blocksMovement) blocked.add(key(x, y));
  };
  const oriented = (values, direction) => values.filter(asset => asset.id.endsWith(`-${direction}`) || has(asset, direction));
  for (let y = 0; y < height; y++) for (let x = 0; x < width; x++) {
    add(pick(floors), x, y);
    if (x === 0 || y === 0) {
      const doorway = x === entrance.x && y === entrance.y || x === exitDoor.x && y === exitDoor.y;
      const pool = doorway ? doors : walls;
      const direction = x === 0 ? 'nw' : 'ne';
      const candidates = oriented(pool, direction);
      const corner = !doorway && x === 0 && y === 0 ? pool.find(asset => has(asset, 'corner')) : null;
      add(corner || pick(candidates.length ? candidates : pool), x, y, doorway ? 'door' : 'wall');
      continue;
    }
    if (!reserved.has(key(x, y)) && x < width - 1 && y < height - 1) {
      if (random() < density * 0.4) add(pick(surfaces), x, y);
      if (random() < density) add(pick(props), x, y);
      else if (random() < 0.12) add(pick(details), x, y);
    }
  }
  const exitMarker = oneCell.find(asset => has(asset, 'exit') && !asset.blocksMovement) || oneCell.find(asset => has(asset, 'stairs') && !asset.blocksMovement);
  add(exitMarker, exit.x, exit.y, 'exit');
  return { schemaVersion: 1, kind: 'dungeon-room-authoring', manifest: 'assets/room-kit/manifest.json', seed, width, height, density, tile: { ...manifest.tile }, start, exit, doors: [{ ...entrance, kind: 'entrance' }, { ...exitDoor, kind: 'exit' }], clearRoute, blockedCells: [...blocked].map(value => { const [x, y] = value.split(',').map(Number); return { x, y }; }), placements };
}

export function findRoute(room, from = room.start, to = room.exit) {
  const blocked = new Set(room.blockedCells.map(cell => key(cell.x, cell.y)));
  const parents = new Map([[key(from.x, from.y), null]]), queue = [from];
  for (let index = 0; index < queue.length; index++) {
    const cell = queue[index];
    if (cell.x === to.x && cell.y === to.y) {
      const result = []; let current = cell;
      while (current) { result.push(current); current = parents.get(key(current.x, current.y)); }
      return result.reverse();
    }
    for (const [dx, dy] of [[0, -1], [-1, 0], [1, 0], [0, 1]]) {
      const next = { x: cell.x + dx, y: cell.y + dy }, id = key(next.x, next.y);
      if (next.x >= 0 && next.y >= 0 && next.x < room.width && next.y < room.height && !blocked.has(id) && !parents.has(id)) { parents.set(id, cell); queue.push(next); }
    }
  }
  return [];
}

/** Grid rotation is shared by drawing and inverse picking; component anchors never move. */
export function projectCell(x,y,rotation=0) {
  const q=((rotation%4)+4)%4;
  const [a,b]=q===1?[-y,x]:q===2?[-x,-y]:q===3?[y,-x]:[x,y];
  return {x:(a-b)*64,y:(a+b)*32};
}
export function pickCell(x,y,rotation=0) {
  const a=Math.round(x/128+y/64),b=Math.round(y/64-x/128);
  const q=((rotation%4)+4)%4;
  const [cx,cy]=q===1?[b,-a]:q===2?[-a,-b]:q===3?[-b,a]:[a,b];
  return {x:cx||0,y:cy||0};
}
export function validateRoom(room,manifest) {
  validateManifest(manifest);
  if(room?.schemaVersion!==1||room.kind!=='dungeon-room-authoring'||!Number.isInteger(room.width)||!Number.isInteger(room.height)||room.width<1||room.width>20||room.height<1||room.height>16||!Array.isArray(room.placements)||room.placements.length>5000)throw new Error('Unsupported room dimensions or schema.');
  const assets=new Map(manifest.assets.map(a=>[a.id,a])),ids=new Set();
  for(const p of room.placements){const a=assets.get(p.assetId);if(!a||typeof p.id!=='string'||ids.has(p.id)||p.layer!==a.layer||!Number.isInteger(p.x)||!Number.isInteger(p.y)||p.x<0||p.y<0||p.x>=room.width||p.y>=room.height||!Number.isInteger(p.rotation??0)||(p.rotation??0)<0||(p.rotation??0)>3)throw new Error('Invalid placement reference, position, layer or rotation.');ids.add(p.id);p.blocksMovement=a.blocksMovement;}
  for(const point of [room.start,room.exit,...(room.doors??[])])if(!point||!Number.isInteger(point.x)||!Number.isInteger(point.y)||point.x<0||point.y<0||point.x>=room.width||point.y>=room.height)throw new Error('Invalid entrance or exit.');
  room.blockedCells=[...new Set(room.placements.filter(p=>p.blocksMovement).map(p=>key(p.x,p.y)))].map(k=>{const [x,y]=k.split(',').map(Number);return{x,y};});
  room.clearRoute=findRoute(room);return room;
}
export function paintCell(room,manifest,assetId,x,y,rotation=0,erase=false) {
  const asset=manifest.assets.find(a=>a.id===assetId);if(!asset)throw new Error('Choose a valid asset.');
  if(!Number.isInteger(x)||!Number.isInteger(y)||x<0||y<0||x>=room.width||y>=room.height)return room;
  room.placements=room.placements.filter(p=>!(p.x===x&&p.y===y&&p.layer===asset.layer));
  if(!erase){let id=0;const ids=new Set(room.placements.map(p=>p.id));while(ids.has(`edit.${id}`))id++;room.placements.push({id:`edit.${id}`,assetId,layer:asset.layer,x,y,rotation,blocksMovement:asset.blocksMovement});}
  return validateRoom(room,manifest);
}

/** Exact EncounterDef tile records. Visual asset metadata stays in the separate room recipe. */
export function exportGameTiles(room,manifest) {
  const checked=validateRoom(structuredClone(room),manifest),assets=new Map(manifest.assets.map(a=>[a.id,a]));
  const tiles=[];
  for(let y=0;y<checked.height;y++)for(let x=0;x<checked.width;x++){
    const pieces=checked.placements.filter(p=>p.x===x&&p.y===y),tags=new Set();
    for(const p of pieces){const a=assets.get(p.assetId);if(a.tags.includes('water'))tags.add('surface.water');if(a.tags.includes('oil')&&['floor','surface'].includes(a.layer))tags.add('surface.oil');if(a.tags.includes('burning'))tags.add('surface.burning');}
    const blocked=pieces.some(p=>p.blocksMovement);if(blocked||tags.size)tiles.push({x,y,blocked,tags:[...tags].sort()});
  }
  return {width:checked.width,height:checked.height,tiles};
}

async function boot() {
  const $ = selector => document.querySelector(selector);
  const canvas = $('#room-canvas'), context = canvas.getContext('2d');
  const manifestUrl = new URL('assets/room-kit/manifest.json', location.href);
  const visible = new Set(LAYERS), images = new Map();
  let manifest, room, assetMap, filter = 'all',selectedAsset='stone-a',pieceRotation=0,cameraRotation=0,transform=null;
  const safeText = (tag, text, className) => { const element = document.createElement(tag); element.textContent = text; if (className) element.className = className; return element; };
  function renderGallery() {
    $('#asset-gallery').replaceChildren();
    for (const asset of manifest.assets.filter(asset => filter === 'all' || asset.layer === filter)) {
      const link = document.createElement('button'); link.className = 'asset-card'; link.type='button'; link.setAttribute('aria-pressed',String(selectedAsset===asset.id));link.title=`Paint ${asset.label || asset.id}`; link.addEventListener('click',()=>{selectedAsset=asset.id;$('#selected-piece').textContent=`${asset.label||asset.id} · ${asset.layer}`;renderGallery();});
      const thumbnail = document.createElement('div'); thumbnail.className = 'asset-thumbnail';
      const image = document.createElement('img'); image.src = new URL(asset.file, manifestUrl); image.alt = asset.label || asset.id; image.loading = 'lazy'; thumbnail.append(image);
      const info = document.createElement('div'); info.className = 'asset-info';
      const title = safeText('strong', asset.label || asset.id); title.append(safeText('span', '↓'));
      info.append(title, safeText('small', `${asset.layer} · ${asset.width} × ${asset.height}`)); link.append(thumbnail, info); $('#asset-gallery').append(link);
    }
  }
  function draw() {
    if (!room) return;
    const bounds = canvas.parentElement.getBoundingClientRect(), dpr = Math.min(devicePixelRatio || 1, 2);
    canvas.width = Math.max(1, Math.round(bounds.width * dpr)); canvas.height = Math.max(1, Math.round(bounds.height * dpr));
    context.setTransform(dpr, 0, 0, dpr, 0, 0); context.clearRect(0, 0, bounds.width, bounds.height); context.imageSmoothingEnabled = false;
    const project = (x,y)=>projectCell(x,y,cameraRotation);
    const corners=[[0,0],[room.width-1,0],[0,room.height-1],[room.width-1,room.height-1]].map(([x,y])=>project(x,y));
    let minX=Math.min(...corners.map(p=>p.x))-64,maxX=Math.max(...corners.map(p=>p.x))+64,minY=Math.min(...corners.map(p=>p.y))-100,maxY=Math.max(...corners.map(p=>p.y))+32;
    for (const placement of room.placements) {
      const asset = assetMap.get(placement.assetId), point = project(placement.x, placement.y);
      minX = Math.min(minX, point.x - asset.anchor.x); maxX = Math.max(maxX, point.x - asset.anchor.x + asset.width);
      minY = Math.min(minY, point.y - asset.anchor.y); maxY = Math.max(maxY, point.y - asset.anchor.y + asset.height);
    }
    const scale = Math.min((bounds.width - 42) / (maxX - minX), (bounds.height - 44) / (maxY - minY), 1.65);
    transform={scale,offsetX:(bounds.width-(maxX-minX)*scale)/2-minX*scale,offsetY:(bounds.height-(maxY-minY)*scale)/2-minY*scale};
    context.translate((bounds.width - (maxX - minX) * scale) / 2 - minX * scale, (bounds.height - (maxY - minY) * scale) / 2 - minY * scale); context.scale(scale, scale);
    // Ground planes first. Upright pieces then share a depth order so walls and props occlude naturally.
    const rank = layer => layer === 'floor' ? 0 : layer === 'surface' ? 1 : 2;
    const sorted = [...room.placements].sort((a, b) => rank(a.layer) - rank(b.layer) || project(a.x,a.y).y-project(b.x,b.y).y || a.y - b.y || LAYERS.indexOf(a.layer) - LAYERS.indexOf(b.layer));
    for (const placement of sorted) {
      if (!visible.has(placement.layer)) continue;
      const asset = assetMap.get(placement.assetId), point = project(placement.x, placement.y);
      const q=((placement.rotation??0)+cameraRotation)%4;
      const variantId=q%2?asset.id.replace(/-ne$/, '-TEMP').replace(/-nw$/, '-ne').replace(/-TEMP$/, '-nw'):asset.id;
      const variant=assetMap.get(variantId)??asset;
      context.save();context.translate(point.x,point.y);
      if(['floor','surface'].includes(asset.layer)||asset.tags.includes('decal')){if(q===1)context.transform(0,.5,-2,0,0,0);else if(q===2)context.scale(-1,-1);else if(q===3)context.transform(0,-.5,2,0,0,0);}
      else if(q>=2)context.scale(-1,1);
      context.drawImage(images.get(variant.id),-variant.anchor.x,-variant.anchor.y,variant.width,variant.height);context.restore();
    }
    function diamond(cell, color, label) {
      const point = project(cell.x, cell.y), w = manifest.tile.width / 2, h = manifest.tile.height / 2;
      context.beginPath(); context.moveTo(point.x, point.y - h * 0.75); context.lineTo(point.x + w * 0.75, point.y); context.lineTo(point.x, point.y + h * 0.75); context.lineTo(point.x - w * 0.75, point.y); context.closePath(); context.fillStyle = `${color}33`; context.fill(); context.strokeStyle = color; context.lineWidth = 2; context.stroke();
      if (label) { context.font = 'bold 12px monospace'; context.textAlign = 'center'; context.fillStyle = '#101820'; context.fillRect(point.x - 17, point.y - 8, 34, 16); context.fillStyle = color; context.fillText(label, point.x, point.y + 4); }
    }
    if ($('#show-route').checked) for (const cell of room.clearRoute) diamond(cell, '#e9c77e');
    diamond(room.start, '#b2dab3', 'IN'); diamond(room.exit, '#efce89', 'OUT');
  }
  function assemble() {
    const [width, height] = $('#size').value.split(',').map(Number), density = Number($('#density').value) / 100;
    $('#size-value').textContent = `${width} × ${height}`; $('#density-value').textContent = `${Math.round(density * 100)}%`;
    room = generateRoom(manifest, { seed: $('#seed').value, width, height, density });
    $('#room-title').textContent = `Service room / ${room.seed || '(empty seed)'}`;
    const propCount = room.placements.filter(p => p.layer === 'prop').length;
    $('#room-summary').textContent = `${width * height} floor cells · ${propCount} props · ${room.placements.length} PNG placements`;
    canvas.setAttribute('aria-label', `${width} by ${height} seeded isometric room. ${propCount} props; clear entrance-to-exit route. Seed ${room.seed}.`); draw();
    window.roomWorkshop = { getRoom: () => structuredClone(room), generate: assemble,exportGameTiles:()=>exportGameTiles(room,manifest),importRoom:value=>{room=validateRoom(structuredClone(value),manifest);draw();},paint:(x,y,id=selectedAsset,q=pieceRotation,erase=false)=>{paintCell(room,manifest,id,x,y,q,erase);draw();},cellToScreen:(x,y)=>{const p=projectCell(x,y,cameraRotation);return{x:p.x*transform.scale+transform.offsetX,y:p.y*transform.scale+transform.offsetY};},getRotation:()=>cameraRotation };
  }
  try {
    if (!context) throw new Error('This browser does not support Canvas 2D.');
    const response = await fetch(manifestUrl); if (!response.ok) throw new Error(`PNG manifest returned HTTP ${response.status}.`);
    manifest = validateManifest(await response.json()); assetMap = new Map(manifest.assets.map(asset => [asset.id, asset]));
    await Promise.all(manifest.assets.map(asset => new Promise((resolve, reject) => { const image = new Image(); image.onload = () => { images.set(asset.id, image); resolve(); }; image.onerror = () => reject(new Error(`Could not load ${asset.file}.`)); image.src = new URL(asset.file, manifestUrl); })));
    $('#loading').hidden = true;
    for (const layer of LAYERS) {
      const button = safeText('button', layer, 'layer-toggle'); button.setAttribute('aria-pressed', 'true');
      button.addEventListener('click', () => { visible.has(layer) ? visible.delete(layer) : visible.add(layer); button.setAttribute('aria-pressed', String(visible.has(layer))); draw(); }); $('#layers').append(button);
    }
    for (const layer of ['all', ...LAYERS]) {
      const button = safeText('button', layer); button.setAttribute('aria-pressed', String(layer === filter));
      button.addEventListener('click', () => { filter = layer; for (const item of $('#gallery-filter').children) item.setAttribute('aria-pressed', String(item === button)); renderGallery(); }); $('#gallery-filter').append(button);
    }
    $('#rotate-piece').addEventListener('click',()=>{pieceRotation=(pieceRotation+1)%4;$('#rotate-piece').textContent=`Piece rotation: ${pieceRotation*90}°`;});
    $('#rotate-camera').addEventListener('click',()=>{cameraRotation=(cameraRotation+1)%4;$('#rotate-camera').textContent=`Map view: ${['North','East','South','West'][cameraRotation]}`;draw();});
    canvas.addEventListener('click',event=>{if(!transform)return;const box=canvas.getBoundingClientRect();const cell=pickCell((event.clientX-box.left-transform.offsetX)/transform.scale,(event.clientY-box.top-transform.offsetY)/transform.scale,cameraRotation);paintCell(room,manifest,selectedAsset,cell.x,cell.y,pieceRotation,$('#erase-piece').checked);$('#room-summary').textContent=`${room.placements.length} placements · ${room.clearRoute.length?'entrance connected':'entrance blocked'} · edited`;draw();});
    $('#import-json').addEventListener('change',async event=>{const file=event.target.files[0];if(!file)return;try{const candidate=validateRoom(JSON.parse(await file.text()),manifest);room=candidate;$('#room-title').textContent='Imported room';draw();$('#room-summary').textContent=`Imported ${room.placements.length} validated placements`;}catch(error){$('#room-summary').textContent=`Import rejected: ${error.message}`;}event.target.value='';});
    $('#generate').addEventListener('click', assemble); $('#size').addEventListener('change', assemble); $('#density').addEventListener('input', assemble);
    $('#seed').addEventListener('keydown', event => { if (event.key === 'Enter') assemble(); });
    $('#shuffle').addEventListener('click', () => { const values = new Uint32Array(1); crypto.getRandomValues(values); $('#seed').value = `room-${values[0].toString(36)}`; assemble(); });
    $('#show-route').addEventListener('change', draw);
    $('#export-game-tiles').addEventListener('click',()=>{const url=URL.createObjectURL(new Blob([JSON.stringify(exportGameTiles(room,manifest),null,2)+'\n'],{type:'application/json'}));const link=document.createElement('a');link.href=url;link.download='encounter-map-tiles.json';link.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
    $('#export-json').disabled = false; $('#export-json').addEventListener('click', () => { const url = URL.createObjectURL(new Blob([JSON.stringify(room, null, 2) + '\n'], { type: 'application/json' })); const link = document.createElement('a'); link.href = url; link.download = `room-${room.seed.replace(/[^a-z0-9_-]/gi, '_') || 'untitled'}.json`; link.click(); setTimeout(() => URL.revokeObjectURL(url), 1000); });
    new ResizeObserver(draw).observe(canvas.parentElement); renderGallery(); assemble();
  } catch (error) { $('#loading').textContent = `The kit could not load. ${error.message} Serve this folder over HTTP and reload.`; $('#loading').classList.add('error'); $('#room-summary').textContent = 'Asset loading failed'; $('#generate').disabled = true; }
}

if (typeof document !== 'undefined') boot();
