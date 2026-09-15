"""Behavioral tests for the opt-in reconnaissance read surface.

``tangle node NODE`` keeps its exact output; only
``tangle node references NODE`` expands the non-pinned ``Informed by``
relation. These tests prove the expansion is deterministic, one hop, and
explicit about a missing target.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from tangle import index
from tangle.main import main as tangle_main


def _write(path: Path, *lines: str) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _hub(root: Path) -> Path:
    nodes = root / ".tangle"
    for status in ("resolved", "proposed"):
        (nodes / status).mkdir(parents=True, exist_ok=True)
    _write(
        nodes / "index-map.md",
        "---",
        "updated: 2026-09-14T00:00:00Z",
        "summary: Route agents.",
        "---",
        "",
        "# Root hubs",
        "",
        "- Indexes [[IDX-001-root]]",
    )
    _write(
        nodes / "resolved" / "IDX-001-root.md",
        "---",
        "context_rev: 1",
        "updated: 2026-09-14T00:00:00Z",
        "summary: Root hub.",
        "---",
    )
    return nodes


def _knowledge(nodes: Path, name: str, *body: str) -> None:
    _write(
        nodes / "resolved" / name,
        "---",
        "context_rev: 1",
        "updated: 2026-09-14T00:00:00Z",
        "summary: Reconnaissance.",
        "---",
        "",
        *body,
    )


def _consumer(nodes: Path, *context: str) -> None:
    _write(
        nodes / "proposed" / "TAS-001-consumer.md",
        "---",
        "context_rev: 1",
        "updated: 2026-09-14T00:00:00Z",
        "summary: Consume the reconnaissance.",
        "next: Do the work.",
        "---",
        "",
        "Area [[IDX-001-root]].",
        "",
        "# Context",
        "",
        *context,
    )


def _reference(target: str) -> str:
    return f"Informed by [[{target}]]."


@pytest.fixture
def nodes(tmp_path: Path) -> Path:
    root = _hub(tmp_path / "consumer")
    _knowledge(root, "THO-002-beta.md", "Area [[IDX-001-root]].")
    _knowledge(root, "THO-001-alpha.md", "Area [[IDX-001-root]].")
    _consumer(root, _reference("THO-002-beta"), _reference("THO-001-alpha"))
    return root


def test_node_references_lists_direct_reconnaissance(
    nodes: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("TANGLE_NODES_DIR", str(nodes))
    assert tangle_main(["node", "references", "TAS-001-consumer"]) == 0
    out = capsys.readouterr().out
    assert 'node: "TAS-001"' in out
    assert 'name: "TAS-001-consumer"' in out
    assert 'route: "IDX-001-root"' in out
    assert "references[2]{id,status,context_rev,summary}:" in out
    # Rows are ordered by target name, so the answer is stable across reindexes.
    assert out.index('"THO-001"') < out.index('"THO-002"')


def test_plain_node_output_omits_the_expansion(
    nodes: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("TANGLE_NODES_DIR", str(nodes))
    assert tangle_main(["node", "TAS-001-consumer"]) == 0
    out = capsys.readouterr().out
    assert "references" not in out
    assert "context_edges" in out


def test_missing_target_is_reported_not_dropped(
    nodes: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _consumer(nodes, _reference("THO-999-missing"))
    monkeypatch.setenv("TANGLE_NODES_DIR", str(nodes))
    assert tangle_main(["node", "references", "TAS-001-consumer"]) == 0
    out = capsys.readouterr().out
    assert '"THO-999-missing","missing","0",""' in out


def test_expansion_is_one_hop_so_a_cycle_terminates(
    nodes: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # A reference cycle between two reconnaissance nodes stays one hop from the
    # consumer: each referenced node is reported, and neither is expanded again.
    _knowledge(
        nodes,
        "THO-002-beta.md",
        "Area [[IDX-001-root]].",
        "",
        _reference("THO-003-gamma"),
    )
    _knowledge(
        nodes,
        "THO-003-gamma.md",
        "Area [[IDX-001-root]].",
        "",
        _reference("THO-002-beta"),
    )
    _consumer(nodes, _reference("THO-002-beta"), _reference("THO-003-gamma"))
    monkeypatch.setenv("TANGLE_NODES_DIR", str(nodes))
    assert tangle_main(["node", "references", "TAS-001-consumer"]) == 0
    out = capsys.readouterr().out
    assert "references[2]{id,status,context_rev,summary}:" in out
    # The referenced nodes' own references are never followed.
    assert '"THO-002"' in out and '"THO-003"' in out


def test_repeated_reference_collapses_to_one_row(
    nodes: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _consumer(nodes, _reference("THO-001-alpha"), _reference("THO-001-alpha"))
    monkeypatch.setenv("TANGLE_NODES_DIR", str(nodes))
    view = index.reference_view(str(nodes), "TAS-001-consumer")
    assert view is not None
    assert [item.name for item in view.references] == ["THO-001-alpha"]


def test_no_references_prints_the_zero_line(
    nodes: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    _consumer(nodes, "No reconnaissance yet.")
    monkeypatch.setenv("TANGLE_NODES_DIR", str(nodes))
    assert tangle_main(["node", "references", "TAS-001-consumer"]) == 0
    assert "references: 0 references" in capsys.readouterr().out


def test_unknown_node_is_reported(
    nodes: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("TANGLE_NODES_DIR", str(nodes))
    assert tangle_main(["node", "references", "TAS-999"]) == 1
    assert "unknown node: TAS-999" in capsys.readouterr().out


def test_missing_operand_is_a_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert tangle_main(["node", "references"]) == 2
    assert "node references requires NODE" in capsys.readouterr().out


def test_node_references_help(capsys: pytest.CaptureFixture[str]) -> None:
    assert tangle_main(["node", "references", "--help"]) == 0
    out = capsys.readouterr().out
    assert "one hop" in out
    assert "exits[3]{code,meaning}:" in out
