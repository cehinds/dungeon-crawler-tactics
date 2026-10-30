// Field presentation consumes the shared C# exploration view; it awards no loot
// and never calculates encounters, movement legality or equipment bonuses.
const esc=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const stats=view=>{const s=view.generatedDungeon,p=s.floorPlan;return {s,p,won:s.defeatedGroupIds?.length??0,total:p.groups.length,found:s.claimedIds??[]};};
export function renderFieldShell(view,{portrait,worldControls}) {
 const map=view.exploration,{s,p,won,total,found}=stats(view);
 const nearby=map.points.filter(point=>point.canInteract&&!point.claimed);
 const goals=p.discoveries.filter(d=>d.kind==='objective');
 const goal=goals.find(d=>!found.includes(d.id));
 const instruction=goal?`Find: ${goal.label}`:won<total?'Clear the remaining encounters':view.generatedCampaign?'Reach the exit to review descent':'Reach the stairway';
 const danger=map.points.find(point=>point.kind==='danger'&&Math.abs(point.x-map.x)+Math.abs(point.y-map.y)<=4);
 const party=view.roster.filter(r=>r.selected);
 return `<section class="exploration-screen square-exploration field-screen" aria-label="Explore the floor">
 <header class="field-location"><small>${view.generatedCampaign?`EXPEDITION · DEPTH ${view.generatedCampaign.floorNumber} / ${view.generatedCampaign.totalFloors}`:'THE CRAWL · FLOOR EXPEDITION'}</small><h2>${esc(map.label.split(' / ')[0].replace(/^Depth \d+ · /,''))}</h2><p>${esc(instruction)} <span> · ${won}/${total} encounters</span></p></header>
 <div id="battlefield-slot" class="battlefield-slot">${worldControls()}<div class="board accessible-board" aria-label="Adjacent walkable tiles">${map.tiles.filter(t=>t.reachable).map(t=>`<button data-explore-cell="${t.x},${t.y}" aria-label="Walk to ${t.x},${t.y}"></button>`).join('')}</div><div id="map-inspect" hidden></div></div>
 <aside class="field-compass"><button id="field-map-button" aria-label="Open explored floor map">Map</button><button id="field-menu-button">Party & gear</button></aside>
 <div class="field-danger ${danger?'is-danger':''}" role="status">${danger?'! Danger area · Keep moving or prepare for an encounter':'Walk freely · WASD / arrows'}</div>
 <footer class="exploration-hud field-dock"><div class="walk-pad" aria-label="Walk"><button data-walk="north" aria-label="Walk up">↑</button><button data-walk="west" aria-label="Walk left">←</button><button data-walk="south" aria-label="Walk down">↓</button><button data-walk="east" aria-label="Walk right">→</button></div>
 <div class="explore-party">${party.map(r=>`<button class="explore-crawler" data-character-sheet="${esc(r.id)}" aria-label="${esc(r.label)} stats">${portrait(r)}<span><b>${esc(r.label.replace('Princess ','')).toUpperCase()}</b><small>HP ${r.hp}/${r.maxHp}</small></span></button>`).join('')}</div>
 <div class="explore-interactions">${nearby.length?nearby.slice(0,2).map(point=>`<button class="primary" data-explore-interact="${esc(point.id)}">${esc(point.label)} <kbd>E</kbd></button>`).join(''):'<span class="field-hint">Follow the paths.<br>Explore the side passages.</span>'}</div><div id="narrator-slot" class="narrator-slot"></div></footer></section>`;
}
export function renderFieldMenu(view) {
 const {won,total,p,found}=stats(view),campaign=view.generatedCampaign;
 const progress=campaign?`<div class="field-campaign-progress"><strong>${esc(campaign.label)}</strong><small>Depth ${campaign.floorNumber} of ${campaign.totalFloors} · ${campaign.completedFloors} completed</small><small>Descent is one-way. Your party and supplies carry forward.</small></div>`:'';
 const objectives=p.discoveries.filter(d=>d.kind==='objective').map(d=>`<li class="${found.includes(d.id)?'complete':''}"><span aria-hidden="true">${found.includes(d.id)?'✓':'◇'}</span>${esc(d.label)} · ${found.includes(d.id)?'Complete':'Find and activate'}</li>`).join('');
 return `<dialog id="field-menu" class="field-dialog"><div class="dialog-head"><h2>Expedition menu</h2><button data-close-field aria-label="Close menu">×</button></div><div class="modal-body">${progress}<p>${won}/${total} encounters cleared · Party level ${view.progression?.level??1}</p><ul class="field-objectives" aria-label="Floor objectives">${objectives}</ul><nav class="field-menu-grid">${[['party','Party status','Stats, skills and conditions'],['equipment','Equipment','Weapons, armor and charms'],['map','Floor map','Your explored paths and landmarks'],['home','Return to safe room','Rest and prepare; floor progress is kept'],['save','Save & options','Export, load and settings']].map(([id,name,detail])=>`<button data-field-action="${id}"><strong>${name}</strong><small>${detail}</small></button>`).join('')}</nav></div></dialog>`;
}
export function renderFieldMap(view) {
 const map=view.exploration,{s,p}=stats(view),revealed=new Set(map.tiles.filter(t=>t.revealed).map(t=>`${t.x},${t.y}`));
 const opened=(view.mechanisms??[]).filter(item=>item.solved).flatMap(item=>item.openedCells??[]).filter(cell=>revealed.has(`${cell.x},${cell.y}`)).map(cell=>`<rect x="${cell.x}" y="${cell.y}" width="1" height="1" fill="#70bd92"><title>Open shortcut</title></rect>`).join('');
 const mechanisms=(view.mechanisms??[]).filter(item=>!item.solved&&revealed.has(`${item.x},${item.y}`)).map(item=>`<rect x="${item.x}" y="${item.y}" width="1" height="1" fill="#eed08c"><title>${esc(item.label)} · Closed shortcut</title></rect>`).join('');
 const rects=map.tiles.filter(t=>t.revealed).map(t=>`<rect x="${t.x}" y="${t.y}" width="1" height="1" fill="${t.blocked?'#374252':'#a9a190'}"/>`).join('');
 const points=map.points.filter(point=>!point.claimed&&revealed.has(`${point.x},${point.y}`)).map(point=>`<circle cx="${point.x+.5}" cy="${point.y+.5}" r=".6" fill="${point.kind==='mechanism'?(view.mechanisms?.find(item=>item.id===point.mechanismId)?.solved?'#70bd92':'#eed08c'):point.kind==='enemy'?'#ed7777':point.kind==='danger'?'#e4a856':point.kind==='exit'?'#96c9ff':'#edd18c'}"><title>${esc(point.label)}${point.kind==='mechanism'?(view.mechanisms?.find(item=>item.id===point.mechanismId)?.solved?' · Open shortcut':' · Shortcut / lever'):''}</title></circle>`).join('');
 return `<dialog id="field-map" class="field-dialog"><div class="dialog-head"><h2>Explored floor</h2><button data-close-field aria-label="Close map">×</button></div><div class="modal-body"><svg class="field-map-svg" viewBox="0 0 ${map.width} ${map.height}" role="img" aria-label="Discovered paths. Blue is your position; red indicates visible enemies.">${rects}${opened}${mechanisms}${points}<circle cx="${map.x+.5}" cy="${map.y+.5}" r=".65" fill="#68e6ff" stroke="#fff" stroke-width=".15"/></svg><p>● You · Red: enemy · Amber: danger / discovery · Gold: shortcut / lever · Green: open route</p><p>Unexplored areas stay hidden. ${s.defeatedGroupIds.length}/${p.groups.length} encounters cleared.</p></div></dialog>`;
}

export function refreshFieldStep(view) {
 const map=view.exploration;
 const points=map.points.filter(p=>p.canInteract&&!p.claimed);
 const host=document.querySelector('.field-dock .explore-interactions');
 const html=points.length?points.slice(0,2).map(p=>`<button class="primary" data-explore-interact="${esc(p.id)}">${esc(p.label)} <kbd>E</kbd></button>`).join(''):'<span class="field-hint">Follow the paths.<br>Explore the side passages.</span>';
 if(host&&host.innerHTML!==html)host.innerHTML=html;
 const danger=map.points.some(p=>p.kind==='danger'&&Math.abs(p.x-map.x)+Math.abs(p.y-map.y)<=4);
 const status=document.querySelector('.field-danger');
 if(status){status.classList.toggle('is-danger',danger);status.textContent=danger?'! Danger area · Keep moving or prepare for an encounter':'Walk freely · WASD / arrows';}
 const board=document.querySelector('.field-screen .accessible-board');
 if(board)board.innerHTML=map.tiles.filter(t=>t.reachable).map(t=>`<button data-explore-cell="${t.x},${t.y}" aria-label="Walk to ${t.x},${t.y}"></button>`).join('');
}
