# DungeonCrawlerTactics working agreement

This is a separate Unity tactics game with a shared-C# browser delivery. Do not change the neighboring AshenSpire repository for work on this kit.

- Read README.md and Docs/PlayableGame.md for the implemented game; Docs/DeliveryPlan.md is historical planning context.
- The user requested a coordinator using GPT-6.1 Sol and Luna specialists. Assign Sol code/integration work and Luna content/docs/fixture work. Name exclusive file ownership; do not let multiple agents edit the same files concurrently.
- Keep the rules pure C#. Rendering, input, saves and audio sit behind the Unity integration boundary.
- Treat JSON as the authored source of truth. Stable string IDs, explicit schemas and validated references are mandatory. No mechanics keyed to display names, character names or class IDs.
- New combinations of existing effects should require data only. A new effect primitive requires code, validation, forecast support and a meaningful scenario test.
- Preserve deterministic ordering. Never use wall-clock time or UnityEngine.Random in combat resolution.
- Preview and commit use the same resolver. Do not duplicate damage formulas in a presenter or wireframe.
- A readable small system is preferable to custom scripting languages, reflection plugins or a universal manager.
- Distinguish implemented behavior from design targets. Do not claim Unity or Web validation without actually running it.
- Avoid editing Unity serialized scene/prefab YAML by hand; use Editor tooling when available.
- Run the focused tests and content validator in README after relevant changes. Never include SDK binaries, node_modules, generated Unity Library folders or test build outputs in delivery archives.
