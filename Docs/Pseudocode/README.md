# Dungeon Crawler Tactics — feature pseudocode specification

**Design specification only. No gameplay features were implemented by writing these documents.**

Implementation tracking: [the first connected-expedition delivery](../Generated-Campaign.md) now implements a bounded part of the adventure-loop package. The pseudocode below remains a design reference, not a declaration that all listed features or exact proposed APIs exist.

This breaks down the preceding feature checklist into named, high-level pseudocode features. Each system identifies authored data, saved state, dependencies, behavior and acceptance criteria. Existing features are extended rather than assumed absent. Preserve the current tactical combat while rebuilding the adventure around it.

Book evidence is incomplete: a source-supported name does not establish exact stats, cooldowns, rank tables or a complete floor simulation. Label each rule as primary-supported, secondary-supported, adapted or unresolved. Unknown details must not become invented canon.

## Read the specification

| Section | Subsections |
| --- | --- |
| [1. Missing book systems](01-Missing-Book-Systems.md) | Races; Hole; physical shapeshifting; companions; Cookbook; construction; deadlines; audience; potion overuse; social systems |
| [2. Existing systems to improve](02-System-Improvements.md) | Exploration; environmental interactions; Carl; Donut; reserve characters; ranks; classes; equipment; loot; levels; enemies; bosses; house; achievements/narration; animation |
| [3. Floor-specific systems](03-Floor-Systems.md) | Floors 1–8 individually; reserved Floors 9–18 |
| [4. Implementation order](04-Implementation-Order.md) | Adventure loop; progression; environmental solutions; characters; floor adventures; release gates |

Within each section, a named function corresponds to an individual checklist feature. Supporting validation and commit functions appear where a feature needs a safe lifecycle. Authoring/auditing functions are development tools, not commands exposed to a player.

## Shared command contract

This is a **proposed integration contract**, not a claim that these exact types/APIs exist. The current GameSession and RulesEngine remain the integration points. Existing battle-only preview cloning is not sufficient for effects that also change floor topology, clocks, companions, loot or other session-owned state.

~~~text
SessionSnapshot:
    revision and content/schema versions
    party, companions, inventory, equipment and progression
    campaign, current floor, canonical geometry and topology overlays
    objects, footprints, occupants, active encounter and tactical turn state
    objectives, discoveries, social facts, facilities and reward receipts
    simulation clocks, timed effects, deterministic RNG states and counters

Command:
    stable command ID
    actor ID, action/interaction ID and selected targets/options
    expected state revision
    no client-supplied damage, prices, rank gains or reward quantities

SessionTransition:
    proposed next snapshot
    authoritative domain events
    visible forecast and validation errors
    information-visibility policy for hidden outcomes
~~~

All mutation pseudocode in the section documents runs inside this contract. Read-only descriptions and authoring checks do not need to create a transaction.

~~~text
Preview(command):
    require command.expectedRevision == liveState.revision
    candidate = deepCopy(liveState including RNG streams and counters)
    result = ResolveCommand(candidate, command)
    require result satisfies state invariants
    return allowedForecast(result), confirmationBoundTo(command, liveState.revision)
    // Discard candidate. Do not change live state, RNG, clocks or receipts.

Confirm(command, confirmation):
    reject unknown/mismatched confirmation or stale state revision
    reject an already committed command ID
    candidate = deepCopy(liveState including the same RNG states used for preview)
    result = ResolveCommand(candidate, command)
    validate complete result, including topology, occupants and resources
    atomically replace live state with result and increment revision
    record command receipt and emit committed domain events
    save through the persistence boundary; show a save failure honestly if it occurs

Cancel(confirmation):
    discard temporary preview and selection
    preserve all live state, timers, RNG and resource balances

ResolveCommand(candidate, command):
    validate actor, availability, prerequisites, target legality and full cost
    dispatch to a typed supported operation, never code keyed to display names
    resolve effects and secondary reactions in stable bounded order
    apply costs, training, clock advancement and receipts exactly once
    resolve defeat/objective/transition rules in explicit documented priority
    return candidate plus events, or reject without exposing a partial mutation
~~~

Random behavior is permitted only where the authored rule needs it. Preview may simulate draws from a **cloned** stream to match confirmation, but must never advance live RNG. Hidden loot or enemy information remains hidden by the forecast policy. Repeated previews cannot reroll live outcomes. Confirmation only remains valid for the same command and state revision.

A command that changes no state may return a read-only view. Invalid commands, canceled previews and presentation-only actions do not earn practice, consume supplies, move actors, advance clocks or grant achievements.

## Data-driven rule shape

Use existing JSON schemas/records where possible. Add small typed definitions for new concepts. These illustrative records show the separation; they are not a ready-to-import schema.

~~~text
AbilityDefinition:
    id
    acquisitionRuleId
    requiredActorTags / targetTagPredicate
    costProfileId
    supportedEffects[]             // Typed primitives, not arbitrary scripts
    rankProfileId
    presentationId
    evidenceStatus and sourceRefs[]

TraversalDefinition:
    id
    endpointPredicate
    allowedFootprint / direction
    durationPolicyId
    occupiedExpiryPolicy
    costProfileId

MaterialDefinition:
    id
    tags[]
    mass / blocking / supportProperties
    reactionRuleIds[]

FloorRecipe:
    id and generatorVersion
    layoutFamilyIds[]
    requiredLocations / objectives
    encounterBudget and templates
    visualKitIds and edgeCompatibilityRules
    deadlinePolicyId
    availability and evidenceStatus
~~~

- Stable IDs identify content and saved instances; tags express capabilities and conditions.
- A tag such as “exit” cannot establish a physical route by itself.
- Validate actual endpoints, direction, locks, occupancy, footprint and collision.
- Rotate square-tile side tags with the tile; match the touching opposing sides.
- Reserve connected gameplay paths before fitting artwork.
- Keep optional art failures separate from gameplay validity.
- New combinations of supported effects should require data only.
- A genuinely new primitive needs typed C# code, schema validation, forecast support, save handling and a meaningful behavior test.
- Do not introduce a general scripting language to avoid writing small explicit operations.

## Persistence and compatibility

~~~text
LoadCandidateSave(serialized):
    deserialize into a bounded versioned save DTO
    migrate only explicitly supported older versions on a detached candidate
    validate IDs, quantities, ownership, progression and reward receipts
    validate geometry, temporary topology, footprints, occupants and encounter state
    validate clock domains, expiry state and RNG records
    atomically replace the running session only after all checks pass

EnterPreviouslyGeneratedFloor(floorId):
    restore its realized saved plan and dynamic changes
    do not regenerate from an updated recipe and overwrite a live adventure

GenerateNewFloor(floorId):
    derive a versioned seed from run seed, floor ID and generation policy
    generate with bounded retries and stable ordering
    validate required objective reachability and encounter clearance
    persist the realized plan once before entering it
~~~

Do not silently discard existing saves because a new feature is introduced. Define migrations, preserve a legacy mode, or clearly explain incompatibility. Generated-floor and authored-journey state currently have separate constraints; combining them needs an explicit new campaign state contract.

Persistence is not the same as a simulation transaction. An external storage write can fail after a legal action commits: retain the coherent in-memory result, expose the unsaved status and allow retry/export. Do not repeat the gameplay command to retry saving.

## Cross-system rules that must remain explicit

1. **HP and Mana changes**
   - Raising a cap does not heal or refill a resource.
   - A safe gear/form default is newCurrent = min(oldCurrent, newMaximum).
   - Preserve zero HP; a transformation cannot revive a defeated actor.
2. **Temporary passage expiration**
   - Resolve topology and affected occupants together.
   - Use an authored, deterministic safe-evacuation or deferred-close policy.
   - A deferred passage rejects new entries and closes when safe.
   - Never overlap actors, delete them or silently place them beyond an impassable route.
3. **Clock ownership**
   - Use simulation steps/actions/round boundaries, not render frames or wall-clock time.
   - Define conversion between exploration and tactical time domains.
   - Menu reading, preview and canceled commands generate no ticks under the proposed pause policy.
   - State the ordering when expiration, death, objective completion and descent coincide.
4. **Progression ownership**
   - Keep crawler level, trained skill rank, effective cast rank and temporary bonuses distinct.
   - Define companion progression independently rather than merely tagging an ordinary crawler as a pet.
   - Character identity can reference content; it must not replace rule validation.
5. **Presentation independence**
   - Authoritative state is correct even if animations are skipped.
   - Effects render above sprites where needed for readability.
   - Modals block incompatible input; toasts do not steal focus.
   - Use labels/shapes as well as color for state and action feedback.

## Integration with the actual codebase

| Current integration point | Proposed responsibility |
| --- | --- |
| UnityPackage/Runtime/Core/GameSession.cs and partials | Command lifecycle, session-owned progression, floor transitions and coordinated state changes |
| UnityPackage/Runtime/Core/RulesEngine.cs | Supported effects and bounded deterministic reactions; reuse for forecasts and commits |
| UnityPackage/Runtime/Core/GameData.cs and validators | Typed definitions, view/save records and validation for newly introduced state |
| GameSession.GeneratedFloor.cs | Existing standalone floor loop; extend deliberately for campaign ownership |
| GameSession.Progression.cs / Development.cs | Existing stats, equipment, practice and crafting; extend without duplicating calculations |
| Web/wwwroot/exploration-floor.js | Current deterministic layout authoring/generation; shared core remains the import/collision authority |
| Web/wwwroot/field-ui.js / camp-hub.js / battlefield.js | Controls, modals, presentation and event animation; no mechanical formulas |
| UnityProject | Generated canonical C# mirror; native presenter and Unity validation are separate delivery work |

Possible new files should be small partials or typed services around traversal, physical forms, companion progression and campaign ownership, introduced only when the feature is built. This document does not require a new universal manager or a wholesale rules-engine rewrite.

## Definition of done for an individual feature

~~~text
FeatureIsDone(feature):
    authored data and evidence/adaptation status are explicit
    eligibility, costs, invalid cases and cancellation are implemented
    preview and committed result agree at the same revision
    save/reload and migrations preserve the feature's state
    feedback explains effects and blocked reasons on phone and desktop
    meaningful rule and interaction checks pass
    actual gameplay has been reviewed
    completion checklist distinguishes browser validation from Unity validation
~~~

No Unity Editor or gameplay test was run for this documentation-only task. The specification's acceptance conditions are future work, not recorded passes.
