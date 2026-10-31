"""Author semantic source-coordinate world regions; never synthesize hidden pixels."""

from pathlib import Path
import json
import argparse
from PIL import Image, ImageDraw, ImageChops, ImageFilter
import numpy as np
from scipy import ndimage as ndi

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, default=ROOT / "Web/wwwroot/assets/concept-reconstruction/masks/scene")
parser.add_argument("--regions-output", type=Path, default=ROOT / "Docs/ConceptReconstruction/scene-regions.json")
args = parser.parse_args()
landmark_path = ROOT / "Docs/ConceptReconstruction/brick-landmarks.json"
silhouette_path = ROOT / "Docs/ConceptReconstruction/actor-silhouettes.json"
landmarks = json.loads(landmark_path.read_text())
silhouette_data = json.loads(silhouette_path.read_text())
architecture_data = json.loads((ROOT / "Docs/ConceptReconstruction/source-architecture.json").read_text())
if not landmarks.get("zones") or set(silhouette_data.get("actors", {})) != {"carl", "donut", "katia", "mongo", "rat-target", "rat-east", "rat-south"}:
    raise ValueError("Required authored brick and seven actor landmarks are missing")
for zone in landmarks["zones"]:
    for row in zone["rows"]:
        if not (0 <= row["y0"] < row["y1"] <= 1024 and len(row["seams"]) >= 2 and all(0 <= x <= 1536 for x in row["seams"]) and all(a < b for a, b in zip(row["seams"], row["seams"][1:]))):
            raise ValueError("Invalid brick landmark row")
for actor in silhouette_data["actors"].values():
    for polygon in [actor["outer"], *actor.get("additions", [])]:
        if len(polygon) < 3 or any(not (0 <= x < 1536 and 0 <= y < 1024) for x, y in polygon):
            raise ValueError("Invalid actor silhouette polygon")
if not architecture_data.get("regions"):
    raise ValueError("Required source architecture landmarks are missing")
for correction in architecture_data["regions"]:
    if "bounds" in correction:
        x, y, w, h = correction["bounds"]
        if not (0 <= x < x + w <= 1536 and 0 <= y < y + h <= 1024):
            raise ValueError("Invalid source architecture bounds")
    elif len(correction.get("points", [])) < 3 or any(not (0 <= x < 1536 and 0 <= y < 1024) for x, y in correction["points"]):
        raise ValueError("Invalid source architecture polygon")
OUT = args.output
OUT.mkdir(parents=True, exist_ok=True)
regions = []


def rect(id, cat, b, p=10, note=None):
    r = dict(
        id=id,
        category=cat,
        label=id.replace("-", " "),
        priority=p,
        shape=dict(type="rect", bounds=b),
    )
    if note:
        r["note"] = note
    regions.append(r)


def poly(id, cat, pts, p=30, note=None):
    r = dict(
        id=id,
        category=cat,
        label=id.replace("-", " "),
        priority=p,
        shape=dict(type="polygon", points=pts),
    )
    if note:
        r["note"] = note
    regions.append(r)


def raster(pts):
    im = Image.new("L", (1536, 1024))
    ImageDraw.Draw(im).polygon(pts, fill=255)
    return im


arena = [
    (342, 179),
    (810, 179),
    (810, 209),
    (1215, 209),
    (1215, 371),
    (1230, 371),
    (1230, 660),
    (1072, 660),
    (1072, 706),
    (973, 706),
    (973, 762),
    (904, 762),
    (904, 786),
    (644, 786),
    (644, 737),
    (552, 737),
    (552, 660),
    (319, 660),
    (319, 516),
    (342, 516),
]
channels = [
    [
        (69, 188),
        (310, 188),
        (310, 367),
        (280, 367),
        (280, 501),
        (194, 501),
        (194, 416),
        (174, 416),
        (174, 309),
        (69, 309),
    ],
    [(1214, 173), (1312, 173), (1312, 358), (1214, 358)],
    [(1263, 530), (1450, 530), (1450, 660), (1414, 660), (1414, 832), (1258, 832)],
]
# Individual masonry blocks follow the visible staggered stone courses. Arena and
# water footprints are cut out; these are source pieces, never clean plates.
world = raster([(0, 0), (1535, 0), (1535, 831), (0, 831)])
world = ImageChops.subtract(world, raster(arena))
for ch in channels:
    world = ImageChops.subtract(world, raster(ch))
# Mortar-aware masonry segmentation replaces the earlier coordinate lattice.
# Saturated blue surface components supply interior seeds. Watershed ascent
# follows dark mortar in the actual source; nearest surface ownership divides
# only remaining mortar/void pixels and prevents a remote bright UI seed from
# swallowing an entire dark wall. No regularly spaced rectangular stone cuts.
wall_rgb = np.asarray(
    Image.open(ROOT / "Web/wwwroot/assets/broadcast-kit/combat-concept.png").convert(
        "RGB"
    )
).astype(float)
wr, wg, wb = wall_rgb[:, :, 0], wall_rgb[:, :, 1], wall_rgb[:, :, 2]
surface = (wb > 35) & (wg > 16) & (wb > wr * 1.15) & (wb > wg * 1.03)
surface[832:] = False
surface = ndi.binary_opening(surface, iterations=1)
components, component_count = ndi.label(surface)
component_sizes = np.bincount(components.ravel())
interior_distance = ndi.distance_transform_edt(surface)
local_peaks = ndi.maximum_filter(interior_distance, size=21)
markers = np.zeros(surface.shape, np.int32)
marker_id = 0
for component_id in range(1, component_count + 1):
    if component_sizes[component_id] < 70:
        continue
    yy, xx = np.where(components == component_id)
    if component_sizes[component_id] < 2400:
        pos = int(np.argmax(interior_distance[yy, xx]))
        marker_id += 1
        markers[yy[pos], xx[pos]] = marker_id
    else:
        candidates = np.column_stack(
            np.where(
                (components == component_id)
                & (interior_distance == local_peaks)
                & (interior_distance > 3)
            )
        )
        chosen = []
        for py, px in sorted(candidates, key=lambda pt: -interior_distance[tuple(pt)]):
            if any((py - sy) ** 2 + (px - sx) ** 2 < 22**2 for sy, sx in chosen):
                continue
            marker_id += 1
            markers[py, px] = marker_id
            chosen.append((py, px))
# Manual landmarks: source top edge has dark stones too dim for the blue
# surface threshold. These centers were checked on the 3x native source zoom;
# they add watershed seeds, never prescribe rectangular output boundaries.
manual_top_centers = [8, 34, 63, 93, 121, 151, 174, 196, 223, 247, 272, 292, 315, 338]
manual_support = np.zeros(surface.shape, bool)
for px in manual_top_centers:
    marker_id += 1
    markers[8, px] = marker_id
    manual_support[6:11, max(0, px - 2) : px + 3] = True
brightness = ndi.gaussian_filter(np.max(wall_rgb, axis=2), 0.7)
seam_cost = np.clip(255 - brightness, 0, 255).astype("uint8")
watershed = ndi.watershed_ift(seam_cost, markers)
support = surface | manual_support
nearest_indices = ndi.distance_transform_edt(
    ~support, return_distances=False, return_indices=True
)
nearest_ownership = watershed[nearest_indices[0], nearest_indices[1]]
wall_ownership = np.where(support, watershed, nearest_ownership)
wall_ownership[:27, :340] = watershed[:27, :340]
world_pixels = np.asarray(world) > 0
# Connected pieces receive stable top-left ordering. Source occlusion can
# leave only a portion of an original stone; no unseen continuation is painted.
stone_parts = []
for marker in np.unique(wall_ownership[world_pixels]):
    mask = (wall_ownership == marker) & world_pixels
    parts, count = ndi.label(mask)
    for part in range(1, count + 1):
        yy, xx = np.where(parts == part)
        if len(xx) == 0:
            continue
        x0, y0, x1, y1 = (
            int(xx.min()),
            int(yy.min()),
            int(xx.max()) + 1,
            int(yy.max()) + 1,
        )
        stone_parts.append((y0, x0, x1, y1, parts[y0:y1, x0:x1] == part))
for index, (y0, x0, x1, y1, pixels) in enumerate(
    sorted(stone_parts, key=lambda item: (item[0], item[1]))
):
    id = f"wall-source-stone-{index:04}"
    Image.fromarray((pixels * 255).astype("uint8")).save(OUT / f"{id}.png")
    regions.append(
        dict(
            id=id,
            category="source-masonry-fragment",
            label=f"Source masonry surface fragment {index+1}",
            priority=5,
            shape=dict(
                type="mask",
                src=f"masks/scene/{id}.png",
                bounds=[x0, y0, x1 - x0, y1 - y0],
            ),
            tags=[
                "source-seam-derived",
                "visible-source-only",
                "masonry-fragment-not-whole-brick",
            ],
            note="Source blue-surface component seeds; inverse-brightness watershed follows dark mortar; remaining mortar assigned to nearest source surface. Dark NW top-course seeds manually checked. Boundaries are irregular source-derived estimates, not a regular cell grid. Texture and foliage may split a single original brick into several visible fragments; this ID does not assert one complete brick. Higher object/foliage/UI masks own overlapping pixels; occluded stone is not restored.",
        )
    )
# Independently checked source mortar landmark rows consolidate texture pieces
# into physical brick components. A brick can contain disconnected visible
# patches around foreground objects; higher-priority object masks clip those.
landmark_path = ROOT / "Docs/ConceptReconstruction/brick-landmarks.json"
if landmarks:
    mapped_bricks = Image.new("L", (1536, 1024))
    for zone in landmarks["zones"]:
        for row_index, row in enumerate(zone.get("rows", [])):
            for brick_index, (x0, x1) in enumerate(zip(row["seams"], row["seams"][1:])):
                y0, y1 = row["y0"], row["y1"]
                brick_id = f"brick-{zone['id']}-r{row_index:02}-b{brick_index:02}"
                mask = world.crop((x0, y0, x1, y1))
                if not mask.getbbox():
                    continue
                mapped_bricks.paste(mask, (x0, y0))
                mask.save(OUT / f"{brick_id}.png")
                regions.append(
                    dict(
                        id=brick_id,
                        category="wall-brick",
                        label=f"{zone['id']} physical brick row {row_index + 1} stone {brick_index + 1}",
                        priority=7,
                        shape=dict(
                            type="mask",
                            src=f"masks/scene/{brick_id}.png",
                            bounds=[x0, y0, x1 - x0, y1 - y0],
                        ),
                        tags=["source-mortar-landmark", "physical-brick", zone["id"]],
                        note="Independently checked source mortar landmarks group texture fragments into the same visible physical brick. Foreground props and UI own overlapping pixels. Disconnected source-visible patches remain one component; no hidden stone is filled.",
                    )
                )

    # Suppress obsolete texture partitions beneath consolidated physical bricks;
    # retain only truly unmapped source masonry pieces for review, not duplicate
    # invisible nodes that would inflate the component inventory.
    consolidated = []
    for region in regions:
        if region["category"] != "source-masonry-fragment":
            consolidated.append(region)
            continue
        shape = region["shape"]
        x0, y0, width, height = shape["bounds"]
        old_mask = Image.open(OUT / Path(shape["src"]).name).convert("L")
        remainder = ImageChops.subtract(
            old_mask, mapped_bricks.crop((x0, y0, x0 + width, y0 + height))
        )
        if remainder.getbbox():
            remainder.save(OUT / Path(shape["src"]).name)
            consolidated.append(region)
    regions = consolidated

# Connected wall capstones have deliberate source landmark boundaries, distinct
# from the darker blue brick faces. Priority only supersedes masonry ownership.
capstone_rows = [
    ("southwest-room-rim", 661, 689, [319, 362, 408, 460, 504, 551]),
    ("southeast-room-rim", 661, 689, [1072, 1116, 1157, 1194, 1231]),
    ("south-step-rim", 706, 734, [974, 1017, 1060]),
    ("south-low-rim", 762, 788, [903, 947, 974]),
]
for name, y0, y1, joints in capstone_rows:
    for i, (x0, x1) in enumerate(zip(joints, joints[1:])):
        rect(
            f"{name}-capstone-{i+1}",
            "wall-capstone",
            [x0, y0, x1 - x0, y1 - y0],
            6,
            "Manually checked visible capstone joint landmarks; cropped source face and edge, with no occluded continuation.",
        )
for name, x0, x1, joints in [
    ("west-channel-rim", 35, 70, [263, 309, 361, 406, 453, 498, 542, 589, 643]),
    ("east-channel-rim", 1444, 1482, [308, 361, 406, 453, 499, 544, 589, 644, 688]),
]:
    for i, (y0, y1) in enumerate(zip(joints, joints[1:])):
        rect(
            f"{name}-capstone-{i+1}",
            "wall-capstone",
            [x0, y0, x1 - x0, y1 - y0],
            6,
            "Manually checked visible stacked capstone joints; source crop only.",
        )
# Floor slabs use source mortar boundaries, clipped to the irregular room footprint.
xs = [319, 384, 461, 552, 644, 728, 811, 899, 974, 1061, 1155, 1216, 1231]
ys = [179, 220, 295, 369, 446, 518, 588, 661, 730, 787]
for j, (y0, y1) in enumerate(zip(ys, ys[1:])):
    for i, (x0, x1) in enumerate(zip(xs, xs[1:])):
        m = raster(arena).crop((x0, y0, x1, y1))
        if not m.getbbox():
            continue
        id = f"floor-slab-r{j:02}-c{i:02}"
        m.save(OUT / f"{id}.png")
        regions.append(
            dict(
                id=id,
                category="floor-slab",
                label=f"Room floor slab row {j+1} column {i+1}",
                priority=10,
                shape=dict(
                    type="mask",
                    src=f"masks/scene/{id}.png",
                    bounds=[x0, y0, x1 - x0, y1 - y0],
                ),
                tags=["source-visible-only", "occluded"],
                note="Mortar-bounded visible slab; overlapping props/actors/effects have higher ownership. Occluded pixels unavailable.",
            )
        )
# Flowing channels split at stone crossings and changes in channel direction.
for ci, ch in enumerate(channels):
    for n, (y0, y1) in enumerate(
        zip(
            [173, 220, 267, 309, 358, 416, 465, 503, 550, 600, 660, 714, 766],
            [220, 267, 309, 358, 416, 465, 503, 550, 600, 660, 714, 766, 832],
        )
    ):
        m = raster(ch).crop((0, y0, 1536, y1))
        bb = m.getbbox()
        if not bb:
            continue
        x0, _, x1, _ = bb
        m = m.crop((x0, 0, x1, y1 - y0))
        id = f"water-channel-{ci+1}-flow-{n:02}"
        m.save(OUT / f"{id}.png")
        regions.append(
            dict(
                id=id,
                category="water-channel",
                label=id.replace("-", " "),
                priority=20,
                shape=dict(
                    type="mask",
                    src=f"masks/scene/{id}.png",
                    bounds=[x0, y0, x1 - x0, y1 - y0],
                ),
                tags=["water", "reflection", "visible-source"],
            )
        )
# Editable source-traced perimeter corrections supersede approximate arena cells.
for correction in architecture_data["regions"]:
    if "points" in correction:
        poly(correction["id"], correction["category"], correction["points"], 40,
             "Source-traced visible architecture at the arena boundary; no hidden surface inference.")
    else:
        rect(correction["id"], correction["category"], correction["bounds"], 40,
             "Source-traced visible architecture at the arena boundary; no hidden surface inference.")
# Door assembly, staircase and individual frame pieces.
for id, b in [
    ("exit-left-column", [899, 0, 46, 184]),
    ("exit-right-column", [1080, 0, 51, 185]),
    ("exit-lintel", [943, 0, 137, 32]),
    ("exit-left-hazard-base", [898, 153, 47, 42]),
    ("exit-right-hazard-base", [1080, 153, 53, 44]),
    ("exit-stairs", [946, 33, 131, 105]),
    ("exit-threshold-grille", [963, 139, 104, 58]),
    ("exit-upper-light", [987, 0, 50, 29]),
    ("exit-left-frame-rail", [939, 29, 23, 153]),
    ("exit-right-frame-rail", [1065, 29, 21, 154]),
]:
    rect(id, "exit-architecture", b, 35)
poly(
    "exit-direction-arrow",
    "ground-pointer",
    [
        (1009, 137),
        (1033, 160),
        (1024, 161),
        (1024, 190),
        (1003, 190),
        (1003, 161),
        (992, 161),
    ],
    72,
)
poly(
    "west-drain-upper-elbow-outline",
    "pipe-joint",
    [
        (80, 159),
        (80, 151),
        (84, 143),
        (92, 138),
        (102, 137),
        (111, 141),
        (118, 148),
        (120, 160),
        (111, 165),
        (110, 154),
        (106, 148),
        (100, 146),
        (94, 150),
        (92, 159),
    ],
    48,
    "Manually traced visible upper pipe elbow arch; separates gold metal edging from source masonry above/behind the outlet.",
)
# Targeted source-boundary corrections from native-scale final QA.
# North riser side handle extends left of its original main tube rectangle.
poly(
    "north-pipe-b-side-handle",
    "pipe-joint",
    [
        (410, 47),
        (416, 43),
        (425, 43),
        (426, 51),
        (423, 56),
        (423, 79),
        (419, 88),
        (410, 87),
        (407, 80),
        (407, 55),
    ],
    48,
    "Native-source traced metal side handle; owns gold/dark metal previously left in the adjacent brick. Parent is north pipe B joint.",
)
regions[-1]["parentId"] = "north-pipe-b-segment-02"
poly(
    "north-pipe-b-mounting-plate",
    "pipe-joint",
    [
        (396, 48),
        (406, 48),
        (409, 53),
        (409, 82),
        (407, 87),
        (396, 87),
        (394, 83),
        (394, 53),
    ],
    48,
    "Native-source review identifies this dark rectangular piece with gold bolts/rim as the pipe mounting plate, distinct from the blue masonry behind it.",
)
regions[-1]["parentId"] = "north-pipe-b-segment-02"
# East drain has an exposed horizontal branch under its crate. Its straight
# tube and collars are separate source pieces rather than a wall crop.
for pipe_id, bounds in [
    ("east-drain-horizontal-left-collar", [1355, 493, 20, 32]),
    ("east-drain-horizontal-left-tube", [1375, 494, 22, 29]),
    ("east-drain-horizontal-mid-collar", [1397, 492, 22, 34]),
    ("east-drain-horizontal-right-tube", [1419, 494, 17, 29]),
    ("east-drain-horizontal-right-collar", [1436, 492, 12, 34]),
]:
    rect(
        pipe_id,
        "pipe-joint" if "collar" in pipe_id else "pipe-tube",
        bounds,
        48,
        "Native-source landmarks follow exposed east drain horizontal metal branch; no gold-lit stone is classified by a broad color predicate.",
    )
    regions[-1]["parentId"] = "east-drain-segment-01"

poly(
    "east-drain-outer-elbow-casing",
    "pipe-joint",
    [
        (1310, 520),
        (1310, 505),
        (1315, 491),
        (1324, 479),
        (1336, 475),
        (1348, 480),
        (1358, 491),
        (1365, 509),
        (1365, 529),
        (1358, 541),
        (1352, 546),
        (1351, 522),
        (1346, 513),
        (1335, 511),
        (1327, 516),
        (1323, 526),
        (1323, 550),
        (1314, 542),
    ],
    48,
    "Native-source traced outer curved drain casing and two lower brackets. Inner flowing-water mouth remains outside the traced metal contour.",
)
regions[-1]["parentId"] = "east-drain-segment-01"

# Each pipe has distinct straight runs, collars, end mouths and valve/control boxes.
for prefix, items in {
    "west-drain": [
        (82, 150, 33, 37),
        (87, 182, 24, 38),
        (81, 215, 35, 18),
        (88, 231, 23, 38),
    ],
    "north-pipe-a": [
        (357, 0, 35, 69),
        (351, 68, 47, 43),
        (363, 108, 27, 44),
        (351, 151, 50, 49),
    ],
    "north-pipe-b": [(429, 0, 27, 53), (422, 51, 42, 39)],
    "north-pipe-c": [
        (589, 0, 28, 79),
        (582, 76, 40, 20),
        (591, 95, 25, 38),
        (583, 132, 38, 39),
    ],
    "north-pipe-d": [
        (625, 0, 32, 40),
        (619, 37, 45, 24),
        (631, 61, 26, 94),
        (624, 154, 40, 27),
    ],
    "west-lower-pipe": [
        (286, 410, 31, 34),
        (287, 443, 23, 39),
        (282, 480, 35, 22),
        (289, 501, 22, 65),
    ],
    "west-bottom-pipe": [(272, 576, 38, 26), (277, 602, 26, 45), (274, 646, 33, 30)],
    "southwest-wall-pipe": [(77, 531, 33, 44), (82, 575, 21, 67)],
    "east-upper-pipe": [
        (1396, 104, 31, 65),
        (1395, 164, 45, 57),
        (1433, 188, 36, 35),
        (1468, 219, 68, 31),
    ],
    "east-mid-pipe": [
        (1492, 279, 44, 30),
        (1494, 310, 23, 53),
        (1482, 363, 39, 25),
        (1494, 389, 23, 70),
        (1484, 458, 52, 36),
    ],
    "southeast-pipe": [
        (1234, 599, 28, 63),
        (1235, 715, 37, 32),
        (1269, 718, 40, 26),
        (1308, 715, 39, 31),
        (1347, 719, 35, 25),
        (1380, 702, 35, 42),
        (1385, 744, 24, 88),
    ],
    "east-drain": [(1315, 477, 47, 37), (1323, 513, 28, 22)],
}.items():
    for i, b in enumerate(items):
        rect(
            f"{prefix}-segment-{i+1:02}",
            "pipe-joint" if i % 2 == 0 else "pipe-tube",
            list(b),
            40,
        )
for id, b in [
    ("north-control-power", [465, 28, 65, 151]),
    ("north-control-switches", [422, 94, 39, 84]),
    ("north-control-meter", [530, 57, 40, 120]),
    ("north-small-relay", [765, 15, 30, 117]),
    ("north-relay-foot", [762, 129, 38, 47]),
]:
    rect(id, "machine-panel", b, 42)
for id, b in [
    ("west-arched-water-outlet", [121, 90, 90, 105]),
    ("east-arched-water-outlet", [1237, 97, 63, 73]),
    ("west-floor-grate", [319, 516, 63, 66]),
    ("east-floor-grate", [1102, 298, 96, 70]),
    ("south-floor-grate", [730, 590, 79, 65]),
    ("west-crate-upper", [79, 314, 82, 52]),
    ("west-crate-lower", [81, 367, 79, 44]),
    ("west-tall-grate", [74, 468, 53, 99]),
    ("west-grate-base", [78, 567, 53, 41]),
    ("east-crate-upper", [1363, 253, 73, 60]),
    ("east-crate-under", [1368, 313, 63, 41]),
    ("east-crate-lower", [1363, 433, 68, 62]),
    ("east-lower-grate", [1365, 493, 60, 57]),
    ("south-crate-upper", [554, 687, 42, 45]),
    ("south-crate-lower", [555, 731, 40, 32]),
]:
    rect(
        id,
        (
            "grate"
            if "grate" in id
            else "crate" if "crate" in id else "water-outlet-frame"
        ),
        b,
        45,
    )
for id, pts in [
    (
        "west-waterfall",
        [
            (151, 134),
            (176, 133),
            (179, 206),
            (195, 228),
            (181, 246),
            (143, 248),
            (128, 233),
            (148, 207),
        ],
    ),
    (
        "east-waterfall",
        [
            (1260, 121),
            (1281, 122),
            (1280, 185),
            (1294, 199),
            (1274, 217),
            (1251, 206),
            (1254, 189),
        ],
    ),
    (
        "southeast-waterfall",
        [
            (1329, 522),
            (1352, 522),
            (1350, 584),
            (1377, 611),
            (1355, 637),
            (1321, 628),
            (1303, 615),
            (1325, 588),
        ],
    ),
]:
    poly(id, "waterfall", pts, 65)
# Leaf clusters are bounded by foliage silhouettes, not a rectangular replacement backdrop.
for id, pts in [
    (
        "west-vine",
        [
            (19, 89),
            (48, 92),
            (49, 122),
            (62, 138),
            (43, 173),
            (41, 212),
            (27, 250),
            (6, 248),
            (14, 203),
            (12, 165),
            (22, 135),
            (10, 116),
        ],
    ),
    (
        "west-door-vine",
        [
            (229, 77),
            (262, 81),
            (270, 103),
            (249, 126),
            (255, 150),
            (237, 176),
            (218, 168),
            (232, 131),
            (222, 112),
        ],
    ),
    (
        "north-center-vine",
        [
            (697, 0),
            (747, 0),
            (764, 34),
            (743, 58),
            (749, 91),
            (732, 127),
            (739, 160),
            (718, 171),
            (715, 131),
            (700, 99),
            (710, 69),
            (693, 40),
        ],
    ),
    ("north-switch-vine", [(539, 0), (569, 0), (564, 25), (546, 43), (531, 31)]),
    (
        "west-crate-vine",
        [
            (167, 303),
            (194, 310),
            (212, 336),
            (204, 364),
            (185, 383),
            (168, 370),
            (176, 347),
        ],
    ),
    (
        "west-middle-vine",
        [
            (83, 418),
            (125, 419),
            (155, 444),
            (148, 477),
            (159, 513),
            (137, 535),
            (121, 505),
            (128, 472),
            (105, 459),
            (81, 467),
        ],
    ),
    (
        "west-floor-vine",
        [(340, 377), (369, 391), (370, 420), (351, 448), (335, 431), (340, 407)],
    ),
    (
        "west-bottom-vine",
        [(175, 554), (207, 562), (225, 591), (213, 616), (185, 604), (179, 581)],
    ),
    (
        "southwest-vine",
        [(119, 685), (146, 690), (155, 715), (143, 750), (125, 744), (130, 719)],
    ),
    (
        "south-crate-vine",
        [(625, 740), (653, 742), (672, 771), (661, 806), (639, 796), (648, 772)],
    ),
    (
        "southeast-floor-vine",
        [
            (1007, 634),
            (1039, 631),
            (1067, 649),
            (1068, 676),
            (1045, 693),
            (1018, 681),
            (1000, 660),
        ],
    ),
    (
        "east-upper-vine",
        [
            (1340, 112),
            (1374, 114),
            (1373, 149),
            (1383, 175),
            (1373, 211),
            (1355, 225),
            (1348, 197),
            (1354, 171),
            (1339, 148),
        ],
    ),
    (
        "east-wall-vine",
        [(1405, 372), (1432, 380), (1440, 414), (1422, 438), (1402, 427), (1411, 402)],
    ),
    (
        "east-floor-vine",
        [(1205, 415), (1235, 422), (1239, 460), (1223, 483), (1208, 469), (1214, 444)],
    ),
    (
        "east-bottom-vine",
        [
            (1494, 542),
            (1528, 553),
            (1534, 580),
            (1514, 612),
            (1515, 642),
            (1534, 666),
            (1523, 702),
            (1501, 684),
            (1497, 652),
            (1483, 631),
            (1496, 602),
        ],
    ),
    (
        "southeast-wall-vine",
        [
            (1447, 694),
            (1479, 703),
            (1487, 735),
            (1467, 766),
            (1472, 803),
            (1451, 825),
            (1437, 803),
            (1445, 773),
            (1434, 741),
        ],
    ),
]:
    poly(id, "vines", pts, 52)
# Actors: manually traced visible silhouettes preserve open negative-space gaps.
actors = {key: value["outer"] for key, value in silhouette_data["actors"].items()}
for id, pts in actors.items():
    # Remove blue stone/shadow negative spaces inside a traced outer contour.
    # This local chromatic test retains warm bodies, purple hair, neutral armor,
    # and Mongo's brighter blue head. It cannot infer occluded anatomy.
    source_rgb = np.asarray(
        Image.open(
            ROOT / "Web/wwwroot/assets/broadcast-kit/combat-concept.png"
        ).convert("RGB")
    ).astype(float)
    rr, gg, bb = source_rgb[:, :, 0], source_rgb[:, :, 1], source_rgb[:, :, 2]
    floor_chroma = (gg > rr * 1.18) & (bb > rr * 1.22) & (bb < 165) & (gg > 25)
    traced = np.asarray(raster(pts)) > 0
    if id == "mongo":
        # Blue head is a saturated actor feature, not the muted stone substrate.
        floor_chroma[286:317, 970:1017] = False
    for addition in silhouette_data["actors"][id].get("additions", []):
        traced |= np.asarray(raster(addition)) > 0
    body = traced & ~floor_chroma
    if id == "rat-target":
        # Magenta selection substrate is distinct from warm pink feet/tail.
        body &= ~((rr > gg * 1.5) & (bb > gg * 1.18) & (bb > 35))
        protected_red = np.zeros(body.shape, dtype=bool)
        protected_red[494:537, 835:873] = True  # visible tail
        protected_red[522:553, 769:829] = True  # visible pink feet
        protected_red[490:514, 751:784] = True  # eye and nose
        body &= ~((rr > gg * 1.8) & (rr > bb * 1.3) & ~protected_red)
    if id == "carl":
        # Native 10x foot inspection: the selected yellow cell is not blue,
        # so the general negative-space chroma test cannot remove its wedges.
        # Replace only y>=512 with traced bare lower-leg/foot outlines.
        left_foot = [
            (482, 510),
            (494, 513),
            (501, 513),
            (498, 518),
            (494, 521),
            (490, 526),
            (485, 531),
            (485, 533),
            (487, 536),
            (493, 538),
            (497, 541),
            (497, 544),
            (491, 547),
            (477, 547),
            (471, 545),
            (469, 541),
            (466, 539),
            (466, 534),
            (470, 530),
            (471, 524),
            (473, 519),
            (479, 515),
        ]
        right_foot = [
            (510, 509),
            (521, 508),
            (529, 504),
            (530, 510),
            (527, 516),
            (523, 520),
            (529, 523),
            (533, 524),
            (536, 527),
            (536, 531),
            (531, 533),
            (515, 533),
            (506, 532),
            (504, 529),
            (505, 523),
            (508, 519),
            (510, 515),
        ]
        feet = (np.asarray(raster(left_foot)) > 0) | (
            np.asarray(raster(right_foot)) > 0
        )
        body[512:552] = feet[512:552]
        # Visible selected-cell corners behind backpack/shorts are outside the
        # actor, as checked against the native x455..550/y480..515 grid.
        right_cell = raster(
            [
                (521, 486),
                (548, 486),
                (548, 512),
                (531, 512),
                (534, 504),
                (534, 499),
                (531, 495),
                (527, 492),
                (521, 490),
            ]
        )
        left_cell = raster(
            [
                (455, 486),
                (463, 486),
                (466, 493),
                (471, 497),
                (479, 501),
                (477, 507),
                (478, 512),
                (455, 512),
            ]
        )
        body[(np.asarray(right_cell) > 0) | (np.asarray(left_cell) > 0)] = False
        # Selection is near-neutral yellow (R/G<1.12); warm skin has a higher
        # ratio. Restrict this test to the traced feet, never backpack/armor.
        selected_yellow = (
            (rr < gg * 1.12) & (rr > gg * 0.85) & (gg > 50) & (bb < gg * 0.8)
        )
        body[512:552] &= ~selected_yellow[512:552]
        # The lit selection edge immediately outside the right shorts can be
        # warmer than the ground. Its x>=533/y486..511 location is beyond the
        # checked black shorts outline, so discard only its bright yellow pixels.
        shorts_cell = (gg > 70) & (bb < gg * 0.8) & (rr > gg * 0.85)
        body[486:512, 533:] &= ~shorts_cell[486:512, 533:]
        traced = traced | feet
    ys_body, xs_body = np.where(traced)
    x0, y0, x1, y1 = (
        int(xs_body.min()),
        int(ys_body.min()),
        int(xs_body.max()) + 1,
        int(ys_body.max()) + 1,
    )
    Image.fromarray((body[y0:y1, x0:x1] * 255).astype("uint8")).save(
        OUT / f"{id}-body.png"
    )
    regions.append(
        dict(
            id=id + "-body",
            category="actor-body",
            label=id + " visible body partition (combine actor-edge children)",
            priority=85,
            shape=dict(
                type="mask",
                src=f"masks/scene/{id}-body.png",
                bounds=[x0, y0, x1 - x0, y1 - y0],
            ),
            tags=["source-visible-only", "color-assisted-negative-space"],
            note="Hand-traced outer contour with local blue stone/shadow chroma removed from internal negative spaces. Visible source cutout; no hidden anatomy. Fine antialiased outlines remain approximate.",
        )
    )
for id, b in [
    ("donut-hp", [420, 247, 64, 16]),
    ("katia-hp", [678, 212, 57, 15]),
    ("mongo-hp", [926, 251, 58, 16]),
    ("carl-hp", [484, 411, 56, 15]),
    ("rat-target-hp", [752, 427, 60, 15]),
    ("rat-east-hp", [1082, 417, 61, 15]),
    ("rat-south-hp", [867, 562, 61, 15]),
]:
    rect(id, "world-hp-bar", b, 90)
for id, b in [
    ("carl-selected-ground", [459, 487, 95, 73]),
    ("path-step-one", [545, 482, 72, 84]),
    ("path-step-two", [617, 482, 67, 84]),
    ("path-step-three", [684, 482, 66, 84]),
    ("donut-ground", [414, 291, 98, 76]),
    ("rat-target-ground", [733, 462, 119, 117]),
]:
    rect(
        id,
        "ground-highlight",
        b,
        70,
        "Source ground effect includes visible underlying floor; actor silhouette owns overlapping pixels. No invented clean alpha effect.",
    )
poly(
    "rat-target-chevron",
    "world-pointer",
    [
        (768, 444),
        (780, 452),
        (791, 442),
        (798, 448),
        (783, 465),
        (774, 462),
        (764, 451),
    ],
    95,
)
poly(
    "explosive-barrel",
    "prop",
    [
        (978, 554),
        (995, 549),
        (1018, 550),
        (1033, 558),
        (1035, 571),
        (1032, 591),
        (1037, 607),
        (1033, 635),
        (1020, 644),
        (990, 642),
        (973, 633),
        (972, 606),
        (976, 591),
        (971, 573),
    ],
    80,
)
for side, x in [("left", 854), ("right", 1140)]:
    poly(
        f"exit-{side}-torch-flame",
        "torch-flame",
        [
            (x + 7, 62),
            (x + 16, 81),
            (x + 23, 71),
            (x + 30, 94),
            (x + 33, 115),
            (x + 25, 126),
            (x + 8, 127),
            (x, 117),
            (x + 2, 93),
        ],
        64,
    )
    rect(f"exit-{side}-torch-bracket", "torch-bracket", [x, 119, 37, 28], 62)
# Narrow stone/void backdrop pieces below the HUD are source artwork, not a full-scene fallback.
for i, x in enumerate(range(0, 1536, 96)):
    rect(f"lower-void-rock-{i:02}", "void-rock", [x, 980, min(96, 1536 - x), 44], 4)
# Color-assisted source-edge masks: source-derived fringes which extend beyond
# the manually traced silhouettes. Thresholds are local to each semantic object;
# no background fill or hidden pixel recovery occurs. Dark outline pixels are
# admitted only within two pixels of a saturated subject-color seed.
source = Image.open(
    ROOT / "Web/wwwroot/assets/broadcast-kit/combat-concept.png"
).convert("RGB")


def color_edge(id, parent, cat, bounds, kind, priority):
    x, y, w, h = bounds
    crop = source.crop((x, y, x + w, y + h))
    rgb = np.asarray(crop).astype(float)
    r, g, b = rgb[:, :, 0], rgb[:, :, 1], rgb[:, :, 2]
    if kind == "purple":
        seed = (r > 45) & (b > 65) & (b > g * 1.65) & (r > g * 1.45) & (b > r * 0.9)
    elif kind == "red":
        seed = (r > 75) & (r > g * 1.7) & (r > b * 1.3)
    elif kind == "green":
        seed = (g > 30) & (g > r * 1.18) & (g > b * 1.03)
    elif kind == "cyan":
        seed = (g > 110) & (b > 125) & (g > r * 1.48) & (b > r * 1.5)
    seedmask = Image.fromarray((seed * 255).astype("uint8"))
    if cat == "actor-edge":
        nearby = np.asarray(seedmask.filter(ImageFilter.MaxFilter(5))) > 0
        dark = (r < 48) & (g < 43) & (b < 63)
        seed = seed | (nearby & dark)
    mask = Image.fromarray((seed * 255).astype("uint8"))
    mask.save(OUT / f"{id}.png")
    regions.append(
        dict(
            id=id,
            parentId=parent,
            category=cat,
            label=id.replace("-", " "),
            priority=priority,
            shape=dict(type="mask", src=f"masks/scene/{id}.png", bounds=bounds),
            tags=["source-color-assisted", "visible-edge-only"],
            note=(
                "Local source RGB predicate; binary mask preserves original RGB. Color edge ownership is inferred from adjacent visible subject color; no unseen pixels are fabricated. Dark outline restricted to two pixels from saturated actor color seed."
                if cat == "actor-edge"
                else "Local source RGB predicate separates visible saturated effect pixels from floor; source includes original blended glow colors, not recovered independent alpha."
            ),
        )
    )


color_edge(
    "katia-purple-hair-edge",
    "katia-body",
    "actor-edge",
    [632, 228, 111, 104],
    "purple",
    86,
)
color_edge(
    "mongo-red-feather-edge",
    "mongo-body",
    "actor-edge",
    [838, 272, 158, 100],
    "red",
    86,
)
color_edge(
    "route-cyan-border-fringe",
    "path-step-one",
    "ground-effect-edge",
    [544, 477, 205, 92],
    "cyan",
    75,
)
color_edge(
    "target-red-glow-fringe",
    "rat-target-ground",
    "ground-effect-edge",
    [731, 463, 119, 116],
    "red",
    75,
)
# All authored foliage clusters receive their own bounded source-color fringe
# pass so neighboring wall bricks retain no obvious saturated leaf spill.
for vine_region in list(regions):
    if vine_region["category"] != "vines":
        continue
    points = vine_region["shape"]["points"]
    x0 = max(0, min(p[0] for p in points) - 5)
    y0 = max(0, min(p[1] for p in points) - 5)
    x1 = min(1536, max(p[0] for p in points) + 6)
    y1 = min(832, max(p[1] for p in points) + 6)
    color_edge(
        vine_region["id"] + "-leaf-fringe",
        vine_region["id"],
        "vine-edge",
        [x0, y0, x1 - x0, y1 - y0],
        "green",
        53,
    )

color_edge(
    "east-bottom-vine-edge",
    "east-bottom-vine",
    "vine-edge",
    [1482, 540, 54, 177],
    "green",
    53,
)
# Outer exposed rock beside the beveled bottom HUD.
for side, x, w in [("left", 0, 23), ("right", 1510, 26)]:
    for i, y in enumerate(range(832, 980, 37)):
        rect(
            f"hud-{side}-exterior-rock-{i}", "void-rock", [x, y, w, min(37, 980 - y)], 4
        )
# Surface reflections and actor contact shadows are separate source-visible pieces.
for id, pts in [
    (
        "north-gold-reflection",
        [(495, 190), (516, 189), (535, 221), (521, 250), (496, 247), (485, 220)],
    ),
    (
        "exit-gold-reflection",
        [(991, 195), (1035, 197), (1047, 230), (1033, 260), (1008, 275), (988, 246)],
    ),
    (
        "middle-gold-reflection",
        [(930, 449), (960, 450), (972, 489), (961, 516), (938, 516), (924, 481)],
    ),
    (
        "south-gold-reflection",
        [(836, 665), (875, 669), (892, 698), (881, 723), (851, 729), (830, 709)],
    ),
    ("northwest-puddle", [(386, 224), (418, 223), (438, 251), (428, 286), (391, 290)]),
    (
        "midwest-puddle",
        [(558, 373), (601, 372), (635, 398), (631, 438), (579, 442), (556, 423)],
    ),
    (
        "southwest-puddle",
        [(649, 593), (691, 592), (723, 618), (720, 652), (659, 656), (645, 635)],
    ),
    (
        "southeast-puddle",
        [(1166, 594), (1208, 591), (1223, 617), (1214, 655), (1171, 657), (1159, 635)],
    ),
]:
    poly(
        id,
        "floor-reflection",
        pts,
        23,
        "Source reflection/puddle patch retains its visible stone substrate; not a fabricated translucent overlay.",
    )
# Landmark bricks supersede any earlier capstone rectangle in their footprint.
# Keep only independently visible capstone portions beyond the new map.
if landmarks:
    retained_regions = []
    for region in regions:
        if region["category"] != "wall-capstone" or region["priority"] >= 40:
            retained_regions.append(region)
            continue
        x, y, width, height = region["shape"]["bounds"]
        remaining = ImageChops.subtract(
            Image.new("L", (width, height), 255),
            mapped_bricks.crop((x, y, x + width, y + height)),
        )
        if not remaining.getbbox():
            continue
        capstone_id = region["id"]
        remaining.save(OUT / f"{capstone_id}.png")
        region["shape"] = dict(
            type="mask",
            src=f"masks/scene/{capstone_id}.png",
            bounds=[x, y, width, height],
        )
        retained_regions.append(region)
    regions = retained_regions

DOC = args.regions_output
DOC.parent.mkdir(parents=True, exist_ok=True)
DOC.write_text(
    json.dumps(dict(schemaVersion=1, canvas=[1536, 1024], regions=regions), indent=2)
    + "\n"
)
referenced = {
    r["shape"]["src"].split("/")[-1] for r in regions if r["shape"]["type"] == "mask"
}
for stale in OUT.glob("*.png"):
    if stale.name not in referenced:
        stale.unlink()
print(f"Wrote {len(regions)} semantic world regions to {DOC}")
