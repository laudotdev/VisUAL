"""Trace snapshot helpers for VisUAL."""
from __future__ import annotations

from copy import deepcopy


def freeze_snapshot(snapshot: dict) -> dict:
    """Return a detached snapshot so later mutations cannot alter history."""
    return deepcopy(snapshot)


def validate_trace(snapshots: list[dict]) -> bool:
    """Basic consistency check for a serialized trace."""
    for index, snapshot in enumerate(snapshots):
        if snapshot.get("step_index") != index:
            return False
        ids = {node.get("id") for node in snapshot.get("nodes", [])}
        for node in snapshot.get("nodes", []):
            if node.get("next") is not None and node["next"] not in ids:
                return False
        if snapshot.get("head_ref") is not None and snapshot["head_ref"] not in ids:
            return False
    return True
