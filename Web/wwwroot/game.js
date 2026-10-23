import { renderScenarioMenu, renderScenarioDetails } from './scenario-ui.js';
import { renderDevelopment, renderDevelopmentConfirmation } from './development-ui.js';
import { notify, syncFeedbackHost } from './feedback.js';
import { createBattlefield } from './battlefield.js';
import { renderAbilityDetails, renderCharacterSheet } from './character-ui.js';
import { createNarrator } from './narrator.js';
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
let previewTargetId = null;
let targetTile = false;
let chosenReward = false;
let drawer = null;
let drawerReturn = null;
let battleReturn = null;
let battlefield = null;
let battleCanvas = null;
let commandQueue = Promise.resolve();
let inputQueue = Promise.resolve();
let saveRevision = 0;
let fastForwardRequested = false;
let inspectPosition = null;
let pinnedInspection = null;
let pendingActionChoice = null;
let detailedForecast = false;
let actionChooser = false;
let endTurnActor = null;
let animating = false;
let campModal = null;
let developmentTab=null,developmentUnit=null,developmentPending=null;
let scenarioMenu=false,scenarioBriefing=null,scenarioDetails=false,scenarioInteraction=null;
let rosterExpanded=false;
let questModal = false;
let levelNotice = null;
let enemySequence = false;
let enemyPlayback = false;
let characterSheetId=null;
let sheetReturn=null;
let sheetOpenSection=null;
let abilityDetailsOpen=false;
let narrator=null;
let enemyPhaseName='resolving';
const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, (c) => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }[c]));
const e = escapeHtml;
const call = (method, ...args) => DotNet.invokeMethodAsync(assembly, method, ...args);
const classLabel = (id) => view?.classes.find(c => c.id === id)?.label ?? id?.replace('class.', '') ?? '';
const unit = () => view?.units.find(u => u.id === view.selectedUnitId);
const shortTag = (tag) => String(tag ?? '').replace(/^[^.]+\./, '').replace(/_/g, ' ').toUpperCase();
const tagClass = (tag) => /fire|burning/.test(tag) ? 'fire' : /oil/.test(tag) ? 'oil' : /wet|lightning|shock/.test(tag) ? 'water' : /frozen|frost|ice/.test(tag) ? 'frost' : '';
const tags = (values = []) => values.map(t => `<span class="tag ${tagClass(t)}" title="${e(t)}">${e(shortTag(t))}</span>`).join('');
const legacySpriteName = (u) => u.id === 'crawler.donut' ? 'donut' : u.team === 'enemy' ? (/boss|foreman|retention_engine|Retention Engine/i.test(u.id + ' ' + u.label) ? 'boss' : 'enemy') : u.classId?.replace('class.', '') ?? 'brawler';
const characterIndex = (u) => {
  const id=(u.artId || u.id || '').replace(/^art\./,'').replace(/^crawler\./,'');
  return {carl:0,donut:1,katia:2,mongo:3}[id] ?? null;
};
const spriteName = legacySpriteName;
const reserveArtId = u => ({elle:'elle',iman:'imani',imani:'imani',louis:'louis',brittany:'brittany'}[(u.artId||u.id?.replace('crawler.',''))]) ?? null;
const portrait = (u, className = 'unit-portrait') => characterIndex(u) === 3 ? `<img class="${className}${u.hp===0?' dead':''}" style="object-fit:contain" src="assets/revamp/mongo-portrait.png" alt="${e(u.label || 'Mongo')}">` : reserveArtId(u) ? `<img class="${className}${u.hp===0?' dead':''}" style="object-fit:contain" src="assets/directional/${reserveArtId(u)}-portrait.png" data-fallback-src="assets/${e(legacySpriteName(u))}.png" alt="${e(u.label||'Crawler')}">` : characterIndex(u) == null ? `<img class="${className}${u.hp===0?' dead':''}" src="assets/${e(legacySpriteName(u))}.png" alt="${e(u.label || 'Crawler')}">` : `<span class="${className} atlas-character${u.hp === 0 ? ' dead' : ''}" style="--character:${characterIndex(u)}" role="img" aria-label="${e(u.label || 'Crawler')}"></span>`;
const abilityIcon = (a) => /bomb|blast/.test(a.id) ? 6 : /heal|wind|recovery|rally/.test(a.id) ? 10 : /teleport|blink|swap/.test(a.id) ? 9 : /bite|maul|pounce/.test(a.id) ? 12 : /guard|bulwark/.test(a.id) ? 14 : /strike|kick|shatter|blow|bash/.test(a.id) ? 5 : /shape|transform/.test(a.id) ? 11 : 8;
function abilityPresentation(ability) {
  if(ability.id!=='ability.katia_shapeshift')return ability;
  return {...ability,formChooser:true,cost:0,range:0,target:'self',targetIds:view.canAct?[view.selectedUnitId]:[],description:abilityDescription(ability),enabled:view.canAct,disabledReason:view.canAct?'':'Action already spent'};
}
function actionCategory(action, item=false) {
  if(item) return {key:'item',label:'Item'};
  const authored=content.abilities.find(a=>a.id===(action.abilityId||action.id));
  if(authored?.effects.some(effect=>effect.op==='Heal')) return {key:'healing',label:'Healing'};
  if(authored?.incomingTags?.includes('element.fire')) return {key:'fire',label:'Fire'};
  if(authored?.incomingTags?.some(tag=>tag.startsWith('element.'))) return {key:'arcane',label:'Arcane'};
  if(authored?.incomingTags?.includes('damage.physical')) return {key:'physical',label:'Physical'};
  return {key:'arcane',label:'Utility'};
}
const actionIcon = (index) => `<span class="hud-icon" style="--icon:${index}" aria-hidden="true"></span>`;
const hpBar = (u) => `<span class="health${u.team === 'enemy' ? ' enemy-hp' : ''}"><span style="width:${Math.max(0, Math.min(100, u.hp / u.maxHp * 100))}%"></span></span>`;
const displayLog = (text) => String(text ?? '').replace(/(?:ability|reaction|surface|status|element|damage|impact)\.[a-z0-9_]+/g, id => content?.abilities.find(a => a.id === id)?.label ?? id.replace(/^[^.]+\./, '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()));
const forecastLabel = (forecast) => { const tile=view.tiles.find(t=>t.id===forecast?.targetId); return tile ? `Terrain ${String.fromCharCode(65+tile.x)}${tile.y+1}` : forecast?.label || ''; };
const selectedAction = () => {
  if(localAction?.stanceId||localAction?.formId){const mode=(localAction.stanceId?view.stances:view.forms)?.find(mode=>mode.id===(localAction.stanceId||localAction.formId));return mode?{...mode,target:'self',cost:0,range:0,targetIds:[view.selectedUnitId],disabledReason:mode.enabled?'':'Action already spent'}:null;}
  return localAction?.itemId?view.items.find(action=>action.id===localAction.itemId):view.abilities.find(action=>action.id===localAction?.abilityId);
};
const canEndCharacter = () => {const selected=unit();return view?.screen==='battle'&&view.phase==='player'&&selected?.hp>0&&!selected.finished;};

function abilityDescription(a) {
  if (!a) return '';
  if(a.id==='ability.katia_shapeshift')return 'Choose a form and preview its health, mana and movement tradeoffs. Changing maximum stats does not heal or restore mana.';
  const label = id => shortTag(id).toLowerCase().replace(/\b\w/g, c => c.toUpperCase());
  const effects = (a.effects ?? []).map(x => {
    if (x.op === 'Damage') return `Deal ${x.amount} damage`;
    if (x.op === 'Heal') return `Restore ${x.amount} HP`;
    if (x.op === 'Push') return `Push ${x.amount} tile${x.amount===1?'':'s'}`;
    if (x.op === 'Teleport') return 'Teleport to the chosen tile';
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
  const revision=++saveRevision;
  try {
    const serialized = await call('GetSave');
    if(revision!==saveRevision) return;
    localStorage.setItem(saveKey, serialized);
    $('#save-status').textContent = 'Progress saved in this browser';
  } catch (error) {
    if(revision!==saveRevision) return;
    $('#save-status').textContent = 'Local save unavailable · export a backup';
  }
}
function command(type, args = {}, options = {}) {
  const next = commandQueue.then(() => dispatchCommand(type,args,options));
  commandQueue = next.catch(() => {});
  return next;
}
function schedulePersist() {
  // GetSave snapshots the committed C# state while presentation animates independently.
  // Revision ordering prevents a slower earlier snapshot overwriting a newer command.
  void persist();
}
function playerInput(work) {
  if(enemySequence){toast('Enemy turn in progress. Watch their movement, or use Skip animation.','info');return Promise.resolve();}
  if(busy || animating) fastForwardRequested=true;
  battlefield?.skipAnimations();
  const next=inputQueue.then(work);
  inputQueue=next.catch(error=>toast(`Input could not be completed: ${error.message}`,'error'));
  return next;
}
function setEnemyPlayback(active,phase='enemy') {
  enemyPlayback=active;enemyPhaseName=phase;
  const banner=$('#enemy-phase-banner');
  if(banner){banner.hidden=!active;banner.textContent=phase==='enemy'?'ENEMY TURN · Watch their movement':phase==='player'?'YOUR TURN · Preparing the next crawler':'RESOLVING TURN…';}
  document.body.classList.toggle('enemy-playback',active);
  const roundLabel=$('.party-round');if(roundLabel)roundLabel.textContent=active?'ENEMY PHASE':`ROUND ${view.round}`;
  const guidance=$('.battle-guidance');if(guidance)guidance.textContent=active?'Enemies are moving and attacking. Your actions unlock when their turn ends.':view.message||'Select a crawler. Move or act in either order.';
  document.querySelectorAll('.hud-action,#open-actions,#end-turn,.party-chip,#confirm-forecast,#detail-confirm-forecast').forEach(button=>{
    if(active){if(!button.dataset.enemyLock)button.dataset.enemyLock=button.disabled?'disabled':'ready';button.disabled=true;}
    else if(button.dataset.enemyLock){button.disabled=button.dataset.enemyLock==='disabled';delete button.dataset.enemyLock;}
  });
}
async function playPresentation(events,before,after) {
  enemySequence=events.some(event=>event.type==='phase'&&event.tag==='enemy'||before.units.some(unit=>unit.team==='enemy'&&unit.id===event.actorId));
  animating=true; $('#skip-animation')?.removeAttribute('hidden');
  if(enemySequence){fastForwardRequested=false;setEnemyPlayback(true,'resolving');}
  const playback=battlefield.playEvents(events,before,after);
  if(fastForwardRequested&&!enemySequence) battlefield.skipAnimations();
  try {await playback;} finally {fastForwardRequested=false;enemySequence=false;setEnemyPlayback(false);}
}
async function dispatchCommand(type, args = {}, { preserveAction = false, save = true } = {}) {
  busy = true;
  $('#game').setAttribute('aria-busy', 'true');
  try {
    const previousScreen = view.screen;
    const before = view;
    const actionLabel=selectedAction()?.label;
    const actionContext={type,actorId:before.selectedUnitId,actorLabel:unit()?.label,actionLabel:actionLabel||'Action',targetLabel:type==='move'?`Terrain ${String.fromCharCode(65+args.x)}${args.y+1}`:before.units.find(target=>target.id===previewTargetId)?.label||forecastLabel(before.forecast.find(target=>target.targetId===previewTargetId))||'self'};
    const result = await call('Dispatch', JSON.stringify({ type, ...args }));
    const after = JSON.parse(result);
    narrator?.begin(actionContext,before,after);
    if(save && !['preview','cancel','select'].includes(type)) schedulePersist();
    if (before.screen === 'battle' && after.screen !== 'battle' && battlefield && after.events?.length) {
      try { await playPresentation(after.events, before, after); } catch { /* Presentation cannot prevent the committed result appearing. */ }
    }
    view = after;
    if(after.screen!=='camp'){campModal=null;developmentTab=null;developmentPending=null;scenarioMenu=false;}
    if(after.screen!==before.screen)characterSheetId=null;
    if (!preserveAction) { actionChooser=false; endTurnActor=null; detailedForecast=false; localAction = null; previewTargetId=null; inspectedTile = null; targetTile = false; }
    if(type==='preview' && after.canConfirm) detailedForecast=true;
    if (type === 'choose_reward' && previousScreen === 'victory') chosenReward = view.rewards.length === 0;
    if(type==='new_run')narrator?.reset(after);
    if (type === 'continue' || type === 'start' || type === 'new_run' || type === 'retry') {
      chosenReward = false;
      inspectedTile = null;
    }
    busy = false;
    render();
    if (battlefield && view.screen === 'battle' && view.events?.length) {
      busy=true;
      try { await playPresentation(view.events,before,view); } catch { /* Keep the authoritative result if an animation fails. */ }
    }
    narrator?.finish();
    animating=false; $('#skip-animation')?.setAttribute('hidden','');
    if (before.canConfirm && !view.canConfirm && battleReturn) $(battleReturn)?.focus();
    commandFeedback(type, args, before, view,actionLabel);
    for(const quest of after.quests??[])if(quest.complete&&!before.quests?.find(old=>old.id===quest.id)?.complete)toast(`${quest.label} complete.`,'success');
    for(const event of after.events??[])if(event.type==='equipment_unlock'){const gear=after.equipment?.find(item=>item.id===event.tag);if(gear)toast(`${gear.label} is now available in the safe room.`,'success');}
    if((after.events??[]).some(event=>event.type==='level_up'&&!event.preview)){levelNotice=after.progression;render();}
  } catch (error) {
    toast(`The command could not be completed: ${error.message}`, 'error');
  } finally {
    animating=false; busy = false;
    $('#skip-animation')?.setAttribute('hidden','');
    $('#game').setAttribute('aria-busy', 'false');
  }
}
function commandFeedback(type, args, before, after,actionLabel) {
  if(type==='scenario_interact'&&after.events?.some(event=>event.type==='scenario_interact')){toast('Interaction completed. Your unused movement remains available.','success');return;}
  if(type==='confirm_development'&&JSON.stringify(before.development?.crawlers)!==JSON.stringify(after.development?.crawlers)){toast('Stat allocation applied. Updated stats are ready.','success');return;}
  if(type==='craft'&&JSON.stringify(before.items)!==JSON.stringify(after.items)){toast('Recipe crafted. Materials spent and supplies received.','success');return;}
  if(type==='open_loot_box'&&after.development?.lootBoxes.find(box=>box.id===args.lootBoxId)?.opened&&!before.development?.lootBoxes.find(box=>box.id===args.lootBoxId)?.opened){toast('Owned lootbox opened. Rewards added to supplies.','success');return;}
  if(type==='safe_room_rest' && (JSON.stringify(before.roster)!==JSON.stringify(after.roster)||!before.safeRoom?.rested&&after.safeRoom?.rested)){toast('Party rested. Health and mana restored.','success');return;}
  if(['equip','unequip'].includes(type)){const old=before.equipment?.find(gear=>gear.id===args.equipmentId),gear=after.equipment?.find(gear=>gear.id===args.equipmentId);if(old?.equippedUnitId!==gear?.equippedUnitId){toast(`${gear.label} ${type==='equip'?'equipped':'unequipped'}. ${gearBonuses(gear)}`,'success');return;}}
  if(type==='end_turn') {
    const actor=before.units.find(u=>u.id===(args.unitId||before.selectedUnitId));
    const ended=after.units.find(u=>u.id===actor?.id);
    if(actor && (ended?.finished || after.round>before.round || after.screen!==before.screen)) { const next=after.units.find(u=>u.id===after.selectedUnitId); toast(`${actor.label} ends their turn. ${next?.team==='player'?next.label+' is ready.':'Enemy turn resolved.'}`,'success'); return; }
  }
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
    const next=after.units.find(u=>u.id===after.selectedUnitId);
    toast(after.screen === 'victory' ? 'Room cleared. Choose your sponsor reward.' : `${actionLabel||'Action'} used. ${after.canMove?'Movement is still ready.':'End this character’s turn when ready.'}`, 'success'); return;
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
  if (battleCanvas?.isConnected) battleCanvas.remove();
  if (!['battle','explore'].includes(view.screen) && battlefield) { battlefield.dispose(); battlefield = null; battleCanvas = null; }
  $('#game').innerHTML = view.screen === 'camp' ? renderCamp() : view.screen === 'explore' ? renderExploration() : view.screen === 'battle' ? renderBattle() : view.screen === 'victory' ? renderVictory() : renderEnding();
  if(scenarioMenu) $('#game').insertAdjacentHTML('beforeend',renderScenarioMenu(view,scenarioBriefing));
  if(scenarioDetails&&view.scenario) $('#game').insertAdjacentHTML('beforeend',renderScenarioDetails(view,scenarioInteraction));
  if(developmentTab&&view.development) $('#game').insertAdjacentHTML('beforeend',renderDevelopment(view,content,{tab:developmentTab,unitId:developmentUnit}));
  if(developmentPending&&view.development) $('#game').insertAdjacentHTML('beforeend',renderDevelopmentConfirmation(view,content,developmentPending));
  if(questModal) $('#game').insertAdjacentHTML('beforeend',renderQuestDialog());
  if(!['battle','explore'].includes(view.screen)) $('#game').insertAdjacentHTML('beforeend','<div id="narrator-slot" class="narrator-slot narrator-page-slot"></div>');
  if(levelNotice) $('#game').insertAdjacentHTML('beforeend',renderLevelDialog());
  if(characterSheetId) $('#game').insertAdjacentHTML('beforeend',renderCharacterSheet(view,content,gameData,{id:characterSheetId,portrait,describe:abilityDescription}));
  if(abilityDetailsOpen&&selectedAction()) $('#game').insertAdjacentHTML('beforeend',`<dialog id="ability-details-dialog" aria-labelledby="ability-details-title"><div class="dialog-head"><h2 id="ability-details-title">Action details</h2><button id="close-ability-details" class="icon-button" aria-label="Close action details">×</button></div><div class="modal-body">${renderAbilityDetails(selectedAction(),content,{full:true})}</div><div class="modal-actions"><button id="done-ability-details">Back to targeting</button></div></dialog>`);
  if (['battle','explore'].includes(view.screen)) {
    const slot = $('#battlefield-slot');
    if (!battleCanvas) { battleCanvas=document.createElement('canvas'); battleCanvas.id='battlefield'; battleCanvas.addEventListener('battleevent',event=>narrator?.onEvent(event.detail?.event||event.detail)); battleCanvas.addEventListener('battlephase',event=>{if(event.detail?.phase==='enemy')setEnemyPlayback(true);else if(event.detail?.phase==='player'&&enemySequence)setEnemyPlayback(true,'player');}); battleCanvas.setAttribute('aria-label','Isometric dungeon battlefield. Use the accessible map controls to select cells.'); }
    slot.prepend(battleCanvas);
    if (!battlefield) battlefield=createBattlefield(battleCanvas,{onCell:(x,y)=>view.screen==='explore'?command('explore_move',{x,y}):clickCell(x,y),onHover:hoverCell});
    battlefield.setView(view,{mode:view.screen==='battle'&&localAction ? 'ability' : 'move',action:selectedAction(),preview:view.canConfirm ? view.forecast : null,targetId:view.canConfirm?previewTargetId:null});
    battlefield.resize();
  }
  narrator?.mount($('#narrator-slot'));
  bindScreen();
  if(enemySequence)setEnemyPlayback(true,enemyPhaseName);
  if(pinnedInspection&&view.screen==='battle')hoverCell(pinnedInspection.x,pinnedInspection.y);
  window.dungeonView = view;
}
const gearFor = unitId => (view.equipment??[]).filter(gear=>gear.equippedUnitId===unitId);
const gearBonuses = gear => [gear.hpBonus?`${gear.hpBonus>0?'+':''}${gear.hpBonus} HP`:'',gear.manaBonus?`${gear.manaBonus>0?'+':''}${gear.manaBonus} MP`:'',gear.moveBonus?`${gear.moveBonus>0?'+':''}${gear.moveBonus} MOVE`:''].filter(Boolean).join(' · ') || 'No stat change';
function activeQuest() {return (view.quests??[]).find(quest=>!quest.complete)??view.quests?.[0];}
function questRows() {return (view.quests??[]).map(quest=>`<div class="quest-row${quest.complete?' complete':''}"><div><strong>${e(quest.label)}</strong><span>${quest.progress}/${quest.total}${quest.complete?' · Complete':''}</span></div><p>${e(quest.description)}</p><progress value="${quest.progress}" max="${quest.total}" aria-label="${e(quest.label)} progress"></progress></div>`).join('')||'<p class="small muted">Explore the passages and clear the next encounter.</p>';}
function renderQuestTracker() {const quest=activeQuest();if(view.scenario)return `<button id="scenario-objective-button" class="quest-tracker"><span>SCENARIO</span> ${e(view.scenario.objective)} <b>${view.scenario.progress??0}/${view.scenario.total??0}</b></button>`;return `<button id="quest-button" class="quest-tracker"><span>QUEST</span> ${e(quest?.label||'Find the encounter door')} <b>${quest?quest.progress+'/'+quest.total:''}</b></button>`;}
function renderSafeRoomStations(focused,advisor) {
  return `<section class="safe-stations" aria-label="Safe-room stations"><div class="safe-station-floor" aria-hidden="true">${Array.from({length:9},(_,index)=>{const x=index%3,y=Math.floor(index/3);return `<img src="assets/room-kit/floors/stone-${index%2?'b':'a'}.png" style="left:calc(50% + ${(x-y)*58-66}px);top:${25+(x+y)*29}px" alt="">`;}).join('')}<img class="safe-torch torch-one" src="assets/room-kit/props/torch.png" alt=""><img class="safe-torch torch-two" src="assets/room-kit/props/torch.png" alt=""></div><button id="station-rest" class="safe-station rest-station">${portrait(advisor,'station-advisor')}<span>REST <small>Mordecai</small></span></button><button class="safe-station equipment-station" data-equipment="${e(focused.id)}"><img src="assets/room-kit/props/chest.png" alt=""><span>EQUIPMENT <small>Open shared gear</small></span></button><button class="safe-station skills-station" data-skills="${e(focused.id)}"><img src="assets/room-kit/props/lever.png" alt=""><span>SKILLS <small>Abilities & unlocks</small></span></button><button id="quick-enter" class="safe-station exit-station" ${view.partyCount!==view.partyCapacity?'disabled':''}><img src="assets/room-kit/doors/exit.png" alt=""><span>ENTER DUNGEON <small>${view.partyCount}/${view.partyCapacity} deployed</small></span></button></section>`;
}
function renderCamp() {
  const focused=view.roster.find(r=>r.id===focusedRoster&&r.deployable!==false)??view.roster.find(r=>r.selected)??view.roster.find(r=>r.deployable!==false);
  focusedRoster=focused?.id;
  const progression=view.progression;
  const advisor=view.roster.find(r=>r.deployable===false)??{id:'crawler.mordecai',label:'Mordecai',classId:'class.cleric'};
  return `<section class="camp-screen safe-room" aria-labelledby="screen-title"><header class="safe-room-heading"><div><span class="section-label">MORDECAI’S SAFE ROOM</span><h1 id="screen-title">Rest. Equip. Prepare.</h1><p>A safe place between the cameras and the next fight.</p></div><div class="party-progression"><strong>PARTY LEVEL ${progression?.level??1}</strong><span>${progression?.xp??view.xp} XP${progression?.nextLevelXp?' / '+progression.nextLevelXp+' next level':''}</span><progress value="${progression?.xpIntoLevel??0}" max="${(progression?.xpIntoLevel??0)+(progression?.xpToNextLevel??1)||1}" aria-label="Party level progress"></progress></div></header>${renderSafeRoomStations(focused,advisor)}<nav class="safe-activities" aria-label="Safe-room activities"><button id="open-development" ${view.development?'':'disabled'}>Stats · Practice · Craft · Loot</button><button id="open-scenarios" ${view.scenarios?.length?'':'disabled'}>Scenario expeditions</button></nav><div class="safe-room-layout"><aside class="safe-advisor panel"><div class="advisor-head">${portrait(advisor,'advisor-portrait')}<div><h2>Mordecai</h2><span>Safe-room advisor</span></div></div><p>${e(view.safeRoom?.description||'Catch your breath. Check your gear and skills before heading back into the dungeon.')}</p><button id="rest-button" class="primary" ${view.safeRoom?.available===false?'disabled':''}>${view.safeRoom?.rested?'Rest again':'Rest & restore HP / MP'}</button><small>${view.safeRoom?.rested?'Party rested. Equipment and skills are ready to change.':'Rest restores the party’s actual health and mana.'}</small><details class="safe-quests"><summary>Quest journal · ${e(activeQuest()?.label||'Explore the dungeon')} ${activeQuest()?activeQuest().progress+'/'+activeQuest().total:''}</summary>${questRows()}</details></aside><details class="safe-party" ${rosterExpanded?'open':''}><summary class="panel-head"><h2>Manage your crawlers</h2><span>${view.partyCount}/${view.partyCapacity} deployed · classes & stats</span></summary><div class="safe-roster-grid">${view.roster.filter(r=>r.deployable!==false).map(r=>`<article class="safe-crawler${r.selected?' deployed':''}${r.id===focusedRoster?' focused':''}" data-crawler-card="${e(r.id)}"><button class="safe-crawler-select" data-roster="${e(r.id)}" aria-pressed="${r.id===focusedRoster}">${portrait(r)}<span><strong>${e(r.label)}</strong><small>Level ${r.level??progression?.level??1} · ${e(classLabel(r.classId))}</small><span class="deployment-label">${r.selected?'DEPLOYED':'RESERVE'}</span></span></button><div class="safe-crawler-stats"><span>HP <b>${r.hp}/${r.maxHp}</b></span><span>MP <b>${r.energy??r.maxEnergy??'—'}/${r.maxEnergy??'—'}</b></span><span>MOVE <b>${r.move??'—'}</b></span><span>XP <b>${progression?.xp??view.xp}</b></span></div><div class="safe-crawler-gear">${gearFor(r.id).map(gear=>`<span>${e(gear.label)}</span>`).join('')||'<span>No equipment</span>'}</div><div class="safe-crawler-buttons"><button data-equipment="${e(r.id)}">Equipment</button><button data-skills="${e(r.id)}">Skills</button><button data-character-sheet="${e(r.id)}">Sheet</button></div></article>`).join('')}</div><section class="safe-loadout panel"><div><strong>${e(focused?.label)} · Class & deployment</strong><p>Character skills stay with their crawler. Classes add their own abilities.</p></div><label class="field" for="class-select">CLASS<select id="class-select">${view.classes.map(klass=>`<option value="${e(klass.id)}" ${klass.id===focused?.classId?'selected':''}>${e(klass.label)}</option>`).join('')}</select></label><button id="toggle-party">${focused?.selected?'Move to reserve':'Deploy crawler'}</button></section><details class="panel inventory-strip"><summary>Shared consumables · ${view.items.reduce((sum,item)=>sum+item.count,0)} charges</summary><div class="tags">${view.items.map(item=>`<span class="tag">${e(item.label)} ×${item.count}</span>`).join('')}</div></details></details></div>${renderCampModal()}</section>`;
}
function renderCampModal() {
  if(!campModal)return '';
  const crawler=view.roster.find(r=>r.id===focusedRoster);
  if(!crawler)return '';
  const equipment=campModal==='equipment';
  const klass=view.classes.find(c=>c.id===crawler.classId);
  const innate=crawler.innateAbilityIds??[];
  const classIds=klass?.abilityIds??[];
  const gearIds=gearFor(crawler.id).flatMap(gear=>gear.abilityIds??[]);
  const unlocked=(view.progression?.skills??[]).filter(skill=>(!skill.unitId||skill.unitId===crawler.id));
  const abilityCard=(id,source)=>{const authored=content.abilities.find(a=>a.id===id);return `<div class="skill-row"><strong>${e(authored?.label||id)}</strong><span class="skill-source">${e(source)}</span><p>${e(abilityDescription(authored))}</p><small>${authored?.cost??0} MP · range ${authored?.range??0}</small></div>`;};
  return `<dialog id="${equipment?'equipment':'skills'}-dialog" class="loadout-dialog" aria-labelledby="loadout-title"><div class="dialog-head"><div><span class="section-label">${e(crawler.label)} · LEVEL ${crawler.level??view.progression?.level??1}</span><h2 id="loadout-title">${equipment?'Equipment':'Skills & unlocks'}</h2></div><button id="close-loadout" class="icon-button" aria-label="Close ${equipment?'equipment':'skills'}">×</button></div><div class="modal-body"><label class="loadout-crawler-label" for="loadout-crawler">CRAWLER<select id="loadout-crawler">${view.roster.filter(r=>r.deployable!==false).map(r=>`<option value="${e(r.id)}" ${r.id===crawler.id?'selected':''}>${e(r.label)}</option>`).join('')}</select></label><div class="action-modal-stats"><span>HP ${crawler.hp}/${crawler.maxHp}</span><span>MP ${crawler.energy??'—'}/${crawler.maxEnergy??'—'}</span><span>Move ${crawler.move??'—'}</span></div>${equipment?`<p class="modal-intro">Equip owned gear to change actual stats and grant skills. Each item has one owner; equipping replaces that slot’s current item.</p><div class="equipment-grid">${(view.equipment??[]).map(gear=>{const mine=gear.equippedUnitId===crawler.id;const owner=view.roster.find(r=>r.id===gear.equippedUnitId);return `<article class="equipment-card${mine?' equipped':''}${!gear.owned?' locked':''}" data-gear="${e(gear.id)}"><div><strong>${e(gear.label)}</strong><span>${e(gear.slot)}</span></div><p class="gear-bonuses">${e(gearBonuses(gear))}</p>${(gear.abilityIds??[]).map(id=>`<small>Grants ${e(content.abilities.find(a=>a.id===id)?.label||id)}</small>`).join('')}<p class="equipment-ownership">${mine?'Equipped by '+e(crawler.label):owner?'Equipped by '+e(owner.label):gear.owned?'Owned · available':'Locked · unlock encounter '+gear.unlockEncounter}</p><button ${mine?'data-unequip':'data-equip'}="${e(gear.id)}" ${!gear.owned||owner&&!mine?'disabled':''}>${mine?'Unequip':owner?'In use':'Equip'}</button></article>`;}).join('')}</div>`:`<p class="modal-intro">Available skills combine character, class, equipped gear and level unlocks. Locked skills become usable automatically at the required party level.</p><div class="skill-grid">${innate.map(id=>abilityCard(id,'Character skill')).join('')}${classIds.filter(id=>!innate.includes(id)).map(id=>abilityCard(id,'Class skill')).join('')}${gearIds.filter(id=>!innate.includes(id)&&!classIds.includes(id)).map(id=>abilityCard(id,'Equipment skill')).join('')}${unlocked.map(skill=>`<div class="skill-row${skill.unlocked?' unlocked':' locked'}" data-skill="${e(skill.id)}"><strong>${e(skill.label)}</strong><span class="skill-source">${skill.unlocked?'Unlocked':'Locked'} · Level ${skill.level}</span><p>${e(abilityDescription(content.abilities.find(a=>a.id===skill.abilityId)))}</p><small>${skill.unlocked?'Available in the action menu.':'Reach party level '+skill.level+' to unlock.'}</small></div>`).join('')}</div>`}</div><div class="modal-actions"><button id="done-loadout">Done</button><button id="switch-loadout">${equipment?'View skills':'View equipment'}</button></div></dialog>`;
}
function renderQuestDialog() {return `<dialog id="quest-dialog" aria-labelledby="quest-title"><div class="dialog-head"><h2 id="quest-title">Quest journal</h2><button id="close-quests" class="icon-button" aria-label="Close quests">×</button></div><div class="modal-body">${questRows()}</div><div class="modal-actions"><button id="done-quests">Back to dungeon</button></div></dialog>`;}
function renderLevelDialog() {
  if(!levelNotice)return '';
  return `<dialog id="level-up-dialog" aria-labelledby="level-up-title"><div class="dialog-head"><h2 id="level-up-title">Party level ${levelNotice.level}</h2></div><div class="modal-body"><p class="level-up-line">Your crawlers grow stronger.</p><div class="action-modal-stats"><span>+${levelNotice.hpBonus} HP</span><span>+${levelNotice.manaBonus} MP</span><span>+${levelNotice.moveBonus} MOVE</span></div><p class="modal-intro">These are the party’s current level bonuses. Rest at Mordecai’s safe room, check new equipment and open Skills to see your unlocks.</p><div class="skill-grid">${(view.progression?.skills??[]).filter(skill=>skill.level===levelNotice.level).map(skill=>`<div class="skill-row unlocked"><strong>${e(skill.label)}</strong><small>${e(view.roster.find(r=>r.id===skill.unitId)?.label||'Party skill')} · unlocked</small></div>`).join('')}</div></div><div class="modal-actions"><button id="continue-level-up" class="primary">Continue</button></div></dialog>`;
}
function renderParty() {
  const players=view.units.filter(u=>u.team==='player');
  const order=view.partyOrder?.length ? [...players].sort((a,b)=>view.partyOrder.indexOf(a.id)-view.partyOrder.indexOf(b.id)) : players;
  return `<div class="party-strip" style="--party-columns:${Math.min(4,players.length)}" aria-label="Crawler turn order">${order.map(u=>`<button class="party-chip${u.selected?' active':''}${u.finished?' turn-spent':''}" data-unit="${e(u.id)}" ${u.hp<=0?'disabled':''} aria-pressed="${u.selected}">${portrait(u)}<span><strong>${e(u.label)}</strong><small>${u.hp<=0?'Fallen':u.finished?'Turn ended':u.acted?'Action spent':u.selected?'Selected': 'Ready'}</small></span></button>`).join('')}<span class="party-round">ROUND ${view.round}</span></div>`;
}
function renderBattle() {
  return `<section class="battle-screen" aria-label="Tactical dungeon"><div class="objective-banner"><span class="objective-seal" aria-hidden="true"></span><div><small>FLOOR ${String(view.encounterIndex+1).padStart(2,'0')}</small><h2 id="screen-title">${e(view.objective || 'OPEN THE EXIT')}</h2></div></div>${renderQuestTracker()}<div id="enemy-phase-banner" class="enemy-phase-banner" hidden role="status">ENEMY TURN · Watch their movement</div><div id="battlefield-slot" class="battlefield-slot">${renderWorldControls()}${renderBoard()}<div id="map-inspect" class="map-inspect" hidden></div></div><div class="battle-guidance" role="status">${e(view.message || 'Select a crawler. Move or act in either order.')}</div><div class="battle-hud">${renderParty()}<section class="action-dock" aria-label="Selected crawler and actions">${renderInspector(unit())}</section><div id="narrator-slot" class="narrator-slot"></div></div>${renderDrawer()}${actionChooser?renderActionDialog():''}${endTurnActor?renderEndTurnDialog():''}${detailedForecast?renderForecastDialog():''}</section>`;
}
function renderWorldControls() {
  return `<div class="world-controls" aria-label="Battlefield camera"><button id="zoom-in" aria-label="Zoom in">+</button><button id="zoom-out" aria-label="Zoom out">−</button><button id="rotate-left" aria-label="Rotate left 90 degrees">↶ 90°</button><span id="compass-label">${e(battlefield?.getRotationLabel?.()||'North view')}</span><button id="rotate-right" aria-label="Rotate right 90 degrees">90° ↷</button><button id="center-map">Center</button><button id="skip-animation" ${animating?'':'hidden'}>Skip animation</button></div>`;
}
function hoverCell(x,y) {
  if(x==null&&pinnedInspection&&view.screen==='battle'){x=pinnedInspection.x;y=pinnedInspection.y;}
  inspectPosition = x == null ? null : {x,y};
  const box=$('#map-inspect'); if(!box) return;
  if(view.screen==='explore') { const point=view.exploration.points.find(p=>p.x===x&&p.y===y);box.hidden=!point;if(point)box.innerHTML=`<strong>${e(point.label)}</strong><span>${e(point.description)}</span>`;return; }
  const target=view.units.find(u=>u.x===x&&u.y===y&&u.hp>0);
  const tile=view.tiles.find(t=>t.x===x&&t.y===y);
  box.hidden=!target&&!tile?.tags?.length;
  if(!box.hidden) box.innerHTML=target?`<strong>${e(target.label)}</strong><span>HP ${target.hp}/${target.maxHp} · ${e(target.team)}</span>${tags(target.tags)}`:`<strong>Terrain</strong>${tags(tile.tags)}`;
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
  const map=view.exploration;
  if(!map) return '<p>Preparing the passages…</p>';
  const points=map.points.filter(p=>p.canInteract&&!p.claimed);
  return `<section class="exploration-screen iso-exploration"><div class="objective-banner"><span class="objective-seal" aria-hidden="true"></span><div><small>EXPLORE THE FLOOR</small><h2>${e(map.label)}</h2></div></div>${renderQuestTracker()}<div id="battlefield-slot" class="battlefield-slot">${renderWorldControls()}<div class="board accessible-board" style="--columns:${map.width};--rows:${map.height}" aria-label="Exploration map">${map.tiles.map(t=>`<button data-explore-cell="${t.x},${t.y}" ${!t.reachable?'disabled':''} aria-label="${t.x},${t.y}: ${t.blocked?'wall':t.revealed?'passage':'unexplored'}"></button>`).join('')}</div><div id="map-inspect" class="map-inspect" hidden></div></div><div class="exploration-hud"><div class="explore-party">${view.roster.filter(r=>r.selected).map(r=>portrait(r)).join('')}</div><div class="explore-copy"><strong>${e(points[0]?.label || 'Find the encounter door')}</strong><p>${e(points[0]?.description || 'Click a path or use arrow keys / WASD. Approach discoveries to interact.')}</p></div><div class="explore-interactions">${points.map(point=>`<button class="primary" data-explore-interact="${e(point.id)}">${point.kind==='encounter'?'Enter':'Investigate'} ${e(point.label)}</button>`).join('')}<button id="return-camp">Return to Mordecai</button></div><div id="narrator-slot" class="narrator-slot"></div></div></section>`;
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
  return `<div class="board accessible-board" style="--columns:${view.width};--rows:${view.height}" role="group" aria-label="Tactical battle map. Click a crawler to select, or a highlighted tile to move.">${rows.join('')}</div>`;
}
function renderInspector(selected) {
  const action=selectedAction();
  const changes=view.forecast.filter(f=>f.beforeHp!==f.afterHp||f.beforeEnergy!==f.afterEnergy||JSON.stringify(f.beforeTags)!==JSON.stringify(f.afterTags));
  const target=changes.find(f=>f.targetId!==view.selectedUnitId&&f.beforeHp!==f.afterHp) ?? changes.find(f=>f.targetId!==view.selectedUnitId) ?? changes[0];
  return `<div class="hud-crawler">${selected?`<button id="open-character-sheet" class="hud-character-button" aria-label="Open ${e(selected.label)} character sheet">${portrait(selected,'hud-portrait')}<span>Character sheet</span></button>`:''}<div class="hud-stats"><strong>${e(selected?.label || 'SELECT CRAWLER')}</strong><small class="hud-class">${e(classLabel(selected?.classId))}</small><div class="hud-meter hp"><span>HP</span><b>${selected?.hp??0}/${selected?.maxHp??0}</b><i style="--fill:${selected?selected.hp/selected.maxHp*100:0}%"></i></div><div class="hud-meter en"><span>MP</span><b>${selected?.energy??0}/${selected?.maxEnergy??0}</b><i style="--fill:${selected?selected.energy/selected.maxEnergy*100:0}%"></i></div><div class="hud-move">MOVE <b>${selected?.effectiveMove??selected?.move??'—'}</b> <small>${selected?.finished?'TURN ENDED':selected?.acted?'ACTION SPENT':selected?.moved?'MOVE SPENT':'READY'}</small></div><div class="hud-statuses">${(selected?.statuses??[]).map(status=>`<span class="tag" title="${e(displayLog(status.source))}">${e(shortTag(status.tag))} ${status.remainingRounds}r</span>`).join('')}</div></div></div><div class="hud-actions"><button id="open-actions" class="action-picker-button">Abilities & skills <span>Full action book</span></button><div class="hud-action-list"><button id="move-mode" class="hud-action${!localAction?' active':''}" ${!view.canMove&&!localAction?'disabled':''}>${actionIcon(4)}<strong>MOVE</strong><small>${selected?.moved?'Spent':`${selected?.effectiveMove??selected?.move??'—'} tiles`}</small></button>${view.abilities.map(abilityPresentation).map((a,index)=>`<button class="hud-action category-${actionCategory(a).key}${localAction?.abilityId===a.id?' active':''}" data-ability="${e(a.id)}" ${!a.enabled?'disabled':''} aria-label="${e(a.label+'. '+a.description+'. '+(a.disabledReason||''))}" title="${e(a.description+(a.disabledReason?' · '+a.disabledReason:''))}">${actionIcon(abilityIcon(a))}<strong>${e(a.label)}</strong><small>${a.formChooser?'Choose form · 1 action':a.cost+' MP · '+a.range+' RNG'}</small>${a.disabledReason?`<small class="action-reason">${e(a.disabledReason)}</small>`:''}</button>`).join('')}<button class="hud-action category-item${localAction?.itemId?' active':''}" data-drawer="items">${actionIcon(7)}<strong>ITEMS</strong><small>${localAction?.itemId?e(selectedAction()?.label)+' ×'+(selectedAction()?.count??0):view.items.reduce((sum,i)=>sum+i.count,0)+' charges'}</small></button></div><p class="action-caption">${e(action?.description || (selected?.finished?'Choose another crawler.':selected?.acted?'Action spent. Move or end this character’s turn.':'Move or act in either order.'))}${action?.disabledReason?' · '+e(action.disabledReason):''}</p></div><div class="hud-target" aria-live="polite">${view.canConfirm?`<div class="target-forecast"><strong>${e((target?forecastLabel(target):null)||action?.label||'TARGET')}</strong>${target&&target.beforeHp!==target.afterHp?`<span class="target-hp">HP <b>${target.beforeHp} → ${target.afterHp}</b></span>`:''}${target?tags(target.afterTags.filter(t=>!target.beforeTags.includes(t))):''}<small>${e(action?.label||'Action')} · ${action?.cost??0} MP</small></div><div class="forecast-buttons"><button id="cancel-forecast">Cancel</button><button id="confirm-forecast" class="primary">Confirm</button><button id="review-forecast" class="details-button" aria-label="Detailed forecast">Details</button></div>`:`${localAction?renderAbilityDetails(action,content):'<strong>READ THE ROOM</strong><small>Select an enemy to inspect, or open the character sheet for stats, forms and all skills.</small>'}${localAction?'<button id="cancel-forecast">Cancel targeting</button>':''}`}<button id="end-turn" class="end-character" ${!canEndCharacter()?'disabled':''}>End character turn →</button><button data-drawer="log" class="hud-log">Combat log</button></div>`;
}
function abilitySource(id,unitId) {
  const crawler=view.roster.find(r=>r.id===unitId);
  if(crawler?.innateAbilityIds?.includes(id))return 'Character';
  if(gearFor(unitId).some(gear=>gear.abilityIds?.includes(id)))return 'Equipment';
  if(view.progression?.skills?.some(skill=>skill.abilityId===id&&skill.unlocked&&(!skill.unitId||skill.unitId===unitId)))return 'Level unlock';
  return 'Class';
}
function renderActionDialog() {
  const actor=unit();
  const abilityButton=(a,item=false)=>{ const category=actionCategory(a,item);const available=item ? a.count>0&&view.canAct : a.enabled; const reason=a.disabledReason || (!a.targetIds.length?'No legal target in range · move first':'');return `<button class="modal-action-card category-${category.key}${(item?localAction?.itemId:localAction?.abilityId)===a.id?' active':''}" ${item?'data-modal-item':'data-modal-ability'}="${e(a.id)}" ${available?'':'disabled'}>${actionIcon(item?7:abilityIcon(a))}<span><strong>${e(a.label)}${item?' ×'+a.count:''}</strong><span class="category-label">${category.label} · ${item?'Shared item':abilitySource(a.id,view.selectedUnitId)}</span><small>${a.formChooser?'Choose form · 1 action':(item?'1 action':a.cost+' MP')+' · range '+a.range+' · '+e(a.target)}</small><p>${e(a.description)}</p><small class="${reason?'availability-warning':'availability-ready'}">${e(reason||a.targetIds.length+' legal target'+(a.targetIds.length===1?'':'s'))}</small></span></button>`;};
  return `<dialog id="action-dialog" aria-labelledby="action-title"><div class="dialog-head"><div><span class="section-label">${e(actor?.label||'Crawler')} · ${e(classLabel(actor?.classId))}</span><h2 id="action-title">Choose an action</h2></div><button id="close-actions" class="icon-button" aria-label="Close action choices">×</button></div><div class="modal-body"><div class="action-modal-stats"><span>HP ${actor?.hp}/${actor?.maxHp}</span><span>MP ${actor?.energy}/${actor?.maxEnergy}</span><span>Move ${actor?.effectiveMove??actor?.move??0}${actor?.moved?' · spent':''}</span></div><p class="modal-intro">Choose an ability, then select a highlighted target on the map. Review the exact result before confirming.</p><button id="modal-move" class="modal-move" ${view.canMove?'':'disabled'}>${actionIcon(4)}<span><strong>Move</strong><small>${view.canMove?'Choose a blue path. No action or mana cost.':'Movement is spent for this character.'}</small></span></button><div class="modal-action-grid">${view.abilities.map(abilityPresentation).map(a=>abilityButton(a)).join('')}</div><details class="modal-item-section" ${localAction?.itemId?'open':''}><summary>Shared items · ${view.items.reduce((sum,i)=>sum+i.count,0)} charges</summary><div class="modal-action-grid">${view.items.map(a=>abilityButton(a,true)).join('')}</div></details></div><div class="modal-actions"><button id="cancel-actions">Back to map</button><button id="actions-end-turn">End character turn…</button></div></dialog>`;
}
function closeActionDialog() { actionChooser=false;render();$('#open-actions')?.focus(); }
function requestEndTurn() {
  actionChooser=false; detailedForecast=false;
  return playerInput(async()=>{await commandQueue;endTurnActor=view.selectedUnitId;render();});
}
function renderEndTurnDialog() {
  const actor=view.units.find(u=>u.id===endTurnActor);
  const order=view.partyOrder?.length?view.partyOrder:view.units.filter(u=>u.team==='player').map(u=>u.id);
  const next=order.map(id=>view.units.find(u=>u.id===id)).find(u=>u&&u.id!==actor?.id&&u.hp>0&&!u.finished);
  return `<dialog id="end-turn-dialog" aria-labelledby="end-turn-title"><div class="dialog-head"><h2 id="end-turn-title">End ${e(actor?.label||'this character')}’s turn?</h2><button class="icon-button" id="close-end-turn" aria-label="Keep playing">×</button></div><div class="modal-body"><div class="turn-actor-summary">${actor?portrait(actor):''}<div><strong>${e(actor?.label||'Crawler')}</strong><p>${actor?.moved?'Movement spent.':'Movement is still ready.'} ${view.canAct?'An ability is still available.':''}</p></div></div><p class="turn-next"><span>NEXT</span><strong>${e(next?.label||'Enemy phase')}</strong><small>${next?'Only this character ends their turn. The next ready crawler can act.':'All living crawlers will have finished. Enemies move and attack, then the next round begins.'}</small></p><p class="small muted">Cancel returns to the map without spending movement, mana or an action.</p></div><div class="modal-actions"><button id="cancel-end-turn">Keep playing</button><button id="confirm-end-turn" class="primary">End ${e(actor?.label||'character')}’s turn</button></div></dialog>`;
}
function closeEndTurnDialog() {endTurnActor=null;render();$('#end-turn')?.focus();}
function renderForecastDialog() {
  if (!view.canConfirm) return '';
  const action = selectedAction();
  return `<dialog id="forecast-dialog" class="forecast-dialog" aria-labelledby="forecast-title"><div class="dialog-head"><div><span class="section-label">EXACT ACTION FORECAST</span><h2 id="forecast-title">${e(action?.label || 'Review action')}</h2></div><button class="icon-button" id="close-forecast" aria-label="Close forecast details">×</button></div><div class="modal-body"><p class="modal-intro">${e(action?.description || 'Review the exact result before spending this crawler’s action.')}</p><div class="forecast-detail-list">${view.forecast.filter(f => f.beforeHp !== f.afterHp || f.beforeEnergy !== f.afterEnergy || JSON.stringify(f.beforeTags) !== JSON.stringify(f.afterTags)||f.beforeMaxHp!==f.afterMaxHp||f.beforeMaxEnergy!==f.afterMaxEnergy||f.beforeMove!==f.afterMove).map(f => `<section class="forecast-detail"><h3>${e(forecastLabel(f))}</h3>${f.beforeHp !== f.afterHp ? `<div class="forecast-number"><span>Health</span><b>${f.beforeHp} → ${f.afterHp}</b></div>` : ''}${f.beforeMaxHp!==undefined&&f.beforeMaxHp!==f.afterMaxHp?`<div class="forecast-number"><span>Maximum HP</span><b>${f.beforeMaxHp} → ${f.afterMaxHp}</b></div>`:''}${f.beforeMaxEnergy!==undefined&&f.beforeMaxEnergy!==f.afterMaxEnergy?`<div class="forecast-number"><span>Maximum MP</span><b>${f.beforeMaxEnergy} → ${f.afterMaxEnergy}</b></div>`:''}${f.beforeMove!==undefined&&f.beforeMove!==f.afterMove?`<div class="forecast-number"><span>Movement</span><b>${f.beforeMove} → ${f.afterMove}</b></div>`:''}${f.beforeEnergy !== f.afterEnergy ? `<div class="forecast-number"><span>Mana</span><b>${f.beforeEnergy} → ${f.afterEnergy}</b></div>` : ''}<div class="tags">${f.afterTags.filter(t => !f.beforeTags.includes(t)).map(t => `<span class="tag good">+ ${e(shortTag(t))}</span>`).join('')}${f.beforeTags.filter(t => !f.afterTags.includes(t)).map(t => `<span class="tag">− ${e(shortTag(t))}</span>`).join('')}</div></section>`).join('') || '<p>The action changes terrain or status without changing health or mana.</p>'}</div><ol class="forecast-chain">${view.log.filter(l => l.startsWith('Forecast:')).slice(-8).map(l => `<li>${e(displayLog(l.slice(10)))}</li>`).join('')}</ol><p class="small muted">Confirm spends one action. Movement is independent: act or move first, then end this character’s turn. Cancel spends nothing.</p></div><div class="modal-actions"><button id="detail-cancel-forecast">Cancel action <span class="key">Esc</span></button><button id="detail-confirm-forecast" class="primary">Confirm ${e(action?.label||'action')}</button></div></dialog>`;
}
function renderLog() {
  return `<details class="log" ${view.canConfirm ? 'open' : ''}><summary>COMBAT LOG / ${view.log.length} EVENTS</summary><div class="log-lines">${view.log.slice(-24).map(l => `<p>${e(displayLog(l))}</p>`).join('') || '<p>No actions yet.</p>'}</div></details>`;
}
function renderSurvivors() {
  return `<div class="outcome-party">${view.roster.filter(r => r.selected).map(r => `<div class="survivor">${portrait(r)}<span><strong>${e(r.label)}</strong><small>${e(classLabel(r.classId))} · ${r.hp} / ${r.maxHp} HP</small></span></div>`).join('')}</div>`;
}
function renderScenarioOutcome(won) {
  return `<section class="outcome-layout" aria-labelledby="screen-title"><div class="center-outcome"><div class="trophy" aria-hidden="true">${won?'♜':'†'}</div><h2 id="screen-title">${e(view.scenario.label)} · ${won?'Cleared':'Defeated'}</h2><p>${e(view.scenario.objective)}</p><p>Your campaign checkpoint is preserved. Return to it or retry this standalone challenge.</p><div class="button-row"><button id="return-scenario" class="primary">Return to campaign</button><button id="retry-button">Retry scenario</button></div></div>${renderSurvivors()}${renderLog()}</section>`;
}
function renderVictory() {
  if(view.scenario)return renderScenarioOutcome(true);
  return `<section class="outcome-layout" aria-labelledby="screen-title"><div class="outcome-header"><div><h2 id="screen-title">Room cleared. Cameras rolling.</h2><p>${e(view.encounterName)} · Encounter ${view.encounterIndex + 1} complete</p></div><div class="xp-value">${view.xp} XP<small>TOTAL RUN EXPERIENCE</small></div></div><div class="reward-layout"><div><span class="section-label">${view.rewards.length ? 'PICK ONE SPONSOR REWARD' : 'SPONSOR REWARD CLAIMED'}</span><div class="reward-list">${view.rewards.map((r, i) => `<button data-reward="${e(r.id)}" class="reward-button" ${chosenReward ? 'disabled' : ''}><span class="reward-icon" aria-hidden="true">${['◇', '▱', '✦'][i % 3]}</span><span><strong>${e(r.label)}</strong><small>${e(r.description)}</small></span></button>`).join('') || '<div class="panel panel-body"><span class="tag good">DELIVERY RECEIVED</span><p class="small muted" style="margin-top:12px">Your sponsor reward is in the shared supplies. Ready for the next room.</p></div>'}</div></div><aside class="panel sponsor-copy"><h3>SPONSOR TRANSMISSION</h3><blockquote>“A surprising number of you are still alive. We’ve sent a little something.”</blockquote><p>${e(view.message || (view.rewards.length ? 'Choose a reward for your party, then head to camp before the next encounter.' : 'Delivery received. Continue when you’re ready.'))}</p><button id="continue-button" class="primary" ${view.rewards.length ? 'disabled' : ''}>${view.encounterIndex + 1 >= view.encounterCount ? 'Finish the floor' : 'Return to camp'} <span aria-hidden="true">→</span></button><p class="small">One reward per encounter. Your run saves automatically.</p></aside></div>${renderSurvivors()}${renderLog()}</section>`;
}
function renderEnding() {
  if(view.scenario)return renderScenarioOutcome(false);
  const complete = view.screen === 'complete';
  return `<section class="outcome-layout" aria-labelledby="screen-title"><div class="center-outcome"><div class="trophy" aria-hidden="true">${complete ? '♜' : '†'}</div><h2 id="screen-title">${complete ? 'The floor is yours.' : 'The dungeon wins. For now.'}</h2><p>${complete ? `${view.customMap?'Your workshop room is clear.':'All three encounters cleared.'} Your crawlers earned ${view.xp} XP, exploited the elements, and made it back in one piece. The audience will want a sequel.` : 'Your deployed crawlers have fallen. Retry the encounter with the same starting party and supplies, or rebuild from the beginning.'}</p><div class="tags" style="justify-content:center"><span class="tag gold">${complete ? 'FLOOR 01 COMPLETE' : 'PARTY DEFEATED'}</span><span class="tag">${view.xp} XP EARNED</span></div><div class="button-row">${!complete ? '<button class="primary" id="retry-button">Retry encounter</button>' : '<button id="open-scenarios" class="primary">Play boss scenarios</button>'}<button id="ending-new-run" ${complete ? 'class="primary"' : ''}>Start a new run</button></div><button class="quiet" id="ending-export">Export this run</button></div>${renderSurvivors()}${renderLog()}</section>`;
}
function bindScenario(){
  $('#open-scenarios')?.addEventListener('click',()=>{scenarioMenu=true;render();});
  const close=()=>{scenarioMenu=false;render();$('#open-scenarios')?.focus();};
  $('#close-scenarios')?.addEventListener('click',close);$('#done-scenarios')?.addEventListener('click',close);
  if($('#scenario-dialog')){openDialog('#scenario-dialog');$('#scenario-dialog').addEventListener('cancel',event=>{event.preventDefault();close();});}
  document.querySelectorAll('[data-scenario-briefing]').forEach(button=>button.addEventListener('click',()=>{scenarioBriefing=button.dataset.scenarioBriefing;render();$('#scenario-briefing')?.scrollIntoView({block:'nearest'});}));
  $('#start-scenario')?.addEventListener('click',event=>{scenarioMenu=false;command('scenario_start',{targetId:event.currentTarget.dataset.scenarioId});});
  $('#scenario-objective-button')?.addEventListener('click',()=>{scenarioDetails=true;render();});
  const closeDetails=()=>{scenarioDetails=false;scenarioInteraction=null;render();$('#scenario-objective-button')?.focus();};
  $('#close-scenario-objective')?.addEventListener('click',closeDetails);$('#done-scenario-objective')?.addEventListener('click',closeDetails);
  if($('#scenario-objective-dialog')){openDialog('#scenario-objective-dialog');$('#scenario-objective-dialog').addEventListener('cancel',event=>{event.preventDefault();closeDetails();});}
  $('#return-scenario')?.addEventListener('click',()=>{scenarioDetails=false;command('scenario_return');});
  document.querySelectorAll('[data-scenario-interact]').forEach(button=>button.addEventListener('click',()=>{scenarioInteraction=button.dataset.scenarioInteract;render();$('#scenario-interaction-confirm')?.scrollIntoView({block:'nearest'});}));
  $('#cancel-scenario-interaction')?.addEventListener('click',()=>{scenarioInteraction=null;render();});
  $('#confirm-scenario-interaction')?.addEventListener('click',event=>{const targetId=event.currentTarget.dataset.target;scenarioDetails=false;scenarioInteraction=null;command('scenario_interact',{unitId:view.selectedUnitId,targetId});});
}
function bindDevelopment(){
  $('#open-development')?.addEventListener('click',()=>{developmentTab='stats';render();});
  const close=async()=>{if(view.development?.canConfirm)await command('cancel_development',{}, {save:false});developmentTab=null;developmentPending=null;render();$('#open-development')?.focus();};
  $('#close-development')?.addEventListener('click',close);$('#done-development')?.addEventListener('click',close);
  if($('#development-dialog')){openDialog('#development-dialog');$('#development-dialog').addEventListener('cancel',event=>{event.preventDefault();close();});}
  $('[id="development-crawler"]')?.addEventListener('change',event=>{developmentUnit=event.target.value;render();});
  document.querySelectorAll('[data-development-tab]').forEach(button=>button.addEventListener('click',async()=>{if(view.development?.canConfirm)await command('cancel_development',{}, {save:false});developmentTab=button.dataset.developmentTab;render();}));
  document.querySelectorAll('[data-allocate-stat]').forEach(button=>button.addEventListener('click',()=>command('preview_allocate',{unitId:$('#development-crawler').value,statId:button.dataset.allocateStat,points:1},{save:false})));
  $('#cancel-allocation')?.addEventListener('click',()=>command('cancel_development',{}, {save:false}));
  $('#confirm-allocation')?.addEventListener('click',()=>command('confirm_development'));
  document.querySelectorAll('[data-craft-recipe],[data-loot-box]').forEach(button=>button.addEventListener('click',()=>{developmentPending=button.dataset.craftRecipe?{type:'craft',id:button.dataset.craftRecipe}:{type:'loot',id:button.dataset.lootBox};render();}));
  const closeConfirmation=()=>{developmentPending=null;render();};
  for(const id of ['close-development-confirm','cancel-development-operation'])$('#'+id)?.addEventListener('click',closeConfirmation);
  if($('#development-confirm-dialog')){openDialog('#development-confirm-dialog');$('#development-confirm-dialog').addEventListener('cancel',event=>{event.preventDefault();closeConfirmation();});}
  $('#confirm-development-operation')?.addEventListener('click',()=>{const pending=developmentPending;developmentPending=null;command(pending.type==='craft'?'craft':'open_loot_box',pending.type==='craft'?{recipeId:pending.id}:{lootBoxId:pending.id});});
}
function bindScreen() {
  bindDevelopment();bindScenario();
  const openSheet=(id,from)=>{characterSheetId=id;sheetReturn=from;actionChooser=false;render();};
  $('#open-character-sheet')?.addEventListener('click',()=>openSheet(view.selectedUnitId,'#open-character-sheet'));
  document.querySelectorAll('[data-character-sheet]').forEach(button=>button.addEventListener('click',()=>openSheet(button.dataset.characterSheet,`[data-character-sheet="${button.dataset.characterSheet}"]`)));
  const closeSheet=()=>{characterSheetId=null;render();$(sheetReturn||'#open-character-sheet')?.focus();};
  const sheet=$('#character-sheet-dialog');
  if(sheet){openDialog('#character-sheet-dialog');$('#close-character-sheet').focus();if(sheetOpenSection){document.getElementById(sheetOpenSection)?.scrollIntoView({block:'start'});sheetOpenSection=null;}sheet.addEventListener('cancel',event=>{event.preventDefault();closeSheet();});}
  $('#close-character-sheet')?.addEventListener('click',closeSheet);$('#done-character-sheet')?.addEventListener('click',closeSheet);
  $('#sheet-crawler')?.addEventListener('change',event=>{characterSheetId=event.target.value;render();});
  document.querySelectorAll('[data-sheet-section]').forEach(button=>button.addEventListener('click',()=>document.getElementById(button.dataset.sheetSection)?.scrollIntoView({block:'start',behavior:'auto'})));
  $('#sheet-select-character')?.addEventListener('click',()=>playerInput(()=>command('select',{unitId:characterSheetId})));
  $('#sheet-manage-gear')?.addEventListener('click',()=>{focusedRoster=characterSheetId;characterSheetId=null;campModal='equipment';render();});
  const chooseMode=(field,id)=>{
    const actorId=characterSheetId;
    characterSheetId=null;
    return playerInput(async()=>{
      await commandQueue;
      if(view.selectedUnitId!==actorId)await command('select',{unitId:actorId});
      if(view.canConfirm)await command('cancel',{}, {save:false});
      localAction={[field]:id};previewTargetId=actorId;battleReturn='#open-character-sheet';
      await command('preview',{unitId:actorId,[field]:id},{preserveAction:true,save:false});
    });
  };
  document.querySelectorAll('[data-sheet-stance]').forEach(button=>{if(enemySequence)button.disabled=true;button.addEventListener('click',()=>chooseMode('stanceId',button.dataset.sheetStance));});
  document.querySelectorAll('[data-sheet-form]').forEach(button=>{if(enemySequence)button.disabled=true;button.addEventListener('click',()=>chooseMode('formId',button.dataset.sheetForm));});
  const closeAbilityDetails=()=>{abilityDetailsOpen=false;render();$('#open-ability-details')?.focus();};
  $('#open-ability-details')?.addEventListener('click',()=>{abilityDetailsOpen=true;render();});
  if($('#ability-details-dialog')){openDialog('#ability-details-dialog');$('#close-ability-details').focus();$('#ability-details-dialog').addEventListener('cancel',event=>{event.preventDefault();closeAbilityDetails();});}
  $('#close-ability-details')?.addEventListener('click',closeAbilityDetails);$('#done-ability-details')?.addEventListener('click',closeAbilityDetails);

  document.querySelectorAll('img[data-fallback-src]').forEach(img=>img.addEventListener('error',()=>{img.src=img.dataset.fallbackSrc;delete img.dataset.fallbackSrc;},{once:true}));
  const refreshCompass=()=>{if($('#compass-label'))$('#compass-label').textContent=battlefield?.getRotationLabel?.()||'North view';};
  $('#rotate-left')?.addEventListener('click',()=>{battlefield?.rotate?.(-1);refreshCompass();});
  $('#rotate-right')?.addEventListener('click',()=>{battlefield?.rotate?.(1);refreshCompass();});
  refreshCompass();
  $('#rest-button')?.addEventListener('click',()=>command('safe_room_rest'));
  $('#station-rest')?.addEventListener('click',()=>command('safe_room_rest'));
  document.querySelectorAll('[data-equipment]').forEach(button=>button.addEventListener('click',()=>{focusedRoster=button.dataset.equipment;campModal='equipment';render();}));
  document.querySelectorAll('[data-skills]').forEach(button=>button.addEventListener('click',()=>{focusedRoster=button.dataset.skills;campModal='skills';render();}));
  const loadoutDialog=$('#equipment-dialog')||$('#skills-dialog');
  const closeLoadout=()=>{const id=focusedRoster,kind=campModal;campModal=null;render();document.querySelector(`[data-${kind}="${id}"]`)?.focus();};
  if(loadoutDialog){openDialog('#'+loadoutDialog.id);$('#close-loadout').focus();loadoutDialog.addEventListener('cancel',event=>{event.preventDefault();closeLoadout();});}
  $('#close-loadout')?.addEventListener('click',closeLoadout);$('#done-loadout')?.addEventListener('click',closeLoadout);
  $('#switch-loadout')?.addEventListener('click',()=>{campModal=campModal==='equipment'?'skills':'equipment';render();});
  $('#loadout-crawler')?.addEventListener('change',event=>{focusedRoster=event.target.value;render();});
  document.querySelectorAll('[data-equip]').forEach(button=>button.addEventListener('click',()=>{button.disabled=true;command('equip',{unitId:focusedRoster,equipmentId:button.dataset.equip});}));
  document.querySelectorAll('[data-unequip]').forEach(button=>button.addEventListener('click',()=>{button.disabled=true;command('unequip',{unitId:focusedRoster,equipmentId:button.dataset.unequip});}));
  $('#quest-button')?.addEventListener('click',()=>{questModal=true;render();});
  const closeQuests=()=>{questModal=false;render();$('#quest-button')?.focus();};
  if($('#quest-dialog')){openDialog('#quest-dialog');$('#quest-dialog').addEventListener('cancel',event=>{event.preventDefault();closeQuests();});}
  $('#close-quests')?.addEventListener('click',closeQuests);$('#done-quests')?.addEventListener('click',closeQuests);
  const closeLevel=()=>{levelNotice=null;render();};
  if($('#level-up-dialog')){openDialog('#level-up-dialog');$('#continue-level-up').focus();$('#level-up-dialog').addEventListener('cancel',event=>{event.preventDefault();closeLevel();});}
  $('#continue-level-up')?.addEventListener('click',closeLevel);

  $('#open-actions')?.addEventListener('click',()=>{if(enemySequence)return; battlefield?.skipAnimations();actionChooser=true;detailedForecast=false;endTurnActor=null;render();});
  const actionDialog=$('#action-dialog');
  if(actionDialog){openDialog('#action-dialog');$('#close-actions').focus();actionDialog.addEventListener('cancel',event=>{event.preventDefault();closeActionDialog();});}
  $('#close-actions')?.addEventListener('click',closeActionDialog);
  $('#cancel-actions')?.addEventListener('click',closeActionDialog);
  document.querySelectorAll('[data-modal-ability]').forEach(button=>button.addEventListener('click',()=>{actionChooser=false;chooseAction({abilityId:button.dataset.modalAbility});}));
  document.querySelectorAll('[data-modal-item]').forEach(button=>button.addEventListener('click',()=>{actionChooser=false;chooseAction({itemId:button.dataset.modalItem});}));
  $('#modal-move')?.addEventListener('click',()=>{actionChooser=false;command('cancel',{}, {save:false});});
  $('#actions-end-turn')?.addEventListener('click',requestEndTurn);
  const endDialog=$('#end-turn-dialog');
  if(endDialog){openDialog('#end-turn-dialog');$('#cancel-end-turn').focus();endDialog.addEventListener('cancel',event=>{event.preventDefault();closeEndTurnDialog();});}
  $('#close-end-turn')?.addEventListener('click',closeEndTurnDialog);
  $('#cancel-end-turn')?.addEventListener('click',closeEndTurnDialog);
  $('#confirm-end-turn')?.addEventListener('click',()=>{const unitId=endTurnActor;if(!unitId)return;$('#confirm-end-turn').disabled=true;endTurnActor=null;command('end_turn',{unitId});});

  $('#zoom-in')?.addEventListener('click',()=>battlefield?.zoom(.2));
  $('#zoom-out')?.addEventListener('click',()=>battlefield?.zoom(-.2));
  $('#center-map')?.addEventListener('click',()=>battlefield?.centerSelected());
  $('#skip-animation')?.addEventListener('click',()=>battlefield?.skipAnimations());
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
  $('.safe-party')?.addEventListener('toggle',event=>{rosterExpanded=event.target.open;});
  document.querySelectorAll('[data-roster]').forEach(b => b.addEventListener('click', () => { rosterExpanded=true;focusedRoster = b.dataset.roster; render(); }));
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
  $('#quick-enter')?.addEventListener('click', () => command('start'));
  document.querySelectorAll('[data-unit], [data-ability], [data-modal-ability], [data-modal-item]').forEach(b => b.addEventListener('pointerdown', () => b.classList.add('pressed')));
  document.querySelectorAll('[data-cell]').forEach(b => b.addEventListener('focus', () => hoverCell(...b.dataset.cell.split(',').map(Number))));
  document.querySelectorAll('[data-unit]').forEach(b => b.addEventListener('click', () => { targetTile = false; playerInput(()=>command('select', { unitId: b.dataset.unit })); }));
  document.querySelectorAll('[data-cell]').forEach(b => b.addEventListener('click', () => clickCell(...b.dataset.cell.split(',').map(Number))));
  document.querySelectorAll('[data-ability]').forEach(b => b.addEventListener('click', () => chooseAction({ abilityId: b.dataset.ability })));
  document.querySelectorAll('[data-item]').forEach(b => b.addEventListener('click', () => chooseAction({ itemId: b.dataset.item })));
  $('#move-mode')?.addEventListener('click', () => { targetTile = false; command('cancel'); });
  $('#terrain-mode')?.addEventListener('click', () => { targetTile = !targetTile; render(); });
  const forecastDialog = $('#forecast-dialog');
  if (forecastDialog) { openDialog('#forecast-dialog'); $('#detail-cancel-forecast').focus(); forecastDialog.addEventListener('cancel', event => {event.preventDefault();cancelTargeting();}); }
  $('#review-forecast')?.addEventListener('click', () => {detailedForecast=true;render();});
  $('#detail-cancel-forecast')?.addEventListener('click', cancelTargeting);
  $('#detail-confirm-forecast')?.addEventListener('click', () => {$('#detail-confirm-forecast').disabled=true;detailedForecast=false;command('confirm');});
  $('#close-forecast')?.addEventListener('click',cancelTargeting);
  $('#cancel-forecast')?.addEventListener('click', cancelTargeting);
  $('#confirm-forecast')?.addEventListener('click', () => command('confirm'));
  $('#wait-button')?.addEventListener('click', () => command('wait'));
  $('#end-turn')?.addEventListener('click',requestEndTurn);
  document.querySelectorAll('[data-reward]').forEach(b => b.addEventListener('click', () => command('choose_reward', { rewardId: b.dataset.reward })));
  $('#continue-button')?.addEventListener('click', () => command('continue'));
  $('#retry-button')?.addEventListener('click', () => command('retry'));
  $('#ending-new-run')?.addEventListener('click', () => openDialog('#restart-dialog'));
  $('#ending-export')?.addEventListener('click', exportSave);
}
function chooseAction(action) {
  if(action.abilityId==='ability.katia_shapeshift')return playerInput(async()=>{await commandQueue;if(view.canConfirm)await command('cancel',{}, {save:false});localAction=null;actionChooser=false;characterSheetId=view.selectedUnitId;sheetReturn='#open-actions';sheetOpenSection='sheet-forms';render();});
  pendingActionChoice=action;
  pinnedInspection=null;
  document.querySelectorAll('[data-ability]').forEach(button=>button.classList.toggle('active',button.dataset.ability===action.abilityId));
  const result=playerInput(()=>applyActionChoice(action));
  const clearPending=()=>{if(pendingActionChoice===action)pendingActionChoice=null;};
  result.then(clearPending,clearPending);
  return result;
}
async function applyActionChoice(action) {
  await commandQueue;
  actionChooser=false;
  if (view.canConfirm) await command('cancel', {}, { save: false });
  drawer = null;
  battleReturn = action.itemId ? '[data-drawer="items"]' : `[data-ability="${action.abilityId}"]`;
  localAction = action;
  targetTile = false;
  if (selectedAction()?.target === 'self') {
    previewTargetId=view.selectedUnitId;
    await command('preview', { ...localAction, targetId: view.selectedUnitId }, { preserveAction: true, save: false });
  } else {render();toast(`Choose a highlighted ${selectedAction()?.target||'target'} for ${selectedAction()?.label||'this action'}.`);}
}
function clickCell(x,y) {
  const occupant=view.units.find(unit=>unit.x===x&&unit.y===y&&unit.hp>0);
  if(view.screen==='battle'&&!localAction&&!pendingActionChoice&&occupant?.team==='enemy') {
    // Taps have no sustained hover: keep this read-only inspection after pointerleave.
    pinnedInspection={x,y};hoverCell(x,y);return Promise.resolve();
  }
  pinnedInspection=null;
  return playerInput(()=>applyCellClick(x,y));
}
async function applyCellClick(x, y) {
  await commandQueue;
  if(view.screen!=='battle') return;
  battleReturn = `[data-cell="${x},${y}"]`;
  inspectedTile = view.tiles.find(t => t.x === x && t.y === y);
  const occupant = view.units.find(u => u.x === x && u.y === y && u.hp > 0);
  const action = selectedAction();
  if (localAction && action) {
    const targetId = targetTile || action.target === 'tile' ? inspectedTile?.id ?? `tile.${x}.${y}` : occupant?.id;
    if (!targetId || !(action.targetIds ?? []).includes(targetId)) { if (view.canConfirm) await command('cancel', {}, {preserveAction:true,save:false}); toast('This action needs a unit target. Choose a valid crawler or enemy. Use a terrain ability to target a surface.', 'warning'); render(); return; }
    previewTargetId=targetId;
    await command('preview', { ...localAction, targetId }, { preserveAction: true, save: false });
  } else if (occupant?.team === 'player') {
    await command('select', { unitId: occupant.id });
  } else if (!occupant && view.reachable.some(c => c.x === x && c.y === y)) {
    await command('move', { x, y });
  } else {
    pinnedInspection={x,y};hoverCell(x,y);
  }
}
async function cancelTargeting() { detailedForecast=false; targetTile = false; await command('cancel', {}, { save: false }); }
async function exportSave() {
  try {
    await inputQueue;
    await commandQueue;
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
  await inputQueue;
  await commandQueue;
  ++saveRevision;
  const result = await call('LoadSave', serialized);
  const nextView = JSON.parse(result);
  if (nextView.message?.startsWith('Save rejected:')) throw new Error(nextView.message.slice(15));
  view = nextView;
  narrator?.reset(view);
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
    narrator=createNarrator({getView:()=>view,content});
    let saved;
    try { saved = localStorage.getItem(saveKey); } catch { /* Export remains available. */ }
    if (saved) {
      try { await loadSerializedSave(saved); toast('Your run has been restored.'); }
      catch (error) { render(); toast('Your stored save could not be restored. A new party is ready; the stored file has been preserved.', 'warning'); $('#save-status').textContent = 'Stored save invalid · import or start fresh'; }
    } else {
      render();
      await persist();
      // The camp gateway is the first playable screen; help remains available on demand.
    }
    $('#game').setAttribute('aria-busy', 'false');
    if(new URLSearchParams(location.search).get('workshop')==='1'){try{const storedMap=localStorage.getItem('dct.workshop-map');if(!storedMap)throw new Error('No workshop map is stored.');await command('import_map',{customMap:JSON.parse(storedMap)});}catch(error){toast(`Workshop map could not be loaded: ${error.message}`,'error');}}
    window.dungeon = { get scene(){return battlefield;}, cellToScreen:(x,y)=>battlefield?.cellToScreen(x,y), command, getView: () => view, getSave: () => call('GetSave'), loadSave: loadSerializedSave };
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
$('#import-map-button').addEventListener('click',()=>$('#import-map-file').click());
$('#import-map-file').addEventListener('change',async event=>{
 const file=event.target.files[0];if(!file)return;
 try{if(file.size>2000000)throw new Error('Map file exceeds 2 MB.');const customMap=JSON.parse(await file.text());const previousMap=JSON.stringify(view.customMap);await command('import_map',{customMap});if(view.customMap&&JSON.stringify(view.customMap)!==previousMap)closeDialog('#save-dialog');}
 catch(error){toast(`Map could not be loaded: ${error.message}`,'error');}
 event.target.value='';
});
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
  if(view?.screen==='explore'&&!document.querySelector('dialog[open]')&&!['INPUT','SELECT','TEXTAREA'].includes(document.activeElement?.tagName)&&!event.ctrlKey&&!event.metaKey&&!event.altKey&&['ArrowLeft','ArrowRight','ArrowUp','ArrowDown','w','a','s','d'].includes(event.key)) {
    event.preventDefault();battleCanvas?.focus({preventScroll:true});battleCanvas?.dispatchEvent(new KeyboardEvent('keydown',{key:event.key}));
  }

  if (event.key === '?' && !document.querySelector('dialog[open]') && !event.ctrlKey && !event.metaKey && !['INPUT', 'SELECT', 'TEXTAREA'].includes(document.activeElement?.tagName)) { event.preventDefault(); openDialog('#help-dialog'); }
  if (event.key === 'Escape' && !document.querySelector('dialog[open]')) { if(enemySequence)return; if (drawer) { closeDrawer(); } else if (view?.screen === 'battle') cancelTargeting(); }
});
boot();

window.addEventListener('resize', () => battlefield?.resize());
