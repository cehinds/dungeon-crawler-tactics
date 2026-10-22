"""Optional browser UI regression: camp, exploration, class actions, viewport and focus.

Requires Playwright and a running published game. Uses ordinary UI inputs, never
edits saved state. Each viewport gets a new browser context with a fresh save.
"""
import argparse
from pathlib import Path
import tempfile
parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--url',default='http://localhost:8000')
parser.add_argument('--browser',default='/usr/bin/chromium')
args=parser.parse_args()
import json
from playwright.sync_api import sync_playwright
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=args.browser,headless=True,args=['--no-sandbox'])
    for w,h in [(1366,768),(390,844),(360,640),(844,390)]:
        page=browser.new_page(viewport={'width':w,'height':h}); errors=[]
        page.on('pageerror',lambda e: errors.append(str(e)))
        page.goto(args.url,wait_until='networkidle')
        page.wait_for_function('window.dungeon && window.dungeon.getView()',timeout=60000)
        page.locator('#begin-button').click()
        if page.locator('#help-dialog').evaluate('(el)=>el.open'):page.locator('#help-dialog [data-close]').last.click()
        page.locator('#class-select').select_option('class.guardian')
        page.wait_for_function('window.dungeon.getView().roster.find(r=>r.id==="crawler.carl").classId==="class.guardian"')
        assert '6 damage' in page.locator('.class-abilities').inner_text()
        page.wait_for_function('document.querySelector(".toast-success")?.textContent.includes("Guardian")')
        page.locator('.toast-dismiss').click()
        # Export feedback must stay visible above the native dialog's backdrop.
        page.locator('#save-button').click()
        with page.expect_download():
            page.locator('#export-button').click()
        page.wait_for_function('document.querySelector("#save-dialog .toast-success")?.textContent.includes("exported")')
        page.locator('.toast-dismiss').click()
        page.keyboard.press('Escape')
        assert page.evaluate('document.activeElement.id === "save-button"')
        if w<500:
            assert page.evaluate('document.documentElement.scrollHeight <= innerHeight'), 'Camp page scroll'
        page.locator('#enter-battle').click()
        page.wait_for_function('window.dungeon.getView().screen==="explore"')
        page.keyboard.press('ArrowRight')
        page.wait_for_function('window.dungeon.getView().exploration.x===2')
        # Actual UI commands reveal the map; no state editing or hidden point lookup.
        for step in range(100):
            v=page.evaluate('window.dungeon.getView()'); m=v['exploration']
            door=next((n for n in m['points'] if n['kind']=='encounter' and n['canInteract']),None)
            if door:
                page.locator('[data-explore-interact="'+door['id']+'"]').click(); break
            frontier=[t for t in m['tiles'] if t['reachable'] and not t['revealed']]
            if frontier:t=sorted(frontier,key=lambda t:(t['y'],t['x']))[0]
            else:
                door=next(n for n in m['points'] if n['kind']=='encounter')
                t=min([t for t in m['tiles'] if t['reachable']],key=lambda t:abs(t['x']-door['x'])+abs(t['y']-door['y']))
            page.locator('[data-explore-cell="'+str(t['x'])+','+str(t['y'])+'"]').click()
            page.wait_for_function('([x,y])=>window.dungeon.getView().exploration.x===x&&window.dungeon.getView().exploration.y===y',arg=[t['x'],t['y']])
        page.wait_for_function('window.dungeon.getView().screen==="battle"')
        assert page.evaluate('document.documentElement.scrollHeight <= innerHeight'), 'Battle page scroll'
        if w<500:
            chips=page.locator('.party-chip').evaluate_all('(els)=>els.map(e=>{let r=e.getBoundingClientRect();return r.left>=0&&r.right<=innerWidth})')
            assert all(chips) and len(chips)==4
        before_preview=page.evaluate('window.dungeon.getSave()')
        page.locator('[data-ability="ability.bulwark"]').click()
        page.wait_for_function('window.dungeon.getView().canConfirm')
        assert page.locator('#forecast-dialog').evaluate('(el)=>el.open')
        page.keyboard.press('Escape')
        page.wait_for_function('!window.dungeon.getView().canConfirm')
        assert page.evaluate('window.dungeon.getSave()') == before_preview, 'Cancel spent resources'
        assert page.evaluate('document.activeElement.dataset.ability === "ability.bulwark"')
        page.locator('[data-ability="ability.bulwark"]').click()
        page.wait_for_function('window.dungeon.getView().canConfirm')
        confirm=page.locator('#confirm-forecast'); box=confirm.bounding_box()
        assert box['y']>=0 and box['y']+box['height']<=h
        assert page.evaluate('document.documentElement.scrollHeight <= innerHeight')
        page.screenshot(path=str(Path(tempfile.gettempdir()) / f'dungeon-final-{w}.png'))
        confirm.click()
        page.wait_for_function('window.dungeon.getView().units.find(u=>u.id==="crawler.carl").tags.includes("status.guarded")')
        page.wait_for_function('document.querySelector(".toast-success")?.textContent.includes("Action confirmed")')
        assert page.locator('#forecast-dialog').count() == 0
        page.locator('.toast-dismiss').click()
        page.locator('[data-unit="crawler.donut"]').click()
        page.locator('[data-drawer="items"]').click()
        assert page.locator('#game-drawer-dialog').evaluate('(el)=>el.open')
        page.keyboard.press('Escape')
        assert page.evaluate('document.activeElement.dataset.drawer === "items"')
        assert not errors, errors
        print(json.dumps({'viewport':[w,h],'camp':'class changed','exploration':'keyboard+clicked traversal','battle':'cancel preserves save; confirm applies Guarded','feedback':'class, export inside dialog, confirm; dismiss and focus','pageScroll':False,'pageErrors':errors}))
        page.close()
    browser.close()
