#!/usr/bin/env python3
"""Replay visible source fragments, with explicit semantic ownership and no residual layer."""

import argparse, hashlib, io, json, zipfile
from pathlib import Path
from xml.etree.ElementTree import Element, SubElement, tostring
import numpy as np
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "Web/wwwroot/assets/broadcast-kit/combat-concept.png"
OUT = ROOT / "Web/wwwroot/assets/concept-reconstruction"


def mask_for(region, canvas, base):
    shape = region["shape"]
    mask = Image.new("L", canvas)
    if shape["type"] == "rect":
        x, y, w, h = shape["bounds"]
        ImageDraw.Draw(mask).rectangle((x, y, x + w - 1, y + h - 1), fill=255)
    elif shape["type"] == "polygon":
        ImageDraw.Draw(mask).polygon(shape["points"], fill=255)
    elif shape["type"] == "mask":
        path = Path(shape["src"])
        candidates = [base / path, OUT / path, ROOT / path]
        path = next((p for p in candidates if p.exists()), candidates[0])
        part = Image.open(path).convert("L")
        if part.size == canvas:
            return np.array(part) > 0
        x, y, w, h = shape["bounds"]
        if part.size != (w, h):
            raise ValueError(f'{region["id"]}: mask dimensions differ from bounds')
        mask.paste(part, (x, y))
    else:
        raise ValueError(f"Unknown shape: {shape}")
    return np.array(mask) > 0


def save_png(im, path):
    path.parent.mkdir(parents=True, exist_ok=True)
    im.save(path)


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--source", type=Path, default=SOURCE)
    p.add_argument("--out", type=Path, default=OUT)
    p.add_argument("--regions", type=Path, nargs="+")
    args = p.parse_args()
    files = args.regions or sorted(
        (ROOT / "Docs/ConceptReconstruction").glob("*-regions.json")
    )
    source = Image.open(args.source).convert("RGB")
    pixels = np.array(source)
    w, h = source.size
    regions = []
    for file in files:
        doc = json.loads(file.read_text())
        assert doc["canvas"] == [w, h]
        for r in doc["regions"]:
            regions.append((r, file.parent))
    if not regions:
        raise SystemExit("No semantic region annotations supplied")
    ids = [r["id"] for r, _ in regions]
    if len(ids) != len(set(ids)):
        raise ValueError("Region IDs must be unique")
    owner = np.full((h, w), -1, dtype=np.int32)
    for index, (r, base) in sorted(
        enumerate(regions), key=lambda pair: (pair[1][0].get("priority", 0), pair[0])
    ):
        owner[mask_for(r, (w, h), base)] = index
    out = args.out
    out.mkdir(parents=True, exist_ok=True)
    missing = owner < 0
    save_png(
        Image.fromarray((missing * 255).astype("uint8")), out / "unassigned-mask.png"
    )
    manifest = {
        "schemaVersion": 1,
        "canvas": [w, h],
        "source": (
            str(args.source.relative_to(ROOT))
            if args.source.is_relative_to(ROOT)
            else str(args.source)
        ),
        "sourceSha256": hashlib.sha256(args.source.read_bytes()).hexdigest(),
        "representation": "visible source fragments; occluded pixels are absent, not inferred",
        "layers": [],
        "unassignedPixels": int(missing.sum()),
        "annotationInputs": [
            {
                "path": str(f.relative_to(ROOT)) if f.is_relative_to(ROOT) else str(f),
                "sha256": hashlib.sha256(f.read_bytes()).hexdigest(),
            }
            for f in files
        ],
    }
    replay = np.zeros_like(pixels)
    coverage = np.zeros_like(pixels)
    ora = Element("image", {"w": str(w), "h": str(h), "name": "Literal combat concept"})
    stack = SubElement(ora, "stack")
    groups = {}
    atlas = {}
    with zipfile.ZipFile(out / "combat-concept.ora", "w") as z:
        z.writestr("mimetype", "image/openraster", compress_type=zipfile.ZIP_STORED)
        for index, (r, _) in enumerate(regions):
            mask = owner == index
            ys, xs = np.where(mask)
            if not len(xs):
                manifest["layers"].append(
                    {**r, "visiblePixels": 0, "visibility": "fully occluded"}
                )
                continue
            x, y, x2, y2 = (
                int(xs.min()),
                int(ys.min()),
                int(xs.max() + 1),
                int(ys.max() + 1),
            )
            rgba = np.dstack(
                (pixels[y:y2, x:x2], mask[y:y2, x:x2].astype("uint8") * 255)
            )
            rgba[rgba[:, :, 3] == 0, :3] = 0
            im = Image.fromarray(rgba)
            rel = f'components/{r["category"]}/{r["id"]}.png'
            save_png(im, out / rel)
            entry = {
                **r,
                "file": rel,
                "componentSha256": hashlib.sha256((out / rel).read_bytes()).hexdigest(),
                "offset": [x, y],
                "size": [x2 - x, y2 - y],
                "z": r.get("priority", 0),
                "visiblePixels": int(mask.sum()),
                "visibility": "visible fragment",
                "provenance": {
                    "kind": "literal-source-pixels",
                    "sourceSha256": manifest["sourceSha256"],
                    "hiddenPixels": "not reconstructed",
                },
            }
            manifest["layers"].append(entry)
            replay[mask] = pixels[mask]
            color = hashlib.sha256(r["id"].encode()).digest()[:3]
            coverage[mask] = list(color)
            cat = r["category"]
            group = groups.get(cat)
            if group is None:
                group = SubElement(stack, "stack", {"name": cat})
                groups[cat] = group
            node = Element(
                "layer",
                {
                    "name": r.get("label", r["id"]),
                    "src": rel,
                    "x": str(x),
                    "y": str(y),
                    "opacity": "1.0",
                    "visibility": "visible",
                    "composite-op": "svg:src-over",
                },
            )
            group.insert(0, node)
            b = io.BytesIO()
            im.save(b, format="PNG")
            z.writestr(rel, b.getvalue())
            atlas.setdefault(cat, []).append((r["id"], im))
        z.writestr("stack.xml", tostring(ora, encoding="utf-8", xml_declaration=True))
        b = io.BytesIO()
        Image.fromarray(replay).save(b, format="PNG")
        z.writestr("mergedimage.png", b.getvalue())
    save_png(Image.fromarray(replay), out / "reconstructed.png")
    save_png(Image.fromarray(coverage), out / "coverage-map.png")
    diff = np.abs(pixels.astype("int16") - replay.astype("int16")).astype("uint8")
    save_png(Image.fromarray(diff), out / "diff.png")
    manifest["changedPixels"] = int(np.any(diff, axis=2).sum())
    manifest["maxChannelError"] = int(diff.max())
    stats = {}
    for cat, items in atlas.items():
        stats[cat] = {
            "componentCount": len(items),
            "visiblePixels": sum(
                e["visiblePixels"] for e in manifest["layers"] if e["category"] == cat
            ),
        }
        cellw, cellh = 180, 150
        sheet = Image.new(
            "RGB", (cellw * 6, cellh * ((len(items) + 5) // 6)), (30, 33, 40)
        )
        draw = ImageDraw.Draw(sheet)
        for i, (name, im) in enumerate(items):
            thumb = im.copy()
            thumb.thumbnail((170, 122))
            x = (i % 6) * cellw
            y = (i // 6) * cellh
            sheet.paste(thumb, (x, y), thumb)
            draw.text((x + 3, y + 125), name[:27], fill="white")
        save_png(sheet, out / f"atlases/{cat}.png")
    # Prune only exporter-owned obsolete PNGs; annotation masks belong to their authors.
    retained = {
        (out / l["file"]).resolve() for l in manifest["layers"] if l.get("file")
    }
    if (out / "components").exists():
        for old in (out / "components").rglob("*.png"):
            if old.resolve() not in retained:
                old.unlink()
    retainedAtlases = {(out / f"atlases/{cat}.png").resolve() for cat in atlas}
    if (out / "atlases").exists():
        for old in (out / "atlases").glob("*.png"):
            if old.resolve() not in retainedAtlases:
                old.unlink()
    manifest["categoryStats"] = stats
    (out / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    (out / "stats.json").write_text(
        json.dumps(
            {
                k: manifest[k]
                for k in [
                    "sourceSha256",
                    "unassignedPixels",
                    "changedPixels",
                    "maxChannelError",
                    "categoryStats",
                ]
            },
            indent=2,
        )
        + "\n"
    )
    # Portable component-only delivery: no duplicate atlases, ORA or reference image.
    with zipfile.ZipFile(
        out / "combat-concept-components.zip", "w", compression=zipfile.ZIP_DEFLATED
    ) as bundle:
        bundle.write(out / "manifest.json", "manifest.json")
        for layer in manifest["layers"]:
            if layer.get("file"):
                if (
                    hashlib.sha256((out / layer["file"]).read_bytes()).hexdigest()
                    != layer["componentSha256"]
                ):
                    raise ValueError("Component hash changed before archive")
                bundle.write(out / layer["file"], layer["file"])
        bundle.writestr(
            "source.json",
            json.dumps(
                {
                    "path": manifest["source"],
                    "sha256": manifest["sourceSha256"],
                    "canvas": manifest["canvas"],
                    "representation": manifest["representation"],
                },
                indent=2,
            )
            + "\n",
        )
        bundle.writestr(
            "README.txt",
            "Literal combat-concept visible fragments\n\nPlace every RGBA PNG at manifest offset; masks partition all source pixels. Alpha is binary source ownership, preserving original edge RGB. Fragments contain no invented hidden pixels. Text remains raster, with editable transcription in the manifest. These are source-visible fragments, not clean independent sprites. Procedural variants and their normalized source samples are separately labeled derived assets.\n",
        )
        recipe = ROOT / "Docs/ConceptReconstruction/procedural-recipe.json"
        if recipe.exists():
            bundle.write(recipe, "procedural-recipe.json")
    print(
        json.dumps(
            {
                "regions": len(regions),
                "unassignedPixels": manifest["unassignedPixels"],
                "changedPixels": manifest["changedPixels"],
                "output": str(out),
            }
        )
    )
    if manifest["unassignedPixels"] or manifest["changedPixels"]:
        raise SystemExit(1)


if __name__ == "__main__":
    main()
