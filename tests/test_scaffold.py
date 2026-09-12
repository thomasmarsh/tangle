"""Scaffold contract tests for the Braintree Python package."""

from __future__ import annotations

import importlib.metadata

import pytest

from braintree import __version__, cli, graph_check

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


def test_bt_known_command_reports_unimplemented(capsys: pytest.CaptureFixture[str]) -> None:
    assert cli.main(["status"]) == 1
    assert 'error: "command is not implemented in the scaffold: status"' in capsys.readouterr().out


def test_graph_check_help(capsys: pytest.CaptureFixture[str]) -> None:
    assert graph_check.main(["--help"]) == 0
    assert "usage: graph-check" in capsys.readouterr().out


def test_graph_check_stub_exit_code(capsys: pytest.CaptureFixture[str]) -> None:
    assert graph_check.main(["nodes"]) == 1
    assert "not implemented" in capsys.readouterr().err
