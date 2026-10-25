# Book 1–5 location tile delivery checks

Checked 2026-10-24 against the authored inventory, reviewed crop fragments, and actual exported PNGs.

## Alignment correction — 2026-10-25

The initial export used the complete alpha rectangle as a floor plane and independently forced wall heights. This included slab thickness and vegetation in floor dimensions and changed wall slopes. Registration now maps reviewed floor surfaces and visible wall foot contacts to the grid while retaining surrounding artwork.

- [x] 298 full-ground surfaces and 300 wall/door contact baselines registered across all three styles.
- [x] Floor registration separates decorative overhang and slab depth from the walking surface.
- [x] Wall contact endpoints lie on supported portions of the visible feet, rather than extending into empty space.
- [x] Ink & Lanterns desert wall 7 and Over City wall 6 regenerated to supply the missing opposing directions; all 48 replacement-sheet crops passed extraction and ownership checks.
- [x] 20 exporter tests passed, including floor-edge matching, overhang independence, wall contacts, clipping rejection and registered export reconstruction.
- [x] Layout tests confirm adjacent wall endpoints coincide and land on floor vertices in both projections; the two isometric room boundaries meet at one corner.
- [x] The browser uses edge-centered wall placement and provides a Show grid overlay from exported contact metadata. Irregular rail pieces are excluded from automatic compositions.
- [x] All 100 pixel wall/door registrations passed clipping validation. The tall submarine open doorway has a reviewed vertical-scale override rather than silently cropping its arch.
- [x] All 75 rebuilt variants passed fresh-browser checks. Show grid changes the canvas and switching it off restores the exact original pixels in every variant.
- [x] All 2,025 download/manifest/contact-sheet links and all 75 ZIPs passed local HTTP, content and CRC checks again.
- [x] Twelve representative rooms were visually reviewed with the grid: all three starter styles, the corrected painted city/desert, painted rails, and coral/jungle in all three styles. Desktop and 390px mobile checks passed without errors or horizontal overflow.

A small visible gap remains at the rear corner of the comic submarine room, between the beveled wall-end silhouettes. The contact baselines meet; a dedicated corner joint or a further wall-end art pass is still needed for a seamless silhouette there.

The two irregular Ink & Lanterns rail components described in [Registration.md](Registration.md) retain legacy sizing and are marked for manual alignment in the browser. Transition pieces, corners, endcaps, stairs and props retain their previous sizing rules; this pass does not certify every component as a seamless autotile.

## Asset checks

- [x] 25 kits in each of three styles: 75 variants and 1,800 individual component PNGs.
- [x] All 75 source atlases are 1536×1024 RGBA with transparent separation; preserved under `sources/` outside the published site.
- [x] All 1,800 extractions are nonempty and have disjoint reviewed pixel ownership. Masks retain separate alpha islands without painting new pixels.
- [x] Every export is RGBA on a 256×256 canvas; all 1,800 decoded pixel hashes are distinct.
- [x] Export builds reconstruct and validate PNG pixels, source hashes, anchors, metadata, contact sheets and ZIP contents. Every ZIP contains 24 PNGs, one manifest and one contact sheet.
- [x] Four comic wall/rail axis defects were regenerated and revalidated before export.
- [x] The 20 focused exporter tests passed, including changed-source rejection, overlap rejection, clipping, determinism, partial builds and catalog consistency.
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

The normalized grid and anchors support composition, but the generated silhouettes can leave small visible seams. The raw atlases do not guarantee uniform gutters; extraction uses reviewed masks rather than blind grid slicing. Pocket Dungeon previews use a north wall; isometric previews use two boundary axes assembled from registered straight walls rather than stretched corner blocks. Not every prop has four directional views, and the PNGs do not constitute a complete autotiling set. A comic open-doorway illustration reads more like a filled door face than a clear opening; it needs a future art pass before being used as an unambiguous open-state gameplay indicator. Random preview compositions can repeat props.

The browser composition uses actual selected-kit PNGs, but is an art study rather than a playable map. The new assets are not connected to the game's encounters, procedural runtime, collision rules or Unity scenes. No Unity Editor validation was run. Shared C# build and regression validation runs in the GitHub Pages workflow; no local .NET SDK was available.

The alignment revision’s static source tree is 878.6 MiB before the browser build adds framework output. Original source atlases remain outside Web to avoid including them in the Pages artifact.
