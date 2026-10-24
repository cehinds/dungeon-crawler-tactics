"""Real browser chamber/HUD regression, using legal campaign commands only."""
import json,os
from pathlib import Path
from playwright.sync_api import sync_playwright
from playtest_neighborhood import boot,view,save,wait,approach,send
from playtest_finish import cell,end,select_ability
ROOT=Path(__file__).resolve().parents[1]
OUT=ROOT/'Docs/Screenshots'
def snap(p,name):
 p.wait_for_timeout(400);p.screenshot(path=str(OUT/('chambers-'+name+'.png')),full_page=True)
def battle(p,label):
 result={'label':label,'size':[view(p)['width'],view(p)['height']], 'rotations':[]}
 result['openingNotifications']=p.locator('.game-toast').all_inner_texts()
 if label.endswith('-sewers'):assert not result['openingNotifications'],'Stale feedback crossed expedition transition'
 if p.viewport_size['width']<600:
  assert p.locator('.game-toast:not(.toast-error)').count()<=1
  result['guidanceFits']=p.locator('.hud-target>small').evaluate('(e)=>e.scrollHeight<=e.clientHeight+1')
  assert result['guidanceFits'],'Phone target guidance clips vertically'
 snap(p,label+'-opening')
 for r in range(4):
  if r:p.locator('#rotate-right').click()
  v=view(p);uid=v['selectedUnitId'];u=next(x for x in v['units'] if x['id']==uid)
  picked=p.evaluate('''u=>{const q=window.dungeon.cellToScreen(u.x,u.y);return window.dungeon.scene.screenToCell(q.x,q.y)}''',u)
  assert picked['x']==u['x'] and picked['y']==u['y'],picked
  cell(p,u['x'],u['y']);assert view(p)['selectedUnitId']==uid
  snap(p,label+'-rotation'+str(r));result['rotations'].append(p.locator('#compass-label').inner_text())
 p.locator('#open-actions').click();snap(p,label+'-abilities');p.locator('[data-modal-ability="ability.carl_bomb"]').click()
 action=next(a for a in view(p)['abilities'] if a['id']=='ability.carl_bomb')
 targets=[{'x':int(t.split('.')[1]),'y':int(t.split('.')[2])} for t in action['targetIds'] if t.startswith('tile.')]
 target=p.evaluate('''targets=>{let b=document.querySelector('#battlefield').getBoundingClientRect();return targets.map(t=>({...t,p:window.dungeon.cellToScreen(t.x,t.y)})).filter(t=>t.p.x>30&&t.p.x<b.width-30&&t.p.y>150&&t.p.y<b.height-70).sort((a,c)=>Math.hypot(a.p.x-b.width/2,a.p.y-b.height/2)-Math.hypot(c.p.x-b.width/2,c.p.y-b.height/2))[0]}''',targets)
 assert target,'No visibly clickable legal ability target'
 before=save(p);cell(p,target['x'],target['y']);wait(p,'window.dungeon.getView().canConfirm');snap(p,label+'-forecast')
 assert save(p)==before;p.locator('#detail-cancel-forecast').click();assert save(p)==before
 select_ability(p,'ability.carl_bomb');cell(p,target['x'],target['y']);wait(p,'window.dungeon.getView().canConfirm');p.locator('#detail-confirm-forecast').click();wait(p,'!window.dungeon.getView().canConfirm')
 rnd=view(p)['round'];actors=[]
 for i in range(4):
  assert view(p)['round']==rnd;actors.append(view(p)['selectedUnitId']);end(p)
 wait(p,'window.dungeon.getView().round>'+str(rnd));assert len(set(actors))==4
 snap(p,label+'-enemy-phase');result['actors']=actors
 result['overflow']=p.evaluate('document.documentElement.scrollWidth>innerWidth')
 return result
with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox']);results=[]
 for w,h in ([(390,844)] if os.environ.get('MOBILE_ONLY') else [(1672,941),(390,844)]):
  c=b.new_context(viewport={'width':w,'height':h});p=c.new_page();errors=[];p.on('pageerror',lambda e:errors.append(str(e)))
  try:
   boot(p,'http://127.0.0.1:5188');p.locator('#quick-enter').click();wait(p,"window.dungeon.getView().screen==='explore'");door=approach(p,'@encounter');p.locator('[data-explore-interact="'+door['id']+'"]').click();wait(p,"window.dungeon.getView().screen==='battle'")
   results.append(battle(p,str(w)+'-legacy'))
   send(p,'expedition_start',targetId='expedition.sewers');wait(p,"window.dungeon.getView().expedition?.id==='expedition.sewers'");results.append(battle(p,str(w)+'-sewers'))
   assert not errors,errors
  except Exception as e:
   snap(p,str(w)+'-failure');print('FAIL',w,repr(e));print(json.dumps(view(p))[:1000]);raise
  finally:c.close()
 b.close();print(json.dumps(results,indent=2))
