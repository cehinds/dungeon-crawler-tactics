#!/usr/bin/env python3
"""Strict authoring checks. Runtime Catalog also validates loaded references.

Usage: python3 Tools/validate_content.py [path/to/content.json]
This reads only the supplied file and the bundled schema. No remote refs.
"""
import json
from pathlib import Path
import sys

try:
    from jsonschema import Draft202012Validator
except ImportError:
    raise SystemExit("Install tooling dependencies: python3 -m pip install -r Tools/requirements.txt")

ROOT = Path(__file__).resolve().parents[1]
SCHEMA = json.loads((ROOT / "Tools/content.schema.json").read_text())


def no_duplicate_keys(pairs):
    result = {}
    for key, value in pairs:
        if key in result:
            raise ValueError(f"Duplicate JSON property: {key}")
        result[key] = value
    return result


def validate(content):
    errors = []
    for error in Draft202012Validator(SCHEMA).iter_errors(content):
        path = ".".join(str(part) for part in error.absolute_path) or "$"
        errors.append(f"{path}: {error.message}")
    if errors:
        return sorted(errors)

    ids = {}
    for category in ("tags", "classes", "abilities", "reactions", "items"):
        ids[category] = set()
        for index, record in enumerate(content[category]):
            if record["id"] in ids[category]:
                errors.append(f"{category}.{index}.id: duplicate {record['id']}")
            ids[category].add(record["id"])

    def references(values, category, path):
        for index, value in enumerate(values):
            if value not in ids[category]:
                errors.append(f"{path}.{index}: unknown {category} ID {value}")

    def effects(records, path):
        for index, effect in enumerate(records):
            if effect["op"] in ("AddTag", "RemoveTag"):
                references([effect["tag"]], "tags", f"{path}.{index}.tag")
            elif effect["op"] == "Teleport" and (effect["amount"] != 0 or effect["tag"] != ""):
                errors.append(f"{path}.{index}: Teleport requires amount 0 and empty tag")
            elif effect["op"] == "Push" and (effect["amount"] < 1 or effect["tag"] != ""):
                errors.append(f"{path}.{index}: Push requires positive amount and empty tag")

    for index, record in enumerate(content["classes"]):
        references(record["abilityIds"], "abilities", f"classes.{index}.abilityIds")
    for index, record in enumerate(content["items"]):
        references([record["abilityId"]], "abilities", f"items.{index}.abilityId")
        if record.get("favorEligible"):
            ability = next((a for a in content["abilities"] if a["id"] == record["abilityId"]), None)
            if ability and (ability["target"] != "tile" or ability["incomingTags"] or any(e["op"] != "AddTag" for e in ability["effects"])):
                errors.append(f"items.{index}: Favor supplies must only add environmental tags without incoming reactions")
    for index, record in enumerate(content["abilities"]):
        references(record["incomingTags"], "tags", f"abilities.{index}.incomingTags")
        effects(record["effects"], f"abilities.{index}.effects")
    for index, record in enumerate(content["reactions"]):
        base = f"reactions.{index}"
        for query in ("incoming", "target"):
            for clause in ("all", "any", "none"):
                references(record[query][clause], "tags", f"{base}.{query}.{clause}")
            conflict = set(record[query]["all"]) & set(record[query]["none"])
            if conflict:
                errors.append(f"{base}.{query}: all/none conflict: {', '.join(sorted(conflict))}")
            any_tags = set(record[query]["any"])
            if any_tags and any_tags <= set(record[query]["none"]):
                errors.append(f"{base}.{query}: every any tag is excluded by none")
        for field in ("consumeTags", "emitTags"):
            references(record[field], "tags", f"{base}.{field}")
        effects(record["effects"], f"{base}.effects")
    return sorted(errors)


def main():
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else ROOT / "UnityPackage/Runtime/Data/starter-content.json"
    try:
        content = json.loads(path.read_text(), object_pairs_hook=no_duplicate_keys)
        errors = validate(content)
    except (OSError, ValueError) as error:
        print(f"{path}: {error}", file=sys.stderr)
        return 1
    if errors:
        for error in errors:
            print(f"{path}: {error}", file=sys.stderr)
        return 1
    print("Valid content v1: " + ", ".join(f"{len(content[key])} {key}" for key in ("tags", "classes", "abilities", "reactions", "items")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
