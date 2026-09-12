"""Pytest port of ``tests/bt-index.sh`` for the Python ``bt`` index commands.

Builds a small Markdown vault, then checks reindex counts, full-text search,
backlink edges, stale dependency pins, recovery after database loss, and the
argument errors that gate the index commands.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path

RunBt = Callable[..., subprocess.CompletedProcess[str]]


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _seed(vault: Path) -> None:
    (vault / "resolved").mkdir(parents=True)
    (vault / "active").mkdir()
    _write(
        vault / "resolved" / "IDX-001-root.md",
        "---\ncontext_rev: 2\nupdated: 2026-09-11T00:00:00Z\n"
        "summary: Root graph entry.\n---\n\n# Invariant\n\nRoot content finds all work.\n",
    )
    _write(
        vault / "resolved" / "DEF-001-contract.md",
        "---\ncontext_rev: 3\nupdated: 2026-09-11T00:00:00Z\n"
        "summary: Searchable protocol contract.\n---\n\n# Context\n\n"
        "Area [[IDX-001-root]].\n\n# Invariant\n\nThe protocol uses a durable token.\n",
    )
    _write(
        vault / "active" / "TAS-001-consumer.md",
        "---\ncontext_rev: 1\npriority: P1\nupdated: 2026-09-11T00:00:00Z\n"
        "summary: Consume the protocol.\nnext: Reconcile the contract.\n---\n\n"
        "# Context\n\nParent [[IDX-001-root]].\n\n"
        "Depends on [[DEF-001-contract]] at context_rev 2.\n\n"
        "# Outcome\n\nUse the durable token.\n",
    )
    _write(
        vault / "active" / "TAS-002-missing.md",
        "---\ncontext_rev: 1\nupdated: 2026-09-11T00:00:00Z\n"
        "summary: Recover a missing dependency.\nnext: Locate it.\n---\n\n"
        "# Context\n\nParent [[IDX-001-root]].\n\nDepends on [[DEF-404-missing]].\n",
    )


def _env(tmp_path: Path, vault: Path) -> dict[str, str]:
    return {
        "BT_SIDECAR_DIR": str(tmp_path / "sidecar"),
        "BT_PROJECT_ID": "index-test",
        "BT_NODES_DIR": str(vault),
    }


def _database(tmp_path: Path) -> Path:
    return tmp_path / "sidecar" / "projects" / "index-test" / "graph.sqlite3"


def test_reindex_counts_and_queries(tmp_path: Path, run_bt: RunBt) -> None:
    vault = tmp_path / "vault" / "nodes"
    _seed(vault)
    env = _env(tmp_path, vault)

    output = run_bt("reindex", env=env)
    assert output.stdout.splitlines()[:2] == ["nodes: 4", "edges: 5"]

    search = run_bt("search", "durable", env=env)
    assert '"DEF-001","resolved","Searchable protocol contract."' in search.stdout

    backlinks = run_bt("backlinks", "DEF-001", env=env)
    assert '"TAS-001","active","Depends on","2"' in backlinks.stdout

    stale = run_bt("stale", env=env)
    assert '"TAS-001","active","DEF-001","2","3"' in stale.stdout
    assert '"TAS-002","active","DEF-404-missing","",""' in stale.stdout


def test_reindex_recovers_after_database_loss(tmp_path: Path, run_bt: RunBt) -> None:
    vault = tmp_path / "vault" / "nodes"
    _seed(vault)
    env = _env(tmp_path, vault)
    run_bt("reindex", env=env)
    _database(tmp_path).unlink()
    run_bt("reindex", env=env)
    assert '"DEF-001"' in run_bt("search", "protocol", env=env).stdout


def test_explicit_nodes_argument_overrides_environment(
    tmp_path: Path, run_bt: RunBt
) -> None:
    vault = tmp_path / "vault" / "nodes"
    _seed(vault)
    env = {
        "BT_SIDECAR_DIR": str(tmp_path / "sidecar"),
        "BT_PROJECT_ID": "index-arg-test",
    }
    output = run_bt("reindex", str(vault), env=env)
    assert output.stdout.splitlines()[:2] == ["nodes: 4", "edges: 5"]


def test_search_requires_query(tmp_path: Path, run_bt: RunBt) -> None:
    vault = tmp_path / "vault" / "nodes"
    _seed(vault)
    result = run_bt("search", "--limit", "1", env=_env(tmp_path, vault))
    assert result.returncode == 2
    assert 'error: "search requires QUERY"' in result.stdout
