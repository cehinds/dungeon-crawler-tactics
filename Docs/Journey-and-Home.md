# Story campaign, progression and the party house

Open **18-floor journey** in camp. Starting it replaces the active run only after an explicit review; export the old save from that dialog if you want both. Ordinary imported saves continue in the original three-encounter mode. Optional expeditions and boss scenarios preserve and restore their campaign checkpoint.

## The first eight floors

| Floor | Playable adaptation |
|---|---|
| 1–2 | Tutorial exploration and combat; personal actions remain usable while class selection and stat spending are locked. |
| 3 | Over City: class selection and accumulated stat points become available. Later documented class options remain gated. |
| 4 | Iron Tangle: find and operate the route control before entering the encounter. The party house becomes available. |
| 5 | Bubble: inspect the four Land, Sea, Air and Subterranean objectives before the battle. These are a compact substitute for four full castle campaigns. |
| 6 | Hunting Grounds: inspect hunter intentions and resolve the tactical encounter. |
| 7 | Great Race: an explicit destroyed-floor bypass, with no invented race battle or XP reward. |
| 8 | Ghosts of Earth: weaken and capture six enemies using a three-tile action. Review and confirm each capture. Accidentally defeated ghosts reform weakened so the objective cannot become impossible. |
| 9–18 | Listed in the registry and locked. Unknown details are not invented as book facts. |

The capture system implements a collection objective, not the novel’s complete T’Ghee deck combat. Enemies and tile layouts are authored tactical adaptations. The [floor/enemy research](Research-Floors-Enemies.md) separates documented weaknesses from proposed tactical opportunities.

## Algorithmic progression

Party XP is shared. The first five cumulative thresholds remain `0, 30, 70, 120, 200`. For level `L > 5`, add `40 + 10*(L-5) + floor(3*(L-5)^2/2)` to the previous threshold. Level 50 requires 59,431 XP, allowing a final-floor build before the last encounter. This curve and the floor rewards are game balance, not published canonical numbers.

Class trees grant one point at each authored tier: 1, 5, 10, 20, 30, 40, 50. There are fourteen nodes across two branches and seven points by level 50. The selected class determines active bonuses and grants; saved ownership survives class changes. Personal crawler trees use a separate pool.

Training ranks are separate from party level. Rank thresholds start at 0, 3 and 8 committed uses; subsequent increments use the squared zero-based rank index, multiplied by four from rank 11 onward. Per-ability profiles can adjust training speed, bounded damage/healing, cost reduction and milestones. Items and canceled previews do not train. Ordinary rank eligibility is 15; configured Primal eligibility reaches 20 after floor 3. View exact tables under **Development → Rank reference**. The shared C# resolver consumes these same values.

The [research codex](https://cehinds.github.io/dungeon-crawler-tactics/codex.html) covers 122 source-attested class names, including four verified Book 8 options reserved for floor 10. Its class trees and complete numerical rank rows are extrapolations. It does not claim an exhaustive audit of every published sentence or imply that unknown canonical effects are known.

## A shared house with purchased facilities

Open **Personal space** in camp. Select a bedroom or shared facility on the floor plan. Purchases show the exact current gold, price and remaining balance; cancel leaves the saved game unchanged.

| Upgrade | Gold | Current function |
|---|---:|---|
| Shared personal space | 50,000 | Opens eight private bedrooms and the shared lounge. The bundled layout is an adaptation of the documented base offer. |
| Training Room | 250,000 | One paid eligible nonmagical practice session per crawler per floor. |
| Engineer’s Table | 25,000 | Enables story-mode supply crafting; this reported price is approximate. |
| Enhanced Crafting Studio | 255,000 | Adds one unit to each recipe output. The price is documented; this numerical benefit is adapted. |
| Social Screen | 50,000 | Displays the local achievement, victory and captured-card record. It is not an external social network. |

The game starts with 100,000 gold and awards `100,000 + 25,000*floor` for each first campaign victory. Receipts prevent repeat rewards. Training costs 1,000 gold and adds one use per session. These income, timing and training formulas are explicitly adapted. The novels instead describe time-limited training; the [housing research](Research-Housing.md) preserves that distinction.

The Compensated Anarchist kit can claim a personal Desperado credential from floor 3. It charges no gold, is saved per crawler, and excludes Mongo. Changing to an ineligible class retains the historical credential while blocking current entry eligibility. Vanquisher access is not sold as an invented universal pass. Full club interiors, deity quests and all exceptional access rules are not simulated.

## Editing the game

- Author maps, journey objectives, housing prices and class trees in `UnityPackage/Runtime/Data/game-content.json`; combat tags and actions live in `combat-content.json`.
- `Tools/build_lore_catalog.py` regenerates the documented class profiles and level thresholds. It preserves unrelated journey and housing content.
- `SkillRankProgression` provides the runtime rank algorithm; `GameSession.Journey`, `.Home` and `.SkillTree` own their narrow systems.
- `Tools/prepare_research.py` publishes the source-linked research snapshots. `Tools/prepare_unity_project.py` synchronizes the canonical C# and JSON into the Unity project.
- The [menu atlas](https://cehinds.github.io/dungeon-crawler-tactics/menu-atlas.html) presents six illustrations and thirty separate stateful components. [Art direction](Art-Direction.md) documents reusable icons, tile anchors and layers.

The browser runs the shared C# game through .NET WebAssembly. Native Unity Editor execution and Unity Web export remain unverified; Unity’s current presenter is still the older IMGUI layer.
