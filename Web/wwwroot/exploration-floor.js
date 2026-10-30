// Floor topology and encounter placement are independent of rendering and combat.
const key = p => `${p.x},${p.y}`;
export function floorSeed(value) {
  let n = 2166136261;
  for (const c of String(value)) n = Math.imul(n ^ c.charCodeAt(0), 16777619);
  return n & 0x7fffffff;
}
// Authored contract: Schemas/exploration-floor-rules.schema.json.
// Fail authored configuration mistakes before carving or allocating the floor.
export function validateExplorationFloorRules(rules) {
  const check = (condition, message) => { if (!condition) throw new Error(`Invalid exploration floor rules: ${message}`); };
  const integer = (n, min, max) => Number.isInteger(n) && n >= min && n <= max;
  const label = value => typeof value === 'string' && value.trim().length > 0 && value.length <= 120;
  const uniqueIds = (values, name) => {
    const ids = new Set();
    for (const value of values) { check(value && label(value.id) && !ids.has(value.id), `${name} require unique nonempty IDs.`); ids.add(value.id); }
  };
  check(rules && rules.schemaVersion === 1, 'schemaVersion must be 1.');
  check(integer(rules.width, 8, 40) && integer(rules.height, 8, 32), 'dimensions must be integers within 8–40 by 8–32.');
  check(integer(rules.safeRadius, 1, 70) && integer(rules.minimumGroupDistance, 1, 70), 'safeRadius and minimumGroupDistance must be positive integers up to 70.');
  check(Array.isArray(rules.zones) && rules.zones.length >= 3 && rules.zones.length <= 32, 'zones must contain 3–32 regions.');
  uniqueIds(rules.zones, 'Zones');
  for (const z of rules.zones) {
    check(label(z.label), `zone ${z.id} requires a label.`);
    check(integer(z.x, 1, rules.width-2) && integer(z.y, 1, rules.height-2)
      && integer(z.width, 5, rules.width-2) && integer(z.height, 5, rules.height-2)
      && z.x+z.width <= rules.width-1 && z.y+z.height <= rules.height-1, `zone ${z.id} must fit inside the boundary with width and height at least 5.`);
  }
  const arrival=rules.zones[0];
  check(arrival.x<=4 && arrival.y<=4 && arrival.x+arrival.width-2>=5 && arrival.y+arrival.height-2>=5, 'arrival zone must contain the starting clearing at (4,4) through (5,5), including seeded size variation.');
  const zoneRef = n => integer(n, 0, rules.zones.length-1);
  check(Array.isArray(rules.connections) && rules.connections.length > 0, 'connections are required.');
  const reached=new Set([0]);
  for(const pair of rules.connections) check(Array.isArray(pair) && pair.length===2 && pair.every(zoneRef) && pair[0]!==pair[1], 'connections must reference two distinct existing zones.');
  for(let pass=0;pass<rules.zones.length;pass++) for(const [a,b] of rules.connections) if(reached.has(a)||reached.has(b)){reached.add(a);reached.add(b);}
  check(reached.size===rules.zones.length, 'all zones must be connected to arrival.');
  check(Array.isArray(rules.groups) && rules.groups.length>0 && rules.groups.length<=24, 'groups must contain 1–24 encounters.');
  uniqueIds(rules.groups, 'Groups');
  const occupied=new Set();
  for(const g of rules.groups) {
    check(g.rewardXp === undefined || integer(g.rewardXp,0,500), 'group rewardXp must be an integer from 0 to 500.');
    check(label(g.label) && ['visible','ambush'].includes(g.kind), `group ${g.id} requires a label and visible or ambush kind.`);
    check(zoneRef(g.zone) && g.zone!==0 && !occupied.has(g.zone), `group ${g.id} needs a unique existing encounter zone outside arrival.`); occupied.add(g.zone);
  }
  check(Array.isArray(rules.enemyRecipe) && rules.enemyRecipe.length>0 && rules.enemyRecipe.length*rules.groups.length<=48, 'enemyRecipe must produce 1–48 enemies.');
  for(const e of rules.enemyRecipe) check(e && typeof e.classId==='string' && /^class\.[a-z0-9_]+$/.test(e.classId) && ['rat','guard','boss'].includes(e.artId)
    && integer(e.hp,1,9999) && integer(e.energy,0,999) && integer(e.move,1,20) && Array.isArray(e.tags) && e.tags.every(label), 'enemyRecipe has invalid class, art, stats or tags.');
  for(const g of rules.groups) check(rules.enemyRecipe.length<=Math.floor((rules.zones[g.zone].width-1)/2), `enemyRecipe does not fit encounter zone ${g.zone}.`);
  check(Array.isArray(rules.discoveries) && rules.discoveries.length<=32, 'discoveries must be an array of at most 32 entries.');
  uniqueIds(rules.discoveries, 'Discoveries');
  for(const d of rules.discoveries) {
    check(zoneRef(d.zone) && label(d.label) && label(d.description) && ['cache','objective'].includes(d.kind), `discovery ${d.id} has invalid zone, description or kind.`);
    check(d.kind==='cache' ? typeof d.itemId==='string' && /^item\.[a-z0-9_]+$/.test(d.itemId) && integer(d.count,1,99) : d.itemId===null && d.count===0, `discovery ${d.id} requires a valid cache item/count or objective null item and zero count.`);
  }
  if(rules.mechanisms !== undefined) {
    check(Array.isArray(rules.mechanisms) && rules.mechanisms.length<=8, 'mechanisms must contain at most 8 recipes.');
    uniqueIds(rules.mechanisms,'Mechanisms');
    const fields=(v,allowed)=>v && Object.keys(v).every(k=>allowed.includes(k));
    const stableId=v=>typeof v==='string'&&/^[a-z0-9._-]{1,100}$/.test(v);
    const description=v=>typeof v==='string'&&v.trim().length>0&&v.length<=500;
    const tags=v=>Array.isArray(v)&&v.length<=8&&v.every(label)&&new Set(v).size===v.length;
    for(const m of rules.mechanisms) {
      check(stableId(m.id)&&fields(m,['id','label','description','materialTags','solutions'])&&label(m.label)&&description(m.description)&&tags(m.materialTags), `mechanism ${m.id} has invalid fields or materials.`);
      check(Array.isArray(m.solutions)&&m.solutions.length===3,'mechanisms require three solutions.');
      uniqueIds(m.solutions,'Mechanism solutions');
      check(new Set(m.solutions.map(s=>s.kind)).size===3,'mechanisms require manual, ability and item solutions.');
      for(const s of m.solutions) {
        check(stableId(s.id)&&fields(s,['id','label','description','kind','abilityTag','itemId','itemCount','requiredMaterialTags'])&&label(s.label)&&description(s.description)&&tags(s.requiredMaterialTags)&&s.requiredMaterialTags.every(t=>m.materialTags.includes(t)), 'invalid mechanism solution fields or materials.');
        check(['manual','ability','item'].includes(s.kind), 'invalid mechanism solution kind.');
        check(s.kind!=='manual' ? label(s.abilityTag) : s.abilityTag===undefined, 'abilityTag is required for ability and item solutions.');
        check(s.kind==='item' ? typeof s.itemId==='string'&&/^item\.[a-z0-9_]+$/.test(s.itemId)&&integer(s.itemCount,1,99) : s.itemId===undefined&&s.itemCount===undefined, 'item solutions require itemId and itemCount only.');
      }
    }
  }
  check(typeof rules.propLabelPattern==='string' && rules.propLabelPattern.length<=500, 'propLabelPattern must be a string up to 500 characters.');
  try { new RegExp(rules.propLabelPattern,'i'); } catch { check(false,'propLabelPattern must be a valid regular expression.'); }
  return rules;
}
export function generateExplorationFloor(manifest, rules, seed = 'floor') {
  validateExplorationFloorRules(rules);
  const numericSeed = floorSeed(seed);
  let state = numericSeed || 1;
  const random = () => { state = Math.imul(state, 1664525) + 1013904223 | 0; return (state >>> 0) / 4294967296; };
  const { width, height } = rules;
  const open = new Set(), protectedCells = new Set();
  const carve = (x,y,protect=false) => {
    if (x < 1 || y < 1 || x >= width-1 || y >= height-1) return;
    open.add(`${x},${y}`); if (protect) protectedCells.add(`${x},${y}`);
  };
  const zones = rules.zones.map(z => ({...z, width:z.width-Math.floor(random()*2), height:z.height-Math.floor(random()*2), theme:{id:z.id}}));
  const center = z => ({x:z.x+Math.floor(z.width/2), y:z.y+Math.floor(z.height/2)});
  for (const z of zones) for(let y=z.y;y<z.y+z.height;y++) for(let x=z.x;x<z.x+z.width;x++) carve(x,y);
  const corridors = [];
  for (const [a,b] of rules.connections) {
    let p = center(zones[a]); const end = center(zones[b]); const cells=[];
    const stamp = () => { for(let dy=0;dy<2;dy++) for(let dx=0;dx<2;dx++) {carve(p.x+dx,p.y+dy,true);cells.push({x:p.x+dx,y:p.y+dy});} };
    stamp();
    const horizontalFirst = random() < .5;
    for(const axis of horizontalFirst ? ['x','y'] : ['y','x']) while(p[axis]!==end[axis]) {p={...p,[axis]:p[axis]+Math.sign(end[axis]-p[axis])};stamp();}
    corridors.push({from:zones[a].id,to:zones[b].id,cells});
  }
  const entrance = {x:4,y:4}, exit={x:zones[2].x+zones[2].width-2,y:zones[2].y+zones[2].height-2};
  const groups=rules.groups.map(g=>{const {zone,...data}=g; return {...data,...center(zones[zone]),enemyIds:[]};});
  const discoveries=rules.discoveries.map(d=>{const {zone,...data}=d; const z=zones[zone];return {...data,x:z.x+1,y:z.y+1};});
  const players=[entrance,{x:5,y:4},{x:4,y:5},{x:5,y:5}];
  for(const p of [...players,exit,...groups,...discoveries]) protectedCells.add(key(p));
  const floor=manifest.assets.find(a=>a.id==='stone-a'), wall=manifest.assets.find(a=>a.id==='wall-ne');
  if(!floor || !wall) throw new Error('Canonical floor and wall assets required.');
  const placements=[], blockedCells=[];
  const add=(asset,x,y,kind)=>placements.push({id:`floor.placement.${placements.length}`,assetId:asset.id,layer:asset.layer,x,y,rotation:0,blocksMovement:asset.blocksMovement,kind});
  for(let y=0;y<height;y++) for(let x=0;x<width;x++) {
    if(open.has(`${x},${y}`)) add(floor,x,y,'floor');
    else {add(wall,x,y,'wall');blockedCells.push({x,y});}
  }
  const enemies=groups.flatMap((g,i)=>rules.enemyRecipe.map((recipe,j)=>{
    const id=`custom.enemy.floor${i}.${j}`;g.enemyIds.push(id);
    return {...structuredClone(recipe),id,label:`${g.label} ${j+1}`,x:g.x+j,y:g.y};
  }));
  // Opening a mechanism only adds walkable cells; the original connected map stays intact.
  const mechanisms=placeMechanisms(rules.mechanisms||[],open,width,height,[...players,exit,...groups,...discoveries,...enemies],protectedCells,numericSeed);
  const room={schemaVersion:1,kind:'dungeon-room-authoring',seed:String(seed),width,height,density:0,biome:'stone',layout:'continuous-floor',tile:{...manifest.tile},start:entrance,entrance,exit,rooms:zones,corridors,placements,blockedCells,clearRoute:[],playerSpawns:players,enemies,doors:[],generation:{version:1,algorithm:'continuous-zoned-floor',protectedCells:[...protectedCells].map(k=>{const[x,y]=k.split(',').map(Number);return{x,y};})}};
  const map={schemaVersion:1,label:`Abandoned works / ${seed}`.slice(0,100),width,height,tiles:blockedCells.map(p=>({...p,blocked:true,tags:[]})),placements:placements.map(({kind,...p})=>p),playerSpawns:players,enemies};
  const floorPlan={schemaVersion:1,seed:numericSeed,map,entrance,exit,groups,discoveries,...(rules.mechanisms===undefined?{}:{mechanisms})};
  validateExplorationFloor(floorPlan,rules);
  return {room,floorPlan};
}
export function validateExplorationFloor(plan,rules) {
  const {map,entrance,exit,groups,discoveries}=plan;
  const blocked=new Set(map.tiles.filter(t=>t.blocked).map(key));
  const seen=new Set([key(entrance)]),queue=[entrance],distance=new Map([[key(entrance),0]]);
  for(let i=0;i<queue.length;i++) for(const [dx,dy] of [[1,0],[-1,0],[0,1],[0,-1]]) {
    const p={x:queue[i].x+dx,y:queue[i].y+dy}, k=key(p);
    if(p.x<0||p.y<0||p.x>=map.width||p.y>=map.height||blocked.has(k)||seen.has(k))continue;
    seen.add(k);distance.set(k,distance.get(key(queue[i]))+1);queue.push(p);
  }
  for(const p of [exit,...groups,...discoveries,...map.enemies,...map.playerSpawns]) if(!seen.has(key(p))) throw new Error(`Unreachable floor feature ${p.id||key(p)}.`);
  for(const g of groups) {
    if(distance.get(key(g))<rules.safeRadius) throw new Error('Encounter inside safe arrival area.');
    for(const other of groups) if(other.id!==g.id&&Math.abs(g.x-other.x)+Math.abs(g.y-other.y)<rules.minimumGroupDistance)throw new Error('Encounter groups too close.');
  }
  const reserved=new Set([entrance,exit,...discoveries,...groups,...map.enemies,...map.playerSpawns].map(key)), opened=new Set();
  const open=new Set(queue.map(key));
  if((plan.mechanisms||[]).length!==(rules.mechanisms||[]).length)throw new Error('Missing authored floor mechanism.');
  for(const mechanism of plan.mechanisms||[]) {
    if(!Array.isArray(mechanism.openCells)||!mechanism.openCells.length||mechanism.openCells.length>8)throw new Error('Invalid mechanism opening.');
    for(const p of mechanism.openCells) {
      const k=key(p);
      if(p.x<1||p.y<1||p.x>=map.width-1||p.y>=map.height-1||!blocked.has(k)||reserved.has(k)||opened.has(k))throw new Error('Conflicting mechanism opening.');
      opened.add(k);
    }
    const local=mechanism.solutions.find(s=>s.kind==='ability'),manual=mechanism.solutions.find(s=>s.kind==='manual');
    for(const action of mechanism.solutions)if(!seen.has(key(action))||reserved.has(key(action)))throw new Error('Unreachable or occupied mechanism action.');
    const distances=floorDistances(local,open);
    if(distances.get(key(manual))<6)throw new Error('Mechanism manual route too short.');
    const ends=[];
    for(const p of mechanism.openCells)for(const [dx,dy] of [[1,0],[-1,0],[0,1],[0,-1]]){
      const n={x:p.x+dx,y:p.y+dy};if(open.has(key(n)))ends.push(n);
    }
    const expanded=new Set([...open,...mechanism.openCells.map(key)]);
    if(!ends.some(a=>{const before=floorDistances(a,open),after=floorDistances(a,expanded);return ends.some(b=>before.get(key(b))>=6&&after.get(key(b))<before.get(key(b)));}))throw new Error('Mechanism does not shorten a baseline route.');
    for(const action of mechanism.solutions)reserved.add(key(action));
  }
  if(seen.size!==map.width*map.height-blocked.size)throw new Error('Disconnected walkable floor.');
  return {walkableCells:seen.size,exitDistance:distance.get(key(exit))};
}

// Campaign recipes compose the independently usable continuous-floor rules.
export function campaignDepthRules(baseRules, campaignRules, depth) {
  const family = campaignRules.families.find(f => f.id === depth.familyId);
  if (!family) throw new Error(`Invalid generated campaign rules: unknown family ${depth.familyId}.`);
  return {...structuredClone(baseRules), zones:structuredClone(family.zones), connections:structuredClone(family.connections),
    groups:structuredClone(depth.groups), enemyRecipe:structuredClone(depth.enemyRecipe), discoveries:structuredClone(depth.discoveries), propLabelPattern:depth.propLabelPattern, ...(depth.mechanisms===undefined?{}:{mechanisms:structuredClone(depth.mechanisms)})};
}
export function validateGeneratedCampaignRules(config, baseRules, catalog) {
  const check = (value, message) => { if (!value) throw new Error(`Invalid generated campaign rules: ${message}`); };
  const text = value => typeof value === 'string' && value.trim().length > 0 && value.length <= 120;
  const keys = (value, allowed) => value && Object.keys(value).every(k=>allowed.includes(k));
  check(keys(config,['schemaVersion','id','label','families','depths']) && config.schemaVersion===1 && text(config.id) && text(config.label), 'version, identity or fields.');
  check(Array.isArray(config.families) && config.families.length>=1 && config.families.length<=8, '1–8 families required.');
  check(Array.isArray(config.depths) && config.depths.length>=2 && config.depths.length<=8, '2–8 depths required.');
  for (const [values, fields] of [[config.families,['id','zones','connections']],[config.depths,['id','label','familyId','kitId','groups','enemyRecipe','discoveries','propLabelPattern','mechanisms']]]) {
    const ids = new Set();
    for (const value of values) { check(keys(value,fields) && text(value.id) && !ids.has(value.id), 'unique identities and supported fields required.'); ids.add(value.id); }
  }
  for(const family of config.families) {
    // Validate even unused graph definitions with the shared relationship validator.
    validateExplorationFloorRules({...structuredClone(baseRules),zones:family.zones,connections:family.connections});
  }
  for(const depth of config.depths) {
    check(text(depth.label) && text(depth.familyId) && text(depth.kitId), 'depth label, graph and kit required.');
    const rules=campaignDepthRules(baseRules,config,depth);
    validateExplorationFloorRules(rules);
    check(rules.groups.some(g=>g.kind==='visible') && rules.groups.some(g=>g.kind==='ambush'), 'each depth requires visible threats and an ambush.');
    check(rules.discoveries.some(d=>d.kind==='cache') && rules.discoveries.some(d=>d.kind==='objective'), 'each depth requires supplies and objectives.');
    const sites=new Set();
    for(const discovery of rules.discoveries) { check(!sites.has(discovery.zone), 'discoveries must use distinct zones.'); sites.add(discovery.zone); }
    if(catalog) check(catalog.kits.some(k=>k.id===depth.kitId), `unknown kit ${depth.kitId}.`);
  }
  return config;
}
export function generateCampaignFloor(manifest, baseRules, campaignRules, depthIndex, seed) {
  const depth=campaignRules.depths[depthIndex];
  if(!depth) throw new Error('Invalid campaign depth.');
  const result=generateExplorationFloor(manifest,campaignDepthRules(baseRules,campaignRules,depth),`${seed}/${depth.id}`);
  result.floorPlan.map.label=depth.label;
  result.room.generation.familyId=depth.familyId;
  return result;
}

// Breadth-first distances are bounded by the authored floor dimensions.
function floorDistances(start,open) {
  const distances=new Map([[key(start),0]]),queue=[start];
  for(let i=0;i<queue.length;i++) for(const [dx,dy] of [[1,0],[-1,0],[0,1],[0,-1]]) {
    const p={x:queue[i].x+dx,y:queue[i].y+dy},k=key(p);
    if(open.has(k)&&!distances.has(k)){distances.set(k,distances.get(key(queue[i]))+1);queue.push(p);}
  }
  return distances;
}
function placeMechanisms(recipes,open,width,height,features,protectedCells,seed) {
  const occupied=new Set(features.map(key)),result=[];
  for(const recipe of recipes) {
    const candidates=[];
    for(let y=1;y<height-1;y++) for(let x=1;x<width-1;x++) {
      const start={x,y};
      if(!open.has(key(start))||occupied.has(key(start)))continue;
      for(const [dx,dy] of [[1,0],[0,1]]) {
        const cells=[];
        for(let step=1;step<Math.max(width,height);step++) {
          const p={x:x+dx*step,y:y+dy*step};
          if(p.x>=width-1||p.y>=height-1)break;
          if(open.has(key(p))) {
            if(cells.length && cells.length<=8 && !occupied.has(key(p)))candidates.push({start,end:p,cells});
            break;
          }
          if(occupied.has(key(p)))break;
          cells.push(p);
        }
      }
    }
    candidates.sort((a,b)=>a.cells.length-b.cells.length||floorSeed(`${seed}/${recipe.id}/${key(a.start)}/${key(a.end)}`)-floorSeed(`${seed}/${recipe.id}/${key(b.start)}/${key(b.end)}`));
    let placed;
    for(const candidate of candidates) {
      const distances=floorDistances(candidate.start,open);
      if(distances.get(key(candidate.end))<Math.max(6,candidate.cells.length+3))continue;
      const manual=[...distances].filter(([k,d])=>d>=6&&!occupied.has(k)&&k!==key(candidate.start)&&k!==key(candidate.end))
        .sort((a,b)=>a[1]-b[1]||(a[0]<b[0]?-1:a[0]>b[0]?1:0))[0];
      if(!manual)continue;
      const [mx,my]=manual[0].split(',').map(Number);
      placed={...structuredClone(recipe),...candidate.cells[0],openCells:candidate.cells,solutions:recipe.solutions.map(s=>({...structuredClone(s),...(s.kind==='manual'?{x:mx,y:my}:candidate.start)}))};
      for(const p of [candidate.start,candidate.end,{x:mx,y:my},...candidate.cells])occupied.add(key(p));
      for(const p of [candidate.start,candidate.end,{x:mx,y:my}])protectedCells.add(key(p));
      break;
    }
    if(!placed)throw new Error(`Cannot place meaningful floor mechanism ${recipe.id}.`);
    result.push(placed);
  }
  return result;
}
