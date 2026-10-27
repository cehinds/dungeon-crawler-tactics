"""Check Foundry viewport layout, dialogs, settings and downloads in Chromium."""
import argparse
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from playwright.sync_api import sync_playwright


def ready(page):
    page.wait_for_function("!document.querySelector('#play').disabled", timeout=60000)


def visible_in_viewport(page, selector):
    box = page.locator(selector).bounding_box()
    viewport = page.viewport_size
    assert box and box['width'] > 0 and box['height'] > 0, selector
    assert box['x'] >= 0 and box['y'] >= 0, (selector, box)
    assert box['x'] + box['width'] <= viewport['width'] + 1, (selector, box)
    assert box['y'] + box['height'] <= viewport['height'] + 1, (selector, box)


def export_map(page, directory):
    page.locator('#open-export').click()
    with page.expect_download() as download:
        page.locator('#map-json').click()
    path = Path(directory) / 'map.json'
    download.value.save_as(path)
    page.locator('#close-export').click()
    return json.loads(path.read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:8127')
    parser.add_argument('--browser', default='/usr/bin/chromium')
    args = parser.parse_args()
    with sync_playwright() as p, TemporaryDirectory() as temporary:
        browser = p.chromium.launch(executable_path=args.browser, args=['--no-sandbox'])
        page = browser.new_page(viewport={'width': 1440, 'height': 900})
        errors = []
        page.on('pageerror', lambda error: errors.append(str(error)))
        page.goto(args.url.rstrip('/') + '/dungeon-generator.html')
        ready(page)
        assert 'Dungeon Foundry' in page.title()
        initial_map = export_map(page, temporary)
        page.locator('#open-info').click()
        page.locator('#edge-inspector summary').click()
        wall_id = page.evaluate("""async () => {
            const manifest = await fetch('assets/book-tiles/pocket-dungeon/starter-dungeon/manifest.json').then(r=>r.json());
            return manifest.assets.find(asset=>asset.cell===6).id;
        }""")
        page.locator('#edge-asset').select_option(wall_id)
        assert page.locator('#edge-sides [data-side="north"] code').all_text_contents() == ['join.exterior']
        page.locator('#edge-rotation').select_option('1')
        assert page.locator('#edge-sides [data-side="east"] code').all_text_contents() == ['join.exterior']
        assert 'floor edges verified' in page.locator('#edge-check').inner_text()
        page.locator('#close-info').click()
        original_pixels = page.locator('#map').evaluate('canvas=>canvas.toDataURL()')
        page.locator('#open-info').click()
        page.locator('#show-connections').click()
        page.wait_for_function("document.activeElement.id === 'map'")
        assert page.locator('#connection-controls').is_visible()
        assert page.locator('#map').evaluate('canvas=>canvas.toDataURL()') != original_pixels
        # The toolbar inspector must synchronize a map selection even when the
        # previous catalog inspection was a different component and rotation.
        page.locator('#open-info').click()
        assert 'Placed tile' in page.locator('#edge-cell-summary').inner_text()
        assert page.locator('#edge-asset').input_value() != wall_id
        assert page.locator('#edge-rotation').input_value() == '0'
        assert page.locator('#edge-sides .edge-match').count() == 4
        page.keyboard.press('Escape')
        page.locator('#map').focus()
        page.keyboard.press('Enter')
        assert 'Placed tile' in page.locator('#edge-cell-summary').inner_text()
        assert page.locator('#edge-sides .edge-match').count() == 4
        assert page.locator('#edge-rotation').input_value() == '0'
        page.keyboard.press('Escape')
        page.wait_for_function("document.activeElement.id === 'map'")
        # Native dialog.close() queues its close event. Reopening the map
        # inspector before that event arrives must preserve the new opener.
        page.locator('#open-info').click()
        page.evaluate("""() => new Promise(resolve => {
            const dialog = document.querySelector('#info-dialog');
            dialog.addEventListener('close', resolve, {once:true});
            dialog.close();
            const map = document.querySelector('#map');
            map.focus();
            map.dispatchEvent(new KeyboardEvent('keydown', {key:'Enter', bubbles:true}));
        })""")
        assert page.locator('#info-dialog').evaluate('dialog=>dialog.open')
        assert page.evaluate("document.querySelector('#info-dialog').contains(document.activeElement)")
        page.keyboard.press('Escape')
        page.wait_for_function("document.activeElement.id === 'map'")
        # Click an actual floor through every rotated camera; derive projected
        # bounds from the exported scene, independently of the pointer handler.
        for rotation in range(4):
            point = page.evaluate("""async ({map, rotation}) => {
                const {nativeSceneFromVisuals} = await import('./native-map-visuals.js');
                const {visibleSceneCorners} = await import('./generator-art.js');
                const manifest = await fetch(`assets/book-tiles/${map.visuals.styleId}/${map.visuals.kitId}/manifest.json`).then(r=>r.json());
                const art = {manifest, images:new Map(manifest.assets.map(a=>[a.id,{}]))};
                const scene = nativeSceneFromVisuals(map.visuals, art, map.width, map.height, map.tiles);
                const c = Math.round(Math.cos(rotation*Math.PI/2)), s = Math.round(Math.sin(rotation*Math.PI/2));
                const rotate = p => ({x:p.x*c-p.y*s, y:p.x*s+p.y*c});
                const corners = visibleSceneCorners(scene).map(rotate);
                const minX = Math.min(...corners.map(p=>p.x)), maxX = Math.max(...corners.map(p=>p.x));
                const minY = Math.min(...corners.map(p=>p.y)), maxY = Math.max(...corners.map(p=>p.y));
                const bounds = document.querySelector('#map').getBoundingClientRect();
                const scale = Math.min((bounds.width-48)/(maxX-minX),(bounds.height-48)/(maxY-minY),1);
                const floor = scene.floor.toSorted((a,b)=>
                    Math.hypot(a.px-map.width*64,a.py-map.height*64)-Math.hypot(b.px-map.width*64,b.py-map.height*64))[0];
                const p = rotate({x:floor.px,y:floor.py});
                return {x:bounds.x+(bounds.width-(maxX-minX)*scale)/2+(p.x-minX)*scale,
                    y:bounds.y+(bounds.height-(maxY-minY)*scale)/2+(p.y-minY)*scale,
                    column:floor.px/128+1,row:floor.py/128+1};
            }""", {'map': initial_map, 'rotation': rotation})
            page.mouse.click(point['x'], point['y'])
            assert page.locator('#edge-cell-summary').inner_text() == f"Placed tile · column {point['column']}, row {point['row']}"
            assert page.locator('#edge-sides .edge-match').count() == 4
            page.keyboard.press('Escape')
            page.locator('#rotate-right').click()
        page.locator('#hide-connections').click()
        assert not page.locator('#connection-controls').is_visible()
        assert page.locator('#map').evaluate('canvas=>canvas.toDataURL()') == original_pixels
        for width, height in [(1440, 900), (1280, 720), (768, 1024), (390, 844), (360, 640), (844, 390)]:
            page.set_viewport_size({'width': width, 'height': height})
            page.wait_for_function("""() => document.querySelector('#controls').parentElement.id ===
                (matchMedia('(max-width: 760px), (max-height: 500px)').matches ? 'mobile-controls' : 'desktop-controls')""")
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth && document.documentElement.scrollHeight <= innerHeight')
            for selector in ['#map', '#generate', '#play', '#open-export', '#open-info']:
                visible_in_viewport(page, selector)
            assert page.locator('#map').bounding_box()['height'] >= 100
            # Escape returns focus to the trigger and leaves the canvas available.
            for name in ['export', 'info']:
                page.locator(f'#open-{name}').click()
                assert page.locator(f'#{name}-dialog').evaluate('dialog=>dialog.open')
                page.keyboard.press('Escape')
                assert page.evaluate('document.activeElement.id') == f'open-{name}'
            page.locator('#open-info').click()
            page.locator('#show-connections').click()
            page.wait_for_function("document.activeElement.id === 'map'")
            visible_in_viewport(page, '#hide-connections')
            page.keyboard.press('Enter')
            assert page.locator('#edge-sides .edge-match').count() == 4
            page.keyboard.press('Escape')
            page.wait_for_function("document.activeElement.id === 'map'")
            page.keyboard.press('Escape')
            assert not page.locator('#connection-controls').is_visible()

        page.set_viewport_size({'width': 390, 'height': 844})
        page.locator('#open-settings').click()
        page.locator('#advanced-settings summary').click()
        page.locator('#seed').fill('friendly-map')
        page.locator('#width').fill('12')
        page.locator('#height').fill('10')
        assert 'Generate to apply' in page.locator('#settings-status').inner_text()
        assert '16 × 12' in page.locator('#counts').inner_text(), 'Unapplied settings changed the preview'
        page.locator('#apply-settings').click()
        ready(page)
        assert not page.locator('#settings-dialog').evaluate('dialog=>dialog.open')
        assert '12 × 10' in page.locator('#counts').inner_text()
        expected = export_map(page, temporary)
        page.locator('#generate').click()
        ready(page)
        assert export_map(page, temporary) == expected, 'Fixed seed no longer repeats through the new controls'
        page.locator('#open-settings').click()
        page.locator('#fixed-seed').uncheck()
        page.keyboard.press('Escape')
        page.locator('#generate').click()
        ready(page)
        assert export_map(page, temporary) != expected
        # A loading error must be visible inside the phone dialog, not behind it.
        page.locator('#open-settings').click()
        unavailable = '**/ink-and-lanterns/starter-dungeon/manifest.json'
        page.route(unavailable, lambda route: route.fulfill(status=503, body='Unavailable'))
        page.locator('#art-style').select_option('ink-and-lanterns')
        page.locator('#settings-dialog .dialog-error').wait_for()
        assert page.locator('#play').is_disabled()
        page.unroute(unavailable)
        page.locator('#art-style').select_option('pocket-dungeon')
        ready(page)
        assert page.locator('#settings-dialog .dialog-error').count() == 0
        page.locator('#close-settings').click()
        page.locator('#play').click()
        assert page.locator('#play-dialog').evaluate('dialog=>dialog.open')
        page.locator('#play-dialog button[value="cancel"]').click()
        assert page.url.endswith('/dungeon-generator.html')
        page.locator('#open-settings').click()
        page.set_viewport_size({'width': 1280, 'height': 720})
        page.wait_for_function("document.querySelector('#controls').parentElement.id === 'desktop-controls'")
        assert not page.locator('#settings-dialog').evaluate('dialog=>dialog.open')
        page.locator('#fit').click()
        page.locator('#map').hover()
        page.mouse.wheel(0, -100)
        page.wait_for_function("document.querySelector('#map').classList.contains('zoomed')")
        assert not errors, errors
        browser.close()
    print('PASS six viewport layouts, visible primary actions, keyboard dialogs, phone settings, fixed/new generation, export, play cancellation, resize, wheel zoom, connection overlay and placed-tile picking across four rotations.')


if __name__ == '__main__':
    main()
