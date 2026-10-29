# 2. Existing systems to deepen — high-level pseudocode

Design only. These functions describe proposed behavior, not new implemented APIs. Use the [shared command contract](README.md#shared-command-contract) for every state change: validate, simulate on a snapshot, preview, then atomically commit against the same revision. Each function that says “return changes” participates in that transaction; it does not write independently.

Tags select behavior. IDs identify records. JSON defines supported rules; typed C# code implements new primitives. UI and animations consume results and never determine damage, legal movement or rewards.

## 2.1 Exploration

Current: standalone continuous floor, square tiles, fog, discoveries, hybrid encounters and safe-room resume.

Data: FloorRecipe, LayoutFamily, ObjectiveGraph, EncounterGroup, Landmark, CampaignFloorState.
Saved: currentFloorId, canonical floor plans, reveal sets, claimed IDs, encounter outcomes, world flags.

~~~text
DescendWithParty(exitId):
    require current objectives complete and party eligible to descend
    load next floor definition; reject reserved or unavailable floors
    create next floor once using its saved generation seed and recipe version
    atomically preserve party/inventory, archive current floor, activate next floor

ChooseLayoutFamily(floorDefinition, generationSeed):
    filter families by floor theme, map bounds and required mechanics
    select with deterministic generation RNG and stable candidate ordering
    construct connected rooms, loops and optional branches
    reject unreachable mandatory points; retry within an explicit attempt budget

PlaceLandmarksAndBranches(plan):
    reserve entrance, exit, safe areas, quest locations and encounter pads
    place distinct landmarks at authored navigation decisions
    give optional branches rewards or information; validate their return paths
    fit square art using rotated edge tags without changing authoritative collision

ReturnToExistingFloor(floorId):
    load stored geometry and dynamic state; do not regenerate from current rules
    restore claimed discoveries, opened routes, encounters and safe return position
    apply only authored cross-floor consequences with unprocessed event IDs
    reveal the resumed location and display the current objective
~~~

Dependencies: campaign persistence, generator validation, objective records.
Acceptance: descend, return where allowed, reload, and find the same geometry and receipts; a failed generation leaves the current run intact.

## 2.2 Environmental interaction

Current: specific tag reactions, entry-triggered traps and bounded authored interactions.

Data: InteractableDef, MaterialDef, MechanismDef, NavigationChange.
Saved: object health/state, connections, moved positions, mechanism flags.

~~~text
DiscoverInteractable(actor, object):
    read visible object tags and actor capabilities
    return available actions plus blocked reasons and estimated consequences
    keep undiscovered solutions hidden unless the clue policy exposes them

DamageObstacle(action, obstacle):
    resolve material defenses through the normal effect resolver
    if destruction threshold is reached, propose debris and navigation changes
    validate occupied cells, support dependencies and required-route policy
    return damage, geometry changes and destruction presentation events together

MoveWorldObject(actor, object, destination):
    require push/pull capability, clear swept footprint and valid support
    evaluate traps, hazards and connected mechanisms along the movement path
    return position, navigation and interaction changes as one transaction

ActivateLinkedMechanism(triggerId):
    traverse authored connections in stable order with a bounded event budget
    evaluate each mechanism's prerequisites and current state
    propose gate, bridge or surface changes with occupant-safe transitions
    suppress repeated activation of the same event/node pair

FindAlternativeSolutions(obstacle):
    match authored solutions against skills, items and environmental tags
    show visible eligible solutions and their costs
    preserve an authored fallback for mandatory routes
    validate every accepted solution through the same navigation contract
~~~

Dependencies: typed navigation mutations, material rules, bounded reaction queue.
Acceptance: canceling demolition changes nothing; moving a crate cannot overlap actors or create an accidental mandatory-route softlock.

## 2.3 Carl's abilities

Current: Powerful Strike, ignition, direct-hit Dynamite and entry-triggered traps.

Data: AbilityDef, AreaShape, ExplosionProfile, TrapDef, UnarmedModifier.
Saved: existing ability ranks plus placed traps, destructible states and placement receipts.

~~~text
PreviewExplosion(cast):
    calculate affected cells from authored shape, blockers and falloff policy
    resolve all affected actors and objects, including allowed friendly fire
    return exact resource costs, damage, tag reactions and navigation consequences

ResolveDemolition(cast, structure):
    require the ability's material predicates match the structure
    resolve blast and support changes using the shared environmental rules
    queue bounded secondary events; do not invent unsupported structural physics

SetUpTrapCombination(actor, placement):
    require owned ingredients or authored ability cost and a legal placement
    attach trigger, effect, owner and lifecycle records to the placed instance
    show armed state and likely interaction without guaranteeing future AI choices

ResolveUnarmedAttack(actor, ability):
    derive eligible weapon/unarmed tags from effective equipment state
    combine applicable skill, stat and equipment modifiers once
    use the same effective ability for targeting, forecast and commit
~~~

Dependencies: areas, destructibles and equipment modifiers.
Acceptance: preview accounts for every affected target; detonating or stepping on a trap consumes it exactly once.

## 2.4 Donut's abilities

Current: personal spells, controllable pet copies and a curated floor specialty adaptation.

Data: AcquisitionRule, SpecialtyOffer, RetentionPolicy, FieldUseRule, SourceEvidence.
Saved: acquired ability IDs, floor choice receipts, retained skills, specialty progress.

~~~text
GrantAbilityAtStoryMilestone(event):
    find unclaimed acquisition rules matching committed story facts
    grant eligible abilities and record the receipt atomically
    use explicit migration policy for saves that already own an early-granted skill

OfferFloorSpecialty(floorTransition):
    evaluate source-backed or explicitly adapted specialty prerequisites
    show eligible choices and blocked reasons
    confirm once for this floor and replace only the temporary specialty grants

RetainLearnedSpecialtySkills(floorTransition):
    classify learned skills using the authored retention policy
    preserve qualifying permanent learning; remove expired temporary grants
    reconcile ranks, prerequisites and equipped actions without deleting unrelated skills

UseSpellInExploration(actor, spell, target):
    require an authored field-use definition and valid environmental target
    preview traversal, resource, duration and mechanism consequences
    commit through the same ability resolver used in combat
~~~

Dependencies: acquisition events, permanent/temporary grant separation, environmental actions.
Acceptance: changing floors never duplicates grants; importing an older save preserves valid ownership according to a declared migration.

## 2.5 Reserve party identities

Current: Elle, Imani, Louis and Britney have generic Strike innates; class kits provide additional actions.

Data: CharacterKitDef, AcquisitionRule, FieldUseRule, SourceEvidence.
Saved: existing personal skill unlocks and new interaction receipts.

~~~text
AuthorEllePersonalKit():
    attach researched ability definitions and explicit adaptations to her content record
    configure prerequisites, role, effects and animation references
    validate every grant and mark unverified lore effects as unresolved

AuthorImaniPersonalKit():
    attach independently researched personal abilities to her content record
    describe tactical role and field uses without copying another kit by default
    validate costs, targets, progression and source status

AuthorLouisAndBritneyPersonalKits():
    author separate kits and acquisition timelines for each character record
    distinguish personal identity from freely selectable class abilities
    validate each character's complete playable opening and progression loadout

OfferCharacterFieldInteractions(actor, object):
    match actor capability tags and learned abilities to interaction requirements
    show available action, cost and benefit with a fallback where required
    record story outcomes through stable event IDs, not display-name comparisons
~~~

Dependencies: research and ability authoring; no special character-name branches in C#.
Acceptance: each reserve character has a distinct usable kit; changing optional classes does not erase personal identity.

## 2.6 Skill ranks

Current: use-based practice, authored rank profiles, selected cast modes and restricted upper ranks.

Data: RankProfile, RankPermission, ModifierSource, MilestoneGrant, SourceEvidence.
Saved: trained rank/experience, claimed milestones and persistent permission sources.

~~~text
ApplyAbilitySpecificMilestone(skill, newRank):
    evaluate the skill's authored milestone records crossed by this increase
    grant each persistent milestone once
    derive temporary/effective bonuses separately from permanent learning

CalculateEffectiveSkillRank(actor, skill):
    trained = actor.practice[skill].rank
    modifiers = eligible equipment, status and grant modifiers
    return trained, modifiers and effective cast rank under the authored policy

DetermineTrainingCap(actor, skill):
    collect active race, class and other permission rules matching skill tags
    resolve explicit priority/stacking policy; never infer permission from a name
    return training cap separately from effective-cast limits

DescribeRankEvidence(skill, rank):
    show effect, evidence category and source reference where available
    label extrapolated formulas and unknown canonical breakpoints
    never present every generated rank row as a quotation from the books

ValidateRankTwentyEligibility(actor, skill):
    require an explicit permission for training beyond the ordinary cap
    preserve banked practice according to policy when temporarily ineligible
    explain the missing permission without granting universal rank 20
~~~

Dependencies: modifiers, permissions and migration policies.
Acceptance: gear bonuses do not overwrite trained rank; removing gear restores the correct effective value without losing practice.

## 2.7 Classes and skill trees

Current: a large selectable catalog and authored trees.

Data: ClassDef, PrerequisiteSet, TreeNode, BuildRole.
Saved: selected classes, unlocked nodes, spent points and respec receipts if supported.

~~~text
AuditRepeatedBranches(classCatalog):
    compare grant/effect paths and identify functionally identical branches
    flag repetition for design review; do not automatically rewrite content
    replace selected duplicates with authored choices that have distinct tradeoffs

ExplainClassPrerequisites(actor, classDef):
    evaluate each requirement against current and permanent progression facts
    return satisfied, missing and mutually exclusive requirements
    preview exactly what selecting the class adds, removes or locks

CompareBuildChoices(actor, candidateNodes):
    simulate each eligible node using the shared stat/ability calculation
    show role, resource and tactical differences using representative scenarios
    reject grants that reference unsupported or unreachable abilities

AuditSelectableClass(classDef):
    validate a usable starting action and reachable milestone path
    check point budgets, prerequisite cycles and duplicate grants
    run representative scenarios and flag weak or dominant choices for review
~~~

Dependencies: rank permissions and class evidence.
Acceptance: a class can be deployed, act, progress and save/reload without dead-end prerequisites.

## 2.8 Equipment

Current: six gear definitions and equipment management outside combat.

Data: ItemDef, EquipmentSlot, AffixDef, AcquisitionRule, AppearanceLayer.
Saved: item instance IDs, modifiers, ownership, equipped slots and acquisition receipts.

~~~text
ExpandEquipmentCatalog(tierPlan):
    author items for supported slots and progression stages
    assign stable IDs, capability tags, effect references and source status
    validate all grants and avoid unsupported effect descriptions

ApplyDistinctEquipmentEffects(actor, item):
    collect matching stat, skill and behavior modifiers
    resolve stacking rules once through the effective-build calculation
    clamp current HP/Mana to changed caps; never heal merely by swapping gear

DistributeEquipmentAcrossCampaign():
    associate rewards, shops and discoveries with authored progression bands
    validate that prerequisites can be met before an item becomes obsolete
    check that important build options have reachable acquisition routes

PreviewEquipmentSwap(actor, item):
    simulate removing the current slot item and applying the candidate
    show stat, rank, ability and capacity differences plus ownership conflicts
    require confirmation for the same state revision before transferring ownership

RenderEquipmentAppearance(actor):
    map equipped appearance IDs to compatible body/form animation layers
    resolve layer order, anchors, direction and frame alignment
    use a clear fallback for missing art without changing gameplay effects
~~~

Dependencies: item instances and modifier ownership; presentation layers are separate.
Acceptance: equip/unequip cannot duplicate items, stack removed bonuses or restore resources for free.

## 2.9 Loot and reward boxes

Current: fixed-content boxes and bounded reward choices.

Data: LootTable, RewardChoice, BoxDef, EligibilityRule, RewardContext.
Saved: box instances, reward receipts, selected choices and reward RNG state/outcomes.

~~~text
ResolveBoxContents(boxInstance):
    require ownership and unopened state
    use fixed contents or a configured table with stable deterministic ordering
    store the committed result and opening receipt atomically
    prevent reloads from rerolling an already resolved box

OfferMeaningfulRewardChoices(context):
    build eligible choices from authored progression and reward rules
    show known contents, tradeoffs and any intentionally hidden outcomes
    reserve no reward until the choice is confirmed

SelectContextualRewards(event):
    match committed achievement/encounter facts to reward rules
    apply repeat limits and eligibility checks
    grant owned reward instances once per receipt key

ExplainBoxAccess(actor, box):
    show owner, opening requirements, known rewards and missing conditions
    reject invalid or already opened boxes without mutation
    handle inventory overflow through an explicit claim policy; never discard silently
~~~

Dependencies: receipt ledger, stable item instances and deterministic rewards.
Acceptance: replaying an event or reopening a save cannot grant the same reward twice.

## 2.10 Level progression

Current: story rewards reach level 50 by Floor 6.

Data: ProgressionCurve, EncounterBudget, UnlockSchedule, DifficultyProfile.
Saved: earned XP, claimed rewards and allocated/unspent progression resources.

~~~text
RebalanceStoryCurve():
    define intended level bands and encounter counts for the scoped floors
    simulate cumulative XP against those bands
    adjust authored rewards/thresholds and publish a save migration policy

SpaceMajorUnlocks():
    schedule encounters that introduce, practice and combine new capabilities
    avoid stacking unrelated tutorials and unlocks in the same reward beat
    check that later challenges do not require an optional unowned skill

TeachNewAbility(unlockEvent):
    show a short explanation and a safe optional practice opportunity
    demonstrate cost, targeting and interaction with existing systems
    save tutorial acknowledgement separately from skill ownership

ValidateCombinedProgression():
    simulate representative party builds with expected equipment and ranks
    inspect survival, resource pressure and encounter duration
    supplement simulations with recorded playtests before declaring balance accepted
~~~

Dependencies: campaign encounter plan, loot tiers and skill milestones.
Acceptance: migration preserves earned progress deliberately; new pacing is verified floor by floor rather than inferred from a level cap.

## 2.11 Enemy behavior

Current: enemies move and declare actions; tactical selection is limited.

Data: EnemyBehaviorProfile, Intent, PerceptionRule, CounterplayRule.
Saved: committed plans where necessary, alert state and persistent encounter outcomes.

~~~text
ChooseEnemyAction(enemy, perceivedState):
    enumerate legal actions with the same validation used for players
    score outcomes using its authored role and available information
    select deterministically; use saved RNG only for explicitly tied choices

CoordinateEnemyGroup(group):
    share only information allowed by communication/perception rules
    allocate roles and planned positions without illegal occupancy
    revalidate each action when its actual turn starts

ReactToThreatChange(enemy):
    evaluate retreat, pursuit, defense and support conditions
    choose a legal reachable objective and communicate observable intent
    avoid endless pursuit across boundaries forbidden by the encounter rules

ApplyResearchedCounterplay(enemy, incomingEvent):
    match material, condition and behavior tags against verified/adapted rules
    expose discoverable clues about the resulting vulnerability or response
    use the normal resolver for all damage, resistance and status changes

ValidateWeaknessEvidence(enemyDef):
    require an evidence category for every claimed canonical weakness
    flag appearance-based assumptions for research
    label invented balance weaknesses as adaptations
~~~

Dependencies: action evaluation, perception and navigation.
Acceptance: AI cannot use unavailable knowledge or illegal moves; declared plans may change only with visible explanation when invalidated.

## 2.12 Boss battles

Current: three standalone adapted scenarios; bosses occupy one logical tile.

Data: Footprint, BossPhase, TransitionRule, ArenaMechanism, EncounterPlacement.
Saved: footprint/position, phase, transition receipts and arena mechanism states.

~~~text
MoveLargeBoss(boss, path):
    validate the full footprint and swept cells at every step
    reserve occupied cells and reject unsupported overlaps
    calculate hazard contact using an explicit per-body/per-cell policy

EvaluateBossPhase(committedEvent):
    find eligible transitions in deterministic priority order
    apply each allowed transition once and reset only specified behavior
    emit a warning before delayed phase attacks according to the phase definition

UseArenaMechanism(actor, mechanism):
    validate interaction reach, required tools and current mechanism state
    preview interruption, cover or route effects against the boss scenario
    commit changes through shared environmental rules

EnterCampaignBoss(node):
    load the authored encounter using the current campaign party and resources
    preserve the surrounding floor and return checkpoint
    award story progress and rewards once on the configured outcome
~~~

Dependencies: large-body collision, environmental interactions and campaign persistence.
Acceptance: a large boss cannot pass through a one-cell doorway; saving at a phase boundary cannot repeat its transition reward.

## 2.13 House and facilities

Current: bedrooms, upgrades, paid training, crafting, social display and credentials.

Data: RoomDef, FacilityDef, UpgradeDef, ConversationDef, ServiceInteraction.
Saved: purchased rooms/upgrades, service-use limits, conversations and visit receipts.

~~~text
UseRoomActivity(actor, room, activity):
    require access and installed facilities
    preview authored cost, benefit and time policy
    commit service effects and usage receipts together

UpgradeTrainingOrCraftingFacility(facility, upgrade):
    check gold, prerequisites, ownership and available upgrade path
    preview unlocked services and limits
    debit gold and install the upgrade atomically

StartPartyConversation(actor, location):
    select eligible dialogue from story facts, relationships and unplayed events
    present choices without advancing state until a choice is committed
    record outcomes and any once-only rewards

UnlockFacilityFromDiscovery(discoveryEvent):
    evaluate upgrade/recipe/service unlock rules
    record the unlock without automatically purchasing the facility
    notify the player where the newly available service can be obtained

UseSocialDisplayOrClubAccess():
    show actual audience, sponsor and challenge history from saved state
    evaluate credentials and entry conditions for the selected destination
    open supported interactions; clearly label unavailable interiors
~~~

Dependencies: social state, economy and facility services.
Acceptance: double-clicking a purchase cannot spend twice; facility benefits cannot be obtained before ownership.

## 2.14 Achievements and narration

Current: saved achievements, original narration and revisit-able history.

Data: AchievementRule, RewardDef, NarrationTemplate, PresentationPriority.
Saved: achievement receipts, relevant bounded counters and narration history.

~~~text
RecognizeUnusualSolution(committedEvents):
    evaluate bounded achievement predicates over actual outcomes
    ignore previews, cancellations and duplicate event IDs
    queue eligible achievement awards once

AwardAchievement(achievementId):
    require eligibility and no previous receipt for its repeat scope
    grant configured rewards and record completion atomically
    emit NEW ACHIEVEMENT with reward details

DescribeEncounterContext(event):
    select an original template matching actor, action, place and outcome tags
    fill it from authoritative event data
    prioritize meaningful changes and avoid unsupported lore claims

PresentNarration(queue):
    combine repeated low-priority messages and cap visible toast count
    show compact notices without stealing movement or targeting focus
    retain history; pause input only for an explicitly interactive modal
~~~

Dependencies: domain events, receipts and presentation queue.
Acceptance: a replayed animation never grants an achievement; a toast does not interrupt a held walking direction.

## 2.15 Animation and feedback

Current: four-direction walking and existing combat effects; coverage is incomplete.

Data: AnimationSet, DirectionSet, FrameAnchor, EquipmentLayer, EffectPresentation.
Saved: authoritative facing/form/equipment as needed; do not save transient animation frames as mechanics.

~~~text
PlayDistinctAbilityAnimation(event):
    resolve the ability presentation ID and actor-compatible animation
    align impact cues with the committed event timeline
    skip or accelerate presentation without skipping gameplay outcomes

PlayFormAttackOrHit(actor, event):
    select the active form's compatible animation and measured anchor
    fall back explicitly if that action strip is missing
    maintain logical footprint and position independently of the artwork

ResolveEnemyFacing(enemy, movementOrTarget, cameraRotation):
    derive world-facing direction from authoritative movement or target vector
    convert it into the current camera view exactly once
    choose matching authored frames and validate all four orientations

CompositeEquipmentSprites(actor, frame):
    align compatible equipment layers to the body's frame anchors
    order front/back layers according to direction and attachment metadata
    suppress incompatible overlays using a documented fallback

RenderImpactAndEnvironmentEvents(events):
    draw floor/base geometry, actors and foreground occlusion in scene order
    draw readable combat impacts, projectiles and floating text above sprites
    use color plus labels/shapes for statuses; support reduced motion
    display committed state correctly even when animation is interrupted
~~~

Dependencies: normalized sprite metadata and authoritative event streams.
Acceptance: rotate the camera and verify every actor/action direction; skipping effects leaves identical gameplay state.

## References

- [Current playable architecture](../PlayableGame.md)
- [Exploration rebuild and limits](../Exploration-Rebuild.md)
- [Signature moves and adaptation boundaries](../Signature-Moves-Audit.md)
- [Rank evidence and unknowns](../Ability-Rank-Audit.md)
- [Progression implementation](../Progression.md)
