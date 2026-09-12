"""Rebuildable Markdown-derived graph index.

Typed Python implementation of the Markdown index builder. Durable graph state stays in
Markdown; this module rebuilds the disposable ``nodes``, ``edges``, and FTS
rows plus the search, backlinks, and stale-pin queries over them, and derives
the direct ``frontier``, ``node_view``, ``impact``, and ``orient`` answers from
the same Markdown. The structured ``search`` filters and the lexical
``similar`` baseline are likewise derived from Markdown, so an admission or
filter decision never depends on a derived sidecar column.
"""

from __future__ import annotations

import glob
import math
import os
import re
import sqlite3
from collections import Counter, deque
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from datetime import UTC, datetime

from .graph_check import (
    CONTEXT_PIN_LINE,
    CONTEXT_RELATIONS,
    context_pin_problem,
    findings,
    stale_reason,
)
from .sidecar import SidecarError, content_hash

__all__ = [
    "Backlink",
    "ContextEdge",
    "FrontierEntry",
    "Impact",
    "ImpactEdge",
    "IndexedNode",
    "NodeView",
    "ORIENT_SECTIONS",
    "OrientSection",
    "Orientation",
    "SearchFilters",
    "SimilarCandidate",
    "backlinks",
    "ensure_index_schema",
    "existing_allocations",
    "format_table",
    "frontier",
    "impact",
    "node_hash",
    "node_view",
    "orient",
    "prefix_maxima",
    "reindex",
    "resolve_node",
    "search",
    "search_filter",
    "similar",
    "stale",
    "stale_pins",
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
    by_reference: dict[str, IndexedNode] = {}
    for candidate in nodes:
        by_reference[candidate.name] = candidate
        by_reference[candidate.id] = candidate
    target = by_reference.get(node)
    if target is None:
        return None

    # ``incoming[dependency]`` lists the edges whose source depends on it.
    incoming: dict[str, list[tuple[IndexedNode, str, int | None]]] = {}
    for source in nodes:
        for relation, reference, suffix in _CONTEXT_EDGE.findall(source.body):
            dependency = by_reference.get(reference)
            if dependency is None:
                continue
            pin_match = CONTEXT_PIN_LINE.fullmatch(suffix)
            pinned = int(pin_match.group(1)) if pin_match is not None else None
            incoming.setdefault(dependency.id, []).append((source, relation, pinned))

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


def _token_counts(text: str) -> Counter[str]:
    """Return the lowercased alphanumeric token counts of ``text``."""
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


def similar(root: str, text: str, limit: int) -> list[SimilarCandidate]:
    """Rank existing nodes by lexical similarity to ``text`` for admission.

    The metric is cosine similarity over the lowercased alphanumeric token
    counts of ``text`` and each node's ``summary`` plus body. It is
    deterministic and model-free: the stable lexical baseline an admission
    decision compares a draft against, which an optional semantic layer may
    later rerank without changing this path. Only positive scores are returned,
    ties break by node ID, and the result is bounded by ``limit``.
    """
    query = _token_counts(text)
    candidates: list[SimilarCandidate] = []
    for node in _read_nodes(root):
        body = node.metadata.get("summary", "") + "\n" + node.body
        score = _cosine(query, _token_counts(body))
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
