"""Verify earned progression through the first encounter using actual browser controls against a published build.
Requires Python Playwright and Chromium; does not inject game commands or saves.
"""

import argparse
from pathlib import Path
import math
import json

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--url", default="http://127.0.0.1:8771")
parser.add_argument("--browser", default="/usr/bin/chromium")
parser.add_argument("--fixture-checkpoint", type=Path, help="Replay only rank-5 fixture stage from an actual earned safe-room checkpoint")
parser.add_argument("--output", type=Path, default=Path("Rebuild/ProgressionComparison/final"))
args = parser.parse_args()
args.output.mkdir(parents=True, exist_ok=True)
from collections import deque
from playwright.sync_api import sync_playwright

with sync_playwright() as p:
    b = p.chromium.launch(
        executable_path=args.browser, headless=True, args=["--no-sandbox"]
    )
    page = b.new_page(viewport={"width": 1440, "height": 1000})
    errors = []
    page.on("pageerror", lambda e: errors.append(str(e)))
    page.goto(args.url)
    page.wait_for_function("window.rpgView?.party?.length===2")
    page.wait_for_timeout(1000)

    def v():
        return page.evaluate("rpgView")

    def key(k):
        page.keyboard.down(k)
        page.wait_for_timeout(25)
        page.keyboard.up(k)
        page.wait_for_timeout(190)

    def capture(name):
        page.screenshot(path=str(args.output / (name + ".png")))
        (args.output / (name + ".json")).write_text(json.dumps(v(), indent=2))

    def panel(name):
        if page.locator("#close-modal").count(): page.locator("#close-modal").click()
        key("Escape")
        page.locator('[data-open="' + name + '"]').click()

    def walk_to(o):
        view = v()
        blocked = {
            (x, y)
            for prop in view["world"].get("props", [])
            if prop.get("blocksMovement", True)
            for x in range(prop["x"], prop["x"] + prop["width"])
            for y in range(prop["y"], prop["y"] + prop["height"])
        }
        start = (view["x"], view["y"])
        q = deque([start])
        prev = {start: None}
        goal = None
        while q:
            xy = q.popleft()
            if abs(xy[0] - o["x"]) + abs(xy[1] - o["y"]) <= 1:
                goal = xy
                break
            for dx, dy in [(1, 0), (-1, 0), (0, 1), (0, -1)]:
                n = (xy[0] + dx, xy[1] + dy)
                m = view["world"]
                if (
                    0 <= n[0] < m["width"]
                    and 0 <= n[1] < m["height"]
                    and n not in prev
                    and n not in blocked
                    and m["tiles"][n[1] * m["width"] + n[0]] == "."
                ):
                    prev[n] = xy
                    q.append(n)
        assert goal is not None, "No walkable route to the first encounter"
        path = []
        while goal != start:
            path.append(goal)
            goal = prev[goal]
        for xy in reversed(path):
            view = v()
            key(
                "ArrowRight"
                if xy[0] > view["x"]
                else (
                    "ArrowLeft"
                    if xy[0] < view["x"]
                    else "ArrowDown" if xy[1] > view["y"] else "ArrowUp"
                )
            )

    def tile(x, y):
        box = page.locator("#world").bounding_box()
        width, height = v()["battle"]["width"], v()["battle"]["height"]
        t = math.floor(min(box["width"] / (width + 2), box["height"] / (height + 2)))
        page.mouse.click(
            box["x"] + math.floor(box["width"] / 2 - width / 2 * t) + (x + 0.5) * t,
            box["y"] + math.floor(box["height"] / 2 - height / 2 * t) + (y + 0.5) * t,
        )
        page.wait_for_timeout(60)

    if not args.fixture_checkpoint:
        initial = v()
        capture("initial")
        for name in ["Party", "Skills"]:
            panel(name)
            capture("initial-" + name.lower())
        page.locator("#close-modal").click()

        walk_to(next(o for o in v()["world"]["objects"] if o["id"] == "false-guild"))
        key("e")
        page.wait_for_timeout(250)
        assert v()["mode"] == "battle", v()["message"]
        page.screenshot(path=str(args.output / "battle.png"))

        # A distant punch is an actual invalid forecast, and opening/canceling it must not train.
        before_invalid = v()
        carl = next(u for u in before_invalid["battle"]["units"] if u["id"] == "carl")
        tile(carl["x"], carl["y"])
        page.locator('[data-skill="punch"]').click()
        page.locator('[data-target]').first.click()
        assert not v()["forecast"]["valid"]
        assert next(u for u in v()["battle"]["units"] if u["id"] == "carl")["skillPractice"] == carl["skillPractice"]
        capture("invalid-forecast-no-practice")
        page.locator("#close-modal").click()
        did_forecast = False
        enemy_phase = False
        for turn in range(60):
            if v()["mode"] != "battle":
                break
            for uid in ["carl", "donut"]:
                if page.locator("#close-modal").count():
                    page.locator("#close-modal").click()
                view = v()
                if view["mode"] != "battle":
                    break
                u = next(x for x in view["battle"]["units"] if x["id"] == uid)
                if u["hp"] <= 0:
                    continue
                # Let Carl earn three Punch uses through ordinary turns before Donut attacks.
                # This keeps the first rank-up visible without injecting progression.
                if uid == "donut" and next(x for x in view["battle"]["units"] if x["id"] == "carl")["skillPractice"].get("punch", 0) < 3:
                    continue
                tile(u["x"], u["y"])
                e = next(x for x in v()["battle"]["enemies"] if x["hp"] > 0)
                if not u["moved"]:
                    occupied = {
                        (x["x"], x["y"])
                        for x in view["battle"]["units"] + view["battle"]["enemies"]
                        if x["hp"] > 0
                    } | {(x["x"], x["y"]) for x in view["battle"]["obstacles"]}
                    candidates = [
                        (x, y)
                        for y in range(8)
                        for x in range(10)
                        if 0 < abs(x - u["x"]) + abs(y - u["y"]) <= 3
                        and (x, y) not in occupied
                    ]
                    for x, y in sorted(
                        candidates, key=lambda xy: abs(xy[0] - e["x"]) + abs(xy[1] - e["y"])
                    ):
                        tile(x, y)
                        if next(x for x in v()["battle"]["units"] if x["id"] == uid)[
                            "moved"
                        ]:
                            break
                for skill in (["punch"] if uid == "carl" else u["skills"]):
                    if page.locator("#close-modal").count():
                        page.locator("#close-modal").click()
                    button = page.locator('[data-skill="' + skill + '"]')
                    if not button.count() or button.is_disabled():
                        continue
                    button.click()
                    target = page.locator('[data-target="' + e["id"] + '"]')
                    if not target.count():
                        page.locator("#close-modal").click()
                        continue
                    target.click()
                    page.wait_for_timeout(80)
                    if v().get("forecast", {}).get("valid"):
                        before_action = v()
                        page.screenshot(path=str(args.output / "forecast.png"))
                        page.locator("#confirm-action").click()
                        page.wait_for_timeout(100)
                        actor_after = next(x for x in (v()["battle"]["units"] if v().get("battle") else v()["party"]) if x["id"] == uid)
                        actor_before = next(x for x in before_action["battle"]["units"] if x["id"] == uid)
                        assert actor_after["skillPractice"].get(skill, 0) == actor_before["skillPractice"].get(skill, 0) + 1
                        capture("successful-use")
                        did_forecast = True
                        break
                    page.locator("#close-modal").click()
            if v()["mode"] == "battle":
                if page.locator("#close-modal").count():
                    page.locator("#close-modal").click()
                old = v()["turn"]
                page.locator('[data-command="endTurn"]').click()
                page.locator("#end-turn-confirm").click()
                page.wait_for_timeout(150)
                enemy_phase = enemy_phase or v()["turn"] > old
        assert v()["mode"] == "explore", v()["mode"]
        assert did_forecast and enemy_phase
        assert "false-guild" in v()["cleared"]
        page.screenshot(path=str(args.output / "victory.png"))
        won = v()
        assert all(u["xp"] > initial["party"][i]["xp"] for i,u in enumerate(won["party"]))
        assert any(u["level"] > initial["party"][i]["level"] for i,u in enumerate(won["party"]))
        assert any(p["trainedRank"] > 1 for u in won["party"] for p in u["skillProgress"]), "No earned skill rank-up"
        capture("earned-victory")
        for name in ["Party", "Skills"]:
            panel(name)
            capture("earned-" + name.lower())
            if name == "Skills":
                page.locator('[data-skills-actor="carl"]').click()
                capture("earned-skills-carl")
        page.locator("#close-modal").click()
        walk_to(next(o for o in v()["world"]["objects"] if o["kind"] == "guide"))
        key("e")
        walk_to(next(o for o in v()["world"]["objects"] if o["kind"] == "safe"))
        panel("Save")
        page.locator("#rest-button").click()
        page.locator("#save-button").click()
        page.wait_for_function('document.querySelector("#save-result")?.textContent === "Game saved."')
        saved_party = v()["party"]
        (args.output / "earned-safe-checkpoint.json").write_text(page.evaluate('localStorage.getItem("dcc.rebuild.v1")'))
        assert page.locator("#load-button").is_enabled(), "Save did not enable Load immediately"
        page.locator("#load-button").click()
        page.wait_for_timeout(250)
        persistent = lambda party: [{k:value for k,value in u.items() if k not in {"x","y","moved","acted","ended"}} for u in party]
        assert persistent(v()["party"]) == persistent(saved_party)
        capture("safe-save-load")
        page.set_viewport_size({"width":390,"height":844})
        for name in ["Party", "Skills"]:
            panel(name)
            assert page.evaluate('document.documentElement.scrollWidth <= innerWidth'), "Document overflows mobile width"
            assert page.locator('.modal').evaluate('(e) => e.scrollWidth <= e.clientWidth'), "Modal overflows mobile width"
            capture("mobile-" + name.lower())
            if name == "Skills":
                for actor in ["carl","donut"]:
                    page.locator('[data-skills-actor="'+actor+'"]').click()
                    assert page.locator('.modal').evaluate('(e) => e.scrollWidth <= e.clientWidth')
                    capture("mobile-skills-"+actor)
    else:
        page.evaluate('(s)=>localStorage.setItem("dcc.rebuild.v1",s)',args.fixture_checkpoint.read_text())
        panel("Save")
        page.locator("#load-button").click()
        page.wait_for_timeout(250)
        assert "loaded" in v()["message"].lower()
        initial = won = v()
        saved_party = v()["party"]

    if not args.fixture_checkpoint:
        assert not errors, errors
        (args.output / "natural-report.json").write_text(json.dumps({"errors":errors,"initialParty":initial["party"],"earnedParty":won["party"],"savedParty":saved_party,"scope":"Actual keyboard/UI play without injected commands/saves/progression. Immediate Load enabling, persistent progression, natural Punch rank2 and level2, mobile Party and both Skills tabs verified."},indent=2))
    # Disclosed legacy migration fixture: rank 5 is NOT earned in the gameplay above.
    page.set_viewport_size({"width":1440,"height":1000})
    fixture = json.loads(page.evaluate('localStorage.getItem("dcc.rebuild.v1")'))
    fixture["version"] = 1
    fixture["state"]["party"][1]["ranks"]["magic-missile"] = 5
    (args.output / "rank5-migration-fixture.json").write_text(json.dumps(fixture,indent=2))
    mana_results = []
    for spend in [3,6]:
        page.evaluate('(s) => localStorage.setItem("dcc.rebuild.v1",s)',json.dumps(fixture))
        panel("Save")
        page.locator("#load-button").click()
        page.wait_for_timeout(200)
        assert v()["party"][1]["ranks"]["magic-missile"] == 5
        assert "xp rebased" in v()["message"].lower(), v()["message"]
        capture("fixture-migration-loaded-"+str(spend)+"-mana")
        walk_to(next(o for o in v()["world"]["objects"] if o["id"] == "hoarder"))
        key("e")
        assert v()["mode"] == "battle"
        # Wait normally while enemies close the initial 10-cell gap.
        for _ in range(2):
            page.locator('[data-command="endTurn"]').click()
            page.locator('#end-turn-confirm').click()
            page.wait_for_timeout(150)
        unit = next(u for u in v()["battle"]["units"] if u["id"] == "donut")
        enemy = next(e for e in v()["battle"]["enemies"] if e["hp"] > 0)
        tile(unit["x"],unit["y"])
        occupied={(x["x"],x["y"]) for x in v()["battle"]["units"]+v()["battle"]["enemies"] if x["hp"]>0}|{(x["x"],x["y"]) for x in v()["battle"]["obstacles"]}
        for x,y in sorted([(x,y) for y in range(8) for x in range(10) if 0<abs(x-unit["x"])+abs(y-unit["y"])<=3 and (x,y) not in occupied],key=lambda xy:abs(xy[0]-enemy["x"])+abs(xy[1]-enemy["y"])):
            tile(x,y)
            if next(u for u in v()["battle"]["units"] if u["id"]=="donut")["moved"]:break
        page.locator('[data-skill="magic-missile"]').click()
        page.locator('[data-mana-spend]').select_option(str(spend))
        page.locator('[data-target="'+enemy["id"]+'"]').click()
        forecast=v()["forecast"]
        assert forecast["valid"] and forecast["cost"]==spend and forecast["effectRank"]==5
        capture("fixture-rank5-forecast-"+str(spend)+"-mana")
        before_mp=next(u for u in v()["battle"]["units"] if u["id"]=="donut")["mp"]
        page.locator('#confirm-action').click()
        page.wait_for_timeout(100)
        after_mp=next(u for u in v()["battle"]["units"] if u["id"]=="donut")["mp"]
        assert before_mp-after_mp==spend
        after_enemy = next(e for e in v()["battle"]["enemies"] if e["id"]==enemy["id"])
        assert enemy["hp"] - after_enemy["hp"] == min(enemy["hp"], forecast["damage"])
        mana_results.append({"spend":spend,"forecast":forecast,"mpBefore":before_mp,"mpAfter":after_mp})
        capture("fixture-rank5-confirmed-"+str(spend)+"-mana")
    assert mana_results[1]["forecast"]["damage"] > mana_results[0]["forecast"]["damage"]
    (args.output / ("fixture-report.json" if args.fixture_checkpoint else "report.json")).write_text(json.dumps({"errors":errors,"initialParty":initial["party"],"earnedParty":won["party"],"savedParty":saved_party,"fixtureManaResults":mana_results,"fixtureProvenance":"Actual earned safe-room checkpoint; only root version changed to 1 and Donut Magic Missile rank changed to 5. Browser Load UI performs migration. Rank 5 is fixture-backed, not naturally earned.","scope":"Natural stage uses actual keyboard/UI play without injected state. Separate rank-5 stage explicitly injects only a disclosed version-1 save fixture through browser storage, then uses Load and ordinary gameplay controls."},indent=2))
    assert not errors, errors
    print("PASS progression browser verification; fixture-only replay" if args.fixture_checkpoint else "PASS natural progression and fixture browser verification; no browser errors")
    b.close()
