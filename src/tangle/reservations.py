"""Read-only view of the sidecar's id reservations across worktrees.

``tangle allocate`` advances a counter that never rewinds, so every integer
below a prefix's ``next`` was allocated. The ones with no node file on disk were
burned by a caller that discarded its allocation; naming them lets a reader tell
a discarded allocation from a missing node.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence

from . import index, sidecar, vault
from .toon import field

__all__ = ["main", "reservation_rows"]


def _compact_ranges(values: Sequence[int]) -> str:
    """Render ascending integers as compact ranges: ``1-3,5``."""
    if not values:
        return ""
    parts: list[str] = []
    start = previous = values[0]
    for value in values[1:]:
        if value == previous + 1:
            previous = value
            continue
        parts.append(str(start) if start == previous else f"{start}-{previous}")
        start = previous = value
    parts.append(str(start) if start == previous else f"{start}-{previous}")
    return ",".join(parts)


def reservation_rows(root: str) -> list[tuple[str, str, str]]:
    """Return ``prefix``, ``next``, and the burned ids no node claims."""
    used = index.existing_allocations(root)
    rows: list[tuple[str, str, str]] = []
    for prefix, next_value in sidecar.reservations():
        claimed = used.get(prefix, set())
        burned = [number for number in range(1, int(next_value)) if number not in claimed]
        rows.append((prefix, next_value, _compact_ranges(burned)))
    return rows


_USAGE = (
    "usage: tangle reservations\n"
    "List each allocated id prefix, its next allocation, and the burned ids "
    "no node uses."
)


def _usage_error(message: str) -> int:
    print(field("error", message))
    print(
        field(
            "help",
            "Run `tangle reservations --help` for operands and exit meanings.",
        )
    )
    return 2


def main(argv: Sequence[str] | None = None) -> int:
    """Print the reservation table and return the process exit code."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    if arguments:
        if arguments[0] in {"-h", "--help"}:
            print(_USAGE)
            return 0
        return _usage_error(f"reservations takes no arguments: {arguments[0]}")
    print(
        index.format_table(
            "reservations",
            "prefix,next,burned",
            "reservations: 0 prefixes",
            reservation_rows(vault.resolve()),
        )
    )
    return 0

