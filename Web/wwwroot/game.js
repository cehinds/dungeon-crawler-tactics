import { notify, syncFeedbackHost } from './feedback.js';
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
let chosenReward = false;
let drawer = null;
let drawerReturn = null;
let battleReturn = null;
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

function abilityDescription(a) {
  if (!a) return '';
  const label = id => shortTag(id).toLowerCase().replace(/\b\w/g, c => c.toUpperCase());
  const effects = (a.effects ?? []).map(x => {
    if (x.op === 'Damage') return `Deal ${x.amount} damage`;
    if (x.op === 'Heal') return `Restore ${x.amount} HP`;
    const protection = content.reactions?.find(r => r.damageReduction > 0 && r.consumeTags?.includes(x.tag));
    return `${x.op === 'AddTag' ? 'Apply' : 'Remove'} ${label(x.tag)}${x.op === 'AddTag' && protection ? ` (prevents ${protection.damageReduction} damage from the next matching hit)` : ''}`;
  });
  return effects.join(' · ') || `Trigger ${(a.incomingTags ?? []).map(label).join(', ') || 'elemental'} reactions on ${a.target === 'tile' ? 'terrain' : 'the target'}`;
}
function toast(message, severity = 'info') { notify(message, severity); }
function openDialog(id) {
  const dialog=$(id);
  if (!dialog.dataset.focusManaged) {
    dialog.dataset.focusManaged = 'true';
    dialog.addEventListener('keydown', event => {
      if (event.key !== 'Tab') return;
      const controls = [...dialog.querySelectorAll('button:not(:disabled),a[href],input:not([hidden]):not(:disabled),select:not(:disabled),[tabindex="0"]')].filter(control => control.getClientRects().length);
      const first=controls[0], last=controls[controls.length-1];
      if (event.shiftKey && document.activeElement === first) {event.preventDefault();last?.focus();}
      else if (!event.shiftKey && document.activeElement === last) {event.preventDefault();first?.focus();}
    });
  }
  if (!dialog.open) dialog.showModal();
  syncFeedbackHost();
}
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
    const before = view;
    const result = await call('Dispatch', JSON.stringify({ type, ...args }));
    view = JSON.parse(result);
    if (!preserveAction) { localAction = null; inspectedTile = null; targetTile = false; }
    if (type === 'choose_reward' && previousScreen === 'victory') chosenReward = view.rewards.length === 0;
    if (type === 'continue' || type === 'start' || type === 'new_run' || type === 'retry') {
      chosenReward = false;
      inspectedTile = null;
    }
    if (save && type !== 'preview' && type !== 'cancel') await persist();
    busy = false;
    render();
    if (before.canConfirm && !view.canConfirm && battleReturn) $(battleReturn)?.focus();
    commandFeedback(type, args, before, view);
  } catch (error) {
    toast(`The command could not be completed: ${error.message}`, 'error');
  } finally {
    busy = false;
    $('#game').setAttribute('aria-busy', 'false');
  }
}
function commandFeedback(type, args, before, after) {
  const beforeClass = before.roster.find(r => r.id === args.unitId);
  const afterClass = after.roster.find(r => r.id === args.unitId);
  if (type === 'set_class' && beforeClass?.classId !== afterClass?.classId) {
    toast(`${afterClass.label} is now a ${classLabel(afterClass.classId)}.`, 'success'); return;
  }
  if (type === 'choose_reward' && before.rewards.length > after.rewards.length) {
    const reward = before.rewards.find(r => r.id === args.rewardId);
    toast(`${reward?.label ?? 'Sponsor reward'} claimed.`, 'success'); return;
  }
  if (type === 'explore_interact') {
    const point = after.exploration?.points.find(p => p.id === args.targetId);
    const previous = before.exploration?.points.find(p => p.id === args.targetId);
    if (point?.claimed && !previous?.claimed) {
      const loot = after.items.filter(i => i.count > (before.items.find(old => old.id === i.id)?.count ?? 0)).map(i => `+${i.count - (before.items.find(old => old.id === i.id)?.count ?? 0)} ${i.label}`).join(', ');
      toast(loot || `${point.label} discovered.`, 'success'); return;
    }
  }
  const signature = state => JSON.stringify([state.screen,state.units,state.roster,state.items.map(i => [i.id,i.count]),state.round,state.xp,state.exploration]);
  const changed = signature(before) !== signature(after);
  if (type === 'confirm' && before.canConfirm && changed) {
    toast(after.screen === 'victory' ? 'Room cleared. Choose your sponsor reward.' : 'Action confirmed.', 'success'); return;
  }
  // Core returns rejected commands as a message rather than a thrown exception.
  // A changed presentation message with unchanged game state is not a successful action.
  if (!changed && after.message && before.message !== after.message && !['select','cancel'].includes(type) && !(type === 'preview' && after.canConfirm)) toast(after.message, 'warning');
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
  if (view.screen !== 'battle') drawer = null;
  document.body.dataset.screen = view.screen;
  $('#game').innerHTML = view.screen === 'camp' ? renderCamp() : view.screen === 'explore' ? renderExploration() : view.screen === 'battle' ? renderBattle() : view.screen === 'victory' ? renderVictory() : renderEnding();
  bindScreen();
  window.dungeonView = view;
}
function renderCamp() {
  const focused = view.roster.find(r => r.id === focusedRoster) ?? view.roster.find(r => r.selected) ?? view.roster[0];
  focusedRoster = focused?.id;
  const focusClass = view.classes.find(c => c.id === focused?.classId);
  const encounter = gameData.encounters[view.encounterIndex];
  return `<section class="camp-screen" aria-labelledby="screen-title"><div class="screen-heading"><div><h2 id="screen-title">A little preparation. A little mayhem.</h2><p>Choose ${view.partyCapacity} crawlers and their classes. The next room won’t clear itself.</p></div><div class="status-group"><span class="tag gold">CAMP / FLOOR 01</span><span class="small muted mono">${view.xp} XP EARNED</span></div></div>
  <div class="camp-layout"><section class="panel"><div class="panel-head"><h3>YOUR ROSTER</h3><span class="small mono ${view.partyCount === view.partyCapacity ? '' : 'muted'}">${view.partyCount} / ${view.partyCapacity} DEPLOYED</span></div><div class="roster-grid">${view.roster.map(r => `<button class="roster-card${r.selected ? ' chosen' : ''}${r.id === focused.id ? ' focused' : ''}" data-roster="${e(r.id)}" aria-pressed="${r.id === focused.id}">${portrait(r)}<span><strong>${e(r.label)}</strong><small>${e(classLabel(r.classId))}</small><small>${r.selected ? 'DEPLOYED' : 'RESERVE'} · ${r.hp} / ${r.maxHp} HP</small></span><span class="choice-marker" aria-hidden="true">${r.selected ? '✓' : ''}</span></button>`).join('')}</div><div class="roster-bottom"><span>Select a crawler to edit their class or deployment.</span><span class="mono">${view.roster.length} CRAWLERS · ${view.classes.length} CLASSES</span></div></section>
  <aside class="panel"><div class="panel-body"><div class="loadout-head">${portrait(focused)}<div><h2>${e(focused.label)}</h2><p>${focused.selected ? 'Deployed for the next encounter' : 'Resting in reserve'}</p><div class="tags" style="margin-top:8px"><span class="tag good">${focused.hp} / ${focused.maxHp} HP</span></div></div></div><label class="field" for="class-select">ACTIVE CLASS<select id="class-select">${view.classes.map(c => `<option value="${e(c.id)}" ${c.id === focused.classId ? 'selected' : ''}>${e(c.label)}</option>`).join('')}</select></label><div class="class-abilities">${(focusClass?.abilityIds ?? []).map(id => `<span><strong>${e(content.abilities.find(a => a.id === id)?.label ?? id)}</strong><small>${e(abilityDescription(content.abilities.find(a => a.id === id)))}</small></span>`).join('')}</div><button class="camp-party-toggle" id="toggle-party">${focused.selected ? 'Move to reserve' : 'Deploy this crawler'}</button><div class="encounter-brief"><span class="section-label">NEXT / ENCOUNTER ${view.encounterIndex + 1} OF ${view.encounterCount}</span><h3>${e(encounter?.label ?? view.encounterName)}</h3><p>${e(encounter?.description ?? 'Defeat every enemy to advance. Scout the surfaces and watch your energy.')}</p><button class="primary" id="enter-battle" ${view.partyCount !== view.partyCapacity ? 'disabled' : ''}>Explore the dungeon <span aria-hidden="true">→</span></button>${view.partyCount !== view.partyCapacity ? `<p class="small">Deploy exactly ${view.partyCapacity} crawlers to enter.</p>` : ''}</div><p class="camp-note">Camp restores your crawlers. Classes can change freely here. Consumables carry through the run.</p></div></aside></div>
  <details class="panel inventory-strip"><summary>SHARED SUPPLIES</summary><div class="tags">${view.items.map(i => `<span class="tag">${e(i.label)} ×${i.count}</span>`).join('') || '<span class="small muted">No consumables remaining.</span>'}</div></details>${view.message ? `<div class="board-message" role="status">${e(view.message)}</div>` : ''}</section>`;
}
function renderParty() {
  return `<div class="party-strip" style="--party-columns:${Math.min(4,view.units.filter(u => u.team === 'player').length)}" aria-label="Select a crawler">${view.units.filter(u => u.team === 'player').map(u => `<button class="party-chip${u.selected ? ' active' : ''}" data-unit="${e(u.id)}" ${u.hp <= 0 ? 'disabled' : ''} aria-pressed="${u.selected}">${portrait(u)}<span><strong>${e(u.label)}</strong><small class="party-class">${e(classLabel(u.classId))}</small><small class="party-vitals">${u.hp} HP · ${u.energy} EN</small><small class="party-budget">${u.hp <= 0 ? 'Fallen' : u.acted ? 'Activation spent' : u.moved ? 'Move spent · ability ready' : 'Move + ability ready'}</small></span></button>`).join('')}</div>`;
}
function renderBattle() {
  const selected = unit();
  return `<section class="battle-screen" aria-labelledby="screen-title"><div class="battle-heading"><h2 id="screen-title">${e(view.encounterName)}</h2><span class="round-status">ROUND ${view.round} · YOUR TURN</span><button data-drawer="log">Log</button></div>${renderParty()}<div class="battle-stage"><div class="playfield">${renderBoard()}<div class="battle-hint" role="status">${e(view.message || 'Select a crawler → Move or ability → highlighted target → confirm.')}</div></div><section class="action-dock" aria-label="Crawler actions and forecast">${renderInspector(selected)}</section></div><div class="battle-turn"><span>${view.units.filter(u => u.team === 'player' && u.hp > 0 && !u.acted).length} ready · Enemies act when the party ends its turn</span><button id="wait-button" ${!view.canAct ? 'disabled' : ''}>Wait crawler</button><button id="end-turn" class="primary">End party turn →</button></div>${renderDrawer()}${renderForecastDialog()}</section>`;
}
function renderDrawer() {
  if (!drawer) return '';
  return `<dialog class="drawer-backdrop" id="game-drawer-dialog"><section class="game-drawer" aria-label="${drawer === 'items' ? 'Shared supplies' : 'Combat log'}"><div class="dialog-head"><h2>${drawer === 'items' ? 'Shared supplies' : 'Combat log'}</h2><button id="close-drawer" aria-label="Close drawer">×</button></div>${drawer === 'items' ? `<p class="small muted">Using a supply spends this crawler’s action.</p><div class="action-list">${view.items.map(i => `<button data-item="${e(i.id)}" ${i.count <= 0 || !view.canAct ? 'disabled' : ''}><strong>${e(i.label)} ×${i.count}</strong><small>${e(i.description || 'Target: ' + i.target)} · range ${i.range}</small></button>`).join('')}</div>` : `<div class="log-lines">${view.log.slice(-30).map(l => `<p>${e(displayLog(l))}</p>`).join('')}</div>`}</section></dialog>`;
}
function closeDrawer() {
  const selector = drawerReturn;
  drawer = null; render();
  if (selector) $(selector)?.focus();
}
function renderExploration() {
  const map = view.exploration;
  if (!map) return '<p>Preparing exploration…</p>';
  return `<section class="exploration-screen"><div class="battle-heading"><h2>${e(map.label)}</h2><button id="return-camp">Return to camp</button></div><p class="explore-description">${e(map.description)}</p><div class="exploration-field"><div class="board exploration-board" style="--columns:${map.width};--rows:${map.height}" aria-label="Dungeon exploration map">${map.tiles.map(t => {
    const point = map.points.find(p => p.x === t.x && p.y === t.y);
    const here = map.x === t.x && map.y === t.y;
    return `<button class="tile${!t.revealed ? ' fog' : ''}${t.blocked ? ' blocked' : ''}${t.reachable ? ' reachable' : ''}${here ? ' selected' : ''}${point?.claimed ? ' claimed' : ''}" data-explore-cell="${t.x},${t.y}" ${!t.reachable || here ? 'disabled' : ''} aria-label="${e(here ? 'Your party' : !t.revealed ? 'Unexplored' : t.blocked ? 'Wall' : point?.label || 'Corridor')}">${here ? portrait(view.roster.find(r => r.selected) ?? {classId:'class.brawler'}, 'tile-portrait') : point ? `<span class="point-symbol">${point.kind === 'encounter' ? '⚔' : point.kind === 'cache' ? '◇' : '✦'}</span><span class="point-label">${e(point.label)}</span>` : !t.revealed ? '<span class="fog-mark">?</span>' : ''}</button>`;
  }).join('')}</div></div><div class="exploration-prompt" role="status"><p>${e(view.message || 'Click a highlighted tile to explore. Approach a landmark to interact.')}</p><div>${map.points.filter(p => p.canInteract && !p.claimed).map(p => `<button class="primary" data-explore-interact="${e(p.id)}">${p.kind === 'encounter' ? 'Enter' : 'Investigate'} ${e(p.label)}</button><small>${e(p.description)}</small>`).join('') || '<small>Click blue paths or use arrow keys / WASD to walk. Approach a landmark to interact.</small>'}</div></div></section>`;
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
    const isTarget = localAction && action && (action.targetIds ?? []).includes(action.target === 'tile' ? t.id : u?.id);
    const coord = `${String.fromCharCode(65 + x)}${y + 1}`;
    rows.push(`<button class="tile${t.blocked ? ' blocked' : ''}${t.tags.some(t => /oil/.test(t)) ? ' oil' : ''}${t.tags.some(t => /wet/.test(t)) ? ' wet' : ''}${t.tags.some(t => /frozen|frost/.test(t)) ? ' frozen' : ''}${t.tags.some(t => /burning/.test(t)) ? ' burning' : ''}${!localAction && reachable.has(`${x},${y}`) ? ' reachable' : ''}${u?.selected ? ' selected' : ''}${u?.team === 'enemy' ? ' enemy' : ''}${isTarget ? ' valid-target' : ''}${inspectedTile?.id === t.id ? ' targeted' : ''}" data-cell="${x},${y}" aria-label="${e(`${coord}: ${t.blocked ? 'blocked wall' : t.tags.map(shortTag).join(', ') || 'stone floor'}${u ? ', ' + u.label + ', ' + u.hp + ' HP, ' + u.team : ''}${!localAction && reachable.has(`${x},${y}`) ? ', reachable' : ''}`)}"><span class="coord">${coord}</span>${u ? `${portrait(u, 'tile-portrait')}<span class="unit-label">${e(u.label.toUpperCase())}</span><span class="tile-health"><span style="width:${u.hp / u.maxHp * 100}%"></span></span>${u.acted && u.team === 'player' ? '<span class="action-spent" aria-hidden="true">✓</span>' : ''}` : ''}</button>`);
  }
  return `<div class="board" style="--columns:${view.width};--rows:${view.height}" role="group" aria-label="Tactical battle map. Click a crawler to select, or a highlighted tile to move.">${rows.join('')}</div>`;
}
function renderInspector(selected) {
  const action = selectedAction();
  const info = view.classes.find(c => c.id === selected?.classId);
  const forecast = view.forecast.filter(f => f.beforeHp !== f.afterHp || f.beforeEnergy !== f.afterEnergy || JSON.stringify(f.beforeTags) !== JSON.stringify(f.afterTags));
  return `<div class="dock-identity"><strong>${e(selected?.label || 'Select a crawler')} <span>${e(classLabel(selected?.classId))}${info?.role ? ' · ' + e(info.role) : ''}</span></strong><small>${selected?.energy ?? 0} / ${selected?.maxEnergy ?? 0} energy · ${selected?.acted ? 'Activation spent' : selected?.moved ? 'Move spent · ability ready' : 'Move + ability ready'}</small>${info?.description ? `<small>${e(info.description)}</small>` : ''}</div><div class="dock-modes"><button id="move-mode" class="${!localAction ? 'active' : ''}" ${!view.canMove && !localAction ? 'disabled' : ''}>Move${selected?.moved ? ' · spent' : ''}</button><span>ABILITIES · 1 ACTION</span><button data-drawer="items">Supplies</button></div><div class="dock-abilities">${view.abilities.map(a => `<button data-ability="${e(a.id)}" class="${localAction?.abilityId === a.id ? 'active' : ''}" ${!a.enabled ? 'disabled' : ''}><strong>${e(a.label)} <small>${a.cost} EN · ${a.range} range</small></strong><span>${e(a.description)}${a.disabledReason ? ` · ${e(a.disabledReason)}` : ''}</span></button>`).join('')}</div><div class="dock-forecast" aria-live="polite"><strong>${view.canConfirm ? 'Confirm ' + e(action?.label || 'action') : localAction ? (action?.targetIds?.length ? 'Choose a highlighted ' + e(action?.target || 'target') : 'No legal targets in range · cancel to move') : view.canMove ? 'Move: choose a blue tile, or select an ability' : selected?.acted ? 'Choose another crawler or end the party turn' : 'Choose an ability'}</strong><div class="forecast-results">${view.canConfirm ? forecast.map(f => `<span><b>${e(f.label)}</b>${f.beforeHp !== f.afterHp ? ` HP ${f.beforeHp} → ${f.afterHp}` : ''}${f.beforeEnergy !== f.afterEnergy ? ` EN ${f.beforeEnergy} → ${f.afterEnergy}` : ''}${tags(f.afterTags.filter(t => !f.beforeTags.includes(t)))}${f.beforeTags.filter(t => !f.afterTags.includes(t)).map(t => `<small>−${e(shortTag(t))}</small>`).join('')}</span>`).join('') || '<span>Surface or status change. See log for details.</span>' : `<span>${e(localAction ? action?.description || 'Select a valid target. Nothing is spent until you confirm.' : 'Each crawler moves once and uses one ability. Acting ends their activation.')}</span>`}</div>${view.canConfirm ? '<button id="review-forecast">Review forecast</button>' : localAction ? '<div class="forecast-buttons"><button id="cancel-forecast">Cancel targeting <span class="key">Esc</span></button></div>' : ''}</div>`;
}
function renderForecastDialog() {
  if (!view.canConfirm) return '';
  const action = selectedAction();
  return `<dialog id="forecast-dialog" class="forecast-dialog" aria-labelledby="forecast-title"><div class="dialog-head"><div><span class="section-label">EXACT ACTION FORECAST</span><h2 id="forecast-title">${e(action?.label || 'Review action')}</h2></div><button class="icon-button" id="close-forecast" aria-label="Cancel forecast">×</button></div><div class="modal-body"><p class="modal-intro">${e(action?.description || 'Review the exact result before spending this crawler’s action.')}</p><div class="forecast-detail-list">${view.forecast.filter(f => f.beforeHp !== f.afterHp || f.beforeEnergy !== f.afterEnergy || JSON.stringify(f.beforeTags) !== JSON.stringify(f.afterTags)).map(f => `<section class="forecast-detail"><h3>${e(f.label)}</h3>${f.beforeHp !== f.afterHp ? `<div class="forecast-number"><span>Health</span><b>${f.beforeHp} → ${f.afterHp}</b></div>` : ''}${f.beforeEnergy !== f.afterEnergy ? `<div class="forecast-number"><span>Energy</span><b>${f.beforeEnergy} → ${f.afterEnergy}</b></div>` : ''}<div class="tags">${f.afterTags.filter(t => !f.beforeTags.includes(t)).map(t => `<span class="tag good">+ ${e(shortTag(t))}</span>`).join('')}${f.beforeTags.filter(t => !f.afterTags.includes(t)).map(t => `<span class="tag">− ${e(shortTag(t))}</span>`).join('')}</div></section>`).join('') || '<p>The action changes terrain or status without changing health or energy.</p>'}</div><ol class="forecast-chain">${view.log.filter(l => l.startsWith('Forecast:')).slice(-8).map(l => `<li>${e(displayLog(l.slice(10)))}</li>`).join('')}</ol><p class="small muted">Confirm spends the action and ends this crawler’s activation. Cancel spends nothing.</p></div><div class="modal-actions"><button id="cancel-forecast">Cancel <span class="key">Esc</span></button><button id="confirm-forecast" class="primary">Confirm action</button></div></dialog>`;
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
  document.querySelectorAll('.board').forEach(board => {
    const cells = [...board.querySelectorAll('button')];
    const entry = cells.find(cell => !cell.disabled && cell.classList.contains('selected')) ?? cells.find(cell => !cell.disabled);
    cells.forEach(cell => {
      cell.tabIndex = cell === entry ? 0 : -1;
      cell.addEventListener('keydown', event => {
        const movement = {ArrowLeft:[-1,0],ArrowRight:[1,0],ArrowUp:[0,-1],ArrowDown:[0,1]}[event.key];
        if (!movement) return;
        if (view.screen === 'explore') return;
        event.preventDefault();
        const attr = cell.dataset.cell !== undefined ? 'data-cell' : 'data-explore-cell';
        const [x,y] = cell.getAttribute(attr).split(',').map(Number);
        const next = board.querySelector(`[${attr}="${x+movement[0]},${y+movement[1]}"]`);
        if (next && !next.disabled) { cell.tabIndex=-1; next.tabIndex=0; next.focus(); }
      });
    });
  });
  document.querySelectorAll('[data-roster]').forEach(b => b.addEventListener('click', () => { focusedRoster = b.dataset.roster; render(); }));
  $('#class-select')?.addEventListener('change', event => command('set_class', { unitId: focusedRoster, classId: event.target.value }));
  $('#toggle-party')?.addEventListener('click', () => command('toggle_party', { unitId: focusedRoster }));
  document.querySelectorAll('[data-drawer]').forEach(b => b.addEventListener('click', () => { drawerReturn = `[data-drawer="${b.dataset.drawer}"]`; drawer = b.dataset.drawer; render(); }));
  $('#close-drawer')?.addEventListener('click', closeDrawer);
  const drawerDialog = $('#game-drawer-dialog');
  if (drawerDialog) { drawerDialog.showModal(); $('#close-drawer').focus(); drawerDialog.addEventListener('cancel', event => {event.preventDefault();closeDrawer();});
    drawerDialog.addEventListener('keydown', event => {
      if (event.key !== 'Tab') return;
      const focusable = [...drawerDialog.querySelectorAll('button:not(:disabled),a[href],input:not(:disabled),select:not(:disabled),[tabindex="0"]')];
      const first = focusable[0], last = focusable[focusable.length-1];
      if (event.shiftKey && document.activeElement === first) {event.preventDefault();last?.focus();}
      else if (!event.shiftKey && document.activeElement === last) {event.preventDefault();first?.focus();}
    }); }
  document.querySelectorAll('[data-explore-cell]').forEach(b => b.addEventListener('click', () => { const [x,y] = b.dataset.exploreCell.split(',').map(Number); command('explore_move', {x,y}); }));
  document.querySelectorAll('[data-explore-interact]').forEach(b => b.addEventListener('click', () => command('explore_interact', {targetId:b.dataset.exploreInteract})));
  $('#return-camp')?.addEventListener('click', () => command('return_camp'));
  $('#enter-battle')?.addEventListener('click', () => command('start'));
  document.querySelectorAll('[data-unit]').forEach(b => b.addEventListener('click', () => { targetTile = false; command('select', { unitId: b.dataset.unit }); }));
  document.querySelectorAll('[data-cell]').forEach(b => b.addEventListener('click', () => clickCell(...b.dataset.cell.split(',').map(Number))));
  document.querySelectorAll('[data-ability]').forEach(b => b.addEventListener('click', () => chooseAction({ abilityId: b.dataset.ability })));
  document.querySelectorAll('[data-item]').forEach(b => b.addEventListener('click', () => chooseAction({ itemId: b.dataset.item })));
  $('#move-mode')?.addEventListener('click', () => { targetTile = false; command('cancel'); });
  $('#terrain-mode')?.addEventListener('click', () => { targetTile = !targetTile; render(); });
  const forecastDialog = $('#forecast-dialog');
  if (forecastDialog) { openDialog('#forecast-dialog'); $('#cancel-forecast').focus(); forecastDialog.addEventListener('cancel', event => {event.preventDefault();cancelTargeting();}); }
  $('#review-forecast')?.addEventListener('click', () => openDialog('#forecast-dialog'));
  $('#close-forecast')?.addEventListener('click', cancelTargeting);
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
  drawer = null;
  battleReturn = action.itemId ? '[data-drawer="items"]' : `[data-ability="${action.abilityId}"]`;
  localAction = action;
  targetTile = false;
  if (selectedAction()?.target === 'self') {
    await command('preview', { ...localAction, targetId: view.selectedUnitId }, { preserveAction: true, save: false });
  } else render();
}
async function clickCell(x, y) {
  if (busy) return;
  battleReturn = `[data-cell="${x},${y}"]`;
  inspectedTile = view.tiles.find(t => t.x === x && t.y === y);
  const occupant = view.units.find(u => u.x === x && u.y === y && u.hp > 0);
  const action = selectedAction();
  if (localAction && action) {
    const targetId = targetTile || action.target === 'tile' ? inspectedTile?.id ?? `tile.${x}.${y}` : occupant?.id;
    if (!targetId || !(action.targetIds ?? []).includes(targetId)) { if (view.canConfirm) await command('cancel', {}, {preserveAction:true,save:false}); toast('This action needs a unit target. Choose a valid crawler or enemy. Use a terrain ability to target a surface.', 'warning'); render(); return; }
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
    toast('Save file exported.', 'success');
  } catch (error) { $('#save-error').textContent = `Could not export save: ${error.message}`; toast(`Could not export save: ${error.message}`, 'error'); }
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
      catch (error) { render(); toast('Your stored save could not be restored. A new party is ready; the stored file has been preserved.', 'warning'); $('#save-status').textContent = 'Stored save invalid · import or start fresh'; }
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
$('#import-button').addEventListener('click', () => $('#import-file').click());
$('#import-file').addEventListener('change', async event => {
  const file = event.target.files[0];
  if (!file) return;
  try {
    if (file.size > 2_000_000) throw new Error('Save files must be smaller than 2 MB.');
    await loadSerializedSave(await file.text());
    closeDialog('#save-dialog');
    toast('Save imported. Your run is ready.', 'success');
  } catch (error) { $('#save-error').textContent = `Could not import save: ${error.message}`; toast(`Could not import save: ${error.message}`, 'error'); }
  event.target.value = '';
});
$('#reload-save-button').addEventListener('click', async () => {
  try {
    const serialized = localStorage.getItem(saveKey);
    if (!serialized) throw new Error('No local save was found.');
    await loadSerializedSave(serialized);
    closeDialog('#save-dialog');
    toast('Local save restored.', 'success');
  } catch (error) { $('#save-error').textContent = `Could not reload save: ${error.message}`; toast(`Could not reload save: ${error.message}`, 'error'); }
});
$('#restart-button').addEventListener('click', () => { closeDialog('#save-dialog'); openDialog('#restart-dialog'); });
$('#confirm-restart').addEventListener('click', async () => { closeDialog('#restart-dialog'); focusedRoster = null; await command('new_run'); });
document.addEventListener('keydown', event => {
  if (view?.screen === 'explore' && !busy && !document.querySelector('dialog[open]') && !['INPUT','SELECT','TEXTAREA'].includes(document.activeElement?.tagName) && !event.ctrlKey && !event.metaKey && !event.altKey) {
    const direction = {ArrowLeft:[-1,0],a:[-1,0],ArrowRight:[1,0],d:[1,0],ArrowUp:[0,-1],w:[0,-1],ArrowDown:[0,1],s:[0,1]}[event.key];
    if (direction) { event.preventDefault(); const map = view.exploration; const x=map.x+direction[0], y=map.y+direction[1]; if (map.tiles.some(t => t.x===x && t.y===y && t.reachable)) command('explore_move',{x,y}); }
  }

  if (event.key === '?' && !document.querySelector('dialog[open]') && !event.ctrlKey && !event.metaKey && !['INPUT', 'SELECT', 'TEXTAREA'].includes(document.activeElement?.tagName)) { event.preventDefault(); openDialog('#help-dialog'); }
  if (event.key === 'Escape' && !document.querySelector('dialog[open]')) { if (drawer) { closeDrawer(); } else if (view?.screen === 'battle') cancelTargeting(); }
});
boot();
