// Read-only roadmap from authored thresholds and the shared engine's current views.
const e = value => String(value ?? '').replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
export function renderLevelRoadmap(view, data, roster) {
  if(roster.deployable===false || !view.progression)return '';
  const p=view.progression;
  const development=view.development?.crawlers?.find(c=>c.unitId===roster.id);
  const personal=view.skillTree?.trees?.find(t=>t.rosterId===roster.id);
  const classTree=view.skillTree?.classTrees?.find(t=>t.rosterId===roster.id);
  const authoredClass=data.classSkillTrees?.find(t=>t.classId===roster.classId);
  const tiers=[...new Set((classTree?.nodes??authoredClass?.nodes??[]).map(n=>n.level))].sort((a,b)=>a-b);
  const nextTier=tiers.find(level=>level>p.level);
  const nextSkills=(p.skills??[]).filter(s=>(!s.unitId||s.unitId===roster.id)&&!s.unlocked).sort((a,b)=>a.level-b.level);
  const practice=(view.development?.practice??[]).filter(s=>s.unitId===roster.id&&s.uses>0&&!s.atCap).sort((a,b)=>(a.nextRankUses-a.uses)-(b.nextRankUses-b.uses)).slice(0,3);
  const skillName=id=>data.progression?.skillUnlocks?.find(s=>s.abilityId===id)?.label ?? id.replace(/^ability\./,'').replaceAll('_',' ');
  return `<section id="sheet-progress" class="sheet-section level-roadmap"><h3>Next level & unlocks</h3><div class="roadmap-next"><strong>${p.level<p.maxLevel?`${p.xpToNextLevel} XP to level ${p.level+1}`:`Level ${p.maxLevel} reached`}</strong><progress value="${p.xpIntoLevel}" max="${Math.max(1,p.xpIntoLevel+p.xpToNextLevel)}" aria-label="Experience toward next level"></progress><small>${p.xp} total XP${p.nextLevelXp?' · next threshold '+p.nextLevelXp:''}</small></div><div class="roadmap-points"><span>Stat points <b>${development?.unspentPoints??0}</b></span><span>Personal tree <b>${personal?.unspentPoints??0}</b></span><span>Class tree <b>${classTree?.unspentPoints??0}</b></span></div>${view.journey?.active&&!view.journey.classesUnlocked?'<p class="small">Your stat points are banked. Class selection, class trees and manual stats open on Floor 3.</p>':''}<p>${nextSkills.length?`Next personal skill: <strong>${e(nextSkills[0].label)}</strong> at level ${nextSkills[0].level}.`:'All personal level unlocks earned.'} ${nextTier?`Next class milestone: <strong>level ${nextTier}</strong>.`:'No further class level milestones.'}</p>${tiers.length?`<ol class="roadmap-tiers" aria-label="Class milestone levels">${tiers.map(level=>`<li class="${p.level>=level?'reached':'locked'}"><span>${p.level>=level?'✓':'◇'}</span> Lv ${level}</li>`).join('')}</ol>`:''}${practice.length?`<details><summary>Closest practice ranks</summary><ul>${practice.map(s=>`<li>${e(skillName(s.abilityId))}: rank ${s.rank}/${s.maxRank} · ${Math.max(0,s.nextRankUses-s.uses)} more committed uses to rank ${s.rank+1}</li>`).join('')}</ul></details>`:''}<p class="small muted">Earn XP by completing encounters. Skill practice comes from committed ability use. Spend points and train in the safe room; previewing never earns XP or practice.</p></section>`;
}
