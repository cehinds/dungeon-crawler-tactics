# Art direction: readable pixel tactics

The working language is **navy panels, brass framing, cream text and cyan selection**, with warm orange reserved for declared danger. The board, character silhouettes and next decision come first. Generated illustrations establish direction; live labels, values, controls and combat forecasts remain native interface elements.

## References reviewed

These are reference studies, not sources of reusable game assets. The practical recommendations below are our design interpretation.

| Official reference | What the source establishes | Guidance for this game |
|---|---|---|
| [Nintendo: Fire Emblem on GBA](https://www.nintendo.com/en-gb/Games/Game-Boy-Advance/Fire-Emblem-266738.html) | Character classes, terrain/weather and approachable controls are central to its tactical presentation. | Keep units recognizable at board scale; expose terrain and action choices without burying the playfield. Use concise text beside portraits and icons. |
| [Square Enix: Final Fantasy Tactics art](https://na.store.square-enix-games.com/the-art-of-final-fantasy-tactics) | Official development art includes character/job illustrations and rough map designs. | Give classes a consistent silhouette vocabulary and maps a clear spatial hierarchy. Study composition; do not copy character designs, UI frames or map assets. |
| [Square Enix: Tactics Ogre Reborn](https://www.square-enix-games.com/en_GB/news/tactics-ogre-reborn) | Its publisher describes preserving detailed pixel art while redesigning the interface for easier understanding. | Preserve crisp sprites while allowing readable modern text and larger controls. “Retro” must not mean tiny or ambiguous. |
| [Subset Games: Into the Breach](https://www.subsetgames.com/itb.html) | The official description emphasizes telegraphed enemy attacks and deliberate counters. | Show the authoritative intent footprint, timing and counterplay before commitment. Danger must be readable independently of animation. |

The Subset description was available through its indexed official page; direct retrieval returned 403. The Square Enix Tactics Ogre article was available in indexed official text although the current page shell omitted its article body. No community-forum claims are used as developer statements.

## Implemented inventory and its limits

- [UI kit manifest](https://github.com/cehinds/AI-Art/blob/dungeon-crawler/dungeon-crawler-tactics/Web/wwwroot/assets/ui-kit/manifest.json): **12 individual 128×128 PNG icons**—kick, bomb, missile, move, heart, mana, guard, bag, skills, quest, wait and potion.
- [Room kit](RoomKit.md): **25 transparent PNG pieces**, with measured anchors and layer metadata in the [manifest](https://github.com/cehinds/AI-Art/blob/dungeon-crawler/dungeon-crawler-tactics/Web/wwwroot/assets/room-kit/manifest.json).
- [Expedition enemy manifest](https://github.com/cehinds/AI-Art/blob/dungeon-crawler/dungeon-crawler-tactics/Web/wwwroot/assets/expedition-enemies/manifest.json): **six four-frame strips**—sludge, cinder, frost, spore, sentry and mauler. Each frame is 160×160, anchor `(80,148)`, with a 108-pixel body-height reference. These are authored game archetypes, not six verified novel species.
- [Menu atlas](../Web/wwwroot/menu-atlas.html): **six generated menu sheets and 30 separate interactive HTML component previews**. The sheets are downloadable concept PNGs; the preview values are illustrative and do not alter saves.

The new [personal-home sheet](https://github.com/cehinds/AI-Art/blob/dungeon-crawler/dungeon-crawler-tactics/Web/wwwroot/assets/menu-concepts/safe-room-services.png) replaces the earlier cave-like safe-room concept: individual crawler rooms connect to communal living, training and crafting spaces. Use the housing floorplan and installed-room states to communicate ownership and access. An old cave illustration is not evidence that personal housing is merely a battle room with service buttons. See [housing research](Research-Housing.md) for the distinction between sourced facilities and game adaptation.

## Palette and interface tokens

The live game's current base tokens are defined in [game.css](../Web/wwwroot/game.css); the atlas has a related, deliberately darker presentation in [menu-atlas.css](../Web/wwwroot/menu-atlas.css).

| Role | Live base token | Use |
|---|---|---|
| Background | `--bg: #10151f` | Recessive application canvas |
| Panel | `--panel: #1b2532` | Information and command surfaces |
| Raised surface | `--panel2: #242f3e` | Controls and secondary regions |
| Text / muted | `--ink: #f2efdf`, `--muted: #a7b3c0` | Primary facts / supporting explanation |
| Brass | `--gold: #edc77d` | Primary action, selected identity, hierarchy |
| Cyan | `--blue: #83c5d6` | Focus, selection and movement context |
| Red / green | `--red: #e69887`, `--green: #aacb9e` | Harm or loss / recovery or improvement |

Color is reinforced with labels, shapes and numbers. Cyan reach, amber danger and gold target tiles need a legend; HP and Mana bars need explicit values. Avoid adding new colors for every category. Use restrained square frames, consistent gutters, readable system text and monospace labels; keep pixel styling in the artwork rather than rasterizing functional copy.

## Grid, anchors and rendering

The runtime and workshop share a **128×64 logical diamond**, not a guarantee that every PNG is exactly one tile. Room floor pieces include padding: typical normalized floor PNGs are 132×68 with anchor `(66,34)`. Project the cell, then place its measured asset anchor at that center. Preserve character foot anchors and source proportions; never center a tall sprite by its image bounding box.

Draw floors and ground surfaces first. Depth-sort upright structures, props and units; render projectiles, fire, impacts and floating text above occluding units/walls. Decorative size does not silently enlarge a unit's collision footprint. Camera rotation and placed-piece rotation are separate. [Room-kit anchor and layer contract](RoomKit.md)

A new asset must supply a stable manifest ID, dimensions, anchor, layer and logical footprint. Animation strips also declare frame dimensions and count. Art must not create a visible door, hazard or obstacle whose logical behavior contradicts its presentation.

## Readability acceptance

Before shipping a change, inspect desktop and phone portrait/landscape at normal zoom. Keep the objective, selected crawler, remaining allowances and next threat visible. Check text contrast, keyboard focus, meaningful disabled reasons, touch-sized controls, scrollable dialogs, and reduced-motion behavior. Never rely solely on color, hover, sound or flashing effects. On a crowded board, simplify decoration before shrinking the information needed to make a decision.

These are production criteria, not a claim of complete native Unity validation or exhaustive accessibility compliance. All imported/generated art remains subject to visual alignment and behavior checks in the actual renderer.
