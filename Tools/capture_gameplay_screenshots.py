"""Capture the real camp, continuous floor, gear and map across four viewport sizes.

Requires Playwright, Chrome and hydrated native assets. Never substitutes a runtime
or edits rendered game state; departure uses the actual safe-room station.
"""
import argparse
import json
from pathlib import Path

from playwright.sync_api import sync_playwright
from playtest_generated_adventure import view
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
            assert page.locator('.game-toast.toast-error').count() == 0, 'Game error toast during capture'
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
        from playtest_continuous_floor import launch_floor
        sizes = [(1440,1000),(390,844),(320,740),(844,390)]
        for width,height in sizes:
            page.set_viewport_size({'width':width,'height':height})
            capture(f'hub-{width}x{height}.png', 'Walkable safe room before departure.')
        page.set_viewport_size({'width':1440,'height':1000})
        state = launch_floor(page, args.seed)
        assert state['generatedDungeon']['floorPlan']
        for width,height in sizes:
            page.set_viewport_size({'width':width,'height':height})
            capture(f'field-{width}x{height}.png', 'Continuous 40x32 floor, untouched entrance.', native=True)
            page.locator('#field-menu-button').click()
            page.locator('[data-field-action=equipment]').click()
            page.locator('#equipment-dialog').wait_for(state='visible')
            capture(f'gear-{width}x{height}.png', 'Actual expedition equipment dialog.', native=True)
            page.locator('#done-loadout').click()
            page.locator('#field-map-button').click()
            page.locator('#field-map').wait_for(state='visible')
            capture(f'map-{width}x{height}.png', 'Actual discovered-floor map.', native=True)
            page.locator('#field-map [data-close-field]').click()
        assert not errors, errors
        summary = {'seed': args.seed, 'runtime': 'actual C# WASM', 'layout': 'chambers',
                   'captures': captures, 'nativeArt': page.evaluate('window.dungeon.scene.getNativeArtStatus()'), 'errors': errors}
        (output / 'capture-summary.json').write_text(json.dumps(summary, indent=2) + '\n')
        browser.close()
    print(json.dumps({'output': str(output), 'files': [capture['file'] for capture in captures], 'errors': errors}))


if __name__ == '__main__':
    main()
