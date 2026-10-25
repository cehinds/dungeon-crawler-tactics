"""Focused renderer checks independent of the WebAssembly game controller."""
import argparse
import shutil
from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8127')
    parser.add_argument('--browser', default=shutil.which('chromium') or shutil.which('google-chrome'))
    args = parser.parse_args()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.browser, headless=True, args=['--no-sandbox'])
        page = browser.new_page(viewport={'width': 1100, 'height': 800})
        page.goto(args.url + '/dungeon-generator.html')
        page.evaluate('''async()=>{
          document.body.innerHTML='<div style="position:relative"><canvas style="width:1000px;height:700px"></canvas></div>';
          const {createBattlefield}=await import('./battlefield.js');
          window.field=createBattlefield(document.querySelector('canvas'));
          window.state={screen:'explore',roster:[{id:'carl',selected:true,hp:40,maxHp:40}],exploration:{id:'large-authored',width:26,height:18,x:2,y:2,points:[],tiles:[]}};
          for(let y=0;y<18;y++)for(let x=0;x<26;x++)state.exploration.tiles.push({x,y,blocked:x===0||y===0||x===25||y===17||(x===12&&y!==9),revealed:x<5,reachable:x<5,tags:[]});
          window.loads=0;document.querySelector('canvas').addEventListener('nativeartready',()=>loads++);
          field.setView(state);
        }''')
        page.wait_for_function("field.getNativeArtStatus().state==='ready'", timeout=60000)
        result = page.evaluate('''()=>{
          const initial=field.getNativeArtStatus();
          if(initial.projection!=='orthogonal'||initial.pieceCount<100)throw Error(JSON.stringify(initial));
          for(let q=0;q<4;q++){
            for(const [x,y] of [[1,1],[24,16],[12,9],[2,2]]){
              const p=field.cellToScreen(x,y),cell=field.screenToCell(p.x,p.y);
              if(cell?.x!==x||cell?.y!==y)throw Error('Rotation picking mismatch '+q);
            }
            const a=field.cellToScreen(2,2),b=field.cellToScreen(3,2),c=field.cellToScreen(2,3);
            if(Math.abs(Math.hypot(b.x-a.x,b.y-a.y)-Math.hypot(c.x-a.x,c.y-a.y))>.001)throw Error('Nonsquare cell');
            const d=field.movementDirection(1,0);
            if(Math.abs(d.x)+Math.abs(d.y)!==1)throw Error('Invalid movement direction');
            field.rotate(1);
          }
          const next=structuredClone(state);next.exploration.x=3;next.exploration.tiles.forEach(t=>{t.revealed=t.x<8;t.reachable=t.x<8;});field.setView(next);
          if(loads!==1||field.getNativeArtStatus().state!=='ready')throw Error('Movement or fog reveal reloaded map art');
          return initial;
        }''')
        page.evaluate('''()=>{
          const tiles=[];for(let y=0;y<8;y++)for(let x=0;x<8;x++)tiles.push({x,y,blocked:false,reachable:true,revealed:true,tags:[]});
          const visuals={schemaVersion:1,styleId:'pocket-dungeon',kitId:'starter-dungeon',pieces:tiles.map(t=>({cell:0,x2:t.x*2,y2:t.y*2,rotation:0,layer:'ground'}))};
          window.portable={screen:'battle',width:8,height:8,tiles,units:[],customMap:{tiles,visuals}};
          field.setView(portable);
        }''')
        page.wait_for_function("field.getNativeArtStatus().state==='ready'", timeout=60000)
        page.evaluate('''()=>{
          const battle=field.getNativeVisuals();
          if(JSON.stringify(battle)!==JSON.stringify(portable.customMap.visuals))throw Error('Battle art changed');
          const explore={...portable,screen:'explore',exploration:{id:'generated',width:8,height:8,x:1,y:1,tiles:portable.tiles,points:[]},roster:[]};
          field.setView(explore);
          if(field.getNativeArtStatus().state!=='ready'||JSON.stringify(field.getNativeVisuals())!==JSON.stringify(battle))throw Error('Exploration art differs from battle');
          for(let q=0;q<4;q++){
            const p=field.cellToScreen(7,7),cell=field.screenToCell(p.x,p.y);
            if(cell?.x!==7||cell?.y!==7)throw Error('Generated exploration picking mismatch');
            field.rotate(1);
          }
        }''')
        print('Square authored exploration, large dimensions, all four rotations, picking, stable movement art, and exact portable battle/exploration parity passed:', result)
        browser.close()


if __name__ == '__main__':
    main()
