"""Exercise continuous exploration movement using the real canvas renderer."""
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
    parser.add_argument('--browser', default=shutil.which('chromium') or shutil.which('google-chrome'))
    args = parser.parse_args()
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), functools.partial(QuietHandler, directory=str(ROOT / 'Web/wwwroot')))
    threading.Thread(target=server.serve_forever, daemon=True).start()
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=args.browser, headless=True, args=['--no-sandbox'])
            page = browser.new_page(viewport={'width': 1100, 'height': 800}, reduced_motion='no-preference')
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.route('**/__motion-fixture.html', lambda route: route.fulfill(content_type='text/html', body='<!doctype html><body></body>'))
            page.goto(f'http://127.0.0.1:{server.server_port}/__motion-fixture.html')
            page.evaluate('''async()=>{
              document.body.innerHTML='<div style="position:relative"><canvas style="width:1000px;height:700px"></canvas></div>';
              const canvas=document.querySelector('canvas'),ctx=canvas.getContext('2d'),draw=ctx.drawImage.bind(ctx);
              window.paint=[];window.partySheets=new Set();
              ctx.drawImage=(image,...c)=>{
                const source=image.currentSrc||image.src||'';
                if(source.includes('/directional/'))partySheets.add(source.split('/').pop());
                if(source.endsWith('/directional/carl.png')){
                  const t=ctx.getTransform();paint.push({sx:c[0],sy:c[1],x:t.e,y:t.f,scale:Math.hypot(t.a,t.b),at:performance.now()});
                }
                return draw(image,...c);
              };
              const {createBattlefield}=await import('./battlefield.js');
              window.field=createBattlefield(canvas);
              const tiles=[];for(let y=0;y<32;y++)for(let x=0;x<40;x++)tiles.push({x,y,blocked:false,reachable:true,revealed:x<25&&y<20,tags:[]});
              window.state={screen:'explore',width:40,height:32,exploration:{id:'motion-floor',width:40,height:32,x:5,y:5,tiles,points:[]},
                roster:['carl','donut','katia','mongo'].map(key=>({id:'crawler.'+key,artId:key,selected:true,hp:40,maxHp:40})),units:[],tiles:[]};
              field.setView(state);
            }''')
            page.wait_for_function("field.getNativeArtStatus().state==='ready'&&paint.length>0", timeout=60000)
            result = page.evaluate('''async()=>{
              const wait=ms=>new Promise(resolve=>setTimeout(resolve,ms));
              const assert=(ok,message)=>{if(!ok)throw Error(message);};
              const checks=[];
              for(const [dx,dy,column] of [[1,0,0],[0,1,128],[-1,0,128],[0,-1,256]]){
                paint.length=0;
                state=structuredClone(state);state.exploration.x+=dx;state.exploration.y+=dy;
                field.setView(state);const start=performance.now();
                await wait(65);field.setView(structuredClone(state));await wait(115);
                const moving=paint.filter(f=>f.at-start<145);
                assert(moving.length>=4,'Walking did not render enough display frames');
                assert(moving.every(f=>f.sx===column),'Wrong cardinal directional art column '+JSON.stringify(moving));
                assert(moving.some(f=>f.sy===144)&&moving.some(f=>f.sy===288),'Both walking poses must render');
                const positions=moving.map(f=>dx?f.x:f.y);
                assert(new Set(positions.map(x=>Math.round(x))).size>=4,'Movement snapped instead of interpolating');
                for(let i=1;i<positions.length;i++)assert(Math.abs(positions[i]-positions[i-1])<35,'Movement jumped during unchanged-state render');
                assert(paint.at(-1).sy===0,'Walking should settle to idle promptly');
                assert(paint.at(-1).scale>=.6,'Large floors must preserve readable character scale');
                checks.push({dx,dy,frames:moving.length});
              }
              assert(partySheets.size===1&&partySheets.has('carl.png'),'Explore must draw one living party leader');
              const before=field.cellToScreen(5,5);
              for(let i=0;i<12;i++){state=structuredClone(state);state.exploration.x++;field.setView(state);await wait(150);}
              const after=field.cellToScreen(5,5),leader=field.cellToScreen(state.exploration.x,state.exploration.y);
              assert(after.x<before.x-100,'Exploration camera did not follow travel');
              assert(leader.x<800&&leader.x>200,'Follow camera lost the leader');
              // Camera can inspect the dark portion of the map, but floor pixels stay opaque.
              state=structuredClone(state);state.exploration.id='fog-floor';state.exploration.x=30;state.exploration.y=24;field.setView(state);await wait(80);
              const dark=field.cellToScreen(32,24),pixel=document.querySelector('canvas').getContext('2d').getImageData(Math.round(dark.x-8),Math.round(dark.y-8),1,1).data;
              assert(pixel[0]===7&&pixel[1]===16&&pixel[2]===25&&pixel[3]===255,'Unexplored native tiles leaked artwork '+JSON.stringify([...pixel]));
              return {directions:checks,camera:leader,fog:[...pixel]};
            }''')
            assert not errors, errors
            print('Exploration motion/camera/fog passed:', result)
            browser.close()
    finally:
        server.shutdown()

if __name__ == '__main__':
    main()
