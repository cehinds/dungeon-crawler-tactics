# 4. Implementation order — high-level delivery pseudocode

These are work packages, not gameplay functions and not promises that the entire backlog is implemented. Each package has dependencies and a concrete exit condition. The first dependency is the [shared command contract](README.md#shared-command-contract), including saved topology, session state, RNG and revision-bound previews.

## 4.1 Complete the adventure loop

~~~text
ConnectExploreCombatRewardsAndDescent():
    define a campaign-owned floor state and stable encounter identities
    replace standalone reset behavior only through an explicit campaign command
    preserve existing tactical turn and forecast behavior
    implement return-from-battle and descent as atomic session transitions

PreservePartyAndWorldAcrossFloors():
    version the campaign save schema and define supported migrations
    persist party, inventory, generated geometry, receipts and world consequences
    validate candidate saves completely before replacing a running session

ExpandLayoutsAndObjectives():
    author additional graph families and bounded objective recipes
    reserve routes and placements before visual tile fitting
    validate connectivity, edge compatibility, encounter clearance and return paths

AcceptAdventureLoop():
    play fresh run -> discover -> fight -> reward -> home -> resume -> descend
    reload at supported boundaries and compare authoritative state
    reject the package if any transition loses progress or duplicates rewards
~~~

Exit condition: a continuous multi-floor run with reliable saves. Prerequisite work includes explicit traversal/occupancy and clock policies, even if advanced effects are deferred.

## 4.2 Improve rewards and progression

~~~text
ExpandGearAndLoot():
    introduce stable item instances and reviewed modifier rules where needed
    author acquisition bands, distinct choices and receipt-safe loot tables
    expose ownership and accurate equipment comparisons

RebalanceExperienceAndUnlockPacing():
    model the intended campaign encounter count before changing XP tables
    distribute levels, personal skills, class nodes and gear over that route
    preserve existing saves through a declared migration

MakeUpgradeBenefitsLegible():
    calculate before/after stats and abilities through the shared resolver
    show a short practical description and relevant future requirements
    test that previews match committed results

AcceptProgressionPackage():
    play representative builds across each supported floor
    verify reward uniqueness, no free healing through gear swaps and rank permissions
    record remaining balance concerns rather than claiming completion from unit tests
~~~

Exit condition: rewards change useful choices throughout the run without overwhelming the player with simultaneous unlocks.

## 4.3 Add environmental problem-solving

~~~text
ImplementHoleAndDemolitionPrimitives():
    define temporary traversal and destructible navigation state
    add validation, preview, atomic commit, save migration and presentation events
    specify occupied-expiry and collapse policies before writing effects

ExpandTrapsAndMaterialCrafting():
    author material predicates and supported typed construction operations
    calculate ingredient use and placement in one transaction
    ensure hazards, traps and crafted structures participate in ordinary resolver events

BuildReusableMultiSolutionMechanisms():
    author bounded mechanism connections and eligible interaction rules
    support skills, items and physical routes where the design calls for alternatives
    validate mandatory-route fallbacks and prevent repeated event loops

AcceptEnvironmentPackage():
    test cancel, stale confirmation, occupied passage expiry and failed placement
    test area forecasts, friendly effects and bounded reaction chains
    reload altered maps and verify topology, occupants and rewards remain coherent
~~~

Exit condition: at least one complete adventure supports several different valid solutions using shared rules rather than one-off scripted shortcuts.

## 4.4 Deepen character identities

~~~text
ImplementPhysicalFormsAndMomentum():
    introduce footprint, mass and attachment validation
    preserve current resources when caps change; keep defeated actors defeated
    author source-backed constraints and clearly marked tactical tradeoffs

SeparateCompanionProgression():
    add an explicit companion policy and owned progression state
    migrate the existing pet unit without discarding unrelated campaign progress
    author researched stages, commands and pet gear independently of crawler classes

AuthorDistinctReserveKits():
    establish sourced or labeled adapted personal abilities for each reserve
    define acquisition timing, field uses and tactical roles
    test that switching optional classes preserves personal grants

CompleteCharacterPresentation():
    fill directional walking, attacks, hits, forms and equipment attachment gaps
    validate shared anchors and camera-facing conversions
    keep presentation interruption independent from gameplay resolution

AcceptCharacterPackage():
    play a representative encounter and field interaction with every supported kit
    test transformation rejection, companion growth and equipment changes across reload
    review actual gameplay captures rather than concept art alone
~~~

Exit condition: each character's identity changes how the player explores or fights and is visually understandable.

## 4.5 Build book-specific adventures

~~~text
AuthorFloorDefiningSystems():
    choose a supported floor and verify its required book mechanics
    implement reusable primitives before bespoke encounter content
    label simplified mechanics and leave unsupported later floors reserved

IntegrateBossDiscoveriesAndConsequences():
    place clues, alternate solutions and boss encounters within the floor graph
    connect outcomes to rewards, NPC/world facts and descent requirements
    preserve clear objectives and reliable fallback/return behavior

ExpandAudienceSponsorsAndRelationships():
    derive bounded progression from committed gameplay and story events
    add reviewable offers, conversations and service consequences
    keep all rewards receipt-safe and avoid claiming a simulated online audience

AcceptFloorAdventure():
    complete a fresh playthrough including optional paths, supported failures and reloads
    review readability, resource pressure, boss counterplay and narrative continuity
    mark only the tested floor/systems complete; record unresolved research and content
~~~

Exit condition: each released floor has its defining experience, not only the appropriate art or a renamed generic battle.

## Cross-package release gate

~~~text
ReleaseFeaturePackage(package):
    validate JSON schemas, stable references and supported migrations
    run meaningful shared-core tests for changed rules and invalid commands
    run browser interaction checks for changed flows at phone and desktop sizes
    sync canonical C# into UnityProject; report Unity Editor checks separately
    publish a checkbox list separating implemented, validated and still proposed work
~~~

Preserve the user's existing tactical combat. Do not substitute a new combat model while rebuilding exploration or the special floor-specific systems.
