"""Rebuildable Markdown-derived graph index.

Typed Python implementation of the Markdown index builder. Durable graph state stays in
Markdown; this module rebuilds the disposable ``nodes``, ``edges``, and FTS
rows plus the search, backlinks, and stale-pin queries over them.
"""

from __future__ import annotations

import glob
import os
import re
import sqlite3
from collections.abc import Sequence
from datetime import UTC, datetime

from .sidecar import SidecarError, content_hash

__all__ = [
    "backlinks",
    "ensure_index_schema",
    "existing_allocations",
    "format_table",
    "node_hash",
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


def stale(conn: sqlite3.Connection) -> list[tuple[str, str, str, str, str]]:
    """Return dependency edges missing a target or mismatching its revision."""
    cursor = conn.execute(
        "SELECT COALESCE(e.source_id,''),COALESCE(n.status,''),COALESCE(e.target_id,''),"
        "COALESCE(e.pinned_context_rev,''),COALESCE(d.context_rev,'') "
        "FROM edges e JOIN nodes n ON n.id=e.source_id "
        "LEFT JOIN nodes d ON d.id=e.target_id "
        "WHERE e.relation='Depends on' AND "
        "(e.pinned_context_rev IS NULL OR d.id IS NULL OR d.context_rev != e.pinned_context_rev) "
        "ORDER BY e.source_id,e.target_id",
        (),
    )
    return [
        (str(row[0]), str(row[1]), str(row[2]), str(row[3]), str(row[4]))
        for row in cursor.fetchall()
    ]


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
