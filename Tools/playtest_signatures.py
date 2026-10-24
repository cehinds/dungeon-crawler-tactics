"""Exercise signature abilities through the published WASM UI, without fabricated saves.

Campaign setup reuses the legal-command story player in playtest_lore.py.
Run: python3 Tools/playtest_signatures.py --url http://127.0.0.1:5188
"""
import json
from pathlib import Path

# Its CLI accepts the same --url/--browser/--screenshots options as this check.
import playtest_lore as lore
from playwright.sync_api import sync_playwright

OUT = lore.OUT


def select_ability(page, ability_id):
    """Choose a primary shortcut or open the complete action book."""
    shortcut = page.locator('[data-ability="' + ability_id + '"]')
    if shortcut.count():
        shortcut.click()
    else:
        page.locator('#open-actions').click()
        page.locator('[data-modal-ability="' + ability_id + '"]').click()


def shot(page, name):
    # Settle real renderer playback before describing committed units as visible.
    skip = page.locator('#skip-animation')
    if skip.count() and skip.is_visible():
        skip.click()
        skip.wait_for(state='hidden')
    page.evaluate('()=>new Promise(resolve=>requestAnimationFrame(()=>requestAnimationFrame(resolve)))')
    # Dismiss transient notices through their actual UI for clear review captures.
    for button in page.locator('.toast-dismiss').all():
        if button.is_visible():
            button.click()
    page.screenshot(path=str(OUT / ('fidelity-' + name + '.png')))


def stable_save(page):
    return lore.save(page)


def click_unit(page, unit_id):
    page.locator(f'.party-chip[data-unit="{unit_id}"]').click()
    lore.wait(page, f'window.dungeon.getView().selectedUnitId==={json.dumps(unit_id)}')


def click_tile(page, x, y):
    lore.grid_click(page, x, y)
    lore.wait(page, 'window.dungeon.getView().canConfirm')
    lore.wait(page, "document.querySelector('#forecast-dialog')?.open")


def cancel_forecast(page):
    page.locator('#detail-cancel-forecast').click()
    lore.wait(page, '!window.dungeon.getView().canConfirm')


def commit_forecast(page):
    page.locator('#detail-confirm-forecast').click()
    lore.wait(page, '!window.dungeon.getView().canConfirm')


def tripwire(page):
    # A real expedition start preserves the clean campaign for subsequent story play.
    lore.send(page, 'expedition_start', targetId='expedition.sewers')
    lore.wait(page, "window.dungeon.getView().screen==='battle'")
    click_unit(page, 'crawler.carl')
    before = stable_save(page)
    select_ability(page, 'ability.carl_tripwire')
    action = next(a for a in lore.view(page)['abilities'] if a['id'] == 'ability.carl_tripwire')
    target = next(t for t in action['targetIds'] if t == 'tile.3.2') if 'tile.3.2' in action['targetIds'] else action['targetIds'][0]
    x, y = map(int, target.split('.')[1:])
    click_tile(page, x, y)
    assert stable_save(page) == before, 'Tripwire preview mutated save'
    assert 'shock' in page.locator('#forecast-dialog').inner_text().lower()
    shot(page, 'tripwire-preview-desktop')
    cancel_forecast(page)
    assert stable_save(page) == before, 'Tripwire cancel spent resources'
    select_ability(page, 'ability.carl_tripwire')
    click_tile(page, x, y)
    commit_forecast(page)
    carl = next(u for u in lore.view(page)['units'] if u['id'] == 'crawler.carl')
    assert carl['acted'], 'Tripwire did not spend the action'
    assert stable_save(page) != before, 'Tripwire commit did not persist'
    shot(page, 'tripwire-committed-desktop')
    lore.send(page, 'expedition_return')
    lore.wait(page, "window.dungeon.getView().screen==='camp'")


def story_and_specialty(page):
    page.locator('#open-journey').click()
    page.locator('#review-journey-start').click()
    page.locator('#confirm-journey-start').click()
    lore.wait(page, 'window.dungeon.getView().journey.active')
    result = lore.advance_story_to(page, 3)
    assert result['floor'] == 3
    donut = next(r for r in lore.view(page)['roster'] if r['id'] == 'crawler.donut')
    assert donut['level'] >= 3, f'Legal floor-three progression did not unlock level 3: {donut}'
    page.locator('.safe-party > summary').click()
    page.locator('[data-character-sheet="crawler.donut"]').click()
    page.locator('[data-sheet-section="sheet-skills"]').click()
    assert page.locator('#sheet-set-specialty').is_enabled()
    page.locator('#sheet-specialty-class').select_option('class.cryomancer')
    before = stable_save(page)
    page.locator('#sheet-set-specialty').click()
    assert page.locator('#specialty-review-dialog').is_visible()
    assert 'cryomancer' in page.locator('#specialty-review-dialog').inner_text().lower()
    shot(page, 'specialty-preview-desktop')
    page.locator('#cancel-specialty-review').click()
    assert stable_save(page) == before, 'Specialty cancel changed save'
    page.locator('#sheet-specialty-class').select_option('class.cryomancer')
    page.locator('#sheet-set-specialty').click()
    page.locator('#confirm-specialty-review').click()
    lore.wait(page, "window.dungeon.getView().roster.find(r=>r.id==='crawler.donut').specialtyClassId==='class.cryomancer'")
    assert page.locator('#sheet-set-specialty').is_disabled(), 'Specialty can be selected twice in one floor'
    shot(page, 'specialty-committed-desktop')
    page.locator('#done-character-sheet').click()
    return result


def triplicate(page):
    lore.send(page, 'expedition_start', targetId='expedition.sewers')
    lore.wait(page, "window.dungeon.getView().screen==='battle'")
    click_unit(page, 'crawler.donut')
    select_ability(page, 'ability.donut_clockwork_triplicate')
    mongo = next(u for u in lore.view(page)['units'] if u['id'] == 'crawler.mongo')
    before = stable_save(page)
    click_tile(page, mongo['x'], mongo['y'])
    assert stable_save(page) == before, 'Triplicate preview mutated save'
    forecast = lore.view(page)['forecast']
    assert len([f for f in forecast if f['targetId'].startswith('clockwork.')]) == 2
    shot(page, 'triplicate-preview-desktop')
    page.set_viewport_size({'width':390,'height':844})
    assert page.locator('#detail-cancel-forecast').is_visible()
    assert page.locator('#detail-confirm-forecast').is_visible()
    shot(page, 'triplicate-preview-phone')
    page.set_viewport_size({'width':1672,'height':941})
    cancel_forecast(page)
    assert stable_save(page) == before, 'Triplicate cancel changed save'
    select_ability(page, 'ability.donut_clockwork_triplicate')
    click_tile(page, mongo['x'], mongo['y'])
    commit_forecast(page)
    copies = [u for u in lore.view(page)['units'] if u.get('duplicateSourceId')]
    assert len(copies) == 2
    assert page.locator('.party-chip').count() == 6, 'Copies have no selectable party controls'
    assert all(u['duplicateSourceId'] == 'crawler.mongo' and u['duplicateRounds'] == 2 for u in copies)
    shot(page, 'triplicate-six-turns-desktop')
    copy = copies[0]
    click_unit(page, copy['id'])
    page.locator('#open-character-sheet').click()
    assert page.locator('.clockwork-sheet').is_visible()
    assert page.locator('.clockwork-sheet [role="tab"]').count() == 2
    assert page.locator('#sheet-specialty-class').count() == 0
    assert 'Mongo' in page.locator('.clockwork-sheet').inner_text()
    shot(page, 'clockwork-sheet-desktop')
    page.locator('[data-sheet-section="sheet-skills"]').click()
    assert page.locator('#sheet-skills').is_visible()
    page.locator('#done-character-sheet').click()
    # Exercise the selected copy's real movement and end-turn controls.
    destination = next(c for c in lore.view(page)['reachable'] if c['cost'] > 0)
    lore.grid_click(page, destination['x'], destination['y'])
    lore.wait(page, f'window.dungeon.getView().units.find(u=>u.id==={json.dumps(copy["id"])}).moved')
    page.locator('#end-turn').click()
    page.locator('#confirm-end-turn').click()
    lore.wait(page, f'window.dungeon.getView().units.find(u=>u.id==={json.dumps(copy["id"])}).finished')
    checkpoint = stable_save(page)
    page.reload(wait_until='domcontentloaded')
    lore.wait(page, 'window.dungeon && window.dungeon.getView().screen')
    assert stable_save(page) == checkpoint, 'Copy state did not survive real reload'
    assert page.locator('.party-chip').count() == 6
    page.set_viewport_size({'width': 390, 'height': 844})
    click_unit(page, copies[1]['id'])
    chip = page.locator(f'.party-chip[data-unit="{copies[1]["id"]}"]')
    page.wait_for_function('(id)=>{const r=document.querySelector(`[data-unit="${id}"]`).getBoundingClientRect();return r.left>=0&&r.right<=innerWidth}', arg=copies[1]['id'])
    point = page.evaluate('(id)=>{const u=dungeon.getView().units.find(u=>u.id===id);return dungeon.cellToScreen(u.x,u.y)}', copies[1]['id'])
    assert 0 <= point['x'] <= 390 and 0 <= point['y'] <= 524, f'Phone resize left selected copy off map: {point}'
    shot(page, 'triplicate-six-turns-phone')
    page.locator('#open-character-sheet').click()
    assert page.locator('.clockwork-sheet').is_visible()
    shot(page, 'clockwork-sheet-phone')
    page.locator('#done-character-sheet').click()
    assert not page.evaluate('document.documentElement.scrollWidth>innerWidth'), 'Copy controls overflow phone viewport'
    return {'copies': [u['id'] for u in copies], 'reload': True, 'sixPartyControls': True}


def rush(page):
    click_unit(page, 'crawler.katia')
    before = stable_save(page)
    original = next(u for u in lore.view(page)['units'] if u['id']=='crawler.katia')
    select_ability(page, 'ability.katia_rush')
    lore.wait(page, "document.querySelector('#forecast-dialog')?.open")
    assert stable_save(page) == before, 'Rush preview mutated save'
    forecast = next(f for f in lore.view(page)['forecast'] if f['targetId']=='crawler.katia')
    assert forecast['afterMove'] == forecast['beforeMove'] + 2
    shot(page, 'rush-preview-phone')
    cancel_forecast(page)
    assert stable_save(page) == before, 'Rush cancel changed save'
    select_ability(page, 'ability.katia_rush')
    lore.wait(page, "document.querySelector('#forecast-dialog')?.open")
    commit_forecast(page)
    katia = next(u for u in lore.view(page)['units'] if u['id']=='crawler.katia')
    assert katia['effectiveMove'] == original['effectiveMove'] + 2
    assert katia['acted'] and not katia['moved'] and lore.view(page)['canMove']
    assert katia['energy'] == original['energy'] - 3
    shot(page, 'rush-committed-phone')
    return {'moveBefore':original['effectiveMove'],'moveAfter':katia['effectiveMove'],'movementStillAvailable':True}


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=lore.args.browser, headless=True, args=['--no-sandbox'])
        context = browser.new_context(viewport={'width':1672,'height':941}, device_scale_factor=1)
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        lore.boot(page)
        print('Checking Tripwire UI', flush=True)
        tripwire(page)
        print('Playing legal story to Floor 3 and checking specialty UI', flush=True)
        journey = story_and_specialty(page)
        print('Checking Triplicate UI, copy turns and reload', flush=True)
        copies = triplicate(page)
        rushing = rush(page)
        assert not errors, errors
        print(json.dumps({'journey':journey,'rush':rushing,'clockwork':copies,'errors':errors,'screenshots':str(OUT)}, indent=2))
        context.close()
        browser.close()


if __name__ == '__main__':
    main()
