"""Contract tests for the typed behavioral filesystem diagnostic."""

from __future__ import annotations

import pytest
from tangle_research import behavioral_benchmark

from tangle import main as tangle_main

# Benchmark verification recomputes full fixtures, so it is opt-in.
pytestmark = pytest.mark.benchmark


def test_repository_module_help_names_development_entry_path(
    capsys: pytest.CaptureFixture[str],
) -> None:
    with pytest.raises(SystemExit) as exit_status:
        behavioral_benchmark.main(["--help"])
    assert exit_status.value.code == 0
    assert "python -m tangle_research.behavioral_benchmark" in capsys.readouterr().out


def test_installed_command_reports_repository_only_boundary(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr("tangle.main.census.reconcile", lambda: None)
    monkeypatch.setattr(tangle_main, "_maintain_index", lambda _command: None)
    assert tangle_main.main(["benchmark", "behavioral"]) == 2
    out = capsys.readouterr().out
    assert "unavailable in an ordinary installation" in out
    assert "make diagnostic-benchmark" in out


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
