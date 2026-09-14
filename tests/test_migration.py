"""Behavioral tests for the legacy-to-stationary compatibility migration."""

from __future__ import annotations

import re
import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

from braintree import graph_check, migration, store

RunBt = Callable[..., subprocess.CompletedProcess[str]]

_INDEX = (
    "---\n"
    "updated: 2026-01-01T00:00:00Z\n"
    "summary: Route graph work.\n"
    "---\n"
    "\n"
    "# Root hubs\n"
    "\n"
    "- Indexes [[IDX-001-root]].\n"
)
_HUB = (
    "---\n"
    "context_rev: 1\n"
    "updated: 2026-01-01T00:00:00Z\n"
    "summary: Root hub.\n"
    "---\n"
    "\n"
    "# Outcome\n"
    "\n"
    "Root.\n"
)
_PROPOSED = (
    "---\n"
    "context_rev: 3\n"
    "priority: P1\n"
    "updated: 2026-09-10T01:30:00Z\n"
    "summary: Fix the thing.\n"
    "next: Add the failing boundary test.\n"
    "---\n"
    "\n"
    "Area [[IDX-001-root]].\n"
    "\n"
    "# Outcome\n"
    "\n"
    "Fix it.\n"
)
_RESOLVED_TASK = (
    "---\n"
    "context_rev: 2\n"
    "updated: 2026-09-10T01:30:00Z\n"
    "summary: Finish the older work.\n"
    "---\n"
    "\n"
    "Area [[IDX-001-root]].\n"
    "\n"
    "# Outcome\n"
    "\n"
    "Done.\n"
)
_QUESTION = (
    "---\n"
    "context_rev: 1\n"
    "updated: 2026-09-10T01:30:00Z\n"
    "summary: Open question.\n"
    "---\n"
    "\n"
    "Area [[IDX-001-root]].\n"
    "\n"
    "# Question\n"
    "\n"
    "Why?\n"
)
_UPDATED = re.compile(r"^updated: (\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z)$", re.MULTILINE)


def _vault(root: Path) -> Path:
    """Seed a minimal valid legacy status-directory vault and return it."""
    nodes = root / ".braintree"
    (nodes / "proposed").mkdir(parents=True)
    (nodes / "resolved").mkdir()
    (nodes / "index-map.md").write_text(_INDEX, encoding="utf-8")
    (nodes / "resolved" / "IDX-001-root.md").write_text(_HUB, encoding="utf-8")
    (nodes / "proposed" / "TAS-001-fix-the-thing.md").write_text(
        _PROPOSED, encoding="utf-8"
    )
    (nodes / "resolved" / "TAS-003-finish-the-older-work.md").write_text(
        _RESOLVED_TASK, encoding="utf-8"
    )
    (nodes / "resolved" / "THO-002-open-question.md").write_text(
        _QUESTION, encoding="utf-8"
    )
    return nodes


def _legacy_files(nodes: Path) -> list[Path]:
    return sorted(
        path
        for entry in store.iter_node_paths(str(nodes))
        if not entry.stationary
        for path in [Path(entry.path)]
    )


def _stationary_files(nodes: Path) -> list[Path]:
    return sorted(
        Path(entry.path)
        for entry in store.iter_node_paths(str(nodes))
        if entry.stationary
    )


def test_plan_lists_every_legacy_node_beside_its_canonical_target(tmp_path: Path) -> None:
    nodes = _vault(tmp_path)

    planned = migration.plan(str(nodes))

    assert planned.is_empty is False
    assert [(node.node_id, node.status) for node in planned.nodes] == [
        ("TAS-001", "proposed"),
        ("IDX-001", "resolved"),
        ("TAS-003", "resolved"),
        ("THO-002", "resolved"),
    ]
    for node in planned.nodes:
        assert node.target == str(
            nodes
            / store.CANONICAL_DIRECTORY
            / node.node_id[-2:]
            / Path(node.source).name
        )


def test_apply_moves_nodes_and_stamps_authoritative_status(tmp_path: Path) -> None:
    nodes = _vault(tmp_path)
    original_updated = _UPDATED.search(_PROPOSED)
    assert original_updated is not None

    result = migration.apply(migration.plan(str(nodes)))

    assert result.moved == 4
    assert result.project_uid.startswith("prj-")
    assert _legacy_files(nodes) == []
    assert len(_stationary_files(nodes)) == 4
    moved = nodes / store.CANONICAL_DIRECTORY / "01" / "TAS-001-fix-the-thing.md"
    text = moved.read_text(encoding="utf-8")
    assert "status: proposed" in text
    assert "context_rev: 3" in text
    assert "priority: P1" in text
    assert text.count("status:") == 1
    refreshed = _UPDATED.search(text)
    assert refreshed is not None
    assert refreshed.group(1) != original_updated.group(1)
    assert graph_check.findings(str(nodes)) == []
    assert migration.plan(str(nodes)).is_empty is True


def test_apply_preserves_an_existing_frontmatter_status(tmp_path: Path) -> None:
    nodes = _vault(tmp_path)
    source = nodes / "proposed" / "TAS-001-fix-the-thing.md"
    source.write_text(
        _PROPOSED.replace("context_rev: 3", "status: proposed\ncontext_rev: 3"),
        encoding="utf-8",
    )

    migration.apply(migration.plan(str(nodes)))

    moved = nodes / store.CANONICAL_DIRECTORY / "01" / "TAS-001-fix-the-thing.md"
    assert moved.read_text(encoding="utf-8").count("status:") == 1


def test_plan_rejects_a_collision_before_writing_anything(tmp_path: Path) -> None:
    nodes = _vault(tmp_path)
    target = nodes / store.CANONICAL_DIRECTORY / "01" / "TAS-001-fix-the-thing.md"
    target.parent.mkdir(parents=True)
    target.write_text("occupied", encoding="utf-8")

    with pytest.raises(migration.MigrationError, match="already exists"):
        migration.plan(str(nodes))
    assert target.read_text(encoding="utf-8") == "occupied"


def test_plan_rejects_two_nodes_that_share_one_identity(tmp_path: Path) -> None:
    nodes = _vault(tmp_path)
    (nodes / "resolved" / "TAS-001-fix-the-thing.md").write_text(
        _RESOLVED_TASK, encoding="utf-8"
    )

    with pytest.raises(migration.MigrationError, match="duplicate node identity"):
        migration.plan(str(nodes))


def test_case_only_rename_stages_through_an_intermediate_path(tmp_path: Path) -> None:
    source = tmp_path / "TAS-001-node.md"
    target = tmp_path / "tas-001-node.md"
    source.write_text("old", encoding="utf-8")

    migration.case_safe_move(str(source), str(target), "new")

    assert target.read_text(encoding="utf-8") == "new"
    assert sorted(path.name for path in tmp_path.iterdir()) == ["tas-001-node.md"]
    assert not (tmp_path / "TAS-001-node.md.case-migrating").exists()


def test_failed_apply_restores_every_source(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    nodes = _vault(tmp_path)
    planned = migration.plan(str(nodes))
    real = migration.case_safe_move
    calls = {"count": 0}

    def flaky(source: str, target: str, text: str) -> None:
        calls["count"] += 1
        if calls["count"] == 2:
            raise OSError("simulated failure")
        real(source, target, text)

    monkeypatch.setattr(migration, "case_safe_move", flaky)

    with pytest.raises(OSError):
        migration.apply(planned)

    assert calls["count"] == 2
    for node in planned.nodes:
        assert Path(node.source).is_file()
    assert _stationary_files(nodes) == []


def test_stationarize_plans_by_default_and_applies_on_request(
    tmp_path: Path, run_bt: RunBt
) -> None:
    nodes = _vault(tmp_path)
    env = {"BT_PROJECT_ID": "migration-test", "BT_SIDECAR_DIR": str(tmp_path / "state")}

    planned = run_bt("stationarize", cwd=tmp_path, env=env)
    assert planned.returncode == 0
    assert 'result: "planned"' in planned.stdout
    assert 'moves[4]{id,status,source,target}:' in planned.stdout
    assert _stationary_files(nodes) == []

    applied = run_bt("stationarize", "--apply", cwd=tmp_path, env=env)
    assert applied.returncode == 0
    assert 'result: "migrated"' in applied.stdout
    assert 'moved: "4"' in applied.stdout
    assert len(_stationary_files(nodes)) == 4

    no_op = run_bt("stationarize", cwd=tmp_path, env=env)
    assert no_op.returncode == 0
    assert 'result: "no-op"' in no_op.stdout
