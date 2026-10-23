# Visual fidelity pass — 23 October 2026

## Reference and scope

The selected targets are `Web/wwwroot/assets/menu-concepts/combat-targeting.png`,
`character-equipment.png`, and `safe-room-services.png`, together with the
user's original dungeon image. The menu boards include isolated components on
their right side. Comparisons crop to the illustrated game area; the component
index is not treated as part of a playable viewport.

The existing shared-C# game remains the runtime. Layout, generated assets and
rendering were changed without replacing the board with a static illustration.
Numeric values in the references remain illustrative; the UI displays live
health, mana, movement, equipment and unlock data.

## Changes reviewed

- [x] Textured wall PNG runs align to the actual half-cell boundaries under all
  four camera orientations. Blocked tile clusters use consistent stone walls.
- [x] Closer camera, less label clutter, cached texture tint rather than costly
  per-frame filters, and rotation about the selected character.
- [x] Persistent character portrait and working Stats / Gear / Abilities /
  Stances / Progress tabs. Gear controls use actual saved equipment commands.
- [x] Eight independent house PNG components and a nine-slice golden frame,
  rebuilt reproducibly from preserved generated sources.
- [x] Available, locked and selected room treatments; condensed explanatory
  text; real upgrade preview and cancellation.
- [x] Larger party chips, readable action names and separate signature icons.
- [x] Real summon previews, visible copy lifespan and dedicated copy stats.

## Captures and comparisons

Desktop viewport: **1672 × 941 CSS pixels**, device scale 1. Phone viewport:
**390 × 844 CSS pixels**, device scale 1. PNGs have those same dimensions.

`Docs/Screenshots/fidelity-sheet-{desktop,mobile}.png` shows the initial Carl
Stats tab. `fidelity-home-{desktop,mobile}.png` shows the initial house with
locked rooms. The neutral and target battle captures show the Sewers training
encounter, with Carl selected, then his actual bomb forecast. They are runtime
captures; generated concept art is not used as the battlefield screenshot.

`fidelity-combat-comparison.png` places the cropped concept game area beside the
actual playable view. The source and runtime use different encounter layouts;
this is a composition and component comparison, not a pixel-diff score.

## Iterations and validation

An initial live canvas tint caused excessive rendering work; it was replaced
with cached textures. Browser inspection caught and corrected resource-bar
style collisions, sheet padding, the first house bedroom ordering, and HUD
caption overlap. Pointer picking was exercised through all four orientations
at both viewport sizes. Tabs, room selection and purchase preview/cancel were
checked through the rendered controls, with no JavaScript errors.

The rebuilt local publish passes `Tools/playtest_signatures.py`: legal story
progression to Floor 3 (103 setup commands, 16 committed battle actions),
specialty review/cancel/commit, Tripwire and Triplicate forecasts, two controllable
copies, copy sheets, movement, turn completion and exact reload. These checks
use the visible action controls and actual shared rules, not fabricated saves.
Additional `fidelity-specialty-*`, `fidelity-triplicate-*` and
`fidelity-clockwork-*` captures record the new flow. The existing four-lane
desktop/phone gameplay suite also passes with no browser errors. A final phone
review caught an offscreen selected copy chip and stale desktop camera framing
after resizing; both were corrected before deployment.

The final phone run additionally casts Rush through its button and self-target
forecast, checks free cancellation, then confirms movement 4 → 6, Mana −3,
action spent and movement still available. The selected Copy 2 chip and selected
map position are within the phone viewport. The production atlas loads all nine
PNG links, serves the downloadable kit and has no horizontal phone overflow.

## Remaining reference differences

The concept depicts a dense bespoke dungeon composition. Authored playable
rooms have different geometry and still include larger open spaces. Character
portraits use existing game sprite art rather than the concept's painted
full-body illustration. The house uses separate room islands rather than a
single continuous cutaway, allowing independent locked/selected states. The
phone interface reflows controls; it cannot preserve the desktop proportions.

**Result:** substantial component and layout improvements; full reference
parity is not claimed. These remaining differences are documented rather than
hidden behind a “pixel-perfect” pass result.
