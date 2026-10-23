"""Browser QA for the standalone seeded room-kit generator and PNG gallery."""
import argparse
import json
from pathlib import Path
import zipfile

from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--url", default="http://127.0.0.1:5188/room-kit.html")
parser.add_argument("--browser", default="/usr/bin/chromium")
parser.add_argument("--downloads", default="/tmp/dct-room-kit")
args = parser.parse_args()
VIEWPORTS = [(1366, 768), (390, 844)]


def run_viewport(browser, downloads, width, height):
    page = browser.new_page(viewport={"width": width, "height": height},
                            is_mobile=width < 500, has_touch=width < 500,
                            accept_downloads=True)
    errors, bad_images = [], []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.on("response", lambda response: bad_images.append((response.status, response.url))
            if response.url.endswith(".png") and response.status >= 400 else None)
    page.goto(args.url, wait_until="domcontentloaded", timeout=60000)
    page.wait_for_function("window.roomWorkshop?.getRoom && document.querySelector('#loading')?.hidden", timeout=60000)
    assert page.evaluate("document.documentElement.scrollWidth <= innerWidth"), "Room-kit page overflows horizontally."

    manifest = page.evaluate("fetch('assets/room-kit/manifest.json').then(r=>r.json())")
    room = page.evaluate("window.roomWorkshop.getRoom()")
    assert len(manifest["assets"]) >= 24, f"Expected a complete PNG kit, found only {len(manifest['assets'])} pieces."
    assert room["seed"] == "crawler-13" and room["width"] == 10 and room["height"] == 8
    assert room["clearRoute"] and all((c["x"], c["y"]) not in {(b["x"], b["y"]) for b in room["blockedCells"]} for c in room["clearRoute"]), "Generated route intersects a blocked cell."
    assert all(abs(a["x"]-b["x"])+abs(a["y"]-b["y"]) == 1 for a,b in zip(room["clearRoute"], room["clearRoute"][1:])), "Generated route is not contiguous."

    pngs = page.evaluate("""async assets => Promise.all(assets.map(async a => {
      const response=await fetch(new URL(`assets/room-kit/${a.file}`, location.href));
      const bitmap=await createImageBitmap(await response.blob());
      return {file:a.file,status:response.status,width:bitmap.width,height:bitmap.height};
    }))""", manifest["assets"])
    assert all(item["status"] == 200 and item["width"] > 0 and item["height"] > 0 for item in pngs), "One or more manifest PNGs failed to load."
    colors = page.locator("#room-canvas").evaluate("""c => {
      const d=c.getContext('2d').getImageData(0,0,c.width,c.height).data, colors=new Set();
      for(let i=0;i<d.length;i+=Math.max(4,Math.floor(d.length/30000/4)*4)) colors.add(`${d[i]},${d[i+1]},${d[i+2]},${d[i+3]}`);
      return colors.size;
    }""")
    assert colors > 40, f"Generated room canvas looks empty ({colors} sampled colors)."

    route_before = page.locator("#room-canvas").evaluate("c=>c.toDataURL()")
    page.locator("#show-route").check()
    assert page.locator("#show-route").is_checked()
    route_after = page.locator("#room-canvas").evaluate("c=>c.toDataURL()")
    assert route_before != route_after, "Show-route control did not draw the route overlay."
    page.locator("#show-route").uncheck()

    # Reassembly is deterministic for a fixed seed/options; controls visibly change it.
    page.locator("#seed").fill("qa-room-seed")
    page.locator("#size").select_option("8,6")
    page.locator("#density").fill("0")
    page.locator("#generate").click()
    changed = page.evaluate("window.roomWorkshop.getRoom()")
    page.locator("#generate").click()
    repeated = page.evaluate("window.roomWorkshop.getRoom()")
    assert changed == repeated, "Same seed/options produced different placements."
    assert changed["seed"] == "qa-room-seed" and (changed["width"], changed["height"], changed["density"]) == (8,6,0)
    assert changed["placements"] != room["placements"], "Seed/size/density controls did not change the generated room."

    before_layers = page.locator("#room-canvas").evaluate("c=>c.toDataURL()")
    props = page.locator("#layers button").filter(has_text="prop")
    assert props.get_attribute("aria-pressed") == "true"
    props.click()
    assert props.get_attribute("aria-pressed") == "false"
    after_layers = page.locator("#room-canvas").evaluate("c=>c.toDataURL()")
    assert before_layers != after_layers, "Hiding the prop layer did not change the preview."
    props.click()
    assert props.get_attribute("aria-pressed") == "true"

    page.locator("#gallery-filter button").filter(has_text="prop").click()
    gallery = page.locator("#asset-gallery .asset-card")
    assert gallery.count() and all("prop" in label.lower() for label in gallery.locator(".asset-info small").all_text_contents())
    page.locator("#gallery-filter button").filter(has_text="all").click()
    assert page.locator("#asset-gallery .asset-card").count() == len(manifest["assets"])

    with page.expect_download() as download_info:
        page.locator("#export-json").click()
    json_download = download_info.value
    json_path = downloads / f"room-{width}x{height}.json"
    json_download.save_as(str(json_path))
    exported = json.loads(json_path.read_text())
    assert exported == repeated, "Exported JSON differs from the visible generated room."

    # A gallery asset exports its authored transparent PNG, not a canvas crop.
    with page.expect_download() as png_download_info:
        page.locator("#asset-gallery .asset-card").first.click()
    png_download = png_download_info.value
    png_path = downloads / f"asset-{width}x{height}.png"
    png_download.save_as(str(png_path))
    assert png_path.stat().st_size > 100, "Gallery PNG download is empty."
    with page.expect_download() as kit_download_info:
        page.locator("a.download-kit").click()
    kit_download = kit_download_info.value
    kit_path = downloads / f"room-kit-{width}x{height}.zip"
    kit_download.save_as(str(kit_path))
    with zipfile.ZipFile(kit_path) as archive:
        kit_pngs = [name for name in archive.namelist() if name.lower().endswith(".png")]
    assert len(kit_pngs) == len(manifest["assets"]), f"ZIP contents differ from manifest: {len(kit_pngs)} PNGs vs {len(manifest['assets'])} assets."
    assert not bad_images, f"PNG HTTP errors: {bad_images}"
    assert not errors, f"Browser page errors: {errors}"
    result = {"viewport": [width,height], "manifestAssets":len(manifest["assets"]),
              "pngsLoaded":len(pngs), "sampledCanvasColors":colors,
              "deterministic":True, "routeConnected":True,
              "routeToggleChangesPreview":True, "layerToggleChangesPreview":True,
              "exports":{"json":json_path.as_posix(),"png":png_path.as_posix(),"zip":kit_path.as_posix(),"zipPngCount":len(kit_pngs)},
              "pageErrors":errors}
    page.close()
    return result


if __name__ == "__main__":
    output = Path(args.downloads)
    output.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=args.browser, headless=True, args=["--no-sandbox"])
        results = [run_viewport(browser, output, width, height) for width,height in VIEWPORTS]
        browser.close()
    for item in results:
        print(json.dumps(item))
