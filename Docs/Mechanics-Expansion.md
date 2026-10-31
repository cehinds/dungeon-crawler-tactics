# Thermal counterplay expansion

Implemented as an original tactical adaptation, not a claim about canonical book rules.

A fire-tagged action hitting a target that was already frozen consumes `status.frozen` and adds `status.wet`. The action keeps its ordinary damage, Mana, range, targeting and immunity rules. It grants no bonus damage or rewards. A later Lightning action can consume the resulting wetness for the existing conductivity bonus; a later Cold action can freeze it again. Physical Shatter loses its frozen prerequisite after thawing.

The rule is authored as `reaction.fire_thaws_frozen` in `UnityPackage/Runtime/Data/combat-content.json`, using only the existing `AddTag` primitive and reaction prerequisite/consumption fields. It works for allied skills, enemy fire and Fire Bombs because matching uses `element.fire`, not actor or ability names. Its priority is 95, between ignition and existing wet reactions; the resolver still snapshots eligibility before applying effects. A combined Fire/Lightning event cannot conduct wetness newly created by its own thaw, because the thaw emits no elemental tags.

No new core primitive, save field, status tag or map topology is introduced. Existing tag persistence and lifetime rules apply to the resulting wet condition. Existing saves without a frozen target behave as before; frozen targets now respond to subsequent fire with the authored counterplay. There is no spread, area chain, added tile targeting or permanent exploration change.

## Validation

`ThermalReactionChecks.cs` runs from the existing mechanism suite and covers source immutability; exact preview/commit state, log and presentation-event identity; ordinary damage and cost; condition events; subsequent conductivity/refreezing; loss of the Shatter prerequisite; immunity; non-frozen/non-fire cases; consumables; enemy symmetry; and same-event eligibility snapshots.

Run:

```sh
python3 Tools/validate_content.py UnityPackage/Runtime/Data/combat-content.json
python3 Tools/validate_game_data.py
dotnet run --project Tests/MechanismTests/MechanismTests.csproj
```

Validation passed: both Python content validators and the focused shared-C# suite (15 thermal reaction checks plus 54 existing mechanism checks) using .NET SDK 8.0.427.

Sensible later packages include an explicit cold-on-burning quench reaction, or a cold tile-targeting ability with separately specified water-freeze traversal and expiry rules. Neither is implemented here.

This package changes canonical content and focused shared-C# tests. Browser publication and Unity source mirroring are integration steps, not validation performed by this package alone.
