"""Rebuildable Markdown-derived graph index.

Typed Python implementation of the Markdown index builder. Durable graph state stays in
Markdown; this module rebuilds the disposable ``nodes``, ``edges``, and FTS
rows plus the search, backlinks, and stale-pin queries over them, and derives
the direct ``frontier`` and ``node_view`` answers from the same Markdown.
"""

from __future__ import annotations

import glob
import os
import re
import sqlite3
from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from .graph_check import (
    CONTEXT_PIN_LINE,
    CONTEXT_RELATIONS,
    context_pin_problem,
    stale_reason,
)
from .sidecar import SidecarError, content_hash

__all__ = [
    "Backlink",
    "ContextEdge",
    "FrontierEntry",
    "IndexedNode",
    "NodeView",
    "backlinks",
    "ensure_index_schema",
    "existing_allocations",
    "format_table",
    "frontier",
    "node_hash",
    "node_view",
    "prefix_maxima",
    "reindex",
    "resolve_node",
    "search",
    "stale",
]

_STATUSES = frozenset({"proposed", "active", "blocked", "resolved"})
_FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_NODE_ID = re.compile(r"([A-Z][A-Z0-9_]*-\d+)-")
_EDGE = re.compile(
    r"^([A-Za-z][A-Za-z ]*?)\s+\[\[([^\]]+)\]\](?:\s+at context_rev\s+(\d+))?\.?\s*$",
    re.MULTILINE,
)
# The relation set is the one canonical context-edge definition; capturing the
# relation lets the direct view name the edge exactly as ``stale`` does.
_CONTEXT_EDGE = re.compile(
    r"^(" + "|".join(CONTEXT_RELATIONS) + r")\s+\[\[([^\]]+)\]\](.*)$",
    re.MULTILINE,
)
_PRIMARY_ROUTE = re.compile(r"^(Parent|Area) \[\[([^\]]+)\]\]\.", re.MULTILINE)

_INDEX_SCHEMA = """
CREATE TABLE IF NOT EXISTS nodes (
  id TEXT PRIMARY KEY, path TEXT UNIQUE NOT NULL, type TEXT NOT NULL,
  status TEXT NOT NULL, summary TEXT, context_rev INTEGER,
  content_hash TEXT NOT NULL, indexed_at TEXT NOT NULL, body TEXT NOT NULL
);
CREATE TABLE IF NOT EXISTS edges (
  source_id TEXT NOT NULL, relation TEXT NOT NULL, target_id TEXT NOT NULL,
  pinned_context_rev INTEGER, PRIMARY KEY(source_id, relation, target_id)
);
CREATE INDEX IF NOT EXISTS edges_target ON edges(target_id);
CREATE INDEX IF NOT EXISTS edges_source ON edges(source_id);
CREATE VIRTUAL TABLE IF NOT EXISTS nodes_fts USING fts5(id UNINDEXED, summary, body);
CREATE TABLE IF NOT EXISTS graph_meta (key TEXT PRIMARY KEY, value TEXT NOT NULL);
"""


def ensure_index_schema(conn: sqlite3.Connection) -> None:
    """Create the derived index tables when they are absent."""
    conn.executescript(_INDEX_SCHEMA)


def _frontmatter(text: str) -> tuple[dict[str, str], str]:
    match = _FRONTMATTER.match(text)
    if not match:
        return {}, text
    fields: dict[str, str] = {}
    for line in match.group(1).splitlines():
        key, separator, value = line.partition(":")
        if not separator:
            continue
        value = value.strip()
        if len(value) >= 2 and value.startswith('"') and value.endswith('"'):
            value = value[1:-1]
        fields[key] = value
    return fields, text[match.end() :]


def _context_rev(fields: dict[str, str]) -> int:
    raw = fields.get("context_rev")
    if not raw:
        return 0
    try:
        return int(raw)
    except ValueError as exc:
        raise SidecarError(f"invalid context_rev in frontmatter: {raw}") from exc


def _now() -> str:
    return datetime.now(UTC).replace(microsecond=0).strftime("%Y-%m-%dT%H:%M:%SZ")


def _read_index_rows(root: str) -> tuple[list[tuple[object, ...]], list[tuple[object, ...]]]:
    rows: list[tuple[object, ...]] = []
    edge_rows: list[tuple[object, ...]] = []
    for path in sorted(glob.glob(os.path.join(root, "*", "*.md"))):
        status = os.path.basename(os.path.dirname(path))
        if status not in _STATUSES:
            continue
        basename = os.path.basename(path)[:-3]
        match = _NODE_ID.match(basename)
        if match is None:
            continue
        node_id = match.group(1)
        with open(path, "rb") as handle:
            raw = handle.read()
        text = raw.decode("utf-8")
        header, body = _frontmatter(text)
        relative = os.path.relpath(path, root)
        rows.append(
            (
                node_id,
                relative,
                node_id.split("-", 1)[0],
                status,
                header.get("summary", ""),
                _context_rev(header),
                content_hash(raw),
                _now(),
                body,
            )
        )
        for relation, target, pin in _EDGE.findall(body):
            edge_rows.append((node_id, relation.strip(), target, int(pin) if pin else None))
    names = {os.path.basename(str(row[1]))[:-3]: str(row[0]) for row in rows}
    resolved: list[tuple[object, ...]] = [
        (source, relation, names.get(str(target), target), pin)
        for source, relation, target, pin in edge_rows
    ]
    deduped: list[tuple[object, ...]] = list(dict.fromkeys(resolved))
    return rows, deduped


def existing_allocations(root: str) -> dict[str, set[int]]:
    """Return the numeric suffixes already used per node-ID prefix under ``root``.

    A filename supplies its identity, so allocation can refuse an integer that
    would collide with an existing node even when the sidecar counter is stale.
    """
    taken: dict[str, set[int]] = {}
    for path in glob.glob(os.path.join(os.path.abspath(root), "*", "*.md")):
        status = os.path.basename(os.path.dirname(path))
        if status not in _STATUSES:
            continue
        match = _NODE_ID.match(os.path.basename(path)[:-3])
        if match is None:
            continue
        prefix, _, digits = match.group(1).rpartition("-")
        taken.setdefault(prefix, set()).add(int(digits))
    return taken


def prefix_maxima(root: str) -> dict[str, int]:
    """Return the highest numeric suffix already used per prefix under ``root``."""
    return {prefix: max(values) for prefix, values in existing_allocations(root).items()}


def node_hash(root: str, node: str) -> str | None:
    """Return the raw-content SHA-256 for a bare ID or full node name under ``root``.

    Reads Markdown alone so the value is available before any sidecar exists,
    and matches the ``content_hash`` the index stores.
    """
    root = os.path.abspath(root)
    for path in sorted(glob.glob(os.path.join(root, "*", "*.md"))):
        status = os.path.basename(os.path.dirname(path))
        if status not in _STATUSES:
            continue
        basename = os.path.basename(path)[:-3]
        match = _NODE_ID.match(basename)
        if match is None or node not in {basename, match.group(1)}:
            continue
        with open(path, "rb") as handle:
            return content_hash(handle.read())
    return None


def _upsert_reservations(
    conn: sqlite3.Connection, maxima: dict[str, int]
) -> None:
    """Raise each prefix reservation above the Markdown maximum."""
    for prefix, maximum in maxima.items():
        conn.execute(
            "INSERT INTO id_sequences(prefix,next_value) VALUES(?, ?) "
            "ON CONFLICT(prefix) DO UPDATE SET next_value = "
            "MAX(id_sequences.next_value, excluded.next_value)",
            (prefix, maximum + 1),
        )


def reindex(conn: sqlite3.Connection, root: str) -> tuple[int, int, str]:
    """Rebuild derived node, edge, and FTS rows from Markdown under ``root``."""
    root = os.path.abspath(root)
    if not os.path.isdir(root):
        raise SidecarError(f"nodes directory does not exist: {root}")
    ensure_index_schema(conn)
    rows, edges = _read_index_rows(root)
    maxima: dict[str, int] = {}
    for row in rows:
        prefix, _, digits = str(row[0]).rpartition("-")
        maxima[prefix] = max(maxima.get(prefix, 0), int(digits))
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute("DELETE FROM edges")
        conn.execute("DELETE FROM nodes_fts")
        conn.execute("DELETE FROM nodes")
        conn.executemany(
            "INSERT INTO nodes VALUES(?,?,?,?,?,?,?,?,?)",
            rows,
        )
        conn.executemany(
            "INSERT INTO nodes_fts VALUES(?,?,?)",
            [(str(row[0]), row[4], row[8]) for row in rows],
        )
        conn.executemany("INSERT INTO edges VALUES(?,?,?,?)", edges)
        _upsert_reservations(conn, maxima)
        conn.execute(
            "INSERT INTO graph_meta(key,value) VALUES('nodes_root',?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (root,),
        )
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    return len(rows), len(edges), root


def search(conn: sqlite3.Connection, query: str, limit: int) -> list[tuple[str, str, str]]:
    """Return ``id``, ``status``, and ``summary`` for the best FTS matches."""
    try:
        cursor = conn.execute(
            "SELECT COALESCE(n.id,''),COALESCE(n.status,''),COALESCE(n.summary,'') "
            "FROM nodes_fts JOIN nodes n ON n.id=nodes_fts.id "
            "WHERE nodes_fts MATCH ? ORDER BY bm25(nodes_fts) LIMIT ?",
            (query, limit),
        )
    except sqlite3.OperationalError as exc:
        raise SidecarError(
            "invalid full-text query; use words, quoted phrases, or AND/OR"
        ) from exc
    return [(str(row[0]), str(row[1]), str(row[2])) for row in cursor.fetchall()]


def resolve_node(conn: sqlite3.Connection, node: str) -> str | None:
    """Resolve a bare ID or full node name to the indexed node ID."""
    row = conn.execute("SELECT id FROM nodes WHERE id = ?", (node,)).fetchone()
    if row is not None:
        return str(row[0])
    for candidate_id, path in conn.execute("SELECT id, path FROM nodes").fetchall():
        if os.path.basename(str(path))[:-3] == node:
            return str(candidate_id)
    return None


def backlinks(conn: sqlite3.Connection, node: str) -> list[tuple[str, str, str, str]]:
    """Return incoming edges for ``node`` as source, status, relation, pin."""
    cursor = conn.execute(
        "SELECT COALESCE(e.source_id,''),COALESCE(n.status,''),COALESCE(e.relation,''),"
        "COALESCE(e.pinned_context_rev,'') "
        "FROM edges e LEFT JOIN nodes n ON n.id=e.source_id "
        "WHERE e.target_id=? ORDER BY e.source_id,e.relation",
        (node,),
    )
    return [(str(row[0]), str(row[1]), str(row[2]), str(row[3])) for row in cursor.fetchall()]


def stale(conn: sqlite3.Connection) -> list[tuple[str, str, str, str, str, str, str]]:
    """Return the context edges that need reconciliation and the shared verdict.

    The rows are exactly the canonical context edges
    :data:`braintree.graph_check.CONTEXT_RELATIONS` defines, filtered by the
    same verdict ``braintree check`` reaches: a pin that is missing, a target
    that is missing, a target that is not resolved, or a revision that differs
    from the pin.
    """
    placeholders = ",".join("?" for _ in CONTEXT_RELATIONS)
    cursor = conn.execute(
        "SELECT COALESCE(e.source_id,''),COALESCE(n.status,''),"
        "COALESCE(e.target_id,''),COALESCE(e.pinned_context_rev,''),"
        "COALESCE(d.context_rev,''),COALESCE(e.relation,''),d.status "
        "FROM edges e JOIN nodes n ON n.id=e.source_id "
        "LEFT JOIN nodes d ON d.id=e.target_id "
        f"WHERE e.relation IN ({placeholders}) "
        "ORDER BY e.source_id,e.target_id,e.relation",
        CONTEXT_RELATIONS,
    )
    rows: list[tuple[str, str, str, str, str, str, str]] = []
    for row in cursor.fetchall():
        source, source_status, target, pinned, current, relation, target_status = row
        pinned_rev = int(pinned) if pinned != "" else None
        current_rev = int(current) if current != "" else None
        status = str(target_status) if target_status is not None else None
        problem = context_pin_problem(pinned_rev, status, current_rev)
        if problem is None:
            continue
        rows.append(
            (
                str(source),
                str(source_status),
                str(target),
                str(pinned),
                str(current),
                str(relation),
                stale_reason(problem, status),
            )
        )
    return rows


def format_table(
    name: str,
    header: str,
    empty_message: str,
    rows: Sequence[Sequence[str]],
) -> str:
    """Render an indented TOON-style table or the explicit zero-result line."""
    if not rows:
        return empty_message
    lines = [f"{name}[{len(rows)}]{{{header}}}:"]
    for row in rows:
        cells = ",".join('"' + str(value).replace('"', '\\"') + '"' for value in row)
        lines.append(f"  {cells}")
    return "\n".join(lines)


@dataclass(frozen=True)
class IndexedNode:
    """One Markdown node read from a status directory."""

    id: str
    name: str
    path: str
    status: str
    metadata: dict[str, str]
    body: str


@dataclass(frozen=True)
class FrontierEntry:
    """One actionable frontier candidate."""

    id: str
    status: str
    priority: str
    summary: str
    next: str
    stale: bool


@dataclass(frozen=True)
class ContextEdge:
    """One context edge with its pin, the target's current revision, and verdict."""

    relation: str
    target: str
    pinned: str
    current: str
    status: str
    stale: str


@dataclass(frozen=True)
class Backlink:
    """One incoming edge pointing at the node."""

    source: str
    status: str
    relation: str
    pinned: str


@dataclass(frozen=True)
class NodeView:
    """The graph view ``braintree node`` prints for one resolved node."""

    node: IndexedNode
    route_relation: str
    route: str
    context_edges: tuple[ContextEdge, ...]
    backlinks: tuple[Backlink, ...]


def _read_nodes(root: str) -> list[IndexedNode]:
    """Read every Markdown node under ``root`` from its status directory."""
    root = os.path.abspath(root)
    nodes: list[IndexedNode] = []
    for path in sorted(glob.glob(os.path.join(root, "*", "*.md"))):
        status = os.path.basename(os.path.dirname(path))
        if status not in _STATUSES:
            continue
        basename = os.path.basename(path)[:-3]
        match = _NODE_ID.match(basename)
        if match is None:
            continue
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
        header, body = _frontmatter(text)
        nodes.append(
            IndexedNode(
                id=match.group(1),
                name=basename,
                path=os.path.relpath(path, root),
                status=status,
                metadata=header,
                body=body,
            )
        )
    return nodes


def _target_context_rev(node: IndexedNode | None) -> int | None:
    if node is None:
        return None
    return _context_rev(node.metadata)


def _context_edges(
    node: IndexedNode, by_name: dict[str, IndexedNode]
) -> tuple[ContextEdge, ...]:
    edges: list[ContextEdge] = []
    for relation, target, suffix in _CONTEXT_EDGE.findall(node.body):
        pin_match = CONTEXT_PIN_LINE.fullmatch(suffix)
        pinned = int(pin_match.group(1)) if pin_match is not None else None
        target_node = by_name.get(target)
        current = _target_context_rev(target_node)
        target_status = target_node.status if target_node is not None else None
        problem = context_pin_problem(pinned, target_status, current)
        edges.append(
            ContextEdge(
                relation=relation,
                target=target,
                pinned=str(pinned) if pinned is not None else "",
                current=str(current) if current is not None else "",
                status=target_status if target_status is not None else "",
                stale="" if problem is None else stale_reason(problem, target_status),
            )
        )
    edges.sort(key=lambda edge: (edge.target, edge.relation))
    return tuple(edges)


def _is_stale(node: IndexedNode, by_name: dict[str, IndexedNode]) -> bool:
    return any(edge.stale != "" for edge in _context_edges(node, by_name))


def frontier(root: str) -> list[FrontierEntry]:
    """Return the unfinished nodes whose ``next`` is an action rather than a route."""
    nodes = _read_nodes(root)
    by_name = {node.name: node for node in nodes}
    entries: list[FrontierEntry] = []
    for node in nodes:
        if node.status == "resolved":
            continue
        next_value = node.metadata.get("next", "")
        if "[[" in next_value:
            continue
        entries.append(
            FrontierEntry(
                id=node.id,
                status=node.status,
                priority=node.metadata.get("priority", ""),
                summary=node.metadata.get("summary", ""),
                next=next_value,
                stale=_is_stale(node, by_name),
            )
        )
    entries.sort(key=lambda entry: entry.id)
    return entries


def _backlinks_for(node: IndexedNode, nodes: list[IndexedNode]) -> tuple[Backlink, ...]:
    backlinks: list[Backlink] = []
    for source in nodes:
        for relation, target, pin in _EDGE.findall(source.body):
            if target not in {node.name, node.id}:
                continue
            backlinks.append(
                Backlink(
                    source=source.id,
                    status=source.status,
                    relation=relation.strip(),
                    pinned=pin,
                )
            )
    backlinks.sort(key=lambda edge: (edge.source, edge.relation))
    return tuple(backlinks)


def node_view(root: str, node: str) -> NodeView | None:
    """Resolve a bare ID or full node name and return its Markdown graph view."""
    nodes = _read_nodes(root)
    target = next(
        (candidate for candidate in nodes if node in {candidate.id, candidate.name}),
        None,
    )
    if target is None:
        return None
    by_name = {candidate.name: candidate for candidate in nodes}
    route_match = _PRIMARY_ROUTE.search(target.body)
    return NodeView(
        node=target,
        route_relation=route_match.group(1) if route_match is not None else "",
        route=route_match.group(2) if route_match is not None else "",
        context_edges=_context_edges(target, by_name),
        backlinks=_backlinks_for(target, nodes),
    )
