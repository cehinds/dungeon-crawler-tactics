# Top-down whole-object library

The reusable library has 46 root-approved whole-object classes across the 36 Floor 1 concept scenes: 12 AB, 12 EF, and 22 CD. One front-facing CD barricade candidate is excluded. The 46 classes fit the planned 30–50 range. The central manifest lists IDs, source crops, transparent assets, and scene placements.

The old exact-reference decomposition is unchanged. Its partial source cutouts remain useful for pixel-accurate comparison, but they do not become whole-object assets through cropping. This new library uses image-generation source sheets with transparent backgrounds to reconstruct complete objects. These new images are inferred illustrations, not restored original pixels; covered portions are invented to complete the silhouette. Creature designs are illustrative placeholders and do not establish canonical models.

## Acceptance checklist

Root approved the current 46 classes against these object-image checks. Apply them again to any revised or new classes:

- The PNG shows the complete object silhouette, including sections covered in its source scene. No source-floor rectangles, neighboring props, shadow mats, or other background patches are included.
- The object reads from a direct overhead camera and keeps a consistent footprint and scale with the other approved library objects. Mappings use uniform `fit: contain-uniform`; do not stretch the source ratio.
- Transparency is real alpha with a clean, complete object boundary. Review the native PNG over a plain light background, a plain dark background, and a contrasting alternate floor to catch halos or hidden floor patches. Preserve the generated native RGBA; do not silently clean low alpha values.
- The source sheet, prompt, source rectangle, object ID, pivot, footprint, tags, and AI-generated-whole-object provenance are recorded. Distinguish generated completions from any exact source extraction.

Some edge shading or shadows may be baked into an object image. Do not claim a separate shadow asset unless it has its own object record.

Mappings remain separate from object-image approval. A mapping records `sceneId`, `objectId`, `replaceComponentIds`, target bounds, `z`, uniform-fit rule, status, and notes. The manifest has 125 placement demonstrations across 26 scenes; ten scenes have no whole-object placement. Root approved the 26-scene montage as partial demonstrations at scene scale, not as production replacements. The review removed the giant rail-network substitutions, corrected shelf orientation to 90 degrees and toilet orientation to 180 degrees, aligned long fixture axes, and placed rugs beneath furniture. Continue to validate any final mapping in its target scene and over an alternate floor. Architectural modules such as doors and wall segments are reusable authoring pieces; do not blindly overwrite complete wall, stair, or room regions. Partial demonstration mappings are not proof that the entire old scene cutout has been replaced.

## Coverage and remaining work

The [coverage file](coverage.json) lists all 46 approved object classes, the rejected barricade candidate, and all 36 scenes with mapping targets and remaining cutout counts. A library object being approved does not mean every matching scene has a production-approved mapping. Keep class coverage separate from mapping coverage. Of 524 previous reusable components, 412 remain unmapped in the current demonstrations. The 26-scene montage is [available here](../../Web/wwwroot/assets/top-down-object-kit/previews/scene-montage.png); additional [before/after](../../Web/wwwroot/assets/top-down-object-kit/previews/before-after.png), [light-background](../../Web/wwwroot/assets/top-down-object-kit/previews/library-light.png), [alternate-floor](../../Web/wwwroot/assets/top-down-object-kit/previews/floor-sand.png), and [mobile viewer](../../Web/wwwroot/assets/top-down-object-kit/previews/mobile.png) previews are also available.

The target is a focused 30–50-class library reused across all 36 scene IDs, not a claim that all roughly 500 old cutouts have been restored. Coverage counts refer to selected whole-object classes and explicit scene mappings only. Low-visibility background pieces, fine clutter, and non-object environmental context may remain as existing scene art.

## Central data

The central [schema](../../Web/wwwroot/assets/top-down-object-kit/schema.json), [manifest](../../Web/wwwroot/assets/top-down-object-kit/manifest.json), and [viewer](../../Web/wwwroot/assets/top-down-object-kit/viewer.html) are authoritative for object IDs, source sheet rectangles, per-asset QA, and scene mappings. The central output contains source sheets, transparent object PNGs, placement previews, and the viewer under `Web/wwwroot/assets/top-down-object-kit/`. The viewer compares each whole object with the previous context cutout at the same footprint and offers checker, light, dark, blue-floor, and sand-floor backgrounds, plus JSON and PNG downloads. The montage is an approved reference for provisional partial demos, not approval to replace the full old cutout in each scene. Five focused asset checks and the HTTP viewer smoke check passed; coverage records their scope.

To run the viewer locally from the repository root, start `python3 -m http.server 8000 --directory Web/wwwroot/assets/top-down-object-kit`, then open `http://localhost:8000/viewer.html`. This workstream does not alter the separate exact-reference layer kit. Production mapping acceptance still requires sample integration; the 125 montage-approved placements are provisional demonstrations, not completed restoration of the old component set.
