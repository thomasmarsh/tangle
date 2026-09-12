"""Contract tests for the typed storage-representation comparison."""

from __future__ import annotations

import pytest

from braintree import storage_comparison


def test_verify_matches_tracked_baseline(capsys: pytest.CaptureFixture[str]) -> None:
    assert storage_comparison.main(["--verify"]) == 0
    out = capsys.readouterr().out
    assert out.count("storage{name,diff,") == 4
    assert "verification: passed" in out


def test_default_run_skips_verification(capsys: pytest.CaptureFixture[str]) -> None:
    assert storage_comparison.main([]) == 0
    out = capsys.readouterr().out
    assert "verification: passed" not in out
    assert "storage{name,diff," in out
