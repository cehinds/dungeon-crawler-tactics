# Map structure browser QA

Validated 2026-10-31 against the regenerated concept room outputs using headless Chromium (`/usr/bin/chromium`) and Playwright. Run the static inspector server, then execute:

```sh
python3 -m http.server 5197 --bind 127.0.0.1 --directory Web/wwwroot
python3 Tools/playtest_map_structure.py
```

All seeds **7, 9, 29, 103** passed at **1440 × 1000** and **390 × 844**:

- Canvas RGB pixels exactly equal the Python-rendered `procedural/room-SEED.png` at native 1536 × 1024 resolution.
- Downloaded JSON equals the corresponding generated room plan, including structural data, placements, validation and ordered draw plan. The browser adds explicit asset provenance; that additional field is excluded from room-plan equality.
- Downloaded PNG equals the displayed canvas; filenames and JSON seeds match the displayed seed.
- Editing the input without generating preserves the displayed seed and downloaded recipe.
- No JavaScript page errors or horizontal document overflow occurred.

Actual seed-9 canvas and full-page desktop/mobile screenshots plus machine results are stored outside delivery at `/workspace/scratch/map-browser/`. Visual review of the browser canvas confirms distinct stepped wall contours, visible portal openings, clear entrance/exit approaches, upright actors/props, readable wall edges and water bank, and separation of board art from the HUD. The mobile screenshot confirms controls and preview fit the page. The room preview is an illustrative static composition; this test makes no gameplay or Unity execution claim.
