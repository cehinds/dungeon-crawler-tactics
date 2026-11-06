# Depth pass review

Compared the supplied clean map with the published seed-1337 boss capture in `MasonryPassComparison/source-vs-final-boss.png`. This is a visual gap review for a draw-only pass. The room shape, water boundaries, routes, collision, and gameplay remain fixed.

## Review results

- [x] **Perimeter depth:** Raised coping inside blocked cells exposes the blue wall face and contact shadow; south parapet face gradients add depth. Boundaries and floor proportions stay fixed.
- [x] **Pipe continuity:** An eastern peripheral pipe elbow now connects visibly to the channel bank.
- [x] **Blocked-cell accents:** Two southern vine tails are placed within actual blocked-cell bounds.
- [ ] **Masonry and coping variation:** The pass does not broadly vary masonry or break up every regular coping run; those source differences remain.

## Review status

The seed-1337 boss capture is `DepthPassComparison/pass-01/seed-1337-boss.png`. Final integrated browser QA also captured seed 42 battle state with the eastern pipe, and checked doorways and full bridge crossings for both seeds. Arena evidence was reused where recorded by the harness; the seed-42 battle capture was refreshed. These checks do not claim a full source-art match.

## Scene-graph review scope

The new inspector presents a 47-type catalog (27 props, 12 terrain/render components, and 8 world-object/interaction kinds). Its room and surface hierarchy represents containment. Actual runtime edges, geometric connector relationships, and advisory expected relations are shown separately so a tree parent is not mistaken for an object connection. Placement checks cover catalog surface support, runtime footprint overlap, explicitly required relations, and route preservation. Preview, suggestions, and graph JSON export use a copied world and do not commit a placement.

The pure JavaScript graph supplies presentation geometry and connector data to the renderer. C# remains authoritative for world generation and gameplay. Declared ports are metadata; active pipe attachments follow geometric catalog connector rules, not a general compatible-port solver. The inspector is available at `http://localhost:8765/object-inspector.html` after publishing and serving the Web app. Contract fixtures are in `Tools/fixtures/object-scenes.json`; the Node.js check is `node Tools/test_map_scene_graph.mjs`.

## Final QA status

Final published-host QA passed. The inspector was checked at both seeds for room/node groups, valid in-world props, invalid out-of-bounds props, placement suggestions, JSON export, and unchanged generated worlds; mobile layout was also reviewed. The scene-graph suite accepted all 132 baseline prop placements across seeds 1337 and 42. Published-map checks covered both seeds’ doorways and full bridge crossings, and refreshed the seed-42 battle capture with the eastern pipe visible. The layered-map harness reused arena evidence (`arenaReused: true`); its seed-42 capture was rerun, with a short synthetic key hold initially missed after 25 ms and then captured at 80 ms. Focused scene-graph tests and the published browser checks passed. The earlier C# suite, publish, 91-asset restoration, floor-one flow, and full-arena checks are retained from their prior run; they were not rerun as part of this final affected-scope QA. Masonry and coping variation remains an acknowledged visual gap.
