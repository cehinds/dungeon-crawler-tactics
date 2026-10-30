const escape = value => String(value ?? '').replace(/[&<>"']/g, char => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[char]));
const slots = ['weapon', 'armor', 'charm'];
const title = value => value.charAt(0).toUpperCase() + value.slice(1);
export const equipmentBenefits = gear => [['hpBonus','HP'],['manaBonus','Mana'],['moveBonus','Move']].filter(([key])=>gear[key]).map(([key,label])=>`${gear[key]>0?'+':''}${gear[key]} ${label}`).join(' · ') || 'No stat bonus';
const abilityName = (id, describe) => { const result = describe?.(id); return typeof result === 'object' ? result?.label || id : result || title(id.replace(/[_-]/g,' ')); };
export function renderEquipmentDialog(view, {crawlerId, slot='weapon', showLocked=false, portrait, describeAbility}={}) {
  const roster = (view.roster??[]).filter(unit=>unit.deployable!==false);
  const unit = roster.find(item=>item.id===crawlerId) || roster[0];
  if (!unit) return '';
  if (!slots.includes(slot)) slot='weapon';
  const inventory = view.equipment??[];
  const current = inventory.filter(gear=>gear.equippedUnitId===unit.id);
  const visible = inventory.filter(gear=>gear.slot===slot && (showLocked||gear.owned));
  const cards = visible.map(gear=>{
    const mine=gear.equippedUnitId===unit.id;
    const owner=roster.find(item=>item.id===gear.equippedUnitId);
    const unavailable=!!gear.equippedUnitId&&!mine;
    return `<article class="equipment-item${mine?' is-equipped':''}${!gear.owned?' is-locked':''}" data-gear="${escape(gear.id)}"><div class="equipment-item-heading"><strong>${escape(gear.label)}</strong><span>${mine?'Equipped':gear.owned?'Owned':'Locked'}</span></div>${gear.description?`<p>${escape(gear.description)}</p>`:''}<p class="equipment-benefits">${escape(equipmentBenefits(gear))}</p>${(gear.abilityIds??[]).length?`<p class="equipment-grants">Grants ${gear.abilityIds.map(id=>escape(abilityName(id,describeAbility))).join(' · ')}</p>`:''}<div class="equipment-item-action"><small>${mine?'Equipped by '+escape(unit.label):unavailable?'In use by '+escape(owner?.label||gear.equippedUnitId):gear.owned?'Available':escape(gear.unlockReason||(gear.rewardOnly?'Choose this item as an encounter reward.':'Progress through encounters to unlock.'))}</small><button ${mine?'data-unequip':'data-equip'}="${escape(gear.id)}" ${!gear.owned||unavailable?'disabled':''}>${mine?'Unequip':unavailable?'In use':!gear.owned?'Locked':'Compare'}</button></div></article>`;
  }).join('');
  return `<dialog id="equipment-dialog" class="loadout-dialog equipment-dialog" aria-labelledby="equipment-title"><div class="dialog-head"><div><span class="section-label">SHARED INVENTORY</span><h2 id="equipment-title">Equipment</h2></div><button id="close-loadout" class="icon-button" aria-label="Close equipment">×</button></div><div class="modal-body"><div class="equipment-crawler">${portrait?portrait(unit,'equipment-portrait'):''}<label for="loadout-crawler">Crawler<select id="loadout-crawler">${roster.map(item=>`<option value="${escape(item.id)}" ${item.id===unit.id?'selected':''}>${escape(item.label)}</option>`).join('')}</select></label></div><div class="equipment-live-stats" aria-label="Actual crawler stats"><span>HP <b>${escape(unit.hp)}/${escape(unit.maxHp)}</b></span><span>Mana <b>${escape(unit.energy??'—')}/${escape(unit.maxEnergy??'—')}</b></span><span>Move <b>${escape(unit.move??'—')}</b></span></div><div class="equipment-slot-summary">${slots.map(key=>`<div><span>${title(key)}</span><strong>${escape(current.find(gear=>gear.slot===key)?.label||'Empty')}</strong></div>`).join('')}</div><div class="equipment-filters"><div class="equipment-tabs" role="group" aria-label="Equipment slot">${slots.map(key=>`<button data-equipment-slot="${key}" aria-pressed="${key===slot}">${title(key)}</button>`).join('')}</div><label class="equipment-locked-toggle"><input id="equipment-show-locked" type="checkbox" ${showLocked?'checked':''}> Show locked</label></div><p class="equipment-instruction">Compare gear before equipping. One item per slot; each item has one owner.</p><div class="equipment-items">${cards||`<p class="equipment-empty">No owned ${escape(slot)} items yet. Find gear in encounter rewards.</p>`}</div></div><div class="modal-actions"><button id="done-loadout" class="primary">Done</button><button id="switch-loadout">View skills</button></div></dialog>`;
}
export function renderEquipmentComparison(view, {portrait, abilityLabel}={}) {
  const preview=view.equipmentPreview;
  if (!preview) return '';
  const unit=(view.roster??[]).find(item=>item.id===preview.unitId);
  const gear=(view.equipment??[]).find(item=>item.id===preview.equipmentId);
  const previous=(view.equipment??[]).find(item=>item.id===preview.previousGearId);
  const before=preview.before??{}, after=preview.after??{};
  const stat=(label,key)=>{
    const from=before[key],to=after[key];
    const delta=typeof from==='number'&&typeof to==='number'?to-from:0;
    const change=delta>0?' equipment-stat-gain':delta<0?' equipment-stat-loss':'';
    return `<tr><th scope="row">${label}</th><td>${escape(from??'—')}</td><td aria-hidden="true">→</td><td class="equipment-stat-after${change}">${escape(to??'—')}${delta?` <span class="equipment-stat-delta">(${delta>0?'+':''}${delta})</span>`:''}</td></tr>`;
  };
  const abilities=(ids,label)=>`<div class="equipment-ability-change"><strong>${label}</strong><span>${ids?.length?ids.map(id=>escape(abilityName(id,abilityLabel))).join(' · '):'None'}</span></div>`;
  return `<dialog id="equipment-confirm-dialog" class="equipment-dialog equipment-confirm-dialog" aria-labelledby="equipment-confirm-title"><div class="dialog-head"><div><span class="section-label">${escape(unit?.label||'Crawler')} · EQUIPMENT</span><h2 id="equipment-confirm-title">${preview.remove?'Remove equipment?':previous?'Replace equipment?':'Equip item?'}</h2></div><button id="close-equipment-confirm" class="icon-button" aria-label="Close equipment comparison">×</button></div><div class="modal-body">${portrait&&unit?`<div class="equipment-comparison-portrait">${portrait(unit,'equipment-portrait')}</div>`:''}<p class="equipment-change-title">${escape(preview.remove?gear?.label||'Current item':previous?.label||'Empty slot')} <span>→</span> ${escape(preview.remove?'Empty slot':gear?.label||preview.equipmentId)}</p><table class="equipment-comparison"><caption>Actual stats after this change</caption><thead><tr><th>Stat</th><th>Before</th><th></th><th>After</th></tr></thead><tbody>${stat('Max HP','maxHp')}${stat('Max Mana','maxEnergy')}${stat('Move','move')}${stat('Current HP','hp')}${stat('Current Mana','energy')}</tbody></table><div class="equipment-ability-changes">${abilities(preview.gainedAbilityIds,'Abilities gained')}${abilities(preview.lostAbilityIds,'Abilities lost')}</div><p class="equipment-instruction">No currency cost. Equipment does not heal or refill Mana; current values may be capped when a maximum falls.</p>${!preview.canConfirm?'<p class="equipment-empty">This change is unavailable. Return to inventory to choose another item.</p>':''}</div><div class="modal-actions"><button id="confirm-equipment" class="primary" ${preview.canConfirm?'':'disabled'}>${preview.remove?'Confirm removal':'Confirm equipment'}</button><button id="cancel-equipment">Cancel</button></div></dialog>`;
}
