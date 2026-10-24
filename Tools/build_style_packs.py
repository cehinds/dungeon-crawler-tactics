"""Mechanically split generated transparent atlases into labeled concept packs.

python3 Tools/build_style_packs.py --style all
python3 Tools/build_style_packs.py --style all --check

Source alpha bounds and optional reviewed alpha islands are selected mechanically.
Native retained pixels are never resized, recolored, painted, or inferred; scaled
copies are used solely in the previews.
"""
import argparse
from collections import deque
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from PIL import Image, ImageDraw, ImageFilter, ImageFont


ROOT = Path(__file__).resolve().parents[1]
PACKS = ROOT / "Web/wwwroot/assets/style-packs"
SHEETS = {"world": (6, 4), "ui": (4, 3), "expansion": (6, 4), "supplies": (6, 4), "biomes": (4, 3)}
REQUIRED_SHEETS = ("world", "ui")
LAYERS = ("ground", "terrain", "structures", "props", "actors", "effects", "ui")
PADDING = 4
SEAM_GUTTER = 2
MAX_ARCHIVE_BYTES = 32 * 1024 * 1024
PREVIEW_SIZE = (1200, 900)


class PackError(ValueError):
    """An input or output cannot be safely presented as an extracted pack."""


def require(condition, message):
    if not condition:
        raise PackError(message)


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def safe_path(directory, relative):
    target = (directory / relative).resolve()
    require(target.is_relative_to(directory.resolve()), f"Path escapes pack: {relative}")
    return target


def read_catalog(path):
    catalog = json.loads(path.read_text(encoding="utf-8"))
    styles = catalog["styles"]
    if isinstance(styles, dict):
        styles = [dict(value, id=key) for key, value in styles.items()]
    require(isinstance(styles, list) and styles, "catalog.styles must contain styles")
    require(len({style["id"] for style in styles}) == len(styles), "Duplicate style IDs")
    return styles


def cell_box(size, columns, rows, index):
    require(isinstance(index, int) and 0 <= index < columns * rows,
            f"Cell index {index!r} is outside {columns}×{rows}")
    column, row = index % columns, index // columns
    width, height = size
    return (round(column * width / columns), round(row * height / rows),
            round((column + 1) * width / columns), round((row + 1) * height / rows))


def source_region(size, grid, index, override=None):
    default = cell_box(size, *grid, index)
    if override is None:
        return default
    require(isinstance(override, (list, tuple)) and len(override) == 4
            and all(type(value) is int for value in override),
            f"Cell {index}: sourceBox must contain four integer coordinates")
    left, top, right, bottom = override
    require(0 <= left < right <= size[0] and 0 <= top < bottom <= size[1],
            f"Cell {index}: sourceBox is outside source image or empty")
    return tuple(override)


def claim_region(regions, sheet_name, region, asset_id, ownership=None, masked=False):
    for other_sheet, other_region, other_id, other_ownership, other_masked in regions:
        if sheet_name != other_sheet:
            continue
        overlaps = (max(region[0], other_region[0]) < min(region[2], other_region[2])
                    and max(region[1], other_region[1]) < min(region[3], other_region[3]))
        if overlaps:
            require((masked or other_masked) and ownership is not None and other_ownership is not None,
                    f"{asset_id}: source region overlaps {other_id} on {sheet_name}")
            require(ownership.isdisjoint(other_ownership),
                    f"{asset_id}: selected substantial pixels overlap {other_id} on {sheet_name}")
    regions.append((sheet_name, region, asset_id, ownership, masked))


def island_mask_metadata(seeds):
    return {"method": "connected-alpha-islands", "threshold": 16, "connectivity": 8,
            "seeds": seeds, "fringePixels": 2}


def isolate_alpha_islands(sheet, region, seeds):
    """Select source-connected alpha islands and their existing faint fringe only."""
    require(isinstance(seeds, list) and seeds, "alphaIslandSeeds must contain at least one source coordinate")
    width, height = sheet.size
    alpha = sheet.getchannel("A").tobytes()
    selected = set()
    left, top, right, bottom = region
    for seed in seeds:
        require(isinstance(seed, (list, tuple)) and len(seed) == 2
                and all(type(value) is int for value in seed), "Island seed must be two integer source coordinates")
        x, y = seed
        require(left <= x < right and top <= y < bottom, f"Island seed {seed} is outside sourceBox")
        start = y * width + x
        require(alpha[start] > 16, f"Island seed {seed} is empty or below substantial alpha threshold")
        if start in selected:
            continue
        pending = deque([start])
        selected.add(start)
        while pending:
            current = pending.popleft()
            cx, cy = current % width, current // width
            require(left <= cx < right and top <= cy < bottom,
                    f"Selected alpha island is cropped by sourceBox at ({cx}, {cy})")
            for ny in range(max(0, cy - 1), min(height, cy + 2)):
                for nx in range(max(0, cx - 1), min(width, cx + 2)):
                    neighbor = ny * width + nx
                    if alpha[neighbor] > 16 and neighbor not in selected:
                        selected.add(neighbor)
                        pending.append(neighbor)
    cell = sheet.crop(region)
    mask_bytes = bytearray(cell.width * cell.height)
    for index in selected:
        mask_bytes[(index // width - top) * cell.width + index % width - left] = 255
    solid = Image.frombytes("L", cell.size, bytes(mask_bytes))
    expanded = solid.filter(ImageFilter.MaxFilter(5)).tobytes()
    cell_alpha = cell.getchannel("A").tobytes()
    # Exclude other >16-alpha islands even when they are within the fringe radius.
    mask = Image.frombytes("L", cell.size, bytes(255 if core or (near and 0 < opacity <= 16) else 0
                                               for core, near, opacity in zip(mask_bytes, expanded, cell_alpha)))
    result = Image.new("RGBA", cell.size)
    result.paste(cell, (0, 0), mask)
    return result


def substantial_ownership(sprite, bounds, sheet_width):
    alpha = sprite.getchannel("A").tobytes()
    return {(bounds["y"] + index // sprite.width - PADDING) * sheet_width
            + bounds["x"] + index % sprite.width - PADDING
            for index, value in enumerate(alpha) if value > 16}


def extract_cell(sheet, grid, index, name="source", source_box=None, alpha_island_seeds=None):
    box = source_region(sheet.size, grid, index, source_box)
    cell = isolate_alpha_islands(sheet, box, alpha_island_seeds) if alpha_island_seeds is not None else sheet.crop(box)
    alpha = cell.getchannel("A")
    bounds = alpha.getbbox()
    require(bounds is not None, f"{name} cell {index}: empty generated component")
    # A nontransparent seam makes ownership ambiguous: never silently chop it.
    substantial = alpha.point(lambda value: 255 if value > 16 else 0).getbbox()
    require(substantial is not None, f"{name} cell {index}: no visible generated content")
    left, top, right, bottom = substantial
    bad_edges = []
    if box[0] > 0 and left < SEAM_GUTTER:
        bad_edges.append("left")
    if box[2] < sheet.width and right > cell.width - SEAM_GUTTER:
        bad_edges.append("right")
    if box[1] > 0 and top < SEAM_GUTTER:
        bad_edges.append("top")
    if box[3] < sheet.height and bottom > cell.height - SEAM_GUTTER:
        bad_edges.append("bottom")
    require(not bad_edges,
            f"{name} cell {index}: generated content crosses or touches the "
            f"{'/'.join(bad_edges)} {'region boundary' if source_box is not None else 'grid seam'}; "
            "review the isolated artwork and configure non-overlapping sourceBox regions with transparent gutters")
    cropped = cell.crop(bounds)
    sprite = Image.new("RGBA", (cropped.width + 2 * PADDING, cropped.height + 2 * PADDING))
    sprite.paste(cropped, (PADDING, PADDING))
    absolute = {"x": box[0] + bounds[0], "y": box[1] + bounds[1],
                "width": cropped.width, "height": cropped.height}
    return sprite, absolute


def font(size):
    try:
        return ImageFont.truetype("DejaVuSans.ttf", size)
    except OSError:
        return ImageFont.load_default(size=size)


def preview_resampling(style):
    return Image.Resampling.NEAREST if style.get("id") == "pocket-dungeon" else Image.Resampling.LANCZOS


def contact_sheet(assets, sprites, style=None):
    columns, card_width, card_height = 6, 240, 250
    result = Image.new("RGBA", (columns * card_width, math.ceil(len(assets) / columns) * card_height),
                       (17, 24, 35, 255))
    draw = ImageDraw.Draw(result)
    for index, asset in enumerate(assets):
        x, y = index % columns * card_width, index // columns * card_height
        draw.rounded_rectangle((x + 6, y + 6, x + 234, y + 244), radius=8,
                               fill=(28, 38, 52, 255))
        copy = sprites[asset["id"]].copy()
        copy.thumbnail((210, 180), preview_resampling(style or {}))
        result.alpha_composite(copy, (x + (card_width - copy.width) // 2, y + 10 + (180 - copy.height) // 2))
        label = asset["label"]
        while draw.textlength(label, font=font(13)) > 216:
            label = label[:-2] + "…"
        draw.text((x + 12, y + 198), label, font=font(13), fill="white")
        draw.text((x + 12, y + 219), asset["layer"], font=font(11), fill=(170, 192, 211))
    return result


def preview_layers(assets, sprites, style):
    layers = {layer: Image.new("RGBA", PREVIEW_SIZE) for layer in LAYERS}
    grouped = {layer: [asset for asset in assets if asset["layer"] == layer] for layer in LAYERS}

    def place(asset, x, y, width):
        sprite = sprites[asset["id"]]
        scale = min(width / sprite.width, (105 if asset["layer"] == "ui" else 240) / sprite.height)
        copy = sprite.resize((round(sprite.width * scale), round(sprite.height * scale)),
                             preview_resampling(style))
        position = (round(x - asset["anchor"]["x"] * scale),
                    round(y - asset["anchor"]["y"] * scale))
        layers[asset["layer"]].alpha_composite(copy, position)

    explicit = style.get("preview", {}).get("placements")
    if explicit:
        lookup = {asset["id"]: asset for asset in assets}
        for placement in explicit:
            require(placement["id"] in lookup, f"Unknown preview asset: {placement['id']}")
            place(lookup[placement["id"]], placement["x"], placement["y"], placement["width"])
    else:
        # A demonstration assembled only from extracted components, not game geometry.
        orthogonal = style.get("grid", {}).get("projection") == "orthogonal"
        for row in range(5):
            for column in range(5):
                if grouped["ground"]:
                    base = grouped["ground"][(row + column) % min(2, len(grouped["ground"]))]
                    if orthogonal:
                        place(base, 400 + column * 100, 240 + row * 100, 104)
                    else:
                        place(base, 600 + (column - row) * 78, 290 + (column + row) * 39, 164)
        positions = {
            "terrain": [(600, 446, 155), (756, 446, 145), (444, 446, 145)],
            "structures": [(440, 310, 180), (600, 300, 180), (760, 310, 180), (910, 380, 180)],
            "props": [(350, 460, 110), (840, 540, 110), (510, 590, 100)],
            "actors": [(590, 460, 105), (690, 510, 105), (515, 510, 105), (770, 435, 105)],
            "effects": [(600, 465, 125), (760, 490, 110)],
        }
        if orthogonal:
            positions.update({
                "terrain": [(500, 440, 104), (700, 540, 104)],
                "structures": [(400, 220, 110), (500, 220, 110), (700, 220, 110), (800, 220, 110)],
                "props": [(400, 480, 80), (800, 590, 80), (500, 640, 80)],
                "actors": [(600, 450, 85), (700, 470, 85), (500, 520, 85), (800, 380, 85)],
                "effects": [(600, 440, 100), (700, 540, 100)],
            })
        for layer, slots in positions.items():
            for asset, (x, y, width) in zip(grouped[layer], slots):
                place(asset, x, y, width)
        for index, asset in enumerate(grouped["ui"]):
            row, column = divmod(index, 6)
            place(asset, 225 + column * 150, 735 + row * 105, 126)
    composite = Image.new("RGBA", PREVIEW_SIZE)
    for layer in LAYERS:
        composite.alpha_composite(layers[layer])
    return layers, composite


def read_source(path):
    require(path.is_file(), f"{path}: source atlas is missing; save the generated transparent PNG before building")
    with Image.open(path) as source:
        require(source.format == "PNG", f"{path}: source must be PNG")
        require("A" in source.getbands(), f"{path}: source has no alpha channel")
        sheet = source.convert("RGBA")
    alpha = sheet.getchannel("A")
    require(alpha.getextrema()[0] == 0 and alpha.getbbox(),
            f"{path}: genuine transparent background and visible content required")
    return sheet


def active_sheets(names):
    """Require the legacy atlases and include optional atlases only when declared."""
    names = set(names)
    require(names <= SHEETS.keys(), f"Unknown sheets: {sorted(names - SHEETS.keys())}")
    require(set(REQUIRED_SHEETS) <= names, "Pack requires world and ui sheets")
    return {name: grid for name, grid in SHEETS.items() if name in names}


def expected_cells(sheets):
    return {(name, index) for name, grid in sheets.items() for index in range(grid[0] * grid[1])}


def build_pack(style, packs=PACKS):
    style_id = style["id"]
    require(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", style_id), f"Unsafe style ID: {style_id}")
    directory = packs / style_id
    definitions = style["assets"]
    sheets = active_sheets(definition["sheet"] for definition in definitions)
    require(len(definitions) == len(expected_cells(sheets)),
            f"{style_id}: expected {len(expected_cells(sheets))} components for declared sheets")
    sources, sheet_records = {}, {}
    for name, grid in sheets.items():
        relative = f"source/{name}.png"
        path = directory / relative
        sources[name] = read_source(path)
        sheet_records[name] = {"file": relative, "columns": grid[0], "rows": grid[1],
                               "width": sources[name].width, "height": sources[name].height,
                               "sha256": digest(path)}
    assets, sprites, used, regions = [], {}, set(), []
    for definition in definitions:
        asset_id, sheet_name, index = definition["id"], definition["sheet"], definition["cell"]
        require(sheet_name in sheets, f"Unknown sheet: {sheet_name}")
        if isinstance(index, dict):
            index = index["row"] * SHEETS[sheet_name][0] + index["column"]
        require(re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", asset_id), f"Unsafe asset ID: {asset_id}")
        require(asset_id not in sprites, f"Duplicate component ID: {asset_id}")
        require(sheet_name in SHEETS, f"Unknown sheet: {sheet_name}")
        require((sheet_name, index) not in used, f"Duplicate source cell: {sheet_name}/{index}")
        used.add((sheet_name, index))
        require(definition["layer"] in LAYERS, f"Unknown layer: {definition['layer']}")
        region = source_region(sources[sheet_name].size, SHEETS[sheet_name], index, definition.get("sourceBox"))
        sprite, bounds = extract_cell(sources[sheet_name], SHEETS[sheet_name], index,
                                      f"{style_id}/{sheet_name}", definition.get("sourceBox"),
                                      definition.get("alphaIslandSeeds"))
        claim_region(regions, sheet_name, region, asset_id,
                     substantial_ownership(sprite, bounds, sources[sheet_name].width),
                     "alphaIslandSeeds" in definition)
        anchor = definition.get("anchor", {"x": 0.5, "y": 1})
        require(all(isinstance(anchor[axis], (int, float)) and 0 <= anchor[axis] <= 1 for axis in ("x", "y")),
                f"{asset_id}: catalog anchor must be normalized within crop")
        asset = {"id": asset_id, "label": definition["label"], "category": definition["category"],
                 "layer": definition["layer"], "file": f"components/{asset_id}.png",
                 "width": sprite.width, "height": sprite.height,
                 "anchor": {"x": PADDING + bounds["width"] * anchor["x"],
                            "y": PADDING + bounds["height"] * anchor["y"]},
                 "source": {"sheet": sheet_name, "cell": {"column": index % SHEETS[sheet_name][0],
                              "row": index // SHEETS[sheet_name][0], "index": index}, "bounds": bounds},
                 "logicalFootprint": definition.get("logicalFootprint", {"width": 1, "height": 1}),
                 "status": "concept-component"}
        if "sourceBox" in definition:
            asset["source"]["region"] = list(region)
        if "alphaIslandSeeds" in definition:
            asset["source"]["mask"] = island_mask_metadata(definition["alphaIslandSeeds"])
        assets.append(asset)
        sprites[asset_id] = sprite
    require(used == expected_cells(sheets),
            f"{style_id}: all atlas cells must be assigned exactly once")
    layers, preview = preview_layers(assets, sprites, style)
    manifest = {"schemaVersion": 1, "id": style_id, "title": style.get("title", style_id),
                "description": style.get("description", ""), "status": "concept-component-pack",
                "generation": {"source": "imagegen", "extraction": "native-grid-crop", "padding": PADDING,
                               "explicitSourceRegions": any("sourceBox" in asset for asset in definitions),
                               "explicitAlphaIslands": any("alphaIslandSeeds" in asset for asset in definitions)},
                "sheets": sheet_records, "assets": assets,
                "preview": {"file": "preview.png", "kind": "component-composition",
                            "width": PREVIEW_SIZE[0], "height": PREVIEW_SIZE[1],
                            "layers": [{"id": layer, "label": layer.title(), "file": f"layers/{layer}.png"}
                                       for layer in LAYERS]},
                "contactSheet": "contact-sheet.png", "download": f"{style_id}.zip"}
    for key in ("grid", "concept", "newConcept", "combatConcept", "accent"):
        if key in style:
            manifest[key] = style[key]
    manifest["conceptFiles"] = sorted(path.relative_to(directory).as_posix()
                                      for path in (directory / "concepts").glob("*.png"))
    for asset in assets:
        path = directory / asset["file"]
        path.parent.mkdir(parents=True, exist_ok=True)
        sprites[asset["id"]].save(path, optimize=True)
    (directory / "layers").mkdir(exist_ok=True)
    for layer, image in layers.items():
        image.save(directory / f"layers/{layer}.png", optimize=True)
    preview.save(directory / "preview.png", optimize=True)
    contact_sheet(assets, sprites, style).save(directory / "contact-sheet.png", optimize=True)
    (directory / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n", encoding="utf-8")
    (directory / "README.md").write_text(readme(manifest), encoding="utf-8")
    archive_path = directory / manifest["download"]
    with ZipFile(archive_path, "w", ZIP_DEFLATED, compresslevel=9) as archive:
        for relative in archive_files(manifest):
            info = ZipInfo(relative, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            archive.writestr(info, (directory / relative).read_bytes(), compresslevel=9)
    validate_pack(directory)
    return manifest


def archive_files(manifest):
    return sorted(["manifest.json", "README.md", manifest["contactSheet"], manifest["preview"]["file"]]
                  + [asset["file"] for asset in manifest["assets"]]
                  + [layer["file"] for layer in manifest["preview"]["layers"]]
                  + manifest.get("conceptFiles", []))


def readme(manifest):
    return f"""# {manifest['title']} — extracted concept components

{len(manifest["assets"])} individually labeled transparent PNGs, mechanically cropped at native pixel
resolution from {len(manifest["sheets"])} generated atlases. Each crop has {PADDING}px transparent padding.
Available original and additional concept-scene PNGs are included in concepts/;
manifest.conceptFiles lists the archive-relative paths.
The original source atlases remain in the repository's source/ directory; their
SHA-256 fingerprints, cell coordinates and absolute crop bounds are in manifest.json.
When the generated layout drifts from the requested grid, reviewed non-overlapping
source.region rectangles identify the actual extraction regions; source.cell still
identifies the intended logical slot. Source regions never invent or repaint art.
For tightly packed silhouettes, source.mask records reviewed source-coordinate
alphaIslandSeeds. Eight-connected source pixels with alpha >16 are selected by
flood fill; existing alpha 1–16 fringe within two pixels is also retained. Every
retained RGBA pixel is unchanged. Other pixels become transparent; no colors or
details are synthesized. Overlapping extraction rectangles are permitted only
with an explicit island mask and disjoint substantial-pixel ownership. An island
cut by its extraction rectangle is rejected.
No painting, recoloring or invented detail is performed by the extraction script.

The contact sheet labels sit outside the artwork. preview.png is an illustrative
component arrangement, not a playable room or an integrated game screenshot.
The seven full-canvas layers/*.png composite in manifest order to reproduce it.
Toggle these same layers in the gallery to inspect their contribution. Components
are scaled only in the previews; the individual PNGs preserve source pixels.

Anchors are measured in pixels from each PNG's top-left, including padding.
The default anchor is the original crop's bottom-center. logicalFootprint is
placement guidance, not a collision shape. These are concept components: animation,
directional views, tile seams and runtime collision require a production art pass.

Rebuild: python3 Tools/build_style_packs.py --style {manifest['id']}
Validate without writing: python3 Tools/build_style_packs.py --style {manifest['id']} --check
"""


def validate_pack(directory):
    manifest = json.loads((directory / "manifest.json").read_text(encoding="utf-8"))
    require(manifest["schemaVersion"] == 1, "Unsupported style-pack schema")
    sheets = active_sheets(manifest["sheets"])
    require(len(manifest["assets"]) == len(expected_cells(sheets)), "Pack component count differs from declared sheets")
    sources = {}
    for name, record in manifest["sheets"].items():
        require((record["columns"], record["rows"]) == sheets[name], f"{name}: invalid sheet grid")
        path = safe_path(directory, record["file"])
        require(digest(path) == record["sha256"], f"{name}: source fingerprint changed")
        sources[name] = read_source(path)
        require(sources[name].size == (record["width"], record["height"]), f"{name}: source size changed")
    seen, cells, regions = set(), set(), []
    for asset in manifest["assets"]:
        require(asset["id"] not in seen, f"Duplicate asset: {asset['id']}")
        seen.add(asset["id"])
        require(asset["status"] == "concept-component" and asset["layer"] in LAYERS,
                f"{asset['id']}: invalid status/layer")
        source = asset["source"]
        require(source["sheet"] in sheets, f"Unknown sheet: {source['sheet']}")
        key = (source["sheet"], source["cell"]["index"])
        require(key not in cells, f"Duplicate cell assignment: {key}")
        cells.add(key)
        region = source_region(sources[key[0]].size, SHEETS[key[0]], key[1], source.get("region"))
        mask = source.get("mask")
        if mask is not None:
            require(mask == island_mask_metadata(mask.get("seeds")), f"{asset['id']}: unsupported mask metadata")
        expected, bounds = extract_cell(sources[key[0]], SHEETS[key[0]], key[1], key[0], source.get("region"),
                                        mask["seeds"] if mask is not None else None)
        claim_region(regions, key[0], region, asset["id"],
                     substantial_ownership(expected, bounds, sources[key[0]].width), mask is not None)
        require(bounds == source["bounds"], f"{asset['id']}: source crop metadata changed")
        with Image.open(safe_path(directory, asset["file"])) as sprite:
            require(sprite.mode == "RGBA", f"{asset['id']}: expected RGBA")
            require(sprite.size == (asset["width"], asset["height"]) == expected.size,
                    f"{asset['id']}: PNG dimensions differ")
            require(sprite.tobytes() == expected.tobytes(), f"{asset['id']}: PNG differs from native source pixels")
        require(all(0 <= asset["anchor"][axis] <= asset["width" if axis == "x" else "height"]
                    for axis in ("x", "y")), f"{asset['id']}: anchor outside PNG")
    require(cells == expected_cells(sheets),
            "Every source cell must be represented exactly once")
    composite = Image.new("RGBA", PREVIEW_SIZE)
    require([layer["id"] for layer in manifest["preview"]["layers"]] == list(LAYERS), "Invalid layer order")
    for layer in manifest["preview"]["layers"]:
        with Image.open(safe_path(directory, layer["file"])) as image:
            require(image.mode == "RGBA" and image.size == PREVIEW_SIZE, f"{layer['id']}: invalid preview layer")
            composite.alpha_composite(image)
    with Image.open(directory / manifest["preview"]["file"]) as image:
        require(image.mode == "RGBA" and image.size == PREVIEW_SIZE and image.tobytes() == composite.tobytes(),
                "Preview differs from composited layer PNGs")
    archive_path = safe_path(directory, manifest["download"])
    require(archive_path.stat().st_size <= MAX_ARCHIVE_BYTES, "Style ZIP exceeds 32 MiB limit")
    with ZipFile(archive_path) as archive:
        require(archive.namelist() == archive_files(manifest), "Archive entries differ from manifest")
        require(archive.testzip() is None, "Corrupt ZIP archive")
        for relative in archive.namelist():
            require(archive.read(relative) == safe_path(directory, relative).read_bytes(), f"Stale archive entry: {relative}")
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--style", default="all", help="Style ID or all (default)")
    parser.add_argument("--check", action="store_true", help="Validate existing outputs without mutations")
    parser.add_argument("--catalog", type=Path, default=PACKS / "catalog.json")
    args = parser.parse_args(argv)
    try:
        styles = read_catalog(args.catalog)
        chosen = [style for style in styles if args.style in ("all", style["id"])]
        require(chosen, f"Unknown style: {args.style}")
        for style in chosen:
            manifest = validate_pack(args.catalog.parent / style["id"]) if args.check else build_pack(style, args.catalog.parent)
            print(f"{'Validated' if args.check else 'Built'} {manifest['id']}: {len(manifest['assets'])} native PNG components, seven layers and ZIP")
    except (PackError, OSError, KeyError, json.JSONDecodeError) as error:
        print(f"Style pack error: {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
