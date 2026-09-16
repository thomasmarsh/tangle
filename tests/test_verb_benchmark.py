"""Contract tests for the direct-answer verb correctness gate."""

from __future__ import annotations

import json

import pytest
from tangle_research import verb_benchmark

from tangle import main as tangle_main

# Benchmark verification spawns the verb gate, so it is opt-in.
pytestmark = pytest.mark.benchmark


def test_repository_module_help_names_development_entry_path(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exit_status:
        verb_benchmark.main(["--help"])
    assert exit_status.value.code == 0
    assert "python -m tangle_research.verb_benchmark" in capsys.readouterr().out


@pytest.mark.parametrize("name", ["verb", "verbs"])
def test_installed_command_reports_repository_only_boundary(
    name: str, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("tangle.main.census.reconcile", lambda: None)
    monkeypatch.setattr(tangle_main, "_maintain_index", lambda _command: None)
    assert tangle_main.main(["benchmark", name]) == 2
    out = capsys.readouterr().out
    assert "unavailable in an ordinary installation" in out
    assert "PYTHONPATH=research uv run python -m tangle_research.verb_benchmark" in out
    assert "make verb-benchmark" in out


def test_verify_matches_tracked_baseline(capsys: pytest.CaptureFixture[str]) -> None:
    assert verb_benchmark.main(["--verify"]) == 0
    out = capsys.readouterr().out
    assert out.count("verb_gate{") == 7
    assert out.strip().endswith("verification: passed")


def test_default_emits_the_checked_in_baseline(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert verb_benchmark.main([]) == 0
    emitted = json.loads(capsys.readouterr().out)
    assert emitted["protocol"] == verb_benchmark.PROTOCOL
    assert emitted == verb_benchmark._baseline()


def test_verify_rejects_a_wrong_answer(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr(
        verb_benchmark,
        "_answer",
        lambda *arguments, **keywords: {"exit": 0, "stdout": "wrong\n"},
    )
    assert verb_benchmark.main(["--verify"]) == 1
    assert "verb baseline mismatch for frontier" in capsys.readouterr().err


def test_unknown_option_is_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert verb_benchmark.main(["--bogus"]) == 2
    assert "error: unknown option" in capsys.readouterr().err
