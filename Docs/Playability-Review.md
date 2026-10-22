# Playability review

Verified against the newly published browser build at `http://127.0.0.1:5188` using Chromium on 2026-10-22. Tested viewports: desktop 1366×768, mobile 390×844 and 360×740.

## Verified results

- From a fresh run, the welcome and help dialogs could be dismissed, and the party entered exploration from camp.
- I moved over the exploration grid with visible tile clicks, discovered the Sponsor supply cache, and claimed it. The shared Health Tonic count increased from 3 to 4. I then approached and entered the marked encounter door through its visible interaction button.
- In battle, a legal move updated Carl's position and marked his move spent. Brawler's Second Wind showed a forecast and was confirmed; the crawler's activation then showed as spent.
- Stormcaller's Spark was selectable and targeted the Maintenance Goblin. The forecast showed energy changing from 12 to 10 and the goblin's HP changing from 18 to 10. Confirming applied the action.
- At each tested viewport, document height equaled the viewport height (768/768, 844/844, 740/740), with no horizontal overflow. The board, selected crawler, action panel, forecast and turn controls were on screen without page scrolling.

## Small-screen behavior

At 360×740 with a forecast open, the ability list uses a bounded inner scroll area so the board and confirm/cancel controls remain visible. The final layout uses full-height action rows, rather than shrinking their text. Longer action lists still require scrolling within that panel.

The final mobile camp layout was also checked at 360×740 and 390×844: all eight roster choices, class selector, effect summaries, deployment toggle and Explore button fit in the viewport. All four deployed crawlers are visible together during battle. Native supplies/log dialogs trap keyboard focus and restore it on close.

## Follow-up regression checklist

- Repeat cache discovery and collection, then verify the supply count and save state persist after reload.
- Verify each encounter landmark leads to its matching battle and that reward, return-to-camp and next-sector progression remain connected.
- At 1366×768, 390×844 and 360×740, check keyboard and touch movement, action-list scrolling, target highlighting, forecast cancellation and confirmation, and end-turn controls.
- Test representative enemy, ally and terrain actions, including disabled actions and their reasons.
- Confirm that action purpose, target type, cost and range remain visible before selection, and that screen-reader labels and focus states identify map cells, landmarks and forecasts.
