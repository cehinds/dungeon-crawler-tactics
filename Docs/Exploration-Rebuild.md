# Exploration rebuild

Exploration should make dungeon floors feel like places the party can cross and revisit while keeping the existing tactical battle as the main event. A floor is one connected walkable space with visible threats and quieter ambushes; entering an encounter switches to the current turn based tactical board, and victory returns the party to the same floor. Use the classic room, corridor, path, and landmark vocabulary, with visible enemies as the newer layer. Keep combat rules and its forecast/commit flow intact.

## Reference principles

These games are references for authored exploration, not examples of procedural generation.

| Reference | Useful observation | Adaptation here |
| --- | --- | --- |
| [Final Fantasy II Pixel Remaster](https://www.jp.square-enix.com/pcgamehub/title/ff_pixelremaster/ff2/index.html) | Towns, dungeons, and world travel use distinct spaces and readable routes; menus support deliberate party and equipment choices. | Make the floor route legible, then keep loadout choices close to a safe hub. Do not copy its encounter or progression rules. |
| [Golden Sun](https://www.nintendo.com/eu/media/downloads/games_8/emanuals/game_boy_advance_8/Manual_GameBoyAdvance_GoldenSun_EN_DE_FR_ES_IT.pdf) | Field abilities let the player read a small environmental problem, apply a known ability, and see an immediate change. | Use a small authored vocabulary of switches, blocked passages, movable objects, and elemental interactions, each with a clear clue and visible result. |
| Pokémon Emerald | Routes connect settlements and landmarks; optional branches, shortcuts, and return paths make navigation memorable. | Connect floor zones through a main route, with short reward branches and loops that reconnect to known ground. |
| [The Legend of Zelda: The Minish Cap](https://www.nintendo.com/en-gb/Games/Game-Boy-Advance/The-Legend-of-Zelda-The-Minish-Cap-267486.html) | Distinct landmarks and compact side paths give useful orientation; exploration rewards attention as well as forward progress. | Give every generated zone a readable landmark or material cue, and put discoveries just off the travel line rather than behind opaque dead ends. |

These are design inspirations, not a claim that we playtested those titles during this pass. The official FFII overview, Golden Sun manual and Nintendo Minish Cap description provide reference context. The procedural rules below are our own adaptation.

## Proposed floor rules

1. **Reserve the route before decoration.** Choose a stable entrance, exit, and 3–6 zones. Build a connected main path between them, then add a limited number of branches, loops, and optional ports. Reserve clear spawn pads at the entrance, each encounter site, and the exit before placing walls, props, discoveries, or enemies.
2. **Keep every objective reachable.** Run a flood fill over walkable cells after generation. Require the exit, every encounter trigger, every required quest point, and each intended branch endpoint to connect to the entrance. If a required connection fails, retry that room connection or reject the seed. Optional rewards may be missed by choice, never by accidental disconnection.
3. **Use doors as graph links.** A door has a stable ID, a source edge, a destination zone or port, and an open/locked state. Align cells and rotations at joins before committing the map. A locked door must name a reachable key/objective; don't seal the only route behind its own lock.
4. **Protect boundaries and compatibility.** Keep generated walkability and collision authoritative. Fit visual tiles against their edge connectors after the floor graph is valid; rotate tiles with their edge metadata. When no compatible art fits, use the canonical neutral tile or report the kit mismatch, never silently alter collision to make art fit.
5. **Mix threat types.** Mark encounter groups as visible or ambush. Visible groups appear in exploration and trigger when approached. Ambushes use a short, bounded trigger radius or a marked danger zone. Both lead into the existing tactical battle, with clear warning, retreat where topology permits, and the same party, forecast, and turn rules.
6. **Make movement continuous and readable.** The party walks tile by tile with directional facing and animation; camera follows within floor bounds. Movement input can be held/repeated with a small step cadence, while interaction is explicit. Enemies do not start combat through a long silent teleport or an unexplained screen transition.
7. **Put puzzles in data.** A puzzle records its visible clue, required interaction or field ability, changed tiles/door state, and completion flag. Place clues before the relevant decision point. Puzzle state, discoveries, defeated groups, and current position persist in the floor save.
8. **Give the hub physical space.** The safe camp is a compact walkable room with clear service points for rest, equipment, skills, and the floor entrance. Keep quick menu access for players who prefer direct navigation.

For bounded generation, start with a small set of zone templates and graph shapes rather than unconstrained cell noise. Seed the topology, feature placement, and visual fitting separately but deterministically. Validate each layer: graph reachability, collision/spawn clearance, encounter and quest reachability, then art-edge compatibility. Store the resulting canonical map and stable feature IDs in the save so later rule changes cannot reshuffle a live run.

## Data shape

Keep authored content in JSON and runtime rules in the shared C# core. A floor plan should carry a schema/version, seed, dimensions, canonical collision tiles, presentation placements, entrance and exit, zone/door graph, encounter groups, discoveries and quest objectives, puzzle definitions, and reserved spawn pads. Each dynamic record gets a stable string ID. Save state separately carries player position/facing, revealed cells, opened doors, puzzle flags, claimed discoveries, defeated group IDs, and the active encounter ID. Validate bounds, ID uniqueness, enemy ownership, spawn overlap, and graph connectivity on import and save load. Keep presentation asset IDs optional so missing art cannot invalidate a playable map.

The current room kit already separates canonical gameplay tiles from optional placed-art metadata, and the tile-edge fitter only changes visual choices. Reuse that separation for generated floors rather than making art tags determine navigation.

## Original continuous-floor foundation

Validated locally on 2026-10-29 against the published shared-C# WebAssembly build.

- [x] A default 40×32 continuous floor with five connected zones, two-wide routes, a loop, side discoveries, and an entrance/exit.
- [x] JSON-authored generation rules, schema, seeded placement, reserved routes, and existing square-tile edge fitting. Required points are checked for reachability.
- [x] Hybrid encounters: three visible groups and one danger-area ambush. Visible groups trigger within three walkable steps; ambushes check every eighth step within four walkable steps. This is bounded, deterministic encounter timing rather than unrestricted random battles.
- [x] Existing tactical combat, forecasts and turn sequence. A victory clears only the active encounter group; other groups remain on the floor.
- [x] A cache, exit-seal objective, fog-of-war map, and saved discovery/encounter receipts. Exit requires the objective and cleared encounters.
- [x] One animated party leader in exploration, using existing four-direction idle/walking frames; held WASD/arrows or touch controls, interpolated steps, and a following camera.
- [x] Walkable safe-room hub with rest, equipment, training, crafting, personal-space and dungeon stations; quick menu access remains available.
- [x] Field equipment modal using actual owned gear, stat changes and granted skills. Swapping gear clamps current HP/Mana without healing; combat still blocks equipment changes.
- [x] Returning home and resuming preserves the current floor, position, discoveries and defeated groups. Starting a new generated floor explicitly replaces the run after a warning.
- [x] Movement saves after 300 ms without another step; other state-changing commands save immediately. Opening field menus and hiding the page flush pending movement saves.
- [x] Shared C# source mirrored into the Unity project. Unity Editor execution remains unverified; the new visual hub/field presentation is browser-specific.

### Source map

| Source | Responsibility |
| --- | --- |
| `Web/wwwroot/data/exploration-floor-rules.json` | Bounded zone graph, dimensions, links, encounter recipes and discovery definitions |
| `Schemas/exploration-floor-rules.schema.json` | Authoring schema; runtime additionally validates relationships |
| `Web/wwwroot/exploration-floor.js` | Deterministic routes, placement and generation validation |
| `UnityPackage/Runtime/Core/GameSession.GeneratedFloor.cs` | Floor imports, movement, encounters, discoveries, safe-room resume and save validation |
| `Web/wwwroot/camp-hub.js` / `.css` | Walkable home and service navigation |
| `Web/wwwroot/field-ui.js` / `.css` | Compact field controls, discoveries and revealed map |
| `Web/wwwroot/exploration-controls.js` / `battlefield.js` | Held input, directional animation, interpolation and camera |

### Validation

- 28 focused continuous-floor checks; 65 custom-map checks; 223 general game checks; core compatibility build.
- 200 generated seeds and 18 invalid-rule cases; existing 720-map regression; native-art rotation/serialization tests.
- Actual browser lifecycle: hub → generated floor → exploration → tactical battle → reward → same floor; equipment, once-only cache, home/resume, save/reload and modal movement blocking.
- Phone/desktop layouts at 320×740, 390×844, 844×390 and 1440×1000, plus directional motion and existing combat-facing checks.
- Isolated local desktop Chromium measurement: seven steps over 1.057 seconds, 64 animation frames averaging 16.51 ms (about 60 fps). This is measured local behavior, not a guarantee for all devices.

### Remaining exploration work

- [x] Connect generated floors into a persistent adapted expedition. The [generated campaign](Generated-Campaign.md) adds three depths with party/resource carryover and saved archives. Story floors 1–8 retain their authored route; the full procedural book campaign remains future work.
- [x] Add three authored graph families and per-depth environment/encounter/objective recipes for connected expeditions. Seeds still operate within bounded authored layouts; broader biome systems remain future work.
- [ ] Reusable keys/locked doors, field abilities and multi-step environmental puzzles. These are design targets above, not current generalized systems.
- [ ] More equipment drops, rarity/progression tiers, and visible equipment attachments. This pass exposes the existing six gear pieces during exploration; it does not create a new item catalog or armor overlays.
- [ ] Distinct overworld travel, settlements and book-specific floor simulations.

## Separate book-content backlog

The exploration rebuild does not attempt to finish every book. Keep the existing bounded playable scope, and track deeper fidelity separately: later floors and their distinct mechanics, class/rank/economy curves with source-specific evidence, full race and companion progression, and remaining encounter/club/plot systems. See [Book fidelity checklist](Book-Fidelity-Checklist.md) and [Story levels](Story-Levels.md) for the existing inventory and adaptation boundaries.
