"""Tests for the strict ``tangle packet`` work-packet read surface.

The verb must return exactly one executable frontier node when the route from
``index-map.md`` is unique, and must refuse to guess with a structured blocked,
ambiguous, or invalid result otherwise. These tests build small Markdown vaults
so each route shape is independent of the shipped vault.
"""

from __future__ import annotations

import csv
import subprocess
from collections.abc import Callable
from pathlib import Path

RunTangle = Callable[..., subprocess.CompletedProcess[str]]


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


def _write(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def _node(
    *,
    status: str,
    summary: str,
    next_value: str | None = None,
    route: str = "Area [[IDX-001-root]].",
    context: str = "",
    context_rev: int = 1,
    priority: str = "",
) -> str:
    header = ["---", f"context_rev: {context_rev}"]
    if priority:
        header.append(f"priority: {priority}")
    header.extend(["updated: 2026-09-14T00:00:00Z", f"summary: {summary}"])
    if next_value is not None:
        if next_value.startswith("[[") and next_value.endswith("]]"):
            header.append(f'next: "{next_value}"')
        else:
            header.append(f"next: {next_value}")
    header.append("---")
    body = [route, ""]
    if context:
        body.extend([context, ""])
    return "\n".join(header) + "\n\n" + "\n".join(body) + "\n"


def _hub(vault: Path, hub: str = "IDX-001-root") -> None:
    _write(
        vault / "index-map.md",
        f"# Root hubs\n\n- Indexes [[{hub}]]: durable entry.\n",
    )
    _write(
        vault / "resolved" / f"{hub}.md",
        _node(status="resolved", summary="Root hub.", route=""),
    )


def _env(tmp_path: Path, vault: Path) -> dict[str, str]:
    return {
        "TANGLE_SIDECAR_DIR": str(tmp_path / "sidecar"),
        "TANGLE_PROJECT_ID": "packet-test",
        "TANGLE_NODES_DIR": str(vault),
    }


def test_packet_ready_returns_the_unique_executable_node(
    tmp_path: Path, run_tangle: RunTangle
) -> None:
    vault = tmp_path / "vault"
    _hub(vault)
    _write(
        vault / "resolved" / "DEF-001-contract.md",
        _node(status="resolved", summary="Contract.", context_rev=2),
    )
    _write(
        vault / "proposed" / "TAS-100-plan.md",
        _node(
            status="proposed",
            summary="Coordinate the plan.",
            next_value="[[TAS-101-first]]",
        ),
    )
    _write(
        vault / "proposed" / "TAS-101-first.md",
        _node(
            status="proposed",
            summary="Run the first step.",
            next_value="Run the first step.",
            route="Parent [[TAS-100-plan]].",
            context="Depends on [[DEF-001-contract]] at context_rev 2.",
        ),
    )

    result = run_tangle("packet", env=_env(tmp_path, vault))
    assert result.returncode == 0
    assert 'result: "ready"' in result.stdout
    assert 'id: "TAS-101"' in result.stdout
    assert 'status: "proposed"' in result.stdout
    assert 'next: "Run the first step."' in result.stdout
    assert _toon_rows(result.stdout, "route") == [
        ["IDX-001", "Area", "TAS-100"],
        ["TAS-100", "Parent", "TAS-101"],
    ]
    assert _toon_rows(result.stdout, "dependencies") == [
        ["Depends on", "DEF-001-contract", "2", "2", "resolved", ""],
    ]
    assert _toon_rows(result.stdout, "files") == [["proposed/TAS-101-first.md"]]
    assert _toon_rows(result.stdout, "verification") == [
        ["tangle check"],
        ["make test"],
    ]


def test_packet_blocked_lists_the_terminal_blocked_route(
    tmp_path: Path, run_tangle_inproc: RunTangle
) -> None:
    vault = tmp_path / "vault"
    _hub(vault)
    _write(
        vault / "proposed" / "TAS-100-plan.md",
        _node(
            status="proposed",
            summary="Coordinate the plan.",
            next_value="[[TAS-101-first]]",
        ),
    )
    _write(
        vault / "blocked" / "TAS-101-first.md",
        _node(
            status="blocked",
            summary="Waiting on the gate.",
            next_value="Clear the gate.",
            route="Parent [[TAS-100-plan]].",
        ),
    )

    result = run_tangle_inproc("packet", env=_env(tmp_path, vault))
    assert result.returncode == 1
    assert 'result: "blocked"' in result.stdout
    rows = _toon_rows(result.stdout, "terminals")
    assert len(rows) == 1
    assert rows[0][0] == "TAS-101"
    assert rows[0][2] == "blocked"
    assert rows[0][4] == "IDX-001 > TAS-100 > TAS-101"


def test_packet_blocked_when_the_terminal_context_is_stale(
    tmp_path: Path, run_tangle_inproc: RunTangle
) -> None:
    vault = tmp_path / "vault"
    _hub(vault)
    _write(
        vault / "resolved" / "DEF-001-contract.md",
        _node(status="resolved", summary="Contract.", context_rev=2),
    )
    _write(
        vault / "proposed" / "TAS-100-plan.md",
        _node(
            status="proposed",
            summary="Coordinate the plan.",
            next_value="[[TAS-101-first]]",
        ),
    )
    _write(
        vault / "proposed" / "TAS-101-first.md",
        _node(
            status="proposed",
            summary="Run the first step.",
            next_value="Run the first step.",
            route="Parent [[TAS-100-plan]].",
            context="Depends on [[DEF-001-contract]] at context_rev 1.",
        ),
    )

    result = run_tangle_inproc("packet", env=_env(tmp_path, vault))
    assert result.returncode == 1
    assert 'result: "blocked"' in result.stdout
    rows = _toon_rows(result.stdout, "terminals")
    assert rows[0][0] == "TAS-101"
    assert rows[0][2] == "stale"


def test_packet_ambiguous_reports_every_distinct_route(
    tmp_path: Path, run_tangle_inproc: RunTangle
) -> None:
    vault = tmp_path / "vault"
    _hub(vault)
    for name, child in (("TAS-100-plan", "TAS-101-first"), ("TAS-200-plan", "TAS-201-second")):
        _write(
            vault / "proposed" / f"{name}.md",
            _node(status="proposed", summary=f"Coordinate {name}.", next_value=f"[[{child}]]"),
        )
        _write(
            vault / "proposed" / f"{child}.md",
            _node(
                status="proposed",
                summary=f"Execute {child}.",
                next_value=f"Execute {child}.",
                route=f"Parent [[{name}]].",
            ),
        )

    result = run_tangle_inproc("packet", env=_env(tmp_path, vault))
    assert result.returncode == 1
    assert 'result: "ambiguous"' in result.stdout
    rows = _toon_rows(result.stdout, "candidates")
    assert [row[0] for row in rows] == ["TAS-101", "TAS-201"]
    assert rows[0][4] == "IDX-001 > TAS-100 > TAS-101"
    assert rows[1][4] == "IDX-001 > TAS-200 > TAS-201"


def test_packet_invalid_when_next_is_not_a_direct_child(
    tmp_path: Path, run_tangle_inproc: RunTangle
) -> None:
    vault = tmp_path / "vault"
    _hub(vault)
    _write(
        vault / "proposed" / "TAS-100-plan.md",
        _node(status="proposed", summary="Coordinate.", next_value="[[TAS-101-first]]"),
    )
    _write(
        vault / "proposed" / "TAS-101-first.md",
        _node(
            status="proposed",
            summary="Execute.",
            next_value="Execute.",
            route="Area [[IDX-001-root]].",
        ),
    )

    result = run_tangle_inproc("packet", env=_env(tmp_path, vault))
    assert result.returncode == 1
    assert 'result: "invalid"' in result.stdout
    assert _toon_rows(result.stdout, "problems")[0][:2] == ["next-not-child", "TAS-100"]


def test_packet_walk_reports_a_route_cycle() -> None:
    """A revisited node is a structural cycle, not a terminal or a candidate.

    The direct-child rule keeps a whole-vault route acyclic, so this defensive
    branch is exercised at the derivation boundary rather than through a vault.
    """
    from tangle import index

    loop = index.IndexedNode(
        id="TAS-100",
        name="TAS-100-loop",
        path="proposed/TAS-100-loop.md",
        status="proposed",
        metadata={"next": "[[TAS-100-loop]]", "summary": "Loop."},
        body="Parent [[TAS-100-loop]].\n",
    )
    candidate, terminal, problems = index._walk_packet_route(
        loop, loop, "Area", {"TAS-100-loop": loop}, {"TAS-100": loop}
    )
    assert candidate is None
    assert terminal is None
    assert [(problem.code, problem.node) for problem in problems] == [
        ("next-cycle", "TAS-100")
    ]


def test_packet_invalid_when_the_next_target_is_missing(
    tmp_path: Path, run_tangle_inproc: RunTangle
) -> None:
    vault = tmp_path / "vault"
    _hub(vault)
    _write(
        vault / "proposed" / "TAS-100-plan.md",
        _node(status="proposed", summary="Coordinate.", next_value="[[TAS-404-absent]]"),
    )

    result = run_tangle_inproc("packet", env=_env(tmp_path, vault))
    assert result.returncode == 1
    assert 'result: "invalid"' in result.stdout
    assert _toon_rows(result.stdout, "problems")[0][:2] == ["next-missing", "TAS-100"]


def test_packet_invalid_when_next_mentions_a_link_inside_prose(
    tmp_path: Path, run_tangle_inproc: RunTangle
) -> None:
    vault = tmp_path / "vault"
    _hub(vault)
    _write(
        vault / "proposed" / "TAS-100-plan.md",
        _node(
            status="proposed",
            summary="Coordinate.",
            next_value="Do [[TAS-101-first]] now.",
        ),
    )

    result = run_tangle_inproc("packet", env=_env(tmp_path, vault))
    assert result.returncode == 1
    assert 'result: "invalid"' in result.stdout
    assert _toon_rows(result.stdout, "problems")[0][:2] == ["next-malformed", "TAS-100"]


def test_packet_invalid_without_a_root_hub(tmp_path: Path, run_tangle_inproc: RunTangle) -> None:
    vault = tmp_path / "vault"
    _write(vault / "index-map.md", "# Root hubs\n\nNo hubs here.\n")
    _write(
        vault / "resolved" / "IDX-001-root.md",
        _node(status="resolved", summary="Root hub.", route=""),
    )

    result = run_tangle_inproc("packet", env=_env(tmp_path, vault))
    assert result.returncode == 1
    assert 'result: "invalid"' in result.stdout
    assert _toon_rows(result.stdout, "problems")[0][0] == "no-root-hub"


def test_packet_rejects_arguments(tmp_path: Path, run_tangle_inproc: RunTangle) -> None:
    vault = tmp_path / "vault"
    _hub(vault)
    result = run_tangle_inproc("packet", "extra", env=_env(tmp_path, vault))
    assert result.returncode == 2
    assert 'error: "packet takes no arguments: extra"' in result.stdout


def test_packet_requires_an_existing_nodes_directory(
    tmp_path: Path, run_tangle_inproc: RunTangle
) -> None:
    result = run_tangle_inproc("packet", env=_env(tmp_path, tmp_path / "missing"))
    assert result.returncode == 1
    assert "nodes directory does not exist" in result.stdout
