# HUD component QA

Validated the frozen export with `python Tools/test_hud_components.py`. Result: **PASS**.

The independently replayed 78 raw PNG fragments reproduce every displayed source RGBA pixel at 1536×1024, with zero differences. The test uses only exported fragment PNGs and declared offsets to build the replay; the source is used solely for comparison. RGB bytes beneath fully transparent pixels are normalized to zero for comparison, because the source contains hidden RGB data. Source and fragments have binary alpha (0 or 255), preserving transparency without an opaque canvas fallback.

Verified 17 widget PNGs by independently composing their declared constituents. Group membership is complete and unique; stable IDs, parent references, original fragment-parent references, relative offsets, bounds, source hashes and individual PNG hashes pass. The layered OpenRaster archive independently replays exactly, and its merged preview matches. Every delivered file is present byte-for-byte in the ZIP. The three optional frame slice sets contain 27 PNG pieces; each set covers its frame exactly once and rejoins to the original native-size frame.

Visual review of the source and overview confirms:

| Visible region | Raw fragments |
| --- | ---: |
| Objective frame, face, lantern and text | 4 |
| Party phase, round, separator and three diamonds | 9 |
| Four party cards, portraits and ready markers, including Carl selection glow | 17 |
| Bottom frame and background | 2 |
| Selected Carl portrait, frame, backing and name | 4 |
| HP label, 32 / 40 value, outline, track and fill | 5 |
| Mana label, 8 / 12 value, outline, track and fill | 5 |
| Movement separator, boot, 4 and Move label | 4 |
| Move, Strike, Skills and Items actions, including selected Move glow | 17 |
| Rat target portrait, frame, face, separator, name and 12 damage text | 7 |
| End Carl’s turn frame, face, text and arrow | 4 |
| **Total** | **78** |

The overview presents all 17 groups legibly on a transparency checkerboard, including the full-width structural bottom panel separately. World health bars and speech/tooltip layers are absent. The exact replay also protects frame edges, ready dots, both active diamonds, the empty diamond and selection glow pixels against omissions.

These are visible raster fragments. Backgrounds and frames retain holes where foreground artwork owned the pixels. They are not reconstructed hidden panels. Text is raster artwork rather than editable font objects. Portrait/icon boundaries retain the source segmentation and baked edge colors. Nine-slice validation establishes exact native-size reassembly; it does not certify a redesigned frame at arbitrary sizes.
