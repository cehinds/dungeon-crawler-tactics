> Historical planning/starter reference. For the implemented playable game, current content and setup, see [PlayableGame.md](PlayableGame.md). The original starter fixture is retained for regression tests.

# Unity Web implementation target

## Current status

This repository is a design and source starter kit. It is not an exported Unity Web game. No Unity Editor, Unity Web Build Support module, live scene or Unity MCP connection was available during authoring. C# kernel verification and browser wireframe checks are distinct from Unity import, Play Mode and Web player verification.

Use Unity 6 LTS with the Web Build Support module. Pin the exact editor patch in the real project once selected. Start from the 2D Built-in template; add URP only when a concrete lighting requirement justifies it. Import the supplied source folder into `Assets/DungeonCrawlerTactics`. Keep gameplay code independent of the render pipeline.

## Intended assembly boundaries

```text
Assets/DungeonCrawlerTactics/
  Runtime/
    Core/            Plain C# definitions, tags, state, commands, resolver
    Data/            Human-authored JSON loaded as TextAsset
    Unity/           MonoBehaviour adapter and presentation boundary
  Editor/            Later: validators, import helpers, content inspector
  Tests/             Later: Unity EditMode and PlayMode integration suites
```

The starter may organize these names slightly differently; use the actual source tree as authoritative. The separation matters: core has no `UnityEngine` dependency; Unity integration references core; editor references runtime, never the reverse. Small files named for the responsibility are preferred over one manager for the entire game.

For the finished game, use `Boot`, `Camp` and `Battle` scenes, with one explicit composition root that supplies the content catalog, run state, command handler and presenters. Persist state as data, not references to scene GameObjects. No global mutable combat singleton.

## Board and UI

Use a flat 2D orthographic grid, four cardinal facings, sorting by board Y and an optional small sprite shadow. Keep coordinates integer and rules independent from sprite positions. Animation plays event results after the simulation commits; animation completion must not decide damage or turns.

Use UI Toolkit for the finished HUD, driven by view models. A selected unit panel, action bar, tile inspector, forecast, party roster, camp and floor route map are specified in `Wireframes/index.html`. The HTML is a clickable planning artifact; it is not embedded in Unity and does not contain the production resolver.

Pointer hover must have an equivalent selection/tap inspection path. Show hazard patterns, names and icons; color is supplementary. Make menus at least 44 CSS-equivalent pixels at default browser scale. Support 1280×720 and 1920×1080 desktop; design tablet fallback before claiming touch support. Suspend hotkeys when a text field has focus. Escape closes/cancels; Enter confirms only when a visible confirmation has focus.

## Pixel art specification

- Characters: 128×128 transparent source frames, feet pivot `(0.5, 0.16)`, consistent scale and four directions. Start with idle 2, walk 4, attack 4, hit 1, downed 1 frames per direction. Mirroring is permitted only where equipment asymmetry does not matter.
- Tiles: 64×64 top-down cells; characters may overhang their footprint. Keep collision exactly one logical cell, independent of drawn width.
- UI icons: 32×32 or 48×48; portraits 128×128. Palette and silhouette distinguish class roles; no text baked into sprites.
- Unity import: Sprite (2D and UI), Point filtering, mipmaps off for sprite/UI atlases, appropriate lossless or tested compression, consistent pixels-per-unit. Test integer camera scaling on the chosen reference resolution.
- Atlas by encounter/theme and character set. Avoid one atlas containing every future floor. Audit sprite padding and alpha edges at browser zoom levels.
- These are production guidelines. The supplied wireframes use schematic tokens, not a finished sprite pack.

## Browser-safe data and saves

Load built-in JSON through serialized TextAsset references. Do not assume ordinary filesystem APIs work in a browser. Optional remote packs must be versioned and loaded asynchronously through UnityWebRequest, with explicit CORS, failure messages and an offline fallback.

Planned save envelope: `saveVersion`, `contentVersion`, `contentHash`, `runId`, seed/RNG state, floor/encounter ID, party, inventory, tile/unit state, active team, activation budgets and completed reward IDs. Use stable string IDs, never array indices or Unity instance IDs. Migrate version N to N+1 explicitly; preserve an original copy until migration validates. Save one immutable committed snapshot after an action, not a partially resolving chain.

Implement an async browser persistence adapter backed by IndexedDB (Unity persistent storage or an explicit JS bridge). Treat flush completion as part of the save acknowledgement. Keep one previous snapshot. Handle quota/private-mode failures with a visible warning and export option. Provide JSON export/import through browser file APIs; validate schema, bounded sizes and references before replacing the live save. Cloud saves are later work, not required to finish version 1.

## Practical budgets

Initial targets to measure, not claimed results: compressed first-play download ≤25 MB; first interactive screen ≤10 seconds on a representative broadband connection; process memory ≤256 MB on the smallest supported device; stable 30 FPS minimum at 720p. Measure browser memory and Unity profiler separately. Simulate on commands, not every frame. Bound reaction queues and candidate AI searches. Pool effect visuals only after measurement identifies a need.

Use no runtime code generation, reflection-discovered effects, blocking waits or required background threads. Register effect opcodes explicitly. Make content validation an editor/build step, while retaining runtime bounds checks. Start single-threaded to simplify hosting and cross-origin header requirements.

Audio begins after a user gesture. Pause presentation and preserve committed state when the browser loses focus. Avoid treating background-tab timer throttling as game time. The game is turn-based; there is no reason to make a player lose a turn while switching tabs.

## Build and host procedure — to run once the Unity project exists

1. Install the chosen Unity 6 editor patch and matching Web Build Support module.
2. Create the 2D project, copy the source kit into Assets, and follow the README demo wiring. Resolve all Console errors before UI work.
3. Create real Boot/Camp/Battle scenes. Add only actual finished scenes to the Web build profile. Select the Web platform in Build Profiles.
4. Run EditMode tests, PlayMode scenarios and a local development build. Keep development builds separate from release builds.
5. Choose compression supported by the host. Configure correct `.wasm` MIME and compression headers for compressed assets, or use Unity's decompression fallback when host configuration is unavailable. Test with an HTTP server, not `file://`.
6. Verify the real hosted origin: load and refresh, audio after gesture, save/refresh/import, browser focus, window resize, texture rendering and cache invalidation after a content update.
7. Publish only after the first-floor acceptance checklist passes. Preserve the previous exported build and content version for rollback.

Support initially means latest stable Chrome, Firefox, Edge and Safari on desktop, verified on actual supported OS/browser combinations. Mobile browsers are a separate measured support decision. No hosted build or publication is performed by this starter task.
