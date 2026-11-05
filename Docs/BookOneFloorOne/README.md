# Book 1, Floor 1 playable route

[`book-one-floor-one.json`](../../Web/wwwroot/data/book-one-floor-one.json) defines a seeded, continuous 40×32 playable floor with 12 physical districts and one nonphysical guild-rumor interaction. The districts are generated as connected regions in one map, so preview, export, and Play use the same realized floor. Positions organize the authored graph; they do not assert canonical coordinates or a measured floorplan.

## Route and evidence

The publisher’s Book 1 sample supports the opening descent and Kua-tin threshold. A Book 1-only chapter guide gives the broad story sequence through the goblin alley, Hoarder’s lair, Polish restaurant safe room, goblin workshop, creature territories and Juicer’s gym, then the long trip to the Ball of Swine spiral. The Ball of Swine reference cites Chapters 21–27 for the maze, bridges, switch chamber, construction, arena reveal and stairwell. The catalog records the sources and what each supports.

The route graph connects those named places for play, but every graph connection is an inference: available sources establish locations and a broad sequence, not exact adjacency or a complete First Floor map. The links are navigation connections, not corridor quest locks. Optional branches include Tally’s restaurant, Sebastian’s Peruvian Taco Bell, the DMV safe room and Meadow Lark’s camp. The Alabama Waffle House and candy-vending stop are only reports heard at the Tutorial Guild; they are not physical districts or established Carl visits.

Tally’s play area stays within the same safe room. The Ball of Swine switch chamber, Speedbump construction area, revealed arena and stairs are subregions or encounter states inside one boss district. Territory labels refer to creature areas, not official neighborhood names. The 36 concept panels include views, subregions, routes, reported places and generic concepts; they do not represent 36 unique canon locations.

## Gameplay and presentation limits

The regional catalog uses `scenario.hoarder`, `scenario.juicer` and `scenario.swine` as references to existing story-themed scenarios. The continuous 40×32 floor does **not** launch those named scenarios. Its tactical encounters are five authored groups of existing enemy templates placed on the floor. The regional catalog’s lore references and the continuous floor’s actual combat setup are separate layers; neither claims to recreate the novel’s party, timeline or combat exactly. The Murder Dozer and goblin workshop remain story locations/objectives without invented encounter IDs.

Corridor links are navigational and do not impose quest locks. To finish, the player must complete every required region objective and clear all five tactical encounter groups before interacting with the exit. Optional-region objectives are not required for floor completion.

The gameplay preview draws the exact whole-object sprites and blocked cells in the generated playable layout. Export preserves that map layout; runtime uses the game’s existing art presentation, so its pixels can differ from the preview. The preview and runtime therefore share gameplay geometry and collision, not identical artwork. Neither represents a canonical novel floorplan.

Mordecai appears as a Tutorial Guild guide and is not a deployable party member. Katia’s presence in the broader runtime roster does not establish her involvement on Floor 1. Floor 3 class unlocks are outside this floor’s scope.
