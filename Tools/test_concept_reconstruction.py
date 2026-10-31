#!/usr/bin/env python3
"""Independently verify exported fragment coverage/replay. Semantic review stays separate."""

import argparse, hashlib, io, json, zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def verify(manifest_path):
    m = json.loads(manifest_path.read_text())
    base = manifest_path.parent
    width, height = m["canvas"]
    assert [width, height] == [1536, 1024]
    coverage = np.zeros((height, width), np.uint16)
    replay = np.zeros((height, width, 3), np.uint8)
    ids = set()
    files = {}
    for layer in m["layers"]:
        ident = layer["id"]
        assert ident not in ids, f"duplicate {ident}"
        ids.add(ident)
        assert layer.get("label") and layer.get("category"), ident
        if not layer.get("file"):
            assert (
                layer["visiblePixels"] == 0 and layer["visibility"] == "fully occluded"
            ), ident
            continue
        assert (
            hashlib.sha256((base / layer["file"]).read_bytes()).hexdigest()
            == layer["componentSha256"]
        ), f"component digest {ident}"
        im = Image.open(base / layer["file"]).convert("RGBA")
        a = np.asarray(im)
        x, y = layer["offset"]
        w, h = layer["size"]
        assert (
            im.size == (w, h)
            and x >= 0
            and y >= 0
            and x + w <= width
            and y + h <= height
        ), ident
        assert set(np.unique(a[:, :, 3])).issubset(
            {0, 255}
        ), f"non-binary ownership {ident}"
        assert np.all(a[:, :, :3][a[:, :, 3] == 0] == 0), f"hidden RGB backing {ident}"
        mask = a[:, :, 3] > 0
        assert int(mask.sum()) == layer["visiblePixels"] > 0, ident
        assert (
            mask.any(axis=0)[0]
            and mask.any(axis=0)[-1]
            and mask.any(axis=1)[0]
            and mask.any(axis=1)[-1]
        ), f"non-tight bounds {ident}"
        assert (
            int(mask.sum()) < width * height * 0.4
        ), f"oversized reference fallback {ident}"
        assert layer["provenance"]["sourceSha256"] == m["sourceSha256"], ident
        coverage[y : y + h, x : x + w] += mask
        replay[y : y + h, x : x + w][mask] = a[:, :, :3][mask]
        files[layer["file"]] = (a, x, y)
    assert np.all(
        coverage == 1
    ), f"coverage gaps={int((coverage==0).sum())}, overlaps={int((coverage>1).sum())}"
    # Original is opened only after independent reconstruction, for comparison.
    source = ROOT / m["source"]
    assert hashlib.sha256(source.read_bytes()).hexdigest() == m["sourceSha256"]
    original = np.asarray(Image.open(source).convert("RGB"))
    assert original.shape == replay.shape
    changed = int(np.any(np.bitwise_xor(original, replay), axis=2).sum())
    assert changed == 0, f"{changed} changed pixels"
    assert np.array_equal(
        np.asarray(Image.open(base / "reconstructed.png").convert("RGB")), replay
    )
    ora_replay = np.zeros_like(replay)
    ora_coverage = np.zeros_like(coverage)
    with zipfile.ZipFile(base / "combat-concept.ora") as z:
        tree = ET.fromstring(z.read("stack.xml"))
        assert [int(tree.attrib[k]) for k in ("w", "h")] == [width, height]
        seen = set()
        for node in reversed(list(tree.iter("layer"))):
            name = node.attrib["src"]
            seen.add(name)
            a = np.asarray(Image.open(io.BytesIO(z.read(name))).convert("RGBA"))
            x = int(node.attrib.get("x", 0))
            y = int(node.attrib.get("y", 0))
            h, w = a.shape[:2]
            mask = a[:, :, 3] > 0
            assert (
                name in files
                and np.array_equal(a, files[name][0])
                and (x, y) == files[name][1:]
            )
            ora_replay[y : y + h, x : x + w][mask] = a[:, :, :3][mask]
            ora_coverage[y : y + h, x : x + w] += mask
        assert seen == set(files)
        assert np.array_equal(
            np.asarray(
                Image.open(io.BytesIO(z.read("mergedimage.png"))).convert("RGB")
            ),
            ora_replay,
        )
    assert np.array_equal(ora_replay, replay) and np.all(ora_coverage == 1)
    bundle = base / "combat-concept-components.zip"
    if bundle.exists():
        with zipfile.ZipFile(bundle) as z:
            names = set(z.namelist())
            assert "manifest.json" in names
            bundled = json.loads(z.read("manifest.json"))
            assert bundled == m
            for name in files:
                assert (
                    z.read(name) == (base / name).read_bytes()
                ), f"ZIP component differs: {name}"
            assert not any(
                name.endswith("combat-concept.png") for name in names
            ), "reference image inside component ZIP"
    procedural = []
    for path in sorted((base / "procedural").glob("room-*.json")):
        data = json.loads(path.read_text())
        grid = data["grid"]
        start = tuple(data["entrance"]["cell"])
        end = tuple(data["exit"]["cell"])
        seen = {start}
        pending = [start]
        while pending:
            x, y = pending.pop()
            for nx, ny in ((x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)):
                if (
                    0 <= ny < len(grid)
                    and 0 <= nx < len(grid[0])
                    and grid[ny][nx] not in ("wall", "water")
                    and (nx, ny) not in seen
                ):
                    seen.add((nx, ny))
                    pending.append((nx, ny))
        walkable = {
            (x, y)
            for y, row in enumerate(grid)
            for x, kind in enumerate(row)
            if kind not in ("wall", "water")
        }
        assert seen == walkable and end in seen, f"disconnected room {path}"
        actors = [p for p in data["placements"] if "component" in p]
        assert all(
            tuple(p["cell"]) in seen for p in actors
        ), f"unreachable actor {path}"
        assert len({tuple(p["cell"]) for p in actors}) == len(
            actors
        ), f"overlapping actor cells {path}"
        procedural.append(
            {
                "seed": data["seed"],
                "reachableCells": len(seen),
                "placedComponents": len(actors),
            }
        )
    return {
        "rasterVerdict": "PASS",
        "sourceSha256": m["sourceSha256"],
        "layers": len(ids),
        "visibleLayers": len(files),
        "pixelsCoveredExactlyOnce": width * height,
        "xorChangedPixels": changed,
        "oraReplay": "PASS",
        "proceduralConnectivity": procedural,
        "semanticVerdict": "REQUIRES SEPARATE VISUAL REVIEW; pixel equality cannot establish semantic ownership",
    }


if __name__ == "__main__":
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument(
        "--manifest",
        type=Path,
        default=ROOT / "Web/wwwroot/assets/concept-reconstruction/manifest.json",
    )
    a = p.parse_args()
    print(json.dumps(verify(a.manifest), indent=2))
