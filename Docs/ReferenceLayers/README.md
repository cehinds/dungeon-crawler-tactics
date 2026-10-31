# Reference layer pack

This pack separates the supplied combat concept image into editable PNG fragments while keeping its native layout. It is for studying and editing this one reference composition; it does not claim gameplay or animation integration.

## Files

- `scene.json` is the layer manifest and coordinate source of truth. `manifest.json` is the same scene data in the generated web asset pack.
- `layers/` contains the transparent PNG crops used to assemble the scene. There are 1,595 exported layers across 11 semantic groups. The source inventory has 1,463 records: 1,317 visible source fragments and 146 fully occluded records that had no visible pixels to export.
- `reference-layers.ora` is an OpenRaster file with semantic groups and native layer offsets, ready to open in Krita, GIMP, or another ORA editor.
- `viewer.html` is the bundled layer viewer; it renders the individual component PNGs. `group-previews/` contains cached group images for inspection or optional consumers.
- `original-reference.png`, `reconstructed.png`, `diff.png`, `clean-map.png`, and `exploded-layer.png` are comparison and review images. The original is comparison-only and is not part of the editable draw stack.
- `reassemble.py` composes the PNG layers using the manifest. `package-manifest.json` records SHA-256 hashes for package files; it excludes itself and the containing ZIP.
- In the ZIP, `tools/` contains the builder, viewer template, and QA test; `recipe/scene.json` is the authored scene manifest. Rebuilding the pack requires the original repository inputs. The standalone `reassemble.py` command works with the packaged scene and layers.

## Coordinates and layer fields

The canvas is **1536 × 1024** native reference pixels, with `(0, 0)` at the top left. Use scale 1 with no rotation or snapping to preserve the supplied positions. In each scene layer, `offset: [x, y]` is the PNG's top-left position on the canvas; `size` is its crop size; and `anchor: [0, 0]` records the crop's top-left pivot. `z` is the actual painter order in the exported scene. `sourceZ`, `sourceBounds`, and `sourceAnchor` retain corresponding source-manifest metadata where available.

The `kind` field distinguishes `original-visible` fragments, `inferred-underpaint`, and `context-restoration` pieces. Underpainting was generated from the map-grid-pass inferred environment; it is not recovered original background art. The context-restoration pieces retain exact source boundary pixels around removed silhouettes. They are tied to these reference positions and should stay with the affected context; they do not reveal hidden edges or make objects animation-ready. In the viewer, these restorations are automatically hidden when any dynamic group is toggled off, which avoids leaving source-edge ghosts.

The exact source fragments are separate from the 144 new atlas designs in the project: those designs are alternative assets and were not used to recreate this exact source image.

## Edit and reassemble

For visual editing, open `reference-layers.ora`. Keep each layer's canvas offset intact when editing or replacing its image. To replay the JSON package from the repository root:

```sh
python3 Docs/ReferenceLayers/reassemble.py \
  --scene Docs/ReferenceLayers/scene.json \
  --output /tmp/reference-replay.png
```

The script reads each layer path relative to the scene file. `--clean` renders layers marked `cleanVisible`; `--hide GROUP` can be repeated to omit semantic groups. For example:

```sh
python3 Docs/ReferenceLayers/reassemble.py \
  --scene Docs/ReferenceLayers/scene.json \
  --clean --output /tmp/clean-map.png
```

The package includes an HTTP-served viewer at `viewer.html`. Serve the pack directory with any static HTTP server and open that page; browsers may block local image fetches under `file://`, so use HTTP when testing the viewer. It reads the bundled scene data and component PNGs directly.

## Fidelity

The full reconstruction was checked at native size: `scene.json` records zero changed RGBA pixels against the supplied source. The underpainted clean view is an inferred environment reconstruction, not evidence of the original hidden background. See [QA.md](QA.md) for validation scope and limits.
