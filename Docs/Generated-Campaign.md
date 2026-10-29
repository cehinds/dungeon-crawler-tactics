# Generated campaign

Generated campaign mode connects several generated floors into one saved expedition. It is a separate mode from the existing authored story route and from standalone generated-floor imports. The default is a three-floor run, and supported plans contain 2–8 floors. The default route visits Abandoned Works, Dry Cistern, and Relay Vault, three layout families, and one, two, and three objectives respectively. This work does not complete or represent canon book floors 1–8.

## Player controls and flow

Start a run with **Begin an expedition** and choose **Connected expedition · 3 depths** for a campaign or **Single floor** for the standalone mode. On a cleared floor, interact with the exit to open a modal with **Keep exploring**, **Descend**, and, on the final floor, **Finish expedition**. The campaign view presents its label, current floor number, total floors, completed floors, and whether descent can be confirmed. `preview_descent` shows the next-floor label and a confirmation-ready view; `confirm_descent` enters that floor, while `cancel_descent` returns to play without advancing. A preview becomes invalid after any intervening command, so the player must preview again before confirming.

Descent is one-way: earlier floors are archived and cannot be revisited. It carries the party, stats, current HP and Mana, gear, items, and practice state forward. Descent itself does not heal. Rest is an explicit safe-room action. Other optional modes are unavailable while a generated campaign is active until checkpoint integration is defined. Standalone legacy `import_floor` and its save compatibility remain supported.

## Technical contract

The imported plan has this shape:

```text
campaignPlan {
  schemaVersion: 1,
  id: string,
  label: string,
  seed: integer,
  floors: GeneratedFloorPlan[2..8]
}
```

The save records the immutable plan, current floor index, and one state archive per visited floor. The active floor state is stored in `generatedDungeon`:

```text
generatedCampaign {
  schemaVersion: 1,
  plan: campaignPlan,
  floorIndex: integer,
  archives: GeneratedDungeonState[]
}
generatedDungeon: GeneratedDungeonState
```

Archived entries serialize `floorPlan: null` to avoid duplicating plan data; archived floor plans are reconstructed from the saved campaign plan.

The lightweight view exposes `id`, `label`, `floorIndex`, `floorNumber`, `totalFloors`, `completedFloors`, `canDescend`, `nextFloorLabel`, `complete`, and `canConfirmDescent`. `canConfirmDescent` is true only for a current, uninvalidated preview. Commands are atomic: validation failure or cancellation must not advance the floor, alter carried state, or duplicate a reward. A successful descent archives the departing floor and advances exactly once.

## Authoring and implementation references

- [Shared command contract and implementation order](Pseudocode/README.md#shared-command-contract), especially [complete the adventure loop](Pseudocode/04-Implementation-Order.md#41-complete-the-adventure-loop).
- [Exploration rebuild](Exploration-Rebuild.md) describes the generated-floor model, existing standalone behavior, and the explicit remaining campaign-progression work.
- Campaign generation authoring is in [generated-campaign-rules.json](../Web/wwwroot/assets/generated-campaign-rules.json), with its JSON Schema at [generated-campaign-rules.schema.json](../Schemas/generated-campaign-rules.schema.json). The existing `Web/wwwroot/assets/map-generation-rules.json` and `Schemas/exploration-floor-rules.schema.json` continue to describe existing map/floor systems.
- Runtime integration is in the shared C# core, in [GeneratedCampaign](../UnityPackage/Runtime/Core/GameSession.GeneratedCampaign.cs), [GeneratedDungeon](../UnityPackage/Runtime/Core/GameSession.GeneratedDungeon.cs), and [GeneratedFloor](../UnityPackage/Runtime/Core/GameSession.GeneratedFloor.cs). Unity source was refreshed; Unity Editor execution remains unverified.

## Acceptance checklist

- [x] Import rejects malformed plans, unsupported schema versions, and invalid campaign configurations without replacing the active save.
- [x] Default generation creates three floors with three layout families and one, two, and three objectives; fixed-seed generation is covered.
- [x] Clear, exit readiness, preview, cancel, and confirm follow the command contract; intervening commands invalidate a preview.
- [x] Successful descent archives the completed floor, increments once, and preserves party, stats, HP/Mana, gear, items, and practice. No descent healing occurs; safe-room rest remains explicit.
- [x] Final-floor completion reports the campaign complete and does not offer another descent.
- [x] Cancellation, stale/repeated confirmation, duplicate cache claims, real combat/rewards, completion and save/reload were exercised in the actual browser runtime. Malformed plans/saves and invalid transitions are covered by shared-core tests.
- [x] Standalone legacy floor import and existing save compatibility remain intact; active campaigns reject optional modes pending checkpoint integration.
- [x] Story route remains separate; its 84 shared-core journey checks pass. This release does not claim a full new browser playthrough of the story route.

## Validation status

The 78 campaign checks pass, as do the existing core suites (including 84 journey, 28 exploration, 65 custom-map, and 223 general-game checks). Compatibility is clean. Generator checks pass for 300 floor seeds, nine style/theme fits, 11 invalid configurations, and legacy-floor cases (200 and 18).

Actual WebAssembly browser QA passes: the default three-depth route launches with distinct saved plans; movement and home/resume/reload preserve state. A small explicitly authored two-depth fixture then exercises real tactical combat, cache/objective claims, gear and practice, descent, final completion and exact resource/archive roundtrips. The full default three-depth route has not been manually played through every encounter.

Descent modal controls are visible without horizontal overflow at 320×740, 390×844, 844×390 and 1440×1000. No browser page errors were recorded. The tested default save is 1,134,424 UTF-8 bytes and successfully saves/reloads in localStorage.

The existing continuous-floor and generated-adventure browser regressions also pass. Held movement measured seven steps in 1.034 seconds with an average 16.41 ms animation frame interval in local desktop Chromium; this is not a guarantee for all devices.

Content validators passed and Unity source was refreshed; Unity Editor validation remains unverified. Deployment status is tracked separately by the GitHub Pages workflow.
