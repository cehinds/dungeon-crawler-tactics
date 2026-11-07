"""Block B published-browser QA; actual keyboard/pointer controls, read-only core views.
Reuses the Block A route unchanged except reward acknowledgement and awaiting visible
animated enemy phases. No state/command injection or fixture is used by default.
"""
import argparse
from pathlib import Path
import sys

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--url', default='http://127.0.0.1:8771')
parser.add_argument('--browser', default='/usr/bin/chromium')
parser.add_argument('--output', type=Path, default=Path('Rebuild/BlockBComparison/after'))
parser.add_argument('--full-route', action='store_true')
parser.add_argument('--smoke', action='store_true')
parser.add_argument('--defeat-check', action='store_true')
a = parser.parse_args()
a.output.mkdir(parents=True, exist_ok=True)
if a.smoke:
    smoke = Path(__file__).with_name('playtest_floor_one.py').read_text()
    smoke = smoke.replace('page.wait_for_timeout(150)', "page.wait_for_function(\"rpgView.mode !== 'battle' || rpgView.battle.phase !== 'enemy'\", timeout=20000)")
    smoke = smoke.replace('page.screenshot(path=str(args.output / "victory.png"))', 'page.screenshot(path=str(args.output / "victory.png"))\n    if page.locator("#reward-continue").count(): page.locator("#reward-continue").click()')
    sys.argv = ['playtest_floor_one.py', '--url', a.url, '--browser', a.browser, '--output', str(a.output)]
    exec(compile(smoke, 'playtest_floor_one.py', 'exec'))
    raise SystemExit(0)
source = Path(__file__).with_name('playtest_block_a.py').read_text().replace("page=b.new_page(viewport={'width':1440,'height':1000})", "page=b.new_context(viewport={'width':1440,'height':1000}).new_page()")
# Avoid the legacy harness closing the new reward modal as it advances actors.
source = source.replace("close();s=v()\n    if s['mode']!='battle':break", "s=v()\n    if s['mode']!='battle':break\n    close();s=v()")
# Both existing route helpers and assertions remain authoritative. Adapt timing
# to the new user-visible enemy sequence, then acknowledge the reward through UI.
source = source.replace("page.wait_for_timeout(160)", "page.wait_for_function(\"rpgView.mode !== 'battle' || rpgView.battle.phase !== 'enemy'\", timeout=20000);settled=v();page.wait_for_timeout(500);assert v()['turn']==settled['turn'];assert v().get('battle')==settled.get('battle'),'Duplicate enemy timer'")
source = source.replace("assert v()['mode']=='explore',(oid,v()['mode'],v()['message']);assert oid in v()['cleared'];capture(oid+'-victory')", "assert v()['mode']=='explore',(oid,v()['mode'],v()['message']);assert oid in v()['cleared'];capture(oid+'-victory'); acknowledge(oid)")
source = source.replace("page.locator('#end-turn-confirm').click();page.wait_for_function", "page.locator('#end-turn-confirm').click();page.wait_for_timeout(70);assert v()['battle']['phase']=='enemy';capture(oid+'-enemy-phase');locked=v();page.keyboard.press('Escape');page.keyboard.press('ArrowRight');assert v()['selectedId']==locked['selectedId'];assert not page.locator('#close-modal').count();page.wait_for_function")
source = source.replace("if u['hp']<=0:continue", """if u['hp']<=0:continue
    if globals().get('use_supply') and oid=='goblin-workshop' and not globals().get('supply_used') and any(p['actorId']==uid and p['itemId']==supply_id and p['available'] for p in s.get('consumablePreviews',[])):
     page.locator('[data-open="Items"]').click();page.locator('#crawler-select').focus();page.keyboard.press('Home');page.keyboard.press('ArrowDown' if uid=='donut' else 'Home');page.keyboard.press('Enter');before_count=next(i['count'] for i in s['inventory'] if i['itemId']==supply_id);page.locator('[data-item="'+supply_id+'"][data-actor="'+uid+'"]').click();page.wait_for_timeout(100);assert next(i['count'] for i in v()['inventory'] if i['itemId']==supply_id)==before_count-1;assert next(p for p in v()['battle']['units'] if p['id']==uid)['acted'];assert any(e['kind']=='heal' and e['targetId']==uid and e['amount']>0 for e in v()['battle']['effectEvents']);globals()['supply_used']=True;capture('purchased-supply-used');close();continue""")
source = source.replace("capture(oid+'-start')", """capture(oid+'-start')
  if globals().get('use_supply') and oid=='goblin-workshop':
   for waiting in range(8):
    if any(p['itemId']==supply_id and p['available'] for p in v().get('consumablePreviews',[])):break
    page.locator('[data-command="endTurn"]').click();page.locator('#end-turn-confirm').click();page.wait_for_timeout(70);capture('preparation-wait-enemy-phase');page.wait_for_function("rpgView.mode !== 'battle' || rpgView.battle.phase !== 'enemy'",timeout=20000);assert v()['mode']=='battle','Party defeated while waiting for damage'
   assert any(p['itemId']==supply_id and p['available'] for p in v().get('consumablePreviews',[])),'No live consumable opportunity after enemy approach'""")
helper = '''
 def acknowledge(oid):
  assert v().get('reward'),'Victory reward acknowledgement missing'
  before=v();r=before['reward'];assert r['name'] and page.locator('.reward-title').inner_text()==r['name'];reward_text=page.locator('.modal').inner_text();assert all(('Level '+str(p['levelBefore'])+' → '+str(p['levelAfter'])) in reward_text for p in r['party'] if p['levelAfter']>p['levelBefore']);names={i['id']:i['name'] for i in page.request.get(a.url+'/data/floor-one-rpg.json').json()['items']};assert all(('+'+str(i['count'])+' '+names[i['itemId']]) in reward_text for i in r['items']);assert page.locator('.reward-gold').inner_text()=='+'+str(r['gold'])+' gold';assert all(('+'+str(p['xp'])+' XP') in page.locator('.modal').inner_text() for p in r['party']);assert all(('+'+str(i['count'])+' ') in page.locator('.modal').inner_text() for i in r['items']);assert 'Safe room:' in page.locator('.modal').inner_text();globals()['rewards_verified']=globals().get('rewards_verified',0)+1;capture(oid+'-rewards');page.locator('#reward-continue').click();page.wait_for_function('!rpgView.reward')
  after=v();assert after['gold']==before['gold'];assert after['inventory']==before['inventory'];assert after['party']==before['party'];page.wait_for_timeout(900);assert v()['gold']==after['gold'],'Duplicate reward/timer'
'''
source = source.replace(" capture('initial')", helper + " capture('initial')", 1)
source = source.replace("'errors':errors,'seed':a.seed", "'errors':errors,'rewardsVerified':globals().get('rewards_verified',0),'seed':a.seed")
if a.defeat_check:
    import json
    fixture_path=Path('Rebuild/Tests/Fixtures/earned-safe-v2.json')
    fixture=json.loads(fixture_path.read_text())
    for unit in fixture['state']['party']:unit['hp']=1
    disclosed=a.output/'low-hp-earned-v2-fixture.json'
    disclosed.write_text(json.dumps(fixture,indent=2))
    storage_script='localStorage.setItem("dcc.rebuild.v1",'+json.dumps(json.dumps(fixture))+')'
    source=source.replace("page.goto(a.url+'?seed='", "page.add_init_script("+repr(storage_script)+");page.goto(a.url+'?seed='")
    source=source[:source.index(" capture('initial')")]+'''
 panel('Save');page.locator('#load-button').click();page.wait_for_timeout(150);assert 'loaded' in v()['message'].lower();checkpoint=v();capture('low-hp-checkpoint-loaded')
 walk('goblin-workshop');key('e');assert v()['mode']=='battle'
 for waiting in range(30):
  if v()['mode']!='battle':break
  page.locator('[data-command="endTurn"]').click();page.locator('#end-turn-confirm').click();page.wait_for_function("rpgView.mode !== 'battle' || rpgView.battle.phase !== 'enemy'",timeout=20000)
 assert v()['mode']=='defeat';assert page.locator('#retry-button').is_visible();capture('actual-defeat');page.locator('#retry-button').click();page.wait_for_function("rpgView.mode==='explore'");assert v()['inventory']==checkpoint['inventory'];assert v()['cleared']==checkpoint['cleared'];capture('retry-checkpoint');settled=v();page.wait_for_timeout(1200);assert v()['turn']==settled['turn'];assert v()['mode']=='explore';origin=(v()['x'],v()['y']);walk('mordecai');assert (v()['x'],v()['y'])!=origin;capture('retry-movement');assert not errors,errors
 (a.output/'report.json').write_text(json.dumps({'passed':True,'errors':errors,'fixture':'low-hp-earned-v2-fixture.json','fixtureSource':'Rebuild/Tests/Fixtures/earned-safe-v2.json','fixtureChange':'Party HP set to1 within legal bounds before browser boot; loaded with actual Load game button; no injected game command','scope':'Actual enemy damage defeat, real Retry button, checkpoint inventory/cleared retained, timer quiet1200ms, subsequent keyboard walking'},indent=2));b.close();print('PASS actual defeat Retry and movement')
'''
    sys.argv=['playtest_block_a.py','--url',a.url,'--browser',a.browser,'--output',str(a.output)]
    exec(compile(source,'block-b-defeat-check','exec'))
    raise SystemExit(0)
if not a.full_route:
    source = source[:source.index(" capture('initial')")] + '''
 capture('initial')
 # Measure a real browser key down until the public core view changes, then
 # wait one animation frame so the corresponding renderer paint is eligible.
 import statistics
 page.evaluate("""() => { window.__qaLatency=[]; addEventListener('keydown',e=>{if(!e.key.startsWith('Arrow')||e.repeat)return;const x=rpgView.x,y=rpgView.y,t=performance.now();function observe(){if(rpgView.x!==x||rpgView.y!==y){requestAnimationFrame(()=>window.__qaLatency.push(performance.now()-t));return;}if(performance.now()-t<500)requestAnimationFrame(observe);}requestAnimationFrame(observe);},{capture:true}); }""")
 for direction in ['ArrowRight','ArrowLeft']*8:
  page.wait_for_timeout(220);page.keyboard.down(direction);page.wait_for_timeout(75);page.keyboard.up(direction)
 latencies=page.evaluate('__qaLatency');assert latencies,'No movement timing samples'
 latency={'samplesMs':latencies,'p50Ms':statistics.median(latencies),'p95Ms':sorted(latencies)[min(len(latencies)-1,math.ceil(len(latencies)*.95)-1)],'method':'In-page capture keydown timestamp to read-only public view position change observed by requestAnimationFrame plus following frame; no injected commands'}
 (a.output/'input-latency.json').write_text(json.dumps(latency,indent=2))
 page.set_viewport_size({'width':1280,'height':720})
 panel('Save');assert page.locator('#rest-button').is_disabled();assert page.locator('#save-button').is_disabled();capture('outside-safe-disabled');close()
 # A held direction must stop when opening a modal, even after that modal closes.
 page.keyboard.down('ArrowRight');page.wait_for_timeout(25);page.keyboard.press('Escape');page.keyboard.up('ArrowRight');pos=(v()['x'],v()['y']);page.wait_for_timeout(500);assert (v()['x'],v()['y'])==pos;close();page.wait_for_timeout(500);assert (v()['x'],v()['y'])==pos
 page.context.new_cdp_session(page).send('Emulation.setFocusEmulationEnabled',{'enabled':False});page.evaluate("() => {window.__qaBlur=0;addEventListener('blur',()=>__qaBlur++);}");page.keyboard.down('ArrowDown');page.wait_for_timeout(25);other=page.context.new_page();page.context.new_cdp_session(other).send('Emulation.setFocusEmulationEnabled',{'enabled':False});other.goto('about:blank');other.bring_to_front();page.wait_for_timeout(150);pos=(v()['x'],v()['y']);page.wait_for_timeout(700);assert (v()['x'],v()['y'])==pos;assert page.evaluate('__qaBlur')>0;page.keyboard.up('ArrowDown');page.bring_to_front();other.close();page.context.new_cdp_session(page).send('Emulation.setFocusEmulationEnabled',{'enabled':True})
 fight('false-guild');assert all(u['xp']>0 for u in v()['party']);assert v()['gold']>0
 walk('mordecai');key('e');close();walk('safe-room');key('e');capture('safe-room')
 page.locator('#rest-button').click();page.wait_for_timeout(100);assert all(u['hp']==u['maxHp'] and u['mp']==u['maxMp'] for u in v()['party'])
 page.locator('#save-button').click();page.wait_for_function('document.querySelector("#save-result")?.textContent==="Game saved."');capture('rest-save')
 page.locator('[data-open="Shop"]').click();capture('shop');before=v();offer=next(o for o in before['resupplyOffers'] if o['available']);count=lambda s:next((i['count'] for i in s['inventory'] if i['itemId']==offer['itemId']),0)
 page.locator('[data-buy="'+offer['offerId']+'"]').click();page.wait_for_timeout(150);assert v()['gold']==before['gold']-offer['goldCost'];assert count(v())==count(before)+offer['quantity'];capture('bought-supply')
 panel('Equipment');capture('equipment-preview');select=page.locator('#crawler-select');select.focus();page.keyboard.press('ArrowDown');page.keyboard.press('Enter');page.wait_for_timeout(100);assert select.input_value()=='donut','Native select keyboard did not change crawler'
 gear=next(p for p in v()['equipmentPreviews'] if p['itemId'] and p['available']);actor_id=gear['actorId'];page.locator('#crawler-select').focus();page.keyboard.press('Home');page.keyboard.press('ArrowDown' if actor_id=='donut' else 'Home');page.keyboard.press('Enter');before=v();assert page.locator('.stat-preview').count();equip=page.locator('[data-equip]:not([data-equip=""]):not([disabled])').first
 assert equip.count(),'No personal equipment available'
 if equip.count():
  item=equip.get_attribute('data-equip');preview=next(p for p in before['equipmentPreviews'] if p['actorId']==actor_id and p['itemId']==item);old=next(u for u in before['party'] if u['id']==actor_id);equip.click();page.wait_for_timeout(100);assert next(u for u in v()['party'] if u['id']==actor_id)['equipment']==item;assert next(u for u in v()['party'] if u['id']==actor_id)['power']==old['power']+preview['powerDelta'];assert next(u for u in v()['party'] if u['id']==actor_id)['armor']==old['armor']+preview['armorDelta'];capture('equipped');page.locator('[data-equip=""]').click();page.wait_for_timeout(100);assert next(u for u in v()['party'] if u['id']==actor_id)['equipment']=='';capture('unequipped')
 walk('safe-room');panel('Save');page.locator('#save-button').click();page.wait_for_function('document.querySelector("#save-result")?.textContent==="Game saved."');saved=v();page.locator('#load-button').click();page.wait_for_timeout(150);assert v()['gold']==saved['gold'];assert v()['inventory']==saved['inventory'];assert [u['equipment'] for u in v()['party']]==[u['equipment'] for u in saved['party']];capture('preparation-save-load')
 for size,label in [({'width':390,'height':844},'mobile'),({'width':1280,'height':720},'desktop')]:
  page.set_viewport_size(size)
  for name in ['Party','Equipment','Items','Skills','Save']:
   panel(name);assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');assert page.locator('.modal').evaluate('(e)=>e.scrollWidth<=e.clientWidth');capture(label+'-'+name.lower())
 close();use_supply=True;supply_id=offer['itemId'];supply_used=False;fight('goblin-workshop');assert supply_used,'Purchased supply was not used in subsequent encounter';assert globals().get('rewards_verified',0)>=2;assert not errors,errors
 (a.output/'report.json').write_text(json.dumps({'errors':errors,'fixtures':[],'rewardsVerified':globals().get('rewards_verified',0),'scope':'Natural first encounter rewards, safe room rest/save, earned-gold resupply, equipment/native select, persistence and responsive menus','actions':actions},indent=2));b.close();print('PASS Block B preparation loop')
'''
sys.argv = ['playtest_block_a.py','--url',a.url,'--browser',a.browser,'--output',str(a.output)]
exec(compile(source, str(Path(__file__).with_name('playtest_block_a.py')), 'exec'))
