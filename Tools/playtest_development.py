"""Browser regression for crawler development, scenarios, and runtime maps.

All consequential changes are made through the visible game controls. The one
saved battle adjustment in this script is a bounded QA fixture: it leaves one
real enemy at 1 HP so a short legal ability use can produce a genuine victory.
"""
import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--url', default='http://127.0.0.1:5188')
parser.add_argument('--browser', default='/usr/bin/chromium')
parser.add_argument('--screenshots', default='/tmp/dct-development')
args = parser.parse_args()


def view(page):
    return page.evaluate('window.dungeon.getView()')


def save(page):
    raw = page.evaluate('window.dungeon.getSave()')
    return json.loads(raw) if isinstance(raw, str) else raw


def wait_for(page, condition, timeout=20000, arg=None):
    page.wait_for_function(condition, arg=arg, timeout=timeout)


def cell_click(page, x, y):
    point = page.evaluate('''([x,y])=>{const p=window.dungeon.cellToScreen(x,y),b=document.querySelector('#battlefield').getBoundingClientRect();return {x:b.left+p.x,y:b.top+p.y}}''', [x, y])
    page.mouse.click(point['x'], point['y'])


def dismiss_intro(page):
    wait_for(page, 'window.dungeon && window.dungeon.getView()')
    if page.locator('#welcome-dialog').evaluate('d=>d.open'):
        page.locator('#begin-button').click()
    if page.locator('#help-dialog').evaluate('d=>d.open'):
        page.locator("#help-dialog [data-close='help-dialog']").last.click()
    wait_for(page, "!document.querySelector('dialog[open]')")


def enter_encounter(page):
    page.locator('#quick-enter').click()
    wait_for(page, "window.dungeon.getView().screen==='explore'")
    for _ in range(100):
        current = view(page)
        if current['screen'] == 'battle':
            return
        exploration = current['exploration']
        door = next((p for p in exploration['points'] if p['kind'] == 'encounter' and p['canInteract']), None)
        if door:
            page.locator(f"[data-explore-interact='{door['id']}']").click()
            wait_for(page, "window.dungeon.getView().screen==='battle'")
            return
        frontier = [t for t in exploration['tiles'] if t['reachable'] and not t['revealed']]
        if frontier:
            tile = min(frontier, key=lambda t: (t['y'], t['x']))
        else:
            point = next(p for p in exploration['points'] if p['kind'] == 'encounter')
            tile = min((t for t in exploration['tiles'] if t['reachable']), key=lambda t: abs(t['x']-point['x'])+abs(t['y']-point['y']))
        cell_click(page, tile['x'], tile['y'])
        wait_for(page, '([x,y])=>{const m=window.dungeon.getView().exploration;return m.x===x&&m.y===y}', timeout=5000, arg=[tile['x'], tile['y']])
    raise AssertionError('Could not reach the campaign encounter door.')


def earn_real_level_and_box(page):
    """Use one real ability command after preparing a one-hit encounter fixture."""
    enter_encounter(page)
    fixture = save(page)
    enemy = next(u for u in fixture['units'] if u['team'] == 'enemy')
    enemy_id = enemy['id']
    carl = next(u for u in fixture['units'] if u['id'] == 'crawler.carl')
    occupied = {(u['x'], u['y']) for u in fixture['units'] if u['team'] == 'player' and u['hp'] > 0}
    melee = [t for t in fixture['tiles'] if not t['blocked'] and (t['x'], t['y']) not in occupied and abs(t['x']-carl['x'])+abs(t['y']-carl['y']) == 1]
    assert melee, 'Could not prepare a legal adjacent target fixture.'
    enemy['x'], enemy['y'] = melee[0]['x'], melee[0]['y']
    for unit in fixture['units']:
        if unit['team'] == 'enemy':
            unit['hp'] = 1 if unit['id'] == enemy_id else 0
        else:
            unit['moved'] = False
            unit['acted'] = False
            unit['finished'] = False
    fixture['selectedUnitId'] = 'crawler.carl'
    fixture['phase'] = 'player'
    fixture['round'] = 1
    page.evaluate('s=>window.dungeon.loadSave(JSON.stringify(s))', fixture)
    wait_for(page, "window.dungeon.getView().screen==='battle' && window.dungeon.getView().selectedUnitId==='crawler.carl'")
    target = next(u for u in view(page)['units'] if u['id'] == enemy_id)
    ability = next((a for a in view(page)['abilities'] if a['enabled'] and a['target'] == 'enemy' and enemy_id in a['targetIds']), None)
    assert ability, 'The live encounter offers no legal ability against the QA target.'
    page.locator('#open-actions').click()
    wait_for(page, "document.querySelector('#action-dialog')?.open===true")
    page.locator(f"[data-modal-ability='{ability['id']}']").click()
    cell_click(page, target['x'], target['y'])
    wait_for(page, 'window.dungeon.getView().canConfirm')
    page.locator('#detail-confirm-forecast').click()
    wait_for(page, "window.dungeon.getView().screen==='victory'", timeout=15000)
    if page.locator('#level-up-dialog').count() and page.locator('#level-up-dialog').evaluate('d=>d.open'):
        page.locator('#continue-level-up').click()
    if page.locator('[data-reward]').count():
        page.locator('[data-reward]').first.click()
    page.locator('#continue-button').click()
    wait_for(page, "window.dungeon.getView().screen==='camp'", timeout=15000)
    assert view(page)['progression']['level'] >= 2


def inventory_counts(game):
    return {item['id']: item['count'] for item in game['items']}


def main():
    output = Path(args.screenshots)
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.browser, headless=True, args=['--no-sandbox', '--disable-cache'])
        page = browser.new_page(viewport={'width': 1366, 'height': 768}, device_scale_factor=1)
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(args.url, wait_until='domcontentloaded', timeout=60000)
        dismiss_intro(page)
        assert view(page)['screen'] == 'camp'
        earn_real_level_and_box(page)
        assert view(page)['development']['crawlers'][0]['unspentPoints'] >= 1
        page.screenshot(path=str(output / 'development-safe-room.png'), full_page=True)

        # Preview cancellation must leave persistent allocations and roster caps intact.
        page.locator('#open-development').click()
        wait_for(page, "document.querySelector('#development-dialog')?.open===true")
        before = save(page)
        before_carl = next(r for r in view(page)['roster'] if r['id'] == 'crawler.carl')
        page.locator("[data-allocate-stat='stat.constitution']").click()
        wait_for(page, "document.querySelector('#allocation-forecast')")
        forecast = view(page)['development']['forecast']
        assert forecast['afterHp'] == forecast['beforeHp'] + 3, 'Constitution preview does not show its actual max-HP effect.'
        page.screenshot(path=str(output / 'development-allocation-forecast.png'), full_page=True)
        page.locator('#cancel-allocation').click()
        wait_for(page, 'window.dungeon.getView().development.forecast===null')
        after_cancel = save(page)
        assert after_cancel.get('development') == before.get('development'), 'Canceled allocation changed persisted development data.'
        after_carl = next(r for r in view(page)['roster'] if r['id'] == 'crawler.carl')
        assert after_carl['maxHp'] == before_carl['maxHp'], 'Canceled allocation changed max HP.'

        page.locator("[data-allocate-stat='stat.constitution']").click()
        page.locator('#confirm-allocation').click()
        wait_for(page, f"window.dungeon.getView().roster.find(r=>r.id==='crawler.carl').maxHp > {before_carl['maxHp']}", timeout=10000)
        # Check persisted state, not only the current dialog forecast.
        committed = save(page)
        allocation = next(a for a in committed['development']['allocated'] if a['unitId'] == 'crawler.carl' and a['statId'] == 'stat.constitution')
        assert allocation['points'] == 1
        page.locator('[data-development-tab="practice"]').click()
        assert page.locator("[data-practice^='crawler.carl:']").count() >= 1, 'The committed ability use did not appear in its personal practice track.'
        page.locator('[data-development-tab="craft"]').click()
        recipe = page.locator("[data-craft-recipe='recipe.mega_tonic']")
        assert recipe.count() == 1 and recipe.is_enabled(), 'Starter inventory should support the Mega Tonic recipe.'
        supplies = inventory_counts(view(page))
        recipe.click()
        wait_for(page, "document.querySelector('#development-confirm-dialog')?.open===true")
        page.screenshot(path=str(output / 'development-craft-confirmation.png'), full_page=True)
        page.locator('#cancel-development-operation').click()
        assert inventory_counts(view(page)) == supplies, 'Canceling a craft spent materials.'
        page.locator("[data-craft-recipe='recipe.mega_tonic']").click()
        page.locator('#confirm-development-operation').click()
        wait_for(page, "window.dungeon.getView().items.find(i=>i.id==='item.mega_tonic').count >= 2")
        crafted = inventory_counts(view(page))
        assert crafted['item.health_tonic'] == supplies['item.health_tonic'] - 2

        page.locator('[data-development-tab="loot"]').click()
        owned = view(page)['development']['lootBoxes']
        unopened = next((box for box in owned if not box['opened']), None)
        assert unopened, 'The earned encounter box is missing from the safe-room menu.'
        item_before = inventory_counts(view(page))
        page.locator(f"[data-loot-box='{unopened['id']}']").click()
        page.locator('#cancel-development-operation').click()
        assert not next(box for box in view(page)['development']['lootBoxes'] if box['id'] == unopened['id'])['opened']
        assert inventory_counts(view(page)) == item_before, 'Canceling lootbox opening granted its rewards.'
        page.locator(f"[data-loot-box='{unopened['id']}']").click()
        page.locator('#confirm-development-operation').click()
        wait_for(page, f"window.dungeon.getView().development.lootBoxes.find(b=>b.id==={json.dumps(unopened['id'])}).opened")
        loot_committed = save(page)['development']
        page.locator('#done-development').click()
        page.reload(wait_until='domcontentloaded')
        dismiss_intro(page)
        assert save(page)['development'] == loot_committed, 'Allocation, practice, craft, or loot state did not survive reload.'
        practice_after_reload = view(page)['development']['practice']
        assert practice_after_reload, 'Personal ability practice did not survive reload.'
        page.screenshot(path=str(output / 'development-after-reload.png'), full_page=True)

        # Reopen the development sheets on a narrow screen and confirm they fit.
        page.set_viewport_size({'width': 390, 'height': 844})
        page.locator('#open-development').click()
        wait_for(page, "document.querySelector('#development-dialog')?.open===true")
        bounds = page.locator('#development-dialog').evaluate('(d)=>{const r=d.getBoundingClientRect();return {x:r.x,y:r.y,right:r.right,bottom:r.bottom}}')
        assert bounds['x'] >= 0 and bounds['right'] <= 390 and bounds['bottom'] <= 844, f'Development sheet clips at phone size: {bounds}'
        page.screenshot(path=str(output / 'development-phone.png'), full_page=True)
        persisted_before_escape = save(page)['development']
        page.keyboard.press('Escape')
        wait_for(page, "!document.querySelector('#development-dialog')?.open")
        assert save(page)['development'] == persisted_before_escape, 'Escape from the development sheet changed saved state.'
        page.set_viewport_size({'width': 1366, 'height': 768})

        # Boss scenario briefings and the first committed enemy phase are driven by visible controls.
        page.locator('#open-scenarios').click()
        wait_for(page, "document.querySelector('#scenario-dialog')?.open===true")
        scenarios = view(page)['scenarios']
        assert {s['id'] for s in scenarios} >= {'scenario.hoarder', 'scenario.juicer', 'scenario.swine'}
        campaign_save = save(page)
        campaign_xp = campaign_save['xp']
        campaign_level = view(page)['progression']['level']
        campaign_development = campaign_save.get('development')
        duplicate_level_notices = 0
        for scenario_id in ('scenario.hoarder', 'scenario.juicer', 'scenario.swine'):
            scenario_dialog = page.locator('#scenario-dialog')
            if not scenario_dialog.count() or not scenario_dialog.evaluate('d=>d.open'):
                if page.locator('#level-up-dialog').count() and page.locator('#level-up-dialog').evaluate('d=>d.open'):
                    duplicate_level_notices += 1
                    page.screenshot(path=str(output / 'scenario-return-level-up-notice.png'), full_page=True)
                    page.locator('#continue-level-up').click()
                    wait_for(page, "!document.querySelector('#level-up-dialog')?.open")
                page.locator('#open-scenarios').click()
                wait_for(page, "document.querySelector('#scenario-dialog')?.open===true")
            page.locator(f"[data-scenario-briefing='{scenario_id}']").click()
            assert page.locator('#scenario-briefing').is_visible()
            assert 'adaptation' in page.locator('#scenario-briefing').inner_text().lower()
            page.screenshot(path=str(output / f'{scenario_id}-briefing.png'), full_page=True)
            page.locator('#start-scenario').click()
            wait_for(page, f"window.dungeon.getView().scenario?.id==={json.dumps(scenario_id)}")
            assert view(page)['scenario']['intent']['cells'], f'{scenario_id} has no visible telegraph footprint.'
            page.screenshot(path=str(output / f'{scenario_id}-intent.png'), full_page=True)
            scenario_before = view(page)
            if scenario_id == 'scenario.juicer':
                # Move Carl into the exact telegraphed lane through the map controls.
                selected = next(u for u in scenario_before['units'] if u['id'] == 'crawler.carl')
                lane = [c for c in scenario_before['reachable'] if c['y'] == 3 and c['x'] <= 6]
                assert lane, 'Juicer telegraph has no reachable tile for a lane-interception test.'
                if scenario_before['selectedUnitId'] != selected['id']:
                    page.locator(f"[data-unit='{selected['id']}']").click()
                page.locator('#move-mode').click()
                cell_click(page, lane[0]['x'], lane[0]['y'])
                wait_for(page, f"window.dungeon.getView().units.find(u=>u.id==='crawler.carl').x==={lane[0]['x']} && window.dungeon.getView().units.find(u=>u.id==='crawler.carl').y===3")
            if scenario_id == 'scenario.swine':
                # Collect an actual component through the objective panel.
                page.locator('#scenario-objective-button').click()
                wait_for(page, "document.querySelector('#scenario-objective-dialog')?.open===true")
                part = page.locator("[data-scenario-interact='speedbump.parts']")
                assert part.count() == 1 and part.is_enabled(), 'Swine component is not available from the starting party position.'
                part.click()
                wait_for(page, "document.querySelector('#scenario-interaction-confirm')")
                assert 'component' in page.locator('#scenario-interaction-confirm').inner_text().lower()
                page.locator('#confirm-scenario-interaction').click()
                wait_for(page, "window.dungeon.getView().scenario.carryingUnitIds.length===1")
            # End each living crawler through the visible actor confirmation. The last
            # confirmation alone starts the scenario enemy phase.
            initial_round = view(page)['round']
            for _ in range(4):
                current = view(page)
                if current['phase'] != 'player':
                    break
                unfinished = [u for u in current['units'] if u['team'] == 'player' and u['hp'] > 0 and not u['finished']]
                if not unfinished:
                    break
                actor_id = current['selectedUnitId'] if any(u['id'] == current['selectedUnitId'] for u in unfinished) else unfinished[0]['id']
                if current['selectedUnitId'] != actor_id:
                    page.locator(f"[data-unit='{actor_id}']").click()
                    wait_for(page, f"window.dungeon.getView().selectedUnitId==={json.dumps(actor_id)}")
                page.locator('#end-turn').click()
                wait_for(page, "document.querySelector('#end-turn-dialog')?.open===true")
                page.locator('#confirm-end-turn').click()
                try:
                    wait_for(page, f"(()=>{{const v=window.dungeon.getView();return v.round>{initial_round} || v.units.find(u=>u.id==={json.dumps(actor_id)}).finished}})()", timeout=6000)
                except Exception as error:
                    raise AssertionError(f"Could not finish {actor_id}'s turn: {json.dumps(view(page))}") from error
            wait_for(page, f"window.dungeon.getView().round>{initial_round} && window.dungeon.getView().phase==='player'", timeout=15000)
            after_phase = view(page)
            before_by_id = {u['id']: u for u in scenario_before['units']}
            after_by_id = {u['id']: u for u in after_phase['units']}
            changed = [uid for uid, old in before_by_id.items() if uid in after_by_id and (old['x'], old['y'], old['hp']) != (after_by_id[uid]['x'], after_by_id[uid]['y'], after_by_id[uid]['hp'])]
            if scenario_id == 'scenario.hoarder':
                assert sum(1 for u in after_phase['units'] if u['id'].startswith('scatterer.') and u['hp'] > 0) == 2, 'Hoarder failed to spawn the capped pair of Scatterers.'
            elif scenario_id == 'scenario.juicer':
                assert after_by_id['crawler.carl']['hp'] < before_by_id['crawler.carl']['hp'], 'Juicer did not resolve its visible flaming lane against the moved crawler.'
            else:
                assert (after_by_id['boss.swine']['x'], after_by_id['boss.swine']['y']) != (before_by_id['boss.swine']['x'], before_by_id['boss.swine']['y']), 'Ball of Swine did not move along its telegraphed route.'
            assert changed or scenario_id == 'scenario.hoarder', f'{scenario_id} enemy phase had no visible impact or movement.'
            page.screenshot(path=str(output / f'{scenario_id}-resolved-phase.png'), full_page=True)
            wait_for(page, "!document.body.classList.contains('enemy-playback')", timeout=20000)
            page.locator('#scenario-objective-button').click()
            wait_for(page, "document.querySelector('#scenario-objective-dialog')?.open===true")
            assert page.locator('#scenario-objective-dialog').inner_text().strip()
            page.locator('#return-scenario').click()
            wait_for(page, "window.dungeon.getView().screen==='camp' && window.dungeon.getView().scenario===null")
            restored_campaign = save(page)
            assert restored_campaign['xp'] == campaign_xp and view(page)['progression']['level'] == campaign_level, f'{scenario_id} return did not restore campaign progression.'
            assert restored_campaign.get('development') == campaign_development, f'{scenario_id} return changed campaign allocation/practice/loot state.'
            if page.locator('#level-up-dialog').count() and page.locator('#level-up-dialog').evaluate('d=>d.open'):
                duplicate_level_notices += 1
                page.screenshot(path=str(output / 'scenario-return-level-up-notice.png'), full_page=True)
                page.locator('#continue-level-up').click()
                wait_for(page, "!document.querySelector('#level-up-dialog')?.open")

        # Malformed map import must preserve the actual run byte-for-byte.
        campaign_level_before_map = view(page)['progression']['level']
        before_invalid = save(page)
        page.locator('#save-button').click()
        invalid = {'schemaVersion': 1, 'width': 21, 'height': 8, 'tiles': [], 'playerSpawns': [], 'enemies': [], 'placements': [], 'label': 'invalid width'}
        page.locator('#import-map-file').set_input_files({'name': 'invalid-map.json', 'mimeType': 'application/json', 'buffer': json.dumps(invalid).encode()})
        wait_for(page, "[...document.querySelectorAll('.game-toast .toast-text')].some(node=>/map|workshop|width/i.test(node.textContent))", timeout=5000)
        error_copy = ' '.join(page.locator('.game-toast').all_inner_texts()).lower()
        assert any(word in error_copy for word in ('map', 'workshop', 'invalid')), f'Invalid map feedback was unclear: {error_copy}'
        assert save(page) == before_invalid, 'Rejected custom map replaced or mutated the active campaign.'
        page.screenshot(path=str(output / 'invalid-map-preserves-campaign.png'), full_page=True)

        # Valid workshop map import, serialization, and reload.
        valid = {'schemaVersion': 1, 'width': 10, 'height': 8, 'tiles': [{'x': 4, 'y': 4, 'blocked': True, 'tags': []}], 'playerSpawns': [], 'enemies': [], 'placements': [], 'label': 'QA connected chamber'}
        page.locator('#import-map-file').set_input_files({'name': 'qa-map.json', 'mimeType': 'application/json', 'buffer': json.dumps(valid).encode()})
        wait_for(page, "window.dungeon.getView().screen==='battle' && window.dungeon.getView().customMap?.label==='QA connected chamber'")
        assert len(view(page)['units']) >= 7
        page.screenshot(path=str(output / 'custom-map-battle.png'), full_page=True)
        page.reload(wait_until='domcontentloaded')
        dismiss_intro(page)
        assert view(page)['customMap']['label'] == 'QA connected chamber'
        assert duplicate_level_notices == 0, 'Returning from a scenario repeated the campaign level-up notice.'
        assert not errors, f'Browser errors: {errors}'
        print(json.dumps({'campaignLevelBeforeMapImport': campaign_level_before_map, 'practiceRowsAfterReload': len(practice_after_reload),
                          'craft': 'canceled without cost, then confirmed', 'loot': 'canceled without reward, then confirmed and persisted',
                          'scenarios': ['scenario.hoarder', 'scenario.juicer', 'scenario.swine'],
                          'duplicateLevelUpNoticesOnScenarioReturn': duplicate_level_notices,
                          'invalidMap': 'rejected without campaign mutation', 'validMap': 'imported and survived reload',
                          'screenshots': [str(path) for path in sorted(output.iterdir())], 'errors': errors}))
        browser.close()


if __name__ == '__main__':
    main()
