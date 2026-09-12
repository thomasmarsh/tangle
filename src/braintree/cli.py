"""The ``bt`` sidecar and query command line interface.

Typed Python port of ``scripts/bt`` widening the scaffold: the ten command
names, their arguments, the TOON field styling, and the ``0``/``1``/``2``
exit codes are preserved. Coordination lives in :mod:`braintree.sidecar` and
the rebuildable Markdown index in :mod:`braintree.index`.
"""

from __future__ import annotations

import os
import re
import sys
from collections.abc import Callable, Sequence

from . import __version__, index, sidecar
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

_PREFIX = re.compile(r"[A-Z0-9_-]*\Z")
_POSITIVE_INTEGER = re.compile(r"[0-9]+\Z")


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


def _print_fields(fields: Sequence[tuple[str, str]]) -> None:
    for name, value in fields:
        print(field(name, value))


def _nodes_directory() -> str:
    return os.environ.get("BT_NODES_DIR", "nodes")


def _index_guard[T](operation: Callable[[], T]) -> T:
    try:
        return operation()
    except sidecar.SidecarError as exc:
        print(str(exc), file=sys.stderr)
        raise sidecar.SidecarError(
            "unable to reconcile the derived Markdown index"
        ) from exc


def _run_reindex(root: str) -> tuple[int, int, str]:
    conn = sidecar.open_connection()
    try:
        return index.reindex(conn, root)
    finally:
        conn.close()


def _allocate(args: list[str]) -> int:
    if len(args) != 2:
        return _usage_error("allocate requires PREFIX")
    prefix = args[1]
    if prefix == "" or _PREFIX.fullmatch(prefix) is None:
        return _usage_error(
            "PREFIX must contain only uppercase letters, digits, underscores, or hyphens"
        )
    value = sidecar.allocate(prefix)
    print(field("id", f"{prefix}-{value:03d}"))
    return 0


def _claim(args: list[str]) -> int:
    if len(args) < 5:
        return _usage_error("claim requires NODE AGENT --base-hash HASH")
    node = args[1]
    agent = args[2]
    base_hash: str | None = None
    lease_raw = "900"
    index_arg = 3
    while index_arg < len(args):
        argument = args[index_arg]
        if argument == "--base-hash":
            index_arg += 1
            if index_arg >= len(args):
                return _usage_error("--base-hash requires HASH")
            base_hash = args[index_arg]
        elif argument == "--lease-seconds":
            index_arg += 1
            if index_arg >= len(args):
                return _usage_error("--lease-seconds requires seconds")
            lease_raw = args[index_arg]
        else:
            return _usage_error(f"unknown argument for claim: {argument}")
        index_arg += 1
    if node == "" or agent == "" or base_hash is None or base_hash == "":
        return _usage_error("claim requires non-empty NODE, AGENT, and --base-hash HASH")
    if _POSITIVE_INTEGER.fullmatch(lease_raw) is None or int(lease_raw) <= 0:
        return _usage_error("--lease-seconds must be a positive integer")
    try:
        owner, recorded_hash, recorded_expiry = sidecar.claim(
            node, agent, base_hash, int(lease_raw)
        )
    except sidecar.ClaimConflict as exc:
        print(field("error", f"node is claimed by {exc.owner} with a different base hash"))
        print(
            field(
                "help",
                "Use a different node or reconcile the current Markdown content "
                "before claiming.",
            )
        )
        return 1
    print(field("result", "claimed"))
    print(field("node", node))
    print(field("agent", agent))
    print(field("base_hash", recorded_hash))
    print(field("lease_expires_at", recorded_expiry))
    return 0


def _release(args: list[str]) -> int:
    if len(args) != 5 or args[3] != "--base-hash":
        return _usage_error("release requires NODE AGENT --base-hash HASH")
    node, agent, base_hash = args[1], args[2], args[4]
    if node == "" or agent == "" or base_hash == "":
        return _usage_error("release requires non-empty NODE, AGENT, and HASH")
    released = sidecar.release(node, agent, base_hash)
    print(field("result", "released" if released else "no-op"))
    print(field("node", node))
    return 0


def _search(args: list[str]) -> int:
    if len(args) < 2 or args[1] == "--limit":
        return _usage_error("search requires QUERY")
    query = args[1]
    limit_raw = "20"
    index_arg = 2
    while index_arg < len(args):
        if args[index_arg] != "--limit":
            return _usage_error(f"unknown argument for search: {args[index_arg]}")
        index_arg += 1
        if index_arg >= len(args):
            return _usage_error("--limit requires N")
        limit_raw = args[index_arg]
        index_arg += 1
    if _POSITIVE_INTEGER.fullmatch(limit_raw) is None or int(limit_raw) <= 0:
        return _usage_error("--limit must be a positive integer")

    def query_index() -> list[tuple[str, str, str]]:
        print_rows: list[tuple[str, str, str]] = []
        conn = sidecar.open_connection()
        try:
            index.reindex(conn, _nodes_directory())
            print_rows = index.search(conn, query, int(limit_raw))
        finally:
            conn.close()
        return print_rows

    rows = _index_guard(query_index)
    print(
        index.format_table(
            "nodes", "id,status,summary", "nodes: 0 matching nodes", rows
        )
    )
    return 0


def _backlinks(args: list[str]) -> int:
    if len(args) != 2:
        return _usage_error("backlinks requires NODE")
    node = args[1]

    def query_index() -> list[tuple[str, str, str, str]]:
        conn = sidecar.open_connection()
        try:
            index.reindex(conn, _nodes_directory())
            return index.backlinks(conn, node)
        finally:
            conn.close()

    rows = _index_guard(query_index)
    print(
        index.format_table(
            "backlinks",
            "source,status,relation,pinned_context_rev",
            "backlinks: 0 matching edges",
            rows,
        )
    )
    return 0


def _stale(args: list[str]) -> int:
    if len(args) != 1:
        return _usage_error("stale accepts no arguments")

    def query_index() -> list[tuple[str, str, str, str, str]]:
        conn = sidecar.open_connection()
        try:
            index.reindex(conn, _nodes_directory())
            return index.stale(conn)
        finally:
            conn.close()

    rows = _index_guard(query_index)
    print(
        index.format_table(
            "stale",
            "source,status,target,pinned,current",
            "stale: 0 dependency pins",
            rows,
        )
    )
    return 0


def _dispatch(command: str, args: list[str]) -> int:
    if command == "status":
        if len(args) != 1:
            return _usage_error("status accepts no arguments")
        _print_fields(sidecar.status_fields())
        return 0
    if command == "location":
        if len(args) != 1:
            return _usage_error("location accepts no arguments")
        _print_fields(sidecar.location_fields())
        return 0
    if command == "init":
        if len(args) != 1:
            return _usage_error("init accepts no arguments")
        sidecar.ensure_sidecar()
        print(field("result", "initialized"))
        _print_fields(sidecar.location_fields())
        return 0
    if command == "allocate":
        return _allocate(args)
    if command == "claim":
        return _claim(args)
    if command == "release":
        return _release(args)
    if command == "reindex":
        if len(args) > 2:
            return _usage_error("reindex accepts at most one NODES directory")
        root = args[1] if len(args) == 2 else _nodes_directory()
        nodes, edges, absolute_root = _index_guard(lambda: _run_reindex(root))
        print(f"nodes: {nodes}")
        print(f"edges: {edges}")
        print(f"root: {absolute_root}")
        return 0
    if command == "search":
        return _search(args)
    if command == "backlinks":
        return _backlinks(args)
    return _stale(args)


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
    if command not in {name.split()[0] for name, _ in _COMMANDS}:
        return _usage_error(f"unknown command: {command}")
    try:
        return _dispatch(command, args)
    except sidecar.SidecarError as exc:
        return _runtime_error(str(exc))
