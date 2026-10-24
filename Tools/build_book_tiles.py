"""Export compact, normalized Books 1–5 location art, without changing sources.

    python3 Tools/build_book_tiles.py --style pocket-dungeon
    python3 Tools/build_book_tiles.py --style pocket-dungeon --kit starter-dungeon
    python3 Tools/build_book_tiles.py --style all --check
    python3 Tools/build_book_tiles.py --catalog

Source atlases and reviewed crops live under Docs/BookLocationTiles, outside the
published site. Components are normalized derived exports, not native pixel
copies: tight alpha crops are resized onto transparent 256×256 canvases. Ground
is centered on the logical tile anchor; other art uses its reviewed anchor or
bottom center. Walls/doors with renderHeight are mechanically normalized to
authored grid dimensions; other structures and props retain their aspect ratio.
--kit permits incremental builds from partial reviewed crop sheets; omitting it
requires complete style coverage. --check reconstructs exports and never writes.
--catalog aggregates completed manifests, so independent style builds cannot
erase another style's catalog entries. Catalog links are catalog-relative;
component links in each manifest are manifest-relative. Pillow is required.
"""

import argparse
import hashlib
import json
import math
from pathlib import Path
import re
import sys
from zipfile import BadZipFile, ZipFile

from PIL import Image, ImageDraw

from build_style_packs import (
    PackError, claim_region, digest, extract_cell, font, island_mask_metadata,
    read_source, require, safe_path, source_region, substantial_ownership, write_archive,
)


ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "Docs/BookLocationTiles"
OUTPUT = ROOT / "Web/wwwroot/assets/book-tiles"
CANVAS = (256, 256)
ANCHOR = {"x": 128, "y": 192}
SLUG = re.compile(r"[a-z0-9]+(?:-[a-z0-9]+)*\Z")


def read_json(path):
    require(path.is_file(), f"Missing authored input: {path}")
    return json.loads(path.read_text(encoding="utf-8"))


def json_bytes(value):
    return (json.dumps(value, ensure_ascii=False, indent=2) + "\n").encode("utf-8")


def read_inventory(docs=DOCS):
    inventory = read_json(docs / "inventory.json")
    for collection in (inventory["styles"], inventory["kits"]):
        identifiers = [item["id"] for item in collection]
        require(len(identifiers) == len(set(identifiers)), "Duplicate style or kit IDs")
        require(all(isinstance(value, str) and SLUG.fullmatch(value) for value in identifiers),
                "Style and kit IDs must be safe slugs")
    asset_ids = set()
    for kit in inventory["kits"]:
        assets = kit["assets"]
        require(kit.get("columns", 6) == 6 and kit.get("rows", 4) == 4,
                f"{kit['id']}: expected 6×4 atlas")
        require(len(assets) == 24 and {a["cell"] for a in assets} == set(range(24)),
                f"{kit['id']}: exactly 24 unique cells required")
        for asset in assets:
            require(isinstance(asset["id"], str) and SLUG.fullmatch(asset["id"]), "Unsafe asset ID")
            require(asset["id"] not in asset_ids, f"Duplicate asset ID: {asset['id']}")
            asset_ids.add(asset["id"])
            for field in ("renderWidth", "renderHeight", "orthogonalRenderWidth"):
                if field != "renderWidth" and field not in asset:
                    continue
                value = asset.get(field)
                require(type(value) in (float, int) and math.isfinite(value) and value > 0,
                        f"{asset['id']}: positive finite {field} required")
    return inventory


def reviewed_crops(docs, style):
    document = read_json(docs / "crops" / f"{style['id']}.json")
    require(document["style"] == style["id"], "Crop style mismatch")
    return document["sheets"]


def normalized_anchor(value, default):
    if value is None:
        return default
    if isinstance(value, dict):
        value = [value.get("x"), value.get("y")]
    require(isinstance(value, (list, tuple)) and len(value) == 2
            and all(type(v) in (float, int) and 0 <= v <= 1 for v in value),
            "Reviewed anchor must contain normalized x/y relative to actual tight alpha bounds")
    return tuple(value)


def normalize(tight, asset, style, reviewed_anchor=None):
    """Return derived canvas and exact, reconstructible resize/placement metadata."""
    ground = asset["role"] == "ground"
    pixel = style["id"] == "pocket-dungeon"
    resampling = Image.Resampling.NEAREST if pixel else Image.Resampling.LANCZOS
    if ground:
        size = (style["tileWidth"], style["tileHeight"])
        relative = normalized_anchor(reviewed_anchor, (0.5, 0.5))
        sizing = "logical-ground"
    else:
        architecture = asset["role"] in ("wall", "door")
        width = (asset.get("orthogonalRenderWidth", 128)
                 if style["projection"] == "orthogonal" and architecture else asset["renderWidth"])
        if architecture and "renderHeight" in asset:
            size = (max(1, round(min(width, 240))), max(1, round(min(asset["renderHeight"], 184))))
            sizing = "modular-architecture"
        else:
            scale = min(width / tight.width, 240 / tight.width, 184 / tight.height)
            size = (max(1, round(tight.width * scale)), max(1, round(tight.height * scale)))
            sizing = "preserve-aspect"
        relative = normalized_anchor(reviewed_anchor, (0.5, 1))
    offset = (round(ANCHOR["x"] - relative[0] * size[0]),
              round(ANCHOR["y"] - relative[1] * size[1]))
    require(offset[0] >= 0 and offset[1] >= 0
            and offset[0] + size[0] <= CANVAS[0] and offset[1] + size[1] <= CANVAS[1],
            f"{asset['id']}: reviewed anchor would clip normalized canvas")
    resized = tight.resize(size, resampling)
    canvas = Image.new("RGBA", CANVAS)
    canvas.paste(resized, offset)
    derived = {"kind": "normalized-derived-export", "sizing": sizing,
               "resampling": "nearest" if pixel else "lanczos",
               "scaleX": size[0] / tight.width, "scaleY": size[1] / tight.height,
               "width": size[0], "height": size[1], "offset": {"x": offset[0], "y": offset[1]}}
    return canvas, derived, {"x": relative[0], "y": relative[1]}


def prepare_kit(docs, kit, style, crops):
    """Read reviewed source once, claim ownership, and construct expected artifacts."""
    source = docs / "sources" / style["id"] / f"{kit['id']}.png"
    sheet = read_source(source)
    require(sheet.size == (1536, 1024), f"{source}: expected 1536×1024 source atlas")
    source_hash = digest(source)
    reviews = crops.get(kit["id"])
    require(isinstance(reviews, list) and len(reviews) == 24,
            f"{kit['id']}: 24 reviewed crop definitions required")
    require({review["cell"] for review in reviews} == set(range(24)),
            f"{kit['id']}: duplicate or missing reviewed cells")
    reviews = {review["cell"]: review for review in reviews}
    assets, sprites, regions, visible = [], {}, [], set()
    for definition in sorted(kit["assets"], key=lambda a: a["cell"]):
        asset = dict(definition)
        review = reviews[asset["cell"]]
        require("sourceBox" in review and "alphaIslandSeeds" in review,
                f"{asset['id']}: sourceBox and alphaIslandSeeds review required")
        region = source_region(sheet.size, (6, 4), asset["cell"], review["sourceBox"])
        retained, bounds = extract_cell(sheet, (6, 4), asset["cell"], asset["id"],
                                        review["sourceBox"], review["alphaIslandSeeds"])
        ownership = substantial_ownership(retained, bounds, sheet.width)
        claim_region(regions, kit["id"], region, asset["id"], ownership,
                     review["alphaIslandSeeds"] is not None)
        tight = retained.crop(retained.getchannel("A").getbbox())
        sprite, derived, relative = normalize(tight, asset, style, review.get("anchor"))
        fingerprint = visible_digest(sprite)
        require(fingerprint not in visible, f"{asset['id']}: duplicate visible asset in kit")
        visible.add(fingerprint)
        asset.update(file=f"components/{asset['id']}.png", width=256, height=256,
                     anchor=dict(ANCHOR), derived=derived)
        asset["source"] = {
            "file": f"Docs/BookLocationTiles/sources/{style['id']}/{kit['id']}.png",
            "sha256": source_hash, "atlasWidth": sheet.width, "atlasHeight": sheet.height,
            "cell": asset["cell"], "sourceBox": list(region), "bounds": bounds,
            "originalWidth": tight.width, "originalHeight": tight.height,
            "alphaMask": island_mask_metadata(review["alphaIslandSeeds"])
            if review["alphaIslandSeeds"] is not None else {"method": "source-region-alpha"},
            "normalizedAnchor": relative,
        }
        assets.append(asset)
        sprites[asset["id"]] = sprite
    manifest = {"schemaVersion": 1, "id": kit["id"], "style": style["id"],
                "title": kit["title"], "books": kit["books"],
                "exportKind": "normalized-derived-exports-not-native-pixel-copies",
                "grid": {key: style[key] for key in ("projection", "tileWidth", "tileHeight")},
                "assets": assets, "download": f"{kit['id']}.zip", "contactSheet": "contact-sheet.png"}
    manifest["grid"].update(canvasWidth=256, canvasHeight=256, anchor=dict(ANCHOR))
    return manifest, sprites


def visible_digest(sprite):
    """Ignore RGB in fully transparent pixels when checking visible duplicates."""
    visible = Image.new("RGBA", sprite.size)
    visible.alpha_composite(sprite)
    return hashlib.sha256(visible.tobytes()).hexdigest()


def contact_sheet(assets, sprites, style):
    result = Image.new("RGBA", (768, 640), (18, 25, 36, 255))
    draw = ImageDraw.Draw(result)
    resampling = Image.Resampling.NEAREST if style["id"] == "pocket-dungeon" else Image.Resampling.LANCZOS
    label_font = font(10)
    for index, asset in enumerate(assets):
        x, y = index % 6 * 128, index // 6 * 160
        draw.rectangle((x + 3, y + 3, x + 124, y + 156), fill=(31, 41, 55, 255))
        sprite = sprites[asset["id"]]
        preview = sprite.crop(sprite.getchannel("A").getbbox())
        scale = min(112 / preview.width, 112 / preview.height)
        preview = preview.resize((max(1, round(preview.width * scale)),
                                  max(1, round(preview.height * scale))), resampling)
        result.alpha_composite(preview, (x + (128 - preview.width) // 2,
                                         y + 4 + (120 - preview.height) // 2))
        label = asset["label"]
        while len(label) > 1 and draw.textlength(label, font=label_font) > 116:
            label = label[:-2] + "…"
        draw.text((x + 6, y + 126), label, font=label_font, fill="white")
        draw.text((x + 6, y + 141), asset["role"], font=label_font, fill=(167, 188, 210))
    return result


def archive_files(manifest):
    return {"manifest.json", manifest["contactSheet"], *(asset["file"] for asset in manifest["assets"])}


def build_kit(directory, manifest, sprites, style):
    (directory / "components").mkdir(parents=True, exist_ok=True)
    expected = archive_files(manifest) | {manifest["download"]}
    require(not {p.relative_to(directory).as_posix() for p in directory.rglob("*") if p.is_file()} - expected,
            f"{directory}: unexpected files; refusing to retain obsolete exports")
    for asset in manifest["assets"]:
        sprites[asset["id"]].save(directory / asset["file"], optimize=True)
    (directory / "manifest.json").write_bytes(json_bytes(manifest))
    contact_sheet(manifest["assets"], sprites, style).save(directory / manifest["contactSheet"], optimize=True)
    write_archive(directory, manifest["download"], archive_files(manifest))


def validate_kit(directory, expected, sprites, style):
    manifest = read_json(directory / "manifest.json")
    require(manifest == expected, f"{directory}: stale manifest, source hash, or provenance")
    files = {p.relative_to(directory).as_posix() for p in directory.rglob("*") if p.is_file()}
    require(files == archive_files(manifest) | {manifest["download"]}, f"{directory}: unexpected/missing outputs")
    fingerprints = set()
    for asset in manifest["assets"]:
        path = directory / asset["file"]
        with Image.open(path) as actual:
            require(actual.format == "PNG" and actual.mode == "RGBA" and actual.size == CANVAS,
                    f"{path}: expected 256×256 RGBA PNG")
            require(actual.getchannel("A").getextrema()[0] == 0 and actual.getbbox(), f"{path}: true alpha required")
            require(actual.tobytes() == sprites[asset["id"]].tobytes(), f"{path}: source reconstruction differs")
            fingerprints.add(visible_digest(actual))
    require(len(fingerprints) == 24, f"{directory}: duplicate visible components")
    with Image.open(directory / manifest["contactSheet"]) as contact:
        expected_contact = contact_sheet(manifest["assets"], sprites, style)
        require(contact.format == "PNG" and contact.mode == "RGBA" and contact.size == (768, 640)
                and contact.tobytes() == expected_contact.tobytes(), f"{directory}: stale contact sheet")
    with ZipFile(directory / manifest["download"]) as archive:
        require(len(archive.namelist()) == len(set(archive.namelist()))
                and set(archive.namelist()) == archive_files(manifest), f"{directory}: incorrect ZIP contents")
        require(archive.testzip() is None, f"{directory}: corrupt ZIP")
        for name in archive_files(manifest):
            require(archive.read(name) == (directory / name).read_bytes(), f"{directory}: stale ZIP member {name}")
    return fingerprints


def catalog_document(inventory, coverage, output, docs=DOCS):
    known = {kit["id"] for kit in inventory["kits"]}
    for location in coverage["locations"]:
        require(set(location["kitIds"]) <= known, f"{location['id']}: unknown kit reference")
    kits = []
    for kit in inventory["kits"]:
        variants = {}
        for style in inventory["styles"]:
            directory = output / style["id"] / kit["id"]
            path = directory / "manifest.json"
            if not path.is_file():
                continue
            manifest = read_json(path)
            require(manifest["id"] == kit["id"] and manifest["style"] == style["id"], "Manifest identity mismatch")
            require(len(manifest["assets"]) == 24
                    and {asset["id"] for asset in manifest["assets"]} == {asset["id"] for asset in kit["assets"]},
                    f"{path}: stale authored asset inventory")
            source = docs / "sources" / style["id"] / f"{kit['id']}.png"
            require(source.is_file(), f"{path}: source atlas is missing")
            source_hash = digest(source)
            require(all(asset["source"]["sha256"] == source_hash for asset in manifest["assets"]),
                    f"{path}: stale source hash")
            for name in archive_files(manifest) | {manifest["download"]}:
                require(safe_path(directory, name).is_file(), f"Catalog link missing: {directory / name}")
            base = f"{style['id']}/{kit['id']}/"
            variants[style["id"]] = {"manifest": base + "manifest.json",
                                      "download": base + manifest["download"],
                                      "contactSheet": base + manifest["contactSheet"]}
        kits.append({"id": kit["id"], "title": kit["title"], "books": kit["books"], "variants": variants})
    return {"schemaVersion": 1, "title": inventory["title"], "scope": inventory.get("scope", ""),
            "styles": inventory["styles"], "books": inventory["books"],
            "locations": coverage["locations"], "sources": coverage.get("sources", []),
            "coverageGaps": coverage.get("coverageGaps", []), "kits": kits}


def run(style_id=None, check=False, catalog=False, docs=DOCS, output=OUTPUT, kit_id=None):
    inventory = read_inventory(docs)
    require(kit_id is None or style_id is not None, "--kit requires --style")
    kits = inventory["kits"] if kit_id is None else [kit for kit in inventory["kits"] if kit["id"] == kit_id]
    require(kit_id is None or kits, f"Unknown kit: {kit_id}")
    styles = inventory["styles"] if style_id == "all" else [s for s in inventory["styles"] if s["id"] == style_id]
    require(style_id is None or styles, f"Unknown style: {style_id}")
    total = 0
    for style in styles:
        crops = reviewed_crops(docs, style)
        known_kits = {kit["id"] for kit in inventory["kits"]}
        require(set(crops) <= known_kits and (set(crops) == known_kits if kit_id is None else kit_id in crops),
                f"{style['id']}: crop kit coverage mismatch")
        seen = set()
        for kit in kits:
            manifest, sprites = prepare_kit(docs, kit, style, crops)
            fingerprints = {visible_digest(sprite) for sprite in sprites.values()}
            require(not seen.intersection(fingerprints), f"{style['id']}/{kit['id']}: repeated visible asset across kits")
            seen.update(fingerprints)
            directory = output / style["id"] / kit["id"]
            if not check:
                build_kit(directory, manifest, sprites, style)
            validate_kit(directory, manifest, sprites, style)
            total += len(sprites)
    if catalog:
        expected = catalog_document(inventory, read_json(docs / "coverage.json"), output, docs)
        path = output / "catalog.json"
        if check:
            require(read_json(path) == expected, "Stale catalog or broken catalog links")
        else:
            output.mkdir(parents=True, exist_ok=True)
            path.write_bytes(json_bytes(expected))
    return total


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--style", help="style ID or all")
    parser.add_argument("--kit", help="incrementally build/check one kit; permits partial style crop sheets")
    parser.add_argument("--check", action="store_true", help="read-only exact source reconstruction and validation")
    parser.add_argument("--catalog", action="store_true", help="aggregate completed per-style kit manifests")
    args = parser.parse_args(argv)
    if not (args.style or args.catalog):
        parser.error("provide --style or --catalog")
    try:
        total = run(args.style, args.check, args.catalog, kit_id=args.kit)
    except (PackError, OSError, KeyError, TypeError, json.JSONDecodeError, BadZipFile) as error:
        print(f"Book tiles: {error}", file=sys.stderr)
        return 1
    print(f"{'Validated' if args.check else 'Built'} {total} normalized component PNGs" + (" and catalog" if args.catalog else ""))
    return 0


if __name__ == "__main__":
    sys.exit(main())
