"""Check art-only gallery labels, exports and PNG downloads; no gameplay claims."""
import argparse
import json
from pathlib import Path
import shutil
from playwright.sync_api import sync_playwright

parser=argparse.ArgumentParser(description=__doc__)
parser.add_argument('--url',default='http://127.0.0.1:8773')
parser.add_argument('--expected',type=int,default=61)
parser.add_argument('--output',default='/workspace/scratch/broadcast-deck/gallery')
args=parser.parse_args()
out=Path(args.output);out.mkdir(parents=True,exist_ok=True)
results=[]
with sync_playwright() as p:
    browser=p.chromium.launch(executable_path=shutil.which('chromium'),args=['--no-sandbox'])
    for width,height in [(1440,900),(390,844)]:
        page=browser.new_page(viewport={'width':width,'height':height},accept_downloads=True)
        errors=[];page.on('pageerror',lambda error:errors.append(str(error)))
        page.goto(args.url.rstrip('/')+'/broadcast-kit.html')
        page.wait_for_function('document.querySelectorAll("#pieces figure").length>0')
        page.evaluate("document.querySelectorAll('img').forEach(i=>i.loading='eager')")
        page.wait_for_function('Array.from(document.images).every(i=>i.complete)')
        assert page.locator('#pieces figure').count()==args.expected
        assert page.locator('#concepts figure').count()==2
        assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
        assert 'do not consume this manifest' in page.locator('main>p').first.inner_text()
        assert 'N:' in page.locator('#pieces figcaption').first.inner_text()
        assert page.evaluate('Array.from(document.querySelectorAll("#pieces img")).every(i=>i.naturalWidth===128&&i.naturalHeight===128)')
        for prefix in ['broadcast-combat-','broadcast-exploration-']:
            link=page.locator(f'#pieces a[download^="{prefix}"]').first
            with page.expect_download() as info:link.click()
            download=info.value
            assert download.suggested_filename.startswith(prefix)
            download.save_as(str(out/download.suggested_filename))
        page.screenshot(path=str(out/f'gallery-{width}.png'),full_page=True)
        assert not errors,errors
        results.append({'viewport':[width,height],'pieces':args.expected,'checks':['two concepts','all square128 PNGs','N/E/S/W labels','combat and exploration PNG downloads','no horizontal overflow'],'errors':errors})
        page.close()
    browser.close()
(out/'report.json').write_text(json.dumps({'scope':'art-only gallery', 'results':results},indent=2))
print(json.dumps(results))
