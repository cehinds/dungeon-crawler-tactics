# Reusable HUD assets

`Web/wwwroot/assets/hud-reusable/` contains 205 reusable parts across 17 groups, including 16 clean panel and stat-bar backgrounds, alongside the 78 archived source fragments. Sixteen groups have a composed `blank/` control; movement is represented by separate parts without a background frame. `manifest.json` is the index: it records each asset's stable ID, file, role, provenance, top-left `offset`, size, z value, parent group, and hash. PNG coordinates use the original 1536 × 1024 canvas. `offsetInParent` gives the part's position inside its cropped group image. Pivots are currently top-left (`[0, 0]`); set a different engine pivot deliberately when importing.

## Files

- `backgrounds/`: clean material clipped to a panel's authored silhouette.
- `parts/`: individual borders, icons, portraits, meters, raster text and other foreground pieces.
- `blank/`: assembled clean panel controls where the source has enough frame/background geometry to make one.
- `populated/`: assembled group previews with their foreground parts.
- `details/`: labeled part sheets, and `overview.png`, `original-vs-clean.png`, `repopulated-hud.png` for review.
- `materials/`: cropped navy and parchment surfaces used by the clean backgrounds.
- `sources/`: generated surface source image.
- `masks/`: exterior panel masks.
- `original/`: archived literal source fragments; these retain the extracted cutouts.
- `hud-reusable.ora`: layered OpenRaster composition; `hud-reusable.zip`: portable copy of the package.

Four party-card frames and two stat outlines include separate `source-boundary-fringe` overlays: colored edge pixels are kept off the blank controls and restored in the populated groups. The HP and mana blank bars also have clean navy backing beneath the outline and complete track. The manifest also maps each original layer in `originals`, groups in `groups`, and split text or meter parts in `splitSources`. Use those entries to discover the actual parts and their assembly order instead of relying on filenames alone.

## Rebuilding controls

For a full-canvas composition, draw each asset at its `offset` in ascending `z`; ties are ordered by ID in the generated preview. For a cropped group, use `groups[].offset` as its canvas position and each asset's `offsetInParent` within it. Parts keep their source-derived position and size. To replace a label, place new text at the intended layout position, above its background and below any foreground ornament that should overlap it. The clean backgrounds are reconstructed image-generated navy or parchment surfaces clipped to source panel shapes. They remove holes under text, shoes, portraits and controls, but are not pixel-exact recovered source backgrounds. The original fragments remain available for reference.

For a resizable frame, use its nine-slice `border-*` crops; fully transparent crops are omitted. Stretch the top and bottom edges horizontally, the left and right edges vertically, and keep the corners at native size. `slice.rect` and `stretchAxis` in the manifest identify the pieces. The configured margins are construction choices in `reusable-spec.json`; check the panel at the target size because arbitrary resizing has not been visually certified. The `center-residual` piece is a source crop for the middle region; don't stretch it over the clean background.

Use z values to preserve intended overlaps. For example, put the clean background below its border and place text or icons above the panel surface. Keep portraits and their decorative frames in the order recorded by the manifest, then add selection glows where appropriate. Reposition or resize parts only as needed for the new layout; the included group previews show the reference arrangement.

## Text and dynamic values

The `raster-glyph-run` assets split only the glyph runs visible in the source artwork. They are raster crops, not a font, a complete character set, or recovered editable text. Use them only when the original lettering itself is needed. In a game, render changing values such as HP, mana, round, movement and damage as text at runtime above the clean background. The `textTokens` in `reusable-spec.json` transcribe selected source labels and example values; they are not a text-layout system.

## Provenance

Ordinary icon, portrait and decoration parts are literal source fragments. Panel surfaces are newly reconstructed from generated materials; stat tracks and glyph runs are documented individually in `provenance`. `original-vs-clean.png` shows the change on the dock. This package supports flexible layering and clean text placement while retaining the visible source's frames and artwork.
