// Presentation only: all eligible targets, prices and receipts come from GameView.
const escape = value => String(value ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
const itemName = (view,id) => view.items?.find(item=>item.id===id)?.label ?? id;
const earned = view => view.audience?.challenges?.filter(challenge=>challenge.earned).length ?? 0;
const cellName = (view,id) => { const tile=view.tiles?.find(t=>t.id===id); return tile ? `${String.fromCharCode(65+tile.x)}${tile.y+1}` : id; };
function favorButton(view,item,targetId,unitId,label) {
  return `<button data-preview-favor data-item-id="${escape(item.id)}" data-unit-id="${escape(unitId)}" data-target-id="${escape(targetId)}" title="${escape(item.description)}">${escape(label)}</button>`;
}
export function renderAudienceSummary(view) {
  if(!view.audience)return '';
  return `<button class="audience-map-button" data-open-audience aria-label="Open sponsors and AI Favor"><span aria-hidden="true">◆</span> Favor ${view.audience.favor}/${view.audience.favorCap}<small>Sponsors ${earned(view)}/${view.audience.challenges.length}</small></button>`;
}
export function renderAudienceHome(view) {
  if(!view.audience)return '';
  return `<button class="audience-home-button" data-open-audience><span><strong>Sponsors & audience</strong><small>${earned(view)}/${view.audience.challenges.length} challenges delivered · saved for this run</small></span><span>Review offers →</span></button>`;
}
export function renderFavorControls(view,{itemId,unitId,targetId}={}) {
  const item=view.items?.find(i=>i.id===itemId);
  if(!item?.favorTargetIds?.includes(targetId))return '';
  return `<aside class="favor-offer"><strong>Keep your action with AI Favor</strong><p>Favor ${view.audience.favor} → ${view.audience.favor-1} · ${escape(item.label)} ${item.count} → ${item.count-1}. Movement and action stay unchanged.</p>${favorButton(view,item,targetId,unitId,'Preview with 1 Favor instead')}</aside>`;
}
export function renderAudience(view) {
  const audience=view.audience;if(!audience)return '';
  const actor=view.units?.find(u=>u.id===view.selectedUnitId);
  const utilities=(view.items??[]).filter(item=>audience.favorItemIds.includes(item.id));
  const canPlay=view.screen==='battle'&&view.phase==='player'&&actor?.hp>0&&!actor.finished;
  return `<dialog id="audience-dialog" aria-labelledby="audience-title"><div class="dialog-head"><div><span class="section-label">THE DUNGEON IS WATCHING</span><h2 id="audience-title">Sponsors & AI Favor</h2></div><button id="close-audience" aria-label="Close sponsors">×</button></div><div class="modal-body"><section class="audience-favor"><span class="audience-favor-value">◆ ${audience.favor}<small> / ${audience.favorCap} FAVOR</small></span><div><strong>${audience.favor?'One clever opportunity':audience.favorEarned?'Favor spent this encounter':'Make the environment work for you'}</strong><p>Your first committed elemental reaction earns one Favor per encounter. Spend it and one eligible supply to place an environmental effect without using your action or movement. Unspent Favor expires at the next encounter.</p></div></section><h3>Sponsor challenges</h3><p class="small muted">Each offer pays once per run. Previews and reloading cannot repeat a delivery.</p><div class="audience-challenges">${audience.challenges.map(c=>`<article class="audience-challenge${c.earned?' delivered':''}"><span class="audience-seal" aria-hidden="true">${c.earned?'✓':'◇'}</span><div><strong>${escape(c.label)}</strong><p>${escape(c.description)}</p><small>${c.earned?'DELIVERED':'REWARD'} · ${c.rewardCount} × ${escape(itemName(view,c.rewardItemId))}</small></div></article>`).join('')}</div><h3>Environmental supplies</h3><p>${canPlay?`Selected crawler: <strong>${escape(actor.label)}</strong>. Choose a supply, then a legal tile to review its exact placement.`:'Use these during an unfinished crawler’s battle turn. The selected crawler’s position sets the legal range.'} Traps trigger on the next entrant, including allies.</p><div class="audience-utilities">${utilities.map(item=>`<details class="audience-utility"><summary>${escape(item.label)} <span>×${item.count} · ${item.favorTargetIds.length} legal tiles</span></summary><p>${escape(item.description)}</p>${canPlay&&item.favorTargetIds.length?`<p class="small">Choose tile · costs 1 Favor + 1 supply. You will confirm before spending.</p><div class="favor-targets">${item.favorTargetIds.map(id=>favorButton(view,item,id,actor.id,cellName(view,id))).join('')}</div>`:`<p class="small muted">${!canPlay?'Enter battle and select an unfinished crawler.':!audience.favor?'Earn Favor from a reaction first.':!item.count?'Craft or collect this supply first.':'No legal target in range.'}</p>`}</details>`).join('')}</div><p class="small muted">These are original tactical rules inspired by the books and reported tabletop ideas. No live audience count or external social account is connected.</p></div><div class="modal-actions"><button id="done-audience">Back to ${view.screen==='camp'?'safe room':'map'}</button></div></dialog>`;
}
