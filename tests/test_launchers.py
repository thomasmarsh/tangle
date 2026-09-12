"""Smoke tests for the single in-repo ``scripts/braintree`` launcher.

Behavioral coverage for every command lives in the pytest suite and the
installer test. These checks keep the one dev launcher wired to the unified
``braintree`` command.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_LAUNCHER = _ROOT / "scripts" / "braintree"


def test_launcher_is_executable_and_runs_braintree() -> None:
    assert _LAUNCHER.is_file()
    assert _LAUNCHER.stat().st_mode & 0o111
    text = _LAUNCHER.read_text(encoding="utf-8")
    assert 'exec uv run --project "$here" --frozen braintree "$@"' in text


@pytest.mark.parametrize("args", [["--version"], ["--help"], ["check", "--help"]])
def test_launcher_runs(args: list[str]) -> None:
    result = subprocess.run(
        [str(_LAUNCHER), *args],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (args, result.stdout, result.stderr)
