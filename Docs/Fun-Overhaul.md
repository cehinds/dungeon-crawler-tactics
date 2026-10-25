# Gameplay overhaul — design proposal

Status: concepts and implementation brief, not shipped gameplay. The previous
chamber pass remains the current game. New objectives, movement rules, enemy
plans and traversal interactions below require implementation and playtesting.

## What needs to change

The current loop offers many menus and classes but too few consequential room
decisions. Code review found that ordinary exploration is mostly reveal/cache/
lore/encounter-door interaction; most battle outcomes require every enemy dead;
enemy AI skips tile abilities and moves only when it cannot already attack;
range is Manhattan distance without wall occlusion; and moving even one tile
spends the entire movement activation. These are code findings, not a new user
playtest study.

Relevant sources: `GameSession.Exploration.cs`, `GameSession.cs`,
`RulesEngine.cs`, `game.js`, and authored `combat-content.json`.

## The next playable slice: steal the broadcast battery

Proposed original scenario; not a named book event. Build one satisfying
8–10 minute run before expanding its systems across eight floors.

1. **See a goal immediately.** A stranded crawler has a broadcast battery;
   recover both and reach the extraction lift. A short in-world briefing shows
   the destination. Four familiar crawlers begin with useful, distinct actions.
2. **Choose a route.** Cross the guarded main aisle, open a maintenance passage,
   or visit an optional supply alcove. A valve prepares Wet terrain; a tripwire
   prepares an ambush. Each interaction previews its consequence. Exploration
   has no turn-end clicks in safe space. Avoid a punishing global travel timer;
   any alert increase comes from explicit risky interactions.
3. **Resolve a compact encounter.** Fight a charger, a ranged guard and a
   saboteur around the battery. Their intended targets, threatened cells and
   fallback behavior are visible. Use the room to break their plan. Reaching
   the objective can succeed while enemies remain alive.
4. **Extract, then change the next run.** Taking the battery starts a clearly
   announced round countdown with a preview of the exit route. Rescue and
   extraction grant the main reward. Optional supplies and clever-combo
   achievements give bonuses; no hidden style-score gate blocks progress.
   Choose one meaningful upgrade and return to the house or replay another route.

## Moment-to-moment controls

- Click/tap a destination to preview a path and its hazards, then commit through
  the same interaction. Party followers occupy distinct visible spaces during
  exploration. Doors and interactables have a generous contextual target.
- Replace `moved` as the sole movement budget with remaining movement points.
  Move two cells, act, then spend the remaining two. Keep one main action;
  do not introduce a second general-purpose action-point currency.
- Keep a compact exact attack forecast beside its target and a Confirm button.
  Leave optional detailed modal inspection for the player. Do not require
  another modal to end a fully spent activation. If movement or an action
  remains, a compact anchored confirmation explains what will be forfeited.
- End character turn selects the next ready crawler. Enemy phase begins only
  after all living party members finish. Summons remain visibly distinct.
- Contextual quick actions expose likely useful abilities; the complete action
  book remains one tap away. Inspect explains range, Mana, effects and target
  requirements before resources are spent.
- A short movement animation, impact, status icon and concise event callout
  accompany each resolution. Effects draw above actors. Routine notices never
  intercept a map tap. Playback can be accelerated or skipped.

## Make environmental play worth its cost

- Author a guaranteed useful interaction in the first room: charge into an
  armed lane, push into an existing hazard, or prepare Wet before Lightning.
- Give each reaction a visible causal preview: affected tiles, affected units,
  friendly fire, tag consumption, cost and resulting state. No damage formula
  lives in JavaScript presentation code.
- Add bounded area footprints and reaction propagation only with a documented
  event order, maximum depth and visited-target rule. Never introduce an
  unbounded chain reaction just to match an illustration.
- Add data-authored targeting policies for line of sight, arcing and self/tile
  abilities. Solid walls must have an intentional, explained effect on ranged
  targeting. Preview and actual resolution enforce the same policy.
- Enemy plans reference real abilities and legal targets. Show whether the
  plan locks a location or tracks a unit, and what happens if disrupted.

## Party identity and lore boundaries

The existing source audit remains authoritative. These roles and interaction
rules are tactical adaptations, not claims about canonical damage formulas.

| Crawler | Distinct contribution | Art and lore constraint |
| --- | --- | --- |
| Carl | Rig traps, improvise explosives, push enemies and manipulate machinery | Barefoot brawler; explosives/traps anchored to Compensated Anarchist identity |
| Princess Donut | Magic Missile, mobility and utility spells, companion support | Small crowned Persian cat; don't turn her into a human mage |
| Katia | Choose physical forms, brace or force passages, carry and charge | Mass-constrained physical shapeshifting; forms do not copy spell powers |
| Mongo | Ground scouting, pressure, interception and distraction | Feathered raptor with folded forelimb wings; no pterodactyl or unsupported flight claim |

Mordecai remains a house advisor. New achievements use original short comic
lines. Numerical benefits, independent Mongo turns, traversal effects and
audience rewards remain explicit game adaptations.

## Visual alternatives

The generated concepts are targets, not screenshots or evidence of implemented
systems. Each is a single game viewport at a requested 1672×941 composition.

- **Torchlight Expedition:** overhead pixel-art exploration; connected rooms,
  warm refuge, visible paths and contextual interactions, minimal combat UI.
- **Chain-Reaction Tactics:** close isometric combat; readable enemy intent,
  projected displacement and hazards, a compact target forecast and action bar.
- **The Dungeon Show:** emerald/copper industrial game-show dungeon; exploration
  and an objective ambush share one visible space, with environmental rigging
  and restrained comic achievement feedback.

Displayed concept order in the 24 October ideation set:

1. [Torchlight Expedition](https://github.com/cehinds/AI-Art/blob/dungeon-crawler/dungeon-crawler-tactics/Docs/ConceptArt/Overhaul/torchlight-expedition.png)
2. [The Dungeon Show](https://github.com/cehinds/AI-Art/blob/dungeon-crawler/dungeon-crawler-tactics/Docs/ConceptArt/Overhaul/dungeon-show.png)
3. [Chain-Reaction Tactics](https://github.com/cehinds/AI-Art/blob/dungeon-crawler/dungeon-crawler-tactics/Docs/ConceptArt/Overhaul/chain-reaction-tactics.png)

Original generated PNGs are retained without modification. The illustrations
are visual targets, not validated tactical layouts or final sprite sheets.
Final UI assets must correct generated icon/label inconsistencies (particularly
the hand-shaped Powerful Strike illustration, which should communicate a kick)
and show actual Mana labels, turn state and resolver outcomes.

Use the user's selected visual target before replacing production presentation.
The artwork must be broken into a grid-matched environment kit, four-direction
character animation sets, effects and UI components; a concept image must never
be pasted over the game and presented as working gameplay.

## Implementation sequence and acceptance checklist

- [x] Inspect current code and screenshots; identify the friction above.
- [x] Define a compact objective scenario and party roles.
- [ ] Select the new visual target from generated concepts.
- [ ] Build a greybox objective encounter with deterministic extraction success,
  timeout, defeat/retry and optional rescue rewards.
- [ ] Implement remaining movement points, shared preview/commit and save migration.
- [ ] Implement readable enemy plans, deliberate wall-targeting rules and bounded
  environmental effects; verify cancel cannot spend resources.
- [ ] Connect exploration switches, alternate route and optional supply alcove
  to the battle state. No encounter reset should discard preparation.
- [ ] Replace redundant modal steps with compact contextual feedback, retaining
  confirm/cancel for costly actions and explicit turn forfeits.
- [ ] Produce a reusable art kit from the selected concept and integrate it into
  the real renderer. Verify animation anchors, all four map rotations and phone input.
- [ ] Playtest the entire loop: meaningful choice within 30 seconds, a useful
  environmental opportunity in the first fight, a winnable escape without
  killing every enemy, and no mandatory scrolling between world and actions.
- [ ] Ask fresh players to identify their goal and the next enemy action without
  coaching, then observe whether they choose a different route or combo on replay.
- [ ] Validate mid-objective saves, old campaign saves, exact return from the new
  scenario, Unity-compatible source compilation and desktop/mobile browser flow.

New systems stay in small pure-C# modules behind authored objective, interaction,
targeting and enemy-plan records. Stable IDs and explicit schema/save versions
remain mandatory. Launch the slice as an optional scenario that preserves the
current campaign, then expand only after the loop works in playtests.
