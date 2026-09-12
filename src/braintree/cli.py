"""The sidecar and index query command group behind ``braintree``.

The command names, their arguments, the TOON field styling, and the
``0``/``1``/``2`` exit codes are the internal engine the unified
``braintree`` command fronts. Coordination lives in :mod:`braintree.sidecar`
and the rebuildable Markdown index in :mod:`braintree.index`.
"""

from __future__ import annotations

import os
import re
import sqlite3
import sys
import time
from collections.abc import Callable, Sequence

from . import index, semantic, sidecar
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
    "orient [--section NAME] [--limit N]|next [--rank] [--limit N]|"
    "clusters [--limit N]|digest NODE [--limit N]|"
    "reconcile [--base REF] [--head REF ...] [NODES]]"
)

_COMMANDS: tuple[tuple[str, str], ...] = (
    ("status", "show the current sidecar state"),
    ("location", "show the stable project identity and database path"),
    ("init", "create or repair the local sidecar"),
    ("allocate PREFIX", "atomically allocate PREFIX-NNN"),
    (
        "claim NODE AGENT --base-hash HASH [--lease-seconds N]",
        "acquire or renew an exclusive lease (default 900 seconds)",
    ),
    (
        "release NODE AGENT --base-hash HASH",
        "release the matching lease or report it expired",
    ),
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
    (
        "frontier [--group] [--limit N]",
        "list frontier candidates or cluster them into advisory workstreams",
    ),
    ("node NODE", "show one node's frontmatter, route, edges, and backlinks"),
    ("impact NODE", "list direct and transitive dependents of a node"),
    ("orient [--section NAME] [--limit N]", "print a bounded orientation packet"),
    ("next [--rank] [--limit N]", "rank frontier candidates for the next actor"),
    (
        "clusters [--limit N]",
        "list advisory clusters, over-broad routes, and outlier nodes",
    ),
    ("digest NODE [--limit N]", "digest a hub's or node's unresolved direct members"),
    (
        "reconcile [--base REF] [--head REF ...] [NODES]",
        "plan duplicate, divergence, and stale-pin repairs from a Git change set",
    ),
)

_PREFIX = re.compile(r"[A-Z0-9_-]*\Z")
_POSITIVE_INTEGER = re.compile(r"[0-9]+\Z")
# The only accepted ``--base-hash`` operand is the bare digest ``braintree hash``
# prints, so the labelled ``node:``/``content_hash:`` block, a short placeholder,
# or an uppercase digest can never become a recorded lease identity.
_BASE_HASH = re.compile(r"[0-9a-f]{64}\Z")
_STATUSES = frozenset({"proposed", "active", "blocked", "resolved"})
_NODE_STEM = re.compile(r"([A-Z][A-Z0-9_]*-\d+)-")
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

# ``clusters`` is an explicit, derived answer: it states its advisory status on
# every path and is bounded by ``--limit`` rows plus this wall-clock budget. The
# semantic seam already caps each provider call at its own timeout and the
# derived layer caps the sample count, so the budget only stops the heavy fit
# when the embedding phase alone has already exhausted it.
_CLUSTERS_ADVISORY = "clusters are advisory, derived, and are not work claims"
_CLUSTERS_TIME_BUDGET_SECONDS = 60.0
_CLUSTERS_DEFAULT_LIMIT = "10"
_DIGEST_DEFAULT_LIMIT = "20"


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


def _base_hash_error(value: str) -> int:
    """Reject a base hash that is not the bare digest ``braintree hash`` prints.

    The accepted operand is one bare 64-character lowercase hex digest, so the
    labelled ``node:``/``content_hash:`` block, a short placeholder, or an
    uppercase digest fails here, before any sidecar write.
    """
    return _usage_error(
        "--base-hash must be a bare 64-character lowercase hex digest, not "
        f"{value!r}"
    )


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


def _unknown_node(node: str) -> int:
    """Print the unknown-node error and name the accepted addressing forms.

    A path-shaped operand is the common handoff mistake, so when the operand
    looks like a path the help names the bare ID and full node name derived
    from it instead of repeating the generic form.
    """
    print(field("error", f"unknown node: {node}"))
    if "/" not in node and not node.endswith(".md"):
        print(field("help", "Use a bare ID or a full node name from the vault."))
        return 1
    stem = os.path.basename(node.removesuffix(".md"))
    match = _NODE_STEM.match(stem)
    if match is None:
        print(
            field(
                "help",
                "Use a bare ID or a full node name from the vault, not a path.",
            )
        )
        return 1
    print(
        field(
            "help",
            f"Use the bare ID '{match.group(1)}' or the full node name "
            f"'{stem}', not a path.",
        )
    )
    return 1


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
    if _BASE_HASH.fullmatch(base_hash) is None:
        return _base_hash_error(base_hash)
    if _POSITIVE_INTEGER.fullmatch(lease_raw) is None or int(lease_raw) <= 0:
        return _usage_error("--lease-seconds must be a positive integer")
    try:
        owner, recorded_hash, recorded_expiry, remaining = sidecar.claim(
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
    print(field("lease_remaining_seconds", remaining))
    return 0


def _release(args: list[str]) -> int:
    if len(args) != 5 or args[3] != "--base-hash":
        return _usage_error("release requires NODE AGENT --base-hash HASH")
    node, agent, base_hash = args[1], args[2], args[4]
    if node == "" or agent == "" or base_hash == "":
        return _usage_error("release requires non-empty NODE, AGENT, and HASH")
    if _BASE_HASH.fullmatch(base_hash) is None:
        return _base_hash_error(base_hash)
    try:
        result, remaining = sidecar.release(node, agent, base_hash)
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
    print(field("lease_remaining_seconds", remaining))
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
    # The semantic provider is optional: without ``BT_SEMANTIC_PROVIDER`` no
    # process runs, and an unhealthy provider degrades to the lexical baseline.
    provider = semantic.probe()
    connection: sqlite3.Connection | None = None
    if provider is not None:
        try:
            connection = sidecar.open_connection()
        except sidecar.SidecarError:
            provider = None
    try:
        rows = index.similar(root, text, int(limit_raw), provider, connection)
    finally:
        if connection is not None:
            connection.close()
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
        return _unknown_node(node)
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
        return _unknown_node(node)
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
        return _unknown_node(args[1])
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
        return _unknown_node(args[1])
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


def _clusters(args: list[str]) -> int:
    limit_raw = _CLUSTERS_DEFAULT_LIMIT
    index_arg = 1
    while index_arg < len(args):
        argument = args[index_arg]
        if argument == "--limit":
            index_arg += 1
            if index_arg >= len(args):
                return _usage_error("--limit requires N")
            limit_raw = args[index_arg]
        else:
            return _usage_error(f"unknown argument for clusters: {argument}")
        index_arg += 1
    if _POSITIVE_INTEGER.fullmatch(limit_raw) is None or int(limit_raw) <= 0:
        return _usage_error("--limit must be a positive integer")
    root = _require_nodes_directory()
    if root is None:
        return 1
    # The capability is probed cheaply before any heavy import: an absent extra
    # or provider answers with an advisory line and no model load.
    extra = semantic.extra()
    provider = semantic.probe() if extra is not None else None
    if provider is None:
        print(field("advisory", _CLUSTERS_ADVISORY))
        print(field("clusters", "capability absent"))
        print(
            field(
                "help",
                "Install the semantic extra and set BT_SEMANTIC_PROVIDER to cluster.",
            )
        )
        return 0
    started = time.monotonic()
    try:
        connection = sidecar.open_connection()
    except sidecar.SidecarError:
        print(field("advisory", _CLUSTERS_ADVISORY))
        print(field("clusters", "capability absent"))
        print(field("help", "Run `braintree init` to create the vector cache."))
        return 0
    try:
        # The clustering layer is imported lazily, so the absent path above
        # never binds it and a plain install loads no heavy module.
        from . import clustering

        sources = index.cluster_source(root, clustering.MAX_SAMPLES)
        items = [(source.content_hash, source.text) for source in sources]
        vectors = semantic.vectors(provider, connection, items)
        if vectors is not None and time.monotonic() - started <= _CLUSTERS_TIME_BUDGET_SECONDS:
            answer = clustering.answer(
                vectors,
                provider.key,
                connection,
                {
                    source.content_hash: clustering.NodeFacts(
                        node_id=source.id, route=source.route
                    )
                    for source in sources
                },
                int(limit_raw),
            )
        else:
            answer = None
    finally:
        connection.close()
    print(field("advisory", _CLUSTERS_ADVISORY))
    if vectors is None:
        print(field("clusters", "no embeddings"))
        print(field("help", "Check the provider command and retry."))
        return 0
    if answer is None:
        print(field("clusters", "time budget exhausted"))
        print(field("help", "Reduce the vault or provider latency and retry."))
        return 0
    if not answer.available:
        print(field("clusters", "no embeddings"))
        return 0
    print(field("limit", limit_raw))
    print(field("space", answer.space))
    if answer.method:
        print(field("method", answer.method))
    print(
        field(
            "params",
            f"min_cluster_size={answer.params.min_cluster_size},"
            f"min_samples={answer.params.min_samples}",
        )
    )
    print(
        index.format_table(
            "stability",
            "space,runs,ari",
            "stability: 0 spaces",
            [(row.space, str(row.runs), f"{row.ari:.4f}") for row in answer.stability],
        )
    )
    print(field("clusters_total", str(answer.total_clusters)))
    print(
        index.format_table(
            "clusters",
            "id,representative,route,members",
            "clusters: 0 clusters",
            [
                (str(cluster.id), cluster.representative, cluster.route, str(len(cluster.members)))
                for cluster in answer.clusters
            ],
        )
    )
    print(field("over_broad_total", str(answer.total_over_broad)))
    print(
        index.format_table(
            "over_broad",
            "route,clusters,members",
            "over_broad: 0 over-broad routes",
            [
                (row.route, str(row.clusters), str(row.members))
                for row in answer.over_broad
            ],
        )
    )
    print(field("noise_total", str(answer.total_noise)))
    print(
        index.format_table(
            "noise",
            "node",
            "noise: 0 orphan nodes",
            [(member,) for member in answer.noise],
        )
    )
    print(field("outliers_total", str(answer.total_outliers)))
    print(
        index.format_table(
            "outliers",
            "node",
            "outliers: 0 outliers",
            [(member,) for member in answer.outliers],
        )
    )
    return 0


def _digest(args: list[str]) -> int:
    if len(args) < 2 or args[1].startswith("--"):
        return _usage_error("digest requires NODE")
    node = args[1]
    limit_raw = _DIGEST_DEFAULT_LIMIT
    index_arg = 2
    while index_arg < len(args):
        argument = args[index_arg]
        if argument == "--limit":
            index_arg += 1
            if index_arg >= len(args):
                return _usage_error("--limit requires N")
            limit_raw = args[index_arg]
        else:
            return _usage_error(f"unknown argument for digest: {argument}")
        index_arg += 1
    if _POSITIVE_INTEGER.fullmatch(limit_raw) is None or int(limit_raw) <= 0:
        return _usage_error("--limit must be a positive integer")
    root = _require_nodes_directory()
    if root is None:
        return 1
    result = index.digest(root, node, int(limit_raw))
    if result is None:
        return _unknown_node(node)
    print(field("target", result.target))
    print(field("status", result.status))
    print(field("total", str(result.total)))
    print(
        index.format_table(
            "members",
            "id,status,priority,updated,summary,next",
            "members: 0 unresolved members",
            [
                (
                    member.id,
                    member.status,
                    member.priority,
                    member.updated,
                    member.summary,
                    member.next,
                )
                for member in result.members
            ],
        )
    )
    return 0


def _reconcile(args: list[str]) -> int:
    base = "HEAD"
    heads: list[str] = []
    nodes_arg: str | None = None
    index_arg = 1
    while index_arg < len(args):
        argument = args[index_arg]
        if argument == "--base":
            index_arg += 1
            if index_arg >= len(args):
                return _usage_error("--base requires REF")
            base = args[index_arg]
        elif argument == "--head":
            index_arg += 1
            if index_arg >= len(args):
                return _usage_error("--head requires REF")
            heads.append(args[index_arg])
        elif argument.startswith("-"):
            return _usage_error(f"unknown argument for reconcile: {argument}")
        elif nodes_arg is None:
            nodes_arg = argument
        else:
            return _usage_error("reconcile accepts at most one NODES directory")
        index_arg += 1
    if nodes_arg is None:
        root = _require_nodes_directory()
        if root is None:
            return 1
    elif not os.path.isdir(nodes_arg):
        print(field("error", f"nodes directory does not exist: {os.path.abspath(nodes_arg)}"))
        print(field("help", "Run from the project root or set BT_NODES_DIR."))
        return 1
    else:
        root = nodes_arg
    try:
        plan = index.reconcile(base, heads or ["HEAD"], root)
    except index.ReconcileError as exc:
        print(field("error", str(exc)))
        print(
            field(
                "help",
                "Run inside the vault's Git repository and pass refs it knows.",
            )
        )
        return 1
    print(field("base", plan.base))
    print(
        index.format_table(
            "head",
            "ref",
            "head: 0 refs",
            [(head,) for head in plan.heads],
        )
    )
    print(
        index.format_table(
            "steps",
            "action,depth,node,path,pinned,current,detail",
            "reconcile: 0 steps",
            [
                (
                    step.action,
                    str(step.depth),
                    step.node,
                    step.path,
                    step.pinned,
                    step.current,
                    step.detail,
                )
                for step in plan.steps
            ],
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
    if command == "clusters":
        return _clusters(args)
    if command == "digest":
        return _digest(args)
    if command == "reconcile":
        return _reconcile(args)
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
