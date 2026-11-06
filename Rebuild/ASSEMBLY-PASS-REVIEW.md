# Assembly catalog pass review

## Scope

This pass adds 13 catalog templates for authored composite groups. It preserves all 47 existing object, terrain, and world-object type IDs and does not change placement surfaces or connector geometry. The outlet mouth adds the existing `fluid` connection tag so its fluid-output port is mutually compatible with the pipe ports accepted by `validateConnection`; this changes only declared port compatibility and creates no attachments. Assembly membership is keyed by each runtime prop's exact `roomId` and `groupId`; assembly member roles refer to existing object type IDs.

## Evidence

Each generated world seed has 31 runtime assemblies and there are 13 catalog templates; some authored groups intentionally remain generic and unclassified, which is not an error. The northwest-machinery template matches that exact groupId in both industrial rooms. The catalog entries are grounded in `Web/wwwroot/data/concept-room-rules.json`. Runtime examples are present in the committed `Tools/fixtures/object-scenes.json`, including the entry stair approach, tutorial teaching table, Tally dining cluster, waiting area, Sebastian bedroom and washroom, and workshop machinery, pipe banks, and gate lights. The boss complex has its own `north-descent` group. Assembly bounds are runtime member bounds; catalog placement anchors are authored anchor guidance and are not suggested nearby positions.

Required members represent the identifying fixture(s) for a declared group. Chairs, rug underlays, bedside lamps, machine pipe fittings, and vending machine companions remain optional diagnostics. The catalog does not treat these declarations as universal room requirements or infer physical pipe connections. The outlet mouth is tagged `water` and `fluid`, allowing mutual compatibility with pipe `fluid` ports in `validateConnection`. This is metadata for compatibility checking only; it does not establish flow direction or create an attachment, and the mouth remains a discharge port rather than a feed inlet.

## Review status

Final bounded QA passed for seeds 1337 and 42. Each seed reports 31 runtime assemblies, including the reusable `northwest-machinery` template in both industrial rooms. Inspector checks covered parent/member selection and highlighting, compatible and rejected port candidates, accepted and out-of-bounds placement suggestions, graph JSON export matching the displayed graph, unchanged source worlds, mobile layout, and zero browser errors. Published-host gameplay checks passed keyboard/canvas encounter flow through victory. The C# core suite, portable scene-graph suite, Web publish with the 91 checksum-verified assets, and required floor-one playtest passed.

The latest inspector report, verification records, screenshots, and comparison gallery are retained under `Rebuild/AssemblyPassComparison/final/` and the pass comparison directory. Full arena replay was not part of this bounded pass; prior arena evidence remains unchanged. Port compatibility is metadata validation only and does not establish flow direction or create physical routing.
