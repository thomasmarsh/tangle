"""Helpers for rendering the compact TOON output contract.

The shell tools emit double-quoted ``name: "value"`` fields and indented,
comma-separated table rows. These helpers reproduce that escaping so every
Python command keeps the same machine-readable surface.
"""

from __future__ import annotations

from collections.abc import Iterable

__all__ = ["escape", "field", "row", "table"]


def escape(value: object) -> str:
    """Escape a value for a double-quoted TOON field or table cell."""
    return str(value).replace("\\", "\\\\").replace('"', '\\"')


def field(name: str, value: object) -> str:
    """Render one ``name: "value"`` TOON line."""
    return f'{name}: "{escape(value)}"'


def row(values: Iterable[object]) -> str:
    """Render one indented, comma-separated TOON table row."""
    return "  " + ",".join(f'"{escape(value)}"' for value in values)


def table(
    name: str,
    header: str,
    rows: Iterable[Iterable[object]],
    empty: str | None = None,
) -> str:
    """Render TOON records as an indented table or an explicit zero-result line."""
    materialized = [tuple(values) for values in rows]
    if not materialized:
        return empty if empty is not None else f"{name}: 0"
    lines = [f"{name}[{len(materialized)}]{{{header}}}:"]
    lines.extend(row(values) for values in materialized)
    return "\n".join(lines)
