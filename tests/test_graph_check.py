"""Behavioral tests for the Python ``graph-check`` validator.

Ported from ``tests/graph-check.sh`` so the validator is verified through the
Python package. Each failure case starts from the same valid fixture and applies the
single mutation the shell test used.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from braintree import graph_check


def _write(path: Path, *lines: str) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _seed(nodes: Path) -> None:
    (nodes / "active").mkdir(parents=True)
    (nodes / "proposed").mkdir()
    (nodes / "resolved").mkdir()
    (nodes / "blocked").mkdir()
    _write(
        nodes / "index-map.md",
        "---",
        "updated: 2026-09-10T00:00:00Z",
        "summary: Route graph work.",
        "---",
        "",
        "# Root hubs",
        "",
        "- Indexes [[IDX-001-root]].",
    )
    _write(
        nodes / "resolved" / "IDX-001-root.md",
        "---",
        "context_rev: 1",
        "updated: 2026-09-10T00:00:00Z",
        "summary: Root hub.",
        "---",
    )
    _write(
        nodes / "resolved" / "DEF-001-contract.md",
        "---",
        "context_rev: 1",
        "updated: 2026-09-10T00:00:00Z",
        "summary: Contract.",
        "---",
        "",
        "Area [[IDX-001-root]].",
    )
    _write(
        nodes / "active" / "TAS-001-parent.md",
        "---",
        "context_rev: 1",
        "updated: 2026-09-10T00:00:00Z",
        "summary: Parent.",
        "next: Continue [[TAS-002-child]].",
        "---",
        "",
        "Area [[IDX-001-root]].",
        "",
        "Depends on [[DEF-001-contract]] at context_rev 1.",
    )
    _write(
        nodes / "active" / "TAS-002-child.md",
        "---",
        "context_rev: 1",
        "updated: 2026-09-10T00:00:00Z",
        "summary: Child.",
        "next: Finish the check.",
        "---",
        "",
        "Parent [[TAS-001-parent]].",
    )


@pytest.fixture
def nodes(tmp_path: Path) -> Path:
    root = tmp_path / "nodes"
    _seed(root)
    return root


def _run(nodes: Path, capsys: pytest.CaptureFixture[str]) -> tuple[int, str]:
    code = graph_check.main([str(nodes)])
    captured = capsys.readouterr()
    return code, captured.err


def _replace(path: Path, old: str, new: str) -> None:
    path.write_text(path.read_text(encoding="utf-8").replace(old, new), encoding="utf-8")


def test_valid_vault_passes(nodes: Path, capsys: pytest.CaptureFixture[str]) -> None:
    assert graph_check.main([str(nodes)]) == 0
    assert "graph check: passed" in capsys.readouterr().out


def test_empty_vault_bootstrap_passes(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    bootstrap = tmp_path / "bootstrap"
    (bootstrap / "active").mkdir(parents=True)
    (bootstrap / "resolved").mkdir()
    _write(
        bootstrap / "index-map.md",
        "---",
        "updated: 2026-09-10T00:00:00Z",
        "summary: Route graph work.",
        "---",
        "",
        "# Root hubs",
        "",
        "- Indexes [[IDX-001-root]].",
    )
    _write(
        bootstrap / "resolved" / "IDX-001-root.md",
        "---",
        "context_rev: 1",
        "updated: 2026-09-10T00:00:00Z",
        "summary: Root hub.",
        "---",
        "",
        "# Invariant",
        "",
        "No Parent or Area route.",
    )
    _write(
        bootstrap / "active" / "TAS-001-first-action.md",
        "---",
        "context_rev: 1",
        "updated: 2026-09-10T00:00:00Z",
        "summary: First actionable node.",
        "next: Perform the first action.",
        "---",
        "",
        "Area [[IDX-001-root]].",
    )
    assert graph_check.main([str(bootstrap)]) == 0
    assert "graph check: passed" in capsys.readouterr().out


def test_duplicate_node_identity(nodes: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source = nodes / "active" / "TAS-001-parent.md"
    (nodes / "blocked" / "TAS-001-copy.md").write_text(
        source.read_text(encoding="utf-8"), encoding="utf-8"
    )
    code, err = _run(nodes, capsys)
    assert code == 1
    assert "duplicate node identity: TAS-001" in err


def test_broken_link(nodes: Path, capsys: pytest.CaptureFixture[str]) -> None:
    child = nodes / "active" / "TAS-002-child.md"
    child.write_text(
        child.read_text(encoding="utf-8") + "Related to [[TAS-999-missing]].\n",
        encoding="utf-8",
    )
    code, err = _run(nodes, capsys)
    assert code == 1
    assert "broken link [[TAS-999-missing]]" in err


def test_unfinished_task_requires_next(nodes: Path, capsys: pytest.CaptureFixture[str]) -> None:
    child = nodes / "active" / "TAS-002-child.md"
    child.write_text(
        "".join(
            line
            for line in child.read_text(encoding="utf-8").splitlines(keepends=True)
            if not line.startswith("next:")
        ),
        encoding="utf-8",
    )
    code, err = _run(nodes, capsys)
    assert code == 1
    assert "unfinished task requires next" in err


def test_non_task_type_requires_next(
    nodes: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(
        nodes / "active" / "BUG-001-defect.md",
        "---",
        "context_rev: 1",
        "updated: 2026-09-10T00:00:00Z",
        "summary: Defect.",
        "---",
        "",
        "Area [[IDX-001-root]].",
    )
    code, err = _run(nodes, capsys)
    assert code == 1
    assert "unfinished task requires next" in err


def test_blocked_node_requires_blocked_section(
    nodes: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(
        nodes / "blocked" / "TAS-003-waiting.md",
        "---",
        "context_rev: 1",
        "updated: 2026-09-10T00:00:00Z",
        "summary: Waiting.",
        "---",
        "",
        "Area [[IDX-001-root]].",
    )
    code, err = _run(nodes, capsys)
    assert code == 1
    assert "blocked node requires a # Blocked section" in err


def test_blocked_section_satisfies_contract(
    nodes: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(
        nodes / "blocked" / "TAS-003-waiting.md",
        "---",
        "context_rev: 1",
        "updated: 2026-09-10T00:00:00Z",
        "summary: Waiting.",
        "---",
        "",
        "Area [[IDX-001-root]].",
        "",
        "# Blocked",
        "",
        "Blocked by the owner decision. Unblocks when the owner selects a rule.",
    )
    assert graph_check.main([str(nodes)]) == 0
    assert "graph check: passed" in capsys.readouterr().out


def test_invalid_disposition(nodes: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _write(
        nodes / "resolved" / "TAS-003-done.md",
        "---",
        "context_rev: 1",
        "updated: 2026-09-10T00:00:00Z",
        "summary: Done.",
        "disposition: current",
        "---",
        "",
        "Area [[IDX-001-root]].",
    )
    code, err = _run(nodes, capsys)
    assert code == 1
    assert "disposition must be abandoned, deprecated, or superseded" in err


def test_disposition_requires_resolved(
    nodes: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(
        nodes / "active" / "TAS-003-current.md",
        "---",
        "context_rev: 1",
        "updated: 2026-09-10T00:00:00Z",
        "summary: Current.",
        "next: Continue.",
        "disposition: abandoned",
        "---",
        "",
        "Area [[IDX-001-root]].",
    )
    code, err = _run(nodes, capsys)
    assert code == 1
    assert "disposition requires a resolved node" in err


def test_context_rev_mismatch(nodes: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _replace(nodes / "active" / "TAS-001-parent.md", "context_rev 1.", "context_rev 2.")
    code, err = _run(nodes, capsys)
    assert code == 1
    assert "context_rev mismatch" in err


def test_missing_context_rev_pin(nodes: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _replace(nodes / "active" / "TAS-001-parent.md", " at context_rev 1.", ".")
    code, err = _run(nodes, capsys)
    assert code == 1
    assert "invalid or missing context_rev pin" in err


def test_context_pin_with_trailing_text_names_it(
    nodes: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _replace(
        nodes / "active" / "TAS-001-parent.md",
        " at context_rev 1.",
        " at context_rev 1. and more context.",
    )
    code, err = _run(nodes, capsys)
    assert code == 1
    assert "context_rev pin for [[DEF-001-contract]] has trailing text: and more context." in err


def test_stored_reciprocal_edge(nodes: Path, capsys: pytest.CaptureFixture[str]) -> None:
    parent = nodes / "active" / "TAS-001-parent.md"
    parent.write_text(
        parent.read_text(encoding="utf-8") + "Child [[TAS-002-child]].\n",
        encoding="utf-8",
    )
    code, err = _run(nodes, capsys)
    assert code == 1
    assert "stored reciprocal edge" in err


def test_orphan_unfinished_node(nodes: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _replace(
        nodes / "active" / "TAS-002-child.md",
        "Parent [[TAS-001-parent]].",
        "Parent [[TAS-777-missing]].",
    )
    code, err = _run(nodes, capsys)
    assert code == 1
    assert "orphan unfinished node" in err


def test_parent_cycle(nodes: Path, capsys: pytest.CaptureFixture[str]) -> None:
    _replace(
        nodes / "active" / "TAS-002-child.md",
        "Parent [[TAS-001-parent]].",
        "Parent [[TAS-002-child]].",
    )
    code, err = _run(nodes, capsys)
    assert code == 1
    assert "parent cycle" in err


def test_allow_stale_suppresses_mismatch(
    nodes: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _replace(nodes / "active" / "TAS-001-parent.md", "context_rev 1.", "context_rev 2.")
    assert graph_check.main(["--allow-stale", str(nodes)]) == 0
    assert "graph check: passed" in capsys.readouterr().out


def test_allow_stale_still_rejects_missing_pin(
    nodes: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _replace(nodes / "active" / "TAS-001-parent.md", " at context_rev 1.", ".")
    assert graph_check.main(["--allow-stale", str(nodes)]) == 1
    assert "invalid or missing context_rev pin" in capsys.readouterr().err


def test_pinned_dependency_not_resolved(
    nodes: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = nodes / "resolved" / "DEF-001-contract.md"
    source.rename(nodes / "proposed" / source.name)
    code, err = _run(nodes, capsys)
    assert code == 1
    assert "pinned dependency [[DEF-001-contract]] is proposed, not resolved" in err


def test_allow_stale_still_rejects_unresolved_pin(
    nodes: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = nodes / "resolved" / "DEF-001-contract.md"
    source.rename(nodes / "proposed" / source.name)
    assert graph_check.main(["--allow-stale", str(nodes)]) == 1
    err = capsys.readouterr().err
    assert "pinned dependency [[DEF-001-contract]] is proposed, not resolved" in err


def test_allow_orphan_suppresses_orphan(
    nodes: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(
        nodes / "active" / "TAS-003-orphan.md",
        "---",
        "context_rev: 1",
        "updated: 2026-09-10T00:00:00Z",
        "summary: Orphan.",
        "next: Finish the check.",
        "---",
    )
    code, err = _run(nodes, capsys)
    assert code == 1
    assert "orphan unfinished node" in err
    assert graph_check.main(["--allow-orphan", "TAS-003-orphan", str(nodes)]) == 0
    assert "graph check: passed" in capsys.readouterr().out


def test_help_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    assert graph_check.main(["--help"]) == 0
    assert graph_check.main(["-h"]) == 0
    assert "usage: graph-check" in capsys.readouterr().out


def test_unknown_option_exits_one(capsys: pytest.CaptureFixture[str]) -> None:
    assert graph_check.main(["--bogus"]) == 1
    assert "error: unknown option" in capsys.readouterr().err


def test_extra_argument_exits_two(capsys: pytest.CaptureFixture[str]) -> None:
    assert graph_check.main(["nodes", "extra"]) == 2
    assert "usage: graph-check" in capsys.readouterr().out


def test_missing_directory_exits_one(capsys: pytest.CaptureFixture[str]) -> None:
    assert graph_check.main(["does-not-exist"]) == 1
    assert "nodes directory does not exist: does-not-exist" in capsys.readouterr().err


def _feedback_node(revision: str | None, *body: str) -> list[str]:
    lines = [
        "---",
        "context_rev: 1",
        "updated: 2026-09-12T00:00:00Z",
        "summary: Allocation collided with nodes on disk.",
    ]
    if revision is not None:
        lines.append(f"braintree_revision: {revision}")
    lines += ["---", "", "Area [[IDX-001-root]].", ""]
    lines += list(body)
    return lines


def test_feedback_node_valid(
    nodes: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(
        nodes / "proposed" / "FBK-001-allocation-friction.md",
        *_feedback_node(
            "0.4.0+g1b58d57",
            "# Feedback",
            "",
            "Attempted: Ran bt allocate after a reindex.",
            "Friction: The allocated id already existed on disk.",
            "Improvement: Seed allocation from the Markdown maximum.",
        ),
    )
    assert graph_check.main([str(nodes)]) == 0
    assert "graph check: passed" in capsys.readouterr().out


def test_feedback_node_unknown_revision_is_valid(
    nodes: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(
        nodes / "proposed" / "FBK-002-unknown-revision.md",
        *_feedback_node(
            "unknown",
            "# Feedback",
            "",
            "Attempted: Installed the skill.",
            "Friction: No revision record existed.",
            "Improvement: Record the revision at install time.",
        ),
    )
    assert graph_check.main([str(nodes)]) == 0


def test_feedback_node_requires_revision(
    nodes: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(
        nodes / "proposed" / "FBK-003-missing-revision.md",
        *_feedback_node(
            None,
            "# Feedback",
            "",
            "Attempted: Installed the skill.",
            "Friction: No revision record existed.",
            "Improvement: Record the revision at install time.",
        ),
    )
    code, err = _run(nodes, capsys)
    assert code == 1
    assert "feedback node requires braintree_revision" in err


def test_feedback_node_rejects_malformed_revision(
    nodes: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(
        nodes / "proposed" / "FBK-004-malformed-revision.md",
        *_feedback_node(
            "latest",
            "# Feedback",
            "",
            "Attempted: Installed the skill.",
            "Friction: No revision record existed.",
            "Improvement: Record the revision at install time.",
        ),
    )
    code, err = _run(nodes, capsys)
    assert code == 1
    assert "braintree_revision must be a version like 0.4.0+g1b58d57 or unknown" in err


def test_feedback_node_requires_content(
    nodes: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(
        nodes / "proposed" / "FBK-005-missing-friction.md",
        *_feedback_node(
            "0.4.0",
            "# Feedback",
            "",
            "Attempted: Ran bt allocate.",
            "Improvement: Seed allocation from the Markdown maximum.",
        ),
    )
    code, err = _run(nodes, capsys)
    assert code == 1
    assert "feedback node requires a Friction: line in # Feedback" in err


def test_feedback_node_requires_section(
    nodes: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(
        nodes / "proposed" / "FBK-006-missing-section.md",
        *_feedback_node("0.4.0", "# Context", "", "No feedback body."),
    )
    code, err = _run(nodes, capsys)
    assert code == 1
    assert "feedback node requires a # Feedback section" in err
