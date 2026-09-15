"""Behavioral tests for automatic derived-index upkeep.

The derived index is derived, disposable local state that a client never
maintains by hand. When local coordination state exists, every dispatched
interaction brings the index up to date from Markdown: a read-only answer and a
mutating capture both leave it current, an unchanged vault writes nothing, a
lost index is restored from Markdown alone, and a broken index warns on stderr
without changing the answer or the exit code. A read-only interaction never
creates that state in the first place.
"""

from __future__ import annotations

import hashlib
import re
import sqlite3
import subprocess
import time
from collections.abc import Callable
from pathlib import Path

RunTangle = Callable[..., subprocess.CompletedProcess[str]]

_PROJECT = "index-upkeep-test"


def _env(tmp_path: Path, vault: Path) -> dict[str, str]:
    return {
        "TANGLE_SIDECAR_DIR": str(tmp_path / "sidecar"),
        "TANGLE_PROJECT_ID": _PROJECT,
        "TANGLE_NODES_DIR": str(vault),
    }


def _database(tmp_path: Path) -> Path:
    return tmp_path / "sidecar" / "projects" / _PROJECT / "graph.sqlite3"


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _frontmatter(summary: str, next_line: str | None = None) -> str:
    lines = [
        "---",
        "context_rev: 1",
        "updated: 2026-09-11T00:00:00Z",
        f"summary: {summary}",
    ]
    if next_line is not None:
        lines.append(f"next: {next_line}")
    lines.extend(["---", ""])
    return "\n".join(lines) + "\n"


def _seed(vault: Path) -> None:
    """Write one hub, one routed member, and the index route the capture reads."""
    (vault / "resolved").mkdir(parents=True)
    (vault / "active").mkdir()
    _write(vault / "index-map.md", "# Root hubs\n\n- Indexes [[IDX-001-root]]\n")
    _write(
        vault / "resolved" / "IDX-001-root.md",
        _frontmatter("Root graph entry.")
        + "\n# Invariant\n\nRoot content finds all work.\n",
    )
    _write(
        vault / "active" / "TAS-001-consumer.md",
        _frontmatter("Consume the root.", "Reconcile the root.")
        + "\n# Context\n\nParent [[IDX-001-root]].\n",
    )


def _add_node(vault: Path, name: str, summary: str) -> Path:
    path = vault / "active" / f"{name}.md"
    _write(
        path,
        _frontmatter(summary, "Keep the derived index current.")
        + "\n# Context\n\nParent [[IDX-001-root]].\n",
    )
    return path


def _snapshot(database: Path) -> tuple[dict[str, tuple[str, str]], set[tuple[str, str, str, str]]]:
    """Return the stored node identity rows and the stored edge rows."""
    connection = sqlite3.connect(database)
    try:
        nodes = {
            str(node_id): (str(path), str(content_hash))
            for node_id, path, content_hash in connection.execute(
                "SELECT id, path, content_hash FROM nodes"
            )
        }
        edges = {
            (str(source), str(relation), str(target), str(pin))
            for source, relation, target, pin in connection.execute(
                "SELECT source_id, relation, target_id, COALESCE(pinned_context_rev,'') "
                "FROM edges"
            )
        }
    finally:
        connection.close()
    return nodes, edges


def _indexed_at(database: Path) -> dict[str, str]:
    connection = sqlite3.connect(database)
    try:
        return {
            str(node_id): str(stamp)
            for node_id, stamp in connection.execute("SELECT id, indexed_at FROM nodes")
        }
    finally:
        connection.close()


def test_a_read_only_interaction_maintains_the_index(
    tmp_path: Path, run_tangle: RunTangle
) -> None:
    """`frontier` leaves a hand-authored node indexed with no client step."""
    vault = tmp_path / "nodes"
    _seed(vault)
    env = _env(tmp_path, vault)
    assert run_tangle("init", env=env).returncode == 0

    added = _add_node(vault, "TAS-002-edited-by-hand", "Edit the vault directly.")
    expected = hashlib.sha256(added.read_bytes()).hexdigest()

    answered = run_tangle("frontier", env=env)
    assert answered.returncode == 0
    assert answered.stderr == ""
    nodes, edges = _snapshot(_database(tmp_path))
    assert nodes["TAS-002"][1] == expected
    assert nodes["TAS-001"][1] == hashlib.sha256(
        (vault / "active" / "TAS-001-consumer.md").read_bytes()
    ).hexdigest()
    assert ("TAS-001", "Parent", "IDX-001", "") in edges
    assert ("TAS-002", "Parent", "IDX-001", "") in edges


def test_a_mutating_interaction_maintains_the_index(
    tmp_path: Path, run_tangle: RunTangle
) -> None:
    """A capture leaves the node it just wrote indexed with no client step."""
    vault = tmp_path / "nodes"
    _seed(vault)
    env = _env(tmp_path, vault)
    assert run_tangle("init", env=env).returncode == 0

    recorded = run_tangle(
        "node",
        "record",
        "--type",
        "TAS",
        "--summary",
        "Record through the capture path.",
        "--body",
        "# Outcome\n\nRecord the node.",
        "--next",
        "Verify the index.",
        env=env,
    )
    assert recorded.returncode == 0, recorded.stdout
    match = re.search(r'id: "(tas-[0-7][0-9a-hjkmnp-tv-z]{25})"', recorded.stdout)
    assert match is not None

    nodes, _edges = _snapshot(_database(tmp_path))
    node_id = match.group(1)
    written = next((vault / "canonical").rglob(f"{node_id}-record-through-the-capture-path.md"))
    assert nodes[node_id] == (
        str(written.relative_to(vault)),
        hashlib.sha256(written.read_bytes()).hexdigest(),
    )


def test_upkeep_agrees_with_a_full_rebuild(tmp_path: Path, run_tangle: RunTangle) -> None:
    """The incremental upkeep writes exactly the rows a full rebuild would."""
    vault = tmp_path / "nodes"
    _seed(vault)
    env = _env(tmp_path, vault)
    assert run_tangle("init", env=env).returncode == 0
    _add_node(vault, "TAS-002-edited-by-hand", "Edit the vault directly.")
    assert run_tangle("frontier", env=env).returncode == 0
    incremental = _snapshot(_database(tmp_path))

    assert run_tangle("index", env=env).returncode == 0
    assert _snapshot(_database(tmp_path)) == incremental


def test_upkeep_writes_nothing_when_markdown_is_unchanged(
    tmp_path: Path, run_tangle: RunTangle
) -> None:
    """A second interaction over an unchanged vault rewrites no indexed row."""
    vault = tmp_path / "nodes"
    _seed(vault)
    env = _env(tmp_path, vault)
    assert run_tangle("init", env=env).returncode == 0
    assert run_tangle("frontier", env=env).returncode == 0
    first = _indexed_at(_database(tmp_path))
    assert first

    # ``indexed_at`` has one-second resolution, so a rewrite lands on a new
    # stamp only after the clock advances.
    time.sleep(1.1)
    assert run_tangle("frontier", env=env).returncode == 0
    assert _indexed_at(_database(tmp_path)) == first


def test_upkeep_removes_a_deleted_node_and_its_edges(
    tmp_path: Path, run_tangle: RunTangle
) -> None:
    """A deleted node file takes its rows and edges out of the index."""
    vault = tmp_path / "nodes"
    _seed(vault)
    env = _env(tmp_path, vault)
    assert run_tangle("init", env=env).returncode == 0
    assert run_tangle("frontier", env=env).returncode == 0

    (vault / "active" / "TAS-001-consumer.md").unlink()
    assert run_tangle("frontier", env=env).returncode == 0
    nodes, edges = _snapshot(_database(tmp_path))
    assert set(nodes) == {"IDX-001"}
    assert edges == set()

    assert run_tangle("index", env=env).returncode == 0
    assert _snapshot(_database(tmp_path)) == (nodes, edges)


def test_a_lost_index_is_restored_from_markdown_alone(
    tmp_path: Path, run_tangle: RunTangle
) -> None:
    """Emptied derived rows come back from Markdown with no `index` call."""
    vault = tmp_path / "nodes"
    _seed(vault)
    env = _env(tmp_path, vault)
    assert run_tangle("init", env=env).returncode == 0
    assert run_tangle("frontier", env=env).returncode == 0
    expected = _snapshot(_database(tmp_path))

    connection = sqlite3.connect(_database(tmp_path))
    try:
        connection.execute("DELETE FROM edges")
        connection.execute("DELETE FROM nodes_fts")
        connection.execute("DELETE FROM nodes")
        connection.commit()
    finally:
        connection.close()
    assert _snapshot(_database(tmp_path)) == ({}, set())

    assert run_tangle("frontier", env=env).returncode == 0
    assert _snapshot(_database(tmp_path)) == expected


def test_a_lost_state_file_is_rebuilt_from_markdown(tmp_path: Path, run_tangle: RunTangle) -> None:
    """`tangle index` rebuilds the whole state from Markdown after its loss."""
    vault = tmp_path / "nodes"
    _seed(vault)
    env = _env(tmp_path, vault)
    assert run_tangle("init", env=env).returncode == 0
    assert run_tangle("frontier", env=env).returncode == 0
    _database(tmp_path).unlink()

    rebuilt = run_tangle("index", env=env)
    assert rebuilt.returncode == 0
    assert rebuilt.stdout.splitlines()[:2] == ["nodes: 2", "edges: 1"]
    assert '"TAS-001","active"' in run_tangle("search", "Consume", env=env).stdout


def test_a_read_only_interaction_creates_no_local_state(
    tmp_path: Path, run_tangle: RunTangle
) -> None:
    """An answer that needs no local state does not create any."""
    vault = tmp_path / "nodes"
    _seed(vault)
    result = run_tangle("frontier", env=_env(tmp_path, vault))
    assert result.returncode == 0
    assert result.stderr == ""
    assert not (tmp_path / "sidecar").exists()


def test_concurrent_interactions_converge_on_one_index(
    tmp_path: Path,
    run_tangle: RunTangle,
    bt_command: Callable[[], list[str]],
) -> None:
    """Concurrent upkeep fails no answer and converges on the rebuilt index."""
    vault = tmp_path / "nodes"
    _seed(vault)
    env = _env(tmp_path, vault)
    assert run_tangle("init", env=env).returncode == 0

    processes = [
        subprocess.Popen(
            [*bt_command(), "frontier"],
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
        for _ in range(8)
    ]
    outputs = [process.communicate() for process in processes]
    assert all(process.returncode == 0 for process in processes)
    assert all(not stderr for _stdout, stderr in outputs)

    raced = _snapshot(_database(tmp_path))
    assert raced[0], "concurrent upkeep indexed no nodes"
    assert run_tangle("index", env=env).returncode == 0
    assert _snapshot(_database(tmp_path)) == raced


def test_an_unreadable_derived_input_warns_without_failing(
    tmp_path: Path, run_tangle: RunTangle
) -> None:
    """A node the index cannot read is a warning, not a failed interaction."""
    vault = tmp_path / "nodes"
    _seed(vault)
    (vault / "active" / "BAD-001-undecodable.md").write_bytes(
        b"---\nsummary: \xff\xfe undecodable\n---\n"
    )
    env = _env(tmp_path, vault)
    assert run_tangle("init", env=env).returncode == 0

    allocated = run_tangle("allocate", "CON", env=env)
    assert allocated.returncode == 0
    assert 'id: "CON-001"' in allocated.stdout
    assert "warning: unable to maintain the derived index" in allocated.stderr
    assert "warning:" not in allocated.stdout


def test_a_broken_index_warns_and_still_answers(tmp_path: Path, run_tangle: RunTangle) -> None:
    """Falsification probe: upkeep failure is one warning, never a failed answer."""
    vault = tmp_path / "nodes"
    _seed(vault)
    env = _env(tmp_path, vault)
    assert run_tangle("init", env=env).returncode == 0
    assert run_tangle("frontier", env=env).returncode == 0

    connection = sqlite3.connect(_database(tmp_path))
    try:
        connection.execute("ALTER TABLE nodes RENAME TO nodes_salvage")
        connection.execute("CREATE TABLE nodes(id TEXT)")
        connection.commit()
    finally:
        connection.close()

    answered = run_tangle("frontier", env=env)
    assert answered.returncode == 0
    assert '"TAS-001"' in answered.stdout
    assert "warning:" in answered.stderr
    assert "warning:" not in answered.stdout
