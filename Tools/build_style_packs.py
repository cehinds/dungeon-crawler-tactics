"""Mechanically split generated transparent atlases into labeled concept packs.

python3 Tools/build_style_packs.py --style all
python3 Tools/build_style_packs.py --style all --check

Source alpha bounds and optional reviewed alpha islands are selected mechanically.
Native retained pixels are never resized, recolored, painted, or inferred; scaled
copies are used solely in the previews.
"""
import argparse
import copy
from collections import deque
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from zipfile import ZIP_DEFLATED, ZipFile, ZipInfo

from PIL import Image, ImageDraw, ImageFilter, ImageFont
from art_metadata import enrich_expected


ROOT = Path(__file__).resolve().parents[1]
PACKS = ROOT / "Web/wwwroot/assets/style-packs"
SHEETS = {"world": (6, 4), "ui": (4, 3), "expansion": (6, 4), "supplies": (6, 4), "biomes": (4, 3), "services": (6, 4)}
COLLECTION_IDS = ("arsenal", "armor", "gear", "settlements", "roads", "forest", "highlands", "caverns", "attacks", "spells")
COLLECTION_LABELS = dict(zip(COLLECTION_IDS, ("Weapons", "Armor", "Gear", "Cities & towns", "Roads", "Forests", "Mountains & volcanic", "Caves", "Character attacks", "Spells")))
SHEETS.update({name: (6, 4) for name in COLLECTION_IDS})
REQUIRED_SHEETS = ("world", "ui")
LAYERS = ("ground", "terrain", "structures", "props", "actors", "effects", "ui")
PADDING = 4
SEAM_GUTTER = 2
MAX_ARCHIVE_BYTES = 90 * 1024 * 1024
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
    alpha = sheet.info.get("pack_alpha")
    if alpha is None:
        alpha = sheet.getchannel("A").tobytes()
        sheet.info["pack_alpha"] = alpha
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
        if sheet_name in COLLECTION_IDS:
            require(definition.get("collection") == sheet_name, f"{asset_id}: collection must match source sheet")
        if sheet_name in ("attacks", "spells"):
            require("animation" in definition, f"{asset_id}: animation metadata required")
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
        for key in ("collection", "animation"):
            if key in definition:
                asset[key] = definition[key]
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
    manifest["animations"] = build_animations(directory, assets, sprites, style)
    manifest["collections"] = build_collections(directory, assets, sprites, manifest["animations"], style)
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


def animation_files(clip):
    return clip["frames"] + [clip["preview"], clip["spriteSheet"], clip["metadata"]]


def normalized_frames(members, sprites, style):
    """Use one scale, fitting every frame around a common registration point."""
    kinds = {asset["animation"]["anchor"] for asset in members}
    require(len(kinds) == 1 and kinds <= {"feet", "center"}, "Animation anchors must agree")
    anchor = {"x": 128, "y": 240 if "feet" in kinds else 128}
    registrations = []
    scale = float("inf")
    for asset in members:
        sprite = sprites[asset["id"]]
        bounds = sprite.getchannel("A").getbbox()
        require(bounds is not None, "Empty animation frame")
        registration = asset.get("anchor")
        if registration is None:
            x = (bounds[0] + bounds[2]) / 2
            y = bounds[3] if "feet" in kinds else (bounds[1] + bounds[3]) / 2
        else:
            x, y = registration["x"], registration["y"]
            require(isinstance(x, (int, float)) and isinstance(y, (int, float))
                    and 0 <= x <= sprite.width and 0 <= y <= sprite.height,
                    "Animation registration anchor outside native component")
        registrations.append((x, y))
        for extent, space in ((x, anchor["x"] - 2), (sprite.width - x, 254 - anchor["x"]),
                              (y, anchor["y"] - 2), (sprite.height - y, 254 - anchor["y"])):
            if extent > 0:
                scale = min(scale, space / extent)
    frames = []
    for asset, (x, y) in zip(members, registrations):
        sprite = sprites[asset["id"]]
        copy = sprite.resize((max(1, round(sprite.width * scale)), max(1, round(sprite.height * scale))),
                             preview_resampling(style))
        frame = Image.new("RGBA", (256, 256))
        position = (round(anchor["x"] - x * scale), round(anchor["y"] - y * scale))
        require(position[0] >= 0 and position[1] >= 0 and position[0] + copy.width <= 256
                and position[1] + copy.height <= 256, "Shared animation scale clips a frame")
        frame.alpha_composite(copy, position)
        frames.append(frame)
    require(len({frame.tobytes() for frame in frames}) == 6, "Animation contains duplicate rendered frames")
    return frames, anchor, scale


def animation_groups(assets):
    groups = {}
    for asset in assets:
        if "animation" in asset:
            metadata = asset["animation"]
            clip = metadata["clip"]
            require(isinstance(clip, str) and re.fullmatch(r"[a-z0-9]+(?:-[a-z0-9]+)*", clip), "Unsafe animation ID")
            require(type(metadata["frame"]) is int and metadata["fps"] == 8, "Animation requires integer frames and 8 fps")
            groups.setdefault(clip, []).append(asset)
    for clip, members in groups.items():
        members.sort(key=lambda asset: asset["animation"]["frame"])
        require([asset["animation"]["frame"] for asset in members] == list(range(1, 7)),
                f"{clip}: animation requires six unique frames numbered 1–6")
        require(len({asset.get("collection") for asset in members}) == 1, f"{clip}: collection differs across frames")
    return groups


def build_animations(directory, assets, sprites, style):
    records = []
    for clip, members in sorted(animation_groups(assets).items()):
        frames, anchor, scale = normalized_frames(members, sprites, style)
        base = f"animations/{clip}"
        (directory / base).mkdir(parents=True, exist_ok=True)
        paths = [f"{base}/frame-{index:02}.png" for index in range(1, 7)]
        for path, frame in zip(paths, frames):
            frame.save(directory / path, optimize=True)
        strip = Image.new("RGBA", (1536, 256))
        for index, frame in enumerate(frames):
            strip.paste(frame, (index * 256, 0))
        strip.save(directory / base / "strip.png", optimize=True)
        frames[0].save(directory / base / "preview.webp", save_all=True, append_images=frames[1:],
                       duration=125, loop=0, lossless=True, exact=True, minimize_size=False)
        records.append({"id": clip, "label": re.sub(r"\s*·\s*frame\s+\d+\s*$", "", members[0]["label"], flags=re.IGNORECASE), "frames": paths,
                        "fps": 8, "frameWidth": 256, "frameHeight": 256, "anchor": anchor,
                        "scale": scale, "preview": f"{base}/preview.webp", "spriteSheet": f"{base}/strip.png",
                        "componentIds": [asset["id"] for asset in members], "metadata": f"{base}/metadata.json"})
        (directory / records[-1]["metadata"]).write_text(json.dumps(records[-1], indent=2) + "\n", encoding="utf-8")
    return records


def write_archive(directory, relative, files):
    with ZipFile(directory / relative, "w", ZIP_DEFLATED, compresslevel=9) as archive:
        for path in sorted(set(files)):
            info = ZipInfo(path, date_time=(1980, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            archive.writestr(info, safe_path(directory, path).read_bytes(), compresslevel=9)


def build_collections(directory, assets, sprites, animations, style):
    records = []
    for collection in sorted({asset["collection"] for asset in assets if "collection" in asset}):
        require(collection in COLLECTION_IDS, f"Unknown collection: {collection}")
        members = [asset for asset in assets if asset.get("collection") == collection]
        clips = [clip for clip in animations if clip["componentIds"][0] in {asset["id"] for asset in members}]
        base = f"collections/{collection}"
        (directory / base).mkdir(parents=True, exist_ok=True)
        record = {"id": collection, "label": COLLECTION_LABELS[collection], "count": len(members),
                  "download": f"{base}/{collection}.zip", "contactSheet": f"{base}/contact-sheet.png",
                  "manifest": f"{base}/manifest.json"}
        contact_sheet(members, sprites, style).save(directory / record["contactSheet"], optimize=True)
        document = {"schemaVersion": 1, "id": collection, "label": record["label"],
                    "pathBase": "pack-root", "assets": members, "animations": clips}
        (directory / record["manifest"]).write_text(json.dumps(document, indent=2) + "\n", encoding="utf-8")
        files = [record["manifest"], record["contactSheet"]] + [asset["file"] for asset in members]
        files += [path for clip in clips for path in animation_files(clip)]
        write_archive(directory, record["download"], files)
        records.append(record)
    return records


def validate_collections_and_animations(directory, manifest):
    assets = manifest["assets"]
    sprites = {}
    for asset in assets:
        with Image.open(safe_path(directory, asset["file"])) as image:
            sprites[asset["id"]] = image.convert("RGBA")
    groups = animation_groups(assets)
    records = manifest.get("animations", [])
    require(len(records) == len(groups) and {clip["id"] for clip in records} == set(groups), "Animation inventory differs")
    for clip in records:
        members = groups[clip["id"]]
        validate_animation_metadata(directory, clip)
        frames, anchor, scale = normalized_frames(members, sprites, manifest)
        require(clip["anchor"] == anchor and clip.get("scale") == scale and clip["fps"] == 8
                and clip["frameWidth"] == clip["frameHeight"] == 256, "Animation registration metadata differs")
        require(clip["componentIds"] == [asset["id"] for asset in members], "Animation component order differs")
        require(len(clip["frames"]) == len(set(clip["frames"])) == 6, "Duplicate or missing animation frames")
        for path, expected in zip(clip["frames"], frames):
            with Image.open(safe_path(directory, path)) as actual:
                require(actual.mode == "RGBA" and actual.size == (256, 256)
                        and actual.tobytes() == expected.tobytes(), "Animation frame differs from shared-scale export")
        with Image.open(safe_path(directory, clip["spriteSheet"])) as strip:
            require(strip.size == (1536, 256) and strip.mode == "RGBA", "Invalid animation strip")
            for index, frame in enumerate(frames):
                require(strip.crop((index * 256, 0, (index + 1) * 256, 256)).tobytes() == frame.tobytes(), "Animation strip frame differs")
        with Image.open(safe_path(directory, clip["preview"])) as preview:
            require(preview.format == "WEBP" and preview.n_frames == 6, "Animation preview requires six decoded frames")
            for index, frame in enumerate(frames):
                preview.seek(index)
                require(preview.size == (256, 256), "Animation preview size differs")
                # WebP may discard RGB beneath zero alpha; visible pixels must remain lossless.
                actual = preview.convert("RGBA")
                require(actual.getchannel("A").tobytes() == frame.getchannel("A").tobytes()
                        and Image.alpha_composite(Image.new("RGBA", frame.size, "black"), actual).tobytes()
                        == Image.alpha_composite(Image.new("RGBA", frame.size, "black"), frame).tobytes(), "Lossless animation preview differs")
    collections = manifest.get("collections", [])
    expected_ids = {asset["collection"] for asset in assets if "collection" in asset}
    require(len(collections) == len(expected_ids) and {record["id"] for record in collections} == expected_ids, "Collection inventory differs")
    for record in collections:
        members = [asset for asset in assets if asset.get("collection") == record["id"]]
        clips = [clip for clip in records if clip["componentIds"][0] in {asset["id"] for asset in members}]
        document = json.loads(safe_path(directory, record["manifest"]).read_text())
        require(record["count"] == len(members) and document["assets"] == members and document["animations"] == clips, "Collection manifest differs")
        with Image.open(safe_path(directory, record["contactSheet"])) as contact:
            require(contact.size == (1440, math.ceil(len(members) / 6) * 250), "Collection contact sheet size differs")
        files = sorted(set([record["manifest"], record["contactSheet"]] + [asset["file"] for asset in members]
                           + [path for clip in clips for path in animation_files(clip)]))
        with ZipFile(safe_path(directory, record["download"])) as archive:
            require(archive.namelist() == files and archive.testzip() is None, "Collection archive inventory differs")
            for path in files:
                require(archive.read(path) == safe_path(directory, path).read_bytes(), "Stale collection archive entry")


def archive_files(manifest):
    return sorted(["manifest.json", "README.md", manifest["contactSheet"], manifest["preview"]["file"]]
                  + [asset["file"] for asset in manifest["assets"]]
                  + [layer["file"] for layer in manifest["preview"]["layers"]]
                  + manifest.get("conceptFiles", [])
                  + [path for clip in manifest.get("animations", []) for path in animation_files(clip)]
                  + [record[key] for record in manifest.get("collections", []) for key in ("manifest", "contactSheet")])


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
Toggle these same layers in the gallery to inspect their contribution. Native component PNGs preserve source pixels. Animation exports are derived, resampled
256×256 canvases using a shared scale per clip, with fixed feet or center anchors.
Lossless WebP previews and horizontal PNG strips accompany each six-frame clip.

Anchors are measured in pixels from each PNG's top-left, including padding.
The default anchor is the original crop's bottom-center. logicalFootprint is
placement guidance, not a collision shape. These are concept components; directional views, tile seams and runtime collision
require a production art pass. Animation clips are illustrative derived exports.

Rebuild: python3 Tools/build_style_packs.py --style {manifest['id']}
Validate without writing: python3 Tools/build_style_packs.py --style {manifest['id']} --check
"""


def validate_animation_metadata(directory, clip):
    require(json.loads(safe_path(directory, clip["metadata"]).read_text()) == enrich_expected(copy.deepcopy(clip), directory),
            "Animation metadata differs")


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
        if source["sheet"] in COLLECTION_IDS:
            require(asset.get("collection") == source["sheet"], f"{asset['id']}: collection must match source sheet")
        if source["sheet"] in ("attacks", "spells"):
            require("animation" in asset, f"{asset['id']}: animation metadata required")
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
    validate_collections_and_animations(directory, manifest)
    archive_path = safe_path(directory, manifest["download"])
    require(archive_path.stat().st_size <= MAX_ARCHIVE_BYTES, f"Style ZIP exceeds {MAX_ARCHIVE_BYTES // (1024 * 1024)} MiB limit")
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
