# Asset expansion validation — 2026-10-24

- [x] 720 new native PNG files with distinct SHA-256 hashes; 240 per style.
- [x] 1,080 total native components; 360 per style.
- [x] 576 new static components and 144 native animation frames, counted once.
- [x] 24 six-frame clips, with shared-scale 256×256 exports, strips, metadata and WebP previews.
- [x] 30 collection ZIPs, each containing its 24 native components, manifest and contact sheet.
- [x] All three packs built successfully with extraction, alpha ownership, frame registration, pixel comparison and archive validation.
- [x] 28 exporter regression tests passed, including legacy optional-sheet support and authored animation anchors.
- [x] Gallery JavaScript syntax and whitespace checks passed.
- [x] Actual desktop and 390px mobile gallery checks passed for all three styles: 48 initial cards, 96 after load-more, 240 new additions, ten 24-piece filters, play/pause, scrubbing and reduced motion.
- [x] All 144 normalized frame URLs and collection, sprite-sheet and metadata download links returned HTTP 200; no browser errors or horizontal mobile overflow were observed.

| Style | Native components | New components | Clips | Complete ZIP |
| --- | ---: | ---: | ---: | ---: |
| Pocket Dungeon | 360 | 240 | 8 | 61.50 MiB |
| Ink & Lanterns | 360 | 240 | 8 | 74.15 MiB |
| Dungeon After Dark | 360 | 240 | 8 | 76.85 MiB |

The artwork was visually reviewed during generation and extraction. Clipped long weapons and animation effects that connected neighboring cells were regenerated. Frame anchors were reviewed against the source images and normalized to actual extraction bounds. Contact sheets and browser animation previews were also inspected.

These checks validate the downloadable art library and its browser gallery. They do not certify production tile seams, collision shapes, every directional pose, Unity import settings or gameplay integration. Those remain separate integration work. The procedural generator continues to use its existing production room kit.
