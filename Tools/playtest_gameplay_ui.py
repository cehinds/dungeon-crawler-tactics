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
                tiles=tiles, width=12, height=10, reachable=[t for t in tiles if not t['blocked'] and abs(t['x']-2)+abs(t['y']-3)<=5],
                forecast=[], abilities=abilities, items=[], equipment=[], log=[],
                audience=dict(favor=0,favorCap=1,challenges=[],favorItemIds=[]),
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
   if(e.matches('button, summary') && touch && (r.width<40 || r.height<40)) errors.push('Small touch control: '+selector+' '+r.width+'x'+r.height);
   if(e.matches('button, summary') && parseFloat(getComputedStyle(e).fontSize)<12) errors.push('Unreadable text: '+selector);
 }
 const controls=selectors.filter(s=>document.querySelector(s)?.matches('button, summary'));
 const panels=['.hud-crawler','.hud-actions','.hud-target','.world-controls','.objective-banner','.party-strip'];
 const overlap=(a,b)=>Math.min(a.x+a.width,b.x+b.width)-Math.max(a.x,b.x)>2 && Math.min(a.y+a.height,b.y+b.height)-Math.max(a.y,b.y)>2;
 for(let i=0;i<panels.length;i++)for(let j=i+1;j<panels.length;j++){const a=boxes[panels[i]],b=boxes[panels[j]];if(a&&b&&overlap(a,b))errors.push('Overlapping HUD panels: '+panels[i]+' / '+panels[j]);}
 for(let i=0;i<controls.length;i++)for(let j=i+1;j<controls.length;j++){
   if(document.querySelector(controls[i])===document.querySelector(controls[j]))continue;
   const a=boxes[controls[i]],b=boxes[controls[j]];if(!a||!b)continue;
   if(Math.min(a.x+a.width,b.x+b.width)-Math.max(a.x,b.x)>2 && Math.min(a.y+a.height,b.y+b.height)-Math.max(a.y,b.y)>2)
      errors.push('Overlapping controls: '+controls[i]+' / '+controls[j]);
 }
 const turn=boxes['#end-turn'];
 if(turn){
   if(innerHeight-(turn.y+turn.height)>10)errors.push('End turn is not at the bottom');
   const party=boxes['.party-strip'];
   if(innerWidth<=730 && party && Math.abs(party.y+party.height-turn.y-turn.height)>4)errors.push('Phone party and End turn must share the lowest row');
   const hud=document.querySelector('.battle-hud').getBoundingClientRect();
   if(hud.height>(innerWidth<=730?230:150))errors.push('Persistent HUD covers too much of the map');
 }
 for(const meter of document.querySelectorAll('.deck-meter')) {
   const r=meter.getBoundingClientRect(), label=meter.querySelector('span').getBoundingClientRect(), value=meter.querySelector('b').getBoundingClientRect();
   if(r.height<18||label.right>value.left+1)errors.push('Vitals label/value overlap');
 }
 const hp=document.querySelector('.deck-meter.health')?.getBoundingClientRect(), mana=document.querySelector('.deck-meter.mana')?.getBoundingClientRect();
 if(hp&&mana&&overlap(hp,mana))errors.push('HP and Mana overlap');
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
            for width, height in [(1672, 941), (1440, 1000), (390, 844), (320, 740), (844, 390)]:
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
                            boot = 'content='+json.dumps(content)+';gameData='+json.dumps(game)+';view='+json.dumps(fixture(screen))+''';
                              narrator=createNarrator({getView:()=>view,content});
                              const initialFixture=structuredClone(view);
                              window.layoutMode=(mode)=>{
                                document.querySelectorAll('#forecast-dialog, #ability-details-dialog').forEach(dialog=>dialog.close());
                                detailedForecast=false;abilityDetailsOpen=false;
                                view=structuredClone(initialFixture);localAction=null;actionChooser=false;
                                if(mode==='targeting'||mode==='forecast'||mode==='status-forecast'||mode==='mana-forecast'||mode==='narrator-targeting'||mode==='long-description')localAction={abilityId:view.abilities[1].id};
                                if(mode==='forecast'||mode==='status-forecast'||mode==='mana-forecast'){
                                  view.canConfirm=true;
                                  view.forecast=[mode==='status-forecast'
                                    ?{targetId:'enemy.rat',label:'Dungeon rat',beforeHp:30,afterHp:30,beforeEnergy:12,afterEnergy:12,beforeTags:[],afterTags:['status.burning']}
                                    :mode==='mana-forecast'
                                      ?{targetId:'enemy.rat',label:'Dungeon rat',beforeHp:30,afterHp:30,beforeEnergy:12,afterEnergy:7,beforeTags:[],afterTags:[]}
                                      :{targetId:'enemy.rat',label:'Dungeon rat',beforeHp:30,afterHp:18,beforeEnergy:12,afterEnergy:12,beforeTags:[],afterTags:['status.burning']}];
                                }
                                if(mode==='enemy'){view.phase='enemy';view.canMove=false;view.canAct=false;}
                                if(mode==='finished-fallen') {view.units[0].finished=true;view.units[1].hp=0;view.roster[0].finished=true;view.roster[1].hp=0;}
                                if(mode==='narrator-targeting')narrator.onEvent({type:'damage',actorId:'crawler.carl',targetId:'enemy.rat',before:30,after:28,amount:2});
                                if(mode==='long-description')view.abilities[1].description='A carefully aimed explosive that travels across the chamber, fractures the target’s armor, ignites the landing tile, and leaves burning debris in a wide area. Choose a safe line of attack, then review the complete forecast before committing this action.';
                                render();
                              };
                              render();document.querySelector("#game").setAttribute("aria-busy","false");window.layoutFixture=true;window.layoutFixtureScene=battlefield;
                            '''
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
                    common = ['#camera-toggle', '#save-button', '.objective-banner', '.world-controls']
                    selectors = common + (['#open-character-sheet', '#open-actions', '#move-mode', '#end-turn', '.hud-crawler', '.hud-actions', '.party-strip', '.party-phase'] + [f'.hud-actions [data-ability]:nth-of-type({i})' for i in (2,3)] if screen=='battle' else ['[data-walk="north"]', '[data-walk="west"]', '[data-walk="south"]', '[data-walk="east"]', '#return-camp', '.exploration-hud', '.explore-party'] + [f'.explore-crawler:nth-child({i})' for i in range(1, 5)])
                    page.locator('#camera-toggle').click()
                    camera = page.evaluate(MEASURE, dict(selectors=['#zoom-in', '#zoom-out', '#rotate-left', '#rotate-right', '#center-map'], touch=width<900))
                    page.locator('#camera-toggle').click()
                    result = page.evaluate(MEASURE, dict(selectors=selectors, touch=width<900))
                    result['errors'] += camera['errors']
                    filename = f'{screen}-{width}x{height}.png'
                    page.screenshot(path=str(output/filename), full_page=True)
                    result.update(screen=screen, viewport=[width,height], screenshot=filename, runtime='presentation fixture; no C# WASM', pageErrors=list(errors))
                    results.append(result)
                    if screen=='battle':
                        assert page.locator('.hud-actions [data-ability]').count()==2
                        quick=page.locator('.hud-actions [data-ability]').first
                        assert 'Mana' in quick.get_attribute('title')
                        quick.click()
                        page.wait_for_function("document.querySelector('.hud-target')?.textContent.includes('Powerful Strike')")
                        assert page.locator('.hud-actions [data-ability]').first.get_attribute('aria-pressed')=='true'
                        page.evaluate("window.layoutMode('battle')")
                        assert not page.locator('#narrator-panel').is_visible(), 'Idle narrator still covers the map'
                        page.locator('#save-button').click()
                        page.locator('#help-button').click()
                        page.locator('#help-dialog').wait_for(state='visible')
                        assert not page.locator('#save-dialog').is_visible()
                        page.locator('#help-dialog .modal-actions [data-close]').click()
                        page.locator('#save-button').click()
                        page.locator('#menu-narrator-history').click()
                        page.locator('#narrator-history-dialog').wait_for(state='visible')
                        page.locator('#done-narrator-history').click()
                        page.locator('#save-button').click()
                        page.locator('#menu-game-tools [data-open-audience]').click()
                        page.locator('#audience-dialog').wait_for(state='visible')
                        assert not page.locator('#save-dialog').is_visible(), 'Run menu stayed open under sponsors'
                        page.locator('#done-audience').click()
                        page.locator('#open-actions').click()
                        page.locator('#action-dialog').wait_for(state='visible')
                        modal = page.evaluate(MEASURE, dict(selectors=['#action-dialog', '#close-actions', '#modal-move', '#cancel-actions', '#actions-end-turn'], touch=width<900))
                        modal.update(screen='action-book', viewport=[width,height], runtime='presentation fixture; no C# WASM', pageErrors=list(errors))
                        filename=f'actions-{width}x{height}.png'
                        page.screenshot(path=str(output/filename), full_page=True)
                        modal['screenshot']=filename
                        results.append(modal)
                        page.locator('#cancel-actions').click()
                        for mode in ['targeting', 'forecast', 'status-forecast', 'mana-forecast', 'finished-fallen', 'narrator-targeting', 'long-description', 'enemy']:
                            page.evaluate('(mode)=>window.layoutMode(mode)', mode)
                            page.wait_for_timeout(100)
                            state_selectors = ['#end-turn', '#open-actions', '.hud-crawler', '.hud-actions', '.party-phase']
                            if mode=='enemy':
                                assert page.locator('.hud-actions [data-ability]:enabled').count()==0
                                assert page.locator('#end-turn').is_disabled()
                            if mode not in ('enemy','finished-fallen'): state_selectors += ['.hud-target', '#cancel-forecast']
                            if mode in ('forecast','status-forecast','mana-forecast'): state_selectors += ['#review-forecast']
                            if mode=='finished-fallen': state_selectors += ['.party-chip:nth-child(1) .party-state', '.party-chip:nth-child(2) .party-state']
                            if mode=='finished-fallen':
                                assert page.locator('.party-chip:nth-child(1) .party-state').inner_text()=='END'
                                assert page.locator('.party-chip:nth-child(2) .party-state').inner_text()=='DOWN'
                            if mode=='narrator-targeting': state_selectors += ['#narrator-panel', '.hud-target', '#cancel-forecast']
                            if mode=='long-description': state_selectors += ['.hud-target', '#cancel-forecast']
                            if mode=='status-forecast':
                                page.locator('#review-forecast').click()
                                assert page.locator('.forecast-detail').count()==1
                                assert 'burn' in page.locator('.forecast-detail').inner_text().lower()
                                assert 'burn' in page.locator('.target-result').inner_text().lower()
                            if mode=='mana-forecast':
                                page.locator('#review-forecast').click()
                                detail=page.locator('.forecast-detail').inner_text()
                                assert 'Mana' in detail and '12 → 7' in detail
                            if mode=='narrator-targeting':
                                assert page.locator('#narrator-panel').get_attribute('data-empty')=='false'
                                overlap_check="""(() => {const a=document.querySelector('#narrator-panel').getBoundingClientRect(); return ['.hud-target','.hud-actions','#end-turn','#open-actions','#cancel-forecast'].some(s=>{const e=document.querySelector(s);if(!e)return false;const b=e.getBoundingClientRect();return Math.min(a.right,b.right)-Math.max(a.left,b.left)>2 && Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>2;});})()"""
                                assert not page.evaluate(overlap_check), 'Narrator overlaps targeting or action controls'
                            if mode=='long-description':
                                description=page.locator('.target-description')
                                assert description.is_visible()
                                assert len(description.inner_text()) > 180
                                desc_box=description.bounding_box()
                                card_box=page.locator('.hud-target').bounding_box()
                                assert desc_box['x'] >= card_box['x']-1 and desc_box['x']+desc_box['width'] <= card_box['x']+card_box['width']+1
                                assert desc_box['y'] >= card_box['y']-1 and desc_box['y']+desc_box['height'] <= card_box['y']+card_box['height']+1
                                page.locator('#open-ability-details').click()
                                assert page.locator('#ability-details-dialog').is_visible()
                                assert 'carefully aimed explosive' in page.locator('#ability-details-dialog').inner_text()
                            assert page.locator('.game-toast.toast-error').count()==0, 'Error toast appeared in presentation fixture'
                            state_result=page.evaluate(MEASURE, dict(selectors=state_selectors,touch=width<900))
                            assert state_result['boxes']['#end-turn'] == result['boxes']['#end-turn'], 'End turn moved between gameplay states'

                            state_filename=f'{mode}-{width}x{height}.png'
                            page.screenshot(path=str(output/state_filename),full_page=True)
                            state_result.update(screen=mode, viewport=[width,height], runtime='presentation fixture; no C# WASM', pageErrors=list(errors), screenshot=state_filename)
                            results.append(state_result)

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
