"""Behavioral tests for the Python ``graph-check`` validator.

Ported from ``tests/graph-check.sh`` so the validator is verified through the
Python package. Each failure case starts from the same valid fixture and applies the
single mutation the shell test used.
"""

from __future__ import annotations

import re
import shutil
from collections.abc import Callable
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
        'next: "[[TAS-002-child]]"',
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


def _resolve_child(nodes: Path) -> None:
    """Resolve the active child in place, dropping its now-invalid next."""
    child = nodes / "active" / "TAS-002-child.md"
    child.write_text(
        "".join(
            line
            for line in child.read_text(encoding="utf-8").splitlines(keepends=True)
            if not line.startswith("next:")
        ),
        encoding="utf-8",
    )
    child.rename(nodes / "resolved" / child.name)


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


def test_inline_code_span_hides_a_link_shaped_token(
    nodes: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    child = nodes / "active" / "TAS-002-child.md"
    child.write_text(
        child.read_text(encoding="utf-8")
        + "The grammar is `[[TAS-999-missing]]` and the contract is [[DEF-001-contract]].\n",
        encoding="utf-8",
    )
    assert graph_check.main([str(nodes)]) == 0
    assert "graph check: passed" in capsys.readouterr().out


@pytest.mark.parametrize("fence", ["```", "~~~"])
def test_fenced_code_block_hides_a_link_shaped_token(
    nodes: Path, capsys: pytest.CaptureFixture[str], fence: str
) -> None:
    child = nodes / "active" / "TAS-002-child.md"
    child.write_text(
        child.read_text(encoding="utf-8")
        + f"{fence}markdown\nThe grammar is [[TAS-999-missing]].\n{fence}\n",
        encoding="utf-8",
    )
    assert graph_check.main([str(nodes)]) == 0
    assert "graph check: passed" in capsys.readouterr().out


def test_real_link_beside_quoted_tokens_still_fails(
    nodes: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    child = nodes / "active" / "TAS-002-child.md"
    child.write_text(
        child.read_text(encoding="utf-8")
        + "The grammar is `[[TAS-999-missing]]`.\n"
        + "```markdown\n[[TAS-998-missing]]\n```\n"
        + "Related to [[TAS-997-missing]].\n",
        encoding="utf-8",
    )
    code, err = _run(nodes, capsys)
    assert code == 1
    assert "broken link [[TAS-997-missing]]" in err
    assert "TAS-999-missing" not in err
    assert "TAS-998-missing" not in err


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


def test_next_naming_a_resolved_child_is_flagged(
    nodes: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An unfinished coordinator whose route names a resolved child is stale."""
    _resolve_child(nodes)
    code, err = _run(nodes, capsys)
    assert code == 1
    assert "next frontier [[TAS-002-child]] is already resolved" in err


def test_action_next_beside_a_resolved_child_passes(
    nodes: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A coordinator's action next is not a stale route, resolved child or not."""
    _resolve_child(nodes)
    _replace(
        nodes / "active" / "TAS-001-parent.md",
        'next: "[[TAS-002-child]]"',
        "next: Audit the resolved child outcome.",
    )
    assert graph_check.main([str(nodes)]) == 0
    assert "graph check: passed" in capsys.readouterr().out


def test_action_sentence_next_containing_a_wikilink_names_the_token(
    nodes: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An action-sentence next carries no wikilink; the checker names the token.

    The embedded link resolves to a live direct child, so only the
    action-sentence rule makes this a finding; the diagnostic must name the
    token rather than leave it to be found by trial.
    """
    _replace(
        nodes / "active" / "TAS-001-parent.md",
        'next: "[[TAS-002-child]]"',
        "next: Move this node to resolved once [[TAS-002-child]] closes.",
    )
    code, err = _run(nodes, capsys)
    assert code == 1
    assert "action-sentence next contains a wikilink: [[TAS-002-child]]" in err


def test_non_child_route_names_the_offending_token(
    nodes: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A lone route link that is not a direct child is named in the finding."""
    _replace(
        nodes / "active" / "TAS-001-parent.md",
        'next: "[[TAS-002-child]]"',
        'next: "[[DEF-001-contract]]"',
    )
    code, err = _run(nodes, capsys)
    assert code == 1
    assert "next frontier [[DEF-001-contract]] is not a direct child" in err


def test_node_without_children_is_not_a_stale_route(
    nodes: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(
        nodes / "active" / "TAS-003-leaf.md",
        "---",
        "context_rev: 1",
        "updated: 2026-09-10T00:00:00Z",
        "summary: Leaf work.",
        "next: Finish the leaf action.",
        "---",
        "",
        "Area [[IDX-001-root]].",
    )
    assert graph_check.main([str(nodes)]) == 0
    assert "graph check: passed" in capsys.readouterr().out


def test_blocked_action_next_is_not_a_stale_route(
    nodes: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _write(
        nodes / "blocked" / "TAS-003-waiting.md",
        "---",
        "context_rev: 1",
        "updated: 2026-09-10T00:00:00Z",
        "summary: Waiting.",
        "next: Request the vendor fixture.",
        "---",
        "",
        "Area [[IDX-001-root]].",
        "",
        "# Blocked",
        "",
        "Blocked by the vendor. Unblocks when the fixture arrives.",
    )
    assert graph_check.main([str(nodes)]) == 0
    assert "graph check: passed" in capsys.readouterr().out


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
    # The target is resolved, so the gate form does not apply and is not named.
    assert graph_check.GATED_RELATION not in err


def test_missing_pin_to_unresolved_target_names_the_gated_form(
    nodes: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """An unpinned edge to a not-yet-resolved target names the sanctioned gate."""
    source = nodes / "resolved" / "DEF-001-contract.md"
    source.rename(nodes / "proposed" / source.name)
    _replace(nodes / "active" / "TAS-001-parent.md", " at context_rev 1.", ".")
    code, err = _run(nodes, capsys)
    assert code == 1
    assert (
        "invalid or missing context_rev pin for [[DEF-001-contract]]; "
        "a not-yet-resolved predecessor is recorded as Gated on "
        "[[DEF-001-contract]]." in err
    )


def test_gated_dependency_on_unresolved_predecessor_passes(
    nodes: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A gate records a dependency on a not-yet-resolved target without a pin."""
    source = nodes / "resolved" / "DEF-001-contract.md"
    source.rename(nodes / "proposed" / source.name)
    _replace(
        nodes / "active" / "TAS-001-parent.md",
        "Depends on [[DEF-001-contract]] at context_rev 1.",
        f"{graph_check.GATED_RELATION} [[DEF-001-contract]].",
    )
    assert graph_check.main([str(nodes)]) == 0
    assert "graph check: passed" in capsys.readouterr().out


@pytest.mark.parametrize("relation", graph_check.CONTEXT_RELATIONS)
def test_each_context_relation_requires_a_pin(
    nodes: Path, capsys: pytest.CaptureFixture[str], relation: str
) -> None:
    parent = nodes / "active" / "TAS-001-parent.md"
    parent.write_text(
        parent.read_text(encoding="utf-8")
        + f"{relation} [[DEF-001-contract]].\n",
        encoding="utf-8",
    )
    code, err = _run(nodes, capsys)
    assert code == 1
    assert "invalid or missing context_rev pin for [[DEF-001-contract]]" in err


def test_non_context_relation_is_not_pinned(
    nodes: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    parent = nodes / "active" / "TAS-001-parent.md"
    parent.write_text(
        parent.read_text(encoding="utf-8")
        + "Related to [[DEF-001-contract]].\n",
        encoding="utf-8",
    )
    assert graph_check.main([str(nodes)]) == 0
    assert "graph check: passed" in capsys.readouterr().out


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
    assert (
        "a not-yet-resolved predecessor is recorded as Gated on "
        "[[DEF-001-contract]]." in err
    )


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
    assert "usage: braintree check" in capsys.readouterr().out


def test_help_names_the_pending_advance_sanction(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert graph_check.main(["--help"]) == 0
    assert "--allow-pending-advance NODE" in capsys.readouterr().out


def test_pending_advance_sanction_covers_the_multi_writer_transient(
    nodes: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """A declared pending advance is the transient, not a failed slice."""
    _mut_next_resolved_node(nodes)
    assert graph_check.main(["--format", "toon", str(nodes)]) == 1
    assert "next-resolved-node" in _toon_codes(capsys.readouterr().out)
    assert graph_check.main(["--allow-pending-advance", "TAS-001-parent", str(nodes)]) == 0
    assert "graph check: passed" in capsys.readouterr().out


def test_pending_advance_sanction_accepts_the_bare_parent_id(
    nodes: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _mut_next_resolved_node(nodes)
    assert graph_check.main(["--allow-pending-advance", "TAS-001", str(nodes)]) == 0
    assert "graph check: passed" in capsys.readouterr().out


def test_pending_advance_sanction_is_scoped_to_the_named_parent(
    nodes: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Naming another node leaves the genuine stale route failing."""
    _mut_next_resolved_node(nodes)
    assert (
        graph_check.main(
            ["--allow-pending-advance", "TAS-002-child", "--format", "toon", str(nodes)]
        )
        == 1
    )
    assert "next-resolved-node" in _toon_codes(capsys.readouterr().out)


def test_pending_advance_sanction_relaxes_nothing_else(
    nodes: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """The sanction covers the pending advance and no other finding."""
    _mut_next_resolved_node(nodes)
    _mut_context_rev_mismatch(nodes)
    assert (
        graph_check.main(
            [
                "--allow-pending-advance",
                "TAS-001-parent",
                "--format",
                "toon",
                str(nodes),
            ]
        )
        == 1
    )
    assert _toon_codes(capsys.readouterr().out) == ["context-rev-mismatch"]


def test_unknown_option_exits_one(capsys: pytest.CaptureFixture[str]) -> None:
    assert graph_check.main(["--bogus"]) == 1
    assert "error: unknown option" in capsys.readouterr().err


def test_extra_argument_exits_two(capsys: pytest.CaptureFixture[str]) -> None:
    assert graph_check.main(["nodes", "extra"]) == 2
    assert "usage: braintree check" in capsys.readouterr().out


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


# --- Structured ``--format toon`` output and stable finding codes ----------------


def _toon_codes(out: str) -> list[str]:
    """Return the leading ``code`` cell of every emitted TOON record."""
    codes: list[str] = []
    for line in out.splitlines():
        match = re.match(r'\s+"([^"]+)"', line)
        if match is not None:
            codes.append(match.group(1))
    return codes


def _mut_vault_no_nodes(nodes: Path) -> None:
    for path in sorted(nodes.glob("*/*.md")):
        path.unlink()


def _mut_vault_missing_directory(nodes: Path) -> None:
    shutil.rmtree(nodes)


def _mut_node_status_directory(nodes: Path) -> None:
    (nodes / "weird").mkdir()
    _write(
        nodes / "weird" / "TAS-010-weird.md",
        "---",
        "context_rev: 1",
        "updated: 2026-09-10T00:00:00Z",
        "summary: Weird status.",
        "next: Continue.",
        "---",
    )


def _mut_node_frontmatter_missing(nodes: Path) -> None:
    _write(nodes / "active" / "TAS-010-bare.md", "No frontmatter here.")


def _mut_node_frontmatter_mapping(nodes: Path) -> None:
    _write(nodes / "active" / "TAS-010-bad.md", "---", "not a mapping", "---")


def _mut_node_context_rev(nodes: Path) -> None:
    _write(
        nodes / "active" / "TAS-010-bad-rev.md",
        "---",
        "context_rev: 0",
        "updated: 2026-09-10T00:00:00Z",
        "summary: Bad revision.",
        "next: Continue.",
        "---",
        "",
        "Area [[IDX-001-root]].",
    )


def _mut_node_updated(nodes: Path) -> None:
    _write(
        nodes / "active" / "TAS-010-bad-updated.md",
        "---",
        "context_rev: 1",
        "updated: yesterday",
        "summary: Bad timestamp.",
        "next: Continue.",
        "---",
        "",
        "Area [[IDX-001-root]].",
    )


def _mut_node_summary(nodes: Path) -> None:
    _write(
        nodes / "active" / "TAS-010-no-summary.md",
        "---",
        "context_rev: 1",
        "updated: 2026-09-10T00:00:00Z",
        "next: Continue.",
        "---",
        "",
        "Area [[IDX-001-root]].",
    )


def _mut_node_authority_fields(nodes: Path) -> None:
    _write(
        nodes / "active" / "TAS-010-authority.md",
        "---",
        "context_rev: 1",
        "updated: 2026-09-10T00:00:00Z",
        "summary: Duplicated authority.",
        "next: Continue.",
        "status: active",
        "---",
        "",
        "Area [[IDX-001-root]].",
    )


def _mut_node_next_required(nodes: Path) -> None:
    child = nodes / "active" / "TAS-002-child.md"
    child.write_text(
        "".join(
            line
            for line in child.read_text(encoding="utf-8").splitlines(keepends=True)
            if not line.startswith("next:")
        ),
        encoding="utf-8",
    )


def _mut_node_blocked_section(nodes: Path) -> None:
    _write(
        nodes / "blocked" / "TAS-010-waiting.md",
        "---",
        "context_rev: 1",
        "updated: 2026-09-10T00:00:00Z",
        "summary: Waiting.",
        "---",
        "",
        "Area [[IDX-001-root]].",
    )


def _mut_node_disposition(nodes: Path) -> None:
    _write(
        nodes / "resolved" / "TAS-010-disposition.md",
        "---",
        "context_rev: 1",
        "updated: 2026-09-10T00:00:00Z",
        "summary: Disposition.",
        "disposition: current",
        "---",
        "",
        "Area [[IDX-001-root]].",
    )


def _mut_node_disposition_status(nodes: Path) -> None:
    _write(
        nodes / "active" / "TAS-010-disposition.md",
        "---",
        "context_rev: 1",
        "updated: 2026-09-10T00:00:00Z",
        "summary: Disposition too early.",
        "next: Continue.",
        "disposition: abandoned",
        "---",
        "",
        "Area [[IDX-001-root]].",
    )


def _mut_node_resolved_next(nodes: Path) -> None:
    _write(
        nodes / "resolved" / "TAS-010-done.md",
        "---",
        "context_rev: 1",
        "updated: 2026-09-10T00:00:00Z",
        "summary: Done but unsettled.",
        "next: Keep going.",
        "---",
        "",
        "Area [[IDX-001-root]].",
    )


def _mut_node_reciprocal_edge(nodes: Path) -> None:
    parent = nodes / "active" / "TAS-001-parent.md"
    parent.write_text(
        parent.read_text(encoding="utf-8") + "Child [[TAS-002-child]].\n",
        encoding="utf-8",
    )


def _mut_node_duplicate_identity(nodes: Path) -> None:
    source = nodes / "active" / "TAS-001-parent.md"
    (nodes / "blocked" / "TAS-001-copy.md").write_text(
        source.read_text(encoding="utf-8"), encoding="utf-8"
    )


def _mut_node_broken_link(nodes: Path) -> None:
    child = nodes / "active" / "TAS-002-child.md"
    child.write_text(
        child.read_text(encoding="utf-8") + "Related to [[TAS-999-missing]].\n",
        encoding="utf-8",
    )


def _mut_feedback_revision_missing(nodes: Path) -> None:
    _write(
        nodes / "proposed" / "FBK-010-missing.md",
        *_feedback_node(
            None,
            "# Feedback",
            "",
            "Attempted: a.",
            "Friction: b.",
            "Improvement: c.",
        ),
    )


def _mut_feedback_revision_format(nodes: Path) -> None:
    _write(
        nodes / "proposed" / "FBK-010-malformed.md",
        *_feedback_node(
            "latest",
            "# Feedback",
            "",
            "Attempted: a.",
            "Friction: b.",
            "Improvement: c.",
        ),
    )


def _mut_feedback_section_missing(nodes: Path) -> None:
    _write(
        nodes / "proposed" / "FBK-010-no-section.md",
        *_feedback_node("0.4.0", "# Context", "", "No feedback body."),
    )


def _mut_feedback_content_missing(nodes: Path) -> None:
    _write(
        nodes / "proposed" / "FBK-010-no-friction.md",
        *_feedback_node(
            "0.4.0",
            "# Feedback",
            "",
            "Attempted: a.",
            "Improvement: c.",
        ),
    )


def _mut_context_pin_trailing_text(nodes: Path) -> None:
    _replace(
        nodes / "active" / "TAS-001-parent.md",
        " at context_rev 1.",
        " at context_rev 1. and more.",
    )


def _mut_context_pin_missing(nodes: Path) -> None:
    _replace(nodes / "active" / "TAS-001-parent.md", " at context_rev 1.", ".")


def _mut_context_unresolved(nodes: Path) -> None:
    source = nodes / "resolved" / "DEF-001-contract.md"
    source.rename(nodes / "proposed" / source.name)


def _mut_context_rev_mismatch(nodes: Path) -> None:
    _replace(nodes / "active" / "TAS-001-parent.md", "context_rev 1.", "context_rev 2.")


def _mut_index_missing(nodes: Path) -> None:
    (nodes / "index-map.md").unlink()


def _mut_index_copied_state(nodes: Path) -> None:
    index = nodes / "index-map.md"
    index.write_text(
        index.read_text(encoding="utf-8") + "| [[TAS-002-child]] | active |\n",
        encoding="utf-8",
    )


def _mut_index_root_route_missing(nodes: Path) -> None:
    _replace(nodes / "index-map.md", "- Indexes [[IDX-001-root]].\n", "")


def _mut_index_root_hub_type(nodes: Path) -> None:
    _replace(
        nodes / "index-map.md",
        "- Indexes [[IDX-001-root]].",
        "- Indexes [[DEF-001-contract]].",
    )


def _mut_index_broken_link(nodes: Path) -> None:
    index = nodes / "index-map.md"
    index.write_text(
        index.read_text(encoding="utf-8") + "\n- [[TAS-999-missing]].\n",
        encoding="utf-8",
    )


def _mut_index_focus_without_active(nodes: Path) -> None:
    (nodes / "active" / "TAS-001-parent.md").rename(
        nodes / "resolved" / "TAS-001-parent.md"
    )
    (nodes / "active" / "TAS-002-child.md").rename(
        nodes / "resolved" / "TAS-002-child.md"
    )
    index = nodes / "index-map.md"
    index.write_text(
        index.read_text(encoding="utf-8")
        + "\n# Focus\n\n- [[TAS-002-child]]\n",
        encoding="utf-8",
    )


def _mut_index_focus_target(nodes: Path) -> None:
    index = nodes / "index-map.md"
    index.write_text(
        index.read_text(encoding="utf-8")
        + "\n# Focus\n\n- [[DEF-001-contract]]\n",
        encoding="utf-8",
    )


def _mut_route_root_hub_unrouted(nodes: Path) -> None:
    hub = nodes / "resolved" / "IDX-001-root.md"
    hub.write_text(
        hub.read_text(encoding="utf-8") + "\nArea [[IDX-001-root]].\n",
        encoding="utf-8",
    )


def _mut_route_primary_missing(nodes: Path) -> None:
    _write(
        nodes / "active" / "TAS-010-unrouted.md",
        "---",
        "context_rev: 1",
        "updated: 2026-09-10T00:00:00Z",
        "summary: No route.",
        "next: Continue.",
        "---",
    )


def _mut_route_cycle(nodes: Path) -> None:
    _replace(
        nodes / "active" / "TAS-002-child.md",
        "Parent [[TAS-001-parent]].",
        "Parent [[TAS-002-child]].",
    )


def _mut_route_orphan(nodes: Path) -> None:
    _replace(
        nodes / "active" / "TAS-002-child.md",
        "Parent [[TAS-001-parent]].",
        "Parent [[TAS-777-missing]].",
    )


def _mut_next_multiple_frontiers(nodes: Path) -> None:
    _replace(
        nodes / "active" / "TAS-001-parent.md",
        'next: "[[TAS-002-child]]"',
        "next: Continue [[TAS-002-child]] and [[DEF-001-contract]].",
    )


def _mut_next_action_wikilink(nodes: Path) -> None:
    _replace(
        nodes / "active" / "TAS-001-parent.md",
        'next: "[[TAS-002-child]]"',
        "next: Move this node to resolved once [[TAS-002-child]] closes.",
    )


def _mut_next_not_direct_child(nodes: Path) -> None:
    _replace(
        nodes / "active" / "TAS-001-parent.md",
        'next: "[[TAS-002-child]]"',
        'next: "[[DEF-001-contract]]"',
    )


def _mut_next_resolved_node(nodes: Path) -> None:
    _resolve_child(nodes)


# Every error class the validator can raise, with one mutation that triggers it.
_MUTATIONS: dict[str, tuple[Callable[[Path], None], str]] = {
    "vault-no-nodes": (_mut_vault_no_nodes, "vault-no-nodes"),
    "vault-missing-directory": (_mut_vault_missing_directory, "vault-missing-directory"),
    "node-status-directory": (_mut_node_status_directory, "node-status-directory"),
    "node-frontmatter-missing": (_mut_node_frontmatter_missing, "node-frontmatter-missing"),
    "node-frontmatter-mapping": (_mut_node_frontmatter_mapping, "node-frontmatter-mapping"),
    "node-context-rev": (_mut_node_context_rev, "node-context-rev"),
    "node-updated": (_mut_node_updated, "node-updated"),
    "node-summary": (_mut_node_summary, "node-summary"),
    "node-authority-fields": (_mut_node_authority_fields, "node-authority-fields"),
    "node-next-required": (_mut_node_next_required, "node-next-required"),
    "node-blocked-section": (_mut_node_blocked_section, "node-blocked-section"),
    "node-disposition": (_mut_node_disposition, "node-disposition"),
    "node-disposition-status": (_mut_node_disposition_status, "node-disposition-status"),
    "node-resolved-next": (_mut_node_resolved_next, "node-resolved-next"),
    "node-reciprocal-edge": (_mut_node_reciprocal_edge, "node-reciprocal-edge"),
    "node-duplicate-identity": (_mut_node_duplicate_identity, "node-duplicate-identity"),
    "node-broken-link": (_mut_node_broken_link, "node-broken-link"),
    "feedback-revision-missing": (
        _mut_feedback_revision_missing,
        "feedback-revision-missing",
    ),
    "feedback-revision-format": (
        _mut_feedback_revision_format,
        "feedback-revision-format",
    ),
    "feedback-section-missing": (
        _mut_feedback_section_missing,
        "feedback-section-missing",
    ),
    "feedback-content-missing": (
        _mut_feedback_content_missing,
        "feedback-content-missing",
    ),
    "context-pin-trailing-text": (
        _mut_context_pin_trailing_text,
        "context-pin-trailing-text",
    ),
    "context-pin-missing": (_mut_context_pin_missing, "context-pin-missing"),
    "context-unresolved": (_mut_context_unresolved, "context-unresolved"),
    "context-rev-mismatch": (_mut_context_rev_mismatch, "context-rev-mismatch"),
    "index-missing": (_mut_index_missing, "index-missing"),
    "index-copied-state": (_mut_index_copied_state, "index-copied-state"),
    "index-root-route-missing": (
        _mut_index_root_route_missing,
        "index-root-route-missing",
    ),
    "index-root-hub-type": (_mut_index_root_hub_type, "index-root-hub-type"),
    "index-broken-link": (_mut_index_broken_link, "index-broken-link"),
    "index-focus-without-active": (
        _mut_index_focus_without_active,
        "index-focus-without-active",
    ),
    "index-focus-target": (_mut_index_focus_target, "index-focus-target"),
    "route-root-hub-unrouted": (
        _mut_route_root_hub_unrouted,
        "route-root-hub-unrouted",
    ),
    "route-primary-missing": (_mut_route_primary_missing, "route-primary-missing"),
    "route-cycle": (_mut_route_cycle, "route-cycle"),
    "route-orphan": (_mut_route_orphan, "route-orphan"),
    "next-multiple-frontiers": (
        _mut_next_multiple_frontiers,
        "next-multiple-frontiers",
    ),
    "next-action-wikilink": (_mut_next_action_wikilink, "next-action-wikilink"),
    "next-not-direct-child": (_mut_next_not_direct_child, "next-not-direct-child"),
    "next-resolved-node": (_mut_next_resolved_node, "next-resolved-node"),
}


def test_toon_format_passes_with_zero_findings(
    nodes: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert graph_check.main(["--format", "toon", str(nodes)]) == 0
    out = capsys.readouterr().out
    assert 'result: "passed"' in out
    assert 'nodes: "4"' in out
    assert "findings: 0" in out


def test_toon_format_emits_a_record_per_finding(
    nodes: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _mut_context_rev_mismatch(nodes)
    assert graph_check.main(["--format", "toon", str(nodes)]) == 1
    out = capsys.readouterr().out
    assert 'result: "failed"' in out
    assert "findings[1]{code,node,detail}:" in out
    assert '"context-rev-mismatch"' in out
    assert str(nodes / "active" / "TAS-001-parent.md") in out
    assert "context_rev mismatch" in out


def test_toon_finding_carries_all_three_fields(
    nodes: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _mut_node_broken_link(nodes)
    assert graph_check.main(["--format", "toon", str(nodes)]) == 1
    out = capsys.readouterr().out
    assert "node-broken-link" in _toon_codes(out)
    assert '"node-broken-link","' in out
    assert "broken link [[TAS-999-missing]]" in out


def test_text_format_is_the_default(
    nodes: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert graph_check.main([str(nodes)]) == 0
    default_out = capsys.readouterr().out
    assert graph_check.main(["--format", "text", str(nodes)]) == 0
    assert capsys.readouterr().out == default_out


def test_unknown_format_exits_one(capsys: pytest.CaptureFixture[str]) -> None:
    assert graph_check.main(["--format", "json", "nodes"]) == 1
    assert "unknown format: json" in capsys.readouterr().err


def test_format_requires_a_value(capsys: pytest.CaptureFixture[str]) -> None:
    assert graph_check.main(["--format"]) == 1
    assert "--format requires text or toon" in capsys.readouterr().err


@pytest.mark.parametrize("name", sorted(_MUTATIONS))
def test_every_error_class_emits_a_documented_code(
    nodes: Path, capsys: pytest.CaptureFixture[str], name: str
) -> None:
    mutate, expected = _MUTATIONS[name]
    mutate(nodes)
    assert graph_check.main(["--format", "toon", str(nodes)]) == 1
    out = capsys.readouterr().out
    emitted = _toon_codes(out)
    assert expected in emitted
    assert set(emitted) <= set(graph_check.FINDING_CODES)


def test_documented_codes_cover_every_error_class() -> None:
    covered = {expected for _mutate, expected in _MUTATIONS.values()}
    assert covered == set(graph_check.FINDING_CODES)
