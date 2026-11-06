"""Fast, reproducible actual-WASM room captures for five sequential visual reviews."""
import argparse, hashlib, html, json, math, shutil, subprocess
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
def sha(path): return hashlib.sha256(path.read_bytes()).hexdigest()
def main():
 p=argparse.ArgumentParser(description=__doc__)
 p.add_argument('--url',default='http://127.0.0.1:8773'); p.add_argument('--browser',default='/usr/bin/chromium')
 p.add_argument('--stage',required=True,choices=['baseline']+[f'pass-{i:02}' for i in range(1,6)])
 p.add_argument('--label',required=True); p.add_argument('--output',type=Path,default=ROOT/'Rebuild/FivePassComparison')
 a=p.parse_args(); out=a.output/a.stage
 if (out/'capture.json').exists(): raise SystemExit('Stage already captured; preserve reviewed evidence: '+str(out))
 out.mkdir(parents=True,exist_ok=True)
 ref=ROOT/'Web/wwwroot/assets/reference-layers/clean-map.png'
 shutil.copyfile(ref,a.output/'reference.png')
 report={'stage':a.stage,'label':a.label,'seed':1337,'viewport':{'width':1440,'height':1000},'rendererAnimationTimestampMs':1000,'disclosure':'Actual published WASM state. Browser response override changes room camera framing and renderer frame timestamp only (1000 ms). External controls/toast/battle banner hidden for environment crop. No state, geometry, assets, or draw calls injected. Initial player state retained for equal comparisons.','sourceReferenceSha256':sha(ref),'sourceRendererSha256':sha(ROOT/'Web/wwwroot/rpg-renderer.js'),'manifestSha256':sha(ROOT/'Tools/hosted-assets.json'),'gitRevision':subprocess.check_output(['git','rev-parse','HEAD'],cwd=ROOT,text=True).strip(),'publishedFiles':{},'rooms':{},'errors':[]}
 with sync_playwright() as pw:
  browser=pw.chromium.launch(executable_path=a.browser,headless=True,args=['--no-sandbox'])
  page=browser.new_page(viewport=report['viewport'])
  page.on('pageerror',lambda e:report['errors'].append(str(e)))
  def camera(route):
   r=route.fetch(); s=r.text(); needle='const tile = this.tile,'
   assert needle in s,'Camera anchor changed'
   s=s.replace(needle,'''const captureRoom = window.captureRoom;
      if (captureRoom && !battle) {
        this.tile = Math.floor(Math.min(r.width / (captureRoom.width + 2), r.height / (captureRoom.height + 2)));
        this.offsetX = Math.floor(r.width / 2 - (captureRoom.x + captureRoom.width / 2) * this.tile);
        this.offsetY = Math.floor(r.height / 2 - (captureRoom.y + captureRoom.height / 2) * this.tile);
      }
      const tile = this.tile,''')
   assert 'this.frame(t)' in s
   s=s.replace('this.frame(t)','this.frame(1000)')
   route.fulfill(response=r,body=s)
  page.route('**/rpg-renderer.js',camera)
  for file in ('rpg-renderer.js','game.js','data/concept-room-rules.json','_framework/blazor.boot.json'):
   r=page.request.get(a.url.rstrip('/')+'/'+file); assert r.ok,file
   report['publishedFiles'][file]=hashlib.sha256(r.body()).hexdigest()
  report['servedRendererMatchesSource']=report['publishedFiles']['rpg-renderer.js']==report['sourceRendererSha256']
  assert a.stage=='baseline' or report['servedRendererMatchesSource'],'Published renderer is stale; sync source before labeling a pass'
  page.goto(a.url.rstrip('/')+'/?seed=1337')
  page.wait_for_function('window.rpgView?.world?.props?.length > 0',timeout=90000)
  page.wait_for_timeout(1800)
  state=page.evaluate('window.rpgView'); assert state['seed']==1337
  (out/'world.json').write_text(json.dumps(state['world'],indent=2)+'\n')
  page.add_style_tag(content='#controls,#toast,#battle-banner{visibility:hidden!important}')
  for name,rid in [('boss','ball-of-swine-complex'),('workshop','goblin-workshop')]:
   room=next(r for r in state['world']['rooms'] if r['id']==rid)
   page.evaluate('(r)=>window.captureRoom=r',room); page.wait_for_timeout(350)
   box=page.locator('#world').bounding_box(); tile=math.floor(min(box['width']/(room['width']+2),box['height']/(room['height']+2)))
   cw,ch=(room['width']+2)*tile,(room['height']+2)*tile
   clip={'x':box['x']+(box['width']-cw)/2,'y':box['y']+(box['height']-ch)/2,'width':cw,'height':ch}
   page.screenshot(path=str(out/f'seed-1337-{name}.png'),clip=clip)
   report['rooms'][name]={'room':room,'tilePixels':tile,'clip':clip}
  browser.close()
 assert not report['errors'],report['errors']
 report['screenshots']={f.name:sha(f) for f in out.glob('*.png')}
 (out/'capture.json').write_text(json.dumps(report,indent=2)+'\n')
 stages=[x for x in ['baseline']+[f'pass-{i:02}' for i in range(1,6)] if (a.output/x/'capture.json').exists()]
 markup='<!doctype html><meta charset="utf-8"><title>Five visual passes</title><style>body{background:#121820;color:#eee;font:16px system-ui;margin:24px}section{display:flex;gap:12px}figure{margin:0;flex:1;min-width:0}img{width:100%}p{max-width:1150px;line-height:1.5}</style><h1>Five visual passes: actual WASM</h1><p>'+html.escape(report['disclosure'])+'</p>'
 for stage in stages:
  info=json.loads((a.output/stage/'capture.json').read_text())
  markup+='<h2>'+html.escape(stage+': '+info['label'])+'</h2><section>'
  for title,file in [('Clean source reference','reference.png'),('Seed 1337 boss',stage+'/seed-1337-boss.png'),('Seed 1337 workshop',stage+'/seed-1337-workshop.png')]:markup+=f'<figure><figcaption>{title}</figcaption><img src="{file}"></figure>'
  markup+='</section>'
 (a.output/'index.html').write_text(markup)
 print(json.dumps({'stage':a.stage,'output':str(out),'hashes':report['screenshots']}))
if __name__=='__main__':main()
