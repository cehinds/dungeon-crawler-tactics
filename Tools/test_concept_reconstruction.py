#!/usr/bin/env python3
"""Independently verify exported fragment coverage/replay. Semantic review stays separate."""

import argparse, hashlib, io, json, math, zipfile
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
    # Props are solid obstacles; graph coverage must hold after removing them.
    prop_cells = {tuple(p["cell"]) for p in data["placements"] if p["kind"] == "prop"}
    navigable = walkable - prop_cells
    pending = [tuple(data["entrance"]["cell"])]; unblocked = set(pending)
    assert pending[0] in navigable, "prop blocks entrance"
    while pending:
        x,y = pending.pop()
        for cell in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
            if cell in navigable and cell not in unblocked:
                unblocked.add(cell); pending.append(cell)
    assert unblocked == navigable, "prop-obstructed navigation graph"
    assert tuple(data["exit"]["cell"]) in unblocked, "prop blocks exit"
    for p in data["placements"]:
        x,y = p["cell"]
        if p["kind"] == "actor":
            assert (x,y) in unblocked, "actor unreachable around props"
        else:
            assert any(c in unblocked for c in ((x-1,y),(x+1,y),(x,y-1),(x,y+1))), "inaccessible prop"
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
    for i,first in enumerate(entities):
        for second in entities[i+1:]:
            padding = recipe["constraints"]["entityArtPadding"]
            assert (first["x"]+first["width"]+padding <= second["x"] or second["x"]+second["width"]+padding <= first["x"]
                    or first["y"]+first["height"]+padding <= second["y"] or second["y"]+second["height"]+padding <= first["y"]), "entity art bounds overlap or lose readability padding"
    assert [d["layer"] for d in plan] == sorted(d["layer"] for d in plan), "layer order"
    for d in plan:
        assert d.get("assetId") in assets or d.get("primitive") == "rect", "unknown draw asset"
        assert d["width"] > 0 and d["height"] > 0, "empty draw bounds"
        if d["layer"] < 100:
            assert d["y"] + d["height"] <= recipe["uiBounds"]["y"], "draw overlaps HUD"
    floor = {tuple(d["cell"]):d for d in plan if d["layer"] == 10 and d.get("cell") and grid[d["cell"][1]][d["cell"][0]] != "water"}
    assert len([d for d in plan if d["layer"] == 10 and d.get("cell")]) == sum(v != "wall" for row in grid for v in row), "tile cardinality"
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
        assert y == -recipe["architecture"]["footprint"]["wallThickness"] or any(
            0 <= y+dy < board["rows"] and 0 <= x < board["columns"] and grid[y+dy][x] != "wall"
            for dy in (-1,1)), "decorative cap stripes a vertical masonry face"
        corner_neighbors = {"wallCornerNW":((0,1),(1,0)),"wallCornerNE":((0,1),(-1,0)),
                            "wallCornerSW":((0,-1),(1,0)),"wallCornerSE":((0,-1),(-1,0))}
        if d["tileRole"] in corner_neighbors:
            assert all(0 <= x+dx < board["columns"] and 0 <= y+dy < board["rows"]
                       and grid[y+dy][x+dx] != "wall" for dx,dy in corner_neighbors[d["tileRole"]]), "corner faces away from exposed room"
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
        native = asset.get("size") or [asset["width"],asset["height"]]
        crop_top = recipe["architecture"]["entrancePresentation"]["cropTop"] if name=="entrance" else 0
        assert 0 <= crop_top < native[1], "invalid authored portal crop"
        assert [d["width"],d["height"]] == [native[0],native[1]-crop_top], "portal native presentation bounds"
        assert d.get("sourceRect") == ([0,crop_top,native[0],native[1]-crop_top] if crop_top else None), "portal source crop mismatch"
        assert [d["x"]+anchor[0],d["y"]+anchor[1]-crop_top] == d["threshold"], "portal anchor alignment"
    # Each solid masonry cell belongs to the perimeter, including stepped bays;
    # an isolated pillar masquerading as a perimeter bay cannot satisfy this.
    masonry = {(x,y) for y,row in enumerate(grid) for x,v in enumerate(row) if v == "wall"}
    attached = {c for c in masonry if c[0] in (0,board["columns"]-1) or c[1] in (0,board["rows"]-1)}
    pending = list(attached)
    while pending:
        x,y = pending.pop()
        for c in ((x-1,y),(x+1,y),(x,y-1),(x,y+1)):
            if c in masonry and c not in attached:
                attached.add(c); pending.append(c)
    assert attached == masonry, "isolated masonry disconnected from perimeter"
    wall_draw_cells = {tuple(d["cell"]) for d in plan if d.get("tileRole")=="wallFace" and d["layer"]==20}
    assert masonry <= wall_draw_cells, "solid grid masonry lacks rendered wall face"
    # Derive portal opening columns from actual art bounds, never from a claimed
    # clearance boolean. Any positive-width intersection reserves a column.
    tile = board["tileSize"]; ox,oy = board["origin"]
    for name in ("entrance", "exit"):
        portal = data[name]
        d = next(d for d in plan if d.get("portal") == name)
        columns = set(range(math.floor((d["x"]-ox)/tile), math.ceil((d["x"]+d["width"]-ox)/tile)))
        assert columns and min(columns) >= 0 and max(columns) < board["columns"], "portal extends beyond board"
        wall_y = board["rows"] if name == "entrance" else -1
        approach_rows = recipe["architecture"]["portalApproachRows"]
        approach = {"x":d["x"]-recipe["architecture"]["portalPadding"],
                    "y":d["threshold"][1] if name=="exit" else d["y"]-approach_rows*tile,
                    "width":d["width"]+2*recipe["architecture"]["portalPadding"],"height":approach_rows*tile}
        def cells_in_rect(rect):
            return {(x,y) for x in range(board["columns"]) for y in range(board["rows"])
                    if ox+x*tile < rect["x"]+rect["width"] and ox+(x+1)*tile > rect["x"]
                    and oy+y*tile < rect["y"]+rect["height"] and oy+(y+1)*tile > rect["y"]}
        clearance = cells_in_rect(d) | cells_in_rect(approach)
        assert clearance <= walkable, "portal footprint/approach blocked by terrain"
        assert not clearance.intersection(tuple(p["cell"]) for p in placements), "entity in portal footprint/approach"
        for entity in entities:
            for rect in (d,approach):
                assert not (entity["x"] < rect["x"]+rect["width"] and entity["x"]+entity["width"] > rect["x"] and
                            entity["y"] < rect["y"]+rect["height"] and entity["y"]+entity["height"] > rect["y"]), "entity art overlaps portal/approach"
        assert not any(d.get("cell") and tuple(d["cell"]) in {(x,wall_y) for x in columns}
                       and d.get("tileRole", "").startswith("wall") for d in plan), "masonry obstructs portal visual width"
        for wall in (p for p in plan if p.get("tileRole", "").startswith("wall")):
            assert not (wall["x"] < d["x"]+d["width"] and wall["x"]+wall["width"] > d["x"] and
                        wall["y"] < d["y"]+d["height"] and wall["y"]+wall["height"] > d["y"]), "masonry overlaps portal art at outer collar"
    # Upright masonry and all entities share painter ordering by ground contact.
    upright = [d for d in plan if d.get("entityId") or d.get("tileRole") == "pier" or d.get("portal")]
    assert all(d["layer"] == entities[0]["layer"] for d in upright), "pier bypasses common upright layer"
    for d in upright:
        if d.get("tileRole") != "pier": continue
        a = assets[d["assetId"]]; native = a.get("size") or [a["width"],a["height"]]
        assert [d["width"],d["height"]] == native, "pier stretches native upright art"
        x,y = d["cell"]
        assert [d["x"]+a["anchor"][0],d["y"]+a["anchor"][1]] == [ox+(x+.5)*tile,oy+(y+1)*tile], "pier foot anchor mismatch"
        assert d["footY"] == oy+(y+1)*tile, "pier depth differs from ground contact"
    for d in entities:
        p = next(p for p in placements if p["id"]==d["entityId"])
        a = assets[d["assetId"]]; native = a.get("size") or [a["width"],a["height"]]
        expected_foot = oy+(p["cell"][1]+1)*tile-4
        assert d["footY"] == p["footY"] == expected_foot, "entity depth differs from ground contact"
        assert abs(d["y"]+a["anchor"][1]*recipe["actorScale"]-expected_foot)<1e-8, "entity visual foot anchor mismatch"
    assert [d["footY"] for d in upright] == sorted(d["footY"] for d in upright), "upright foot depth order"
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
