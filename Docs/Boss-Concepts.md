# Boss scenarios and concept references

Three separate playable scenario adaptations now accompany these generated visual proposals. Choose a scenario from the safe room, review its objective, and enter it using the current party. The scenario preserves a campaign checkpoint; returning restores that campaign. The images remain concept references rather than screenshots or exact runtime specifications. Each was generated with GPT Image using the current game screenshot as an attached reference, then visually inspected. They share the navy/gold interface, detailed pixel sprites, isometric grid, objective, enemy intent, and bottom action dock. The requested target was 1600 × 900; the image service returned native 1672 × 941 PNGs, retained without resampling.

| Concept | Image | Source-grounded scene | Proposed mechanics |
|---|---|---|---|
| Hoarder | [PNG](https://github.com/cehinds/AI-Art/blob/dungeon-crawler/dungeon-crawler-tactics/Web/wwwroot/assets/concepts/boss-hoarder-concept.png) | Giant black-haired human-ish woman, gray torn shirt, blue pants, garbage stockpile, cockroach Scatterers. Not a chest mimic. | Swarm telegraph, readable nests, optional fire interruption, explosive environment, safe movement preview. |
| Juicer | [PNG](https://github.com/cehinds/AI-Art/blob/dungeon-crawler/dungeon-crawler-tactics/Web/wwwroot/assets/concepts/boss-juicer-concept.png) | Extremely muscular scaly lizard humanoid with tail and black shorts, gym, flaming thrown metal weight plates. | Straight-line attack forecast, topplable benches that create cover, clear action cost previews. |
| Ball of Swine | [PNG](https://github.com/cehinds/AI-Art/blob/dungeon-crawler/dungeon-crawler-tactics/Web/wwwroot/assets/concepts/boss-swine-concept.png) | Rolling pink sphere with pig features, tusks, tuxedo/sequin scraps; collaborative Speedbump built from furniture and gym equipment. | Carry/brace construction actions, progress segments, rolling-impact countdown, trap placement, safe-side positioning. |

## Source checks

- [Hoarder — DCC Database](https://www.dccdatabase.com/wiki/hoarder/): Book 1, Chapters 10–11; human-ish woman, black hair, trash chamber, Scatterer minions. The art intentionally omits graphic skin injuries.
- [Juicer — DCC Database](https://www.dccdatabase.com/wiki/juicer/): Book 1, Chapters 23–25; scaly lizard head, tail, oversized musculature, black shorts, gym and flaming weight-plate attack. Plate telegraphs and cover interactions are adaptation rules.
- [Ball of Swine — Fandom](https://dungeon-crawler-carl.fandom.com/wiki/Ball_of_Swine): Book 1 rolling borough boss and Speedbump collaboration with Meadow Lark, checked through indexed search text because direct retrieval was restricted. The art uses generic Meadow Lark helpers rather than claiming a canonical four-character fight.

## Playable mechanics

| Scenario | Implemented behavior |
|---|---|
| Hoarder | Three authored Scatterer slots, at most two active at once; emergence warnings; Burning, Frozen or Shocked interruption; action-cost adjacent garbage clearing; nearby swipe and ordinary damage victory. |
| Juicer | A locked cardinal throw lane, visible before execution; dodge by moving away; Frozen/Shocked interruption; topple an adjacent bench by spending an action, creating cover that intercepts one throw and is destroyed. Scenario throws target player crawlers. |
| Ball of Swine | An eight-cell route with the next three rolled cells warned; action-cost part collection, carrying and three-part barricade construction; completed barriers stop a roll and damage the boss; limited durability, recoverable helpers and reusable parts. Ordinary attacks also remain viable. |

These are bounded scenario rules in shared C#, not a general scripting, construction or area-effect framework. Objectives, intent, carried parts, object state, helper progress and the preserved campaign checkpoint are saved. Retry starts a fresh scenario attempt. The mixed-timeline roster, costs, numbers and interactions are explicitly adaptation choices.

## Production sprites and scenery

The playable renderer uses dedicated generated art, separate from the concept sheets:

- [Boss atlas manifest](https://github.com/cehinds/AI-Art/blob/dungeon-crawler/dungeon-crawler-tactics/Web/wwwroot/assets/bosses/manifest.json): Hoarder, Juicer and Ball of Swine, each with idle, two walking and attack frames (12 frames total). Each frame is 192×192 with a measured foot anchor.
- [Scenario art manifest](https://github.com/cehinds/AI-Art/blob/dungeon-crawler/dungeon-crawler-tactics/Web/wwwroot/assets/scenario-props/manifest.json): four Scatterer frames plus garbage, bench, barrier and parts components. The Scatterer frames bring the animated boss/minion set to 16 frames; the four scenery components are separate art.
- The retained `source-atlas.png` files in both asset directories are generation/extraction sources. Manifest dimensions and anchors describe the shipped sheets; concept-image geometry is not an import contract.

Larger rendered boss art still occupies **one logical tile**. Multi-cell occupancy, general large-unit collisions, carried platforms, broad trap construction and universal area/chain reactions remain planned. Art size does not establish a larger tactical footprint or guarantee perfect alignment in every projection. Camera/occlusion and touch readability require actual rendered checks.

The browser has the scenario interface and retained art. Native Unity presentation parity, Editor Play Mode and Unity Web export remain unverified; reference compilation alone does not establish those results.

## Timeline and fidelity limits

The screens are clearly marked “CONCEPT • BOOK 1 SCENARIO ADAPTATION.” They show Carl and Donut; the swine concept adds generic Meadow Lark collaborators. Katia and Mongo are absent. Carl's class title appears in the generated dock, compressing a later progression unlock into this mockup; it is not a claim that he has selected that class during the original First Floor events. All displayed numerical stats and named tactical commands are illustrative. The concept sheets are composition references rather than sprite sheets. Dedicated production sheets now have their own manifests, dimensions and anchors; use those files for runtime integration.
