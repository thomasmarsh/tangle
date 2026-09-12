"""The sidecar and index query command group behind ``braintree``.

The command names, their arguments, the TOON field styling, and the
``0``/``1``/``2`` exit codes are the internal engine the unified
``braintree`` command fronts. Coordination lives in :mod:`braintree.sidecar`
and the rebuildable Markdown index in :mod:`braintree.index`.
"""

from __future__ import annotations

import os
import re
import sys
from collections.abc import Callable, Sequence

from . import index, sidecar
from .revision import reported_version
from .toon import escape, field

__all__ = ["main"]

_USAGE = (
    "braintree [status|location|init|allocate PREFIX|"
    "claim NODE AGENT --base-hash HASH [--lease-seconds N]|"
    "release NODE AGENT --base-hash HASH|index [NODES]|"
    "search QUERY [--limit N] [--status S] [--type T] [--priority P] "
    "[--parent REF] [--dependency REF]|"
    "similar TEXT|--file PATH [--limit N]|backlinks NODE|hash NODE|stale|"
    "frontier [--group] [--limit N]|node NODE|impact NODE|"
    "orient [--section NAME] [--limit N]|next [--rank] [--limit N]]"
)

_COMMANDS: tuple[tuple[str, str], ...] = (
    ("status", "show the current sidecar state"),
    ("location", "show the stable project identity and database path"),
    ("init", "create or repair the local sidecar"),
    ("allocate PREFIX", "atomically allocate PREFIX-NNN"),
    ("claim NODE AGENT --base-hash HASH", "acquire or renew an exclusive lease"),
    ("release NODE AGENT --base-hash HASH", "release the matching unexpired lease"),
    ("index [NODES]", "rebuild derived nodes, edges, and FTS from Markdown"),
    (
        "search QUERY [--limit N] [--status S] [--type T] [--priority P] "
        "[--parent REF] [--dependency REF]",
        "full-text search derived Markdown content",
    ),
    ("similar TEXT|--file PATH [--limit N]", "rank nodes by lexical similarity"),
    ("backlinks NODE", "list derived incoming graph edges"),
    ("hash NODE", "print the raw-content SHA-256 of a node file"),
    ("stale", "find missing or outdated dependency pins"),
    ("frontier [--group] [--limit N]", "list the frontier or cluster it into advisory workstreams"),
    ("node NODE", "show one node's frontmatter, route, edges, and backlinks"),
    ("impact NODE", "list direct and transitive dependents of a node"),
    ("orient [--section NAME] [--limit N]", "print a bounded orientation packet"),
    ("next [--rank] [--limit N]", "rank frontier candidates for the next actor"),
)

_PREFIX = re.compile(r"[A-Z0-9_-]*\Z")
_POSITIVE_INTEGER = re.compile(r"[0-9]+\Z")
_STATUSES = frozenset({"proposed", "active", "blocked", "resolved"})
_PRIORITY = re.compile(r"P[0-3]\Z")
_NODE_TYPE = re.compile(r"[A-Z][A-Z0-9_]*\Z")
# The structured search filter flags map to ``index.SearchFilters`` fields.
_SEARCH_FILTERS: dict[str, str] = {
    "--status": "status",
    "--type": "type",
    "--priority": "priority",
    "--parent": "parent",
    "--dependency": "dependency",
}


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
    print(field("help", "Run `braintree --help` for command usage."))
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


def _require_nodes_directory() -> str | None:
    root = _nodes_directory()
    if os.path.isdir(root):
        return root
    print(field("error", f"nodes directory does not exist: {os.path.abspath(root)}"))
    print(field("help", "Run from the project root or set BT_NODES_DIR."))
    return None


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
    value = sidecar.allocate(prefix, index.existing_allocations(_nodes_directory()).get(prefix))
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
    try:
        result = sidecar.release(node, agent, base_hash)
    except sidecar.ReleaseConflict as exc:
        if exc.owner != agent:
            print(field("error", f"node is claimed by {exc.owner}; release refused"))
        else:
            print(
                field(
                    "error",
                    f"base hash does not match the recorded claim for {node}; release refused",
                )
            )
        print(
            field(
                "help",
                "Release with the agent and starting hash recorded by `braintree claim`.",
            )
        )
        return 1
    print(field("result", result))
    print(field("node", node))
    return 0


def _search(args: list[str]) -> int:
    if len(args) < 2 or args[1].startswith("--"):
        return _usage_error("search requires QUERY")
    query = args[1]
    limit_raw = "20"
    values: dict[str, str] = {}
    index_arg = 2
    while index_arg < len(args):
        argument = args[index_arg]
        if argument == "--limit":
            index_arg += 1
            if index_arg >= len(args):
                return _usage_error("--limit requires N")
            limit_raw = args[index_arg]
        elif argument in _SEARCH_FILTERS:
            name = _SEARCH_FILTERS[argument]
            if name in values:
                return _usage_error(f"duplicate {argument}")
            index_arg += 1
            if index_arg >= len(args):
                return _usage_error(f"{argument} requires a value")
            values[name] = args[index_arg]
        else:
            return _usage_error(f"unknown argument for search: {argument}")
        index_arg += 1
    if _POSITIVE_INTEGER.fullmatch(limit_raw) is None or int(limit_raw) <= 0:
        return _usage_error("--limit must be a positive integer")
    status = values.get("status", "").lower()
    if status and status not in _STATUSES:
        return _usage_error("--status must be one of: proposed, active, blocked, resolved")
    priority = values.get("priority", "").upper()
    if priority and _PRIORITY.fullmatch(priority) is None:
        return _usage_error("--priority must be one of: P0, P1, P2, P3")
    node_type = values.get("type", "").upper()
    if node_type and _NODE_TYPE.fullmatch(node_type) is None:
        return _usage_error("--type must be an uppercase node-type prefix such as TAS or DEF")
    filters = index.SearchFilters(
        status=status,
        type=node_type,
        priority=priority,
        parent=values.get("parent", ""),
        dependency=values.get("dependency", ""),
    )
    root = _nodes_directory()
    match: Callable[[str], bool] | None = None
    if filters.any():
        if _require_nodes_directory() is None:
            return 1
        match = index.search_filter(root, filters)

    def query_index() -> list[tuple[str, str, str]]:
        conn = sidecar.open_connection()
        try:
            index.reindex(conn, root)
            return index.search(conn, query, int(limit_raw), match)
        finally:
            conn.close()

    rows = _index_guard(query_index)
    print(
        index.format_table(
            "nodes", "id,status,summary", "nodes: 0 matching nodes", rows
        )
    )
    return 0


def _similar(args: list[str]) -> int:
    positional: list[str] = []
    file_path = ""
    limit_raw = "10"
    index_arg = 1
    while index_arg < len(args):
        argument = args[index_arg]
        if argument == "--limit":
            index_arg += 1
            if index_arg >= len(args):
                return _usage_error("--limit requires N")
            limit_raw = args[index_arg]
        elif argument == "--file":
            index_arg += 1
            if index_arg >= len(args):
                return _usage_error("--file requires PATH")
            file_path = args[index_arg]
        elif argument.startswith("--"):
            return _usage_error(f"unknown argument for similar: {argument}")
        else:
            positional.append(argument)
        index_arg += 1
    if _POSITIVE_INTEGER.fullmatch(limit_raw) is None or int(limit_raw) <= 0:
        return _usage_error("--limit must be a positive integer")
    if positional and file_path:
        return _usage_error("similar accepts TEXT or --file PATH, not both")
    if len(positional) > 1:
        return _usage_error("similar requires TEXT or --file PATH")
    if file_path:
        try:
            with open(file_path, encoding="utf-8") as handle:
                text = handle.read()
        except OSError:
            print(field("error", f"cannot read file: {file_path}"))
            print(field("help", "Check the path and retry with readable UTF-8 text."))
            return 1
    elif positional:
        text = positional[0]
    else:
        return _usage_error("similar requires TEXT or --file PATH")
    root = _require_nodes_directory()
    if root is None:
        return 1
    rows = index.similar(root, text, int(limit_raw))
    print(
        index.format_table(
            "similar",
            "id,status,score,summary",
            "similar: 0 matching nodes",
            [(row.id, row.status, f"{row.score:.4f}", row.summary) for row in rows],
        )
    )
    return 0


def _backlinks(args: list[str]) -> int:
    if len(args) != 2:
        return _usage_error("backlinks requires NODE")
    node = args[1]

    def query_index() -> tuple[bool, list[tuple[str, str, str, str]]]:
        conn = sidecar.open_connection()
        try:
            index.reindex(conn, _nodes_directory())
            resolved = index.resolve_node(conn, node)
            if resolved is None:
                return False, []
            return True, index.backlinks(conn, resolved)
        finally:
            conn.close()

    found, rows = _index_guard(query_index)
    if not found:
        print(field("error", f"unknown node: {node}"))
        print(field("help", "Use a bare ID or a full node name from the vault."))
        return 1
    print(
        index.format_table(
            "backlinks",
            "source,status,relation,pinned_context_rev",
            "backlinks: 0 matching edges",
            rows,
        )
    )
    return 0


def _hash(args: list[str]) -> int:
    if len(args) != 2:
        return _usage_error("hash requires NODE")
    node = args[1]
    value = index.node_hash(_nodes_directory(), node)
    if value is None:
        print(field("error", f"unknown node: {node}"))
        print(field("help", "Use a bare ID or a full node name from the vault."))
        return 1
    print(field("node", node))
    print(field("content_hash", value))
    return 0


def _stale(args: list[str]) -> int:
    if len(args) != 1:
        return _usage_error("stale accepts no arguments")

    def query_index() -> list[tuple[str, str, str, str, str, str, str]]:
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
            "source,status,target,pinned,current,relation,reason",
            "stale: 0 stale dependency pins",
            rows,
        )
    )
    return 0


def _frontier(args: list[str]) -> int:
    group = False
    limit_raw = "10"
    limit_given = False
    index_arg = 1
    while index_arg < len(args):
        argument = args[index_arg]
        if argument == "--group":
            group = True
        elif argument == "--limit":
            index_arg += 1
            if index_arg >= len(args):
                return _usage_error("--limit requires N")
            limit_raw = args[index_arg]
            limit_given = True
        else:
            return _usage_error("frontier accepts no arguments")
        index_arg += 1
    if limit_given and not group:
        return _usage_error("frontier --limit requires --group")
    if _POSITIVE_INTEGER.fullmatch(limit_raw) is None or int(limit_raw) <= 0:
        return _usage_error("--limit must be a positive integer")
    root = _require_nodes_directory()
    if root is None:
        return 1
    if group:
        groups = index.frontier_groups(root, int(limit_raw))
        print(field("advisory", "groups are advisory and are not work claims"))
        print(field("groups", str(groups.total)))
        print(
            index.format_table(
                "frontier_groups",
                "group,id,status,priority,summary,next,stale",
                "frontier_groups: 0 groups",
                [
                    (
                        row.group,
                        row.candidate.id,
                        row.candidate.status,
                        row.candidate.priority,
                        row.candidate.summary,
                        row.candidate.next,
                        "true" if row.candidate.stale else "false",
                    )
                    for row in groups.rows
                ],
            )
        )
        return 0
    rows = [
        (
            entry.id,
            entry.status,
            entry.priority,
            entry.summary,
            entry.next,
            "true" if entry.stale else "false",
        )
        for entry in index.frontier(root)
    ]
    print(
        index.format_table(
            "frontier",
            "id,status,priority,summary,next,stale",
            "frontier: 0 frontier nodes",
            rows,
        )
    )
    return 0


def _next(args: list[str]) -> int:
    limit_raw = "5"
    index_arg = 1
    while index_arg < len(args):
        argument = args[index_arg]
        if argument == "--rank":
            # Ranking is the default and only mode; accept the flag explicitly.
            pass
        elif argument == "--limit":
            index_arg += 1
            if index_arg >= len(args):
                return _usage_error("--limit requires N")
            limit_raw = args[index_arg]
        else:
            return _usage_error(f"unknown argument for next: {argument}")
        index_arg += 1
    if _POSITIVE_INTEGER.fullmatch(limit_raw) is None or int(limit_raw) <= 0:
        return _usage_error("--limit must be a positive integer")
    root = _require_nodes_directory()
    if root is None:
        return 1
    ranking = index.next_ranked(root, int(limit_raw))
    print(
        field(
            "ranking",
            "priority P0-P3 asc; transitive blocking desc; updated desc; id asc",
        )
    )
    print(field("total", str(ranking.total)))
    print(
        index.format_table(
            "next",
            "rank,id,status,priority,blocking,updated,summary,next",
            "next: 0 ranked candidates",
            [
                (
                    str(candidate.rank),
                    candidate.id,
                    candidate.status,
                    candidate.priority,
                    str(candidate.blocking),
                    candidate.updated,
                    candidate.summary,
                    candidate.next,
                )
                for candidate in ranking.candidates
            ],
        )
    )
    return 0


def _node(args: list[str]) -> int:
    if len(args) != 2:
        return _usage_error("node requires NODE")
    root = _require_nodes_directory()
    if root is None:
        return 1
    view = index.node_view(root, args[1])
    if view is None:
        print(field("error", f"unknown node: {args[1]}"))
        print(field("help", "Use a bare ID or a full node name from the vault."))
        return 1
    node = view.node
    print(field("node", node.id))
    print(field("name", node.name))
    print(field("status", node.status))
    print(field("path", node.path))
    print(
        index.format_table(
            "frontmatter",
            "key,value",
            "frontmatter: 0 fields",
            [(key, value) for key, value in sorted(node.metadata.items())],
        )
    )
    print(field("route_relation", view.route_relation))
    print(field("route", view.route))
    print(
        index.format_table(
            "context_edges",
            "relation,target,pinned,current,status,stale",
            "context_edges: 0 context edges",
            [
                (
                    edge.relation,
                    edge.target,
                    edge.pinned,
                    edge.current,
                    edge.status,
                    edge.stale,
                )
                for edge in view.context_edges
            ],
        )
    )
    print(
        index.format_table(
            "backlinks",
            "source,status,relation,pinned",
            "backlinks: 0 backlinks",
            [
                (edge.source, edge.status, edge.relation, edge.pinned)
                for edge in view.backlinks
            ],
        )
    )
    return 0


def _impact(args: list[str]) -> int:
    if len(args) != 2:
        return _usage_error("impact requires NODE")
    root = _require_nodes_directory()
    if root is None:
        return 1
    view = index.impact(root, args[1])
    if view is None:
        print(field("error", f"unknown node: {args[1]}"))
        print(field("help", "Use a bare ID or a full node name from the vault."))
        return 1
    print(field("target", view.target))
    print(field("target_context_rev", str(view.target_context_rev)))
    print(
        index.format_table(
            "impact",
            "dependent,status,depth,relation,dependency,pinned,current,stale",
            "impact: 0 dependents",
            [
                (
                    edge.dependent,
                    edge.status,
                    str(edge.depth),
                    edge.relation,
                    edge.dependency,
                    edge.pinned,
                    edge.current,
                    edge.stale,
                )
                for edge in view.edges
            ],
        )
    )
    return 0


def _orient(args: list[str]) -> int:
    sections: list[str] = []
    limit_raw = "10"
    index_arg = 1
    while index_arg < len(args):
        argument = args[index_arg]
        if argument == "--section":
            index_arg += 1
            if index_arg >= len(args):
                return _usage_error("--section requires a section name")
            sections.append(args[index_arg])
        elif argument == "--limit":
            index_arg += 1
            if index_arg >= len(args):
                return _usage_error("--limit requires N")
            limit_raw = args[index_arg]
        else:
            return _usage_error(f"unknown argument for orient: {argument}")
        index_arg += 1
    for name in sections:
        if name not in index.ORIENT_SECTIONS:
            return _usage_error(
                f"unknown section: {name}; choose from " + ", ".join(index.ORIENT_SECTIONS)
            )
    if _POSITIVE_INTEGER.fullmatch(limit_raw) is None or int(limit_raw) <= 0:
        return _usage_error("--limit must be a positive integer")
    root = _require_nodes_directory()
    if root is None:
        return 1
    packet = index.orient(root, sections or None, int(limit_raw))
    for section in packet.sections:
        print(field("section", section.name))
        print(field("total", str(section.total)))
        print(
            index.format_table(
                section.name,
                section.header,
                section.empty,
                section.rows,
            )
        )
    return 0


def _dispatch(command: str, args: list[str]) -> int:
    if command == "status":
        if len(args) != 1:
            return _usage_error("status accepts no arguments")
        _print_fields(sidecar.status_fields())
        print(
            index.format_table(
                "reservations",
                "prefix,next",
                "reservations: 0 prefixes",
                sidecar.reservations(),
            )
        )
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
        sidecar.reconcile_sequences(index.prefix_maxima(_nodes_directory()))
        print(field("result", "initialized"))
        _print_fields(sidecar.location_fields())
        return 0
    if command == "allocate":
        return _allocate(args)
    if command == "claim":
        return _claim(args)
    if command == "release":
        return _release(args)
    if command == "index":
        if len(args) > 2:
            return _usage_error("index accepts at most one NODES directory")
        root = args[1] if len(args) == 2 else _nodes_directory()
        nodes, edges, absolute_root = _index_guard(lambda: _run_reindex(root))
        print(f"nodes: {nodes}")
        print(f"edges: {edges}")
        print(f"root: {absolute_root}")
        return 0
    if command == "search":
        return _search(args)
    if command == "similar":
        return _similar(args)
    if command == "backlinks":
        return _backlinks(args)
    if command == "hash":
        return _hash(args)
    if command == "frontier":
        return _frontier(args)
    if command == "node":
        return _node(args)
    if command == "impact":
        return _impact(args)
    if command == "orient":
        return _orient(args)
    if command == "next":
        return _next(args)
    return _stale(args)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the sidecar/index command group and return the process exit code."""
    args = list(sys.argv[1:] if argv is None else argv)
    if len(args) == 1 and args[0] in {"--version", "-v", "-V"}:
        print(reported_version())
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
