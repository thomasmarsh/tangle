"""Behavioral tests for the Tangle node capture paths.

The writers are exercised against fixture vaults so they are proven to allocate
an id, discover a route to the root hub, stamp the required frontmatter, and
produce a node that ``graph-check`` accepts: ``feedback-record`` for ``FBK``
and ``node record`` for ``THO``, ``DEF``, ``DEC``, and ``TAS``.
"""

from __future__ import annotations

import re
import threading
from pathlib import Path

import pytest

from tangle import __version__, feedback_record, graph_check, node_record, revision
from tangle.main import main as tangle_main


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
    "Ran tangle allocate after a reindex.",
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
    assert re.search(r'id: "fbk-[0-7][0-9a-hjkmnp-tv-z]{25}"', out)
    node = _recorded(nodes, "FBK", "the-allocated-id-already-existed-on-disk")
    assert node.is_file()
    text = node.read_text(encoding="utf-8")
    assert "context_rev: 1" in text
    assert "Area [[IDX-001-root]]." in text
    assert f"tangle_revision: {__version__}+unknown" in text
    assert "Attempted: Ran tangle allocate after a reindex." in text
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


def test_capture_announces_a_legacy_vault_migration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """A legacy ``nodes/`` root is migrated in place and the move is announced.

    The capture path resolves the vault itself, so writing from a root that
    still holds a legacy vault renames it. The operator must see the move, and
    the reported ``path`` must name the resolved ``.tangle`` directory.
    """
    root = tmp_path / "consumer"
    _hub(root)
    monkeypatch.delenv("TANGLE_NODES_DIR", raising=False)
    # Pin the sidecar to an absent location so the capture reserves its id
    # vault-locally instead of touching any sidecar on this machine.
    monkeypatch.setenv("TANGLE_SIDECAR_DIR", str(tmp_path / "absent-sidecar"))
    monkeypatch.setenv("TANGLE_PROJECT_ID", "legacy-vault-migration")
    monkeypatch.chdir(root)

    assert (
        feedback_record.main(
            [
                "--route",
                "Area [[IDX-001-root]]",
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

    captured = capsys.readouterr()
    assert captured.err == "migrated vault: nodes -> .tangle\n"
    assert not (root / "nodes").exists()
    node = _recorded(Path.cwd() / ".tangle", "FBK", "the-allocated-id-already-existed-on-disk")
    assert f'path: "{node}"' in captured.out
    assert "/nodes/proposed" not in captured.out


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
    node = _recorded(nodes, "FBK", "the-allocated-id-already-existed-on-disk")
    assert "tangle_revision: 0.4.0+g1b58d57" in node.read_text(encoding="utf-8")


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
                "fbk-0123456789abcdefghjkmnpqrs",
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
    node = _recorded(nodes, "FBK", "allocation-friction")
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
        "tangle_revision: unknown",
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
    assert _recorded(nodes, "FBK", "the-allocated-id-already-existed-on-disk").is_file()


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
        "fbk-0123456789abcdefghjkmnpqrs",
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
    assert "usage: tangle feedback record" in capsys.readouterr().out


def test_record_unknown_option_exits_two(capsys: pytest.CaptureFixture[str]) -> None:
    assert feedback_record.main(["--bogus"]) == 2
    assert "unknown option: --bogus" in capsys.readouterr().out


# The generic capture path: one command creates a routed, stamped node of a
# named type from a summary and body, the way ``feedback record`` does for FBK.

_CAPTURE_BODY = {
    "THO": "# Question\n\nDoes a claim survive a worktree move?",
    "DEF": "# Invariant\n\nThe vault root holds .tangle/index-map.md.",
    "DEC": (
        "# Decision\n\nKeep the sidecar derived.\n\n"
        "# Rationale\n\nMarkdown stays authoritative.\n\n"
        "# Consequences\n\nIndex rebuilds stay disposable."
    ),
    "TAS": "# Outcome\n\nReject a lease whose base hash is stale.",
}


_TASK_NEXT = {"--next": "Add the boundary test."}


def _recorded(nodes: Path, node_type: str, slug: str) -> Path:
    matches = list((nodes / "canonical").rglob(f"{node_type.lower()}-*-{slug}.md"))
    assert len(matches) == 1
    return matches[0]


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
    assert _recorded(nodes, "THO", "capture-one-tho-node").is_file()
    assert _recorded(nodes, "TAS", "capture-one-tas-node").is_file()
    assert _recorded(nodes, "DEF", "capture-one-def-node").is_file()
    assert _recorded(nodes, "DEC", "capture-one-dec-node").is_file()
    assert graph_check.main([str(nodes)]) == 0
    assert "graph check: passed (5 nodes)" in capsys.readouterr().out


def test_capture_is_dispatched_as_one_documented_command(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    nodes = _hub(tmp_path / "consumer")
    assert tangle_main(["node", "record", *_capture_args(nodes, "THO")]) == 0
    assert _recorded(nodes, "THO", "capture-one-tho-node").is_file()
    assert graph_check.main([str(nodes)]) == 0
    capsys.readouterr()
    assert tangle_main(["--help"]) == 0
    assert "node record [OPTIONS]" in capsys.readouterr().out


def test_capture_stamps_the_route_revision_and_timestamp(tmp_path: Path) -> None:
    nodes = _hub(tmp_path / "consumer")
    assert node_record.main(_capture_args(nodes, "THO")) == 0
    text = _recorded(nodes, "THO", "capture-one-tho-node").read_text(encoding="utf-8")
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
    recorded = list((nodes / "canonical").rglob("tas-*-capture-one-tas-node.md"))
    assert len(recorded) == 2
    texts = [path.read_text(encoding="utf-8") for path in recorded]
    linked = next(text for text in texts if 'next: "[[' in text)
    action = next(text for text in texts if "next: Add" in text)
    assert 'next: "[[TAS-002-validate-manifests]]"' in linked
    assert "next: Add the boundary test." in action


# The capture paths reserve the automatically chosen id before writing, so two
# parallel callers with different slugs cannot both claim the same number. With
# no sidecar this falls back to a vault-local exclusive-create reservation.
def test_concurrent_capture_with_different_slugs_never_duplicates_an_id(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    nodes = _hub(tmp_path / "consumer")
    # Pin the sidecar to an absent location so the test exercises the portable
    # vault-local reservation instead of any sidecar on the machine.
    monkeypatch.setenv("TANGLE_SIDECAR_DIR", str(tmp_path / "absent-sidecar"))
    monkeypatch.setenv("TANGLE_PROJECT_ID", "capture-concurrency")
    workers = 8
    ready = threading.Barrier(workers)
    codes: list[int] = []
    lock = threading.Lock()

    def capture(index: int) -> None:
        ready.wait(timeout=30)
        code = node_record.main(
            _capture_args(
                nodes,
                "TAS",
                **{"--slug": f"worker-{index}", "--next": "Add the boundary test."},
            )
        )
        with lock:
            codes.append(code)

    threads = [threading.Thread(target=capture, args=(index,)) for index in range(workers)]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join(timeout=30)

    assert codes == [0] * workers
    recorded = sorted((nodes / "canonical").rglob("tas-*.md"))
    assert len(recorded) == workers
    identities = [path.name.split("-", 2)[1] for path in recorded]
    assert len(set(identities)) == workers
    # Cryptographic identities need no shared numeric reservation state.
    assert not (nodes / "reservations").exists()
    assert graph_check.main([str(nodes)]) == 0


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
    assert _recorded(nodes, "TAS", "capture-one-tas-node").is_file()


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
            "tas-0123456789abcdefghjkmnpqrs",
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
    node = _recorded(nodes, "TAS", "allocation-decision")
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
    assert "canonical tho identity" in capsys.readouterr().out


def test_capture_refuses_to_overwrite_an_explicit_id(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    nodes = _hub(tmp_path / "consumer")
    args = _capture_args(nodes, "THO", **{"--id": "tho-0123456789abcdefghjkmnpqrs"})
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
    assert "tangle feedback record" in out
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
    assert "usage: tangle node record" in capsys.readouterr().out


def test_capture_unknown_option_exits_two(capsys: pytest.CaptureFixture[str]) -> None:
    assert node_record.main(["--bogus"]) == 2
    assert "unknown option: --bogus" in capsys.readouterr().out


# A capture summary is one line of at most 96 characters. An over-long value is
# cut on a word boundary with a trailing ellipsis and reported as a warning, so
# neither capture path silently stores a mid-phrase summary.

_ELLIPSIS = "..."


def _summary_of(path: Path) -> str:
    match = re.search(r"^summary: (.*)$", path.read_text(encoding="utf-8"), re.MULTILINE)
    assert match is not None, path
    return match.group(1)


def _summary_at_limit(limit: int) -> str:
    """Return a word-separated summary of exactly ``limit`` characters."""
    words = "alpha bravo charlie delta echo foxtrot golf hotel india".split()
    padding = limit - len(" ".join(words)) - 1
    assert padding >= 2
    words.append("p" * padding)
    text = " ".join(words)
    assert len(text) == limit
    return text


# The phrase the round-seven probe stored cut in half: ``...so that a truncation
# becomes`` is exactly what the word-boundary cut must never produce.
_LONG_SUMMARY = (
    "Record a summary that is deliberately made much longer than the limit so "
    "that a truncation becomes visible in the stored frontmatter"
)


def test_summary_limit_is_the_documented_96_characters() -> None:
    assert node_record.SUMMARY_LIMIT == 96


def test_capture_stores_a_summary_at_the_limit_without_a_warning(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    nodes = _hub(tmp_path / "consumer")
    summary = _summary_at_limit(node_record.SUMMARY_LIMIT)
    args = _capture_args(nodes, "THO", **{"--summary": summary, "--slug": "at-limit"})
    assert node_record.main(args) == 0
    out = capsys.readouterr().out
    assert _summary_of(_recorded(nodes, "THO", "at-limit")) == summary
    assert "warning" not in out
    assert "..." not in summary


def test_capture_cuts_one_character_over_the_limit_on_a_word_boundary(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    nodes = _hub(tmp_path / "consumer")
    summary = _summary_at_limit(node_record.SUMMARY_LIMIT) + "!"
    assert len(summary) == node_record.SUMMARY_LIMIT + 1
    args = _capture_args(nodes, "THO", **{"--summary": summary, "--slug": "over-limit"})
    assert node_record.main(args) == 0
    capsys.readouterr()
    stored = _summary_of(_recorded(nodes, "THO", "over-limit"))
    assert len(stored) <= node_record.SUMMARY_LIMIT
    assert stored.endswith(_ELLIPSIS)
    head = stored[: -len(_ELLIPSIS)]
    assert summary.startswith(head)
    assert summary[len(head)] == " "


def test_capture_never_stores_a_mid_phrase_summary(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    nodes = _hub(tmp_path / "consumer")
    args = _capture_args(nodes, "THO", **{"--summary": _LONG_SUMMARY, "--slug": "long"})
    assert node_record.main(args) == 0
    out = capsys.readouterr().out
    stored = _summary_of(_recorded(nodes, "THO", "long"))
    assert len(stored) <= node_record.SUMMARY_LIMIT
    assert stored.endswith(_ELLIPSIS)
    head = stored[: -len(_ELLIPSIS)]
    assert _LONG_SUMMARY.startswith(head)
    assert _LONG_SUMMARY[len(head)] == " "
    assert "so that a truncation becomes" not in stored
    assert f'warning: "summary exceeds {node_record.SUMMARY_LIMIT} characters' in out
    assert f"stored the word-boundary truncation '{stored}'\"" in out


def test_feedback_capture_cuts_the_summary_derived_from_the_friction(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    nodes = _hub(tmp_path / "consumer")
    friction = (
        "The allocated id collided with a node already on disk and the stored "
        "summary stopped in the middle of a phrase instead of naming the field"
    )
    assert len(friction) > node_record.SUMMARY_LIMIT
    assert (
        feedback_record.main(
            [
                "--nodes",
                str(nodes),
                "--attempted",
                "Ran the capture path for a long friction.",
                "--friction",
                friction,
                "--improvement",
                "Fit the derived summary to the limit.",
            ]
        )
        == 0
    )
    out = capsys.readouterr().out
    node = next(iter((nodes / "canonical").rglob("fbk-*.md")))
    stored = _summary_of(node)
    assert len(stored) <= node_record.SUMMARY_LIMIT
    assert stored.endswith(_ELLIPSIS)
    head = stored[: -len(_ELLIPSIS)]
    assert friction.startswith(head)
    assert friction[len(head)] == " "
    assert f"stored the word-boundary truncation '{stored}'\"" in out


def test_capture_help_surfaces_the_summary_limit(
    capsys: pytest.CaptureFixture[str],
) -> None:
    for verb in (("node", "record"), ("feedback", "record")):
        assert tangle_main([*verb, "--help"]) == 0
        out = capsys.readouterr().out
        assert "96 characters" in out, out
