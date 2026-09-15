"""Contract tests for the install-time revision record and its read path."""

from __future__ import annotations

from pathlib import Path

import pytest

from tangle import __version__, cli, graph_check, revision


def _use_record(monkeypatch: pytest.MonkeyPatch, tmp_path: Path, value: str) -> Path:
    record = tmp_path / "installed-revision"
    record.write_text(f"{value}\n", encoding="utf-8")
    monkeypatch.setattr(revision, "_record_path", lambda: record)
    return record


def test_reported_version_without_record_is_the_declared_version(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    # With no record beside the package, the plain declared version is reported.
    monkeypatch.setattr(revision, "_record_path", lambda: tmp_path / revision.RECORD_NAME)
    assert revision.RECORD_NAME == "installed-revision"
    assert revision.recorded_revision() is None
    assert revision.reported_version() == __version__


def test_recorded_revision_is_read_and_trimmed(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _use_record(monkeypatch, tmp_path, "0.4.0+g1b58d57")
    assert revision.recorded_revision() == "0.4.0+g1b58d57"
    assert revision.reported_version() == "0.4.0+g1b58d57"


def test_unknown_revision_record_is_reported_verbatim(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _use_record(monkeypatch, tmp_path, "0.4.0+unknown")
    assert revision.reported_version() == "0.4.0+unknown"


def test_tangle_reports_the_recorded_revision(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _use_record(monkeypatch, tmp_path, "0.4.0+g1b58d57")
    assert cli.main(["--version"]) == 0
    assert capsys.readouterr().out.strip() == "0.4.0+g1b58d57"


def test_graph_check_reports_the_recorded_revision(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    _use_record(monkeypatch, tmp_path, "0.4.0+g1b58d57")
    for flag in ("--version", "-v", "-V"):
        assert graph_check.main([flag]) == 0
        assert capsys.readouterr().out.strip() == "0.4.0+g1b58d57"


def test_feedback_revision_uses_the_record(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    _use_record(monkeypatch, tmp_path, "0.4.0+g1b58d57")
    assert revision.feedback_revision() == "0.4.0+g1b58d57"


def test_feedback_revision_degrades_to_unknown_without_a_record(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(revision, "_record_path", lambda: tmp_path / revision.RECORD_NAME)
    value = revision.feedback_revision()
    assert value == f"{__version__}+unknown"
    assert graph_check._TANGLE_REVISION.match(value) is not None


def test_recorded_revision_matches_the_feedback_convention() -> None:
    # The record value is the exact string a consuming project writes into
    # `tangle_revision:` frontmatter.
    for value in ("0.4.0+g1b58d57", "0.4.0+unknown"):
        assert graph_check._TANGLE_REVISION.match(value) is not None
