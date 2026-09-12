"""Pytest port of ``tests/bt-verification.sh`` for the Python ``bt``.

Disposable correctness screen for the external sidecar: cross-process claim
and allocation contention, lease expiry, base-hash mismatch, Markdown
immutability during reindex, recovery after database loss, shared
Git-common-dir identity across worktrees, and the network-filesystem guard.
"""

from __future__ import annotations

import os
import re
import sqlite3
import subprocess
from collections.abc import Callable
from pathlib import Path

BtCommand = Callable[[], list[str]]


def _env(**overrides: str | None) -> dict[str, str]:
    env = os.environ.copy()
    for key, value in overrides.items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = value
    return env


def _seed_vault(vault: Path) -> None:
    (vault / "resolved").mkdir(parents=True)
    (vault / "active").mkdir()
    (vault / "resolved" / "IDX-001-root.md").write_text(
        "---\ncontext_rev: 1\nupdated: 2026-09-11T00:00:00Z\nsummary: Root.\n---\n"
        "\n# Invariant\n\nRoot.\n",
        encoding="utf-8",
    )
    (vault / "resolved" / "DEF-001-definition.md").write_text(
        "---\ncontext_rev: 2\nupdated: 2026-09-11T00:00:00Z\n"
        "summary: Durable definition.\n---\n\n# Context\n\nArea [[IDX-001-root]].\n"
        "\n# Invariant\n\nSearch needle.\n",
        encoding="utf-8",
    )
    (vault / "active" / "TAS-001-consumer.md").write_text(
        "---\ncontext_rev: 1\nupdated: 2026-09-11T00:00:00Z\nsummary: Consumer.\n"
        "next: Reconcile.\n---\n\n# Context\n\nParent [[IDX-001-root]].\n\n"
        "Depends on [[DEF-001-definition]] at context_rev 1.\n",
        encoding="utf-8",
    )


def test_claim_contention_produces_one_owner(
    tmp_path: Path, bt_command: BtCommand
) -> None:
    env = _env(
        BT_SIDECAR_DIR=str(tmp_path / "sidecar"),
        BT_PROJECT_ID="verification-test",
    )
    subprocess.run([*bt_command(), "init"], env=env, capture_output=True, check=True)
    command = [
        *bt_command(),
        "claim",
        "TAS-900",
        "agent-a",
        "--base-hash",
        "hash-a",
        "--lease-seconds",
        "60",
    ]
    other = list(command)
    other[3] = "agent-b"
    stdout = subprocess.PIPE
    stderr = subprocess.STDOUT
    first = subprocess.Popen(command, env=env, stdout=stdout, stderr=stderr, text=True)
    second = subprocess.Popen(other, env=env, stdout=stdout, stderr=stderr, text=True)
    outputs = [first.communicate()[0], second.communicate()[0]]
    claimed = sum('result: "claimed"' in output for output in outputs)
    assert claimed == 1


def test_concurrent_allocation_is_unique_and_dense(
    tmp_path: Path, bt_command: BtCommand
) -> None:
    env = _env(
        BT_SIDECAR_DIR=str(tmp_path / "sidecar"),
        BT_PROJECT_ID="verification-test",
    )
    subprocess.run([*bt_command(), "init"], env=env, capture_output=True, check=True)
    processes = [
        subprocess.Popen(
            [*bt_command(), "allocate", "CON"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )
        for _ in range(8)
    ]
    outputs = [process.communicate()[0] for process in processes]
    assert all(process.returncode == 0 for process in processes)
    ids = sorted(
        match.group(1)
        for output in outputs
        if (match := re.search(r'^id: "(.*)"$', output, re.MULTILINE)) is not None
    )
    assert len(set(ids)) == 8
    assert ids == [f"CON-{number:03d}" for number in range(1, 9)]


def test_expiry_and_base_hash_mismatch(tmp_path: Path, bt_command: BtCommand) -> None:
    sidecar = tmp_path / "sidecar"
    env = _env(BT_SIDECAR_DIR=str(sidecar), BT_PROJECT_ID="verification-test")
    command = bt_command()
    subprocess.run([*command, "init"], env=env, capture_output=True, check=True)
    subprocess.run(
        [*command, "claim", "TAS-901", "agent-a", "--base-hash", "old", "--lease-seconds", "60"],
        env=env,
        capture_output=True,
        check=True,
    )
    database = sidecar / "projects" / "verification-test" / "graph.sqlite3"
    connection = sqlite3.connect(database)
    try:
        connection.execute("UPDATE claims SET lease_expires_at=0 WHERE node_id='TAS-901';")
        connection.commit()
    finally:
        connection.close()
    reclaimed = subprocess.run(
        [*command, "claim", "TAS-901", "agent-b", "--base-hash", "new", "--lease-seconds", "60"],
        env=env,
        capture_output=True,
        text=True,
    )
    assert 'agent: "agent-b"' in reclaimed.stdout
    mismatch = subprocess.run(
        [
            *command,
            "claim",
            "TAS-901",
            "agent-b",
            "--base-hash",
            "changed",
            "--lease-seconds",
            "60",
        ],
        env=env,
        capture_output=True,
        text=True,
    )
    assert "different base hash" in mismatch.stdout


def test_reindex_is_read_only_and_recovers(
    tmp_path: Path, bt_command: BtCommand
) -> None:
    vault = tmp_path / "vault" / "nodes"
    _seed_vault(vault)
    env = _env(
        BT_SIDECAR_DIR=str(tmp_path / "sidecar"),
        BT_PROJECT_ID="verification-test",
        BT_NODES_DIR=str(vault),
    )
    command = bt_command()
    before = {
        path: path.read_bytes() for path in sorted(vault.rglob("*.md"))
    }
    subprocess.run([*command, "index", str(vault)], env=env, capture_output=True, check=True)
    search = subprocess.run([*command, "search", "needle"], env=env, capture_output=True, text=True)
    assert '"DEF-001","resolved"' in search.stdout
    backlinks = subprocess.run(
        [*command, "backlinks", "DEF-001"], env=env, capture_output=True, text=True
    )
    assert '"TAS-001","active","Depends on","1"' in backlinks.stdout
    stale = subprocess.run([*command, "stale"], env=env, capture_output=True, text=True)
    assert '"TAS-001","active","DEF-001","1","2"' in stale.stdout
    after = {
        path: path.read_bytes() for path in sorted(vault.rglob("*.md"))
    }
    assert before == after

    database = tmp_path / "sidecar" / "projects" / "verification-test" / "graph.sqlite3"
    database.unlink()
    subprocess.run([*command, "index", str(vault)], env=env, capture_output=True, check=True)
    recovered = subprocess.run(
        [*command, "search", "needle"], env=env, capture_output=True, text=True
    )
    assert '"DEF-001","resolved"' in recovered.stdout


def test_worktrees_share_project_identity(
    tmp_path: Path, bt_command: BtCommand
) -> None:
    repo = tmp_path / "repo"
    tree_a = tmp_path / "tree-a"
    tree_b = tmp_path / "tree-b"
    subprocess.run(["git", "init", "-q", "-b", "main", str(repo)], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "config", "user.email", "bt-test@example.invalid"], check=True
    )
    subprocess.run(["git", "-C", str(repo), "config", "user.name", "BT Test"], check=True)
    (repo / "README.md").write_text("fixture\n", encoding="utf-8")
    subprocess.run(["git", "-C", str(repo), "add", "README.md"], check=True)
    subprocess.run(["git", "-C", str(repo), "commit", "-qm", "fixture"], check=True)
    subprocess.run(
        ["git", "-C", str(repo), "worktree", "add", "-q", "-b", "tree-a", str(tree_a), "main"],
        check=True,
    )
    subprocess.run(
        ["git", "-C", str(repo), "worktree", "add", "-q", "-b", "tree-b", str(tree_b), "main"],
        check=True,
    )
    env = _env(BT_SIDECAR_DIR=str(tmp_path / "sidecar"), BT_PROJECT_ID=None)
    command = bt_command()

    def project_id(cwd: Path) -> str:
        result = subprocess.run(
            [*command, "location"], cwd=cwd, env=env, capture_output=True, text=True, check=True
        )
        match = re.search(r'^project_id: "(.*)"$', result.stdout, re.MULTILINE)
        assert match is not None
        return match.group(1)

    identity_a = project_id(tree_a)
    identity_b = project_id(tree_b)
    assert identity_a and identity_a == identity_b

    subprocess.run(
        [*command, "claim", "TAS-902", "tree-a", "--base-hash", "base", "--lease-seconds", "60"],
        cwd=tree_a,
        env=env,
        capture_output=True,
        check=True,
    )
    conflict = subprocess.run(
        [*command, "claim", "TAS-902", "tree-b", "--base-hash", "base", "--lease-seconds", "60"],
        cwd=tree_b,
        env=env,
        capture_output=True,
        text=True,
    )
    assert "claimed by tree-a" in conflict.stdout


def test_network_guard_refuses_sidecar(tmp_path: Path, bt_command: BtCommand) -> None:
    mock_bin = tmp_path / "mock-bin"
    mock_bin.mkdir()
    df = mock_bin / "df"
    df.write_text(
        "#!/bin/sh\n"
        "printf '%s\\n' \"Filesystem 1024-blocks Used Available Capacity Mounted on\" "
        '"server:/bt 1 1 0 100% /mock"\n',
        encoding="utf-8",
    )
    df.chmod(0o755)
    env = _env(
        BT_PROJECT_ID="network-guard",
        BT_SIDECAR_DIR=str(tmp_path / "network-sidecar"),
        PATH=f"{mock_bin}{os.pathsep}{os.environ.get('PATH', '')}",
    )
    result = subprocess.run(
        [*bt_command(), "init"], env=env, capture_output=True, text=True
    )
    assert result.returncode == 1
    assert "filesystem appears network-mounted" in result.stdout
