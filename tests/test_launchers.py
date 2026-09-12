"""Smoke tests for the in-repo shell launchers under ``scripts/``.

The behavioral coverage for each command lives in the pytest suite and the
installer test. These checks keep the thin historical launcher path wired to
the right ``braintree`` module now that the mirrored shell suites are gone.
"""

from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

_ROOT = Path(__file__).resolve().parents[1]
_SCRIPTS = _ROOT / "scripts"

# ``storage-comparison`` has no argument parser and runs the full comparison on
# any input, so it is checked statically rather than executed here.
_LAUNCHER_TARGETS = {
    "bt": "braintree",
    "graph-check": "braintree.graph_check",
    "feedback-scan": "braintree.feedback_scan",
    "feedback-record": "braintree.feedback_record",
    "behavioral-benchmark": "braintree.behavioral_benchmark",
    "storage-comparison": "braintree.storage_comparison",
    "token-benchmark": "braintree.token_benchmark",
}

_LAUNCHER_RUNS = {
    "bt": ["--version"],
    "graph-check": ["--version"],
    "feedback-scan": ["--help"],
    "feedback-record": ["--help"],
    "behavioral-benchmark": ["--help"],
    "token-benchmark": ["--protocol"],
}


@pytest.mark.parametrize(("name", "module"), sorted(_LAUNCHER_TARGETS.items()))
def test_launcher_targets_the_braintree_module(name: str, module: str) -> None:
    script = _SCRIPTS / name
    assert script.is_file()
    assert script.stat().st_mode & 0o111
    assert f'exec "$python" -m {module} "$@"' in script.read_text(encoding="utf-8")


@pytest.mark.parametrize(("name", "args"), sorted(_LAUNCHER_RUNS.items()))
def test_launcher_runs(name: str, args: list[str]) -> None:
    result = subprocess.run(
        [str(_SCRIPTS / name), *args],
        capture_output=True,
        text=True,
    )
    assert result.returncode == 0, (name, result.stdout, result.stderr)
