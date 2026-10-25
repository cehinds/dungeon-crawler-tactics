"""Verify generator responsiveness and exact native-map handoff in the real C# browser build.

Requires a freshly published build, hydrated book art, Playwright and Chromium.
A legacy runtime that drops native visuals is a failure, never a skipped check.
"""
import argparse
import copy
import json
from pathlib import Path
from tempfile import TemporaryDirectory

from playwright.sync_api import sync_playwright

SAVE_KEY = "dungeon-crawler-tactics.save.v1"


def canonical_map(value):
    result = copy.deepcopy(value)
    result["playerSpawns"] = [{"x": p["x"], "y": p["y"]} for p in result["playerSpawns"]]
    return result


def assert_exact(view, expected):
    assert view["screen"] == "battle", view.get("message")
    assert canonical_map(view["customMap"]) == canonical_map(expected), "Runtime map differs from exported map"
    assert (view["width"], view["height"]) == (expected["width"], expected["height"])
    tiles = {(t["x"], t["y"]): t for t in expected["tiles"]}
    for tile in view["tiles"]:
        authored = tiles.get((tile["x"], tile["y"]), {})
        assert tile["blocked"] == authored.get("blocked", False), "Collision differs from the preview export"
        assert sorted(tile["tags"]) == sorted(authored.get("tags", [])), "Terrain differs from the preview export"
    assert len(view["tiles"]) == expected["width"] * expected["height"]
    assert sorted((u["x"], u["y"]) for u in view["units"] if u["team"] == "player") == sorted((u["x"], u["y"]) for u in expected["playerSpawns"])
    assert sorted((u["id"], u["x"], u["y"]) for u in view["units"] if u["team"] == "enemy") == sorted((u["id"], u["x"], u["y"]) for u in expected["enemies"])


def ready_generator(page):
    page.wait_for_function("""!document.querySelector('#settings').disabled &&
        document.querySelector('#loading').hidden && !document.querySelector('#play').disabled &&
        document.querySelector('#canvas-wrap').getAttribute('aria-busy') === 'false'""", timeout=60000)


def ready_runtime(page, native=False):
    page.wait_for_function("window.dungeon?.getView || document.querySelector('#workshop-load-error')", timeout=120000)
    failure = page.locator("#workshop-load-error")
    assert not failure.count(), failure.inner_text() if failure.count() else ""
    if native:
        page.wait_for_function("""window.dungeon?.scene?.getNativeArtStatus &&
            ['ready','error'].includes(window.dungeon.scene.getNativeArtStatus().state)""", timeout=60000)
        status = page.evaluate("window.dungeon.scene.getNativeArtStatus()")
        assert status["state"] == "ready" and status["projection"] == "orthogonal", status


def export_json(page, button, path):
    with page.expect_download() as download:
        page.locator(button).click()
    download.value.save_as(path)
    return json.loads(Path(path).read_text())


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--url", default="http://localhost:5200")
    parser.add_argument("--browser", default="/usr/bin/chromium")
    args = parser.parse_args()
    base = args.url.rstrip("/")
    with sync_playwright() as playwright, TemporaryDirectory(prefix="dct-map-playtest-") as temporary:
        browser = playwright.chromium.launch(executable_path=args.browser, args=["--no-sandbox"])
        page = browser.new_page(viewport={"width": 1440, "height": 1000})
        errors = []
        page.on("pageerror", lambda error: errors.append(str(error)))
        # Seed an existing, different autosave before using the generator.
        page.goto(base + "/index.html")
        ready_runtime(page)
        old_map = page.evaluate("""async () => {
          const {generateDungeon,getPlayableMap}=await import('./procedural-map.js');
          const manifest=await fetch('assets/room-kit/manifest.json').then(r=>r.json());
          const rules=await fetch('assets/map-generation-rules.json').then(r=>r.json());
          const map=getPlayableMap(generateDungeon(manifest,{seed:'prior-saved-dungeon',width:12,height:10,layout:'cavern'},rules),manifest);
          await window.dungeon.command('import_map',{customMap:map});
          localStorage.setItem('dungeon-crawler-tactics.save.v1',await window.dungeon.getSave());
          return map;
        }""")
        old_save = page.evaluate("localStorage.getItem('dungeon-crawler-tactics.save.v1')")
        page.goto(base + "/dungeon-generator.html")
        ready_generator(page)
        assert not page.locator("#fixed-seed").is_checked(), "New maps must be the default"
        first_pixels = page.locator("#map").evaluate("canvas=>canvas.toDataURL()")
        first_seed = page.locator("#seed").input_value()
        page.locator("#generate").click()
        ready_generator(page)
        second_pixels = page.locator("#map").evaluate("canvas=>canvas.toDataURL()")
        assert page.locator("#seed").input_value() != first_seed and second_pixels != first_pixels
        second_seed = page.locator("#seed").input_value()
        page.locator("#generate").click()
        ready_generator(page)
        assert page.locator("#seed").input_value() != second_seed
        assert page.locator("#map").evaluate("canvas=>canvas.toDataURL()") != second_pixels
        assert "New dungeon ready" in page.locator("#generation-feedback").inner_text()
        page.locator("#seed").fill("repeatable-native-dungeon")
        assert page.locator("#fixed-seed").is_checked(), "Typing a seed must lock it"
        page.locator("#art-style").select_option("ink-and-lanterns")
        ready_generator(page)
        page.locator("#art-theme").select_option("bubble-desert")
        ready_generator(page)
        page.locator("#generate").click()
        ready_generator(page)
        expected = export_json(page, "#map-json", Path(temporary) / "expected.json")
        recipe = export_json(page, "#recipe", Path(temporary) / "recipe.json")
        assert expected["visuals"]["styleId"] == "ink-and-lanterns" and expected["visuals"]["kitId"] == "bubble-desert"
        expected_visuals = page.evaluate("""async recipe => {
          const {buildArtScene}=await import('./generator-art.js');
          const {serializeNativeVisuals}=await import('./native-map-visuals.js');
          const a=recipe.visualAuthoring;
          const manifest=await fetch(`assets/book-tiles/${a.styleId}/${a.kitId}/manifest.json`).then(r=>r.json());
          const scene=buildArtScene(recipe,{manifest},a.varyRoomMaterials);
          return serializeNativeVisuals(scene,{styleId:a.styleId,kitId:a.kitId,width:recipe.width,height:recipe.height});
        }""", recipe)
        assert expected["visuals"] == expected_visuals, "Portable art must be the exact preview scene"
        fixed_pixels = page.locator("#map").evaluate("canvas=>canvas.toDataURL()")
        page.locator("#generate").click()
        ready_generator(page)
        assert export_json(page, "#map-json", Path(temporary) / "fixed-again.json") == expected
        assert page.locator("#map").evaluate("canvas=>canvas.toDataURL()") == fixed_pixels
        # Invalid settings cannot replace the current map.
        page.locator("#width").fill("2")
        page.locator("#generate").click()
        page.wait_for_function("document.querySelector('#generate').getAttribute('aria-busy') === 'false'")
        assert "kept" in page.locator("#generation-feedback").inner_text().lower()
        assert export_json(page, "#map-json", Path(temporary) / "after-failure.json") == expected
        page.locator("#width").fill(str(expected["width"]))
        page.locator("#play").click()
        page.locator("#play-dialog button[value='cancel']").click()
        assert page.evaluate("localStorage.getItem('dungeon-crawler-tactics.save.v1')") == old_save
        # Simulate another tab replacing the old global key during navigation.
        page.add_init_script("""if(new URLSearchParams(location.search).get('workshop')==='1'){
          localStorage.setItem('dct.workshop-map',%s);
          if(sessionStorage.getItem('qa.failGeneratedSave')==='1'){
            const original=Storage.prototype.setItem;
            Storage.prototype.setItem=function(key,value){if(key==='dungeon-crawler-tactics.save.v1')throw new DOMException('Test storage failure','QuotaExceededError');return original.call(this,key,value)};
          }
        }""" % json.dumps(json.dumps(old_map)))
        tokens = []
        page.on("request", lambda request: tokens.append(request.url.split("map=", 1)[1].split("&", 1)[0]) if request.is_navigation_request() and "workshop=1&map=" in request.url else None)
        page.locator("#play").click()
        page.locator("#confirm-play").click()
        ready_runtime(page, native=True)
        assert_exact(page.evaluate("window.dungeon.getView()"), expected)
        assert page.evaluate("window.dungeon.scene.getNativeVisuals()") == expected["visuals"], "Rendered pieces differ from the preview"
        saved = page.evaluate("window.dungeon.getSave().then(JSON.parse)")
        assert canonical_map(saved["customMap"]) == canonical_map(expected), "Native art must survive C# save export"
        assert "workshop=" not in page.url and "map=" not in page.url and tokens
        assert page.evaluate("token=>sessionStorage.getItem(`dct.workshop-map.${token}`)", tokens[-1]) is None
        page.reload()
        ready_runtime(page, native=True)
        assert_exact(page.evaluate("window.dungeon.getView()"), expected)
        assert page.evaluate("window.dungeon.scene.getNativeVisuals()") == expected["visuals"], "Reload imported a stale global map"
        # Verify square pointer picking and real pointer hover at every camera quarter turn.
        for quarter in range(4):
            result = page.evaluate("""() => {
              const scene=window.dungeon.scene,view=window.dungeon.getView();
              const players=view.units.filter(u=>u.team==='player'),unit=players[scene.getRotation()%players.length];
              const point=scene.cellToScreen(unit.x,unit.y);
              return {unit,point,picked:scene.screenToCell(point.x,point.y),rotation:scene.getRotation()};
            }""")
            assert result["rotation"] == quarter
            assert result["picked"] == {"x": result["unit"]["x"], "y": result["unit"]["y"]}
            box = page.locator("#battlefield").bounding_box()
            page.mouse.move(box["x"] + result["point"]["x"], box["y"] + result["point"]["y"])
            page.wait_for_function("label=>document.querySelector('#map-inspect strong')?.textContent===label", arg=result["unit"]["label"])
            page.locator("#rotate-right").click()
        assert page.evaluate("window.dungeon.scene.getNativeVisuals()") == expected["visuals"]
        # Strict save failure must preserve the previous autosave and retain the packet.
        save_before_failure = page.evaluate("localStorage.getItem('dungeon-crawler-tactics.save.v1')")
        token = "native-save-failure-test"
        page.evaluate("({map,token})=>{sessionStorage.setItem(`dct.workshop-map.${token}`,JSON.stringify(map));sessionStorage.setItem('qa.failGeneratedSave','1')}", {"map": expected, "token": token})
        page.goto(base + f"/index.html?workshop=1&map={token}")
        page.locator("#workshop-load-error").wait_for(timeout=120000)
        assert page.evaluate("localStorage.getItem('dungeon-crawler-tactics.save.v1')") == save_before_failure
        assert page.evaluate("token=>sessionStorage.getItem(`dct.workshop-map.${token}`)", token)
        page.evaluate("sessionStorage.removeItem('qa.failGeneratedSave')")
        page.reload()
        ready_runtime(page, native=True)
        assert_exact(page.evaluate("window.dungeon.getView()"), expected)
        # Size extremes and all art styles pass through the new compiled C# importer.
        for layout, width, height, style, kit in [
            ("chambers", 6, 6, "pocket-dungeon", "starter-dungeon"),
            ("cavern", 20, 16, "ink-and-lanterns", "bubble-sea"),
            ("hall", 14, 10, "dungeon-after-dark", "ghost-cemetery"),
        ]:
            result = page.evaluate("""async options => {
              const {generateDungeon,getPlayableMap}=await import('./procedural-map.js');
              const {buildArtScene}=await import('./generator-art.js');
              const {serializeNativeVisuals}=await import('./native-map-visuals.js');
              const manifest=await fetch('assets/room-kit/manifest.json').then(r=>r.json());
              const rules=await fetch('assets/map-generation-rules.json').then(r=>r.json());
              const native=await fetch(`assets/book-tiles/${options.style}/${options.kit}/manifest.json`).then(r=>r.json());
              const room=generateDungeon(manifest,{...options,seed:'native-extreme',roomCount:6,density:.4,biome:'sewer'},rules);
              const map=getPlayableMap(room,manifest),scene=buildArtScene(room,{manifest:native},true);
              map.visuals=serializeNativeVisuals(scene,{styleId:options.style,kitId:options.kit,width:options.width,height:options.height,tiles:map.tiles});
              await window.dungeon.command('import_map',{customMap:map});return {map,view:window.dungeon.getView()};
            }""", {"layout": layout, "width": width, "height": height, "style": style, "kit": kit})
            assert_exact(result["view"], result["map"])
            ready_runtime(page, native=True)
            assert page.evaluate("window.dungeon.scene.getNativeVisuals()") == result["map"]["visuals"]
        assert not errors, errors
        browser.close()
    print("PASS new/fixed generation, preserved failed map, exact C# terrain/placements/spawns/native art and saves, single-consume token handoff, strict storage failure retry, 4 native pointer rotations, all styles and size extremes.")


if __name__ == "__main__":
    main()
