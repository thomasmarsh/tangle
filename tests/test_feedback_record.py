"""Behavioral tests for the ``feedback-record`` writer.

The writer is exercised against fixture vaults so it is proven to allocate an
``FBK`` id, discover a route to the root hub, stamp the Braintree revision, and
produce a node that ``graph-check`` accepts.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from braintree import __version__, feedback_record, graph_check, revision


def _write(path: Path, *lines: str) -> None:
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _hub(root: Path) -> Path:
    nodes = root / "nodes"
    (nodes / "resolved").mkdir(parents=True, exist_ok=True)
    _write(
        nodes / "index-map.md",
        "---",
        "updated: 2026-09-12T00:00:00Z",
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
        "updated: 2026-09-12T00:00:00Z",
        "summary: Root hub.",
        "---",
    )
    return nodes


_CONTENT = (
    "Ran bt allocate after a reindex.",
    "The allocated id already existed on disk.",
    "Seed allocation from the Markdown maximum.",
)


def test_record_writes_a_routed_revision_stamped_node(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    nodes = _hub(tmp_path / "consumer")
    assert (
        feedback_record.main(
            [
                "--nodes",
                str(nodes),
                "--attempted",
                _CONTENT[0],
                "--friction",
                _CONTENT[1],
                "--improvement",
                _CONTENT[2],
            ]
        )
        == 0
    )
    out = capsys.readouterr().out
    assert 'result: "recorded"' in out
    assert 'id: "FBK-001"' in out
    node = nodes / "proposed" / "FBK-001-the-allocated-id-already-existed-on-disk.md"
    assert node.is_file()
    text = node.read_text(encoding="utf-8")
    assert "context_rev: 1" in text
    assert "Area [[IDX-001-root]]." in text
    assert f"braintree_revision: {__version__}+unknown" in text
    assert "Attempted: Ran bt allocate after a reindex." in text
    assert "Friction: The allocated id already existed on disk." in text
    assert "Improvement: Seed allocation from the Markdown maximum." in text


def test_recorded_node_passes_graph_check(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    nodes = _hub(tmp_path / "consumer")
    assert (
        feedback_record.main(
            [
                "--nodes",
                str(nodes),
                "--attempted",
                _CONTENT[0],
                "--friction",
                _CONTENT[1],
                "--improvement",
                _CONTENT[2],
            ]
        )
        == 0
    )
    capsys.readouterr()
    assert graph_check.main([str(nodes)]) == 0
    assert "graph check: passed (2 nodes)" in capsys.readouterr().out


def test_record_uses_the_installed_revision_record(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    nodes = _hub(tmp_path / "consumer")
    record = tmp_path / "installed-revision"
    record.write_text("0.4.0+g1b58d57\n", encoding="utf-8")
    monkeypatch.setattr(revision, "_record_path", lambda: record)
    assert (
        feedback_record.main(
            [
                "--nodes",
                str(nodes),
                "--attempted",
                _CONTENT[0],
                "--friction",
                _CONTENT[1],
                "--improvement",
                _CONTENT[2],
            ]
        )
        == 0
    )
    node = nodes / "proposed" / "FBK-001-the-allocated-id-already-existed-on-disk.md"
    assert "braintree_revision: 0.4.0+g1b58d57" in node.read_text(encoding="utf-8")


def test_record_accepts_explicit_id_route_summary_and_slug(
    tmp_path: Path,
) -> None:
    nodes = _hub(tmp_path / "consumer")
    assert (
        feedback_record.main(
            [
                "--nodes",
                str(nodes),
                "--id",
                "FBK-042",
                "--route",
                "Parent [[IDX-001-root]]",
                "--summary",
                "Allocation collided with nodes on disk.",
                "--slug",
                "allocation-friction",
                "--attempted",
                _CONTENT[0],
                "--friction",
                _CONTENT[1],
                "--improvement",
                _CONTENT[2],
            ]
        )
        == 0
    )
    node = nodes / "proposed" / "FBK-042-allocation-friction.md"
    assert node.is_file()
    text = node.read_text(encoding="utf-8")
    assert "summary: Allocation collided with nodes on disk." in text
    assert "Parent [[IDX-001-root]]." in text


def test_record_allocates_the_next_id(tmp_path: Path) -> None:
    nodes = _hub(tmp_path / "consumer")
    (nodes / "proposed").mkdir()
    _write(
        nodes / "proposed" / "FBK-003-old-note.md",
        "---",
        "context_rev: 1",
        "updated: 2026-09-12T00:00:00Z",
        "summary: Old note.",
        "braintree_revision: unknown",
        "---",
        "",
        "Area [[IDX-001-root]].",
        "",
        "# Feedback",
        "",
        "Attempted: one.",
        "Friction: two.",
        "Improvement: three.",
    )
    assert (
        feedback_record.main(
            [
                "--nodes",
                str(nodes),
                "--attempted",
                _CONTENT[0],
                "--friction",
                _CONTENT[1],
                "--improvement",
                _CONTENT[2],
            ]
        )
        == 0
    )
    assert (nodes / "proposed" / "FBK-004-the-allocated-id-already-existed-on-disk.md").is_file()


def test_record_requires_all_three_content_lines(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    nodes = _hub(tmp_path / "consumer")
    assert feedback_record.main(["--nodes", str(nodes), "--attempted", "x", "--friction", "y"]) == 2
    out = capsys.readouterr().out
    assert "--improvement" in out
    assert not (nodes / "proposed").exists()


def test_record_rejects_a_bad_route(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    nodes = _hub(tmp_path / "consumer")
    assert (
        feedback_record.main(
            [
                "--nodes",
                str(nodes),
                "--route",
                "links to [[IDX-001-root]]",
                "--attempted",
                _CONTENT[0],
                "--friction",
                _CONTENT[1],
                "--improvement",
                _CONTENT[2],
            ]
        )
        == 2
    )
    assert "route must be" in capsys.readouterr().out


def test_record_needs_a_route_without_an_index_map(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    nodes = tmp_path / "bare" / "nodes"
    (nodes / "proposed").mkdir(parents=True)
    assert (
        feedback_record.main(
            [
                "--nodes",
                str(nodes),
                "--attempted",
                _CONTENT[0],
                "--friction",
                _CONTENT[1],
                "--improvement",
                _CONTENT[2],
            ]
        )
        == 1
    )
    assert "unable to discover a root hub" in capsys.readouterr().out


def test_record_refuses_to_overwrite_an_explicit_id(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    nodes = _hub(tmp_path / "consumer")
    args = [
        "--nodes",
        str(nodes),
        "--id",
        "FBK-001",
        "--attempted",
        _CONTENT[0],
        "--friction",
        _CONTENT[1],
        "--improvement",
        _CONTENT[2],
    ]
    assert feedback_record.main(args) == 0
    capsys.readouterr()
    assert feedback_record.main(args) == 1
    assert "already exists" in capsys.readouterr().out


def test_record_missing_nodes_directory(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert (
        feedback_record.main(
            [
                "--nodes",
                str(tmp_path / "absent"),
                "--attempted",
                _CONTENT[0],
                "--friction",
                _CONTENT[1],
                "--improvement",
                _CONTENT[2],
            ]
        )
        == 1
    )
    assert "nodes directory does not exist" in capsys.readouterr().out


def test_record_help_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    assert feedback_record.main(["--help"]) == 0
    assert feedback_record.main(["-h"]) == 0
    assert "usage: feedback-record" in capsys.readouterr().out


def test_record_unknown_option_exits_two(capsys: pytest.CaptureFixture[str]) -> None:
    assert feedback_record.main(["--bogus"]) == 2
    assert "unknown option: --bogus" in capsys.readouterr().out
