# Tactics UI screenshot research and component placement

The user asked for actual comparable-game screenshots, analysis of those screens, and a comparison with this game's UI before another design pass. The visual targets remain the user's original dungeon concept and the later combat concept with a bottom-right End turn control. These references guide the HUD; the requested square-tile gameplay remains square.

## Screenshots actually inspected

Screenshots were downloaded from the public Libretro thumbnail archive and visually inspected. These are game captures, not generated imitations. Each finding is limited to the visible state; one screenshot cannot establish the entire game's interaction behavior. Nintendo, Steam, Game UI Database, MobyGames, and Wikipedia requests were blocked with CONNECT tunnel 403 in this environment. GitHub's screenshot archive was accessible.

| Game / screenshot | Visible state | Useful evidence | Application to this game |
| --- | --- | --- | --- |
| [Fire Emblem, GBA](https://raw.githubusercontent.com/libretro-thumbnails/Nintendo_-_Game_Boy_Advance/master/Named_Snaps/Fire%20Emblem%20%28USA%2C%20Australia%29.png) | Map with Lyn selected, Protect objective | Portrait and HP top-left; terrain DEF/AVO bottom-left; objective and turn count bottom-right. Small framed panels have distinct jobs. | Keep objective compact. Make selected character identity and vitals legible. Use corner panels for context. |
| [Final Fantasy Tactics: The War of the Lions](https://raw.githubusercontent.com/libretro-thumbnails/Sony_-_PlayStation_Portable/master/Named_Snaps/Final%20Fantasy%20Tactics%20-%20The%20War%20of%20the%20Lions%20%28USA%29.png) | Ramza's command menu open | Short Move/Act/Wait/Status/AI list above a substantial portrait/stat card. HP, MP and CT have labeled bars and numeric values. | Restore prominent portrait and labeled HP/Mana bars. Surface a small set of commands; put the full skill collection in the existing modal. |
| [Final Fantasy Tactics Advance, Japanese release](https://raw.githubusercontent.com/libretro-thumbnails/Nintendo_-_Game_Boy_Advance/master/Named_Snaps/Final%20Fantasy%20Tactics%20Advance%20%28Japan%29.png) | Both combatants' statistics visible on the snowy map | Attacker portrait and opposing unit details appear together along the lower edge. | Show selected action and real target results together. Never substitute a decorative fixed damage value for resolver output. |
| [Tactics Ogre: The Knight of Lodis](https://raw.githubusercontent.com/libretro-thumbnails/Nintendo_-_Game_Boy_Advance/master/Named_Snaps/Tactics%20Ogre%20-%20The%20Knight%20of%20Lodis%20%28USA%29.png) | Battle map, leader selected | Several units visibly labeled END; selected leader card bottom-right includes HP/MP. | Retain explicit turn-state feedback, keep End turn fixed, and distinguish spent party members. |

Also inspected Sacred Stones' terrain-inspection view, Advance Wars' attack animation, FFT's dialogue view, and FFTA's unadorned town scene. Those states are not evidence for command-menu or forecast placement and are excluded from the primary comparison.

## What was wrong with our preceding UI

The working source browser fixture had a 103px two-row rail at 1440×1000. Its selected portrait was 36×42px, identity text 15px, and vitals 12px; Move and Actions were plain buttons on the far right. The center of the rail contributed little. This preserved map area but removed the illustrated command deck that gives the concept its identity. Target information was a small chip on the opposite side from the selected character.

The preceding UI was tested for fitting on screen. That is not the same as matching the art or being easy to read. The review uses browser captures for the UI, with a presentation fixture clearly labeled as such. Its simple rectangular room does not represent campaign map quality or prove C# gameplay behavior. The fixture's old reachable list incorrectly included every tile; that fixture has been corrected to a bounded, unblocked movement zone. No movement-rule change follows from that correction.

## Component map: newer combat concept, 1672×941

Approximate hand-measured bounds; coordinates are source-image pixels from the upper-left. These are layout anchors, not a demand to stretch a phone to desktop proportions.

| # | Component | x / y / width / height | Role and implementation direction |
| --- | --- | --- | --- |
| 1 | Objective | 20 / 20 / 412 / 118 | One top-left objective panel, title first. Secondary instructions remain compact. |
| 2 | Phase and round | 1299 / 20 / 355 / 82 | The concept uses the top-right. Current Menu/Camera remain accessible there; phase stays by the objective to avoid overlap. |
| 3 | Action forecast | 20 / 461 / 415 / 240 | Conditional card above the party row. Show action, Mana, range, actual preview results, Details/Review/Cancel. Full exact confirmation remains a modal. |
| 4 | Party selection | 38 / 718 / 509 / 72 | Portrait tabs immediately above the command deck, aligned left. |
| 5 | Portrait and vitals | 35 / 801 / 302 / 107 | Large clickable portrait, character name, labeled red HP and blue Mana bars with numbers. |
| 6 | Movement | 345 / 801 / 175 / 107 | Clearly visible movement capability/spent state. Fold into the character block when width is limited. |
| 7 | Commands | 549 / 795 / 598 / 117 | Illustrated Move, two authored-order abilities, and Actions & Items. All remaining abilities remain in the modal. |
| 8 | End turn | 1360 / 803 / 283 / 86 | Persistent bottom-right control. On phones it takes the bottom row, with existing next-character confirmation. |

The original 1672×941 concept has a deeper bottom deck beginning near y=742, portrait/vitals in the left 37%, commands in the middle 37%, and target readout in the right quarter. The later concept makes room for party selection and End turn. This pass follows the later composition, retaining the original navy/gold material, illustrated commands, and strong character identity.

## Scope and acceptance

- [x] Inspect and cite real game screenshots.
- [x] Locate both exact generated concept sources.
- [x] Record component coordinates before changing the layout.
- [x] Capture the preceding source UI in a browser and distinguish it from the deployed build.
- [x] Validate larger portrait, readable HP/Mana bars, illustrated command tiles and bottom End turn at desktop and phone sizes.
- [x] Verify quick-action selection, modal access, forecast-state controls and enemy-phase disabled commands in browser fixtures.
- [x] Compare the revised browser screenshots with the concept and record remaining differences.

This is a HUD composition pass. It does not recreate the concept's isometric camera, handcrafted room, dramatic effects, terrain geometry, or every depicted mechanic. The square-map requirement and shared C# resolver remain intact. Research screenshots are reference material only; they are not shipped as game assets.

## Second clarity pass

- [x] END and DOWN labels on portraits supplement opacity and color.
- [x] Desktop movement has its own readout; End turn names the actor and previews the next actor using the same helper as its confirmation.
- [x] Targeting immediately shows the ability illustration and description. Status-only and Mana-only forecasts use the existing resolver data.
- [x] Active narration remains visible in a separate strip while targeting.
- [x] Action modal uses the same navy/gold frame treatment and Mana terminology.
- [x] Expanded presentation checks cover 60 states. Error toasts now fail the fixture suite.
- [x] Real-game capture for `05db6de` verified forecast cancellation preserves the save, Carl → Donut → Katia → Mongo turns, and round2 after enemies. [Capture run](https://github.com/cehinds/dungeon-crawler-tactics/actions/runs/40435988421).
- [x] The real mobile capture exposed truncated Donut command names and a toast over the objective; the follow-up wraps names and separates feedback.
- [x] Second-pass Pages deployment succeeded: [run 40437214998](https://github.com/cehinds/dungeon-crawler-tactics/actions/runs/40437214998).

## Third pass: menu scaling and scrolling

- [x] Abilities/Items tabs expose supplies without scrolling past locked skills.
- [x] Action header, category tabs and three-button footer sit outside the list scroller. Dialog height follows its content up to a viewport limit.
- [x] Forecasts show signed HP changes and before/after numbers together; reaction details expand separately.
- [x] Character sheets use compact resources and fixed navigation; the active panel owns scrolling.
- [x] Phone targeting is smaller; full action details stay accessible.

The concept's illustrated hierarchy remains the reference. This pass reduces repeated chrome and nested scrolling rather than scaling down the entire interface. Long inventories and progression lists still scroll, while their navigation remains visible. Current validation and screenshots are recorded at the top of `design-qa.md`.

## Fourth pass: compact command list and exact target comparison

The preceding action menu repeated a description, source, rank progress and availability message on every large card. A compact command list with one focused detail panel gives each command one place and uses the available space to explain the current choice. The FFT PSP capture supports the short command-list pattern (Move/Act/Wait/Status/AI); the FFTA capture supports showing both combatants' results together. Nintendo's [FFT battle-options guide](https://www.guiasnintendo.com/1_GAMEBOY_ADVANCE/finalfantasytactics/fftactics/opcionesbatalla.html) names Move, Action (special skills/items), Wait and Status. The visible stills guide layout only; they do not establish interaction behavior or additional rules.

- [x] Replace repetitive command cards with a compact keyboard-navigable list and one detail panel on hover/focus. Support ArrowUp/ArrowDown, Home/End, Enter to select and Escape to go back. Unavailable or locked skills remain inspectable but cannot activate.
- [x] On phones, place the detail panel above the command list. Keep Back, Move and End turn in a fixed footer.
- [x] In the action forecast, previous/next legal-target controls compare exact C# previews without spending resources. Keep the same ability, cast mode and item while changing the target.
- [x] Preserve the existing navy/gold command-menu style. This pass needs no new graphics or rule changes. Special forms, stances, Favor and capture remain outside scope.
- [x] Compared the user’s combat concept and reference screenshots with desktop, phone and landscape browser captures.

The old cards gave every description equal visual weight. The list keeps command selection together, while the single panel explains only the currently pointed-to choice and the forecast controls let players inspect other legal targets using resolver output. The browser implementation uses `command-menu.css` for the command list and forecast navigation. Dialog geometry stays fixed while descriptions change, preventing pointer targets from shifting. Long descriptions can scroll within their bounded detail panel; the command list scrolls independently, with no nested page scrolling.

Validation: the four-viewport command fixture covers pointer/keyboard input, disabled commands, long names, stable row positions, item scrolling and fixed controls. The existing 70-state HUD fixture and rank fixtures pass. A published C# WASM test verifies legal-target wraparound, byte-identical cancel, exactly one chosen target damaged, one Mana charge and practice use, movement after casting, and advancement to the next ready ally. The generated-map test uses explicitly seeded enemy positions/HP; it does not claim the fixture was earned through campaign play.

## Fifth UX pass: activation and targeting clarity

This pass applies the compact status-feedback approach of the references above to the game’s independent movement and action budgets. These are presentation changes, not new combat rules.

- [x] Give Move and Act independent ready/spent checks on party portraits; strike through the spent part. Keep END and DOWN visibly distinct.
- [x] During targeting, keep the acting unit, legal targets and selected preview in view without covering the HUD. Preserve manual pan on unchanged targeting and the selected target when reframing. For large terrain-target sets, prioritize occupied legal tiles plus a local sample rather than every legal tile.
- [x] Match invalid-click guidance to the command's target type and team legality, rather than always suggesting a terrain target.

Validation: the 70-state HUD suite, four-size command menu and readiness fixtures, and 16 target-camera scenarios pass. Camera checks also cover four rotations, resize continuity and unchanged-render pan preservation. The actual published C# WASM flow verifies invalid-target/save preservation, exact target confirmation, independent action/movement readiness and party advancement. A fresh-run screenshot walkthrough covers exploration, targeting, party turns and the enemy phase. Numeric rank rules and Unity presentation are unchanged.

The preceding Pages run failed its 320px command-row height check with the CI system font. Command names now wrap to at most two visible lines; the selected detail panel retains the complete name. A monospace-font stress case verifies the compact row budget without relaxing it.
