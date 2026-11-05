# Class and skill research, and proposed progression

Research date: 23 October 2026. This artifact separates research evidence from proposed rules. The lore-catalog generator derives separate adapted runtime class kits from its profiles. [The companion JSON](../Research/classes-skills.json) contains source URLs, confidence/access notes, 122 source-attested class names, mappings for all 26 existing class kits and all 88 abilities, 1,760 proposed ability-rank rows, and 122 proposed class profiles with 1,708 nodes.

## What is established and what remains unknown

Class selection happens on Floor 3. Donut is level 13 after selection in the authorized sample, so the requested **class trees through level 50** must not be confused with a **crawler-level-50 unlock**. [Publisher Book 2 sample, PDF p.25](https://cdn.penguin.co.uk/dam-assets/books/9780241816219/9780241816219-sample.pdf).

The requested playable scope is Floors 1–8 within an eighteen-floor setting. The [secondary floor overview](https://crawlerscookbook.com/floors/) supports that distinction; it does not establish a finished gameplay specification for those floors. Source-reported later-floor class options remain marked separately in the JSON. A Floor 3 base unlock does not silently move a documented Floor 9 option earlier.

The [class directory](https://www.dccdatabase.com/wiki/list_of_classes/) describes coverage through Book 7. Four additional names were verified in the authorized Book 8 excerpt; this extends the source coverage without establishing an exhaustive all-books list. Its entries mix generic archetypes, offered choices, upgrades, temporary classes and earlier-season characters. The JSON records their names, rather than copying descriptions or claiming independently verified rules for each. It is **not an exhaustive all-books audit**. Unknown first-appearance chapters, prerequisites and rank effects remain unknown. A directory entry alone does not mean a crawler can choose that class on any floor.

Sources are graded in the JSON. The authorized publisher sample is primary; wikis and unofficial indices are secondary. Some Fandom pages could only be checked through indexed excerpts because direct access failed. Those entries are explicitly marked `secondary_search_excerpt`. No complete canonical rank table for every skill was established.

## Book 8 primary additions

The [publisher Book 8 sample, PDF43–44](https://cdn.penguin.co.uk/dam-assets/books/9780241836880/9780241836880-sample.pdf) names Las Vegas Showgirl, Zoo Warden, Problematic Influencer and Assassin of Sekhmet as Floor 10 options. The excerpt mentions accessories, a social-board upgrade and a healing aura, without complete numerical grant/rank tables. Their generated profiles remain explicitly adapted and locked beyond the current journey scope.

## Verified rank anchors

The JSON's `knownRankBreakpoints` records eleven scoped observations. It distinguishes an effect change from a training cap or a character's reported current rank.

- [Magic Missile](https://www.dccdatabase.com/wiki/magic_missile/) has documented low-rank cost, a rank-5 expenditure choice and possible rank-10 ignition. It does not supply exact damage at every rank.
- [Heal Critter](https://www.dccdatabase.com/wiki/heal_critter/) targets a nearby pet-class mob or dungeon familiar; a reported starting rank does not establish a healing formula.
- The [Puddle Jumper index excerpt](https://www.dccfansite.com/entry/puddle-jumper/) describes delay, cooldown and companion transport. It needs an independent full-text check before its numbers become strict design constraints.
- The publisher sample provides specific examples for Cockroach, Character Actor, cap permissions and exceptional high-rank magic. Consult the JSON's exact page locators. These examples are not a universal curve.

A known rank is not evidence for all intervening ranks. Missing canonical values are `null`, never zero and never an unlabeled interpolated number. Rank 20 also needs a supported cap unlock; it is not universally available to every crawler.

## Mapping the current game

All 88 current ability IDs have a mapping record and a copy of their current game baseline. Only four have directly researched matching canonical skill/spell labels in this pass: Powerful Strike, Magic Missile, Puddle Jumper and Heal Critter. Their current numeric effects remain game adaptations. This conservative classification does not assert that every other label is absent from the novels; it means an exact corresponding rank table was not verified.

Important differences affect implementation:

| Current behavior | Source distinction | Required design decision |
|---|---|---|
| Heal Critter heals any ally | The referenced spell targets pets/familiars | Retain as an explicitly broadened adaptation or add typed target eligibility. |
| Puddle Jumper is an immediate self-only tile move | Referenced transport includes other passengers, timing and cooldown limits | Keep the compact teleport or implement transport/timing as new mechanics. |
| Magic Missile is fixed Arcane damage | Source reports expenditure choice and a later ignition possibility | Add typed expenditure/breakpoint support if adopting those features. |
| Powerful Strike uses fixed damage and push | The matching name does not verify these grid numbers | Keep explicit tactical numbers unless a primary chapter check supplies the desired formula. |

Katia's shapechanging is a race-based physical capability; her class is Monster Truck Driver. The game's Doppelganger class record is an identity convenience, not a canonical class conversion. [Katia source](https://www.novelpantheon.com/novels/dungeon-crawler-carl/characters/katia), [class source](https://www.dccdatabase.com/wiki/monster_truck_driver_class/). Mongo remains a companion rather than evidence of a canonical “Raptor Companion” crawler class. The original enemy kits and newly authored capstone actions remain adaptations.

## Proposed ability ranks 1–20

Every existing ability has twenty **proposed game ranks** in the JSON, with `provenance: proposed_game_extrapolation` and `canonicalEffect: null`. Rank 1 means the present game's baseline, not a claimed canonical starting value.

For rank `r`, set `L = min(r, 15)`:

```text
multiplier = (1 + 0.07×(L−1) + 0.15×floor((L−1)/5)) × 1.12^max(0,r−15)
positive Damage/Heal = round-half-up(current baseline × multiplier)
range, when baseline > 1 = baseline + min(3, floor((r−1)/5))
positive Mana cost = max(1, baseline − min(2, floor((r−1)/5)))
zero Mana cost remains zero
```

This is an invented bounded balance curve. Status sets, target allegiance, push distances, teleport legality, tag duration and reaction damage stay unchanged. The proposal adds no area effects, summons, copied creature magic or party transport. Item-action rows represent hypothetical potency tiers; they do not mean consumable use should train skills.

The proposal must be reconciled with existing three-rank practice, stat allocation, class-tree passives and equipment so bonuses do not accidentally apply twice. The resolver, exact preview, AI, saves and tooltips need a single effective-rank calculation. Exceptional source breakpoints should be separate typed overrides. A particularly dramatic example for one spell cannot justify multiplying every ability by the same amount. The game currently has Firebolt, not a source-verified Fireball implementation.

## Proposed class trees through level 50

Each of the 122 source-attested names has a proposed profile with two branches, seven nodes per branch, and nodes at class levels **1, 5, 10, 20, 30, 40 and 50**. Seven points across fourteen nodes create a depth-versus-breadth choice. These point schedules and grants are invented, not a canonical class-level system.

Profiles use the existing 88 ability IDs and bounded passive stat bonuses. Their representative roles and branch labels are design inferences, never novel grant lists. A repeated profile role does not establish canon equivalence between classes. No new skill name is labeled canonical. `sourceIds` supports the class name; `provenance` labels the invented nodes. Initial selection uses the Floor 3 base rule, with source-reported later options kept later and unknown prerequisites left unresolved.

These profiles are reviewable authoring proposals. The runtime now derives class kits and level-gated trees from them, with explicit eligibility and ability deduplication. Runtime availability follows party XP; a separate class-XP track remains future work. Further balance and save-migration checks are required for later changes. Existing crawler levels, skill ranks, class levels, floors and race permissions must remain distinct concepts. The profiles do not grant unimplemented Necromancer summons, universal Bard area buffs, or a physical mass model merely because a class name suggests them.

## Integrity and follow-up

The JSON includes a SHA-256 of the combat-content snapshot, complete existing ability IDs, source IDs and explicit uncertainty notes. Validate that snapshot before applying generated rows to a changed catalog. Next research should verify individual primary chapters for the directory's class names, resolve unknown prerequisites, and check any desired unique breakpoint before it becomes a promised feature.

The reproducible lore-catalog generator updates runtime JSON separately; these research tables are not themselves executable rules. Native Unity support, balance, complete Floor 1–8 content and canonical completeness are not established by the research artifact.
