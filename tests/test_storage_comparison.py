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


def test_case_only_rename_is_layout_independent() -> None:
    # Every representation must survive a case-only rename through an
    # intermediate path; the comparison reports that shared capability as 1.
    assert storage_comparison._case_safe_rename() == 1


def test_default_run_skips_verification(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    # Exercise the flag handling without rebuilding the four disposable Git
    # fixtures: the default path must print every case and no verification line.
    result = storage_comparison._CaseResult(
        shape="M",
        transition_paths=1,
        point_edit_shape="M",
        point_edit_paths=1,
        query_reads=0,
        query_entries=25,
        conflicts=0,
        stale=0,
        stable=0,
        sidecar_recover=1,
        wikilink_stable=1,
        case_safe=1,
        symlink_view=0,
    )
    monkeypatch.setattr(storage_comparison, "_result_for", lambda name: result)
    assert storage_comparison.main([]) == 0
    out = capsys.readouterr().out
    assert "verification: passed" not in out
    assert out.count("storage{name,diff,") == 4
