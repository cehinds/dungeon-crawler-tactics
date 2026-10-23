"""Play the revamp through its visible browser UI at desktop and phone sizes.

Requires the newly published WebAssembly build plus Python Playwright and Chromium.
The test reads window.dungeon.getView() only for assertions and legal destinations;
all actions are performed through visible camp, grid, canvas, and HUD controls.
"""
import argparse
import json
from pathlib import Path
import re
import time

from playwright.sync_api import sync_playwright

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--url", default="http://127.0.0.1:5188")
parser.add_argument("--browser", default="/usr/bin/chromium")
parser.add_argument("--screenshots", default="/tmp/dct-revamp")
args = parser.parse_args()

VIEWPORTS = [(1366, 768), (390, 844), (844, 390)]
EXPECTED_PARTY = ["crawler.carl", "crawler.donut", "crawler.katia", "crawler.mongo"]


def view(page):
    return page.evaluate("window.dungeon.getView()")


def state(page):
    return page.evaluate("window.dungeon.getSave()")


def cell_center(page, x, y):
    return page.evaluate("""([x,y]) => {
      const canvas = document.querySelector('#battlefield');
      const point = window.dungeon.cellToScreen(x,y);
      const box = canvas.getBoundingClientRect();
      return {x:box.left + point.x, y:box.top + point.y};
    }""", [x, y])


def click_cell(page, x, y):
    point = cell_center(page, x, y)
    page.mouse.click(point["x"], point["y"])


def dismiss_intro(page):
    page.wait_for_function("window.dungeon && window.dungeon.getView()", timeout=60000)
    if page.locator("#welcome-dialog").evaluate("d => d.open"):
        page.locator("#begin-button").click()
    if page.locator("#help-dialog").evaluate("d => d.open"):
        page.locator("#help-dialog [data-close='help-dialog']").last.click()
    page.wait_for_function("!document.querySelector('dialog[open]')")


def enter_encounter(page):
    page.locator("#quick-enter").click()
    page.wait_for_function("window.dungeon.getView().screen === 'explore'")
    # Choose newly reachable frontier cells through the visible grid until the
    # encounter door exposes its normal interaction button.
    for _ in range(100):
        current = view(page)
        if current["screen"] == "battle":
            break
        map_view = current["exploration"]
        door = next((p for p in map_view["points"]
                     if p["kind"] == "encounter" and p["canInteract"]), None)
        if door:
            page.locator(f"[data-explore-interact='{door['id']}']").click()
            page.wait_for_function("window.dungeon.getView().screen === 'battle'")
            break
        frontier = [t for t in map_view["tiles"] if t["reachable"] and not t["revealed"]]
        if frontier:
            tile = min(frontier, key=lambda t: (t["y"], t["x"]))
        else:
            encounter = next(p for p in map_view["points"] if p["kind"] == "encounter")
            tile = min((t for t in map_view["tiles"] if t["reachable"]),
                       key=lambda t: abs(t["x"] - encounter["x"]) + abs(t["y"] - encounter["y"]))
        old = (map_view["x"], map_view["y"])
        # The accessible hit-target buttons sit beneath the rendered canvas;
        # route the real pointer through the shared projected map cell.
        click_cell(page, tile["x"], tile["y"])
        page.wait_for_function("([x,y]) => { const m=window.dungeon.getView().exploration; return m.x===x && m.y===y; }",
                               arg=[tile["x"], tile["y"]])
        assert (tile["x"], tile["y"]) != old
    assert view(page)["screen"] == "battle", "Exploration did not enter the encounter through its door."


def party_ids(game_view):
    return [u["id"] for u in game_view["units"] if u["team"] == "player"]


def unit(game_view, unit_id):
    return next(u for u in game_view["units"] if u["id"] == unit_id)


def ability(game_view, ability_id):
    return next(a for a in game_view["abilities"] if a["id"] == ability_id)


def click_ability(page, ability_id):
    button = page.locator(f"[data-ability='{ability_id}']")
    assert button.count() == 1 and button.is_enabled(), f"{ability_id} is missing or disabled."
    assert "MP" in button.inner_text(), f"{ability_id} does not show its mana cost in MP."
    button.click()
    page.wait_for_function(
        "id => document.querySelector(`[data-ability='${id}']`)?.classList.contains('active')",
        arg=ability_id,
    )


def assert_ordered_events(game_view):
    events = game_view["events"]
    assert [e["sequence"] for e in events] == list(range(len(events))), "Presentation event sequence is not ordered."
    return events


def canvas_signature(page):
    return page.locator("#battlefield").evaluate("c => c.toDataURL('image/png')")


def save_screenshot(page, directory, width, height, name):
    path = directory / f"revamp-{width}x{height}-{name}.png"
    page.screenshot(path=str(path), full_page=True)
    return str(path)


def run_viewport(browser, directory, width, height):
    page = browser.new_page(viewport={"width": width, "height": height},
                            is_mobile=width < 500, has_touch=width < 500)
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(args.url, wait_until="domcontentloaded", timeout=60000)
    dismiss_intro(page)

    camp = view(page)
    selected = [r["id"] for r in camp["roster"] if r["selected"]]
    assert selected == EXPECTED_PARTY, f"Default party/order mismatch: {selected}"
    mordecai = next(r for r in camp["roster"] if r["id"] == "crawler.mordecai")
    assert not mordecai["selected"] and mordecai["deployable"] is False, "Mordecai should be camp-only."
    camp_labels = " ".join(page.locator(".camp-arrival-party strong").all_text_contents()).casefold()
    assert all(name.casefold() in camp_labels
               for name in ["Carl", "Princess Donut", "Katia", "Mongo"])
    camp_shot = save_screenshot(page, directory, width, height, "camp")

    enter_encounter(page)
    game = view(page)
    assert party_ids(game) == EXPECTED_PARTY, f"Battle roster/order mismatch: {party_ids(game)}"
    assert game["selectedUnitId"] == "crawler.carl"
    assert "MP" in page.locator(".hud-meter.en").inner_text(), "Mana meter is not labeled MP."
    assert page.locator(".hud-action-list").inner_text().count("MP") >= 1, "Actions do not show costs in MP."
    assert page.locator("#battlefield").count() == 1
    assert page.evaluate("document.documentElement.scrollHeight <= innerHeight"), "Battle page scrolls."

    # Verify generated sprite sheets loaded and the canvas contains actual art.
    images = page.evaluate("""async () => {
      const names=['terrain','characters','enemies','ui','effects','mongo','mongo-portrait'];
      return await Promise.all(names.map(async name => {
        const response=await fetch(`assets/revamp/${name}.png`);
        const bitmap=await createImageBitmap(await response.blob());
        return [name,response.status,bitmap.width,bitmap.height];
      }));
    }""")
    assert all(status == 200 and w > 0 and h > 0 for _, status, w, h in images), f"Sprite sheet failed: {images}"
    page.wait_for_timeout(160)
    canvas_colors = page.locator("#battlefield").evaluate("""c => {
      const g=c.getContext('2d'); const d=g.getImageData(0,0,c.width,c.height).data;
      const colors=new Set(); for(let i=0;i<d.length;i+=Math.max(4,Math.floor(d.length/30000/4)*4))
        colors.add(`${d[i]},${d[i+1]},${d[i+2]}`);
      return colors.size;
    }""")
    assert canvas_colors > 40, f"Battle canvas looks empty or atlas art did not draw ({canvas_colors} sampled colors)."

    # Hover on desktop and tap on phone to reveal target identity/health.
    game = view(page)
    target = next(u for u in game["units"] if u["team"] == "enemy" and u["hp"] > 0)
    point = cell_center(page, target["x"], target["y"])
    if width < 500:
        page.locator("#battlefield").tap(position={"x": point["x"] - page.locator("#battlefield").bounding_box()["x"],
                                                   "y": point["y"] - page.locator("#battlefield").bounding_box()["y"]})
        page.wait_for_function("!document.querySelector('#map-inspect').hidden")
        inspect = page.locator("#map-inspect").inner_text()
        assert target["label"] in inspect and "HP" in inspect, "Tap target info omitted the enemy label/health."
    else:
        page.mouse.move(point["x"], point["y"])
        page.wait_for_function("!document.querySelector('#map-inspect').hidden")
        inspect = page.locator("#map-inspect").inner_text()
        assert target["label"] in inspect and "HP" in inspect, f"Hover info missing target health: {inspect}"
    page.keyboard.press("Escape")
    initial_shot = save_screenshot(page, directory, width, height, "battle")

    # Move Carl through a real projected pointer click and retain a frame from
    # the movement animation for visual review.
    game = view(page)
    actor = unit(game, "crawler.carl")
    destinations = [t for t in game["reachable"] if t["cost"] > 0]
    assert destinations, "Carl has no reachable movement cells."
    destination = max(destinations, key=lambda t: (t["cost"], t["x"], -t["y"]))
    move_start = canvas_signature(page)
    move_started = time.perf_counter()
    click_cell(page, destination["x"], destination["y"])
    page.wait_for_function("([x,y]) => { const u=window.dungeon.getView().units.find(u=>u.id==='crawler.carl'); return u.x===x&&u.y===y; }",
                           arg=[destination["x"], destination["y"]])
    move_latency_ms = round((time.perf_counter() - move_started) * 1000, 1)
    move_events = assert_ordered_events(view(page))
    assert any(e["type"] == "move" and e["actorId"] == "crawler.carl" for e in move_events), f"Move event missing: {move_events}"
    page.wait_for_timeout(45)
    move_frame = canvas_signature(page)
    move_shot = save_screenshot(page, directory, width, height, "move-frame")
    page.wait_for_timeout(240)
    assert move_frame != move_start, "Canvas frame did not change during/after a committed move."

    # One end-turn advances to the next crawler and cannot start the enemy phase.
    page.locator("#end-turn").click()
    page.wait_for_function("window.dungeon.getView().selectedUnitId === 'crawler.donut'")
    game = view(page)
    assert game["phase"] == "player" and game["selectedUnitId"] == "crawler.donut"
    assert not any(e["type"] == "phase" and e["tag"] == "enemy" for e in game["events"]), "Enemy phase began before all four actors ended."

    # Move Donut close enough to the wet enemy, preserving her one action.
    wet_enemy = next(u for u in game["units"] if u["team"] == "enemy" and "status.wet" in u["tags"])
    donut = unit(game, "crawler.donut")
    donut_moves = [t for t in game["reachable"] if t["cost"] > 0]
    assert donut_moves, "Donut has no legal movement destinations."
    destination = min(donut_moves, key=lambda t: (abs(t["x"]-wet_enemy["x"])+abs(t["y"]-wet_enemy["y"]), -t["cost"]))
    click_cell(page, destination["x"], destination["y"])
    page.wait_for_function("([x,y]) => { const u=window.dungeon.getView().units.find(u=>u.id==='crawler.donut'); return u.x===x&&u.y===y; }",
                           arg=[destination["x"], destination["y"]])
    game = view(page)
    missile = ability(game, "ability.donut_magic_missile")
    assert missile["enabled"] and missile["target"] == "enemy", f"Magic Missile state invalid: {missile}"
    assert wet_enemy["id"] in missile["targetIds"], f"Wet enemy not a legal Magic Missile target: {missile['targetIds']}"
    before_missile = state(page)
    click_ability(page, "ability.donut_magic_missile")
    missile_started = time.perf_counter()
    click_cell(page, wet_enemy["x"], wet_enemy["y"])
    try:
        page.wait_for_function("window.dungeon.getView().canConfirm", timeout=5000)
    except Exception as error:
        diagnostic = page.evaluate("""() => { const v=window.dungeon.getView(); return {
          active:v.activeAction, selected:v.selectedUnitId, units:v.units.map(u=>[u.id,u.x,u.y,u.hp,u.tags]),
          targetIds:v.abilities.find(a=>a.id==='ability.donut_magic_missile')?.targetIds,
          point:window.dungeon.cellToScreen(%d,%d), canvas:document.querySelector('#battlefield').getBoundingClientRect().toJSON(),
          message:v.message, body:document.body.innerText.slice(-500)
        }; }""" % (wet_enemy["x"], wet_enemy["y"]))
        raise AssertionError(f"Magic Missile target click did not preview; {diagnostic}") from error
    missile_preview_ms = round((time.perf_counter() - missile_started) * 1000, 1)
    preview = view(page)
    target_forecast = next(f for f in preview["forecast"] if f["targetId"] == wet_enemy["id"])
    assert target_forecast["afterHp"] < target_forecast["beforeHp"]
    assert "MP" in page.locator(".target-forecast").inner_text()
    forecast_shot = save_screenshot(page, directory, width, height, "magic-missile-forecast")
    canvas_before_attack = canvas_signature(page)
    missile_confirm_started = time.perf_counter()
    page.locator("#confirm-forecast").click()
    page.wait_for_function("!window.dungeon.getView().canConfirm && window.dungeon.getView().selectedUnitId === 'crawler.katia'")
    missile_commit_ms = round((time.perf_counter() - missile_confirm_started) * 1000, 1)
    committed = view(page)
    missile_events = assert_ordered_events(committed)
    assert any(e["type"] == "attack" and e["abilityId"] == "ability.donut_magic_missile" for e in missile_events), f"Attack animation event missing: {missile_events}"
    page.wait_for_timeout(75)
    attack_frame = canvas_signature(page)
    attack_shot = save_screenshot(page, directory, width, height, "magic-missile-frame")
    assert attack_frame != canvas_before_attack, "Canvas did not change after the committed attack/reaction."
    actual_wet_enemy = unit(committed, wet_enemy["id"])
    assert actual_wet_enemy["hp"] == target_forecast["afterHp"]

    # Katia's Shapeshift is previewed and commits the intended guarded state.
    katia = unit(committed, "crawler.katia")
    shapeshift = ability(committed, "ability.katia_shapeshift")
    assert shapeshift["enabled"] and shapeshift["target"] == "self", f"Shapeshift not legal: {shapeshift}"
    click_ability(page, "ability.katia_shapeshift")
    page.wait_for_function("window.dungeon.getView().canConfirm")
    guard_preview = view(page)
    guard = next(f for f in guard_preview["forecast"] if f["targetId"] == "crawler.katia")
    assert "status.guarded" in guard["afterTags"]
    shapeshift_shot = save_screenshot(page, directory, width, height, "shapeshift-forecast")
    page.locator("#confirm-forecast").click()
    page.wait_for_function("window.dungeon.getView().units.find(u=>u.id==='crawler.katia').tags.includes('status.guarded') && window.dungeon.getView().selectedUnitId === 'crawler.mongo'")
    assert any(e["type"] in ("tag_add", "guard") for e in assert_ordered_events(view(page)))

    # Enemy turn must follow Mongo only after Carl, Donut and Katia have all ended.
    before_end = view(page)
    assert before_end["selectedUnitId"] == "crawler.mongo" and before_end["phase"] == "player"
    page.locator("#end-turn").click()
    page.wait_for_function("window.dungeon.getView().round >= 2 || window.dungeon.getView().screen !== 'battle'", timeout=15000)
    after_enemies = view(page)
    assert after_enemies["screen"] == "battle" and after_enemies["round"] >= 2
    phase_events = [e for e in assert_ordered_events(after_enemies) if e["type"] == "phase"]
    assert any(e["tag"] == "enemy" for e in phase_events) and any(e["tag"] == "player" for e in phase_events), f"Enemy/player phase events missing: {phase_events}"
    reaction_seen = any(e["type"] == "reaction" for e in assert_ordered_events(after_enemies))
    assert after_enemies["phase"] == "player" and after_enemies["selectedUnitId"] == "crawler.carl"

    page.close()

    # Puddle Jumper gets its own fresh run because one committed action ends
    # Donut's activation; the enemy round can legitimately fell her before the
    # next round. All state changes below still come from visible controls.
    page = browser.new_page(viewport={"width": width, "height": height},
                            is_mobile=width < 500, has_touch=width < 500)
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(args.url, wait_until="domcontentloaded", timeout=60000)
    dismiss_intro(page)
    enter_encounter(page)
    page.locator("#end-turn").click()
    page.wait_for_function("window.dungeon.getView().selectedUnitId === 'crawler.donut'")
    game = view(page)
    jumper = ability(game, "ability.donut_puddle_jumper")
    assert jumper["enabled"] and jumper["target"] == "tile" and jumper["targetIds"], f"Puddle Jumper has no legal tiles: {jumper}"
    donut = unit(game, "crawler.donut")
    candidates = []
    for target_id in jumper["targetIds"]:
        match = re.fullmatch(r"tile\.(\d+)\.(\d+)", target_id)
        if match and (int(match.group(1)), int(match.group(2))) != (donut["x"], donut["y"]):
            candidates.append((int(match.group(1)), int(match.group(2))))
    assert candidates, "Puddle Jumper offered no different destination."
    tx, ty = max(candidates, key=lambda p: abs(p[0]-donut["x"])+abs(p[1]-donut["y"]))
    click_ability(page, "ability.donut_puddle_jumper")
    puddle_started = time.perf_counter()
    click_cell(page, tx, ty)
    page.wait_for_function("window.dungeon.getView().canConfirm")
    puddle_preview_ms = round((time.perf_counter() - puddle_started) * 1000, 1)
    jumper_preview = view(page)
    moved_forecast = next(f for f in jumper_preview["forecast"] if f["targetId"] == "crawler.donut")
    assert (moved_forecast["afterX"], moved_forecast["afterY"]) == (tx, ty)
    jumper_shot = save_screenshot(page, directory, width, height, "puddle-jumper-forecast")
    puddle_confirm_started = time.perf_counter()
    page.locator("#confirm-forecast").click()
    page.wait_for_function("x => !window.dungeon.getView().canConfirm && window.dungeon.getView().units.find(u=>u.id==='crawler.donut').x === x", arg=tx)
    puddle_commit_ms = round((time.perf_counter() - puddle_confirm_started) * 1000, 1)
    final = view(page)
    assert (unit(final, "crawler.donut")["x"], unit(final, "crawler.donut")["y"]) == (tx, ty)
    assert any(e["type"] in ("teleport", "move") and e["actorId"] == "crawler.donut" for e in assert_ordered_events(final))
    final_shot = save_screenshot(page, directory, width, height, "after-puddle-jumper")
    assert not errors, f"Browser page errors: {errors}"

    result = {
        "viewport": [width, height],
        "party": EXPECTED_PARTY,
        "campOnly": "Mordecai",
        "manaLabel": "MP",
        "moveEvent": True,
        "uiLatencyMs": {"moveToState": move_latency_ms, "missileTargetPreview": missile_preview_ms,
                        "missileConfirmToState": missile_commit_ms, "puddleConfirmToState": puddle_commit_ms,
                        "puddleTargetPreview": puddle_preview_ms},
        "magicMissile": {"target": wet_enemy["label"], "forecastCommitted": True},
        "shapeshift": "status.guarded forecast and commit",
        "turnOrder": "Carl -> Donut -> Katia -> Mongo -> enemy -> round 2 Carl",
        "puddleJumper": {"from": [donut["x"], donut["y"]], "to": [tx, ty], "forecastCommitted": True},
        "reactionSeen": reaction_seen,
        "atlas": images,
        "sampledCanvasColors": canvas_colors,
        "screenshots": [camp_shot, initial_shot, move_shot, forecast_shot, attack_shot, shapeshift_shot, jumper_shot, final_shot],
        "pageErrors": errors,
    }
    page.close()
    return result


def run_reaction_case(browser, directory):
    """Use the visible Shock Tonic on a Wet enemy to exercise a real reaction."""
    page = browser.new_page(viewport={"width": 1366, "height": 768})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(args.url, wait_until="domcontentloaded", timeout=60000)
    dismiss_intro(page)
    enter_encounter(page)
    page.locator("#end-turn").click()
    page.wait_for_function("window.dungeon.getView().selectedUnitId === 'crawler.donut'")
    game = view(page)
    wet = next(u for u in game["units"] if u["team"] == "enemy" and "status.wet" in u["tags"])
    destination = min(game["reachable"], key=lambda t: abs(t["x"]-wet["x"])+abs(t["y"]-wet["y"]))
    click_cell(page, destination["x"], destination["y"])
    page.wait_for_function("([x,y]) => {const u=window.dungeon.getView().units.find(u=>u.id==='crawler.donut');return u.x===x&&u.y===y;}", arg=[destination["x"],destination["y"]])
    page.locator("[data-drawer='items']").click()
    page.locator("[data-item='item.thunder_flask']").click()
    page.wait_for_function("document.querySelector('.hud-target')?.textContent.includes('CHOOSE TARGET')")
    click_cell(page, wet["x"], wet["y"])
    page.wait_for_function("window.dungeon.getView().canConfirm")
    forecast = view(page)
    target_forecast = next(f for f in forecast["forecast"] if f["targetId"] == wet["id"])
    assert target_forecast["afterHp"] < target_forecast["beforeHp"]
    shot = save_screenshot(page, directory, 1366, 768, "wet-lightning-forecast")
    page.locator("#confirm-forecast").click()
    page.wait_for_function("!window.dungeon.getView().canConfirm && window.dungeon.getView().selectedUnitId === 'crawler.katia'")
    events = assert_ordered_events(view(page))
    assert any(e["type"] == "reaction" and e["reactionId"] == "reaction.wet_conducts" for e in events), f"Wet/lightning reaction missing: {events}"
    assert any(e["type"] == "damage" and e["targetId"] == wet["id"] for e in events)
    assert not errors, f"Browser page errors: {errors}"
    page.close()
    return {"reaction": "reaction.wet_conducts", "target": wet["label"], "forecastCommitted": True, "screenshot": shot}


if __name__ == "__main__":
    screenshot_dir = Path(args.screenshots)
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=args.browser, headless=True, args=["--no-sandbox"])
        results = [run_viewport(browser, screenshot_dir, width, height) for width, height in VIEWPORTS]
        reaction = run_reaction_case(browser, screenshot_dir)
        browser.close()
    for result in results:
        print(json.dumps(result))
    print(json.dumps({"explicitReactionCase": reaction}))
