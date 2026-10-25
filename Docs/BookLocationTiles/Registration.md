# Legacy registration workflow

This page records the previous atlas-cropping workflow for historical reference. It is not the current authoring or export specification. The active pipeline redraws component artwork for a native 128×128 orthogonal grid, preserves each style's palette, and removes isometric floor and door perspective.

The old exporter used reviewed crop masks and affine floor and wall registration against isometric or orthogonal source art. It included exceptions for two irregular Ink & Lanterns rail components and a special submarine doorway scale. Those decisions apply only to legacy crops and must not be carried into new crop records as current placement requirements.

For the native pipeline, use the square floor and wall/door geometry documented in [the coverage guide](README.md). New art should be validated through the current exporter and QA checklist in [QA.md](QA.md). The legacy authoring helpers and registration data may remain for back-compatibility, but they do not define the new redraw.
