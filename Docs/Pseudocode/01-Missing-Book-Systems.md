# Missing book-inspired systems — design pseudocode

**Status: proposal only.** Nothing here describes implemented behavior or commits gameplay changes. This is a C#-friendly design sketch for the ten systems listed below. Canon facts stay source-gated: use the linked research documents as leads, attach book/chapter evidence to authored mechanics, and leave unsupported timing, numeric limits, and formulas unset. When evidence is absent, an adaptation must be labeled as such or the mechanic remains disabled. Do not infer tabletop rules.

Mechanics are selected by stable IDs and tag/rule queries, never display names or class IDs. JSON is authored truth. Follow the [shared command contract](README.md#shared-command-contract): preview and commit resolve from the same full session snapshot and cloned RNG state, using the same resolver. Preview never advances live RNG. A preview returns its snapshot revision and forecast; confirmation must name that revision and commit the resolved result only if the live session still has that revision. A stale confirmation must be previewed again. Validate before commit, then atomically replace state and RNG; invalid or cancelled commands mutate neither. Saves include a version and migrate missing optional records safely. Resolve committed death before save; a defeated party cannot persist a half-applied action. Stable ordering is ordinal by ID unless authored priority says otherwise.

## Shared command shape

```text
Preview(command, snapshot, revision): validate -> clone full snapshot and RNG -> SharedResolver -> forecast + revision
Commit(command, confirmation): bind command and revision -> resolve same snapshot/RNG -> validate -> commit once
Cancel(preview): discard forecast; preserve live state, inventory, clocks, and RNG
```

## 1. Race selection and progression

**Data IDs:** `race.*`, `prerequisite.*`, `trait.*`, `skill.*`, `source.*`. Authored records contain source references, eligibility predicates, persistent trait grants, advancement rules, and skill-cap permissions. **Save fields:** schema version; selected race ID per crawler; earned trait IDs/advancement values; race selection history; pending allocation; race-specific skill-cap permissions. **Prerequisites:** current story mode already gates class changes and class-tree access on Floor 3 ([Playable game](../PlayableGame.md)); this proposal may align race choice with that existing game gate, but does not claim Floor 3 as canonical race timing. Require a safe-room checkpoint and eligible crawler. See [Lore and mechanics review](../Lore-Mechanics-Review.md), [Progression](../Progression.md), and [Research: classes and skills](../Research-Classes-Skills.md).

### Floor 3 prerequisite preview

```text
PreviewRaceChoices(crawlerId, floorId):
  require crawler exists and is eligible for race choice
  load race definitions in stable race ID order
  evaluate each prerequisite against current saved state
  return eligible choices and blocked choices with unmet prerequisite IDs
  include evidence/adaptation labels and resulting trait/cap deltas
  do not reserve a choice, spend points, or mutate progression
```

### Commit race selection

```text
SelectRace(crawlerId, raceId):
  require floor milestone unlocked and safe-room selection context
  require confirmed preview revision still matches and raceId was eligible in its forecast
  stage selected race ID and initial traits on the full-session/RNG clone
  preserve existing learned skills, equipment, XP, and unrelated traits
  validate trait uniqueness and all referenced IDs, then commit atomically
  invalid input or cancel discards clone and changes nothing
```

### Persistent traits and advancement

```text
ApplyRaceAdvancement(crawlerId, advancementId):
  resolve advancement definition by stable ID and verify its source/adaptation status
  require crawler's selected race and all advancement prerequisites satisfied
  require advancement receipt is not already claimed
  resolve granted trait IDs, removals, and derived-stat changes through shared resolver
  stage receipt and persistent trait delta in resolver result; commit only matching revision
  retain receipts through save/load and prevent duplicate grants on replay
  reject unknown traits or unsatisfied prerequisites without state mutation
```

### Skill-cap permission

```text
GetSkillCap(crawlerId, skillId):
  collect base cap and permissions from race, class, gear, and explicit rewards
  match permission rules by skill tags and stable IDs, not class/display names
  resolve enabled permissions by authored priority then ordinal permission ID
  return cap plus the source IDs and evidence labels explaining the result
  use the same result for skill preview, training validation, and committed gain
```

**Acceptance:** Before the configured floor, race selection is unavailable; on unlock, previews name each unmet requirement and show deltas. Reload preserves race, traits, advancement receipts, and cap permissions. Replaying a grant cannot duplicate it; preview/cancel spends nothing.

## 2. Donut Hole traversal

**Data IDs:** `ability.donut_hole`, `surface.*`, `traversal.*`, `status.*`. Surface eligibility is tag/rule authored. **Save fields:** active traversal ID, endpoints, owner, creation turn, expiry boundary, and blocked state. **Prerequisites:** Donut's ability grant, eligible surface pair, valid endpoints, and a living actor. Rules and duration remain source-gated; no exact canon duration is assumed. See [Signature moves audit](../Signature-Moves-Audit.md) and [Tag rules](../TagRules.md).

### Surface and endpoint preview

```text
PreviewDonutHole(actorId, entryCell, exitCell):
  require actor owns ability ID and both cells are in bounds
  query authored traversal rules for matching surface tags at each endpoint
  reject cells occupied by blocking entities or reserved by incompatible terrain
  report legal pair, path/teleport consequences, cost, and expiry policy
  use no RNG and do not place a traversal marker during forecast
```

### Create temporary traversal

```text
CommitDonutHole(command):
  require confirmed preview revision still matches; use its shared-resolver result
  use staged cost and traversal from same snapshot/RNG clone; atomically replace session
  create traversal record with stable instance ID and explicit expiry boundary
  append presentation event and commit resource plus traversal atomically
  if actor dies before commit validation or either endpoint becomes illegal, reject
```

### Use traversal

```text
TraverseHole(actorId, traversalId):
  require active record, unexpired boundary, eligible actor, and free destination
  use the confirmed preview revision; stale occupancy requires a fresh forecast
  resolve movement and entry-trigger effects with the ordinary movement resolver
  mark use/charges only if movement resolves; preserve unrelated action budgets
  commit movement and traversal update together, or leave both unchanged
```

### Expiration and occupied endpoints

```text
ExpireDonutHoles(turnBoundary):
  select records whose authored expiry boundary has been reached
  order records by creation turn then stable traversal ID
  apply authored policy: safely evacuate footprint in stable entity-ID order, or defer-close
  a deferred-close traversal accepts no new entries; existing occupants retain a legal exit
  stage topology, occupant positions, and events before removing any traversal marker
  atomically validate and replace staged state only if every occupant has a legal outcome
  save/load retains boundary semantics so reload cannot refresh duration
```

**Acceptance:** Only configured surface tags qualify. Occupied/blocked endpoints are rejected with a reason. Preview and cancel place nothing; committed traversal expires once at its declared boundary, including across reload.

## 3. Katia physical shapeshifting

**Data IDs:** `form.*`, `shapeProfile.*`, `massRule.*`, `clearanceRule.*`, `ability.rush`. **Save fields:** current form/profile ID, mass budget and equipped-mass snapshot/reference, mastery receipts, momentum/bracing state, carried-platform IDs and attachment data. **Prerequisites:** Katia's shapeshift grant, legal profile, and a safe action boundary. Same-mass transformation and no copied powers are supported as design constraints; exact mass, shape catalog, and budgets require source evidence or explicit adaptation. See [Lore and mechanics review](../Lore-Mechanics-Review.md).

### Mass and equipment budget

```text
PreviewShape(crawlerId, profileId):
  sum authored body mass and equipped-item mass using stable item IDs
  query target profile's mass envelope and legal equipment compatibility rules
  reject any profile or carried load outside the conserved-mass budget
  report dropped, stowed, or incompatible equipment disposition explicitly
  return stat/footprint delta from shared resolver; do not copy ability grants
```

### Dimensions and clearance

```text
CheckShapeClearance(crawlerId, profileId, originCell):
  resolve occupied-cell footprint and height/width clearance from profile data
  test every covered cell for bounds, walls, units, hazards, and reserved objects
  apply authored doorway and ceiling rules in stable cell order
  return first blocking cell plus complete valid footprint for UI explanation
  do not move occupants or alter map collision during preview
```

### Commit physical shape

```text
CommitShape(crawlerId, profileId):
  require confirmed preview revision still matches; take equipment, footprint, and form result from shared resolver
  stage on its full session/RNG clone; set newHP=min(oldHP,newMaxHP), newMana=min(oldMana,newMaxMana)
  preserve learned skills and granted abilities; appearance grants no copied powers; never heal on change
  if oldHP is zero, preserve zero HP and keep the crawler down
  resolve overlap and resource caps before replacing live state atomically
  invalid profile, insufficient budget, or cancel leaves form and equipment unchanged
```

### Momentum and bracing

```text
ResolveRush(crawlerId, destination):
  read current movement vector, mass profile, terrain tags, and Rush rule data
  preview path, stopping clearance, collision consequences, and action/movement costs
  share cloned RNG outcome for explicitly random authored rule; persist clone only on matching commit
  resolve collision/bracing with shared physics-like rules and ordered event records
  stop at first illegal cell; never grant momentum from preview or animation timing
```

### Carrying platforms

```text
CarryPlatform(crawlerId, platformId, attachCell):
  require platform has carryable tag, valid anchor, and compatible form clearance
  calculate combined carried mass against shape and movement budgets
  preview route and every cell's platform footprint before accepting attachment
  commit attachment and platform ownership atomically; persist relative anchor/orientation
  detach by explicit rule or authored event; never silently delete a carried platform
```

**Acceptance:** A shape cannot exceed authored mass or clearance; carried load affects the same forecast used at commit. Shape changes preserve skills and ability grants. Invalid/cancel leaves gear, position, momentum, and form untouched.

## 4. Mongo companion progression

**Data IDs:** `companion.mongo`, `companionStage.*`, `command.*`, `petGear.*`, `growthSource.*`. **Save fields:** companion ID, XP/growth receipts, stage ID, command unlock IDs, owned/equipped pet gear, visual profile ID, movement profile ID, health/conditions, and RNG stream reference if needed. **Prerequisites:** Mongo is assigned as a companion; companion progression is separate from crawler race/class/stat allocation. Book sources support pets, but Mongo's progression schedule and exact stages must be evidence-gated. See [Lore and mechanics review](../Lore-Mechanics-Review.md).

### Award sourced growth

```text
AwardCompanionGrowth(companionId, sourceEventId):
  resolve growth rule by source event ID and require source evidence or adaptation label
  reject duplicate receipt and unsupported event types
  calculate growth from authored rule without touching crawler XP or stat points
  advance stage using configured thresholds in stable order and record each receipt
  commit companion progression with the triggering event's transaction
```

### Stage visual and movement

```text
ResolveCompanionStage(companionId):
  select highest unlocked stage by authored threshold then stable stage ID
  load visual profile and movement profile referenced by that stage
  validate both profiles exist before changing saved stage pointer
  return presentation references and movement capabilities as separate values
  missing art may use explicit fallback profile; it cannot grant new mechanics
```

### Commands

```text
PreviewCompanionCommand(companionId, commandId, targetId):
  require command unlocked for current stage and companion is available/alive
  validate target tags, range, command budget, and encounter restrictions
  resolve effects through shared action resolver and return exact resource/status forecast
  commit revalidates and spends companion budget atomically with effects
  cancel or invalid target spends neither companion nor crawler resources
```

### Companion gear

```text
EquipPetGear(companionId, gearId, slotId):
  require gear owned, slot accepted by gear tags, and companion load limits satisfied
  preview derived companion effects and any displaced item using shared resolver
  commit ownership/equipment changes atomically; gear bonuses never alter crawler race
  save gear IDs and validate references before replacing state on load
  reject duplicate or incompatible slot occupancy without partial unequip
```

**Acceptance:** Companion XP never adds crawler levels or stat points. Stage visuals and movement are independently sourced by IDs. Commands and gear preview exact effects; reload preserves all companion records.

## 5. Cookbook and environmental knowledge

**Data IDs:** `knowledge.*`, `recipe.*`, `clue.*`, `solution.*`, `experiment.*`, `source.*`. **Save fields:** discovered knowledge IDs, known recipe IDs, clue receipts, experiment records, and environmental solution receipts per floor. **Prerequisites:** observation or experiment in a valid context; advanced recipe use may require authored workbench/location tags. Simple combinations and specialized crafting contexts remain source-gated. See [Lore and mechanics review](../Lore-Mechanics-Review.md), [Tag rules](../TagRules.md), and [Mechanics plan](../Mechanics-Plan.md).

### Discover inherited knowledge and recipes

```text
DiscoverKnowledge(actorId, discoveryId):
  require discovery is present in current context and actor can observe it
  load knowledge record with source/adaptation label and linked recipe IDs
  record stable discovery receipt once; merge learned recipe IDs in ordinal order
  show whether each recipe is known, usable here, or waiting on ingredients/tools
  duplicate observations may narrate recall but cannot duplicate inventory rewards
```

### Clue unlocks environmental solution

```text
ApplyClue(clueId, environmentId):
  match clue's target tags and prerequisite knowledge against current environment
  return candidate solution IDs and missing clues without changing the map
  on commit, record clue receipt and unlock only explicitly referenced solutions
  solution effects use authored environmental rules and existing resolver effects
  never infer solution from display text or consume a clue on failed validation
```

### Record experiments

```text
RecordExperiment(actorId, inputIds, contextId):
  normalize inputs as sorted stable IDs and match authored experiment patterns
  show known outcome, safe failure, and any cost in a shared preview
  on commit, consume only validated inputs and record outcome receipt atomically
  deterministic experiments use no RNG; authored chance uses shared cloned RNG outcome
  unknown combinations may be logged as observations without inventing a recipe
```

### Craft from cookbook

```text
CraftFromRecipe(actorId, recipeId, locationTags):
  require recipe known, required station tags present, and all ingredient counts available
  forecast outputs, substitutions, byproducts, and environmental effects
  resolve complete transaction on clone; validate inventory capacity and references
  commit consumption and output together; cancel or invalid state consumes nothing
  recipe source status remains visible as canon-supported, uncertain, or adaptation
```

**Acceptance:** A recorded clue unlocks only its authored solution IDs. Experiment records survive reload and replay cannot duplicate rewards. Ingredient shortage, unavailable station, or cancellation leaves inventory unchanged.

## 6. Improvised construction

**Data IDs:** `material.*`, `constructionRecipe.*`, `contraption.*`, `part.*`, `trap.*`, `tool.*`. **Save fields:** inventory material counts, constructed object instance IDs, part IDs/positions/orientation, armed state, durability, ownership, and creation event. **Prerequisites:** suitable material tags, valid surface/space, and any authored tool/station context. Exact recipes are adaptations unless directly sourced. See [Audience and traps](../Audience-and-Traps.md), [Mechanics plan](../Mechanics-Plan.md), and [Book fidelity checklist](../Book-Fidelity-Checklist.md).

### Build bombs, traps, and tools

```text
PreviewConstruction(actorId, recipeId, location, targetCell):
  match recipe input tags and counts against inventory by stable material ID
  validate target footprint, placement tags, required tool, and encounter limits
  forecast resource costs, created object effects, and affected cells
  return every missing ingredient or blocked cell; do not consume or spawn objects
  use same BuildResolver as commit, with deterministic ordering and no RNG
```

### Commit construction atomically

```text
CommitConstruction(command):
  rerun recipe, inventory, space, and permission checks on current state
  clone state; consume ingredients and create stable instance ID in the clone
  initialize object from recipe data, including armed/durability fields and tags
  validate complete resulting inventory and map state before one atomic replacement
  invalid or cancelled construction leaves supplies, actions, and map unchanged
```

### Multipart persistent contraptions

```text
AttachContraptionPart(actorId, contraptionId, partId, cell, orientation):
  require contraption active and part owned, attachable, and not already installed
  validate connector tags, total footprint, adjacency, and collision for all parts
  preview structural state and resulting behavior through a shared contraption resolver
  commit part placement and resource/action costs together; persist stable part instance
  load rebuilds from IDs and rejects malformed graphs without deleting the saved run
```

### Arm, trigger, and dismantle

```text
ResolveConstructedObjectEvent(objectId, eventId):
  match event tags against authored trigger rules and object armed/durability state
  order matching rules by priority then stable ID; resolve bounded child events
  update object state, triggered effects, and consumed parts in one transaction
  dismantle only through an explicit command/rule and return only authored salvage
  persist trigger receipt so reload cannot replay an already committed explosion
```

**Acceptance:** Previews enumerate ingredients and placement failures. Constructed objects and multipart state survive reload; replayed trigger events cannot duplicate effects. Failed placement never consumes materials.

## 7. Floor deadlines and descent pressure

**Data IDs:** `floorClock.*`, `deadline.*`, `descentObjective.*`, `pausePolicy.*`. **Save fields:** floor clock remaining units, clock policy ID, last committed clock event, deadline receipts, evacuation state, and closing opportunity IDs. **Prerequisites:** floor has an explicitly authored clock and objective; clocks are disabled if duration/trigger evidence is unknown. No canon timeline or exact number is invented. See [Story levels](../Story-Levels.md), [Lore and mechanics review](../Lore-Mechanics-Review.md), and [Playable game](../PlayableGame.md).

### Clock policy and remaining time

```text
GetFloorClock(floorId):
  load authored clock policy; if absent, return Disabled with reason and no countdown
  expose remaining units and required descent objective from saved floor state
  derive display urgency from configured bands, not wall-clock time
  provide exact pause/advance rules for combat, exploration, menus, and loading
  never decrement time during preview, animation, pause, save, or reload
```

### Advance floor clock

```text
AdvanceFloorClock(eventId, floorId):
  require event type listed by floor's pause/clock policy and receipt not present
  compute authored elapsed units deterministically from event data
  clamp at deadline boundary and record event receipt exactly once
  emit warning/closing opportunity events from authored thresholds in stable order
  commit clock and emitted events together; ignore real-world elapsed time
```

### Evacuation and closing opportunities

```text
ResolveDeadline(floorId):
  if clock disabled or remaining time positive, report no deadline transition
  select authored evacuation objective and available closing opportunity rules
  stage automatic closures and consequences explicitly defined by the clock policy
  if a decision is required, block incompatible actions until a legal choice is made
  commit the boundary once; reload or declining a choice cannot reset elapsed time
```

### Descent requirement

```text
PreviewDescent(floorId, exitId):
  check required objective IDs, evacuation condition, party state, and exit tags
  return satisfied and unmet conditions with source/adaptation labels
  show any remaining time and closing opportunities affected by descent
  on commit, revalidate and update floor progression atomically
  failed or cancelled descent preserves clock, party, and objective receipts
```

**Acceptance:** A floor without authored timing data has no clock. Menus and save/load obey explicit pause rules. Deadline and descent transitions are idempotent, forecastable, and cannot partially advance the campaign.

## 8. Audience popularity and show consequences

**Data IDs:** `audienceInterest.*`, `audienceEvent.*`, `sponsor.*`, `interview.*`, `rivalry.*`, `consequence.*`. **Save fields:** views/followers or configured proxies, interest values by stable topic ID, committed event receipts, sponsor offers/claims, interview history, rivalry state, and consequences. **Prerequisites:** an audience event authored for the campaign; metrics and rewards are adaptations unless sourced. See [Audience and traps](../Audience-and-Traps.md), [Mechanics plan](../Mechanics-Plan.md), and [Lore and mechanics review](../Lore-Mechanics-Review.md).

### Record views, followers, and interest

```text
RecordAudienceEvent(eventId, actorId, actionTags):
  match committed action tags to authored audience event rules by stable ID
  calculate configured view/follower/interest deltas without hidden display-name matching
  use deterministic deltas by default; random rules resolve against cloned session RNG
  save one event receipt and apply clamped metrics from revision-bound resolver result
  preview exposes that result without advancing the live RNG
```

### Unusual acts and sponsors

```text
EvaluateSponsorOffers(audienceState, eventId):
  filter offers by explicit achievement/event predicates and eligibility window
  order offers by priority then stable sponsor ID; calculate rewards and conflicts
  show all unmet criteria and whether an offer is once-only or repeatable
  claim on commit with an idempotent receipt and atomic reward delivery
  full inventory must follow authored overflow policy, never silently lose a reward
```

### Interviews

```text
ResolveInterview(interviewId, choiceId):
  validate interview availability and choice IDs against current audience context
  preview effects on interest topics, relationship/faction flags, and future offers
  apply authored consequences through shared resolver; no inferred prose scoring
  commit choice receipt and effects atomically, then close or update interview state
  preserve source/adaptation label and prohibit duplicate reward on reload
```

### Rivalries and consequences

```text
UpdateRivalry(rivalryId, eventId):
  require matching public event and rivalry rule prerequisites
  calculate state transition from prior saved rivalry stage and event tags
  preview consequences such as offers, dialogue, hostility, or encounter modifiers
  commit stage, event receipt, and consequence records together
  deterministic ordering resolves simultaneous rivalries by stable rivalry ID
```

**Acceptance:** Only committed qualifying acts affect audience state. Preview has no random draw. Sponsor claims and interview consequences are once-only where configured and survive save/load with inspectable causes.

## 9. Potion overuse and recovery

**Data IDs:** `potionRule.*`, `potionSource.*`, `status.potionOveruse.*`, `recoveryRule.*`. **Save fields:** use counts by configured window/source, active overuse statuses with source/remaining duration/stack policy, recovery receipts, and clock boundary state. **Prerequisites:** a potion has an explicit overuse rule backed by a cited source or labeled adaptation. Do not assert universal thresholds, durations, or tabletop rules. See [Book fidelity checklist](../Book-Fidelity-Checklist.md), [Lore and mechanics review](../Lore-Mechanics-Review.md), and [Tag rules](../TagRules.md).

### Resolve potion use and overuse

```text
PreviewPotionUse(actorId, potionId):
  load potion rule and source status; if no overuse rule exists, report none configured
  count prior committed uses within the rule's authored window and reset boundaries
  forecast potion effect plus threshold crossing, status changes, and recovery needs
  resolve with shared action engine and cloned RNG; leave live counters and RNG untouched
  identify uncertain/source-gated rules as disabled until reviewed
```

### Commit use and status

```text
CommitPotionUse(command):
  require confirmed preview revision still matches, including potion ownership and use window
  resolve potion effects and overuse transition on the same working state
  record use receipt and status source/expiry/stacking policy from authored rule
  validate inventory and status invariants; atomically apply effects and consumption
  death/defeat resolution occurs before save; invalid/cancel changes nothing
```

### Forecast recovery

```text
PreviewRecovery(actorId, recoveryId):
  match recovery rule against active overuse statuses and context tags
  calculate eligible status removals, elapsed boundaries, costs, and remaining duration
  show which statuses will persist and why; do not reset potion counters implicitly
  commit applies the confirmed shared-resolver removals/boundary advances on the matching revision
  save recovery receipt to prevent reload from repeating a consumable recovery
```

**Acceptance:** Unconfigured potion sources do not acquire invented penalties. Forecast identifies threshold/status changes; committed use alone updates counters. Recovery duration/stacking follows explicit rules and persists correctly through load.

## 10. Persistent social systems

**Data IDs:** `npc.*`, `relationship.*`, `alliance.*`, `faction.*`, `dialogue.*`, `service.*`, `interior.*`. **Save fields:** relationship values/flags, alliance receipts, faction standing, hostility state, dialogue choices, shop inventories/receipts, service unlocks, club credentials, and interior discovery/ownership. **Prerequisites:** authored NPC/faction and context; relationship effects, access, and full club interiors remain proposals until source evidence or adaptation labels are supplied. See [Journey and home](../Journey-and-Home.md), [Over City neighborhood](../Over-City-Neighborhood.md), and [Lore and mechanics review](../Lore-Mechanics-Review.md).

### NPC relationships and alliances

```text
ApplySocialEvent(npcId, eventId):
  match event tags to relationship rules and verify prerequisite receipts
  calculate bounded relationship/flag changes using stable rule order
  preview alliance eligibility and resulting dialogue/service effects
  commit relationship values and unique alliance receipt atomically
  duplicate event IDs cannot repeat permanent alliance or reward changes
```

### Faction dialogue and hostility

```text
ResolveFactionDialogue(factionId, dialogueId, choiceId):
  validate location, faction standing, hostility, and dialogue prerequisite IDs
  return available choices and blocked choices with exact missing conditions
  preview consequences to standing, hostility, alliances, and future dialogue
  commit selected choice plus consequence receipts as one state transition
  use original authored dialogue text; rules reference IDs and tags only
```

### Shops and services

```text
PreviewSocialService(actorId, serviceId, offerId):
  require service available in current context and actor meets access predicates
  calculate price, stock, inventory capacity, relationship/faction gates, and effects
  show exact before/after values and deterministic stock state
  commit applies the shared-resolver transfer only if the confirmation revision still matches
  invalid/cancel leaves currency, stock, inventory, and relationship unchanged
```

### Club interiors and credentials

```text
EnterClubInterior(actorId, interiorId):
  validate interior exists, credential/source rules, faction state, and entry context
  preview available rooms, NPC services, and exits from stable interior IDs
  commit records discovery/entry only; purchases and choices use their own transactions
  save room discovery and credential receipts; reload restores the same access state
  unknown canonical access conditions remain source-gated rather than guessed
```

**Acceptance:** Relationships, alliances, faction hostility, shop/service effects, and room access survive reload. Blocked dialogue/service choices explain unmet IDs. No name-based mechanics or replayable permanent rewards.

## Cross-system acceptance checks

- Every data reference resolves through strict JSON validation; all mechanic IDs are stable and unique.
- For every command, preview and commit use one resolver on the same full snapshot and cloned RNG; preview is side-effect-free against live state.
- Confirmation is bound to the preview revision; changed state requires a fresh preview and cannot use stale results.
- Commit applies the staged resolver result and cloned RNG atomically; it does not separately mutate through preview routines.
- Cancel, stale preview, malformed save, and invalid target leave authoritative state and RNG unchanged.
- Save migration initializes absent optional system records, validates present records before replacement, and retains death/defeat outcome consistently.
- Acceptance scenarios above are behavioral gates for a future implementation. This document does not claim those systems or checks exist in the game.
