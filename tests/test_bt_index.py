"""Pytest port of ``tests/bt-index.sh`` for the Python ``bt`` index commands.

Builds a small Markdown vault, then checks reindex counts, full-text search,
backlink edges, stale dependency pins, recovery after database loss, and the
argument errors that gate the index commands.
"""

from __future__ import annotations

import csv
import hashlib
import re
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

from braintree.graph_check import CONTEXT_RELATIONS

RunBt = Callable[..., subprocess.CompletedProcess[str]]

_ROOT = Path(__file__).resolve().parents[1]
_FINAL_STATUSES = {"proposed", "active", "blocked"}
_NODE_ID = re.compile(r"([A-Z][A-Z0-9_]*-\d+)-")


def _markdown_frontier_ids(root: Path) -> set[str]:
    """Derive the frontier the documented recipe yields, straight from Markdown."""
    ids: set[str] = set()
    for path in sorted(root.glob("*/*.md")):
        if path.parent.name not in _FINAL_STATUSES:
            continue
        match = _NODE_ID.match(path.stem)
        if match is None:
            continue
        next_match = re.search(r"^next: (.*)$", path.read_text(encoding="utf-8"), re.MULTILINE)
        if next_match is not None and "[[" in next_match.group(1):
            continue
        ids.add(match.group(1))
    return ids


def _toon_rows(output: str, name: str) -> list[list[str]]:
    """Parse the indented TOON rows that follow a ``name[n]{...}:`` header line."""
    lines = output.splitlines()
    start = next(index for index, line in enumerate(lines) if line.startswith(f"{name}["))
    rows: list[list[str]] = []
    for line in lines[start + 1 :]:
        if not line.startswith("  "):
            break
        parsed = next(csv.reader([line.strip()], escapechar="\\"))
        rows.append([cell.strip() for cell in parsed])
    return rows


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

    output = run_bt("index", env=env)
    assert output.stdout.splitlines()[:2] == ["nodes: 4", "edges: 5"]

    search = run_bt("search", "durable", env=env)
    assert '"DEF-001","resolved","Searchable protocol contract."' in search.stdout

    backlinks = run_bt("backlinks", "DEF-001", env=env)
    assert '"TAS-001","active","Depends on","2"' in backlinks.stdout

    stale = run_bt("stale", env=env)
    assert (
        '"TAS-001","active","DEF-001","2","3","Depends on","context_rev mismatch"'
        in stale.stdout
    )
    assert (
        '"TAS-002","active","DEF-404-missing","","","Depends on",'
        '"missing context_rev pin"'
    ) in stale.stdout


def test_stale_reports_missing_pinned_target(tmp_path: Path, run_bt: RunBt) -> None:
    """A pin whose target is absent is reported with the missing-target verdict."""
    vault = tmp_path / "vault" / "nodes"
    (vault / "resolved").mkdir(parents=True)
    (vault / "active").mkdir()
    _write(
        vault / "resolved" / "IDX-001-root.md",
        "---\ncontext_rev: 1\nupdated: 2026-09-11T00:00:00Z\n"
        "summary: Root hub.\n---\n",
    )
    _write(
        vault / "active" / "TAS-001-consumer.md",
        "---\ncontext_rev: 1\nupdated: 2026-09-11T00:00:00Z\n"
        "summary: Consume a missing contract.\nnext: Locate the contract.\n---\n\n"
        "# Context\n\nRequires [[DEF-404-missing]] at context_rev 1.\n",
    )
    stale = run_bt("stale", env=_env(tmp_path, vault))
    assert stale.returncode == 0
    assert (
        '"TAS-001","active","DEF-404-missing","1","","Requires","missing target"'
        in stale.stdout
    )


def test_reindex_recovers_after_database_loss(tmp_path: Path, run_bt: RunBt) -> None:
    vault = tmp_path / "vault" / "nodes"
    _seed(vault)
    env = _env(tmp_path, vault)
    run_bt("index", env=env)
    _database(tmp_path).unlink()
    run_bt("index", env=env)
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
    output = run_bt("index", str(vault), env=env)
    assert output.stdout.splitlines()[:2] == ["nodes: 4", "edges: 5"]


def test_search_requires_query(tmp_path: Path, run_bt: RunBt) -> None:
    vault = tmp_path / "vault" / "nodes"
    _seed(vault)
    result = run_bt("search", "--limit", "1", env=_env(tmp_path, vault))
    assert result.returncode == 2
    assert 'error: "search requires QUERY"' in result.stdout


def test_backlinks_resolve_full_name_and_reject_unknown(
    tmp_path: Path, run_bt: RunBt
) -> None:
    vault = tmp_path / "vault" / "nodes"
    _seed(vault)
    env = _env(tmp_path, vault)

    bare = run_bt("backlinks", "DEF-001", env=env)
    named = run_bt("backlinks", "DEF-001-contract", env=env)
    assert bare.returncode == 0 and named.returncode == 0
    assert bare.stdout == named.stdout
    assert '"TAS-001","active","Depends on","2"' in named.stdout

    (vault / "resolved" / "DEF-002-leaf.md").write_text(
        "---\ncontext_rev: 1\nupdated: 2026-09-11T00:00:00Z\n"
        "summary: Leaf definition.\n---\n\n# Context\n\nArea [[IDX-001-root]].\n",
        encoding="utf-8",
    )
    zero = run_bt("backlinks", "DEF-002-leaf", env=env)
    assert zero.returncode == 0
    assert zero.stdout.strip() == "backlinks: 0 matching edges"

    unknown = run_bt("backlinks", "DEF-999", env=env)
    assert unknown.returncode == 1
    assert 'error: "unknown node: DEF-999"' in unknown.stdout


def test_hash_matches_raw_sha256_algorithm(tmp_path: Path, run_bt: RunBt) -> None:
    vault = tmp_path / "vault" / "nodes"
    _seed(vault)
    env = _env(tmp_path, vault)
    node_file = vault / "active" / "TAS-001-consumer.md"
    expected = hashlib.sha256(node_file.read_bytes()).hexdigest()

    bare = run_bt("hash", "TAS-001", env=env)
    assert bare.returncode == 0
    assert f'content_hash: "{expected}"' in bare.stdout

    named = run_bt("hash", "TAS-001-consumer", env=env)
    assert named.returncode == 0
    assert f'content_hash: "{expected}"' in named.stdout

    unknown = run_bt("hash", "TAS-999", env=env)
    assert unknown.returncode == 1
    assert 'error: "unknown node: TAS-999"' in unknown.stdout


def test_stale_without_stale_pins_names_them(tmp_path: Path, run_bt: RunBt) -> None:
    vault = tmp_path / "vault" / "nodes"
    (vault / "resolved").mkdir(parents=True)
    (vault / "active").mkdir()
    (vault / "resolved" / "DEF-001-contract.md").write_text(
        "---\ncontext_rev: 1\nupdated: 2026-09-11T00:00:00Z\n"
        "summary: Current contract.\n---\n\n# Invariant\n\nCurrent.\n",
        encoding="utf-8",
    )
    (vault / "active" / "TAS-001-consumer.md").write_text(
        "---\ncontext_rev: 1\npriority: P1\nupdated: 2026-09-11T00:00:00Z\n"
        "summary: Consume the protocol.\nnext: Reconcile the contract.\n---\n\n"
        "# Context\n\nDepends on [[DEF-001-contract]] at context_rev 1.\n",
        encoding="utf-8",
    )
    result = run_bt("stale", env=_env(tmp_path, vault))
    assert result.returncode == 0
    assert result.stdout.strip() == "stale: 0 stale dependency pins"


@pytest.mark.parametrize("relation", CONTEXT_RELATIONS)
def test_stale_reports_each_context_relation(
    tmp_path: Path, run_bt: RunBt, relation: str
) -> None:
    """A pin on every canonical context relation is reconciled, not just `Depends on`."""
    vault = tmp_path / "vault" / "nodes"
    (vault / "resolved").mkdir(parents=True)
    (vault / "active").mkdir()
    _write(
        vault / "resolved" / "DEF-001-contract.md",
        "---\ncontext_rev: 3\nupdated: 2026-09-11T00:00:00Z\n"
        "summary: Current contract.\n---\n\n# Invariant\n\nCurrent.\n",
    )
    _write(
        vault / "active" / "TAS-001-consumer.md",
        "---\ncontext_rev: 1\nupdated: 2026-09-11T00:00:00Z\n"
        "summary: Consume the contract.\nnext: Reconcile the contract.\n---\n\n"
        f"# Context\n\n{relation} [[DEF-001-contract]] at context_rev 2.\n",
    )
    result = run_bt("stale", env=_env(tmp_path, vault))
    assert result.returncode == 0
    assert (
        '"TAS-001","active","DEF-001","2","3",'
        f'"{relation}","context_rev mismatch"'
    ) in result.stdout


def test_stale_and_check_agree_on_unresolved_pin(
    tmp_path: Path, run_bt: RunBt
) -> None:
    """`stale` reports a pin whose target is not resolved, as `check` does."""
    vault = tmp_path / "vault" / "nodes"
    (vault / "resolved").mkdir(parents=True)
    (vault / "active").mkdir()
    (vault / "proposed").mkdir()
    _write(
        vault / "index-map.md",
        "---\nupdated: 2026-09-11T00:00:00Z\nsummary: Route work.\n---\n\n"
        "# Root hubs\n\n- Indexes [[IDX-001-root]].\n",
    )
    _write(
        vault / "resolved" / "IDX-001-root.md",
        "---\ncontext_rev: 1\nupdated: 2026-09-11T00:00:00Z\n"
        "summary: Root hub.\n---\n",
    )
    _write(
        vault / "proposed" / "DEF-001-contract.md",
        "---\ncontext_rev: 2\nupdated: 2026-09-11T00:00:00Z\n"
        "summary: Proposed contract.\n---\n\nArea [[IDX-001-root]].\n",
    )
    _write(
        vault / "active" / "TAS-001-consumer.md",
        "---\ncontext_rev: 1\nupdated: 2026-09-11T00:00:00Z\n"
        "summary: Consume the contract.\nnext: Reconcile the contract.\n---\n\n"
        "# Context\n\nParent [[IDX-001-root]].\n\n"
        "Implements [[DEF-001-contract]] at context_rev 2.\n",
    )

    checked = run_bt("check", str(vault))
    assert checked.returncode == 1
    assert (
        "pinned dependency [[DEF-001-contract]] is proposed, not resolved"
        in checked.stderr
    )

    stale = run_bt("stale", env=_env(tmp_path, vault))
    assert stale.returncode == 0
    assert (
        '"TAS-001","active","DEF-001","2","2","Implements",'
        '"target is proposed, not resolved"'
    ) in stale.stdout


def _seed_views(vault: Path) -> None:
    (vault / "resolved").mkdir(parents=True)
    (vault / "active").mkdir()
    (vault / "proposed").mkdir()
    _write(
        vault / "resolved" / "IDX-001-root.md",
        "---\ncontext_rev: 1\nupdated: 2026-09-11T00:00:00Z\n"
        "summary: Root hub.\n---\n",
    )
    _write(
        vault / "resolved" / "DEF-001-contract.md",
        "---\ncontext_rev: 2\nupdated: 2026-09-11T00:00:00Z\n"
        "summary: Current contract.\n---\n\n# Invariant\n\nCurrent.\n",
    )
    _write(
        vault / "active" / "TAS-001-consumer.md",
        "---\ncontext_rev: 1\npriority: P1\nupdated: 2026-09-11T00:00:00Z\n"
        "summary: Consume the contract.\nnext: Reconcile the contract.\n---\n\n"
        "# Context\n\nParent [[IDX-001-root]].\n\n"
        "Depends on [[DEF-001-contract]] at context_rev 1.\n",
    )
    _write(
        vault / "active" / "TAS-002-coordinator.md",
        "---\ncontext_rev: 1\npriority: P1\nupdated: 2026-09-11T00:00:00Z\n"
        "summary: Coordinate the child work.\n"
        'next: "[[TAS-003-child]]"\n---\n\n'
        "# Context\n\nParent [[IDX-001-root]].\n",
    )
    _write(
        vault / "proposed" / "TAS-003-child.md",
        "---\ncontext_rev: 1\npriority: P2\nupdated: 2026-09-11T00:00:00Z\n"
        "summary: Finish the child work.\nnext: Finish the child work.\n---\n\n"
        "# Context\n\nParent [[TAS-002-coordinator]].\n",
    )
    _write(
        vault / "proposed" / "THO-010-theory.md",
        "---\ncontext_rev: 1\nupdated: 2026-09-11T00:00:00Z\n"
        "summary: A theory to answer.\n---\n\n# Question\n\nWhy?\n",
    )
    _write(
        vault / "resolved" / "TAS-004-done.md",
        "---\ncontext_rev: 1\nupdated: 2026-09-11T00:00:00Z\n"
        "summary: Already finished.\n---\n",
    )


def test_frontier_matches_markdown_on_fixture(tmp_path: Path, run_bt: RunBt) -> None:
    """The frontier verb returns exactly the nodes the Markdown recipe derives."""
    vault = tmp_path / "vault" / "nodes"
    _seed_views(vault)
    assert _markdown_frontier_ids(vault) == {"TAS-001", "TAS-003", "THO-010"}

    result = run_bt("frontier", env=_env(tmp_path, vault))
    assert result.returncode == 0
    rows = _toon_rows(result.stdout, "frontier")
    assert [row[0] for row in rows] == ["TAS-001", "TAS-003", "THO-010"]
    assert {row[0] for row in rows} == _markdown_frontier_ids(vault)


def test_frontier_reports_fields_and_stale_flag(tmp_path: Path, run_bt: RunBt) -> None:
    """Frontier rows carry identity, status, priority, summary, next, and staleness."""
    vault = tmp_path / "vault" / "nodes"
    _seed_views(vault)
    rows = _toon_rows(run_bt("frontier", env=_env(tmp_path, vault)).stdout, "frontier")
    by_id = {row[0]: row for row in rows}
    assert by_id["TAS-001"][1:] == [
        "active",
        "P1",
        "Consume the contract.",
        "Reconcile the contract.",
        "true",
    ]
    assert by_id["TAS-003"][1:] == [
        "proposed",
        "P2",
        "Finish the child work.",
        "Finish the child work.",
        "false",
    ]
    assert by_id["THO-010"][1:] == ["proposed", "", "A theory to answer.", "", "false"]


def test_frontier_excludes_resolved_and_child_routes(tmp_path: Path, run_bt: RunBt) -> None:
    vault = tmp_path / "vault" / "nodes"
    _seed_views(vault)
    rows = _toon_rows(run_bt("frontier", env=_env(tmp_path, vault)).stdout, "frontier")
    ids = {row[0] for row in rows}
    assert "TAS-002" not in ids  # next is a [[child]] route
    assert "TAS-004" not in ids  # resolved


def test_frontier_matches_markdown_on_live_vault(run_bt: RunBt) -> None:
    """The frontier verb agrees with the Markdown recipe on the shipped vault."""
    nodes = _ROOT / "nodes"
    env = {
        "BT_NODES_DIR": str(nodes),
        "BT_SIDECAR_DIR": None,
        "BT_PROJECT_ID": None,
    }
    result = run_bt("frontier", cwd=_ROOT, env=env)
    assert result.returncode == 0
    rows = _toon_rows(result.stdout, "frontier")
    assert {row[0] for row in rows} == _markdown_frontier_ids(nodes)


def test_frontier_reports_zero_nodes(tmp_path: Path, run_bt: RunBt) -> None:
    vault = tmp_path / "vault" / "nodes"
    (vault / "resolved").mkdir(parents=True)
    _write(
        vault / "resolved" / "IDX-001-root.md",
        "---\ncontext_rev: 1\nupdated: 2026-09-11T00:00:00Z\n"
        "summary: Root hub.\n---\n",
    )
    result = run_bt("frontier", env=_env(tmp_path, vault))
    assert result.returncode == 0
    assert result.stdout.strip() == "frontier: 0 frontier nodes"


def test_frontier_requires_an_existing_nodes_directory(
    tmp_path: Path, run_bt: RunBt
) -> None:
    result = run_bt("frontier", env=_env(tmp_path, tmp_path / "missing"))
    assert result.returncode == 1
    assert "nodes directory does not exist" in result.stdout


def test_node_resolves_bare_id_and_full_name(tmp_path: Path, run_bt: RunBt) -> None:
    vault = tmp_path / "vault" / "nodes"
    _seed_views(vault)
    env = _env(tmp_path, vault)
    bare = run_bt("node", "TAS-001", env=env)
    named = run_bt("node", "TAS-001-consumer", env=env)
    assert bare.returncode == 0 and named.returncode == 0
    assert bare.stdout == named.stdout


def test_node_reports_frontmatter_route_edges_and_backlinks(
    tmp_path: Path, run_bt: RunBt
) -> None:
    """The node view ties its frontmatter, route, edge verdict, and backlinks to Markdown."""
    vault = tmp_path / "vault" / "nodes"
    _seed_views(vault)
    result = run_bt("node", "TAS-001", env=_env(tmp_path, vault))
    assert result.returncode == 0
    assert 'node: "TAS-001"' in result.stdout
    assert 'name: "TAS-001-consumer"' in result.stdout
    assert 'status: "active"' in result.stdout
    assert 'path: "active/TAS-001-consumer.md"' in result.stdout
    assert 'route_relation: "Parent"' in result.stdout
    assert 'route: "IDX-001-root"' in result.stdout
    frontmatter = {row[0]: row[1] for row in _toon_rows(result.stdout, "frontmatter")}
    assert frontmatter["context_rev"] == "1"
    assert frontmatter["next"] == "Reconcile the contract."
    assert frontmatter["priority"] == "P1"
    assert _toon_rows(result.stdout, "context_edges") == [
        ["Depends on", "DEF-001-contract", "1", "2", "resolved", "context_rev mismatch"]
    ]
    assert result.stdout.strip().endswith("backlinks: 0 backlinks")


def test_node_backlinks_follow_markdown_edges(tmp_path: Path, run_bt: RunBt) -> None:
    vault = tmp_path / "vault" / "nodes"
    _seed_views(vault)
    rows = _toon_rows(
        run_bt("node", "TAS-002-coordinator", env=_env(tmp_path, vault)).stdout,
        "backlinks",
    )
    assert ["TAS-003", "proposed", "Parent", ""] in rows


def test_node_unknown_node_is_an_error(tmp_path: Path, run_bt: RunBt) -> None:
    vault = tmp_path / "vault" / "nodes"
    _seed_views(vault)
    result = run_bt("node", "TAS-999", env=_env(tmp_path, vault))
    assert result.returncode == 1
    assert 'error: "unknown node: TAS-999"' in result.stdout
