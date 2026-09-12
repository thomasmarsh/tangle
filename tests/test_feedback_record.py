"""Behavioral tests for the Braintree node capture paths.

The writers are exercised against fixture vaults so they are proven to allocate
an id, discover a route to the root hub, stamp the required frontmatter, and
produce a node that ``graph-check`` accepts: ``feedback-record`` for ``FBK``
and ``node record`` for ``THO``, ``DEF``, ``DEC``, and ``TAS``.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from braintree import __version__, feedback_record, graph_check, node_record, revision
from braintree.main import main as braintree_main


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
    assert "usage: braintree feedback record" in capsys.readouterr().out


def test_record_unknown_option_exits_two(capsys: pytest.CaptureFixture[str]) -> None:
    assert feedback_record.main(["--bogus"]) == 2
    assert "unknown option: --bogus" in capsys.readouterr().out


# The generic capture path: one command creates a routed, stamped node of a
# named type from a summary and body, the way ``feedback record`` does for FBK.

_CAPTURE_BODY = {
    "THO": "# Question\n\nDoes a claim survive a worktree move?",
    "DEF": "# Invariant\n\nThe vault root holds nodes/index-map.md.",
    "DEC": (
        "# Decision\n\nKeep the sidecar derived.\n\n"
        "# Rationale\n\nMarkdown stays authoritative.\n\n"
        "# Consequences\n\nIndex rebuilds stay disposable."
    ),
    "TAS": "# Outcome\n\nReject a lease whose base hash is stale.",
}


_TASK_NEXT = {"--next": "Add the boundary test."}


def _capture_args(nodes: Path, node_type: str, **overrides: str) -> list[str]:
    values = {
        "--nodes": str(nodes),
        "--type": node_type,
        "--summary": f"Capture one {node_type} node.",
        "--body": _CAPTURE_BODY[node_type],
    }
    values.update(overrides)
    args: list[str] = []
    for name, value in values.items():
        args.extend([name, value])
    return args


def test_capture_creates_a_checker_accepted_node_of_each_type(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    nodes = _hub(tmp_path / "consumer")
    assert node_record.main(_capture_args(nodes, "THO")) == 0
    assert node_record.main(_capture_args(nodes, "DEF", **{"--status": "resolved"})) == 0
    assert node_record.main(_capture_args(nodes, "DEC", **{"--status": "resolved"})) == 0
    assert node_record.main(_capture_args(nodes, "TAS", **_TASK_NEXT)) == 0
    out = capsys.readouterr().out
    assert out.count('result: "recorded"') == 4
    assert (nodes / "proposed" / "THO-001-capture-one-tho-node.md").is_file()
    assert (nodes / "proposed" / "TAS-001-capture-one-tas-node.md").is_file()
    assert (nodes / "resolved" / "DEF-001-capture-one-def-node.md").is_file()
    assert (nodes / "resolved" / "DEC-001-capture-one-dec-node.md").is_file()
    assert graph_check.main([str(nodes)]) == 0
    assert "graph check: passed (5 nodes)" in capsys.readouterr().out


def test_capture_is_dispatched_as_one_documented_command(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    nodes = _hub(tmp_path / "consumer")
    assert braintree_main(["node", "record", *_capture_args(nodes, "THO")]) == 0
    assert (nodes / "proposed" / "THO-001-capture-one-tho-node.md").is_file()
    assert graph_check.main([str(nodes)]) == 0
    capsys.readouterr()
    assert braintree_main(["--help"]) == 0
    assert "node record [OPTIONS]" in capsys.readouterr().out


def test_capture_stamps_the_route_revision_and_timestamp(tmp_path: Path) -> None:
    nodes = _hub(tmp_path / "consumer")
    assert node_record.main(_capture_args(nodes, "THO")) == 0
    text = (nodes / "proposed" / "THO-001-capture-one-tho-node.md").read_text(encoding="utf-8")
    assert text.startswith("---\ncontext_rev: 1\n")
    assert re.search(r"^updated: \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z$", text, re.MULTILINE)
    assert "summary: Capture one THO node." in text
    assert "Area [[IDX-001-root]]." in text
    assert "# Question\n\nDoes a claim survive a worktree move?" in text
    assert "next:" not in text


def test_capture_quotes_a_wikilink_next_and_keeps_an_action_next(tmp_path: Path) -> None:
    nodes = _hub(tmp_path / "consumer")
    assert node_record.main(
        _capture_args(nodes, "TAS", **{"--next": "[[TAS-002-validate-manifests]]"})
    ) == 0
    assert node_record.main(_capture_args(nodes, "TAS", **_TASK_NEXT)) == 0
    linked = (nodes / "proposed" / "TAS-001-capture-one-tas-node.md").read_text(encoding="utf-8")
    action = (nodes / "proposed" / "TAS-002-capture-one-tas-node.md").read_text(encoding="utf-8")
    assert 'next: "[[TAS-002-validate-manifests]]"' in linked
    assert "next: Add the boundary test." in action


def test_capture_allocates_the_next_id_from_markdown(tmp_path: Path) -> None:
    nodes = _hub(tmp_path / "consumer")
    (nodes / "proposed").mkdir()
    _write(
        nodes / "proposed" / "TAS-003-old-work.md",
        "---",
        "context_rev: 1",
        "updated: 2026-09-12T00:00:00Z",
        "summary: Old work.",
        "next: Add the boundary test.",
        "---",
        "",
        "Area [[IDX-001-root]].",
    )
    assert node_record.main(_capture_args(nodes, "TAS", **_TASK_NEXT)) == 0
    assert (nodes / "proposed" / "TAS-004-capture-one-tas-node.md").is_file()
    assert not (nodes / "proposed" / "TAS-001-capture-one-tas-node.md").exists()


def test_capture_accepts_an_explicit_id_route_summary_and_slug(tmp_path: Path) -> None:
    nodes = _hub(tmp_path / "consumer")
    assert node_record.main(
        [
            "--nodes",
            str(nodes),
            "--type",
            "TAS",
            "--status",
            "resolved",
            "--id",
            "TAS-042",
            "--route",
            "Parent [[IDX-001-root]]",
            "--summary",
            "Capture the allocation decision.",
            "--slug",
            "allocation-decision",
            "--body",
            _CAPTURE_BODY["TAS"],
        ]
    ) == 0
    node = nodes / "resolved" / "TAS-042-allocation-decision.md"
    text = node.read_text(encoding="utf-8")
    assert "summary: Capture the allocation decision." in text
    assert "Parent [[IDX-001-root]]." in text
    assert graph_check.main([str(nodes)]) == 0


def test_capture_rejects_an_id_of_another_type(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    nodes = _hub(tmp_path / "consumer")
    args = _capture_args(nodes, "THO", **{"--id": "TAS-001"})
    assert node_record.main(args) == 2
    assert "id must look like THO-001" in capsys.readouterr().out


def test_capture_refuses_to_overwrite_an_explicit_id(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    nodes = _hub(tmp_path / "consumer")
    args = _capture_args(nodes, "THO", **{"--id": "THO-001"})
    assert node_record.main(args) == 0
    capsys.readouterr()
    assert node_record.main(args) == 1
    assert "already exists" in capsys.readouterr().out


def test_capture_requires_type_summary_and_body(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    nodes = _hub(tmp_path / "consumer")
    assert node_record.main(["--nodes", str(nodes), "--summary", "s", "--body", "b"]) == 2
    assert "--type must be one of THO, DEF, DEC, TAS" in capsys.readouterr().out
    assert node_record.main(["--nodes", str(nodes), "--type", "THO", "--body", "b"]) == 2
    assert "requires --summary" in capsys.readouterr().out
    assert node_record.main(["--nodes", str(nodes), "--type", "THO", "--summary", "s"]) == 2
    assert "requires --body" in capsys.readouterr().out
    assert not (nodes / "proposed").exists()


def test_capture_names_the_feedback_path_for_fbk(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    nodes = _hub(tmp_path / "consumer")
    args = [
        "--nodes",
        str(nodes),
        "--type",
        "FBK",
        "--summary",
        "Capture one FBK node.",
        "--body",
        "# Feedback\n",
    ]
    assert node_record.main(args) == 2
    out = capsys.readouterr().out
    assert "braintree feedback record" in out
    assert "IDX" in out
    assert not (nodes / "proposed").exists()


def test_capture_requires_next_for_an_unfinished_task(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    nodes = _hub(tmp_path / "consumer")
    assert node_record.main(_capture_args(nodes, "TAS")) == 2
    assert "requires --next" in capsys.readouterr().out
    assert not (nodes / "proposed").exists()


def test_capture_refuses_next_on_a_resolved_node(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    nodes = _hub(tmp_path / "consumer")
    args = _capture_args(nodes, "DEC", **{"--status": "resolved", "--next": "Do it."})
    assert node_record.main(args) == 2
    assert "must omit --next" in capsys.readouterr().out


def test_capture_requires_a_blocked_section_in_a_blocked_body(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    nodes = _hub(tmp_path / "consumer")
    assert node_record.main(_capture_args(nodes, "THO", **{"--status": "blocked"})) == 2
    assert "# Blocked section" in capsys.readouterr().out
    blocked = "# Blocked\n\nBlocked by: an external approval.\nUnblocks when: it lands."
    assert node_record.main(
        _capture_args(nodes, "THO", **{"--status": "blocked", "--body": blocked})
    ) == 0
    assert graph_check.main([str(nodes)]) == 0


def test_capture_rejects_an_unknown_status(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    nodes = _hub(tmp_path / "consumer")
    args = _capture_args(nodes, "THO", **{"--status": "parked"})
    assert node_record.main(args) == 2
    assert "--status must be one of" in capsys.readouterr().out


def test_capture_rejects_a_bad_route(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    nodes = _hub(tmp_path / "consumer")
    args = _capture_args(nodes, "THO", **{"--route": "links to [[IDX-001-root]]"})
    assert node_record.main(args) == 2
    assert "route must be" in capsys.readouterr().out


def test_capture_needs_a_route_without_an_index_map(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    nodes = tmp_path / "bare" / "nodes"
    (nodes / "proposed").mkdir(parents=True)
    assert node_record.main(_capture_args(nodes, "THO")) == 1
    assert "unable to discover a root hub" in capsys.readouterr().out


def test_capture_missing_nodes_directory(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert node_record.main(_capture_args(tmp_path / "absent", "THO")) == 1
    assert "nodes directory does not exist" in capsys.readouterr().out


def test_capture_help_exits_zero(capsys: pytest.CaptureFixture[str]) -> None:
    assert node_record.main(["--help"]) == 0
    assert node_record.main(["-h"]) == 0
    assert "usage: braintree node record" in capsys.readouterr().out


def test_capture_unknown_option_exits_two(capsys: pytest.CaptureFixture[str]) -> None:
    assert node_record.main(["--bogus"]) == 2
    assert "unknown option: --bogus" in capsys.readouterr().out
