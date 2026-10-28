# Ability rank progression pass

The rank interface preserves the preceding fixed character/action menu controls. Actions show current rank/cap and progress; Character → Abilities shows effective current effects and a collapsed twenty-rank inspector. Book anchors and source links are separate from numeric game tuning.

- [x] All 95 authored abilities have explicit profiles and twenty runtime rows.
- [x] Utility range, push, summons and ranked tags affect the actual shared resolver.
- [x] Mode-based Shapeshift earns practice; consumables and previews do not.
- [x] Heal Critter requires a pet; Magic Missile has an explicitly adapted rank-10 Burning rider.
- [x] Rank-up feedback occurs only on an attained rank, not on preview or ordinary practice.
- [x] 743 shared C# checks across eleven suites, 169 Python checks, content validation, four-viewport rank UI fixtures, and the 70-state HUD suite passed. Summon save validation also enforces the saved floor’s rank gate and rejects forged high-tier copies atomically.
- [x] A fresh local .NET WASM publish passed eight rank integration checks. High-rank test states were explicitly seeded through validated saves; the rank-1-to-2 transition was earned by an actual cast. Preview/cancel preserved the save, commit trained once, reload retained progress, pet targeting and extended teleport range resolved through C#, and Burning appeared in the committed timed statuses.

Evidence: `/workspace/scratch/ability-rank-runtime-final/report.json`, `earned-rank2-desktop.png`, `seeded-inspector-1440.png`, `seeded-inspector-390.png`. This is browser and shared-core verification. Unity source/data were synchronized and the compatibility build passed; Unity Editor execution remains unverified. A complete novel rank table, generic race/class cap selection, variable-power Missile and group teleport are not claimed. See `Docs/Ability-Rank-Audit.md` and `Docs/Progression.md`.

---

# Third HUD pass: scrolling and menu architecture

Source remains the newer 1672×941 combat concept at `/workspace/generated_images/exec-3af4f6ce-48a8-449e-a705-f78ea6819b7a.png`. The previous pass deployed successfully in Pages run 40437214998. This pass focuses on the action book, target/forecast cards, and character sheets; whole-scene art parity remains unfinished.

- [x] Direct Abilities/Items tabs; locked future abilities collapsed.
- [x] Compact fixed action header/tabs/footer, with the list as its only scroll owner.
- [x] Natural action-dialog height and responsive viewport bounds; 44px controls retained.
- [x] Opaque navy/gold forecast; prominent signed HP changes accompany exact before/after values, with reaction logs disclosed on demand.
- [x] Smaller phone targeting card with full effect details accessible.
- [x] Compact character identity/resources and fixed section navigation; only the active tab panel scrolls.
- [x] Remaining character/action-detail MP labels changed to Mana; stale routine toasts cleared on menu entry while errors remain.

The presentation suite passes 70 checks at five viewports, including long item/equipment lists, keyboard tabs, unavailable-action reasons and loss/heal/status forecasts. Visual review covers the action menu, exact forecast, phone item list and character sheets at 320×740, 390×844 and 844×390. A short-landscape test initially found a 58px content panel that could not display a full equipment card; a height-specific compact summary now leaves approximately 160px and the strict last-item visibility check passes. Screenshots: `/workspace/scratch/ui-third-pass/`. JavaScript syntax, Python compilation and whitespace checks pass. Shared C# validation and deployment are tracked separately in Actions. The real-game capture script also checks that browsing Items/Abilities preserves the save before continuing through preview cancellation and the four-character turn cycle. Presentation fixtures do not establish C# runtime validation. Actual WASM capture run 40618912825 passed on `0827e7b`: tab browsing and preview cancellation preserved the save, Carl/Donut/Katia/Mongo ended in order, and the enemy phase advanced to round 2. Its screenshots exposed inherited character-summary alignment and stacked stat rows; a follow-up stretches the summary and aligns labels/values side by side. Pages deployment is tracked independently.

---

# Second HUD clarity pass

Source: the same 1672×941 combat concept (`/workspace/generated_images/exec-3af4f6ce-48a8-449e-a705-f78ea6819b7a.png`). Implementation: `/workspace/scratch/ui-second-pass/`, Chromium at DPR 1, desktop 1672×941 and 1440×1000, phones 390×844 and 320×740, landscape 844×390. This remains HUD-only review with square-map presentation fixtures.

Fixed shortcomings from the preceding pass: spent units only faded; End turn lacked actor/next context; movement looked like incidental text; status-only previews could show a choose-target prompt despite a valid preview; narration could occupy the same area as targeting. Visible END/DOWN badges, a desktop movement column, named End turn/next actor hint, illustrated targeting descriptions and complete preview-delta categories now address those issues. Narration remains visible and separate from action controls. Modal frames and Mana terminology match the deck.

The expanded suite passes 60 fixture states without page/console errors or error toasts. An initial fixture falsely reported success after invoking engine-backed cancellation without C# loaded; visual review found the toast, and the fixture now inspects dialogs without pretending to run the engine. Real-game capture for `05db6de` passed in run 40435988421: cancellation preserved the save, all four allies ended in order, enemies resolved and round 2 began. Its 12 screenshots are in `/workspace/second-pass-gameplay/`. These real screenshots exposed truncated Donut command labels and an objective/toast overlap on phones; follow-up CSS wraps labels and raises toast separation. Final follow-up presentation checks add the long-command case; final deployment remains separately tracked in Actions.

Typography, spacing, navy/gold/cyan tokens, reused PNG artwork and actual-view copy were reviewed in desktop/phone captures. Portrait art, square room composition and exact ornament remain the previously documented differences. The command deck height remains 132px desktop and 218px phone. Controls, meters and visible narration fit the tested viewports.

Evidence: `/workspace/scratch/ui-second-pass/battle-1672x941.png`, `finished-fallen-390x844.png`, `narrator-targeting-320x740.png`, `targeting-844x390.png`, and `status-forecast-1672x941.png`. Combined concept/deck comparison is `/workspace/scratch/ui-second-pass/concept-detail.png`.

A subsequent deployment check exposed a queued native dialog-close race in Foundry: an old close event consumed the origin of a newly reopened inspector and returned focus to the toolbar. One guarded close handler now restores the correct focus destination; the full six-viewport Foundry suite and deterministic close/reopen regression pass locally.

final result: passed

---

# Screenshot research and concept HUD alignment — current review

**Scope:** browser HUD composition. The square map, existing shared C# combat rules and real forecast modal are retained. This is not a claim that the game reproduces the concept's entire scene.

## Evidence

- Source visual truth: `/workspace/generated_images/exec-3af4f6ce-48a8-449e-a705-f78ea6819b7a.png` (newer combat concept), 1672×941. Original concept: `exec-06ff3830-e51f-4e52-904f-19880ed43c1d.png`, also 1672×941.
- External visual evidence: four actual Libretro archive screenshots of Fire Emblem GBA, FFT: The War of the Lions, FFTA and Tactics Ogre: The Knight of Lodis. Source URLs, observed states and component coordinates are in `Docs/Tactics-UI-References.md`.
- Final browser screenshots: `/workspace/scratch/ui-concept-final/`; Chromium, DPR 1, CSS viewports 1672×941, 1440×1000, 390×844, 320×740 and 844×390.
- Full-view combined comparison: `/workspace/scratch/ui-reference-research/concept-vs-revised.png`. Focused party/deck comparison: `/workspace/scratch/ui-reference-research/hud-detail-comparison.png`. Both inputs are displayed together in each comparison artifact. Full-view source and implementation each use 1672×941, no density correction. Focused crops use the same x=0…1672, y=710…941 region.
- State: source depicts an attack preview; the implementation comparison uses a presentation fixture's forecast state. Action name, numbers and room geometry differ and are not used as fidelity evidence. No C# state was fabricated in a real saved run. These fixtures validate layout and UI wiring, not combat-rule correctness.

## Comparison history and fixes

1. Before: the 103px two-row rail had a 36×42 portrait, plain Move/Actions controls and almost no central content. [P1] It missed the concept's illustrated deck hierarchy. Replaced with a 132px framed deck, larger selected portrait, HP/Mana meters, four illustrated command tiles, party above the deck and bottom End turn.
2. Initial capture: [P1] global `.health` styles collapsed the new HP row, overlapping Mana; [P2] inherited footer centering shifted party portraits; [P2] End turn sat too high; [P2] short-landscape target card covered objective. Reset meter layout, footer width/margins and lower anchoring; repositioned landscape target card.
3. Focused comparison: [P2] the party row and command tiles remained undersized relative to the concept. Desktop party tabs now span roughly456px and full command frames include their labels, up to130×108px. Phones retain compact44px-or-larger controls. Short visible labels preserve full accessible names/tooltips. Removed duplicate select-target toast because the live action card already gives that instruction and the toast covered it in landscape.
4. Final captures: no overlapping primary controls or vitals in the five tested viewports. Targeting, forecast and enemy state retain the exact End turn position. Quick abilities visibly select, carry Mana/range/description tooltips and are disabled when the actor cannot act or it is the enemy phase.

## Five fidelity surfaces

- **Typography:** larger serif character/action headings match the concept's hierarchy; readable sans-serif labels serve numeric and touch UI. Exact font matching is not claimed. Short labels avoid command truncation at320px.
- **Layout:** selected identity left, commands center, End turn bottom-right, party above desktop deck, target card above party. Phone reflow deliberately places party and End turn on the lowest row. Phase remains by the objective to preserve Menu/Camera access.
- **Colors:** navy surfaces, cream/gold hierarchy, cyan selected commands, red HP and blue Mana. Numeric labels accompany color. Objective is a plain cream UI panel, not a reproduced parchment illustration.
- **Images:** existing generated portrait/action PNGs and ornate frame PNG are used. No external game's assets are integrated into runtime. Portrait paint style, exact ornament thickness and icons still differ from the concept; these remain P3 art-polish work within this HUD scope.
- **Copy/content:** HP and Mana values come from view data; movement shows capability/spent state. Quick abilities use stable authored ordering. Forecast summaries consume existing preview data. Full actions/items, stats, forms and equipment remain accessible through modals; no illustrative concept damage value is hardcoded into gameplay.

## Validation and limits

The browser presentation suite covers30 states across five viewports, measures overlap/touch sizes/bottom anchoring, checks HP/Mana geometry, activates a quick ability, opens Actions, Help, History and Sponsors, and checks console/page errors. Player-facing canvas playback, pure facing/exploration controls and square-map projection/picking checks pass separately. Shared C# and Unity were not rebuilt locally; the browser fixture is not a substitute for deployment's WASM gameplay checks.

**Accepted differences:** square projection and fixture room; simplified objective ornament; full forecast confirmation remains a modal; no new directional attack art; existing art styles reused; map and effects are outside this HUD pass. Whole-scene visual parity with the concept remains unfinished.

- [x] Real screenshot research with source URLs.
- [x] Component bounds mapped from the exact concept.
- [x] Desktop and mobile HUD implemented and visually inspected.
- [x] Relevant browser presentation and renderer checks.
- [ ] Whole-scene art, room composition and effect parity (separate work).

final result: passed

---

# Historical reviews (not validation of the current UI)

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
