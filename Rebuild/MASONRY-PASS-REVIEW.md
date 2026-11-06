# Masonry pass review

Compared the clean-map reference with the accepted seed-1337 boss capture at `MasonryPassComparison/pass-01/seed-1337-boss.png`. This pass adopts the reference’s broad visual hierarchy without claiming a 1:1 reconstruction or that all shapes match.

The accepted capture reads first as a broad paved court bordered by substantial dark masonry. The wall blocks are larger and their courses vary more than in the prior five-pass capture. Floor damage is sparse enough for the broad slabs to remain legible. A few small moss clusters sit along blocked wall margins. Existing water channels, grates, brass machinery, gold coping, and the stair focal point remain distinct.

Implementation assembles masonry from existing hosted art with renderer `drawImage` crops and descriptors; it does not place the clean reference image as a background. Wall and floor sampling share an origin for consistent placement. The hosted asset manifest remains at 91 files; this pass reuses those assets.

## Acceptance checklist

- [x] Broad dark masonry reads at overview scale; larger blocks and varied courses replace the formerly dominant small-brick repetition.
- [x] The central paving reads as broad slabs; fracture marks are sparse and do not repeat densely across the court.
- [x] Small moss accents are restrained and placed along blocked masonry margins.
- [x] Existing route, water edges, grates, machinery, coping, and stair remain visually legible in the capture.
- [x] Art is assembled from existing assets rather than using the reference image as a whole-map background.
- [x] Floor and wall sampling use a consistent origin.
- [x] Hosted asset manifest count remains 91.
- [x] Final C# test, publish, and browser verification passed.

Capture evidence: `Rebuild/MasonryPassComparison/pass-01/`. See `README.md` for the reproducible capture command and review gallery location.

## Final verification

Release QA passed: the C# suite covered 102 worlds; publish restored all 91 manifest assets; the floor-one browser playthrough and full arena suite passed for seeds 1337 and 42. Arena evidence used fresh captures (`arenaReused: false`), including desktop and mobile combat, real doorway and full three-cell bridge crossings for both seeds, and a closeup. The read-only surface identity audit matched 114 observed floor/wall cells per seed, and its JSON report validated. These captures record actual keyboard play with the normal clock; the separate comparison capture uses fixed camera framing and animation time for visual review.

For the actual layered arena checks, including the observational surface identity report, run:

```sh
python3 Tools/capture_map_refinement.py --layered --url http://localhost:8765 --browser /usr/bin/chromium --output Rebuild/MasonryPassComparison/final-qa
```
