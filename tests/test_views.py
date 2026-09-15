"""Behavioral tests for generated Markdown navigation views.

Views are a disposable, deterministic projection of canonical Markdown that
Tangle publishes itself. These tests drive the real command process: a direct
Markdown edit reaches the pages on the next interaction, an unchanged vault
rewrites nothing, a generated page is never discovered as a node, and the
``status`` and ``index`` diagnostic surfaces report the projection state.
"""

from __future__ import annotations

import json
import re
import subprocess
from collections.abc import Callable
from pathlib import Path

RunTangle = Callable[..., subprocess.CompletedProcess[str]]

_PROJECT = "views-test"
_PROJECT_UID = "prj-04r8b1t7n2c6m9x3q5f0hkwdza"


def _env(tmp_path: Path, vault: Path) -> dict[str, str]:
    return {
        "TANGLE_SIDECAR_DIR": str(tmp_path / "sidecar"),
        "TANGLE_PROJECT_ID": _PROJECT,
        "TANGLE_NODES_DIR": str(vault),
    }


def _frontmatter(
    summary: str,
    *,
    updated: str,
    priority: str | None = None,
    next_line: str | None = None,
) -> str:
    """Return legacy-layout frontmatter; status comes from the directory."""
    lines = ["---", "context_rev: 1"]
    if priority is not None:
        lines.append(f"priority: {priority}")
    lines.append(f"updated: {updated}")
    lines.append(f"summary: {summary}")
    if next_line is not None:
        lines.append(f"next: {next_line}")
    lines.extend(["---", ""])
    return "\n".join(lines) + "\n"


def _seed(vault: Path) -> None:
    """Write one hub and one routed member in the legacy directory layout."""
    (vault / "resolved").mkdir(parents=True)
    (vault / "active").mkdir()
    (vault / "index-map.md").write_text(
        "# Root hubs\n\n- Indexes [[IDX-001-root]]\n", encoding="utf-8"
    )
    (vault / "resolved" / "IDX-001-root.md").write_text(
        _frontmatter("Root graph entry.", updated="2026-09-10T00:00:00Z")
        + "\n# Invariant\n\nRoot content finds all work.\n",
        encoding="utf-8",
    )
    (vault / "active" / "TAS-001-consumer.md").write_text(
        _frontmatter(
            "Consume the root.",
            updated="2026-09-12T00:00:00Z",
            priority="P0",
            next_line="Reconcile the root.",
        )
        + "\nParent [[IDX-001-root]].\n",
        encoding="utf-8",
    )


def _page(vault: Path, name: str) -> str:
    return (vault / "views" / name).read_text(encoding="utf-8")


def test_a_read_only_interaction_publishes_view_pages(
    tmp_path: Path, run_tangle: RunTangle
) -> None:
    """`frontier` publishes the deterministic pages with no client step."""
    vault = tmp_path / "nodes"
    _seed(vault)
    env = _env(tmp_path, vault)
    assert run_tangle("init", env=env).returncode == 0

    answered = run_tangle("frontier", env=env)
    assert answered.returncode == 0

    assert set(name.name for name in (vault / "views").iterdir()) == {
        "by-status.md",
        "by-area.md",
        "by-priority.md",
        "recent.md",
        "projects.md",
    }
    status_page = _page(vault, "by-status.md")
    assert "[[TAS-001-consumer|Consume the root.]]" in status_page
    assert "## active (1)" in status_page
    assert "## resolved (1)" in status_page


def test_a_direct_markdown_edit_reaches_the_views(tmp_path: Path, run_tangle: RunTangle) -> None:
    """A hand edit is reflected on the next interaction without an index call."""
    vault = tmp_path / "nodes"
    _seed(vault)
    env = _env(tmp_path, vault)
    assert run_tangle("init", env=env).returncode == 0
    assert run_tangle("frontier", env=env).returncode == 0

    (vault / "active" / "TAS-001-consumer.md").write_text(
        _frontmatter(
            "A revised summary.",
            updated="2026-09-12T00:00:00Z",
            priority="P0",
            next_line="Reconcile the root.",
        )
        + "\nParent [[IDX-001-root]].\n",
        encoding="utf-8",
    )
    assert run_tangle("frontier", env=env).returncode == 0
    assert "A revised summary." in _page(vault, "by-status.md")


def test_views_group_by_priority_and_area(tmp_path: Path, run_tangle: RunTangle) -> None:
    """The priority and area pages group the routed node under its own values."""
    vault = tmp_path / "nodes"
    _seed(vault)
    env = _env(tmp_path, vault)
    assert run_tangle("init", env=env).returncode == 0
    assert run_tangle("frontier", env=env).returncode == 0

    priority_page = _page(vault, "by-priority.md")
    assert "## P0 (1)" in priority_page
    assert "[[TAS-001-consumer|Consume the root.]]" in priority_page

    area_page = _page(vault, "by-area.md")
    assert "## IDX-001-root" in area_page
    assert "## Unassigned" in area_page


def test_an_unchanged_vault_rewrites_no_view(tmp_path: Path, run_tangle: RunTangle) -> None:
    """A second interaction reproduces the pages byte for byte and writes none."""
    vault = tmp_path / "nodes"
    _seed(vault)
    env = _env(tmp_path, vault)
    assert run_tangle("init", env=env).returncode == 0
    assert run_tangle("frontier", env=env).returncode == 0
    before = {
        path.name: (path.read_bytes(), path.stat().st_mtime_ns)
        for path in (vault / "views").iterdir()
    }

    assert run_tangle("frontier", env=env).returncode == 0
    after = {
        path.name: (path.read_bytes(), path.stat().st_mtime_ns)
        for path in (vault / "views").iterdir()
    }
    assert after == before


def test_views_are_never_discovered_as_nodes(tmp_path: Path, run_tangle: RunTangle) -> None:
    """A published page is excluded from discovery and graph validation."""
    vault = tmp_path / "nodes"
    _seed(vault)
    env = _env(tmp_path, vault)
    assert run_tangle("init", env=env).returncode == 0
    assert run_tangle("frontier", env=env).returncode == 0
    assert (vault / "views" / "by-status.md").is_file()

    checked = run_tangle("check", env=env)
    assert checked.returncode == 0, checked.stdout + checked.stderr
    assert "by-status" not in checked.stdout

    frontier = run_tangle("frontier", env=env)
    assert "by-status" not in frontier.stdout


def test_status_reports_stale_then_current_views(tmp_path: Path, run_tangle: RunTangle) -> None:
    """`status` reports a pending projection, then current after upkeep."""
    vault = tmp_path / "nodes"
    _seed(vault)
    env = _env(tmp_path, vault)
    assert run_tangle("init", env=env).returncode == 0
    assert run_tangle("frontier", env=env).returncode == 0

    assert 'views: "current (5)"' in run_tangle("status", env=env).stdout

    (vault / "active" / "TAS-001-consumer.md").write_text(
        _frontmatter(
            "Edited by hand.",
            updated="2026-09-12T00:00:00Z",
            priority="P0",
            next_line="Reconcile the root.",
        )
        + "\nParent [[IDX-001-root]].\n",
        encoding="utf-8",
    )
    # `status` answers before its own upkeep publishes the pending page.
    assert re.search(
        r'views: "stale \(\d+ pending\)"', run_tangle("status", env=env).stdout
    )
    assert 'views: "current (5)"' in run_tangle("status", env=env).stdout


def test_index_republishes_views(tmp_path: Path, run_tangle: RunTangle) -> None:
    """`index` rebuilds derived state and republishes missing pages."""
    vault = tmp_path / "nodes"
    _seed(vault)
    env = _env(tmp_path, vault)
    assert run_tangle("init", env=env).returncode == 0
    assert run_tangle("frontier", env=env).returncode == 0

    for page in (vault / "views").iterdir():
        page.unlink()
    rebuilt = run_tangle("index", env=env)
    assert rebuilt.returncode == 0
    assert 'views: "updated 5"' in rebuilt.stdout
    assert (vault / "views" / "by-status.md").is_file()


def test_a_registered_external_project_is_projected(
    tmp_path: Path, run_tangle: RunTangle
) -> None:
    """A local registry entry appears on the projects page without a fake node."""
    vault = tmp_path / "nodes"
    _seed(vault)
    (vault / "projects.json").write_text(
        json.dumps({"projects": {"hekate": {"uid": _PROJECT_UID, "path": "."}}}),
        encoding="utf-8",
    )
    env = _env(tmp_path, vault)
    assert run_tangle("init", env=env).returncode == 0
    assert run_tangle("frontier", env=env).returncode == 0

    projects = _page(vault, "projects.md")
    assert "## hekate" in projects
    assert _PROJECT_UID in projects
    assert "- local: present" in projects
