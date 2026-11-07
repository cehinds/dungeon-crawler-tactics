# Content authoring guide

## Identity and provenance

Give every content definition a stable typed ID. Once an ID is used by a save, engine, or authored reference, do not rename it to match a display-label change. Definitions must carry tags, a short description, a source reference, and availability. A source reference names a registered source and a locator; when research has no reliable locator, record `unknown` rather than guessing a chapter or page. Mark confidence where the evidence is uncertain.

Store source references as `sourceRefs: [{sourceId, locator, confidence}]` and ensure each `sourceId` resolves through the shared `sources` registry. Adaptation-only definitions may cite the registered `adaptation-design` source with locator `authored game design` and confidence `author-created`; do not use an item or content ID as a fake source ID. Keep source references alongside concise player-facing descriptions. Put provenance and implementation status in `sourceNote`, `loreStatus`, and `adaptationStatus`.

Keep evidence and implementation separate. Source-backed names or events may still have adapted numerical effects, encounter composition, timings, access gates, and rewards. Label those values as adaptations. Secondary databases can guide research but must not be described as primary text evidence.

## Floor One roster and places

The deployable Floor One party consists of Carl and Princess Donut. Keep Carl clean-shaven and barefoot in the opening description. Donut is a cat. Mordecai is a Tutorial Guild guide and NPC. Katia and Mongo are not Floor One party members. Crawler class selection belongs to Floor 3; any Floor One entry about that facility must be future-facing and non-selectable.

The live roster is `characters[]` in `Web/wwwroot/data/content-catalog.json`. The older `party[]` rows in `floor-one-rpg.json` are retained compatibility metadata; changing them does not change the active roster or starting skill assignment. Edit the typed character records for live party membership and starting skills.

Maintain the distinction among visited regions, traversed or inferred routes, and places merely mentioned in conversation or reports. Do not turn a rumor into a visited map destination. The compact game route is an authored playable abstraction, not a canonical floor plan.

## Skills, equipment, recipes, and rank access

Keep Floor One's five early skill records limited to its supported playable set. Numerical costs, ranges, damage, and rank progression are tactical adaptations unless a source explicitly establishes them. Rank 5 is the Floor One training cap. A possible rank 20 must be permissioned per skill and must not be inferred from the existence of a global progression curve.

Keep only supported personal opening gear as lore-grounded depictions: Carl's underpants and backpack, and Donut's tiara. Do not grant them undocumented combat bonuses. Other equipment and supplies need explicit provenance and adaptation notes. A recipe may be retained for research completeness while marked inactive or research-only; its presence must not imply that the Floor One runtime supports crafting. In particular, bomb manufacture is not an available Floor One recipe unless a later implementation explicitly enables it.

Gear bonuses and temporary modifiers must be represented as separate, typed data from trained skill rank. Avoid treating an equipment bonus as learned practice or permanent rank access. Any implemented caps or permissions should be explicit on the skill definition.

## Tags and reactions

Tags describe reusable properties or states; reactions state which tags they inspect, what they consume, and what result they emit. Keep the relation declarative and data-backed. Initial authored examples include oil igniting when exposed to fire, water extinguishing fire, and explosions destroying objects explicitly marked destructible. These are intended rules and must not be described as implemented until the runtime resolver supports them.

The current authored `effectRules.reactions` schema uses `id`, `priority`, `triggerTags`, `requiredTargetTags`, `excludedTargetTags`, `removeTags`, and `operations`. Oil ignition is blocked by water or suppressant tags so water takes precedence. Bomb uses the `explosion` tag and a one-tile radius. Only asset IDs explicitly listed in `destructibleAssetIds` become persistent destructible props; the current whitelist uses the registered crate and barrel IDs in `map-object-rules.json`.

## Asset ownership

The canonical art source is the separate AI-Art repository. This game stores asset registrations and local asset metadata in `Web/wwwroot/data/asset-catalog.json`; the small hosted set is checksum-pinned in `Tools/hosted-assets.json`. A new local asset registration does not imply that the asset is hosted or approved for release. Preserve source ownership and follow the existing review/upload gate before changing hosted checksums.

## Story definitions

Bind story milestones to actual quest events. The current required sequence is the false guild ambush, Mordecai's tutorial briefing, goblin workshop, Ball of Swine, then the exit. The Hoarder and Juicer are optional after the briefing. Do not add a second source of quest-stage truth in the content registry.

Keep dialogue brief and original. Paraphrase story circumstances rather than copying novel dialogue. Give each authored NPC beat its own provenance and mark invented interaction outcomes as adaptations.

## Review checklist

Before adding or changing a definition, check that its ID is stable and typed, all references resolve, source locators are honest, availability matches the Floor One scope, numerical adaptations are labeled, and intended runtime behavior is distinguished from future or research-only data. See `BLOCK-A-CHECKLIST.md` for Block A coverage and acceptance status.
