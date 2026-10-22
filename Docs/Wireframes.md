# Interactive wireframes

Open `Wireframes/index.html` directly in a modern browser. No dependencies, install, build, network access, or server are required. The initial screen targets a 1280 × 720 desktop viewport; narrow displays stack the battle panels and keep the map intact.

The intended shipped game is **Unity 6 targeting Web**. This HTML artifact demonstrates screen flow only; it is not a Unity Web build or the game runtime.

This is a **clickable screen prototype with authored sample outcomes**, not a browser implementation of the combat rules. The C# project owns gameplay behavior. Selected tiles, equipment choices, forecasts, rewards, and JSON edits are temporary presentation state and do not save to Unity or a backend. Displayed stats illustrate UX requirements and are not authoritative balance data.

## Screen structure and loop

| Screen | Intended decision | Working prototype interactions |
| --- | --- | --- |
| Battle | Read the terrain and commit to an understandable action | Select any of 80 tiles; choose a deployed crawler; switch between three reaction forecasts; confirm, cancel, or reset; preview the enemy-turn handoff. |
| Party & classes | Prepare four complementary crawlers from eight roster slots | Inspect all eight roster entries; preview class and equipment selections. Deployment swaps are explicitly disabled and explained. |
| Floor route | Assess risk and choose an encounter | Inspect current battle or elite alternative; preview the shared sample battle. Cleared and next-depth nodes are disabled with explanation. |
| Camp & loot | Recover and choose one reward | Select each sponsor reward; choose/reset a single selection; rest once. |
| Content lab | See how readable content might be authored | Switch between ability, reaction, and tag JSON; edit, syntax-check, and reset each sample. Validation errors are visible. |

Planned gameplay loop: safe room → roster/loadout → floor-route decision → deploy up to four → team turn (each crawler may move, then takes one action that ends activation) → enemy intent → hazards → repeat until victory/defeat → reward choice → safe room or next floor. A completed route grants access to later nodes. The prototype allows navigation freely for design review.

## Battle annotations

- **Left rail: team ownership.** All four deployed crawlers remain visible. Their classes, HP, selection outline, and state labels establish a team turn instead of an alternating initiative queue. The rail describes movement before one action, which ends activation and arbitrary party action order.
- **Center: spatial decision.** Exactly 10 columns × 8 rows, with coordinates A1–J8. Schematic wall height, surface texture, named occupant labels, and terrain tags supplement color. Reachable borders illustrate movement range; they do not compute movement. Selecting a wall reports blocked terrain.
- **Right rail: inspect → choose → forecast → commit.** Tile, occupant, and tags appear before actions. The three action buttons select fixed authored examples and jump inspection to their authored target. The list intentionally previews examples across different kits; it does not enforce the selected crawler's class or abilities.
- **Forecast order is explicit.** Direct damage, reaction cause, secondary effect, and consumed tags/surfaces appear in sequence. Numbers are deterministic, with no hidden accuracy roll. A chain can be reviewed before commitment.
- **Confirm is a reversible presentation state.** It displays the chosen outcome and marks an action spent. The map does not animate or apply damage; “Reset sample” restores the view. “Cancel” and Escape close the forecast without spending an action. An action button reopens it.
- **Bottom strip: temporal decision.** Party acts → enemy intent → hazards. Ending the party turn opens an explanatory sample transition rather than silently simulating combat.

Sample forecasts:

| Trigger | Authored result | Consumed/remaining state |
| --- | --- | --- |
| Fire + Oil | 12 direct + 8 ignition = 20; Scrapper 28 → 8 HP | Oil consumed; Burning surface remains |
| Wet + Lightning | Sentry takes 14; adjacent wet Drudge takes 6 | Each target's individual resulting HP is shown; 20 is total damage across both targets |
| Frozen + Shatter | 16 direct + 10 shatter = 26; Foreman 36 → 10 HP | Frozen consumed |

The battle reaction forecast is explicitly a future design scenario, including consumed-state explanations, rather than a replay of kernel outputs. The pure C# implementation may expose a narrower first slice; its own behavior and tests are authoritative. Content-lab JSON copies the actual v1 Firebolt ability, oil-ignition reaction, and Oil tag records from `UnityPackage/Runtime/Data/starter-content.json`. It checks syntax only and never edits or imports that source file. The battle sample intentionally shows future spatial effects and different example numbers: current Firebolt deals 8 damage, oil ignition adds the burning tag without bonus direct damage, and current wet conduction adds 5 damage to its target rather than jumping to a neighbor. Frozen/shatter uses `status.frozen` and `impact.shatter`; brittle is not a v1 tag.

## Characters and adaptation

Carl, Donut, and Katia are the recognizable fan party; Iris is an original fourth recruit. Ash, Bram, Sable, and Pip fill four original reserve slots. Mordecai is a camp mentor rather than a deployed combatant. Class choices, party arrangements, recruit identities, sponsor copy, and encounters are non-canonical adaptation concepts. The interface visibly identifies the project as an unofficial fan adaptation.

## Edge states and accessibility

- No selection ambiguity: tile borders, party selection outlines, explicit names, and tag text accompany colors. Every map tile has an accessible coordinate/terrain/occupant label.
- Forecast cancellation, action spent, route locked, route cleared, reward chosen, rested, invalid JSON, and valid syntax are represented. Loss, game-over, inventory-full, insufficient-action, and save/load failures still need dedicated Unity screens; they are not silently mocked as implemented features.
- Native buttons, select elements, textareas, and modal dialogs provide keyboard operation. Visible focus outlines support navigation; Escape cancels forecasts and closes the native dialog. Dialog dismissal restores browser focus behavior. Status messages use live regions.
- At ≤820 px the party becomes a compact four-column row; map and inspector stack. At ≤420 px the forecast stacks below tile inspection, route nodes become a vertical list, and token artwork shrinks. No combat controls require hover. Motion respects reduced-motion preferences.
- The map's small tile targets are deliberate for the desktop grid reference. A production touch implementation should add map zoom and a large target inspector/confirm control; this wireframe keeps inspection available without precise sprite taps.

## Art handoff: 128 px character canvases

No production sprite assets are included. CSS pixel tokens and geometric surfaces are explicitly schematic placeholders for a GBA-inspired visual direction; they are not a finished sprite sheet or adaptations of copyrighted official art.

| Asset | Source specification | Runtime display / alignment |
| --- | --- | --- |
| Character or enemy frame | 128 × 128 transparent RGBA canvas; nearest-neighbor import; no compression/filtering during iteration | Common foot anchor at (64, 112); silhouette within x=24–104, y=20–112; draw 48–64 px tall over a 48–64 px tile, keeping feet anchored |
| Idle/walk/action/hit/defeat | Separate named frame sequences on the same canvas and anchor | Start with idle 2–4, walk 4, action 4–6, hit 2, defeat 4 frames; timings authored separately |
| Portrait | 128 × 128 separate portrait canvas, transparent or deliberate framed background | Display at 48–96 px; readable outline and facial silhouette |
| Ground terrain tile | 64 × 64 square top-down source, seamless edges | One tile per grid cell; map contains 10 × 8 = 80 cells; nearest-neighbor scaling |
| Wall/prop | 64 × 96 or 128 × 128 transparent source; occupancy and visual height authored separately | Logical occupancy stays one 64 × 64 cell unless explicitly defined; lower edge aligns to tile base |
| Surface overlay | 64 × 64 transparent source, center/edge variants for Oil, Wet, Frost, Burning | Overlay ground under unit feet; preserve coordinate, range, and selection visibility |
| Selection / range / target | Native UI vector or pixel-border effect | Separate from art; text/tag/outline channels preserve meaning beyond color |

For a 1280 × 720 desktop reference, the map has roughly 46 px cells (490 × 392 px framed map) at the desktop reference. A Unity implementation can render a 640 × 512 logical tilemap into the center viewport, with character frames independently scaled around their foot anchor. Keep pixel scale consistent at a chosen integer zoom; fractional scaling in this HTML wireframe is a layout compromise, not the final pixel-perfect renderer.

## Unity Web handoff

- **Load and failure states:** the Web host should show download/decompression progress, an explicit Start button, and a retryable error state with a plain-language connection or unsupported-browser message. A stall should preserve navigation to troubleshooting; it must not resemble an active game turn. These hosting screens are planned, outside this wireframe.
- **Keyboard focus:** the game canvas receives controls only while focused. Entering a text field, opening a menu, or switching browser tabs suspends gameplay input. Escape closes the topmost menu or cancels targeting; it never consumes an action. Restore the last useful focus after a modal closes and provide a visible click/tap-to-focus affordance after focus loss.
- **Touch and viewport:** place inspect/confirm/cancel and menu controls outside the densest map area with at least 44 × 44 CSS-pixel hit regions. Tapping selects; a separate confirm commits. Allow camera pan/zoom without selecting targets. Reflow menus for portrait displays and safe-area insets instead of shrinking text into a scaled desktop canvas.
- **Audio:** use an explicit Start/Enable audio gesture to unlock browser audio. Provide persistent mute and separate music/effects settings. A blocked or background-suspended audio context must not stop turn progression.
- **Save ownership:** show whether the current run is saved locally and when the last checkpoint completed. Offer Export save and Import save file as visible camp/main-menu actions; explain that clearing site data removes browser storage. Validate save version/checksum and show a recoverable import error before replacing the current run. An overwrite requires a concrete choice. These are design requirements, not working controls in this prototype.
- **Delivery constraints:** the production host needs the correct Unity-generated compression/MIME headers, a tested HTTPS deployment, and responsive loading before the Web canvas initializes. Fullscreen should be optional, user-initiated, and reversible. Use a normal browser error screen if the build cannot start.

## Visual system and intentional scope

Dark ink background `#10151f`, slate panels `#1c2532`, warm gold selection `#edc77d`, pale readable body text `#f2efdf`, and blue/red/green semantic accents. Monospaced headings and numeric labels suggest handheld strategy games while system body text preserves legibility. Small square corners and restrained pixel shapes avoid a modern web-product appearance. Semantic controls remain native HTML.

The artifact intentionally uses no image-generation pass, production game art, external fonts, JavaScript framework, or combat engine: the requested deliverable is a standalone low/medium fidelity wireframe. It is a screen-flow and information-hierarchy reference for the Unity project.
