# Completed layer source cutouts

This pack explores how the supplied dungeon scene could be rebuilt from reusable, complete components. It is an art and layout study, not a production runtime integration. Hidden pixels cannot be recovered from the flattened reference, so new surfaces and replacements are inferred artwork. The reference-aligned composition is not pixel-identical and carries no zero-difference claim.

## Inventory

The current manifest contains **315 assets** and **255 placed instances** on a 1536 × 1024 canvas. Assets are available images; instances are placements in the composition. The inventory separates reused components, newly authored designs, derived construction regions, and reference placements:

| Source or role | Count | Meaning |
| --- | ---: | --- |
| Reused complete map modules | 144 | Existing full authored modules selected from `map-grid-pass`; not the 52 visible fragments. |
| Reused clean HUD backgrounds | 16 | Complete HUD backing plates. |
| Reused blank framed HUD controls | 16 | Complete blank controls with frames. |
| New world/HUD overlay designs | 24 | New reusable designs; only the placements listed in the recipe are used in this composition. |
| Derived architecture construction regions | 95 | Grid regions from generated completed architecture. These are derived construction surfaces, not 95 separately authored objects. |
| Isolated complete exit | 1 | Whole generated exit fitted at its reference anchor with margin; its doorway and stair threshold are designed openings. |
| Reference-anchor variants | 17 | Reusable full modules fitted as complete silhouettes to source positions. These are placements/variants, not new authored designs. |
| Continuous water backing regions | 2 | Coverage behind foreground architecture and objects, not object designs. |

The 315 assets comprise 144 + 16 + 16 + 24 + 95 + 1 + 17 + 2. The **255 instances** are the placements recorded in `recipe.json`; they are not the sum of the available component inventory. `manifest.json` is the definitive source for paths, dimensions, pivots, placement offsets, painter order, hashes, and per-asset provenance.

## Layering and transparency

The ground covers the whole canvas beneath objects. The two water backing regions continue beneath foreground banks and objects so removing an occluder does not reveal an object-shaped hole. Architecture comes from a newly generated complete study, with designed passage gaps. It is segmented into construction regions, while the exit remains one whole component. `sources/completed-architecture-generation.png` preserves the generated architecture source.

Alpha marks component silhouettes and designed openings; it is not a mask copied around foreground objects from the flattened reference. A transparent doorway or canal opening is intentional. A transparent patch shaped like a crate, pipe, or other occluder would be cutout damage. Region boundaries and `construction-continuation` values describe construction joins. They do not promise seamless joins for every neighbor or mean every region is an independently authored game object.

The manifest's pivots, illustrative collision bounds, side socket labels, alpha intent, and provenance are editing and placement metadata. Collision bounds are not gameplay collision data, and sockets do not form a runtime connection system. Check the actual PNG and its alpha before relying on a visual join; metadata alone does not promise seamlessness or pixel matching.

## Provenance and exclusions

The 144 map modules are reused from `Web/wwwroot/assets/map-grid-pass/manifest.json`. The HUD backing plates and blank framed controls are reused from `Web/wwwroot/assets/hud-reusable/manifest.json`. The 24 new overlay designs are generated assets, with their source image, individual components, and hashes recorded in the manifest. Architecture regions derive from the generated architecture study. The exit is a separately generated standalone image, fitted as a whole object at its reference anchor. The 17 reference-anchor variants are complete reused modules resized as whole silhouettes, not copied source masks. The two water regions are inferred continuous coverage.

This pack excludes the 52 derived visible fragments and exact-view contextual restoration pieces from the reference-layer workflow. Contextual repair patches are excluded because they restore pixels specific to a cutout view rather than provide reusable complete objects. No asset is recovered hidden source art.

## Files and rebuilding

- `manifest.json` and `recipe.json` describe the available assets and all 255 placements. `components/` holds the reusable component PNGs.
- `layers/` contains nine full-canvas category plates. In `completed-layers.ora`, the 255 editable instance leaves are grouped into nine categories; the ORA retains individual placements rather than flattening each category into one layer.
- `reference-aligned-scene.png` and `composition-demo.png` show the current composition. `modular-room-demo.png` shows the secondary modular arrangement.
- `comparisons/` places prior visible-fragment layers beside complete modular category plates. These are visual comparisons, not pixel-difference evidence.
- `sources/` contains generated studies. `completed-layers.zip` is the portable pack; `package-manifest.json` records hashes for packaged files; `reassemble.py` is the portable replay script.

Rebuild from the repository root with:

```sh
python3 Tools/build_completed_layers.py
```

Replay the packaged recipe from its directory (requires Pillow):

```sh
python3 reassemble.py --recipe recipe.json --output replay.png
```

The archive carries the files and recipe. Rebuilding the repository pack reads the source manifests and assets named by `Tools/build_completed_layers.py`. These files are art templates and demonstrations; they do not connect assets to production game rendering, animation, navigation, or gameplay collision.
