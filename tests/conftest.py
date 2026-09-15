"""Shared subprocess harness for the ``tangle`` sidecar tests.

The shell suites in ``tests/*.sh`` drive the installed Python launchers.
These helpers let the pytest ports drive the Python ``tangle`` as a real process so
concurrency, cross-worktree identity, and environment handling are identical.
"""

from __future__ import annotations

import os
import subprocess
import sys
from collections.abc import Callable
from pathlib import Path

import pytest
import vault_helpers

_TANGLE_COMMAND = (sys.executable, "-m", "tangle")


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
    return list(_TANGLE_COMMAND)


@pytest.fixture
def bt_command() -> Callable[[], list[str]]:
    """Return a factory for the argv prefix that runs the Python ``tangle``."""
    return _command


@pytest.fixture
def deterministic_ids(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make in-process identity generation deterministic and unique per call."""
    vault_helpers.fixed_identity(monkeypatch)


@pytest.fixture(autouse=True)
def hermetic_sidecar(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    """Pin the derived sidecar to a per-test temporary root for every test.

    The sidecar is derived, disposable coordination state. Without a pin the
    default state root is the developer's real ``$XDG_STATE_HOME`` or
    ``$HOME/.local/state``, so an in-process ``tangle`` call would reconcile
    and rewrite that machine's real database and publish views for a temporary
    vault. A test that needs an absent, explicit, or ambient sidecar overrides
    these values with its own ``monkeypatch.setenv``.
    """
    monkeypatch.setenv("TANGLE_SIDECAR_DIR", str(tmp_path / "sidecar"))
    monkeypatch.setenv("TANGLE_PROJECT_ID", "pytest-hermetic")


@pytest.fixture
def run_tangle() -> Callable[..., subprocess.CompletedProcess[str]]:
    """Run the Python ``tangle`` and capture its text output."""

    def run(
        *args: str,
        cwd: str | Path | None = None,
        env: dict[str, str | None] | None = None,
        check: bool = False,
    ) -> subprocess.CompletedProcess[str]:
        result = subprocess.run(
            [*_TANGLE_COMMAND, *args],
            cwd=None if cwd is None else str(cwd),
            env=build_env(env),
            capture_output=True,
            text=True,
        )
        if check and result.returncode != 0:
            raise AssertionError(
                f"tangle {' '.join(args)} failed ({result.returncode}): "
                f"{result.stdout}{result.stderr}"
            )
        return result

    return run
