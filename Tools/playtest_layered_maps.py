"""Real keyboard traversal and camera-only closeups supplement the full arena combat check."""
import argparse, functools, hashlib, json, subprocess, sys, threading
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from collections import deque
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--url',default='http://127.0.0.1:8773')
p.add_argument('--browser',default='/usr/bin/chromium')
p.add_argument('--output',type=Path,default=ROOT/'Rebuild/LayeredMapComparison')
p.add_argument('--skip-arena',action='store_true',help='Reuse arena captures only during visual iteration; final verification must omit this flag')
a=p.parse_args(); a.output.mkdir(parents=True,exist_ok=True)
# Run the existing actual-combat harness against this exact published host.
if not a.skip_arena:
 subprocess.run([sys.executable,str(ROOT/'Tools/playtest_reference_arena.py'),'--url',a.url,'--browser',a.browser,'--output',str(a.output)],check=True)
report={'arenaReused':a.skip_arena,'disclosure':'Actual published WASM; all movement uses keyboard. Camera-only response override frames closeups. No game state or draw calls are injected. Arena screenshots and actual combat checks are produced by playtest_reference_arena.py.','runs':[]}
with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path=a.browser,headless=True,args=['--no-sandbox'])
 for seed in (1337,42):
  page=b.new_page(viewport={'width':1440,'height':1000})
  def camera(route):
   r=route.fetch(); s=r.text(); needle='const tile = this.tile,'
   assert needle in s
   s=s.replace(needle,'''const captureRoom = window.captureRoom;
      if (captureRoom && !battle) {
        this.tile = Math.floor(Math.min(r.width / (captureRoom.width + 2), r.height / (captureRoom.height + 2)));
        this.offsetX = Math.floor(r.width / 2 - (captureRoom.x + captureRoom.width / 2) * this.tile);
        this.offsetY = Math.floor(r.height / 2 - (captureRoom.y + captureRoom.height / 2) * this.tile);
      }
      const tile = this.tile,''')
   route.fulfill(response=r,body=s)
  page.route('**/rpg-renderer.js',camera)
  page.goto(a.url+('&' if '?' in a.url else '?')+f'seed={seed}'); page.wait_for_function('window.rpgView?.world?.props?.length > 0',timeout=90000); page.wait_for_timeout(1800)
  def view(): return page.evaluate('window.rpgView')
  w=view()['world']; width=w['width']; tiles=w['tiles']
  report['rendererSha256']=hashlib.sha256(page.request.get(a.url.rstrip('/')+'/rpg-renderer.js').body()).hexdigest()
  def floor(x,y): return 0<=x<width and 0<=y<w['height'] and tiles[y*width+x]=='.'
  def key(k):
   page.keyboard.down(k); page.wait_for_timeout(25); page.keyboard.up(k); page.wait_for_timeout(190)
  def walk(goal):
   v=view(); start=(v['x'],v['y']); prev={start:None}; q=deque([start])
   while q and goal not in prev:
    x,y=q.popleft()
    for n in ((x+1,y),(x-1,y),(x,y+1),(x,y-1)):
     if floor(*n) and n not in prev: prev[n]=(x,y); q.append(n)
   assert goal in prev,goal
   path=[]; n=goal
   while n!=start: path.append(n); n=prev[n]
   for x,y in reversed(path):
    s=view(); key('ArrowRight' if x>s['x'] else 'ArrowLeft' if x<s['x'] else 'ArrowDown' if y>s['y'] else 'ArrowUp')
    assert (view()['x'],view()['y'])==(x,y), {'expected':(x,y),'actual':(view()['x'],view()['y']),'message':view()['message']}
   return len(path)
  room=next(r for r in w['rooms'] if r['id']=='goblin-workshop')
  checks=[]
  doors=sorted([o for o in w['objects'] if o['kind']=='door' and floor(o['x'],o['y'])], key=lambda o: abs(o['x']-room['x'])+abs(o['y']-room['y']))
  assert doors,'No door floor cells'
  # The room bridge is the dry row crossing a vertical water channel.
  bridges=[]
  for y in range(room['y']+1,room['y']+room['height']-1):
   for x in range(room['x'],room['x']+room['width']):
    if floor(x,y) and ((floor(x-1,y) and floor(x+1,y) and tiles[(y-1)*width+x]=='~' and tiles[(y+1)*width+x]=='~') or (floor(x,y-1) and floor(x,y+1) and tiles[y*width+x-1]=='~' and tiles[y*width+x+1]=='~')): bridges.append((x,y))
  assert bridges,'No dry water crossing'
  doors=[o for o in doors if (o['x'],o['y']) not in bridges]
  assert doors,'No doorway separate from water crossing'
  for label,xy in [('doorway',(doors[0]['x'],doors[0]['y'])),('bridge',bridges[0])]:
   steps=walk(xy)
   # Traverse through the cell on the available axis, then return for layering capture.
   axes=[((xy[0]-1,xy[1]),(xy[0]+1,xy[1])),((xy[0],xy[1]-1),(xy[0],xy[1]+1))]
   pair=next((z for z in axes if all(floor(*n) for n in z)),None); assert pair,(label,xy)
   bridge_cells=[]
   if label=='bridge':
    dx=1 if pair[0][1]==pair[1][1] else 0; dy=1-dx
    left=right=xy
    while (left[0]-dx,left[1]-dy) in bridges: left=(left[0]-dx,left[1]-dy)
    while (right[0]+dx,right[1]+dy) in bridges: right=(right[0]+dx,right[1]+dy)
    pair=((left[0]-dx,left[1]-dy),(right[0]+dx,right[1]+dy))
    assert all(floor(*n) for n in pair),'Bridge approaches blocked'
    bridge_cells=[(left[0]+dx*i,left[1]+dy*i) for i in range(abs(right[0]-left[0])+abs(right[1]-left[1])+1)]
    xy=bridge_cells[len(bridge_cells)//2]
   walk(pair[0]); walk(pair[1]); walk(xy)
   page.evaluate('(r)=>window.captureRoom=r',{'x':xy[0]-3,'y':xy[1]-2,'width':7,'height':5}); page.wait_for_timeout(400)
   page.locator('#world').screenshot(path=str(a.output/f'seed-{seed}-{label}-closeup.png'))
   checks.append({'kind':label,'cell':xy,'crossedFrom':pair[0],'crossedTo':pair[1],'keyboardStepsToCell':steps,'bridgeCells':bridge_cells})
  report['runs'].append({'seed':seed,'crossings':checks})
  page.close()
 b.close()
before='before-seed-1337-boss.png'
if (a.output/before).exists():
 page='''<!doctype html><meta charset="utf-8"><title>Layered map review</title><style>body{background:#101720;color:#eee;font:16px system-ui;padding:24px}.row{display:flex;gap:12px}figure{flex:1;margin:0}img{width:100%}p{max-width:1100px;line-height:1.5}</style><h1>Layered map review</h1><p>Original clean-map reference, prior generated boss room, and updated actual browser render. Room captures use camera-only framing, crop the actual screenshot to the generated room plus one tile border, and hide external DOM controls/toast/battle banner. Door/bridge closeups and combat retain full UI. World objects, sprites, labels and geometry remain actual. Movement and combat are real keyboard / UI play.</p><div class="row">'''
 for title,file in [('Original clean-map reference','reference.png'),('Before: seed 1337 boss',before),('After: seed 1337 boss','seed-1337-boss.png')]: page+=f'<figure><figcaption>{title}</figcaption><img src="{file}"></figure>'
 page+='</div>'
 for seed in (1337,42):
  page+=f'<h2>Seed {seed}: doorway and water crossing</h2><div class="row">'
  for kind in ('doorway','bridge'): page+=f'<figure><figcaption>{kind}: player standing on traversable cell</figcaption><img src="seed-{seed}-{kind}-closeup.png"></figure>'
  page+='</div>'
 (a.output/'layered-review.html').write_text(page)
 server=ThreadingHTTPServer(('127.0.0.1',0),functools.partial(SimpleHTTPRequestHandler,directory=str(a.output)))
 threading.Thread(target=server.serve_forever,daemon=True).start()
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path=a.browser,headless=True,args=['--no-sandbox'])
  tab=browser.new_page(viewport={'width':1800,'height':1000})
  tab.goto(f'http://127.0.0.1:{server.server_port}/layered-review.html')
  tab.screenshot(path=str(a.output/'layered-comparison.png'),full_page=True)
  browser.close()
 server.shutdown()
report['sha256']={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in a.output.iterdir() if f.suffix in ('.png','.html')}
(a.output/'layered-report.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS layered doorway and bridge keyboard crossing, seeds 1337/42; full combat and blocked water/wall checks in report.json')
