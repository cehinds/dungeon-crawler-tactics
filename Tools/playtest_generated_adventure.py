"""Exercise generated exploration and hold controls against a freshly published C# WASM build.

Requires Playwright, Chrome, and hydrated native art. Old WASM lacking import_generated
fails explicitly; this test never substitutes a mocked runtime.
"""
import argparse
from collections import deque

from playwright.sync_api import sync_playwright
from playtest_procedural_maps import ready_runtime, canonical_map

SAVE_KEY = "dungeon-crawler-tactics.save.v1"
DIRECTIONS = [(0, -1, 'ArrowUp', 'north'), (1, 0, 'd', 'east'),
              (0, 1, 'ArrowDown', 'south'), (-1, 0, 'a', 'west')]


def view(page):
    return page.evaluate('window.dungeon.getView()')


def position(page):
    state = view(page)['generatedDungeon']
    return state['x'], state['y']


def command(page, name, **args):
    return page.evaluate('async ({name,args})=>{await window.dungeon.command(name,args);return window.dungeon.getView()}',
                         {'name': name, 'args': args})


def distances(start, cells):
    found = {start: 0}
    queue = deque([start])
    while queue:
        x, y = queue.popleft()
        for dx, dy, *_ in DIRECTIONS:
            cell = x + dx, y + dy
            if cell in cells and cell not in found:
                found[cell] = found[(x, y)] + 1
                queue.append(cell)
    return found


def route(start, goal, cells):
    previous = {start: None}
    queue = deque([start])
    while queue:
        current = queue.popleft()
        if current == goal:
            result = []
            while previous[current] is not None:
                result.append(current)
                current = previous[current]
            return list(reversed(result))
        for dx, dy, *_ in DIRECTIONS:
            cell = current[0] + dx, current[1] + dy
            if cell in cells and cell not in previous:
                previous[cell] = current
                queue.append(cell)
    raise AssertionError(f'No route from {start} to {goal}')


def walk(page, path):
    for x, y in path:
        before = position(page)
        state = command(page, 'explore_step', x=x-before[0], y=y-before[1])
        assert position(page) == (x, y), state.get('message')
        if state['screen'] == 'battle':
            return state
    return view(page)


def restore(page, serialized):
    page.evaluate('save=>window.dungeon.loadSave(save)', serialized)
    ready_runtime(page, native=True)


def assert_scene(page, expected):
    ready_runtime(page, native=True)
    state = view(page)
    assert canonical_map(state['customMap']) == canonical_map(expected)
    assert page.evaluate('window.dungeon.scene.getNativeVisuals()') == expected['visuals']
    assert page.evaluate('window.dungeon.scene.getNativeArtStatus().projection') == 'orthogonal'
    assert (state['width'], state['height']) == (expected['width'], expected['height'])


def reload_roundtrip(page, expected):
    saved = page.evaluate('window.dungeon.getSave().then(JSON.parse)')
    page.evaluate('({key,save})=>localStorage.setItem(key,JSON.stringify(save))', {'key': SAVE_KEY, 'save': saved})
    page.reload()
    ready_runtime(page, native=True)
    actual = page.evaluate('window.dungeon.getSave().then(JSON.parse)')
    for field in ['screen', 'generatedDungeon', 'units', 'tiles', 'xp', 'encounterIndex']:
        assert actual[field] == saved[field], f'{field} changed during reload'
    assert_scene(page, expected)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://localhost:8765')
    parser.add_argument('--browser', default='/usr/bin/google-chrome')
    args = parser.parse_args()
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.browser, args=['--no-sandbox'])
        context = browser.new_context(viewport={'width': 1440, 'height': 1000})
        # Each context is isolated. Clear only its first document, preserving reload saves.
        context.add_init_script("""if(!sessionStorage.getItem('qa.generated.initialized')){
          localStorage.clear();sessionStorage.setItem('qa.generated.initialized','1');
          localStorage.setItem('dct.help.seen','1');
        }""")
        page = context.new_page()
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(args.url.rstrip('/') + '/index.html')
        ready_runtime(page)
        # Close first-run welcome/help using their real UI.
        for selector in ['#begin-button', '[data-close="help-dialog"]']:
            button = page.locator(selector).last
            if button.is_visible():
                button.click()
        page.locator('#quick-enter').click()
        page.locator('#generated-adventure-dialog').wait_for(state='visible')
        page.locator('#adventure-seed').fill('generated-adventure-browser-qa')
        page.locator('#adventure-layout').select_option('hall')
        page.locator('#begin-generated-adventure').click()
        page.wait_for_function("""window.dungeon.getView().generatedDungeon ||
          document.querySelector('#generated-adventure-status').textContent.startsWith('Could not')""", timeout=120000)
        state = view(page)
        assert state.get('generatedDungeon'), page.locator('#generated-adventure-status').inner_text()
        page.locator('#generated-adventure-dialog').wait_for(state='hidden')
        expected = state['customMap']
        assert state['screen'] == 'explore'
        assert_scene(page, expected)
        expected_packet = page.evaluate("""async()=>{const {createGeneratedAdventure}=await import('./generated-adventure.js');
          return createGeneratedAdventure({seed:'generated-adventure-browser-qa',layout:'hall'});} """)
        assert canonical_map(expected) == canonical_map(expected_packet['customMap']), 'UI generated a different scene/map'
        reload_roundtrip(page, expected)
        baseline = page.evaluate('window.dungeon.getSave()')
        open_cells = {(x, y) for y in range(expected['height']) for x in range(expected['width'])}
        open_cells -= {(t['x'], t['y']) for t in expected['tiles'] if t.get('blocked')}
        enemies = {(e['x'], e['y']) for e in expected['enemies']}
        danger = set()
        for enemy in enemies:
            danger.update(cell for cell, cost in distances(enemy, open_cells).items() if cost <= 3)
        safe = open_cells - danger
        start = position(page)
        reachable = distances(start, safe)
        # Find a reachable run with two safe cardinal steps; real controls must repeat.
        runs = [(cell, direction) for cell in reachable for direction in DIRECTIONS
                if all((cell[0]+direction[0]*i, cell[1]+direction[1]*i) in safe for i in (1, 2))]
        assert runs, 'Fixture needs a safe two-cell straight run'
        anchor, direction = min(runs, key=lambda item: reachable[item[0]])
        walk(page, route(start, anchor, safe))
        hold_baseline = page.evaluate('window.dungeon.getSave()')
        dx, dy, key, pad = direction
        # Camera buttons must not strand movement focus outside the map.
        if page.locator('#camera-toggle').count() and not page.locator('#zoom-in').is_visible(): page.locator('#camera-toggle').click()
        page.locator('#zoom-in').click()
        page.keyboard.down(key)
        page.wait_for_function("([x,y])=>{const s=window.dungeon.getView().generatedDungeon;return Math.abs(s.x-x)+Math.abs(s.y-y)>=2}", arg=list(anchor), timeout=10000)
        page.keyboard.up(key)
        page.wait_for_timeout(350)
        stopped = position(page)
        page.wait_for_timeout(500)
        assert position(page) == stopped, 'Keyboard release kept walking'
        assert view(page)['screen'] == 'explore', 'Safe hold unexpectedly entered combat'
        restore(page, hold_baseline)
        # Actual held pointer survives the HUD being rendered after its first step.
        page.locator(f'[data-walk="{pad}"]').scroll_into_view_if_needed()
        box = page.locator(f'[data-walk="{pad}"]').bounding_box()
        page.mouse.move(box['x']+box['width']/2, box['y']+box['height']/2)
        page.mouse.down()
        page.wait_for_function("([x,y])=>{const s=window.dungeon.getView().generatedDungeon;return Math.abs(s.x-x)+Math.abs(s.y-y)>=2}", arg=list(anchor), timeout=10000)
        page.mouse.up()
        page.wait_for_timeout(350)
        stopped = position(page)
        page.wait_for_timeout(500)
        assert position(page) == stopped, 'Pointer release kept walking'
        restore(page, hold_baseline)
        page.locator('#battlefield').focus()
        page.keyboard.down(key)
        page.locator('#save-button').click()
        page.locator('#help-button').click()
        page.locator('#help-dialog').wait_for(state='visible')
        page.wait_for_timeout(350)
        stopped = position(page)
        page.wait_for_timeout(500)
        assert position(page) == stopped, 'Modal allowed held walking'
        page.keyboard.up(key)
        page.locator('[data-close="help-dialog"]').last.click()
        restore(page, baseline)
        page.set_viewport_size({'width':390,'height':844})
        page.wait_for_timeout(200)
        for selector in ['#battlefield', '.walk-pad', '[data-walk="north"]', '[data-walk="south"]']:
            box = page.locator(selector).bounding_box()
            assert box and box['x'] >= 0 and box['y'] >= 0 and box['x'] + box['width'] <= 391 and box['y'] + box['height'] <= 845, (selector, box)
        assert page.locator('#battlefield').bounding_box()['height'] > 100
        page.set_viewport_size({'width':1440,'height':1000})
        wall_runs = [(cell, (dx, dy)) for cell in reachable for dx, dy, *_ in DIRECTIONS
                     if (cell[0]+dx, cell[1]+dy) not in open_cells]
        assert wall_runs, 'Fixture must have a reachable wall'
        cell, (dx, dy) = min(wall_runs, key=lambda item: reachable[item[0]])
        walk(page, route(position(page), cell, safe))
        state = command(page, 'explore_step', x=dx, y=dy)
        assert position(page) == cell and state['screen'] == 'explore', 'Wall accepted movement'
        restore(page, baseline)
        # Approach an enemy using real C# cardinal commands, retaining the exact map.
        start = position(page)
        target = min(enemies, key=lambda enemy: distances(start, open_cells)[enemy])
        path = route(start, target, open_cells - (enemies - {target}))
        previous = start
        for cell in path:
            previous = position(page)
            state = walk(page, [cell])
            if state['screen'] == 'battle':
                break
        assert state['screen'] == 'battle', 'Nearby enemy did not trigger turn-based combat'
        players = [u for u in state['units'] if u['team'] == 'player']
        assert any((u['x'], u['y']) == cell for u in players), 'Party deployment lost the exploration leader anchor'
        assert abs(cell[0]-previous[0])+abs(cell[1]-previous[1]) == 1
        assert_scene(page, expected)
        reload_roundtrip(page, expected)
        assert not errors, errors
        browser.close()
    print('PASS generated UI/map/art, real keyboard and pointer holds, release/modal/wall stops, exploration and battle reload, same-map enemy transition')


if __name__ == '__main__':
    main()
