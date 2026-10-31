#!/usr/bin/env python3
"""Focused static room inspector QA; requires generated Python reference images."""
import argparse
import base64
import io
import json
from pathlib import Path
from PIL import Image, ImageChops
from playwright.sync_api import sync_playwright

ROOT = Path(__file__).resolve().parents[1]
BASE = ROOT / 'Web/wwwroot/assets/concept-reconstruction'

def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--url', default='http://127.0.0.1:5197/concept-reconstruction.html')
    parser.add_argument('--out', type=Path, default=Path('/workspace/scratch/map-browser'))
    args = parser.parse_args()
    args.out.mkdir(parents=True, exist_ok=True)
    results = []
    with sync_playwright() as pw:
        browser = pw.chromium.launch(executable_path='/usr/bin/chromium', headless=True, args=['--no-sandbox'])
        for width, height in [(1440,1000),(390,844)]:
            context = browser.new_context(viewport={'width':width,'height':height}, accept_downloads=True)
            page = context.new_page()
            errors = []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(args.url)
            page.wait_for_function("document.querySelector('#status').textContent.startsWith('Pre-rendered exact replay')")
            page.locator('#room-details summary').click()
            for seed in [7,9,29,103]:
                page.locator('#seed').fill(str(seed))
                page.locator('#generate').click()
                page.wait_for_function("seed => document.querySelector('#room-status').textContent.startsWith('Displayed seed '+seed+' ·')", arg=seed)
                with page.expect_download() as download:
                    page.locator('#recipe').click()
                recipe = json.loads(Path(download.value.path()).read_text())
                assert download.value.suggested_filename == f'combat-room-recipe-{seed}.json'
                expected = json.loads((BASE/f'procedural/room-{seed}.json').read_text())
                assert {k:v for k,v in recipe.items() if k!='assetProvenance'} == expected, f'recipe drift seed {seed}'
                encoded = page.locator('#procedural').evaluate("c=>c.toDataURL('image/png').split(',')[1]")
                actual = Image.open(io.BytesIO(base64.b64decode(encoded))).convert('RGB')
                reference = Image.open(BASE/f'procedural/room-{seed}.png').convert('RGB')
                diff = ImageChops.difference(actual, reference)
                assert actual.size == reference.size and not diff.getbbox(), f'pixel drift seed {seed}, {width}px'
                with page.expect_download() as download:
                    page.locator('#room-download').click()
                downloaded = Image.open(download.value.path()).convert('RGB')
                assert download.value.suggested_filename == f'combat-room-{seed}.png'
                assert not ImageChops.difference(actual, downloaded).getbbox(), 'download differs from displayed canvas'
                if seed == 9:
                    actual.save(args.out/f'seed9-canvas-{width}.png')
                    page.locator('#procedural').scroll_into_view_if_needed()
                    page.screenshot(path=str(args.out/f'seed9-browser-{width}.png'), full_page=True)
                results.append({'viewport':[width,height],'seed':seed,'exactPythonPixels':True,'displayedRecipeAndDownloadMatch':True})
            # Editing an unsubmitted seed must preserve the displayed download.
            page.locator('#seed').fill('999')
            assert page.locator('#room-status').inner_text().startswith('Displayed seed 103.')
            with page.expect_download() as download:
                page.locator('#recipe').click()
            assert json.loads(Path(download.value.path()).read_text())['seed'] == 103
            assert not errors, errors
            assert not page.evaluate('document.documentElement.scrollWidth > innerWidth'), 'horizontal page overflow'
            context.close()
        browser.close()
    (args.out/'results.json').write_text(json.dumps(results,indent=2)+'\n')
    print(json.dumps(results,indent=2))

if __name__ == '__main__':
    main()
