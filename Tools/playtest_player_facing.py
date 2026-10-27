"""Exercise real canvas sprite selection and event playback, without WebAssembly."""
import argparse
import functools
import http.server
from pathlib import Path
import shutil
import threading

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


class QuietHandler(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *_args):
        pass


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', help='Existing server serving Web/wwwroot; otherwise start a temporary server')
    parser.add_argument('--browser', default=shutil.which('chromium') or shutil.which('google-chrome'))
    args = parser.parse_args()
    server = None
    if not args.url:
        handler = functools.partial(QuietHandler, directory=str(ROOT / 'Web/wwwroot'))
        server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
        threading.Thread(target=server.serve_forever, daemon=True).start()
        args.url = f'http://127.0.0.1:{server.server_port}'
    try:
        with sync_playwright() as playwright:
            browser = playwright.chromium.launch(executable_path=args.browser, headless=True, args=['--no-sandbox'])
            page = browser.new_page(viewport={'width': 1100, 'height': 800}, reduced_motion='no-preference')
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.route('**/__player-facing-fixture.html', lambda route: route.fulfill(
                content_type='text/html', body='<!doctype html><html><body></body></html>'))
            page.goto(args.url.rstrip('/') + '/__player-facing-fixture.html')
            page.evaluate('''async()=>{
              document.body.innerHTML='<div style="position:relative"><canvas style="width:1000px;height:700px"></canvas></div>';
              const canvas=document.querySelector('canvas'), context=canvas.getContext('2d');
              window.paint=[];
              const draw=context.drawImage.bind(context);
              context.drawImage=(image,...coordinates)=>{
                const src=image.currentSrc||image.src||'';
                if(/assets\\/(directional|forms|revamp)\\//.test(src))
                  paint.push({src,sx:coordinates[0],sy:coordinates[1],pixelWidth:coordinates[6]*Math.hypot(context.getTransform().a,context.getTransform().b)/devicePixelRatio,at:performance.now()});
                if(paint.length>1000)paint.splice(0,500);
                return draw(image,...coordinates);
              };
              const {createBattlefield}=await import('./battlefield.js');
              window.field=createBattlefield(canvas);
              window.fixture=(key,formId)=>{
                const tiles=[];
                for(let y=0;y<8;y++)for(let x=0;x<8;x++)tiles.push({id:`tile.${x}.${y}`,x,y,blocked:false,reachable:true,revealed:true,tags:[]});
                return {screen:'battle',encounterName:`facing-${key}-${formId||''}`,width:8,height:8,tiles,
                  selectedUnitId:`crawler.${key}`,units:[
                    {id:`crawler.${key}`,artId:key,team:'player',hp:40,maxHp:40,x:4,y:4,tags:[],formId},
                    {id:'enemy.rat',artId:'rat',team:'enemy',hp:20,maxHp:20,x:2,y:4,tags:[]}],roster:[]};
              };
              window.state=fixture('carl');field.setView(state);
            }''')
            page.wait_for_function("field.getNativeArtStatus().state==='ready'", timeout=60000)
            page.wait_for_function("paint.some(p=>p.src.endsWith('/directional/carl.png'))", timeout=60000)
            result = page.evaluate('''async()=>{
              const frames=()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
              const assert=(condition,message)=>{if(!condition)throw Error(message);};
              const expectedLeft=[128,256,0,128],expectedDown=[128,128,256,0];
              const expectedRight=[0,128,128,256];
              const results=[];
              for(const [key,formId,file] of [['carl',null,'directional/carl.png'],['donut',null,'directional/donut.png'],['katia','form.bulwark','forms/bulwark.png']]){
                for(let q=0;q<4;q++){
                  // A fresh encounter clears persistent facing, just as a new battle does.
                  state=fixture(key,formId);state.encounterName+=`-${q}`;field.setView(state);
                  for(let turn=0;turn<q;turn++)field.rotate(1);
                  const check=async(column,rows,label)=>{
                    await frames();paint.length=0;await frames();
                    const sprites=paint.filter(p=>p.src.endsWith('/'+file));
                    assert(sprites.length,`${key} q${q} ${label}: missing directional sheet`);
                    assert(sprites.every(p=>p.sx===column&&rows.includes(p.sy)),
                      `${key} q${q} ${label}: actual source frames ${JSON.stringify(sprites)}`);
                    assert(!paint.some(p=>/\\/revamp\\/(characters|mongo)\\.png$/.test(p.src)),
                      `${key} q${q} ${label}: fell back to legacy action/hit art`);
                  };
                  await check(expectedLeft[q],[0],'initial nearest-left enemy');
                  let after=structuredClone(state);after.units[0].y=5;
                  let pending=field.playEvents([{type:'move',actorId:`crawler.${key}`,fromX:4,fromY:4,toX:4,toY:5}],state,after);
                  await check(expectedDown[q],[144,288],'walking down');await pending;state=after;
                  await check(expectedDown[q],[0],'walk direction persists');
                  // Move the target to the actor's right in the committed fixture.
                  state=structuredClone(state);state.units[1].x=6;state.units[1].y=5;field.setView(state);
                  after=structuredClone(state);
                  pending=field.playEvents([{type:'attack',actorId:`crawler.${key}`,targetId:'enemy.rat',abilityId:'ability.strike'}],state,after);
                  await check(expectedRight[q],[0],'attack turns to right target');await pending;state=after;
                  await check(expectedRight[q],[0],'attack direction persists');
                  after=structuredClone(state);after.units[0].hp=35;
                  pending=field.playEvents([{type:'damage',actorId:'enemy.rat',targetId:`crawler.${key}`,amount:5,after:35}],state,after);
                  await check(expectedRight[q],[0],'hit preserves direction');await pending;state=after;
                  results.push(`${key}${formId?' bulwark':''} view ${q}`);
                }
              }
              return results;
            }''')
            framing = []
            for width, height in [(320, 740), (390, 844), (1440, 900)]:
                page.set_viewport_size({'width': width, 'height': height})
                page.evaluate('''([width,height])=>{
                  const canvas=document.querySelector('canvas');canvas.style.width=width+'px';canvas.style.height=(height-160)+'px';field.resize();
                  const tiles=[];for(let y=0;y<13;y++)for(let x=0;x<17;x++)tiles.push({id:`tile.${x}.${y}`,x,y,blocked:false,reachable:true,revealed:true,tags:[]});
                  state=fixture('carl');state.width=17;state.height=13;state.tiles=tiles;state.encounterName='framing-'+width;
                  state.units=[...[[2,5],[3,5],[2,6],[3,6]].map(([x,y],i)=>({id:'crawler.'+['carl','donut','katia','mongo'][i],artId:['carl','donut','katia','mongo'][i],team:'player',hp:40,maxHp:40,x,y,tags:[]})),{id:'enemy.rat',artId:'rat',team:'enemy',hp:20,maxHp:20,x:5,y:5,tags:[]}];
                  field.setView(state);
                }''', [width, height])
                page.wait_for_function("field.getNativeArtStatus().state==='ready'", timeout=60000)
                page.wait_for_timeout(80)
                metrics = page.evaluate('''async()=>{
                  paint.length=0;await new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)));
                  const first=paint.find(p=>p.src.endsWith('/directional/carl.png'));
                  const canvas=document.querySelector('canvas'),box=canvas.getBoundingClientRect();
                  const points=state.units.map(u=>field.cellToScreen(u.x,u.y));
                  for(let q=0;q<4;q++){
                    for(const unit of state.units){const p=field.cellToScreen(unit.x,unit.y),cell=field.screenToCell(p.x,p.y);
                      if(cell?.x!==unit.x||cell?.y!==unit.y)throw Error('Default framing rotation/picking mismatch');
                      if(p.x<20||p.x>box.width-20||p.y<60||p.y>box.height-20)throw Error('Default framing cropped combat group '+JSON.stringify({q,p,box:box.toJSON()}));}
                    field.rotate(1);
                  }
                  return {width:box.width,framePixelWidth:first?.pixelWidth,tilePixelWidth:Math.hypot(field.cellToScreen(3,5).x-field.cellToScreen(2,5).x,field.cellToScreen(3,5).y-field.cellToScreen(2,5).y),points};
                }''')
                assert metrics['framePixelWidth'] >= (45 if width < 600 else 70), metrics
                framing.append(metrics)
            page.evaluate('field.dispose()')
            assert not errors, 'Browser errors: ' + '; '.join(errors)
            print('Real canvas player-facing playback passed: ' + ', '.join(result))
            print('Default combat framing (CSS pixels):', framing)
            print('Verified initial facing, walking frames, persistent facing, attacks and hits; renderer fixtures only, no WebAssembly rules execution.')
            browser.close()
    finally:
        if server:
            server.shutdown()
            server.server_close()


if __name__ == '__main__':
    main()
