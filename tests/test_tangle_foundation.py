"""Pytest port of ``tests/tangle-foundation.sh`` for the Python ``tangle``.

Covers the sidecar lifecycle, atomic ID allocation, lease claims and renewal,
base-hash conflicts, release idempotence, expiry, and argument validation.
"""

from __future__ import annotations

import io
import os
import re
import sqlite3
import subprocess
from collections.abc import Callable
from contextlib import redirect_stdout
from pathlib import Path

import pytest

from tangle import __version__, main

RunTangle = Callable[..., subprocess.CompletedProcess[str]]


def _env(tmp_path: Path) -> dict[str, str]:
    return {
        "TANGLE_SIDECAR_DIR": str(tmp_path / "sidecar"),
        "TANGLE_PROJECT_ID": "test-project",
        "TANGLE_NODES_DIR": str(tmp_path / "vault" / "nodes"),
    }


_FRONTMATTER = (
    "---\ncontext_rev: 1\nupdated: 2026-09-11T00:00:00Z\nsummary: Fixture.\n---\n"
)

# Real 64-character lowercase hex digests stand in for a node's recorded base
# hash, the bare operand `tangle hash` prints.
_BASE_HASH_A = "1a" * 32
_BASE_HASH_B = "2b" * 32
_BASE_HASH_C = "3c" * 32


def _seed_allocations(vault: Path) -> None:
    (vault / "active").mkdir(parents=True)
    (vault / "resolved").mkdir()
    (vault / "resolved" / "IDX-001-root.md").write_text(_FRONTMATTER, encoding="utf-8")
    (vault / "resolved" / "THO-003-note.md").write_text(_FRONTMATTER, encoding="utf-8")
    for number in range(1, 8):
        (vault / "active" / f"TAS-{number:03d}-existing.md").write_text(
            _FRONTMATTER, encoding="utf-8"
        )


def _database(tmp_path: Path) -> Path:
    return tmp_path / "sidecar" / "projects" / "test-project" / "graph.sqlite3"


def _write_vault(nodes: Path) -> Path:
    (nodes / "resolved").mkdir(parents=True)
    (nodes / "index-map.md").write_text(
        "# Root hubs\n\n- Indexes [[IDX-001-root]]\n", encoding="utf-8"
    )
    (nodes / "resolved" / "IDX-001-root.md").write_text(_FRONTMATTER, encoding="utf-8")
    return nodes


def _record_env(tmp_path: Path, project: str) -> dict[str, str]:
    """Return a process environment for a capture run pinned to a temp sidecar."""
    env = {key: value for key, value in os.environ.items() if key != "TANGLE_NODES_DIR"}
    env["TANGLE_SIDECAR_DIR"] = str(tmp_path / "sidecar")
    env["TANGLE_PROJECT_ID"] = project
    return env


def _remaining(stdout: str) -> int:
    match = re.search(r'^lease_remaining_seconds: "(\d+)"$', stdout, re.MULTILINE)
    assert match is not None, stdout
    return int(match.group(1))


@pytest.fixture(scope="module")
def global_help() -> str:
    """The global command index, rendered once in-process for the whole module.

    The global help is environment-independent and vault-free, so one render
    serves every assertion that the index lists a verb. The spawned ``--help``
    path stays covered by the real entry-point tests.
    """
    buffer = io.StringIO()
    with redirect_stdout(buffer):
        code = main.main(["--help"])
    assert code == 0
    return buffer.getvalue()


def test_version_status_and_init(tmp_path: Path, run_tangle: RunTangle) -> None:
    """The file's real-process entry-point smoke: version, status, and init."""
    env = _env(tmp_path)
    version = run_tangle("--version", env=env)
    assert version.stdout.strip() == __version__
    status = run_tangle("status", env=env)
    assert 'initialized: "false"' in status.stdout
    initialized = run_tangle("init", env=env)
    assert 'result: "initialized"' in initialized.stdout
    database = _database(tmp_path)
    assert database.is_file()
    connection = sqlite3.connect(database)
    try:
        mode = connection.execute("PRAGMA journal_mode;").fetchone()
    finally:
        connection.close()
    assert mode is not None and mode[0] == "wal"


def test_allocate_is_atomic_and_per_prefix(tmp_path: Path, run_tangle_inproc: RunTangle) -> None:
    env = _env(tmp_path)
    assert run_tangle_inproc("allocate", "TAS", env=env).stdout.strip() == 'id: "TAS-001"'
    assert run_tangle_inproc("allocate", "TAS", env=env).stdout.strip() == 'id: "TAS-002"'
    assert run_tangle_inproc("allocate", "DEF", env=env).stdout.strip() == 'id: "DEF-001"'


def test_reservations_takes_no_arguments_and_reports_none_when_uninitialized(
    tmp_path: Path, run_tangle_inproc: RunTangle
) -> None:
    env = _env(tmp_path)
    empty = run_tangle_inproc("reservations", env=env)
    assert empty.returncode == 0
    assert empty.stdout.strip() == "reservations: 0 prefixes"

    unknown = run_tangle_inproc("reservations", "extra", env=env)
    assert unknown.returncode == 2
    assert 'error: "reservations takes no arguments: extra"' in unknown.stdout


def test_reservations_lists_burned_ids_apart_from_missing_nodes(
    tmp_path: Path, run_tangle_inproc: RunTangle
) -> None:
    env = _env(tmp_path)
    vault = tmp_path / "vault" / "nodes"
    assert run_tangle_inproc("init", env=env).returncode == 0
    # Three allocations the caller discards and never writes as nodes: the
    # counter still advances past them, so they are burned, not missing.
    for expected in ("TAS-001", "TAS-002", "TAS-003"):
        assert run_tangle_inproc("allocate", "TAS", env=env).stdout.strip() == f'id: "{expected}"'
    # The fourth allocation is written, so only 001-003 stay burned.
    assert run_tangle_inproc("allocate", "TAS", env=env).stdout.strip() == 'id: "TAS-004"'
    (vault / "active").mkdir(parents=True)
    (vault / "active" / "TAS-004-written.md").write_text(_FRONTMATTER, encoding="utf-8")

    listed = run_tangle_inproc("reservations", env=env)
    assert listed.returncode == 0
    assert "prefix,next,burned" in listed.stdout
    # TAS-001 through TAS-003 are burned; TAS-004 is a node; the next id is 005.
    assert '"TAS","5","1-3"' in listed.stdout


def test_claim_renew_conflict_and_release(tmp_path: Path, run_tangle_inproc: RunTangle) -> None:
    env = _env(tmp_path)
    first = run_tangle_inproc(
        "claim",
        "TAS-001",
        "agent-a",
        "--base-hash",
        _BASE_HASH_A,
        "--lease-seconds",
        "60",
        env=env,
    )
    assert 'result: "claimed"' in first.stdout
    renewed = run_tangle_inproc(
        "claim",
        "TAS-001",
        "agent-a",
        "--base-hash",
        _BASE_HASH_A,
        "--lease-seconds",
        "60",
        env=env,
    )
    assert 'result: "claimed"' in renewed.stdout

    other_agent = run_tangle_inproc(
        "claim", "TAS-001", "agent-b", "--base-hash", _BASE_HASH_A, env=env
    )
    assert other_agent.returncode == 1
    assert (
        'error: "node is claimed by agent-a with a different base hash"' in other_agent.stdout
    )
    other_hash = run_tangle_inproc(
        "claim", "TAS-001", "agent-a", "--base-hash", _BASE_HASH_B, env=env
    )
    assert other_hash.returncode == 1
    assert 'error: "node is claimed by agent-a with a different base hash"' in other_hash.stdout

    wrong_hash = run_tangle_inproc(
        "release", "TAS-001", "agent-a", "--base-hash", _BASE_HASH_B, env=env
    )
    assert wrong_hash.returncode == 1
    assert (
        'error: "base hash does not match the recorded claim for TAS-001; release refused"'
        in wrong_hash.stdout
    )
    wrong_owner = run_tangle_inproc(
        "release", "TAS-001", "agent-b", "--base-hash", _BASE_HASH_A, env=env
    )
    assert wrong_owner.returncode == 1
    assert 'error: "node is claimed by agent-a; release refused"' in wrong_owner.stdout
    still_held = run_tangle_inproc(
        "claim", "TAS-001", "agent-b", "--base-hash", _BASE_HASH_A, env=env
    )
    assert still_held.returncode == 1

    released = run_tangle_inproc(
        "release", "TAS-001", "agent-a", "--base-hash", _BASE_HASH_A, env=env
    )
    assert 'result: "released"' in released.stdout
    again = run_tangle_inproc("release", "TAS-001", "agent-a", "--base-hash", _BASE_HASH_A, env=env)
    assert 'result: "no-op"' in again.stdout


def test_claim_and_release_reject_a_non_digest_base_hash(
    tmp_path: Path, run_tangle_inproc: RunTangle
) -> None:
    env = _env(tmp_path)
    labelled_block = f'node: "TAS-001"\ncontent_hash: "{_BASE_HASH_A}"'
    malformed = {
        "the labelled multi-line hash block": labelled_block,
        "a short placeholder": "abc",
        "an uppercase digest": _BASE_HASH_A.upper(),
    }
    for label, operand in malformed.items():
        claim = run_tangle_inproc("claim", "TAS-001", "agent-a", "--base-hash", operand, env=env)
        assert claim.returncode == 2, label
        assert (
            "--base-hash must be a bare 64-character lowercase hex digest" in claim.stdout
        ), label
        release = run_tangle_inproc(
            "release", "TAS-001", "agent-a", "--base-hash", operand, env=env
        )
        assert release.returncode == 2, label
        assert (
            "--base-hash must be a bare 64-character lowercase hex digest" in release.stdout
        ), label
    # The shape check runs before any sidecar write, so no claim and no sidecar
    # were created by the rejected operands.
    assert not _database(tmp_path).is_file()


def test_claim_and_release_accept_a_bare_digest(
    tmp_path: Path, run_tangle_inproc: RunTangle
) -> None:
    env = _env(tmp_path)
    claimed = run_tangle_inproc("claim", "TAS-001", "agent-a", "--base-hash", _BASE_HASH_A, env=env)
    assert claimed.returncode == 0
    assert f'base_hash: "{_BASE_HASH_A}"' in claimed.stdout
    released = run_tangle_inproc(
        "release", "TAS-001", "agent-a", "--base-hash", _BASE_HASH_A, env=env
    )
    assert released.returncode == 0
    assert 'result: "released"' in released.stdout


def test_expired_lease_can_be_reclaimed(tmp_path: Path, run_tangle_inproc: RunTangle) -> None:
    env = _env(tmp_path)
    run_tangle_inproc(
        "claim", "TAS-001", "agent-b", "--base-hash", _BASE_HASH_B, "--lease-seconds", "1", env=env
    )
    database = _database(tmp_path)
    connection = sqlite3.connect(database)
    try:
        connection.execute("UPDATE claims SET lease_expires_at=0 WHERE node_id='TAS-001';")
        connection.commit()
    finally:
        connection.close()
    reclaimed = run_tangle_inproc(
        "claim",
        "TAS-001",
        "agent-a",
        "--base-hash",
        _BASE_HASH_C,
        "--lease-seconds",
        "60",
        env=env,
    )
    assert 'result: "claimed"' in reclaimed.stdout


def test_claim_states_the_default_lease_duration(
    tmp_path: Path, run_tangle_inproc: RunTangle
) -> None:
    env = _env(tmp_path)
    claimed = run_tangle_inproc("claim", "TAS-001", "agent-a", "--base-hash", _BASE_HASH_A, env=env)
    assert 'result: "claimed"' in claimed.stdout
    assert _remaining(claimed.stdout) == 900


def test_reclaim_with_the_same_agent_and_hash_renews_the_lease(
    tmp_path: Path, run_tangle_inproc: RunTangle
) -> None:
    env = _env(tmp_path)
    first = run_tangle_inproc(
        "claim",
        "TAS-001",
        "agent-a",
        "--base-hash",
        _BASE_HASH_A,
        "--lease-seconds",
        "60",
        env=env,
    )
    assert _remaining(first.stdout) == 60
    renewed = run_tangle_inproc(
        "claim",
        "TAS-001",
        "agent-a",
        "--base-hash",
        _BASE_HASH_A,
        "--lease-seconds",
        "300",
        env=env,
    )
    assert 'result: "claimed"' in renewed.stdout
    assert _remaining(renewed.stdout) == 300
    released = run_tangle_inproc(
        "release", "TAS-001", "agent-a", "--base-hash", _BASE_HASH_A, env=env
    )
    assert 'result: "released"' in released.stdout
    assert 1 <= _remaining(released.stdout) <= 300


def test_release_separates_expired_from_never_held(
    tmp_path: Path, run_tangle_inproc: RunTangle
) -> None:
    env = _env(tmp_path)
    never_held = run_tangle_inproc(
        "release", "TAS-001", "agent-a", "--base-hash", _BASE_HASH_A, env=env
    )
    assert never_held.returncode == 0
    assert 'result: "no-op"' in never_held.stdout
    assert _remaining(never_held.stdout) == 0

    run_tangle_inproc(
        "claim", "TAS-001", "agent-a", "--base-hash", _BASE_HASH_A, "--lease-seconds", "1", env=env
    )
    database = _database(tmp_path)
    connection = sqlite3.connect(database)
    try:
        connection.execute("UPDATE claims SET lease_expires_at=0 WHERE node_id='TAS-001';")
        connection.commit()
    finally:
        connection.close()

    lapsed = run_tangle_inproc(
        "release", "TAS-001", "agent-a", "--base-hash", _BASE_HASH_A, env=env
    )
    assert lapsed.returncode == 0
    assert 'result: "expired"' in lapsed.stdout
    assert _remaining(lapsed.stdout) == 0

    # The lapsed claim is cleared, so the node is free for the next writer.
    reclaimed = run_tangle_inproc(
        "claim", "TAS-001", "agent-b", "--base-hash", _BASE_HASH_B, env=env
    )
    assert 'result: "claimed"' in reclaimed.stdout


def test_unknown_claim_argument_is_a_usage_error(
    tmp_path: Path, run_tangle_inproc: RunTangle
) -> None:
    env = _env(tmp_path)
    result = run_tangle_inproc("claim", "TAS-002", "agent-a", "--bogus", "x", env=env)
    assert result.returncode == 2
    assert 'error: "unknown argument for claim: --bogus"' in result.stdout


def test_init_seeds_reservations_from_markdown(
    tmp_path: Path, run_tangle_inproc: RunTangle
) -> None:
    vault = tmp_path / "vault" / "nodes"
    _seed_allocations(vault)
    env = _env(tmp_path)
    env["TANGLE_NODES_DIR"] = str(vault)

    assert run_tangle_inproc("init", env=env).returncode == 0
    status = run_tangle_inproc("status", env=env)
    assert '"TAS","8"' in status.stdout
    assert run_tangle_inproc("allocate", "TAS", env=env).stdout.strip() == 'id: "TAS-008"'
    assert run_tangle_inproc("allocate", "IDX", env=env).stdout.strip() == 'id: "IDX-002"'
    assert run_tangle_inproc("allocate", "THO", env=env).stdout.strip() == 'id: "THO-004"'


def test_allocate_skips_on_disk_identity_with_empty_sidecar(
    tmp_path: Path, run_tangle_inproc: RunTangle
) -> None:
    vault = tmp_path / "vault" / "nodes"
    _seed_allocations(vault)
    env = _env(tmp_path)
    env["TANGLE_NODES_DIR"] = str(vault)

    # No init or reindex: the counter is empty, but allocation must still not
    # return an identity that already exists on disk.
    result = run_tangle_inproc("allocate", "TAS", env=env)
    assert result.returncode == 0
    assert result.stdout.strip() == 'id: "TAS-008"'


def test_allocate_reserves_a_count_of_consecutive_ids(
    tmp_path: Path, run_tangle_inproc: RunTangle
) -> None:
    env = _env(tmp_path)
    batch = run_tangle_inproc("allocate", "TAS", "3", env=env)
    assert batch.returncode == 0
    # One call reserves the whole batch in a stable, parseable table.
    assert batch.stdout.strip().splitlines() == [
        "ids[3]{id}:",
        '  "TAS-001"',
        '  "TAS-002"',
        '  "TAS-003"',
    ]
    # The counter advanced past the batch, so the next call continues it.
    assert run_tangle_inproc("allocate", "TAS", env=env).stdout.strip() == 'id: "TAS-004"'


def test_allocate_count_of_one_keeps_the_single_id_output(
    tmp_path: Path, run_tangle_inproc: RunTangle
) -> None:
    env = _env(tmp_path)
    default = run_tangle_inproc("allocate", "TAS", env=env)
    assert default.returncode == 0
    assert default.stdout.strip() == 'id: "TAS-001"'
    explicit = run_tangle_inproc("allocate", "TAS", "1", env=env)
    assert explicit.returncode == 0
    assert explicit.stdout.strip() == 'id: "TAS-002"'


def test_allocate_count_skips_on_disk_identities_and_stays_consecutive(
    tmp_path: Path, run_tangle_inproc: RunTangle
) -> None:
    vault = tmp_path / "vault" / "nodes"
    (vault / "active").mkdir(parents=True)
    (vault / "active" / "TAS-002-existing.md").write_text(_FRONTMATTER, encoding="utf-8")
    env = _env(tmp_path)
    env["TANGLE_NODES_DIR"] = str(vault)

    batch = run_tangle_inproc("allocate", "TAS", "2", env=env)
    assert batch.returncode == 0
    # TAS-002 is on disk, so the batch skips it and still returns two ids.
    assert batch.stdout.strip().splitlines() == [
        "ids[2]{id}:",
        '  "TAS-001"',
        '  "TAS-003"',
    ]


def test_allocate_batch_burns_the_reserved_ids_it_never_wrote(
    tmp_path: Path, run_tangle_inproc: RunTangle
) -> None:
    env = _env(tmp_path)
    assert run_tangle_inproc("init", env=env).returncode == 0
    assert run_tangle_inproc("allocate", "TAS", "3", env=env).returncode == 0

    listed = run_tangle_inproc("reservations", env=env)
    assert listed.returncode == 0
    assert '"TAS","4","1-3"' in listed.stdout


def test_allocate_rejects_a_bad_count_or_extra_operand_without_reserving(
    tmp_path: Path, run_tangle_inproc: RunTangle
) -> None:
    env = _env(tmp_path)
    for arguments, expected in (
        ((), 'error: "allocate requires PREFIX"'),
        (("TAS", "0"), 'error: "COUNT must be a positive integer"'),
        (("TAS", "x"), 'error: "COUNT must be a positive integer"'),
        (
            ("TAS", "1", "2"),
            'error: "allocate accepts at most PREFIX and COUNT"',
        ),
    ):
        rejected = run_tangle_inproc("allocate", *arguments, env=env)
        assert rejected.returncode == 2, arguments
        assert expected in rejected.stdout, arguments
    # Every rejection happened before any sidecar write, so the first id is
    # still free.
    assert run_tangle_inproc("allocate", "TAS", env=env).stdout.strip() == 'id: "TAS-001"'


def test_allocate_help_and_command_index_name_the_count_operand(
    tmp_path: Path, run_tangle_inproc: RunTangle, global_help: str
) -> None:
    env = _env(tmp_path)
    verb = run_tangle_inproc("allocate", "--help", env=env)
    assert verb.returncode == 0
    assert 'usage: "tangle allocate PREFIX [COUNT]"' in verb.stdout
    assert '"COUNT"' in verb.stdout
    assert '"positive number of consecutive ids; default 1, no upper bound"' in verb.stdout

    assert '"allocate PREFIX [COUNT]"' in global_help


def test_frontier_and_node_verbs_are_dispatched(
    tmp_path: Path, run_tangle_inproc: RunTangle, global_help: str
) -> None:
    env = _env(tmp_path)
    assert "frontier" in global_help
    assert "node NODE" in global_help

    missing = run_tangle_inproc("node", env=env)
    assert missing.returncode == 2
    assert 'error: "node requires NODE"' in missing.stdout

    extra = run_tangle_inproc("frontier", "extra", env=env)
    assert extra.returncode == 2
    assert 'error: "frontier accepts no arguments"' in extra.stdout


def test_impact_verb_is_dispatched(
    tmp_path: Path, run_tangle_inproc: RunTangle, global_help: str
) -> None:
    env = _env(tmp_path)
    assert "impact NODE" in global_help

    missing = run_tangle_inproc("impact", env=env)
    assert missing.returncode == 2
    assert 'error: "impact requires NODE"' in missing.stdout


def test_orient_verb_is_dispatched(
    tmp_path: Path, run_tangle_inproc: RunTangle, global_help: str
) -> None:
    env = _env(tmp_path)
    assert "orient [--section NAME]" in global_help

    unknown = run_tangle_inproc("orient", "--section", "nope", env=env)
    assert unknown.returncode == 2
    assert 'error: "unknown section: nope' in unknown.stdout

    bad_limit = run_tangle_inproc("orient", "--limit", "0", env=env)
    assert bad_limit.returncode == 2
    assert 'error: "--limit must be a positive integer"' in bad_limit.stdout

    missing_value = run_tangle_inproc("orient", "--section", env=env)
    assert missing_value.returncode == 2
    assert 'error: "--section requires a section name"' in missing_value.stdout


def test_search_filters_and_similar_are_dispatched(
    tmp_path: Path, run_tangle_inproc: RunTangle, global_help: str
) -> None:
    env = _env(tmp_path)
    assert "similar TEXT" in global_help
    assert "--status" in global_help
    missing = run_tangle_inproc("similar", env=env)
    assert missing.returncode == 2
    assert 'error: "similar requires TEXT or --file PATH"' in missing.stdout

    unknown = run_tangle_inproc("search", "q", "--bogus", env=env)
    assert unknown.returncode == 2
    assert 'error: "unknown argument for search: --bogus"' in unknown.stdout


def test_next_and_frontier_group_verbs_are_dispatched(
    tmp_path: Path, run_tangle_inproc: RunTangle, global_help: str
) -> None:
    env = _env(tmp_path)
    assert "next [--rank]" in global_help
    assert "frontier [--group]" in global_help

    unknown = run_tangle_inproc("next", "--bogus", env=env)
    assert unknown.returncode == 2
    assert 'error: "unknown argument for next: --bogus"' in unknown.stdout

    bad_limit = run_tangle_inproc("next", "--rank", "--limit", "0", env=env)
    assert bad_limit.returncode == 2
    assert 'error: "--limit must be a positive integer"' in bad_limit.stdout

    limit_without_group = run_tangle_inproc("frontier", "--limit", "2", env=env)
    assert limit_without_group.returncode == 2
    assert 'error: "frontier --limit requires --group"' in limit_without_group.stdout


def test_reconcile_verb_is_dispatched(
    tmp_path: Path, run_tangle_inproc: RunTangle, global_help: str
) -> None:
    env = _env(tmp_path)
    assert "reconcile [--base REF] [--head REF ...] [NODES]" in global_help

    unknown = run_tangle_inproc("reconcile", "--bogus", env=env)
    assert unknown.returncode == 2
    assert 'error: "unknown argument for reconcile: --bogus"' in unknown.stdout


# The one-command capture paths share the sidecar reservation with `allocate`
# when the sidecar exists and owns the vault, and fall back to a vault-local
# reservation otherwise, so capture never duplicates an automatically chosen id.

_RECORD_BODY = "# Outcome\n\nReserve the id atomically."


def test_allocate_batch_and_node_record_share_one_counter(
    tmp_path: Path, run_tangle_inproc: RunTangle
) -> None:
    """The batch allocator and the capture path number one vault identically."""
    repo = tmp_path / "repo"
    _write_vault(repo / ".tangle")
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    env = _record_env(tmp_path, "allocate-record-shared")
    assert run_tangle_inproc("init", cwd=repo, env=env).returncode == 0

    batch = run_tangle_inproc("allocate", "TAS", "2", cwd=repo, env=env)
    assert batch.returncode == 0, batch.stdout
    assert batch.stdout.strip().splitlines() == [
        "ids[2]{id}:",
        '  "TAS-001"',
        '  "TAS-002"',
    ]

    recorded = run_tangle_inproc(
        "node",
        "record",
        "--type",
        "TAS",
        "--summary",
        "Continue the counter allocate advanced.",
        "--body",
        _RECORD_BODY,
        "--next",
        "Add the shared-counter test.",
        cwd=repo,
        env=env,
    )
    assert recorded.returncode == 0, recorded.stdout
    assert re.search(r'id: "tas-[0-7][0-9a-hjkmnp-tv-z]{25}"', recorded.stdout)


def test_record_reserves_through_the_project_sidecar(
    tmp_path: Path, run_tangle_inproc: RunTangle
) -> None:
    repo = tmp_path / "repo"
    nodes = _write_vault(repo / ".tangle")
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    env = _record_env(tmp_path, "record-sidecar")
    assert run_tangle_inproc("init", cwd=repo, env=env).returncode == 0

    recorded = run_tangle_inproc(
        "node",
        "record",
        "--type",
        "TAS",
        "--summary",
        "Reserve the id through the sidecar.",
        "--body",
        _RECORD_BODY,
        "--next",
        "Add the boundary test.",
        cwd=repo,
        env=env,
    )
    assert recorded.returncode == 0, recorded.stdout
    match = re.search(r'id: "(tas-[0-7][0-9a-hjkmnp-tv-z]{25})"', recorded.stdout)
    assert match is not None
    written = next(
        (nodes / "canonical").rglob(
            f"{match.group(1)}-reserve-the-id-through-the-sidecar.md"
        )
    )
    assert written.is_file()
    # Cryptographic node identity neither advances nor needs numeric reservations.
    assert not (nodes / "reservations").exists()
    assert '"TAS"' not in run_tangle_inproc("status", cwd=repo, env=env).stdout


def test_record_falls_back_for_a_vault_outside_the_project(
    tmp_path: Path, run_tangle_inproc: RunTangle
) -> None:
    repo = tmp_path / "repo"
    _write_vault(repo / ".tangle")
    external = _write_vault(tmp_path / "external" / ".tangle")
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    env = _record_env(tmp_path, "record-external")
    assert run_tangle_inproc("init", cwd=repo, env=env).returncode == 0
    # The project sidecar counter is ahead; it must not number another vault.
    assert run_tangle_inproc("allocate", "TAS", cwd=repo, env=env).stdout.strip() == 'id: "TAS-001"'

    recorded = run_tangle_inproc(
        "node",
        "record",
        "--type",
        "TAS",
        "--summary",
        "Capture into an external vault.",
        "--body",
        _RECORD_BODY,
        "--next",
        "Add the boundary test.",
        "--nodes",
        str(external),
        cwd=repo,
        env=env,
    )
    assert recorded.returncode == 0, recorded.stdout
    assert re.search(r'id: "tas-[0-7][0-9a-hjkmnp-tv-z]{25}"', recorded.stdout)
    assert not (external / "reservations").exists()


def test_concurrent_records_share_the_project_sidecar_reservation(
    tmp_path: Path, run_tangle: RunTangle, bt_command: Callable[[], list[str]]
) -> None:
    repo = tmp_path / "repo"
    nodes = _write_vault(repo / ".tangle")
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    env = _record_env(tmp_path, "record-race")
    assert run_tangle("init", cwd=repo, env=env).returncode == 0

    workers = 4
    children = [
        subprocess.Popen(
            [
                *bt_command(),
                "node",
                "record",
                "--type",
                "TAS",
                "--summary",
                f"Capture worker {index}.",
                "--body",
                _RECORD_BODY,
                "--next",
                "Add the boundary test.",
                "--slug",
                f"worker-{index}",
            ],
            cwd=str(repo),
            env=env,
            stdout=subprocess.PIPE,
            text=True,
        )
        for index in range(workers)
    ]
    ids: list[str] = []
    for process in children:
        output, _ = process.communicate(timeout=60)
        assert process.returncode == 0, output
        match = re.search(r'^id: "(tas-[0-7][0-9a-hjkmnp-tv-z]{25})"$', output, re.MULTILINE)
        assert match is not None, output
        ids.append(match.group(1))

    assert len(set(ids)) == workers
    assert not (nodes / "reservations").exists()
