# Over City neighborhood: Lantern Row

Lantern Row is the first tabletop-inspired neighborhood slice in Dungeon Crawler Tactics. It is an original game scenario built around connected places, optional approaches, preparation, rescue and environmental clues. It does not reproduce an official RPG adventure or claim to describe a canonical neighborhood from the novels.

## What the sources establish

Renegade's [official RPG overview](https://dungeoncrawlercarl.renegadegamestudios.com/games) promotes skill-based character building, custom skills and classes, crafting, achievements, loot, audiences and talk shows. The [official core rulebook page](https://dungeoncrawlercarl.renegadegamestudios.com/dungeon-crawler-carl-rpg-core-rulebook/) describes a campaign covering floors 3–5 with neighborhoods and quests. These product pages establish the tabletop game's broad structure; they do not provide the rules text or the Lantern Row scenario.

The [Crawler's Cookbook guide](https://crawlerscookbook.com/ttrpg/) is secondary reporting about the tabletop RPG. Its discussion of AI Favor and other mechanics is not used as evidence for this neighborhood's rules. The encounter, map, choices, rewards and challenge rules below are original adaptations authored for this game.

## Entering and exploring

At a safe room, choose **Play Over City neighborhood…** to open the briefing, then choose **Enter Over City**. This starts an isolated mini-campaign with its own party and supplies; the current campaign is checkpointed and can be restored with **Return to preserved campaign**. Progress and rewards from the isolated mini-campaign do not transfer to the preserved campaign. The same authored neighborhood also appears as an optional discovery in the floor 3 story route. There, none of its optional interactions is required to finish the floor. The safe-room preparation choice is optional in either route.

Lantern Row is a connected 15×11 area in the floor 3 journey. The main street leads toward the Pump-chamber boss entrance. A northern branch passes the Lantern workshop and trapped supply store; a southern alley leads to a crawler under a shutter and reconnects with the street. An emergency shelf cache is also available. Use the existing map movement controls to explore and reveal passages. In the story route, visit the neighborhood discovery before its room choices become available. The journal explains choices, costs and blocked conditions.

The intended loop is **prepare at the safe room → explore the connected streets → choose optional trades or rescue → use the clue to plan for the pump chamber → fight or continue the floor route**. Neighborhood actions have a preview that shows the exact item cost and resulting reward before confirmation. Cancel or Escape leaves the choice uncommitted.

## Preparation, choices and rewards

At the floor 3 camp, choose one free preparation package: two health tonics or two coolant bombs. This choice is separate from the house, which remains a floor 4 purchase.

The neighborhood offers three optional interactions:

- **Lantern workshop:** barter one health tonic for a fire bomb, or take a free coolant bomb.
- **Trapped supply store:** spend a coolant bomb to disarm the trap and receive a mega tonic, or use the free manual bypass to receive a health tonic.
- **Crawler under the shutter:** use Heavy Blow rank 1 to complete the rescue and receive two shock tonics, or use the free manual winch to receive one. Either solution reveals the clue about wet/lightning and oil/fire reactions.

The choices offer distinct costs and routes while preserving a free fallback for the trap and rescue. The clue points to the game's existing water/wet/lightning and oil/fire reactions; it does not teach a new damage rule or add a general placeable-trap system.

## Challenges and records

Three once-per-run challenges reward optional play: completing the rescue by either method grants a health tonic; cooling the trapped supply store grants a fire bomb; and choosing either preparation package grants a cleansing tonic. Earned challenges show a **NEW ACHIEVEMENT** notice and appear in the journal and home social history. These are game achievements and rewards, not official tabletop RPG awards.

## Saves and authoring

Choices, challenge receipts and clues are saved with the run. Published older floor-three exploration saves are validated against their original layout and migrated to Lantern Row, preserving claimed discoveries and inventory. Corrupt current saves are rejected instead of reset. The standalone entry keeps a validated campaign backup and restores it when leaving.

Edit `neighborhood` and the matching journey exploration in `UnityPackage/Runtime/Data/game-content.json`. Each authored interaction defines stable option IDs, costs, rewards and optional skill requirements; challenges reference committed choices. Keep `legacyExploration` as the published layout snapshot for save migration. Run the content validators and `Tests/NeighborhoodTests` after changes, then sync the Unity project.

## Scope and limitations

Lantern Row adds one authored neighborhood, a handful of bounded interactions, a rescue clue and three challenge rewards. Its trap is a one-time scenario interaction: improvised recipes, arbitrary trap placement and general disarming mechanics remain future work. AI Favor and sponsor challenges are not part of this slice. The boss clue references existing reactions; it does not create a new boss mechanism. The tabletop sources above do not verify these details or the game's exact costs and outcomes.

For source distinctions and the broader feature roadmap, see [Tabletop inspiration](Tabletop-Inspiration.md). For current controls, campaign behavior and tested-platform limits, see [Playable game](PlayableGame.md).
