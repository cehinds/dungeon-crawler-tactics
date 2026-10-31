#!/usr/bin/env python3
"""Author visible UI pieces from the flattened reference; never invent hidden pixels.
Text masks retain source RGB via compositor; font metadata is descriptive only.
"""

import json
import argparse
from pathlib import Path
import numpy as np
from PIL import Image, ImageFilter

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("--output", type=Path, default=ROOT / "Web/wwwroot/assets/concept-reconstruction/masks/ui")
parser.add_argument("--regions-output", type=Path, default=ROOT / "Docs/ConceptReconstruction/ui-regions.json")
args = parser.parse_args()
MASK_OUT = args.output
SOURCE = ROOT / "Web/wwwroot/assets/broadcast-kit/combat-concept.png"
im = Image.open(SOURCE).convert("RGB")
MASK_OUT.mkdir(parents=True, exist_ok=True)
regions = []


def rect(id, cat, label, b, p=100, parent=None, **kw):
    d = dict(
        id=id, category=cat, label=label, priority=p, shape=dict(type="rect", bounds=b)
    )
    d.update(kw)
    if parent:
        d["parentId"] = parent
    regions.append(d)
    return id


def poly(id, cat, label, pts, p=100, parent=None):
    d = dict(
        id=id,
        category=cat,
        label=label,
        priority=p,
        shape=dict(type="polygon", points=pts),
    )
    if parent:
        d["parentId"] = parent
    regions.append(d)
    return id


def txt(id, s, b, parent=None, mode="light", p=150):
    x, y, w, h = b
    a = np.array(im.crop((x, y, x + w, y + h)))
    r, g, bl = [a[:, :, i].astype(float) for i in range(3)]
    if mode == "dark":
        m = (r < 125) & (g < 120) & (bl < 100)
    elif mode == "red":
        m = (r > 110) & (r > g * 1.4) & (r > bl * 1.25)
    elif mode == "gold":
        m = (r > 125) & (g > 105) & (bl < g * 0.85)
    else:
        m = (
            (r > 105)
            & (g > 105)
            & (bl > 95)
            & ((np.maximum.reduce([r, g, bl]) - np.minimum.reduce([r, g, bl])) < 100)
        )
    mask = Image.fromarray((m * 255).astype("uint8")).filter(ImageFilter.MaxFilter(3))
    path = MASK_OUT / f"{id}.png"
    mask.save(path)
    d = dict(
        id=id,
        category="text",
        label=s,
        priority=p,
        shape=dict(type="mask", src=f"masks/ui/{id}.png", bounds=b),
        text=dict(
            value=s,
            confidence=1.0,
            fontApproximation="Condensed serif display; original font unavailable in flattened source",
            editableOriginal=False,
        ),
        tags=["source-visible-glyphs", "baked-antialiasing"],
        note="Contrast-isolated visible glyphs with one-pixel source edge fringe; no hidden glyph reconstruction.",
    )
    if parent:
        d["parentId"] = parent
    regions.append(d)


# Objective plaque, separate hanging lantern and text.
poly(
    "objective-frame",
    "ui-frame",
    "Objective gold perimeter",
    [
        [20, 32],
        [31, 28],
        [280, 28],
        [294, 34],
        [294, 75],
        [282, 82],
        [31, 81],
        [20, 74],
    ],
    100,
)
rect(
    "objective-body",
    "ui-panel",
    "Objective parchment face",
    [31, 35, 252, 39],
    110,
    "objective-frame",
)
rect(
    "objective-lantern",
    "ui-icon",
    "Lantern illustration and hanging loop",
    [41, 15, 44, 66],
    130,
    "objective-frame",
)
txt("objective-label", "OPEN THE EXIT", [104, 42, 170, 25], "objective-body", "dark")
poly(
    "phase-frame",
    "ui-frame",
    "Phase panel gold perimeter",
    [
        [1230, 25],
        [1516, 25],
        [1520, 31],
        [1520, 64],
        [1504, 79],
        [1497, 103],
        [1336, 103],
        [1324, 74],
        [1231, 71],
        [1227, 64],
        [1227, 33],
    ],
    100,
)
poly(
    "phase-body",
    "ui-panel",
    "Phase midnight panel",
    [
        [1234, 30],
        [1513, 30],
        [1515, 63],
        [1499, 76],
        [1494, 99],
        [1341, 99],
        [1328, 70],
        [1234, 67],
    ],
    110,
    "phase-frame",
)
txt("phase-party", "PARTY", [1249, 38, 69, 23], "phase-body", "gold")
txt("phase-label", "PHASE", [1323, 38, 64, 23], "phase-body")
txt("phase-dot", "•", [1396, 40, 11, 16], "phase-body")
txt("phase-round", "ROUND 2", [1416, 38, 86, 23], "phase-body")
for i, x in enumerate([1363, 1405, 1446]):
    poly(
        f"phase-diamond-{i+1}",
        "ui-indicator",
        f"Phase resource diamond {i+1}",
        [[x + 15, 64], [x + 30, 80], [x + 15, 96], [x, 80]],
        125,
        "phase-body",
    )
# Four initiative/party cards. Outer glow kept independently on selected Carl.
rect(
    "party-carl-glow", "ui-glow", "Selected Carl portrait glow", [11, 743, 122, 88], 100
)
for id, x, w in [
    ("carl", 18, 108),
    ("donut", 136, 122),
    ("katia", 271, 121),
    ("mongo", 404, 121),
]:
    parent = rect(
        f"party-{id}-frame",
        "ui-frame",
        f"{id.title()} party portrait frame",
        [x, 750, w, 77],
        110,
    )
    rect(
        f"party-{id}-body",
        "ui-panel",
        f"{id.title()} portrait dark backing",
        [x + 5, 756, w - 10, 65],
        115,
        parent,
    )
    rect(
        f"party-{id}-portrait",
        "ui-portrait",
        f"{id.title()} portrait artwork",
        [x + 7, 757, w - 20, 65],
        120,
        parent,
    )
    rect(
        f"party-{id}-marker",
        "ui-indicator",
        f"{id.title()} ready marker",
        [x + w - 23, 756, 17, 20],
        135,
        parent,
    )
# World actor HP bars (only the visible rectangles, no inferred values).
for id, b in [
    ("donut", [422, 248, 61, 14]),
    ("katia", [678, 212, 57, 14]),
    ("mongo", [926, 252, 59, 14]),
    ("carl", [485, 411, 55, 14]),
    ("rat-target", [752, 427, 59, 15]),
    ("rat-east", [1082, 418, 61, 15]),
    ("rat-south", [867, 562, 61, 15]),
]:
    x, y, w, h = b
    parent = rect(
        f"world-hp-{id}-outline", "world-ui-frame", f"{id} HP outline", b, 170
    )
    rect(
        f"world-hp-{id}-track",
        "world-ui-track",
        f"{id} HP dark track",
        [x + 2, y + 2, w - 4, h - 4],
        171,
        parent,
    )
    rect(
        f"world-hp-{id}-fill",
        "world-ui-fill",
        f"{id} HP visible fill",
        [x + 3, y + 3, w - 7, h - 7],
        172,
        parent,
    )
poly(
    "target-chevron",
    "world-ui-indicator",
    "Selected rat downward chevron",
    [
        [766, 442],
        [773, 442],
        [782, 451],
        [790, 442],
        [798, 442],
        [797, 450],
        [783, 464],
        [768, 451],
    ],
    185,
)
poly(
    "forecast-frame",
    "ui-frame",
    "Strike forecast gold balloon perimeter",
    [
        [828, 394],
        [991, 394],
        [1000, 402],
        [1000, 433],
        [991, 440],
        [853, 440],
        [816, 472],
        [836, 438],
        [820, 438],
        [816, 430],
        [816, 404],
    ],
    190,
)
poly(
    "forecast-body",
    "ui-panel",
    "Strike forecast navy balloon face",
    [
        [830, 399],
        [990, 399],
        [995, 404],
        [995, 431],
        [989, 436],
        [849, 436],
        [826, 459],
        [841, 435],
        [823, 433],
        [822, 405],
    ],
    191,
    "forecast-frame",
)
txt("forecast-strike", "Strike", [835, 405, 58, 25], "forecast-body", p=195)
txt("forecast-dot", "•", [898, 407, 10, 19], "forecast-body", p=195)
txt("forecast-mana", "2 Mana", [915, 405, 70, 25], "forecast-body", p=195)
# Bottom HUD chrome.
poly(
    "hud-frame",
    "ui-frame",
    "Full bottom HUD gold outer frame",
    [
        [22, 831],
        [1513, 831],
        [1523, 840],
        [1524, 969],
        [1513, 980],
        [22, 980],
        [12, 969],
        [12, 842],
    ],
    200,
)
rect(
    "hud-body",
    "ui-panel",
    "Bottom HUD navy face",
    [19, 838, 1498, 136],
    205,
    "hud-frame",
)
rect(
    "hud-carl-frame",
    "ui-frame",
    "Carl large portrait gold border",
    [26, 852, 112, 116],
    210,
    "hud-body",
)
rect(
    "hud-carl-backing",
    "ui-panel",
    "Carl large portrait blue backing",
    [32, 860, 98, 102],
    211,
    "hud-carl-frame",
)
rect(
    "hud-carl-portrait",
    "ui-portrait",
    "Carl large portrait visible artwork",
    [33, 859, 98, 104],
    212,
    "hud-carl-frame",
)
txt("hud-carl-name", "CARL", [150, 854, 68, 28], "hud-body", "gold", 220)
txt("hud-hp-label", "HP", [149, 888, 31, 24], "hud-body", p=220)
txt("hud-hp-value", "32 / 40", [212, 888, 74, 25], "hud-body", p=220)
txt("hud-mana-label", "Mana", [149, 930, 53, 25], "hud-body", p=220)
txt("hud-mana-value", "8 / 12", [214, 930, 60, 25], "hud-body", p=220)
for id, y, fill in [("hp", 913, 112), ("mana", 954, 92)]:
    parent = rect(
        f"hud-{id}-outline",
        "ui-frame",
        f"{id} bar outline",
        [213, y, 146, 13],
        215,
        "hud-body",
    )
    rect(
        f"hud-{id}-track",
        "ui-track",
        f"{id} bar dark track",
        [215, y + 2, 142, 9],
        216,
        parent,
    )
    rect(
        f"hud-{id}-fill",
        "ui-fill",
        f"{id} bar visible fill",
        [215, y + 2, fill, 9],
        217,
        parent,
    )
rect(
    "hud-stat-separator",
    "ui-separator",
    "Vertical status/movement separator",
    [374, 872, 2, 88],
    215,
    "hud-body",
)
rect(
    "hud-movement-boot",
    "ui-icon",
    "Movement boot icon",
    [390, 882, 59, 56],
    220,
    "hud-body",
)
txt("hud-movement-count", "4", [464, 883, 22, 32], "hud-body", p=220)
txt("hud-movement-label", "Move", [458, 924, 49, 26], "hud-body", p=220)
# Action controls: independently owned outer glow, border, panel, icon and label.
rect(
    "action-move-glow",
    "ui-glow",
    "Move active gold glow",
    [526, 844, 123, 127],
    218,
    "hud-body",
)
for id, x, w, label, ib, tb in [
    ("move", 534, 106, "Move", [560, 866, 55, 59], [558, 930, 59, 27]),
    ("strike", 652, 106, "Strike", [670, 866, 65, 57], [673, 930, 67, 26]),
    ("skills", 772, 107, "Skills", [792, 866, 60, 56], [791, 930, 68, 26]),
    ("items", 892, 108, "Items", [919, 868, 52, 57], [914, 930, 62, 26]),
]:
    parent = rect(
        f"action-{id}-frame",
        "ui-button-frame",
        f"{label} gold button border",
        [x, 853, w, 110],
        225,
        "hud-body",
    )
    rect(
        f"action-{id}-body",
        "ui-button-body",
        f"{label} dark button face",
        [x + 6, 860, w - 12, 96],
        226,
        parent,
    )
    rect(
        f"action-{id}-icon", "ui-icon", f"{label} action illustration", ib, 230, parent
    )
    txt(f"action-{id}-label", label, tb, parent, p=235)
# Target forecast card and end-turn button.
poly(
    "target-card-frame",
    "ui-frame",
    "Target forecast gold border",
    [
        [1033, 853],
        [1230, 853],
        [1242, 864],
        [1242, 944],
        [1232, 956],
        [1032, 956],
        [1020, 945],
        [1020, 864],
    ],
    225,
    "hud-body",
)
rect(
    "target-card-body",
    "ui-panel",
    "Target forecast navy face",
    [1026, 859, 209, 91],
    226,
    "target-card-frame",
)
rect(
    "target-card-portrait",
    "ui-portrait",
    "Rat target portrait",
    [1035, 871, 84, 76],
    230,
    "target-card-body",
)
rect(
    "target-card-separator",
    "ui-separator",
    "Rat portrait/text divider",
    [1118, 866, 2, 82],
    235,
    "target-card-body",
)
txt("target-card-name", "Rat", [1130, 879, 33, 23], "target-card-body", p=235)
txt(
    "target-card-damage-value",
    "12",
    [1128, 902, 31, 29],
    "target-card-body",
    "red",
    235,
)
txt(
    "target-card-damage-label", "damage", [1161, 908, 70, 23], "target-card-body", p=235
)
poly(
    "end-turn-frame",
    "ui-button-frame",
    "End turn gold perimeter",
    [
        [1267, 859],
        [1496, 859],
        [1505, 868],
        [1505, 931],
        [1495, 941],
        [1266, 941],
        [1255, 932],
        [1255, 870],
    ],
    225,
    "hud-body",
)
rect(
    "end-turn-body",
    "ui-button-body",
    "End turn parchment face",
    [1265, 869, 231, 63],
    226,
    "end-turn-frame",
)
txt(
    "end-turn-label",
    "End Carl’s turn",
    [1276, 886, 180, 32],
    "end-turn-body",
    "dark",
    235,
)
poly(
    "end-turn-arrow",
    "ui-icon",
    "End turn right-pointing arrow",
    [[1468, 887], [1488, 902], [1468, 918]],
    235,
    "end-turn-body",
)
# Isolate UI illustration silhouettes from their dark panel backgrounds.
# Threshold seeds locate visible colored artwork; one source-pixel fringe retains
# its black outline/AA. Holes are retained unless enclosed inside solid artwork.
from scipy.ndimage import binary_fill_holes

for region in regions:
    if region["category"] != "ui-icon" or region["id"] == "objective-lantern":
        continue
    if region["shape"]["type"] != "rect":
        continue
    x, y, w, h = region["shape"]["bounds"]
    a = np.array(im.crop((x, y, x + w, y + h)))
    seed = np.max(a, axis=2) > 68
    mask = Image.fromarray((seed * 255).astype("uint8")).filter(
        ImageFilter.MaxFilter(3)
    )
    if region["id"] in ["hud-movement-boot", "action-items-icon"]:
        mask = Image.fromarray(
            (binary_fill_holes(np.array(mask) > 0) * 255).astype("uint8")
        )
    path = MASK_OUT / f"{region['id']}.png"
    mask.save(path)
    region["shape"] = dict(
        type="mask", src=f"masks/ui/{region['id']}.png", bounds=[x, y, w, h]
    )
    region["note"] = "Visible illustration silhouette with original baked edge RGB."
# Portrait artwork is independently masked from the authored blue backing.
for region in regions:
    if region["category"] != "ui-portrait":
        continue
    x, y, w, h = region["shape"]["bounds"]
    a = np.array(im.crop((x, y, x + w, y + h))).astype(float)
    # Navy backing is blue-dominant; neutral fur, warm skin/hair, magenta hair,
    # cyan feathers and bright eyes are source foreground seeds.
    r, g, bl = a[:, :, 0], a[:, :, 1], a[:, :, 2]
    seed = (np.max(a, axis=2) > 72) & ((r > bl * 0.8) | (g > bl * 0.92) | (r > 80))
    if region["id"] == "party-mongo-portrait":
        seed = np.max(a, axis=2) > 72
    mask = Image.fromarray((seed * 255).astype("uint8")).filter(
        ImageFilter.MaxFilter(3)
    )
    mask = Image.fromarray(
        (binary_fill_holes(np.array(mask) > 0) * 255).astype("uint8")
    )
    if region["id"] == "party-carl-portrait":
        clip = Image.new("L", (w, h))
        from PIL import ImageDraw

        ImageDraw.Draw(clip).polygon(
            [
                (9, 0),
                (76, 0),
                (84, 13),
                (83, 26),
                (74, 34),
                (73, 49),
                (85, 64),
                (5, 64),
                (8, 48),
                (7, 33),
                (3, 18),
            ],
            fill=255,
        )
        mask = Image.fromarray(np.minimum(np.array(mask), np.array(clip)))
        ma = np.array(mask)
        gold = (r > 160) & (g > 125) & (g > r * 0.72) & (bl < g * 0.7)
        yy, xx = np.indices((h, w))
        edge = (yy < 8) | (yy > 57) | (xx < 10)
        ma[gold & edge] = 0
        ma[(yy < 5) & (g > 80) & (g > bl * 1.6)] = 0
        # Teal backing is excluded even when captured as a one-pixel dilation fringe.
        ma[(bl > r * 1.1) & (g > r * 1.1) & (r < 100)] = 0
        ma[:, 0:3] = 0
        ma[-2:, :] = 0
        ma[:5, :22] = 0
        ma[:3, 65:] = 0
        ma[(xx < 12) & (yy > 53) & (g > bl * 1.5) & (g > r * 0.65)] = 0
        mask = Image.fromarray(ma)
    if region["id"] == "hud-carl-portrait":
        # Remove isolated bright frame-corner fragments, outside the head silhouette.
        ma = np.array(mask)
        ma[:6, :9] = 0
        ma[:7, -12:] = 0
        mask = Image.fromarray(ma)
    if region["id"].startswith("party-"):
        marker = next(
            v
            for v in regions
            if v["id"] == region["id"].replace("-portrait", "-marker")
        )
        mx, my, mw, mh = marker["shape"]["bounds"]
        ma = np.array(mask)
        ma[
            max(0, my - y) : max(0, min(h, my + mh - y)),
            max(0, mx - x) : max(0, min(w, mx + mw - x)),
        ] = 0
        mask = Image.fromarray(ma)
    mask.save(MASK_OUT / f"{region['id']}.png")
    region["shape"] = dict(
        type="mask", src=f"masks/ui/{region['id']}.png", bounds=[x, y, w, h]
    )
    region["note"] = (
        "Visible portrait foreground isolated from navy backing; source black edge retained. Boundary silhouette is a source-cutout approximation: ambiguous one-pixel frame/art blends stay original RGB and may be assigned to backing."
    )
# Lantern crosses both parchment and world; hand-traced silhouette excludes both.
from PIL import ImageDraw

lantern = next(v for v in regions if v["id"] == "objective-lantern")
b = [41, 15, 44, 66]
m = Image.new("L", (44, 66))
ImageDraw.Draw(m).polygon(
    [
        (19, 0),
        (28, 1),
        (29, 8),
        (35, 12),
        (35, 20),
        (40, 23),
        (39, 51),
        (34, 61),
        (22, 65),
        (11, 62),
        (2, 55),
        (2, 25),
        (8, 18),
        (11, 9),
    ],
    fill=255,
)
m.save(MASK_OUT / "objective-lantern.png")
lantern["shape"] = dict(type="mask", src="masks/ui/objective-lantern.png", bounds=b)
# The arrow is a dark silhouette, separately from parchment.
arrow = next(v for v in regions if v["id"] == "end-turn-arrow")
b = [1466, 885, 24, 35]
x, y, w, h = b
a = np.array(im.crop((x, y, x + w, y + h)))
m = np.max(a, axis=2) < 145
Image.fromarray((m * 255).astype("uint8")).save(MASK_OUT / "end-turn-arrow.png")
arrow["shape"] = dict(type="mask", src="masks/ui/end-turn-arrow.png", bounds=b)
# Source yellow pointer has a two-pixel jagged fringe beyond the nominal polygon.
b = [811, 436, 58, 40]
x, y, w, h = b
a = np.array(im.crop((x, y, x + w, y + h))).astype(float)
r, g, bl = a[:, :, 0], a[:, :, 1], a[:, :, 2]
m = (r > 170) & (g > 140) & (bl < 130) & (r > bl * 1.5)
# Clip tightly to pointer geometry so unrelated floor glints stay scene-owned.
clip = Image.new(
    "L", (w, h), 255
)  # Entire tight tail crop is floor-gray except this source yellow pointer.
m = Image.fromarray((m * 255).astype("uint8")).filter(ImageFilter.MaxFilter(3))
m = np.minimum(np.array(m), np.array(clip))
Image.fromarray(m).save(MASK_OUT / "forecast-pointer.png")
regions.append(
    dict(
        id="forecast-pointer",
        category="ui-frame",
        label="Strike forecast yellow pointer visible jagged fringe",
        priority=196,
        parentId="forecast-frame",
        shape=dict(type="mask", src="masks/ui/forecast-pointer.png", bounds=b),
    )
)
out = args.regions_output
out.parent.mkdir(parents=True, exist_ok=True)
out.write_text(
    json.dumps(
        dict(
            schemaVersion=1,
            canvas=[1536, 1024],
            source="Web/wwwroot/assets/broadcast-kit/combat-concept.png",
            regions=regions,
        ),
        indent=2,
    )
    + "\n"
)
print(
    f'{len(regions)} UI regions; {sum(r["category"]=="text" for r in regions)} source glyph masks'
)
