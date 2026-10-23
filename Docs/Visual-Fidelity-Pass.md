# Visual fidelity pass

**Pass status, 23 October 2026:** the checklist below records the initial
comparison against the previous release. The new pass implements textured wall
runs, closer framing, larger turn chips, ornate frames, tabbed character sheets
and eight separate illustrated house components. Current captures and remaining
differences are recorded in [design-qa.md](../design-qa.md). Equipment comparison
panels and full composition parity remain unfinished; this initial checklist is
not an assertion that all of the reference has been reproduced.

Use this as a screenshot review checklist for the current interface. The menu concept images are **concept boards**, not single-screen captures: compare their left game/screen composition to the implementation and treat the right column as isolated component references. Crop to that left composition before judging scale or layout.

## Combat targeting: highest priority

Reference: [`combat-targeting.png`](../Web/wwwroot/assets/menu-concepts/combat-targeting.png) (1672 × 912). Its gameplay composition occupies about 62% of the board width; the remaining 38% shows standalone UI examples. The current desktop capture is [`finish-battle-desktop.png`](Screenshots/finish-battle-desktop.png) (1440 × 900).

- [ ] **Make the party and target the focal point.** In the current capture, the arena spans about 1,130 × 625 px, but all four party sprites cluster in roughly 170 × 125 px at the far upper end. After cropping the concept to its left 62%, the party and active skeleton occupy a much larger share of the scene and the target forecast sits beside them. Increase the rendered party/hostile scale or adjust camera framing so the active units and target read at a glance without zooming.
- [ ] **Show tactical targeting on the floor.** The concept distinguishes selected tile (gold), reachable tiles (cyan), hostile target (red), and above-tile magic effect (magenta). The current capture has cyan water pools and red enemy markers, but no comparable movement-range field or clearly selected tile. Add the same distinct tile states and preserve enough contrast against the gray stone floor.
- [ ] **Give target choice a prominent forecast.** The current “CHOOSE YOUR TARGET” instruction is small system text in a narrow right-side HUD column. The concept uses a large framed forecast with ability icon/name, before→after HP, push, mana/range, and Cancel/Confirm actions. Bring those details into a legible, high-contrast card near the battle action area when a target is selected.
- [ ] **Strengthen turn state and action hierarchy.** The concept places a clear party-turn chip above a large, illustrated action row and gives End Turn an explicit confirmation state. The screenshot has a thin top status line and smaller action buttons. Increase selected/ready/acted/finished distinction and make the current actor and end-turn action immediately recognizable.
- [ ] **Replace generic UI typography and framing in combat HUD.** The concept uses warm gold ornamental borders, deep navy panel fills, pixel-art icons, and large serif pixel headings. The screenshot uses mostly small monospaced/system text and thin gold outlines. Apply the concept’s frame, type, and icon treatment first to the target card, party status, and action row; retain the existing dark palette.

## Equipment and character sheet

Reference: [`character-equipment.png`](../Web/wwwroot/assets/menu-concepts/character-equipment.png) (1672 × 912). The left 62% is the complete screen concept; the right side gives component dimensions and examples.

- [ ] Group portrait, stats, equipped items, inventory, and comparison into framed regions. The concept gives the portrait about 30% of its screen width, stats about 28%, and the equipment/inventory area the remaining 42%; avoid reducing the character to a small header above an unstructured list.
- [ ] Show item comparison at the point of selection: currently equipped and candidate item side by side, with green gains and red losses, plus a clear equip confirmation. Keep item icons large enough to identify without relying on labels.
- [ ] Use the concept’s tab strip and selected-state treatment to make Stats, Gear, Abilities, and Stance feel like parts of one character screen.

## Safe room

Reference: [`safe-room-services.png`](../Web/wwwroot/assets/menu-concepts/safe-room-services.png) (1672 × 912). The room scene and upgrade shop occupy the left 68%; isolated component references occupy the right 32%.

- [ ] Lead with the room itself as a navigable illustrated space. Preserve the distinct bedrooms, training area, social screen, and crafting area as recognizable landmarks; place service details alongside or below that scene.
- [ ] Present upgrades as consistent illustrated cards with a named facility, concise benefit, cost, and before/installed state. The concept uses three cards across the lower scene and separate wallet, locked-room, installed, and eligibility examples; keep those states explicit rather than relying on plain text alone.

## Comparison rules

- [ ] Compare screenshots at the same viewport size and crop concept boards to the full-screen composition before measuring proportions. Do not include isolated component columns in scene-scale comparisons.
- [ ] Review at desktop and narrow mobile widths. Keep text and controls readable, and let panels reflow without hiding the scene’s primary action or selected character.
- [ ] Capture the equipment and safe-room implementations before scoring those screens; the supplied current screenshots show combat and a narrow character-sheet view, so they do not establish fidelity for those two full screens.
