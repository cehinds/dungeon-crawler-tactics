# Floor One lore and adaptation guide

## Scope

This rebuild covers the opening stretch of Book 1: Carl and Princess Donut enter the dungeon, encounter the false Tutorial Guild and goblin Murder Dozer, reach Mordecai's real Tutorial Guild, and explore a compact set of First Floor landmarks through the Hoarder, Tally's safe room, the goblin workshop, Juicer, Meadow Lark, and the Ball of Swine descent. The regions and routes are a playable abstraction. The novels do not provide a complete canonical map, exact room plan, or all inter-region connections.

Carl is a human man, clean-shaven, and barefoot at the start. Princess Donut is a cat. They are the only deployable Floor 1 party members. Mordecai is a guild guide and NPC, never a party member. Katia and Mongo are not members of this Floor 1 party. Crawler class selection happens on Floor 3; Floor 1 progression must not grant those classes early.

## Content evidence and limits

The authorized publisher sample and the existing Floor One research catalogue support named people, places, and broad events. `Web/wwwroot/data/book-one-floor-one.json` and `Web/wwwroot/data/lore-catalog.json` are retained in `Rebuild/ReferenceData/` as research references, alongside their source links and confidence notes. The Floor One catalogue explicitly distinguishes visited places, inferred routes, and merely mentioned locations; retain that distinction in all future map work.

The previous combat catalogs contain useful stable identifiers and candidate names, not proof that their effects are canonical. The previous rank audit documents that complete 1–20 ability tables do not exist in the available evidence. Use existing sourced ability/item IDs where they fit, and mark tactical values, effect changes, progression curves, invented encounters, and NPC interaction outcomes as game adaptations. Do not present interpolated rank values as book facts.

Magic Missile is included in Donut's Floor 1 usable set per the retained source review; its tactical damage is adapted and it spends mana. Do not include later Donut abilities such as Heal Critter or Puddle Jumper without clear Floor 1 evidence. Carl may use melee and Powerful Strike; any fixed-damage tactical implementation is an adaptation of the described unarmed damage multiplier. Bombs, explosives, and stomp effects can be represented as tactical adaptations, with clear provenance.

Spells spend mana. Any future rank progression should separate trained rank from gear bonuses and effective cast rank. Available evidence supports selective rank anchors for some abilities, not a universal ability progression table or universal rank-20 access. The First Floor content needs only early, playable values; class unlocks belong to Floor 3.

## Adaptation rules

- Reuse source-backed identifiers from the archived catalogs when their concept is appropriate; avoid borrowing an unrelated ability's ID for a new mechanic.
- Preserve a short provenance/adaptation note on every item, ability, enemy, encounter, and NPC beat that adds invented combat or narrative behavior.
- Keep NPC interactions brief and original. Paraphrase the situation; do not reproduce novel dialogue.
- Enemy variants may adapt documented goblins, the Murder Dozer, Hoarder/Scatterers, Juicer, and the Ball of Swine. Numerical stats, turn patterns, and the precise composition of a tactical encounter are game design.
- Use only personal Floor 1 gear supported by the retained source review (Carl’s underpants/backpack and Donut’s tiara). These are depictions, not a canonical loot table. Do not assign them combat bonuses as book facts; any gameplay effect is an adaptation. Keep generic armor, charms, and loot from the prior game in reference archives only, not the Floor 1 runtime inventory.
- Include only the Floor 1 slice in this file. Do not import later-book rosters, floor lists, or complete class trees into the starting campaign.

## Source trail

The copied references under `Rebuild/ReferenceData/` preserve the prior lore, item, skill, and class catalogs before cleanup. Particularly relevant materials include `lore-catalog.json`, `book-one-floor-one.json`, `combat-content.json`, `game-content.json`, `Ability-Rank-Audit.md`, `Research/classes-skills.json`, and the copied source catalogues in `sources/`. Their source URLs and evidence labels are retained in those files. Consult the publisher sample first, then use chapter-cited secondary databases only for claims explicitly marked secondary.
