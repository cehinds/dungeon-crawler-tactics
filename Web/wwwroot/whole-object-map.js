import { seededRandom, findRoute } from './room-kit.js';
import { generateDungeon, getPlayableMap } from './procedural-map.js';

export const WHOLE_OBJECT_ASSET_BASE = 'https://raw.githubusercontent.com/cehinds/AI-Art/a0483c7db869f28e35bf2878d22e9bc68ead77a7/dungeon-crawler-tactics/Web/wwwroot/assets/top-down-object-kit/';
const DIRECTIONS = [['north',0,-1],['east',1,0],['south',0,1],['west',-1,0]];
const key = p => `${p.x},${p.y}`;
const inside = (r,x,y) => x>=r.x && y>=r.y && x<r.x+r.width && y<r.y+r.height;
const cellsOf = r => Array.from({length:r.width*r.height},(_,i)=>({x:r.x+i%r.width,y:r.y+Math.floor(i/r.width)}));
const copy = value => structuredClone(value);
function weighted(values,random) { let n=random()*values.reduce((sum,v)=>sum+v.weight,0); for(const value of values){n-=value.weight;if(n<0)return value;}return values.at(-1); }
function flood(width,height,blocked,start) { const seen=new Set([key(start)]),queue=[start];for(let i=0;i<queue.length;i++)for(const [,dx,dy] of DIRECTIONS){const p={x:queue[i].x+dx,y:queue[i].y+dy};if(p.x>=0&&p.y>=0&&p.x<width&&p.y<height&&!blocked.has(key(p))&&!seen.has(key(p))){seen.add(key(p));queue.push(p);}}return seen; }

export function validateWholeObjectRules(rules,library) {
  if(rules?.schemaVersion!==1||!Array.isArray(rules.themes)||!rules.themes.length||!Array.isArray(rules.templates))throw new Error('Missing whole-object room rules.');
  const objects=new Set(library?.objects?.map(o=>o.id));const ids=new Set();
  for(const t of rules.templates){if(!t.id||ids.has(t.id)||!Array.isArray(t.furnishings))throw new Error('Invalid/duplicate room template.');ids.add(t.id);const entries=new Set();for(const f of t.furnishings){if(!f.id||entries.has(f.id)||!f.objectIds?.length||f.objectIds.some(id=>!objects.has(id))||!Array.isArray(f.footprint)||f.footprint.length!==2||f.footprint.some(v=>!Number.isInteger(v)||v<1||v>6)||!f.rotations?.length||f.rotations.some(v=>![0,90,180,270].includes(v))||!Number.isInteger(f.min)||!Number.isInteger(f.max)||f.min<0||f.max<f.min||f.max>12||!Number.isFinite(f.priority)||typeof f.blocksMovement!=='boolean'||!['wall','center','anywhere'].includes(f.placement)||!Number.isInteger(f.clearance??0)||(f.clearance??0)<0||(f.clearance??0)>2||!Array.isArray(f.surfaceAffinity??['floor:stone']))throw new Error(`Invalid furnishing ${t.id}/${f.id}`);entries.add(f.id);}}
  const themes=new Set();for(const t of rules.themes){if(!t.id||themes.has(t.id)||typeof t.floorTag!=='string'||!t.roomTypes?.length||t.roomTypes.some(v=>!ids.has(v.templateId)||!Number.isInteger(v.weight)||v.weight<1))throw new Error('Invalid theme/room weight.');themes.add(t.id);}
  return rules;
}

/** Existing Foundry geometry first; this module adds semantic, full-footprint dressing only. */
export function generateWholeObjectMap(library,options={},rules,canonicalManifest) {
  validateWholeObjectRules(rules,library);
  const seed=options.seed??'whole-floor-1',themeId=options.theme??rules.themes[0].id;
  if(typeof seed!=='string'||seed.length>120)throw new Error('Seed must be a string up to120 characters.');
  const theme=rules.themes.find(t=>t.id===themeId);if(!theme)throw new Error('Unknown room theme.');
  if(!canonicalManifest)throw new Error('Load the canonical room-kit manifest before generation.');
  const layoutOptions={width:options.width??20,height:options.height??16,roomCount:options.roomCount??3,density:0,layout:'chambers',biome:'stone'};
  let base=generateDungeon(canonicalManifest,{...layoutOptions,seed});
  const desiredMinimum=base.width>=18&&base.height>=14?5:4;
  const roomScore=room=>Math.min(...room.rooms.map(r=>Math.min(r.width,r.height)));
  let geometryAttempts=1;
  // Retry the existing Foundry partitioner with deterministic derived seeds; no second layout engine.
  if(base.width>=12&&base.height>=10){const suffix=Math.floor(seededRandom(seed)()*0xffffffff).toString(16);for(let attempt=1;attempt<48&&roomScore(base)<desiredMinimum;attempt++){
    const candidate=generateDungeon(canonicalManifest,{...layoutOptions,seed:`${seed.slice(0,85)}|${suffix}|rooms${attempt}`});geometryAttempts++;
    if(roomScore(candidate)>roomScore(base))base=candidate;
  }}
  const {width,height}=base;const geometryBlocked=new Set(base.blockedCells.map(key));
  const floor=new Set();for(let y=0;y<height;y++)for(let x=0;x<width;x++)if(!geometryBlocked.has(`${x},${y}`))floor.add(`${x},${y}`);
  const cells=[];for(let y=0;y<height;y++)for(let x=0;x<width;x++){const open=floor.has(`${x},${y}`),edges={};for(const [name,dx,dy] of DIRECTIONS){const next=floor.has(`${x+dx},${y+dy}`);edges[name]=open&&next?`join:${theme.floorTag}`:open!==next?`boundary:${theme.floorTag}`:`solid:${theme.floorTag}`;}cells.push({x,y,kind:open?'floor':DIRECTIONS.some(([,dx,dy])=>floor.has(`${x+dx},${y+dy}`))?'wall':'void',blocked:!open,tags:[`${open?'floor':'wall'}:${theme.floorTag}`],edges});}
  const cellMap=new Map(cells.map(c=>[key(c),c]));const random=seededRandom(`${seed}:whole-objects:v1:${themeId}`);const templates=new Map(rules.templates.map(t=>[t.id,t]));
  const rooms=base.rooms.map(r=>({...copy(r),templateId:weighted(theme.roomTypes,random).templateId}));
  const corridorSet=new Set(base.corridors.flatMap(c=>c.cells).map(key));const doors=[];const doorIds=new Set();
  for(const room of rooms)for(const p of cellsOf(room))for(const [side,dx,dy] of DIRECTIONS){const next={x:p.x+dx,y:p.y+dy};if(!inside(room,next.x,next.y)&&floor.has(key(next))&&(corridorSet.has(key(next))||corridorSet.has(key(p)))){const id=room.id+':'+key(p);if(!doorIds.has(id)){doors.push({...p,roomId:room.id,side});doorIds.add(id);}}}
  const doorClear=new Set();for(const door of [...doors,base.start,base.exit])for(let dy=-1;dy<=1;dy++)for(let dx=-1;dx<=1;dx++){const p={x:door.x+dx,y:door.y+dy};if(floor.has(key(p)))doorClear.add(key(p));}
  const reserved=new Set([...base.generation.protectedCells.map(key),...doorClear]);
  const occupied=new Set(),halos=new Set(),blocked=new Set(geometryBlocked),objects=[],diagnostics=[];
  function support(rect,side){const points=side==='north'?Array.from({length:rect.width},(_,i)=>({x:rect.x+i,y:rect.y})):side==='south'?Array.from({length:rect.width},(_,i)=>({x:rect.x+i,y:rect.y+rect.height-1})):side==='west'?Array.from({length:rect.height},(_,i)=>({x:rect.x,y:rect.y+i})):Array.from({length:rect.height},(_,i)=>({x:rect.x+rect.width-1,y:rect.y+i}));return points.every(p=>cellMap.get(key(p))?.edges[side]===`boundary:${theme.floorTag}`);}
  function safe(rect,item){const footprint=cellsOf(rect);if(footprint.some(p=>!floor.has(key(p))||occupied.has(key(p))||halos.has(key(p))||doorClear.has(key(p))||(item.blocksMovement&&reserved.has(key(p)))||!(item.surfaceAffinity??[`floor:${theme.floorTag}`]).some(tag=>cellMap.get(key(p)).tags.includes(tag))))return false;
    const clearance=item.clearance??0;for(let y=rect.y-clearance;y<rect.y+rect.height+clearance;y++)for(let x=rect.x-clearance;x<rect.x+rect.width+clearance;x++){if(x<rect.x||x>=rect.x+rect.width||y<rect.y||y>=rect.y+rect.height){if(occupied.has(`${x},${y}`))return false;}}
    if(item.blocksMovement){const candidate=new Set(blocked);footprint.forEach(p=>candidate.add(key(p)));const reachable=flood(width,height,candidate,base.start);if(reachable.size!==width*height-candidate.size)return false;}
    return true;}
  const byObject=new Map(library.objects.map(o=>[o.id,o]));
  for(const room of rooms){const template=templates.get(room.templateId);room.role=room.width>=4&&room.height>=4?'furnished-room':'unfurnished-passage';if(room.role==='unfurnished-passage'){diagnostics.push({roomId:room.id,reason:'Narrow partition retained as an unfurnished passage; no room-scale furniture.'});continue;}for(const item of [...template.furnishings].sort((a,b)=>b.priority-a.priority||(a.id<b.id?-1:a.id>b.id?1:0))){const desired=item.min+Math.floor(random()*(item.max-item.min+1));let placed=0;
      for(let n=0;n<desired;n++){const candidates=[];for(const rotationDegrees of item.rotations){const swapped=rotationDegrees%180!==0,w=item.footprint[swapped?1:0],h=item.footprint[swapped?0:1];for(let y=room.y;y+h<=room.y+room.height;y++)for(let x=room.x;x+w<=room.x+room.width;x++){const rect={x,y,width:w,height:h};const sides=['north','east','south','west'].filter(side=>support(rect,side));if(item.placement==='wall'&&(!sides.length||(w>h&&!sides.some(s=>['north','south'].includes(s)))||(h>w&&!sides.some(s=>['east','west'].includes(s)))))continue;if(!safe(rect,item))continue;const distance=Math.abs(x+(w-1)/2-room.center.x)+Math.abs(y+(h-1)/2-room.center.y);candidates.push({rect,rotationDegrees,sides,score:item.placement==='center'?distance:0,tie:random()});}}
        if(!candidates.length)break;candidates.sort((a,b)=>a.score-b.score||a.tie-b.tie||a.rect.y-b.rect.y||a.rect.x-b.rect.x||a.rotationDegrees-b.rotationDegrees);const chosen=candidates[0],object=byObject.get(item.objectIds[Math.floor(random()*item.objectIds.length)]);const bounds=object.visibleBounds;const sourceVisibleBounds=[bounds[0],bounds[1],bounds[2]-bounds[0],bounds[3]-bounds[1]];
        const entry={id:`object.${objects.length}`,assetId:object.id,objectId:object.id,assetPath:object.asset.path,roomId:room.id,templateId:template.id,ruleId:item.id,...chosen.rect,rotationDegrees:chosen.rotationDegrees,z:object.category.match(/rug|floor|carpet/)?0:20,blocksMovement:item.blocksMovement,clearance:item.clearance??0,placement:item.placement,attachmentEdges:chosen.sides,surfaceAffinity:copy(item.surfaceAffinity??[`floor:${theme.floorTag}`]),sourceVisibleBounds,pivot:copy(object.pivot),fit:'contain-uniform'};
        objects.push(entry);cellsOf(chosen.rect).forEach(p=>{occupied.add(key(p));if(item.blocksMovement)blocked.add(key(p));});if(item.clearance)for(let y=chosen.rect.y-item.clearance;y<chosen.rect.y+chosen.rect.height+item.clearance;y++)for(let x=chosen.rect.x-item.clearance;x<chosen.rect.x+chosen.rect.width+item.clearance;x++)if(!inside(chosen.rect,x,y))halos.add(`${x},${y}`);placed++;}
      if(placed<item.min)diagnostics.push({roomId:room.id,ruleId:item.id,requestedMinimum:item.min,placed,reason:'No footprint satisfies connectivity, doorway, surface, wall-edge or clearance constraints.'});}}
  for(const cell of cells)cell.blocked=blocked.has(key(cell));
  const blockedCells=[...blocked].map(s=>{const [x,y]=s.split(',').map(Number);return{x,y};}).sort((a,b)=>a.y-b.y||a.x-b.x);
  const map={schemaVersion:1,kind:'whole-object-map',generationVersion:1,geometrySeed:base.seed,geometryAttempts,minimumRoomDimension:roomScore(base),seed,theme:themeId,width,height,tileSize:48,cells,rooms,corridors:copy(base.corridors),doors,entrance:copy(base.start),start:copy(base.start),exit:copy(base.exit),playerSpawns:copy(base.playerSpawns),enemies:copy(base.enemies),clearRoute:findRoute({width,height,start:base.start,exit:base.exit,blockedCells}),reservedCells:[...reserved].map(s=>{const[x,y]=s.split(',').map(Number);return{x,y};}),doorClearanceCells:[...doorClear].map(s=>{const[x,y]=s.split(',').map(Number);return{x,y};}),blockedCells,objects,diagnostics,canonicalMap:getPlayableMap(base,canonicalManifest)};
  const validation=validateWholeObjectMap(map,library);if(!validation.valid)throw new Error(validation.errors.join(' '));return map;
}

export function validateWholeObjectMap(map,library) {
  const errors=[];if(!map||map.kind!=='whole-object-map'||!Number.isInteger(map.width)||map.width<6||map.width>20||!Number.isInteger(map.height)||map.height<6||map.height>16||!Array.isArray(map.cells)||map.cells.length!==map.width*map.height||!Array.isArray(map.objects)||!Array.isArray(map.reservedCells)||!Array.isArray(map.doorClearanceCells))return{valid:false,errors:['Unsupported generated map.']};
  const blocked=new Set(map.cells.filter(c=>c.blocked).map(key)),open=new Map(map.cells.filter(c=>c.kind==='floor').map(c=>[key(c),c]));const occupied=new Set();const ids=new Set(library?.objects?.map(o=>o.id)??[]);const reserved=new Set(map.reservedCells.map(key)),doorClear=new Set(map.doorClearanceCells.map(key));
  for(const object of map.objects){if(![object.x,object.y,object.width,object.height].every(Number.isInteger)||object.width<1||object.height<1||object.x<0||object.y<0||object.x+object.width>map.width||object.y+object.height>map.height||![0,90,180,270].includes(object.rotationDegrees)){errors.push('Invalid object footprint/rotation.');continue;}if(!ids.has(object.assetId))errors.push('Unknown object asset.');for(const p of cellsOf(object)){const k=key(p);if(!open.has(k)||occupied.has(k)||doorClear.has(k)||(object.blocksMovement&&reserved.has(k)))errors.push('Object footprint overlaps, leaves floor or blocks a reserved approach.');occupied.add(k);if(object.blocksMovement&&!blocked.has(k))errors.push('Object collision footprint disagrees.');}if(object.placement==='wall'&&!object.attachmentEdges.length)errors.push('Wall object lacks compatible boundary attachment.');}
  const reached=flood(map.width,map.height,blocked,map.entrance);if(reached.size!==map.width*map.height-blocked.size)errors.push('Walkable floor disconnected.');for(const p of [map.entrance,map.exit,...map.playerSpawns,...map.enemies,...map.rooms.map(r=>r.center)])if(blocked.has(key(p))||!reached.has(key(p)))errors.push('Reserved point unreachable.');
  const grid=new Map(map.cells.map(c=>[key(c),c]));const opposite={north:'south',east:'west',south:'north',west:'east'};for(const cell of map.cells)for(const [direction,dx,dy] of DIRECTIONS){const next=grid.get(`${cell.x+dx},${cell.y+dy}`);if(next&&cell.edges[direction]!==next.edges[opposite[direction]])errors.push('Cardinal edge join mismatch.');}
  return{valid:errors.length===0,errors:[...new Set(errors)]};
}

/** Strict current workshop schema: new sprites remain preview-only, collision is shared. */
export function exportWholeObjectGameMap(map) {
  const validation=validateWholeObjectMap(map,{objects:map.objects.map(o=>({id:o.assetId}))});if(!validation.valid)throw new Error('Cannot export invalid generated map: '+validation.errors.join(' '));
  const output=copy(map.canonicalMap);output.label=`Whole objects / ${map.theme} / ${map.seed}`.slice(0,100);
  const tiles=new Map(output.tiles.map(t=>[key(t),t]));for(const object of map.objects)if(object.blocksMovement)for(const p of cellsOf(object))tiles.set(key(p),{...p,blocked:true,tags:tiles.get(key(p))?.tags??[]});output.tiles=[...tiles.values()].sort((a,b)=>a.y-b.y||a.x-b.x);return output;
}
