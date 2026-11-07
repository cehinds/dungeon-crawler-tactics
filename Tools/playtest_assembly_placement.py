"""Published-WASM group preview QA using actual graph observations and UI events."""
import argparse, hashlib, json
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT=Path(__file__).resolve().parents[1]
p=argparse.ArgumentParser(description=__doc__)
p.add_argument('--url',default='http://127.0.0.1:8778');p.add_argument('--browser',default='/usr/bin/chromium');p.add_argument('--output',type=Path,default=ROOT/'Rebuild/AssemblyPlacementComparison/final')
a=p.parse_args();a.output.mkdir(parents=True,exist_ok=True)
report={'disclosure':'Actual published WASM world, unmodified exported graph, bounded read-only proposal searches and actual UI events. No runtime geometry or game state injected.','runs':[],'errors':[]}
with sync_playwright() as pw:
 b=pw.chromium.launch(executable_path=a.browser,headless=True,args=['--no-sandbox'])
 for seed in (1337,42):
  page=b.new_page(viewport={'width':1440,'height':1000},accept_downloads=True);page.on('pageerror',lambda e:report['errors'].append(str(e)))
  page.goto(a.url+'/object-inspector.html');page.wait_for_function('window.objectInspector?.graph?.nodes.length>0',timeout=90000)
  page.locator('#seed').select_option(str(seed));page.wait_for_function('(s)=>document.querySelector("#status").textContent.includes("seed "+s)',arg=seed,timeout=90000)
  before=page.evaluate('JSON.stringify(objectInspector.world)');graph=page.evaluate('objectInspector.graph')
  cases=page.evaluate('''async()=>{const catalog=await(await fetch('data/map-object-rules.json')).json(),g=objectInspector.graph,map=objectInspector.world,out={};for(const assembly of g.nodes.filter(n=>n.typeId==='assembly'&&n.memberIds.length>1)){const context={map,catalog,nodes:g.nodes};for(let dy=-4;dy<=4;dy++)for(let dx=-4;dx<=4;dx++){if(!dx&&!dy)continue;const target={x:assembly.x+dx,y:assembly.y+dy},r=objectInspector.previewAssemblyPlacement(assembly,target,context),kind=r.valid?'valid':r.reasons.some(q=>q.code==='overlap')?'overlap':null;if(kind&&!out[kind])out[kind]={assembly,target,result:r};}if(out.valid&&out.overlap)break;}return out;}''')
  assert 'valid' in cases, 'No valid nonzero multi-member proposal found in actual world'
  assert 'overlap' in cases, 'No actual overlap rejection found'
  def choose(node):
   page.locator('#search').fill(node.get('groupId') or node['label']);page.locator('[data-id='+json.dumps(node['id'])+']').click()
  def submit(x,y):
   page.locator('#assembly-x').fill(str(x));page.locator('#assembly-y').fill(str(y));page.locator('[data-testid=preview-group]').click()
  def shot(label):page.screenshot(path=str(a.output/f'seed-{seed}-{label}.png'),full_page=True)
  run={'seed':seed,'cases':{}}
  for kind,c in cases.items():
   n=c['assembly'];choose(n);ox=int(page.locator('#assembly-x').input_value());oy=int(page.locator('#assembly-y').input_value())
   submit(ox+c['target']['x']-n['x'],oy+c['target']['y']-n['y'])
   assert page.locator('[data-preview-valid]').get_attribute('data-preview-valid')==str(kind=='valid').lower()
   assert page.locator('.preview-member').count()==len(n['memberIds'])
   shot(kind+'-desktop');run['cases'][kind]={'assembly':n['id'],'target':c['target'],'reasons':c['result']['reasons'],'members':len(c['result']['members'])}
  c=cases['valid'];n=c['assembly'];choose(n);ox=int(page.locator('#assembly-x').input_value());oy=int(page.locator('#assembly-y').input_value());submit(ox,oy)
  assert 'Translation 0, 0 tiles' in page.locator('#assembly-preview-result').inner_text();run['noOpValid']=page.locator('[data-preview-valid]').get_attribute('data-preview-valid');assert run['noOpValid']=='true'
  page.locator('[data-nudge="1,0"]').click();assert int(page.locator('#assembly-x').input_value())==ox+1
  page.locator('#assembly-reset').click();assert page.locator('.assembly-preview-overlay').count()==0 and int(page.locator('#assembly-x').input_value())==ox
  submit(-5,-5);assert page.locator('[data-preview-valid]').get_attribute('data-preview-valid')=='false';shot('bounds-desktop')
  submit(ox+c['target']['x']-n['x'],oy+c['target']['y']-n['y']);page.set_viewport_size({'width':390,'height':844});shot('valid-mobile');assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
  underlay=page.evaluate('''async()=>{const catalog=await(await fetch('data/map-object-rules.json')).json(),g=objectInspector.graph,map=objectInspector.world;const n=g.nodes.find(n=>n.typeId==='assembly'&&n.memberIds.length>1&&map.props.some(p=>p.roomId===n.roomId&&p.groupId===n.groupId&&p.layer==='underlay'));if(!n)return null;return {assembly:n,result:objectInspector.previewAssemblyPlacement(n,{x:n.x,y:n.y},{map,catalog,nodes:g.nodes}),props:map.props.filter(p=>p.roomId===n.roomId&&p.groupId===n.groupId)};}''')
  assert underlay, 'No authored multi-member underlay group'
  choose(underlay['assembly']);ux=int(page.locator('#assembly-x').input_value());uy=int(page.locator('#assembly-y').input_value());submit(ux,uy)
  assert page.locator('[data-preview-valid]').get_attribute('data-preview-valid')=='true'
  for member in underlay['result']['members']:
   original=next(p for p in underlay['props'] if p['id']==member['candidate']['id'])
   assert (member['x'],member['y'],member['candidate'].get('rotation'))==(original['x'],original['y'],original.get('rotation'))
  shot('authored-underlay-mobile');run['authoredUnderlay']={'assembly':underlay['assembly']['id'],'noOpValid':True,'relativeOffsetsAndRotationsPreserved':True}
  submit(9007199254740992,0);assert page.locator('[data-preview-valid]').get_attribute('data-preview-valid')=='false'
  assert page.evaluate('JSON.stringify(objectInspector.world)')==before
  with page.expect_download() as d:page.locator('#export').click()
  path=a.output/f'graph-{seed}.json';d.value.save_as(path);assert json.loads(path.read_text())==graph
  if seed==1337:
   report['servedFiles']={}
   for file in ('object-inspector.html','object-inspector.css','object-inspector.js','map-scene-graph.js','data/map-object-rules.json','rpg-renderer.js','game.js'):
    response=page.request.get(a.url+'/'+file);assert response.ok
    served=hashlib.sha256(response.body()).hexdigest();source=hashlib.sha256((ROOT/'Web/wwwroot'/file).read_bytes()).hexdigest();assert served==source,file
    report['servedFiles'][file]=served
  run.update(worldUnchanged=True,exportUnchanged=True,nudgeAndReset=True,mobileNoOverflow=True);report['runs'].append(run);page.close()
 b.close()
assert not report['errors'],report['errors']
report['sha256']={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in a.output.iterdir() if f.suffix in ('.png','.json') and f.name!='report.json'}
(a.output/'report.json').write_text(json.dumps(report,indent=2)+'\n');print('PASS published actual assembly placement UI seeds 1337/42; valid, invalid, no-op, nudge/reset, immutable world/export and mobile')
