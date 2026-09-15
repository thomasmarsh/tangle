"""Behavioral tests for the pre-dispatch canonical-store hash census.

Every project-scoped interaction hashes the complete canonical store and
reconciles the derived index before its body answers, so a direct Markdown edit
is observed by the next command with no client step. ``tangle census`` is the
dedicated diagnostic surface that reports whether the last census found zero or
N changes and whether the generated views were current, updated, or failed. The
census hashes exact bytes, so a preserved-mtime edit is still detected, and a
fresh vault with no local state is reported without creating any.
"""

from __future__ import annotations

import hashlib
import os
import re
import sqlite3
import subprocess
from collections.abc import Callable
from pathlib import Path

import vault_helpers

RunTangle = Callable[..., subprocess.CompletedProcess[str]]

_PROJECT = "census-test"
_HUB = vault_helpers.deterministic_id("idx", 0)
_CONSUMER = vault_helpers.deterministic_id("tas", 1)
_HUB_NAME = f"{_HUB}-root"


def _env(tmp_path: Path, vault: Path) -> dict[str, str]:
    return {
        "TANGLE_SIDECAR_DIR": str(tmp_path / "sidecar"),
        "TANGLE_PROJECT_ID": _PROJECT,
        "TANGLE_NODES_DIR": str(vault),
    }


def _database(tmp_path: Path) -> Path:
    return tmp_path / "sidecar" / "projects" / _PROJECT / "graph.sqlite3"


def _node_text(
    *,
    status: str,
    summary: str,
    next_line: str | None = None,
    parent: str | None = None,
) -> str:
    """Return one stationary canonical node with frontmatter authority."""
    lines = [
        "---",
        f"status: {status}",
        "context_rev: 1",
        "updated: 2026-09-11T00:00:00Z",
        f"summary: {summary}",
    ]
    if next_line is not None:
        lines.append(f"next: {next_line}")
    lines.extend(["---", ""])
    text = "\n".join(lines) + "\n"
    if parent is not None:
        text += f"\nParent [[{parent}]].\n"
    return text


def _consumer_text(summary: str) -> str:
    return _node_text(
        status="active",
        summary=summary,
        next_line="Reconcile the root.",
        parent=_HUB_NAME,
    )


def _seed(vault: Path) -> dict[str, Path]:
    """Write a resolved hub and one routed active member in the canonical store."""
    vault.mkdir(parents=True, exist_ok=True)
    (vault / "index-map.md").write_text(
        f"# Root hubs\n\n- Indexes [[{_HUB_NAME}]]\n", encoding="utf-8"
    )
    hub = vault_helpers.write_node(
        vault,
        _HUB,
        "root",
        _node_text(status="resolved", summary="Root graph entry."),
    )
    consumer = vault_helpers.write_node(
        vault, _CONSUMER, "consumer", _consumer_text("Consume the root.")
    )
    return {"hub": hub, "consumer": consumer}


def _stored_nodes(database: Path) -> dict[str, tuple[str, str]]:
    """Return the stored ``(path, content_hash)`` rows keyed by node id."""
    connection = sqlite3.connect(database)
    try:
        return {
            str(node_id): (str(path), str(content_hash))
            for node_id, path, content_hash in connection.execute(
                "SELECT id, path, content_hash FROM nodes"
            )
        }
    finally:
        connection.close()


def test_census_reports_zero_then_a_direct_edit(
    tmp_path: Path, run_tangle: RunTangle
) -> None:
    """A settled vault reports zero changes; a direct edit reports one."""
    vault = tmp_path / "nodes"
    paths = _seed(vault)
    env = _env(tmp_path, vault)
    assert run_tangle("init", env=env).returncode == 0
    # Build the derived index and publish the views from the current snapshot.
    assert run_tangle("frontier", env=env).returncode == 0

    settled = run_tangle("census", env=env)
    assert settled.returncode == 0, settled.stdout + settled.stderr
    assert 'census: "reconciled"' in settled.stdout
    assert 'changes: "0"' in settled.stdout
    assert 'edges: "0"' in settled.stdout
    assert 'removed: "0"' in settled.stdout
    assert 'views: "current (5)"' in settled.stdout

    paths["consumer"].write_text(_consumer_text("A revised summary."), encoding="utf-8")
    edited = run_tangle("census", env=env)
    assert edited.returncode == 0
    assert 'changes: "1"' in edited.stdout
    assert re.search(r'views: "updated [1-9]', edited.stdout), edited.stdout

    settled_again = run_tangle("census", env=env)
    assert 'changes: "0"' in settled_again.stdout
    assert 'views: "current (5)"' in settled_again.stdout


def test_a_direct_edit_is_observed_before_the_diagnostic_answers(
    tmp_path: Path, run_tangle_inproc: RunTangle
) -> None:
    """The pre-dispatch census reconciles a hand edit the diagnostic reports."""
    vault = tmp_path / "nodes"
    paths = _seed(vault)
    env = _env(tmp_path, vault)
    assert run_tangle_inproc("init", env=env).returncode == 0
    assert run_tangle_inproc("frontier", env=env).returncode == 0

    revised = _consumer_text("A revised summary.")
    paths["consumer"].write_text(revised, encoding="utf-8")

    observed = run_tangle_inproc("census", env=env)
    assert observed.returncode == 0, observed.stdout + observed.stderr
    assert 'changes: "1"' in observed.stdout
    stored = _stored_nodes(_database(tmp_path))
    assert stored[_CONSUMER][1] == hashlib.sha256(revised.encode("utf-8")).hexdigest()


def test_a_preserved_mtime_byte_change_is_still_detected(
    tmp_path: Path, run_tangle_inproc: RunTangle
) -> None:
    """Identical size and mtime do not hide a byte change; the hash is the signal."""
    vault = tmp_path / "nodes"
    paths = _seed(vault)
    env = _env(tmp_path, vault)
    assert run_tangle_inproc("init", env=env).returncode == 0
    assert run_tangle_inproc("frontier", env=env).returncode == 0

    before = paths["consumer"].stat()
    # Same length as "Consume the root." and the same restored mtime, so only a
    # byte-level digest can tell the two files apart.
    revised = _consumer_text("Consume the root!")
    paths["consumer"].write_text(revised, encoding="utf-8")
    os.utime(paths["consumer"], ns=(before.st_atime_ns, before.st_mtime_ns))
    after = paths["consumer"].stat()
    assert after.st_mtime_ns == before.st_mtime_ns
    assert after.st_size == before.st_size

    detected = run_tangle_inproc("census", env=env)
    assert detected.returncode == 0
    assert 'changes: "1"' in detected.stdout
    stored = _stored_nodes(_database(tmp_path))
    assert stored[_CONSUMER][1] == hashlib.sha256(revised.encode("utf-8")).hexdigest()


def test_census_counts_a_removed_node(tmp_path: Path, run_tangle_inproc: RunTangle) -> None:
    """A vanished node file is a change the census records and reconciles."""
    vault = tmp_path / "nodes"
    paths = _seed(vault)
    env = _env(tmp_path, vault)
    assert run_tangle_inproc("init", env=env).returncode == 0
    assert run_tangle_inproc("frontier", env=env).returncode == 0

    paths["consumer"].unlink()
    deleted = run_tangle_inproc("census", env=env)
    assert deleted.returncode == 0
    assert 'changes: "0"' in deleted.stdout
    assert 'removed: "1"' in deleted.stdout
    assert _CONSUMER not in _stored_nodes(_database(tmp_path))


def test_census_without_local_state_creates_none(
    tmp_path: Path, run_tangle_inproc: RunTangle
) -> None:
    """A fresh vault is reported without creating a sidecar or any view page."""
    vault = tmp_path / "nodes"
    _seed(vault)
    env = _env(tmp_path, vault)
    result = run_tangle_inproc("census", env=env)
    assert result.returncode == 0, result.stdout + result.stderr
    assert 'census: "uninitialized"' in result.stdout
    assert 'views: "unavailable"' in result.stdout
    assert not (tmp_path / "sidecar").exists()
    assert not (vault / "views").exists()


def test_census_excludes_views_and_local_non_nodes(
    tmp_path: Path, run_tangle_inproc: RunTangle
) -> None:
    """A proposal, a receipt, and a temporary file are never counted as nodes."""
    vault = tmp_path / "nodes"
    _seed(vault)
    env = _env(tmp_path, vault)
    assert run_tangle_inproc("init", env=env).returncode == 0
    assert run_tangle_inproc("frontier", env=env).returncode == 0

    (vault / "proposals").mkdir()
    (vault / "proposals" / f"{_CONSUMER}-draft.md").write_text(
        _consumer_text("Unaccepted draft."), encoding="utf-8"
    )
    (vault / "receipts").mkdir()
    (vault / "receipts" / f"{_HUB}-receipt.md").write_text(
        _node_text(status="resolved", summary="A receipt, not a node."), encoding="utf-8"
    )
    # A same-directory staging file does not end in ``.md`` and is not a node.
    shard = vault / "canonical" / _CONSUMER[-2:]
    (shard / f"{_CONSUMER}-consumer.md.4242.tmp").write_text("staging", encoding="utf-8")

    settled = run_tangle_inproc("census", env=env)
    assert settled.returncode == 0
    assert 'changes: "0"' in settled.stdout
    assert 'removed: "0"' in settled.stdout


def test_routine_interaction_stays_silent_on_a_noop_census(
    tmp_path: Path, run_tangle_inproc: RunTangle
) -> None:
    """A settled read-only interaction reports no census; only `census` speaks."""
    vault = tmp_path / "nodes"
    _seed(vault)
    env = _env(tmp_path, vault)
    assert run_tangle_inproc("init", env=env).returncode == 0
    assert run_tangle_inproc("frontier", env=env).returncode == 0

    quiet = run_tangle_inproc("frontier", env=env)
    assert quiet.returncode == 0
    assert quiet.stderr == ""
    assert "census" not in quiet.stdout
