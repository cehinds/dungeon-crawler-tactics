"""Public-UI Lantern Row checks. Run after publishing WASM, with --url URL.

Uses legal exploration commands to approach rooms; every choice is clicked in
its actual modal. No save data is fabricated or edited.
"""
import argparse
import json
from pathlib import Path
from playwright.sync_api import sync_playwright


def wait(page, expression):
    page.wait_for_function(expression, timeout=30000)


def view(page):
    return page.evaluate('window.dungeon.getView()')


def save(page):
    value = page.evaluate('window.dungeon.getSave()')
    return json.loads(value) if isinstance(value, str) else value


def send(page, kind, **args):
    page.evaluate('([kind,args])=>window.dungeon.command(kind,args)', [kind, args])


def count(v, item):
    return next((i['count'] for i in v['items'] if i['id'] == item), 0)


def snapshot(page, output, name):
    page.screenshot(path=str(output / (name + '.png')), full_page=True)


def boot(page, url):
    page.goto(url, wait_until='domcontentloaded')
    wait(page, 'window.dungeon && window.dungeon.getView()')
    for dialog, button in [('#welcome-dialog', '#begin-button'), ('#help-dialog', '#help-dialog [data-close]')]:
        if page.locator(dialog).count() and page.locator(dialog).evaluate('(d)=>d.open'):
            page.locator(button).last.click()
    wait(page, "!document.querySelector('dialog[open]')")


def approach(page, point_id):
    """Find a reachable tile adjacent to the authored point using legal moves."""
    for _ in range(80):
        v = view(page)
        point = next((p for p in v['exploration']['points'] if (p['id'] == point_id or (point_id == '@encounter' and p['kind'] == 'encounter'))), None)
        if point and point['canInteract']:
            return point
        tiles = [t for t in v['exploration']['tiles'] if t['reachable'] and not t['blocked']]
        assert tiles, 'Exploration has no legal reachable tiles'
        if point:
            tiles.sort(key=lambda t: (abs(t['x']-point['x'])+abs(t['y']-point['y']), t['y'], t['x']))
        else:
            tiles = [t for t in tiles if not t['revealed']]
            assert tiles, 'Unseen room has no unrevealed reachable passages: '+point_id
            tiles.sort(key=lambda t: (t['y'], t['x']))
        tile = tiles[0]
        before = save(page)
        send(page, 'explore_move', x=tile['x'], y=tile['y'])
        assert save(page) != before, 'Legal exploration path made no progress'
    raise AssertionError('Room could not be reached through connected passages: '+point_id)


def choose(page, interaction_id, option_id, output, name):
    page.locator('[data-open-neighborhood]').first.click()
    wait(page, "document.querySelector('#neighborhood-dialog')?.open")
    selector = f'[data-neighborhood-interaction="{interaction_id}"][data-neighborhood-option="{option_id}"]'
    assert page.locator(selector).is_enabled(), 'Expected choice unavailable: '+option_id
    page.locator(selector).scroll_into_view_if_needed()
    snapshot(page, output, name+'-room-options')
    before_save = save(page)
    if option_id == 'rescue.help':
        trained = page.locator('[data-neighborhood-option="rescue.trained"]')
        assert trained.is_enabled(), 'Qualified party skill was not offered'
        trained.click()
        wait(page, "document.querySelector('#neighborhood-confirm-dialog')?.open")
        assert view(page)['neighborhood']['forecast']['rewardCount'] == 2
        assert save(page) == before_save
        snapshot(page, output, 'rescue-trained-preview')
        page.locator('#cancel-neighborhood').click()
        wait(page, '!window.dungeon.getView().neighborhood.forecast')
        assert save(page) == before_save
    before = view(page)
    page.locator(selector).click()
    wait(page, "document.querySelector('#neighborhood-confirm-dialog')?.open")
    forecast = view(page)['neighborhood']['forecast']
    assert save(page) == before_save, 'Preview mutated committed campaign'
    text = page.locator('#neighborhood-confirm-dialog').inner_text()
    assert 'Confirm' in text and 'Cancel' in text
    rect = page.locator('#neighborhood-confirm-dialog').bounding_box()
    assert rect['x'] >= 0 and rect['x']+rect['width'] <= page.viewport_size['width']+1, 'Choice dialog clips horizontally'
    for row in forecast['afterItems']:
        old = next(i['count'] for i in forecast['beforeItems'] if i['itemId']==row['itemId'])
        assert str(old)+' → '+str(row['count']) in text, 'Complete challenge inventory delta is hidden'
    if forecast['costCount']:
        assert str(forecast['beforeCost'])+' → '+str(forecast['afterCost']) in text, 'Cost inventory delta is hidden'
    snapshot(page, output, name+'-preview')
    page.locator('#cancel-neighborhood').click()
    wait(page, '!window.dungeon.getView().neighborhood.forecast')
    assert save(page) == before_save, 'Cancel mutated committed campaign'
    page.locator(selector).click()
    wait(page, "document.querySelector('#neighborhood-confirm-dialog')?.open")
    page.locator('#confirm-neighborhood').click()
    wait(page, '!window.dungeon.getView().neighborhood.forecast')
    after = view(page)
    # Assert visible total inventory matches the resolver's complete forecast,
    # including the separately displayed once-only challenge rewards.
    expected = {i['itemId']: i['count'] for i in forecast['afterItems']}
    for item, quantity in expected.items():
        assert count(after, item) == quantity, f'Confirmed inventory differs from preview: {item}'
    assert next(i for i in after['neighborhood']['interactions'] if i['id']==interaction_id)['completed']
    stable = save(page)
    send(page, 'confirm_neighborhood')
    assert save(page) == stable, 'Repeated confirm duplicated a receipt or reward'
    snapshot(page, output, name+'-committed')
    page.locator('#done-neighborhood').click()
    return {'option': option_id, 'cost': forecast['costCount'], 'earned': forecast['challengeIds']}


def run(browser, args, width, height):
    output = Path(args.screenshots) / str(width)
    output.mkdir(parents=True, exist_ok=True)
    context = browser.new_context(viewport={'width':width,'height':height}, device_scale_factor=1,
                                  is_mobile=width<600, has_touch=width<600)
    page = context.new_page()
    errors = []
    page.on('pageerror', lambda e: errors.append(str(e)))
    try:
        boot(page, args.url)
        campaign = save(page)
        page.locator('#open-neighborhood-start').click()
        snapshot(page, output, 'briefing')
        page.locator('#cancel-neighborhood-start').click()
        assert save(page) == campaign
        page.locator('#open-neighborhood-start').click()
        page.locator('#confirm-neighborhood-start').click()
        wait(page, 'window.dungeon.getView().neighborhood?.standalone')
        results = [choose(page, 'neighborhood.over_city.preparation', 'preparation.engineering', output, 'preparation')]
        page.locator('#quick-enter').click()
        wait(page, "window.dungeon.getView().screen==='explore'")
        start = save(page)
        # Actual keyboard navigation verifies the visible map accepts player input.
        for key in ('ArrowRight','ArrowDown','ArrowLeft','ArrowUp'):
            page.keyboard.press(key)
        snapshot(page, output, 'connected-map')
        for suffix, option in [('workshop','workshop.barter'), ('trap','trap.disarm'), ('rescue','rescue.help')]:
            interaction = next(i for i in view(page)['neighborhood']['interactions'] if i['id'].endswith('.'+suffix))
            approach(page, interaction['pointId'])
            assert next(p for p in view(page)['exploration']['points'] if p['id']==interaction['pointId'])['canInteract']
            results.append(choose(page, interaction['id'], option, output, suffix))
        assert sum(c['earned'] for c in view(page)['neighborhood']['challenges']) == 3, 'Not all three challenges earned'
        before_reload = save(page)
        (output/'before-reload.json').write_text(json.dumps(before_reload, indent=2))
        page.reload(wait_until='domcontentloaded')
        wait(page, 'window.dungeon && window.dungeon.getView().screen')
        assert save(page) == before_reload, 'Receipts, clues or inventory lost on reload'
        page.locator('[data-open-neighborhood]').first.click()
        assert page.locator('.neighborhood-challenges .earned').count() == 3
        snapshot(page, output, 'three-receipts-reloaded')
        page.locator('#done-neighborhood').click()
        send(page, 'return_camp')
        page.locator('#quick-enter').click()
        wait(page, "window.dungeon.getView().screen==='explore'")
        door = approach(page, '@encounter')
        page.locator(f'[data-explore-interact="{door["id"]}"]').click()
        wait(page, "window.dungeon.getView().screen==='battle'")
        before = save(page)
        actor = view(page)['selectedUnitId']
        page.locator('#end-turn').click()
        wait(page, "document.querySelector('#end-turn-dialog')?.open")
        assert 'NEXT' in page.locator('#end-turn-dialog').inner_text()
        page.locator('#cancel-end-turn').click()
        assert save(page) == before, 'Cancel end turn mutated battle'
        page.locator('#end-turn').click()
        page.locator('#confirm-end-turn').click()
        wait(page, 'window.dungeon.getView().selectedUnitId!=='+json.dumps(actor))
        assert next(u for u in view(page)['units'] if u['id']==actor)['finished']
        assert view(page)['round'] == 1, 'Enemies acted before remaining ready allies'
        snapshot(page, output, 'battle-next-ally')
        # Return the isolated neighborhood, then test the separate scenario lane.
        page.locator('[data-open-neighborhood]').first.click()
        page.locator('[data-return-neighborhood]').last.click()
        wait(page, '!window.dungeon.getView().neighborhood?.standalone')
        assert save(page) == campaign, 'Neighborhood did not restore exact preserved campaign'
        checkpoint = save(page)
        page.locator('#open-scenarios').click()
        page.locator('[data-scenario-briefing]').first.click()
        page.locator('#start-scenario').click()
        wait(page, '!!window.dungeon.getView().scenario')
        page.locator('#scenario-objective-button').click()
        page.locator('#return-scenario').click()
        wait(page, '!window.dungeon.getView().scenario')
        assert save(page) == checkpoint, 'Optional scenario did not restore exact campaign'
        assert not errors, errors
        return {'viewport':width,'choices':results,'screenshots':str(output),'browserErrors':errors}
    except Exception:
        snapshot(page, output, 'failure')
        (output/'failure-view.json').write_text(json.dumps(view(page), indent=2))
        (output/'failure-save.json').write_text(json.dumps(save(page), indent=2))
        raise
    finally:
        context.close()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:5188')
    parser.add_argument('--browser', default='/usr/bin/chromium')
    parser.add_argument('--screenshots', default='/tmp/dct-neighborhood-qa')
    args = parser.parse_args()
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=args.browser, headless=True, args=['--no-sandbox'])
        try:
            print(json.dumps([run(browser,args,1440,900),run(browser,args,390,844)], indent=2))
        finally:
            browser.close()


if __name__ == '__main__':
    main()
