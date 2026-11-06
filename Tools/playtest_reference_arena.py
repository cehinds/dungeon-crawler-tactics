"""Capture actual published WASM worlds and battles; camera framing changes presentation only."""
import argparse, functools, hashlib, html, json, math, shutil, subprocess, threading
from collections import deque
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--url', default='http://127.0.0.1:8773')
p.add_argument('--browser', default='/usr/bin/chromium')
p.add_argument('--output', type=Path, default=ROOT/'Rebuild/ReferenceArenaComparison')
a=p.parse_args(); a.output.mkdir(parents=True,exist_ok=True)
report={'url':a.url,'revision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'captureDisclosure':'Actual published WebAssembly state and original renderer. Workshop and boss room screenshots use a camera-only browser response override to fit the generated room. No state, gameplay, geometry, assets, or draw calls are fabricated. Combat is entered by keyboard walking and E interaction.','runs':[],'publishedFiles':{}}
ref=ROOT/'Web/wwwroot/assets/reference-layers/clean-map.png'
if not ref.exists(): ref=ref.with_name('original-reference.png')
shutil.copyfile(ref,a.output/'reference.png')
report['referenceSource']=str(ref.relative_to(ROOT))
report['workingTreeDiffSha256']=hashlib.sha256(subprocess.check_output(['git','diff','HEAD'],cwd=ROOT)).hexdigest()
with sync_playwright() as pw:
    browser=pw.chromium.launch(executable_path=a.browser,headless=True,args=['--no-sandbox'])
    context=browser.new_context()
    for path in ('rpg-renderer.js','game.js','data/concept-room-rules.json','_framework/blazor.boot.json'):
        response=context.request.get(a.url.rstrip('/')+'/'+path)
        assert response.ok,'Cannot fingerprint '+path
        report['publishedFiles'][path]=hashlib.sha256(response.body()).hexdigest()
    context.close()
    for seed in (1337,42):
        page=browser.new_page(viewport={'width':1440,'height':1000}); errors=[]; missing=[]
        page.on('pageerror',lambda e:errors.append(str(e)))
        page.on('response',lambda r:missing.append({'url':r.url,'status':r.status}) if r.status>=400 else None)
        def camera(route):
            response=route.fetch(); source=response.text(); needle='const tile = this.tile,'
            assert needle in source,'Renderer camera anchor changed'
            source=source.replace(needle,'''const captureRoom = window.captureRoom;
      if (captureRoom && !battle) {
        this.tile = Math.floor(Math.min(r.width / (captureRoom.width + 2), r.height / (captureRoom.height + 2)));
        this.offsetX = Math.floor(r.width / 2 - (captureRoom.x + captureRoom.width / 2) * this.tile);
        this.offsetY = Math.floor(r.height / 2 - (captureRoom.y + captureRoom.height / 2) * this.tile);
      }
      const tile = this.tile,''')
            route.fulfill(response=response,body=source)
        page.route('**/rpg-renderer.js',camera)
        page.goto(a.url+('&' if '?' in a.url else '?')+f'seed={seed}')
        page.wait_for_function('window.rpgView?.world?.props?.length > 0',timeout=90000); page.wait_for_timeout(1800)
        def view(): return page.evaluate('window.rpgView')
        def key(k):
            page.keyboard.down(k); page.wait_for_timeout(25); page.keyboard.up(k); page.wait_for_timeout(190)
        state=view(); world=state['world']; assert state['seed']==seed
        (a.output/f'seed-{seed}-world.json').write_text(json.dumps(world,indent=2)+'\n')
        def neighbors(xy):
            for dx,dy in ((1,0),(-1,0),(0,1),(0,-1)):
                x,y=xy[0]+dx,xy[1]+dy
                if 0<=x<world['width'] and 0<=y<world['height'] and world['tiles'][y*world['width']+x]=='.': yield (x,y)
        def route(goal):
            s=view(); start=(s['x'],s['y']); prev={start:None}; q=deque([start])
            while q and goal not in prev:
                xy=q.popleft()
                for n in neighbors(xy):
                    if n not in prev: prev[n]=xy; q.append(n)
            assert goal in prev,f'No route to {goal}'
            path=[]; n=goal
            while n!=start: path.append(n); n=prev[n]
            for x,y in reversed(path):
                s=view(); key('ArrowRight' if x>s['x'] else 'ArrowLeft' if x<s['x'] else 'ArrowDown' if y>s['y'] else 'ArrowUp')
                assert (view()['x'],view()['y'])==(x,y),'Keyboard route diverged'
            return len(path)
        reachable={(state['x'],state['y'])}; q=deque(reachable)
        while q:
            for n in neighbors(q.popleft()):
                if n not in reachable: reachable.add(n); q.append(n)
        solids=[prop for prop in world['props'] if prop.get('blocksMovement',True)]
        collision=None
        for prop in solids:
            for x in range(prop['x'],prop['x']+prop['width']):
                for y in range(prop['y'],prop['y']+prop['height']):
                    assert world['tiles'][y*world['width']+x]=='#'
                    if collision: continue
                    for dx,dy,k in ((-1,0,'ArrowRight'),(1,0,'ArrowLeft'),(0,-1,'ArrowDown'),(0,1,'ArrowUp')):
                        if (x+dx,y+dy) in reachable: collision=(prop['id'],(x+dx,y+dy),k); break
        assert collision
        route(collision[1]); key(collision[2]); assert (view()['x'],view()['y'])==collision[1]
        room=next(r for r in world['rooms'] if r['id']=='goblin-workshop')
        tile_collisions=[]
        for material in ('~','#'):
            candidates=[]
            for y in range(max(0,room['y']-1),min(world['height'],room['y']+room['height']+1)):
                for x in range(max(0,room['x']-1),min(world['width'],room['x']+room['width']+1)):
                    if world['tiles'][y*world['width']+x]!=material: continue
                    for dx,dy,k in ((-1,0,'ArrowRight'),(1,0,'ArrowLeft'),(0,-1,'ArrowDown'),(0,1,'ArrowUp')):
                        if (x+dx,y+dy) in reachable: candidates.append(((x+dx,y+dy),k,(x,y)))
            assert candidates,'No accessible '+material+' edge'
            adjacent,direction,blocked_cell=candidates[0]; route(adjacent); key(direction)
            assert (view()['x'],view()['y'])==adjacent,'Blocked material allowed movement: '+material
            tile_collisions.append({'tile':material,'blockedCell':blocked_cell,'approach':adjacent,'message':view()['message']})
        page.evaluate('(r)=>window.captureRoom=r',room); page.wait_for_timeout(400)
        page.locator('#world').screenshot(path=str(a.output/f'seed-{seed}-workshop.png'))
        page.screenshot(path=str(a.output/f'seed-{seed}-desktop.png'))
        workshop=next((r for r in world['rooms'] if 'workshop' in r['id']),None)
        if workshop:
            page.evaluate('(r)=>window.captureRoom=r',workshop); page.wait_for_timeout(300)
            page.locator('#world').screenshot(path=str(a.output/f'seed-{seed}-goblin-workshop.png'))
            page.evaluate('(r)=>window.captureRoom=r',room); page.wait_for_timeout(300)
        boss=next(r for r in world['rooms'] if r['id']=='ball-of-swine-complex')
        page.evaluate('(r)=>window.captureRoom=r',boss); page.wait_for_timeout(300)
        page.locator('#world').screenshot(path=str(a.output/f'seed-{seed}-boss.png'))
        page.evaluate('(r)=>window.captureRoom=r',room); page.wait_for_timeout(300)
        page.set_viewport_size({'width':390,'height':844}); page.wait_for_timeout(400)
        page.screenshot(path=str(a.output/f'seed-{seed}-mobile-workshop.png'))
        page.evaluate('window.captureRoom=null'); page.set_viewport_size({'width':1440,'height':1000}); page.wait_for_timeout(250)
        encounter=next(o for o in world['objects'] if o['id']=='false-guild')
        approaches=[xy for xy in reachable if abs(xy[0]-encounter['x'])+abs(xy[1]-encounter['y'])<=1]
        assert approaches,'No reachable encounter approach'; steps=route(approaches[0]); key('e')
        page.wait_for_timeout(400); assert view()['mode']=='battle',view()['message']
        def tile(x,y):
            box=page.locator('#world').bounding_box(); battle=view()['battle']
            t=math.floor(min(box['width']/(battle['width']+2),box['height']/(battle['height']+2)))
            page.mouse.click(box['x']+math.floor(box['width']/2-battle['width']*t/2)+(x+.5)*t,box['y']+math.floor(box['height']/2-battle['height']*t/2)+(y+.5)*t)
            page.wait_for_timeout(70)
        for turn in range(60):
            if view()['mode']!='battle': break
            for uid in ('carl','donut'):
                if page.locator('#close-modal').count(): page.locator('#close-modal').click()
                state=view()
                if state['mode']!='battle': break
                u=next(u for u in state['battle']['units'] if u['id']==uid)
                if u['hp']<=0: continue
                tile(u['x'],u['y']); enemy=next(e for e in view()['battle']['enemies'] if e['hp']>0)
                if not u['moved']:
                    occupied={(o['x'],o['y']) for o in state['battle']['units']+state['battle']['enemies'] if o['hp']>0}|{(o['x'],o['y']) for o in state['battle']['obstacles']}
                    candidates=[(x,y) for y in range(state['battle']['height']) for x in range(state['battle']['width']) if 0<abs(x-u['x'])+abs(y-u['y'])<=3 and (x,y) not in occupied]
                    for x,y in sorted(candidates,key=lambda xy:abs(xy[0]-enemy['x'])+abs(xy[1]-enemy['y'])):
                        tile(x,y)
                        if next(o for o in view()['battle']['units'] if o['id']==uid)['moved']: break
                for skill in reversed(u['skills']):
                    if page.locator('#close-modal').count(): page.locator('#close-modal').click()
                    button=page.locator('[data-skill="'+skill+'"]')
                    if not button.count() or button.is_disabled(): continue
                    button.click(); target=page.locator('[data-target="'+enemy['id']+'"]')
                    if not target.count(): page.locator('#close-modal').click(); continue
                    target.click(); page.wait_for_timeout(80)
                    if view().get('forecast',{}).get('valid'):
                        page.locator('#confirm-action').click(); page.wait_for_timeout(100); break
                    page.locator('#close-modal').click()
            if view()['mode']=='battle':
                if page.locator('#close-modal').count(): page.locator('#close-modal').click()
                page.locator('[data-command="endTurn"]').click(); page.locator('#end-turn-confirm').click(); page.wait_for_timeout(150)
        assert view()['mode']=='explore' and 'false-guild' in view()['cleared'],'First battle did not clear'
        def interact_object(obj):
            choices=[xy for xy in reachable if abs(xy[0]-obj['x'])+abs(xy[1]-obj['y'])<=1]
            # Standing on the object gives it interaction priority over nearby doors.
            goal=min(choices,key=lambda xy:abs(xy[0]-obj['x'])+abs(xy[1]-obj['y']))
            route(goal); key('e'); page.wait_for_timeout(250)
        interact_object(next(o for o in world['objects'] if o['kind']=='guide'))
        assert view()['questStage']>=2,view()['message']
        interact_object(next(o for o in world['objects'] if o['id']=='goblin-workshop'))
        assert view()['mode']=='battle' and view()['battle']['encounterId']=='goblin-workshop',view()['message']
        assert view()['battle']['width']==11
        battle=view()['battle']; actor=next(u for u in battle['units'] if u['id']==view()['selectedId'])
        old_message=view()['message']; tile(battle['width']-1,0)
        assert view()['message']!=old_message,'Rightmost column click was discarded'
        rightmost_message=view()['message']
        blocked=next(o for o in battle['obstacles'] if (o['x'],o['y']) not in {(u['x'],u['y']) for u in battle['units']+battle['enemies']})
        tile(blocked['x'],blocked['y'])
        now=next(u for u in view()['battle']['units'] if u['id']==actor['id'])
        assert (now['x'],now['y'])==(actor['x'],actor['y']),'Blocked arena cell allowed movement'
        page.screenshot(path=str(a.output/f'seed-{seed}-combat.png'))
        (a.output/f'seed-{seed}-battle.json').write_text(json.dumps(view()['battle'],indent=2)+'\n')
        page.set_viewport_size({'width':390,'height':844}); page.wait_for_timeout(400)
        page.screenshot(path=str(a.output/f'seed-{seed}-mobile-combat.png'))
        assert not errors,errors
        assert not missing,missing
        report['runs'].append({'seed':seed,'room':room,'reachableCells':len(reachable),'solidProps':len(solids),'materialKeyboardCollisions':tile_collisions,'collisionProp':collision[0],'keyboardStepsToEncounter':steps,'actualCombat':True,'battleEncounterId':'goblin-workshop','rightmostColumnMessage':rightmost_message,'blockedArenaMovementMessage':view()['message'],'browserErrors':errors,'missingAssets':missing})
        page.close()
    assert (a.output/'seed-1337-world.json').read_bytes()!=(a.output/'seed-42-world.json').read_bytes()
    cards=''.join(f'<section><h2>Seed {seed}: {label}</h2><div class="pair"><figure><figcaption>REFERENCE · {html.escape(ref.name)}</figcaption><img src="reference.png"></figure><figure><figcaption>ACTUAL PUBLISHED WASM · {label}</figcaption><img src="seed-{seed}-{kind}.png"></figure></div></section>' for seed in (1337,42) for label,kind in [('Generated boss arena · golden exit · camera fitted','boss'),('Generated workshop arena · camera fitted','workshop'),('Combat · actual keyboard encounter','combat')])
    (a.output/'index.html').write_text('<!doctype html><meta charset="utf-8"><title>Reference arena versus actual runtime</title><style>body{margin:0;padding:24px;background:#111923;color:#eee;font:16px system-ui}p{max-width:1100px;line-height:1.5;color:#bfcbd8}.pair{display:grid;grid-template-columns:1fr 1fr;gap:14px}figure{margin:0;background:#080d14}figcaption{padding:12px;font-size:13px}img{width:100%;height:510px;object-fit:contain}section{margin-top:32px}h2{font-size:21px}@media(max-width:650px){.pair{grid-template-columns:1fr}}</style><h1>Reference arena / actual runtime</h1><p>'+html.escape(report['captureDisclosure'])+'</p><p>The reference is a visual target. These comparisons document the current generated geometry, furniture and tactical battle; they do not assert a pixel identical reproduction. Full desktop and mobile captures and runtime JSON are included alongside this page.</p>'+cards)
    server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(SimpleHTTPRequestHandler,directory=str(a.output)))
    threading.Thread(target=server.serve_forever,daemon=True).start(); page=browser.new_page(viewport={'width':1600,'height':1000})
    page.goto(f'http://127.0.0.1:{server.server_port}'); page.screenshot(path=str(a.output/'reference-vs-actual.png'),full_page=True)
    for i,(seed,kind) in enumerate((seed,kind) for seed in (1337,42) for kind in ('boss','workshop','combat')):
        page.locator('section').nth(i).screenshot(path=str(a.output/f'seed-{seed}-{kind}-comparison.png'))
    server.shutdown(); browser.close()
report['sha256']={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in a.output.iterdir() if f.suffix in ('.png','.html')}
(a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS two seeds, solid prop collision, keyboard encounter, actual combat, desktop/mobile, no browser errors or missing assets')
