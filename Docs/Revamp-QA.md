# Revamp browser QA

## Forms, independent action/movement and narrator update

`Tools/playtest_mechanics.py` passed campaign and editor interactions at 1366×768, 390×844 and 844×390. It covers all nine character sheets, persistent selected-ability information, exact form forecasts, cancel/confirm, a committed action followed by movement, explicit End Turn, and narrated achievements. Bulwark’s +8 maximum HP / −1 movement and its one first-form achievement survived an actual browser reload without save rejection. The Shapeshift quick action opens the form chooser.

`Tools/playtest_revamp.py` passed the updated party turn order and Wet + Lightning scenario. A separated-enemy fixture captured six movement events and 74 changing rendered frames with a visible phase banner and disabled player actions. A separate actual attack fixture verified Heavy Blow damaged Carl and narrator history named the enemy, ability and target. No JavaScript errors occurred.

Visual inspection caught and fixed two issues beyond DOM assertions: the narrator history dialog initially faded from invisible, and exterior wall/pillar placements floated beyond the floor. Dialogs now appear immediately; continuous perimeter walls share the floor boundary. Root inspected `/tmp/revamp-current.png` and `/tmp/narrator-before-390.png` after these fixes. Form-specific sprite sets remain planned; current shapes change real stats and tags.

## Earlier progression, directional movement and enemy turns

The final combined visible-UI suite passed at 1366×768, 390×844 and 844×390, including all four rotations, movement and spell forecasts/commits, turn order, cancellation, touch inspection and Wet + Lightning. No JavaScript errors occurred.

Integrated checks at desktop 1366×768 and phone 360×640 verified the safe-room stations and Equipment/Skills dialog footers fit. Field Vest adds 5 actual maximum HP, Rest restores HP/Mana, and future skills show their level requirement. All four phone camera rotations passed actual pointer targeting and screen-relative arrow movement. An enemy scenario emitted eight movement steps; the enemy banner and input lock remained through playback, map clicks did not skip it, and controls unlocked afterward. No JavaScript errors occurred. A final phone fix makes enemy taps pin the HP/condition inspect panel after pointer leave without changing the save; ability-target taps still open their forecast.

The repeatable `Tools/playtest_revamp.py` enemy fixture uses separated walkable team positions in a validated save and ends Mongo’s activation through the visible confirmation. It observed nine enemy move events and 62 changing canvas frames, with the enemy banner visible and actions disabled throughout sampled playback. `Tools/playtest_progression.py` verified Field Vest’s +5 HP persisted through local-save reload, Rest restored damaged HP/Mana, a real attack awarded 30 XP and level 2, Rigged Burst changed from locked to unlocked, and the floor quest advanced to 1. Its weakened-enemy save fixture keeps this UI test short; the separate full-floor driver uses unmodified enemy health.

The directional-art validator checks all 96 distinct frames across eight characters. Root visually inspected the current battle, exploration, safe-room phone and enemy-phase captures. These checks establish browser behavior and viewport fit, not native Unity rendering or physical-device performance.

## Room kit and modal update

The updated visible-UI suite passes at 1366×768, 390×844 and 844×390. It opens the action chooser, checks Mana costs and legal-target counts, cancels a forecast with Escape without spending resources, reselects and confirms, and checks end-turn confirmation/cancellation and next-actor labels. The Wet + Lightning item scenario still commits the forecast reaction. A separate modal check at 360×640 also verified footer controls fit.

`Tools/playtest_room_kit.py` passes against the published local files at desktop and phone sizes: all 25 PNGs load, seed changes and repeated inputs behave correctly, entrance/exit routes stay clear, layer and route toggles work, and JSON, individual PNG and ZIP downloads succeed. The ZIP contains 25 sprites. No page errors or horizontal overflow were found. `node Tools/test_room_generator.mjs` passes 461 checks covering 450 seeded layouts. PNG validation checks transparency, dimensions, unique IDs and layer metadata. Unity import settings are documented but were not tested in the Unity Editor.

## Earlier animated-dungeon verification

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
