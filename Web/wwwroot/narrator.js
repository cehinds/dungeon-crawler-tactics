// Original UI feedback generated from committed game events, never canonical quotations.
const achievementLabels={
  'achievement.first_move':'First movement',
  'achievement.first_reaction':'First elemental reaction',
  'achievement.first_form':'First form change',
  'achievement.first_victory':'First room cleared',
  'achievement.first_level':'First level gained'
};
export function createNarrator({getView,content}) {
  const panel=document.createElement('section');panel.id='narrator-panel';panel.className='narrator-panel';panel.dataset.empty='true';panel.setAttribute('aria-label','Dungeon narrator game feedback');
  const label=document.createElement('span');label.className='narrator-label';label.textContent='NARRATOR';
  const line=document.createElement('p');line.id='narrator-line';line.setAttribute('role','status');line.setAttribute('aria-live','polite');line.textContent='';
  const historyButton=document.createElement('button');historyButton.id='narrator-history';historyButton.textContent='History';
  const dismiss=document.createElement('button');dismiss.id='narrator-dismiss';dismiss.textContent='×';dismiss.setAttribute('aria-label','Dismiss narrator message');
  panel.append(label,line,historyButton,dismiss);
  const dialog=document.createElement('dialog');dialog.id='narrator-history-dialog';dialog.setAttribute('aria-labelledby','narrator-history-title');
  dialog.innerHTML='<div class="dialog-head"><div><span class="section-label">ORIGINAL GAME FEEDBACK</span><h2 id="narrator-history-title">Dungeon narrator</h2></div><button id="close-narrator-history" class="icon-button" aria-label="Close narrator history">×</button></div><div class="modal-body"><p class="modal-intro">Declarations, impacts and achievements from this session. These lines describe actual game events.</p><ol class="narrator-history-list"></ol></div><div class="modal-actions"><button id="done-narrator-history">Back to game</button></div>';
  document.body.append(dialog);
  let pending=[],history=[],timer=null,batch=0,eventKeys=new WeakMap(),seen=new Set(),batchEvents=[],beforeView=null,afterView=null,currentContext=null;
  let achievements=new Set(getView()?.achievementIds??[]);
  const labelFor=(id)=>{const view=afterView??getView();const tile=view?.tiles.find(tile=>tile.id===id);if(tile)return `Terrain ${String.fromCharCode(65+tile.x)}${tile.y+1}`;return view?.units.find(unit=>unit.id===id)?.label??view?.roster.find(unit=>unit.id===id)?.label??id?.replace(/^[^.]+\./,'').replace(/_/g,' ')??'Target';};
  const abilityFor=id=>content.abilities.find(ability=>ability.id===id)?.label??id?.replace(/^[^.]+\./,'').replace(/_/g,' ')??'an ability';
  function drawHistory(){const list=dialog.querySelector('.narrator-history-list');list.replaceChildren();for(const entry of [...history].reverse()){const row=document.createElement('li');row.className=entry.kind==='achievement'?'narrator-achievement':'';row.textContent=entry.text;list.append(row);}}
  function advance(){clearTimeout(timer);const entry=pending.shift();if(!entry){timer=null;return;}panel.dataset.empty='false';panel.classList.toggle('narrator-achievement',entry.kind==='achievement');line.textContent=entry.text;line.title=entry.text;timer=setTimeout(advance,entry.kind==='achievement'?2600:entry.kind==='impact'?1100:1800);}
  function enqueue(text,kind='declaration'){if(!text)return;history.push({text,kind});history=history.slice(-80);pending.push({text,kind});if(pending.length>8){const oldestImpact=pending.findIndex(entry=>entry.kind==='impact');pending.splice(oldestImpact>=0?oldestImpact:0,1);}if(!timer)advance();if(dialog.open)drawHistory();}
  function onEvent(event){if(!event||event.preview)return;const key=`${batch}:${event.sequence??JSON.stringify(event)}`;if(seen.has(key))return;seen.add(key);
    const current=afterView??getView();
    if(event.type==='achievement'){if(!achievements.has(event.tag)){achievements.add(event.tag);enqueue(`NEW ACHIEVEMENT · ${current?.neighborhood?.challenges?.find(c=>c.id===(event.tag||event.targetId))?.label??achievementLabels[event.tag]??(event.tag||event.targetId||'Neighborhood challenge completed').replace(/^achievement\./,'').replace(/_/g,' ')}`,'achievement');}return;}
    const actor=labelFor(event.actorId),target=labelFor(event.targetId);
    const actorUnit=(afterView??getView())?.units.find(unit=>unit.id===event.actorId);
    if(event.type==='favor'){enqueue(`AI Favor earned: +${event.amount}. Place an eligible environmental supply without using your action. Open Sponsors to review.`,'achievement');return;}
    if(event.type==='sponsor_challenge'){const challenge=current?.audience?.challenges?.find(c=>c.id===event.tag);const supply=current?.items?.find(i=>i.id===challenge?.rewardItemId);enqueue(`SPONSOR DELIVERY · ${challenge?.label??'Challenge complete'} · ${challenge?.rewardCount??event.amount} × ${supply?.label??'supplies'}. Saved once for this run.`,'achievement');return;}
    if(event.type==='trap_trigger'){enqueue(`${target} triggers the trap. Its one-use surface is consumed.`,'impact');return;}
    if(event.type==='scenario_intent'){const intent=beforeView?.scenario?.intent??current?.scenario?.intent;enqueue(`${actor} declares ${intent?.label??'a special attack'}. ${intent?.description??''}`);return;}
    if(event.type==='scenario_spawn'){enqueue(`${target} emerges. Watch the marked nests.`);return;}
    if(event.type==='scenario_interact'){const object=current?.scenario?.interactables.find(item=>item.id===event.targetId);enqueue(`${actor} uses ${object?.label??'a room interaction'}. Action spent; unused movement remains.`);return;}
    if(event.type==='stat_allocation'){enqueue(`${actor} allocated stat points. Rest to fill any increased HP or Mana cap.`);return;}
    if(event.type==='skill_practice'){enqueue(`${actor}: ${abilityFor(event.abilityId)} practiced (${event.amount} uses).${event.after>event.before?' Skill rank '+event.after+' reached!':''}`,event.after>event.before?'achievement':'impact');return;}
    if(event.type==='craft'){const recipe=current?.development?.recipes.find(item=>item.id===event.tag);enqueue(`Crafted ${recipe?.label??'a recipe'}. Ingredients consumed; supplies updated.`);return;}
    if(event.type==='loot_box_earned'||event.type==='loot_box_opened'){const box=current?.development?.lootBoxes.find(item=>item.id===event.tag);enqueue(event.type==='loot_box_earned'?`${box?.label??'Loot box'} earned. Open it in the safe room.`:`${box?.label??'Loot box'} opened. Rewards added to shared supplies.`,'achievement');return;}
    if(event.type==='phase'){enqueue(event.tag==='enemy'?'Enemy turn. Watch their movement and intentions.':'Player turn. Move and act in either order.');return;}
    if(event.type==='move'&&actorUnit?.team==='enemy'){enqueue(`${actor} advances toward the crawlers.`);return;}
    if(event.type==='attack'&&actorUnit?.team==='enemy'){enqueue(`${actor} declares ${abilityFor(event.abilityId)} against ${target}.`);return;}
    if(event.type==='damage'){enqueue(`${target}: ${event.before} → ${event.after} HP (${event.amount} damage).`,'impact');return;}
    if(event.type==='heal'){enqueue(`${target}: ${event.before} → ${event.after} HP restored.`,'impact');return;}
    if(event.type==='reaction'){enqueue(`Reaction: ${event.reactionId?.replace(/^reaction\./,'').replace(/_/g,' ')||'elemental reaction'} on ${target}.`,'impact');return;}
    if(event.type==='level_up')enqueue(`Party level ${event.after||event.amount}. New skills and stronger stats.`,'achievement');
  }
  function begin(context,before,after){batch++;beforeView=before;afterView=after;currentContext=context;batchEvents=after.events??[];eventKeys=new WeakMap();batchEvents.forEach((event,index)=>eventKeys.set(event,`${batch}:${index}`));
    if(context?.type==='move'){const old=before.units.find(unit=>unit.id===context.actorId),moved=after.units.find(unit=>unit.id===context.actorId);if(old&&moved&&(old.x!==moved.x||old.y!==moved.y))enqueue(`${context.actorLabel} declares Move → ${context.targetLabel}.`);}
    if(context?.type==='confirm'){const actorBefore=before.units.find(unit=>unit.id===context.actorId),actorAfter=after.units.find(unit=>unit.id===context.actorId);if(before.canConfirm&&!after.canConfirm&&actorBefore&&!actorBefore.acted&&actorAfter?.acted)enqueue(`${context.actorLabel} declares ${context.actionLabel} → ${context.targetLabel||'self'}.`);}
  }
  function finish(){for(const event of batchEvents)onEvent(event);batchEvents=[];beforeView=null;currentContext=null;}
  historyButton.addEventListener('click',()=>{drawHistory();dialog.showModal();dialog.querySelector('#close-narrator-history').focus();});
  const close=()=>{dialog.close();historyButton.focus();};dialog.querySelector('#close-narrator-history').addEventListener('click',close);dialog.querySelector('#done-narrator-history').addEventListener('click',close);
  dialog.addEventListener('cancel',event=>{event.preventDefault();close();});dialog.addEventListener('keydown',event=>{if(event.key!=='Tab')return;const first=dialog.querySelector('#close-narrator-history'),last=dialog.querySelector('#done-narrator-history');if(event.shiftKey&&document.activeElement===first){event.preventDefault();last.focus();}else if(!event.shiftKey&&document.activeElement===last){event.preventDefault();first.focus();}});
  dismiss.addEventListener('click',()=>{clearTimeout(timer);pending=[];timer=null;line.textContent='';line.title='';panel.dataset.empty='true';panel.classList.remove('narrator-achievement');});
  return {mount(slot){if(slot&&panel.parentElement!==slot)slot.append(panel);},begin,onEvent,finish,reset(view){achievements=new Set(view?.achievementIds??[]);pending=[];history=[];seen.clear();clearTimeout(timer);timer=null;panel.classList.remove('narrator-achievement');panel.dataset.empty='true';line.title='';line.textContent='';},dispose(){clearTimeout(timer);panel.remove();dialog.remove();}};
}
