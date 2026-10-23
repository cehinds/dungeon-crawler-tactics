# Revamp research and content boundaries

This content pack adapts the named characters into distinct tactical identities. Character labels and source facts are grounded in the books; ability effects, costs, range, and turn behavior are game conversions. The interface uses the identity class names without appending a disclaimer to every action. This document records which parts are source anchors and which are invented mechanics.

## Source notes

The primary source checked is the publisher's official sample for *Carl's Doomsday Scenario* (Dungeon Crawler Carl, Book 2), ISBN 9780241816219: [Penguin Random House UK sample PDF](https://cdn.penguin.co.uk/dam-assets/books/9780241816219/9780241816219-sample.pdf). Relevant passages identify Carl's Compensated Anarchist class and explosive/trap improvisation, Princess Donut's Former Child Actor class and learned Magic Missile, and Mordecai as a noncombatant (p. 12); Donut's Magic Missile is described as a permanent learned ability on pp. 19–20. The sample also describes Mongo as a baby velociraptor on PDF page 14 (zero-based page 13). These are narrow early-series anchors, not a full-series lore source.

Secondary references include [Princess Donut](https://dungeon-crawler-carl.fandom.com/wiki/Donut), [Katia's Doppelgänger page](https://dungeon-crawler-carl.fandom.com/wiki/Doppelg%C3%A4nger), and [Mongo](https://www.novelpantheon.com/novels/dungeon-crawler-carl/characters/mongo). They help identify terms such as Puddle Jumper, Heal Critter, and Mongo's species name, *Velociraptor mongoliensis*. Novel Pantheon's character summary says Mongo's forelimbs develop feathered wings and describes red/pink plumage with blue eye highlights (chapters 46–81). The exact first-appearance book within that range has not been independently verified; the official Book 4 sample ([PDF](https://cdn.penguin.co.uk/dam-assets/books/9780241829912/9780241829912-sample.pdf)) does not readily confirm the wing details. Treat these as secondary references; they do not establish the tactical effects shipped here.

## Character identity and game mechanics

- **Carl — Compensated Anarchist:** The class identity and his explosive/trap improvisation are source-grounded. `Powerful Strike` and `Improvised Bomb` are descriptive game actions. The current bomb lights one tile and can trigger the existing oil reaction; it does not do area damage.
- **Princess Donut — Former Child Actor:** The class identity and learned `Magic Missile` come from the official sample. This game's Magic Missile is Arcane damage and does not set up Wet/Lightning reactions. `Puddle Jumper` and `Heal Critter` are source-inspired labels; their tile teleport and ally-healing behavior are game conversions.
- **Katia — Doppelganger:** Doppelganger is her source-grounded race/identity, used here as the class name. Her `Shapeshift`, `Heavy Blow`, and `New Look` effects and stats are invented tactical conversions, not claims about exact book mechanics.
- **Mongo — Raptor Companion:** The Book 2 sample identifies Mongo as a baby velociraptor. A secondary chapter summary describes later feathered wings and red/pink plumage; the authored art uses that appearance direction without asserting flight or a pterodactyl identity. `Mongo Bite` and `Mongo Pounce` are descriptive game actions; the damage and teleport rules are invented mechanics.
- **Mordecai:** The publisher sample identifies him as a noncombatant (p. 12). He remains a nondeployable advisor. The default field party is Carl, Donut, Katia, and Mongo.

## Mechanical scope

Identity class grants and personal innate grants point to the same stable ability IDs; the resolver deduplicates them. Push moves a target away from the actor until blocked; Teleport moves the actor to a legal tile in range. Arcane has no registered reactions. Water followed by Lightning still demonstrates Wet/Conductivity through the existing Coolant Bomb and Shock Tonic items, and Cold/Frozen/Shatter remains available through the existing items and abilities. Content and saves retain the internal `energy` fields and stable IDs for compatibility.

The floor keeps three authored encounters and optional caches/notes. It adds no summon system, class progression, equipment, or scripted exploration-objective language.

## Resource terminology

Player-facing resource terminology is **Mana**, abbreviated **MP** in compact HUD labels. Ability costs are mana costs. The content schema and save format retain the established `energy` field names for compatibility. There is no authored Energy/EN label or mana-restoration consumable in this pack.
