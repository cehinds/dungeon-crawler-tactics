# Boss encounter concepts

These three generated images are visual proposals, not implemented encounters. Each was generated with GPT Image using the current game screenshot as an attached reference, then visually inspected. They share the navy/gold interface, detailed pixel sprites, isometric grid, objective, enemy intent, and bottom action dock. The requested target was 1600 × 900; the image service returned native 1672 × 941 PNGs, retained without resampling.

| Concept | Image | Source-grounded scene | Proposed mechanics |
|---|---|---|---|
| Hoarder | [PNG](../Web/wwwroot/assets/concepts/boss-hoarder-concept.png) | Giant black-haired human-ish woman, gray torn shirt, blue pants, garbage stockpile, cockroach Scatterers. Not a chest mimic. | Swarm telegraph, readable nests, optional fire interruption, explosive environment, safe movement preview. |
| Juicer | [PNG](../Web/wwwroot/assets/concepts/boss-juicer-concept.png) | Extremely muscular scaly lizard humanoid with tail and black shorts, gym, flaming thrown metal weight plates. | Straight-line attack forecast, topplable benches that create cover, clear action cost previews. |
| Ball of Swine | [PNG](../Web/wwwroot/assets/concepts/boss-swine-concept.png) | Rolling pink sphere with pig features, tusks, tuxedo/sequin scraps; collaborative Speedbump built from furniture and gym equipment. | Carry/brace construction actions, progress segments, rolling-impact countdown, trap placement, safe-side positioning. |

## Source checks

- [Hoarder — DCC Database](https://www.dccdatabase.com/wiki/hoarder/): Book 1, Chapters 10–11; human-ish woman, black hair, trash chamber, Scatterer minions. The art intentionally omits graphic skin injuries.
- [Juicer — DCC Database](https://www.dccdatabase.com/wiki/juicer/): Book 1, Chapters 23–25; scaly lizard head, tail, oversized musculature, black shorts, gym and flaming weight-plate attack. Plate telegraphs and cover interactions are adaptation rules.
- [Ball of Swine — Fandom](https://dungeon-crawler-carl.fandom.com/wiki/Ball_of_Swine): Book 1 rolling borough boss and Speedbump collaboration with Meadow Lark, checked through indexed search text because direct retrieval was restricted. The art uses generic Meadow Lark helpers rather than claiming a canonical four-character fight.

## Implementation checklist — all still proposed

- [ ] Boss-size footprints, tile occupancy, health display, and scenario objective states.
- [ ] Enemy intent UI: target lanes, affected tiles, countdowns, and interruption explanation before commitment.
- [ ] Hoarder: Scatterer spawning with a visible cap, nest indicators, fire interruption, and an ordinary damage route to victory.
- [ ] Juicer: flaming plate projectile, cover interception, topplable gym props, and a readable close-range fallback attack.
- [ ] Ball of Swine: rolling path and collision resolution, carryable parts, shared construction progress, barricade durability, traps, allied helper turns, and a recovery route if construction fails.
- [ ] Original AI quips triggered by visible actions; no novel quotations or hidden audience-score victory requirement.
- [ ] Scenario help explaining that costs, ranges, HP/MP numbers, class presentation, turn timing, and construction rules are invented game adaptations.
- [ ] Test grid alignment, large-unit occlusion, camera readability, contrast, input cancellation, and restart behavior before claiming any encounter works.

## Timeline and fidelity limits

The screens are clearly marked “CONCEPT • BOOK 1 SCENARIO ADAPTATION.” They show Carl and Donut; the swine concept adds generic Meadow Lark collaborators. Katia and Mongo are absent. Carl's class title appears in the generated dock, compressing a later progression unlock into this mockup; it is not a claim that he has selected that class during the original First Floor events. All displayed numerical stats and named tactical commands are illustrative. Exact sprite geometry and pixel dimensions remain production work; these are composition references, not ready-to-import sprite sheets.
