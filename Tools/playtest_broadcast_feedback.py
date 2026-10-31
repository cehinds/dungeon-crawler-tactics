"""Browser-only notification regressions; no shared-rule or Unity claims.

Use the real narrator and feedback modules with a minimal event fixture and a
controlled browser clock. Focus must hold the current message, later events
must queue, and a dismissed message must not strand keyboard focus.
"""
import argparse
import functools
import http.server
import json
from pathlib import Path
import shutil
import threading

from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', default='/tmp/dct-broadcast-feedback')
    args = parser.parse_args()
    output = Path(args.output)
    output.mkdir(parents=True, exist_ok=True)
    handler = functools.partial(http.server.SimpleHTTPRequestHandler,
                                directory=str(ROOT / 'Web/wwwroot'))
    server = http.server.ThreadingHTTPServer(('127.0.0.1', 0), handler)
    threading.Thread(target=server.serve_forever, daemon=True).start()
    results = []
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch(executable_path=shutil.which('chromium'),
                                        args=['--no-sandbox'])
            for width, height in [(1440, 900), (390, 844), (844, 390)]:
                page = browser.new_page(viewport=dict(width=width, height=height))
                errors = []
                page.on('pageerror', lambda error: errors.append(str(error)))
                page.route('**/index.html', lambda r: r.fulfill(
                    content_type='text/html', body='''
                    <link rel="stylesheet" href="game.css">
                    <link rel="stylesheet" href="gameplay-ui.css">
                    <link rel="stylesheet" href="broadcast-feedback.css">
                    <body data-screen="battle"><button id="save-button">Menu</button>
                    <div class="narrator-slot" id="test-slot"></div></body>'''))
                page.goto(f'http://127.0.0.1:{server.server_port}/index.html')
                page.clock.install()
                page.evaluate('''async () => {
                    const {createNarrator} = await import('./narrator.js');
                    window.fixtureNarrator = createNarrator({
                        getView: () => ({units: [], tiles: [], roster: [], achievementIds: []}),
                        content: {abilities: []}
                    });
                    fixtureNarrator.mount(document.querySelector('#test-slot'));
                    fixtureNarrator.onEvent({type: 'achievement',
                        tag: 'achievement.first_move', sequence: 1});
                }''')
                assert 'NEW ACHIEVEMENT' in page.locator('#narrator-line').inner_text()
                assert page.locator('.narrator-label').inner_text() == 'SYSTEM REWARD'
                page.locator('#narrator-history').focus()
                page.clock.fast_forward(7000)
                assert page.locator('#narrator-panel').is_visible()
                page.evaluate('''fixtureNarrator.onEvent({type:'damage', targetId:'enemy.rat',
                    before:30, after:28, amount:2, sequence:2})''')
                assert 'NEW ACHIEVEMENT' in page.locator('#narrator-line').inner_text()
                page.locator('#save-button').focus()
                page.mouse.move(0, 0)
                page.clock.fast_forward(7000)
                assert '2 damage' in page.locator('#narrator-line').inner_text()
                page.locator('#narrator-history').click()
                history = page.locator('.narrator-history-list').inner_text()
                assert 'NEW ACHIEVEMENT' in history and '2 damage' in history
                page.locator('#done-narrator-history').click()
                page.locator('#narrator-dismiss').click()
                assert page.locator('#save-button').evaluate('e => e === document.activeElement')
                page.evaluate('''async () => {
                    const {notify} = await import('./feedback.js');
                    notify('Magic Missile used. Movement is still ready.', 'success');
                }''')
                page.clock.run_for(50)
                text = page.locator('.toast-text').bounding_box()
                assert text['width'] > 200, text
                assert text['x'] >= 0 and text['x'] + text['width'] <= width
                page.evaluate("""async()=>{
                    const {notify,clearFeedback}=await import('./feedback.js');clearFeedback();
                    const dialog=document.createElement('dialog');dialog.id='level-up-dialog';
                    dialog.innerHTML='<p>Actual gains and skills</p><button id="continue-gains">Continue</button>';
                    document.body.append(dialog);dialog.showModal();
                    notify('Queued achievement one','success');notify('Queued sponsor two','success');
                }""")
                page.clock.run_for(50)
                assert page.locator('#level-up-dialog .game-toast:not(.toast-error)').count()==0
                page.evaluate("""async()=>{const {notify}=await import('./feedback.js');notify('Visible error','error')}""")
                page.clock.run_for(50)
                assert 'Visible error' in page.locator('#level-up-dialog .toast-error').inner_text()
                page.evaluate("document.querySelector('#level-up-dialog').close()")
                page.clock.run_for(50)
                assert 'Queued achievement one' in page.locator('body > .toast-region').inner_text()
                page.clock.run_for(6800)
                assert 'Queued sponsor two' in page.locator('body > .toast-region').inner_text()
                assert page.locator('#level-up-dialog .game-toast').count()==0
                page.evaluate("document.querySelector('#level-up-dialog').remove()")
                assert not errors, errors
                results.append(dict(viewport=[width, height], errors=errors,
                    checks=['focus holds message', 'events queue', 'history retained',
                            'dismiss restores focus', 'toast text wraps legibly',
                            'routine notices queue during gains; errors stay visible']))
                page.close()
            browser.close()
    finally:
        server.shutdown()
    report = dict(runtime='production JS modules; event fixture', results=results)
    (output / 'report.json').write_text(json.dumps(report, indent=2))
    print(json.dumps(report, indent=2))


if __name__ == '__main__':
    main()
