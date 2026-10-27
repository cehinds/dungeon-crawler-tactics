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
parser.add_argument("--suite", choices=("all", "reaction", "enemy"), default="all")
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


def exercise_exploration_rotations(page):
    """Check rotated pointer projection and screen-relative arrow walking."""
    tested = []
    keys = [("ArrowUp", 0, -1), ("ArrowDown", 0, 1),
            ("ArrowLeft", -1, 0), ("ArrowRight", 1, 0)]
    for rotation in range(4):
        if rotation:
            if page.locator('#camera-toggle').count() and not page.locator('#zoom-in').is_visible(): page.locator('#camera-toggle').click()
            page.locator("#rotate-right").click()
        assert page.evaluate("window.dungeon.scene.getRotation()") == rotation
        label = page.locator("#compass-label").inner_text()
        assert label == ["North view", "East view", "South view", "West view"][rotation]
        exploration = view(page)["exploration"]
        start = (exploration["x"], exploration["y"])
        adjacent = [tile for tile in exploration["tiles"]
                    if tile["reachable"] and not tile["blocked"]
                    and abs(tile["x"]-start[0])+abs(tile["y"]-start[1]) == 1]
        assert adjacent, f"No adjacent legal exploration tile at rotation {rotation}, position {start}."
        target = min(adjacent, key=lambda t: (t["y"], t["x"]))
        click_cell(page, target["x"], target["y"])
        page.wait_for_function("([x,y])=>{const m=window.dungeon.getView().exploration;return m.x===x&&m.y===y;}",
                               arg=[target["x"], target["y"]])
        page.wait_for_timeout(150)
        back = (start[0]-target["x"], start[1]-target["y"])
        back_key = next((key for key, dx, dy in keys
                         if page.evaluate("([dx,dy])=>window.dungeon.scene.screenDirection(dx,dy)", [dx,dy]) == {"x":back[0],"y":back[1]}), None)
        assert back_key, f"No screen-relative key maps back to prior cell at rotation {rotation}."
        page.locator("#battlefield").focus()
        page.keyboard.press(back_key)
        page.wait_for_function("([x,y])=>{const m=window.dungeon.getView().exploration;return m.x===x&&m.y===y;}",
                               arg=[start[0], start[1]])
        page.wait_for_timeout(150)
        tested.append({"rotation":rotation,"compass":label,"pointerTarget":[target["x"],target["y"]],
                       "arrowKey":back_key,"returnedTo":[start[0],start[1]]})
    return tested


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
    rotations_tested = exercise_exploration_rotations(page)
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
    door_quest = next((q for q in view(page).get("quests", []) if q["id"] == "quest.door"), None)
    if door_quest:
        assert door_quest["complete"] or door_quest["progress"] == door_quest["total"], f"Entering the encounter did not advance the door quest: {door_quest}"
    return rotations_tested


def party_ids(game_view):
    return [u["id"] for u in game_view["units"] if u["team"] == "player"]


def unit(game_view, unit_id):
    return next(u for u in game_view["units"] if u["id"] == unit_id)


def ability(game_view, ability_id):
    return next(a for a in game_view["abilities"] if a["id"] == ability_id)


def click_ability(page, ability_id):
    page.locator("#open-actions").click()
    page.wait_for_function("document.querySelector('#action-dialog')?.open === true")
    button = page.locator(f"[data-modal-ability='{ability_id}']")
    assert button.count() == 1 and button.is_enabled(), f"{ability_id} is missing or disabled."
    assert "MP" in button.inner_text(), f"{ability_id} does not show its mana cost in MP."
    assert "legal target" in button.inner_text(), f"{ability_id} does not expose current target availability."
    button.click()
    page.wait_for_function("document.querySelector('#action-dialog')?.open !== true")
    if ability(view(page), ability_id)["target"] == "self":
        page.wait_for_function("document.querySelector('#forecast-dialog')?.open === true")
    else:
        page.wait_for_function("document.querySelector('.target-action-summary')?.textContent.includes('Mana')")


def end_turn_with_cancel_check(page, expected_next):
    before = view(page)
    actor_id = before["selectedUnitId"]
    actor = unit(before, actor_id)
    page.locator("#end-turn").click()
    page.wait_for_function("document.querySelector('#end-turn-dialog')?.open === true")
    dialog = page.locator("#end-turn-dialog")
    assert actor["label"] in dialog.inner_text(), "End-turn modal omitted the current actor."
    assert expected_next in dialog.inner_text(), "End-turn modal omitted the next actor/phase."
    page.locator("#cancel-end-turn").click()
    page.wait_for_function("document.querySelector('#end-turn-dialog')?.open !== true")
    after_cancel = view(page)
    unchanged = unit(after_cancel, actor_id)
    assert after_cancel["selectedUnitId"] == actor_id and after_cancel["phase"] == before["phase"]
    assert unchanged["energy"] == actor["energy"] and unchanged["moved"] == actor["moved"] and unchanged["acted"] == actor["acted"] and unchanged["finished"] == actor["finished"], "Canceling end turn spent an action, mana, movement, or activation."
    page.locator("#end-turn").click()
    page.wait_for_function("document.querySelector('#end-turn-dialog')?.open === true")
    page.locator("#confirm-end-turn").click()
    page.wait_for_function("document.querySelector('#end-turn-dialog')?.open !== true")


def assert_ordered_events(game_view):
    events = game_view["events"]
    sequences = [e["sequence"] for e in events]
    assert sequences == list(range(len(events))), f"Presentation events are not numbered in order: {sequences}"
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
    camp_labels = " ".join(page.locator(".safe-crawler-select strong").all_text_contents()).casefold()
    assert all(name.casefold() in camp_labels
               for name in ["Carl", "Princess Donut", "Katia", "Mongo"])
    camp_shot = save_screenshot(page, directory, width, height, "camp")

    rotations_tested = enter_encounter(page)
    game = view(page)
    assert party_ids(game) == EXPECTED_PARTY, f"Battle roster/order mismatch: {party_ids(game)}"
    assert game["selectedUnitId"] == "crawler.carl"
    assert "MP" in page.locator(".hud-meter.en").inner_text(), "Mana meter is not labeled MP."
    page.locator("#open-actions").click()
    assert page.locator("#action-dialog").inner_text().count("MP") >= 1, "Action menu does not show mana costs."
    page.locator("#cancel-actions").click()
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
    target_candidates = [u for u in game["units"] if u["team"] == "enemy" and u["hp"] > 0]
    if width < 500:
        # A zoomed-in isometric board can place a legal enemy outside the phone
        # viewport. Pick a rendered target or zoom out using the camera control.
        for _ in range(5):
            box=page.locator("#battlefield").bounding_box()
            visible=[]
            for candidate in target_candidates:
                pnt=cell_center(page,candidate["x"],candidate["y"])
                if box["x"]<=pnt["x"]<=box["x"]+box["width"] and box["y"]<=pnt["y"]<=box["y"]+box["height"]:
                    visible.append((candidate,pnt))
            if visible: break
            if page.locator('#camera-toggle').count() and not page.locator('#zoom-in').is_visible(): page.locator('#camera-toggle').click()
            page.locator("#zoom-out").click()
        assert visible, "No enemy tile is visible for phone target inspection after zooming out."
        target,point=visible[0]
    else:
        target=target_candidates[0]
        point=cell_center(page,target["x"],target["y"])
    if width < 500:
        # Use the real touchscreen API at the projected viewport coordinate.
        # Locator.tap auto-scrolls large canvases and can retarget the document.
        page.touchscreen.tap(point["x"], point["y"])
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

    # Commit a tile-targeted ability first, then move with Carl's remaining
    # movement. Actions and movement are independent within one activation.
    game = view(page)
    actor = unit(game, "crawler.carl")
    bomb=ability(game,"ability.carl_bomb")
    assert bomb["enabled"] and bomb["target"]=="tile" and bomb["targetIds"],f"Carl's bomb is unavailable: {bomb}"
    occupied={(u["x"],u["y"]) for u in game["units"] if u["hp"]>0}
    safe_tiles=[]
    for target_id in bomb["targetIds"]:
        match=re.fullmatch(r"tile\.(\d+)\.(\d+)",target_id)
        if match:
            xy=(int(match.group(1)),int(match.group(2)))
            tile=next((t for t in game["tiles"] if (t["x"],t["y"])==xy),None)
            if xy not in occupied and tile and "surface.burning" not in tile["tags"]:safe_tiles.append(xy)
    assert safe_tiles,"Carl has no empty legal tile for a harmless bomb action-then-move check."
    bomb_cell=safe_tiles[0]
    click_ability(page,"ability.carl_bomb")
    click_cell(page,*bomb_cell)
    page.wait_for_function("window.dungeon.getView().canConfirm")
    page.locator("#detail-confirm-forecast").click()
    page.wait_for_function("""() => {const v=window.dungeon.getView(),u=v.units.find(x=>x.id==='crawler.carl');
      return !v.canConfirm&&v.selectedUnitId==='crawler.carl'&&u.acted&&!u.moved&&!u.finished&&v.canMove;}""")
    after_bomb=view(page)
    assert unit(after_bomb,"crawler.carl")["energy"]<actor["energy"]
    destinations = [t for t in after_bomb["reachable"] if t["cost"] > 0]
    assert destinations, "Carl has no movement remaining after using his action."
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
    end_turn_with_cancel_check(page, "Princess Donut")
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
    energy_before_cancel = unit(preview, "crawler.donut")["energy"]
    page.keyboard.press("Escape")
    page.wait_for_function("document.querySelector('#forecast-dialog')?.open !== true && !window.dungeon.getView().canConfirm")
    cancelled = view(page)
    cancelled_donut = unit(cancelled, "crawler.donut")
    assert cancelled["selectedUnitId"] == "crawler.donut" and cancelled_donut["energy"] == energy_before_cancel and not cancelled_donut["acted"], "Escape canceled the forecast but spent mana or the action."
    click_ability(page, "ability.donut_magic_missile")
    missile_started = time.perf_counter()
    click_cell(page, wet_enemy["x"], wet_enemy["y"])
    page.wait_for_function("document.querySelector('#forecast-dialog')?.open === true")
    missile_preview_ms = round((time.perf_counter() - missile_started) * 1000, 1)
    preview = view(page)
    target_forecast = next(f for f in preview["forecast"] if f["targetId"] == wet_enemy["id"])
    assert target_forecast["afterHp"] < target_forecast["beforeHp"]
    assert "MP" in page.locator(".target-forecast").inner_text()
    forecast_shot = save_screenshot(page, directory, width, height, "magic-missile-forecast")
    canvas_before_attack = canvas_signature(page)
    missile_confirm_started = time.perf_counter()
    page.wait_for_function("document.querySelector('#forecast-dialog')?.open === true")
    page.locator("#detail-confirm-forecast").click()
    page.wait_for_function("""() => {const v=window.dungeon.getView(),u=v.units.find(x=>x.id==='crawler.donut');
      return !v.canConfirm&&v.selectedUnitId==='crawler.donut'&&u.acted&&u.moved&&!u.finished;}""")
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

    # Katia's defensive stance is previewed in her character sheet and changes
    # actual stats only after confirming the mode forecast.
    end_turn_with_cancel_check(page,"Katia")
    page.wait_for_function("window.dungeon.getView().selectedUnitId==='crawler.katia'")
    katia_before=unit(view(page),"crawler.katia")
    page.locator('#open-character-sheet').click();page.wait_for_function("document.querySelector('#character-sheet-dialog')?.open===true")
    page.locator('[data-sheet-section="sheet-forms"]').click()
    stance=page.locator('[data-sheet-stance="stance.defensive"]')
    assert stance.count()==1 and stance.is_enabled(), 'Katia defensive stance is not available in the character sheet.'
    stance.click();page.wait_for_function("document.querySelector('#forecast-dialog')?.open===true")
    guard_preview=view(page);delta=next(f for f in guard_preview['forecast'] if f['targetId']=='crawler.katia')
    assert delta['afterMaxHp']==delta['beforeMaxHp']+5 and delta['afterMove']==delta['beforeMove']-1
    page.locator('#detail-confirm-forecast').click()
    page.wait_for_function("""() => {const v=window.dungeon.getView(),u=v.units.find(x=>x.id==='crawler.katia');
      return u.stanceId==='stance.defensive'&&v.selectedUnitId==='crawler.katia'&&u.acted&&!u.finished&&v.canMove;}""")
    page.wait_for_function("document.querySelector('#forecast-dialog')?.open!==true")
    assert unit(view(page),"crawler.katia")["maxHp"]==katia_before["maxHp"]+5
    stance_shot=save_screenshot(page,directory,width,height,'character-sheet-stance')
    if page.locator('#done-character-sheet').count(): page.locator('#done-character-sheet').click()
    end_turn_with_cancel_check(page,"Mongo")
    page.wait_for_function("window.dungeon.getView().selectedUnitId==='crawler.mongo'")

    # Enemy turn must follow Mongo only after Carl, Donut and Katia have all ended.
    before_end = view(page)
    assert before_end["selectedUnitId"] == "crawler.mongo" and before_end["phase"] == "player"
    page.evaluate("""() => {
      const canvas=document.querySelector('#battlefield'); window.__enemyFrames=[];
      window.__enemyTimer=setInterval(()=>{
        if(document.querySelector('#enemy-phase-banner')?.hidden) return;
        const ctx=canvas.getContext('2d'), data=ctx.getImageData(0,0,canvas.width,canvas.height).data;
        let hash=2166136261; for(let i=0;i<data.length;i+=997) hash=Math.imul(hash^data[i],16777619);
        window.__enemyFrames.push({hash:hash>>>0,locked:document.querySelector('#open-actions')?.disabled===true,
          banner:!document.querySelector('#enemy-phase-banner')?.hidden});
      },35);
    }""")
    end_turn_with_cancel_check(page, "Enemy phase")
    page.wait_for_function("""() => window.dungeon.getView().round >= 2 &&
      document.querySelector('#enemy-phase-banner')?.hidden && !document.body.classList.contains('enemy-playback') &&
      document.querySelector('#open-actions')?.disabled === false""", timeout=25000)
    page.evaluate("clearInterval(window.__enemyTimer)")
    after_enemies = view(page)
    assert after_enemies["screen"] == "battle" and after_enemies["round"] >= 2
    phase_events = [e for e in assert_ordered_events(after_enemies) if e["type"] == "phase"]
    assert any(e["tag"] == "enemy" for e in phase_events) and any(e["tag"] == "player" for e in phase_events), f"Enemy/player phase events missing: {phase_events}"
    reaction_seen = any(e["type"] == "reaction" for e in assert_ordered_events(after_enemies))
    enemy_moves = [e for e in assert_ordered_events(after_enemies) if e["type"] == "move" and any(u["id"] == e["actorId"] and u["team"] == "enemy" for u in before_end["units"])]
    enemy_frames = page.evaluate("window.__enemyFrames")
    assert enemy_frames and all(frame["banner"] and frame["locked"] for frame in enemy_frames), f"Enemy actions were not visibly locked under the phase banner: {enemy_frames}"
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
    end_turn_with_cancel_check(page, "Princess Donut")
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
    page.wait_for_function("document.querySelector('#forecast-dialog')?.open === true")
    page.locator("#detail-confirm-forecast").click()
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
        "actionThenMove": {"ability":"ability.carl_bomb","tile":list(bomb_cell),"thenMoved":True},
        "uiLatencyMs": {"moveToState": move_latency_ms, "missileTargetPreview": missile_preview_ms,
                        "missileConfirmToState": missile_commit_ms, "puddleConfirmToState": puddle_commit_ms,
                        "puddleTargetPreview": puddle_preview_ms},
        "magicMissile": {"target": wet_enemy["label"], "forecastCommitted": True},
        "characterMode": {"stance": "stance.defensive", "maximumHpChange": 5, "movementChange": -1},
        "turnOrder": "Carl -> Donut -> Katia -> Mongo -> enemy -> round 2 Carl",
        "enemyPlayback": {"enemyMoves": len(enemy_moves), "distinctCanvasFrames": len({f["hash"] for f in enemy_frames}), "actionsLocked": True},
        "mapRotations": rotations_tested,
        "puddleJumper": {"from": [donut["x"], donut["y"]], "to": [tx, ty], "forecastCommitted": True},
        "reactionSeen": reaction_seen,
        "atlas": images,
        "sampledCanvasColors": canvas_colors,
        "screenshots": [camp_shot, initial_shot, move_shot, forecast_shot, attack_shot, stance_shot, jumper_shot, final_shot],
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
    end_turn_with_cancel_check(page, "Princess Donut")
    page.wait_for_function("window.dungeon.getView().selectedUnitId === 'crawler.donut'")
    game = view(page)
    wet = next(u for u in game["units"] if u["team"] == "enemy" and "status.wet" in u["tags"])
    destination = min(game["reachable"], key=lambda t: abs(t["x"]-wet["x"])+abs(t["y"]-wet["y"]))
    click_cell(page, destination["x"], destination["y"])
    page.wait_for_function("([x,y]) => {const u=window.dungeon.getView().units.find(u=>u.id==='crawler.donut');return u.x===x&&u.y===y;}", arg=[destination["x"],destination["y"]])
    page.locator("#open-actions").click()
    page.wait_for_function("document.querySelector('#action-dialog')?.open === true")
    page.locator(".modal-item-section summary").click()
    item = page.locator("[data-modal-item='item.thunder_flask']")
    page.wait_for_function("document.querySelector('[data-modal-item=\"item.thunder_flask\"]')?.offsetHeight > 0")
    item_text = item.inner_text()
    assert item.is_enabled() and "1 action" in item_text and "legal target" in item_text, f"Shock Tonic action state: enabled={item.is_enabled()}, text={item_text!r}"
    item.click()
    page.wait_for_function("document.querySelector('#action-dialog')?.open !== true")
    page.wait_for_function("document.querySelector('.target-action-summary')?.textContent.includes('Mana')")
    click_cell(page, wet["x"], wet["y"])
    page.wait_for_function("window.dungeon.getView().canConfirm")
    forecast = view(page)
    target_forecast = next(f for f in forecast["forecast"] if f["targetId"] == wet["id"])
    assert target_forecast["afterHp"] < target_forecast["beforeHp"]
    shot = save_screenshot(page, directory, 1366, 768, "wet-lightning-forecast")
    page.wait_for_function("document.querySelector('#forecast-dialog')?.open === true")
    page.locator("#detail-confirm-forecast").click()
    page.wait_for_function("""() => {const v=window.dungeon.getView(),u=v.units.find(x=>x.id==='crawler.donut');
      return !v.canConfirm&&v.selectedUnitId==='crawler.donut'&&u.acted&&!u.finished;}""")
    events = assert_ordered_events(view(page))
    assert any(e["type"] == "reaction" and e["reactionId"] == "reaction.wet_conducts" for e in events), f"Wet/lightning reaction missing: {events}"
    assert any(e["type"] == "damage" and e["targetId"] == wet["id"] for e in events)
    assert not errors, f"Browser page errors: {errors}"
    page.close()
    return {"reaction": "reaction.wet_conducts", "target": wet["label"], "forecastCommitted": True, "screenshot": shot}


def run_enemy_movement_case(browser, directory):
    """Force a long legal approach with a valid save fixture, then observe the real playback."""
    page = browser.new_page(viewport={"width": 1366, "height": 768})
    errors = []
    page.on("pageerror", lambda error: errors.append(str(error)))
    page.goto(args.url, wait_until="domcontentloaded", timeout=60000)
    dismiss_intro(page)
    page.locator("#quick-enter").click()
    page.wait_for_function("window.dungeon.getView().screen === 'explore'")
    # Keep this movement case short: choose the nearest open frontier until the encounter opens.
    for _ in range(100):
        game = view(page)
        if game["screen"] == "battle": break
        ev = game["exploration"]
        door = next((p for p in ev["points"] if p["kind"] == "encounter" and p["canInteract"]), None)
        if door:
            page.locator(f"[data-explore-interact='{door['id']}']").click()
            page.wait_for_function("window.dungeon.getView().screen === 'battle'")
            break
        frontier = [t for t in ev["tiles"] if t["reachable"] and not t["revealed"]]
        tile = min(frontier, key=lambda t: (abs(t["x"]-ev["x"])+abs(t["y"]-ev["y"]), t["y"], t["x"]))
        click_cell(page, tile["x"], tile["y"])
        page.wait_for_function("([x,y])=>{const m=window.dungeon.getView().exploration;return m.x===x&&m.y===y}", arg=[tile["x"],tile["y"]])
    fixture = json.loads(state(page))
    floors = [(t["x"],t["y"]) for t in fixture["tiles"] if not t["blocked"]]
    clusters = []
    for x,y in floors:
        points = [(x,y),(x+1,y),(x,y+1),(x+1,y+1)]
        if all(point in floors for point in points): clusters.append(points)
    assert len(clusters)>=2, "Encounter map has no separated open 2x2 areas for enemy movement fixture."
    neighbor_cells={id(cluster):[xy for xy in floors if xy not in cluster and min(abs(x-px)+abs(y-py) for px,py in cluster)==1] for cluster in clusters}
    player_cluster, enemy_cluster = max(((a,b) for a in clusters for b in clusters if a is not b and neighbor_cells[id(a)]),
        key=lambda pair:min(abs(x-u)+abs(y-v) for x,y in pair[0] for u,v in pair[1]))
    for index,player in enumerate([u for u in fixture["units"] if u["team"]=="player"]):
        player["x"],player["y"]=player_cluster[index]
        player["moved"]=index<3; player["acted"]=index<3
        player["finished"]=index<3
    for index,enemy in enumerate([u for u in fixture["units"] if u["team"]=="enemy"]):
        enemy["x"],enemy["y"]=enemy_cluster[index%4]
        enemy["moved"]=False; enemy["acted"]=False
        enemy["finished"]=False
    enemy_units=[u for u in fixture["units"] if u["team"]=="enemy"]
    adjacent=neighbor_cells[id(player_cluster)][0]
    assert adjacent,"Encounter map has no free floor cell beside the party for an enemy declaration check."
    enemy_units[0]["x"],enemy_units[0]["y"]=adjacent
    fixture["selectedUnitId"]="crawler.mongo";fixture["phase"]="player";fixture["activationVersion"]=1
    page.evaluate("s=>window.dungeon.loadSave(JSON.stringify(s))",fixture)
    page.wait_for_function("window.dungeon.getView().screen==='battle'&&window.dungeon.getView().selectedUnitId==='crawler.mongo'")
    page.evaluate("""() => {
      const canvas=document.querySelector('#battlefield'); window.__enemyFrames=[];
      window.__enemyTimer=setInterval(()=>{
        if(document.querySelector('#enemy-phase-banner')?.hidden) return;
        const data=canvas.getContext('2d').getImageData(0,0,canvas.width,canvas.height).data;
        let hash=2166136261;for(let i=0;i<data.length;i+=997)hash=Math.imul(hash^data[i],16777619);
        window.__enemyFrames.push({hash:hash>>>0,locked:document.querySelector('#open-actions')?.disabled===true,
          banner:!document.querySelector('#enemy-phase-banner')?.hidden});
      },30);
    }""")
    page.locator("#end-turn").click()
    page.wait_for_function("document.querySelector('#end-turn-dialog')?.open===true")
    assert "enemy phase" in page.locator("#end-turn-dialog").inner_text().lower(), f"Final actor confirmation does not explain next enemy phase: {page.locator('#end-turn-dialog').inner_text()}"
    page.locator("#confirm-end-turn").click()
    page.wait_for_function("!document.querySelector('#enemy-phase-banner')?.hidden", timeout=10000)
    page.wait_for_function("window.__enemyFrames.length>=3", timeout=10000)
    shot=save_screenshot(page,directory,1366,768,"enemy-movement-banner")
    page.wait_for_function("""() => window.dungeon.getView().round>=2 && window.dungeon.getView().phase==='player' &&
      document.querySelector('#enemy-phase-banner')?.hidden && !document.body.classList.contains('enemy-playback') &&
      document.querySelector('#open-actions')?.disabled===false""", timeout=25000)
    page.evaluate("clearInterval(window.__enemyTimer)")
    game=view(page);events=assert_ordered_events(game)
    enemy_ids={u["id"] for u in game["units"] if u["team"]=="enemy"}
    moves=[e for e in events if e["type"]=="move" and e["actorId"] in enemy_ids]
    attacks=[e for e in events if e["type"]=="attack" and e["actorId"] in enemy_ids]
    frames=page.evaluate("window.__enemyFrames")
    assert moves, f"Separated enemy team did not walk toward the party: {events}"
    assert len({f["hash"] for f in frames})>=2, f"No changing rendered frame observed during enemy movement: {frames}"
    assert frames and all(f["banner"] and f["locked"] for f in frames), f"Enemy movement was not covered by visible banner and locked actions: {frames}"
    page.locator('#save-button').click();page.locator('#menu-narrator-history').click();page.wait_for_function("document.querySelector('#narrator-history-dialog')?.open===true")
    history=page.locator('.narrator-history-list').inner_text()
    assert 'Enemy turn' in history and 'advances toward' in history, f'Enemy phase history omitted actual movement declarations: {history}'
    if attacks: assert 'declares' in history, f'Enemy attack event was not narrated: {history}'
    assert not errors, f"Browser page errors: {errors}"
    page.close()
    return {"enemyMoves":len(moves),"enemyAttacks":len(attacks),"frames":len({f["hash"] for f in frames}),"actionsLocked":True,"narratorDeclarations":True,"screenshot":shot}


def run_enemy_attack_narration_case(browser,directory):
    """Put one real enemy in legal strike range, then end turns through the UI."""
    page=browser.new_page(viewport={"width":1366,"height":768});errors=[]
    page.on("pageerror",lambda error:errors.append(str(error)))
    page.goto(args.url,wait_until="domcontentloaded",timeout=60000);dismiss_intro(page);page.locator("#quick-enter").click()
    page.wait_for_function("window.dungeon.getView().screen==='explore'")
    for _ in range(100):
        game=view(page)
        if game["screen"]=="battle":break
        ev=game["exploration"];door=next((p for p in ev["points"] if p["kind"]=="encounter" and p["canInteract"]),None)
        if door:
            page.locator(f"[data-explore-interact='{door['id']}']").click();page.wait_for_function("window.dungeon.getView().screen==='battle'");break
        tile=min((t for t in ev["tiles"] if t["reachable"] and not t["revealed"]),key=lambda t:(abs(t["x"]-ev["x"])+abs(t["y"]-ev["y"]),t["y"],t["x"]))
        click_cell(page,tile["x"],tile["y"]);page.wait_for_function("([x,y])=>{const m=window.dungeon.getView().exploration;return m.x===x&&m.y===y}",arg=[tile["x"],tile["y"]])
    fixture=json.loads(state(page));players=[u for u in fixture["units"] if u["team"]=="player"]
    enemies=[u for u in fixture["units"] if u["team"]=="enemy"]
    occupied={(u["x"],u["y"]) for u in players}
    adjacent=next((t for t in view(page)["tiles"] if not t["blocked"] and (t["x"],t["y"]) not in occupied and min(abs(t["x"]-u["x"])+abs(t["y"]-u["y"]) for u in players)==1),None)
    assert adjacent,"Encounter has no adjacent open cell for an enemy attack declaration."
    attacker=next((u for u in enemies if u["classId"]=="class.brawler"),enemies[0])
    attacker["hp"]=attacker.get("maxHp",attacker["hp"]);attacker["x"]=adjacent["x"];attacker["y"]=adjacent["y"]
    attacker["energy"]=attacker.get("maxEnergy",attacker.get("energy",12));attacker["moved"]=False;attacker["acted"]=False;attacker["finished"]=False
    for enemy in enemies:
        if enemy is not attacker: enemy["hp"]=0;enemy["finished"]=False
    for player in players: player["moved"]=False;player["acted"]=False;player["finished"]=False
    fixture["activationVersion"]=1;fixture["phase"]="player";fixture["selectedUnitId"]="crawler.carl"
    page.evaluate("s=>window.dungeon.loadSave(JSON.stringify(s))",fixture)
    page.wait_for_function("window.dungeon.getView().screen==='battle'&&window.dungeon.getView().selectedUnitId==='crawler.carl'")
    for actor_id,next_id in zip(("crawler.carl","crawler.donut","crawler.katia","crawler.mongo"),("crawler.donut","crawler.katia","crawler.mongo",None)):
        page.locator("#end-turn").click();page.locator("#confirm-end-turn").click()
        if next_id:page.wait_for_function("id=>window.dungeon.getView().selectedUnitId===id",arg=next_id)
    page.wait_for_function("window.dungeon.getView().round>=2&&window.dungeon.getView().phase==='player'&&document.querySelector('#enemy-phase-banner')?.hidden&&!document.body.classList.contains('enemy-playback')",timeout=25000)
    game=view(page);events=assert_ordered_events(game);attacks=[e for e in events if e["type"]=="attack" and e["actorId"]==attacker["id"]]
    assert attacks,f"Adjacent enemy produced no attack event: {events}; enemy state={next(u for u in game['units'] if u['id']==attacker['id'])}"
    page.locator("#save-button").click();page.locator("#menu-narrator-history").click();page.wait_for_function("document.querySelector('#narrator-history-dialog')?.open===true")
    history=page.locator('.narrator-history-list').inner_text()
    assert 'declares' in history and 'Enemy turn' in history,f'Actual enemy attack was not narrated: {history}'
    shot=save_screenshot(page,directory,1366,768,'enemy-attack-narrator')
    assert not errors,f'Enemy attack browser errors: {errors}'
    page.close()
    return {"enemy":attacker["id"],"attackEvent":True,"narrated":True,"history":history,"screenshot":shot}


if __name__ == "__main__":
    screenshot_dir = Path(args.screenshots)
    screenshot_dir.mkdir(parents=True, exist_ok=True)
    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=args.browser, headless=True, args=["--no-sandbox"])
        results = ([run_viewport(browser, screenshot_dir, width, height) for width, height in VIEWPORTS]
                   if args.suite == "all" else [])
        enemy_playback = run_enemy_movement_case(browser, screenshot_dir) if args.suite in ("all", "enemy") else None
        enemy_attack = run_enemy_attack_narration_case(browser,screenshot_dir) if args.suite in ("all","enemy") else None
        reaction = run_reaction_case(browser, screenshot_dir) if args.suite in ("all", "reaction") else None
        browser.close()
    for result in results:
        print(json.dumps(result))
    if enemy_playback: print(json.dumps({"enemyMovementCase": enemy_playback}))
    if enemy_attack: print(json.dumps({"enemyAttackCase": enemy_attack}))
    if reaction: print(json.dumps({"explicitReactionCase": reaction}))
