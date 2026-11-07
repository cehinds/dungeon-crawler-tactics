"""Actual keyboard/pointer combat regression. Reads public views; never injects state.
Reuses the authored Block A walking helper, then exercises new combat presentation.
"""
import argparse
from pathlib import Path
import sys
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--url',default='http://127.0.0.1:8765')
ap.add_argument('--browser',default='/usr/bin/chromium')
ap.add_argument('--output',type=Path,default=Path('Rebuild/CombatFollowthroughComparison/after/targeted'))
a=ap.parse_args()
source=Path(__file__).with_name('playtest_block_a.py').read_text()
source=source[:source.index(" capture('initial')")]
source+='''
 page.set_viewport_size({'width':1280,'height':720})
 walk('false-guild');key('e');assert v()['mode']=='battle';capture('desktop-battle')
 initial=v();carl=next(u for u in initial['battle']['units'] if u['id']=='carl')
 def unchanged(before):
  after=v()
  for k in ['party','inventory','turn']:
   assert after[k]==before[k],('Preview/cancel mutation',k)
  assert after['battle']==before['battle'],'Preview/cancel changed battle'
 def aim():
  page.locator('[data-skill="bomb"]').click();page.locator('[data-aim-map]').click();assert page.locator('[data-aim-instruction]').count()
 # A canceled aim and canceled preview retain both resources and move/action rights.
 aim();page.keyboard.press('Escape');assert not page.locator('[data-aim-instruction]').count();unchanged(initial)
 aim();tile(carl['x'],carl['y']);page.wait_for_timeout(120)
 f=v()['forecast'];assert f['valid'] and f['friendlyFire'];assert page.locator('[data-friendly-fire]').is_visible();assert page.locator('#confirm-action').inner_text()=='Confirm friendly fire';assert f['affectedCells'];unchanged(initial)
 for size,label in [({'width':1280,'height':720},'desktop'),({'width':390,'height':844},'mobile')]:
  page.set_viewport_size(size);page.wait_for_timeout(200);assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');capture(label+'-friendly-fire-preview')
  boxes=page.evaluate("""() => {let a=document.querySelector('#world').getBoundingClientRect(),b=document.querySelector('.modal').getBoundingClientRect();return {map:{x:a.x,y:a.y,width:a.width,height:a.height},forecast:{x:b.x,y:b.y,width:b.width,height:b.height},overlap:Math.max(0,Math.min(a.right,b.right)-Math.max(a.left,b.left))*Math.max(0,Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top))}}""")
  (a.output/(label+'-layout.json')).write_text(json.dumps(boxes,indent=2))
  assert boxes['overlap']==0,('Forecast overlaps map',boxes)
  for selector in ['#confirm-action','[data-open="Targets"]','[data-cancel-forecast]']:
   button=page.locator(selector).bounding_box();assert button and button['y']>=0 and button['y']+button['height']<=size['height'],(selector,'requires scrolling')
  unit_coverage=page.evaluate("""() => {const box=document.querySelector('#world').getBoundingClientRect(),b=rpgView.battle,t=Math.floor(Math.min(box.width/(b.width+2),box.height/(b.height+2))),r=document.querySelector('.modal').getBoundingClientRect();return [...b.units,...b.enemies].filter(u=>u.hp>0).map(u=>{const x=box.x+Math.floor(box.width/2-b.width/2*t)+(u.x+.5)*t,y=box.y+Math.floor(box.height/2-b.height/2*t)+(u.y+.5)*t;return {id:u.id,x,y,covered:x>=r.left&&x<=r.right&&y>=r.top&&y<=r.bottom}})}""")
  assert not any(u['covered'] for u in unit_coverage),unit_coverage
 close();unchanged(initial);page.set_viewport_size({'width':1280,'height':720})
 # Empty ground outside blast distance from actors remains a valid honest preview.
 aim();tile(3,2);page.wait_for_timeout(100);ground=v()['forecast'];assert ground['valid'];assert not ground['friendlyFire'];assert ground['affectedCells'];capture('empty-ground-preview');close();unchanged(initial)
 # Move after cancel, then preview direct enemy ID and validate exact commit receipts.
 tile(3,1);moved=v();actor=next(u for u in moved['battle']['units'] if u['id']=='carl');assert actor['moved'] and not actor['acted'];capture('move-after-cancel')
 page.locator('[data-command="endTurn"]').click();page.locator('#end-turn-confirm').click();page.wait_for_function("rpgView.battle.phase !== 'enemy'",timeout=20000);actor=next(u for u in v()['battle']['units'] if u['id']=='carl')
 page.locator('[data-skill="bomb"]').click()
 candidates=page.locator('[data-target]');assert candidates.count(),'Direct target list missing'
 selected=False
 for i in range(candidates.count()):
  target=candidates.nth(i).get_attribute('data-target');candidates.nth(i).click();page.wait_for_timeout(80)
  if v()['forecast']['valid']:selected=True;break
  page.locator('[data-open="Targets"]').click();candidates=page.locator('[data-target]')
 assert selected,'No reachable direct enemy target after legal move'
 before=v();f=before['forecast'];capture('direct-target-preview');assert not next(u for u in before['battle']['units'] if u['id']=='carl')['acted']
 page.locator('#confirm-action').click();page.wait_for_timeout(70);after=v();assert after['battle']['effectEvents']==f['events'];assert next(u for u in after['battle']['units'] if u['id']=='carl')['mp']==actor['mp']-f['cost'];assert next(u for u in after['battle']['units'] if u['id']=='carl')['acted'];capture('direct-target-impact');page.wait_for_timeout(280);capture('direct-target-impact-wave')
 for event in f['events']:
  if event['kind']=='damage':
   old=next((u for u in before['battle']['units']+before['battle']['enemies'] if u['id']==event['targetId']),None);new=next((u for u in after['battle']['units']+after['battle']['enemies'] if u['id']==event['targetId']),None)
   if old and new:assert old['hp']-new['hp']==min(old['hp'],event['amount'])
 # Independent fresh natural encounter verifies acting before moving.
 page.reload();page.wait_for_function('window.rpgView?.party?.length===2');page.wait_for_timeout(500);walk('false-guild');key('e');fresh=v();c=next(u for u in fresh['battle']['units'] if u['id']=='carl');aim();tile(c['x'],c['y']);page.locator('#confirm-action').click();page.wait_for_timeout(100);tile(3,1);post=v();c=next(u for u in post['battle']['units'] if u['id']=='carl');assert c['acted'] and c['moved'] and (c['x'],c['y'])==(3,1),'Act then move failed';capture('act-then-move')
 assert not errors,errors
 (a.output/'report.json').write_text(json.dumps({'passed':True,'errors':errors,'fixtures':[],'scope':'Natural first encounter; keyboard walking; actual pointer preview/cancel, empty-ground aim, friendly fire warning, responsive map, move after cancel, direct-ID Bomb commit and event/HP/MP parity','forecast':f,'actions':actions},indent=2));b.close();print('PASS combat followthrough targeted browser controls')
'''
sys.argv=['playtest_block_a.py','--url',a.url,'--browser',a.browser,'--output',str(a.output)]
exec(compile(source,'combat-followthrough-browser','exec'))
