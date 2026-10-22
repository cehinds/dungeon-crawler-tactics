# Modal and feedback QA

Verified the published WebAssembly build at `http://127.0.0.1:5188` with Chromium on 2026-10-22. These are browser viewport checks, not physical-device or screen-reader tests.

## Results

Tested 360×640, 390×844, 844×390 and 1366×768. In each viewport, the Save & options dialog and its footer stayed within the visual viewport. Focus entered the dialog, Tab wrapped from its last control to the first, Escape closed it, and focus returned to the Save & options button.

Exporting a real save produced a downloadable JSON file and a success toast inside the open native dialog's top layer. Hit testing confirmed the toast rendered above the dialog. Repeating the export three times left one matching toast. The toast did not steal focus; focusing its dismiss button kept it visible for seven seconds, and dismissal returned focus to Export save file.

An invalid move command produced a warning, “Wait for the crawler phase in battle.” It did not generate movement success feedback. The warning used a live status role.

The integrated UI regression, `python3 Tools/playtest_ui.py --url http://127.0.0.1:5188 --browser /usr/bin/chromium`, passed all four viewports. It verified exploration traversal, class change, no page scroll, forecast Escape preserving the saved state, action confirmation, expected success toast, and focus restoration. There were no browser page errors.

## Limitation

At 844×390, the export toast overlaps part of the Save & options explanatory text while the dialog is open. The toast remains above the dialog, and the footer and controls remain reachable. At the portrait mobile sizes it sits above the bottom sheet without covering its controls; at desktop it sits outside the centered dialog.
