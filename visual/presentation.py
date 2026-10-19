"""Beginner-friendly formatting for immutable VisUAL snapshot values."""
from __future__ import annotations

from typing import Any


def format_variable_value(value: Any) -> str:
    """Format a serialized snapshot value without changing the snapshot.

    Object references intentionally become only their stable numeric identity,
    matching the IDs rendered by the linked-list diagram. Unknown dictionaries
    and malformed references remain visible as safe representations instead of
    being silently treated as objects.
    """
    if isinstance(value, dict):
        if set(value) >= {"ref", "class"} and isinstance(value.get("ref"), int) and not isinstance(value.get("ref"), bool):
            return str(value["ref"])
        return repr(value)
    if isinstance(value, list):
        return "[" + ", ".join(format_variable_value(item) for item in value) + "]"
    if value is None:
        return "None"
    if isinstance(value, (str, int, float, bool)):
        return str(value)
    return repr(value)


def format_explanation_value(value: Any) -> str:
    """Format values for learners, keeping object identity secondary to meaning."""
    if isinstance(value, dict) and {"ref", "class"}.issubset(value):
        return f"{value['class']} object (reference {value['ref']})"
    if isinstance(value, list):
        return "[" + ", ".join(format_explanation_value(item) for item in value) + "]"
    return format_variable_value(value)


def format_variable_explanations(entries: dict[str, dict[str, Any]]) -> str:
    """Render variable explanations as separated, consistently labeled blocks."""
    blocks = []
    for name, item in entries.items():
        blocks.append(
            f"{name}\n"
            f"Current value: {format_explanation_value(item.get('value'))}\n"
            f"Explanation: {item.get('explanation', '')}"
        )
    return "\n\n".join(blocks)
