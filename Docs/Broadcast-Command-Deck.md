# Broadcast Command Deck

Focused UI contract for the selected combination: the compact GBA-inspired command deck (option 1) with the Dungeon Broadcast feedback treatment (option 3). This pass changes presentation and interaction clarity only; combat, movement, targeting legality, costs, forecasts, turn order, and achievement rules remain owned by the existing shared game logic.

## Component contract

- **Fixed bottom deck:** Keep a compact, opaque navy panel with restrained gold framing and readable contrast. It stays anchored to the viewport bottom and reserves its height from the playfield so map input and camera controls remain usable.
- **Selected character:** Show the selected unit's portrait and name beside labeled HP and Mana bars with current and maximum values. Read values from existing game state. Keep the selected portrait visually distinct from party peers.
- **Commands:** Present Move, Basic Attack, Skills, and Items in a clear, stable order. Use existing actions and menus; Skills and Items may open the existing action chooser. Cyan marks the current selection/focus, with a separate visible disabled/spent state.
- **Turn control:** Keep “End character turn” in the bottom-right on desktop and reachable in the phone deck. Preserve existing confirmation and availability behavior.
- **Dungeon Broadcast:** Show concise System and achievement notices in a compact notice area above or within the deck, without obscuring the objective, active target, or command. Notices should wrap or truncate safely and retain access to existing history where available.
- **Contextual targeting:** When a command requires a target, show the chosen action, legal-target guidance, and the existing resolver's preview for the current target. Keep cancel/back reachable. Do not invent damage values, legal targets, resources, or new targeting rules.
- **Shared behavior:** Preserve keyboard focus visibility, touch-sized controls, existing command semantics, and the shared C# resolver as the source of truth. This document specifies no rules or content changes.

## QA acceptance

Current evidence: fresh shared-C# WASM publish and production UI captured at 1672×941, 1440×900, 390×844 and 844×390 in `/workspace/scratch/broadcast-deck/final/`; actual target/save/cast/move checks in `/workspace/scratch/broadcast-deck/fresh-runtime/report.json`. Production UI fixtures passed 70 states at five viewport sizes; feedback fixtures passed three widths. See `design-qa.md` for exact references and scope.

- [ ] **Desktop (1440×900):** Deck remains fixed to the bottom, spans the available width, and is no taller than 190px excluding transient notices. Portrait, name, HP/Mana values, all four commands, and bottom-right End character turn are visible without overlap or page scrolling.
- [ ] **Phone portrait (390×844):** Deck and safe-area inset remain within the viewport; no horizontal scrolling. Portrait and HP/Mana remain legible, all commands are reachable, End character turn remains visible, and a notice does not cover the objective or targeting controls.
- [ ] **Phone landscape (844×390):** Deck leaves a usable map area of at least 120px high, controls do not overlap, and all commands plus End character turn remain reachable without scrolling the page.
- [ ] **Selection and focus:** Cyan selection is visible in pointer, keyboard, and touch states; keyboard focus has a distinct outline. Disabled/spent commands remain distinguishable without relying on color alone.
- [ ] **Notices:** System and achievement notices appear in the intended compact region, wrap or truncate within bounds, and do not cover the selected action, forecast, objective, or End character turn.
- [ ] **Targeting:** Selecting a target-required command exposes contextual guidance and resolver-backed preview; cancel returns to the command state without spending resources or changing the save. Confirm behavior remains the existing game behavior.
- [ ] **UI rule boundary:** UI diff retains the existing shared resolver. This batch separately changes authored thermal reactions and story XP pacing; those have their own shared-core tests. Browser checks do not establish Unity validation.

## Explicitly remaining work

- **Attack strips:** Current command presentation may still use existing icons or temporary art. Designing and integrating dedicated illustrated attack strips is a separate art/UI task.
- **Art re-authoring:** Replacing temporary portraits, icons, environment art, or other existing assets is outside this focused layout pass.
- **Unity parity:** This contract targets the browser UI. Matching the deck and broadcast notices in Unity requires a separate implementation and Unity-side visual validation.

The current browser UI has related building blocks in `Web/wwwroot/gameplay-ui.css`, `Web/wwwroot/concept-menus.css`, and the gameplay presentation code. Their presence does not count as acceptance evidence for this selected hybrid; the evidence above records the current browser implementation. Whole-scene art parity remains unfinished.

## Reference review and exported art

The selected first reference contributes the gold/navy fixed command deck; the third contributes cyan readiness and magenta System reward notices. Current terrain and sprite assets remain the existing runtime art. Exact ornament, a radial command layout, and the reference sewer room composition are outside this UI implementation. New broadcast art exports are independently browseable at `broadcast-kit.html`; its manifest is not consumed by the game or room generator.
