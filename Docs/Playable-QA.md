# Playable build QA checklist

Use this checklist against the runnable .NET harness and the Unity/Web build. Record the build/content revision and exact reproduction steps for every failure. A feature is verified only in the runtime that was actually exercised.

## Floor completion

- [ ] Start a new run, complete encounters 1–3 including the boss, select a reward, and return to camp.
- [ ] Complete each required encounter without consuming an optional item; optional sponsor goals never block progress.
- [ ] Win, lose, retreat, and restart each lead to a clear valid next state. Defeat leaves a retry route and does not permanently remove required roster members.
- [ ] Checkpoint/save and reload at camp and between encounters; reject malformed, truncated, incompatible, or logically invalid saves without a crash or unusable run.

## Party, classes, abilities, and items

- [ ] Camp can select any four of the eight available crawlers, including rotating the roster after a loss.
- [ ] Every configured class grant matches the visible loadout. Only owned abilities can be used; changing class/loadout updates both UI and commands.
- [ ] Ability and item IDs resolve to the intended definitions. Charges, targets, range, costs, and per-activation action limits update exactly once on commit.
- [ ] Downed units cannot move, act, or be targeted where prohibited; healing/revive behavior follows the authored rules and does not silently revive if unsupported.

## Board, turns, and commands

- [ ] Movement follows orthogonal Manhattan distances and each unit's configured movement budget. Walls, blocked cells, and occupied cells cannot be entered; no diagonal corner-cutting.
- [ ] A unit moves at most once and acts at most once per activation. Acting ends its activation; moving and ending without an action is valid. Cancel before commit spends no movement, action, energy, or item charge.
- [ ] Invalid actor, target, ability ownership, target kind/team, range, energy, occupancy, or phase commands leave all state unchanged.
- [ ] Ally activation order is player-controlled; enemy order and tie-breaking are deterministic. Turns advance when all eligible units have activated, including when units are downed.
- [ ] No softlock if a side has no eligible living units, all paths are blocked, an objective actor is downed, or a saved battle contains dead units.

## Preview, reactions, and encounter finishability

- [ ] Preview and commit use the same resolver: same affected entities, damage/healing, tag changes, reaction order, resource costs, and final objective result. Preview never mutates live state.
- [ ] Exercise oil + fire, wet + lightning, wet + cold, and frozen + shatter in actual encounters. Confirm tile and unit tags stay on their intended entity and no unimplemented spreading/occupancy behavior is implied.
- [ ] Confirm reaction prerequisites, consumption, priority, and once-per-chain rules are deterministic and do not trigger retroactively or loop indefinitely.
- [ ] For every encounter, verify a legal path to its objective with the starting roster/loadout and no optional consumable. Confirm objectives cannot be completed accidentally by unrelated effects and victory/defeat resolves immediately and consistently.

## Evidence to record

For a failure, capture the build/content revision, starting save or setup, command sequence, expected result, actual result, and whether it reproduces in the .NET harness, Unity Play Mode, or hosted Web build. Mark unrun environments explicitly.
