"""Play the first encounter using actual browser controls against a published build.
Requires Python Playwright and Chromium; does not inject game commands or saves.
"""

import argparse
from pathlib import Path
import math

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--url", default="http://127.0.0.1:8771")
parser.add_argument("--browser", default="/usr/bin/chromium")
parser.add_argument("--output", type=Path, default=Path("/tmp/dct-floor-one-qa"))
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

    view = v()
    o = next(o for o in view["world"]["objects"] if o["id"] == "false-guild")
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
    key("e")
    page.wait_for_timeout(250)
    assert v()["mode"] == "battle", v()["message"]
    page.screenshot(path=str(args.output / "battle.png"))

    def tile(x, y):
        box = page.locator("#world").bounding_box()
        t = math.floor(min(box["width"] / 12, box["height"] / 10))
        page.mouse.click(
            box["x"] + math.floor(box["width"] / 2 - 5 * t) + (x + 0.5) * t,
            box["y"] + math.floor(box["height"] / 2 - 4 * t) + (y + 0.5) * t,
        )
        page.wait_for_timeout(60)

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
            for skill in reversed(u["skills"]):
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
                    before = e["hp"]
                    damage = v()["forecast"]["damage"]
                    page.screenshot(path=str(args.output / "forecast.png"))
                    page.locator("#confirm-action").click()
                    page.wait_for_timeout(100)
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
    assert not errors, errors
    print(
        "PASS actual keyboard E encounter, canvas movement/select, skill target forecast/confirm, enemy turns, victory return; no browser errors"
    )
    b.close()
