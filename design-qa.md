# Concept chamber follow-up — 24 October 2026

**Result: passed** for this scoped chamber, camera and battle-HUD pass. This is
not a claim of pixel-for-pixel concept parity or a redesign of every floor.

## Source and final comparison

Reference: `Web/wwwroot/assets/menu-concepts/combat-targeting.png`, plus the
user's original dungeon image. The component index on the right of the source
board is excluded from comparison. The runtime is the existing shared-C# game.

[Side-by-side concept and playable Sewers](https://github.com/cehinds/AI-Art/blob/dungeon-crawler/dungeon-crawler-tactics/Docs/Screenshots/chambers-concept-comparison.png)
shows the cropped source gameplay panel and the complete 1672×941 runtime,
scaled proportionally. Different encounter geometry and gameplay state prevent
a meaningful pixel-diff score; no numerical fidelity score is claimed.

## Reviewed changes

- [x] Connected rooms and real wall collision in the first legacy battle, first
  story battle and Sewers expedition. Doorways preserve routes to every enemy.
- [x] Four generated floor variants and two wall faces, extracted as transparent
  components with measured anchors and ground contacts. Workshop and battle use
  the same stone PNGs; saved room IDs remain stable.
- [x] Closer party framing, raised masonry, warm torch pools, clearer movement
  colors and deterministic stone variation.
- [x] Four primary buttons, the complete action book, local pixel display font,
  corner target confirmation and phone bottom-sheet confirmation.
- [x] Encounter changes reset stale camera pan. All four rotations retain usable
  party framing and correct pointer picking on desktop and phone.
- [x] Routine notices clear on scene changes; phone guidance fits without clipping.
- [x] Existing active saves retain their original walls and hide newly authored
  decorations. New encounters use the new layouts.

## Iterations and actual validation

Early captures exposed stale camera pan when switching encounters and insufficient
headroom after rotation. Both were fixed and recaptured. A subsequent review
caught notices crossing encounters and clipped phone targeting guidance; fresh
captures and explicit browser assertions confirm both fixes. A final workshop
reaction check exposed a routine toast intercepting a map tap; informational
battle toasts now pass clicks through while their dismiss buttons stay usable.

`Tools/playtest_concept_rooms.py` exercises the published WASM build at
1672×941 and 390×844: both changed legacy/Sewers battles, four rotations, inverse
projection and pointer picks, the action book, legal forecast/cancel/commit,
four party activations before enemies, and enemy progression. All pass, with no
JavaScript errors or horizontal overflow. The `chambers-*` PNGs under
`Docs/Screenshots/` record opening, rotation, abilities, forecast and enemy phase.
Focused scene-transition checks find no stale routine notices and complete phone
guidance. The tested views sampled 60 animation frames at median 16.7 ms;
this is an observation in this Chromium environment, not a device-wide guarantee.

Shared tests pass: 650 C# checks (including 16 added save-compatibility checks),
85 Python checks, authored chamber reachability/dry-route checks, and room
recipe/projection checks. The netstandard2.1 compatibility build also passes.
Signature browser regression legally reaches Floor 3 in 109 commands and 17
committed actions, then verifies Tripwire, specialty selection, Triplicate,
two controllable copies, Rush movement 4→6, party controls and exact reload.
The existing four-lane browser suite also passes at 1440×900 and 390×844:
craft/place/trigger a trap, form selection, workshop import, earned Favor,
preview/cancel/commit, preserved movement and reload. Actual map clicks pass
through visible routine toast text, and its dismiss button remains functional.
Unity source/resources were synchronized; Unity Editor was not run.

## Remaining visual differences

The concept has bespoke scenery beyond the map boundary; the game still uses a
navy backdrop around its slab. HUD portraits have a different illustration style
from the pixel map sprites. Later encounters retain their existing geometry.
Phone controls reflow to fit the viewport. These are explicit follow-up art and
content items, not hidden defects in the tested interaction flow. See
[component review](Docs/Concept-Chambers-Review.md).

---

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
