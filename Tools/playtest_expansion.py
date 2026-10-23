"""Browser regression for the branching skill trees and six expeditions.

This exercises the served game through visible controls. It uses a fresh browser
profile so an earlier local save cannot hide first-run or persistence behavior.
"""
import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright


parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--url', default='http://127.0.0.1:5188')
parser.add_argument('--browser', default='/usr/bin/chromium')
parser.add_argument('--screenshots', default='/tmp/dct-expansion')
args = parser.parse_args()


def view(page):
    return page.evaluate('window.dungeon.getView()')


def save(page):
    raw = page.evaluate('window.dungeon.getSave()')
    return json.loads(raw) if isinstance(raw, str) else raw


def wait(page, expression, timeout=20000, arg=None):
    page.wait_for_function(expression, timeout=timeout, arg=arg)


def dismiss_intro(page):
    wait(page, 'window.dungeon && window.dungeon.getView()')
    if page.locator('#welcome-dialog').evaluate('d=>d.open'):
        page.locator('#begin-button').click()
    if page.locator('#help-dialog').evaluate('d=>d.open'):
        page.locator("#help-dialog [data-close='help-dialog']").last.click()
    wait(page, "!document.querySelector('dialog[open]')")


def assert_dialog_fits(page, selector, width, height):
    rect = page.locator(selector).evaluate('(d)=>{const r=d.getBoundingClientRect();return {x:r.x,y:r.y,right:r.right,bottom:r.bottom,width:r.width,height:r.height,scrollHeight:d.scrollHeight,clientHeight:d.clientHeight}}')
    assert rect['x'] >= 0 and rect['y'] >= 0 and rect['right'] <= width and rect['bottom'] <= height, f'{selector} clips at {width}x{height}: {rect}'


def cell_click(page, x, y):
    point = page.evaluate('''([x,y])=>{const p=window.dungeon.cellToScreen(x,y),b=document.querySelector('#battlefield').getBoundingClientRect();return {x:b.left+p.x,y:b.top+p.y}}''', [x, y])
    page.mouse.click(point['x'], point['y'])


def test_skill_tree(page, output):
    assert view(page)['screen'] == 'camp', 'Skill tree check expects the safe room.'
    trees = view(page).get('skillTree', {}).get('trees', [])
    assert len(trees) >= 6, f'Expected the authored branching trees; found {len(trees)}.'
    assert all(len(tree['nodes']) >= 6 for tree in trees), 'Every roster tree should expose six nodes.'
    page.locator('#open-skill-tree').click()
    wait(page, "document.querySelector('#skill-tree-dialog')?.open===true")
    page.locator('#skill-tree-crawler').select_option('crawler.carl')
    tree_id = 'crawler.carl'
    tree = next(t for t in view(page)['skillTree']['trees'] if t['rosterId'] == tree_id)
    assert page.locator('[data-skill-node]').count() == len(tree['nodes'])
    assert page.locator('.skill-node.locked').count() > 0, 'The graph should expose locked nodes and their requirements.'
    locked = next(n for n in tree['nodes'] if not n['enabled'] and not n['unlocked'])
    page.locator(f"[data-skill-node='{locked['id']}']").click()
    assert locked['disabledReason'] in page.locator('#skill-node-details').inner_text(), 'Locked node must explain its prerequisite, level, or point cost.'
    assert page.locator('#preview-skill-node').is_disabled(), 'A locked node must not offer a preview action.'

    available = next((n for n in tree['nodes'] if n['enabled'] and not n['unlocked']), None)
    assert available, f'{tree_id} has no first purchase at current party level.'
    page.locator(f"[data-skill-node='{available['id']}']").click()
    before = save(page)
    page.locator('#preview-skill-node').click()
    wait(page, "window.dungeon.getView().skillTree.forecast!==null")
    forecast = view(page)['skillTree']['forecast']
    assert forecast['nodeId'] == available['id']
    page.screenshot(path=str(output / 'skill-tree-forecast.png'), full_page=True)
    page.locator('#cancel-skill-node').click()
    wait(page, 'window.dungeon.getView().skillTree.forecast===null')
    assert save(page).get('skillTree') == before.get('skillTree'), 'Canceling a tree preview changed persistent unlocks.'

    page.locator(f"[data-skill-node='{available['id']}']").click()
    page.locator('#preview-skill-node').click()
    page.locator('#confirm-skill-node').click()
    wait(page, f"window.dungeon.getView().skillTree.trees.find(t=>t.rosterId==={json.dumps(tree_id)}).nodes.find(n=>n.id==={json.dumps(available['id'])}).unlocked")
    committed = save(page)
    assert available['id'] in committed.get('skillTree', {}).get('unlockedIds', [])
    updated_tree = next(t for t in view(page)['skillTree']['trees'] if t['rosterId'] == tree_id)
    cost_locked = next((n for n in updated_tree['nodes'] if not n['unlocked'] and 'Not enough unspent skill points' in n['disabledReason']), None)
    assert cost_locked, 'After spending the earned point, another node must show its point-cost restriction.'
    page.locator(f"[data-skill-node='{cost_locked['id']}']").click()
    assert 'Not enough unspent skill points' in page.locator('#skill-node-details').inner_text()
    page.screenshot(path=str(output / 'skill-tree-cost-locked.png'), full_page=True)
    page.screenshot(path=str(output / 'skill-tree-committed.png'), full_page=True)

    # Reload in the same isolated browser context and verify the unlock remains.
    page.reload(wait_until='domcontentloaded')
    wait(page, 'window.dungeon && window.dungeon.getView().screen')
    assert available['id'] in save(page).get('skillTree', {}).get('unlockedIds', []), 'Confirmed tree node did not survive reload.'
    page.locator('#open-skill-tree').click()
    wait(page, "document.querySelector('#skill-tree-dialog')?.open===true")
    page.locator('#skill-tree-crawler').select_option(tree_id)
    tree_after_reload = next(t for t in view(page)['skillTree']['trees'] if t['rosterId'] == tree_id)
    node = next(n for n in tree_after_reload['nodes'] if n['id'] == available['id'])
    assert page.locator(f"[data-skill-node='{available['id']}']").get_attribute('class').find('owned') >= 0
    assert node['unlocked']
    page.locator('#done-skill-tree').click()

    # Seed a bounded level-4 campaign save fixture so the full Carl branch can
    # be purchased with real preview/confirm controls and its capstone can be
    # exercised against a real legal enemy target. XP is normally earned in
    # battle; this fixture isolates the unlock and targeting path.
    campaign_baseline = save(page)
    level_fixture = json.loads(json.dumps(campaign_baseline))
    # Two real campaign encounters are represented by the matching index and
    # XP total; roster caps are advanced using the authored per-level growth.
    level_fixture['xp'] = 75
    level_fixture['encounterIndex'] = 2
    for member in level_fixture['roster']:
        member['hp'] += 6
        member['maxHp'] += 6
        member['energy'] += 2
        member['maxEnergy'] += 2
        member['level'] = 3
    page.evaluate('s=>window.dungeon.loadSave(JSON.stringify(s))', level_fixture)
    wait(page, 'window.dungeon.getView().progression.level>=3')
    page.locator('#open-skill-tree').click()
    wait(page, "document.querySelector('#skill-tree-dialog')?.open===true")
    page.locator('#skill-tree-crawler').select_option('crawler.carl')
    tree_now = next(t for t in view(page)['skillTree']['trees'] if t['rosterId'] == 'crawler.carl')
    capstone = next(n for n in tree_now['nodes'] if n['level'] == 3 and n['abilityIds'])
    page.locator(f"[data-skill-node='{capstone['id']}']").click()
    assert 'Learn prerequisite skills first' in page.locator('#skill-node-details').inner_text(), 'Capstone does not explain its missing prerequisite.'
    assert page.locator('#preview-skill-node').is_disabled()
    page.screenshot(path=str(output / 'skill-tree-prerequisite-locked.png'), full_page=True)

    def learn(node_id):
        page.locator(f"[data-skill-node='{node_id}']").click()
        preview = page.locator('#preview-skill-node')
        assert preview.is_enabled(), f'Prerequisite node {node_id} is disabled unexpectedly.'
        preview.click()
        wait(page, 'window.dungeon.getView().skillTree.forecast!==null')
        page.locator('#confirm-skill-node').click()
        wait(page, f"window.dungeon.getView().skillTree.trees.find(t=>t.rosterId==='crawler.carl').nodes.find(n=>n.id==={json.dumps(node_id)}).unlocked")

    ancestors = []
    pending = list(capstone['prerequisiteIds'])
    while pending:
        prerequisite_id = pending.pop(0)
        if prerequisite_id in ancestors:
            continue
        ancestors.append(prerequisite_id)
        prerequisite = next(n for n in tree_now['nodes'] if n['id'] == prerequisite_id)
        pending.extend(prerequisite['prerequisiteIds'])
    for node_id in reversed(ancestors):
        if node_id not in save(page).get('skillTree', {}).get('unlockedIds', []):
            learn(node_id)
    learn(capstone['id'])

    page.locator('#done-skill-tree').click()
    saved_with_tree = save(page)

    enter_campaign_encounter(page)
    granted_id = capstone['abilityIds'][0]
    current_battle = view(page)
    ability = next((a for a in current_battle['abilities'] if a['id'] == granted_id and a.get('target') == 'enemy'), None)
    assert ability, f'Learned ability {granted_id} did not appear with a legal enemy target in battle.'
    if not ability.get('targetIds'):
        enemies = [u for u in current_battle['units'] if u['team'] == 'enemy' and u['hp'] > 0]
        reachable = current_battle.get('reachable', [])
        adjacent_moves = [cell for cell in reachable if any(abs(cell['x']-enemy['x'])+abs(cell['y']-enemy['y']) <= 1 for enemy in enemies)]
        assert adjacent_moves, f'{granted_id} has no legal enemy target and the campaign map has no reachable adjacent cell.'
        destination = min(adjacent_moves, key=lambda cell: min(abs(cell['x']-enemy['x'])+abs(cell['y']-enemy['y']) for enemy in enemies))
        cell_click(page, destination['x'], destination['y'])
        wait(page, "window.dungeon.getView().units.find(u=>u.id==='crawler.carl').moved")
        current_battle = view(page)
        ability = next(a for a in current_battle['abilities'] if a['id'] == granted_id)
    assert ability.get('targetIds'), f'{granted_id} still has no legal enemy target after the real move.'
    target_id = ability['targetIds'][0]
    target = next(u for u in view(page)['units'] if u['id'] == target_id)
    target_hp = target['hp']
    actor_id = view(page)['selectedUnitId']
    page.locator('#open-actions').click()
    page.locator(f"[data-modal-ability='{granted_id}']").click()
    cell_click(page, target['x'], target['y'])
    wait(page, 'window.dungeon.getView().canConfirm')
    assert view(page)['forecast'], 'The learned ability did not produce a target forecast.'
    page.screenshot(path=str(output / 'skill-tree-granted-ability-target.png'), full_page=True)
    page.locator('#detail-confirm-forecast').click()
    wait(page, f"window.dungeon.getView().units.find(u=>u.id==={json.dumps(target_id)}).hp < {target_hp} || window.dungeon.getView().screen==='victory'")
    assert not view(page)['canAct'], 'Confirming the learned action did not spend the crawler’s action.'
    page.screenshot(path=str(output / 'skill-tree-granted-ability-committed.png'), full_page=True)

    # Restore the fixture campaign through the real save-import API so the
    # remaining mission assertions compare its exact post-tree checkpoint.
    page.evaluate('s=>window.dungeon.loadSave(JSON.stringify(s))', saved_with_tree)
    wait(page, "window.dungeon.getView().screen==='camp'")
    assert save(page) == saved_with_tree, 'Restoring the test campaign lost its confirmed skill tree.'


def enter_campaign_encounter(page):
    page.locator('#quick-enter').click()
    wait(page, "window.dungeon.getView().screen==='explore'")
    for _ in range(100):
        current = view(page)
        exploration = current['exploration']
        door = next((point for point in exploration['points'] if point['kind'] == 'encounter' and point['canInteract']), None)
        if door:
            page.locator(f"[data-explore-interact='{door['id']}']").click()
            wait(page, "window.dungeon.getView().screen==='battle'")
            return
        frontier = [tile for tile in exploration['tiles'] if tile['reachable'] and not tile['revealed']]
        if frontier:
            tile = min(frontier, key=lambda cell: (cell['y'], cell['x']))
        else:
            encounter = next(point for point in exploration['points'] if point['kind'] == 'encounter')
            tile = min((cell for cell in exploration['tiles'] if cell['reachable']), key=lambda cell: abs(cell['x']-encounter['x'])+abs(cell['y']-encounter['y']))
        cell_click(page, tile['x'], tile['y'])
        wait(page, '([x,y])=>{const m=window.dungeon.getView().exploration;return m.x===x&&m.y===y}', timeout=5000, arg=[tile['x'], tile['y']])
    raise AssertionError('Could not reach the campaign encounter door.')


def test_missions(page, output):
    expected = {
        'expedition.sewers': ((12, 9), {'sludge'}),
        'expedition.foundry': ((13, 10), {'cinder'}),
        'expedition.crypt': ((12, 10), {'frost'}),
        'expedition.overgrowth': ((14, 10), {'spore'}),
        'expedition.security': ((14, 11), {'sentry'}),
        'expedition.gauntlet': ((15, 11), {'mauler'}),
    }
    campaign_before = save(page)
    campaign_level = view(page)['progression']['level']
    options = view(page).get('expeditions', [])
    ids = {item['id'] for item in options}
    assert ids == set(expected), f'Expected six distinct expeditions, got {sorted(ids)}.'
    page.locator('#open-missions').click()
    wait(page, "document.querySelector('#mission-dialog')?.open===true")
    page.set_viewport_size({'width': 390, 'height': 844})
    assert_dialog_fits(page, '#mission-dialog', 390, 844)
    page.screenshot(path=str(output / 'mission-board-phone.png'), full_page=True)
    page.set_viewport_size({'width': 844, 'height': 390})
    assert_dialog_fits(page, '#mission-dialog', 844, 390)
    page.screenshot(path=str(output / 'mission-board-landscape.png'), full_page=True)
    page.set_viewport_size({'width': 1366, 'height': 768})
    page.locator('#done-missions').click()
    identities = set()
    mission_enemy_art = {}
    for expedition_id in sorted(expected):
        if not page.locator('#mission-dialog').count() or not page.locator('#mission-dialog').evaluate('d=>d.open'):
            page.locator('#open-missions').click()
            wait(page, "document.querySelector('#mission-dialog')?.open===true")
        page.locator(f"[data-mission-briefing='{expedition_id}']").click()
        assert page.locator('#mission-briefing').is_visible()
        page.screenshot(path=str(output / f'{expedition_id}-briefing.png'), full_page=True)
        page.locator('#start-mission').click()
        wait(page, f"window.dungeon.getView().expedition?.id==={json.dumps(expedition_id)}")
        current = view(page)
        assert current['screen'] == 'battle'
        assert current['expedition'].get('decorations'), f'{expedition_id} should show authored room features.'
        expected_size, expected_art = expected[expedition_id]
        assert (current['width'], current['height']) == expected_size, f'{expedition_id} loaded the wrong map size: {(current["width"], current["height"])}.'
        identity = (
            current['width'], current['height'],
            tuple(sorted((t['x'], t['y'], t.get('blocked'), tuple(t.get('tags', []))) for t in current['tiles'])),
            tuple(sorted((d.get('assetId'), d.get('x'), d.get('y')) for d in current['expedition']['decorations'])),
        )
        identities.add(identity)
        enemies = [u for u in current['units'] if u['team'] == 'enemy']
        assert enemies, f'{expedition_id} spawned no enemies.'
        arts = {u.get('artId') for u in enemies}
        assert None not in arts, f'{expedition_id} enemies are missing art IDs.'
        assert expected_art <= arts, f'{expedition_id} is missing its signature enemy art {expected_art}: {arts}.'
        mission_enemy_art[expedition_id] = sorted(arts)
        # Confirm the real renderer drew a nonempty, varied battlefield frame.
        page.wait_for_function("document.querySelector('#battlefield')?.width > 0", timeout=15000)
        canvas_pixels = page.locator('#battlefield').evaluate("c=>{const x=c.getContext('2d');const d=x.getImageData(0,0,c.width,c.height).data;let opaque=0,colors=new Set();for(let i=3;i<d.length;i+=4){if(d[i]>0){opaque++;if(colors.size<64)colors.add(`${d[i-3]},${d[i-2]},${d[i-1]}`)}}return {opaque,colors:colors.size,width:c.width,height:c.height}}")
        assert canvas_pixels['opaque'] > 500 and canvas_pixels['colors'] > 12, f'{expedition_id} battlefield was not visibly rendered: {canvas_pixels}'
        page.screenshot(path=str(output / f'{expedition_id}-battle.png'), full_page=True)

        # Observe actual renderer events while a legal enemy phase runs. End each
        # ready crawler's turn through the confirmation dialog, without forcing
        # any engine state through the debug API.
        page.locator('#battlefield').evaluate("c=>{window.__expansionEvents=[];for(const name of ['battleevent','battlephase'])c.addEventListener(name,e=>window.__expansionEvents.push({name,detail:e.detail}))}")
        before_round = current['round']
        deadline = 0
        while view(page)['phase'] == 'player' and deadline < 4:
            button = page.locator('#end-turn')
            assert button.is_enabled(), f'{expedition_id}: selected party actor cannot end their turn.'
            button.click()
            wait(page, "document.querySelector('#end-turn-dialog')?.open===true")
            page.locator('#confirm-end-turn').click()
            wait(page, "!document.querySelector('#end-turn-dialog')?.open")
            deadline += 1
            if view(page)['phase'] == 'enemy':
                break
        wait(page, f"window.dungeon.getView().round > {before_round} && window.dungeon.getView().phase==='player'", timeout=20000)
        wait(page, "!document.body.classList.contains('enemy-playback')", timeout=20000)
        enemy_events = page.evaluate("window.__expansionEvents.filter(e=>e.name==='battleevent'&&e.detail?.actor?.team==='enemy').map(e=>e.detail.event.type)")
        assert any(kind in ('move', 'attack') for kind in enemy_events), f'{expedition_id} enemy phase produced no visible enemy movement or attack: {enemy_events}'
        page.screenshot(path=str(output / f'{expedition_id}-enemy-phase.png'), full_page=True)
        assert page.locator('#battlefield').count() == 1
        # Each mission is an isolated run; return through its public objective UI.
        page.locator('#expedition-objective-button').click()
        wait(page, "document.querySelector('#expedition-dialog')?.open===true")
        page.locator('#return-expedition').click()
        wait(page, "window.dungeon.getView().screen==='camp'")
        assert save(page) == campaign_before, f'{expedition_id} did not restore the exact campaign save.'
        assert view(page)['progression']['level'] == campaign_level
    assert len(identities) == 6, f'Expedition rooms are not all distinct: {identities}'
    assert len({tuple(v) for v in mission_enemy_art.values()}) >= 4, f'Enemy art variety was not preserved: {mission_enemy_art}'


def test_atlas(playwright, output):
    browser = playwright.chromium.launch(executable_path=args.browser, headless=True, args=['--no-sandbox', '--disable-cache'])
    page = browser.new_page(viewport={'width': 1366, 'height': 768}, device_scale_factor=1)
    errors = []
    page.on('pageerror', lambda error: errors.append(str(error)))
    response = page.goto(args.url.rstrip('/') + '/menu-atlas.html', wait_until='domcontentloaded', timeout=60000)
    assert response and response.ok, f'menu-atlas.html did not load: {response.status if response else None}'
    page.wait_for_load_state('networkidle')
    assert page.locator('.menu-section').count() == 6, 'Atlas should render six menu concepts.'
    images = page.locator('.menu-section .sheet-frame img')
    assert images.count() == 6, f'Expected six concept illustrations, found {images.count()} images.'
    images.evaluate_all("els=>els.forEach(i=>i.loading='eager')")
    for image in images.all():
        image.scroll_into_view_if_needed()
        image.evaluate("i=>i.decode()")
    image_status = images.evaluate_all("els=>els.map(i=>({src:i.currentSrc||i.src,loaded:i.complete&&i.naturalWidth>0,width:i.naturalWidth}))")
    assert all(item['loaded'] for item in image_status), f'Atlas image failed to load: {image_status}'
    page.screenshot(path=str(output / 'menu-atlas-desktop.png'), full_page=True)
    components = page.locator('.component')
    assert components.count() == 30, f'Expected thirty interactive component cards, got {components.count()} cards.'
    state = page.locator('#state-mission-tile')
    before_state = state.input_value()
    page.locator('#component-mission-tile [data-cycle]').click()
    assert state.input_value() != before_state, 'Component preview did not respond to its local state control.'
    page.locator('#component-mission-tile .reset-demo').click()
    assert state.input_value() == before_state, 'Reset did not restore the component preview state.'
    downloads = page.locator('.intro a[download]')
    assert downloads.count() == 1, 'Atlas should expose the component inventory download.'
    with page.expect_download() as download_info:
        downloads.first.click()
    download = download_info.value
    assert download.suggested_filename, 'Download control did not trigger a named file.'
    page.set_viewport_size({'width': 390, 'height': 844})
    page.screenshot(path=str(output / 'menu-atlas-phone.png'), full_page=True)
    assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), 'Atlas overflows horizontally on a phone viewport.'
    assert not errors, f'Atlas raised JavaScript errors: {errors}'
    browser.close()


def main():
    output = Path(args.screenshots)
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.browser, headless=True, args=['--no-sandbox', '--disable-cache'])
        context = browser.new_context(viewport={'width': 1366, 'height': 768}, device_scale_factor=1)
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(args.url, wait_until='domcontentloaded', timeout=60000)
        dismiss_intro(page)
        test_skill_tree(page, output)
        # Validate the responsive tree dialog at phone and landscape sizes.
        page.set_viewport_size({'width': 390, 'height': 844})
        page.locator('#open-skill-tree').click()
        wait(page, "document.querySelector('#skill-tree-dialog')?.open===true")
        assert_dialog_fits(page, '#skill-tree-dialog', 390, 844)
        page.screenshot(path=str(output / 'skill-tree-phone.png'), full_page=True)
        page.keyboard.press('Escape')
        wait(page, "!document.querySelector('#skill-tree-dialog')?.open")
        page.set_viewport_size({'width': 844, 'height': 390})
        page.locator('#open-skill-tree').click()
        wait(page, "document.querySelector('#skill-tree-dialog')?.open===true")
        assert_dialog_fits(page, '#skill-tree-dialog', 844, 390)
        page.screenshot(path=str(output / 'skill-tree-landscape.png'), full_page=True)
        page.keyboard.press('Escape')
        wait(page, "!document.querySelector('#skill-tree-dialog')?.open")
        page.set_viewport_size({'width': 1366, 'height': 768})
        test_missions(page, output)
        assert not errors, f'Expansion gameplay raised JavaScript errors: {errors}'
        browser.close()
        test_atlas(playwright, output)
    print(json.dumps({'screenshots': str(output), 'result': 'skill-tree and six-expedition browser assertions passed'}))


if __name__ == '__main__':
    main()
