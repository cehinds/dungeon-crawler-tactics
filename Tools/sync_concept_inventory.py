#!/usr/bin/env python3
"""Refresh the documented semantic inventory from its authoritative annotations."""

import argparse
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DOCS = ROOT / "Docs/ConceptReconstruction"


def synchronized_inventory(inventory, manifest_path=None):
    result = dict(inventory)
    components = []
    sources = []
    old_sources = {s["path"]: s for s in inventory.get("annotation_sources", [])}
    for name in ("scene-regions.json", "ui-regions.json"):
        path = DOCS / name
        document = json.loads(path.read_text())
        relative = str(path.relative_to(ROOT))
        sources.append({**old_sources.get(relative, {}), "path": relative,
                        "region_count": len(document["regions"])})
        for region in document["regions"]:
            components.append({"id": region["id"], "category": region["category"],
                               "label": region["label"], "parent": region.get("parentId"),
                               "shape": region["shape"], "text": region.get("text"),
                               "note": region.get("note")})
    result["annotation_sources"] = sources
    result["semantic_components"] = components
    if manifest_path:
        manifest = json.loads(manifest_path.read_text())
        authored_ids = {c["id"] for c in components}
        if authored_ids != {l["id"] for l in manifest["layers"]}:
            raise ValueError("Manifest layer IDs differ from current annotations; rebuild first")
        result["export_snapshot"] = {
            "source_sha256": manifest["sourceSha256"],
            "manifest": str(manifest_path.relative_to(ROOT)) if manifest_path.is_relative_to(ROOT) else str(manifest_path),
            "manifest_sha256": hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
            "annotation_rows": len(manifest["layers"]),
            "visible_component_pngs": sum(bool(l.get("file")) for l in manifest["layers"]),
            "fully_occluded_annotation_rows": sum(not l.get("file") for l in manifest["layers"]),
            "unassigned_pixels": manifest["unassignedPixels"],
            "changed_pixels": manifest["changedPixels"],
        }
    elif inventory.get("semantic_components") != components:
        result["export_snapshot"] = {"status": "annotations changed; rebuild and sync with --manifest"}
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true")
    parser.add_argument("--manifest", type=Path)
    args = parser.parse_args()
    path = DOCS / "inventory.json"
    current = json.loads(path.read_text())
    expected = synchronized_inventory(current, args.manifest)
    if args.check:
        if current != expected:
            raise SystemExit("Inventory is stale; run Tools/sync_concept_inventory.py")
        print("Semantic inventory agrees with authored annotations")
    else:
        path.write_text(json.dumps(expected, indent=2) + "\n")
        print(f"Synchronized {len(expected['semantic_components'])} semantic components")


if __name__ == "__main__":
    main()
