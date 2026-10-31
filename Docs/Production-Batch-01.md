# Production batch 01 handoff

**Date:** 2026-10-30  
**State:** local browser integration and focused checks are complete; AI-Art publication is complete; game publication and deployment are tracked separately.

## Workstreams and ownership

Assignments follow the repository working agreement: the coordinator and code/integration work use GPT-6.1 Sol; content, documentation, and fixture work use GPT-6 Luna. Individual agent identities are omitted here because the handoff tracks workstream responsibility, not chat assignments.

| Workstream | Owner/model | Handoff state |
|---|---|---|
| UI hybrid, shared runtime integration, final coordination | Coordinator / GPT-6.1 Sol | Implemented and locally checked; publication pending |
| Fire/thaw reaction mechanics | Code specialist / GPT-6.1 Sol | Implemented; focused and regression checks passed |
| Story progression and rank data | Code specialist / GPT-6.1 Sol | Implemented; fresh WASM and focused suites passed |
| Content/source audit and manager documentation | Content/docs specialist / GPT-6 Luna | Delivered; runtime monster proposals remain unimplemented |
| Art source sheets and export | Upstream AI-Art workstream; generation model/individual author not recorded here | Source files published in AI-Art commit `5991dab` |
| Browser screenshot and UI QA | Integration QA workstream; model not recorded here | Local desktop and phone captures passed |

## Delivered

- [x] **Two sequential art cycles:** two concept scenes and two separate production sheets for combat and exploration. The source batch contains 48 generated components (24 per cycle) plus 13 derived structural variants, for 61 exports. [Art overview](BroadcastArt/README.md) · [art QA](BroadcastArt/QA.md)
- [x] **UI hybrid:** compact command deck and broadcast feedback are integrated in the browser. The focused HUD suite covers 70 presentation states. The local browser gallery shows 61 assets and both concepts; desktop (1440×900) and phone (390×844) checks passed. [Gallery](../Web/wwwroot/broadcast-kit.html) · [UI completion evidence](Completion-Checklist.md)
- [x] **Gameplay and level-up:** fresh shared-C# WASM checks passed for action targeting/commit and a level-up notice. These checks used explicit validated encounter setup; they do not claim an earned end-to-end campaign playthrough. [Detailed reports and limits](Completion-Checklist.md)
- [x] **Mechanics:** fire thawing frozen targets is an authored adaptation using existing effects. Fifteen new thermal checks and 54 mechanism checks passed. [Mechanics handoff](Mechanics-Expansion.md)
- [x] **Progression:** fresh story victory pacing reaches level 25 at the Floor 8 finish while retaining the level-50 cap and legacy XP/level state. JourneyTests passed 105 checks; RankTests passed 97. [Progression](Progression.md) · [full check record](Completion-Checklist.md)
- [x] **Content inventory:** 64 runtime enemy definitions are mapped across legacy encounters, scenarios, expeditions, and journey floors. All 95 abilities have runtime rank profiles through rank 20. The 12-entry monster/ability list is a proposal set, not implemented content. [Content audit](Content-Expansion-Audit.md) · [machine-readable mapping](../Research/broadcast-content-audit.json)

## Remaining work

- [x] Publish the reviewed art to AI-Art `dungeon-crawler` (`5991dabf4db68a73e5bbc4bc398f331364f4f612`) and pin the exact index digest in the game lock. All 244,061 prior index records remain unchanged; 69 new kit records were added.
- [ ] Confirm the game Pages deployment succeeds after publication. Local browser checks do not mean a public release has happened.
- [ ] Build an adapter that consumes the new kit in the room/map generator. The exports and edge metadata alone do not establish generator compatibility.
- [ ] Review assembled terrain for pixel texture seams. Structural edge intervals pass; painted color continuity is still unreviewed for production use.
- [ ] Expand walking, attack, and cast animation coverage for the new combatants and actions.
- [ ] Select and implement any monster proposals from the 12-entry audit. None of those proposals are included in this batch’s runtime integration.
- [ ] Implement and visually validate native Unity presentation parity. Browser/WASM checks are not Unity Editor or Unity Web validation.

This handoff records the completed batch and its limits. It makes no new roadmap commitments and does not claim exhaustive canon coverage.

The inherited art pin contains 244,061 prior records. This workspace did not hydrate that entire library: 222,116 prior paths were absent and 9,273 existing study/metadata files initially differed. Existing runtime PNGs matched; 20 differing runtime JSON manifests were backed up and restored to pinned bytes before browser reruns. New art validation and browser-observed asset hashes are recorded separately; a complete index restore is not claimed.

After targeted restoration and a fresh WASM publish, browser-request audits passed: 122 paths for cast/move/turn, 123 for level-up, and 64 for the gallery. The tracked game-owned generation rules are explicitly distinguished from pinned art. All 69 new kit files match the published art index.

The inherited 11.74 GiB indexed library is compacted for Pages by the existing publication policy. Applying that policy to the complete index leaves 837,425,948 art bytes; adding the current 49,239,826 non-art publish bytes estimates 886,665,774 bytes, below the enforced 1,000,000,000-byte limit. This is an index-based estimate, not a fully hydrated CI artifact measurement. The three publication-policy regression tests pass; CI must still verify its actual artifact.
