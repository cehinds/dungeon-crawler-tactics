"""Presentation-only tile edges in local texture directions at zero rotation.

Clockwise quarter turns map north to east. Joins describe art compatibility,
never gameplay collision, hazards or navigation. Manual and overlay joins do
not authorize automatic connections.
"""

import re

from build_style_packs import require

SIDES = ("north", "east", "south", "west")
TAG = re.compile(r"[a-z][a-z0-9]*(?:-[a-z0-9]+)*(?:\.[a-z][a-z0-9]*(?:-[a-z0-9]+)*)+\Z")


def validate_edges(asset):
    """Require explicit, unambiguous edge tags on an authored/exported asset."""
    label = asset.get("id", "asset")
    edges = asset.get("edges")
    require(isinstance(edges, dict) and set(edges) == set(SIDES),
            f"{label}: edges must contain exactly north, east, south, west")
    manual = False
    for side in SIDES:
        tags = edges[side]
        require(isinstance(tags, list) and bool(tags)
                and all(isinstance(tag, str) and TAG.fullmatch(tag) for tag in tags),
                f"{label}: {side} requires nonempty lowercase dotted edge tags")
        require(len(tags) == len(set(tags)), f"{label}: duplicate {side} edge tags")
        joins = [tag for tag in tags if tag.startswith("join.")]
        require(len(joins) == 1,
                f"{label}: {side} requires exactly one join tag")
        manual |= joins == ["join.manual"]
    require(asset.get("edgeReview") in (None, "manual"), f"{label}: unknown edgeReview")
    require(manual == (asset.get("edgeReview") == "manual"),
            f"{label}: manual joins require edgeReview manual and vice versa")
