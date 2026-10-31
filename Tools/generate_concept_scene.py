#!/usr/bin/env python3
"""Seeded connected tactical rooms; normalized source samples are derived assets, separate from replay."""

import argparse, json, random
from collections import deque
from pathlib import Path
from PIL import Image, ImageDraw

ROOT = Path(__file__).resolve().parents[1]
ASSETS = ROOT / "Web/wwwroot/assets/concept-reconstruction"
RECIPE = ROOT / "Docs/ConceptReconstruction/procedural-recipe.json"


def reachable(grid, start):
    seen = {start}
    queue = deque([start])
    while queue:
        x, y = queue.popleft()
        for nx, ny in [(x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)]:
            if (
                0 <= ny < len(grid)
                and 0 <= nx < len(grid[0])
                and grid[ny][nx] not in ["wall", "water"]
                and (nx, ny) not in seen
            ):
                seen.add((nx, ny))
                queue.append((nx, ny))
    return seen


def main():
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--seed", type=int, nargs="+", default=[7, 29, 103])
    p.add_argument("--out", type=Path, default=ASSETS / "procedural")
    args = p.parse_args()
    recipe = json.loads(RECIPE.read_text())
    source = Image.open(ROOT / recipe["source"]).convert("RGBA")
    manifest = json.loads((ASSETS / "manifest.json").read_text())
    layers = {l["id"]: l for l in manifest["layers"] if l.get("file")}
    args.out.mkdir(parents=True, exist_ok=True)
    samples = {}
    for key, b in recipe["samples"].items():
        x, y, w, h = b
        samples[key] = source.crop((x, y, x + w, y + h)).resize(
            (72, 72), Image.Resampling.NEAREST
        )
    reusableOut = args.out / "reusable"
    reusableOut.mkdir(parents=True, exist_ok=True)
    for key, im in samples.items():
        im.save(reusableOut / (key + ".png"))
    (reusableOut / "provenance.json").write_text(
        json.dumps(
            {
                "sourceSha256": manifest["sourceSha256"],
                "kind": "derived normalized visible samples",
                "tileSourceBounds": recipe["samples"],
                "actors": "Source body masks plus parented edge fragments; approximate silhouettes, no hidden-pixel inference.",
                "ui": "Exact source fragments; fixed raster text and values.",
            },
            indent=2,
        )
        + "\n"
    )

    def component(name, maxsize):
        base = layers[name]
        children = [l for l in layers.values() if l.get("parentId") == name]
        parts = [base] + children
        x = min(l["offset"][0] for l in parts)
        y = min(l["offset"][1] for l in parts)
        right = max(l["offset"][0] + l["size"][0] for l in parts)
        bottom = max(l["offset"][1] + l["size"][1] for l in parts)
        im = Image.new("RGBA", (right - x, bottom - y))
        for l in parts:
            im.alpha_composite(
                Image.open(ASSETS / l["file"]).convert("RGBA"),
                (l["offset"][0] - x, l["offset"][1] - y),
            )
        im.thumbnail(maxsize)
        im.save(reusableOut / (name + ".png"))
        return im

    # Fixed source composition grammar: exact raster UI template over generated map.
    # The scene remains generated; no flattened source background is used.
    for seed in args.seed:
        rng = random.Random(seed)
        tile = 72
        cols, rows = 12, 8
        left, top = 350, 210
        image = Image.new("RGBA", (1536, 1024), (4, 13, 25, 255))
        draw = ImageDraw.Draw(image)
        wall = samples["wall"]
        dry = [samples["floor1"], samples["floor2"]]
        water = samples["water"]
        for y in range(0, 1024, tile):
            for x in range(0, 1536, tile):
                image.alpha_composite(wall, (x, y))
        grid = [["floor"] * cols for _ in range(rows)]
        exitx = 9
        entrance = (rng.choice([3, 5, 7]), rows - 1)
        exitcell = (exitx, 0)
        # A contiguous side channel varies in width and side, never a wet/dry checkerboard.
        channelSide = rng.choice(["west", "east"])
        channelWidth = rng.choice([1, 2])
        for y in range(rows):
            for x in range(cols):
                if (
                    x < channelWidth
                    if channelSide == "west"
                    else x >= cols - channelWidth
                ):
                    grid[y][x] = "water"
        for _ in range(5 + seed % 4):
            x, y = rng.randint(2, cols - 3), rng.randint(2, rows - 3)
            if (x, y) in [entrance, exitcell] or grid[y][x] != "floor":
                continue
            grid[y][x] = "wall"
            seen = reachable(grid, entrance)
            if exitcell not in seen or len(seen) != sum(
                c not in ["wall", "water"] for row in grid for c in row
            ):
                grid[y][x] = "floor"
        grid[exitcell[1]][exitcell[0]] = "exit"
        grid[entrance[1]][entrance[0]] = "entrance"
        placements = []
        for y, row in enumerate(grid):
            for x, kind in enumerate(row):
                sample = (
                    wall
                    if kind == "wall"
                    else water if kind == "water" else dry[(x + y + seed) % 2]
                )
                image.alpha_composite(sample, (left + x * tile, top + y * tile))
                placements.append({"kind": kind, "cell": [x, y]})
        # Heavy source masonry border and actual source exit architecture at its authored location.
        for y in range(top, top + rows * tile, tile):
            image.alpha_composite(wall, (left - tile, y))
            image.alpha_composite(wall, (left + cols * tile, y))
        for layer in sorted(layers.values(), key=lambda l: l.get("z", 0)):
            if layer["id"].startswith("exit-") and layer["category"] not in [
                "floor-reflection"
            ]:
                image.alpha_composite(
                    Image.open(ASSETS / layer["file"]).convert("RGBA"),
                    tuple(layer["offset"]),
                )
        # Boundary grammar: source mechanical console, segmented pipes and vines
        # break up masonry only outside the generated floor; never stamp scene composites.
        boundaryCategories = {"machine-panel", "pipe-tube", "pipe-joint", "vines"}
        for layer in sorted(layers.values(), key=lambda l: l.get("z", 0)):
            x, y = layer["offset"]
            w, h = layer["size"]
            if layer["category"] in boundaryCategories and (
                y + h <= 210
                or (x > 1450 and layer["category"] in {"pipe-tube", "pipe-joint"})
            ):
                image.alpha_composite(
                    Image.open(ASSETS / layer["file"]).convert("RGBA"), (x, y)
                )
        # Source torches keep their own raster pixels, architectural door and lighting coherent.
        threshold = component("exit-threshold-grille", (70, 50))
        image.alpha_composite(
            threshold, (left + entrance[0] * tile, top + rows * tile - 45)
        )
        cells = [
            (x, y)
            for y in range(1, rows - 1)
            for x in range(1, cols - 1)
            if grid[y][x] == "floor"
        ]
        rng.shuffle(cells)
        spaced = []
        for cell in cells:
            if all(abs(cell[0] - o[0]) + abs(cell[1] - o[1]) >= 3 for o in spaced):
                spaced.append(cell)
        names = [
            "carl-body",
            "donut-body",
            "katia-body",
            "mongo-body",
            "rat-east-body",
            "rat-south-body",
        ]
        rng.shuffle(names)
        actors = []
        for name, (x, y) in zip(names, spaced):
            sprite = component(name, (110, 128))
            pos = (
                left + x * tile + (tile - sprite.width) // 2,
                top + (y + 1) * tile - sprite.height,
            )
            actors.append((y, name, x, sprite, pos))
            placements.append(
                {
                    "component": name,
                    "cell": [x, y],
                    "provenance": "derived source-visible body plus parented fringes; no inferred hidden pixels",
                }
            )
        draw = ImageDraw.Draw(image)
        if actors:
            y, name, x, _, _ = next(
                (a for a in actors if a[1] == "carl-body"), actors[0]
            )
            draw.rectangle(
                (
                    left + x * tile + 2,
                    top + y * tile + 2,
                    left + (x + 1) * tile - 3,
                    top + (y + 1) * tile - 3,
                ),
                outline="#ffe468",
                width=4,
            )
        for y, name, x, sprite, pos in sorted(actors):
            image.alpha_composite(sprite, pos)
        draw = ImageDraw.Draw(image)
        for y, name, x, sprite, pos in actors:
            bx = left + x * tile + 8
            by = pos[1] - 12
            draw.rectangle(
                (bx, by, bx + 56, by + 10), fill="#071018", outline="#020509", width=2
            )
            draw.rectangle(
                (bx + 2, by + 2, bx + rng.randint(32, 53), by + 7),
                fill="#ef4961" if "rat" in name else "#38d89a",
            )
        # Controlled props stay on open cells and remain distinct semantic components.
        for name, cell in zip(
            ["explosive-barrel", "east-crate-upper"],
            spaced[len(actors) : len(actors) + 2],
        ):
            if name in layers:
                prop = component(name, (70, 90))
                x, y = cell
                image.alpha_composite(
                    prop, (left + x * tile, top + (y + 1) * tile - prop.height)
                )
                placements.append({"component": name, "cell": list(cell)})
        # UI ownership comes only from authored UI region IDs; never infer it from
        # world coordinates or broad categories that may change after annotation edits.
        uiDoc = json.loads(
            (ROOT / "Docs/ConceptReconstruction/ui-regions.json").read_text()
        )
        uiIds = {
            r["id"]
            for r in uiDoc["regions"]
            if not r["category"].startswith("world-")
            and (
                layers.get(r["id"], {}).get("offset", [0, 0])[1] >= 747
                or r["id"].startswith(("objective-", "phase-"))
            )
        }
        for layer in sorted(layers.values(), key=lambda l: l.get("z", 0)):
            if layer["id"] in uiIds:
                image.alpha_composite(
                    Image.open(ASSETS / layer["file"]).convert("RGBA"),
                    tuple(layer["offset"]),
                )
        image.convert("RGB").save(args.out / f"room-{seed}.png")
        seen = reachable(grid, entrance)
        data = {
            "schemaVersion": 1,
            "seed": seed,
            "grid": grid,
            "tileSize": tile,
            "boardOffset": [left, top],
            "entrance": {"cell": list(entrance), "tags": ["entrance", "walkable"]},
            "exit": {"cell": list(exitcell), "tags": ["exit", "walkable"]},
            "connectivity": {
                "allWalkableConnected": len(seen)
                == sum(c not in ["wall", "water"] for row in grid for c in row),
                "entranceToExit": exitcell in seen,
            },
            "channel": {
                "side": channelSide,
                "width": channelWidth,
                "contiguous": True,
                "walkable": False,
            },
            "placements": placements,
            "layerOrder": [
                "masonry",
                "dry-floor/contiguous-water",
                "exit-architecture",
                "selection",
                "actors-by-foot-y",
                "health-bars",
                "props",
                "fixed-source-raster-UI",
            ],
            "recipe": "procedural-recipe.json",
            "note": "Derived layout with source-visible normalized samples and exact fixed raster UI values. No inferred hidden assets. Raster UI text remains fixed to source values.",
        }
        (args.out / f"room-{seed}.json").write_text(json.dumps(data, indent=2) + "\n")
        print(f'Generated room-{seed}.png, connected={data["connectivity"]}')


if __name__ == "__main__":
    main()
