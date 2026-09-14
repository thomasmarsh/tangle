"""Rebuildable Markdown-derived graph index.

Typed Python implementation of the Markdown index builder. Durable graph state stays in
Markdown; this module rebuilds the disposable ``nodes``, ``edges``, and FTS
rows plus the search, backlinks, and stale-pin queries over them, and derives
the direct ``frontier``, ``node_view``, ``impact``, and ``orient`` answers from
the same Markdown. The same derivation also ranks the frontier for ``next``
and clusters it into advisory workstreams for ``frontier --group``. The
structured ``search`` filters and the lexical ``similar`` baseline are likewise
derived from Markdown, so an admission or filter decision never depends on a
derived sidecar column. The ``digest`` answer bounds a hub's or coordinating
node's unresolved direct members, and ``cluster_source`` gathers only the
per-node embedding inputs the optional clustering verb feeds to the derived
layer. The ``reconcile`` planner reads that same Markdown out of Git snapshots
to classify the integration hazards a coordinator resolves by hand before a
merge.
"""

from __future__ import annotations

import math
import os
import re
import sqlite3
import subprocess
from collections import Counter, deque
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from functools import lru_cache

from . import semantic, store
from .graph_check import (
    CONTEXT_PIN_LINE,
    CONTEXT_RELATIONS,
    context_pin_problem,
    findings,
    reference_targets,
    stale_reason,
)
from .sidecar import SidecarError, content_hash

__all__ = [
    "Backlink",
    "ClusterSource",
    "ContextEdge",
    "Digest",
    "DigestMember",
    "FrontierEntry",
    "FrontierGroups",
    "GroupedCandidate",
    "Impact",
    "ImpactEdge",
    "IndexedNode",
    "NextRanking",
    "NodeView",
    "ORIENT_SECTIONS",
    "OrientSection",
    "Orientation",
    "RankedCandidate",
    "Reconnaissance",
    "ReconcileError",
    "ReconcilePlan",
    "ReconcileStep",
    "ReferenceView",
    "SearchFilters",
    "SimilarCandidate",
    "backlinks",
    "cluster_source",
    "digest",
    "ensure_index_schema",
    "existing_allocations",
    "format_table",
    "frontier",
    "frontier_groups",
    "impact",
    "next_ranked",
    "node_hash",
    "node_view",
    "orient",
    "prefix_maxima",
    "reconcile",
    "reference_view",
    "reindex",
    "refresh",
    "resolve_node",
    "search",
    "search_filter",
    "similar",
    "stale",
    "stale_pins",
]

_STATUSES = frozenset({"proposed", "active", "blocked", "resolved"})
_FRONTMATTER = re.compile(r"\A---\s*\n(.*?)\n---\s*\n", re.DOTALL)
_NODE_ID = re.compile(
    r"((?:[A-Z][A-Z0-9_]*-\d+|(?:tas|tho|def|dec|idx|fbk)-[0-7][0-9a-hjkmnp-tv-z]{25}))(?:-|$)"
)
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
# ``# Focus`` is the advisory orientation pointer list in ``index-map.md``; the
# block ends at the next heading, and the checker validates the same targets.
_FOCUS_BLOCK = re.compile(r"^# Focus\n(.*?)(?=^# |\Z)", re.MULTILINE | re.DOTALL)
_WIKILINK = re.compile(r"\[\[([^\]]+)\]\]")
# Lowercased alphanumeric tokens are the lexical unit the ``similar`` baseline
# compares, so the metric is independent of punctuation and casing.
_ALNUM = re.compile(r"[a-z0-9]+")

# The orientation packet answers the fixed cold-start questions in one bounded
# call. Output order is this order, and each section is truncated to the
# requested limit while ``total`` keeps the unbounded count.
ORIENT_SECTIONS: tuple[str, ...] = (
    "focus",
    "frontier",
    "blockers",
    "stale",
    "recent",
    "conflicts",
)

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


@dataclass(frozen=True)
class _DerivedNode:
    """One Markdown node in the shape the derived ``nodes`` table stores."""

    id: str
    path: str
    type: str
    status: str
    summary: str
    context_rev: int
    content_hash: str
    body: str

    def row(self, indexed_at: str) -> tuple[object, ...]:
        """Return the row for ``INSERT INTO nodes`` with its indexing stamp."""
        return (
            self.id,
            self.path,
            self.type,
            self.status,
            self.summary,
            self.context_rev,
            self.content_hash,
            indexed_at,
            self.body,
        )


# One derived edge as ``edges`` stores it: the pin empty rather than ``None`` so
# a stored row and a freshly derived row compare equal.
DerivedEdge = tuple[str, str, str, str]


def _read_snapshot(root: str) -> tuple[list[_DerivedNode], list[DerivedEdge]]:
    """Read the derived node and edge snapshot the Markdown under ``root`` defines."""
    nodes: list[_DerivedNode] = []
    edge_rows: list[tuple[str, str, str, int | None]] = []
    for entry in store.iter_node_paths(root):
        path, status = entry.path, entry.status
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
        nodes.append(
            _DerivedNode(
                id=node_id,
                path=os.path.relpath(path, root),
                type=node_id.split("-", 1)[0],
                status=status,
                summary=header.get("summary", ""),
                context_rev=_context_rev(header),
                content_hash=content_hash(raw),
                body=body,
            )
        )
        for relation, target, pin in _EDGE.findall(body):
            edge_rows.append((node_id, relation.strip(), target, int(pin) if pin else None))
    names = {os.path.basename(node.path)[:-3]: node.id for node in nodes}
    edges: list[DerivedEdge] = list(
        dict.fromkeys(
            (
                source,
                relation,
                names.get(target, target),
                "" if pin is None else str(pin),
            )
            for source, relation, target, pin in edge_rows
        )
    )
    return nodes, edges


def _maxima(nodes: Sequence[_DerivedNode]) -> dict[str, int]:
    """Return the highest numeric suffix each node-ID prefix reaches."""
    maxima: dict[str, int] = {}
    for node in nodes:
        prefix, _, digits = node.id.rpartition("-")
        if not digits.isdecimal():
            continue
        maxima[prefix] = max(maxima.get(prefix, 0), int(digits))
    return maxima


def existing_allocations(root: str) -> dict[str, set[int]]:
    """Return the numeric suffixes already used per node-ID prefix under ``root``.

    A filename supplies its identity, so allocation can refuse an integer that
    would collide with an existing node even when the sidecar counter is stale.
    """
    taken: dict[str, set[int]] = {}
    for entry in store.iter_node_paths(root):
        path, status = entry.path, entry.status
        if status not in _STATUSES:
            continue
        match = _NODE_ID.match(os.path.basename(path)[:-3])
        if match is None:
            continue
        prefix, _, digits = match.group(1).rpartition("-")
        if not digits.isdecimal():
            continue
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
    for entry in store.iter_node_paths(root):
        path, status = entry.path, entry.status
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
    nodes, edges = _read_snapshot(root)
    stamp = _now()
    conn.execute("BEGIN IMMEDIATE")
    try:
        conn.execute("DELETE FROM edges")
        conn.execute("DELETE FROM nodes_fts")
        conn.execute("DELETE FROM nodes")
        conn.executemany(
            "INSERT INTO nodes VALUES(?,?,?,?,?,?,?,?,?)",
            [node.row(stamp) for node in nodes],
        )
        conn.executemany(
            "INSERT INTO nodes_fts VALUES(?,?,?)",
            [(node.id, node.summary, node.body) for node in nodes],
        )
        conn.executemany("INSERT INTO edges VALUES(?,?,?,?)", edges)
        _upsert_reservations(conn, _maxima(nodes))
        conn.execute(
            "INSERT INTO graph_meta(key,value) VALUES('nodes_root',?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (root,),
        )
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    return len(nodes), len(edges), root


def refresh(conn: sqlite3.Connection, root: str) -> tuple[int, int, str]:
    """Write only the derived rows the Markdown under ``root`` changed.

    The upkeep path behind automatic maintenance. It reads the Markdown
    snapshot, compares it with the rows already indexed, and writes only the
    changed node rows, the added or removed edge rows, and the deletions. An
    unchanged vault writes nothing and opens no write transaction, so an
    interaction that changed no Markdown pays the snapshot read and no indexing
    cost. Markdown is the only input, so repeated calls are idempotent and a
    lost, partial, or foreign index is rebuilt from the same snapshot the whole
    :func:`reindex` rebuilds it from.

    The comparison runs outside the write transaction, so concurrent upkeep is
    expected: every write is a conflict-tolerant upsert of the row the shared
    Markdown defines, which makes a writer that compared a stale index converge
    instead of failing on a duplicate identity.

    Returns ``(nodes_written, edges_written, root)``.
    """
    root = os.path.abspath(root)
    if not os.path.isdir(root):
        raise SidecarError(f"nodes directory does not exist: {root}")
    ensure_index_schema(conn)
    nodes, edges = _read_snapshot(root)
    desired = {node.id: node for node in nodes}
    stored = {
        str(node_id): (str(path), str(content_hash_value))
        for node_id, path, content_hash_value in conn.execute(
            "SELECT id, path, content_hash FROM nodes"
        ).fetchall()
    }
    changed = {
        node_id: node
        for node_id, node in desired.items()
        if stored.get(node_id) != (node.path, node.content_hash)
    }
    removed = sorted(set(stored) - set(desired))
    stored_edges: set[DerivedEdge] = {
        (str(source), str(relation), str(target), "" if pin is None else str(pin))
        for source, relation, target, pin in conn.execute(
            "SELECT source_id, relation, target_id, pinned_context_rev FROM edges"
        ).fetchall()
    }
    desired_edges = set(edges)
    if not changed and not removed and stored_edges == desired_edges:
        return 0, 0, root
    edge_deletions = sorted(stored_edges - desired_edges)
    edge_insertions = sorted(desired_edges - stored_edges)
    stamp = _now()
    conn.execute("BEGIN IMMEDIATE")
    try:
        if removed:
            placeholders = ",".join("?" for _ in removed)
            conn.execute(f"DELETE FROM nodes_fts WHERE id IN ({placeholders})", removed)
            conn.execute(f"DELETE FROM nodes WHERE id IN ({placeholders})", removed)
        for node in changed.values():
            conn.execute(
                "INSERT INTO nodes VALUES(?,?,?,?,?,?,?,?,?) "
                "ON CONFLICT(id) DO UPDATE SET path=excluded.path,"
                "type=excluded.type,status=excluded.status,"
                "summary=excluded.summary,context_rev=excluded.context_rev,"
                "content_hash=excluded.content_hash,indexed_at=excluded.indexed_at,"
                "body=excluded.body",
                node.row(stamp),
            )
            conn.execute("DELETE FROM nodes_fts WHERE id=?", (node.id,))
            conn.execute(
                "INSERT INTO nodes_fts VALUES(?,?,?)",
                (node.id, node.summary, node.body),
            )
        for source, relation, target, _pin in edge_deletions:
            conn.execute(
                "DELETE FROM edges WHERE source_id=? AND relation=? AND target_id=?",
                (source, relation, target),
            )
        for source, relation, target, pin in edge_insertions:
            conn.execute(
                "INSERT INTO edges VALUES(?,?,?,?) "
                "ON CONFLICT(source_id, relation, target_id) DO UPDATE SET "
                "pinned_context_rev=excluded.pinned_context_rev",
                (source, relation, target, None if pin == "" else int(pin)),
            )
        _upsert_reservations(conn, _maxima(nodes))
        conn.execute(
            "INSERT INTO graph_meta(key,value) VALUES('nodes_root',?) "
            "ON CONFLICT(key) DO UPDATE SET value=excluded.value",
            (root,),
        )
        conn.execute("COMMIT")
    except BaseException:
        conn.execute("ROLLBACK")
        raise
    return len(changed), len(edge_insertions), root


def search(
    conn: sqlite3.Connection,
    query: str,
    limit: int,
    match: Callable[[str], bool] | None = None,
) -> list[tuple[str, str, str]]:
    """Return ``id``, ``status``, and ``summary`` for the best FTS matches.

    ``match`` optionally restricts the ranked matches to the node IDs a
    Markdown-derived structured filter allows. It is applied before ``limit``,
    so a filtered search still fills its limit from the best matches rather
    than dropping rows after a truncated fetch.
    """
    statement = (
        "SELECT COALESCE(n.id,''),COALESCE(n.status,''),COALESCE(n.summary,'') "
        "FROM nodes_fts JOIN nodes n ON n.id=nodes_fts.id "
        "WHERE nodes_fts MATCH ? ORDER BY bm25(nodes_fts)"
    )
    params: list[object] = [query]
    if match is None:
        statement += " LIMIT ?"
        params.append(limit)
    try:
        rows = [
            (str(row[0]), str(row[1]), str(row[2]))
            for row in conn.execute(statement, params).fetchall()
        ]
    except sqlite3.OperationalError as exc:
        raise SidecarError(
            "invalid full-text query; use words, quoted phrases, or AND/OR"
        ) from exc
    if match is not None:
        rows = [row for row in rows if match(row[0])]
    return rows[:limit]


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
class RankedCandidate:
    """One frontier candidate with its rank and the signals that set it."""

    rank: int
    id: str
    status: str
    priority: str
    blocking: int
    updated: str
    summary: str
    next: str
    stale: bool


@dataclass(frozen=True)
class NextRanking:
    """The ranked frontier shortlist ``braintree next`` prints."""

    total: int
    candidates: tuple[RankedCandidate, ...]


@dataclass(frozen=True)
class GroupedCandidate:
    """One ranked candidate placed in its advisory workstream group."""

    group: str
    candidate: RankedCandidate


@dataclass(frozen=True)
class FrontierGroups:
    """The advisory workstream grouping ``braintree frontier --group`` prints."""

    total: int
    rows: tuple[GroupedCandidate, ...]


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


@dataclass(frozen=True)
class Reconnaissance:
    """One directly referenced reconnaissance node in a reference view.

    ``missing`` marks a reference whose target is absent from the vault, so the
    bounded read surface reports it instead of dropping it; the structural
    failure is ``braintree check``'s ``node-broken-link`` finding.
    """

    id: str
    name: str
    status: str
    context_rev: int
    summary: str
    missing: bool


@dataclass(frozen=True)
class ReferenceView:
    """The one-hop reconnaissance view ``braintree node references`` prints."""

    node: IndexedNode
    route_relation: str
    route: str
    references: tuple[Reconnaissance, ...]


@dataclass(frozen=True)
class ImpactEdge:
    """One dependent edge reached from the impact target with its shared verdict."""

    dependent: str
    status: str
    depth: int
    relation: str
    dependency: str
    pinned: str
    current: str
    stale: str


@dataclass(frozen=True)
class Impact:
    """The transitive dependent view ``braintree impact`` prints for one node."""

    target: str
    target_context_rev: int
    edges: tuple[ImpactEdge, ...]


@dataclass(frozen=True)
class OrientSection:
    """One bounded orientation section: its columns, total count, and rows."""

    name: str
    header: str
    empty: str
    total: int
    rows: tuple[tuple[str, ...], ...]


@dataclass(frozen=True)
class Orientation:
    """The bounded orientation packet ``braintree orient`` prints."""

    sections: tuple[OrientSection, ...]


@dataclass(frozen=True)
class SearchFilters:
    """The structured node filters ``braintree search`` narrows a query with.

    An empty field is unset, so the fields combine with AND. ``status``,
    ``type``, and ``priority`` match the node's own metadata; ``parent`` matches
    the primary ``Parent``/``Area`` route and ``dependency`` matches any
    canonical context edge.
    """

    status: str = ""
    type: str = ""
    priority: str = ""
    parent: str = ""
    dependency: str = ""

    def any(self) -> bool:
        """Return whether at least one filter field is set."""
        return any((self.status, self.type, self.priority, self.parent, self.dependency))


@dataclass(frozen=True)
class SimilarCandidate:
    """One ranked existing node from the ``braintree similar`` lexical baseline."""

    id: str
    status: str
    score: float
    summary: str


@dataclass(frozen=True)
class ClusterSource:
    """One node's embedding input for the advisory clustering answer.

    ``content_hash`` is the sidecar's raw-content digest of the embedded text,
    so the vector cache and the clustering keys agree; ``text`` is the
    summary-plus-body text the provider embeds; ``route`` is the node's resolved
    primary ``Parent``/``Area`` reference, which becomes its cluster route hint.
    """

    id: str
    content_hash: str
    text: str
    route: str


@dataclass(frozen=True)
class DigestMember:
    """One unresolved direct member in a ``braintree digest`` answer."""

    id: str
    status: str
    priority: str
    updated: str
    summary: str
    next: str


@dataclass(frozen=True)
class Digest:
    """The bounded unresolved-member digest ``braintree digest`` prints.

    ``total`` is the unbounded member count while ``members`` is truncated to
    the caller's limit, so one call answers what remains under a hub or
    coordinating node without dumping the subtree. It carries only the node's
    own summary and ``next``; no generative summary is involved.
    """

    target: str
    status: str
    total: int
    members: tuple[DigestMember, ...]


class ReconcileError(Exception):
    """A reconcile input the planner cannot read, such as an unknown Git ref."""


@dataclass(frozen=True)
class ReconcileStep:
    """One ordered repair step in a ``braintree reconcile`` plan."""

    action: str
    depth: int
    node: str
    path: str
    pinned: str
    current: str
    detail: str


@dataclass(frozen=True)
class ReconcilePlan:
    """The dependency-ordered repair plan ``braintree reconcile`` prints."""

    base: str
    heads: tuple[str, ...]
    steps: tuple[ReconcileStep, ...]


# An unset priority ranks after every declared ``P0``-``P3``, so a pinned
# candidate is always preferred over an unpinned one at equal blocking power.
_PRIORITY_ORDER = {"P0": 0, "P1": 1, "P2": 2, "P3": 3}

# Reconcile orders its repair steps by class, then by dependency distance, so a
# colliding identity is resolved before a bumped dependency is reread and that
# dependency before the consumers that pin its old revision.
_RECONCILE_ACTION_ORDER = {
    "duplicate-identity": 0,
    "same-node-divergence": 1,
    "reread-dependency": 2,
    "reconcile-consumer": 3,
}


def _read_nodes(root: str) -> list[IndexedNode]:
    """Read every Markdown node under ``root`` from its status directory."""
    root = os.path.abspath(root)
    nodes: list[IndexedNode] = []
    for entry in store.iter_node_paths(root):
        path, status = entry.path, entry.status
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


def _frontier_entries(nodes: list[IndexedNode]) -> list[FrontierEntry]:
    """Return the unfinished nodes whose ``next`` is an action rather than a route."""
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


def frontier(root: str) -> list[FrontierEntry]:
    """Return the unfinished nodes whose ``next`` is an action rather than a route."""
    return _frontier_entries(_read_nodes(root))


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


def reference_view(root: str, node: str) -> ReferenceView | None:
    """Return a node with the reconnaissance it directly references.

    Expansion is exactly one hop, so a reference cycle between two nodes is
    reported symmetrically and every request terminates. A reference whose
    target is absent is reported with ``missing`` set rather than dropped, so
    the output stays deterministic; ``braintree check`` is what fails such a
    vault. Repeated targets collapse to one row, and rows sort by target name so
    the answer is stable across reindexes.
    """
    nodes = _read_nodes(root)
    target = next(
        (candidate for candidate in nodes if node in {candidate.id, candidate.name}),
        None,
    )
    if target is None:
        return None
    by_name = {candidate.name: candidate for candidate in nodes}
    by_id = {candidate.id: candidate for candidate in nodes}
    route_match = _PRIMARY_ROUTE.search(target.body)
    seen: set[str] = set()
    references: list[Reconnaissance] = []
    for reference in reference_targets(target.body):
        if reference in seen:
            continue
        seen.add(reference)
        resolved = by_name.get(reference) or by_id.get(reference)
        if resolved is None:
            references.append(
                Reconnaissance(
                    id=reference,
                    name=reference,
                    status="missing",
                    context_rev=0,
                    summary="",
                    missing=True,
                )
            )
            continue
        references.append(
            Reconnaissance(
                id=resolved.id,
                name=resolved.name,
                status=resolved.status,
                context_rev=_context_rev(resolved.metadata),
                summary=resolved.metadata.get("summary", ""),
                missing=False,
            )
        )
    references.sort(key=lambda item: (item.name, item.id))
    return ReferenceView(
        node=target,
        route_relation=route_match.group(1) if route_match is not None else "",
        route=route_match.group(2) if route_match is not None else "",
        references=tuple(references),
    )


def _incoming_context(
    nodes: list[IndexedNode],
) -> tuple[dict[str, list[tuple[IndexedNode, str, int | None]]], dict[str, IndexedNode]]:
    """Return the reverse canonical context edges keyed by dependency id.

    Each ``incoming[dependency]`` entry lists the ``(source, relation, pin)``
    edges that consume that dependency, so it is the reverse of the edges
    :data:`braintree.graph_check.CONTEXT_RELATIONS` defines. The second value
    resolves a wikilink reference to its node by either name or id. ``impact``
    and the frontier ranking read the same reverse edges, so a blocking count
    cannot disagree with the impact the ``impact`` verb reports.
    """
    by_reference: dict[str, IndexedNode] = {}
    for candidate in nodes:
        by_reference[candidate.name] = candidate
        by_reference[candidate.id] = candidate
    incoming: dict[str, list[tuple[IndexedNode, str, int | None]]] = {}
    for source in nodes:
        for relation, reference, suffix in _CONTEXT_EDGE.findall(source.body):
            dependency = by_reference.get(reference)
            if dependency is None:
                continue
            pin_match = CONTEXT_PIN_LINE.fullmatch(suffix)
            pinned = int(pin_match.group(1)) if pin_match is not None else None
            incoming.setdefault(dependency.id, []).append((source, relation, pinned))
    return incoming, by_reference


def impact(root: str, node: str) -> Impact | None:
    """Return every direct and transitive dependent of ``node`` in dependency order.

    Traversal walks the reverse of the canonical context edges, so only edges
    :data:`braintree.graph_check.CONTEXT_RELATIONS` defines count. Each distinct
    dependent edge is reported once with its pinned revision and the current
    revision of the dependency it pins, using the shared ``context_pin_problem``
    verdict. A visited set stops a dependency cycle from repeating, and a cycle
    that returns to the impact target is not listed as its own dependent. Rows
    are ordered by dependency distance, then identity, so the nearest stale
    consumers come first.
    """
    nodes = _read_nodes(root)
    incoming, by_reference = _incoming_context(nodes)
    target = by_reference.get(node)
    if target is None:
        return None

    depth: dict[str, int] = {target.id: 0}
    queue: deque[str] = deque([target.id])
    edges: list[ImpactEdge] = []
    while queue:
        dependency_id = queue.popleft()
        dependency = by_reference[dependency_id]
        current = _context_rev(dependency.metadata)
        for source, relation, pinned in incoming.get(dependency_id, []):
            if source.id == target.id:
                # A cycle back to the impact target is not a dependent of itself.
                continue
            if source.id not in depth:
                depth[source.id] = depth[dependency_id] + 1
                queue.append(source.id)
            problem = context_pin_problem(pinned, dependency.status, current)
            edges.append(
                ImpactEdge(
                    dependent=source.id,
                    status=source.status,
                    depth=depth[source.id],
                    relation=relation,
                    dependency=dependency_id,
                    pinned=str(pinned) if pinned is not None else "",
                    current=str(current),
                    stale="" if problem is None else stale_reason(problem, dependency.status),
                )
            )
    edges.sort(key=lambda edge: (edge.depth, edge.dependent, edge.dependency, edge.relation))
    return Impact(
        target=target.id,
        target_context_rev=_context_rev(target.metadata),
        edges=tuple(edges),
    )


def _resolves_to(reference: str, wanted: str, by_reference: dict[str, IndexedNode]) -> bool:
    """Return whether a wikilink reference names the resolved ``wanted`` node."""
    if not reference:
        return False
    if reference == wanted:
        return True
    target = by_reference.get(reference)
    return target is not None and target.id == wanted


def _matches_filters(
    node: IndexedNode,
    filters: SearchFilters,
    by_reference: dict[str, IndexedNode],
) -> bool:
    """Return whether one node satisfies every set field of ``filters``."""
    if filters.status and node.status != filters.status:
        return False
    if filters.type and node.id.split("-", 1)[0] != filters.type:
        return False
    if filters.priority and node.metadata.get("priority", "") != filters.priority:
        return False
    if filters.parent:
        route = _PRIMARY_ROUTE.search(node.body)
        target = route.group(2) if route is not None else ""
        if not _resolves_to(target, filters.parent, by_reference):
            return False
    if filters.dependency and not any(
        _resolves_to(edge.target, filters.dependency, by_reference)
        for edge in _context_edges(node, by_reference)
    ):
        return False
    return True


def search_filter(root: str, filters: SearchFilters) -> Callable[[str], bool]:
    """Return the Markdown-derived node-ID predicate the structured filters define.

    Every field is compared against the authoritative Markdown: the status
    directory, the ID prefix, the frontmatter priority, the primary
    ``Parent``/``Area`` route, and the canonical context edges. ``search``
    applies the predicate to its ranked full-text matches, so a filter never
    depends on a derived sidecar column that the rebuild might not carry.
    """
    nodes = _read_nodes(root)
    by_reference: dict[str, IndexedNode] = {}
    for node in nodes:
        by_reference[node.name] = node
        by_reference[node.id] = node
    allowed = {node.id for node in nodes if _matches_filters(node, filters, by_reference)}
    return lambda node_id: node_id in allowed


@lru_cache(maxsize=4096)
def _token_counts(text: str) -> Counter[str]:
    """Return the lowercased alphanumeric token counts of ``text``.

    Ranking scans the same node text once per query, so the pure tokenization
    is cached and callers must treat the returned counter as read-only.
    """
    return Counter(_ALNUM.findall(text.lower()))


def _cosine(query: Counter[str], node: Counter[str]) -> float:
    """Return the cosine similarity of two token-count vectors."""
    if not query or not node:
        return 0.0
    dot = sum(count * node.get(token, 0) for token, count in query.items())
    if dot == 0:
        return 0.0
    query_norm = math.sqrt(sum(count * count for count in query.values()))
    node_norm = math.sqrt(sum(count * count for count in node.values()))
    return dot / (query_norm * node_norm)


def _similar_text(node: IndexedNode) -> str:
    """Return the summary-plus-body text ``similar`` embeds and compares."""
    return node.metadata.get("summary", "") + "\n" + node.body


def _similar_lexical(
    nodes: list[IndexedNode], text: str, limit: int
) -> list[SimilarCandidate]:
    """Rank ``nodes`` by lexical cosine over lowercased token counts."""
    query = _token_counts(text)
    candidates: list[SimilarCandidate] = []
    for node in nodes:
        score = _cosine(query, _token_counts(_similar_text(node)))
        if score <= 0:
            continue
        candidates.append(
            SimilarCandidate(
                id=node.id,
                status=node.status,
                score=score,
                summary=node.metadata.get("summary", ""),
            )
        )
    candidates.sort(key=lambda candidate: (-candidate.score, candidate.id))
    return candidates[:limit]


def _similar_semantic(
    nodes: list[IndexedNode],
    text: str,
    limit: int,
    provider: semantic.SemanticProvider,
    connection: sqlite3.Connection,
) -> list[SimilarCandidate] | None:
    """Rerank ``nodes`` by provider embedding cosine, or ``None`` on any failure.

    Node vectors are cached by content hash, and the query is embedded in the
    same call. A provider failure, a wrong-width vector, or a missing query
    vector returns ``None`` so the caller keeps one consistent metric instead of
    mixing semantic and lexical scores.
    """
    items: list[tuple[str, str]] = []
    node_hashes: list[tuple[IndexedNode, str]] = []
    seen: set[str] = set()
    for node in nodes:
        body = _similar_text(node)
        content_digest = content_hash(body.encode("utf-8"))
        node_hashes.append((node, content_digest))
        if content_digest not in seen:
            seen.add(content_digest)
            items.append((content_digest, body))
    query_digest = content_hash(text.encode("utf-8"))
    if query_digest not in seen:
        items.append((query_digest, text))
    resolved = semantic.vectors(provider, connection, items)
    if resolved is None or query_digest not in resolved:
        return None
    query_vector = resolved[query_digest]
    candidates: list[SimilarCandidate] = []
    for node, content_digest in node_hashes:
        vector = resolved.get(content_digest)
        if vector is None:
            return None
        score = semantic.cosine(query_vector, vector)
        if score <= 0:
            continue
        candidates.append(
            SimilarCandidate(
                id=node.id,
                status=node.status,
                score=score,
                summary=node.metadata.get("summary", ""),
            )
        )
    candidates.sort(key=lambda candidate: (-candidate.score, candidate.id))
    return candidates[:limit]


def similar(
    root: str,
    text: str,
    limit: int,
    provider: semantic.SemanticProvider | None = None,
    connection: sqlite3.Connection | None = None,
) -> list[SimilarCandidate]:
    """Rank existing nodes by similarity to ``text`` for admission.

    Without a provider this is the stable lexical baseline: cosine similarity
    over the lowercased alphanumeric token counts of ``text`` and each node's
    ``summary`` plus body. It is deterministic and model-free, the correctness
    reference an admission decision compares a draft against.

    With a probed ``provider`` and a sidecar ``connection`` it reranks by the
    provider's embedding cosine instead, caching node vectors by content hash in
    the disposable sidecar. Nothing semantic is required: when no provider is
    configured, or the provider fails, the answer is the lexical baseline byte
    for byte. Only positive scores are returned, ties break by node ID, and the
    result is bounded by ``limit``.
    """
    nodes = _read_nodes(root)
    if provider is not None and connection is not None:
        reranked = _similar_semantic(nodes, text, limit, provider, connection)
        if reranked is not None:
            return reranked
    return _similar_lexical(nodes, text, limit)


def cluster_source(root: str, limit: int) -> list[ClusterSource]:
    """Return the bounded per-node embedding inputs for the clustering answer.

    The result is ordered by content hash and truncated to ``limit``, matching
    the clustering layer's own bound, so both agree on which nodes survive the
    sample cap. ``route`` is the node's resolved primary ``Parent``/``Area``
    reference, so the derived layer can label a cluster without reading
    Markdown itself. This is Markdown plus the raw-content digest only: it
    imports no heavy module and needs no embedding capability.
    """
    if limit < 1:
        raise SidecarError("cluster source limit must be positive")
    nodes = _read_nodes(root)
    by_reference: dict[str, IndexedNode] = {}
    for candidate in nodes:
        by_reference[candidate.name] = candidate
        by_reference[candidate.id] = candidate
    sources = [
        ClusterSource(
            id=node.id,
            content_hash=content_hash(_similar_text(node).encode("utf-8")),
            text=_similar_text(node),
            route=_primary_route_id(node, by_reference),
        )
        for node in nodes
    ]
    sources.sort(key=lambda source: source.content_hash)
    return sources[:limit]


def digest(root: str, node: str, limit: int) -> Digest | None:
    """Return the bounded unresolved direct members of a hub or coordinating node.

    A member is an unfinished node whose primary ``Parent``/``Area`` reference
    resolves to ``node``; resolved members are omitted because the digest answers
    what still remains under the target. ``total`` is the unbounded member count
    while ``members`` is truncated to ``limit`` and ordered by priority then id.
    Pure Markdown with no embedding and no heavy module, so it stays on the fast
    path, and it reproduces only each member's own summary and ``next`` rather
    than generating text. Returns ``None`` when the target does not resolve.
    """
    if limit < 1:
        raise SidecarError("digest limit must be positive")
    nodes = _read_nodes(root)
    by_reference: dict[str, IndexedNode] = {}
    for candidate in nodes:
        by_reference[candidate.name] = candidate
        by_reference[candidate.id] = candidate
    target = by_reference.get(node)
    if target is None:
        return None
    members = [
        DigestMember(
            id=candidate.id,
            status=candidate.status,
            priority=candidate.metadata.get("priority", ""),
            updated=candidate.metadata.get("updated", ""),
            summary=candidate.metadata.get("summary", ""),
            next=candidate.metadata.get("next", ""),
        )
        for candidate in nodes
        if candidate.id != target.id
        and candidate.status != "resolved"
        and _primary_route_id(candidate, by_reference) == target.id
    ]
    members.sort(
        key=lambda member: (
            _PRIORITY_ORDER.get(member.priority, len(_PRIORITY_ORDER)),
            member.id,
        )
    )
    return Digest(
        target=target.id,
        status=target.status,
        total=len(members),
        members=tuple(members[:limit]),
    )


def stale_pins(root: str) -> list[tuple[str, str, str, str, str, str, str]]:
    """Return the stale context edges in the shape the sidecar ``stale`` query uses.

    Derived from Markdown alone through the shared per-edge verdict, so
    ``orient`` and ``stale`` cannot disagree about a pin: a row is emitted only
    where :func:`_context_edges` already found a missing, unresolved, or
    mismatched pin.
    """
    nodes = _read_nodes(root)
    by_name = {node.name: node for node in nodes}
    rows: list[tuple[str, str, str, str, str, str, str]] = []
    for node in nodes:
        for edge in _context_edges(node, by_name):
            if edge.stale == "":
                continue
            target = by_name.get(edge.target)
            rows.append(
                (
                    node.id,
                    node.status,
                    target.id if target is not None else edge.target,
                    edge.pinned,
                    edge.current,
                    edge.relation,
                    edge.stale,
                )
            )
    rows.sort()
    return rows


def _focus_targets(root: str) -> list[str]:
    """Return the ``# Focus`` pointers in ``index-map.md`` in order, deduplicated."""
    path = os.path.join(os.path.abspath(root), "index-map.md")
    if not os.path.isfile(path):
        return []
    with open(path, encoding="utf-8") as handle:
        index_text = handle.read()
    block = _FOCUS_BLOCK.search(index_text)
    if block is None:
        return []
    return list(dict.fromkeys(_WIKILINK.findall(block.group(1))))


def _focus_section(
    root: str, nodes: list[IndexedNode]
) -> tuple[str, str, list[tuple[str, ...]]]:
    """Frame the advisory ``# Focus`` pointers with the status the target has."""
    by_reference: dict[str, IndexedNode] = {}
    for node in nodes:
        by_reference[node.name] = node
        by_reference[node.id] = node
    rows: list[tuple[str, ...]] = []
    for target in _focus_targets(root):
        target_node = by_reference.get(target)
        status = target_node.status if target_node is not None else ""
        rows.append(
            (
                target,
                status,
                "true" if target_node is not None and status == "active" else "false",
            )
        )
    return ("target,status,active", "focus: 0 focus pointers", rows)


def _frontier_section(root: str) -> tuple[str, str, list[tuple[str, ...]]]:
    rows: list[tuple[str, ...]] = [
        (
            entry.id,
            entry.status,
            entry.priority,
            entry.summary,
            entry.next,
            "true" if entry.stale else "false",
        )
        for entry in frontier(root)
    ]
    return ("id,status,priority,summary,next,stale", "frontier: 0 frontier nodes", rows)


def _blockers_section(nodes: list[IndexedNode]) -> tuple[str, str, list[tuple[str, ...]]]:
    rows: list[tuple[str, ...]] = [
        (
            node.id,
            node.metadata.get("priority", ""),
            node.metadata.get("summary", ""),
            node.metadata.get("next", ""),
        )
        for node in nodes
        if node.status == "blocked"
    ]
    rows.sort(key=lambda row: row[0])
    return ("id,priority,summary,next", "blockers: 0 blocked nodes", rows)


def _stale_section(root: str) -> tuple[str, str, list[tuple[str, ...]]]:
    rows: list[tuple[str, ...]] = [tuple(row) for row in stale_pins(root)]
    return (
        "source,status,target,pinned,current,relation,reason",
        "stale: 0 stale dependency pins",
        rows,
    )


def _recent_section(nodes: list[IndexedNode]) -> tuple[str, str, list[tuple[str, ...]]]:
    ordered = sorted(nodes, key=lambda node: node.id)
    ordered.sort(key=lambda node: node.metadata.get("updated", ""), reverse=True)
    rows: list[tuple[str, ...]] = [
        (
            node.id,
            node.status,
            node.metadata.get("updated", ""),
            node.metadata.get("summary", ""),
        )
        for node in ordered
    ]
    return ("id,status,updated,summary", "recent: 0 nodes", rows)


def _conflicts_section(root: str) -> tuple[str, str, list[tuple[str, ...]]]:
    rows: list[tuple[str, ...]] = [
        (finding.code, finding.node, finding.detail) for finding in findings(root)
    ]
    return ("code,node,detail", "conflicts: 0 findings", rows)


def orient(
    root: str, sections: Sequence[str] | None = None, limit: int = 10
) -> Orientation:
    """Compose the bounded orientation packet from Markdown-derived answers.

    ``sections`` selects and filters the packet; ``None`` selects every
    :data:`ORIENT_SECTIONS` entry. Each section is truncated to ``limit`` rows
    while its ``total`` keeps the unbounded count, so one call answers the
    cold-start questions without dumping the corpus. Sections come back in the
    canonical order regardless of the selection order.
    """
    nodes = _read_nodes(root)
    builders: dict[str, Callable[[], tuple[str, str, list[tuple[str, ...]]]]] = {
        "focus": lambda: _focus_section(root, nodes),
        "frontier": lambda: _frontier_section(root),
        "blockers": lambda: _blockers_section(nodes),
        "stale": lambda: _stale_section(root),
        "recent": lambda: _recent_section(nodes),
        "conflicts": lambda: _conflicts_section(root),
    }
    selected = set(ORIENT_SECTIONS if sections is None else sections)
    packet: list[OrientSection] = []
    for name in ORIENT_SECTIONS:
        if name not in selected:
            continue
        header, empty, rows = builders[name]()
        packet.append(
            OrientSection(
                name=name,
                header=header,
                empty=empty,
                total=len(rows),
                rows=tuple(rows[:limit]),
            )
        )
    return Orientation(tuple(packet))


def _blocking_power(
    candidate_id: str,
    incoming: dict[str, list[tuple[IndexedNode, str, int | None]]],
    status_by_id: dict[str, str],
) -> int:
    """Count the distinct unfinished nodes that transitively depend on a candidate.

    The walk follows the reverse canonical context edges, so only the relations
    ``CONTEXT_RELATIONS`` defines count. A resolved dependent is no longer
    blocked, so it does not add to the power; a cycle is visited once and the
    candidate itself is never counted.
    """
    seen: set[str] = set()
    queue: deque[str] = deque(
        source.id for source, _relation, _pin in incoming.get(candidate_id, [])
    )
    while queue:
        node_id = queue.popleft()
        if node_id == candidate_id or node_id in seen:
            continue
        seen.add(node_id)
        queue.extend(source.id for source, _relation, _pin in incoming.get(node_id, []))
    return sum(1 for node_id in seen if status_by_id.get(node_id) != "resolved")


def _rank_candidates(
    nodes: list[IndexedNode],
    incoming: dict[str, list[tuple[IndexedNode, str, int | None]]],
) -> list[RankedCandidate]:
    """Order the frontier candidates by priority, blocking power, then recency.

    The total order is, most significant first: ``priority`` from ``P0`` to
    ``P3`` with an unset priority last; the transitive blocking count from
    :func:`_blocking_power` descending; ``updated`` descending; and finally the
    node id ascending. The stable passes below apply the least significant key
    first, so the result is deterministic and needs no model.
    """
    updated_of = {node.id: node.metadata.get("updated", "") for node in nodes}
    status_by_id = {node.id: node.status for node in nodes}
    scored = [
        (entry, _blocking_power(entry.id, incoming, status_by_id))
        for entry in _frontier_entries(nodes)
    ]
    scored.sort(key=lambda pair: pair[0].id)
    scored.sort(key=lambda pair: updated_of[pair[0].id], reverse=True)
    scored.sort(key=lambda pair: pair[1], reverse=True)
    scored.sort(key=lambda pair: _PRIORITY_ORDER.get(pair[0].priority, len(_PRIORITY_ORDER)))
    return [
        RankedCandidate(
            rank=rank,
            id=entry.id,
            status=entry.status,
            priority=entry.priority,
            blocking=blocking,
            updated=updated_of[entry.id],
            summary=entry.summary,
            next=entry.next,
            stale=entry.stale,
        )
        for rank, (entry, blocking) in enumerate(scored, start=1)
    ]


def next_ranked(root: str, limit: int) -> NextRanking:
    """Return the frontier candidates ranked for the next actor, bounded by ``limit``.

    ``total`` is the unbounded candidate count while ``candidates`` holds the
    top ``limit`` ranked rows, so one call answers "what should I take next"
    without dumping the corpus.
    """
    nodes = _read_nodes(root)
    incoming, _by_reference = _incoming_context(nodes)
    ranked = _rank_candidates(nodes, incoming)
    return NextRanking(total=len(ranked), candidates=tuple(ranked[:limit]))


def _primary_route_id(node: IndexedNode, by_reference: dict[str, IndexedNode]) -> str:
    """Resolve a node's primary ``Parent``/``Area`` reference to a stable id."""
    match = _PRIMARY_ROUTE.search(node.body)
    if match is None:
        return ""
    target = by_reference.get(match.group(2))
    return target.id if target is not None else match.group(2)


def frontier_groups(root: str, limit: int) -> FrontierGroups:
    """Cluster the ranked frontier candidates into bounded advisory workstreams.

    Two frontier candidates join one group when they share a resolved primary
    ``Parent``/``Area`` route or when one depends on the other through a
    canonical context edge; the connections merge transitively. Each group is
    labelled by its shared route, or by its top-ranked member when the routes
    differ, and a group's members stay in ranked order. ``total`` is the
    unbounded group count while ``rows`` is truncated to ``limit``. The
    grouping is advisory: it never states a claim or assignment.
    """
    nodes = _read_nodes(root)
    incoming, by_reference = _incoming_context(nodes)
    ranked = _rank_candidates(nodes, incoming)
    by_id = {candidate.id: candidate for candidate in ranked}
    node_by_id = {node.id: node for node in nodes}

    parent = {candidate.id: candidate.id for candidate in ranked}

    def find(node_id: str) -> str:
        while parent[node_id] != node_id:
            parent[node_id] = parent[parent[node_id]]
            node_id = parent[node_id]
        return node_id

    def union(left: str, right: str) -> None:
        left_root, right_root = find(left), find(right)
        if left_root != right_root:
            parent[max(left_root, right_root)] = min(left_root, right_root)

    routes: dict[str, list[str]] = {}
    for candidate in ranked:
        route = _primary_route_id(node_by_id[candidate.id], by_reference)
        if route:
            routes.setdefault(route, []).append(candidate.id)
    for members in routes.values():
        for other in members[1:]:
            union(members[0], other)

    for candidate in ranked:
        body = node_by_id[candidate.id].body
        for _relation, reference, _suffix in _CONTEXT_EDGE.findall(body):
            target = by_reference.get(reference)
            if target is not None and target.id in by_id and target.id != candidate.id:
                union(candidate.id, target.id)

    components: dict[str, list[str]] = {}
    for candidate in ranked:
        components.setdefault(find(candidate.id), []).append(candidate.id)

    groups: list[tuple[str, list[str]]] = []
    for members in components.values():
        route_ids = {_primary_route_id(node_by_id[member], by_reference) for member in members}
        route_ids.discard("")
        label = next(iter(route_ids)) if len(route_ids) == 1 else members[0]
        groups.append((label, members))
    rank_of = {candidate.id: candidate.rank for candidate in ranked}
    groups.sort(key=lambda group: (rank_of[group[1][0]], group[0]))

    rows: list[GroupedCandidate] = []
    for label, members in groups:
        for member in members:
            rows.append(GroupedCandidate(group=label, candidate=by_id[member]))
    return FrontierGroups(total=len(groups), rows=tuple(rows[:limit]))


def _git_stdout(repo: str, *args: str) -> str | None:
    """Run a read-only Git command and return its stdout, or ``None`` on failure."""
    try:
        result = subprocess.run(
            ["git", "-C", repo, *args],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:  # pragma: no cover - only when the git binary is absent
        raise ReconcileError(f"git is unavailable: {exc}") from exc
    if result.returncode != 0:
        return None
    return result.stdout


@dataclass(frozen=True)
class _RefNode:
    """One Markdown node as it exists in a Git snapshot."""

    id: str
    name: str
    path: str
    status: str
    context_rev: int
    body: str
    text: str


def _ref_nodes(repo: str, ref: str, prefix: str) -> dict[str, _RefNode]:
    """Read every status-directory node under ``prefix`` as it exists at ``ref``."""
    listing = _git_stdout(repo, "ls-tree", "-r", "--name-only", ref, "--", prefix)
    if listing is None:
        raise ReconcileError(f"unknown Git ref: {ref}")
    nodes: dict[str, _RefNode] = {}
    for path in listing.splitlines():
        status = os.path.basename(os.path.dirname(path))
        basename = os.path.basename(path)
        if status not in _STATUSES or not basename.endswith(".md"):
            continue
        name = basename[:-3]
        match = _NODE_ID.match(name)
        if match is None:
            continue
        text = _git_stdout(repo, "show", f"{ref}:{path}")
        if text is None:
            continue
        header, body = _frontmatter(text)
        nodes[path] = _RefNode(
            id=match.group(1),
            name=name,
            path=path,
            status=status,
            context_rev=_context_rev(header),
            body=body,
            text=text,
        )
    return nodes


def _nodes_by_id(nodes: dict[str, _RefNode]) -> dict[str, _RefNode]:
    """Collapse a snapshot to one node per identity, keeping the first path."""
    by_id: dict[str, _RefNode] = {}
    for node in nodes.values():
        by_id.setdefault(node.id, node)
    return by_id


def reconcile(
    base: str,
    heads: Sequence[str],
    nodes_root: str,
    repo: str | None = None,
) -> ReconcilePlan:
    """Return the dependency-ordered repair plan for integrating ``heads`` into ``base``.

    The planner is a read-only report over two authorities: the Git snapshots
    name which node identities a change set touches, and the Markdown in those
    snapshots supplies the canonical context edges. It classifies the three
    integration hazards the parallel-worktree contract assigns to coordinator
    judgment. An identity created at two different paths across the heads is a
    duplicate identity. The same node changed by two heads is a same-node
    divergence, because a rename and an edit of one basename must be reconciled
    rather than merged blind. A node whose ``context_rev`` changed in a head
    makes any base node that pins the old revision a stale consumer.

    Steps are ordered duplicate identities, then divergences, then the bumped
    dependency, then its consumers, so a pinned dependency is reconciled after
    its target; identity and path break ties within a class. The vault is never
    mutated. Aborting on an unreadable ref keeps the plan trustworthy rather
    than silently dropping a snapshot.
    """
    working = os.getcwd() if repo is None else repo
    top = _git_stdout(working, "rev-parse", "--show-toplevel")
    if top is None:
        raise ReconcileError("not inside a Git work tree")
    prefix = os.path.relpath(os.path.abspath(nodes_root), top.strip())
    if prefix.startswith(".."):
        raise ReconcileError("nodes directory is outside the Git work tree")

    order: list[str] = []
    for head in heads:
        if head not in order:
            order.append(head)
    base_nodes = _ref_nodes(working, base, prefix)
    head_nodes = {head: _ref_nodes(working, head, prefix) for head in order}
    base_by_id = _nodes_by_id(base_nodes)

    steps: list[ReconcileStep] = []
    seen: set[tuple[str, str, str]] = set()

    def add(
        action: str,
        node: str,
        path: str,
        detail: str,
        pinned: str = "",
        current: str = "",
        depth: int = 0,
    ) -> None:
        key = (action, node, path)
        if key in seen:
            return
        seen.add(key)
        steps.append(
            ReconcileStep(
                action=action,
                depth=depth,
                node=node,
                path=path,
                pinned=pinned,
                current=current,
                detail=detail,
            )
        )

    def add_duplicates(nodes: dict[str, _RefNode]) -> None:
        grouped: dict[str, list[_RefNode]] = {}
        for node in nodes.values():
            grouped.setdefault(node.id, []).append(node)
        for label, members in grouped.items():
            if len(members) > 1:
                for member in members:
                    add(
                        "duplicate-identity",
                        label,
                        member.path,
                        f"duplicate node identity: {label}",
                    )

    def changed_relative(nodes: dict[str, _RefNode]) -> dict[str, _RefNode]:
        changed: dict[str, _RefNode] = {}
        for node in nodes.values():
            prior = base_by_id.get(node.id)
            if prior is None or (
                prior.name != node.name
                or prior.path != node.path
                or prior.text != node.text
            ):
                changed[node.id] = node
        return changed

    add_duplicates(base_nodes)
    for head in order:
        add_duplicates(head_nodes[head])

    changed = {head: changed_relative(head_nodes[head]) for head in order}
    touched: dict[str, list[tuple[str, _RefNode]]] = {}
    for head in order:
        for node_id, node in changed[head].items():
            touched.setdefault(node_id, []).append((head, node))

    bumped: dict[str, _RefNode] = {}
    for node_id, members in touched.items():
        names = {node.name for _head, node in members}
        if len(members) > 1 and len(names) > 1:
            for _head, node in members:
                add(
                    "duplicate-identity",
                    node_id,
                    node.path,
                    f"duplicate node identity: {node_id}",
                )
            continue
        if len(members) > 1:
            prior = base_by_id.get(node_id)
            add(
                "same-node-divergence",
                members[0][1].name,
                prior.path if prior is not None else members[0][1].path,
                "diverged on " + ", ".join(head for head, _node in members),
            )
        prior = base_by_id.get(node_id)
        head_node = members[-1][1]
        if prior is not None and prior.context_rev != head_node.context_rev:
            bumped[node_id] = head_node

    base_by_reference: dict[str, _RefNode] = {}
    for node in base_nodes.values():
        base_by_reference[node.name] = node
        base_by_reference[node.id] = node

    for node_id in sorted(bumped):
        target = bumped[node_id]
        base_rev = base_by_id[node_id].context_rev
        add(
            "reread-dependency",
            node_id,
            target.path,
            f"context_rev changed {base_rev} -> {target.context_rev}",
            pinned=str(base_rev),
            current=str(target.context_rev),
        )
        for source in sorted(base_nodes.values(), key=lambda node: (node.id, node.path)):
            for _relation, reference, suffix in _CONTEXT_EDGE.findall(source.body):
                dependency = base_by_reference.get(reference)
                if dependency is None or dependency.id != node_id:
                    continue
                pin_match = CONTEXT_PIN_LINE.fullmatch(suffix)
                pinned = int(pin_match.group(1)) if pin_match is not None else None
                problem = context_pin_problem(pinned, target.status, target.context_rev)
                if problem is None:
                    continue
                add(
                    "reconcile-consumer",
                    source.id,
                    source.path,
                    stale_reason(problem, target.status),
                    pinned=str(pinned) if pinned is not None else "",
                    current=str(target.context_rev),
                    depth=1,
                )

    steps.sort(
        key=lambda step: (
            _RECONCILE_ACTION_ORDER[step.action],
            step.depth,
            step.node,
            step.path,
        )
    )
    return ReconcilePlan(base=base, heads=tuple(order), steps=tuple(steps))
