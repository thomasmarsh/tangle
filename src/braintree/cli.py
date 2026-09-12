"""The ``bt`` sidecar and query command line interface.

This scaffold preserves the public command surface: the ten command names,
their arguments, the TOON field styling, and the ``0``/``1``/``2`` exit codes.
Command bodies are implemented by TAS-040.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence

from . import __version__
from .toon import escape, field

__all__ = ["main"]

_USAGE = (
    "bt [status|location|init|allocate PREFIX|"
    "claim NODE AGENT --base-hash HASH [--lease-seconds N]|"
    "release NODE AGENT --base-hash HASH|reindex [NODES]|"
    "search QUERY [--limit N]|backlinks NODE|stale]"
)

_COMMANDS: tuple[tuple[str, str], ...] = (
    ("status", "show the current sidecar state"),
    ("location", "show the stable project identity and database path"),
    ("init", "create or repair the local sidecar"),
    ("allocate PREFIX", "atomically allocate PREFIX-NNN"),
    ("claim NODE AGENT --base-hash HASH", "acquire or renew an exclusive lease"),
    ("release NODE AGENT --base-hash HASH", "release the matching unexpired lease"),
    ("reindex [NODES]", "rebuild derived nodes, edges, and FTS from Markdown"),
    ("search QUERY [--limit N]", "full-text search derived Markdown content"),
    ("backlinks NODE", "list derived incoming graph edges"),
    ("stale", "find missing or outdated dependency pins"),
)


def _print_usage() -> None:
    description = (
        "Coordinate and query a Markdown-canonical graph through an external "
        "SQLite sidecar."
    )
    print(field("description", description))
    print(field("usage", _USAGE))
    print(f"commands[{len(_COMMANDS)}]{{command,purpose}}:")
    for name, purpose in _COMMANDS:
        print(f'  "{escape(name)}","{escape(purpose)}"')


def _usage_error(message: str) -> int:
    print(field("error", message))
    print(field("help", "Run `bt --help` for command usage."))
    return 2


def _runtime_error(message: str) -> int:
    print(field("error", message))
    print(field("help", "Check the local sidecar location and retry."))
    return 1


def main(argv: Sequence[str] | None = None) -> int:
    """Run the ``bt`` command and return the process exit code."""
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) == 1 and args[0] in {"--version", "-v", "-V"}:
        print(__version__)
        return 0
    command = args[0] if args else "status"
    if command in {"--help", "-h"}:
        _print_usage()
        return 0
    if command not in {name for name, _ in _COMMANDS}:
        return _usage_error(f"unknown command: {command}")
    return _runtime_error(f"command is not implemented in the scaffold: {command}")
