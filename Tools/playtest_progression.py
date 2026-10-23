"""Exercise safe-room progression, saving, and a real encounter level-up via UI.

A validated save fixture weakens the final enemy only to keep the level-up test
short; all reward, equipment, rest, skill, quest, and final-attack actions use UI.
"""
import argparse
import json
import re
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


def enter_encounter(page):
    page.locator('#quick-enter').click()
    page.wait_for_function("window.dungeon.getView().screen==='explore'")
    for _ in range(100):
        game = view(page)
        if game['screen'] == 'battle':
            return
        exploration = game['exploration']
        door = next((p for p in exploration['points'] if p['kind'] == 'encounter' and p['canInteract']), None)
        if door:
            page.locator(f"[data-explore-interact='{door['id']}']").click()
            page.wait_for_function("window.dungeon.getView().screen==='battle'")
            return
        frontier = [t for t in exploration['tiles'] if t['reachable'] and not t['revealed']]
        if frontier:
            tile = min(frontier, key=lambda t: (t['y'], t['x']))
        else:
            point = next(p for p in exploration['points'] if p['kind'] == 'encounter')
            tile = min((t for t in exploration['tiles'] if t['reachable']), key=lambda t: abs(t['x']-point['x'])+abs(t['y']-point['y']))
        cell_click(page, tile['x'], tile['y'])
        page.wait_for_function('([x,y])=>{const m=window.dungeon.getView().exploration;return m.x===x&&m.y===y}', arg=[tile['x'], tile['y']])
    raise AssertionError('Could not reach the encounter door.')


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

        # Quest journal opens from its button in battle; camp includes the journal summary.
        page.locator('.safe-quests summary').click()
        assert 'Quest journal' in page.locator('.safe-quests').inner_text() or page.locator('.safe-quests .quest-row').count()>0
        page.locator('.safe-quests summary').click()

        carl=next(r for r in game['roster'] if r['id']=='crawler.carl')
        old_hp=carl['maxHp']
        page.locator("[data-equipment='crawler.carl']").first.click()
        page.wait_for_function("document.querySelector('#equipment-dialog')?.open===true")
        vest=page.locator("[data-equip='equipment.armor.field_vest']")
        assert vest.count()==1 and vest.is_enabled()
        vest.click()
        page.wait_for_function("window.dungeon.getView().roster.find(r=>r.id==='crawler.carl').maxHp > 0 && window.dungeon.getView().equipment.find(e=>e.id==='equipment.armor.field_vest').equippedUnitId==='crawler.carl'")
        assert next(r for r in view(page)['roster'] if r['id']=='crawler.carl')['maxHp']==old_hp+5
        page.locator('#done-loadout').click()
        page.wait_for_function("!document.querySelector('#equipment-dialog')")

        # Reload through the visible save dialog and verify equipment survived persistence.
        page.locator('#save-button').click()
        page.locator('#reload-save-button').click()
        page.wait_for_function("!document.querySelector('#save-dialog')?.open && window.dungeon.getView().equipment.find(e=>e.id==='equipment.armor.field_vest').equippedUnitId==='crawler.carl'")
        assert next(r for r in view(page)['roster'] if r['id']=='crawler.carl')['maxHp']==old_hp+5

        # Damage and spend mana in a valid camp save fixture, then use visible Rest.
        fixture=save(page)
        carl_save=next(r for r in fixture['roster'] if r['id']=='crawler.carl')
        carl_save['hp']=max(1,carl_save['maxHp']-3)
        carl_save['energy']=max(0,carl_save['maxEnergy']-1)
        page.evaluate('s=>window.dungeon.loadSave(JSON.stringify(s))', fixture)
        page.wait_for_function("window.dungeon.getView().roster.find(r=>r.id==='crawler.carl').hp < window.dungeon.getView().roster.find(r=>r.id==='crawler.carl').maxHp")
        before_rest=next(r for r in view(page)['roster'] if r['id']=='crawler.carl')
        page.locator('#rest-button').click()
        page.wait_for_function("window.dungeon.getView().safeRoom.rested")
        after_rest=next(r for r in view(page)['roster'] if r['id']=='crawler.carl')
        assert after_rest['hp']==after_rest['maxHp'] and after_rest['energy']==after_rest['maxEnergy']

        # Skills and lock reasons are visible before earning level 2.
        page.locator("[data-skills='crawler.carl']").first.click()
        page.wait_for_function("document.querySelector('#skills-dialog')?.open===true")
        locked=page.locator("[data-skill='unlock.carl.level_2']")
        assert locked.count()==1 and 'Locked' in locked.inner_text() and 'Reach party level 2' in locked.inner_text()
        page.locator('#done-loadout').click()
        page.wait_for_function("!document.querySelector('#skills-dialog')")

        # Reach first encounter, then import a valid battle state with one 1 HP enemy.
        enter_encounter(page)
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
        assert 'Party level 2' in level_dialog and 'Rigged Burst' in level_dialog
        page.screenshot(path=str(camp_path/'progression-level-up.png'), full_page=True)
        page.locator('#continue-level-up').click()
        page.wait_for_function("!document.querySelector('#level-up-dialog')")
        rewards=page.locator('[data-reward]')
        if rewards.count():
            rewards.first.click()
        page.locator('#continue-button').click()
        page.wait_for_function("window.dungeon.getView().screen==='camp'", timeout=15000)
        final=view(page)
        assert final['progression']['level']==2 and final['xp']>=30
        assert next(q for q in final['quests'] if q['id']=='quest.floor')['progress']==1
        page.locator("[data-skills='crawler.carl']").first.click()
        page.wait_for_function("document.querySelector('#skills-dialog')?.open===true")
        unlocked=page.locator("[data-skill='unlock.carl.level_2']")
        assert unlocked.count()==1 and 'Unlocked' in unlocked.inner_text() and 'Available in the action menu' in unlocked.inner_text()
        assert 'Rigged Burst' in page.locator('#skills-dialog').inner_text()
        assert not errors, f'Page errors: {errors}'
        result={'safeRoom':'rest restored damaged HP and spent MP','equipment':'Field Vest +5 HP equipped and survived local save reload',
                'skills':'level-2 Rigged Burst transitioned locked → unlocked through real victory',
                'quest':'floor quest advanced after encounter victory','xp':final['xp'],'level':final['progression']['level'],
                'enemyDefeated':enemy_id,'errors':errors,'screenshots':[str(camp_path/'progression-camp.png'),str(camp_path/'progression-level-up.png')]}
        page.close();browser.close();print(json.dumps(result))


if __name__=='__main__':
    main()
