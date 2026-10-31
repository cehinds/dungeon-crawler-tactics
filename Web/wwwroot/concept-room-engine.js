/* Pure deterministic room compiler. No DOM, filesystem, clock, or rendering dependency. */
(function(root,factory){const api=factory();if(typeof module==='object'&&module.exports)module.exports=api;else root.ConceptRoomEngine=api;})(typeof globalThis!=='undefined'?globalThis:this,function(){
'use strict';
function random(seed){let a=Number(seed)>>>0;return()=>{a+=0x6D2B79F5;let t=a;t=Math.imul(t^t>>>15,t|1);t^=t+Math.imul(t^t>>>7,t|61);return((t^t>>>14)>>>0)/4294967296;};}
function assets(c){const all=Array.isArray(c.assets)?Object.fromEntries(c.assets.map(a=>[a.id,a])):c.assets;return Object.fromEntries(Object.entries(all).map(([id,a])=>[id,Object.assign({},a,{size:a.size||[a.width,a.height]})]));}
function reachable(grid,start){let q=[start],seen=new Set([start.join(',')]);for(let i=0;i<q.length;i++){let [x,y]=q[i];for(let [dx,dy] of [[0,1],[0,-1],[1,0],[-1,0]]){let nx=x+dx,ny=y+dy,k=[nx,ny].join(',');if(grid[ny]&&grid[ny][nx]&& !['water','wall'].includes(grid[ny][nx])&&!seen.has(k)){seen.add(k);q.push([nx,ny]);}}}return seen;}
function checkRecipe(r){
 function requireField(path,test){let value=path.split('.').reduce((o,k)=>o&&o[k],r);if(!test(value))throw Error('Recipe '+path+' missing/invalid');}
 const object=v=>v!==null&&typeof v==='object'&&!Array.isArray(v),number=v=>Number.isFinite(v),positive=v=>number(v)&&v>0,integer=v=>Number.isInteger(v),string=v=>typeof v==='string'&&v.length>0;
 if(!object(r))throw Error('Recipe root missing/invalid');
 for(let path of ['canvas','board','uiBounds','roles','constraints','architecture','state','edgeRules','edgeRules.roleSockets'])requireField(path,object);
 requireField('schemaVersion',v=>v===2);
 for(let path of ['canvas.width','canvas.height','board.columns','board.rows','board.tileSize','actorScale','constraints.entitySpacing','constraints.exactActors','constraints.minimumProps','architecture.portalMargin','architecture.landmarkInset','architecture.portalClearanceRows'])requireField(path,v=>positive(v)&&(path==='actorScale'||integer(v)));
 requireField('canvas.background',string);requireField('board.origin',v=>Array.isArray(v)&&v.length===2&&v.every(number));
 for(let path of ['uiBounds.x','uiBounds.y','uiBounds.width','uiBounds.height','architecture.portalClearanceColumns'])requireField(path,integer);
 requireField('architecture.channelSides',v=>Array.isArray(v)&&v.length>0&&v.every(x=>['west','east'].includes(x)));
 requireField('architecture.landmarkRows',v=>Array.isArray(v)&&v.every(integer));requireField('architecture.landmarkProbability',v=>number(v)&&v>=0&&v<=1);
 requireField('edgeRules.allowedPairs',v=>Array.isArray(v)&&v.every(p=>Array.isArray(p)&&p.length===2&&p.every(string)));
 for(let role of ['floor','waterVariants','bankEastVariants','bankWestVariants','waterEndVariants','waterOutletVariants','wallFace','wallCap','wallCapEndWest','wallCapEndEast','wallCornerNW','wallCornerNE','wallCornerSE','wallCornerSW','pier'])requireField('edgeRules.roleSockets.'+role,v=>object(v)&&['north','east','south','west'].every(k=>string(v[k])));
 requireField('entities',v=>Array.isArray(v)&&v.length>0&&v.every(e=>object(e)&&string(e.id)&&string(e.assetId)&&['actor','prop'].includes(e.kind)&&(e.kind!=='actor'||number(e.hp)&&positive(e.maxHp))));
 for(let path of ['state.selectedId','state.targetId'])requireField(path,string);
 for(let path of ['state.hp','state.maxHp','state.mana','state.maxMana','state.move','state.round'])requireField(path,number);
}
function fixedHudErrors(r,c){
 const roles=Object.assign({},c.roles,r.roles);if(!roles.hud)return[];
 const fixed=c.fixedHudState,errors=[];if(!fixed)return['Fixed HUD metadata missing; cannot verify raster state'];
 const expected={hp:Array.isArray(fixed.hp)?fixed.hp[0]:undefined,maxHp:Array.isArray(fixed.hp)?fixed.hp[1]:undefined,mana:Array.isArray(fixed.mana)?fixed.mana[0]:undefined,maxMana:Array.isArray(fixed.mana)?fixed.mana[1]:undefined,move:fixed.move,round:fixed.round,forecastDamage:fixed.forecastDamage,selectedId:fixed.selectedId,targetId:fixed.targetId};
 for(let [key,value]of Object.entries(expected))if(value===undefined||r.state[key]!==value)errors.push('Fixed HUD '+key+' mismatch: raster requires '+JSON.stringify(value)+', recipe declares '+JSON.stringify(r.state[key]));
 const selected=r.entities.find(e=>e.id===r.state.selectedId);if(!selected||selected.hp!==expected.hp||selected.maxHp!==expected.maxHp||selected.assetId!==fixed.selectedAssetId)errors.push('Fixed HUD selected entity HP mismatch');
 if(!r.entities.some(e=>e.id===expected.targetId&&e.assetId===fixed.targetAssetId&&e.kind==='actor'&&e.faction==='enemy'))errors.push('Fixed HUD target identity mismatch');return errors;
}
function generate(r,c,seed){
 checkRecipe(r);
 const hudErrors=fixedHudErrors(r,c);if(hudErrors.length)throw Error(hudErrors.join('; '));
 if(!Number.isSafeInteger(Number(seed)))throw Error('Seed must be a safe integer');
 const rng=random(seed),a=assets(c),roles=Object.assign({},c.roles,r.roles),b=r.board,t=b.tileSize,w=b.columns,h=b.rows,[ox,oy]=b.origin,plan=[],placements=[];
 function role(name){let v=roles[name];if(Array.isArray(v))v=v[Math.floor(rng()*v.length)];if(!a[v])throw Error('Missing catalog role '+name+': '+v);return v;}
 function stamp(id,x,y,layer,extra={}){let v=a[id];if(!v)throw Error('Unknown asset '+id);let size=v.size||[v.width,v.height];plan.push(Object.assign({assetId:id,x,y,width:size[0],height:size[1],layer,footY:y+size[1]},extra));}
 function tile(name,x,y,layer=10){let id;if(name==='floor'){let candidates=[].concat(roles.floor||[]).filter(id=>{let tags=a[id]&&a[id].edgeTags;if(!tags)return false;return [[x-1,y,'west','east'],[x,y-1,'north','south']].every(([nx,ny,edge,other])=>{let n=plan.find(d=>d.layer===10&&d.cell&&d.cell[0]===nx&&d.cell[1]===ny&&d.tileRole==='floor');return !n||a[n.assetId].edgeTags[other]===tags[edge];});});if(!candidates.length)throw Error('No compatible directional floor tile');id=candidates[Math.floor(rng()*candidates.length)];}else id=role(name);stamp(id,ox+x*t,oy+y*t,layer,{width:t,height:t,cell:[x,y],tileRole:name});}
 const arch=r.architecture,margin=arch.portalMargin,side=arch.channelSides[Math.floor(rng()*arch.channelSides.length)],waterX=side==='west'?0:w-1,bankX=side==='west'?1:w-2,exitX=margin+Math.floor(rng()*(w-2*margin)),entranceX=margin+Math.floor(rng()*(w-2*margin));
 const grid=Array.from({length:h},()=>Array(w).fill('floor'));
 for(let y=0;y<h;y++)grid[y][waterX]='water';
 grid[0][exitX]='exit';grid[h-1][entranceX]='entrance';
 // Dry central spine is a permanent clear route; masonry landmarks occupy only side bays.
 const landmarks=[];for(let y of arch.landmarkRows){let x=side==='west'?w-1-arch.landmarkInset:arch.landmarkInset;if(rng()<arch.landmarkProbability){grid[y][x]='wall';landmarks.push([x,y]);}}
 for(let y=0;y<h;y++)for(let x=0;x<w;x++){if(grid[y][x]==='water')tile('waterVariants',x,y);else tile('floor',x,y);if(x===waterX)tile(side==='west'?'bankEastVariants':'bankWestVariants',x,y,11);}
 tile('waterEndVariants',waterX,0,12);tile('waterOutletVariants',waterX,h-1,12);
 for(let y=-1;y<=h;y++)for(let x=-1;x<=w;x++){if(x>=0&&x<w&&y>=0&&y<h)continue;if((y===-1&&x===exitX)||(y===h&&x===entranceX))continue;let name;if((x===-1||x===w)&&(y===-1||y===h))name='wallCorner'+(y===-1?'N':'S')+(x===-1?'W':'E');else if(y===-1||y===h)name=x===exitX-1&&y===-1||x===entranceX-1&&y===h?'wallCapEndEast':x===exitX+1&&y===-1||x===entranceX+1&&y===h?'wallCapEndWest':'wallCap';else name='wallFace';tile('wallFace',x,y,20);if(name!=='wallFace'){let id=role(name),sz=a[id].size;stamp(id,ox+x*t,oy+y*t,22,{width:sz[0],height:sz[1],cell:[x,y],tileRole:name});}}
 for(let [x,y]of landmarks)tile('pier',x,y,21);
 const portals={entrance:{cell:[entranceX,h-1],landing:[entranceX,h-2],tags:['entrance','walkable']},exit:{cell:[exitX,0],landing:[exitX,1],tags:['exit','walkable']}};
 for(let name of ['entrance','exit']){let id=role(name),v=a[id],anchor=v.anchor||[v.size[0]/2,v.size[1]],cell=portals[name].cell;stamp(id,ox+(cell[0]+.5)*t-anchor[0],oy+(cell[1]+1)*t-anchor[1],24,{portal:name,threshold:[ox+(cell[0]+.5)*t,oy+(cell[1]+1)*t]});}
 const reserved=new Set(Object.values(portals).flatMap(p=>[p.cell.join(','),p.landing.join(',')]));for(let name of ['entrance','exit']){let cell=portals[name].cell;for(let dx=-arch.portalClearanceColumns;dx<=arch.portalClearanceColumns;dx++)for(let dy=1;dy<=arch.portalClearanceRows;dy++)reserved.add([cell[0]+dx,name==='entrance'?h-1-dy:dy].join(','));}let cells=[];for(let y=1;y<h-1;y++)for(let x=2;x<w-2;x++)if(grid[y][x]==='floor'&&!reserved.has([x,y].join(',')))cells.push([x,y]);
 for(let i=cells.length-1;i>0;i--){let j=Math.floor(rng()*(i+1));[cells[i],cells[j]]=[cells[j],cells[i]];}
 const entities=r.entities;if(cells.length<entities.length)throw Error('Insufficient cells for exact entity cardinality');
 // Finite deterministic backtracking preserves declared minimum spacing without silently dropping entities.
 let chosen=[];function choose(index,start){if(index===entities.length)return true;for(let i=start;i<cells.length;i++){let p=cells[i];if(chosen.every(q=>Math.abs(q[0]-p[0])+Math.abs(q[1]-p[1])>=r.constraints.entitySpacing)){chosen.push(p);if(choose(index+1,i+1))return true;chosen.pop();}}return false;}
 if(!choose(0,0))throw Error('No placement satisfies exact cardinality and spacing');
 entities.forEach((e,i)=>{let cell=chosen[i],v=a[e.assetId];if(!v)throw Error('Unknown entity '+e.assetId);let scale=r.actorScale,sz=v.size,an=v.anchor||[sz[0]/2,sz[1]],footY=oy+(cell[1]+1)*t-4,x=ox+(cell[0]+.5)*t-an[0]*scale,y=footY-an[1]*scale;let p={id:e.id,assetId:e.assetId,kind:e.kind,cell,footY,hp:e.hp,maxHp:e.maxHp};placements.push(p);stamp(e.assetId,x,y,30,{width:sz[0]*scale,height:sz[1]*scale,footY,entityId:e.id});if(e.id===r.state.selectedId||e.id===r.state.targetId)plan.push({primitive:'rect',x:ox+cell[0]*t+2,y:oy+cell[1]*t+2,width:t-4,height:t-4,stroke:e.id===r.state.selectedId?'#ffe468':'#ff4058',lineWidth:3,layer:25,footY});if(e.kind==='actor'){let by=y-10;plan.push({primitive:'rect',x:x,y:by,width:48,height:6,fill:'#071018',layer:40,footY});plan.push({primitive:'rect',x:x+1,y:by+1,width:46*e.hp/e.maxHp,height:4,fill:e.faction==='enemy'?'#ef4961':'#38d89a',layer:41,footY});}});
 if(roles.hud){let id=role('hud');stamp(id,0,0,100);}
 for(let d of plan)if(d.layer<100&&d.y+d.height>r.uiBounds.y){let clipped=Math.max(1,r.uiBounds.y-d.y);if(d.assetId)d.sourceRect=[0,0,a[d.assetId].size[0],a[d.assetId].size[1]*clipped/d.height];d.height=clipped;}
 plan.sort((a,b)=>a.layer-b.layer||(a.layer===30?a.footY-b.footY:0)||String(a.assetId||'').localeCompare(String(b.assetId||'')));
 let room={schemaVersion:2,seed:Number(seed),canvas:r.canvas,tileSize:t,boardOffset:b.origin,grid,portals,entrance:portals.entrance,exit:portals.exit,channel:{side,width:1,contiguous:true,walkable:false},regions:[{id:'central-route',kind:'clear-path'},{id:'water-channel',kind:'contained-water',side}],landmarks,placements,state:JSON.parse(JSON.stringify(r.state)),drawPlan:plan,note:'Illustrative composition using derived source art; fixed raster HUD matches declared state.'};room.validation=validate(r,c,room);room.connectivity={allWalkableConnected:room.validation.allWalkableConnected,entranceToExit:room.validation.entranceToExit};if(!room.validation.valid)throw Error(room.validation.errors.join('; '));return room;
}
function validate(r,c,room){let errors=fixedHudErrors(r,c),a=assets(c),seen=reachable(room.grid,room.portals.entrance.cell),dry=room.grid.flat().filter(x=>!['wall','water'].includes(x)).length,allWalkableConnected=seen.size===dry,entranceToExit=seen.has(room.portals.exit.cell.join(','));if(!allWalkableConnected||!entranceToExit)errors.push('Disconnected walkable cells');if(room.placements.length!==r.entities.length)errors.push('Entity count mismatch');if(room.placements.filter(p=>p.kind==='actor').length!==r.constraints.exactActors||room.placements.filter(p=>p.kind==='prop').length<r.constraints.minimumProps)errors.push('Required actor/prop counts');for(let i=0;i<room.placements.length;i++)for(let j=i+1;j<room.placements.length;j++){let p=room.placements[i].cell,q=room.placements[j].cell;if(Math.abs(p[0]-q[0])+Math.abs(p[1]-q[1])<r.constraints.entitySpacing)errors.push('Entity spacing');}if(JSON.stringify(room.state)!==JSON.stringify(r.state))errors.push('State differs from recipe');let occupied=new Set();for(let p of room.placements){let key=p.cell.join(',');if(occupied.has(key))errors.push('Overlapping entities');occupied.add(key);if(!seen.has(key))errors.push('Unreachable entity '+p.id);}
 if(r.board.origin[1]+r.board.rows*r.board.tileSize>r.uiBounds.y)errors.push('Board overlaps UI');
 for(let d of room.drawPlan){if(d.layer<100&&d.y+d.height>r.uiBounds.y)errors.push('World draw overlaps UI');if(d.assetId&&!a[d.assetId])errors.push('Unknown draw asset '+d.assetId);if(![d.x,d.y,d.width,d.height].every(Number.isFinite))errors.push('Invalid draw bounds');}
 // Effective terrain uses the bank overlay on the nonwalkable water cell.
 const roles=Object.assign({},c.roles,r.roles),rules=r.edgeRules;
 const terrain=new Map();for(let d of room.drawPlan.filter(d=>d.cell&&[10,11,20].includes(d.layer))){if(!a[d.assetId])continue;terrain.set(d.cell.join(','),d);}
 for(let d of room.drawPlan.filter(d=>d.tileRole)){
  if(![].concat(roles[d.tileRole]||[]).includes(d.assetId))errors.push('Asset does not match declared tile role '+d.tileRole);
  const expected=rules.roleSockets[d.tileRole];if(expected){for(let edge of ['north','east','south','west'])if(a[d.assetId]?.edgeTags?.[edge]!==expected[edge])errors.push('Incorrect directional socket '+d.tileRole+':'+edge);}
  if(d.layer===10&&d.tileRole!==(room.grid[d.cell[1]]?.[d.cell[0]]==='water'?'waterVariants':'floor'))errors.push('Incorrect terrain role');
  if(d.layer===12&&d.tileRole!==(d.cell[1]===0?'waterEndVariants':'waterOutletVariants'))errors.push('Incorrect channel end/outlet role');
  if(d.layer===20&&d.tileRole!=='wallFace')errors.push('Boundary requires wall face underlay');
  if(d.layer===22){let [x,y]=d.cell,w=r.board.columns,h=r.board.rows,exitX=room.portals.exit.cell[0],entranceX=room.portals.entrance.cell[0],expected;if((x===-1||x===w)&&(y===-1||y===h))expected='wallCorner'+(y===-1?'N':'S')+(x===-1?'W':'E');else if(y===-1||y===h)expected=x===exitX-1&&y===-1||x===entranceX-1&&y===h?'wallCapEndEast':x===exitX+1&&y===-1||x===entranceX+1&&y===h?'wallCapEndWest':'wallCap';else expected='wallFace';if(d.tileRole!==expected)errors.push('Incorrect wall boundary orientation');}
  if(d.layer===22&&!room.drawPlan.some(p=>p.layer===20&&p.cell&&p.cell[0]===d.cell[0]&&p.cell[1]===d.cell[1]))errors.push('Missing boundary face underlay');
  if(d.layer===22&&d.assetId){let sz=a[d.assetId].size;if(d.width!==sz[0]||(!d.sourceRect&&d.height!==sz[1])||(d.sourceRect&&d.height!==d.sourceRect[3]))errors.push('Distorted native boundary module');}
  if(d.layer===11){let expectedRole=room.channel.side==='west'?'bankEastVariants':'bankWestVariants';if(d.tileRole!==expectedRole||room.grid[d.cell[1]]?.[d.cell[0]]!=='water')errors.push('Incorrect bank orientation or footprint');}
 }
 for(let d of terrain.values())for(let [dx,dy,edge,opposite]of [[1,0,'east','west'],[0,1,'south','north']]){let n=terrain.get([d.cell[0]+dx,d.cell[1]+dy].join(','));if(n){let e=a[d.assetId]?.edgeTags?.[edge],f=a[n.assetId]?.edgeTags?.[opposite];if(!e||!f||!(e===f||rules.allowedPairs.some(p=>p[0]===e&&p[1]===f||p[1]===e&&p[0]===f)))errors.push('Incompatible directional transition '+d.tileRole+' '+edge+' '+n.tileRole);}}

 for(let e of r.entities){let p=room.placements.find(p=>p.id===e.id);if(!p||p.assetId!==e.assetId||p.hp!==e.hp||p.maxHp!==e.maxHp)errors.push('Entity contract mismatch '+e.id);}let selected=room.placements.find(p=>p.id===room.state.selectedId);if(selected&&(selected.hp!==room.state.hp||selected.maxHp!==room.state.maxHp))errors.push('HUD HP mismatch');
 for(let key of ['selectedId','targetId'])if(!room.placements.some(p=>p.id===room.state[key]))errors.push('Unknown state '+key);
 return{valid:errors.length===0,errors,allWalkableConnected,entranceToExit,reachableCells:seen.size,exactEntityCount:room.placements.length};}
return{generate,validate};});
