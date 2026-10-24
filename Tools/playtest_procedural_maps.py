"""Check generator-to-workshop and generator-to-C# runtime handoffs.

Serve a published browser build that includes the latest authoring files, then:
python3 Tools/playtest_procedural_maps.py --url http://localhost:5200
"""
import argparse

from playwright.sync_api import sync_playwright


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://localhost:5200")
    parser.add_argument("--browser", default="/usr/bin/chromium")
    args = parser.parse_args()
    base = args.url.rstrip("/")
    with sync_playwright() as playwright:
        browser = playwright.chromium.launch(
            executable_path=args.browser, args=["--no-sandbox"]
        )
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        page.goto(base + "/dungeon-generator.html")
        page.wait_for_selector("#settings:not([disabled])")
        page.locator("#edit").click()
        page.wait_for_function(
            "window.roomWorkshop?.getRoom().generation && "
            "document.querySelector('#room-title').textContent.startsWith('Generated map')"
        )
        recipe = page.evaluate("window.roomWorkshop.getRoom()")
        assert len(recipe["playerSpawns"]) == 4 and len(recipe["enemies"]) == 3
        assert page.evaluate("localStorage.getItem('dct.workshop-recipe')") is None

        page.goto(base + "/dungeon-generator.html")
        page.wait_for_selector("#settings:not([disabled])")
        page.locator("#play").click()
        page.locator("#play-dialog button[value='cancel']").click()
        assert page.url.endswith("dungeon-generator.html")
        page.locator("#play").click()
        page.locator("#confirm-play").click()
        page.wait_for_function("window.dungeon?.getView", timeout=120000)
        view = page.evaluate("window.dungeon.getView()")
        assert view["screen"] == "battle" and view["width"] == 16
        assert view["customMap"] and len(view["units"]) == 7

        # Exercise size extremes and each layout through the actual WASM C# importer.
        for layout, width, height in [("chambers", 6, 6), ("cavern", 20, 16), ("hall", 14, 10)]:
            result = page.evaluate(
                """async options => {
                  const {generateDungeon, getPlayableMap} = await import('./procedural-map.js');
                  const manifest = await fetch('assets/room-kit/manifest.json').then(r=>r.json());
                  const rules = await fetch('assets/map-generation-rules.json').then(r=>r.json());
                  const recipe = generateDungeon(manifest, options, rules);
                  const map = getPlayableMap(recipe, manifest);
                  await window.dungeon.command('import_map', {customMap:map});
                  return {map, view:window.dungeon.getView()};
                }""",
                {"layout": layout, "width": width, "height": height,
                 "seed": "long-seed-" + "x" * 110, "roomCount": 6,
                 "density": 0.4, "biome": "sewer"},
            )
            view, expected = result["view"], result["map"]
            assert view["screen"] == "battle"
            assert (view["width"], view["height"]) == (width, height)
            assert len(view["units"]) == 7
            assert view["customMap"]["label"] == expected["label"]
            assert len(view["customMap"]["placements"]) == len(expected["placements"])
        assert not errors, errors
        browser.close()
    print("PASS workshop handoff, play/cancel, four actual C# map imports, 7 actors, and retained placements.")


if __name__ == "__main__":
    main()
