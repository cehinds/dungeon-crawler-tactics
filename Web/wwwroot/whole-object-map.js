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

function rotateRect(rect,width,height,degrees) {
  const {x,y,width:w,height:h}=rect;
  if(degrees===90)return {x:height-y-h,y:x,width:h,height:w};
  if(degrees===180)return {x:width-x-w,y:height-y-h,width:w,height:h};
  if(degrees===270)return {x:y,y:width-x-w,width:h,height:w};
  return {...rect};
}
function assemblyLayout(rule,degrees) {
  const members=rule.members.map(member=>{const swapped=member.rotationDegrees%180!==0;return {member,rect:{x:member.offset[0],y:member.offset[1],width:member.footprint[swapped?1:0],height:member.footprint[swapped?0:1]}};});
  const access=(rule.access??[]).map(a=>({x:a.offset[0],y:a.offset[1],width:a.footprint[0],height:a.footprint[1]}));
  const all=[...members.map(m=>m.rect),...access],width=Math.max(...all.map(r=>r.x+r.width)),height=Math.max(...all.map(r=>r.y+r.height));
  return {width:degrees%180?height:width,height:degrees%180?width:height,members:members.map(m=>({...m,rect:rotateRect(m.rect,width,height,degrees)})),access:access.map(r=>rotateRect(r,width,height,degrees))};
}
function validateAssembly(rule,objectIds,templateId) {
  const footprint=v=>Array.isArray(v)&&v.length===2&&v.every(n=>Number.isInteger(n)&&n>=1&&n<=6);
  const offset=v=>Array.isArray(v)&&v.length===2&&v.every(n=>Number.isInteger(n)&&n>=0&&n<=12);
  if(!rule.id||!Number.isInteger(rule.min)||!Number.isInteger(rule.max)||rule.min<0||rule.max<rule.min||rule.max>6||!Number.isFinite(rule.priority)||!['wall','center','anywhere'].includes(rule.placement)||!rule.rotations?.length||rule.rotations.some(r=>![0,90,180,270].includes(r))||!Number.isInteger(rule.clearance??0)||(rule.clearance??0)<0||(rule.clearance??0)>2||!Array.isArray(rule.members)||!rule.members.length||rule.members.length>12)throw new Error(`Invalid assembly ${templateId}/${rule.id}`);
  const ids=new Set();for(const member of rule.members){if(!member.id||ids.has(member.id)||!member.objectIds?.length||member.objectIds.some(id=>!objectIds.has(id))||!offset(member.offset)||!footprint(member.footprint)||![0,90,180,270].includes(member.rotationDegrees)||!['prop','underlay'].includes(member.layer)||typeof member.blocksMovement!=='boolean'||(member.layer==='underlay'&&member.blocksMovement)||(member.supportEdge&&!['north','east','south','west'].includes(member.supportEdge)))throw new Error(`Invalid assembly member ${rule.id}/${member.id}`);ids.add(member.id);}
  for(const access of rule.access??[])if(!offset(access.offset)||!footprint(access.footprint))throw new Error(`Invalid assembly access ${rule.id}`);
  const layout=assemblyLayout(rule,0),solid=new Set(),underlay=new Set();for(const {member,rect}of layout.members)for(const p of cellsOf(rect)){const set=member.layer==='underlay'?underlay:solid;if(set.has(key(p)))throw new Error(`Assembly members overlap without explicit underlay: ${rule.id}`);set.add(key(p));}
  for(const access of layout.access)if(cellsOf(access).some(p=>solid.has(key(p))))throw new Error(`Assembly access overlaps a prop: ${rule.id}`);
}

export function validateWholeObjectRules(rules,library) {
  if(rules?.schemaVersion!==1||!Array.isArray(rules.themes)||!rules.themes.length||!Array.isArray(rules.templates))throw new Error('Missing whole-object room rules.');
  const objects=new Set(library?.objects?.map(o=>o.id));const ids=new Set();
  for(const t of rules.templates){if(!t.id||ids.has(t.id)||!Array.isArray(t.furnishings))throw new Error('Invalid/duplicate room template.');ids.add(t.id);const entries=new Set();for(const f of t.furnishings){if(!f.id||entries.has(f.id)||!f.objectIds?.length||f.objectIds.some(id=>!objects.has(id))||!Array.isArray(f.footprint)||f.footprint.length!==2||f.footprint.some(v=>!Number.isInteger(v)||v<1||v>6)||!f.rotations?.length||f.rotations.some(v=>![0,90,180,270].includes(v))||!Number.isInteger(f.min)||!Number.isInteger(f.max)||f.min<0||f.max<f.min||f.max>12||!Number.isFinite(f.priority)||typeof f.blocksMovement!=='boolean'||!['wall','center','anywhere'].includes(f.placement)||!Number.isInteger(f.clearance??0)||(f.clearance??0)<0||(f.clearance??0)>2||!Array.isArray(f.surfaceAffinity??['floor:stone']))throw new Error(`Invalid furnishing ${t.id}/${f.id}`);entries.add(f.id);}const assemblies=new Set();for(const assembly of t.assemblies??[]){if(assemblies.has(assembly.id))throw new Error('Duplicate assembly rule.');assemblies.add(assembly.id);validateAssembly(assembly,objects,t.id);}}
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
  const occupied=new Set(),underlayOccupied=new Set(),assemblyEnvelopes=new Set(),halos=new Set(),blocked=new Set(geometryBlocked),objects=[],assemblies=[],diagnostics=[];
  function support(rect,side){const points=side==='north'?Array.from({length:rect.width},(_,i)=>({x:rect.x+i,y:rect.y})):side==='south'?Array.from({length:rect.width},(_,i)=>({x:rect.x+i,y:rect.y+rect.height-1})):side==='west'?Array.from({length:rect.height},(_,i)=>({x:rect.x,y:rect.y+i})):Array.from({length:rect.height},(_,i)=>({x:rect.x+rect.width-1,y:rect.y+i}));return points.every(p=>cellMap.get(key(p))?.edges[side]===`boundary:${theme.floorTag}`);}
  function safe(rect,item){const footprint=cellsOf(rect);if(footprint.some(p=>!floor.has(key(p))||(item.layer==='underlay'?underlayOccupied.has(key(p)):occupied.has(key(p))||halos.has(key(p))||assemblyEnvelopes.has(key(p)))||(item.layer!=='underlay'&&doorClear.has(key(p)))||(item.blocksMovement&&reserved.has(key(p)))||!(item.surfaceAffinity??[`floor:${theme.floorTag}`]).some(tag=>cellMap.get(key(p)).tags.includes(tag))))return false;
    const clearance=item.clearance??0;for(let y=rect.y-clearance;y<rect.y+rect.height+clearance;y++)for(let x=rect.x-clearance;x<rect.x+rect.width+clearance;x++){if(x<rect.x||x>=rect.x+rect.width||y<rect.y||y>=rect.y+rect.height){if(item.layer!=='underlay'&&occupied.has(`${x},${y}`))return false;}}
    if(item.blocksMovement){const candidate=new Set(blocked);footprint.forEach(p=>candidate.add(key(p)));const reachable=flood(width,height,candidate,base.start);if(reachable.size!==width*height-candidate.size)return false;}
    return true;}
  const byObject=new Map(library.objects.map(o=>[o.id,o]));
  function objectEntry(object,room,ruleId,rect,rotationDegrees,item,extra={}) {
    const b=object.visibleBounds;
    return {id:`object.${objects.length}`,assetId:object.id,objectId:object.id,assetPath:object.asset.path,roomId:room.id,templateId:room.templateId,ruleId,...rect,rotationDegrees,z:item.z??(item.layer==='underlay'||object.category.match(/rug|floor|carpet/)?0:20),blocksMovement:item.blocksMovement,clearance:item.clearance??0,placement:item.placement??'anywhere',attachmentEdges:['north','east','south','west'].filter(side=>support(rect,side)),surfaceAffinity:copy(item.surfaceAffinity??[`floor:${theme.floorTag}`]),sourceVisibleBounds:[b[0],b[1],b[2]-b[0],b[3]-b[1]],pivot:copy(object.pivot),fit:'contain-uniform',layer:item.layer??'prop',...extra};
  }
  function placeAssemblies(room,template) {
    for(const rule of [...(template.assemblies??[])].sort((a,b)=>b.priority-a.priority||(a.id<b.id?-1:a.id>b.id?1:0))){
      const desired=rule.min+Math.floor(random()*(rule.max-rule.min+1));let placed=0;
      for(let count=0;count<desired;count++){
        const candidates=[];
        for(const rotationDegrees of rule.rotations){const layout=assemblyLayout(rule,rotationDegrees);
          for(let y=room.y;y+layout.height<=room.y+room.height;y++)for(let x=room.x;x+layout.width<=room.x+room.width;x++){
            const envelope={x,y,width:layout.width,height:layout.height};
            if(cellsOf(envelope).some(p=>!floor.has(key(p))||occupied.has(key(p))||assemblyEnvelopes.has(key(p))))continue;
            if(rule.placement==='wall'&&!['north','east','south','west'].some(side=>support(envelope,side)))continue;
            const members=layout.members.map(({member,rect})=>({member,rect:{...rect,x:x+rect.x,y:y+rect.y}}));
            const access=layout.access.flatMap(rect=>cellsOf({...rect,x:x+rect.x,y:y+rect.y}));
            const localProps=new Set(members.filter(m=>m.member.layer!=='underlay').flatMap(m=>cellsOf(m.rect)).map(key));
            if(access.some(p=>!floor.has(key(p))||occupied.has(key(p))||blocked.has(key(p))||localProps.has(key(p))))continue;
            let valid=true;
            for(const {member,rect}of members){const item={...member,clearance:0,surfaceAffinity:member.surfaceAffinity??rule.surfaceAffinity??[`floor:${theme.floorTag}`]};
              if(!safe(rect,{...item,blocksMovement:false})||(member.blocksMovement&&cellsOf(rect).some(p=>reserved.has(key(p))))){valid=false;break;}
              if(member.supportEdge){const side=DIRECTIONS[(DIRECTIONS.findIndex(d=>d[0]===member.supportEdge)+rotationDegrees/90)%4][0];if(!support(rect,side)){valid=false;break;}}
            }
            if(!valid)continue;
            const gap=rule.clearance??0;for(let yy=y-gap;yy<y+layout.height+gap;yy++)for(let xx=x-gap;xx<x+layout.width+gap;xx++)if(!inside(envelope,xx,yy)&&occupied.has(`${xx},${yy}`))valid=false;
            if(!valid)continue;
            const candidateBlocked=new Set(blocked);for(const m of members)if(m.member.blocksMovement)cellsOf(m.rect).forEach(p=>candidateBlocked.add(key(p)));
            const reachable=flood(width,height,candidateBlocked,base.start);if(reachable.size!==width*height-candidateBlocked.size||access.some(p=>!reachable.has(key(p))))continue;
            const score=rule.placement==='center'?Math.abs(x+(layout.width-1)/2-room.center.x)+Math.abs(y+(layout.height-1)/2-room.center.y):0;
            candidates.push({envelope,members,access,rotationDegrees,score,tie:random()});
          }
        }
        if(!candidates.length)break;
        candidates.sort((a,b)=>a.score-b.score||a.tie-b.tie||a.envelope.y-b.envelope.y||a.envelope.x-b.envelope.x||a.rotationDegrees-b.rotationDegrees);
        const chosen=candidates[0],assemblyId=`assembly.${assemblies.length}`,memberIds=[];
        for(const {member,rect}of chosen.members){const object=byObject.get(member.objectIds[Math.floor(random()*member.objectIds.length)]),item={...member,clearance:0,surfaceAffinity:member.surfaceAffinity??rule.surfaceAffinity};
          const entry=objectEntry(object,room,rule.id,rect,(member.rotationDegrees+chosen.rotationDegrees)%360,item,{assemblyId,memberId:member.id,role:member.role??member.id,localOffset:copy(member.offset),localRotationDegrees:member.rotationDegrees,requiredSupportEdge:member.supportEdge?DIRECTIONS[(DIRECTIONS.findIndex(d=>d[0]===member.supportEdge)+chosen.rotationDegrees/90)%4][0]:null});objects.push(entry);memberIds.push(entry.id);
          for(const p of cellsOf(rect)){(member.layer==='underlay'?underlayOccupied:occupied).add(key(p));if(member.blocksMovement)blocked.add(key(p));}
        }
        cellsOf(chosen.envelope).forEach(p=>assemblyEnvelopes.add(key(p)));chosen.access.forEach(p=>reserved.add(key(p)));
        const gap=rule.clearance??0;for(let y=chosen.envelope.y-gap;y<chosen.envelope.y+chosen.envelope.height+gap;y++)for(let x=chosen.envelope.x-gap;x<chosen.envelope.x+chosen.envelope.width+gap;x++)if(!inside(chosen.envelope,x,y))halos.add(`${x},${y}`);
        assemblies.push({id:assemblyId,ruleId:rule.id,roomId:room.id,templateId:room.templateId,anchor:{x:chosen.envelope.x,y:chosen.envelope.y},width:chosen.envelope.width,height:chosen.envelope.height,rotationDegrees:chosen.rotationDegrees,memberIds,accessCells:chosen.access,clearance:gap});placed++;
      }
      if(placed<rule.min)diagnostics.push({roomId:room.id,assemblyRuleId:rule.id,requestedMinimum:rule.min,placed,reason:'Atomic assembly cannot fit while preserving support, member footprints, access, doors and connected floor.'});
    }
  }

  for(const room of rooms){const template=templates.get(room.templateId);room.role=room.width>=4&&room.height>=4?'furnished-room':'unfurnished-passage';if(room.role==='unfurnished-passage'){diagnostics.push({roomId:room.id,reason:'Narrow partition retained as an unfurnished passage; no room-scale furniture.'});continue;}placeAssemblies(room,template);for(const item of [...template.furnishings].sort((a,b)=>b.priority-a.priority||(a.id<b.id?-1:a.id>b.id?1:0))){const desired=item.min+Math.floor(random()*(item.max-item.min+1));let placed=0;
      for(let n=0;n<desired;n++){const candidates=[];for(const rotationDegrees of item.rotations){const swapped=rotationDegrees%180!==0,w=item.footprint[swapped?1:0],h=item.footprint[swapped?0:1];for(let y=room.y;y+h<=room.y+room.height;y++)for(let x=room.x;x+w<=room.x+room.width;x++){const rect={x,y,width:w,height:h};const sides=['north','east','south','west'].filter(side=>support(rect,side));if(item.placement==='wall'&&(!sides.length||(w>h&&!sides.some(s=>['north','south'].includes(s)))||(h>w&&!sides.some(s=>['east','west'].includes(s)))))continue;if(!safe(rect,item))continue;const distance=Math.abs(x+(w-1)/2-room.center.x)+Math.abs(y+(h-1)/2-room.center.y);candidates.push({rect,rotationDegrees,sides,score:item.placement==='center'?distance:0,tie:random()});}}
        if(!candidates.length)break;candidates.sort((a,b)=>a.score-b.score||a.tie-b.tie||a.rect.y-b.rect.y||a.rect.x-b.rect.x||a.rotationDegrees-b.rotationDegrees);const chosen=candidates[0],object=byObject.get(item.objectIds[Math.floor(random()*item.objectIds.length)]);const bounds=object.visibleBounds;const sourceVisibleBounds=[bounds[0],bounds[1],bounds[2]-bounds[0],bounds[3]-bounds[1]];
        const entry=objectEntry(object,room,item.id,chosen.rect,chosen.rotationDegrees,item);
        objects.push(entry);cellsOf(chosen.rect).forEach(p=>{(item.layer==='underlay'?underlayOccupied:occupied).add(key(p));if(item.blocksMovement)blocked.add(key(p));});if(item.clearance)for(let y=chosen.rect.y-item.clearance;y<chosen.rect.y+chosen.rect.height+item.clearance;y++)for(let x=chosen.rect.x-item.clearance;x<chosen.rect.x+chosen.rect.width+item.clearance;x++)if(!inside(chosen.rect,x,y))halos.add(`${x},${y}`);placed++;}
      if(placed<item.min)diagnostics.push({roomId:room.id,ruleId:item.id,requestedMinimum:item.min,placed,reason:'No footprint satisfies connectivity, doorway, surface, wall-edge or clearance constraints.'});}}
  for(const cell of cells)cell.blocked=blocked.has(key(cell));
  const blockedCells=[...blocked].map(s=>{const [x,y]=s.split(',').map(Number);return{x,y};}).sort((a,b)=>a.y-b.y||a.x-b.x);
  const map={schemaVersion:1,kind:'whole-object-map',generationVersion:2,geometrySeed:base.seed,geometryAttempts,minimumRoomDimension:roomScore(base),seed,theme:themeId,width,height,tileSize:48,cells,rooms,corridors:copy(base.corridors),doors,entrance:copy(base.start),start:copy(base.start),exit:copy(base.exit),playerSpawns:copy(base.playerSpawns),enemies:copy(base.enemies),clearRoute:findRoute({width,height,start:base.start,exit:base.exit,blockedCells}),reservedCells:[...reserved].map(s=>{const[x,y]=s.split(',').map(Number);return{x,y};}),doorClearanceCells:[...doorClear].map(s=>{const[x,y]=s.split(',').map(Number);return{x,y};}),blockedCells,objects,assemblies,diagnostics,canonicalMap:getPlayableMap(base,canonicalManifest)};
  const validation=validateWholeObjectMap(map,library);if(!validation.valid)throw new Error(validation.errors.join(' '));return map;
}

export function validateWholeObjectMap(map,library) {
  const errors=[];if(!map||map.kind!=='whole-object-map'||!Number.isInteger(map.width)||map.width<6||map.width>20||!Number.isInteger(map.height)||map.height<6||map.height>16||!Array.isArray(map.cells)||map.cells.length!==map.width*map.height||!Array.isArray(map.objects)||!Array.isArray(map.reservedCells)||!Array.isArray(map.doorClearanceCells))return{valid:false,errors:['Unsupported generated map.']};
  const blocked=new Set(map.cells.filter(c=>c.blocked).map(key)),open=new Map(map.cells.filter(c=>c.kind==='floor').map(c=>[key(c),c]));const occupied=new Set(),underlayOccupied=new Set();const ids=new Set(library?.objects?.map(o=>o.id)??[]);const reserved=new Set(map.reservedCells.map(key)),doorClear=new Set(map.doorClearanceCells.map(key));
  for(const object of map.objects){if(![object.x,object.y,object.width,object.height].every(Number.isInteger)||object.width<1||object.height<1||object.x<0||object.y<0||object.x+object.width>map.width||object.y+object.height>map.height||![0,90,180,270].includes(object.rotationDegrees)){errors.push('Invalid object footprint/rotation.');continue;}if(!ids.has(object.assetId))errors.push('Unknown object asset.');for(const p of cellsOf(object)){const k=key(p);const occupation=object.layer==='underlay'?underlayOccupied:occupied;if(!open.has(k)||occupation.has(k)||(object.layer!=='underlay'&&doorClear.has(k))||(object.blocksMovement&&reserved.has(k)))errors.push('Object footprint overlaps, leaves floor or blocks a reserved approach.');occupation.add(k);if(object.blocksMovement&&!blocked.has(k))errors.push('Object collision footprint disagrees.');}if(object.placement==='wall'&&!object.attachmentEdges.length)errors.push('Wall object lacks compatible boundary attachment.');}
  const objectById=new Map(map.objects.map(o=>[o.id,o]));
  for(const assembly of map.assemblies??[]){
    const members=assembly.memberIds.map(id=>objectById.get(id));
    if(members.some(o=>!o||o.assemblyId!==assembly.id||o.roomId!==assembly.roomId))errors.push('Assembly member references disagree.');
    const room=map.rooms.find(r=>r.id===assembly.roomId);if(!room||!inside(room,assembly.anchor.x,assembly.anchor.y)||!inside(room,assembly.anchor.x+assembly.width-1,assembly.anchor.y+assembly.height-1))errors.push('Assembly envelope leaves its room.');
    for(const p of assembly.accessCells)if(!open.has(key(p))||blocked.has(key(p))||occupied.has(key(p)))errors.push('Assembly access blocked or missing floor.');
  }
  const assemblyById=new Map((map.assemblies??[]).map(a=>[a.id,a]));
  for(const object of map.objects){if(object.assemblyId&&!assemblyById.get(object.assemblyId)?.memberIds.includes(object.id))errors.push('Orphaned assembly member.');if(object.requiredSupportEdge&&!object.attachmentEdges.includes(object.requiredSupportEdge))errors.push('Member head/back support edge missing.');}
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
