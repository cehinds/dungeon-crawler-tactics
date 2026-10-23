# Revamp browser QA

Verified against the newly published WASM build at `http://127.0.0.1:5188` with headless Chromium (`/usr/bin/chromium`) and Python Playwright. The automated pass used 1366×768, 390×844, and 844×390 viewports. `Tools/playtest_revamp.py` performs actions through the visible camp, exploration, map canvas, party controls, item drawer, and forecast controls; `window.dungeon.getView()` is used to choose legal cells and check results.

All three viewports passed the following flows:

- Camp starts with Carl, Princess Donut, Katia, and Mongo in that order. Mordecai is visible as camp-only and cannot deploy.
- Exploration reaches the encounter through the map UI. Battle shows MP and per-ability MP costs; the battle document fits the viewport without page scrolling.
- Canvas atlas requests for terrain, characters, enemies, UI, effects, winged Mongo, and his dedicated portrait all returned 200 with nonzero dimensions. Sampled battle canvases contained 6,369–11,187 distinct sampled colors.
- Carl’s move, Donut’s Magic Missile, Katia’s Shapeshift, and Donut’s Puddle Jumper were selected through the UI, forecast, and confirmed in WASM. The test checked resulting coordinates, HP, guard tags, and ordered presentation events.
- Turn order advanced Carl → Donut → Katia → Mongo, then the enemy phase and round-two Carl. The separate Shock Tonic scenario applied Lightning to a Wet enemy and emitted `reaction.wet_conducts`.
- Desktop hover and phone tap exposed enemy identity and HP. Captured canvas frames changed after committed movement and attack. No browser page errors occurred.

Observed click-to-view-state latency in this run (milliseconds; one headless Chromium run per viewport, not a performance benchmark):

| Viewport | Move | Magic Missile forecast | Missile confirm | Puddle Jumper forecast | Puddle confirm |
| --- | ---: | ---: | ---: | ---: | ---: |
| 1366×768 | 52 | 40 | 96 | 39 | 69 |
| 390×844 | 38 | 39 | 71 | 35 | 70 |
| 844×390 | 35 | 41 | 70 | 40 | 69 |

Screenshots from the run are in `/tmp/dct-revamp-final/`, including camp/battle views, move and attack frames, spell forecasts, and the wet-lightning reaction forecast. The approved concept image at `generated_images/exec-06ff3830-e51f-4e52-904f-19880ed43c1d.png` was used for a visual comparison: the live scene carries over the isometric battlefield and bottom action dock composition. This was a qualitative check, not a pixel comparison.

These results describe Chromium viewport emulation. They do not establish physical-device performance, screen-reader behavior, or input behavior on a native mobile browser.
