# Tabletop inspiration for Dungeon Crawler Tactics

Research date: 2026-10-23. This document records research and the current adaptation roadmap. The first connected Over City neighborhood is now playable; its original scenario, entry points, choices and limits are documented in [Over City neighborhood: Lantern Row](Over-City-Neighborhood.md). Saved sponsor offers, bounded Favor and two placeable traps are now implemented as described in [Audience and traps](Audience-and-Traps.md); other proposed systems remain design targets unless described as implemented in [Playable game](PlayableGame.md). Use Renegade's official Dungeon Crawler Carl RPG as an additional design reference, alongside the novels and our existing tactics rules.

## What the sources establish

| Source | Evidence and limits |
|---|---|
| [Renegade: official RPG overview](https://dungeoncrawlercarl.renegadegamestudios.com/games) | Describes skill-based character building, custom skills/races/classes, crafting, achievements, loot, audiences and talk shows. It identifies Unstoppable as a separate deckbuilding game. |
| [Renegade: core rulebook](https://dungeoncrawlercarl.renegadegamestudios.com/dungeon-crawler-carl-rpg-core-rulebook/) | Covers floors 3–5, with neighborhoods and quests; advertises over 24 sessions and at least eight neighborhoods/quests per floor. This is a product overview, not the full rules text. |
| [The Crawler's Cookbook: RPG guide](https://crawlerscookbook.com/ttrpg/) | Secondary reporting describes two actions, Mana, cooldowns and AI Favor, and points to an official primer. The primer itself was not retrieved in this research pass, so exact formulas and exceptions remain unverified. |
| [Gen Con participant report](https://www.reddit.com/r/DungeonCrawlerCarl/comments/1vfjlwa/played_the_dcc_rpg_at_gen_con/) | A demo participant describes evasion, AI Favor and bosses with discoverable solutions. This is anecdotal, pre-release play experience, not an authoritative final rulebook. |

Search also surfaced fan-made systems, including an AI-run GitHub campaign. Their rules are not official RPG rules or novel canon. Do not merge their numerical tables into the lore catalog. Secondary sources disagree or simplify initiative and Favor details; those need primary verification before any faithful rules implementation.

## Recommended changes, in order

### 1. Give each floor a neighborhood to explore

The strongest structural lesson is to turn a floor into connected places with choices. Our current seven story battles and small exploration maps are a foundation, not a full floor simulation.

The first slice, Lantern Row, is playable: it has a safe-room entry, workshop, trapped supply store, optional crawler rescue and a boss entrance. Its rescue reveals a clue, and the safe-room offers a preparation choice. The place names, map, choices and rewards are original game content, not reproduced RPG adventures. See the [neighborhood guide](Over-City-Neighborhood.md) for the actual loop and exact choices.

Proposed loop: **house preparation → explore a neighborhood → discover a problem → choose an approach → resolve combat or interaction → achievement and loot → return home or descend**.

### 2. Reward clever behavior with achievements and audience reactions

Extend the existing saved achievements and loot boxes with authored challenges tied to committed events: saving an ally, using a terrain reaction, or disabling a boss mechanism. Show a short corner announcement, the actual reward, and a link to history. Each reward needs a saved receipt and a clear repeat limit.

Add optional sponsor challenges with a visible condition and reward. The house social screen should show how those decisions affected the audience and which offers became available. Audience progression is proposed; the current screen only shows local records.

### 3. Introduce a bounded AI Favor resource

AI Favor is a promising reported RPG concept. Our proposed adaptation would reward a limited set of unusual accomplishments, with a per-encounter cap to prevent farming.

For the first version, spend Favor on one explicitly permitted utility opportunity, such as an extra environmental interaction. Show the cost and exact result before confirmation. Do not grant an unrestricted second attack, silently restore all movement, or change party phase ordering. This particular effect and its balance would be our design, not a verified tabletop rule.

### 4. Make skills useful outside attacks

Add inspect, salvage, disarm, bargain and rescue interactions with visible eligibility and outcomes. A trained crawler should open a different solution, not merely gain another damage button. Provide a fallback route so a missing skill cannot trap the campaign.

Give a small selection of skills authored milestones at ranks 5, 10 and 15: a new target option, a lower cost, or a different interaction. Rank 20 stays an explicit exception. These proposed breakpoints and effects require separate source verification before being labeled official RPG rules; the current additive runtime curve remains a game adaptation.

### 5. Make the crafting room support improvised plans

Start with a handful of bounded recipes that combine compatible material tags into known effects. Preview the ingredients, output, Mana cost if applicable, target shape and reaction tags. Keep the authored definition separate from the player's saved inventory.

Example design: a salvaged container plus oil produces a placeable oil trap; ignition follows the existing fire/oil reaction. A general placeable trap does not currently exist and needs a narrow rules primitive and forecast support. Avoid promising arbitrary free-text inventions or unsupported combinations.

### 6. Give bosses clues, mechanisms and several solutions

Expand the existing boss intent and scenario-object systems. Exploration reveals a mechanism; the battle telegraphs its consequence; the party can disable it, interrupt it or reposition. A countdown advances on committed rounds, not while reading a modal.

Each room should expose at least one environmental opportunity and show the resulting reaction above sprites. Reuse current push, surface and status rules where possible. Ally-assisted reactions, delayed traps and new spatial predicates need explicit runtime support where the existing resolver cannot express them.

## Keep the requested tactics controls

The player still moves and acts in either order, explicitly ends each crawler's turn, and sees the enemy phase after all allies finish. Tabletop inspiration does not authorize replacing that requested behavior with enemy-first initiative or two interchangeable action points. Mana remains Mana. Do not introduce hidden dice into an exact damage forecast.

## Implementation contracts

- Extend the typed definitions in `UnityPackage/Runtime/Core/` and author content in `UnityPackage/Runtime/Data/`. Proposed additions include neighborhood links, interaction requirements, sponsor challenges and Favor grants/spending. They are not existing schema fields.
- Evaluate achievements and challenges from committed shared-core events, never animation callbacks. Save award receipts, counters and chosen offers. Preview and cancellation must not change those records.
- Use `GameSession.Journey` and `.Exploration` for connected objectives, `.Home` and `.Development` for preparation and crafting, and the scenario/intent system for boss mechanisms.
- Add schema and C# validation for each new definition, explicit save migration, and tests for cancellation, repeat-award prevention, reload and legal completion without optional skills.
- Keep the first implementation small: one Over City neighborhood, one rescue, one environmental puzzle, three achievement challenges and one home preparation decision. Playtest that complete loop before multiplying floors or class entries.

## Feature checklist

- [x] Research official product descriptions and label secondary rules reports.
- [x] Map the proposed features to the existing shared-C# architecture.
- [x] Playable connected Over City neighborhood with alternative routes. See [Lantern Row](Over-City-Neighborhood.md).
- [ ] Broader skill-based noncombat interactions with fallback solutions. Lantern Row has the authored Heavy Blow rescue check and manual winch fallback, plus a fixed bypass for its supply latch.
- [x] Three saved contextual sponsor offers with explicit conditions and once-per-run rewards. Broader authored offers remain future work.
- [x] Saved bounded AI Favor with an exact spend forecast for eligible environmental supplies.
- [x] Two authored placeable one-use traps and safe-room recipes.
- [ ] Modular material-tag recipe combinations and arbitrary improvised inventions.
- [ ] Boss clues linked to exploration and visible mechanisms.
- [ ] House social screen showing earned audience consequences.

The existing house, gold purchases, personal/class trees, rank practice, loot boxes, tag reactions, boss scenarios and eight-floor route remain implemented as documented in [Journey and home](Journey-and-Home.md). Lantern Row is the completed neighborhood slice. Its clue links exploration to existing reactions; visible boss mechanisms remain future work. Broader noncombat skill interactions, material-tag improvised crafting, additional boss mechanisms and audience progression remain design targets. The social screen now includes local sponsor delivery receipts; it does not simulate a live audience.
