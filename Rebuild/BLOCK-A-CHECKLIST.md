# Block A: content and systems foundation

Block A establishes reusable content and rule data for the Floor One slice. It does not complete the Book 1 campaign or establish that all future floors have authored content.

## Foundation scope

All items remain open until the listed implementation and evidence exist. Documentation or a populated JSON row alone does not complete its milestone.

- [x] **M01 — content registry and stories:** stable typed IDs, references, source provenance, availability, NPC/character records, location versus rumor status, recipes, facilities, and story events tied to runtime quest triggers. The content validator passed with 53 registry entries and worlds seeded 0, 42, and 1337.
- [x] **M02 — asset pipeline and ownership:** directional character roster, asset catalog and browser, tile/pivot/edge/layer/binding contracts, canonical AI-Art ownership outside this repository, and hosted files checked against `Tools/hosted-assets.json` checksums. The asset validator passed 156 registrations; browser QA verified nine actors with four facings and two walk frames. Local registration does not mean a file is hosted or release-approved.
- [x] **M03 — shared effects and tags:** one resolver serves movement, effects, forecast, commit, item use, enemy turns, and status ticks. Authored reactions are bounded and support unit/object targets. The browser environment scenario verified oil ignition, water suppression, the workshop crate explosion/chain reaction, forecast events, and a saved destruction receipt; Release tests verified resolver preview/commit and rollback behavior.
- [x] **M07 — skill permission and modifiers:** distinguish trained, gear-adjusted, effective, and temporary rank; validate permission, capacity, and floor gates; serialize and restore only supported modifier sources. Floor One training is capped at rank 5. Future rank 20 requires explicit per-skill permission and is not universal. Release tests passed temporary-rank persistence and forged-modifier rejection.
- [x] **M12 — documents and delivery checks:** keep `LORE.md`, `CONTRACT.md`, and `CONTENT-AUTHORING.md` aligned with runtime; run the catalog validator CLI and full regression suite; verify browser/mobile surfaces; exercise v1/v2 save migration, status persistence, modifier expiry, and destructive-prop persistence/rollback. Final presentation QA and the fresh published-host smoke passed.

## Content coverage to author and validate

- [x] Two deployable Floor One characters: Carl and Princess Donut. Mordecai is an NPC. Katia and Mongo are not in the Floor One party.
- [x] Twelve named locations/regions, with visited locations kept distinct from locations that are only mentioned in reports or rumors.
- [x] Five early skill rows, seven enemy definitions, and five encounter definitions.
- [x] Ten item definitions, with personal opening gear separated from adapted supplies and equipment effects.
- [x] Recipes include explicit research-only or inactive records when they describe later mechanics, including bomb manufacture; presence in the catalog does not make crafting available in Floor One.
- [x] Story facilities and gates use definitions tied to actual runtime quest events. Floor 3 class selection is recorded as a future, non-selectable facility and is unavailable in Floor One.
- [x] Opening sequence records what is sourced and what is adapted. Unknown chapter locators are recorded as `unknown`, not guessed.

## Acceptance evidence

Mark a foundation task complete only after its schema, references, and intended runtime behavior have been checked. A catalog row alone does not demonstrate that a mechanic is implemented. Keep campaign-wide content requirements open until the remaining books, floors, encounters, and progression have actually been authored and reviewed.

| Evidence | Result |
| --- | --- |
| `dotnet run --project Rebuild/Tests -c Release -- --validate-content` | Passed: 53 entries; world seeds 0, 42, and 1337 validated. |
| `python3 Tools/validate_assets.py` | Passed: 156 registrations, physical checksums, placement, poses, and metadata. |
| `dotnet run --project Rebuild/Tests -c Release` | Passed: resolver forecast/commit, floor route, save migration, status and temporary modifier persistence, encounter-object destruction receipts, rollback, and catalog gates. |
| Published asset validation | Passed against the fresh 105-file restored publish: 156 registrations and seven negative self-test fixtures rejected. |
| Browser environmental scenario | [AI-Art evidence bundle](https://github.com/cehinds/AI-Art/tree/dev/dungeon-crawler-tactics/block-a-20261107): workshop Bomb destroys the authored crate, applies Burning, water clears it, and the destruction receipt survives save/load; final presentation capture passed. |
| Browser natural route | [AI-Art evidence bundle](https://github.com/cehinds/AI-Art/tree/dev/dungeon-crawler-tactics/block-a-20261107): all five encounter wins, Floor One exit, safe-room save/load, and mobile layout completed without browser errors. |
| Browser save-state check | [AI-Art evidence bundle](https://github.com/cehinds/AI-Art/tree/dev/dungeon-crawler-tactics/block-a-20261107): version 1/2 migration and active effect round-trip passed. |
| Final aggregate QA | [AI-Art Block A evidence bundle](https://github.com/cehinds/AI-Art/tree/dev/dungeon-crawler-tactics/block-a-20261107): final route, environment interaction, save state, assets, mobile, fresh-host smoke, source guard, and presentation checks passed with zero browser/network errors. |
| Hosted runtime assets | [AI-Art Block A asset bundle](https://github.com/cehinds/AI-Art/tree/beb0ae0b27c0a49d96e5f0529583debd28bfee39/dungeon-crawler-tactics/Web/wwwroot/assets/block-a) |
| Review captures and evidence | [AI-Art Block A evidence bundle](https://github.com/cehinds/AI-Art/tree/dev/dungeon-crawler-tactics/block-a-20261107) (published after the game commit). |

Current authored play reaches level 6. The five Floor One skills train through rank 5; `rankCapacity: 20` is a future ceiling and does not grant rank-20 access. This remains a compact Floor One slice, not a complete Book 1 or level 1–20 campaign.

## Future campaign work (outside Block A)

- [ ] Author and review the remaining Book 1 campaign and later floors, including supported characters, places, enemy families, encounters, items, recipes, gates, and rewards.
- [ ] Expand skill progression only from evidence or explicitly labeled adaptations. Do not claim a complete canonical rank table or grant rank-20 permission to every skill.
- [ ] Complete and validate remaining Floor One gameplay content before treating the current compact route as full coverage.

| Milestone | Current runtime event to bind |
| --- | --- |
| False Tutorial Guild ambush survived | Clear `false-guild`; quest stage 1 |
| Tutorial briefing received from Mordecai | Interact with `mordecai` after the ambush; quest stage 2 |
| Goblin workshop cleared | Clear `goblin-workshop`; quest stage 3 |
| Floor guardian defeated | Clear `ball-of-swine`; quest stage 4 |
| Floor One exit available | Interact with `exit` after stage 4 |
| Optional Hoarder / Juicer content | Available after the Mordecai briefing; clearing either does not advance the required story stage |

The current runtime owns these event transitions. Authored story definitions should reference these stable event IDs instead of introducing parallel stage logic.
