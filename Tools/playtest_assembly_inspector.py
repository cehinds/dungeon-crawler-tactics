"""Bounded actual published-WASM assembly inspector QA; no runtime state injection."""
import argparse, hashlib, json
from pathlib import Path
from playwright.sync_api import sync_playwright
ROOT = Path(__file__).resolve().parents[1]
p = argparse.ArgumentParser(description=__doc__)
p.add_argument('--url', default='http://127.0.0.1:8778')
p.add_argument('--browser', default='/usr/bin/chromium')
p.add_argument('--output', type=Path, default=ROOT/'Rebuild/AssemblyPassComparison/final')
a=p.parse_args(); a.output.mkdir(parents=True, exist_ok=True)
report={'disclosure':'Actual published WASM initialization and UI events. No geometry, state or graph injection. Port pairs selected from actual exported graph; checks are catalog advice only.', 'runs':[], 'errors':[]}
with sync_playwright() as pw:
 browser=pw.chromium.launch(executable_path=a.browser,headless=True,args=['--no-sandbox'])
 for seed in (1337,42):
  page=browser.new_page(viewport={'width':1440,'height':1000},accept_downloads=True)
  page.on('pageerror',lambda e:report['errors'].append(str(e)))
  page.goto(a.url.rstrip('/')+'/object-inspector.html')
  page.wait_for_function('window.objectInspector?.graph?.nodes.length>0',timeout=90000)
  if seed!=1337:
   page.locator('#seed').select_option(str(seed))
   page.wait_for_function('(s)=>document.querySelector("#status").textContent.includes("seed "+s)',arg=seed,timeout=90000)
  graph=page.evaluate('window.objectInspector.graph'); before=page.evaluate('JSON.stringify(window.objectInspector.world)')
  assemblies=[n for n in graph['nodes'] if n['typeId']=='assembly']; assert assemblies
  assembly=next(n for n in assemblies if n.get('roomId')=='goblin-workshop')
  def choose(node):
   # Searching is a UI affordance and exposes matching descendants without API mutation.
   page.locator('#search').fill(node.get('runtimeId') or node.get('groupId') or node['label'])
   page.locator('#tree').locator('[data-id='+json.dumps(node['id'])+']').click()
  choose(assembly)
  assert page.locator('.assembly-member-selected').count()==len(assembly['memberIds'])
  assert page.locator('.assembly-bounds').count()==1
  page.screenshot(path=str(a.output/f'seed-{seed}-assembly-desktop.png'),full_page=True)
  member=next(n for n in graph['nodes'] if n['id']==assembly['memberIds'][0])
  page.locator('.assembly-members [data-inspect='+json.dumps(member['id'])+']').click()
  assert page.locator('.parent-assembly').get_attribute('data-inspect')==assembly['id']
  page.screenshot(path=str(a.output/f'seed-{seed}-member-properties.png'),full_page=True)
  page.locator('.parent-assembly').click();assert page.locator('.assembly-member-selected').count()==len(assembly['memberIds'])
  assert page.locator('#relations-actual').is_checked() and not page.locator('#relations-suggestions').is_checked()
  page.locator('#relations-suggestions').check();page.locator('#relations-actual').uncheck()
  page.locator('#relations-actual').check();page.locator('#relations-suggestions').uncheck()
  pairs=page.evaluate('''()=>{const g=objectInspector.graph, result={};for(const s of g.nodes.filter(n=>n.runtimeId&&n.ports?.length))for(const t of g.nodes.filter(n=>n.id!==s.id&&n.runtimeId&&n.ports?.length&&n.roomId===s.roomId))for(const sp of s.ports)for(const tp of t.ports){const r=objectInspector.validateConnection(s,t,{sourcePort:sp.id,targetPort:tp.id});const k=r.valid?'valid':'invalid';if(!result[k])result[k]={source:s,target:t,sp:sp.id,tp:tp.id,reasons:r.reasons};if(result.valid&&result.invalid)return result;}return result;}''')
  assert set(pairs)=={'valid','invalid'},pairs
  for kind,pair in pairs.items():
   choose(pair['source']);
   if page.locator('#connection-check details').get_attribute('open') is None: page.locator('#connection-check summary').click()
   page.locator('#source-port').select_option(pair['sp']);page.locator('#target-object').select_option(pair['target']['id']);page.locator('#target-port').select_option(pair['tp'])
   page.locator('#connection-form button[type=submit]').click()
   assert page.locator('#connection-result').get_attribute('class')==('good' if kind=='valid' else 'bad')
   page.screenshot(path=str(a.output/f'seed-{seed}-port-{kind}.png'),full_page=True)
  # Reject a real member moved out of bounds via the visible preview form.
  choose(member);page.locator('#test-x').fill('-1');page.locator('#test-y').fill('-1');page.locator('#test-form button[type=submit]').click()
  assert page.locator('#test-result').get_attribute('class')=='bad'
  page.locator('#suggest').click()
  suggestion=page.locator('#suggestions [data-suggestion]').first
  assert suggestion.count(), 'No valid placement suggestion for workshop member'
  suggestion.click(); assert page.locator('#test-result').get_attribute('class')=='good'
  assert page.evaluate('JSON.stringify(window.objectInspector.world)')==before
  with page.expect_download() as d:page.locator('#export').click()
  target=a.output/f'map-scene-graph-{seed}.json';d.value.save_as(target)
  exported=json.loads(target.read_text()); assert exported==graph
  choose(assembly);page.set_viewport_size({'width':390,'height':844});page.screenshot(path=str(a.output/f'seed-{seed}-assembly-mobile.png'),full_page=True)
  assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), 'Mobile horizontal overflow'
  report['runs'].append({'seed':seed,'assemblies':len(assemblies),'nodes':len(graph['nodes']),'selectedAssembly':assembly['id'],'highlightedMembers':len(assembly['memberIds']),'portChecks':{k:{'source':v['source']['id'],'target':v['target']['id'],'sourcePort':v['sp'],'targetPort':v['tp'],'reasons':v['reasons']} for k,v in pairs.items()},'exportMatchesGraph':True,'worldUnchanged':True})
  if seed==1337:
   report['servedFiles']={}
   for file in ('object-inspector.html','object-inspector.css','object-inspector.js','map-scene-graph.js','data/map-object-rules.json','rpg-renderer.js','game.js','_framework/blazor.boot.json'):
    response=page.request.get(a.url.rstrip('/')+'/'+file);assert response.ok,file
    served=hashlib.sha256(response.body()).hexdigest();source=ROOT/'Web/wwwroot'/file
    report['servedFiles'][file]={'sha256':served,'matchesSource':served==hashlib.sha256(source.read_bytes()).hexdigest() if source.exists() else None}
    if source.exists():assert report['servedFiles'][file]['matchesSource'],file
  page.close()
 browser.close()
assert not report['errors'],report['errors']
report['sha256']={f.name:hashlib.sha256(f.read_bytes()).hexdigest() for f in a.output.iterdir() if f.suffix in ('.json','.png') and f.name!='inspector-report.json'}
(a.output/'inspector-report.json').write_text(json.dumps(report,indent=2)+'\n')
print('PASS actual WASM assembly selection, hierarchy, highlights, valid/invalid ports, invalid placement, exports and immutability; desktop/mobile seeds 1337/42')
