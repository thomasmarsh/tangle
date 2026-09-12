"""Shared subprocess harness for the ``bt`` sidecar tests.

The shell suites in ``tests/bt-*.sh`` exercise the Ruby/shell implementation.
These helpers let the pytest ports drive the Python ``bt`` as a real process so
concurrency, cross-worktree identity, and environment handling are identical.
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest

_BT_COMMAND = (sys.executable, "-m", "braintree")


def build_env(overrides: dict[str, str | None] | None) -> dict[str, str]:
    """Return the process environment with ``None`` values removed."""
    env = os.environ.copy()
    for key, value in (overrides or {}).items():
        if value is None:
            env.pop(key, None)
        else:
            env[key] = value
    return env


def _command() -> list[str]:
    return list(_BT_COMMAND)


@pytest.fixture
def bt_command() -> Callable[[], list[str]]:
    """Return a factory for the argv prefix that runs the Python ``bt``."""
    return _command


@pytest.fixture
def run_bt() -> Callable[..., subprocess.CompletedProcess[str]]:
    """Run the Python ``bt`` and capture its text output."""

    def run(
        *args: str,
        cwd: str | Path | None = None,
        env: dict[str, str | None] | None = None,
        check: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [*_BT_COMMAND, *args],
            cwd=None if cwd is None else str(cwd),
            env=build_env(env),
            capture_output=True,
            text=True,
        )
        if check and result.returncode != 0:
            raise AssertionError(
                f"bt {' '.join(args)} failed ({result.returncode}): "
                f"{result.stdout}{result.stderr}"
            )
        return result

    return run
