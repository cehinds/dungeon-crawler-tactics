"""Camera presentation regression using production JS/CSS; no C# runtime required."""
import argparse
import functools
import http.server
import json
from pathlib import Path
import shutil
import threading
from playwright.sync_api import sync_playwright
from playtest_gameplay_ui import ROOT, fixture


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--browser', default=shutil.which('chromium') or shutil.which('google-chrome'))
    parser.add_argument('--output', default='/tmp/dct-target-camera')
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(http.server.SimpleHTTPRequestHandler, directory=str(ROOT/'Web/wwwroot')))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    url = f'http://127.0.0.1:{server.server_port}'
    state = fixture('battle')
    state['units'][0].update(x=5, y=5)
    state['units'][-1].update(x=1, y=3)
    state['units'].append(dict(state['units'][-1], id='enemy.opposite', x=10, y=7))
    state['abilities'][1]['targetIds'] = ['enemy.rat', 'enemy.opposite']
    results = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=args.browser, args=['--no-sandbox'])
            page = browser.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            def route(request):
                path = request.request.url.split('?', 1)[0].removeprefix(url+'/')
                if path.startswith('_framework/'):
                    request.fulfill(content_type='application/javascript', body='')
                elif path in ('data/game-content.json', 'data/combat-content.json'):
                    request.fulfill(path=str(ROOT/'UnityPackage/Runtime/Data'/Path(path).name))
                elif path == 'game.js':
                    source = (ROOT/'Web/wwwroot/game.js').read_text()
                    boot = 'content='+ (ROOT/'UnityPackage/Runtime/Data/combat-content.json').read_text()+';gameData='+(ROOT/'UnityPackage/Runtime/Data/game-content.json').read_text()+';view='+json.dumps(state)+''';
                      narrator=createNarrator({getView:()=>view,content});
                      const unitAction=structuredClone(view.abilities[1]);
                      window.cameraFixture={
                        target(id=null){Object.assign(view.abilities[1],unitAction);localAction={abilityId:view.abilities[1].id};view.canConfirm=!!id;previewTargetId=id;render();},
                        terrain(){view.abilities[1]={...unitAction,target:'tile',targetIds:view.tiles.filter(t=>!t.blocked).map(t=>t.id)};localAction={abilityId:unitAction.id};view.canConfirm=false;previewTargetId=null;render();},
                        refresh(){render();},
                        get scene(){return battlefield;},
                        get units(){return view.units;}
                      };
                      render();
                    '''
                    request.fulfill(content_type='application/javascript', body=source.replace('\nboot();','\n'+boot))
                else:
                    request.continue_()
            page.route('**/*', route)
            page.goto(url+'/index.html')
            page.wait_for_function("window.cameraFixture?.scene.getNativeArtStatus().state==='ready'", timeout=60000)
            for width, height in [(390,844), (320,740), (844,390), (1440,1000)]:
                page.set_viewport_size(dict(width=width,height=height))
                page.wait_for_timeout(100)
                resized=page.evaluate('cameraFixture.scene.cellToScreen(10,7)')
                if results:
                    assert 0<resized['x']<width and 0<resized['y']<height, ('Resize lost target',width,height,resized)
                page.evaluate('cameraFixture.target()')
                # Trigger a distinct target-selection transition even when resizing an active action.
                page.evaluate("cameraFixture.target('enemy.rat');cameraFixture.target()")
                for scenario in [None, 'enemy.rat', 'enemy.opposite', 'terrain']:
                    target=None if scenario=='terrain' else scenario
                    if scenario=='terrain':
                        page.evaluate('cameraFixture.terrain()')
                    else:
                        page.evaluate('(id)=>cameraFixture.target(id)', target)
                    page.wait_for_timeout(50)
                    measurements = page.evaluate('''(target)=>{
                      const scene=cameraFixture.scene, canvas=document.querySelector('#battlefield').getBoundingClientRect();
                      const ids=['crawler.carl',...(target?[target]:['enemy.rat','enemy.opposite'])];
                      const obstacles=[...document.querySelectorAll('.objective-banner,.battle-hud,.hud-target')].map(e=>e.getBoundingClientRect());
                      const positions=ids.map(id=>{const unit=cameraFixture.units.find(u=>u.id===id),p=scene.cellToScreen(unit.x,unit.y);return {id,x:p.x+canvas.left,y:p.y+canvas.top};});
                      return {positions,errors:positions.flatMap(p=>{
                        const errors=[];
                        if(p.x<canvas.left+5||p.x>canvas.right-5||p.y<canvas.top+5||p.y>canvas.bottom-5)errors.push(p.id+' outside canvas');
                        if(obstacles.some(o=>p.x>o.left&&p.x<o.right&&p.y>o.top&&p.y<o.bottom))errors.push(p.id+' under HUD');
                        return errors;
                      })};
                    }''', target)
                    assert not measurements['errors'], (width,height,target,measurements)
                    results.append(dict(viewport=[width,height], target=scenario, **measurements))
                for rotation in range(4):
                    page.evaluate('cameraFixture.scene.rotate(1)')
                    page.wait_for_timeout(20)
                    point=page.evaluate('cameraFixture.scene.cellToScreen(10,7)')
                    assert 0<point['x']<width and 0<point['y']<height, (width,height,rotation,point)
                canvas = page.locator('#battlefield').bounding_box()
                x, y = canvas['x']+canvas['width']/2, canvas['y']+canvas['height']/2
                original=page.evaluate('cameraFixture.scene.cellToScreen(5,5)')
                page.mouse.move(x,y)
                page.mouse.down()
                page.mouse.move(x+31,y+19,steps=3)
                page.mouse.up()
                before=page.evaluate('cameraFixture.scene.cellToScreen(5,5)')
                assert abs(before['x']-original['x'])>20, ('Pan did not move camera',original,before)
                page.evaluate('cameraFixture.refresh()')
                after=page.evaluate('cameraFixture.scene.cellToScreen(5,5)')
                assert abs(before['x']-after['x'])<.01 and abs(before['y']-after['y'])<.01, (before,after)
                page.screenshot(path=str(output/f'targeting-{width}x{height}.png'))
            assert not errors, errors
            browser.close()
    finally:
        server.shutdown()
    (output/'summary.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(dict(output=str(output),checks=len(results),failures=[])))


if __name__ == '__main__':
    main()
