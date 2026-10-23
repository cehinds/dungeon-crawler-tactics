# Dungeon presentation review

Final result: passed for the documented browser scope.

The approved concept guides the isometric stone dungeon, warm torchlight, cool water, distinct party silhouettes, cyan ally markers, red enemy markers and navy/gold bottom action dock. These are implemented as separate generated sprite, terrain, prop, icon and effect assets drawn over the real tactical board. The painted concept's exact room geometry is not reproduced pixel for pixel.

The browser keeps the map and action forecast in one viewport. HP, Mana/MP, movement, conditions, cost and range are visible for the selected crawler. Details, inventory and save controls use dialogs; routine feedback uses toasts. End character turn advances through ready allies before the enemy phase.

Visual and interaction evidence is recorded in [Docs/Revamp-QA.md](Docs/Revamp-QA.md); shared-rule, complete-floor and save verification is recorded in [Docs/Validation.md](Docs/Validation.md). The tested viewport sizes cover desktop, portrait phone and landscape phone in Chromium emulation.

Known limits: reserve characters use earlier static art; the native Unity presenter remains IMGUI; there is no audio in this release. Browser viewport testing does not establish performance on physical phones. Character abilities use documented tactical adaptations rather than claiming to reproduce every book mechanic.

The room-kit update adds 25 standalone PNGs and a seeded assembly preview with native manifest anchors. Desktop and phone inspection confirmed aligned floors and clear component layering. Action and end-turn modals now expose costs, target counts and next-actor information, with labeled category colors and target outlines. Browser cancellation and download flows were exercised by the updated Playwright checks.

## Progression and directional-movement update

Inspected the rendered desktop battle and exploration captures, the 360×640 safe room, and an active enemy-turn capture. All eight deployable characters now resolve to generated directional atlases; the validator checks 96 distinct idle/walk frames. The safe room presents Rest, Equipment, Skills and Enter Dungeon stations, with roster controls collapsed to keep the phone screen compact. Actual HP/Mana and equipment changes are shown in the modals. Enemy playback shows a persistent banner and disables player actions; four camera views preserve tile picking and screen-relative keyboard movement. Art and renderer retain the isometric dungeon and bottom action dock composition of the user's reference.

The exploration party is a compact formation representing one shared map position; combat positions are individual cells. Campaign encounters remain authored, and enemy sprites still use the earlier action atlas rather than four-direction artwork. Native Unity still needs a matching presentation implementation and Editor validation.

Also deployed the four reserve characters into a real encounter and visually inspected `/tmp/reserve-party-current.png`: Elle, Imani, Louis and Britney each use their own sprite, with no browser page errors.
