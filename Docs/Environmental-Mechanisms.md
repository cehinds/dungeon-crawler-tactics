# Generated expedition mechanisms

The generated campaign rules now author one permanent-passage mechanism for each of its three depth themes. These are original game adaptations; they do not represent verified book locations, scenes, or mechanisms. Each offers exactly three routes: a free remote manual lever on a longer detour, an ability route that pays the ability's ordinary Mana cost, or an item route that spends one named supply. All three routes open the same passage permanently. They grant no XP or bonus loot and cause no trap damage or timed effects. They do not bypass existing encounter groups or campaign objectives.

| Depth | Mechanism | Ability route | Item route | Existing material tag |
| --- | --- | --- | --- | --- |
| Abandoned Works | Oil-Bound Works Grille | Any current actor's Fire ability | 1 Fire Bomb | `surface.oil` |
| Dry Cistern | Cistern Counterweight Floodgate | Any current actor's Cold ability | 1 Frost Vial | `surface.water` |
| Relay Vault | Conductive Relay Shutter | Any current actor's Lightning ability | 1 Shock Tonic | `status.wet` |

The corresponding ability tags are `element.fire`, `element.cold`, and `element.lightning`. Item solutions name the exact item and consume one. Manual solutions cost no Mana or items and use a longer route around to a remote lever. The required material tags are checked against each mechanism's authored material tags. This design uses existing combat tag vocabulary and does not introduce new status effects or combat rules.

The shared core implements preview, confirmation, resource costs, permanent openings, and save validation. Its 54 focused mechanism checks and existing regression suites pass. The full browser mechanism suite also passes against the compiled shared-C# WebAssembly runtime. This package does not add traps, temporary holes, structural damage, timed effects, or generalized puzzle scripting. Browser validation covered real combat and descent, alongside the existing continuous-floor and generated-campaign regressions.


## Play and author

Start a new **Connected expedition** to use the authored mechanisms. Previously saved plans retain their existing layout and do not gain newly authored mechanisms. Approach a marked shortcut or lever and use **E / Space** or its interaction button. Choose a living deployed crawler and review a matching skill, an available item, or the free manual route. The review shows exact Mana and inventory values before and after the action. Confirm opens the passage; cancel spends nothing. Other commands and reload invalidate pending confirmation.

Recipes live in `Web/wwwroot/data/generated-campaign-rules.json`. Add a recipe using stable IDs, registered material/capability tags and the supported `manual`, `ability`, and `item` solution kinds. A skill solution matches any currently granted ability with the specified incoming tag; it uses the shared normal Mana-cost calculation. It does not cast combat damage, train ranks, or award XP. The generator selects closed cells that shorten an existing connected route and a reachable remote manual action. It reserves interaction cells before fitting artwork and rejects an unplaceable recipe.

`GeneratedFloorPlan.mechanisms` stores the realized definitions. `GeneratedDungeonState.mechanismReceipts` stores the chosen mechanism, solution, actor and optional ability ID. Original map tiles remain immutable; traversal and battle geometry derive the opened cells from validated receipts. Archives carry the same receipts. Definitions or saves without the new optional collections remain supported. The preview is transient and is not serialized.

## Delivery checklist

- [x] Three authored, tag-matched mechanisms with free manual alternatives.
- [x] Shared preview/confirm resolution with actual skill and item costs.
- [x] Persistent collision changes across combat, retry, reload, and archived depths.
- [x] 54 focused rule checks, existing core regressions, compatibility build, and 300 deterministic campaign-floor checks passed.
- [x] Full browser gameplay checks: production native art before/after opening in all four camera rotations; exact skill/item/free costs; eligibility; cancel/stale/reload; real gate traversal into combat; active-battle reload; completion and archive receipts.
- [x] Modal controls remain visible without horizontal overflow at 320×740, 390×844, 844×390 and 1440×1000. Quiet-preview screenshots were recaptured after removing redundant success warnings.
- [x] Canonical shared source mirrored into UnityProject; browser build published locally and tested.
- [ ] Unity Editor validation (source mirror is maintained separately).
- [ ] Temporary portals, expiry/evacuation rules, physical demolition, persistent overworld traps, and material construction remain future packages.
