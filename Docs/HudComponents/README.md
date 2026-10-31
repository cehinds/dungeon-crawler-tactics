# HUD component pack

The 1536 × 1024 reference HUD is split into 78 transparent source fragments and 17 assembled widgets. The exported files live in `Web/wwwroot/assets/hud-components/` in the AI-Art repository. This directory stores the extraction specification and validation documentation.

## Pack contents

- `overview.png`: labeled view of all assembled widgets.
- `details/`: 17 sheets showing each widget's individual layers.
- `raw/`: 78 separate transparent PNG fragments.
- `widgets/`: complete appearances of the 17 visible widgets.
- `slices/`: 27 border pieces for three inactive action frames, plus cut-line guides.
- `manifest.json`: stable IDs, group membership, roles, text transcriptions, source coordinates, local coordinates and hashes.
- `hud-components.ora`: grouped OpenRaster document for layer-aware editors.
- `hud-source.png` and `hud-rebuilt.png`: reference and reconstruction.
- `hud-components.zip`: portable archive of the exports above.

## Component hierarchy

| Widget | Separate parts |
| --- | --- |
| Objective | Frame, background, lantern, objective text |
| Phase | Frame, background, PARTY, PHASE, separator, round text, three diamonds |
| Four party cards | Frame, background, portrait, ready indicator; Carl also has selection glow |
| Bottom panel | Outer frame, background |
| Selected character | Portrait frame, background, portrait, name |
| HP | Label, value, bar outline, track, fill |
| Mana | Label, value, bar outline, track, fill |
| Movement | Divider, boot, movement value, label |
| Four actions | Frame, background, icon, label; Move also has selection glow |
| Target forecast | Frame, background, portrait, divider, name, damage value, damage label |
| End turn | Frame, background, label, arrow |

## Reassembly

Use a transparent 1536 × 1024 canvas with a top-left origin. Draw `layers` in manifest order, placing each PNG at its `offset`. For an individual widget, draw its constituent layers at `offsetInParent`; its `offset` places the assembled widget on the full canvas. Keep pixel filtering set to nearest-neighbor when scaling the artwork.

All text remains raster artwork; the manifest includes transcriptions. Background fragments have transparent holes where foreground pixels were extracted. These fragments reproduce this reference exactly but are not clean, reconstructed backgrounds for arbitrary new text or icons. Complete widget PNGs preserve the original appearance. Native-size border slice reconstruction is tested; arbitrary resizing is not visually certified.

## Regenerate and validate

With the pinned concept-reconstruction art present and Python Pillow and NumPy installed, run from the game repository root:

```sh
python Tools/extract_hud_components.py
python Tools/test_hud_components.py
```

Validation independently replays the PNG and OpenRaster layers and checks widget composition, geometry, hashes, ZIP membership and frame slices. Fully transparent RGB is normalized for comparison; every visible source pixel is preserved.
