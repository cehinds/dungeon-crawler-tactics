#!/usr/bin/env python3
"""Independently verify exported fragment coverage/replay. Semantic review stays separate."""

import argparse, hashlib, io, json, zipfile
from pathlib import Path
from xml.etree import ElementTree as ET
import numpy as np
from PIL import Image

ROOT = Path(__file__).resolve().parents[1]


def verify_room(data, recipe, catalog):
    """Check published geometry without trusting engine validation flags."""
    grid = data["grid"]
    board = recipe["board"]
    assert len(grid) == board["rows"] and all(len(row) == board["columns"] for row in grid), "nonrectangular room"
    assert set(sum(grid, [])) <= {"floor", "water", "wall", "entrance", "exit"}, "unknown grid vocabulary"
    for name in ("entrance", "exit"):
        x, y = data[name]["cell"]
        assert grid[y][x] == name, "portal marker mismatch"
    walkable = {(x,y) for y,row in enumerate(grid) for x,v in enumerate(row) if v not in ("wall", "water")}
    pending = [tuple(data["entrance"]["cell"])]; seen = set(pending)
    while pending:
        x,y = pending.pop()
        for cell in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
            if cell in walkable and cell not in seen:
                seen.add(cell); pending.append(cell)
    assert seen == walkable and tuple(data["exit"]["cell"]) in seen, "disconnected room"
    fixed = catalog["fixedHudState"]
    state = data["state"]
    expected_state = {"selectedId":fixed["selectedId"], "targetId":fixed["targetId"], "hp":fixed["hp"][0], "maxHp":fixed["hp"][1], "mana":fixed["mana"][0], "maxMana":fixed["mana"][1], "move":fixed["move"], "round":fixed["round"], "forecastDamage":fixed["forecastDamage"]}
    assert all(state.get(k) == value for k,value in expected_state.items()), "fixed raster HUD state mismatch"
    placements = data["placements"]
    expected = {e["id"]: e for e in recipe["entities"]}
    for field,asset_field in (("selectedId","selectedAssetId"),("targetId","targetAssetId")):
        assert next(p for p in placements if p["id"] == fixed[field])["assetId"] == fixed[asset_field], "fixed HUD identity art mismatch"
    assert len(placements) == len(expected) and {p["id"] for p in placements} == set(expected), "entity count/identity"
    assert len({tuple(p["cell"]) for p in placements}) == len(placements), "overlapping entities"
    for i,p in enumerate(placements):
        assert tuple(p["cell"]) in seen, "unreachable entity"
        assert all(p.get(k) == expected[p["id"]].get(k) for k in ("assetId", "kind", "hp", "maxHp")), "entity contract"
        for q in placements[i+1:]:
            assert sum(abs(a-b) for a,b in zip(p["cell"],q["cell"])) >= recipe["constraints"]["entitySpacing"], "entity spacing"
    assets = catalog["assets"]
    assets = {a["id"]:a for a in assets} if isinstance(assets,list) else assets
    plan = data["drawPlan"]
    entities = [d for d in plan if d.get("entityId")]
    assert len(entities) == len(placements) and {d["entityId"] for d in entities} == set(expected), "draw entity cardinality"
    assert [d["footY"] for d in entities] == sorted(d["footY"] for d in entities), "entity depth order"
    assert [d["layer"] for d in plan] == sorted(d["layer"] for d in plan), "layer order"
    for d in plan:
        assert d.get("assetId") in assets or d.get("primitive") == "rect", "unknown draw asset"
        assert d["width"] > 0 and d["height"] > 0, "empty draw bounds"
        if d["layer"] < 100:
            assert d["y"] + d["height"] <= recipe["uiBounds"]["y"], "draw overlaps HUD"
    floor = {tuple(d["cell"]):d for d in plan if d["layer"] == 10 and d.get("cell") and grid[d["cell"][1]][d["cell"][0]] != "water"}
    assert len([d for d in plan if d["layer"] == 10 and d.get("cell")]) == board["rows"]*board["columns"], "tile cardinality"
    for (x,y),d in floor.items():
        for dx,dy,edge,opposite in ((1,0,"east","west"),(0,1,"south","north")):
            neighbor = floor.get((x+dx,y+dy))
            if neighbor:
                assert assets[d["assetId"]]["edgeTags"][edge] == assets[neighbor["assetId"]]["edgeTags"][opposite], "incompatible floor edge"
    water = {(x,y) for y,row in enumerate(grid) for x,v in enumerate(row) if v == "water"}
    assert len(water) == board["rows"] and len({x for x,y in water}) == 1, "broken water channel"
    side = data["channel"]["side"]
    water_x = 0 if side == "west" else board["columns"]-1
    assert water == {(water_x,y) for y in range(board["rows"])}, "water side mismatch"
    roles = dict(catalog.get("roles", {}), **recipe.get("roles", {}))
    bank_role = "bankEastVariants" if side == "west" else "bankWestVariants"
    bank_ids = roles[bank_role]
    bank_ids = bank_ids if isinstance(bank_ids,list) else [bank_ids]
    banks = [d for d in plan if d["layer"] == 11]
    assert len(banks) == board["rows"] and {tuple(d["cell"]) for d in banks} == water, "missing/displaced water bank"
    assert all(d["assetId"] in bank_ids and d["tileRole"] == bank_role for d in banks), "wrong bank orientation"
    sockets = recipe["edgeRules"]["roleSockets"]
    pairs = {frozenset(pair) for pair in recipe["edgeRules"]["allowedPairs"]}
    terrain = {}
    for d in plan:
        if d.get("cell") is None or not d.get("tileRole"): continue
        role = d["tileRole"]
        assert role in sockets, "undeclared tile role"
        ids = roles[role]; ids = ids if isinstance(ids,list) else [ids]
        assert d["assetId"] in ids, "asset outside declared role"
        assert assets[d["assetId"]]["edgeTags"] == sockets[role], "asset sockets disagree with role"
        if d["layer"] in (10,11,20):terrain[tuple(d["cell"])] = d
    for d in plan:
        if d["layer"] != 22: continue
        x,y = d["cell"]
        assert any(p["layer"] == 20 and p.get("cell") == d["cell"] for p in plan), "cap/corner lacks wall underlay"
        native = assets[d["assetId"]].get("size") or [assets[d["assetId"]]["width"],assets[d["assetId"]]["height"]]
        if d.get("sourceRect"):
            sx,sy,sw,sh = d["sourceRect"]
            assert sx >= 0 and sy >= 0 and sx+sw <= native[0] and sy+sh <= native[1], "invalid source crop"
            assert [d["width"],d["height"]] == [sw,sh], "squashed boundary crop"
        else:
            assert [d["width"],d["height"]] == native, "stretched cap/corner"
        if x in (-1,board["columns"]) and y in (-1,board["rows"]):
            expected_role = "wallCorner" + ("N" if y == -1 else "S") + ("W" if x == -1 else "E")
            assert d["tileRole"] == expected_role, "wrong wall corner orientation"
    for (x,y),d in terrain.items():
        for dx,dy,edge,opposite in ((1,0,"east","west"),(0,1,"south","north")):
            neighbor = terrain.get((x+dx,y+dy))
            if neighbor:
                first = assets[d["assetId"]]["edgeTags"][edge]
                second = assets[neighbor["assetId"]]["edgeTags"][opposite]
                assert first == second or frozenset((first,second)) in pairs, "incompatible terrain sockets"
    for name in ("entrance", "exit"):
        ds = [d for d in plan if d.get("portal") == name]
        assert len(ds) == 1, "portal draw cardinality"
        d = ds[0]; asset = assets[d["assetId"]]
        anchor = asset["anchor"]
        assert [d["x"]+anchor[0],d["y"]+anchor[1]] == d["threshold"], "portal anchor alignment"
    return {"seed":data["seed"], "reachableCells":len(seen), "entities":len(placements)}


def verify(manifest_path, mask_root=None):
    m = json.loads(manifest_path.read_text())
    base = manifest_path.parent
    for name in m.get("requiredArtifacts", ["combat-concept-components.zip", "combat-concept.ora", "reconstructed.png", "diff.png", "coverage-map.png"]):
        assert (base / name).is_file(), f"required artifact missing: {name}"
    assert m.get("annotationInputs") and m.get("maskInputs"), "missing authored-input digests"
    for entry in m["annotationInputs"]:
        path = ROOT / entry["path"]
        assert hashlib.sha256(path.read_bytes()).hexdigest() == entry["sha256"], f"annotation digest {path}"
    assert {e["regionId"] for e in m["maskInputs"]} == {l["id"] for l in m["layers"] if l["shape"]["type"] == "mask"}, "incomplete mask input inventory"
    for entry in m["maskInputs"]:
        candidates = [base / entry["src"]]
        if mask_root is not None:
            candidates.insert(0, Path(mask_root) / entry["src"])
        candidates += [(ROOT / a["path"]).parent / entry["src"] for a in m.get("annotationInputs", [])]
        found = next((p for p in candidates if p.is_file()), None)
        assert found is not None, f"missing authored mask {entry['src']}"
        assert hashlib.sha256(found.read_bytes()).hexdigest() == entry["sha256"], f"mask digest {entry['regionId']}"
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
        parent_nodes = {child:parent for parent in tree.iter() for child in parent}
        groups_by_id = {node.attrib["id"]:node for node in tree.iter("stack") if "id" in node.attrib}
        layers_by_id = {layer["id"]:layer for layer in m["layers"]}
        for ident,group in groups_by_id.items():
            declared_parent = layers_by_id[ident].get("parentId")
            actual_parent = parent_nodes[group].attrib.get("id")
            assert actual_parent == declared_parent, f"ORA hierarchy differs: {ident}"
        for layer in m["layers"]:
            if not layer.get("file"): continue
            assert layer["id"] in groups_by_id, f"ORA semantic group missing: {layer['id']}"
            matching = [n for n in groups_by_id[layer["id"]] if n.tag == "layer" and n.attrib.get("src") == layer["file"]]
            assert len(matching) == 1, f"ORA own fragment missing: {layer['id']}"
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
    assert bundle.is_file(), "required component ZIP missing"
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
    recipe_path = base / "procedural/recipe.json"
    assert recipe_path.is_file(), "required procedural recipe missing"
    recipe = json.loads(recipe_path.read_text())
    catalog = json.loads((base / "derived/catalog.json").read_text())
    required_seeds = recipe.get("requiredSeeds", [7, 29, 103])
    for seed in required_seeds:
        assert (base / f"procedural/room-{seed}.json").is_file(), f"required room {seed} missing"
    for path in sorted((base / "procedural").glob("room-*.json")):
        data = json.loads(path.read_text())
        png = path.with_suffix(".png")
        assert png.is_file(), f"required room PNG missing: {png}"
        with Image.open(png) as image:
            assert image.size == (recipe["canvas"]["width"], recipe["canvas"]["height"]), "room PNG dimensions"
            image.verify()
        procedural.append(verify_room(data, recipe, catalog))
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
    p.add_argument("--mask-root", type=Path, help="Explicit authored mask root for isolated builds")
    a = p.parse_args()
    print(json.dumps(verify(a.manifest, a.mask_root), indent=2))
