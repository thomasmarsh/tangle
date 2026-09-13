"""Contract tests for the typed storage-representation comparison."""

from __future__ import annotations

import pytest

from braintree import storage_comparison

# Benchmark verification rebuilds throwaway Git fixtures, so it is opt-in.
pytestmark = pytest.mark.benchmark


def test_verify_matches_tracked_baseline(capsys: pytest.CaptureFixture[str]) -> None:
    assert storage_comparison.main(["--verify"]) == 0
    out = capsys.readouterr().out
    assert out.count("storage{name,diff,") == 4
    assert "verification: passed" in out


def test_default_run_skips_verification(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Exercise the flag handling without rebuilding the four disposable Git
    # fixtures: the default path must print every case and no verification line.
    result = storage_comparison._CaseResult("M", 1, 0, 25, 0, 0, 0)
    monkeypatch.setattr(storage_comparison, "_result_for", lambda name: result)
    assert storage_comparison.main([]) == 0
    out = capsys.readouterr().out
    assert "verification: passed" not in out
    assert out.count("storage{name,diff,") == 4
