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
- [ ] Final follow-up deployment is tracked by GitHub Actions; a passed capture does not imply the Pages deployment is finished.
