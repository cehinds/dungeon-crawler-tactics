# Book 1, Floor 1 playable route

[`book-one-floor-one.json`](../../Web/wwwroot/data/book-one-floor-one.json) defines a seeded, continuous 40×32 playable floor with 12 physical districts and one nonphysical guild-rumor interaction. The districts are generated as connected regions in one map, so preview, export, and Play use the same realized floor. Positions organize the authored graph; they do not assert canonical coordinates or a measured floorplan.

## Route and evidence

The publisher’s Book 1 sample supports the opening descent and Kua-tin threshold. A Book 1-only chapter guide gives the broad story sequence through the goblin alley, Hoarder’s lair, Polish restaurant safe room, goblin workshop, creature territories and Juicer’s gym, then the long trip to the Ball of Swine spiral. The Ball of Swine reference cites Chapters 21–27 for the maze, bridges, switch chamber, construction, arena reveal and stairwell. The catalog records the sources and what each supports.

The route graph connects those named places for play, but every graph connection is an inference: available sources establish locations and a broad sequence, not exact adjacency or a complete First Floor map. The links are navigation connections, not corridor quest locks. Optional branches include Tally’s restaurant, Sebastian’s Peruvian Taco Bell, the DMV safe room and Meadow Lark’s camp. The Alabama Waffle House and candy-vending stop are only reports heard at the Tutorial Guild; they are not physical districts or established Carl visits.

Tally’s play area stays within the same safe room. The Ball of Swine switch chamber, Speedbump construction area, revealed arena and stairs are subregions or encounter states inside one boss district. Territory labels refer to creature areas, not official neighborhood names. The 36 concept panels include views, subregions, routes, reported places and generic concepts; they do not represent 36 unique canon locations.

## Gameplay and presentation limits

The regional catalog uses `scenario.hoarder`, `scenario.juicer` and `scenario.swine` as references to existing story-themed scenarios. The continuous 40×32 floor does **not** launch those named scenarios. Its tactical encounters are five authored groups of existing enemy templates placed on the floor. The regional catalog’s lore references and the continuous floor’s actual combat setup are separate layers; neither claims to recreate the novel’s party, timeline or combat exactly. The Murder Dozer and goblin workshop remain story locations/objectives without invented encounter IDs.

Corridor links are navigational and do not impose quest locks. To finish, the player must complete every required region objective and clear all five tactical encounter groups before interacting with the exit. Optional-region objectives are not required for floor completion.

The gameplay preview and C# runtime now use the same saved map descriptor for whole-object props, including stable asset IDs, native footprints, rotations, layers, and collision. Floors and walls use the existing Book Location Tiles art; props use the reusable whole-object PNG library. The shared renderer preserves prop placement and collision between preview and runtime. Exported descriptors are validated against known assets and collision data; older maps without descriptors remain valid and use their existing generic presentation. This visual integration does not make the layouts or art canonical to the novel.

Mordecai appears as a Tutorial Guild guide and is not a deployable party member. Katia’s presence in the broader runtime roster does not establish her involvement on Floor 1. Floor 3 class unlocks are outside this floor’s scope.

## Walk-first exploration and map reference

In the hosted game, `index.html?book1=start` starts the continuous 40×32 C# exploration floor; an existing Book 1 run resumes in place, including after a safe camp. Hold WASD or the arrow keys, or hold the touch direction pad, to walk one direction at a time. The camera follows the player. Press E or Space, or use the nearby interaction button, to inspect a nearby point or interact. Approaching a tactical encounter group starts the existing grid combat automatically. Combat rules and battle mode are unchanged; this adds no Final Fantasy II-style combat system. Use the optional map drawer as a reference: selecting a district does not teleport the player.

The standalone browser preview also starts with direct walking and a following camera. It supports collision-aware movement and nearby discovery/encounter notes, with the map available as an optional reference. Those notes are preview-only; the standalone preview does not run combat or advance game progress. Export its floor JSON to play it through **Save & Options → Load workshop map or floor** in the game. The preview draws whole-object sprites and blocked cells for the generated layout; the runtime uses existing game art, so artwork can differ while gameplay geometry and collision remain tied to the exported floor.

## Generated optional side rooms

[`book-one-location-archetypes.json`](../../Web/wwwroot/data/book-one-location-archetypes.json) supplies eight reusable side-room archetypes for seeded generation, with four to eight optional instances per floor. They anchor only to existing Floor 1 districts and use existing prop and cache IDs. Each archetype has `inferred_generic` or `inferred_context` evidence status and a canon note: the supported evidence concerns its host context (such as rubbish in the Hoarder’s lair, a goblin workshop, gym equipment, torchlit passages, or established safe rooms), while the side-room name, layout, furnishings, and cache are game-authored. No archetype adds an enemy group, protected safe zone, required objective, new named canon place, or later-floor element. `allowedEnemyTemplateIds` is empty throughout; the catalog’s creature-area wording does not authorize additional enemies.

The Book 1-only First Floor chapter guide supports the broad habitat motifs used here—goblins, llamas, Hoarder rubbish, a workshop, slimes, Rot-Stickers, troglodytes, and the Juicer’s gym—but does not establish these supplemental side-room layouts. [Crawler 4,122’s First Floor guide](https://crawler4122.com/book-1/the-first-floor/) provides the chapter sequence; the local source list in the archetype catalog links the location references used for each supported host motif. All room geometries remain inferred adaptations.
