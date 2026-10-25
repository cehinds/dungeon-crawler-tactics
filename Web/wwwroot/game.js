import { createGeneratedAdventure } from './generated-adventure.js';
import { attachExplorationControls } from './exploration-controls.js';
import { renderAudience, renderAudienceSummary, renderAudienceHome, renderFavorControls } from './audience-ui.js';
import { renderNeighborhood, renderNeighborhoodStrip } from './neighborhood-ui.js';
import { renderHome } from './home-ui.js';
import { renderJourney, renderJourneyBattle } from './journey-ui.js';
import { renderSkillTree } from './skill-tree-ui.js';
import { renderMissionBoard, renderExpeditionDetails } from './mission-ui.js';
import { renderScenarioMenu, renderScenarioDetails } from './scenario-ui.js';
import { renderDevelopment, renderDevelopmentConfirmation } from './development-ui.js';
import { notify, syncFeedbackHost, clearFeedback } from './feedback.js';
import { createBattlefield } from './battlefield.js';
import { renderAbilityDetails, renderCharacterSheet, renderSpecialtyReview } from './character-ui.js';
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
let captureTargetId = null;
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
let enemySheetId=null;
let skillTreeOpen=false,skillTreeUnit=null,skillTreeNode=null,missionOpen=false,missionId=null,expeditionDetails=false;
let developmentTab=null,developmentUnit=null,developmentPending=null,practiceAbility=null,practiceRank=1;
let scenarioMenu=false,scenarioBriefing=null,scenarioDetails=false,scenarioInteraction=null;
let rosterExpanded=false;
let homeOpen=false,homeRoomId=null;
let journeyOpen=false,journeyConfirmStart=false,skillTreeKind='personal';
let neighborhoodOpen=false,neighborhoodUnit=null,neighborhoodStart=false;
let audienceOpen = false;
let favorPreview = false;
let questModal = false;
let levelNotice = null;
let enemySequence = false;
let enemyPlayback = false;
let characterSheetId=null;
let sheetReturn=null;
let sheetOpenSection=null;
let sheetActiveSection="sheet-stats";
let specialtyPending=null;
let abilityDetailsOpen=false;
let narrator=null;
let enemyPhaseName='resolving';
const escapeHtml = (value) => String(value ?? '').replace(/[&<>"']/g, (c) => ({ '&':'&amp;', '<':'&lt;', '>':'&gt;', '"':'&quot;', "'":'&#39;' }[c]));
const e = escapeHtml;
const call = (method, ...args) => DotNet.invokeMethodAsync(assembly, method, ...args);
const classLabel = (id) => view?.classes.find(c => c.id === id)?.label ?? id?.replace('class.', '') ?? '';
const classChoiceLabel = klass => `${klass.label}${view.classes.filter(c=>c.label===klass.label).length>1?(klass.id.startsWith('class.lore_')?' · Catalog class':' · Original kit'):''}`;
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
const copyLabel=u=>u.duplicateSourceId?`Copy ${Number(u.id.split('.').at(-1))+1}`:u.id==='crawler.donut'?'Donut':u.label;
const reserveArtId = u => ({elle:'elle',iman:'imani',imani:'imani',louis:'louis',brittany:'brittany'}[(u.artId||u.id?.replace('crawler.',''))]) ?? null;
const portrait = (u, className = 'unit-portrait') => characterIndex(u) === 3 ? `<img class="${className}${u.hp===0?' dead':''}" style="object-fit:contain" src="assets/revamp/mongo-portrait.png" alt="${e(u.label || 'Mongo')}">` : reserveArtId(u) ? `<img class="${className}${u.hp===0?' dead':''}" style="object-fit:contain" src="assets/directional/${reserveArtId(u)}-portrait.png" data-fallback-src="assets/${e(legacySpriteName(u))}.png" alt="${e(u.label||'Crawler')}">` : characterIndex(u) == null ? `<img class="${className}${u.hp===0?' dead':''}" src="assets/${e(legacySpriteName(u))}.png" alt="${e(u.label || 'Crawler')}">` : `<span class="${className} atlas-character${u.hp === 0 ? ' dead' : ''}" style="--character:${characterIndex(u)}" role="img" aria-label="${e(u.label || 'Crawler')}"></span>`;
const hudActionLabel = (a) => a.id==='ability.katia_rush'?'Rush':({triplicate:'Triplicate',tripwire:'Tripwire',dynamite:'Dynamite',5:'Kick',15:'Strike',6:'Bomb',10:'Restore',14:'Guard',11:'Forms'})[abilityIcon(a)] || a.label;
const abilityIcon = (a) => a.id==='ability.katia_rush'?4:({'ability.carl_tripwire':'tripwire','ability.carl_dynamite':'dynamite','ability.donut_clockwork_triplicate':'triplicate'})[a.id] || (a.id==='ability.carl_powerful_strike'?15 : /bomb|blast/.test(a.id) ? 6 : /heal|wind|recovery|rally/.test(a.id) ? 10 : /teleport|blink|swap/.test(a.id) ? 9 : /bite|maul|pounce/.test(a.id) ? 12 : /guard|bulwark/.test(a.id) ? 14 : /strike|kick|shatter|blow|bash/.test(a.id) ? 5 : /shape|transform/.test(a.id) ? 11 : 8);
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
const actionIcon = (index) => {const path=typeof index==='string'?`signatures/${index}`:`ui-kit/${({4:'move',5:'kick',6:'bomb',7:'potion',8:'missile',9:'move',10:'heart',11:'skills',12:'kick',14:'guard',15:'powerful-strike'})[index]||'skills'}`;return `<img class="hud-icon ui-action-icon" src="assets/${path}.png" alt="" aria-hidden="true">`;};
const hpBar = (u) => `<span class="health${u.team === 'enemy' ? ' enemy-hp' : ''}"><span style="width:${Math.max(0, Math.min(100, u.hp / u.maxHp * 100))}%"></span></span>`;
const displayLog = (text) => String(text ?? '').replace(/(?:ability|reaction|surface|status|element|damage|impact)\.[a-z0-9_]+/g, id => content?.abilities.find(a => a.id === id)?.label ?? id.replace(/^[^.]+\./, '').replace(/_/g, ' ').replace(/\b\w/g, c => c.toUpperCase()));
const isSummonForecast=f=>f?.targetId?.startsWith('clockwork.')&&!view.units.some(u=>u.id===f.targetId);
const forecastLabel = (forecast) => { if(isSummonForecast(forecast))return `Summon clockwork copy ${Number(forecast.targetId.split('.').at(-1))+1}`; const tile=view.tiles.find(t=>t.id===forecast?.targetId); return tile ? `Terrain ${String.fromCharCode(65+tile.x)}${tile.y+1}` : forecast?.label || ''; };
const selectedAction = () => {
  if(captureTargetId&&view?.canConfirm){const capture=view.journey?.captures?.find(c=>c.targetId===captureTargetId);if(capture)return {label:'Capture '+capture.label,description:'Seal this weakened monster into a card and remove it from the board. This is capture, not a damaging attack. The selected crawler spends one action; movement remains independent.',cost:0,range:capture.range,target:'enemy'};}
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
    if (x.op === 'DuplicatePet') return `Create ${x.amount} controllable clockwork copies of an allied pet: ${x.summonHp} HP, ${x.summonMove} movement, ${x.summonRounds} rounds each. Requires ${x.amount} adjacent open tiles. Copies have no Mana and use the pet’s free attacks`;
    const tagRule=(gameData?.tagRules??[]).find(rule=>rule.tag===x.tag);
    if(x.op==='AddTag'&&tagRule?.moveBonus)return `Apply ${label(x.tag)}: ${tagRule.moveBonus>0?'+':''}${tagRule.moveBonus} movement for ${tagRule.durationRounds} rounds. Turn duration and Mana cost are tactical adaptations`;
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
async function persist({ strict = false } = {}) {
  const revision=++saveRevision;
  try {
    const serialized = await call('GetSave');
    if(revision!==saveRevision) { if (strict) throw new Error('Another save superseded this handoff. Retry it.'); return false; }
    localStorage.setItem(saveKey, serialized);
    const indicator = $('#save-status'); if (indicator) indicator.textContent = 'Progress saved in this browser';
    return true;
  } catch (error) {
    const indicator = $('#save-status'); if (indicator) indicator.textContent = 'Local save unavailable · export a backup';
    if (strict) throw new Error(`This dungeon could not be saved in this browser. Its handoff is kept for retry. ${error.message}`);
    return false;
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
  const phaseLabel=$('.party-phase');if(phaseLabel){phaseLabel.classList.toggle('hostile-phase',active);phaseLabel.innerHTML=active?'ENEMY TURN · INPUT LOCKED':`PARTY TURN <b>${view.units.filter(u=>u.team==='player'&&u.hp>0&&!u.finished).length}/${view.units.filter(u=>u.team==='player'&&u.hp>0).length} ready</b>`;}
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
    if(before.screen!==after.screen || before.encounterName!==after.encounterName || before.expedition?.id!==after.expedition?.id || before.scenario?.id!==after.scenario?.id) clearFeedback();
    if(type!=='explore_step') narrator?.begin(actionContext,before,after);
    if(save && !['preview','cancel','select'].includes(type)) schedulePersist();
    if (before.screen === 'battle' && after.screen !== 'battle' && battlefield && after.events?.length) {
      try { await playPresentation(after.events, before, after); } catch { /* Presentation cannot prevent the committed result appearing. */ }
    }
    view = after;
    if(after.screen!=='camp'){campModal=null;developmentTab=null;developmentPending=null;scenarioMenu=false;}
    if(after.screen!==before.screen)characterSheetId=null;
    if (!preserveAction) { favorPreview=false; actionChooser=false; endTurnActor=null; detailedForecast=false; localAction = null; previewTargetId=null; inspectedTile = null; targetTile = false; }
    if(type==='preview')favorPreview=false;
    if(['preview','preview_capture','preview_favor'].includes(type) && after.canConfirm) detailedForecast=true;
    if(!after.canConfirm&&type!=='preview_capture')captureTargetId=null;
    if (type === 'choose_reward' && previousScreen === 'victory') chosenReward = view.rewards.length === 0;
    if(['new_run','start_neighborhood','return_neighborhood'].includes(type)||(before.neighborhood?.standalone&&!after.neighborhood?.standalone))narrator?.reset(after);
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
    if(type!=='explore_step') narrator?.finish();
    animating=false; $('#skip-animation')?.setAttribute('hidden','');
    if (before.canConfirm && !view.canConfirm && battleReturn) $(battleReturn)?.focus();
    commandFeedback(type, args, before, view,actionLabel);
    for(const quest of after.quests??[])if(quest.complete&&!before.quests?.find(old=>old.id===quest.id)?.complete)toast(`${quest.label} complete.`,'success');
    for(const event of after.events??[])if(event.type==='equipment_unlock'){const gear=after.equipment?.find(item=>item.id===event.tag);if(gear)toast(`${gear.label} is now available in the safe room.`,'success');}
    for(const c of after.neighborhood?.challenges??[])if(c.earned&&after.events?.some(event=>event.type==='achievement'&&event.tag===c.id))toast(`NEW ACHIEVEMENT · ${c.label} · ${c.rewardCount} × ${after.items?.find(i=>i.id===c.rewardItemId)?.label??c.rewardItemId}. Saved in your neighborhood journal.`,'success');
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
  if(type==='explore_step') { if(before.screen==='explore'&&after.screen==='battle') toast('Enemies spotted · Tactical combat begins.','info'); return; }
  if(type==='preview_neighborhood'&&after.neighborhood?.canConfirm)return;
  if(type==='cancel_neighborhood'){toast('Choice canceled. Supplies unchanged.','info');return;}
  if(type==='confirm_neighborhood'&&before.neighborhood?.forecast&&!after.neighborhood?.canConfirm){
    const choice=after.neighborhood?.interactions.find(i=>i.id===before.neighborhood.forecast.interactionId);
    if(choice?.completed){toast(`${choice.label} resolved. Supplies updated; choice saved.`,'success');return;}
  }
  if((type==='return_neighborhood'||type==='continue')&&before.neighborhood?.standalone&&!after.neighborhood?.standalone){toast('Your campaign has been restored.','success');return;}
  if((type==='preview_capture'&&after.canConfirm)||(type==='preview_skill_node'&&after.skillTree?.canConfirm)||(type.startsWith('preview_home_')&&after.home?.canConfirm))return;
  if(type==='confirm'&&after.events?.some(event=>event.type==='capture')){toast('Monster card secured.','success');return;}
  if(type==='confirm_home_upgrade'&&after.events?.some(event=>event.type==='home_upgrade')){toast(after.message||'Home upgrade installed.','success');return;}
  if(type==='confirm_skill_node'&&after.events?.some(event=>event.type==='skill_node_learned')){toast('Skill unlocked. Updated effects are ready.','success');return;}
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
  if(view.journey?.active){progress.innerHTML=`<span class="current">${String(view.journey.floorNumber).padStart(2,'0')}</span><small>OF 18 · ${e(view.journey.floorLabel)}</small>`;return;}
  if(progress.querySelectorAll('span').length!==3)progress.innerHTML='<span>01</span><i></i><span>02</span><i></i><span>03</span><small>THE FIRST FLOOR</small>';
  progress.querySelectorAll('span').forEach((span, index) => {
    span.classList.toggle('current', index === view.encounterIndex && view.screen !== 'complete');
    span.classList.toggle('done', index < view.encounterIndex || view.screen === 'complete');
    span.textContent = index < view.encounterIndex || view.screen === 'complete' ? '✓' : String(index + 1).padStart(2, '0');
  });
}
function render() {
  const previousPartyStrip=$('.battle-hud .party-strip');
  const previousPartyScroll=previousPartyStrip?.scrollLeft??0;
  const previousPartySelection=previousPartyStrip?.querySelector('[data-unit][aria-pressed="true"]')?.dataset.unit;
  renderProgress();
  if (view.screen !== 'battle') drawer = null;
  document.body.dataset.screen = view.screen;
  if (battleCanvas?.isConnected) battleCanvas.remove();
  if (!['battle','explore'].includes(view.screen) && battlefield) { battlefield.dispose(); battlefield = null; battleCanvas = null; }
  $('#game').innerHTML = view.screen === 'camp' ? renderCamp() : view.screen === 'explore' ? renderExploration() : view.screen === 'battle' ? renderBattle() : view.screen === 'victory' ? renderVictory() : renderEnding();
  if(view.journey?.active&&view.screen==='battle') $('#game').insertAdjacentHTML('beforeend',renderJourneyBattle(view));
  if(neighborhoodOpen&&view.neighborhood) $('#game').insertAdjacentHTML('beforeend',renderNeighborhood(view,content,{unitId:neighborhoodUnit??view.roster.find(r=>r.selected)?.id}));
  if(neighborhoodStart) $('#game').insertAdjacentHTML('beforeend',`<dialog id="neighborhood-start-dialog" aria-labelledby="neighborhood-start-title"><div class="dialog-head"><h2 id="neighborhood-start-title">Explore the Over City</h2></div><div class="modal-body"><p>A connected Floor 3 neighborhood: prepare in camp, inspect the ward, rescue a crawler and uncover a boss clue.</p><p>Your current campaign is preserved. This separate mini-campaign starts with its own party and supplies; return at any time to restore your exact campaign. Supplies and rewards earned here stay in this mini-campaign.</p></div><div class="modal-actions"><button id="cancel-neighborhood-start">Keep exploring here</button><button id="confirm-neighborhood-start" class="primary">Enter Over City</button></div></dialog>`);
  if(homeOpen&&view.home) $('#game').insertAdjacentHTML('beforeend',renderHome(view,{roomId:homeRoomId}));
  if(journeyOpen) $('#game').insertAdjacentHTML('beforeend',renderJourney(view,{confirmStart:journeyConfirmStart}));
  if(enemySheetId){const enemy=view.units.find(u=>u.id===enemySheetId);if(enemy)$('#game').insertAdjacentHTML('beforeend',renderEnemyInfo(enemy));}
  if(skillTreeOpen&&view.skillTree) $('#game').insertAdjacentHTML('beforeend',renderSkillTree(view,content,{unitId:skillTreeUnit,nodeId:skillTreeNode,portrait,kind:skillTreeKind}));
  if(missionOpen) $('#game').insertAdjacentHTML('beforeend',renderMissionBoard(view,gameData,missionId));
  if(expeditionDetails&&view.expedition) $('#game').insertAdjacentHTML('beforeend',renderExpeditionDetails(view));
  if(scenarioMenu) $('#game').insertAdjacentHTML('beforeend',renderScenarioMenu(view,scenarioBriefing));
  if(scenarioDetails&&view.scenario) $('#game').insertAdjacentHTML('beforeend',renderScenarioDetails(view,scenarioInteraction));
  if(developmentTab&&view.development) $('#game').insertAdjacentHTML('beforeend',renderDevelopment(view,content,{tab:developmentTab,unitId:developmentUnit,rankAbility:practiceAbility,rank:practiceRank}));
  if(developmentPending&&view.development) $('#game').insertAdjacentHTML('beforeend',renderDevelopmentConfirmation(view,content,developmentPending));
  if(audienceOpen) $('#game').insertAdjacentHTML('beforeend',renderAudience(view));
  if(questModal) $('#game').insertAdjacentHTML('beforeend',renderQuestDialog());
  if(!['battle','explore'].includes(view.screen)) $('#game').insertAdjacentHTML('beforeend','<div id="narrator-slot" class="narrator-slot narrator-page-slot"></div>');
  if(levelNotice) $('#game').insertAdjacentHTML('beforeend',renderLevelDialog());
  if(characterSheetId) $('#game').insertAdjacentHTML('beforeend',renderCharacterSheet(view,content,gameData,{id:characterSheetId,portrait,describe:abilityDescription}));
  if(specialtyPending) $('#game').insertAdjacentHTML('beforeend',renderSpecialtyReview(view,content,specialtyPending,abilityDescription));
  if(abilityDetailsOpen&&selectedAction()) $('#game').insertAdjacentHTML('beforeend',`<dialog id="ability-details-dialog" aria-labelledby="ability-details-title"><div class="dialog-head"><h2 id="ability-details-title">Action details</h2><button id="close-ability-details" class="icon-button" aria-label="Close action details">×</button></div><div class="modal-body">${renderAbilityDetails(selectedAction(),content,{full:true})}</div><div class="modal-actions"><button id="done-ability-details">Back to targeting</button></div></dialog>`);
  if (['battle','explore'].includes(view.screen)) {
    const slot = $('#battlefield-slot');
    if (!battleCanvas) { battleCanvas=document.createElement('canvas'); battleCanvas.id='battlefield'; battleCanvas.addEventListener('battleevent',event=>narrator?.onEvent(event.detail?.event||event.detail)); battleCanvas.addEventListener('battlephase',event=>{if(event.detail?.phase==='enemy')setEnemyPlayback(true);else if(event.detail?.phase==='player'&&enemySequence)setEnemyPlayback(true,'player');}); battleCanvas.setAttribute('aria-label','Square dungeon battlefield. Walk with WASD or arrow keys outside combat.'); }
    slot.prepend(battleCanvas);
    if (!battlefield) battlefield=createBattlefield(battleCanvas,{onCell:(x,y)=>view.screen==='explore'?hoverCell(x,y):clickCell(x,y),onHover:hoverCell});
    battlefield.setView(view,{mode:view.screen==='battle'&&localAction ? 'ability' : 'move',action:selectedAction(),preview:view.canConfirm ? view.forecast : null,targetId:view.canConfirm?previewTargetId:null});
    battlefield.resize();
  }
  narrator?.mount($('#narrator-slot'));
  bindScreen();
  const partyStrip=$('.battle-hud .party-strip');
  if(partyStrip){
    partyStrip.scrollLeft=previousPartyScroll;
    if(previousPartySelection!==view.selectedUnitId){
      const selectedChip=partyStrip.querySelector('[data-unit][aria-pressed="true"]');
      if(selectedChip){
        const stripBounds=partyStrip.getBoundingClientRect(),chipBounds=selectedChip.getBoundingClientRect();
        if(chipBounds.left<stripBounds.left+6)partyStrip.scrollLeft-=stripBounds.left+6-chipBounds.left;
        else if(chipBounds.right>stripBounds.right-6)partyStrip.scrollLeft+=chipBounds.right-stripBounds.right+6;
      }
    }
  }
  if(enemySequence)setEnemyPlayback(true,enemyPhaseName);
  if(pinnedInspection&&view.screen==='battle')hoverCell(pinnedInspection.x,pinnedInspection.y);
  window.dungeonView = view;
}
const neighborhoodVisible = () => view.neighborhood?.active || view.neighborhood?.challenges?.some(c=>c.earned);
const gearFor = unitId => (view.equipment??[]).filter(gear=>gear.equippedUnitId===unitId);
const gearBonuses = gear => [gear.hpBonus?`${gear.hpBonus>0?'+':''}${gear.hpBonus} HP`:'',gear.manaBonus?`${gear.manaBonus>0?'+':''}${gear.manaBonus} MP`:'',gear.moveBonus?`${gear.moveBonus>0?'+':''}${gear.moveBonus} MOVE`:''].filter(Boolean).join(' · ') || 'No stat change';
function activeQuest() {return (view.quests??[]).find(quest=>!quest.complete)??view.quests?.[0];}
function questRows() {return (view.quests??[]).map(quest=>`<div class="quest-row${quest.complete?' complete':''}"><div><strong>${e(quest.label)}</strong><span>${quest.progress}/${quest.total}${quest.complete?' · Complete':''}</span></div><p>${e(quest.description)}</p><progress value="${quest.progress}" max="${quest.total}" aria-label="${e(quest.label)} progress"></progress></div>`).join('')||'<p class="small muted">Explore the passages and clear the next encounter.</p>';}
function renderQuestTracker() {if(view.customMap)return `<div class="quest-tracker" role="status"><span>OBJECTIVE</span> Defeat every enemy <b>${view.units.filter(u=>u.team==='enemy'&&u.hp>0).length} remaining</b></div>`;const quest=activeQuest();if(view.journey?.active)return `<button id="journey-objective-button" class="quest-tracker"><span>FLOOR ${view.journey.floorNumber}</span> ${e(view.journey.objective)} <b>Floor guide</b></button>`;if(view.expedition)return `<button id="expedition-objective-button" class="quest-tracker"><span>TRAINING</span> ${e(view.expedition.objective)} <b>Details / Return</b></button>`;if(view.scenario)return `<button id="scenario-objective-button" class="quest-tracker"><span>SCENARIO</span> ${e(view.scenario.objective)} <b>${view.scenario.progress??0}/${view.scenario.total??0}</b></button>`;return `<button id="quest-button" class="quest-tracker"><span>QUEST</span> ${e(quest?.label||'Find the encounter door')} <b>${quest?quest.progress+'/'+quest.total:''}</b></button>`;}
function renderSafeRoomStations(focused,advisor) {
  return `<section class="safe-stations" aria-label="Safe-room stations"><div class="safe-station-floor" aria-hidden="true">${Array.from({length:9},(_,index)=>{const x=index%3,y=Math.floor(index/3);return `<img src="assets/room-kit/floors/stone-${index%2?'b':'a'}.png" style="left:calc(50% + ${(x-y)*58-66}px);top:${25+(x+y)*29}px" alt="">`;}).join('')}<img class="safe-torch torch-one" src="assets/room-kit/props/torch.png" alt=""><img class="safe-torch torch-two" src="assets/room-kit/props/torch.png" alt=""></div><button id="station-rest" class="safe-station rest-station">${portrait(advisor,'station-advisor')}<span>REST <small>Mordecai</small></span></button><button class="safe-station equipment-station" data-equipment="${e(focused.id)}"><img src="assets/room-kit/props/chest.png" alt=""><span>EQUIPMENT <small>Open shared gear</small></span></button><button class="safe-station skills-station" data-skills="${e(focused.id)}"><img src="assets/room-kit/props/lever.png" alt=""><span>SKILLS <small>Abilities & unlocks</small></span></button><button id="quick-enter" class="safe-station exit-station" ${view.partyCount!==view.partyCapacity?'disabled':''}><img src="assets/room-kit/doors/exit.png" alt=""><span>ENTER DUNGEON <small>${view.partyCount}/${view.partyCapacity} deployed</small></span></button></section>`;
}
function renderCamp() {
  const focused=view.roster.find(r=>r.id===focusedRoster&&r.deployable!==false)??view.roster.find(r=>r.selected)??view.roster.find(r=>r.deployable!==false);
  focusedRoster=focused?.id;
  const progression=view.progression;
  const advisor=view.roster.find(r=>r.deployable===false)??{id:'crawler.mordecai',label:'Mordecai',classId:'class.cleric'};
  return `<section class="camp-screen safe-room" aria-labelledby="screen-title"><header class="safe-room-heading"><div><span class="section-label">MORDECAI’S SAFE ROOM</span><h1 id="screen-title">Rest. Equip. Prepare.</h1><p>A safe place between the cameras and the next fight.</p></div><div class="party-progression"><strong>PARTY LEVEL ${progression?.level??1}</strong><span>${progression?.xp??view.xp} XP${progression?.nextLevelXp?' / '+progression.nextLevelXp+' next level':''}</span><progress value="${progression?.xpIntoLevel??0}" max="${(progression?.xpIntoLevel??0)+(progression?.xpToNextLevel??1)||1}" aria-label="Party level progress"></progress></div></header>${renderSafeRoomStations(focused,advisor)}${renderAudienceHome(view)}${renderNeighborhoodStrip(view)}<nav class="safe-activities" aria-label="Safe-room activities"><button data-generated-adventure>New generated dungeon</button><button id="legacy-dungeon">Story encounters</button>${view.neighborhood?.standalone?'<button data-return-neighborhood>Return to preserved campaign</button>':'<button id="open-neighborhood-start">Play Over City neighborhood…</button>'}<button id="open-home" ${view.home?'':'disabled'}>Personal space · ${view.home?.gold??0} gold</button><button id="open-journey" ${view.journey?'':'disabled'}>${view.journey?.active?'Floor journey':'Start floors 1–8…'}</button><a class="button" href="codex.html" target="_blank" rel="noopener">Lore codex ↗</a><button id="open-skill-tree" ${view.skillTree?'':'disabled'}>Skill trees</button><button id="open-missions" ${view.expeditions?.length?'':'disabled'}>Mission board</button><button id="open-development" ${view.development?'':'disabled'}>Stats · Practice · Craft · Loot</button><button id="open-scenarios" ${view.scenarios?.length?'':'disabled'}>Scenario expeditions</button></nav><div class="safe-room-layout"><aside class="safe-advisor panel"><div class="advisor-head">${portrait(advisor,'advisor-portrait')}<div><h2>Mordecai</h2><span>Safe-room advisor</span></div></div><p>${e(view.safeRoom?.description||'Catch your breath. Check your gear and skills before heading back into the dungeon.')}</p><button id="rest-button" class="primary" ${view.safeRoom?.available===false?'disabled':''}>${view.safeRoom?.rested?'Rest again':'Rest & restore HP / MP'}</button><small>${view.safeRoom?.rested?'Party rested. Equipment and skills are ready to change.':'Rest restores the party’s actual health and mana.'}</small><details class="safe-quests"><summary>Quest journal · ${e(activeQuest()?.label||'Explore the dungeon')} ${activeQuest()?activeQuest().progress+'/'+activeQuest().total:''}</summary>${questRows()}</details></aside><details class="safe-party" ${rosterExpanded?'open':''}><summary class="panel-head"><h2>Manage your crawlers</h2><span>${view.partyCount}/${view.partyCapacity} deployed · classes & stats</span></summary><div class="safe-roster-grid">${view.roster.filter(r=>r.deployable!==false).map(r=>`<article class="safe-crawler${r.selected?' deployed':''}${r.id===focusedRoster?' focused':''}" data-crawler-card="${e(r.id)}"><button class="safe-crawler-select" data-roster="${e(r.id)}" aria-pressed="${r.id===focusedRoster}">${portrait(r)}<span><strong>${e(r.label)}</strong><small>Level ${r.level??progression?.level??1} · ${e(classLabel(r.classId))}</small><span class="deployment-label">${r.selected?'DEPLOYED':'RESERVE'}</span></span></button><div class="safe-crawler-stats"><span>HP <b>${r.hp}/${r.maxHp}</b></span><span>MP <b>${r.energy??r.maxEnergy??'—'}/${r.maxEnergy??'—'}</b></span><span>MOVE <b>${r.move??'—'}</b></span><span>XP <b>${progression?.xp??view.xp}</b></span></div><div class="safe-crawler-gear">${gearFor(r.id).map(gear=>`<span>${e(gear.label)}</span>`).join('')||'<span>No equipment</span>'}</div><div class="safe-crawler-buttons"><button data-equipment="${e(r.id)}">Equipment</button><button data-skills="${e(r.id)}">Skills</button><button data-character-sheet="${e(r.id)}">Sheet</button></div></article>`).join('')}</div><section class="safe-loadout panel"><div><strong>${e(focused?.label)} · Class & deployment</strong><p>Character skills stay with their crawler. Classes add their own abilities.</p></div><label class="field" for="class-select">CLASS${view.journey?.active&&!view.journey.classesUnlocked?'<small>Unlocks on Floor 3</small>':''}<input id="class-search" type="search" placeholder="Search classes…" aria-label="Search class choices"><select id="class-select" ${view.journey?.active&&!view.journey.classesUnlocked?'disabled':''}>${[...view.classes].sort((a,b)=>a.label.localeCompare(b.label)).map(klass=>`<option value="${e(klass.id)}" ${klass.id===focused?.classId?'selected':''} ${klass.enabled===false?'disabled':''}>${e(classChoiceLabel(klass))}${klass.enabled===false?' · Locked: '+e(klass.disabledReason||'Floor '+klass.minimumFloor):''}</option>`).join('')}</select></label><button id="toggle-party">${focused?.selected?'Move to reserve':'Deploy crawler'}</button></section><details class="panel inventory-strip"><summary>Shared consumables · ${view.items.reduce((sum,item)=>sum+item.count,0)} charges</summary><div class="tags">${view.items.map(item=>`<span class="tag">${e(item.label)} ×${item.count}</span>`).join('')}</div></details></details></div>${renderCampModal()}</section>`;
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
  const order=view.partyOrder?.length ? [...players].sort((a,b)=>(view.partyOrder.includes(a.id)?view.partyOrder.indexOf(a.id):999)-(view.partyOrder.includes(b.id)?view.partyOrder.indexOf(b.id):999)) : players;
  return `<div class="party-strip" style="--party-columns:${Math.min(4,players.length)}" aria-label="Crawler turn order">${order.map(u=>`<button class="party-chip${u.selected?' active':''}${u.finished?' turn-spent':' turn-ready'}${u.duplicateSourceId?' clockwork-chip':''}" data-unit="${e(u.id)}" ${u.hp<=0?'disabled':''} aria-pressed="${u.selected}">${portrait(u)}<span><strong>${e(copyLabel(u))}</strong><small>${u.hp<=0?'Fallen':u.finished?'Turn ended':u.acted?'Action spent':u.selected?'Selected': 'Ready'}${u.duplicateSourceId?' · '+u.duplicateRounds+'r':''}</small></span></button>`).join('')}<span class="party-phase ${view.phase==='player'?'player-phase':'hostile-phase'}">${view.phase==='player'?'PARTY TURN':'ENEMY TURN'} <b>${players.filter(u=>u.hp>0&&!u.finished).length}/${players.filter(u=>u.hp>0).length} ready</b></span><span class="party-round">ROUND ${view.round}</span></div>`;
}
function renderBattle() {
  return `<section class="battle-screen" aria-label="Tactical dungeon"><div class="objective-banner"><span class="objective-seal" aria-hidden="true"></span><div><small>${view.customMap?'CUSTOM DUNGEON':view.expedition?'TRAINING EXPEDITION':view.scenario?'SCENARIO':'FLOOR '+String(view.encounterIndex+1).padStart(2,'0')}</small><h2 id="screen-title">${e(view.customMap?.label || view.objective || 'OPEN THE EXIT')}</h2></div></div>${view.neighborhood?.standalone?`<nav class="neighborhood-battle-controls" aria-label="Neighborhood"><button data-open-neighborhood>Neighborhood journal</button><button data-return-neighborhood>Return to campaign</button></nav>`:renderQuestTracker()}<div id="enemy-phase-banner" class="enemy-phase-banner" hidden role="status">ENEMY TURN · Watch their movement</div><div id="battlefield-slot" class="battlefield-slot">${renderWorldControls()}${renderBoard()}<div id="map-inspect" class="map-inspect" hidden></div></div><div class="battle-guidance" role="status">${e(view.message || 'Select a crawler. Move or act in either order.')}</div><div class="battle-hud">${renderParty()}<section class="action-dock" aria-label="Selected crawler and actions">${renderInspector(unit())}</section><div id="narrator-slot" class="narrator-slot"></div></div>${renderAudienceSummary(view)}${renderDrawer()}${actionChooser?renderActionDialog():''}${endTurnActor?renderEndTurnDialog():''}${detailedForecast?renderForecastDialog():''}</section>`;
}
function renderWorldControls() {
  return `<div class="world-controls" aria-label="Battlefield camera"><button id="zoom-in" aria-label="Zoom in">+</button><button id="zoom-out" aria-label="Zoom out">−</button><button id="rotate-left" aria-label="Rotate left 90 degrees">↶ 90°</button><span id="compass-label">${e(battlefield?.getRotationLabel?.()||'North view')}</span><button id="rotate-right" aria-label="Rotate right 90 degrees">90° ↷</button><button id="center-map">Center</button><button id="skip-animation" ${animating?'':'hidden'}>Skip animation</button></div>`;
}
function enemyAbilities(enemy){const ids=enemy.abilityIds??content.classes.find(c=>c.id===enemy.classId)?.abilityIds??[];return ids.map(id=>content.abilities.find(a=>a.id===id)).filter(Boolean);}
function renderEnemyInfo(enemy){return `<dialog id="enemy-info-dialog" aria-labelledby="enemy-info-title"><div class="dialog-head"><h2 id="enemy-info-title">${e(enemy.label)}</h2><button id="close-enemy-info" aria-label="Close enemy details">×</button></div><div class="modal-body"><p>HP ${enemy.hp}/${enemy.maxHp} · MP ${enemy.energy}/${enemy.maxEnergy} · MOVE ${enemy.effectiveMove??enemy.move}</p><div class="tags">${tags(enemy.tags)}</div><div class="development-cards">${enemyAbilities(enemy).map(a=>`<article><h3>${e(a.label)}</h3><p>${e(abilityDescription(a))}</p><small>${a.cost} MP · Range ${a.range} · ${e(a.target)}</small></article>`).join('')||'<p>No authored class abilities available.</p>'}</div></div><div class="modal-actions"><button id="done-enemy-info">Back to battlefield</button></div></dialog>`;}
function hoverCell(x,y) {
  if(x==null&&pinnedInspection&&view.screen==='battle'){x=pinnedInspection.x;y=pinnedInspection.y;}
  inspectPosition = x == null ? null : {x,y};
  const box=$('#map-inspect'); if(!box) return;
  if(view.screen==='explore') { const point=view.exploration.points.find(p=>p.x===x&&p.y===y);box.hidden=!point;if(point)box.innerHTML=`<strong>${e(point.label)}</strong><span>${e(point.description)}</span>`;return; }
  const target=view.units.find(u=>u.x===x&&u.y===y&&u.hp>0);
  const tile=view.tiles.find(t=>t.x===x&&t.y===y);
  box.hidden=!target&&!tile?.tags?.length;
  if(!box.hidden) box.innerHTML=target?`<strong>${e(target.label)}</strong><span>HP ${target.hp}/${target.maxHp} · ${e(target.team)}</span>${tags(target.tags)}${target.team==='enemy'?`<small>${enemyAbilities(target).slice(0,2).map(a=>e(a.label)).join(' · ')}</small><button id="inspect-enemy-kit">Inspect abilities & stats</button>`:''}`:`<strong>Terrain</strong>${tags(tile.tags)}`;
  $('#inspect-enemy-kit')?.addEventListener('click',()=>{enemySheetId=target.id;render();});
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
  const points=map.points.filter(p=>p.canInteract&&!p.claimed&&!view.neighborhood?.interactions.some(i=>i.pointId===p.id));
  return `<section class="exploration-screen square-exploration"><div class="objective-banner"><span class="objective-seal" aria-hidden="true"></span><div><small>EXPLORE THE FLOOR</small><h2>${e(map.label)}</h2></div></div>${view.generatedDungeon?'<div class="quest-tracker">'+(view.generatedDungeon.cleared?'Enemies cleared · Walk to the exit and press E.':'Explore freely · Nearby enemies start combat.')+'</div>':view.neighborhood?.active?renderNeighborhoodStrip(view):renderQuestTracker()}<div id="battlefield-slot" class="battlefield-slot">${renderWorldControls()}<div class="board accessible-board" style="--columns:${map.width};--rows:${map.height}" aria-label="Exploration map">${map.tiles.map(t=>`<button data-explore-cell="${t.x},${t.y}" ${!t.reachable?'disabled':''} aria-label="${t.x},${t.y}: ${!t.revealed?'unexplored':t.blocked?'wall':'passage'}"></button>`).join('')}</div><div id="map-inspect" class="map-inspect" hidden></div></div><div class="exploration-hud"><div class="walk-pad" aria-label="Walk through the dungeon"><button data-walk="north" aria-label="Walk up">▲</button><button data-walk="west" aria-label="Walk left">◀</button><button data-walk="south" aria-label="Walk down">▼</button><button data-walk="east" aria-label="Walk right">▶</button></div><div class="explore-party">${view.roster.filter(r=>r.selected).map(r=>portrait(r)).join('')}</div><div class="explore-copy"><strong>${e(points[0]?.label || (view.generatedDungeon ? view.generatedDungeon.cleared ? 'Reach the exit' : 'Explore the dungeon' : 'Find the encounter door'))}</strong><p>${e(points[0]?.description || 'Hold WASD / arrow keys or the direction pad to walk. E / Space interacts. Combat stays turn-based.')}</p></div><div class="explore-interactions">${points.map(point=>`<button class="primary" data-explore-interact="${e(point.id)}">${point.kind==='encounter'?'Enter':'Investigate'} ${e(point.label)}</button>`).join('')}${neighborhoodVisible()?'<button data-open-neighborhood>Room choices & journal</button>':''}<button id="return-camp">Return to Mordecai</button></div><div id="narrator-slot" class="narrator-slot"></div></div></section>`;
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
  const availableActions=view.abilities.map(abilityPresentation);
  const primaryActions=availableActions.slice(0,2);
  const chosenAbility=availableActions.find(a=>a.id===localAction?.abilityId);
  if(chosenAbility&&!primaryActions.includes(chosenAbility))primaryActions.splice(1,1,chosenAbility);
  const changes=view.forecast.filter(f=>f.beforeHp!==f.afterHp||f.beforeEnergy!==f.afterEnergy||JSON.stringify(f.beforeTags)!==JSON.stringify(f.afterTags));
  const target=changes.find(f=>f.targetId!==view.selectedUnitId&&f.beforeHp!==f.afterHp) ?? changes.find(f=>f.targetId!==view.selectedUnitId) ?? changes[0];
  return `<div class="hud-crawler">${selected?`<button id="open-character-sheet" class="hud-character-button" aria-label="Open ${e(selected.label)} character sheet">${portrait(selected,'hud-portrait')}<span>Character sheet</span></button>`:''}<div class="hud-stats"><strong>${e(selected?copyLabel(selected):'SELECT CRAWLER')}</strong><small class="hud-class">${e(selected?.duplicateSourceId?'Clockwork · '+selected.duplicateRounds+' rounds':classLabel(selected?.classId))}</small><div class="hud-meter hp"><span>HP</span><b>${selected?.hp??0}/${selected?.maxHp??0}</b><i style="--fill:${selected?selected.hp/selected.maxHp*100:0}%"></i></div><div class="hud-meter en"><span>MP</span><b>${selected?.energy??0}/${selected?.maxEnergy??0}</b><i style="--fill:${selected?selected.energy/selected.maxEnergy*100:0}%"></i></div><div class="hud-move">MOVE <b>${selected?.moved||selected?.finished?0:selected?.effectiveMove??selected?.move??'—'}</b> <small>${selected?.finished?'TURN ENDED':selected?.moved?'SPENT':'TILES LEFT'}</small><span class="hud-action-budget">ACTION <b>${selected?.acted||selected?.finished?0:1}</b></span></div><div class="hud-statuses">${(selected?.statuses??[]).map(status=>`<span class="tag" title="${e(displayLog(status.source))}">${e(shortTag(status.tag))} ${status.remainingRounds}r</span>`).join('')}</div></div></div><div class="hud-actions"><div class="chosen-action-heading"><span>${localAction?'SELECTED ACTION':'MOVEMENT'}</span><strong>${e(action?.label||'Move')}</strong><small>${localAction?`${action?.cost??0} Mana · Range ${action?.range??0} · ${action?.targetIds?.length??0} targets`:'Choose a blue tile · No Mana cost'}</small></div><button id="open-actions" class="action-picker-button"><img src="assets/ui-kit/skills.png" class="ui-inline-icon" alt="">All abilities (${view.abilities.length}) <span>Open action book & items</span></button><div class="hud-action-list"><button id="move-mode" class="hud-action${!localAction?' active':''}" ${!view.canMove&&!localAction?'disabled':''}>${actionIcon(4)}<strong>MOVE</strong><small>${selected?.moved?'Spent':`${selected?.effectiveMove??selected?.move??'—'} tiles`}</small></button>${primaryActions.map((a,index)=>`<button class="hud-action category-${actionCategory(a).key}${localAction?.abilityId===a.id?' active':''}" data-ability="${e(a.id)}" ${!a.enabled?'disabled':''} aria-label="${e(a.label+'. '+a.description+'. '+(a.disabledReason||''))}" title="${e(a.label+' · '+a.description+' · '+a.cost+' MP · Range '+a.range+' · '+(a.disabledReason||a.targetIds.length+' legal targets'))}">${actionIcon(abilityIcon(a))}<strong>${e(hudActionLabel(a))}</strong><small>${a.formChooser?'Choose form · 1 action':a.cost+' MP · '+a.range+' RNG'}</small>${a.disabledReason?`<small class="action-reason">${e(a.disabledReason)}</small>`:''}</button>`).join('')}<button class="hud-action category-item${localAction?.itemId?' active':''}" data-drawer="items">${actionIcon(7)}<strong>ITEMS</strong><small>${localAction?.itemId?e(selectedAction()?.label)+' ×'+(selectedAction()?.count??0):view.items.reduce((sum,i)=>sum+i.count,0)+' charges'}</small></button></div><p class="action-caption">${e(action?.description || (selected?.finished?'Choose another crawler.':selected?.acted?'Action spent. Move or end this character’s turn.':'Move or act in either order.'))}${action?.disabledReason?' · '+e(action.disabledReason):''}</p></div><div class="hud-target" aria-live="polite">${view.canConfirm?`<div class="target-forecast"><strong>${e((target?forecastLabel(target):null)||action?.label||'TARGET')}</strong>${target&&target.beforeHp!==target.afterHp?`<span class="target-hp">HP <b>${isSummonForecast(target)?target.afterHp:target.beforeHp+' → '+target.afterHp}</b></span>`:''}${target?tags(target.afterTags.filter(t=>!target.beforeTags.includes(t))):''}<small>${e(action?.label||'Action')} · ${action?.cost??0} MP</small></div><div class="forecast-buttons"><button id="cancel-forecast">Cancel</button><button id="confirm-forecast" class="primary">Confirm</button><button id="review-forecast" class="details-button" aria-label="Detailed forecast">Details</button></div>`:`${localAction?renderAbilityDetails(action,content):'<strong>CHOOSE YOUR TARGET</strong><small>Choose Move or an ability, then tap a highlighted tile.</small>'}${localAction?'<button id="cancel-forecast">Cancel targeting</button>':''}`}<button id="end-turn" class="end-character" ${!canEndCharacter()?'disabled':''}><img src="assets/ui-kit/wait.png" class="ui-inline-icon" alt="">End character turn →</button><button data-drawer="log" class="hud-log">Combat log</button></div>`;
}
function abilitySource(id,unitId) {
  if(view.units.find(u=>u.id===unitId)?.duplicateSourceId)return 'Clockwork copy';
  const crawler=view.roster.find(r=>r.id===unitId);
  if(crawler?.innateAbilityIds?.includes(id))return 'Character';
  if(gearFor(unitId).some(gear=>gear.abilityIds?.includes(id)))return 'Equipment';
  const unlock=view.progression?.skills?.find(skill=>skill.abilityId===id&&skill.unlocked&&(!skill.unitId||skill.unitId===unitId));
  if(unlock)return `Personal · Level ${unlock.level}${unlock.minimumFloor>1?' · Floor '+unlock.minimumFloor:''}`;
  return 'Class';
}
function renderActionDialog() {
  const actor=unit();
  const lockedPersonal=(view.progression?.skills??[]).filter(skill=>!skill.unlocked&&(!skill.unitId||skill.unitId===actor?.id));
  const lockedPersonalCards=lockedPersonal.length?`<section class="locked-personal-skills"><h3>Upcoming personal abilities</h3><div class="modal-action-grid">${lockedPersonal.map(skill=>{const a=content.abilities.find(a=>a.id===skill.abilityId);return `<article class="locked-personal-card">${actionIcon(abilityIcon(a??{id:skill.abilityId}))}<div><strong>${e(skill.label??a?.label)}</strong><span class="skill-source">Locked · Level ${skill.level}${skill.minimumFloor>1?' · Floor '+skill.minimumFloor:''}</span><p>${e(abilityDescription(a))}</p><small>${a?.cost??0} MP · range ${a?.range??0} · ${e(a?.target??'self')}</small></div></article>`;}).join('')}</div></section>`:'';
  const abilityButton=(a,item=false)=>{ const category=actionCategory(a,item);const available=item ? a.count>0&&view.canAct : a.enabled; const reason=a.disabledReason || (!a.targetIds.length?'No legal target in range · move first':'');return `<button class="modal-action-card category-${category.key}${(item?localAction?.itemId:localAction?.abilityId)===a.id?' active':''}" ${item?'data-modal-item':'data-modal-ability'}="${e(a.id)}" ${available?'':'disabled'}>${actionIcon(item?7:abilityIcon(a))}<span><strong>${e(a.label)}${item?' ×'+a.count:''}</strong><span class="category-label">${category.label} · ${item?'Shared item':abilitySource(a.id,view.selectedUnitId)}</span><small>${a.formChooser?'Choose form · 1 action':(item?'1 action':a.cost+' MP')+' · range '+a.range+' · '+e(a.target)}</small><p>${e(a.description)}</p><small class="${reason?'availability-warning':'availability-ready'}">${e(reason||a.targetIds.length+' legal target'+(a.targetIds.length===1?'':'s'))}</small></span></button>`;};
  return `<dialog id="action-dialog" aria-labelledby="action-title"><div class="dialog-head"><div><span class="section-label">${e(actor?.label||'Crawler')} · ${e(classLabel(actor?.classId))}</span><h2 id="action-title">Choose an action</h2></div><button id="close-actions" class="icon-button" aria-label="Close action choices">×</button></div><div class="modal-body"><div class="action-modal-stats"><span>HP ${actor?.hp}/${actor?.maxHp}</span><span>MP ${actor?.energy}/${actor?.maxEnergy}</span><span>Move ${actor?.effectiveMove??actor?.move??0}${actor?.moved?' · spent':''}</span></div><p class="modal-intro">Choose an ability, then select a highlighted target on the map. Review the exact result before confirming.</p><button id="modal-move" class="modal-move" ${view.canMove?'':'disabled'}>${actionIcon(4)}<span><strong>Move</strong><small>${view.canMove?'Choose a blue path. No action or mana cost.':'Movement is spent for this character.'}</small></span></button><div class="modal-action-grid">${view.abilities.map(abilityPresentation).map(a=>abilityButton(a)).join('')}</div>${lockedPersonalCards}<details class="modal-item-section" ${localAction?.itemId?'open':''}><summary>Shared items · ${view.items.reduce((sum,i)=>sum+i.count,0)} charges</summary><div class="modal-action-grid">${view.items.map(a=>abilityButton(a,true)).join('')}</div></details></div><div class="modal-actions"><button id="cancel-actions">Back to map</button><button id="actions-end-turn">End character turn…</button></div></dialog>`;
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
function renderSponsorForecast() {
  const audience=view.audience;
  if(!audience || (!audience.forecastFavor && !audience.forecastRewards?.length))return '';
  return `<aside class="sponsor-forecast"><strong>SPONSOR DELIVERY ON CONFIRM</strong>${audience.forecastFavor?`<span>+${audience.forecastFavor} AI Favor</span>`:''}${(audience.forecastRewards??[]).map(reward=>`<span>+${reward.count} ${e(view.items.find(item=>item.id===reward.itemId)?.label||reward.itemId)}</span>`).join('')}<small>These rewards arrive only after you confirm the action.</small></aside>`;
}
function renderForecastDialog() {
  if (!view.canConfirm) return '';
  const action = selectedAction();
  return `<dialog id="forecast-dialog" class="forecast-dialog" aria-labelledby="forecast-title"><div class="dialog-head"><div><span class="section-label">EXACT ACTION FORECAST</span><h2 id="forecast-title">${e(action?.label || 'Review action')}</h2></div><button class="icon-button" id="close-forecast" aria-label="Close forecast details">×</button></div><div class="modal-body">${renderSponsorForecast()}${localAction?.itemId&&!favorPreview?renderFavorControls(view,{itemId:localAction.itemId,unitId:view.selectedUnitId,targetId:previewTargetId}):''}<div class="forecast-cost">${actionIcon(abilityIcon(action||{id:''}))}<strong>${action?.cost??0} Mana <span>· Range ${action?.range??0}</span></strong></div><p class="modal-intro">${e(action?.description || 'Review the exact result before spending this crawler’s action.')}</p><div class="forecast-detail-list">${view.forecast.filter(f => f.beforeHp !== f.afterHp || f.beforeEnergy !== f.afterEnergy || JSON.stringify(f.beforeTags) !== JSON.stringify(f.afterTags)||f.beforeMaxHp!==f.afterMaxHp||f.beforeMaxEnergy!==f.afterMaxEnergy||f.beforeMove!==f.afterMove).map(f => `<section class="forecast-detail"><h3>${e(forecastLabel(f))}</h3>${isSummonForecast(f)?`<div class="forecast-number"><span>Spawn tile</span><b>${String.fromCharCode(65+f.afterX)}${f.afterY+1}</b></div>`:''}${f.beforeHp !== f.afterHp ? `<div class="forecast-number"><span>${isSummonForecast(f)?'Summoned HP':'Health'}</span><b>${isSummonForecast(f)?f.afterHp:f.beforeHp+' → '+f.afterHp}</b></div>` : ''}${f.beforeMaxHp!==undefined&&f.beforeMaxHp!==f.afterMaxHp?`<div class="forecast-number"><span>Maximum HP</span><b>${f.beforeMaxHp} → ${f.afterMaxHp}</b></div>`:''}${f.beforeMaxEnergy!==undefined&&f.beforeMaxEnergy!==f.afterMaxEnergy?`<div class="forecast-number"><span>Maximum MP</span><b>${f.beforeMaxEnergy} → ${f.afterMaxEnergy}</b></div>`:''}${f.beforeMove!==undefined&&f.beforeMove!==f.afterMove?`<div class="forecast-number"><span>Movement</span><b>${f.beforeMove} → ${f.afterMove}</b></div>`:''}${f.beforeEnergy !== f.afterEnergy ? `<div class="forecast-number"><span>Mana</span><b>${f.beforeEnergy} → ${f.afterEnergy}</b></div>` : ''}<div class="tags">${f.afterTags.filter(t => !f.beforeTags.includes(t)).map(t => `<span class="tag good">+ ${e(shortTag(t))}</span>`).join('')}${f.beforeTags.filter(t => !f.afterTags.includes(t)).map(t => `<span class="tag">− ${e(shortTag(t))}</span>`).join('')}</div></section>`).join('') || '<p>The action changes terrain or status without changing health or mana.</p>'}</div><ol class="forecast-chain">${view.log.filter(l => l.startsWith('Forecast:')).slice(-8).map(l => `<li>${e(displayLog(l.slice(10)))}</li>`).join('')}</ol><p class="small muted">${favorPreview?'Confirm spends 1 AI Favor and one supply. No action or movement is spent. Cancel spends nothing.':'Confirm spends one action. Movement is independent: act or move first, then end this character’s turn. Cancel spends nothing.'}</p></div><div class="modal-actions"><button id="detail-cancel-forecast">Cancel action <span class="key">Esc</span></button><button id="detail-confirm-forecast" class="primary">Confirm ${favorPreview?'AI Favor · ':''}${e(action?.label||'action')}</button></div></dialog>`;
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
  return `<section class="outcome-layout" aria-labelledby="screen-title"><div class="outcome-header"><div><h2 id="screen-title">Room cleared. Cameras rolling.</h2><p>${e(view.encounterName)} · Encounter ${view.encounterIndex + 1} complete</p></div><div class="xp-value">${view.xp} XP<small>TOTAL RUN EXPERIENCE</small></div></div><div class="reward-layout"><div><span class="section-label">${view.rewards.length ? 'PICK ONE SPONSOR REWARD' : 'SPONSOR REWARD CLAIMED'}</span><div class="reward-list">${view.rewards.map((r, i) => `<button data-reward="${e(r.id)}" class="reward-button" ${chosenReward ? 'disabled' : ''}><span class="reward-icon" aria-hidden="true">${['◇', '▱', '✦'][i % 3]}</span><span><strong>${e(r.label)}</strong><small>${e(r.description)}</small></span></button>`).join('') || '<div class="panel panel-body"><span class="tag good">DELIVERY RECEIVED</span><p class="small muted" style="margin-top:12px">Your sponsor reward is in the shared supplies. Ready for the next room.</p></div>'}</div></div><aside class="panel sponsor-copy"><h3>SPONSOR TRANSMISSION</h3><blockquote>“A surprising number of you are still alive. We’ve sent a little something.”</blockquote><p>${e(view.message || (view.rewards.length ? 'Choose a reward for your party, then head to camp before the next encounter.' : 'Delivery received. Continue when you’re ready.'))}</p><button id="continue-button" class="primary" ${view.rewards.length ? 'disabled' : ''}>${view.journey?.active ? (view.journey.floorNumber===8?'Finish playable journey':'Descend to next floor') : view.encounterIndex + 1 >= view.encounterCount ? 'Finish the floor' : 'Return to camp'} <span aria-hidden="true">→</span></button><p class="small">One reward per encounter. Your run saves automatically.</p></aside></div>${renderSurvivors()}${renderLog()}</section>`;
}
function renderEnding() {
  if(view.scenario)return renderScenarioOutcome(false);
  const complete = view.screen === 'complete';
  return `<section class="outcome-layout" aria-labelledby="screen-title"><div class="center-outcome"><div class="trophy" aria-hidden="true">${complete ? '♜' : '†'}</div><h2 id="screen-title">${complete ? (view.journey?.complete?'Eight floors. Still standing.':'The floor is yours.') : 'The dungeon wins. For now.'}</h2><p>${complete ? `${view.journey?.complete?'All eight playable floors cleared. Floors 9–18 remain locked.':view.customMap?'Your workshop room is clear.':'All three encounters cleared.'} Your crawlers earned ${view.xp} XP, exploited the elements, and made it back in one piece. The audience will want a sequel.` : 'Your deployed crawlers have fallen. Retry the encounter with the same starting party and supplies, or rebuild from the beginning.'}</p><div class="tags" style="justify-content:center"><span class="tag gold">${complete ? (view.journey?.complete?'FLOORS 1–8 COMPLETE':'FLOOR 01 COMPLETE') : 'PARTY DEFEATED'}</span><span class="tag">${view.xp} XP EARNED</span></div><div class="button-row">${!complete ? '<button class="primary" id="retry-button">Retry encounter</button>' : '<button id="open-scenarios" class="primary">Play boss scenarios</button>'}<button data-generated-adventure class="primary">Generate another dungeon</button><button id="ending-new-run" ${complete ? 'class="primary"' : ''}>Start a new run</button></div><button class="quiet" id="ending-export">Export this run</button></div>${renderSurvivors()}${renderLog()}</section>`;
}
function bindProgressionMenus(){
  const closeEnemy=()=>{enemySheetId=null;render();};$('#close-enemy-info')?.addEventListener('click',closeEnemy);$('#done-enemy-info')?.addEventListener('click',closeEnemy);if($('#enemy-info-dialog')){openDialog('#enemy-info-dialog');$('#enemy-info-dialog').addEventListener('cancel',event=>{event.preventDefault();closeEnemy();});}
  $('#open-skill-tree')?.addEventListener('click',()=>{skillTreeOpen=true;render();});
  const closeTree=async()=>{if(view.skillTree?.canConfirm)await command('cancel_skill_node',{}, {save:false});skillTreeOpen=false;render();$('#open-skill-tree')?.focus();};
  $('#close-skill-tree')?.addEventListener('click',closeTree);$('#done-skill-tree')?.addEventListener('click',closeTree);
  if($('#skill-tree-dialog')){openDialog('#skill-tree-dialog');$('#skill-tree-dialog').addEventListener('cancel',event=>{event.preventDefault();closeTree();});}
  document.querySelectorAll('[data-tree-kind]').forEach(button=>button.addEventListener('click',async()=>{if(view.skillTree.canConfirm)await command('cancel_skill_node',{}, {save:false});skillTreeKind=button.dataset.treeKind;skillTreeNode=null;render();}));
  $('#skill-tree-crawler')?.addEventListener('change',async event=>{const id=event.target.value;if(view.skillTree.canConfirm)await command('cancel_skill_node',{}, {save:false});skillTreeUnit=id;skillTreeNode=null;render();});
  document.querySelectorAll('[data-skill-node]').forEach(button=>button.addEventListener('click',async()=>{const id=button.dataset.skillNode;if(view.skillTree.canConfirm)await command('cancel_skill_node',{}, {save:false});skillTreeNode=id;render();$('#skill-node-details')?.scrollIntoView({block:'nearest'});}));
  $('#preview-skill-node')?.addEventListener('click',event=>command('preview_skill_node',{unitId:event.currentTarget.dataset.unit,nodeId:event.currentTarget.dataset.node},{save:false}));
  $('#confirm-skill-node')?.addEventListener('click',()=>command('confirm_skill_node'));
  $('#cancel-skill-node')?.addEventListener('click',()=>command('cancel_skill_node',{}, {save:false}));
  $('#open-missions')?.addEventListener('click',()=>{missionOpen=true;render();});
  const closeMissions=()=>{missionOpen=false;render();$('#open-missions')?.focus();};
  $('#close-missions')?.addEventListener('click',closeMissions);$('#done-missions')?.addEventListener('click',closeMissions);
  if($('#mission-dialog')){openDialog('#mission-dialog');$('#mission-dialog').addEventListener('cancel',event=>{event.preventDefault();closeMissions();});}
  document.querySelectorAll('[data-mission-briefing]').forEach(button=>button.addEventListener('click',()=>{missionId=button.dataset.missionBriefing;render();$('#mission-briefing')?.scrollIntoView({block:'nearest'});}));
  $('#start-mission')?.addEventListener('click',event=>{missionOpen=false;command('expedition_start',{targetId:event.currentTarget.dataset.mission});});
  $('#expedition-objective-button')?.addEventListener('click',()=>{expeditionDetails=true;render();});
  const closeExpedition=()=>{expeditionDetails=false;render();};
  $('#close-expedition')?.addEventListener('click',closeExpedition);$('#done-expedition')?.addEventListener('click',closeExpedition);
  if($('#expedition-dialog')){openDialog('#expedition-dialog');$('#expedition-dialog').addEventListener('cancel',event=>{event.preventDefault();closeExpedition();});}
  $('#return-expedition')?.addEventListener('click',()=>{expeditionDetails=false;command('expedition_return');});
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
  $('#practice-ability')?.addEventListener('change',event=>{practiceAbility=event.target.value;render();});
  $('#practice-rank')?.addEventListener('change',event=>{practiceRank=Number(event.target.value);render();});
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
function bindHome(){
 const homeOperation=action=>action+'_home_'+(view.home?.forecast?.type==='membership'?'membership':view.home?.forecast?.type==='training'?'training':'upgrade');
 $('#open-home')?.addEventListener('click',()=>{homeOpen=true;render();});
 const close=async()=>{if(view.home?.canConfirm)await command(homeOperation('cancel'),{}, {save:false});homeOpen=false;render();$('#open-home')?.focus();};
 $('#close-home')?.addEventListener('click',close);$('#done-home')?.addEventListener('click',close);
 if($('#home-dialog')){openDialog('#home-dialog');$('#home-dialog').addEventListener('cancel',event=>{event.preventDefault();close();});}
 $('#home-social-room')?.addEventListener('click',()=>document.querySelector('#home-dialog .home-social')?.scrollIntoView({block:'start',behavior:'auto'}));
 document.querySelectorAll('[data-home-room]').forEach(button=>button.addEventListener('click',()=>{homeRoomId=button.dataset.homeRoom;render();$('#home-room-details')?.scrollIntoView({block:'nearest'});}));
 document.querySelectorAll('[data-home-upgrade]').forEach(button=>button.addEventListener('click',async()=>{await command('preview_home_upgrade',{targetId:button.dataset.homeUpgrade},{save:false});$('#home-purchase-forecast')?.scrollIntoView({block:'nearest'});}));
 $('#confirm-home-purchase')?.addEventListener('click',()=>command(homeOperation('confirm')));
 $('#cancel-home-purchase')?.addEventListener('click',()=>command(homeOperation('cancel'),{}, {save:false}));
 document.querySelectorAll('[data-home-membership-unit]').forEach(button=>button.addEventListener('click',async()=>{await command('preview_home_membership',{unitId:button.dataset.homeMembershipUnit,targetId:button.dataset.homeMembershipClub},{save:false});$('#home-purchase-forecast')?.scrollIntoView({block:'nearest'});}));
 document.querySelectorAll('[data-home-training-unit]').forEach(button=>button.addEventListener('click',async()=>{await command('preview_home_training',{unitId:button.dataset.homeTrainingUnit,abilityId:button.dataset.homeTrainingAbility},{save:false});$('#home-purchase-forecast')?.scrollIntoView({block:'nearest'});}));
}
function bindJourney(){
 const open=()=>{journeyOpen=true;journeyConfirmStart=false;render();};
 $('#open-journey')?.addEventListener('click',open);$('#battle-journey')?.addEventListener('click',open);$('#journey-objective-button')?.addEventListener('click',open);
 const close=()=>{journeyOpen=false;journeyConfirmStart=false;render();};
 $('#close-journey')?.addEventListener('click',close);$('#done-journey')?.addEventListener('click',close);
 if($('#journey-dialog')){openDialog('#journey-dialog');$('#journey-dialog').addEventListener('cancel',event=>{event.preventDefault();close();});}
 $('#review-journey-start')?.addEventListener('click',()=>{journeyConfirmStart=true;render();$('#journey-start-warning')?.scrollIntoView({block:'nearest'});});
 $('#cancel-journey-start')?.addEventListener('click',()=>{journeyConfirmStart=false;render();});
 $('#journey-export')?.addEventListener('click',exportSave);
 $('#confirm-journey-start')?.addEventListener('click',()=>{journeyOpen=false;journeyConfirmStart=false;focusedRoster=null;command('start_journey');});
 $('#journey-bypass')?.addEventListener('click',()=>{journeyOpen=false;command('journey_bypass');});
 document.querySelectorAll('[data-capture]').forEach(button=>button.addEventListener('click',()=>playerInput(async()=>{localAction=null;captureTargetId=button.dataset.capture;previewTargetId=button.dataset.capture;detailedForecast=true;await command('preview_capture',{unitId:view.selectedUnitId,targetId:button.dataset.capture},{save:false});})));
}
function bindNeighborhood(){
 const close=async()=>{if(view.neighborhood?.forecast)await command('cancel_neighborhood',{}, {save:false});neighborhoodOpen=false;render();$('[data-open-neighborhood]')?.focus();};
 document.querySelectorAll('[data-open-neighborhood]').forEach(b=>b.addEventListener('click',()=>{neighborhoodOpen=true;render();}));
 for(const id of ['close-neighborhood','done-neighborhood'])$('#'+id)?.addEventListener('click',close);
 if($('#neighborhood-dialog')){openDialog('#neighborhood-dialog');$('#neighborhood-dialog').addEventListener('cancel',ev=>{ev.preventDefault();close();});}
 $('#neighborhood-crawler')?.addEventListener('change',ev=>{neighborhoodUnit=ev.target.value;render();});
 document.querySelectorAll('[data-neighborhood-option]').forEach(b=>b.addEventListener('click',()=>{
 const option=view.neighborhood.interactions.find(i=>i.id===b.dataset.neighborhoodInteraction)?.options.find(o=>o.id===b.dataset.neighborhoodOption);
 const chosen=$('#neighborhood-crawler').value;
 neighborhoodUnit=option?.eligibleUnitIds?.length&&!option.eligibleUnitIds.includes(chosen)?option.eligibleUnitIds[0]:chosen;
 return command('preview_neighborhood',{targetId:b.dataset.neighborhoodInteraction,nodeId:b.dataset.neighborhoodOption,unitId:neighborhoodUnit},{save:false});
 }));
 const cancel=()=>command('cancel_neighborhood',{}, {save:false});
 for(const id of ['cancel-neighborhood','close-neighborhood-confirm'])$('#'+id)?.addEventListener('click',cancel);
 if($('#neighborhood-confirm-dialog')){openDialog('#neighborhood-confirm-dialog');$('#cancel-neighborhood').focus();$('#neighborhood-confirm-dialog').addEventListener('cancel',ev=>{ev.preventDefault();cancel();});}
 document.querySelectorAll('[data-return-neighborhood]').forEach(b=>b.addEventListener('click',()=>{neighborhoodOpen=false;command('return_neighborhood');}));
 $('#confirm-neighborhood')?.addEventListener('click',()=>command('confirm_neighborhood'));
 $('#open-neighborhood-start')?.addEventListener('click',()=>{neighborhoodStart=true;render();});
 const closeStart=()=>{neighborhoodStart=false;render();};
 $('#cancel-neighborhood-start')?.addEventListener('click',closeStart);
 if($('#neighborhood-start-dialog')){openDialog('#neighborhood-start-dialog');$('#neighborhood-start-dialog').addEventListener('cancel',ev=>{ev.preventDefault();closeStart();});}
 $('#confirm-neighborhood-start')?.addEventListener('click',()=>{neighborhoodStart=false;command('start_neighborhood');});
}
function bindScreen() {
  document.querySelectorAll('#open-audience,[data-open-audience]').forEach(button=>button.addEventListener('click',()=>{audienceOpen=true;render();}));
  const closeAudience=()=>{audienceOpen=false;render();};
  for(const id of ['close-audience','done-audience'])$('#'+id)?.addEventListener('click',closeAudience);
  if($('#audience-dialog')){openDialog('#audience-dialog');$('#audience-dialog').addEventListener('cancel',event=>{event.preventDefault();closeAudience();});}
  document.querySelectorAll('[data-preview-favor]').forEach(button=>button.addEventListener('click',()=>playerInput(async()=>{localAction={itemId:button.dataset.itemId};previewTargetId=button.dataset.targetId;favorPreview=true;audienceOpen=false;await command('preview_favor',{itemId:button.dataset.itemId,unitId:button.dataset.unitId,targetId:button.dataset.targetId},{preserveAction:true,save:false});})));
  bindNeighborhood();
  if(view.neighborhood?.standalone)for(const id of ['open-journey','open-missions','open-scenarios']){const b=$('#'+id);if(b){b.disabled=true;b.title='Return to your preserved campaign to enter another route.';}}
  bindHome();bindJourney();
  bindDevelopment();bindScenario();bindProgressionMenus();
  const openSheet=(id,from)=>{characterSheetId=id;sheetReturn=from;actionChooser=false;render();};
  $('#open-character-sheet')?.addEventListener('click',()=>openSheet(view.selectedUnitId,'#open-character-sheet'));
  document.querySelectorAll('[data-character-sheet]').forEach(button=>button.addEventListener('click',()=>openSheet(button.dataset.characterSheet,`[data-character-sheet="${button.dataset.characterSheet}"]`)));
  const closeSheet=()=>{characterSheetId=null;render();$(sheetReturn||'#open-character-sheet')?.focus();};
  const sheet=$('#character-sheet-dialog');
  if(sheet){openDialog('#character-sheet-dialog');$('#close-character-sheet').focus();if(sheetOpenSection){sheetActiveSection=sheetOpenSection;sheetOpenSection=null;}sheet.addEventListener('cancel',event=>{event.preventDefault();closeSheet();});}
  $('#close-character-sheet')?.addEventListener('click',closeSheet);$('#done-character-sheet')?.addEventListener('click',closeSheet);
  $('#sheet-crawler')?.addEventListener('change',event=>{characterSheetId=event.target.value;render();});
  const activateSheetTab=id=>{
    const sections=[...document.querySelectorAll('#character-sheet-dialog .sheet-section')];
    if(!sections.some(section=>section.id===id))id='sheet-stats';
    sheetActiveSection=id;
    sections.forEach(section=>{section.hidden=section.id!==id;section.setAttribute('role','tabpanel');section.setAttribute('aria-labelledby',`tab-${section.id.replace('sheet-','')}`);});
    document.querySelectorAll('[data-sheet-section]').forEach(button=>{const active=button.dataset.sheetSection===id;button.setAttribute('aria-selected',String(active));button.tabIndex=active?0:-1;});
  };
  document.querySelectorAll('[data-sheet-section]').forEach((button,index,buttons)=>{
    button.addEventListener('click',()=>activateSheetTab(button.dataset.sheetSection));
    button.addEventListener('keydown',event=>{if(!['ArrowLeft','ArrowRight','Home','End'].includes(event.key))return;event.preventDefault();const next=event.key==='Home'?0:event.key==='End'?buttons.length-1:(index+(event.key==='ArrowRight'?1:-1)+buttons.length)%buttons.length;activateSheetTab(buttons[next].dataset.sheetSection);buttons[next].focus();});
  });
  if(sheet)activateSheetTab(sheetActiveSection);
  document.querySelectorAll('[data-sheet-equip]').forEach(button=>button.addEventListener('click',()=>command('equip',{unitId:characterSheetId,equipmentId:button.dataset.sheetEquip})));
  document.querySelectorAll('[data-sheet-unequip]').forEach(button=>button.addEventListener('click',()=>command('unequip',{unitId:characterSheetId,equipmentId:button.dataset.sheetUnequip})));
  $('#sheet-set-specialty')?.addEventListener('click',()=>{specialtyPending={unitId:characterSheetId,classId:$('#sheet-specialty-class').value};render();});
  const cancelSpecialty=()=>{specialtyPending=null;render();$('#sheet-set-specialty')?.focus();};
  if($('#specialty-review-dialog')){openDialog('#specialty-review-dialog');$('#cancel-specialty-review').focus();$('#specialty-review-dialog').addEventListener('cancel',event=>{event.preventDefault();cancelSpecialty();});}
  $('#close-specialty-review')?.addEventListener('click',cancelSpecialty);$('#cancel-specialty-review')?.addEventListener('click',cancelSpecialty);
  $('#confirm-specialty-review')?.addEventListener('click',()=>{const pending=specialtyPending;specialtyPending=null;command('set_specialty',pending);});
  $('#sheet-select-character')?.addEventListener('click',()=>playerInput(()=>command('select',{unitId:characterSheetId})));
  $('#sheet-open-tree')?.addEventListener('click',()=>{skillTreeUnit=characterSheetId;characterSheetId=null;skillTreeOpen=true;render();});
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
  document.querySelectorAll('[data-generated-adventure]').forEach(button=>button.addEventListener('click',openGeneratedAdventure));
  $('#legacy-dungeon')?.addEventListener('click',()=>command('start'));
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
  $('#class-search')?.addEventListener('input',event=>{const query=event.target.value.toLowerCase();for(const option of $('#class-select').options)option.hidden=!option.text.toLowerCase().includes(query);});
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
  document.querySelectorAll('[data-explore-cell]').forEach(b => b.addEventListener('click', () => { const [x,y] = b.dataset.exploreCell.split(',').map(Number); hoverCell(x,y); }));
  document.querySelectorAll('[data-explore-interact]').forEach(b => b.addEventListener('click', () => command('explore_interact', {targetId:b.dataset.exploreInteract})));
  $('#return-camp')?.addEventListener('click', () => command('return_camp'));
  $('#enter-battle')?.addEventListener('click', () => command('start'));
  $('#quick-enter')?.addEventListener('click', () => view.generatedDungeon || view.journey?.active || view.neighborhood?.active || view.encounterIndex > 0 ? command('start') : openGeneratedAdventure());
  document.querySelectorAll('[data-unit], [data-ability], [data-modal-ability], [data-modal-item]').forEach(b => b.addEventListener('pointerdown', () => b.classList.add('pressed')));
  document.querySelectorAll('[data-cell]').forEach(b => b.addEventListener('focus', () => hoverCell(...b.dataset.cell.split(',').map(Number))));
  document.querySelectorAll('.party-chip[data-unit]').forEach(b => b.addEventListener('click', () => { targetTile = false; playerInput(()=>command('select', { unitId: b.dataset.unit })); }));
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
function workshopRequest() {
  const query = new URLSearchParams(location.search), token = query.get('map');
  if (token && !/^[a-zA-Z0-9-]{8,80}$/.test(token)) throw new Error('This dungeon link is invalid. Return to the generator and choose Play again.');
  const storageKey = token ? `dct.workshop-map.${token}` : 'dct.workshop-map';
  const serialized = token ? sessionStorage.getItem(storageKey) : localStorage.getItem(storageKey);
  if (!serialized) throw new Error('This dungeon handoff has expired. Your saved run is unchanged; return to the generator and choose Play again.');
  if (serialized.length > 2_000_000) throw new Error('The generated map exceeds the 2 MB import limit.');
  const exploring = query.get('explore') === '1';
  const traversal = exploring ? JSON.parse(sessionStorage.getItem(`${storageKey}.exploration`) || 'null') : null;
  if (exploring && !traversal) throw new Error('Exploration handoff expired. Return to Foundry and choose Play again.');
  return { token, storageKey, serialized, map: JSON.parse(serialized), exploring, traversal };
}
function matchesWorkshopValue(actual, expected) {
  if (expected === null || typeof expected !== 'object') return actual === expected;
  if (Array.isArray(expected)) return Array.isArray(actual) && actual.length === expected.length && expected.every((value, index) => matchesWorkshopValue(actual[index], value));
  return actual && typeof actual === 'object' && Object.keys(expected).every(key => matchesWorkshopValue(actual[key], expected[key]));
}
function verifyWorkshopImport(expected, exploring = false) {
  if (expected.visuals && !matchesWorkshopValue(view.customMap?.visuals, expected.visuals)) throw new Error('The game did not retain this dungeon’s selected tile art. Reload the updated game and retry.');
  const portable = {
    schemaVersion: expected.schemaVersion, width: expected.width, height: expected.height, label: expected.label,
    tiles: expected.tiles.map(({ x, y, blocked = false, tags = [] }) => ({ x, y, blocked, tags })),
    placements: expected.placements.map(({ id, assetId, layer, x, y, rotation = 0, blocksMovement }) => ({ id, assetId, layer, x, y, rotation, blocksMovement })),
    ...(expected.playerSpawns?.length ? { playerSpawns: expected.playerSpawns.map(({ x, y }) => ({ x, y })) } : {}),
    ...(expected.enemies?.length ? { enemies: expected.enemies } : {}),
    ...(expected.visuals ? { visuals: expected.visuals } : {}),
  };
  if (view.screen !== (exploring ? 'explore' : 'battle') || view.width !== expected.width || view.height !== expected.height || !matchesWorkshopValue(view.customMap, portable)) throw new Error(view.message || 'The game did not accept this exact dungeon.');
  if (exploring) {
    if (!view.generatedDungeon || view.exploration?.width !== expected.width || view.exploration?.height !== expected.height) throw new Error('Generated exploration did not start on this map.');
    return;
  }
  const authoredTiles = new Map(expected.tiles.map(tile => [`${tile.x},${tile.y}`, tile]));
  if (view.tiles.length !== expected.width * expected.height || view.tiles.some(tile => {
    const authored = authoredTiles.get(`${tile.x},${tile.y}`);
    return tile.blocked !== Boolean(authored?.blocked) || JSON.stringify([...tile.tags].sort()) !== JSON.stringify([...(authored?.tags || [])].sort());
  })) throw new Error('The loaded dungeon terrain does not match the generated map.');
  if (expected.playerSpawns?.length) {
    const positions = list => list.map(cell => `${cell.x},${cell.y}`).sort().join('|');
    if (positions(view.units.filter(unit => unit.team === 'player')) !== positions(expected.playerSpawns)) throw new Error('The loaded party positions do not match the generated map.');
  }
  if (expected.enemies?.length && expected.enemies.some(enemy => !view.units.some(unit => unit.team === 'enemy' && unit.id === enemy.id && unit.x === enemy.x && unit.y === enemy.y))) throw new Error('The loaded enemies do not match the generated map.');
}
function consumeWorkshopRequest(request) {
  if (request.token) sessionStorage.removeItem(request.storageKey);
  sessionStorage.removeItem(`${request.storageKey}.exploration`);
  try { if (localStorage.getItem('dct.workshop-map') === request.serialized) localStorage.removeItem('dct.workshop-map'); } catch { /* The per-tab handoff is already complete. */ }
  const query = new URLSearchParams(location.search); query.delete('workshop'); query.delete('map'); query.delete('explore');
  history.replaceState(null, '', `${location.pathname}${query.size ? `?${query}` : ''}${location.hash}`);
}
async function boot() {
  const isWorkshopRequest = new URLSearchParams(location.search).get('workshop') === '1';
  let workshopCommitted = false;
  try {
    const requestedMap = isWorkshopRequest ? workshopRequest() : null;
    await Blazor.start();
    $('#boot-status').textContent = requestedMap ? 'Loading your generated dungeon…' : 'Loading your party and the first floor…';
    const responses = await Promise.all([fetch('data/combat-content.json'), fetch('data/game-content.json')]);
    if (responses.some(r => !r.ok)) throw new Error('The game content could not be loaded. Serve this folder over HTTP; opening index.html directly is unsupported.');
    const [combatJson, gameJson] = await Promise.all(responses.map(r => r.text()));
    content = JSON.parse(combatJson);
    gameData = JSON.parse(gameJson);
    view = JSON.parse(await call('Initialize', combatJson, gameJson));
    narrator=createNarrator({getView:()=>view,content});
    if (requestedMap) {
      // An explicit map takes precedence over autosave. Commit the browser save only
      // after geometry, spawns and any native visual descriptor match exactly.
      render();
      await command(requestedMap.exploring ? 'import_generated' : 'import_map', { customMap: requestedMap.map, ...requestedMap.traversal }, { save: false });
      verifyWorkshopImport(requestedMap.map, requestedMap.exploring);
      await persist({ strict: true });
      workshopCommitted = true;
      consumeWorkshopRequest(requestedMap);
      toast('Your exact generated dungeon is ready.', 'success');
    } else {
      let saved;
      try { saved = localStorage.getItem(saveKey); } catch { /* Export remains available. */ }
      if (saved) {
        try { await loadSerializedSave(saved); toast('Your run has been restored.'); }
        catch (error) { render(); toast('Your stored save could not be restored. A new party is ready; the stored file has been preserved.', 'warning'); $('#save-status').textContent = 'Stored save invalid · import or start fresh'; }
      } else { render(); await persist(); }
    }
    $('#game').setAttribute('aria-busy', 'false');
    window.dungeon = { get scene(){return battlefield;}, cellToScreen:(x,y)=>battlefield?.cellToScreen(x,y), command, getView: () => view, getSave: () => call('GetSave'), loadSave: loadSerializedSave };
  } catch (error) {
    if (isWorkshopRequest) {
      $('#game').innerHTML = `<section class="fatal" id="workshop-load-error" role="alert"><h1>${workshopCommitted ? 'Your dungeon was saved, but the handoff could not finish.' : 'Your generated dungeon wasn’t loaded.'}</h1><p>${workshopCommitted ? 'Your browser save now contains the generated dungeon. Open your saved run to continue.' : 'Your previous browser save has not been replaced.'}</p><pre>${e(error.message)}</pre><button class="primary" onclick="location.reload()">Retry this dungeon</button><p><a href="dungeon-generator.html">Return to the generator</a> · <a href="index.html">Open your saved run</a></p></section>`;
    } else {
      $('#game').innerHTML = `<section class="fatal"><h1>The dungeon couldn’t load.</h1><p>The C# runtime or game content did not finish loading. Check your connection and reload the page.</p><pre>${e(error.message)}</pre><button class="primary" onclick="location.reload()">Try again</button></section>`;
    }
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
let adventureRequest = 0, adventureCommitting = false;
function openGeneratedAdventure() {
  explorationControls.stop();
  $('#generated-adventure-status').textContent = '';
  $('#begin-generated-adventure').disabled = false;
  openDialog('#generated-adventure-dialog');
}
function closeGeneratedAdventure() {
  if (adventureCommitting) return;
  adventureRequest++;
  closeDialog('#generated-adventure-dialog');
}
$('#close-generated-adventure').onclick = closeGeneratedAdventure;
$('#cancel-generated-adventure').onclick = closeGeneratedAdventure;
$('#generated-adventure-dialog').addEventListener('cancel', event => { if (adventureCommitting) event.preventDefault(); else adventureRequest++; });
$('#begin-generated-adventure').onclick = async () => {
  const request = ++adventureRequest;
  $('#begin-generated-adventure').disabled = true;
  $('#generated-adventure-status').textContent = 'Building connected rooms and fitting square tiles…';
  let previousSave;
  try {
    const packet = await createGeneratedAdventure({ seed: $('#adventure-seed').value, layout: $('#adventure-layout').value,
      styleId: $('#adventure-style').value, kitId: $('#adventure-location').value });
    if (request !== adventureRequest) return;
    adventureCommitting = true;
    previousSave = await call('GetSave');
    await command('import_generated', packet, { save: false });
    verifyWorkshopImport(packet.customMap, true);
    await persist({ strict: true });
    adventureCommitting = false;
    closeGeneratedAdventure();
    battleCanvas?.focus({preventScroll:true});
    toast('Dungeon ready · Hold WASD, arrows, or the direction pad to walk.','success');
  } catch (error) {
    if (previousSave) { view = JSON.parse(await call('LoadSave', previousSave)); render(); }
    if (request === adventureRequest) $('#generated-adventure-status').textContent = `Could not enter the dungeon: ${error.message}`;
  } finally { if (request === adventureRequest) { adventureCommitting = false; $('#begin-generated-adventure').disabled = false; } }
};
const explorationControls = attachExplorationControls({
  canMove: () => view?.screen === 'explore' && !busy && !animating && !enemySequence
    && !document.querySelector('dialog[open]') && battlefield?.getNativeArtStatus?.().state === 'ready',
  focusMap: () => battleCanvas?.focus({preventScroll:true}),
  step: async (dx,dy) => {
    const direction = battlefield.movementDirection(dx,dy);
    const x = view.exploration.x + direction.x, y = view.exploration.y + direction.y;
    if (view.exploration.tiles.some(tile => tile.x === x && tile.y === y && !tile.blocked && tile.reachable))
      await command('explore_step', {x:direction.x,y:direction.y});
  },
  interact: () => {
    const point = view.exploration.points.find(p=>p.canInteract&&!p.claimed);
    if (point) return command('explore_interact', {targetId:point.id});
    toast('Move beside a discovery or the cleared exit to interact.','info');
  }
});
document.addEventListener('keydown', event => {

  if (event.key === '?' && !document.querySelector('dialog[open]') && !event.ctrlKey && !event.metaKey && !['INPUT', 'SELECT', 'TEXTAREA'].includes(document.activeElement?.tagName)) { event.preventDefault(); openDialog('#help-dialog'); }
  if (event.key === 'Escape' && !document.querySelector('dialog[open]')) { if(enemySequence)return; if (drawer) { closeDrawer(); } else if (view?.screen === 'battle') cancelTargeting(); }
});
boot();

window.addEventListener('resize', () => battlefield?.resize());
