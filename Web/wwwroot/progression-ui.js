// Presents authoritative before/after views; progression rules stay in C#.
const e=value=>String(value??'').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export function renderLevelUp(view,notice){
 if(!notice)return '';
 const before=notice.before.progression,after=notice.after.progression;
 const gain=key=>(after[key]??0)-(before[key]??0);
 const unlocked=(after.skills??[]).filter(skill=>skill.unlocked&&!before.skills?.find(old=>old.id===skill.id)?.unlocked);
 const floorLocked=(after.skills??[]).filter(skill=>!skill.unlocked&&skill.level>before.level&&skill.level<=after.level);
 const crawler=notice.after.development?.crawlers?.[0],oldCrawler=notice.before.development?.crawlers?.find(old=>old.unitId===crawler?.unitId);
 const points=crawler&&oldCrawler?crawler.unspentPoints-oldCrawler.unspentPoints:0;
 const banked=view.journey?.active&&!view.journey.allocationUnlocked;
 return `<dialog id="level-up-dialog" aria-labelledby="level-up-title"><div class="dialog-head"><h2 id="level-up-title">Party level ${before.level} → ${after.level}</h2></div><div class="modal-body"><p class="level-up-line">${after.level-before.level} level${after.level-before.level===1?'':'s'} gained · all field crawlers, including reserves</p><div class="action-modal-stats"><span>+${gain('hpBonus')} maximum HP</span><span>+${gain('manaBonus')} maximum Mana</span>${gain('moveBonus')?`<span>+${gain('moveBonus')} movement</span>`:''}<span>+${points} allocation points each</span></div><p>${banked?'Stat points are banked until floor three.':'Spend allocation points in safe-room Development.'} ${after.level<after.maxLevel?`${after.xpToNextLevel} XP to level ${after.level+1}.`:`Level cap ${after.maxLevel} reached.`}</p><h3>Newly available skills</h3><div class="skill-grid">${unlocked.map(skill=>`<div class="skill-row unlocked"><strong>${e(skill.label)}</strong><small>${e(view.roster.find(r=>r.id===skill.unitId)?.label||'Party skill')} · level ${skill.level}</small></div>`).join('')||'<p>No new personal skills this time. Check your earned tree points in Skills.</p>'}${floorLocked.map(skill=>`<div class="skill-row locked"><strong>${e(skill.label)}</strong><small>Level met · unlocks on floor ${skill.minimumFloor}</small></div>`).join('')}</div><p>Rest in the safe room to restore resources to their new maximum.</p></div><div class="modal-actions"><button id="continue-level-up" class="primary">Continue</button></div></dialog>`;
}
export function renderProgressionSummary(view){
 const p=view.progression;if(!p)return '';
 return `<section class="development-preview" aria-label="Party progression"><h3>Party level ${p.level} / ${p.maxLevel}</h3><p>${p.xp} XP · ${p.level<p.maxLevel?`${p.xpToNextLevel} XP to level ${p.level+1}`:'Level cap reached'}</p><p>Current level bonuses: +${p.hpBonus} maximum HP · +${p.manaBonus} maximum Mana.${view.journey?.active?' Story reward pacing is a tactical adaptation; floors nine through eighteen remain reserved.':''}</p></section>`;
}
