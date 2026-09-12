"""Pytest port of ``tests/bt-foundation.sh`` for the Python ``bt``.

Covers the sidecar lifecycle, atomic ID allocation, lease claims and renewal,
base-hash conflicts, release idempotence, expiry, and argument validation.
"""

from __future__ import annotations

import sqlite3
import subprocess
from collections.abc import Callable
from pathlib import Path

from braintree import __version__

RunBt = Callable[..., subprocess.CompletedProcess[str]]


def _env(tmp_path: Path) -> dict[str, str]:
    return {
        "BT_SIDECAR_DIR": str(tmp_path / "sidecar"),
        "BT_PROJECT_ID": "test-project",
    }


def _database(tmp_path: Path) -> Path:
    return tmp_path / "sidecar" / "projects" / "test-project" / "graph.sqlite3"


def test_version_status_and_init(tmp_path: Path, run_bt: RunBt) -> None:
    env = _env(tmp_path)
    version = run_bt("--version", env=env)
    assert version.stdout.strip() == __version__
    status = run_bt("status", env=env)
    assert 'initialized: "false"' in status.stdout
    initialized = run_bt("init", env=env)
    assert 'result: "initialized"' in initialized.stdout
    database = _database(tmp_path)
    assert database.is_file()
    connection = sqlite3.connect(database)
    try:
        mode = connection.execute("PRAGMA journal_mode;").fetchone()
    finally:
        connection.close()
    assert mode is not None and mode[0] == "wal"


def test_allocate_is_atomic_and_per_prefix(tmp_path: Path, run_bt: RunBt) -> None:
    env = _env(tmp_path)
    assert run_bt("allocate", "TAS", env=env).stdout.strip() == 'id: "TAS-001"'
    assert run_bt("allocate", "TAS", env=env).stdout.strip() == 'id: "TAS-002"'
    assert run_bt("allocate", "DEF", env=env).stdout.strip() == 'id: "DEF-001"'


def test_claim_renew_conflict_and_release(tmp_path: Path, run_bt: RunBt) -> None:
    env = _env(tmp_path)
    first = run_bt(
        "claim", "TAS-001", "agent-a", "--base-hash", "abc", "--lease-seconds", "60", env=env
    )
    assert 'result: "claimed"' in first.stdout
    renewed = run_bt(
        "claim", "TAS-001", "agent-a", "--base-hash", "abc", "--lease-seconds", "60", env=env
    )
    assert 'result: "claimed"' in renewed.stdout

    other_agent = run_bt("claim", "TAS-001", "agent-b", "--base-hash", "abc", env=env)
    assert other_agent.returncode == 1
    assert (
        'error: "node is claimed by agent-a with a different base hash"' in other_agent.stdout
    )
    other_hash = run_bt("claim", "TAS-001", "agent-a", "--base-hash", "def", env=env)
    assert other_hash.returncode == 1
    assert 'error: "node is claimed by agent-a with a different base hash"' in other_hash.stdout

    released = run_bt("release", "TAS-001", "agent-a", "--base-hash", "abc", env=env)
    assert 'result: "released"' in released.stdout
    again = run_bt("release", "TAS-001", "agent-a", "--base-hash", "abc", env=env)
    assert 'result: "no-op"' in again.stdout


def test_expired_lease_can_be_reclaimed(tmp_path: Path, run_bt: RunBt) -> None:
    env = _env(tmp_path)
    run_bt("claim", "TAS-001", "agent-b", "--base-hash", "def", "--lease-seconds", "1", env=env)
    database = _database(tmp_path)
    connection = sqlite3.connect(database)
    try:
        connection.execute("UPDATE claims SET lease_expires_at=0 WHERE node_id='TAS-001';")
        connection.commit()
    finally:
        connection.close()
    reclaimed = run_bt(
        "claim", "TAS-001", "agent-a", "--base-hash", "ghi", "--lease-seconds", "60", env=env
    )
    assert 'result: "claimed"' in reclaimed.stdout


def test_unknown_claim_argument_is_a_usage_error(tmp_path: Path, run_bt: RunBt) -> None:
    env = _env(tmp_path)
    result = run_bt("claim", "TAS-002", "agent-a", "--bogus", "x", env=env)
    assert result.returncode == 2
    assert 'error: "unknown argument for claim: --bogus"' in result.stdout
