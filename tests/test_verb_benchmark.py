"""Contract tests for the direct-answer verb correctness gate."""

from __future__ import annotations

import json

import pytest

from tangle import verb_benchmark

# Benchmark verification spawns the verb gate, so it is opt-in.
pytestmark = pytest.mark.benchmark


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
