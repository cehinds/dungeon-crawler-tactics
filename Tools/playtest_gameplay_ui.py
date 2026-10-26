"""Presentation-only QA using explicit fixture state and the production HTML/JS/CSS.

This does NOT validate C# rules, WASM startup, saves, or generated adventures.
Run: python3 Tools/playtest_gameplay_ui.py --output /tmp/dct-gameplay-ui
Requires Python Playwright, Chromium, and hydrated native assets.
A temporary local HTTP server is started unless --url is supplied.
"""
import argparse
import functools
import http.server
import json
from pathlib import Path
import shutil
import threading
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def fixture(screen):
    names = [('carl', 'Carl', 'brawler'), ('donut', 'Princess Donut', 'mage'),
             ('katia', 'Katia', 'guardian'), ('mongo', 'Mongo', 'pet')]
    units = [dict(id='crawler.'+name, label=label, classId='class.'+klass,
                  team='player', selected=i == 0, x=2+i, y=3, hp=30-i*3,
                  maxHp=40, energy=12, maxEnergy=16, move=5, effectiveMove=5,
                  tags=[], statuses=[], selectedClassId='class.'+klass,
                  moved=False, acted=False, finished=False)
             for i, (name, label, klass) in enumerate(names)]
    tiles = [dict(id=f'tile.{x}.{y}', x=x, y=y, blocked=x in (0, 11) or y in (0, 9),
                  tags=[], reachable=0<x<11 and 0<y<9, revealed=True)
             for y in range(10) for x in range(12)]
    abilities = [dict(id='ability.carl_powerful_strike', label='Powerful Strike',
                      description='Strike an adjacent enemy and knock it back one tile.',
                      target='enemy', cost=3, range=1, targetIds=['enemy.rat'], enabled=True),
                 dict(id='ability.carl_dynamite', label='Dynamite',
                      description='Throw dynamite at an enemy and ignite its tile.',
                      target='enemy', cost=5, range=4, targetIds=['enemy.rat'], enabled=True),
                 dict(id='ability.carl_tripwire', label='Rig Tripwire',
                      description='Set a trap on an empty tile.', target='tile', cost=2,
                      range=3, targetIds=['tile.3.4'], enabled=True)]
    enemy = dict(units[0], id='enemy.rat', label='Dungeon rat', team='enemy',
                 selected=False, x=6, y=4, classId='class.enemy')
    return dict(screen=screen, encounterIndex=0, encounterName='Lantern Vault',
                objective='Clear the Lantern Vault', phase='player', round=1,
                selectedUnitId=units[0]['id'], units=units+[enemy], roster=[dict(u, selected=True) for u in units],
                classes=[dict(id='class.'+c, label=c.title()) for _, _, c in names],
                tiles=tiles, width=12, height=10, reachable=tiles,
                forecast=[], abilities=abilities, items=[], equipment=[], log=[],
                events=[], quests=[], canMove=True, canAct=True, canConfirm=False,
                partyOrder=[u['id'] for u in units], message='Move or act in either order. End each crawler’s turn when ready.',
                customMap=None, generatedDungeon=dict(cleared=False) if screen=='explore' else None,
                exploration=dict(id='layout-fixture', label='Lantern Vault', width=12, height=10,
                                 x=2, y=3, tiles=tiles, points=[]))


MEASURE = """({selectors, touch}) => {
 const errors=[], boxes={};
 for(const selector of selectors){
   const e=document.querySelector(selector);
   if(!e || !e.getClientRects().length){errors.push('Missing '+selector);continue;}
   const r=e.getBoundingClientRect(); boxes[selector]={x:r.x,y:r.y,width:r.width,height:r.height,font:getComputedStyle(e).fontFamily,fontSize:getComputedStyle(e).fontSize};
   if(r.left < -1 || r.right > innerWidth+1) errors.push('Outside horizontal viewport: '+selector);
   if(r.top < -1 || r.bottom > innerHeight+1) errors.push('Outside vertical viewport: '+selector);
   if(e.matches('button') && touch && (r.width<40 || r.height<40)) errors.push('Small touch control: '+selector+' '+r.width+'x'+r.height);
   if(e.matches('button') && parseFloat(getComputedStyle(e).fontSize)<12) errors.push('Unreadable text: '+selector);
 }
 const controls=selectors.filter(s=>document.querySelector(s)?.matches('button'));
 const panels=['.hud-crawler','.hud-actions','.hud-target','.world-controls','.battle-guidance','.party-strip'];
 const overlap=(a,b)=>Math.min(a.x+a.width,b.x+b.width)-Math.max(a.x,b.x)>2 && Math.min(a.y+a.height,b.y+b.height)-Math.max(a.y,b.y)>2;
 for(let i=0;i<panels.length;i++)for(let j=i+1;j<panels.length;j++){const a=boxes[panels[i]],b=boxes[panels[j]];if(a&&b&&overlap(a,b))errors.push('Overlapping HUD panels: '+panels[i]+' / '+panels[j]);}
 for(let i=0;i<controls.length;i++)for(let j=i+1;j<controls.length;j++){
   const a=boxes[controls[i]],b=boxes[controls[j]];if(!a||!b)continue;
   if(Math.min(a.x+a.width,b.x+b.width)-Math.max(a.x,b.x)>2 && Math.min(a.y+a.height,b.y+b.height)-Math.max(a.y,b.y)>2)
      errors.push('Overlapping controls: '+controls[i]+' / '+controls[j]);
 }
 if(document.documentElement.scrollWidth>innerWidth+1)errors.push('Document overflows horizontally');
 return {errors,boxes,documentHeight:document.documentElement.scrollHeight};
}"""


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', help='Optional existing server; source files are overlaid by routing')
    parser.add_argument('--browser', default=shutil.which('chromium') or shutil.which('google-chrome'))
    parser.add_argument('--output', default='/tmp/dct-gameplay-ui')
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    server = None
    if not args.url:
        handler = functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT/'Web/wwwroot'))
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        args.url = f'http://127.0.0.1:{server.server_port}'
    results = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=args.browser, args=['--no-sandbox'])
            for width, height in [(1440, 1000), (390, 844), (844, 390)]:
                for screen in ['battle', 'explore']:
                    page = browser.new_page(viewport=dict(width=width, height=height))
                    errors = []
                    page.on('pageerror', lambda error: errors.append(str(error)))
                    page.on('console', lambda message: errors.append(message.text) if message.type == 'error' else None)
                    def route(request):
                        path = request.request.url.split('?', 1)[0].split(args.url.rstrip('/'), 1)[-1].lstrip('/')
                        if path.startswith('_framework/'):
                            request.fulfill(status=200, content_type='application/javascript', body='')
                        elif path in ('data/game-content.json', 'data/combat-content.json'):
                            request.fulfill(path=str(ROOT/'UnityPackage/Runtime/Data'/Path(path).name))
                        elif path == 'game.js':
                            source = (ROOT/'Web/wwwroot/game.js').read_text()
                            content = json.loads((ROOT/'UnityPackage/Runtime/Data/combat-content.json').read_text())
                            game = json.loads((ROOT/'UnityPackage/Runtime/Data/game-content.json').read_text())
                            boot = 'content='+json.dumps(content)+';gameData='+json.dumps(game)+';view='+json.dumps(fixture(screen))+';render();document.querySelector("#game").setAttribute("aria-busy","false");window.layoutFixture=true;window.layoutFixtureScene=battlefield;'
                            request.fulfill(content_type='application/javascript', body=source.replace('\nboot();', '\n'+boot))
                        else:
                            local = ROOT/'Web/wwwroot'/path
                            if local.is_file():
                                request.fulfill(path=str(local))
                            else:
                                request.continue_()
                    page.route('**/*', route)
                    page.goto(args.url.rstrip('/')+'/index.html')
                    page.wait_for_function('window.layoutFixture === true')
                    assert page.title() == 'Dungeon Crawler Tactics · Play', page.title()
                    page.evaluate('document.fonts.ready')
                    page.wait_for_function("window.layoutFixtureScene?.getNativeArtStatus().state === 'ready'", timeout=60000)
                    page.wait_for_timeout(500)
                    common = ['#zoom-in', '#zoom-out', '#rotate-left', '#rotate-right', '#center-map']
                    selectors = common + (['#open-actions', '#move-mode', '[data-ability="ability.carl_powerful_strike"]', '[data-ability="ability.carl_dynamite"]', '[data-drawer="items"]', '#end-turn', '.hud-crawler', '.hud-actions', '.hud-target', '.party-strip', '.world-controls', '.battle-guidance'] if screen=='battle' else ['[data-walk="north"]', '[data-walk="west"]', '[data-walk="south"]', '[data-walk="east"]', '#return-camp', '.exploration-hud'])
                    result = page.evaluate(MEASURE, dict(selectors=selectors, touch=width<900))
                    filename = f'{screen}-{width}x{height}.png'
                    page.screenshot(path=str(output/filename), full_page=True)
                    result.update(screen=screen, viewport=[width,height], screenshot=filename, runtime='presentation fixture; no C# WASM', pageErrors=list(errors))
                    results.append(result)
                    if screen=='battle':
                        page.locator('#open-actions').click()
                        page.locator('#action-dialog').wait_for(state='visible')
                        modal = page.evaluate(MEASURE, dict(selectors=['#action-dialog', '#close-actions', '#modal-move', '#cancel-actions', '#actions-end-turn'], touch=width<900))
                        modal.update(screen='action-book', viewport=[width,height], runtime='presentation fixture; no C# WASM', pageErrors=list(errors))
                        filename=f'actions-{width}x{height}.png'
                        page.screenshot(path=str(output/filename), full_page=True)
                        modal['screenshot']=filename
                        results.append(modal)
                    page.close()
            browser.close()
    finally:
        if server:
            server.shutdown()
    (output/'summary.json').write_text(json.dumps(results, indent=2)+'\n')
    failures = [dict(screen=r['screen'], viewport=r['viewport'], errors=r['errors']+r['pageErrors']) for r in results if r['errors'] or r['pageErrors']]
    print(json.dumps(dict(output=str(output), checks=len(results), failures=failures), indent=2))
    return bool(failures)


if __name__ == '__main__':
    raise SystemExit(main())
