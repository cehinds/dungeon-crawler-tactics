"""Actual published .NET WASM UI test; no core/runtime/view substitution.

A generated map is legally imported; a validated save seeds two 80HP enemies in
Magic Missile range and Donut selected. Positions/HP are setup, not earned play.
Every preview, target switch, cast, movement and end-turn uses production UI/core.
"""
import argparse
import json
import shutil
from pathlib import Path
from playwright.sync_api import sync_playwright
from playtest_procedural_maps import ready_runtime


def view(page):return page.evaluate('window.dungeon.getView()')
def save(page):return page.evaluate('window.dungeon.getSave()')
def cell_click(page,unit):
    point=page.evaluate('''u=>{const p=window.dungeon.cellToScreen(u.x,u.y),b=document.querySelector('#battlefield').getBoundingClientRect();return {x:b.left+p.x,y:b.top+p.y};}''',unit)
    page.mouse.click(point['x'],point['y'])


def main():
    parser=argparse.ArgumentParser(description=__doc__);parser.add_argument('--url',default='http://127.0.0.1:8772');parser.add_argument('--output',default='/tmp/dct-gba-gameplay');args=parser.parse_args()
    output=Path(args.output);output.mkdir(parents=True,exist_ok=True);checks=[];errors=[]
    with sync_playwright() as p:
        browser=p.chromium.launch(executable_path=shutil.which('chromium') or shutil.which('google-chrome'),args=['--no-sandbox'])
        context=browser.new_context(viewport=dict(width=1440,height=1000));context.add_init_script("localStorage.setItem('dct.help.seen','1')")
        page=context.new_page();page.on('pageerror',lambda e:errors.append(str(e)));page.goto(args.url+'/index.html');ready_runtime(page)
        for selector in ['#begin-button','[data-close="help-dialog"]']:
            if page.locator(selector).last.is_visible():page.locator(selector).last.click()
        seed=page.evaluate('''async()=>{
          const {generateDungeon,getPlayableMap}=await import('./procedural-map.js');
          const manifest=await fetch('assets/room-kit/manifest.json').then(r=>r.json()),rules=await fetch('assets/map-generation-rules.json').then(r=>r.json());
          const map=getPlayableMap(generateDungeon(manifest,{seed:'gba-target-switch',width:16,height:12,layout:'chambers'},rules),manifest);
          map.enemies=map.enemies.slice(0,2);if(map.enemies.length===1)map.enemies.push({...map.enemies[0],id:'enemy.gba_second'});
          map.enemies.forEach(e=>e.hp=80);
          await window.dungeon.command('import_map',{customMap:map});return JSON.parse(await window.dungeon.getSave());
        }''')
        actor=next(u for u in seed['units'] if u['id']=='crawler.donut');occupied={(u['x'],u['y']) for u in seed['units'] if u['team']=='player'}
        legal=[t for t in seed['tiles'] if not t['blocked'] and (t['x'],t['y']) not in occupied and 1<abs(t['x']-actor['x'])+abs(t['y']-actor['y'])<=3]
        enemies=[u for u in seed['units'] if u['team']=='enemy'];assert len(legal)>=len(enemies)>=2
        for enemy,tile in zip(enemies,legal):enemy.update(x=tile['x'],y=tile['y'],hp=80,maxHp=80)
        seed['selectedUnitId']=actor['id'];seed['development']['practice']=[]
        page.evaluate('s=>window.dungeon.loadSave(JSON.stringify(s))',seed)
        initial=view(page);ability=next(a for a in initial['abilities'] if a['id']=='ability.donut_magic_missile');ids=ability['targetIds'];assert len(ids)>=2 and ability['enabled']
        checkpoint=save(page)
        def open_forecast():
            page.click('#open-actions');page.click('[data-modal-ability="ability.donut_magic_missile"]');cell_click(page,next(u for u in view(page)['units'] if u['id']==ids[0]));page.wait_for_function('window.dungeon.getView().canConfirm');page.locator('#forecast-next-target').wait_for(state='visible')
        open_forecast()
        def selected_target():
            state=view(page);return next(f['targetId'] for f in state['forecast'] if f['beforeHp']!=f['afterHp'] and f['targetId'] in ids)
        assert selected_target()==ids[0]
        for _ in range(len(ids)):
            before=selected_target();page.click('#forecast-next-target');page.wait_for_function('id=>window.dungeon.getView().forecast.some(f=>f.targetId!==id&&f.beforeHp!==f.afterHp)',arg=before);assert selected_target() in ids;assert save(page)==checkpoint
        assert selected_target()==ids[0],'Next did not wrap to first legal target'
        page.click('#forecast-prev-target');page.wait_for_function('id=>window.dungeon.getView().forecast.some(f=>f.targetId===id&&f.beforeHp!==f.afterHp)',arg=ids[-1]);assert selected_target()==ids[-1]
        page.screenshot(path=str(output/'target-cycling.png'));page.click('#detail-cancel-forecast');assert save(page)==checkpoint
        checks.append('Next and Previous wrap only legal targets; previews and Cancel preserve byte-identical checkpoint.')
        open_forecast();page.click('#forecast-next-target');page.wait_for_function('id=>window.dungeon.getView().forecast.some(f=>f.targetId===id&&f.beforeHp!==f.afterHp)',arg=ids[1]);preview=view(page);chosen=selected_target();expected=next(f['afterHp'] for f in preview['forecast'] if f['targetId']==chosen)
        before_units={u['id']:u for u in initial['units']};page.click('#detail-confirm-forecast');page.wait_for_function('window.dungeon.getView().units.find(u=>u.id==="crawler.donut").acted');committed=view(page)
        for u in committed['units']:
            if u['team']=='enemy':assert u['hp']==(expected if u['id']==chosen else before_units[u['id']]['hp'])
        after_actor=next(u for u in committed['units'] if u['id']==actor['id']);assert after_actor['energy']==actor['energy']-ability['cost'] and not after_actor['moved'] and committed['canMove']
        practice=next(s for s in committed['development']['practice'] if s['unitId']==actor['id'] and s['abilityId']==ability['id']);assert practice['uses']==1
        checks.append('Confirm damages exactly chosen enemy, charges Mana once and trains one practice use; movement remains ready.')
        page.click('#move-mode');page.wait_for_function('window.dungeon.getView().reachable.some(t=>t.cost>0)');destination=next(t for t in view(page)['reachable'] if (t['x'],t['y'])!=(actor['x'],actor['y']));cell_click(page,destination);page.wait_for_function('window.dungeon.getView().units.find(u=>u.id==="crawler.donut").moved')
        moved=view(page);unit=next(u for u in moved['units'] if u['id']==actor['id']);assert (unit['x'],unit['y'])==(destination['x'],destination['y']) and unit['energy']==after_actor['energy']
        page.click('#end-turn');page.click('#confirm-end-turn');page.wait_for_function('window.dungeon.getView().selectedUnitId!=="crawler.donut"');assert next(u for u in view(page)['units'] if u['id']==actor['id'])['finished']
        checks.append('After casting, UI movement succeeds without extra Mana; End turn advances to another ready crawler.')
        page.screenshot(path=str(output/'after-action-move-endturn.png'));assert not errors,errors;browser.close()
    report=dict(runtime='actual published C# WASM',setup=__doc__,checks=checks,errors=errors);(output/'report.json').write_text(json.dumps(report,indent=2));print(json.dumps(report,indent=2))

if __name__=='__main__':main()
