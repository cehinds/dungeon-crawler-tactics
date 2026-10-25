"""Capture authentic generated-adventure UI from a freshly published C# WASM game.

Requires Playwright, Chrome and hydrated native assets. Never substitutes a runtime
or edits rendered game state; combat is reached by actual exploration commands.
"""
import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright
from playtest_generated_adventure import distances, position, route, view, walk
from playtest_procedural_maps import ready_runtime


def settle(page, native=False):
    ready_runtime(page, native=native)
    page.evaluate("document.fonts.ready")
    page.wait_for_function("Array.from(document.images).every(i => i.complete && i.naturalWidth > 0)", timeout=60000)
    page.wait_for_timeout(650)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://localhost:8765')
    parser.add_argument('--browser', default='/usr/bin/google-chrome')
    parser.add_argument('--output', default='/tmp/game-screenshots')
    parser.add_argument('--seed', default='lantern-vault-01')
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    captures = []
    errors = []
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(executable_path=args.browser, args=['--no-sandbox'])
        context = browser.new_context(viewport={'width': 1440, 'height': 1000}, device_scale_factor=1)
        context.add_init_script("""if (!sessionStorage.getItem('qa.capture.initialized')) {
          localStorage.clear(); sessionStorage.setItem('qa.capture.initialized', '1');
          localStorage.setItem('dct.help.seen', '1');
        }""")
        page = context.new_page()
        page.on('pageerror', lambda error: errors.append(str(error)))

        def capture(filename, note, native=False):
            settle(page, native=native)
            assert not errors, errors
            state = view(page)
            page.screenshot(path=str(output / filename), full_page=False, animations='disabled')
            captures.append({'file': filename, 'screen': state['screen'], 'viewport': page.viewport_size,
                             'note': note, 'partyPosition': state.get('generatedDungeon')})

        page.goto(args.url.rstrip('/') + '/index.html')
        ready_runtime(page)
        for selector in ['#begin-button', '[data-close="help-dialog"]']:
            button = page.locator(selector).last
            if button.is_visible():
                button.click()
        page.locator('#quick-enter').click()
        page.locator('#generated-adventure-dialog').wait_for(state='visible')
        page.locator('#adventure-seed').fill(args.seed)
        page.locator('#adventure-layout').select_option('chambers')
        page.locator('#adventure-style').select_option('pocket-dungeon')
        page.locator('#adventure-location').select_option('starter-dungeon')
        capture('01-menu.png', 'Generated adventure dialog in the actual camp.')
        page.locator('#begin-generated-adventure').click()
        page.wait_for_function("""window.dungeon.getView().generatedDungeon ||
          document.querySelector('#generated-adventure-status').textContent.startsWith('Could not')""", timeout=120000)
        state = view(page)
        assert state.get('generatedDungeon'), page.locator('#generated-adventure-status').inner_text()
        assert state['screen'] == 'explore', state.get('message')
        page.locator('#generated-adventure-dialog').wait_for(state='hidden')
        expected = state['customMap']
        assert (expected['width'], expected['height']) == (16, 12)
        assert expected['visuals']['styleId'] == 'pocket-dungeon'
        capture('02-exploration-desktop.png', 'Generated square dungeon; default exploration camera.', native=True)
        page.set_viewport_size({'width': 390, 'height': 844})
        capture('03-exploration-mobile.png', 'Same generated adventure at a mobile viewport.', native=True)
        page.set_viewport_size({'width': 1440, 'height': 1000})
        cells = {(x, y) for y in range(expected['height']) for x in range(expected['width'])}
        cells -= {(tile['x'], tile['y']) for tile in expected['tiles'] if tile.get('blocked')}
        enemies = {(enemy['x'], enemy['y']) for enemy in expected['enemies']}
        reachable = distances(position(page), cells)
        targets = enemies & reachable.keys()
        assert targets, 'No reachable generated enemy'
        target = min(targets, key=lambda enemy: reachable[enemy])
        state = walk(page, route(position(page), target, cells - (enemies - {target})))
        assert state['screen'] == 'battle', 'Walking to an enemy failed to enter real combat'
        assert state['customMap'] == expected, 'Combat replaced the generated map'
        settle(page, native=True)
        page.locator('#center-map').click()
        page.locator('#zoom-in').click()
        page.locator('#zoom-in').click()
        capture('04-combat-desktop.png', 'Real encounter reached by C# explore_step movement; centered on selected crawler.', native=True)
        if page.locator('#open-actions').is_visible() and page.locator('#open-actions').is_enabled():
            page.locator('#open-actions').click()
            page.locator('#action-dialog').wait_for(state='visible')
            capture('05-actions.png', 'Actual action book for the selected crawler.', native=True)
        assert not errors, errors
        summary = {'seed': args.seed, 'runtime': 'actual C# WASM', 'layout': 'chambers',
                   'style': 'pocket-dungeon', 'location': 'starter-dungeon', 'captures': captures,
                   'nativeArt': page.evaluate('window.dungeon.scene.getNativeArtStatus()'), 'errors': errors}
        (output / 'capture-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
        browser.close()
    print(json.dumps({'output': str(output), 'files': [capture['file'] for capture in captures], 'errors': errors}))


if __name__ == '__main__':
    main()
