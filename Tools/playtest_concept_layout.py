"""Verify generated prop collision through browser keyboard input on two seeded worlds."""
import argparse
import json
from collections import deque
from pathlib import Path
from urllib.parse import urlsplit, urlunsplit, parse_qsl, urlencode
from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument('--url', default='http://127.0.0.1:8773')
parser.add_argument('--browser', default='/usr/bin/chromium')
parser.add_argument('--output', type=Path, default=Path('/tmp/dct-concept-qa'))
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)

def seeded_url(seed):
    parts = urlsplit(args.url)
    query = dict(parse_qsl(parts.query)); query['seed'] = str(seed)
    return urlunsplit(parts._replace(query=urlencode(query)))

with sync_playwright() as p:
    browser = p.chromium.launch(executable_path=args.browser, headless=True, args=['--no-sandbox'])
    signatures = []
    reports = []
    for seed in (1337, 42):
        page = browser.new_page(viewport={'width': 1440, 'height': 1000})
        errors = []
        page.on('pageerror', lambda e: errors.append(str(e)))
        page.goto(seeded_url(seed))
        page.wait_for_function('window.rpgView?.world?.props?.length > 0')
        page.wait_for_timeout(1000)
        def view(): return page.evaluate('window.rpgView')
        def key(k):
            page.keyboard.down(k); page.wait_for_timeout(25)
            page.keyboard.up(k); page.wait_for_timeout(190)
        state = view(); world = state['world']
        assert state['seed'] == seed, f"URL seed ignored: {state['seed']} != {seed}"
        signatures.append(json.dumps({'rooms': world['rooms'], 'props': world['props']}, sort_keys=True))
        start = (state['x'], state['y'])
        previous = {start: None}; queue = deque([start])
        while queue:
            x, y = queue.popleft()
            for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                n = (x + dx, y + dy)
                if 0 <= n[0] < world['width'] and 0 <= n[1] < world['height'] and n not in previous and world['tiles'][n[1] * world['width'] + n[0]] == '.':
                    previous[n] = (x, y); queue.append(n)
        def walk(goal):
            state = view(); origin = (state['x'], state['y'])
            # Recompute the route from the current position through the same static floor.
            todo = deque([origin]); prev = {origin: None}
            while todo and goal not in prev:
                x, y = todo.popleft()
                for dx, dy in ((1, 0), (-1, 0), (0, 1), (0, -1)):
                    n = (x + dx, y + dy)
                    if n in previous and n not in prev: prev[n] = (x, y); todo.append(n)
            assert goal in prev
            path = []; step = goal
            while step != origin: path.append(step); step = prev[step]
            for x, y in reversed(path):
                state = view()
                key('ArrowRight' if x > state['x'] else 'ArrowLeft' if x < state['x'] else 'ArrowDown' if y > state['y'] else 'ArrowUp')
                assert (view()['x'], view()['y']) == (x, y), 'Keyboard route diverged'
        collision = None
        for prop in world['props']:
            if not prop.get('blocksMovement', True): continue
            for x in range(prop['x'], prop['x'] + prop['width']):
                for y in range(prop['y'], prop['y'] + prop['height']):
                    assert world['tiles'][y * world['width'] + x] == '#'
                    for dx, dy, k in ((-1, 0, 'ArrowRight'), (1, 0, 'ArrowLeft'), (0, -1, 'ArrowDown'), (0, 1, 'ArrowUp')):
                        adjacent = (x + dx, y + dy)
                        if adjacent in previous: collision = (prop['id'], adjacent, k); break
                    if collision: break
                if collision: break
            if collision: break
        assert collision, 'No accessible solid prop edge'
        prop_id, adjacent, direction = collision
        walk(adjacent); key(direction)
        assert (view()['x'], view()['y']) == adjacent, 'Solid prop allowed keyboard movement'
        page.screenshot(path=str(args.output / f'seed-{seed}-prop-collision.png'))
        for room_id in ('tutorial-guildhall', 'tally-safe-room'):
            room = next((r for r in world['rooms'] if r['id'] == room_id), None)
            if room:
                cells = [xy for xy in previous if room['x'] <= xy[0] < room['x'] + room['width'] and room['y'] <= xy[1] < room['y'] + room['height']]
                if cells:
                    goal = min(cells, key=lambda xy: abs(xy[0] - room['x'] - room['width'] / 2) + abs(xy[1] - room['y'] - room['height'] / 2))
                    walk(goal); page.screenshot(path=str(args.output / f'seed-{seed}-{room_id}.png'))
        assert not errors, errors
        reports.append({'seed': seed, 'props': len(world['props']), 'reachableCells': len(previous), 'collisionProp': prop_id, 'browserErrors': errors})
        page.close()
    assert signatures[0] != signatures[1], 'Different seeds produced identical layouts'
    (args.output / 'report.json').write_text(json.dumps(reports, indent=2) + '\n')
    print('PASS two seeded layouts, solid prop keyboard collision, screenshots, no browser errors')
    browser.close()
