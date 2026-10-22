> Historical planning/starter reference. For the implemented playable game, current content and setup, see [PlayableGame.md](PlayableGame.md). The original starter fixture is retained for regression tests.

# Tag rules contract

Tags are lowercase namespaced IDs, such as `element.fire`, `status.wet`, and `surface.oil`. The accepted shape is dot-separated lowercase segments with optional digits/underscores after each segment's first letter. IDs are case-sensitive ordinal strings. Register every tag in the root `tags` array before referencing it. Engine tags do not use Unity's GameObject Tag setting.

A tag is an identity and boolean membership only. `status.frozen` does not contain stacks, duration, source, strength, or an expiry rule. A future status record should hold `statusId`, `tagId`, source, remaining turns, and stacking policy separately, with clearly defined turn boundaries. This kernel never expires a tag or applies periodic damage. `surface.burning` is currently a persistent surface marker, not automatic damage over time. `status.frozen` currently enables the Shatter reaction; it does not automatically skip a turn. `status.shocked` is a marker with no additional action penalty.

## A reaction record

```json
{
  "id": "reaction.wet_conducts",
  "priority": 90,
  "incoming": {"all": ["element.lightning"], "any": [], "none": []},
  "target": {"all": ["status.wet"], "any": [], "none": []},
  "consumeTags": ["status.wet"],
  "effects": [
    {"op": "Damage", "amount": 5, "tag": ""},
    {"op": "AddTag", "amount": 0, "tag": "status.shocked"}
  ],
  "emitTags": []
}
```

`incoming` tests the transient tags of this event. These tags do not become target tags unless an explicit `AddTag` effect does so. `target` tests the target entity's persistent tags. For both queries:

- `all`: every listed tag must be present; empty passes.
- `any`: at least one listed tag must be present; empty adds no restriction.
- `none`: every listed tag must be absent; empty passes.

All three clauses must pass. An entirely empty query matches everything, so use an explicit incoming trigger for ordinary rules. Repeating a tag in an array has no additional effect; tags are sets at runtime.

## Exact event ordering

1. Validate actor, target, class grant, range, and energy. Clone state and pay cost.
2. Enqueue the ability's incoming tags and effects. Each event in this action refers to the same target.
3. Dequeue FIFO. If processed events exceed the configured budget (default 64), throw and discard the working clone.
4. If any incoming tag appears in the target's immunity set, skip this whole event, including its effects and reaction matching. The valid cast's energy was still paid.
5. Find eligible reactions using incoming tags and target tags **before** applying event effects. Sort by descending priority, then ascending ordinal reaction ID. Catalog sorting establishes this order once.
6. Apply the event's effects in listed order. Damage and heal affect units; tile HP is ignored. Add/remove mutate the target's tag set.
7. For each previously eligible reaction, check its target query again. An earlier rule consuming a prerequisite or this event removing it can suppress the rule. New tags do not make previously ineligible rules eligible retroactively. Mark the rule used for this action, remove `consumeTags` immediately, and enqueue its effects plus `emitTags` as a child event.
8. Continue until the queue is empty. Return state and the ordered event log.

A rule fires at most once per action chain. The deduplication set resets on the next ability use; it is sufficient per rule here because this kernel has one target per action. Future area effects must key deduplication by rule and target. The event budget is a second guard against broad content growth. Budget failure rolls back both effects and resource cost because the original state was never modified.

Consumed tags are removed when a reaction is scheduled. If a child event is immune, those consumed tags stay consumed; its effects are skipped. Rules can chain by emitting tags. With `emitTags: []`, reaction effects still execute in a child event, and unconstrained incoming queries can match that event. Avoid generic match-every-event rules unless this is intentional.

## Seed interactions

| Incoming event | Required target tag | Result |
|---|---|---|
| Fire | Oil surface | Consume oil; add burning surface |
| Lightning | Wet status | Consume wet; +5 damage and shocked marker |
| Cold | Wet status | Consume wet; add frozen marker |
| Shatter impact | Frozen status | Consume frozen; +10 damage |
| Water | Burning surface | Remove burning |

The fixture provides Oil Flask and Ignite Surface as tile abilities. Douse marks an enemy wet, then Spark/Frostbite can react; frozen enemies can be shattered by a Brawler. Water-extinguish is a supported generic rule, but no current water-on-tile ability is granted in the seed, so it requires a new tile ability or future targeting expansion to use against a burning tile. Surfaces never spread to neighbors. Wet does not grant fire resistance unless a future explicit reaction says so.

Tags describe reactive facts. Class grants, damage values, team relation, resource budgets, targeting, and later turn permissions remain explicit systems. Avoid encoding every numerical stat or UI state as a tag.
