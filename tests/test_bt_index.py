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


def _seed_impact_chain(vault: Path) -> None:
    (vault / "resolved").mkdir(parents=True)
    (vault / "active").mkdir()
    _write(
        vault / "resolved" / "DEF-001-contract.md",
        "---\ncontext_rev: 3\nupdated: 2026-09-11T00:00:00Z\n"
        "summary: Current contract.\n---\n\n# Invariant\n\nCurrent.\n",
    )
    _write(
        vault / "resolved" / "TAS-001-consumer.md",
        "---\ncontext_rev: 1\nupdated: 2026-09-11T00:00:00Z\n"
        "summary: Direct consumer.\n---\n\n# Context\n\n"
        "Depends on [[DEF-001-contract]] at context_rev 2.\n",
    )
    _write(
        vault / "active" / "TAS-002-transitive.md",
        "---\ncontext_rev: 1\nupdated: 2026-09-11T00:00:00Z\n"
        "summary: Transitive consumer.\n---\n\n# Context\n\n"
        "Depends on [[TAS-001-consumer]] at context_rev 1.\n",
    )


def test_impact_chain_is_transitive_and_dependency_ordered(
    tmp_path: Path, run_bt: RunBt
) -> None:
    """A chain reports the direct consumer before the transitive one, with pins."""
    vault = tmp_path / "vault" / "nodes"
    _seed_impact_chain(vault)
    result = run_bt("impact", "DEF-001", env=_env(tmp_path, vault))
    assert result.returncode == 0
    assert 'target: "DEF-001"' in result.stdout
    assert 'target_context_rev: "3"' in result.stdout
    assert _toon_rows(result.stdout, "impact") == [
        [
            "TAS-001",
            "resolved",
            "1",
            "Depends on",
            "DEF-001",
            "2",
            "3",
            "context_rev mismatch",
        ],
        ["TAS-002", "active", "2", "Depends on", "TAS-001", "1", "1", ""],
    ]

    named = run_bt("impact", "DEF-001-contract", env=_env(tmp_path, vault))
    assert named.returncode == 0
    assert named.stdout == result.stdout


def _seed_impact_diamond(vault: Path) -> None:
    (vault / "resolved").mkdir(parents=True)
    (vault / "active").mkdir()
    _write(
        vault / "resolved" / "DEF-001-contract.md",
        "---\ncontext_rev: 2\nupdated: 2026-09-11T00:00:00Z\n"
        "summary: Shared contract.\n---\n\n# Invariant\n\nShared.\n",
    )
    for name, summary in (
        ("TAS-001-left.md", "Left consumer."),
        ("TAS-002-right.md", "Right consumer."),
    ):
        _write(
            vault / "resolved" / name,
            "---\ncontext_rev: 1\nupdated: 2026-09-11T00:00:00Z\n"
            f"summary: {summary}\n---\n\n# Context\n\n"
            "Depends on [[DEF-001-contract]] at context_rev 2.\n",
        )
    _write(
        vault / "active" / "TAS-003-join.md",
        "---\ncontext_rev: 1\nupdated: 2026-09-11T00:00:00Z\n"
        "summary: Joining consumer.\n---\n\n# Context\n\n"
        "Depends on [[TAS-001-left]] at context_rev 1.\n\n"
        "Depends on [[TAS-002-right]] at context_rev 1.\n",
    )


def test_impact_diamond_names_every_edge_once(tmp_path: Path, run_bt: RunBt) -> None:
    """A diamond reports both paths to the joining dependent, each edge once."""
    vault = tmp_path / "vault" / "nodes"
    _seed_impact_diamond(vault)
    rows = _toon_rows(
        run_bt("impact", "DEF-001", env=_env(tmp_path, vault)).stdout, "impact"
    )
    assert [row[0] for row in rows] == ["TAS-001", "TAS-002", "TAS-003", "TAS-003"]
    assert [row[2] for row in rows] == ["1", "1", "2", "2"]
    assert {(row[0], row[4]) for row in rows} == {
        ("TAS-001", "DEF-001"),
        ("TAS-002", "DEF-001"),
        ("TAS-003", "TAS-001"),
        ("TAS-003", "TAS-002"),
    }


def _seed_impact_cycle(vault: Path) -> None:
    (vault / "active").mkdir(parents=True)
    for name, target in (
        ("TAS-001-a.md", "TAS-002-b"),
        ("TAS-002-b.md", "TAS-003-c"),
        ("TAS-003-c.md", "TAS-001-a"),
    ):
        _write(
            vault / "active" / name,
            "---\ncontext_rev: 1\nupdated: 2026-09-11T00:00:00Z\n"
            f"summary: Cycle member {target}.\n---\n\n# Context\n\n"
            f"Depends on [[{target}]] at context_rev 1.\n",
        )


def test_impact_cycle_terminates_without_self_listing(
    tmp_path: Path, run_bt: RunBt
) -> None:
    """A dependency cycle terminates and never lists the target as its own dependent."""
    vault = tmp_path / "vault" / "nodes"
    _seed_impact_cycle(vault)
    result = run_bt("impact", "TAS-001", env=_env(tmp_path, vault))
    assert result.returncode == 0
    rows = _toon_rows(result.stdout, "impact")
    assert [row[0] for row in rows] == ["TAS-003", "TAS-002"]
    assert [row[4] for row in rows] == ["TAS-001", "TAS-003"]
    assert all(row[0] != "TAS-001" for row in rows)


def test_impact_ignores_navigation_edges_and_reports_zero(
    tmp_path: Path, run_bt: RunBt
) -> None:
    """Only canonical context edges create impact; navigation edges do not."""
    vault = tmp_path / "vault" / "nodes"
    (vault / "resolved").mkdir(parents=True)
    _write(
        vault / "resolved" / "IDX-001-root.md",
        "---\ncontext_rev: 1\nupdated: 2026-09-11T00:00:00Z\n"
        "summary: Root hub.\n---\n",
    )
    _write(
        vault / "resolved" / "DEF-001-contract.md",
        "---\ncontext_rev: 1\nupdated: 2026-09-11T00:00:00Z\n"
        "summary: Contract with only a route back.\n---\n\n# Context\n\n"
        "Area [[IDX-001-root]].\n",
    )
    result = run_bt("impact", "DEF-001", env=_env(tmp_path, vault))
    assert result.returncode == 0
    assert 'target_context_rev: "1"' in result.stdout
    assert result.stdout.strip().endswith("impact: 0 dependents")


def test_impact_unknown_node_is_an_error(tmp_path: Path, run_bt: RunBt) -> None:
    vault = tmp_path / "vault" / "nodes"
    _seed_impact_chain(vault)
    result = run_bt("impact", "TAS-999", env=_env(tmp_path, vault))
    assert result.returncode == 1
    assert 'error: "unknown node: TAS-999"' in result.stdout


def _section_totals(output: str) -> dict[str, int]:
    """Map each ``orient`` section name to the unbounded ``total`` it reported."""
    totals: dict[str, int] = {}
    current: str | None = None
    for line in output.splitlines():
        section = re.fullmatch(r'section: "([^"]+)"', line)
        if section is not None:
            current = section.group(1)
            continue
        total = re.fullmatch(r'total: "([0-9]+)"', line)
        if current is not None and total is not None:
            totals[current] = int(total.group(1))
            current = None
    return totals


def _seed_orientation(vault: Path) -> None:
    """Seed a vault that populates every orientation section."""
    (vault / "resolved").mkdir(parents=True)
    (vault / "active").mkdir()
    (vault / "blocked").mkdir()
    _write(
        vault / "index-map.md",
        "---\nupdated: 2026-09-11T00:00:00Z\nsummary: Route orientation work.\n---\n\n"
        "# Focus\n\n- [[TAS-001-consumer]]\n\n"
        "# Root hubs\n\n- Indexes [[IDX-001-root]].\n",
    )
    _write(
        vault / "resolved" / "IDX-001-root.md",
        "---\ncontext_rev: 1\nupdated: 2026-09-10T00:00:00Z\n"
        "summary: Root hub.\n---\n",
    )
    _write(
        vault / "resolved" / "DEF-001-contract.md",
        "---\ncontext_rev: 3\nupdated: 2026-09-10T00:00:00Z\n"
        "summary: Current contract.\n---\n\n# Context\n\nArea [[IDX-001-root]].\n\n"
        "# Invariant\n\nCurrent.\n",
    )
    _write(
        vault / "active" / "TAS-001-consumer.md",
        "---\ncontext_rev: 1\npriority: P1\nupdated: 2026-09-11T00:00:00Z\n"
        "summary: Consume the contract.\nnext: Reconcile the contract.\n---\n\n"
        "# Context\n\nParent [[IDX-001-root]].\n\n"
        "Depends on [[DEF-001-contract]] at context_rev 2.\n",
    )
    _write(
        vault / "blocked" / "TAS-002-blocked.md",
        "---\ncontext_rev: 1\npriority: P2\nupdated: 2026-09-09T00:00:00Z\n"
        "summary: Wait on external approval.\nnext: Resume when approval lands.\n---\n\n"
        "# Context\n\nParent [[IDX-001-root]].\n\n"
        "# Blocked\n\nBlocked by: External approval.\n\n"
        "Unblocks when: approval lands.\n",
    )
    _write(
        vault / "active" / "TAS-003-conflict.md",
        "---\ncontext_rev: 1\npriority: P3\nupdated: 2026-09-08T00:00:00Z\n"
        "summary: Track a broken link.\nnext: Repair the link.\n---\n\n"
        "# Context\n\nParent [[IDX-001-root]].\n\nSee [[DEF-404-missing]].\n",
    )


def test_orient_populates_every_section(tmp_path: Path, run_bt: RunBt) -> None:
    """One call answers focus, frontier, blockers, stale, recent, and conflicts."""
    vault = tmp_path / "vault" / "nodes"
    _seed_orientation(vault)
    result = run_bt("orient", env=_env(tmp_path, vault))
    assert result.returncode == 0
    assert _section_totals(result.stdout) == {
        "focus": 1,
        "frontier": 3,
        "blockers": 1,
        "stale": 1,
        "recent": 5,
        "conflicts": 2,
    }
    assert _toon_rows(result.stdout, "focus") == [["TAS-001-consumer", "active", "true"]]
    frontier = {row[0]: row for row in _toon_rows(result.stdout, "frontier")}
    assert set(frontier) == {"TAS-001", "TAS-002", "TAS-003"}
    assert frontier["TAS-001"][5] == "true"
    assert frontier["TAS-002"][5] == "false"
    assert _toon_rows(result.stdout, "blockers") == [
        ["TAS-002", "P2", "Wait on external approval.", "Resume when approval lands."]
    ]
    assert _toon_rows(result.stdout, "stale") == [
        ["TAS-001", "active", "DEF-001", "2", "3", "Depends on", "context_rev mismatch"]
    ]
    assert [row[0] for row in _toon_rows(result.stdout, "recent")] == [
        "TAS-001",
        "DEF-001",
        "IDX-001",
        "TAS-002",
        "TAS-003",
    ]


def test_orient_conflicts_match_check(tmp_path: Path, run_bt: RunBt) -> None:
    """The conflicts section is exactly the findings ``braintree check`` reports."""
    vault = tmp_path / "vault" / "nodes"
    _seed_orientation(vault)
    conflicts = _toon_rows(
        run_bt("orient", "--section", "conflicts", env=_env(tmp_path, vault)).stdout,
        "conflicts",
    )
    checked = run_bt("check", "--format", "toon", str(vault))
    assert checked.returncode == 1
    assert {row[0] for row in conflicts} == {
        "node-broken-link",
        "context-rev-mismatch",
    }
    assert conflicts == _toon_rows(checked.stdout, "findings")


def _seed_recent_corpus(vault: Path, count: int) -> None:
    (vault / "resolved").mkdir(parents=True)
    _write(
        vault / "index-map.md",
        "---\nupdated: 2026-09-11T00:00:00Z\nsummary: Route work.\n---\n\n"
        "# Root hubs\n\n- Indexes [[IDX-001-root]].\n",
    )
    _write(
        vault / "resolved" / "IDX-001-root.md",
        "---\ncontext_rev: 1\nupdated: 2026-08-31T00:00:00Z\nsummary: Root hub.\n---\n",
    )
    for number in range(1, count + 1):
        _write(
            vault / "resolved" / f"THO-{number:03d}-note.md",
            f"---\ncontext_rev: 1\nupdated: 2026-09-{number:02d}T00:00:00Z\n"
            f"summary: Note {number}.\n---\n\n# Context\n\nArea [[IDX-001-root]].\n",
        )


def test_orient_sections_are_selectable_and_bounded(
    tmp_path: Path, run_bt: RunBt
) -> None:
    """A selected section is bounded by the limit while its total stays unbounded."""
    vault = tmp_path / "vault" / "nodes"
    _seed_recent_corpus(vault, 12)
    env = _env(tmp_path, vault)
    selected = run_bt("orient", "--section", "recent", "--limit", "3", env=env)
    assert selected.returncode == 0
    assert "frontier[" not in selected.stdout
    assert _section_totals(selected.stdout) == {"recent": 13}
    assert len(_toon_rows(selected.stdout, "recent")) == 3
    default = run_bt("orient", "--section", "recent", env=env)
    assert len(_toon_rows(default.stdout, "recent")) == 10


def test_orient_keeps_canonical_section_order(tmp_path: Path, run_bt: RunBt) -> None:
    vault = tmp_path / "vault" / "nodes"
    _seed_recent_corpus(vault, 2)
    result = run_bt(
        "orient", "--section", "recent", "--section", "blockers", env=_env(tmp_path, vault)
    )
    assert re.findall(r'section: "([^"]+)"', result.stdout) == ["blockers", "recent"]


def _seed_single_node(vault: Path) -> None:
    (vault / "resolved").mkdir(parents=True)
    _write(
        vault / "index-map.md",
        "---\nupdated: 2026-09-11T00:00:00Z\nsummary: Route work.\n---\n\n"
        "# Root hubs\n\n- Indexes [[IDX-001-root]].\n",
    )
    _write(
        vault / "resolved" / "IDX-001-root.md",
        "---\ncontext_rev: 1\nupdated: 2026-09-11T00:00:00Z\nsummary: Root hub.\n---\n",
    )


def test_orient_on_single_node_vault(tmp_path: Path, run_bt: RunBt) -> None:
    vault = tmp_path / "vault" / "nodes"
    _seed_single_node(vault)
    result = run_bt("orient", env=_env(tmp_path, vault))
    assert result.returncode == 0
    assert _section_totals(result.stdout) == {
        "focus": 0,
        "frontier": 0,
        "blockers": 0,
        "stale": 0,
        "recent": 1,
        "conflicts": 0,
    }
    assert _toon_rows(result.stdout, "recent") == [
        ["IDX-001", "resolved", "2026-09-11T00:00:00Z", "Root hub."]
    ]
    assert result.stdout.count("conflicts: 0 findings") == 1


def test_orient_on_empty_vault(tmp_path: Path, run_bt: RunBt) -> None:
    """An empty vault yields empty sections and the checker's own finding."""
    vault = tmp_path / "vault" / "nodes"
    vault.mkdir(parents=True)
    result = run_bt("orient", env=_env(tmp_path, vault))
    assert result.returncode == 0
    assert result.stdout.count("focus: 0 focus pointers") == 1
    assert result.stdout.count("frontier: 0 frontier nodes") == 1
    assert result.stdout.count("blockers: 0 blocked nodes") == 1
    assert result.stdout.count("stale: 0 stale dependency pins") == 1
    assert result.stdout.count("recent: 0 nodes") == 1
    assert "vault-no-nodes" in {row[0] for row in _toon_rows(result.stdout, "conflicts")}


def test_orient_requires_an_existing_nodes_directory(
    tmp_path: Path, run_bt: RunBt
) -> None:
    result = run_bt("orient", env=_env(tmp_path, tmp_path / "missing"))
    assert result.returncode == 1
    assert "nodes directory does not exist" in result.stdout


def _seed_search_filters(vault: Path) -> None:
    """Seed nodes that share the query term ``token`` but differ on every filter."""
    (vault / "resolved").mkdir(parents=True)
    (vault / "active").mkdir()
    (vault / "proposed").mkdir()
    _write(
        vault / "resolved" / "IDX-001-root.md",
        "---\ncontext_rev: 1\nupdated: 2026-09-11T00:00:00Z\nsummary: Root hub.\n---\n",
    )
    _write(
        vault / "resolved" / "DEF-001-contract.md",
        "---\ncontext_rev: 2\nupdated: 2026-09-11T00:00:00Z\n"
        "summary: Auth token contract.\n---\n\n# Invariant\n\nThe token is signed.\n",
    )
    _write(
        vault / "active" / "TAS-001-consumer.md",
        "---\ncontext_rev: 1\npriority: P1\nupdated: 2026-09-11T00:00:00Z\n"
        "summary: Consume the auth token.\nnext: Reconcile the token.\n---\n\n"
        "# Context\n\nParent [[IDX-001-root]].\n\n"
        "Depends on [[DEF-001-contract]] at context_rev 2.\n",
    )
    _write(
        vault / "proposed" / "TAS-002-draft.md",
        "---\ncontext_rev: 1\npriority: P2\nupdated: 2026-09-11T00:00:00Z\n"
        "summary: Draft the next token flow.\nnext: Draft the token flow.\n---\n\n"
        "# Context\n\nParent [[TAS-001-consumer]].\n",
    )
    _write(
        vault / "proposed" / "THO-010-theory.md",
        "---\ncontext_rev: 1\nupdated: 2026-09-11T00:00:00Z\n"
        "summary: A theory about token rotation.\n---\n\n# Question\n\nWhy?\n",
    )


def _search_ids(output: str) -> list[str]:
    return [row[0] for row in _toon_rows(output, "nodes")]


def test_search_filters_by_status_type_and_priority(
    tmp_path: Path, run_bt: RunBt
) -> None:
    """A structured filter narrows the ranked matches on its Markdown field."""
    vault = tmp_path / "vault" / "nodes"
    _seed_search_filters(vault)
    env = _env(tmp_path, vault)
    assert _search_ids(run_bt("search", "token", "--status", "active", env=env).stdout) == [
        "TAS-001"
    ]
    assert _search_ids(run_bt("search", "token", "--type", "THO", env=env).stdout) == [
        "THO-010"
    ]
    assert _search_ids(run_bt("search", "token", "--priority", "P2", env=env).stdout) == [
        "TAS-002"
    ]


def test_search_filters_by_parent_and_dependency(tmp_path: Path, run_bt: RunBt) -> None:
    """Parent resolves a bare ID or full name; dependency follows context edges."""
    vault = tmp_path / "vault" / "nodes"
    _seed_search_filters(vault)
    env = _env(tmp_path, vault)
    assert _search_ids(run_bt("search", "token", "--parent", "IDX-001", env=env).stdout) == [
        "TAS-001"
    ]
    assert _search_ids(
        run_bt("search", "token", "--parent", "IDX-001-root", env=env).stdout
    ) == ["TAS-001"]
    assert _search_ids(
        run_bt("search", "token", "--parent", "TAS-001", env=env).stdout
    ) == ["TAS-002"]
    assert _search_ids(
        run_bt("search", "token", "--dependency", "DEF-001", env=env).stdout
    ) == ["TAS-001"]


def test_search_combines_filters_and_reports_zero(tmp_path: Path, run_bt: RunBt) -> None:
    """Filters AND together, and an unmatched filter states zero explicitly."""
    vault = tmp_path / "vault" / "nodes"
    _seed_search_filters(vault)
    env = _env(tmp_path, vault)
    combined = run_bt("search", "token", "--status", "active", "--parent", "IDX-001", env=env)
    assert _search_ids(combined.stdout) == ["TAS-001"]
    unfiltered = run_bt("search", "token", env=env)
    assert set(_search_ids(unfiltered.stdout)) == {
        "DEF-001",
        "TAS-001",
        "TAS-002",
        "THO-010",
    }
    zero = run_bt("search", "token", "--status", "resolved", "--type", "TAS", env=env)
    assert zero.returncode == 0
    assert zero.stdout.strip() == "nodes: 0 matching nodes"


def test_search_rejects_invalid_filters(tmp_path: Path, run_bt: RunBt) -> None:
    vault = tmp_path / "vault" / "nodes"
    _seed_search_filters(vault)
    env = _env(tmp_path, vault)
    bad_status = run_bt("search", "token", "--status", "bogus", env=env)
    assert bad_status.returncode == 2
    assert 'error: "--status must be one of' in bad_status.stdout
    bad_priority = run_bt("search", "token", "--priority", "P9", env=env)
    assert bad_priority.returncode == 2
    assert 'error: "--priority must be one of' in bad_priority.stdout
    duplicate = run_bt("search", "token", "--status", "active", "--status", "active", env=env)
    assert duplicate.returncode == 2
    assert 'error: "duplicate --status"' in duplicate.stdout
    missing_value = run_bt("search", "token", "--parent", env=env)
    assert missing_value.returncode == 2
    assert 'error: "--parent requires a value"' in missing_value.stdout


def _seed_similar(vault: Path) -> None:
    """Seed a near-duplicate pair plus an unrelated node."""
    (vault / "resolved").mkdir(parents=True)
    (vault / "proposed").mkdir()
    _write(
        vault / "resolved" / "DEF-001-grant-contract.md",
        "---\ncontext_rev: 1\nupdated: 2026-09-11T00:00:00Z\n"
        "summary: Reject expired authentication grants.\n---\n\n# Invariant\n\n"
        "Reject expired authentication grants before issuing a session.\n",
    )
    _write(
        vault / "proposed" / "TAS-001-reject-grants.md",
        "---\ncontext_rev: 1\npriority: P1\nupdated: 2026-09-11T00:00:00Z\n"
        "summary: Reject expired authentication grants.\nnext: Implement it.\n---\n\n"
        "# Outcome\n\nReject expired authentication grants.\n",
    )
    _write(
        vault / "resolved" / "DEF-002-cache-policy.md",
        "---\ncontext_rev: 1\nupdated: 2026-09-11T00:00:00Z\n"
        "summary: Cache eviction policy.\n---\n\n# Invariant\n\n"
        "The cache evicts cold entries.\n",
    )


def test_similar_ranks_the_near_duplicate_pair(tmp_path: Path, run_bt: RunBt) -> None:
    """The nearest existing nodes to a draft summary are its near-duplicates."""
    vault = tmp_path / "vault" / "nodes"
    _seed_similar(vault)
    result = run_bt(
        "similar", "Reject expired authentication grants", env=_env(tmp_path, vault)
    )
    assert result.returncode == 0
    rows = _toon_rows(result.stdout, "similar")
    assert {row[0] for row in rows} == {"DEF-001", "TAS-001"}
    scores = [float(row[2]) for row in rows]
    assert scores == sorted(scores, reverse=True)
    assert all(score > 0.5 for score in scores)
    assert {row[1] for row in rows} == {"resolved", "proposed"}


def test_similar_is_bounded_and_reports_zero(tmp_path: Path, run_bt: RunBt) -> None:
    vault = tmp_path / "vault" / "nodes"
    _seed_similar(vault)
    env = _env(tmp_path, vault)
    bounded = run_bt(
        "similar", "Reject expired authentication grants", "--limit", "1", env=env
    )
    rows = _toon_rows(bounded.stdout, "similar")
    assert len(rows) == 1
    assert rows[0][0] == "TAS-001"
    zero = run_bt("similar", "unrelated zebra migration", env=env)
    assert zero.returncode == 0
    assert zero.stdout.strip() == "similar: 0 matching nodes"


def test_similar_reads_the_candidate_text_from_a_file(
    tmp_path: Path, run_bt: RunBt
) -> None:
    vault = tmp_path / "vault" / "nodes"
    _seed_similar(vault)
    draft = tmp_path / "draft.md"
    _write(draft, "Reject expired authentication grants")
    env = _env(tmp_path, vault)
    inline = run_bt("similar", "Reject expired authentication grants", env=env)
    from_file = run_bt("similar", "--file", str(draft), env=env)
    assert from_file.returncode == 0
    assert from_file.stdout == inline.stdout


def test_similar_rejects_conflicting_or_missing_input(
    tmp_path: Path, run_bt: RunBt
) -> None:
    vault = tmp_path / "vault" / "nodes"
    _seed_similar(vault)
    env = _env(tmp_path, vault)
    missing = run_bt("similar", env=env)
    assert missing.returncode == 2
    assert 'error: "similar requires TEXT or --file PATH"' in missing.stdout
    both = run_bt("similar", "text", "--file", "path", env=env)
    assert both.returncode == 2
    assert 'error: "similar accepts TEXT or --file PATH, not both"' in both.stdout
    unreadable = run_bt("similar", "--file", str(tmp_path / "absent.md"), env=env)
    assert unreadable.returncode == 1
    assert 'error: "cannot read file:' in unreadable.stdout
