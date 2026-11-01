# Floor 1 top-down semantic layer kit

The reviewable reference layer kit covers all 36 root-approved top-down Floor 1 concepts. The central manifest contains 506 exact-source components and 524 reusable-mode components, plus 119 exact category layers, 35 materials, and 33 reusable library modules. Every exact-mode reconstruction reports zero changed source pixels; this confirms pixel recomposition, not semantic quality or reusable fidelity. Six independent asset tests pass across all 36 scenes, and final browser HTTP QA passes on desktop and at 390px mobile width. Fine-grained object components, background context, and lighting remain incomplete, so this is reference material rather than a production-ready asset set.

The only source art for this kit is the approved top-down set at [floor-one-concepts-top-down](../../Web/wwwroot/assets/floor-one-concepts-top-down/README.md). Use its source panels and corresponding source sheets. Do not use the earlier mixed-camera concepts as source art. The [coverage file](coverage.json) lists the exact 36 panel IDs, source paths and hashes, book-evidence IDs, and per-scene task status.

## Keep the image histories distinct

Each scene has four different visual records, and the viewer should identify them separately:

1. **Approved source image.** The original top-down concept panel, cropped from a reviewed six-panel sheet. Preserve it unchanged and keep its path and hash.
2. **Extracted semantic components.** Crops and masks isolate visible source pixels such as floors, walls, furniture, props, or other scene elements. These are extractions from the approved image; they do not create pixels hidden behind an object.
3. **Interpolated hidden-surface underlay.** Any surface filled in beneath an occluder is newly generated or interpolated. It cannot recover the actual hidden artwork from the source and must never be described as original or canon-supported detail. Retain the prompt/tool provenance and the mask region that required filling.
4. **Reference reconstruction.** A comparison image assembles the underlay and extracted components. It is a reconstruction of the source illustration for layer review, not a canonical floorplan, production map, or seamless tile set.

The original mixed-camera concept package remains separate and unchanged. The approved top-down source panels themselves are illustrative, with inferred layout and prop placement. Neither the source art nor derived layers are runtime game content.

## Proposed JSON layer schema

The central worker has imported the scene schema for all 36 concepts. Its JSON Schema is at [schema.json](../../Web/wwwroot/assets/top-down-layer-kit/schema.json), the full [manifest](../../Web/wwwroot/assets/top-down-layer-kit/manifest.json) records mode-specific paths and metrics, and the [coverage file](coverage.json) lists each source, component count, and limitation. A scene JSON contains `schemaVersion`, `sceneId`, `source`, `grid`, `underlay`, and `components`; `reusable` and `limitations` are optional. The generated output manifest records separate exact and reusable results.

- `schemaVersion` and `sceneId`, using one of the existing 36 coverage IDs.
- `source` with the approved panel path, SHA-256, width, and height.
- `grid` with `major: 14` and `sub: 3` address divisions. Grid addresses annotate positions; they do not make a layer a tile or establish canonical coordinates.
- `underlay` with its image path and provenance marked `ai-interpolated-hidden-surface`, including the generation tool and retained prompt.
- `components`, where each exact component has a stable ID and category, an RGBA crop (`asset`), a full-native-canvas binary `mask` with values 0/255, `bounds` `[x,y,w,h]`, scene coordinates, stable `z` order, an optional grid address such as `D7.b2`, and provenance.
- Optional `reusable`, a separate full-plate mode with a coherent `base` image, its provenance, reusable components, and limitations.
- Exact reconstruction images and pixel metrics are recorded in the generated output manifest, not in the input scene record. A zero-difference result applies only to exact source-pixel recomposition.

The two modes have different source histories and must not be combined into one fidelity claim. All 36 exact reconstructions report zero different pixels, but that metric only verifies source-pixel recomposition; it does not verify semantic masks, object silhouettes, reusable quality, or hidden-surface truth. In exact mode, source pixels outside the union of component masks are preserved, inpainting is confined to that union, and extracted visible source pixels are restored over the underlay. In reusable mode, a complete plate—AI-generated or source-derived and inferred—is composed with reusable components. Record the actual origin of every base and component; a reused visible-source component does not make the whole plate source-exact. Do not overlay the original full image or untracked source fragments as a hidden restoration. Fine-grained props, background context, and lighting remain incomplete. Some regions are represented as broad terrain patches; where present in scenes 25–29, these are labeled as patches rather than complete room floors. Composition quality and source similarity remain art judgments, not exact-match metrics. A perfect visible-pixel match in exact mode validates compositing only; it cannot verify hidden surfaces as recovered source art.

## Viewer and review boundary

The runnable [layer workbench](../../Web/wwwroot/top-down-layers.html) opens with the reusable interpretation and offers separate exact-source and original-reference modes. Its four comparison views are current layers, original/current side by side, sliding comparison, and pixel difference. It supports scene selection, component-category toggles, a reference grid with outer labels, D7.b2 hover and click coordinates, and downloads of the selected scene JSON or current PNG. Scene data and artifacts are under [top-down-layer-kit](../../Web/wwwroot/assets/top-down-layer-kit/); the [manifest](../../Web/wwwroot/assets/top-down-layer-kit/manifest.json) records component paths, provenance, and exact-mode metrics. HTTP QA passed for all 36 scenes, four views and the wipe slider, source/component links, JSON and native PNG downloads, no JavaScript or HTTP errors, and a 390px mobile layout without overflow. Preview screenshots: [desktop](../../Web/wwwroot/assets/top-down-layer-kit/previews/workbench.png) and [mobile](../../Web/wwwroot/assets/top-down-layer-kit/previews/workbench-mobile.png). The workbench is a review tool with no gameplay integration.

To run it locally from the repository root, start `python3 -m http.server 8000 --directory Web/wwwroot`, then open `http://localhost:8000/top-down-layers.html` in a browser. The HTTP server keeps the workbench’s relative asset paths available.

Coverage includes every source panel, exact-mode and reusable-mode component counts, provenance, exact reconstruction metric, and known limitations. The reported totals are 506 exact-source components and 524 reusable components in two separate modes. These counts are not a promise of exhaustive semantic object decomposition: background context, small props, and lighting are not fully separated, and some areas are intentionally represented with broad terrain patches. Root approved this delivery as a reviewable layer kit with exact reconstruction and inferred alternatives kept distinct. It is not production-ready.

Mark an extraction, underlay, reconstruction, reusable kit, viewer, or root review complete only after its corresponding artifact exists and has been checked. Avoid describing the broad schema, pixel-preservation invariant, viewer, or 36-scene package as finished before those checks pass. Per-scene states are in [coverage.json](coverage.json).

## Coverage and canon limits

The inventory has 36 panels in six batches of six. Its selection is evidence-backed, not an exhaustive concordance or a complete dungeon survey. Source names, visit/mention distinctions, source URLs, and visual anchors remain in the linked [top-down concept coverage](../FloorOneConceptsTopDown/coverage.json) and [Book 1–2 research](../BookLocationTiles/research-books-1-2.json).

The known relationships remain important when interpreting layer sets: the false guild alley and Murder Dozer are two views of one encounter; Tally’s play area is inside its restaurant safe room; Ball of Swine details belong to one connected boss complex; and generic or mentioned areas do not become confirmed visited rooms through illustration. Preserve those caveats in scene metadata and viewer labels.
