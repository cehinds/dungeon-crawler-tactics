// Retained isometric presentation. C# owns legality, damage, turns and saved state.
// This module only draws authored assets and plays the ordered events it receives.
const ROOT = 'assets/revamp/';
const TILE_W = 128;
const TILE_H = 64;
const friendly = '#69dbff';
const hostile = '#ff6865';
const rowFor = {carl:0, donut:1, katia:2, mongo:3, rat:0, guard:1, boss:2};
const short = value => String(value ?? '').replace(/^[^.]+\./,'').replaceAll('_',' ');
const clamp = (value, low, high) => Math.max(low, Math.min(high, value));
const copy = value => JSON.parse(JSON.stringify(value));
const images = {};
const legacyImages = {};
let spriteFrames = {};
const directionalArt = {};
const directionalReady = fetch('assets/directional/manifest.json').then(r=>r.json()).then(async data=>{
  await Promise.all(Object.entries(data.characters??{}).map(([key,definition])=>new Promise(resolve=>{
    const image=new Image(); image.onload=()=>{directionalArt[key]={...definition,image};resolve();}; image.onerror=resolve;
    image.src='assets/directional/'+definition.file;
  })));
}).catch(()=>{});
const imageLoads = ['terrain','characters','enemies','ui','effects','mongo'].map(name => new Promise(resolve => {
  const image = new Image();
  image.onload = () => {images[name] = image; resolve();};
  image.onerror = resolve;
  image.src = ROOT + name + '.png';
}));
const ready = Promise.all([directionalReady,...imageLoads, ...['character-art.json','mongo-art.json'].map(file =>
  fetch(ROOT+file).then(r=>r.json()).then(data=>Object.assign(spriteFrames,data)).catch(()=>{}))]);

export function createBattlefield(canvas, {onCell, onHover} = {}) {
  const context = canvas.getContext('2d', {alpha:false});
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  let view = null, options = {}, visualUnits = [], visualTiles = [];
  let width = 1, height = 1, scale = 1, originX = 0, originY = 0;
  let hover = null, cursor = null, disposed = false, animation = null;
  let floating = [], effects = [], queue = Promise.resolve(), generation = 0;
  let missiles = [];
  let lastTime = 0, frameId = 0;
  let shakeUntil = 0;
  let zoomLevel = 1, panX = 0, panY = 0, cameraReady = false, lastSelection = null;
  let drag = null, suppressClick = false, rotation = 0;
  const facing = new Map();
  let explorationMotion = null;
  canvas.tabIndex = 0;
  canvas.setAttribute('role','application');
  canvas.setAttribute('aria-label','Dungeon map. Arrow keys inspect tiles; Enter selects the tile.');

  function rotateVector(x,y,q=rotation) {
    const p=q===1?{x:-y,y:x}:q===2?{x:-x,y:-y}:q===3?{x:y,y:-x}:{x,y};
    return {x:p.x||0,y:p.y||0};
  }
  function project(x, y) { const p=rotateVector(x,y); return {x:(p.x-p.y)*TILE_W/2, y:(p.x+p.y)*TILE_H/2}; }
  function screen(x, y) { const p=project(x,y); return {x:originX+p.x*scale,y:originY+p.y*scale}; }
  function mapData(){return view?.screen==='explore'?view.exploration:view;}
  function cellAt(clientX,clientY) {
    const box=canvas.getBoundingClientRect();
    const px=(clientX-box.left-originX)/scale, py=(clientY-box.top-originY)/scale;
    const p=rotateVector(Math.round(px/TILE_W+py/TILE_H),Math.round(py/TILE_H-px/TILE_W),(4-rotation)%4);
    const map=mapData();
    return map && p.x>=0 && p.y>=0 && p.x<map.width && p.y<map.height ? p : null;
  }
  function depth(x,y){return project(x,y).y/TILE_H*2;}
  // A screen key selects the nearest cardinal grid edge in that visual direction.
  function screenDirection(dx,dy) {
    const projected=dx<0?{x:0,y:1}:dx>0?{x:0,y:-1}:dy<0?{x:-1,y:0}:{x:1,y:0};
    return rotateVector(projected.x,projected.y,(4-rotation)%4);
  }
  function rememberFacing(id,dx,dy){if(dx||dy)facing.set(id,{x:Math.sign(dx),y:Math.sign(dy)});}
  function screenFacing(id){const direction=facing.get(id)??{x:0,y:1};const p=rotateVector(direction.x,direction.y);return p.x>0?'se':p.x<0?'nw':p.y>0?'sw':'ne';}
  function getRotationLabel(){return ['North view','East view','South view','West view'][rotation];}
  function rotate(delta){
    const map=mapData(); const anchor=map?{x:(map.width-1)/2,y:(map.height-1)/2}:null;
    const before=anchor?screen(anchor.x,anchor.y):null;
    rotation=((rotation+Math.round(delta))%4+4)%4;fit();
    if(anchor){const after=screen(anchor.x,anchor.y);panX+=before.x-after.x;panY+=before.y-after.y;fit();}
    canvas.dispatchEvent(new CustomEvent('maprotation',{detail:{rotation,label:getRotationLabel()}}));
  }
  function resize() {
    const box=canvas.getBoundingClientRect();
    width=Math.max(1,box.width); height=Math.max(1,box.height);
    const dpr=Math.min(devicePixelRatio || 1,2);
    canvas.width=Math.round(width*dpr); canvas.height=Math.round(height*dpr);
    context.setTransform(dpr,0,0,dpr,0,0);
    context.imageSmoothingEnabled=false;
    fit();
  }
  function fit() {
    const map = view?.screen === 'explore' ? view.exploration : view;
    if (!map) return;
    const corners=[[0,0],[map.width-1,0],[0,map.height-1],[map.width-1,map.height-1]].map(([x,y])=>project(x,y));
    const minX=Math.min(...corners.map(p=>p.x))-TILE_W/2,maxX=Math.max(...corners.map(p=>p.x))+TILE_W/2;
    const minY=Math.min(...corners.map(p=>p.y))-112,maxY=Math.max(...corners.map(p=>p.y))+TILE_H/2;
    const mapWidth=maxX-minX,mapHeight=maxY-minY;
    if(!cameraReady){zoomLevel=width<600?1.7:1;cameraReady=true;}
    scale=Math.max(.05,Math.min((width-28)/mapWidth,(height-24)/mapHeight)*zoomLevel);
    originX=width/2-(minX+maxX)/2*scale+panX;
    originY=height/2-(minY+maxY)/2*scale+panY;
  }
  function setView(next, settings={}) {
    const oldScreen=view?.screen;
    if(view?.screen==='explore' && next.screen==='explore' && view.exploration.id===next.exploration.id){
      const from=view.exploration,to=next.exploration;
      if(from.x!==to.x||from.y!==to.y){
        const path=pathTo(to.x,to.y); let cells=path.length?path:[[from.x,from.y],[to.x,to.y]];
        if(explorationMotion&&explorationMotion.duration>0){
          const priorMotion=explorationMotion,travel=clamp((performance.now()-priorMotion.started)/priorMotion.duration,0,1)*(priorMotion.cells.length-1);
          if(travel<priorMotion.cells.length-1){
            const index=Math.floor(travel),a=priorMotion.cells[index],b=priorMotion.cells[index+1],t=travel-index;
            cells=[[a[0]+(b[0]-a[0])*t,a[1]+(b[1]-a[1])*t],...priorMotion.cells.slice(index+1),...cells.slice(1)];
          }
        }
        explorationMotion={cells,started:performance.now(),duration:reduced.matches?0:Math.max(130,(cells.length-1)*130)};
        const last=cells.at(-1),prior=cells.at(-2); for(const u of next.roster??[])if(u.selected)rememberFacing(u.id,last[0]-prior[0],last[1]-prior[1]);
      }
    }
    if(oldScreen!==next.screen)explorationMotion=null;
    view=next; options=settings;
    if (!animation) {visualUnits=copy(next.units ?? []); visualTiles=copy(next.tiles ?? []);}
    if (!cursor || oldScreen!==next.screen || lastSelection!==next.selectedUnitId) {
      const selected=next.units?.find(u=>u.id===next.selectedUnitId);
      cursor=selected ? {x:selected.x,y:selected.y} : {x:next.exploration?.x??1,y:next.exploration?.y??1};
    }
    fit();
    if(width<600 && (lastSelection!==next.selectedUnitId || oldScreen!==next.screen)) centerSelected();
    lastSelection=next.selectedUnitId;
  }
  function diamond(x,y,{stroke,fill,weight=2,inset=0}={}) {
    const p=project(x,y), w=TILE_W/2-inset, h=TILE_H/2-inset/2;
    context.beginPath(); context.moveTo(p.x,p.y-h); context.lineTo(p.x+w,p.y);
    context.lineTo(p.x,p.y+h); context.lineTo(p.x-w,p.y); context.closePath();
    if(fill){context.fillStyle=fill;context.fill();}
    if(stroke){context.strokeStyle=stroke;context.lineWidth=weight/scale;context.stroke();}
  }
  function atlas(name,index,cols,rows,dx,dy,dw,dh) {
    const image=images[name]; if(!image)return;
    const sw=image.width/cols, sh=image.height/rows;
    context.drawImage(image,(index%cols)*sw,Math.floor(index/cols)*sh,sw,sh,dx,dy,dw,dh);
  }
  function floor(x,y,index,alpha=1) {
    const image=images.terrain;if(!image)return;
    const cell=image.width/4,p=project(x,y);
    context.globalAlpha=alpha;
    // Crop the generated diamond's transparent margins, then fit its footprint.
    context.drawImage(image,index*cell+cell*.022,cell*.273,cell*.956,cell*.575,
      p.x-TILE_W/2-.5,p.y-TILE_H/2-.5,TILE_W+1,TILE_H+1);
    context.globalAlpha=1;
  }
  function prop(x,y,index,size=128,alpha=1) {
    const p=project(x,y);
    context.globalAlpha=alpha;
    atlas('terrain',index,4,3,p.x-size/2,p.y-size*.77,size,size);
    context.globalAlpha=1;
  }
  function text(message,x,y,color='#fff0cb',size=14) {
    context.font=`bold ${size}px "Courier New", monospace`;
    context.textAlign='center';context.textBaseline='middle';
    context.lineWidth=4;context.strokeStyle='#06111dec';context.strokeText(message,x,y);
    context.fillStyle=color;context.fillText(message,x,y);
  }
  function sprite(unit,time) {
    if(unit.hp<=0)return;
    const enemy=unit.team==='enemy';
    const key=unit.artId || (enemy?'rat':unit.id?.split('.').pop());
    const row=rowFor[key] ?? (enemy?1:0);
    let col=reduced.matches?0:enemy ? Math.floor(time/600)%2 : Math.floor(time/650)%2;
    const current=animation?.event;
    const exploringWalk=view.screen==='explore'&&explorationMotion&&time-explorationMotion.started<explorationMotion.duration;
    const actor=current?.actorId===unit.id, target=current?.targetId===unit.id;
    if(exploringWalk)col=2+Math.floor((time-explorationMotion.started)/95)%2;
    if(actor && ['move','push','teleport'].includes(current.type)) col=enemy?Math.floor(time/105)%2:2+Math.floor(time/95)%3;
    if(actor && current?.type==='attack') col=enemy?2:(animation.progress<.38?5:6);
    if(target && ['damage','guard'].includes(current?.type)) col=enemy?3:7;
    if(key==='katia' && (unit.tags??[]).includes('status.guarded') && !actor && !target) col=5;
    const p=project(unit.x,unit.y), selected=unit.id===view.selectedUnitId;
    if(enemy){
      const direction=rotateVector(...Object.values(facing.get(unit.id)??{x:0,y:1}));
      const dx=(direction.x-direction.y)*22,dy=(direction.x+direction.y)*11;
      context.beginPath();context.moveTo(p.x+dx,p.y+dy);context.lineTo(p.x+dx*.55-dy*.25,p.y+dy*.55+dx*.125);context.lineTo(p.x+dx*.55+dy*.25,p.y+dy*.55-dx*.125);context.closePath();context.fillStyle='#ffb18c';context.fill();
    }
    const pose=(enemy?['idle','walk','attack','hit']:['idle','idle2','walk1','walk2','walk3','windup','attack','hit'])[col];
    const atlasName=key==='mongo' && images.mongo && spriteFrames.mongo ? 'mongo' : enemy?'enemies':'characters';
    const directional=!enemy?directionalArt[key]:null;
    const walking=exploringWalk || (actor && ['move','push','teleport'].includes(current?.type));
    const directionalPose=walking?`walk${1+Math.floor(time/105)%2}`:'idle';
    const directionalFrame=directional?.frames?.[screenFacing(unit.id)]?.[directionalPose];
    const actionPose=actor&&current?.type==='attack'||target&&['damage','guard'].includes(current?.type);
    const legacyFrame=spriteFrames[atlasName]?.frames?.[key]?.[pose];
    const useDirectional=directionalFrame&&(!actionPose||!legacyFrame||screenFacing(unit.id)!=='se');
    const frame=useDirectional?directionalFrame:legacyFrame;
    const size=useDirectional ? directional.bodyHeight ?? frame.drawHeight : frame?.drawHeight ?? (key==='boss'?148:100);
    diamond(unit.x,unit.y,{stroke:unit.team==='enemy'?hostile:friendly,fill:unit.team==='enemy'?'#c12c242b':'#269ed321',weight:selected?3:1.5,inset:23});
    if(selected) diamond(unit.x,unit.y,{stroke:'#fff1b2',weight:2,inset:19});
    context.globalAlpha=unit.acted && unit.team==='player'?.63:1;
    if((unit.tags??[]).includes('status.guarded')) {
      context.globalAlpha=.46;atlas('ui',14,4,4,p.x-45,p.y-95,90,90);context.globalAlpha=1;
    }
    const enlarged=(unit.tags??[]).some(t=>/shapeshift|transformed/.test(t)) || key==='katia'&&(unit.tags??[]).includes('status.guarded')?1.12:1;
    const image=useDirectional?directional.image:images[atlasName];
    if(useDirectional&&actor&&current?.type==='attack'){
      const direction=rotateVector(...Object.values(facing.get(unit.id)??{x:0,y:1}));
      const reach=reduced.matches?0:Math.sin(animation.progress*Math.PI)*9;
      p.x+=(direction.x-direction.y)*reach;p.y+=(direction.x+direction.y)*reach*.5;
    }
    if(frame&&image) {
      const dw=frame.drawWidth*enlarged,dh=frame.drawHeight*enlarged;
      context.drawImage(image,frame.x,frame.y,frame.width,frame.height,p.x-dw*frame.anchorX,p.y-dh*frame.anchorY,dw,dh);
    } else if(!enemy && !(key in rowFor)) {
      const classKey=(unit.classId??'class.brawler').replace('class.','');
      if(!legacyImages[classKey]){const fallback=new Image();fallback.src=`assets/${classKey}.png`;legacyImages[classKey]=fallback;}
      const fallback=legacyImages[classKey];if(fallback.complete&&fallback.naturalWidth)context.drawImage(fallback,p.x-45,p.y-85,90,90);
    } else atlas(enemy?'enemies':'characters',row*(enemy?4:8)+col,enemy?4:8,enemy?3:4,
      p.x-size*enlarged/2,p.y-size*enlarged*.91,size*enlarged,size*enlarged);
    context.globalAlpha=1;
    const healthY=p.y-size*.91-5;
    context.fillStyle='#08131e';context.fillRect(p.x-24,healthY,48,5);
    context.fillStyle=enemy?hostile:'#80d8a4';context.fillRect(p.x-23,healthY+1,46*clamp(unit.hp/unit.maxHp,0,1),3);
    if(unit.acted && !enemy)text('DONE',p.x,p.y+14,'#a4b1bd',10);
    if(hover?.x===Math.round(unit.x)&&hover?.y===Math.round(unit.y)) text(`${unit.label} ${unit.hp}/${unit.maxHp}`,p.x,healthY-13,enemy?'#ffb3a3':'#e3f5ff',13);
    const tags=unit.tags??[];
    if(tags.includes('status.wet')) text('WET',p.x+37,p.y-48,'#84e8ff',11);
    if(tags.includes('status.frozen')) text('FROZEN',p.x,p.y-70,'#b3faff',11);
    if(tags.includes('status.shocked')) text('SHOCK',p.x+34,p.y-35,'#d8b6ff',11);
  }
  function pathTo(x,y) {
    const explore=view?.screen==='explore',map=mapData();
    const actor=explore?map:visualUnits.find(u=>u.id===view.selectedUnitId);
    if(!actor || !explore&&options.mode==='ability')return [];
    const allowed=new Set((explore?map.tiles.filter(t=>t.reachable):view.reachable??[]).map(t=>`${t.x},${t.y}`));
    const revealed=explore?new Set(map.tiles.filter(t=>t.revealed).map(t=>`${t.x},${t.y}`)):null;
    const goal=`${x},${y}`;if(!allowed.has(goal))return [];
    const start=`${actor.x},${actor.y}`, frontier=[[actor.x,actor.y]], parents=new Map([[start,null]]);
    for(let i=0;i<frontier.length;i++) {
      const [cx,cy]=frontier[i]; if(`${cx},${cy}`===goal)break;
      if(revealed&&!revealed.has(`${cx},${cy}`))continue;
      for(const [dx,dy]of[[0,-1],[-1,0],[1,0],[0,1]]) {
        const nx=cx+dx,ny=cy+dy,key=`${nx},${ny}`;
        if(allowed.has(key)&&!parents.has(key)){parents.set(key,`${cx},${cy}`);frontier.push([nx,ny]);}
      }
    }
    if(!parents.has(goal))return [];
    const result=[];for(let key=goal;key!==null;key=parents.get(key))result.unshift(key.split(',').map(Number));
    return result;
  }
  function highlights() {
    const exploring=view.screen==='explore';
    const reachable=exploring?view.exploration.tiles.filter(t=>t.reachable):view.reachable??[];
    if(exploring||options.mode!=='ability') for(const tile of reachable) diamond(tile.x,tile.y,{stroke:'#67d9fd66',weight:1,fill:'#42c8ff0b',inset:3});
    if(!exploring && options.mode==='ability') {
      const targets=new Set(options.action?.targetIds??[]);
      for(const tile of visualTiles) {
        const unit=visualUnits.find(u=>u.hp>0&&u.x===tile.x&&u.y===tile.y);
        if(targets.has(tile.id)||targets.has(unit?.id)) {
          const color=unit?.team==='player'?'#82e7a1':unit?.team==='enemy'?'#ff777c':'#6ddfff';
          diamond(tile.x,tile.y,{stroke:color,fill:color+'28',weight:2,inset:4});
        }
      }
    }
    if(hover) {
      diamond(hover.x,hover.y,{stroke:'#fff4ba',weight:2,inset:2});
      {
        const path=pathTo(hover.x,hover.y);
        if(path.length) {context.beginPath();path.forEach(([x,y],i)=>{const p=project(x,y);i?context.lineTo(p.x,p.y):context.moveTo(p.x,p.y);});context.lineWidth=3;context.strokeStyle='#96efff';context.stroke();const end=project(hover.x,hover.y);text(`${path.length-1} STEP${path.length===2?'':'S'}`,end.x,end.y+29,'#b8f4ff',12);}
      }
    }
    for(const item of options.preview??[]) {
      if(item.beforeX!==item.afterX||item.beforeY!==item.afterY) diamond(item.afterX,item.afterY,{stroke:'#e7c9ff',fill:'#ac76e330',weight:3,inset:8});
    }
    const previewTarget=visualUnits.find(u=>u.id===options.targetId)??visualTiles.find(t=>t.id===options.targetId);
    if(previewTarget)diamond(previewTarget.x,previewTarget.y,{stroke:'#ffc16b',fill:'#ffc16b30',weight:3,inset:8});
  }
  function effectSprite(type,x,y,age,duration) {
    if(age<0)return;
    const p=project(x,y),row=type==='fire'?0:type==='explosion'?2:1;
    const index=row*4+Math.min(3,Math.floor(age/duration*4));
    const size=type==='explosion'?154:100;
    atlas('effects',index,4,3,p.x-size/2,p.y-size*(type==='fire'?.96:.72),size,size);
  }
  function draw(time) {
    if(disposed)return;
    frameId=requestAnimationFrame(draw);
    // Idle artwork animates at a modest rate; moving events still use the display refresh rate.
    if(!animation && time-lastTime<32)return;lastTime=time;
    context.fillStyle='#080f1b';context.fillRect(0,0,width,height);
    if(!view || !images.terrain)return;
    context.save();
    const shake=!reduced.matches&&time<shakeUntil?Math.sin(time*.1)*2:0;
    context.translate(originX+shake,originY);context.scale(scale,scale);
    const explore=view.screen==='explore', map=explore?view.exploration:view;
    const tiles=explore?map.tiles:visualTiles;
    for(const tile of tiles) {
      const tags=tile.tags??[];
      const known=!explore||tile.revealed;
      const terrain=tags.includes('surface.water')?2:tags.includes('surface.oil')?3:(tile.x*3+tile.y)%4===0?1:0;
      if(known)floor(tile.x,tile.y,terrain);
      else if(tile.reachable)floor(tile.x,tile.y,0,.22);
    }
    highlights();
    const drawables=[];
    // Exterior wall art is outside the playable grid. It gives the rooms readable
    // architecture without introducing decorative obstacles into the simulation.
    if(!explore) {
      const farY=rotation===1||rotation===2?map.height:-1,farX=rotation===2||rotation===3?map.width:-1;
      for(let x=0;x<map.width;x++)drawables.push({depth:depth(x,farY),draw:()=>prop(x,farY,x%4===1?6:4,128,.95)});
      for(let y=0;y<map.height;y++)drawables.push({depth:depth(farX,y),draw:()=>prop(farX,y,y%4===2?6:5,128,.95)});
    }
    for(const tile of tiles) {
      if(explore&&!tile.revealed)continue;
      if(tile.blocked)drawables.push({depth:depth(tile.x,tile.y),draw:()=>{
        const wall=project(tile.x,tile.y);
        const nearby=visualUnits.some(u=>{const p=project(u.x,u.y);return u.hp>0&&p.y>=wall.y&&p.y-wall.y<70&&Math.abs(p.x-wall.x)<90;});
        const crate=(tile.x+tile.y)%5===0;
        prop(tile.x,tile.y,crate?8:(tile.x+tile.y)%6===0?6:(tile.x*7+tile.y)%5===0?5:4,crate?95:128,nearby?.66:1);
      }});
      if((tile.tags??[]).includes('surface.oil')) drawables.push({depth:depth(tile.x,tile.y)-.1,draw:()=>prop(tile.x+.15,tile.y+.1,9,65,.95)});
      if((tile.tags??[]).includes('surface.burning'))drawables.push({depth:depth(tile.x,tile.y)+.1,draw:()=>effectSprite('fire',tile.x,tile.y,reduced.matches?0:time%800,800)});
    }
    if(explore) {
      for(const point of map.points??[]) {
        if(point.claimed)continue;
        drawables.push({depth:depth(point.x,point.y),draw:()=>{
          prop(point.x,point.y,point.kind==='encounter'?11:point.kind==='cache'?10:8,point.kind==='encounter'?135:74);
          const p=project(point.x,point.y);text(point.kind==='encounter'?'ENTER':point.kind==='cache'?'SUPPLIES':'INSPECT',p.x,p.y+21,'#f4dd9c',12);
        }});
      }
      const party=(view.roster??[]).filter(u=>u.selected).slice(0,4);
      let partyX=map.x,partyY=map.y;
      if(explorationMotion&&explorationMotion.duration>0){
        const travel=clamp((time-explorationMotion.started)/explorationMotion.duration,0,1)*(explorationMotion.cells.length-1);
        const index=Math.min(Math.floor(travel),explorationMotion.cells.length-2),a=explorationMotion.cells[index],b=explorationMotion.cells[index+1],t=travel-index;
        partyX=a[0]+(b[0]-a[0])*t;partyY=a[1]+(b[1]-a[1])*t;
        if(travel<explorationMotion.cells.length-1)for(const u of party)rememberFacing(u.id,b[0]-a[0],b[1]-a[1]);
      }
      party.forEach((u,i)=>drawables.push({depth:depth(partyX,partyY)+i*.02+.2,draw:()=>sprite({...u,x:partyX+(i%2)*.27-.12,y:partyY+Math.floor(i/2)*.25-.12,hp:u.hp??u.maxHp??40,maxHp:u.maxHp||40,team:'player',tags:[]},time)}));
    } else {
      for(const u of visualUnits)drawables.push({depth:depth(u.x,u.y)+.15,draw:()=>sprite(u,time)});
    }
    drawables.sort((a,b)=>a.depth-b.depth).forEach(item=>item.draw());
    effects=effects.filter(e=>time-e.started<e.duration);
    for(const e of effects)effectSprite(e.type,e.x,e.y,time-e.started,e.duration);
    missiles=missiles.filter(m=>time-m.started<m.duration);
    for(const m of missiles) {
      const progress=clamp((time-m.started)/m.duration,0,1);
      if(progress<=0)continue;
      const from=project(m.fromX,m.fromY),to=project(m.toX,m.toY);
      const px=from.x+(to.x-from.x)*progress,py=from.y+(to.y-from.y)*progress-48;
      atlas('effects',4+Math.floor(progress*3),4,3,px-29,py-29,58,58);
    }
    floating=floating.filter(f=>time-f.started<1100);
    for(const f of floating) {const p=project(f.x,f.y),age=time-f.started;context.globalAlpha=Math.min(1,(1100-age)/250);text(f.text,p.x,p.y-68-age*.027,f.color,18);context.globalAlpha=1;}
    context.restore();
  }
  function eventUnit(event) {return visualUnits.find(u=>u.id===(event.targetId||event.actorId))??visualTiles.find(t=>t.id===event.targetId);}
  function float(message,unit,color='#ffdc93') {if(unit)floating.push({text:message,x:unit.x,y:unit.y,started:performance.now(),color});}
  function playOne(event,token) {
    if(disposed||token!==generation)return Promise.resolve();
    const actor=visualUnits.find(u=>u.id===event.actorId);
    const target=eventUnit(event);
    const moving=['move','push','teleport'].includes(event.type);
    const mover=event.type==='push'?target:actor??target;
    if(moving&&mover)rememberFacing(mover.id,event.toX-event.fromX,event.toY-event.fromY);
    if(event.type==='attack'&&actor&&target)rememberFacing(actor.id,target.x-actor.x,target.y-actor.y);
    let duration=moving?(mover?.team==='enemy'?175:130):event.type==='attack'?270:event.type==='damage'?190:event.type==='reaction'?240:event.type==='phase'?260:45;
    if(reduced.matches)duration=0;
    if(event.type==='damage') {if(target)target.hp=event.after;float(`−${Math.abs(event.amount)}`,target,'#ff8880');}
    if(event.type==='heal') {if(target)target.hp=event.after;float(`+${Math.abs(event.amount)}`,target,'#9cffa5');}
    if(event.type==='guard')float(`BLOCK ${event.amount}`,target,'#a0dcff');
    if(event.type==='reaction') {
      float(short(event.reactionId).toUpperCase(),target,'#ffe29a');
      if(target)effects.push({type:/ignit|explos|fire/.test(event.reactionId)?'explosion':'magic',x:target.x,y:target.y,started:performance.now(),duration:440});
    }
    if(event.type==='attack'&&target) {
      const id=event.abilityId??'';
      if(/bomb|explos|fire/.test(id)) {effects.push({type:'explosion',x:target.x,y:target.y,started:performance.now()+100,duration:420});shakeUntil=performance.now()+280;}
      else if(/missile|spark|teleport|puddle|heal/.test(id))effects.push({type:'magic',x:target.x,y:target.y,started:performance.now()+90,duration:420});
      if(actor&&/missile|spark/.test(id))missiles.push({fromX:actor.x,fromY:actor.y,toX:target.x,toY:target.y,started:performance.now()+70,duration:260});
      if(/shapeshift/.test(id))effects.push({type:'magic',x:target.x,y:target.y,started:performance.now(),duration:350});
    }
    if(event.type==='tag_add'||event.type==='tag_remove') {
      const entity=target??visualTiles.find(t=>t.id===event.targetId);
      if(entity)entity.tags=event.type==='tag_add'?[...new Set([...(entity.tags??[]),event.tag])]:(entity.tags??[]).filter(t=>t!==event.tag);
      if(event.type==='tag_add')float(short(event.tag).toUpperCase(),target,'#bce8ff');
    }
    if(event.type==='phase')canvas.dispatchEvent(new CustomEvent('battlephase',{detail:{phase:event.tag}}));
    const started=performance.now();
    return new Promise(resolve=>{
      function step(now) {
        if(disposed||token!==generation){resolve();return;}
        const progress=duration?clamp((now-started)/duration,0,1):1;
        animation={event,progress};
        if(moving&&mover){mover.x=event.fromX+(event.toX-event.fromX)*progress;mover.y=event.fromY+(event.toY-event.fromY)*progress;}
        if(progress<1)requestAnimationFrame(step);else resolve();
      }
      requestAnimationFrame(step);
    });
  }
  function playEvents(events,before,after) {
    const committed=(events??[]).filter(event=>!event.preview);
    if(!committed.length) {setView(after,options);return Promise.resolve();}
    const token=++generation;
    visualUnits=copy(before.units??[]);visualTiles=copy(before.tiles??[]);
    animation={event:{type:'pending'},progress:0};view=after;fit();
    queue=(async()=>{
      for(const event of committed)await playOne(event,token);
      if(token===generation){animation=null;visualUnits=copy(after.units??[]);visualTiles=copy(after.tiles??[]);}
    })();
    return queue;
  }
  function skipAnimations() {explorationMotion=null;generation++;animation=null;if(view){visualUnits=copy(view.units??[]);visualTiles=copy(view.tiles??[]);}effects=[];floating=[];missiles=[];}
  function centerSelected() {
    const unit=view?.screen==='explore'?view.exploration:view?.units?.find(u=>u.id===view.selectedUnitId);
    if(!unit)return;
    const pos=screen(unit.x,unit.y);panX+=width/2-pos.x;panY+=height*.56-pos.y;fit();
  }
  function zoom(delta) {zoomLevel=clamp(zoomLevel+delta,.7,3.2);fit();centerSelected();}
  const down=event=>{drag={id:event.pointerId,x:event.clientX,y:event.clientY,startX:event.clientX,startY:event.clientY};suppressClick=false;canvas.setPointerCapture(event.pointerId);};
  const up=event=>{if(drag?.id===event.pointerId)drag=null;};
  const move=event=>{
    if(drag?.id===event.pointerId && (suppressClick||Math.hypot(event.clientX-drag.startX,event.clientY-drag.startY)>6)) {
      suppressClick=true;panX+=event.clientX-drag.x;panY+=event.clientY-drag.y;drag.x=event.clientX;drag.y=event.clientY;fit();return;
    }
    hover=cellAt(event.clientX,event.clientY);if(hover)onHover?.(hover.x,hover.y);
  };
  const leave=()=>{hover=null;onHover?.(null,null);};
  const click=event=>{if(suppressClick){suppressClick=false;return;}const cell=cellAt(event.clientX,event.clientY);if(cell){cursor=cell;onCell?.(cell.x,cell.y);}};
  const wheel=event=>{event.preventDefault();zoom(event.deltaY>0?-.15:.15);};
  const key=event=>{
    if(!view)return;
    const input={ArrowUp:[0,-1],ArrowDown:[0,1],ArrowLeft:[-1,0],ArrowRight:[1,0],w:[0,-1],s:[0,1],a:[-1,0],d:[1,0]}[event.key.length===1?event.key.toLowerCase():event.key];
    const direction=input?screenDirection(...input):null;
    const map=view.screen==='explore'?view.exploration:view;
    if(direction && view.screen==='explore') {
      event.preventDefault();event.stopPropagation();
      const x=map.x+direction.x,y=map.y+direction.y;
      if(map.tiles.some(t=>t.x===x&&t.y===y&&t.reachable))onCell?.(x,y);
      return;
    }
    if(direction){event.preventDefault();event.stopPropagation();cursor={x:clamp((cursor?.x??0)+direction.x,0,map.width-1),y:clamp((cursor?.y??0)+direction.y,0,map.height-1)};hover=cursor;onHover?.(cursor.x,cursor.y);}
    if(event.key==='Enter'||event.key===' '){event.preventDefault();if(cursor)onCell?.(cursor.x,cursor.y);}
  };
  canvas.addEventListener('pointermove',move);canvas.addEventListener('pointerleave',leave);canvas.addEventListener('click',click);canvas.addEventListener('keydown',key);
  canvas.addEventListener('pointerdown',down);canvas.addEventListener('pointerup',up);canvas.addEventListener('pointercancel',up);canvas.addEventListener('wheel',wheel,{passive:false});
  const observer=new ResizeObserver(resize);observer.observe(canvas);
  ready.then(resize);resize();frameId=requestAnimationFrame(draw);
  return {setView,playEvents,resize,skipAnimations,zoom,centerSelected,rotate,getRotationLabel,getRotation:()=>rotation,screenDirection,
    // Coordinates support real pointer-based browser regression tests.
    cellToScreen:(x,y)=>screen(x,y),
    screenToCell:(x,y)=>{const box=canvas.getBoundingClientRect();return cellAt(x+box.left,y+box.top);},
    getPathTo:(x,y)=>pathTo(x,y),
    dispose(){disposed=true;generation++;cancelAnimationFrame(frameId);observer.disconnect();canvas.removeEventListener('pointermove',move);canvas.removeEventListener('pointerleave',leave);canvas.removeEventListener('click',click);canvas.removeEventListener('keydown',key);canvas.removeEventListener('pointerdown',down);canvas.removeEventListener('pointerup',up);canvas.removeEventListener('pointercancel',up);canvas.removeEventListener('wheel',wheel);}
  };
}
