"""Behavioral tests for transactional decomposition and the parent-advance shorthand.

``braintree node decompose`` writes an ordered child set and advances the parent
in one operation; a rejected plan and a write failure both leave no half-built
tree. ``braintree node advance`` is the parent-advance-only case.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from braintree import node_record
from braintree.main import main as braintree_main


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _hub(root: Path) -> Path:
    nodes = root / ".braintree"
    (nodes / "active").mkdir(parents=True, exist_ok=True)
    _write(
        nodes / "index-map.md",
        "---\nupdated: 2026-09-14T00:00:00Z\nsummary: Route agents.\n---\n\n"
        "# Root hubs\n\n- Indexes [[IDX-001-root]]\n",
    )
    _write(
        nodes / "resolved" / "IDX-001-root.md",
        "---\ncontext_rev: 1\nupdated: 2026-09-14T00:00:00Z\nsummary: Root hub.\n---\n",
    )
    _write(
        nodes / "active" / "TAS-001-coordinator.md",
        _parent_body("Do the first thing."),
    )
    return nodes


def _parent_body(next_line: str) -> str:
    return (
        "---\n"
        "context_rev: 1\n"
        "updated: 2026-09-14T00:00:00Z\n"
        "summary: Coordinate the work.\n"
        f'next: "{next_line}"\n'
        "---\n\n"
        "Area [[IDX-001-root]].\n\n"
        "# Outcome\n\n"
        "Deliver the whole thing.\n\n"
        "# Done when\n\n"
        "- Every part lands.\n"
    )


def _plan(path: Path, children: object) -> Path:
    _write(path, json.dumps({"children": children}))
    return path


def _child(**overrides: object) -> dict[str, object]:
    child: dict[str, object] = {
        "type": "TAS",
        "summary": "Validate the manifests.",
        "next": "Run the validation.",
        "body": "# Outcome\n\nValidated manifests.\n",
    }
    child.update(overrides)
    return child


def _parent_text(nodes: Path) -> str:
    return (nodes / "active" / "TAS-001-coordinator.md").read_text(encoding="utf-8")


def test_decompose_writes_ordered_children_and_advances_parent(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    nodes = _hub(tmp_path / "consumer")
    plan = _plan(
        tmp_path / "plan.json",
        [_child(**{"slug": "alpha"}), _child(**{"slug": "beta"})],
    )
    assert (
        braintree_main(
            ["node", "decompose", "--parent", "TAS-001", "--plan", str(plan), "--nodes", str(nodes)]
        )
        == 0
    )
    out = capsys.readouterr().out
    assert 'result: "decomposed"' in out
    assert 'next: "TAS-002-alpha"' in out
    first = nodes / "proposed" / "TAS-002-alpha.md"
    second = nodes / "proposed" / "TAS-003-beta.md"
    assert first.is_file() and second.is_file()
    assert "Parent [[TAS-001-coordinator]]." in first.read_text(encoding="utf-8")
    parent = _parent_text(nodes)
    assert 'next: "[[TAS-002-alpha]]"' in parent
    # The parent's acceptance and body are untouched; only next and updated change.
    assert "# Done when" in parent and "Deliver the whole thing." in parent
    assert "updated: 2026-09-14T00:00:00Z" not in parent


def test_decompose_dry_run_writes_and_reserves_nothing(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    nodes = _hub(tmp_path / "consumer")
    plan = _plan(tmp_path / "plan.json", [_child()])
    before = _parent_text(nodes)
    assert (
        braintree_main(
            [
                "node",
                "decompose",
                "--parent",
                "TAS-001",
                "--plan",
                str(plan),
                "--nodes",
                str(nodes),
                "--dry-run",
            ]
        )
        == 0
    )
    out = capsys.readouterr().out
    assert 'result: "dry-run"' in out
    assert "children[1]{type,status,summary}:" in out
    assert not list((nodes / "proposed").glob("*.md"))
    assert not (nodes / "reservations").exists()
    assert _parent_text(nodes) == before


def test_decompose_rejects_an_invalid_plan_before_reserving(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    nodes = _hub(tmp_path / "consumer")
    plan = _plan(tmp_path / "plan.json", [_child(type="BOGUS")])
    assert (
        braintree_main(
            ["node", "decompose", "--parent", "TAS-001", "--plan", str(plan), "--nodes", str(nodes)]
        )
        == 2
    )
    out = capsys.readouterr().out
    assert "child 0 type must be one of" in out
    assert not (nodes / "reservations").exists()
    assert _parent_text(nodes).endswith("# Done when\n\n- Every part lands.\n")


def test_decompose_rejects_an_unknown_child_key(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    nodes = _hub(tmp_path / "consumer")
    plan = _plan(tmp_path / "plan.json", [_child(**{"id": "TAS-099"})])
    assert (
        braintree_main(
            ["node", "decompose", "--parent", "TAS-001", "--plan", str(plan), "--nodes", str(nodes)]
        )
        == 2
    )
    assert "unknown keys: id" in capsys.readouterr().out


def test_decompose_rolls_back_written_children_on_a_write_failure(
    tmp_path: Path, capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    nodes = _hub(tmp_path / "consumer")
    plan = _plan(
        tmp_path / "plan.json",
        [_child(**{"slug": "alpha"}), _child(**{"slug": "beta"})],
    )
    before = _parent_text(nodes)
    real_write = node_record.write_new
    calls = {"count": 0}

    def _fail_second(path: str, content: str) -> bool:
        calls["count"] += 1
        if calls["count"] == 2:
            return False
        return real_write(path, content)

    monkeypatch.setattr(node_record, "write_new", _fail_second)
    assert (
        braintree_main(
            ["node", "decompose", "--parent", "TAS-001", "--plan", str(plan), "--nodes", str(nodes)]
        )
        == 1
    )
    out = capsys.readouterr().out
    assert "node already exists" in out
    assert calls["count"] == 2
    assert not (nodes / "proposed" / "TAS-002-alpha.md").exists()
    assert _parent_text(nodes) == before


def test_decompose_requires_parent_and_plan(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    nodes = _hub(tmp_path / "consumer")
    assert braintree_main(["node", "decompose", "--nodes", str(nodes)]) == 2
    assert "requires --parent and --plan" in capsys.readouterr().out


def test_decompose_unknown_parent_exits_one(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    nodes = _hub(tmp_path / "consumer")
    plan = _plan(tmp_path / "plan.json", [_child()])
    assert (
        braintree_main(
            ["node", "decompose", "--parent", "TAS-999", "--plan", str(plan), "--nodes", str(nodes)]
        )
        == 1
    )
    assert "unknown parent: TAS-999" in capsys.readouterr().out


def test_advance_points_the_parent_at_a_direct_child(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    nodes = _hub(tmp_path / "consumer")
    _write(
        nodes / "proposed" / "TAS-002-child.md",
        "---\ncontext_rev: 1\nupdated: 2026-09-14T00:00:00Z\n"
        "summary: Child work.\nnext: Do it.\n---\n\nParent [[TAS-001-coordinator]].\n",
    )
    assert (
        braintree_main(
            ["node", "advance", "TAS-001", "TAS-002", "--nodes", str(nodes)]
        )
        == 0
    )
    out = capsys.readouterr().out
    assert 'result: "advanced"' in out
    assert 'next: "[[TAS-002-child]]"' in _parent_text(nodes)


def test_advance_refuses_a_non_child(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    nodes = _hub(tmp_path / "consumer")
    _write(
        nodes / "proposed" / "TAS-002-other.md",
        "---\ncontext_rev: 1\nupdated: 2026-09-14T00:00:00Z\n"
        "summary: Other work.\nnext: Do it.\n---\n\nParent [[TAS-099-someone-else]].\n",
    )
    assert (
        braintree_main(
            ["node", "advance", "TAS-001", "TAS-002", "--nodes", str(nodes)]
        )
        == 1
    )
    assert "is not a direct child of TAS-001-coordinator" in capsys.readouterr().out


# --- Derived slug boundaries --------------------------------------------------


def test_slugify_cuts_a_multi_word_summary_at_a_word_boundary() -> None:
    summary = "implement a deliberately long reconnaissance workflow for agents everywhere"
    slug = node_record.slugify(summary, "fallback")
    assert len(slug) <= 48
    assert slug in re.sub(r"[^a-z0-9]+", "-", summary.lower())
    # The cut leaves whole words: neither side of the final hyphen is a fragment.
    words = re.sub(r"[^a-z0-9]+", " ", summary.lower()).split()
    assert slug.split("-") == words[: len(slug.split("-"))]


def test_slugify_clips_a_single_long_word_without_a_boundary() -> None:
    summary = "x" * 80
    slug = node_record.slugify(summary, "fallback")
    assert len(slug) == 48
    assert slug == "x" * 48


def test_slugify_still_falls_back_when_nothing_survives() -> None:
    assert node_record.slugify("!!!", "fallback") == "fallback"
