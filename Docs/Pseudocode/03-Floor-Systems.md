# 3. Floor-specific systems — high-level pseudocode

Design only. The current story route contains seven authored battles, a Floor-7 bypass and bounded discoveries; the new continuous generated floor remains standalone. A floor label or art kit is not evidence that the following systems are implemented.

Each floor definition should reference stable layout, objective, encounter, progression, narrative and rule-set IDs. Do not switch mechanics on floor names in code. Floor-specific behavior comes from typed rule definitions and authored content. All mutating functions below use the [shared command contract](README.md#shared-command-contract).

Research anchors: [floor and enemy evidence](../Research-Floors-Enemies.md), [actual story inventory](../Story-Levels.md), [completion checklist](../Completion-Checklist.md). Exact clocks, routes, enemy behaviors and card rules must be researched or explicitly labeled as adaptations before authoring.

## 3.1 Floor 1 — Introduction

Data: TutorialSequence, AdventureGraph, NamedEncounterPlacement, Discovery.
Saved: tutorial receipts, discovery IDs, encounter results, objective state.

~~~text
BuildIntroductoryAdventure(recipe):
    construct arrival, preparation, exploration and encounter locations
    connect required locations and optional discovery branches
    reserve a safe learning area before unavoidable threats
    validate every required location and a legal route to the exit

TeachCoreLoop(event):
    advance eligible tutorial steps from committed player outcomes
    introduce movement, actions, reactions, rewards and preparation in manageable stages
    provide short optional explanations and repeatable practice where safe
    save completion flags; never replay a grant when reopening help

PlaceNamedEncountersAndClues(plan):
    select source-supported encounters appropriate to this floor and scope
    place clues that explain observable counterplay before the relevant battle
    connect victory and optional discoveries to the floor objective graph
    validate that optional clues improve understanding without making progress impossible
~~~

Acceptance: a fresh player can complete the loop without previously knowing the controls; tutorials do not mutate state during preview or block essential commands.

## 3.2 Floor 2 — Expanded dungeon systems

Data: LocationGraph, EcosystemRule, ResourcePressureProfile, Discovery.
Saved: location state, bounded spawn/growth counters, discoveries and encounter outcomes.

~~~text
ExpandSecondFloorLocations(recipe):
    place distinct locations with linked main paths and optional returns
    assign different encounter and discovery roles to each location
    use theme-specific art while preserving canonical collision and socket compatibility

UpdateResearchedEnemyEcosystem(committedEvent):
    select verified or explicitly adapted ecosystem rules matching the event
    resolve feeding, growth or spawning as separate bounded effects
    never infer that preventing one behavior automatically prevents another
    save counters and instance IDs so reload cannot repeat a spawn

IntroduceResourceDecisions(plan):
    place visible supply choices and safe alternatives under the floor budget
    preview known costs and communicate uncertainty where intended
    ensure required progress remains possible without a particular optional loot roll
    test resource pressure across plausible party builds
~~~

Acceptance: behaviors match their documented rule rather than a generic monster stereotype; resource choices have readable consequences and a viable route forward.

## 3.3 Floor 3 — Over City

Data: DistrictGraph, SettlementService, QuestGraph, SelectionMilestone, WorldConsequence.
Saved: district visits, NPC/quest facts, race/class choice receipts, persistent consequences.

~~~text
BuildConnectedOverCity(recipe):
    create districts, services, safe areas, encounter sites and transit connections
    integrate authored side adventures through explicit entrance/return contracts
    validate routes, boundaries and district identity before fitting square tiles

PopulateCityActivities(district):
    place NPCs, services, quests and discoveries from eligible definitions
    resolve dialogue and shop access from faction/story state
    expose landmarks and journal objectives without filling the screen with labels

OpenStoryRaceAndClassMilestone(event):
    require the authored milestone and actor-specific eligibility
    offer supported class choices and, once implemented, eligible race choices
    preview grants, restrictions and preserved progression before confirmation
    save each selection according to its own repeat/respec policy

ApplyPersistentCityConsequences(choice):
    resolve quest, faction and service changes through authored rules
    record the outcome once with its source event ID
    let later visits and floors read the resulting world facts
    preserve alternate required routes when a local service becomes unavailable
~~~

Acceptance: a city choice survives departure/reload and affects a later interaction; optional side modes return to the correct campaign state.

## 3.4 Floor 4 — Iron Tangle

Data: RailGraph, StationDef, TransitService, SchedulePolicy, DeadlineRule, RouteObjective.
Saved: discovered routes, station states, transit position, simulation clocks and objective facts.

~~~text
BuildRailNetwork(recipe):
    construct directed station/track connections from authored rail rules
    validate route constraints, legal transfers and reachable required destinations
    place navigation landmarks and compatible platform/track tiles
    persist the realized network instead of regenerating it on reload

PlanAndTakeTrainTrip(party, route):
    show discovered stops, transfers, costs, restrictions and known timing
    require the party can board and the route remains valid
    commit boarding/travel/arrival through the configured simulation boundaries
    trigger eligible transit events without duplicating them on save/load

AdvanceRailTime(committedEvent):
    convert accepted travel/actions into configured simulation time
    leave menu reading and previews paused under the chosen game policy
    process schedules, warnings and deadlines in explicitly ordered boundaries
    store clock state and processed event IDs

ResolveRailObjective(event):
    update relevant route/station/quest facts from actual committed outcomes
    unlock only the connections and objectives named by the definition
    update the journal and map with a clear next destination
    verify that changed tracks or stations leave a valid intended resolution
~~~

Acceptance: route information predicts actual travel; a reload during a supported transit checkpoint cannot duplicate arrivals, reset deadlines or strand the party between states.

## 3.5 Floor 5 — Linked regions and castles

Data: RegionDef, CastleObjective, SharedProgressRule, EnvironmentalTraversalRule.
Saved: per-region discoveries/objectives, shared flags and traversal changes.

~~~text
BuildElementalRegions(recipe):
    create distinct environmental regions with their own materials and routes
    connect them according to the researched or clearly adapted floor structure
    select biome-specific hazards, encounters and art from definitions
    validate arrival, escape and required objective reachability in each region

PropagateRegionalProgress(committedObjective):
    evaluate authored dependencies between region and castle objectives
    apply each linked change once under a stable receipt
    notify the player which destination or mechanism changed and why

ResolveEnvironmentalTraversal(actor, route):
    check movement capabilities against water, height, surface and hazard rules
    preview resource costs and entry consequences for the full footprint
    offer supported tools or alternate routes where appropriate
    commit movement through the same navigation resolver as ordinary exploration

ReplaceBeaconOnlyAdventure(recipe):
    expand each region objective into exploration, interaction and encounter steps
    retain recognizable landmarks and clear shared progress
    support old saves through an explicit migration or preserved legacy route
    do not silently rewrite an active floor's geometry
~~~

Acceptance: regions differ mechanically as well as visually; shared progress persists across travel, and migration cannot invalidate an active saved objective.

## 3.6 Floor 6 — Hunting Grounds

Data: HunterProfile, EquipmentLoadout, PerceptionRule, PursuitState, RescueObjective, EscapeRoute.
Saved: hunter identities/loadouts, knowledge/alert state, pursuit position and rescue outcomes.

~~~text
CreatePersistentHunters(plan):
    instantiate eligible authored hunters with stable IDs and actual equipment
    derive combat capabilities from their loadouts and behavior profiles
    preserve injuries/outcomes and inventory according to the scenario policy

UpdateStalkingAndPursuit(committedStepOrRound):
    update each hunter from permitted perception and communication information
    choose search, stalk, pursue, disengage or defend using authored priorities
    move only through valid navigation paths and reveal observable clues
    never teleport a hunter to the player merely to force an encounter

ResolveRescueOrEscapeObjective(event):
    update escort safety, extraction eligibility and pursuit facts
    show the costs and risks of available actions
    commit success/failure and rewards once under the objective rules

ApplyPreparationAndTerrainAdvantage(action):
    evaluate scouting, concealment, traps and movement capabilities against terrain
    resolve detection or combat benefits from declared rules
    reveal useful feedback without exposing hidden enemy knowledge
    allow enemies to respond using the same perception and movement limits
~~~

Acceptance: hunters cannot act on undiscovered player information; escape and rescue states remain coherent across combat transitions and reload.

## 3.7 Floor 7 — Destroyed-floor transition

Data: BypassTransition, NarrativeBeat, NextFloorRef.
Saved: acknowledged story event, transition receipt and destination checkpoint.

~~~text
PresentDestroyedFloorTransition():
    display the source-grounded reason normal traversal is unavailable
    distinguish narrative acknowledgement from a playable dungeon objective
    provide a clear continuation action without fabricating a normal battle

CommitBypassTransition():
    validate the prior floor result and supported next floor
    preserve party, items, progression and permanent story flags
    activate the destination once and record the transition receipt

ValidateBypassContent(definition):
    require an explicit bypass state and a reachable continuation
    reject normal encounter generation for the bypassed floor
    avoid granting invented battle XP or completion loot unless labeled adaptation
~~~

Acceptance: continuing and reloading cannot skip progression gates, duplicate rewards or generate a nonexistent normal Floor-7 adventure.

## 3.8 Floor 8 — T'Ghee

Data: CaptureRule, CollectionEntry, DeckRuleSet, CardDef, BattleRuleSet, ExitObjective.
Saved: captures, owned entries, legal deck, card battle state, RNG and objective receipts.

No complete canonical ruleset is assumed here. Author sourced rules first; explicitly label any simplified card battle adaptation. Keep this floor's distinct battle mode isolated from the existing general tactical combat.

~~~text
CaptureEligibleTarget(actor, target):
    evaluate authored eligibility, costs, target state and collection limits
    preview the known result or declared chance without advancing live RNG
    commit target transformation/removal and collection ownership atomically
    record the unique capture receipt

BuildAndInspectDeck(collection, chosenEntries):
    validate ownership, duplicates, composition and capacity against the rule set
    show card effects, prerequisites and unresolved selection errors
    store the legal chosen deck without consuming entries unless rules require it

ResolveCardBattleCommand(command):
    validate turn/phase, available cards, targets and costs
    simulate through the versioned card rules with a cloned battle RNG state
    preview permitted information; commit against the same state revision
    persist the complete supported battle checkpoint and event receipts

CompleteCaptureBattleExitLoop(event):
    update collection and battle objectives from committed outcomes
    grant exit access only when the authored requirements are met
    preserve the surrounding campaign and apply rewards once
~~~

Acceptance: captured entries cannot be duplicated by reload; invalid decks cannot start a battle; the floor-specific mode returns to the correct campaign state.

## 3.9 Floors 9–18 — Reserved scope

Data: FloorAvailability, SourceEvidence, ResearchStatus, SupportedRuleSet.
Saved: availability changes only when a supported content migration explicitly permits them.

~~~text
DisplayUnavailableFloors():
    show numbered floor entries with accurate playable/researched/reserved status
    disable entry where required mechanics or content are absent
    do not treat available concept art as a playable floor

ResearchFloorBeforeAuthoring(floorId):
    collect primary references and clearly graded secondary references
    record confirmed setting/mechanics separately from unknown details
    create an implementation proposal only within the supported evidence

LabelUnverifiedFloorContent(record):
    assign confirmed, secondary-supported, adapted or unresolved evidence status
    require explicit adaptation wording for invented mechanics
    leave unsupported canonical claims unpublished as facts

ValidatePlayableFloorAvailability(floorId):
    require validated map, objectives, encounter rules, transition and save support
    require recorded playthrough coverage before marking the floor complete
    otherwise retain a reserved or development label
~~~

Acceptance: no unavailable floor can be entered through UI or direct command; the floor guide accurately distinguishes scope from completion.
