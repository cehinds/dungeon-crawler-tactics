# Audience, AI Favor and improvised traps

These are original tactical adaptations inspired by the reported audience, crafting and AI Favor concepts in Dungeon Crawler Carl. Their numbers, recipes and permission limits are not verified official RPG rules or canonical formulas.

## Sponsor offers

The Audience panel shows all three offers from the beginning of a run. No offer selection or payment is required.

| Offer | Committed condition | Once-per-run reward |
|---|---|---|
| Chemistry lesson | A player-owned action resolves a tag reaction | 1 Oil Flask |
| Crawler solidarity | Rescue the Lantern Row crawler by either approach | 1 Mega Tonic |
| Survive the broadcast | Win a battle, including enemies falling to hazards | 1 Shock Snare |

Preview and cancel award nothing. The first matching committed event records a saved receipt. Repeated reactions, retries, reloads and subsequent victories cannot repeat an offer's delivery. Shared supplies cap at 10,000 per item; a receipt still settles an offer when supplies are full. Action forecasts show actual available delivery amounts, combining rewards that share an item ID. Rescue forecasts include the sponsor delivery in their combined inventory changes.

Isolated neighborhoods, scenarios and expeditions retain their campaign backup. Their local audience state returns to the original campaign state when the player returns; they do not transfer sampler rewards into the campaign.

## AI Favor

The first committed player-owned tag reaction in each encounter grants **1 AI Favor**. That is the entire encounter grant limit: spending it and causing more reactions cannot earn it again. Previews, enemy actions, animation callbacks and reading panels grant nothing. A fresh encounter or retry resets both the balance and grant counter.

Spend 1 Favor and one explicitly eligible shared supply to perform an extra environmental utility with a living crawler whose turn has not finished. It works before or after that crawler's normal action. It preserves the crawler's existing movement, normal action and finished flags; it neither restores a spent budget nor advances the phase.

The allowed supplies are Oil Flask, Coolant Snare and Shock Snare. Fire Bomb, attacks, ordinary abilities, stances and forms cannot be substituted into a Favor command. The eligible supply still obeys its ordinary range and target rules. Preview shows the same shared-core result as confirmation. Cancel spends neither Favor nor supplies.

## Crafting and trap placement

| Recipe | Ingredient | Output | Next entrant's effect |
|---|---|---|---|
| Assemble Coolant Snare | 1 Coolant Bomb (`item.frost_vial`) | 1 Coolant Snare | Apply Wet |
| Assemble Shock Snare | 1 Shock Tonic (`item.thunder_flask`) | 1 Shock Snare | 5 damage and Shocked |

Craft in the safe room. Story-mode crafting requires the purchased Engineer's Table; the existing home tools increase authored outputs as displayed in the recipe preview. Crafting uses the existing fixed ingredient/output system, not arbitrary free-text invention.

Place a trap within range 3 on an empty, walkable tile without another trap. Normal placement consumes the crawler's action and one trap supply. Favor placement consumes one Favor and one trap supply instead. Both use zero Mana and the same preview resolver. Cancel changes nothing.

A trap affects the **next entrant, ally or enemy**, then disappears. It does not tick damage at round end. Coolant's Wet enables existing cold/lightning reactions; Shocked uses the existing status lifetime and Mana recovery penalty. Movement remains the existing immediate path command, so inspect marked trap tiles before crossing them; there is no new movement-confirmation dialog. Movement, pushes and teleports that enter a trap use the shared occupancy rules. Traps are not ranged attacks and cannot be placed under a creature to deal immediate damage.

## Controls and delivery

The browser Audience panel exposes offer history and Favor utilities, with legal targets supplied by C#. The existing supplies/action flow places traps normally and confirms or cancels forecasts.

Unity's **Audience & Favor** header button opens offer history, earned achievements, safe-room recipes and legal Favor target buttons. Choose a living unfinished crawler, then a listed supply's tile to open the existing action forecast. Confirm or cancel in the normal inspector. Ordinary trap items appear in the existing item list. Trap tiles have text markers. This source was compiled against Unity reference assemblies; no Unity Editor Play Mode run was available.

## Authoring and saves

`game-content.json` adds `sponsorChallenges`: stable ID, label, description, event type (`reaction`, `rescue` or `victory`), reward item and count. Definitions and references are checked by the strict schema, Python validator and C# validator.

`combat-content.json` items opt into Favor with `favorEligible`. A Favor supply must target tiles, have no incoming reaction tags, and contain only `AddTag` effects. There is no general second-action permission.

A trap is an authored AddTag item plus a `tagRules` entry with `consumeOnEntry`, its optional entry damage and required occupant status. Trap rules must have zero duration and zero round damage; the trap remains until triggered. Placement and effects use shared C# rules, without JavaScript damage formulas.

Saves add an optional version-1 `audience` record with balance, encounter grant count and sponsor receipts. Validation rejects invalid balances and duplicate or unknown receipts before replacing live state. Old saves without audience records initialize empty; missing newly introduced trap inventory entries initialize to zero, while every existing nontrap supply remains required. Placed traps persist as saved tile tags, and triggered statuses use existing timed-tag bookkeeping. Preview state is never saved. New run clears all audience records.
