"""Presentation-only party Move/Act readiness fixtures at four viewport sizes."""
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
 const errors=[], rect=e=>e.getBoundingClientRect(), visible=r=>r.left>=0&&r.top>=0&&r.right<=innerWidth+1&&r.bottom<=innerHeight+1;
 const overlap=(a,b)=>Math.min(a.right,b.right)-Math.max(a.left,b.left)>2&&Math.min(a.bottom,b.bottom)-Math.max(a.top,b.top)>2;
 for(const e of document.querySelectorAll('.party-resource,.party-state,#end-turn')){
   if(!visible(rect(e)))errors.push('Outside viewport: '+e.className);
   if(e.scrollWidth>e.clientWidth+1)errors.push('Clipped badge: '+e.textContent);
   if(parseFloat(getComputedStyle(e).fontSize)<9)errors.push('Unreadable badge: '+e.textContent);
 }
 const chips=[...document.querySelectorAll('.party-chip')];
 for(const chip of chips){const resources=[...chip.querySelectorAll('.party-resource')];
   if(resources.length===2&&overlap(rect(resources[0]),rect(resources[1])))errors.push('Move/Act overlap');
 }
 const party=document.querySelector('.party-strip'),end=document.querySelector('#end-turn');
 if(overlap(rect(party),rect(end)))errors.push('Party overlaps End turn');
 if(document.documentElement.scrollWidth>innerWidth+1)errors.push('Document overflow');
 const style=c=>{const e=document.querySelector(c);if(!e)return null;const s=getComputedStyle(e);return [s.textDecorationLine,s.borderStyle,s.opacity,s.fontWeight,s.fontStyle].join('|')};
 for(const kind of ['move','act'])if(style('.'+kind+'-ready')&&style('.'+kind+'-spent')&&style('.'+kind+'-ready')===style('.'+kind+'-spent'))errors.push(kind+' readiness differs only by color');
 return errors;
}"""

def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--output',default='/tmp/dct-turn-readiness');args=parser.parse_args()
    output=Path(args.output);output.mkdir(parents=True,exist_ok=True)
    server=http.server.ThreadingHTTPServer(('127.0.0.1',0),functools.partial(http.server.SimpleHTTPRequestHandler,directory=str(ROOT/'Web/wwwroot')))
    threading.Thread(target=server.serve_forever,daemon=True).start();base=f'http://127.0.0.1:{server.server_port}'
    state=fixture('battle');state['units'][1]['moved']=True;state['units'][2]['acted']=True;state['units'][3].update(moved=True,acted=True)
    results=[]
    try:
        with sync_playwright() as p:
            browser=p.chromium.launch(executable_path=shutil.which('chromium') or shutil.which('google-chrome'),args=['--no-sandbox'])
            for width,height in [(1440,1000),(390,844),(320,740),(844,390)]:
                page=browser.new_page(viewport=dict(width=width,height=height));errors=[];page.on('pageerror',lambda e:errors.append(str(e)))
                def route(r):
                    path=r.request.url.split('?',1)[0].split(base,1)[-1].lstrip('/')
                    if path.startswith('_framework/'):r.fulfill(status=200,content_type='application/javascript',body='')
                    elif path=='game.js':
                        boot='content='+(ROOT/'UnityPackage/Runtime/Data/combat-content.json').read_text()+';gameData='+(ROOT/'UnityPackage/Runtime/Data/game-content.json').read_text()+';view='+json.dumps(state)+''';narrator=createNarrator({getView:()=>view,content});window.endedFixture=()=>{view.units[0].finished=true;view.units[1].hp=0;render();};render();window.fixtureReady=true;'''
                        r.fulfill(content_type='application/javascript',body=(ROOT/'Web/wwwroot/game.js').read_text().replace('\nboot();','\n'+boot))
                    else:r.continue_()
                page.route('**/*',route);page.goto(base+'/index.html');page.wait_for_function('window.fixtureReady');page.evaluate('document.fonts.ready')
                assert page.locator('.party-resource').count()==8
                for index,classes in enumerate([['move-ready','act-ready'],['move-spent','act-ready'],['move-ready','act-spent'],['move-spent','act-spent']]):
                    chip=page.locator('.party-chip').nth(index)
                    assert chip.locator('.party-resource').all_text_contents()==['Move','Act']
                    assert all(chip.locator('.'+c).count()==1 for c in classes)
                errors.extend(page.evaluate(LAYOUT));page.screenshot(path=str(output/f'readiness-{width}x{height}.png'))
                page.evaluate('window.endedFixture()')
                for index,label in [(0,'END'),(1,'DOWN')]:
                    chip=page.locator('.party-chip').nth(index);assert chip.locator('.party-state').inner_text()==label;assert chip.locator('.party-budget').count()==0
                errors.extend(page.evaluate(LAYOUT))
                page.screenshot(path=str(output/f'ended-down-{width}x{height}.png'));results.append(dict(viewport=[width,height],errors=errors));page.close()
            browser.close()
    finally:server.shutdown()
    report=dict(runtime=__doc__,results=results);(output/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2));return any(r['errors'] for r in results)

if __name__=='__main__':raise SystemExit(main())
