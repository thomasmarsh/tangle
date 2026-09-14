"""Compatibility discovery tests for stationary canonical nodes."""

from __future__ import annotations

import sqlite3
from pathlib import Path

from braintree import graph_check, index, store

_UID = "tas-0123456789abcdefghjkmnpqrs"
_HUB = "idx-1123456789abcdefghjkmnpqrs"


def _node(node_id: str, status: str, route: str, *, next_line: str = "") -> str:
    return (
        "---\n"
        "context_rev: 1\n"
        f"status: {status}\n"
        "updated: 2026-09-14T20:00:00Z\n"
        "summary: Stationary test node.\n"
        f"{next_line}"
        "---\n\n"
        f"{route}.\n"
    )


def test_stationary_nodes_are_discovered_by_check_and_index(tmp_path: Path) -> None:
    nodes = tmp_path / ".braintree"
    canonical = nodes / store.CANONICAL_DIRECTORY / _UID[-2:]
    canonical.mkdir(parents=True)
    (nodes / "index-map.md").write_text(
        f"# Routes\n\n- Indexes [[{_HUB}-root]]\n", encoding="utf-8"
    )
    (canonical / f"{_HUB}-root.md").write_text(
        _node(_HUB, "resolved", ""), encoding="utf-8"
    )
    (canonical / f"{_UID}-capture.md").write_text(
        _node(_UID, "proposed", f"Area [[{_HUB}-root]]", next_line="next: Capture it.\n"),
        encoding="utf-8",
    )

    assert graph_check.findings(str(nodes)) == []
    conn = sqlite3.connect(":memory:")
    try:
        index.ensure_index_schema(conn)
        index.reindex(conn, str(nodes))
        assert index.frontier(str(nodes))[0].id == _UID
    finally:
        conn.close()


def test_stationary_node_requires_frontmatter_status(tmp_path: Path) -> None:
    path = tmp_path / store.CANONICAL_DIRECTORY / "aa" / f"{_UID}-capture.md"
    path.parent.mkdir(parents=True)
    path.write_text("---\nsummary: Missing status.\n---\n", encoding="utf-8")

    [entry] = list(store.iter_node_paths(str(tmp_path)))
    assert entry.stationary is True
    assert entry.status is None
