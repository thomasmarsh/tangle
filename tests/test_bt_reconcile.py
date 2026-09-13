"""Tests for the ``braintree reconcile`` integration planner.

Builds throwaway Git repositories that reproduce the worktree-parallel
scenarios: two snapshots that introduce the same numeric ID, one node changed by
a rename on one snapshot and an edit on another, and a dependency whose
``context_rev`` bump leaves a base consumer stale. The planner must classify
each hazard and order the repairs so a pinned dependency is reconciled after its
target.
"""

from __future__ import annotations

import csv
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

RunBt = Callable[..., subprocess.CompletedProcess[str]]


def _git(repo: Path, *args: str) -> str:
    result = subprocess.run(
        ["git", "-C", str(repo), *args],
        capture_output=True,
        text=True,
        check=True,
    )
    return result.stdout


def _rev(repo: Path) -> str:
    return _git(repo, "rev-parse", "HEAD").strip()


def _commit(repo: Path, message: str) -> None:
    _git(repo, "add", "-A")
    _git(repo, "commit", "-q", "-m", message)


def _branch(repo: Path, name: str) -> None:
    _git(repo, "checkout", "-q", "-b", name)


def _checkout(repo: Path, name: str) -> None:
    _git(repo, "checkout", "-q", name)


def _node_text(
    context_rev: int,
    summary: str,
    body: str = "",
    next_action: str | None = None,
) -> str:
    fields = [
        "---",
        f"context_rev: {context_rev}",
        "updated: 2026-09-11T00:00:00Z",
        f"summary: {summary}",
    ]
    if next_action is not None:
        fields.append(f"next: {next_action}")
    fields.extend(["---", "", body, ""])
    return "\n".join(fields)


def _write(repo: Path, status: str, name: str, text: str) -> None:
    path = repo / ".braintree" / status / f"{name}.md"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _init_repo(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    (repo / ".braintree" / "resolved").mkdir(parents=True)
    _git(repo, "init", "-q", "-b", "main")
    _git(repo, "config", "user.email", "reconcile-test@example.invalid")
    _git(repo, "config", "user.name", "Reconcile Test")
    (repo / ".braintree" / "index-map.md").write_text(
        "# Roots\n\n- Indexes [[IDX-001-root]].\n", encoding="utf-8"
    )
    _write(
        repo,
        "resolved",
        "IDX-001-root",
        _node_text(1, "Root.", "# Invariant\n\nDurable root hub.\n"),
    )
    _commit(repo, "fixture")
    return repo


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


def _env(tmp_path: Path) -> dict[str, str]:
    return {"BT_SIDECAR_DIR": str(tmp_path / "sidecar"), "BT_PROJECT_ID": "reconcile-test"}


def test_reconcile_duplicate_identity_across_snapshots(
    tmp_path: Path, run_bt: RunBt
) -> None:
    """Two heads that introduce the same numeric ID at different paths collide."""
    repo = _init_repo(tmp_path)
    base = _rev(repo)
    _branch(repo, "duplicate-a")
    _write(
        repo,
        "active",
        "TAS-100-alpha",
        _node_text(1, "Duplicate alpha.", "Area [[IDX-001-root]].\n"),
    )
    _commit(repo, "alpha")
    _checkout(repo, "main")
    _branch(repo, "duplicate-b")
    _write(
        repo,
        "active",
        "TAS-100-beta",
        _node_text(1, "Duplicate beta.", "Area [[IDX-001-root]].\n"),
    )
    _commit(repo, "beta")

    result = run_bt(
        "reconcile",
        "--base",
        base,
        "--head",
        "duplicate-a",
        "--head",
        "duplicate-b",
        cwd=repo,
        env=_env(tmp_path),
    )
    assert result.returncode == 0
    rows = _toon_rows(result.stdout, "steps")
    assert [row[0] for row in rows] == ["duplicate-identity", "duplicate-identity"]
    assert {row[2] for row in rows} == {"TAS-100"}
    assert {row[3] for row in rows} == {
        ".braintree/active/TAS-100-alpha.md",
        ".braintree/active/TAS-100-beta.md",
    }
    assert all("duplicate node identity: TAS-100" in row[6] for row in rows)


def test_reconcile_same_node_rename_versus_edit(tmp_path: Path, run_bt: RunBt) -> None:
    """One head renames a basename while another edits it: divergence, not merge."""
    repo = _init_repo(tmp_path)
    _write(
        repo,
        "active",
        "TAS-010-shared",
        _node_text(1, "Shared work.", "Area [[IDX-001-root]].\n", next_action="Finish shared."),
    )
    _commit(repo, "shared")
    base = _rev(repo)

    _branch(repo, "rename")
    (repo / ".braintree" / "resolved").mkdir(exist_ok=True)
    _git(repo, "mv", ".braintree/active/TAS-010-shared.md", ".braintree/resolved/TAS-010-shared.md")
    renamed = repo / ".braintree" / "resolved" / "TAS-010-shared.md"
    renamed.write_text(
        "\n".join(
            line
            for line in renamed.read_text(encoding="utf-8").splitlines()
            if not line.startswith("next:")
        )
        + "\n",
        encoding="utf-8",
    )
    _commit(repo, "rename")

    _checkout(repo, "main")
    _branch(repo, "edit")
    edited = repo / ".braintree" / "active" / "TAS-010-shared.md"
    edited.write_text(
        edited.read_text(encoding="utf-8").replace("Shared work.", "Edited shared work."),
        encoding="utf-8",
    )
    _commit(repo, "edit")

    result = run_bt(
        "reconcile",
        "--base",
        base,
        "--head",
        "rename",
        "--head",
        "edit",
        cwd=repo,
        env=_env(tmp_path),
    )
    assert result.returncode == 0
    rows = _toon_rows(result.stdout, "steps")
    assert [row[0] for row in rows] == ["same-node-divergence"]
    assert rows[0][2] == "TAS-010-shared"
    assert rows[0][3] == ".braintree/active/TAS-010-shared.md"
    assert "rename" in rows[0][6] and "edit" in rows[0][6]


def test_reconcile_orders_consumers_after_their_target(tmp_path: Path, run_bt: RunBt) -> None:
    """A bumped dependency is reread before the consumer that pins its old revision."""
    repo = _init_repo(tmp_path)
    _write(
        repo,
        "resolved",
        "DEF-010-contract",
        _node_text(1, "Initial contract.", "# Invariant\n\nArea [[IDX-001-root]].\n"),
    )
    _write(
        repo,
        "active",
        "TAS-011-consumer",
        _node_text(
            1,
            "Consumer.",
            "Area [[IDX-001-root]].\n\nDepends on [[DEF-010-contract]] at context_rev 1.\n",
            next_action="Execute consumer.",
        ),
    )
    _commit(repo, "consumer")
    base = _rev(repo)

    _branch(repo, "dependency")
    contract = repo / ".braintree" / "resolved" / "DEF-010-contract.md"
    contract.write_text(
        contract.read_text(encoding="utf-8").replace("context_rev: 1", "context_rev: 2"),
        encoding="utf-8",
    )
    _commit(repo, "dependency bump")

    result = run_bt(
        "reconcile", "--base", base, "--head", "dependency", cwd=repo, env=_env(tmp_path)
    )
    assert result.returncode == 0
    rows = _toon_rows(result.stdout, "steps")
    assert [row[0] for row in rows] == ["reread-dependency", "reconcile-consumer"]
    assert [row[2] for row in rows] == ["DEF-010", "TAS-011"]
    assert rows[0][4:6] == ["1", "2"]
    assert rows[1][4:6] == ["1", "2"]
    assert rows[1][6] == "context_rev mismatch"


def test_reconcile_reports_empty_plan(tmp_path: Path, run_bt: RunBt) -> None:
    repo = _init_repo(tmp_path)
    result = run_bt("reconcile", "--base", "HEAD", "--head", "HEAD", cwd=repo, env=_env(tmp_path))
    assert result.returncode == 0
    assert 'base: "HEAD"' in result.stdout
    assert result.stdout.strip().endswith("reconcile: 0 steps")


def test_reconcile_unknown_ref_is_an_error(tmp_path: Path, run_bt: RunBt) -> None:
    repo = _init_repo(tmp_path)
    result = run_bt(
        "reconcile", "--base", "does-not-exist", cwd=repo, env=_env(tmp_path)
    )
    assert result.returncode == 1
    assert 'error: "unknown Git ref: does-not-exist"' in result.stdout


def test_reconcile_outside_a_git_work_tree(tmp_path: Path, run_bt: RunBt) -> None:
    repo = _init_repo(tmp_path)
    outside = tmp_path / "outside"
    outside.mkdir()
    probe = subprocess.run(
        ["git", "-C", str(outside), "rev-parse", "--show-toplevel"],
        capture_output=True,
        text=True,
    )
    if probe.returncode == 0:
        pytest.skip("temporary directory is inside a Git work tree")
    result = run_bt(
        "reconcile", str(repo / ".braintree"), cwd=outside, env=_env(tmp_path)
    )
    assert result.returncode == 1
    assert 'error: "not inside a Git work tree"' in result.stdout
    assert repo.is_dir()


def test_reconcile_argument_errors(tmp_path: Path, run_bt: RunBt) -> None:
    repo = _init_repo(tmp_path)
    env = _env(tmp_path)
    missing_base = run_bt("reconcile", "--base", cwd=repo, env=env)
    assert missing_base.returncode == 2
    assert 'error: "--base requires REF"' in missing_base.stdout

    missing_head = run_bt("reconcile", "--head", cwd=repo, env=env)
    assert missing_head.returncode == 2
    assert 'error: "--head requires REF"' in missing_head.stdout

    unknown = run_bt("reconcile", "--bogus", cwd=repo, env=env)
    assert unknown.returncode == 2
    assert 'error: "unknown argument for reconcile: --bogus"' in unknown.stdout

    extra = run_bt("reconcile", "nodes", "other", cwd=repo, env=env)
    assert extra.returncode == 2
    assert 'error: "reconcile accepts at most one NODES directory"' in extra.stdout

    missing_dir = run_bt("reconcile", "absent", cwd=repo, env=env)
    assert missing_dir.returncode == 1
    assert 'error: "nodes directory does not exist:' in missing_dir.stdout
