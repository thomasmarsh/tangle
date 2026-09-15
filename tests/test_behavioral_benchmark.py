"""Contract tests for the typed behavioral filesystem diagnostic."""

from __future__ import annotations

import pytest

from tangle import behavioral_benchmark

# Benchmark verification recomputes full fixtures, so it is opt-in.
pytestmark = pytest.mark.benchmark


def test_verify_matches_tracked_baseline(capsys: pytest.CaptureFixture[str]) -> None:
    assert behavioral_benchmark.main(["--verify"]) == 0
    out = capsys.readouterr().out
    assert out.count("filesystem_diagnostic{") == 2
    assert out.strip().endswith("verification: passed")


def test_unknown_option_is_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert behavioral_benchmark.main(["--bogus"]) == 2
    assert "error: unknown option" in capsys.readouterr().err


def test_scales_outside_supported_range(capsys: pytest.CaptureFixture[str]) -> None:
    assert behavioral_benchmark.main(["--scales", "5"]) == 2
    assert "scales must be 13 through 10000" in capsys.readouterr().err


def test_single_scale_run(capsys: pytest.CaptureFixture[str]) -> None:
    assert behavioral_benchmark.main(["--scales", "13"]) == 0
    out = capsys.readouterr().out
    assert out.startswith("filesystem_diagnostic{")
    assert "13," in out
