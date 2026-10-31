"""Exercise current progression-gain notice through an actual C# encounter victory.

A validated save fixture weakens the final enemy only to keep the level-up test
short. Generated-map import and save loading are setup; the final attack, gains
dialog and Continue use production UI and the current shared C# rules.
"""
import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--url', default='http://127.0.0.1:5188')
parser.add_argument('--browser', default='/usr/bin/chromium')
parser.add_argument('--screenshots', default='/tmp/dct-progression')
args = parser.parse_args()


def view(page):
    return page.evaluate('window.dungeon.getView()')


def save(page):
    raw = page.evaluate('window.dungeon.getSave()')
    return json.loads(raw) if isinstance(raw, str) else raw


def cell_click(page, x, y):
    point = page.evaluate('''([x,y])=>{const p=window.dungeon.cellToScreen(x,y),b=document.querySelector('#battlefield').getBoundingClientRect();return {x:b.left+p.x,y:b.top+p.y}}''', [x,y])
    page.mouse.click(point['x'], point['y'])


def dismiss_intro(page):
    page.wait_for_function('window.dungeon && window.dungeon.getView()', timeout=60000)
    if page.locator('#welcome-dialog').evaluate('d=>d.open'):
        page.locator('#begin-button').click()
    if page.locator('#help-dialog').evaluate('d=>d.open'):
        page.locator("#help-dialog [data-close='help-dialog']").last.click()
    page.wait_for_function("!document.querySelector('dialog[open]')")



def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=args.browser, headless=True, args=['--no-sandbox'])
        page = browser.new_page(viewport={'width':1366,'height':768})
        errors=[]
        page.on('pageerror', lambda err: errors.append(str(err)))
        page.goto(args.url, wait_until='domcontentloaded', timeout=60000)
        dismiss_intro(page)
        game=view(page)
        assert game['screen']=='camp' and game['safeRoom']['available']
        assert game['progression']['level']==1
        assert game['roster'][0]['id']=='crawler.carl'
        camp_path=Path(args.screenshots); camp_path.mkdir(parents=True, exist_ok=True)
        page.screenshot(path=str(camp_path/'progression-camp.png'), full_page=True)

        # Legally import generated content; the final-hit save fixture below is explicit.
        page.evaluate("""async()=>{
          const {generateDungeon,getPlayableMap}=await import('./procedural-map.js');
          const manifest=await fetch('assets/room-kit/manifest.json').then(r=>r.json());
          const rules=await fetch('assets/map-generation-rules.json').then(r=>r.json());
          const map=getPlayableMap(generateDungeon(manifest,{seed:'broadcast-level-up',width:16,height:12,layout:'chambers'},rules),manifest);
          await window.dungeon.command('import_map',{customMap:map});
        }""")
        page.wait_for_function("window.dungeon.getView().screen==='battle'")
        baseline=save(page)
        enemy=next(u for u in baseline['units'] if u['team']=='enemy')
        enemy_id=enemy['id']
        carl_unit=next(u for u in baseline['units'] if u['id']=='crawler.carl')
        occupied={(u['x'],u['y']) for u in baseline['units'] if u['team']=='player' and u['hp']>0}
        floors=[t for t in baseline['tiles'] if not t['blocked'] and (t['x'],t['y']) not in occupied]
        melee=[t for t in floors if abs(t['x']-carl_unit['x'])+abs(t['y']-carl_unit['y'])==1]
        assert melee, 'Could not create a legal close-range final-hit fixture.'
        enemy['x'],enemy['y']=melee[0]['x'],melee[0]['y']
        for u in baseline['units']:
            if u['team']=='enemy':
                u['hp']=1 if u['id']==enemy_id else 0
            else:
                u['moved']=False; u['acted']=False
        baseline['selectedUnitId']='crawler.carl'
        baseline['phase']='player'; baseline['round']=1
        page.evaluate('s=>window.dungeon.loadSave(JSON.stringify(s))', baseline)
        page.wait_for_function("window.dungeon.getView().screen==='battle' && window.dungeon.getView().selectedUnitId==='crawler.carl'")
        game=view(page)
        target=next(u for u in game['units'] if u['id']==enemy_id)
        legal_attacks=[a for a in game['abilities'] if a['enabled'] and a['target']=='enemy' and enemy_id in a['targetIds']]
        assert legal_attacks, f'No legal final-hit ability for the fixture enemy: {game["abilities"]}'
        attack=legal_attacks[0]
        page.locator('#open-actions').click()
        page.wait_for_function("document.querySelector('#action-dialog')?.open===true")
        page.locator(f"[data-modal-ability='{attack['id']}']").click()
        cell_click(page,target['x'],target['y'])
        page.wait_for_function('window.dungeon.getView().canConfirm')
        page.locator('#detail-confirm-forecast').click()
        page.wait_for_function("window.dungeon.getView().screen==='victory'", timeout=15000)
        page.wait_for_function("document.querySelector('#level-up-dialog')?.open===true", timeout=10000)
        level_dialog=page.locator('#level-up-dialog').inner_text()
        assert 'Party level 1 → 2' in level_dialog and 'Rigged Burst' in level_dialog
        assert '+3 allocation points each' in level_dialog
        assert '+3 maximum HP' in level_dialog and '+1 maximum Mana' in level_dialog
        page.screenshot(path=str(camp_path/'progression-level-up.png'), full_page=True)
        page.locator('#continue-level-up').click()
        page.wait_for_function("!document.querySelector('#level-up-dialog')")
        final=view(page)
        assert final['progression']['level']==2 and final['xp']>=30
        assert not errors,errors
        result={'runtime':'fresh current WASM; validated one-HP final enemy setup; actual UI final attack',
                'checks':['exact level1→2 gains','3HP and1Mana gain','3allocation points','Rigged Burst unlocked','Continue dismisses notice'],
                'xp':final['xp'],'level':final['progression']['level'],'errors':errors}
        (camp_path/'report.json').write_text(json.dumps(result,indent=2))
        page.close();browser.close();print(json.dumps(result))


if __name__=='__main__':
    main()
