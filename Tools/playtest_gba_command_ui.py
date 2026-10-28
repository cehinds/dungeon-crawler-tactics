"""Explicit presentation fixtures: compact action browser, no C# gameplay claims.

Production HTML/CSS/JS are rendered at four viewports. The fixture only replaces
boot state; it never claims practice, Mana, or combat effects were resolved.
"""
import argparse
import functools
import http.server
import json
import shutil
import threading
from pathlib import Path
from playwright.sync_api import sync_playwright
from playtest_gameplay_ui import ROOT, fixture


LAYOUT = """() => {
 const errors=[],box=s=>document.querySelector(s).getBoundingClientRect();
 const visible=r=>r.left>=-1&&r.top>=-1&&r.right<=innerWidth+1&&r.bottom<=innerHeight+1;
 const overlap=(a,b)=>Math.min(a.right,b.right)-Math.max(a.left,b.left)>2&&Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>2;
 for(const s of ['#action-dialog','#action-dialog > .dialog-head','.action-tabs','.action-list-pane','#action-menu-detail','#action-dialog > .modal-actions'])if(!visible(box(s)))errors.push('Outside viewport: '+s);
 const list=box('.action-list-pane'),detail=box('#action-menu-detail'),footer=box('#action-dialog > .modal-actions');
 if(overlap(list,detail))errors.push('List overlaps detail');
 if(overlap(list,footer)||overlap(detail,footer))errors.push('Action content overlaps footer');
 for(const row of document.querySelectorAll('#action-panel-abilities > .action-command-list > button')){
   const rowHeight=row.getBoundingClientRect().height;if(rowHeight>76)errors.push('Command row exceeds 76px compact two-line budget: '+rowHeight);
   if(row.scrollWidth>row.clientWidth+1)errors.push('Command row horizontally overflows');
   for(const cls of ['.action-row-name','.action-row-cost','.action-row-rank']){
     const el=row.querySelector(cls);if(el.scrollWidth>el.clientWidth+1)errors.push('Clipped command field '+cls);
   }
 }
 if(document.documentElement.scrollWidth>innerWidth+1)errors.push('Document horizontal overflow');
 return errors;
}"""


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output',default='/tmp/dct-gba-command-ui')
    args=parser.parse_args();output=Path(args.output);output.mkdir(parents=True,exist_ok=True)
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT/'Web/wwwroot')))
    threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}'
    state=fixture('battle')
    state['abilities'][1]['label']='Extraordinary Explosive Command'
    for index,a in enumerate(state['abilities']):a.update(rank=index+1,maxRank=15,uses=1,nextRankUses=3)
    state['abilities'][1]['description']='A long complete description: choose a safe line of attack, inspect every legal target, then review exact effects before committing this explosive attack. This full explanation belongs in the detail pane.'
    state['items']=[dict(id=f'item.fixture_{i}',label=f'Counted field supply {i+1}',count=2,cost=0,range=0,target='ally',targetIds=['crawler.carl'],description=f'Full supply description {i+1}.') for i in range(18)]
    results=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path=shutil.which('chromium') or shutil.which('google-chrome'),args=['--no-sandbox'])
            for width,height in [(1440,1000),(390,844),(320,740),(844,390)]:
                page=browser.new_page(viewport=dict(width=width,height=height));errors=[]
                page.on('pageerror',lambda e:errors.append(str(e)))
                def route(r):
                    path=r.request.url.split('?',1)[0].split(base,1)[-1].lstrip('/')
                    if path.startswith('_framework/'):r.fulfill(status=200,content_type='application/javascript',body='')
                    elif path=='game.js':
                        boot='content='+ (ROOT/'UnityPackage/Runtime/Data/combat-content.json').read_text()+';gameData='+(ROOT/'UnityPackage/Runtime/Data/game-content.json').read_text()+';view='+json.dumps(state)+''';narrator=createNarrator({getView:()=>view,content});window.gbaResetTargetFixture=()=>{localAction=null;view.canConfirm=false;detailedForecast=false;render();};window.gbaForecastFixture=()=>{actionChooser=false;localAction={abilityId:view.abilities[1].id};view.units.push({...view.units.find(u=>u.id==='enemy.rat'),id:'enemy.second',label:'Second rat',x:7});view.abilities[1].targetIds=['enemy.rat','enemy.second'];previewTargetId='enemy.rat';view.canConfirm=true;view.forecast=[{targetId:'enemy.rat',label:'Dungeon rat',beforeHp:30,afterHp:18,beforeEnergy:12,afterEnergy:12,beforeTags:[],afterTags:[]}];detailedForecast=true;render();};render();window.fixtureReady=true;'''
                        r.fulfill(content_type='application/javascript',body=(ROOT/'Web/wwwroot/game.js').read_text().replace('\nboot();','\n'+boot))
                    else:r.continue_()
                page.route('**/*',route);page.goto(base+'/index.html');page.wait_for_function('window.fixtureReady');page.evaluate('document.fonts.ready')
                page.click('#open-actions');rows=page.locator('#action-panel-abilities > .action-command-list > button');detail=page.locator('#action-menu-detail')
                assert rows.count()==3
                assert rows.locator('progress,p').count()==0,'Repeated description/practice bloats command list'
                rows.nth(0).focus();assert 'Powerful Strike' in detail.inner_text()
                row_before=rows.nth(0).bounding_box()
                rows.nth(0).press('ArrowDown');assert rows.nth(1).evaluate('e=>e===document.activeElement')
                assert state['abilities'][1]['description'] in detail.inner_text()
                row_after=rows.nth(0).bounding_box()
                assert abs(row_after['y']-row_before['y'])<=1 and abs(row_after['x']-row_before['x'])<=1, 'Inspecting a description repositioned command rows'
                rows.nth(1).press('End');assert rows.nth(2).evaluate('e=>e===document.activeElement')
                assert rows.nth(2).get_attribute('aria-disabled')=='true'
                assert 'Requires an open tile' in detail.inner_text()
                rows.nth(2).press('Enter');assert page.locator('#action-dialog').is_visible()
                rows.nth(2).press('Home');assert rows.nth(0).evaluate('e=>e===document.activeElement')
                rows.nth(0).press('ArrowUp');assert rows.nth(2).evaluate('e=>e===document.activeElement')
                page.screenshot(path=str(output/f'pre-hover-{width}x{height}.png'))
                rows.nth(1).hover();assert state['abilities'][1]['description'] in detail.inner_text()
                errors.extend(page.evaluate(LAYOUT));page.screenshot(path=str(output/f'commands-{width}x{height}.png'))
                if width==320:
                    # CI has different system fonts: stress wrapping while retaining
                    # the complete command name in its shared detail panel.
                    font_style=page.add_style_tag(content='body[data-screen] { --ui: monospace; }')
                    rows.nth(1).focus();assert state['abilities'][1]['label'] in detail.inner_text()
                    errors.extend(page.evaluate(LAYOUT))
                    font_style.evaluate('e=>e.remove()')
                rows.nth(0).click();assert not page.locator('#action-dialog').is_visible();assert 'Powerful Strike' in page.locator('.hud-target').inner_text()
                page.evaluate('window.gbaResetTargetFixture()');page.click('#open-actions');page.click('[data-action-tab="items"]')
                pane=page.locator('.action-list-pane');footer=page.locator('#action-dialog > .modal-actions');before=footer.bounding_box()
                pane.evaluate('e=>e.scrollTop=e.scrollHeight');last=page.locator('[data-modal-item="item.fixture_17"]');last.focus()
                assert 'Full supply description 18.' in detail.inner_text()
                after=footer.bounding_box();assert abs(after['y']-before['y'])<=1 and after['y']+after['height']<=height+1
                r=last.bounding_box();b=pane.bounding_box();assert r['y']>=b['y']-1 and r['y']+r['height']<=b['y']+b['height']+1
                page.screenshot(path=str(output/f'items-{width}x{height}.png'))
                page.evaluate('window.gbaForecastFixture()')
                assert page.locator('#forecast-next-target').is_visible() and page.locator('#forecast-prev-target').is_visible()
                nav=page.locator('.forecast-target-nav').bounding_box();footer=page.locator('#forecast-dialog > .modal-actions').bounding_box()
                assert nav['x']>=-1 and nav['x']+nav['width']<=width+1
                assert nav['y']+nav['height']<=footer['y']+1
                assert footer['y']+footer['height']<=height+1
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth+1')
                page.screenshot(path=str(output/f'forecast-{width}x{height}.png'))
                assert page.locator('.game-toast.toast-error').count()==0, 'Fixture unexpectedly invoked a runtime command'
                results.append(dict(viewport=[width,height],errors=errors));page.close()
            browser.close()
    finally:server.shutdown()
    (output/'report.json').write_text(json.dumps(dict(runtime=__doc__,results=results),indent=2))
    failures=[r for r in results if r['errors']];print(json.dumps(dict(output=str(output),failures=failures),indent=2));return bool(failures)

if __name__=='__main__':raise SystemExit(main())
