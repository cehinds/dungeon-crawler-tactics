"""Production presentation fixtures for ability rank UI; does not execute C# rules."""
import functools
import http.server
import json
from pathlib import Path
import shutil
import threading
from playwright.sync_api import sync_playwright
from playtest_gameplay_ui import ROOT, fixture


def main():
    handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT/'Web/wwwroot'))
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{server.server_port}'
    content = json.loads((ROOT/'UnityPackage/Runtime/Data/combat-content.json').read_text())
    game = json.loads((ROOT/'UnityPackage/Runtime/Data/game-content.json').read_text())
    state = fixture('battle')
    state['roster'][0]['innateAbilityIds'] = [a['id'] for a in state['abilities']]
    practice = []
    for index, action in enumerate(state['abilities']):
        rank, cap, uses, next_uses = [(1, 15, 0, 3), (15, 15, 120, 0), (20, 20, 240, 0)][index]
        action.update(rank=rank, maxRank=cap, uses=uses, nextRankUses=next_uses)
        rows = [dict(rank=n, requiredUses=(n-1)*3, cost=2, range=n,
                     effectSummary=f'Effective utility at rank {n}: move {n} tiles; protection lasts {n} rounds.',
                     milestones=['Source-inspired tactical milestone'] if n==10 else []) for n in range(1, 21)]
        practice.append(dict(unitId='crawler.carl', abilityId=action['id'], rank=rank,
                             maxRank=cap, uses=uses, nextRankUses=next_uses, atCap=rank==cap,
                             description=f'CURRENT CORE EFFECT rank {rank}', canonNotes='Verified book effect anchor; numeric progression unknown.', sourceUrls=['https://example.com/book','javascript:alert(1)'], cost=2, range=rank, ranks=rows))
    state['development'] = dict(practice=practice, rankCatalog=[], crawlers=[], stats=[])
    errors=[]
    try:
        with sync_playwright() as playwright:
            browser=playwright.chromium.launch(executable_path=shutil.which('chromium') or shutil.which('google-chrome'), args=['--no-sandbox'])
            for width,height in [(1440,1000),(390,844),(320,740),(844,390)]:
                page=browser.new_page(viewport=dict(width=width,height=height))
                page.on('pageerror',lambda error: (errors.append(str(error)),print('PAGE ERROR',error,flush=True)))
                page.set_default_timeout(10000)
                def route(request):
                    path=request.request.url.split('?',1)[0].split(base,1)[-1].lstrip('/')
                    if path.startswith('_framework/'):
                        request.fulfill(status=200,content_type='application/javascript',body='')
                    elif path=='game.js':
                        source=(ROOT/'Web/wwwroot/game.js').read_text()
                        boot='content='+json.dumps(content)+';gameData='+json.dumps(game)+';view='+json.dumps(state)+''';
                        narrator=createNarrator({getView:()=>view,content});
                        window.rankFixture=()=>{characterSheetId='crawler.carl';sheetActiveSection='sheet-skills';render();};
                        window.rankEvent=(before,after,preview=false)=>{const result={...view,events:[{type:'skill_practice',actorId:'crawler.carl',abilityId:view.abilities[0].id,amount:3,before,after,preview}]};narrator.begin({},view,result);narrator.finish();};
                        render();window.fixtureReady=true;
                        '''
                        request.fulfill(content_type='application/javascript',body=source.replace('\nboot();','\n'+boot))
                    elif path in ('data/game-content.json','data/combat-content.json'):
                        request.fulfill(path=str(ROOT/'UnityPackage/Runtime/Data'/Path(path).name))
                    elif (ROOT/'Web/wwwroot'/path).is_file():
                        request.fulfill(path=str(ROOT/'Web/wwwroot'/path))
                    else:
                        request.continue_()
                page.route('**/*',route)
                page.goto(base+'/index.html')
                page.wait_for_function('window.fixtureReady===true')
                page.click('#open-actions')
                cards=page.locator('[data-modal-ability]')
                assert 'Rank 1/15' in cards.nth(0).inner_text()
                assert '3 uses to rank 2' in cards.nth(0).inner_text()
                assert cards.nth(0).locator('progress').count()==1
                assert 'Training cap reached' in cards.nth(1).inner_text()
                assert 'Rank 20/20' in cards.nth(2).inner_text()
                page.click('#close-actions')
                page.evaluate('window.rankFixture()')
                page.click('[data-sheet-section="sheet-skills"]')
                first=page.locator('#sheet-skills .skill-row').first
                assert 'CURRENT CORE EFFECT rank 1' in first.inner_text()
                assert first.locator('details[open]').count()==0
                first.locator('summary').click()
                rows=first.locator('.ability-rank-row')
                assert rows.count()==20
                assert 'Book anchor:' in first.inner_text()
                assert first.locator('a[href^="javascript:"]').count()==0
                assert rows.filter(has_text='Locked by rank permission').count()==5
                assert 'move 20 tiles' in rows.last.inner_text()
                first.locator('.ability-rank-row').last.scroll_into_view_if_needed()
                assert page.locator('#done-character-sheet').is_visible()
                assert page.locator('.sheet-navigation').is_visible()
                assert page.locator('#sheet-skills').evaluate('e=>e.scrollHeight>e.clientHeight')
                for selector in ['#done-character-sheet','.sheet-navigation','.character-sheet-dialog .dialog-head']:
                    box=page.locator(selector).bounding_box()
                    assert box['y']>=0 and box['y']+box['height']<=height+1,(selector,box)
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth'), 'Horizontal overflow'
                page.click('#done-character-sheet')
                # Preview and unchanged ranks must never announce a rank achievement.
                page.evaluate('window.rankEvent(1,2,true)')
                assert 'SKILL RANK UP' not in page.locator('#narrator-line').inner_text()
                page.evaluate('window.rankEvent(1,1)')
                assert 'SKILL RANK UP' not in page.locator('#narrator-line').inner_text()
                page.evaluate('window.rankEvent(1,2)')
                page.click('#narrator-history')
                assert 'SKILL RANK UP' in page.locator('.narrator-history-list').inner_text()
                page.close()
            browser.close()
        assert not errors,errors
        print('PASS: rank1/15/20 action cards, effective sheet effects, battle20rank inspector, locked16–20, responsive controls, attained-only narration (4 viewports).')
    finally:
        server.shutdown()

if __name__=='__main__':
    main()
