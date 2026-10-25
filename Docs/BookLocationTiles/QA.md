# Book 1–5 location tile QA

The native square-grid art, export, browser, cache, download, and visual review are complete. Working source sheets are the newly drawn 6×4 native atlases; previous source versions remain in Git history, and generated originals are retained under `/workspace/generated_images`. The exporter preserves native source PNGs and only resizes derived component PNGs.

## Engineering checks already passed

- [x] 23 focused exporter tests passed.
- [x] Layout tests passed for north and west wall axes on the orthogonal grid.
- [x] All 75 native atlases and 1,800 component exports built and validated for source, extraction, pixel ownership, geometry, and ZIP contents.
- [x] All 1,800 decoded RGBA component PNG pixel hashes are unique; all use 256×256 canvases with anchor `(128, 192)`.
- [x] All three styles use the orthogonal 128×128 square grid. Export totals: 450 floors, 225 north-wall/door components (including 150 doors), 75 west walls, 450 overlays, and 600 props.
- [x] All 600 components in each of the three styles passed `prepare_kit`.
- [x] The pixel-style open submarine doorway has a clear transparent aperture (0 alpha pixels across its 7,650-pixel opening).

## Browser and visual checks

- [x] All 75 UI variants use orthogonal 128×128 grids. Grid on/off changes pixels and restores the exact original canvas when disabled.
- [x] All 150 doors were visually checked: frontal views, vertical jambs, level bases, and no diamond plinths.
- [x] All 75 variants passed location, evidence, search, style tabs, keyboard navigation, and composition regeneration checks.
- [x] Twelve composition cases across the three styles (starter, sea, jungle, painted city/desert, and rails) visibly use square geometry; all four native rail floor pieces were included.
- [x] At 1440px desktop and 390px mobile widths, there was no overflow, browser error, or failed request.
- [x] All 2,025 raw links and 2,025 versioned asset links returned HTTP 200. All 75 ZIPs contain 26 valid entries (24 PNGs, manifest, contact sheet); CRCs pass and PNGs match their manifests.
- [x] Cache-on style changes and reloads reuse the same 27 asset URLs and canvas; JSON revalidation headers and query downloads return successfully.

Subtle art borders, 32px wall caps, and softness when pixel art is enlarged are expected asset characteristics; they did not indicate projection or alignment failures.

## Location coverage

- [x] 177 unique source-linked location, sub-area, and route records; all kit references resolve.
- [x] 166 records have reusable kit associations; 11 remain explicitly marked `review-needed`.
- [x] Visited, mentioned, remote, and uncertain appearances remain distinct.
- [x] Book 5’s Great Race and Floor 8 selection transition are represented without inventing a visited island destination.
- [x] The castle transfer is distinguished from the Floor 6 bramble-crater battle.
- [ ] Full-text audit and complete canonical map validation remain pending.

The location index remains research coverage, not a complete canonical floorplan collection. Multiple named places share reusable environment kits, and art, layouts, measurements, and unsupported details are adaptations.

## Scope and known limits

The library is a set of art assets and composition metadata. It is not integrated into playable game maps, encounters, procedural runtime, collision, or Unity scenes. A sample composition is not a playable room. Not every prop has alternate directional views, and the metadata does not provide a complete autotiling or pathfinding system. This QA covers the native exports and browser library, not runtime integration.
