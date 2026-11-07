# Earned checkpoint regression fixture

`earned-safe-v2.json` is the exact, unmodified 53,570-byte safe-room checkpoint captured through browser gameplay against baseline game commit `e62baa8f479f0598356ba521f0421c078c885796`. Its original capture path was `Rebuild/BlockAComparison/baseline/save-v2.json`.

The seed-1337 run cleared the false guild, met Mordecai, and saved at quest stage 2. Carl and Donut each earned level 2 and 100 XP; the checkpoint contains 20 gold and turn 4. No XP, ranks, inventory, or world geometry were edited to create this fixture. Its envelope is save version 2 and its world is generation version 4.

The browser state regression uses this retained checkpoint to exercise migration into the current save format and continue normal gameplay. It is test data, contains no art, and requires no untracked comparison directory.

SHA-256: `f09c3c18f86c4fab7a84e81e3c31d99361c0c7a02b039eefc680421486f14bc2`.
