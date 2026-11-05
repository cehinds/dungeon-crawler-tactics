# DungeonCrawlerTactics working agreement

This is a Floor One RPG with a pure C# rules engine and a .NET 8 WebAssembly browser host. Do not change the neighboring AshenSpire repository.

- Read `README.md`, `Rebuild/CONTRACT.md`, and `Rebuild/LORE.md` before changing gameplay. The previous implementation is archived by tag `archive/pre-rpg-reset-20261105`.
- The user requested a coordinator using GPT-6.1 Sol and Luna specialists. Assign Sol code/integration work and Luna content/docs/fixture work. Name exclusive file ownership; do not let multiple agents edit the same files concurrently.
- `Rebuild/Core` is the single authority for game rules. Browser JavaScript handles rendering, input and presentation; never duplicate damage or progression formulas there. Do not claim a Unity export or Unity Editor validation.
- Treat `Web/wwwroot/data/floor-one-rpg.json` and `world-rooms.json` as authored sources of truth. Preserve stable string IDs, explicit contracts and validated references. Do not key mechanics to display names.
- Keep resolution and map generation deterministic. Preview and commit use the same resolver; use meaningful route, forecast, save and connectivity tests when rules change.
- Run `dotnet run --project Rebuild/Tests -c Release` and publish the Web project after relevant changes. For browser changes, run `Tools/playtest_floor_one.py` against the published host as described in README.
- Preserve all physical `Web/wwwroot/assets` files, untracked user files and scratch directories. Art is stored separately in AI-Art; hosting restores only the checksum verified subset in `Tools/hosted-assets.json`. Never clone the full art repository just to publish the game.
- Preserve `Rebuild/ReferenceData` lore, equipment and skill references. Distinguish canonical source claims from tactical adaptations and implemented behavior from targets.
- Do not include SDK binaries, node_modules, build outputs or the retained full art library in commits or delivery archives. Keep `main` unchanged unless explicitly authorized; development releases use `dev` and `pages-dev-*` tags.
