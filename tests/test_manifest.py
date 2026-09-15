"""Tests for the ``tangle manifest`` execution-surface read surface.

A node's authored ``# Manifest`` section declares its source, test, verify, and
compat surfaces. The verb must print the authored entries beside the data derived
from them, report a malformed or unknown entry without dropping it, and treat a
node without a manifest as empty rather than an error. These tests build small
Markdown vaults so each shape is independent of the shipped vault.
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
    body: str,
    next_value: str | None = None,
    route: str = "Area [[IDX-001-root]].",
    context_rev: int = 1,
) -> str:
    header = ["---", f"context_rev: {context_rev}", "updated: 2026-09-14T00:00:00Z"]
    header.append(f"summary: {summary}")
    if next_value is not None:
        header.append(f"next: {next_value}")
    header.append("---")
    return "\n".join(header) + "\n\n" + route + "\n\n" + body + "\n"


def _hub(vault: Path, hub: str = "IDX-001-root") -> None:
    _write(
        vault / "index-map.md",
        f"# Root hubs\n\n- Indexes [[{hub}]]: durable entry.\n",
    )
    _write(
        vault / "resolved" / f"{hub}.md",
        _node(status="resolved", summary="Root hub.", route="", body="# Invariant\n\nRoot.\n"),
    )


def _env(tmp_path: Path, vault: Path) -> dict[str, str]:
    return {
        "TANGLE_SIDECAR_DIR": str(tmp_path / "sidecar"),
        "TANGLE_PROJECT_ID": "manifest-test",
        "TANGLE_NODES_DIR": str(vault),
    }


_MANIFEST_BODY = """# Manifest

- source: src/tangle/manifest.py
- test: tests/test_manifest.py
- verify: tangle check
- verify: make test
- compat: legacy nodes/ status directories stay readable
"""


def test_manifest_ready_prints_authored_and_derived(
    tmp_path: Path, run_tangle: RunTangle
) -> None:
    vault = tmp_path / "vault"
    _hub(vault)
    # The declared source exists under the project root (the vault's parent);
    # the test path does not, so it is absent intent rather than a failure.
    _write(tmp_path / "src" / "tangle" / "manifest.py", "# present\n")
    _write(
        vault / "proposed" / "TAS-100-task.md",
        _node(
            status="proposed",
            summary="Declare an execution surface.",
            body=_MANIFEST_BODY,
            next_value="Declare an execution surface.",
        ),
    )

    result = run_tangle("manifest", "TAS-100", env=_env(tmp_path, vault))
    assert result.returncode == 0
    assert 'result: "ready"' in result.stdout
    assert 'id: "TAS-100"' in result.stdout
    assert _toon_rows(result.stdout, "authored") == [
        ["source", "src/tangle/manifest.py"],
        ["test", "tests/test_manifest.py"],
        ["verify", "tangle check"],
        ["verify", "make test"],
        ["compat", "legacy nodes/ status directories stay readable"],
    ]
    assert _toon_rows(result.stdout, "derived") == [
        ["source", "src/tangle/manifest.py", "present", "src/tangle/manifest.py"],
        ["test", "tests/test_manifest.py", "absent", "tests/test_manifest.py"],
        ["verify", "tangle check", "known", ""],
        ["verify", "make test", "known", ""],
        ["compat", "legacy nodes/ status directories stay readable", "recorded", ""],
    ]
    assert "problems[" not in result.stdout


def test_manifest_accepts_a_backticked_value(tmp_path: Path, run_tangle: RunTangle) -> None:
    vault = tmp_path / "vault"
    _hub(vault)
    _write(
        vault / "proposed" / "TAS-100-task.md",
        _node(
            status="proposed",
            summary="Declare an execution surface.",
            body="# Manifest\n\n- source: `src/tangle/manifest.py`\n",
            next_value="Declare an execution surface.",
        ),
    )

    result = run_tangle("manifest", "TAS-100", env=_env(tmp_path, vault))
    assert result.returncode == 0
    assert _toon_rows(result.stdout, "authored") == [["source", "src/tangle/manifest.py"]]


def test_manifest_absent_is_empty(tmp_path: Path, run_tangle: RunTangle) -> None:
    vault = tmp_path / "vault"
    _hub(vault)
    _write(
        vault / "proposed" / "TAS-100-task.md",
        _node(
            status="proposed",
            summary="No declared surface.",
            body="# Outcome\n\nNothing to declare.\n",
            next_value="Do the work.",
        ),
    )

    result = run_tangle("manifest", "TAS-100", env=_env(tmp_path, vault))
    assert result.returncode == 0
    assert 'result: "empty"' in result.stdout
    assert "authored: 0 entries" in result.stdout
    assert "derived: 0 entries" in result.stdout


def test_manifest_invalid_reports_missing_and_malformed_entries(
    tmp_path: Path, run_tangle: RunTangle
) -> None:
    vault = tmp_path / "vault"
    _hub(vault)
    _write(
        vault / "proposed" / "TAS-100-task.md",
        _node(
            status="proposed",
            summary="Declare a broken surface.",
            body=(
                "# Manifest\n\n"
                "- source\n"
                "- test:\n"
                "- browser: tests/test_manifest.py\n"
                "- source: src/a.py\n"
                "- source: src/a.py\n"
            ),
            next_value="Fix the manifest.",
        ),
    )

    result = run_tangle("manifest", "TAS-100", env=_env(tmp_path, vault))
    assert result.returncode == 1
    assert 'result: "invalid"' in result.stdout
    codes = [row[0] for row in _toon_rows(result.stdout, "problems")]
    assert codes == [
        "manifest-entry-malformed",
        "manifest-entry-malformed",
        "manifest-kind-unknown",
        "manifest-entry-duplicate",
    ]
    # The one well-formed entry is still reported beside the problems.
    assert _toon_rows(result.stdout, "authored") == [["source", "src/a.py"]]


def test_manifest_unknown_node_exits_one(tmp_path: Path, run_tangle: RunTangle) -> None:
    vault = tmp_path / "vault"
    _hub(vault)
    result = run_tangle("manifest", "TAS-404-absent", env=_env(tmp_path, vault))
    assert result.returncode == 1
    assert 'error: "unknown node: TAS-404-absent"' in result.stdout


def test_manifest_rejects_arguments(tmp_path: Path, run_tangle: RunTangle) -> None:
    vault = tmp_path / "vault"
    _hub(vault)
    assert run_tangle("manifest", env=_env(tmp_path, vault)).returncode == 2
    result = run_tangle("manifest", "TAS-100", "extra", env=_env(tmp_path, vault))
    assert result.returncode == 2
    assert 'error: "manifest takes one NODE: extra"' in result.stdout


def test_manifest_requires_an_existing_nodes_directory(
    tmp_path: Path, run_tangle: RunTangle
) -> None:
    result = run_tangle("manifest", "TAS-100", env=_env(tmp_path, tmp_path / "missing"))
    assert result.returncode == 1
    assert "nodes directory does not exist" in result.stdout


def test_check_rejects_a_malformed_manifest(tmp_path: Path, run_tangle: RunTangle) -> None:
    vault = tmp_path / "vault"
    _hub(vault)
    _write(
        vault / "proposed" / "TAS-100-task.md",
        _node(
            status="proposed",
            summary="Declare a broken surface.",
            body="# Manifest\n\n- browser: tests/test_manifest.py\n",
            next_value="Fix the manifest.",
        ),
    )

    result = run_tangle(
        "check", "--format", "toon", str(vault), env=_env(tmp_path, vault)
    )
    assert result.returncode == 1
    assert 'result: "failed"' in result.stdout
    assert _toon_rows(result.stdout, "findings")[0][0] == "manifest-kind-unknown"
