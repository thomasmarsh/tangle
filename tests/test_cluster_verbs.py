"""Capability-path tests for the ``clusters`` and ``digest`` answer verbs.

``tangle clusters`` is an explicit derived answer: with the optional semantic
extra installed and a provider configured it embeds the vault, clusters it
advisoriy, and prints bounded TOON; with either missing it prints one advisory
line and exits zero without loading a heavy module. ``tangle digest`` is a
pure graph answer over a hub's or coordinating node's unresolved direct members,
so it stays on the fast path. These tests drive the absent path through the real
command, the derived answer with deterministic stand-in clusterer and reducer
functions (so the default ``make test`` environment needs no extra), and the
real runtime only when the extra is present.
"""

from __future__ import annotations

import hashlib
import os
import shlex
import sqlite3
import subprocess
import sys
from collections.abc import Callable, Sequence
from pathlib import Path

import pytest

from tangle import clustering, index, main, reduction, semantic

RunTangle = Callable[..., subprocess.CompletedProcess[str]]

_ROOT = Path(__file__).resolve().parents[1]
# The heavy modules only the opt-in semantic extra provides.
_HEAVY_MODULES = ("numpy", "sklearn", "umap", "hdbscan", "fastembed")

# Running the absent path in a fresh interpreter is the only way to observe the
# real import graph: the command must answer without one heavy module loaded.
_IMPORT_PROBE = """\
import sys
from tangle import main

assert main.main(["clusters"]) == 0
assert main.main(["digest", "IDX-001"]) == 0
print("heavy:" + ",".join(name for name in sys.argv[1:] if name in sys.modules))
"""

# A deterministic stand-in provider: a node whose text names a group projects
# onto that group's axis with a small per-text jitter, so two well-separated
# groups cluster cleanly under the real runtime without a model.
_PROVIDER = """\
import hashlib
import json
import sys

AXES = {"alpha": 0, "beta": 1}


def vector(text):
    values = [0.0, 0.0]
    for token in text.lower().split():
        slot = AXES.get(token)
        if slot is not None:
            values[slot] = 3.0
    digest = hashlib.sha256(text.encode("utf-8")).digest()
    values[0] += (digest[0] / 255.0 - 0.5) * 0.2
    values[1] += (digest[1] / 255.0 - 0.5) * 0.2
    return values


print(json.dumps([vector(text) for text in json.load(sys.stdin)]))
"""


class RowsClusterer:
    """A deterministic, row-wise stand-in for HDBSCAN.

    A row whose first coordinate is zero is noise, a positive row is cluster
    ``0`` and a negative row is cluster ``1``; the score is zero everywhere.
    """

    def __call__(
        self, matrix: Sequence[Sequence[float]], params: clustering.ClusterParams
    ) -> tuple[list[int], list[float]]:
        labels = [(-1 if float(row[0]) == 0 else (0 if float(row[0]) > 0 else 1)) for row in matrix]
        return labels, [0.0] * len(matrix)


class IdentityReducer:
    """A stand-in reduction returning each input's first two coordinates."""

    def __call__(
        self,
        method: str,
        matrix: Sequence[Sequence[float]],
        params: reduction.ReductionParams,
    ) -> list[list[float]]:
        return [[float(row[0]), float(row[1])] for row in matrix]


def _env(tmp_path: Path, vault: Path) -> dict[str, str | None]:
    return {
        "TANGLE_SIDECAR_DIR": str(tmp_path / "sidecar"),
        "TANGLE_PROJECT_ID": "cluster-verbs-test",
        "TANGLE_NODES_DIR": str(vault),
        "TANGLE_SEMANTIC_PROVIDER": None,
        "TANGLE_MODEL_CACHE": None,
        "HF_HOME": None,
    }


def _write_hub_vault(vault: Path) -> None:
    """Seed one hub with ordered, resolved, and route-less members."""
    (vault / "resolved").mkdir(parents=True)
    (vault / "active").mkdir()
    (vault / "blocked").mkdir()
    (vault / "index-map.md").write_text("# Focus\n\n# Root hubs\n", encoding="utf-8")
    (vault / "resolved" / "IDX-001-engine.md").write_text(
        "---\ncontext_rev: 1\nupdated: 2026-01-01T00:00:00Z\n"
        "summary: Engine root.\n---\n\n# Invariant\n\nDurable root hub.\n",
        encoding="utf-8",
    )
    members = (
        ("active", "TAS-001", "P2", "Second by priority.", "Do the second thing."),
        ("active", "TAS-002", "P0", "First by priority.", "Do the first thing."),
        ("blocked", "TAS-003", "", "No priority, blocked.", "Request the fixture."),
        ("active", "TAS-004", "", "No priority, active.", "Do the unprioritized thing."),
    )
    for status, node_id, priority, summary, next_action in members:
        fields = ["---", "context_rev: 1"]
        if priority:
            fields.append(f"priority: {priority}")
        fields.extend(
            [
                "updated: 2026-01-02T00:00:00Z",
                f"summary: {summary}",
                f"next: {next_action}",
                "---",
                "",
                "# Context",
                "",
                "Parent [[IDX-001-engine]].",
                "",
            ]
        )
        (vault / status / f"{node_id}-work.md").write_text(
            "\n".join(fields), encoding="utf-8"
        )
    (vault / "resolved" / "TAS-005-done.md").write_text(
        "---\ncontext_rev: 1\nupdated: 2026-01-02T00:00:00Z\n"
        "summary: Already resolved.\n---\n\n# Context\n\nParent [[IDX-001-engine]].\n",
        encoding="utf-8",
    )


def _write_embed_vault(vault: Path) -> None:
    """Seed two well-separated groups under one hub for the real-runtime test."""
    (vault / "resolved").mkdir(parents=True)
    (vault / "active").mkdir()
    (vault / "resolved" / "IDX-001-engine.md").write_text(
        "---\ncontext_rev: 1\nupdated: 2026-01-01T00:00:00Z\n"
        "summary: Engine root.\n---\n\n# Invariant\n\nDurable root hub.\n",
        encoding="utf-8",
    )
    for number in range(12):
        token = "alpha" if number < 6 else "beta"
        (vault / "active" / f"TAS-{number:03d}-{token}.md").write_text(
            "---\ncontext_rev: 1\npriority: P1\nupdated: 2026-01-02T00:00:00Z\n"
            f"summary: {token} node {number}.\nnext: Keep {token}.\n---\n\n# Context\n\n"
            "Parent [[IDX-001-engine]].\n",
            encoding="utf-8",
        )


def test_clusters_absent_path_is_one_advisory_line(
    tmp_path: Path, run_tangle: RunTangle
) -> None:
    """No provider means an advisory line, exit zero, and no model load."""
    vault = tmp_path / "nodes"
    _write_hub_vault(vault)
    result = run_tangle("clusters", env=_env(tmp_path, vault))
    assert result.returncode == 0
    assert result.stderr == ""
    lines = result.stdout.splitlines()
    assert lines[0] == 'advisory: "clusters are advisory, derived, and are not work claims"'
    assert 'clusters: "capability absent"' in result.stdout


def test_clusters_present_path_is_bounded_and_advisory(
    tmp_path: Path, run_tangle_inproc: RunTangle
) -> None:
    """A malformed provider still degrades to the advisory capability-absent line."""
    vault = tmp_path / "nodes"
    _write_hub_vault(vault)
    env = _env(tmp_path, vault)
    env["TANGLE_SEMANTIC_PROVIDER"] = "definitely-not-a-provider-command"
    result = run_tangle_inproc("clusters", env=env)
    assert result.returncode == 0
    assert 'clusters: "capability absent"' in result.stdout


def test_clusters_rejects_an_unknown_argument(tmp_path: Path, run_tangle_inproc: RunTangle) -> None:
    vault = tmp_path / "nodes"
    _write_hub_vault(vault)
    result = run_tangle_inproc("clusters", "--bogus", env=_env(tmp_path, vault))
    assert result.returncode == 2
    assert 'error: "unknown argument for clusters: --bogus"' in result.stdout


def test_clusters_present_path_answers_with_bounded_toon(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """With the capability present the verb prints bounded TOON and the advisory line.

    The semantic probe and derived answer are stubbed so the formatting and
    gating the CLI owns are exercised without the opt-in extra, while the heavy
    derived logic is covered separately with deterministic stand-ins.
    """
    vault = tmp_path / "nodes"
    _write_hub_vault(vault)
    monkeypatch.setenv("TANGLE_NODES_DIR", str(vault))
    monkeypatch.setenv("TANGLE_SIDECAR_DIR", str(tmp_path / "sidecar"))
    monkeypatch.setenv("TANGLE_PROJECT_ID", "cluster-verbs-present")
    monkeypatch.setattr(
        semantic, "extra", lambda: semantic.SemanticExtra(modules=(), model_cache=tmp_path)
    )
    monkeypatch.setattr(
        semantic,
        "probe",
        lambda command=None: semantic.SemanticProvider(command="stub", key="k", dimensions=2),
    )
    monkeypatch.setattr(semantic, "vectors", lambda provider, connection, items: {})
    monkeypatch.setattr(
        index,
        "cluster_source",
        lambda root, limit: [index.ClusterSource("TAS-001", "h", "t", "IDX-001")],
    )
    params = clustering.parameters(12, clustering.ClusterParams(min_cluster_size=3, min_samples=1))
    fake = clustering.ClusterAnswer(
        available=True,
        reason="",
        space="reduced",
        method="umap",
        params=params,
        stability=(
            clustering.Stability(space="raw", runs=4, ari=0.25),
            clustering.Stability(space="reduced", runs=4, ari=0.9),
        ),
        clusters=(
            clustering.Cluster(
                id=0,
                representative="TAS-001",
                route="IDX-001",
                routes=("IDX-001",),
                members=("TAS-001", "TAS-002"),
            ),
        ),
        total_clusters=3,
        over_broad=(clustering.OverBroadRoute(route="IDX-001", clusters=2, members=5),),
        total_over_broad=2,
        noise=("TAS-050",),
        total_noise=4,
        outliers=("TAS-003",),
        total_outliers=1,
    )
    monkeypatch.setattr(clustering, "answer", lambda *arguments, **keywords: fake)

    assert main.main(["clusters", "--limit", "2"]) == 0

    stdout = capsys.readouterr().out
    lines = stdout.splitlines()
    assert lines[0] == 'advisory: "clusters are advisory, derived, and are not work claims"'
    assert 'limit: "2"' in stdout
    assert "clusters_total: \"3\"" in stdout
    assert 'clusters[1]{id,representative,route,members}:' in stdout
    assert 'over_broad[1]{route,clusters,members}:' in stdout
    assert 'noise_total: "4"' in stdout
    assert 'outliers_total: "1"' in stdout


def test_digest_lists_unresolved_members_by_priority(
    tmp_path: Path, run_tangle_inproc: RunTangle
) -> None:
    """The digest is bounded, ordered, and excludes resolved members."""
    vault = tmp_path / "nodes"
    _write_hub_vault(vault)
    result = run_tangle_inproc("digest", "IDX-001-engine", env=_env(tmp_path, vault))
    assert result.returncode == 0
    assert result.stderr == ""
    assert 'target: "IDX-001"' in result.stdout
    assert 'status: "resolved"' in result.stdout
    assert 'total: "4"' in result.stdout
    members = [line for line in result.stdout.splitlines() if line.startswith('  "TAS-')]
    assert [member.strip().split(",")[0] for member in members] == [
        '"TAS-002"',
        '"TAS-001"',
        '"TAS-003"',
        '"TAS-004"',
    ]
    assert "TAS-005" not in result.stdout

    bounded = run_tangle_inproc(
        "digest", "IDX-001-engine", "--limit", "2", env=_env(tmp_path, vault)
    )
    assert 'total: "4"' in bounded.stdout
    rows = [line for line in bounded.stdout.splitlines() if line.startswith("  ")]
    assert len(rows) == 2


def test_digest_unknown_node_is_an_error(
    tmp_path: Path, run_tangle_inproc: RunTangle
) -> None:
    vault = tmp_path / "nodes"
    _write_hub_vault(vault)
    result = run_tangle_inproc("digest", "IDX-999", env=_env(tmp_path, vault))
    assert result.returncode == 1
    assert 'error: "unknown node: IDX-999"' in result.stdout


def test_digest_uses_a_bare_id_or_a_full_name(tmp_path: Path) -> None:
    vault = tmp_path / "nodes"
    _write_hub_vault(vault)
    by_id = index.digest(str(vault), "IDX-001", 10)
    by_name = index.digest(str(vault), "IDX-001-engine", 10)
    assert by_id is not None and by_name is not None
    assert by_id == by_name
    assert index.digest(str(vault), "IDX-999", 10) is None


def test_cluster_source_is_bounded_and_hash_ordered(tmp_path: Path) -> None:
    """The source list is content-hash ordered and truncated to the limit."""
    vault = tmp_path / "nodes"
    _write_hub_vault(vault)
    sources = index.cluster_source(str(vault), 10)
    assert [source.content_hash for source in sources] == sorted(
        source.content_hash for source in sources
    )
    assert {source.id for source in sources} == {
        "IDX-001",
        "TAS-001",
        "TAS-002",
        "TAS-003",
        "TAS-004",
        "TAS-005",
    }
    assert all(source.route == "IDX-001" for source in sources if source.id != "IDX-001")
    assert len(index.cluster_source(str(vault), 2)) == 2


def test_answer_is_bounded_and_reports_over_broad_routes(tmp_path: Path) -> None:
    """The derived answer truncates each tuple and keeps the unbounded totals."""
    connection = sqlite3.connect(tmp_path / "sidecar.sqlite3")
    vectors = {
        **{f"a{index:02d}": [3.0, float(index)] for index in range(6)},
        **{f"b{index:02d}": [-3.0, float(index)] for index in range(6)},
    }
    nodes = {
        key: clustering.NodeFacts(
            node_id=key.upper(), route="IDX-001" if number < 9 else "IDX-002"
        )
        for number, key in enumerate(sorted(vectors))
    }
    answer = clustering.answer(
        vectors,
        "key",
        connection,
        nodes,
        limit=1,
        params=clustering.ClusterParams(min_cluster_size=3, min_samples=1),
        reducer=IdentityReducer(),
        clusterer=RowsClusterer(),
    )

    assert answer.available
    assert len(answer.clusters) == 1 and answer.total_clusters == 2
    assert len(answer.over_broad) == 1 and answer.total_over_broad == 1
    assert [route.route for route in answer.over_broad] == ["IDX-001"]
    assert answer.over_broad[0].clusters == 2
    assert answer.over_broad[0].members == 9
    assert len(answer.noise) <= 1 and len(answer.outliers) <= 1


def test_answer_refuses_a_non_positive_limit(tmp_path: Path) -> None:
    connection = sqlite3.connect(tmp_path / "sidecar.sqlite3")
    with pytest.raises(clustering.ClusterError):
        clustering.answer({}, "key", connection, None, 0)


def test_similar_absent_path_is_byte_identical_to_the_lexical_baseline(
    tmp_path: Path, run_tangle_inproc: RunTangle
) -> None:
    """An absent or failed provider leaves the default ``similar`` answer untouched."""
    vault = tmp_path / "nodes"
    _write_hub_vault(vault)
    env = _env(tmp_path, vault)
    lexical = run_tangle_inproc("similar", "alpha beta priority", env=env)
    env["TANGLE_SEMANTIC_PROVIDER"] = "definitely-not-a-provider-command"
    degraded = run_tangle_inproc("similar", "alpha beta priority", env=env)
    assert degraded.returncode == 0
    assert degraded.stdout == lexical.stdout


def test_absent_paths_import_no_heavy_module(tmp_path: Path) -> None:
    """A plain install answers ``clusters`` and ``digest`` without a heavy import."""
    vault = _ROOT / ".tangle"
    env = os.environ.copy()
    for name in ("TANGLE_SEMANTIC_PROVIDER", "TANGLE_MODEL_CACHE", "HF_HOME"):
        env.pop(name, None)
    env["TANGLE_NODES_DIR"] = str(vault)
    env["TANGLE_SIDECAR_DIR"] = str(tmp_path / "sidecar")
    env["TANGLE_PROJECT_ID"] = "cluster-verbs-import"
    probe = subprocess.run(
        [sys.executable, "-c", _IMPORT_PROBE, *_HEAVY_MODULES],
        cwd=str(_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    assert probe.returncode == 0, probe.stderr
    report = [line for line in probe.stdout.splitlines() if line.startswith("heavy:")]
    assert report == ["heavy:"]


def _require_extra() -> None:
    """Skip a real-runtime test unless the optional semantic extra is installed."""
    for module in ("numpy", "sklearn", "umap", "hdbscan"):
        pytest.importorskip(module)


def test_real_runtime_clusters_the_live_style_vault(
    tmp_path: Path, run_tangle_inproc: RunTangle
) -> None:
    """The shipped runtime wires the embedding, reduction, and clustering layers."""
    _require_extra()
    vault = tmp_path / "nodes"
    _write_embed_vault(vault)
    digest = hashlib.sha256(_PROVIDER.encode("utf-8")).hexdigest()[:8]
    script = tmp_path / f"provider-{digest}.py"
    script.write_text(_PROVIDER, encoding="utf-8")
    env = _env(tmp_path, vault)
    env["TANGLE_SEMANTIC_PROVIDER"] = shlex.join([sys.executable, str(script)])

    result = run_tangle_inproc("clusters", "--limit", "2", env=env)
    assert result.returncode == 0
    assert result.stderr == ""
    lines = result.stdout.splitlines()
    assert lines[0] == 'advisory: "clusters are advisory, derived, and are not work claims"'
    assert 'limit: "2"' in result.stdout
    assert '"reduced"' in result.stdout or '"raw"' in result.stdout
    total_line = next(
        line for line in result.stdout.splitlines() if line.startswith("clusters_total:")
    )
    assert int(total_line.split('"')[1]) >= 1
