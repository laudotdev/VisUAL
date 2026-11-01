"""Trace snapshot helpers for VisUAL."""
from __future__ import annotations

# `deepcopy` ang kailangan dahil nested ang dictionaries/lists ng snapshot;
# hindi sapat ang shallow copy para maprotektahan ang history.
from copy import deepcopy


def freeze_snapshot(snapshot: dict) -> dict:
    # Deep copying prevents later interpreter mutations from rewriting history.
    """Return a detached snapshot so later mutations cannot alter history."""
    return deepcopy(snapshot)


def validate_trace(snapshots: list[dict]) -> bool:
    # Validate indexes and references before a frontend attempts to render the trace.
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
