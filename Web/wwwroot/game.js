const $ = (selector) => document.querySelector(selector);
const assembly = 'DungeonCrawlerTactics.Web';
const saveKey = 'dungeon-crawler-tactics.save.v1';
let view;
let content;
let gameData;
let busy = false;
let localAction = null;
let focusedRoster = null;
let inspectedTile = null;
let targetTile = false;
let toastTimeout;
let chosenReward = false;
const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, (c) => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }[c]));
const e = escapeHtml;
const call = (method, ...args) => DotNet.invokeMethodAsync(assembly, method, ...args);
const classLabel = (id) => view?.classes.find(c => c.id === id)?.label ?? id?.replace('class.', '') ?? '';
const unit = () => view?.units.find(u => u.id === view.selectedUnitId);
const shortTag = (tag) => tag.replace(/^[^.]+\./, '').replace(/_/g, ' ').toUpperCase();
const tagClass = (tag) => /fire|burning/.test(tag) ? 'fire' : /oil/.test(tag) ? 'oil' : /wet|lightning|shock/.test(tag) ? 'water' : /frozen|frost|ice/.test(tag) ? 'frost' : '';
const tags = (values = []) => values.map(t => `<span class="tag ${tagClass(t)}" title="${e(t)}">${e(shortTag(t))}</span>`).join('');
const spriteName = (u) => u.id === 'crawler.donut' ? 'donut' : u.team === 'enemy' ? (/boss|foreman|retention_engine|Retention Engine/i.test(u.id + ' ' + u.label) ? 'boss' : 'enemy') : u.classId?.replace('class.', '') ?? 'brawler';
const portrait = (u, className = 'unit-portrait') => `<img class="${className}${u.hp === 0 ? ' dead' : ''}" src="assets/${e(spriteName(u))}.png" alt="" aria-hidden="true" />`;
const hpBar = (u) => `<span class="health${u.team === 'enemy' ? ' enemy-hp' : ''}"><span style="width:${Math.max(0, Math.min(100, u.hp / u.maxHp * 100))}%"></span></span>`;
const displayLog = (text) => text.replace(/(?:ability|reaction|surface|status|element|damage|impact)\.[a-z0-9_]+/g, id => content?.abilities.find(a => a.id === id)?.label ?? id.replace(/^[^.]+\./, '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()));
const selectedAction = () => localAction?.itemId ? view.items.find(a => a.id === localAction.itemId) : view.abilities.find(a => a.id === localAction?.abilityId);

function toast(message) {
  $('#toast').textContent = message;
  $('#toast').hidden = false;
  clearTimeout(toastTimeout);
  toastTimeout = setTimeout(() => $('#toast').hidden = true, 4200);
}
function openDialog(id) { if (!$(id).open) $(id).showModal(); }
function closeDialog(id) { $(id).close(); }
async function persist() {
  try {
    const serialized = await call('GetSave');
    localStorage.setItem(saveKey, serialized);
    $('#save-status').textContent = 'Progress saved in this browser';
  } catch (error) {
    $('#save-status').textContent = 'Local save unavailable · export a backup';
  }
}
async function command(type, args = {}, { preserveAction = false, save = true } = {}) {
  if (busy) return;
  busy = true;
  $('#game').setAttribute('aria-busy', 'true');
  try {
    const previousScreen = view.screen;
    const result = await call('Dispatch', JSON.stringify({ type, ...args }));
    view = JSON.parse(result);
    if (!preserveAction) localAction = null;
    if (type === 'choose_reward' && previousScreen === 'victory') chosenReward = view.rewards.length === 0;
    if (type === 'continue' || type === 'start' || type === 'new_run' || type === 'retry') {
      chosenReward = false;
      inspectedTile = null;
    }
    if (save && type !== 'preview' && type !== 'cancel') await persist();
    busy = false;
    render();
  } catch (error) {
    toast(`The command could not be completed: ${error.message}`);
  } finally {
    busy = false;
    $('#game').setAttribute('aria-busy', 'false');
  }
}
function renderProgress() {
  const progress = $('#run-progress');
  progress.querySelectorAll('span').forEach((span, index) => {
    span.classList.toggle('current', index === view.encounterIndex && view.screen !== 'complete');
    span.classList.toggle('done', index < view.encounterIndex || view.screen === 'complete');
    span.textContent = index < view.encounterIndex || view.screen === 'complete' ? '✓' : String(index + 1).padStart(2, '0');
  });
}
function render() {
  renderProgress();
  $('#game').innerHTML = view.screen === 'camp' ? renderCamp() : view.screen === 'battle' ? renderBattle() : view.screen === 'victory' ? renderVictory() : renderEnding();
  bindScreen();
  window.dungeonView = view;
}
function renderCamp() {
  const focused = view.roster.find(r => r.id === focusedRoster) ?? view.roster.find(r => r.selected) ?? view.roster[0];
  focusedRoster = focused?.id;
  const focusClass = view.classes.find(c => c.id === focused?.classId);
  const encounter = gameData.encounters[view.encounterIndex];
  return `<section aria-labelledby="screen-title"><div class="screen-heading"><div><h2 id="screen-title">A little preparation. A little mayhem.</h2><p>Choose ${view.partyCapacity} crawlers and their classes. The next room won’t clear itself.</p></div><div class="status-group"><span class="tag gold">CAMP / FLOOR 01</span><span class="small muted mono">${view.xp} XP EARNED</span></div></div>
  <div class="camp-layout"><section class="panel"><div class="panel-head"><h3>YOUR ROSTER</h3><span class="small mono ${view.partyCount === view.partyCapacity ? '' : 'muted'}">${view.partyCount} / ${view.partyCapacity} DEPLOYED</span></div><div class="roster-grid">${view.roster.map(r => `<button class="roster-card${r.selected ? ' chosen' : ''}${r.id === focused.id ? ' focused' : ''}" data-roster="${e(r.id)}" aria-pressed="${r.id === focused.id}">${portrait(r)}<span><strong>${e(r.label)}</strong><small>${e(classLabel(r.classId))}</small><small>${r.selected ? 'DEPLOYED' : 'RESERVE'} · ${r.hp} / ${r.maxHp} HP</small></span><span class="choice-marker" aria-hidden="true">${r.selected ? '✓' : ''}</span></button>`).join('')}</div><div class="roster-bottom"><span>Select a crawler to edit their class or deployment.</span><span class="mono">${view.roster.length} CRAWLERS · ${view.classes.length} CLASSES</span></div></section>
  <aside class="panel"><div class="panel-body"><div class="loadout-head">${portrait(focused)}<div><h2>${e(focused.label)}</h2><p>${focused.selected ? 'Deployed for the next encounter' : 'Resting in reserve'}</p><div class="tags" style="margin-top:8px"><span class="tag good">${focused.hp} / ${focused.maxHp} HP</span></div></div></div><label class="field" for="class-select">ACTIVE CLASS<select id="class-select">${view.classes.map(c => `<option value="${e(c.id)}" ${c.id === focused.classId ? 'selected' : ''}>${e(c.label)}</option>`).join('')}</select></label><div class="class-abilities">${(focusClass?.abilityIds ?? []).map(id => `<span title="${e(content.abilities.find(a => a.id === id)?.effects.map(x => x.op).join(', ') ?? '')}">${e(content.abilities.find(a => a.id === id)?.label ?? id)}</span>`).join('')}</div><button class="camp-party-toggle" id="toggle-party">${focused.selected ? 'Move to reserve' : 'Deploy this crawler'}</button><div class="encounter-brief"><span class="section-label">NEXT / ENCOUNTER ${view.encounterIndex + 1} OF ${view.encounterCount}</span><h3>${e(encounter?.label ?? view.encounterName)}</h3><p>${e(encounter?.description ?? 'Defeat every enemy to advance. Scout the surfaces and watch your energy.')}</p><button class="primary" id="enter-battle" ${view.partyCount !== view.partyCapacity ? 'disabled' : ''}>Enter encounter <span aria-hidden="true">→</span></button>${view.partyCount !== view.partyCapacity ? `<p class="small">Deploy exactly ${view.partyCapacity} crawlers to enter.</p>` : ''}</div><p class="camp-note">Camp restores your crawlers. Classes can change freely here. Consumables carry through the run.</p></div></aside></div>
  <section class="panel inventory-strip"><h3>SHARED SUPPLIES</h3><div class="tags">${view.items.map(i => `<span class="tag">${e(i.label)} ×${i.count}</span>`).join('') || '<span class="small muted">No consumables remaining.</span>'}</div></section>${view.message ? `<div class="board-message" role="status">${e(view.message)}</div>` : ''}</section>`;
}
function renderBattle() {
  const selected = unit();
  const remaining = view.units.filter(u => u.team === 'player' && u.hp > 0 && !u.acted).length;
  return `<section aria-labelledby="screen-title"><div class="screen-heading"><div><h2 id="screen-title">${e(view.encounterName)}</h2><p>Defeat every hostile. Keep your crawlers standing.</p></div><div class="status-group"><span class="round-status"><i class="status-dot"></i>YOUR TURN / ROUND ${String(view.round).padStart(2, '0')}</span><span class="tag">ENCOUNTER ${view.encounterIndex + 1} / ${view.encounterCount}</span></div></div><div class="battle-layout"><aside class="panel party-panel"><div class="panel-head"><h3>YOUR CRAWLERS</h3><span class="small muted">${remaining} ready</span></div><div class="party-list">${view.units.filter(u => u.team === 'player').map(u => `<button class="unit-row${u.selected ? ' active' : ''}" data-unit="${e(u.id)}" ${u.hp <= 0 ? 'disabled' : ''} aria-pressed="${u.selected}">${portrait(u)}<span><strong>${e(u.label)}</strong><small>${e(classLabel(u.classId))}</small>${hpBar(u)}<span class="unit-stats"><span>${u.hp} / ${u.maxHp} HP</span><span>${u.energy} EN</span></span><span class="unit-stats">${u.hp <= 0 ? 'FALLEN' : u.acted ? 'ACTION SPENT' : u.moved ? 'READY TO ACT' : 'MOVE + ACT'}</span></span></button>`).join('')}</div><div class="rules-strip"><strong>Any crawler. Any order.</strong><br>Move once, then use one action.<br>Acting ends that crawler’s activation.<br>Forecast first. Confirm when ready.</div></aside><div class="board-column"><div class="map-top"><span>FLOOR 01 / ${e(view.encounterName.toUpperCase())}</span><span>${view.width} × ${view.height}</span></div>${renderBoard()}<div class="legend"><span><i></i>MOVE RANGE</span><span><i class="oil"></i>OIL</span><span><i class="wet"></i>WET</span><span><i class="frozen"></i>FROST</span></div><div class="board-message" role="status">${e(view.message || 'Select a crawler. Blue tiles are reachable; choose an action to target.')}</div></div><aside class="panel inspector-panel"><div class="panel-head"><h3>${e(selected?.label.toUpperCase() ?? 'SELECT A CRAWLER')}</h3><span class="tag ${view.canAct ? 'gold' : ''}">${selected?.acted ? 'SPENT' : 'READY'}</span></div><div class="panel-body inspector">${renderInspector(selected)}</div></aside></div><div class="turn-bar"><div class="turn-info"><strong>${remaining} CRAWLER${remaining === 1 ? '' : 'S'} READY</strong>Enemies act after you end the party turn.</div><div class="button-row"><button id="wait-button" ${!view.canAct ? 'disabled' : ''}>Wait crawler</button><button id="end-turn" class="primary">End party turn <span aria-hidden="true">→</span></button></div></div>${renderLog()}</section>`;
}
function renderBoard() {
  const action = selectedAction();
  const reachable = new Set(view.reachable.map(t => `${t.x},${t.y}`));
  const rows = [];
  const tileMap = new Map(view.tiles.map(t => [`${t.x},${t.y}`, t]));
  const units = new Map(view.units.filter(u => u.hp > 0).map(u => [`${u.x},${u.y}`, u]));
  for (let y = 0; y < view.height; y++) for (let x = 0; x < view.width; x++) {
    const t = tileMap.get(`${x},${y}`) ?? { id: `tile.${x}.${y}`, tags: [], blocked: false, x, y };
    const u = units.get(`${x},${y}`);
    const isTarget = localAction && action && (action.target === 'tile' || targetTile || u && (action.target === 'ally' ? u.team === 'player' : action.target === 'enemy' ? u.team === 'enemy' : u.id === view.selectedUnitId));
    const coord = `${String.fromCharCode(65 + x)}${y + 1}`;
    rows.push(`<button class="tile${t.blocked ? ' blocked' : ''}${t.tags.some(t => /oil/.test(t)) ? ' oil' : ''}${t.tags.some(t => /wet/.test(t)) ? ' wet' : ''}${t.tags.some(t => /frozen|frost/.test(t)) ? ' frozen' : ''}${t.tags.some(t => /burning/.test(t)) ? ' burning' : ''}${!localAction && reachable.has(`${x},${y}`) ? ' reachable' : ''}${u?.selected ? ' selected' : ''}${u?.team === 'enemy' ? ' enemy' : ''}${isTarget ? ' valid-target' : ''}${inspectedTile?.id === t.id ? ' targeted' : ''}" data-cell="${x},${y}" aria-label="${e(`${coord}: ${t.blocked ? 'blocked wall' : t.tags.map(shortTag).join(', ') || 'stone floor'}${u ? ', ' + u.label + ', ' + u.hp + ' HP, ' + u.team : ''}${!localAction && reachable.has(`${x},${y}`) ? ', reachable' : ''}`)}"><span class="coord">${coord}</span>${u ? `${portrait(u, 'tile-portrait')}<span class="unit-label">${e(u.label.toUpperCase())}</span><span class="tile-health"><span style="width:${u.hp / u.maxHp * 100}%"></span></span>${u.acted && u.team === 'player' ? '<span class="action-spent" aria-hidden="true">✓</span>' : ''}` : ''}</button>`);
  }
  return `<div class="board" style="--columns:${view.width};--rows:${view.height}" role="group" aria-label="Tactical battle map. Click a crawler to select, or a highlighted tile to move.">${rows.join('')}</div>`;
}
function renderInspector(selected) {
  const action = selectedAction();
  const targetText = !localAction ? view.canMove ? 'Click a blue outlined tile to move.' : 'Choose another crawler, or end the party turn.' : action?.target === 'self' ? 'Forecast targets this crawler.' : `Select ${targetTile || action?.target === 'tile' ? 'a terrain tile' : action?.target === 'ally' ? 'an allied crawler' : 'an enemy'} to forecast ${action?.label ?? 'the action'}.`;
  return `<div><p class="selected-subtitle">${e(classLabel(selected?.classId))} · ${selected?.energy ?? 0} / ${selected?.maxEnergy ?? 0} ENERGY</p><div class="budget-row"><span class="budget${selected?.moved ? ' spent' : ''}">${selected?.moved ? '✓ MOVE SPENT' : '◇ MOVE READY'}</span><span class="budget${selected?.acted ? ' spent' : ''}">${selected?.acted ? '✓ ACTION SPENT' : '◇ ACTION READY'}</span></div><div class="tags" style="margin-bottom:12px">${tags(selected?.tags)}</div><span class="section-label">ABILITIES / 1 ACTION EACH</span><div class="action-list">${view.abilities.map(a => `<button data-ability="${e(a.id)}" class="${localAction?.abilityId === a.id ? 'active' : ''}" ${!a.enabled ? 'disabled' : ''} title="${e(a.description)}"><strong>${e(a.label)}</strong><small>${a.cost} ENERGY · RANGE ${a.range}</small></button>`).join('')}</div><div class="mode-row"><button id="move-mode" class="${!localAction ? 'active' : ''}" ${!view.canMove && !localAction ? 'disabled' : ''}>${localAction ? 'Cancel targeting' : 'Move crawler'}</button></div><details class="consumables" ${localAction?.itemId ? 'open' : ''}><summary class="section-label">SHARED CONSUMABLES <span>${view.items.reduce((sum, i) => sum + i.count, 0)} charges</span></summary><div class="action-list">${view.items.map(i => `<button data-item="${e(i.id)}" class="${localAction?.itemId === i.id ? 'active' : ''}" ${i.count <= 0 || !view.canAct ? 'disabled' : ''} title="${e(i.label)} · ${i.target} · range ${i.range}"><strong>${e(i.label)} ×${i.count}</strong><small>1 ACTION · RANGE ${i.range}</small></button>`).join('') || '<span class="small muted">None remaining</span>'}</div></details><p class="target-help">${e(targetText)}</p></div><div class="forecast"><h3>${view.canConfirm ? 'ACTION FORECAST' : 'FORECAST'}</h3>${view.canConfirm ? `${view.forecast.filter(f => f.beforeHp !== f.afterHp || f.beforeEnergy !== f.afterEnergy || JSON.stringify(f.beforeTags) !== JSON.stringify(f.afterTags)).map(f => `<div class="forecast-target"><strong>${e(f.label)}</strong>${f.beforeHp !== f.afterHp ? `<div class="forecast-number"><span>Health</span><b>${f.beforeHp} → ${f.afterHp}</b></div>` : ''}${f.beforeEnergy !== f.afterEnergy ? `<div class="forecast-number"><span>Energy</span><b>${f.beforeEnergy} → ${f.afterEnergy}</b></div>` : ''}<div class="tags">${f.afterTags.filter(t => !f.beforeTags.includes(t)).map(t => `<span class="tag ${tagClass(t)}">+ ${e(shortTag(t))}</span>`).join('')}${f.beforeTags.filter(t => !f.afterTags.includes(t)).map(t => `<span class="tag">− ${e(shortTag(t))}</span>`).join('')}</div></div>`).join('') || '<p class="forecast-empty">No numeric change. This action may still alter a surface or status.</p>'}<ol class="forecast-chain">${view.log.filter(l => l.startsWith('Forecast:')).slice(-5).map(l => `<li>${e(displayLog(l.slice(10)))}</li>`).join('')}</ol><div class="button-row"><button id="cancel-forecast">Cancel <span class="key">Esc</span></button><button id="confirm-forecast" class="primary">Confirm</button></div><p class="small muted" style="margin-top:9px">Exact C# result. Confirm spends the action.</p>` : `<p class="forecast-empty">Choose an ability or consumable, then click a valid target. Review the result here before you commit.</p><div class="tags" style="margin-top:15px"><span class="tag fire">FIRE + OIL</span><span class="tag water">ARC + WET</span><span class="tag frost">IMPACT + FROZEN</span></div>${localAction ? '<button class="quiet full" id="cancel-forecast" style="margin-top:15px">Cancel targeting <span class="key">Esc</span></button>' : ''}`}</div>${inspectedTile ? `<div class="inspect-tile"><strong>${String.fromCharCode(65 + inspectedTile.x)}${inspectedTile.y + 1} · ${inspectedTile.blocked ? 'Blocked wall' : 'Terrain'}</strong><div class="tags">${tags(inspectedTile.tags) || '<span class="small muted">Stone · no surface tags</span>'}</div></div>` : ''}`;
}
function renderLog() {
  return `<details class="log" ${view.canConfirm ? 'open' : ''}><summary>COMBAT LOG / ${view.log.length} EVENTS</summary><div class="log-lines">${view.log.slice(-24).map(l => `<p>${e(displayLog(l))}</p>`).join('') || '<p>No actions yet.</p>'}</div></details>`;
}
function renderSurvivors() {
  return `<div class="outcome-party">${view.roster.filter(r => r.selected).map(r => `<div class="survivor">${portrait(r)}<span><strong>${e(r.label)}</strong><small>${e(classLabel(r.classId))} · ${r.hp} / ${r.maxHp} HP</small></span></div>`).join('')}</div>`;
}
function renderVictory() {
  return `<section class="outcome-layout" aria-labelledby="screen-title"><div class="outcome-header"><div><h2 id="screen-title">Room cleared. Cameras rolling.</h2><p>${e(view.encounterName)} · Encounter ${view.encounterIndex + 1} complete</p></div><div class="xp-value">${view.xp} XP<small>TOTAL RUN EXPERIENCE</small></div></div><div class="reward-layout"><div><span class="section-label">${view.rewards.length ? 'PICK ONE SPONSOR REWARD' : 'SPONSOR REWARD CLAIMED'}</span><div class="reward-list">${view.rewards.map((r, i) => `<button data-reward="${e(r.id)}" class="reward-button" ${chosenReward ? 'disabled' : ''}><span class="reward-icon" aria-hidden="true">${['◇', '▱', '✦'][i % 3]}</span><span><strong>${e(r.label)}</strong><small>${e(r.description)}</small></span></button>`).join('') || '<div class="panel panel-body"><span class="tag good">DELIVERY RECEIVED</span><p class="small muted" style="margin-top:12px">Your sponsor reward is in the shared supplies. Ready for the next room.</p></div>'}</div></div><aside class="panel sponsor-copy"><h3>SPONSOR TRANSMISSION</h3><blockquote>“A surprising number of you are still alive. We’ve sent a little something.”</blockquote><p>${e(view.message || (view.rewards.length ? 'Choose a reward for your party, then head to camp before the next encounter.' : 'Delivery received. Continue when you’re ready.'))}</p><button id="continue-button" class="primary" ${view.rewards.length ? 'disabled' : ''}>${view.encounterIndex + 1 >= view.encounterCount ? 'Finish the floor' : 'Return to camp'} <span aria-hidden="true">→</span></button><p class="small">One reward per encounter. Your run saves automatically.</p></aside></div>${renderSurvivors()}${renderLog()}</section>`;
}
function renderEnding() {
  const complete = view.screen === 'complete';
  return `<section class="outcome-layout" aria-labelledby="screen-title"><div class="center-outcome"><div class="trophy" aria-hidden="true">${complete ? '♜' : '†'}</div><h2 id="screen-title">${complete ? 'The floor is yours.' : 'The dungeon wins. For now.'}</h2><p>${complete ? `All three encounters cleared. Your crawlers earned ${view.xp} XP, exploited the elements, and made it back in one piece. The audience will want a sequel.` : 'Your deployed crawlers have fallen. Retry the encounter with the same starting party and supplies, or rebuild from the beginning.'}</p><div class="tags" style="justify-content:center"><span class="tag gold">${complete ? 'FLOOR 01 COMPLETE' : 'PARTY DEFEATED'}</span><span class="tag">${view.xp} XP EARNED</span></div><div class="button-row">${!complete ? '<button class="primary" id="retry-button">Retry encounter</button>' : ''}<button id="ending-new-run" ${complete ? 'class="primary"' : ''}>Start a new run</button></div><button class="quiet" id="ending-export">Export this run</button></div>${renderSurvivors()}${renderLog()}</section>`;
}
function bindScreen() {
  document.querySelectorAll('[data-roster]').forEach(b => b.addEventListener('click', () => { focusedRoster = b.dataset.roster; render(); }));
  $('#class-select')?.addEventListener('change', event => command('set_class', { unitId: focusedRoster, classId: event.target.value }));
  $('#toggle-party')?.addEventListener('click', () => command('toggle_party', { unitId: focusedRoster }));
  $('#enter-battle')?.addEventListener('click', () => command('start'));
  document.querySelectorAll('[data-unit]').forEach(b => b.addEventListener('click', () => { targetTile = false; command('select', { unitId: b.dataset.unit }); }));
  document.querySelectorAll('[data-cell]').forEach(b => b.addEventListener('click', () => clickCell(...b.dataset.cell.split(',').map(Number))));
  document.querySelectorAll('[data-ability]').forEach(b => b.addEventListener('click', () => chooseAction({ abilityId: b.dataset.ability })));
  document.querySelectorAll('[data-item]').forEach(b => b.addEventListener('click', () => chooseAction({ itemId: b.dataset.item })));
  $('#move-mode')?.addEventListener('click', () => { targetTile = false; command('cancel'); });
  $('#terrain-mode')?.addEventListener('click', () => { targetTile = !targetTile; render(); });
  $('#cancel-forecast')?.addEventListener('click', cancelTargeting);
  $('#confirm-forecast')?.addEventListener('click', () => command('confirm'));
  $('#wait-button')?.addEventListener('click', () => command('wait'));
  $('#end-turn')?.addEventListener('click', () => command('end_turn'));
  document.querySelectorAll('[data-reward]').forEach(b => b.addEventListener('click', () => command('choose_reward', { rewardId: b.dataset.reward })));
  $('#continue-button')?.addEventListener('click', () => command('continue'));
  $('#retry-button')?.addEventListener('click', () => command('retry'));
  $('#ending-new-run')?.addEventListener('click', () => openDialog('#restart-dialog'));
  $('#ending-export')?.addEventListener('click', exportSave);
}
async function chooseAction(action) {
  if (busy) return;
  if (view.canConfirm) await command('cancel', {}, { save: false });
  localAction = action;
  targetTile = false;
  if (selectedAction()?.target === 'self') {
    await command('preview', { ...localAction, targetId: view.selectedUnitId }, { preserveAction: true, save: false });
  } else render();
}
async function clickCell(x, y) {
  if (busy) return;
  inspectedTile = view.tiles.find(t => t.x === x && t.y === y);
  const occupant = view.units.find(u => u.x === x && u.y === y && u.hp > 0);
  const action = selectedAction();
  if (localAction && action) {
    const targetId = targetTile || action.target === 'tile' ? inspectedTile?.id ?? `tile.${x}.${y}` : occupant?.id;
    if (!targetId) { toast('This action needs a unit target. Choose a valid crawler or enemy. Use a terrain ability to target a surface.'); render(); return; }
    await command('preview', { ...localAction, targetId }, { preserveAction: true, save: false });
  } else if (occupant?.team === 'player') {
    await command('select', { unitId: occupant.id });
  } else if (!occupant && view.reachable.some(c => c.x === x && c.y === y)) {
    await command('move', { x, y });
  } else {
    render();
    if (occupant?.team === 'enemy') toast(`${occupant.label}: ${occupant.hp} / ${occupant.maxHp} HP. Choose an ability, then click this enemy.`);
  }
}
async function cancelTargeting() { targetTile = false; await command('cancel', {}, { save: false }); }
async function exportSave() {
  try {
    const data = await call('GetSave');
    const blob = new Blob([JSON.stringify(JSON.parse(data), null, 2)], { type: 'application/json' });
    const a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = 'dungeon-crawler-tactics-save.json';
    a.click();
    setTimeout(() => URL.revokeObjectURL(a.href), 1000);
    toast('Save file exported.');
  } catch (error) { $('#save-error').textContent = `Could not export save: ${error.message}`; }
}
async function loadSerializedSave(serialized) {
  const result = await call('LoadSave', serialized);
  const nextView = JSON.parse(result);
  if (nextView.message?.startsWith('Save rejected:')) throw new Error(nextView.message.slice(15));
  view = nextView;
  localAction = null;
  inspectedTile = null;
  focusedRoster = null;
  chosenReward = JSON.parse(serialized).rewardChosen === true;
  render();
  await persist();
}
async function boot() {
  try {
    await Blazor.start();
    $('#boot-status').textContent = 'Loading your party and the first floor…';
    const responses = await Promise.all([fetch('data/combat-content.json'), fetch('data/game-content.json')]);
    if (responses.some(r => !r.ok)) throw new Error('The game content could not be loaded. Serve this folder over HTTP; opening index.html directly is unsupported.');
    const [combatJson, gameJson] = await Promise.all(responses.map(r => r.text()));
    content = JSON.parse(combatJson);
    gameData = JSON.parse(gameJson);
    view = JSON.parse(await call('Initialize', combatJson, gameJson));
    let saved;
    try { saved = localStorage.getItem(saveKey); } catch { /* Export remains available. */ }
    if (saved) {
      try { await loadSerializedSave(saved); toast('Your run has been restored.'); }
      catch (error) { render(); toast('Your stored save could not be restored. A new party is ready; the stored file has been preserved.'); $('#save-status').textContent = 'Stored save invalid · import or start fresh'; }
    } else {
      render();
      await persist();
      openDialog('#welcome-dialog');
    }
    $('#game').setAttribute('aria-busy', 'false');
    window.dungeon = { command, getView: () => view, getSave: () => call('GetSave'), loadSave: loadSerializedSave };
  } catch (error) {
    $('#game').innerHTML = `<section class="fatal"><h1>The dungeon couldn’t load.</h1><p>The C# runtime or game content did not finish loading. Check your connection and reload the page.</p><pre>${e(error.message)}</pre><button class="primary" onclick="location.reload()">Try again</button></section>`;
    $('#game').setAttribute('aria-busy', 'false');
    console.error(error);
  }
}
$('#help-button').addEventListener('click', () => openDialog('#help-dialog'));
$('#save-button').addEventListener('click', () => { $('#save-error').textContent = ''; openDialog('#save-dialog'); });
$('#begin-button').addEventListener('click', () => { closeDialog('#welcome-dialog'); openDialog('#help-dialog'); });
document.querySelectorAll('[data-close]').forEach(b => b.addEventListener('click', () => closeDialog(`#${b.dataset.close}`)));
$('#export-button').addEventListener('click', exportSave);
$('#import-file').addEventListener('change', async event => {
  const file = event.target.files[0];
  if (!file) return;
  try {
    if (file.size > 2_000_000) throw new Error('Save files must be smaller than 2 MB.');
    await loadSerializedSave(await file.text());
    closeDialog('#save-dialog');
    toast('Save imported. Your run is ready.');
  } catch (error) { $('#save-error').textContent = `Could not import save: ${error.message}`; }
  event.target.value = '';
});
$('#reload-save-button').addEventListener('click', async () => {
  try {
    const serialized = localStorage.getItem(saveKey);
    if (!serialized) throw new Error('No local save was found.');
    await loadSerializedSave(serialized);
    closeDialog('#save-dialog');
    toast('Local save restored.');
  } catch (error) { $('#save-error').textContent = `Could not reload save: ${error.message}`; }
});
$('#restart-button').addEventListener('click', () => { closeDialog('#save-dialog'); openDialog('#restart-dialog'); });
$('#confirm-restart').addEventListener('click', async () => { closeDialog('#restart-dialog'); focusedRoster = null; await command('new_run'); });
document.addEventListener('keydown', event => {
  if (event.key === '?' && !event.ctrlKey && !event.metaKey && !['INPUT', 'SELECT', 'TEXTAREA'].includes(document.activeElement?.tagName)) { event.preventDefault(); openDialog('#help-dialog'); }
  if (event.key === 'Escape' && !document.querySelector('dialog[open]') && view?.screen === 'battle') cancelTargeting();
});
boot();
