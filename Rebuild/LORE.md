# Floor One lore and adaptation guide

## Scope

This rebuild covers the opening stretch of Book 1: Carl and Princess Donut enter the dungeon, encounter the false Tutorial Guild and goblin Murder Dozer, reach Mordecai's real Tutorial Guild, and explore a compact set of First Floor landmarks through the Hoarder, Tally's safe room, the goblin workshop, Juicer, Meadow Lark, and the Ball of Swine descent. The regions and routes are a playable abstraction. The novels do not provide a complete canonical map, exact room plan, or all inter-region connections.

Carl is a human man, clean-shaven, and barefoot at the start. Princess Donut is a cat. They are the only deployable Floor 1 party members. Mordecai is a guild guide and NPC, never a party member. Katia and Mongo are not members of this Floor 1 party. Crawler class selection happens on Floor 3; Floor 1 progression must not grant those classes early.

The authored location set contains twelve entries, but not all are visited: the reported rest stops remain mentioned-only, while visited rooms, safe rooms, camps, and connector regions retain their distinct evidence status. A reported or rumored place must not become a map destination solely because it has a name. The opening order is the publisher-sample threshold and false Guild setup, the adapted ambush and tutorial interaction, then the compact authored route through optional and required First Floor landmarks. Exact chapter/page locators are recorded only where the retained references establish them; otherwise the locator is `unknown`.

## Content evidence and limits

The authorized publisher sample and the existing Floor One research catalogue support named people, places, and broad events. `Web/wwwroot/data/book-one-floor-one.json` and `Web/wwwroot/data/lore-catalog.json` are retained in `Rebuild/ReferenceData/` as research references, alongside their source links and confidence notes. The Floor One catalogue explicitly distinguishes visited places, inferred routes, and merely mentioned locations; retain that distinction in all future map work.

The previous combat catalogs contain useful stable identifiers and candidate names, not proof that their effects are canonical. The previous rank audit documents that complete 1–20 ability tables do not exist in the available evidence. Use existing sourced ability/item IDs where they fit, and mark tactical values, effect changes, progression curves, invented encounters, and NPC interaction outcomes as game adaptations. Do not present interpolated rank values as book facts.

Magic Missile is included in Donut's Floor 1 usable set per the retained source review; its tactical damage is adapted and it spends mana. Do not include later Donut abilities such as Heal Critter or Puddle Jumper without clear Floor 1 evidence. Carl may use melee and Powerful Strike. Secondary evidence describes Powerful Strike as multiplying unarmed damage and reports rank 3; the current Punch-based calculation follows that identity, while the rank-3/4/5 factors of 1.5/1.75/2 remain explicit tactical adaptations. Bombs, explosives, and stomp effects can be represented as tactical adaptations, with clear provenance.

Spells spend mana. Any future rank progression should separate trained rank from gear bonuses and effective cast rank. Available evidence supports selective rank anchors for some abilities, not a universal ability progression table or universal rank-20 access. The First Floor content needs only early, playable values; class unlocks belong to Floor 3.

Floor One training is permissioned through rank 5. Rank capacity and mastery permission are separate: rank capacity may be 20, but a skill can be trained beyond rank 5 only when that skill explicitly grants permission. Rank-20 access is not universal. Gear rank modifiers and temporary modifiers are separate from learned practice and are adaptations unless source-approved.

Bomb manufacture may appear as a research-only recipe definition so later work can preserve its provenance. Such a row is inactive and unavailable in the Floor One runtime. Bomb attacks and item behaviors are tactical adaptations and do not imply a supported crafting system. The active Improvised Bomb uses a radius-1 blast against allies, enemies and destructibles, with cell targeting and existing direct enemy/object targets. Its damage, range, friendly fire and 2-mana resource cost are authored tuning recorded under `adaptation-design`, not claims supported by the publisher sample. No charge inventory or new burning rider is introduced.

## Adaptation rules

- Reuse source-backed identifiers from the archived catalogs when their concept is appropriate; avoid borrowing an unrelated ability's ID for a new mechanic.
- Preserve a short provenance/adaptation note on every item, ability, enemy, encounter, and NPC beat that adds invented combat or narrative behavior.
- Keep NPC interactions brief and original. Paraphrase the situation; do not reproduce novel dialogue.
- Enemy variants may adapt documented goblins, the Murder Dozer, Hoarder/Scatterers, Juicer, and the Ball of Swine. Numerical stats, turn patterns, and the precise composition of a tactical encounter are game design.
- Use only personal Floor 1 gear supported by the retained source review (Carl’s underpants/backpack and Donut’s tiara). These are depictions, not a canonical loot table. Do not assign them combat bonuses as book facts; any gameplay effect is an adaptation. Keep generic armor, charms, and loot from the prior game in reference archives only, not the Floor 1 runtime inventory.
- Include only the Floor 1 slice in this file. Do not import later-book rosters, floor lists, or complete class trees into the starting campaign.
- Bind story milestones to the runtime's stable quest events: clear `false-guild`, interact with `mordecai`, clear `goblin-workshop`, clear `ball-of-swine`, then reach `exit`. Hoarder and Juicer remain optional after the Mordecai briefing.
- Keep tags, source references, availability, and descriptions on each content definition. Mark mechanics as implemented only when the runtime resolver supports them; intended data rules and future facilities remain authored targets until then.

## Source trail

The copied references under `Rebuild/ReferenceData/` preserve the prior lore, item, skill, and class catalogs before cleanup. Particularly relevant materials include `lore-catalog.json`, `book-one-floor-one.json`, `combat-content.json`, `game-content.json`, `Ability-Rank-Audit.md`, `Research/classes-skills.json`, and the copied source catalogues in `sources/`. Their source URLs and evidence labels are retained in those files. Consult the publisher sample first, then use chapter-cited secondary databases only for claims explicitly marked secondary.

See `CONTENT-AUTHORING.md` for stable IDs, source locators, adaptation labels, rank permissions, and data-driven tag authoring. `BLOCK-A-CHECKLIST.md` tracks the content foundation separately from completing a campaign through Floors 1–20.

## Block B preparation economy

Block B covers M05, M06, M08, M09 and M11 as a single playable loop: explore, encounter, rewards, safe room, prepare, continue. These milestone identifiers do not establish recovered module names. Named safe rooms (Tally’s, the DMV and Sebastian’s) and Meadow Lark’s survivor camp retain their separate location evidence; a camp’s existence does not prove safe-room services. Runtime objects of kind `safe` share adapted rest/save and preparation services. This behavior already included rest and saving before Block B.

Health Tonic and Mana Draught retain their existing item IDs and adapted restorative effects. Repeatable purchases cost 8 and 10 gold respectively. Encounter item rewards, quantities, gold, XP, owner enforcement and equipment comparison rules are tactical adaptations, not canonical loot or vendor facts. The false Guild reward supplies both restoratives before the next preparation decision. No crafting, research recipe activation, Floor 3 class selection or later house mechanics are introduced. New games own one copy of Carl’s underpants/backpack and Donut’s tiara without auto-equipping them. Existing saves retain their inventory without a gear backfill. Personal opening gear keeps its zero combat bonuses and is cosmetic in combat. Inspection/equip/unequip support does not establish combat gear builds; generic armor and charm loot remain archived.
