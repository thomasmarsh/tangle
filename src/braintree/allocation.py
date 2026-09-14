"""The ``braintree allocate`` verb: reserve one or many consecutive ids.

``src/braintree/cli.py`` and ``src/braintree/sidecar.py`` are two of the seven
``src/braintree/*.py`` paths embedded as observable prompt content in
``benchmark/memory-authority-cases.json``, so any byte change to either one
invalidates the committed ``benchmark/memory-authority-result.json`` measurement,
whose only faithful repair is a live re-record.
[[TAS-140-allocation-lifecycle-visibility]] resolved the same conflict by
reaching the verb's answer through a new module instead of an observable file,
and this module keeps the batch reservation the verb now needs on the same
footing: the operand grammar, the exit-2 usage text, and the single-id output
stay observably identical to the coordination engine's allocation path.
"""

from __future__ import annotations

import re
import sqlite3
import sys
from collections.abc import Container, Sequence

from . import index, sidecar, vault
from .toon import field

__all__ = ["allocate_many", "main"]

# The accepted prefix and count grammar repeats `braintree.cli`'s allocate path,
# which the frozen-observable rule in the module docstring keeps unchanged.
_PREFIX = re.compile(r"[A-Z0-9_-]*\Z")
_POSITIVE_INTEGER = re.compile(r"[0-9]+\Z")


def allocate_many(prefix: str, count: int, taken: Container[int] | None = None) -> list[int]:
    """Atomically reserve ``count`` consecutive unused integers for ``prefix``.

    ``next_value`` is the integer the next allocation returns. ``taken`` holds
    the numeric suffixes already present on disk; a candidate that appears there
    is skipped so allocation never returns an identity that duplicates an
    existing node filename, even when the counter is behind Markdown, and the
    skipped candidate is still consumed, so it burns exactly as on the single-id
    path. Every candidate in the batch is chosen inside one ``BEGIN IMMEDIATE``
    transaction, so a concurrent caller sees either none of these ids or a
    disjoint consecutive block.
    """
    blocked: Container[int] = () if taken is None else taken
    try:
        conn = sidecar.open_connection()
        try:
            def body(connection: sqlite3.Connection) -> list[int]:
                connection.execute(
                    "INSERT INTO id_sequences(prefix,next_value) VALUES(?, 1) "
                    "ON CONFLICT(prefix) DO NOTHING",
                    (prefix,),
                )
                reserved: list[int] = []
                while len(reserved) < count:
                    row = connection.execute(
                        "SELECT next_value FROM id_sequences WHERE prefix = ?",
                        (prefix,),
                    ).fetchone()
                    candidate = int(row[0])
                    connection.execute(
                        "UPDATE id_sequences SET next_value = next_value + 1 "
                        "WHERE prefix = ?",
                        (prefix,),
                    )
                    if candidate not in blocked:
                        reserved.append(candidate)
                return reserved

            # ``sidecar._run_transaction`` is the one spelling of the busy-retry
            # ``BEGIN IMMEDIATE`` wrapper. The frozen sidecar module cannot
            # export a public alias of it without invalidating the measurement.
            return sidecar._run_transaction(conn, body)
        finally:
            conn.close()
    except sqlite3.Error as exc:
        raise sidecar.SidecarError("unable to allocate an ID atomically") from exc


def _usage_error(message: str) -> int:
    print(field("error", message))
    print(
        field(
            "help",
            "Run `braintree allocate --help` for operands and exit meanings.",
        )
    )
    return 2


def _runtime_error(message: str) -> int:
    print(field("error", message))
    print(field("help", "Check the local sidecar location and retry."))
    return 1


def _print_reserved(prefix: str, values: Sequence[int]) -> None:
    if len(values) == 1:
        print(field("id", f"{prefix}-{values[0]:03d}"))
        return
    print(
        index.format_table(
            "ids",
            "id",
            "",
            [[f"{prefix}-{value:03d}"] for value in values],
        )
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run ``braintree allocate PREFIX [COUNT]`` and return the process exit code.

    ``argv`` is the full ``braintree ...`` argument list, the same shape
    :func:`braintree.cli.main` accepts.
    """
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) < 2:
        return _usage_error("allocate requires PREFIX")
    if len(args) > 3:
        return _usage_error("allocate accepts at most PREFIX and COUNT")
    prefix = args[1]
    if prefix == "" or _PREFIX.fullmatch(prefix) is None:
        return _usage_error(
            "PREFIX must contain only uppercase letters, digits, underscores, or hyphens"
        )
    count = 1
    if len(args) == 3:
        raw_count = args[2]
        if _POSITIVE_INTEGER.fullmatch(raw_count) is None or int(raw_count) <= 0:
            return _usage_error("COUNT must be a positive integer")
        count = int(raw_count)
    try:
        taken = index.existing_allocations(vault.resolve()).get(prefix)
        values = allocate_many(prefix, count, taken)
    except sidecar.SidecarError as exc:
        return _runtime_error(str(exc))
    _print_reserved(prefix, values)
    return 0
