"""Scaffold contract tests for the Braintree Python package."""

from __future__ import annotations

import importlib.metadata
import tomllib
from pathlib import Path

import pytest

from braintree import __version__, cli, graph_check

_ROOT = Path(__file__).resolve().parents[1]

_COMMANDS = (
    "status",
    "location",
    "init",
    "allocate",
    "claim",
    "release",
    "reindex",
    "search",
    "backlinks",
    "stale",
)


def test_version_matches_installed_metadata() -> None:
    assert importlib.metadata.version("braintree") == __version__


def test_declared_version_is_single_sourced() -> None:
    declared = tomllib.loads((_ROOT / "pyproject.toml").read_text(encoding="utf-8"))
    assert declared["project"]["version"] == __version__


def test_bt_version_flag(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["--version"]) == 0
    assert capsys.readouterr().out.strip() == __version__


def test_bt_version_flag_requires_sole_argument(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["--version", "extra"]) == 2
    assert 'error: "unknown command: --version"' in capsys.readouterr().out


def test_bt_help_lists_every_command(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["--help"]) == 0
    out = capsys.readouterr().out
    for command in _COMMANDS:
        assert command in out


def test_bt_unknown_command_is_usage_error(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["frobnicate"]) == 2
    assert 'error: "unknown command: frobnicate"' in capsys.readouterr().out


def test_bt_status_reports_uninitialized_sidecar(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setenv("BT_SIDECAR_DIR", str(tmp_path / "sidecar"))
    monkeypatch.setenv("BT_PROJECT_ID", "scaffold-test")
    assert cli.main(["status"]) == 0
    assert 'initialized: "false"' in capsys.readouterr().out


def test_graph_check_help(capsys: pytest.CaptureFixture[str]) -> None:
    assert graph_check.main(["--help"]) == 0
    assert "usage: graph-check" in capsys.readouterr().out
