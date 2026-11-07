"""Block A browser route: real controls; only disclosed migration fixture uses storage."""
import argparse, json, math
from collections import deque
from pathlib import Path
from playwright.sync_api import sync_playwright
ap=argparse.ArgumentParser(description=__doc__)
ap.add_argument('--url',default='http://127.0.0.1:8771');ap.add_argument('--browser',default='/usr/bin/chromium');ap.add_argument('--seed',type=int,default=1337);ap.add_argument('--output',type=Path,default=Path('Rebuild/BlockAComparison/final'));ap.add_argument('--checkpoint',type=Path);ap.add_argument('--environment',action='store_true');ap.add_argument('--environment-object',default='')
a=ap.parse_args();a.output.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
 b=p.chromium.launch(executable_path=a.browser,args=['--no-sandbox']);page=b.new_page(viewport={'width':1440,'height':1000});errors=[];actions=[];page.on('pageerror',lambda e:errors.append(str(e)));page.on('response',lambda r:errors.append(str(r.status)+' '+r.url) if r.status>=400 else None)
 page.goto(a.url+'?seed='+str(a.seed));page.wait_for_function('window.rpgView?.party?.length===2');page.wait_for_timeout(900)
 def v():return page.evaluate('rpgView')
 def capture(n):
  page.screenshot(path=str(a.output/(n+'.png')));(a.output/(n+'.json')).write_text(json.dumps(v(),indent=2))
 def close():
  if page.locator('#close-modal').count():page.locator('#close-modal').click()
 def panel(n):
  close();page.keyboard.press('Escape');page.locator('[data-open="'+n+'"]').click()
 def key(k):
  page.keyboard.down(k);page.wait_for_timeout(25);page.keyboard.up(k);page.wait_for_timeout(190)
 def walk(oid):
  close();s=v();m=s['world'];o=next(o for o in m['objects'] if o['id']==oid);start=(s['x'],s['y']);q=deque([start]);prev={start:None};goal=None
  blocked={(x,y) for prop in m.get('props',[]) if prop.get('blocksMovement',True) for x in range(prop['x'],prop['x']+prop['width']) for y in range(prop['y'],prop['y']+prop['height'])}
  while q:
   xy=q.popleft()
   if abs(xy[0]-o['x'])+abs(xy[1]-o['y'])<=1:goal=xy;break
   for dx,dy in [(1,0),(-1,0),(0,1),(0,-1)]:
    n=(xy[0]+dx,xy[1]+dy)
    if 0<=n[0]<m['width'] and 0<=n[1]<m['height'] and n not in prev and n not in blocked and m['tiles'][n[1]*m['width']+n[0]]=='.':prev[n]=xy;q.append(n)
  assert goal is not None,oid
  path=[]
  while goal!=start:path.append(goal);goal=prev[goal]
  for x,y in reversed(path):
   s=v();key('ArrowRight' if x>s['x'] else 'ArrowLeft' if x<s['x'] else 'ArrowDown' if y>s['y'] else 'ArrowUp');assert (v()['x'],v()['y'])==(x,y),(oid,x,y,v()['message'])
 def tile(x,y):
  box=page.locator('#world').bounding_box();s=v()['battle'];t=math.floor(min(box['width']/(s['width']+2),box['height']/(s['height']+2)));page.mouse.click(box['x']+math.floor(box['width']/2-s['width']/2*t)+(x+.5)*t,box['y']+math.floor(box['height']/2-s['height']/2*t)+(y+.5)*t);page.wait_for_timeout(65)
 def fight(oid):
  walk(oid);key('e');assert v()['mode']=='battle',v()['message'];capture(oid+'-start')

  environment_done = False
  water_done = False
  for turn in range(75):
   if v()['mode']!='battle':break
   for uid in ['carl','donut']:
    close();s=v()
    if s['mode']!='battle':break
    u=next(u for u in s['battle']['units'] if u['id']==uid)
    if u['hp']<=0:continue
    tile(u['x'],u['y'])
    if a.environment and oid=='goblin-workshop' and uid=='carl' and environment_done and not water_done:
     blocker=next((e for e in s['battle']['enemies'] if e['hp']>0 and (e['x'],e['y'])==(10,5)),None)
     if blocker:
      page.locator('[data-skill="powerful-strike"]').click();page.locator('[data-target="'+blocker['id']+'"]').click();page.wait_for_timeout(70);f=v()['forecast'];assert f['valid'];page.locator('#confirm-action').click();page.wait_for_timeout(100);assert v()['mode']=='battle';assert v()['battle']['effectEvents']==f['events'];assert next(e for e in v()['battle']['enemies'] if e['id']==blocker['id'])['hp']==0
     tile(10,5);after_move=v();actor=next(e for e in after_move['party'] if e['id']=='carl');assert (actor['x'],actor['y'])==(10,5);assert not any(x['id']=='burning' for x in actor['statuses']);assert any(e['kind']=='statusRemoved' and e['tag']=='burning' for e in after_move['battle']['effectEvents']);water_done=True;capture('authored-water-extinguished');continue
    enemy=next(e for e in s['battle']['enemies'] if e['hp']>0)
    environment_attack=a.environment and oid=='goblin-workshop' and uid=='carl' and not environment_done
    if environment_attack:enemy=next(e for e in s['battle']['effectObjects'] if e['id']==a.environment_object)
    destination=((11,5) if not environment_done else (10,5)) if a.environment and uid=='carl' and not water_done else (enemy['x'],enemy['y'])
    if not u['moved']:
     occ={(e['x'],e['y']) for e in s['battle']['units']+s['battle']['enemies'] if e['hp']>0}|{(e['x'],e['y']) for e in s['battle']['obstacles']}
     candidates=[(x,y) for y in range(s['battle']['height']) for x in range(s['battle']['width']) if 0<abs(x-u['x'])+abs(y-u['y'])<=3 and (x,y) not in occ]
     for x,y in sorted(candidates,key=lambda xy:abs(xy[0]-destination[0])+abs(xy[1]-destination[1])):
      tile(x,y)
      if next(e for e in v()['battle']['units'] if e['id']==uid)['moved']:break
    u=next(e for e in v()['battle']['units'] if e['id']==uid)
    for sid in reversed(u['skills']):
     if a.environment and oid=='goblin-workshop' and uid=='donut' and not water_done:continue
     if a.environment and oid=='goblin-workshop' and uid=='carl' and environment_done and not water_done:continue
     if environment_attack and (sid!='bomb' or (u['x'],u['y'])!=(11,5)):continue
     close();button=page.locator('[data-skill="'+sid+'"]')
     if not button.count() or button.is_disabled():continue
     button.click();target=page.locator('[data-target="'+enemy['id']+'"]')
     if not target.count():close();continue
     target.click();page.wait_for_timeout(70);f=v().get('forecast')
     if f and f['valid']:
      before=v();assert next(e for e in before['battle']['enemies']+before['battle'].get('effectObjects',[]) if e['id']==enemy['id'])['hp']==next(e for e in s['battle']['enemies']+s['battle'].get('effectObjects',[]) if e['id']==enemy['id'])['hp'], 'Forecast mutated enemy HP'
      capture(oid+'-forecast')
      if environment_attack:assert any(e['tag']=='explosion' for e in f['events']);assert any(e['kind']=='statusApplied' and e['tag']=='burning' and e['targetId']=='carl' for e in f['events']);capture('authored-explosion-forecast')
      page.locator('#confirm-action').click();page.wait_for_timeout(150);after=v()
      if after['mode']=='battle':assert next(e for e in after['party'] if e['id']==uid)['mp']==next(e for e in before['party'] if e['id']==uid)['mp']-f['cost'], 'Resource charge differs from forecast'
      if after.get('battle') and 'events' in f:assert after['battle']['effectEvents']==f['events'], 'Committed events differ from preview'
      if environment_attack:
       environment_done=True;assert 'goblin-workshop:'+a.environment_object in after['destroyedEncounterObjectIds'];assert any(x['id']=='burning' for x in next(e for e in after['party'] if e['id']=='carl')['statuses']);capture('authored-explosion-confirmed');page.wait_for_timeout(300);capture('authored-explosion-wave-02');page.wait_for_timeout(350);capture('authored-explosion-wave-03')
      actions.append({'encounter':oid,'skill':sid,'forecast':f,'events':after.get('battle',{}).get('effectEvents',[]) if after.get('battle') else []});capture(oid+'-effect');break
   if v()['mode']=='battle':
    if a.environment:(a.output/'environment-latest.json').write_text(json.dumps(v(),indent=2))
    close();page.locator('[data-command="endTurn"]').click();page.locator('#end-turn-confirm').click();page.wait_for_timeout(160)
    if a.environment and oid=='goblin-workshop':
     actor=next(u for u in v()['party'] if u['id']=='carl')
     if actor['x']==10 and actor['y']==5 and not any(x['id']=='burning' for x in actor['statuses']):
      assert any(e['kind']=='statusRemoved' and e['tag']=='burning' for e in v()['battle']['effectEvents']);water_done=True;capture('authored-water-extinguished')
  if a.environment and oid=='goblin-workshop':
   capture('environment-final-state')
   assert environment_done and water_done,'Actual environment explosion/water suppression not committed'
  assert v()['mode']=='explore',(oid,v()['mode'],v()['message']);assert oid in v()['cleared'];capture(oid+'-victory')
 capture('initial')
 for n in ['Party','Skills','Map']:panel(n);capture('initial-'+n.lower())
 close()
 if a.checkpoint:
  page.evaluate('(s)=>localStorage.setItem("dcc.rebuild.v1",s)',a.checkpoint.read_text());panel('Save');page.locator('#load-button').click();page.wait_for_timeout(200);assert 'loaded' in v()['message'].lower();capture('migration-loaded')
 if 'false-guild' not in v()['cleared']:fight('false-guild')
 if v()['questStage']<2:walk('mordecai');key('e')
 capture('guide')
 for oid in (['goblin-workshop'] if a.environment else ['goblin-workshop','hoarder','juicer','ball-of-swine']):
  if oid not in v()['cleared']:
   walk('safe-room')
   if not a.environment:panel('Save');page.locator('#rest-button').click();page.wait_for_timeout(100);close()
   fight(oid)
 walk('safe-room');panel('Save');page.locator('#rest-button').click();page.wait_for_timeout(100);page.locator('#save-button').click();page.wait_for_function('document.querySelector("#save-result")?.textContent==="Game saved."');saved=v();(a.output/'safe-checkpoint.json').write_text(page.evaluate('localStorage.getItem("dcc.rebuild.v1")'));page.locator('#load-button').click();page.wait_for_timeout(200);persistent=lambda party:[{k:value for k,value in u.items() if k not in {'x','y','moved','acted','ended'}} for u in party];assert persistent(v()['party'])==persistent(saved['party']);capture('save-load')
 for n in ['Party','Skills','Journal']:panel(n);capture('earned-'+n.lower())
 page.set_viewport_size({'width':390,'height':844})
 for n in ['Party','Skills','Journal']:
  panel(n);assert page.evaluate('document.documentElement.scrollWidth<=innerWidth');assert page.locator('.modal').evaluate('(e)=>e.scrollWidth<=e.clientWidth');capture('mobile-'+n.lower())
 close();page.set_viewport_size({'width':1440,'height':1000})
 if a.environment:
  assert 'goblin-workshop:'+a.environment_object in v()['destroyedEncounterObjectIds'];capture('authored-destruction-save-load')
 else:walk('exit');key('e');assert v()['mode']=='complete';capture('complete')
 assert not errors,errors
 (a.output/'report.json').write_text(json.dumps({'errors':errors,'seed':a.seed,'complete':v()['mode']=='complete','environmentScenario':a.environment,'actions':actions,'cleared':v()['cleared'],'checkpointFixture':str(a.checkpoint) if a.checkpoint else None,'scope':'Actual authored oil ignition, crate Bomb blast, water suppression, UI-only combat and destruction save/load; optional earned checkpoint loaded unchanged.' if a.environment else 'Keyboard walking and UI-only combat, save/load, responsive menus, full current Floor One route. Checkpoint fixture only if explicitly supplied.'},indent=2));b.close();print('PASS Block A browser route')
