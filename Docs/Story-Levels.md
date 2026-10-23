# Playable story levels

The story journey contains seven authored battles across floors 1–8 and an explicit destroyed-floor bypass on floor 7. Six repeated approaches now have larger, distinct **17 × 13** exploration maps with connected side routes, supply detours, tactical reconnaissance and a staging point before the encounter. Floor 3 retains its existing Lantern Row neighborhood and saved-layout migration.

| Floor | Expanded approach | Playable choices |
|---|---|---|
| 1 | Tutorial supply galleries | Cross the central passages or search side galleries for coolant and a reserve Health Tonic. Inspect the water/extinguishing lesson. |
| 2 | Sewer maintenance circuit | Follow the maintenance loop or take cross-passages. Find a Shock Tonic and inspect advice about dry combat lanes and wet/lightning reactions. |
| 3 | Existing Over City neighborhood | Existing workshop, trap and rescue interactions remain in place. |
| 4 | Rail transfer concourse | Traverse parallel transfer galleries, inspect the existing route control, and recover an Oil Flask before the encounter. |
| 5 | Four-quarter survey ring | Inspect all four existing quadrant markers, explore the connecting survey ring and collect a Frost Vial. The markers remain required. |
| 6 | Hunting blind perimeter | Search around offset blind walls for coolant and a healing reserve; inspect the fire and enemy-intention advice. |
| 7 | Destroyed Great Race | Existing safe-room bypass; no invented battle or reward. |
| 8 | Ghost collection archive | Search archive aisles for a Cleansing Tonic and reserve Health Tonic; review weakening, capture range and confirmation before the six-ghost encounter. |

Each expanded map has the existing entry Health Tonic, an additional elemental or cleansing supply, and an additional Health Tonic reserve. Cache interactions actually add one consumable to the shared inventory and become claimed; the accompanying reconnaissance and staging points record advice in the log. These are optional discoveries, not additional enemy encounters, healing stations, working rail controls or rest mechanics. Entering the marked door starts the existing floor battle. Victory returns to the implemented safe-room camp, where the player can manage supplies, builds and progression.

All map geometry, supply placement and tactical advice are game adaptations. Floor premises and known limitations remain documented in [the floor research](Research-Floors-Enemies.md) and [the journey guide](Journey-and-Home.md). Floor 5 still has one compact tactical battle rather than four castle campaigns. Floor 8 still implements capture rather than the novel's complete deck combat. Floors 9–18 remain locked.

## Authoring and verification

`python3 Tools/expand_story_levels.py` deterministically authors the six exploration maps. It replaces only the journey JSON value, preserves all unrelated content, keeps existing discovery IDs and coordinates except the encounter door, and leaves the battle definitions unchanged. Every previously walkable exploration cell remains walkable, allowing prior party positions and discovered passages to remain valid. The encounter door moves to the expanded map's far staging area; an earlier checkpoint must walk there before entering.

`python3 Tools/expand_story_levels.py --check` verifies the authored result is current and flood-fills **every walkable tile** of every implemented exploration and combat map. It checks every discovery, spawn and enemy position can be reached. The expanded approaches have 143–148 connected walkable tiles each, compared with 55 walkable tiles in the repeated original approaches. The existing floor-3 map has 105 connected walkable tiles.

Also run `python3 Tools/validate_game_data.py` and the shared-C# `Tests/JourneyTests` harness. The latter exercises actual exploration commands, required objectives, all seven battles, capture, journey saves and the destroyed-floor bypass. The map authoring checker covers all optional branches, including branches a normal campaign run may skip.
