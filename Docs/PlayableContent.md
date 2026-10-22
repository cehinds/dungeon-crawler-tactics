# Playable content catalog

Generated from the current combat-content.json and game-content.json. The JSON is authoritative; numeric values are editable. All listed ability effects execute through the shared C# resolver. Some effects also trigger the registered reactions.

## Classes

| ID | Class | HP / Energy / Move | Granted actions |
|---|---|---|---|
| `class.brawler` | Brawler | 42 / 12 / 4 | Strike, Shatter, Heavy Blow, Second Wind |
| `class.guardian` | Guardian | 42 / 12 / 3 | Strike, Shield Bash, Bulwark Recovery |
| `class.rogue` | Rogue | 34 / 12 / 4 | Strike, Knife Throw, Backstab |
| `class.ranger` | Ranger | 34 / 12 / 4 | Strike, Aimed Shot, Piercing Shot |
| `class.pyromancer` | Pyromancer | 34 / 12 / 4 | Strike, Firebolt, Ignite Surface, Flame Lance |
| `class.cryomancer` | Cryomancer | 34 / 12 / 4 | Strike, Frostbite, Deep Freeze, Ice Lance |
| `class.stormcaller` | Stormcaller | 34 / 12 / 4 | Strike, Spark, Douse, Thunderclap |
| `class.cleric` | Cleric | 34 / 12 / 4 | Strike, Mend, Greater Mend, Cleanse |
| `class.alchemist` | Alchemist | 34 / 12 / 4 | Strike, Oil Flask, Douse, Ignite Surface |
| `class.bard` | Bard | 34 / 12 / 4 | Strike, Rallying Song, Dissonant Note |
| `class.necromancer` | Necromancer | 34 / 12 / 4 | Strike, Grave Bolt, Siphon Ward |
| `class.beastmaster` | Beastmaster | 34 / 12 / 4 | Strike, Beast Rend, Second Wind |

## Abilities

| ID | Label | Target / Range / Energy | Effects | Trigger tags |
|---|---|---|---|---|
| `ability.strike` | Strike | enemy / 1 / 0 | Damage 9 | damage.physical |
| `ability.firebolt` | Firebolt | enemy / 4 / 2 | Damage 10 | element.fire |
| `ability.spark` | Spark | enemy / 4 / 2 | Damage 8 | element.lightning |
| `ability.oil_flask` | Oil Flask | tile / 3 / 1 | AddTag surface.oil | — |
| `ability.frostbite` | Frostbite | enemy / 3 / 2 | Damage 4 | element.cold |
| `ability.mend` | Mend | ally / 3 / 2 | Heal 8 | — |
| `ability.douse` | Douse | enemy / 3 / 1 | AddTag status.wet | element.water |
| `ability.shatter` | Shatter | enemy / 1 / 1 | Damage 5 | impact.shatter, damage.physical |
| `ability.fire_surface` | Ignite Surface | tile / 4 / 2 | Reaction trigger only | element.fire |
| `ability.heavy_blow` | Heavy Blow | enemy / 1 / 3 | Damage 15 | damage.physical, impact.shatter |
| `ability.second_wind` | Second Wind | self / 0 / 2 | Heal 10 | — |
| `ability.shield_bash` | Shield Bash | enemy / 1 / 1 | Damage 10; AddTag status.shocked | damage.physical |
| `ability.bulwark` | Bulwark Recovery | self / 0 / 3 | Heal 12 | — |
| `ability.knife_throw` | Knife Throw | enemy / 3 / 1 | Damage 8 | damage.physical |
| `ability.backstab` | Backstab | enemy / 1 / 2 | Damage 13 | damage.physical, impact.shatter |
| `ability.aimed_shot` | Aimed Shot | enemy / 5 / 1 | Damage 9 | damage.physical |
| `ability.piercing_shot` | Piercing Shot | enemy / 4 / 3 | Damage 13 | damage.physical, impact.shatter |
| `ability.flame_lance` | Flame Lance | enemy / 3 / 4 | Damage 16 | element.fire |
| `ability.ice_lance` | Ice Lance | enemy / 4 / 3 | Damage 10 | element.cold, impact.shatter |
| `ability.deep_freeze` | Deep Freeze | enemy / 3 / 3 | Damage 3; AddTag status.frozen | element.cold |
| `ability.thunderclap` | Thunderclap | enemy / 3 / 4 | Damage 13 | element.lightning |
| `ability.greater_mend` | Greater Mend | ally / 4 / 4 | Heal 16 | — |
| `ability.cleanse` | Cleanse | ally / 4 / 1 | RemoveTag status.frozen; RemoveTag status.shocked; RemoveTag status.wet | — |
| `ability.rally` | Rallying Song | ally / 4 / 2 | Heal 10 | — |
| `ability.dirge` | Dissonant Note | enemy / 4 / 2 | Damage 8; AddTag status.shocked | — |
| `ability.grave_bolt` | Grave Bolt | enemy / 4 / 2 | Damage 11 | — |
| `ability.siphon_ward` | Siphon Ward | self / 0 / 2 | Heal 11 | — |
| `ability.beast_rend` | Beast Rend | enemy / 2 / 2 | Damage 12 | damage.physical |
| `ability.tonic` | Health Tonic | ally / 3 / 0 | Heal 14 | — |
| `ability.elixir` | Mega Tonic | ally / 3 / 0 | Heal 26 | — |
| `ability.water_bomb` | Coolant Bomb | enemy / 4 / 0 | AddTag status.wet | element.water |
| `ability.oil_bomb` | Oil Flask | tile / 4 / 0 | AddTag surface.oil | — |
| `ability.frost_vial` | Frost Vial | enemy / 4 / 0 | Damage 5; AddTag status.frozen | element.cold |
| `ability.fire_bomb` | Fire Bomb | enemy / 4 / 0 | Damage 12 | element.fire |
| `ability.thunder_flask` | Thunder Flask | enemy / 4 / 0 | Damage 8 | element.lightning |
| `ability.cleansing_tonic` | Cleansing Tonic | ally / 4 / 0 | Heal 6; RemoveTag status.frozen; RemoveTag status.shocked; RemoveTag status.wet | — |

## Consumables

| ID | Label | Ability | Initial supply |
|---|---|---|---|
| `item.health_tonic` | Health Tonic | `ability.tonic` | 3 |
| `item.mega_tonic` | Mega Tonic | `ability.elixir` | 1 |
| `item.water_bomb` | Coolant Bomb | `ability.water_bomb` | 1 |
| `item.oil_flask` | Oil Flask | `ability.oil_bomb` | 1 |
| `item.frost_vial` | Frost Vial | `ability.frost_vial` | 1 |
| `item.fire_bomb` | Fire Bomb | `ability.fire_bomb` | 1 |
| `item.thunder_flask` | Thunder Flask | `ability.thunder_flask` | 1 |
| `item.cleansing_tonic` | Cleansing Tonic | `ability.cleansing_tonic` | 1 |

## Encounters

| Encounter | Enemies | Reward XP |
|---|---|---|
| Service Corridor 13 | Maintenance Goblin, Coolant Goblin, Security Sentry | 30 |
| The Sponsor Foundry | Foundry Foreman, Fuel Technician, Catwalk Stalker, Live Coil | 45 |
| The Audience Retention Engine | Audience Retention Engine, Fire Handler, Coil Handler | 75 |

## Art source

All included character textures are original procedural pixel artwork generated by `Tools/make_pixel_art.py`. The script draws on a 32×32 pixel grid and exports 128×128 PNGs using nearest-neighbor scaling. Pillow is needed only to regenerate art. No external sprite pack is required.
