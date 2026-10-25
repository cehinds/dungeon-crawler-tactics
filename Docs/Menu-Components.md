# Menu component atlas

Open the [interactive atlas](../Web/wwwroot/menu-atlas.html) through the local HTTP server or the published site. It contains **six illustrated sheets and 30 independent HTML previews**. Every preview has a state selector and reset control; enabled example buttons cycle local preview states. None dispatches game commands or changes a save.

Filter by menu, component type or search text. Choose an illustration to enlarge it, or use its **Download PNG** link. The page header downloads the [JSON component inventory](../Web/wwwroot/menu-atlas.json), including component IDs, anchors, state names, source files and integration-field references. The generated sheets are concepts; their exact layouts, prices and numbers are not implementation or canon guarantees.

## Every component, directly

| Menu sheet | Individual previews |
|---|---|
| [Mission board](../Web/wwwroot/menu-atlas.html#menu-mission-board) | [Mission tile](../Web/wwwroot/menu-atlas.html#component-mission-tile), [briefing](../Web/wwwroot/menu-atlas.html#component-mission-briefing), [quest row](../Web/wwwroot/menu-atlas.html#component-quest-row), [party order](../Web/wwwroot/menu-atlas.html#component-party-turn), [entry confirmation](../Web/wwwroot/menu-atlas.html#component-entry-confirm) |
| [Skill tree](../Web/wwwroot/menu-atlas.html#menu-skill-tree) | [Four-state node](../Web/wwwroot/menu-atlas.html#component-skill-node), [prerequisite connector](../Web/wwwroot/menu-atlas.html#component-prerequisite-connector), [point badge](../Web/wwwroot/menu-atlas.html#component-points-badge), [node details](../Web/wwwroot/menu-atlas.html#component-node-details), [unlock confirmation](../Web/wwwroot/menu-atlas.html#component-unlock-confirm) |
| [Character / equipment](../Web/wwwroot/menu-atlas.html#menu-character-equipment) | [Equipment slot](../Web/wwwroot/menu-atlas.html#component-equipment-slot), [item statistics](../Web/wwwroot/menu-atlas.html#component-item-stats), [HP/Mana bars](../Web/wwwroot/menu-atlas.html#component-resource-bars), [stat comparison](../Web/wwwroot/menu-atlas.html#component-stat-comparison), [party selection](../Web/wwwroot/menu-atlas.html#component-party-selection) |
| [Combat / targeting](../Web/wwwroot/menu-atlas.html#menu-combat-targeting) | [Action card](../Web/wwwroot/menu-atlas.html#component-action-card), [target forecast](../Web/wwwroot/menu-atlas.html#component-target-forecast), [range legend](../Web/wwwroot/menu-atlas.html#component-range-legend), [enemy intent](../Web/wwwroot/menu-atlas.html#component-enemy-intent), [end turn](../Web/wwwroot/menu-atlas.html#component-end-turn) |
| [Safe-room services](../Web/wwwroot/menu-atlas.html#menu-safe-room-services) | [Recipe ingredients](../Web/wwwroot/menu-atlas.html#component-recipe-ingredients), [craft confirmation](../Web/wwwroot/menu-atlas.html#component-craft-confirm), [loot box](../Web/wwwroot/menu-atlas.html#component-loot-box), [rest](../Web/wwwroot/menu-atlas.html#component-rest-service), [service navigation](../Web/wwwroot/menu-atlas.html#component-service-row) |
| [Bestiary / inspection](../Web/wwwroot/menu-atlas.html#menu-bestiary) | [Enemy card](../Web/wwwroot/menu-atlas.html#component-enemy-card), [condition tags](../Web/wwwroot/menu-atlas.html#component-enemy-tags), [intent details](../Web/wwwroot/menu-atlas.html#component-intent-details), [status legend](../Web/wwwroot/menu-atlas.html#component-status-legend), [inspection panel](../Web/wwwroot/menu-atlas.html#component-inspection-panel) |

The skill-node reference includes locked, available, learned and maxed appearances. A four-state design example does not imply that every current authored skill supports multiple purchasable ranks.

## Files and data boundaries

| File | Responsibility |
|---|---|
| [menu-atlas.html](../Web/wwwroot/menu-atlas.html) | Accessible page shell, filters, downloads and illustration dialog |
| [menu-atlas.css](../Web/wwwroot/menu-atlas.css) | Navy/brass/cyan component styling and responsive layout |
| [menu-atlas.js](../Web/wwwroot/menu-atlas.js) | Native HTML examples, local state changes, filtering and sheet enlargement |
| [menu-atlas.json](../Web/wwwroot/menu-atlas.json) | Menu/image inventory and per-component integration references |
| [game.js](../Web/wwwroot/game.js) | Live browser game integration; the atlas does not replace it |
| [character-ui.js](../Web/wwwroot/character-ui.js) | Live character and equipment presentation |
| [skill-tree-ui.js](../Web/wwwroot/skill-tree-ui.js) | Live authored tree presentation and unlock forecast |
| [mission-ui.js](../Web/wwwroot/mission-ui.js), [scenario-ui.js](../Web/wwwroot/scenario-ui.js) | Mission/scenario selection, briefing and interaction presentation |
| [GameData.cs](../UnityPackage/Runtime/Core/GameData.cs), [ScenarioData.cs](../UnityPackage/Runtime/Core/ScenarioData.cs) | Core command/view DTOs and authoritative scenario intent |
| [DevelopmentData.cs](../UnityPackage/Runtime/Core/DevelopmentData.cs) | Stat allocation, practice, recipes and reward definitions |

The inventory's `integrationSource` and `dataFields` identify where a live implementation belongs. They do not cause the atlas to load a save, calculate a forecast or enforce eligibility. In the live game, C# validates commands and owns rules; presenters render returned views. Copying an atlas preview's illustrative before/after numbers into a production damage formula would break this boundary.

## Updating a component

Add or update its manifest record with a unique ID, menu, kind, states, anchor and source references. Implement its local preview in `demo()` in the atlas script, using shared palette and controls. Keep the preview's accessible name and state label; explain any illustrative value. Check menu/kind/search filters, keyboard operation, dialog dismissal, all states and narrow-screen overflow. Keep generated sheet art separate from functional controls.

The [updated housing illustration](https://github.com/cehinds/AI-Art/blob/dungeon-crawler/dungeon-crawler-tactics/Web/wwwroot/assets/menu-concepts/safe-room-services.png) now shows an individually owned home with shared facilities; the services sheet is a menu study, not a complete model of housing ownership, gold, training permissions or club access. Use [housing research](Research-Housing.md) for those constraints and [art direction](Art-Direction.md) for palette, anchor and readability requirements.
