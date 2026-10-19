"""Beginner-friendly formatting for immutable VisUAL snapshot values."""
from __future__ import annotations
from html import escape

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


def format_variable_explanations(entries):
    """Render variable explanations as separated, consistently labeled blocks."""
    blocks = []
    for name, item in entries.items():
        blocks.append(
            f'<div style="margin-bottom:12px;">'
            f'<span style="color:#8be9fd; font-weight:bold;">'
            f'{escape(name)}'
            f'</span><br>'
            f'<b>Current value:</b> {escape(format_explanation_value(item["value"]))}<br>'
            f'<b>Explanation:</b> {escape(item["explanation"])}'
            f'</div>'
        )
    return "".join(blocks)
