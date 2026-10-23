"""Visible boss victory/retry/defeat/return regression with bounded battle fixtures.
The fixture makes the boss vulnerable to one real confirmed strike, then supplies
an explicit defeated checkpoint to inspect the defeat-screen return control.
"""
import json
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
 browser=p.chromium.launch(executable_path='/usr/bin/chromium',headless=True,args=['--no-sandbox'])
 page=browser.new_page(viewport={'width':390,'height':844});errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
 page.goto('http://127.0.0.1:5188/?outcome-qa=1');page.wait_for_function('window.dungeon')
 page.locator('#open-scenarios').click();page.locator('[data-scenario-briefing="scenario.hoarder"]').click();page.locator('#start-scenario').click();page.wait_for_function("window.dungeon.getView().screen==='battle'")
 fixture=json.loads(page.evaluate('window.dungeon.getSave()'))
 boss=next(u for u in fixture['units'] if u['id']=='boss.hoarder');boss.update(hp=1,x=2,y=3)
 page.evaluate('(s)=>window.dungeon.loadSave(JSON.stringify(s))',fixture)
 page.evaluate("window.dungeon.command('preview',{unitId:'crawler.carl',targetId:'boss.hoarder',abilityId:'ability.carl_powerful_strike'})")
 page.locator('#detail-confirm-forecast').click();page.wait_for_function("window.dungeon.getView().screen==='victory'")
 page.wait_for_selector('#return-scenario');page.screenshot(path='/tmp/dct-boss-victory-phone.png')
 assert 'Return to campaign' in page.locator('#game').inner_text()
 page.locator('#retry-button').click();page.wait_for_function("window.dungeon.getView().screen==='battle'")
 fixture=json.loads(page.evaluate('window.dungeon.getSave()'));fixture['screen']='defeat'
 for u in fixture['units']:
  if u['team']=='player':u['hp']=0
 page.evaluate('(s)=>window.dungeon.loadSave(JSON.stringify(s))',fixture)
 page.wait_for_selector('#return-scenario');page.screenshot(path='/tmp/dct-boss-defeat-phone.png')
 page.locator('#return-scenario').click();page.wait_for_function("window.dungeon.getView().screen==='camp' && !window.dungeon.getView().scenario")
 assert not errors,errors
 print('PASS visible boss victory/retry/defeat/return controls; no browser errors.')
 browser.close()
