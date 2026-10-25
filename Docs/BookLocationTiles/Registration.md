# Book location registration landmarks

The crop files contain reviewed `registration` objects on each cell definition.
Coordinates are pixels relative to the extracted component's **tight alpha crop**,
not the sheet, sourceBox, or padded extraction image. The exporter retains all
source artwork and derives an affine copy; registration is not a destructive crop.

298 of the 300 full-ground components (cells 0–3) have floor registration:
100 pocket-dungeon, 98 ink-and-lanterns, and 100 dungeon-after-dark. The source
floor plane, rather than the entire decorative alpha rectangle, maps to the grid.
Isometric order is top/right/bottom/left; orthogonal order is TL/TR/BR/BL.
Each fourth point completes a parallelogram, so it is coherent with the three
points used by the affine fit.

For ordinary isometric floors, two robust straight fits use the upper silhouette
away from its corners (12–40% and 60–88% of its width). These edges describe the
upper plane. Their intersection establishes its rear corner; extrapolation to
the side surface corners and parallelogram completion establish the other three.
The lower silhouette is deliberately excluded because it contains slab depth.
Pixel floors use the full square plane outer edges; their plane reaches the
export's bottom edge, so inset pixel-center landmarks would clip retained art.

The complete landmark contact sheets for all three styles were visually inspected
against source artwork. Explicit overrides address the coral overhang in
bubble-sea cell 1, foliage in hunting-jungle cells 0/1, and the asymmetric visible
ballast rectangles of ink-and-lanterns iron-tracks cells 0/1. Pixel coral/foliage
remain inside their visible square plane. Comic rails have a complete diamond
ballast plane beneath the tracks and use its upper edges.

## Deliberate exceptions

* ink-and-lanterns / iron-tracks / cell 2: curved rails have partial, irregular
  ballast rather than four visible corners of a full rectangular floor plane.
* ink-and-lanterns / iron-tracks / cell 3: crossing ballast is irregular and does
  not expose a coherent parallelogram; an attempted inferred plane was rejected
  during contact review.

These two assets retain the exporter's documented fallback. They require a
separate authored support plane or a special partial-track placement contract;
alpha extrema are not reviewed floor corners.

All 300 straight walls and doors (cells 6/7/12/13 across the 75 kits) also
have reviewed contact baselines. Robust fits use two separate foot bands at
8–28% and 72–92% of width, excluding the central arch opening and terminal
ornament. The fitted line is then intersected with actual bottom-contour
support: endpoints require a consecutive three-pixel run within three source
pixels of the contact line. This avoids extrapolating into empty space past
beveled endcaps or post feet; endcaps remain as retained overhang. Contact
support must span at least 45% of the source width. All 300 baselines pass
that support test. The full three contact sheets were visually inspected. Isometric
axis follows each source baseline's slope: rising right is grid y with reversed
endpoint order; falling right is grid x. This is determined separately for each
state: several door states and even some wall pairs face the same direction.
Orthogonal baselines map to grid x. Vertical scale uses the exporter's baseline
length ratio so vertical proportions remain tied to the horizontal contact span.

The resulting total is 598 reviewed registrations. The two partial ink rail
floors above are the only unregistered members of these eight cell families.

## Reproducing the authoring pass

`python Tools/author_book_registration.py --preview` writes the floor JSON
landmarks and temporary `/tmp/<style>-planes.jpg` review contacts. It does not
change source or exported images. NumPy and SciPy are optional authoring-time
dependencies; the build consumes the checked-in JSON and does not need them.
`python Tools/author_book_registration.py --walls-only` writes wall/door landmarks
and `/tmp/<style>-wall-lines.jpg` contact sheets.
The helper encodes the reviewed exceptions and manual overrides so rerunning
it preserves those decisions. New source artwork requires renewed visual review.

For incremental source replacement, combine `--style ink-and-lanterns` with
repeatable `--kit bubble-desert --kit over-city` filters. Run once for floors
and again with `--walls-only`; unselected styles and kits remain untouched.

The corrected ink bubble-desert and over-city sheets were merged from their
reviewed replacement crop definitions and incrementally registered again.
Bubble-desert wall 7 now faces grid y; over-city wall 6 faces grid x.

Pocket Dungeon bubble-sea cell 12 (open submarine arch) has a specifically
reviewed `verticalScale: 0.85`: its narrow contact span, tall arch, asymmetric
feet and foreground steps exceed the canvas headroom at the default scale.
This override retains the complete arch while preserving its supported contact
endpoints. All 100 pixel wall/door registrations passed direct exporter
transformation and clipping validation after this correction.
