> Historical planning/starter reference. For the implemented playable game, current content and setup, see [PlayableGame.md](PlayableGame.md). The original starter fixture is retained for regression tests.

# Change content without changing the engine

The file to edit today is `UnityPackage/Runtime/Data/starter-content.json`. It is ordinary JSON and loads as a Unity TextAsset. `Tools/content.schema.json` describes its exact format. The wider catalog in `ContentCatalog.md` is a proposal, not a second runtime database.

Use one source of truth. A future Unity inspector can edit/import this JSON, but must not maintain a competing set of manually synchronized ScriptableObjects. Use ScriptableObjects for Unity asset bindings (portrait, prefab, sound) keyed by the same stable IDs; bake those bindings separately from mechanical content.

## What can change as data today?

| Change | Data only? | Where |
|---|---|---|
| Damage/healing, range, energy cost, visible label | Yes | Ability record |
| New class with existing abilities | Yes | Classes array |
| New ability using Damage/Heal/AddTag/RemoveTag | Yes | Abilities array and class grants |
| Fire reacts with a new tag on the selected target | Yes | Tags and reactions arrays |
| Item points to an ability | Yes, definition only | Items array; item-use gameplay is pending |
| Tile spreads fire to neighbors or affects occupants | Requires spatial rules | Resolver/event targeting extension plus data |
| Push, summon, revive, restore energy, armor mitigation | Requires an effect primitive | Core + validator + tests + schema |
| Timed poison, stacked buffs or two sources of one tag | Requires status lifecycle | Status instances and turn boundary hooks |
| Artwork and animation | Unity assets | Presentation bindings; no rules changes |

## Example 1: a new class in two minutes

Append this entry to `classes`. All referenced abilities already exist:

```json
{
  "id": "class.tempest_knight",
  "label": "Tempest Knight",
  "abilityIds": ["ability.strike", "ability.douse", "ability.spark"]
}
```

Set a demo unit's `ClassId` to `class.tempest_knight`. It can mark a target wet with Douse, then trigger bonus lightning damage with Spark on a later command. This creates a working class grant without a subclass, switch on class ID, prefab script, or new effect opcode. Turn restrictions are supplied by the planned turn controller; the current kernel only checks class ownership, target, range and energy.

## Example 2: a new spell

Append this entry to `abilities`, then add `ability.flash_freeze` to the new class's `abilityIds`:

```json
{
  "id": "ability.flash_freeze",
  "label": "Flash Freeze",
  "target": "enemy",
  "range": 4,
  "cost": 3,
  "incomingTags": ["element.cold"],
  "effects": [{"op": "Damage", "amount": 6, "tag": ""}]
}
```

Because the existing `reaction.wet_freezes` queries `element.cold` and `status.wet`, this spell automatically participates in the wet → frozen → shatter combo. `status.frozen` currently enables the shatter bonus only. A future turn-skip effect needs a status system; the name alone does not implement that behavior.

## Example 3: oil on a creature

This is a deliberate new combination. It does not infer creature oil from the tile beneath it.

1. Register `{"id":"status.oiled","label":"Oiled"}` in `tags`.
2. Add an `ability.oil_coat` targeting `enemy`, range 3, cost 1, empty incoming tags, with `{"op":"AddTag","amount":0,"tag":"status.oiled"}` as its effect.
3. Grant the ability to `class.alchemist`.
4. Append this reaction:

```json
{
  "id": "reaction.oiled_ignites",
  "priority": 100,
  "incoming": {"all": ["element.fire"], "any": [], "none": []},
  "target": {"all": ["status.oiled"], "any": [], "none": []},
  "consumeTags": ["status.oiled"],
  "effects": [{"op": "Damage", "amount": 6, "tag": ""}],
  "emitTags": []
}
```

Firebolt now deals its usual 8 damage plus 6 from this reaction against a living oiled target with no fire immunity. Oil is consumed. It does not splash, spread, or create a surface. Compare expected HP 30 → 16 in a scenario test and verify preview and commit agree.

## Validate every edit

```sh
python3 Tools/validate_content.py
dotnet run --project Tests/RulesKernel.Tests.csproj
```

If the Python dependency is absent, install `Tools/requirements.txt` in a virtual environment. The strict authoring validator checks types, unknown fields, required keys, integer bounds, duplicated IDs/properties, references and contradictory queries. The C# Catalog checks loaded values/references too, but `JsonUtility` itself can silently ignore unknown JSON keys. Run the strict check before importing or building. Do not put schema metadata or comments inside the content JSON; the schema intentionally rejects unknown fields.

The Python validator does not prove game balance or that every reaction can be reached through a granted ability. The bounded runtime handles reaction loops; a content-specific scenario test proves a useful chain. A build hook that automatically runs validation is a planned editor task; today the command is manual.

## Tag design rules

- Tags are exact, case-sensitive, registered IDs. A dot is a namespace convention, not inheritance. `element.fire` does not implicitly match `element`, and wildcard `damage.*` is not supported in v1.
- Incoming tags live on a transient event. Persistent tags live on an entity. A fire event does not leave fire on a target unless an effect adds it.
- Keep unit statuses (`status.wet`) and tile surfaces (`surface.oil`) separate. Future entry/exit and occupancy hooks explicitly translate spatial contact into effects.
- A class grants abilities; tags describe facts that effects can query. Display labels can change without breaking save references.
- Numerical amounts, source, lifetime, stacks, faction and target geometry belong in typed fields. Do not encode `damage.12` or `duration.3` as tags.
- Do not remove a tag owned by several buffs until its last contribution expires. The current boolean tag set has no source tracking; implement status instances before overlapping timed sources.
- Explain a reaction with trigger, matched prerequisite, consumed tags, applied operations and affected entities. The future debug inspector should expose this provenance from structured events, not reconstruct it from animation.

## Extending the effect vocabulary

For a new primitive such as Push, first write a concrete scenario: destination bounds, obstacle collision, occupied tile, hazard entry, immunity, trigger order, and failure behavior. Add one typed operation with a deterministic handler, schema validation, forecast support and tests. Keep event target/source IDs and state version explicit when adding multiple targets. Use `(chainId, reactionId, targetId)` for area-rule deduplication, a bounded breadth-first queue, stable entity-coordinate ordering, and atomic rollback on a budget failure.

The existing single-target engine deduplicates by reaction ID per action. Do not merely remove that guard to enable area effects. Extend the scope explicitly and test cycles between neighboring cells. For spatial reactions, author radius, hop limit, affected factions, friendly fire and tag consumption; they must be visible in the forecast.

When changing a schema, bump its version and add a migration. Preserve old IDs or provide a migration map. A saved class/ability reference must never silently bind to another record because an array was reordered. Hot-reload content at camp or restart an encounter; do not change definitions halfway through a forecast.
