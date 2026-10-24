# Book 1–5 location tile delivery checks

Checked 2026-10-24 against the authored inventory, reviewed crop fragments, and actual exported PNGs.

## Asset checks

- [x] 25 kits in each of three styles: 75 variants and 1,800 individual component PNGs.
- [x] All 75 source atlases are 1536×1024 RGBA with transparent separation; preserved under `sources/` outside the published site.
- [x] All 1,800 extractions are nonempty and have disjoint reviewed pixel ownership. Masks retain separate alpha islands without painting new pixels.
- [x] Every export is RGBA on a 256×256 canvas; all 1,800 decoded pixel hashes are distinct.
- [x] Export builds reconstruct and validate PNG pixels, source hashes, anchors, metadata, contact sheets and ZIP contents. Every ZIP contains 24 PNGs, one manifest and one contact sheet.
- [x] Four comic wall/rail axis defects were regenerated and revalidated before export.
- [x] The 16 focused exporter tests passed, including changed-source rejection, overlap rejection, clipping, determinism, partial builds and catalog consistency.
- [x] JavaScript syntax and whitespace checks passed.

## Coverage checks

- [x] 177 unique source-linked location, sub-area and route records; all kit references resolve.
- [x] 166 records have reusable kit associations; 11 remain explicitly marked `review-needed`.
- [x] Visited, mentioned, remote and uncertain appearances remain distinct.
- [x] Book 5’s Great Race and Floor 8 selection transition are represented without inventing a visited island destination.
- [x] The castle transfer is distinguished from the Floor 6 bramble-crater battle.

## Browser checks

- [x] All 75 actual kit variants browsed through the UI, each with 24 component cards and a nonempty composition rendered from its PNGs.
- [x] All 2,025 local HTTP links returned 200: 1,800 PNGs, 75 manifests, 75 ZIPs and 75 contact sheets.
- [x] All 75 downloaded ZIPs passed CRC checks and contained exactly 26 files, including 24 PNGs and a manifest matching the standalone download.
- [x] Desktop and 390px mobile checks passed without horizontal overflow, browser console errors, page errors or failed HTTP requests.
- [x] Three style tabs, keyboard navigation, book/location filters, search and empty results, evidence links and composition regeneration passed.
- [x] Great Race mention versus shattered-pod visit, unidentified Floor 8 destination, and remote Larracos displayed correctly.
- [x] Representative composition and component screenshots were visually inspected in each style. Browser verification used the local static server; the public URL is delivered by the Pages workflow.

## Practical limits

This is a researched asset library, not a full-text concordance or a complete canonical floorplan collection. Multiple named places share environment kits. Tile art, arrangement, measurements and unsourced details are adaptations.

The normalized grid and anchors support composition, but the generated silhouettes can leave small visible seams. The raw atlases do not guarantee uniform gutters; extraction uses reviewed masks rather than blind grid slicing. Pocket Dungeon previews use a north wall; isometric previews use two boundary axes. Not every prop has four directional views, and the PNGs do not constitute a complete autotiling set. A comic open-doorway illustration reads more like a filled door face than a clear opening; it needs a future art pass before being used as an unambiguous open-state gameplay indicator. Random preview compositions can repeat props.

The browser composition uses actual selected-kit PNGs, but is an art study rather than a playable map. The new assets are not connected to the game's encounters, procedural runtime, collision rules or Unity scenes. No Unity Editor validation was run. Shared C# build and regression validation runs in the GitHub Pages workflow; no local .NET SDK was available.

The final static source tree is 869.8 MiB before the browser build adds framework output. Original source atlases remain outside Web to avoid including them in the Pages artifact.
