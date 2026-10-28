"""Production presentation fixtures for cast power UI; does not execute C# rules."""
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
    ability=state['abilities'][0]
    ability.update(rank=5, maxRank=15, cost=5, enabled=False, disabledReason='Not enough Mana')
    ability['castModes']=[dict(id=f'power.{cost}',label=f'Power {cost}',minimumRank=5,cost=cost,range=cost,
        description=f'CORE EFFECT {cost}: precise damage summary',enabled=cost<=3,
        disabledReason='' if cost<=3 else 'Not enough Mana',targetIds=['enemy.rat']) for cost in range(3,7)]
    state['units'][0]['energy']=3
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
                        window.powerFixture=(rank,mana)=>{view.canConfirm=false;window.lastCommand=null;view.abilities[0].rank=rank;view.abilities[0].enabled=mana>=5;view.abilities[0].castModes.forEach(mode=>mode.enabled=mana>=mode.cost&&rank>=mode.minimumRank);localAction=null;castPowerAbilityId=null;render();};
                        window.powerAction=()=>({selected:selectedAction(),local:localAction});
                        window.powerPreview=()=>{view.canConfirm=true;view.forecast=[];localAction={abilityId:view.abilities[1].id};};
                        window.powerLockedDetails=()=>renderAbilityDetails(view.abilities[0],content,{full:true,practice:{rank:4,ranks:[{rank:4,cost:5,range:4,requiredUses:0}],castModes:view.abilities[0].castModes}});
                        window.lastCommand=null;window.powerCommands=[];
                        window.DotNet={invokeMethodAsync:async(assembly,method,payload)=>{if(method==='Dispatch'){window.lastCommand=JSON.parse(payload);window.powerCommands.push(window.lastCommand);view.canConfirm=window.lastCommand.type==='preview';return JSON.stringify(view);}return '{}';}};
                        window.powerTarget=()=>clickCell(6,4);
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
                button='[data-ability="ability.carl_powerful_strike"]'
                assert page.locator(button).is_enabled(), 'Low Mana must retain cheaper mode access'
                page.click(button)
                assert page.locator('[data-cast-mode]').count()==4
                assert page.locator('[data-cast-mode]:enabled').count()==1
                assert 'CORE EFFECT 3' in page.locator('#cast-power-dialog').inner_text()
                page.keyboard.press('Escape')
                assert page.locator('#cast-power-dialog').count()==0
                assert page.locator(button).evaluate('e=>e===document.activeElement')
                for cost in range(3,7):
                    page.evaluate('window.powerFixture(5,10)')
                    page.click(button)
                    page.click(f'[data-cast-mode="power.{cost}"]')
                    action=page.evaluate('window.powerAction()')
                    assert action['local']['castModeId']==f'power.{cost}'
                    assert action['selected']['cost']==cost
                    assert action['selected']['range']==cost
                    assert action['selected']['description'].startswith(f'CORE EFFECT {cost}')
                    assert action['selected']['targetIds']==['enemy.rat']
                    assert f'{cost} Mana' in page.locator('.hud-target').inner_text()
                    page.evaluate('window.powerTarget()')
                    page.wait_for_function('window.lastCommand?.type==="preview"')
                    assert page.evaluate('window.lastCommand.castModeId')==f'power.{cost}'
                page.evaluate('window.powerFixture(5,10);window.powerPreview()')
                page.click(button)
                assert page.evaluate('window.lastCommand.type')=='cancel', 'Clear existing preview before choosing power'
                page.keyboard.press('Escape')
                page.evaluate('window.powerFixture(4,10)')
                assert 'Unlocks at rank 5' in page.evaluate('window.powerLockedDetails()')
                page.click(button)
                assert page.locator('#cast-power-dialog').count()==0
                assert 'castModeId' not in page.evaluate('window.powerAction().local')
                assert page.evaluate('window.powerAction().selected.cost')==5
                page.click('[data-ability="ability.carl_dynamite"]')
                assert page.locator('#cast-power-dialog').count()==0
                assert page.evaluate('window.powerAction().selected.cost')==5
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                page.close()
            browser.close()
        assert not errors,errors
        print('PASS: generic cast-power popup, low Mana, all four DTO budgets/effects/targets, preview mode forwarding, rank4 baseline, ordinary actions, Escape focus (4 viewports).')
    finally:
        server.shutdown()

if __name__=='__main__':
    main()
