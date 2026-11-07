"""Disclosed checkpoint fixtures: browser Load migrates v1/v2, persists active v3 effects."""
import argparse,json
from pathlib import Path
from playwright.sync_api import sync_playwright
ap=argparse.ArgumentParser(description=__doc__);ap.add_argument('--url',default='http://127.0.0.1:8771');ap.add_argument('--browser',default='/usr/bin/chromium');ap.add_argument('--checkpoint',type=Path,default=Path('Rebuild/Tests/Fixtures/earned-safe-v2.json'));ap.add_argument('--output',type=Path,default=Path('Rebuild/BlockAComparison/final/state'));a=ap.parse_args();a.output.mkdir(parents=True,exist_ok=True)
with sync_playwright() as p:
 b=p.chromium.launch(executable_path=a.browser,args=['--no-sandbox']);page=b.new_page(viewport={'width':1440,'height':1000});errors=[];page.on('pageerror',lambda e:errors.append(str(e)));page.goto(a.url);page.wait_for_function('window.rpgView?.party?.length===2');results=[]
 def panel(n):
  if page.locator('#close-modal').count():page.locator('#close-modal').click()
  page.keyboard.press('Escape');page.locator('[data-open="'+n+'"]').click()
 def load(f):
  page.evaluate('(s)=>localStorage.setItem("dcc.rebuild.v1",s)',json.dumps(f));panel('Save');page.locator('#load-button').click();page.wait_for_timeout(200);assert 'loaded' in page.evaluate('rpgView.message').lower(),page.evaluate('rpgView.message')
 base=json.loads(a.checkpoint.read_text())
 for version in [1,2]:
  fixture=json.loads(json.dumps(base));fixture['version']=version;load(fixture);page.screenshot(path=str(a.output/('version-'+str(version)+'-loaded.png')));results.append({'version':version,'message':page.evaluate('rpgView.message')})
 # Fixture deliberately adds burning; this proves persistence and status UI, not natural acquisition.
 fixture=json.loads(json.dumps(base));fixture['version']=2;fixture['state']['party'][0]['statuses']=[{'id':'burning','sourceId':'carl','stacking':'refresh','duration':2,'strength':2,'tags':[]}];load(fixture)
 assert page.evaluate('rpgView.party[0].statuses[0].id')=='burning';panel('Party');assert 'burning' in page.locator('.status-list').first.inner_text();page.screenshot(path=str(a.output/'fixture-burning-party.png'))
 panel('Save');page.locator('#save-button').click();page.wait_for_function('document.querySelector("#save-result")?.textContent==="Game saved."');saved=json.loads(page.evaluate('localStorage.getItem("dcc.rebuild.v1")'));assert saved['version']==3;assert saved['state']['party'][0]['statuses']==fixture['state']['party'][0]['statuses'];(a.output/'burning-v3-fixture.json').write_text(json.dumps(saved,indent=2));page.locator('#load-button').click();page.wait_for_timeout(200);assert page.evaluate('rpgView.party[0].statuses')==fixture['state']['party'][0]['statuses'];assert not errors,errors
 (a.output/'report.json').write_text(json.dumps({'errors':errors,'migrations':results,'activeEffectRoundtrip':True,'provenance':'Earned baseline v2 safe-room checkpoint. Version-1 migration changes only root version. Burning fixture adds one disclosed status through localStorage and uses Load/Save UI; burning is not claimed naturally acquired.'},indent=2));b.close();print('PASS browser save migration and disclosed effect persistence')
