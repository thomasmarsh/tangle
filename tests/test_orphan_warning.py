"""Behavioral tests for the orphan warning on the direct-answer verbs.

An unfinished node that cannot reach a hub is a graph-integrity failure that
``tangle check`` reports as a ``route-orphan`` error. The direct-answer verbs
a client actually calls — ``frontier``, ``next``, ``orient``, and ``status`` —
must surface the same finding as a loud stderr warning without failing the
interaction or corrupting their machine-readable TOON on stdout.
"""

from __future__ import annotations

import subprocess
from collections.abc import Callable
from pathlib import Path

import pytest

RunTangle = Callable[..., subprocess.CompletedProcess[str]]

_DIRECT_ANSWER_VERBS = ("frontier", "next", "orient", "packet", "status")


def _env(tmp_path: Path, vault: Path) -> dict[str, str]:
    return {
        "TANGLE_SIDECAR_DIR": str(tmp_path / "sidecar"),
        "TANGLE_PROJECT_ID": "orphan-warning-test",
        "TANGLE_NODES_DIR": str(vault),
    }


def _write(path: Path, text: str) -> None:
    path.write_text(text, encoding="utf-8")


def _seed(vault: Path, *, orphan: bool) -> None:
    """Build one healthy routed node and, optionally, one unreachable node."""
    (vault / "resolved").mkdir(parents=True)
    (vault / "active").mkdir()
    _write(vault / "index-map.md", "# Root hubs\n\n- Indexes [[IDX-001-root]]\n")
    _write(
        vault / "resolved" / "IDX-001-root.md",
        "---\ncontext_rev: 1\nupdated: 2026-09-11T00:00:00Z\n"
        "summary: Root graph entry.\n---\n\n# Invariant\n\nRoot content finds all work.\n",
    )
    _write(
        vault / "active" / "TAS-001-routed.md",
        "---\ncontext_rev: 1\npriority: P1\nupdated: 2026-09-11T00:00:00Z\n"
        "summary: Routed work.\nnext: Do the routed work.\n---\n\n"
        "# Context\n\nParent [[IDX-001-root]].\n",
    )
    if orphan:
        _write(
            vault / "active" / "TAS-002-orphan.md",
            "---\ncontext_rev: 1\nupdated: 2026-09-11T00:00:00Z\n"
            "summary: Unreachable work.\nnext: Finish the orphan.\n---\n\n"
            "# Context\n\nNo route to a hub.\n",
        )


@pytest.mark.parametrize("verb", _DIRECT_ANSWER_VERBS)
def test_each_direct_answer_verb_warns_on_an_orphan(
    tmp_path: Path, run_tangle_inproc: RunTangle, verb: str
) -> None:
    """Every direct-answer verb surfaces the orphan without failing."""
    vault = tmp_path / "nodes"
    _seed(vault, orphan=True)
    result = run_tangle_inproc(verb, env=_env(tmp_path, vault))
    assert result.returncode == 0
    assert "cannot reach a hub" in result.stderr
    assert "TAS-002-orphan.md" in result.stderr
    # The machine-readable answer on stdout stays clean; the warning is stderr.
    assert "warning:" not in result.stdout


@pytest.mark.parametrize("verb", _DIRECT_ANSWER_VERBS)
def test_healthy_graph_has_no_orphan_warning(
    tmp_path: Path, run_tangle_inproc: RunTangle, verb: str
) -> None:
    """A reachable graph produces no warning and no stderr noise."""
    vault = tmp_path / "nodes"
    _seed(vault, orphan=False)
    result = run_tangle_inproc(verb, env=_env(tmp_path, vault))
    assert result.returncode == 0
    assert result.stderr == ""


def test_routing_the_orphan_silences_the_warning(
    tmp_path: Path, run_tangle_inproc: RunTangle
) -> None:
    """Falsification probe: the warning follows reachability, not the node."""
    vault = tmp_path / "nodes"
    _seed(vault, orphan=True)
    warned = run_tangle_inproc("frontier", env=_env(tmp_path, vault))
    assert "cannot reach a hub" in warned.stderr

    orphan = vault / "active" / "TAS-002-orphan.md"
    _write(
        orphan,
        orphan.read_text(encoding="utf-8") + "\nParent [[IDX-001-root]].\n",
    )
    routed = run_tangle_inproc("frontier", env=_env(tmp_path, vault))
    assert routed.returncode == 0
    assert routed.stderr == ""


def test_check_keeps_its_route_orphan_error_and_allow_orphan(
    tmp_path: Path, run_tangle: RunTangle
) -> None:
    """``check`` keeps its non-zero error and its ``--allow-orphan`` exception."""
    vault = tmp_path / "nodes"
    _seed(vault, orphan=True)
    checked = run_tangle("check", env=_env(tmp_path, vault))
    assert checked.returncode == 1
    assert "orphan unfinished node" in checked.stderr
    allowed = run_tangle("check", "--allow-orphan", "TAS-002-orphan", env=_env(tmp_path, vault))
    assert allowed.returncode == 0
    assert "graph check: passed" in allowed.stdout
