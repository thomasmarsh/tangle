"""Deterministic, offline correctness gate for the direct-answer verbs.

``braintree frontier``, ``braintree node``, ``braintree impact``,
``braintree orient``, and ``braintree check --format toon`` each answer a graph
question in one call. This gate runs every one of them against a small generated
vault whose complete answer is checked in at ``benchmark/verb-baseline.json``,
so a cheaper but wrong answer fails an exact stdout-and-exit comparison. It
makes no model calls and keeps the primary token benchmark zero-live.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import tempfile
from collections.abc import Sequence
from pathlib import Path
from typing import Any

__all__ = ["main"]

Json = dict[str, Any]
PROTOCOL = "direct-answer-verb-v1"
_NOTE = (
    "Exact stdout and exit status for each direct-answer verb on the deterministic "
    "gate fixture; run `braintree benchmark verbs` to regenerate."
)
_USAGE = (
    "usage: braintree benchmark verbs [--verify]\n"
    "Emit the direct-answer verb baseline, or verify each verb against it."
)
# The generated fixture is a valid vault with exactly one intentional stale pin,
# so ``check --allow-stale`` passes while plain ``check`` reports the mismatch.
_STALE_PIN = 2
_DEFINITION_REV = 3


class _UsageError(Exception):
    """A command-line error that maps to exit code 2."""


class _FixtureError(Exception):
    """A generated fixture or a verb answer violated the gate."""


def _repo_root() -> Path:
    """Return the checkout root that holds the tracked baseline."""
    return Path(__file__).resolve().parents[2]


def _baseline_path() -> Path:
    return _repo_root() / "benchmark" / "verb-baseline.json"


def _baseline() -> Json:
    return dict(json.loads(_baseline_path().read_text(encoding="utf-8")))


def _usage() -> None:
    print(_USAGE)


def _parse_options(argv: Sequence[str]) -> bool:
    verify = False
    for option in argv:
        if option == "--verify":
            verify = True
        elif option in {"-h", "--help"}:
            _usage()
            raise SystemExit(0)
        else:
            raise _UsageError(f"unknown option: {option}")
    return verify


def _node(
    *,
    context_rev: int,
    updated: str,
    summary: str,
    body: str,
    priority: str | None = None,
    next_action: str | None = None,
) -> str:
    fields = ["---", f"context_rev: {context_rev}"]
    if priority is not None:
        fields.append(f"priority: {priority}")
    fields.append(f"updated: {updated}")
    fields.append(f"summary: {summary}")
    if next_action is not None:
        fields.append(f"next: {next_action}")
    fields.extend(["---", "", body, ""])
    return "\n".join(fields)


def _write_fixture(root: Path) -> str:
    """Write the gate vault under ``root`` and return its ``nodes`` directory."""
    nodes = root / "nodes"
    for status in ("active", "blocked", "resolved"):
        (nodes / status).mkdir(parents=True)

    def write(status: str, name: str, text: str) -> None:
        (nodes / status / f"{name}.md").write_text(text, encoding="utf-8")

    (nodes / "index-map.md").write_text(
        "# Focus\n\n"
        "- [[TAS-002-implement-parser]]\n\n"
        "# Root hubs\n\n"
        "- Indexes [[IDX-001-engine]]: parser execution root.\n",
        encoding="utf-8",
    )
    write(
        "resolved",
        "IDX-001-engine",
        _node(
            context_rev=1,
            updated="2024-01-01T00:00:00Z",
            summary="Engine execution-memory root.",
            body="# Invariant\n\nDurable root hub.",
        ),
    )
    write(
        "resolved",
        "DEF-010-parser-contract",
        _node(
            context_rev=_DEFINITION_REV,
            updated="2024-01-02T00:00:00Z",
            summary="Parser contract requires signed tokens.",
            body=(
                "# Invariant\n\nArea [[IDX-001-engine]].\n\n"
                "Signed tokens are required."
            ),
        ),
    )
    write(
        "resolved",
        "TAS-000-foundation",
        _node(
            context_rev=1,
            updated="2024-01-03T00:00:00Z",
            summary="Land the resolved parser foundation.",
            body=(
                "# Context\n\nArea [[IDX-001-engine]].\n\n"
                f"Depends on [[DEF-010-parser-contract]] at context_rev {_STALE_PIN}.\n\n"
                "# Result\n\nThe foundation is resolved."
            ),
        ),
    )
    write(
        "active",
        "TAS-001-coordinate-parser",
        _node(
            context_rev=1,
            updated="2024-01-04T00:00:00Z",
            priority="P1",
            summary="Coordinate parser hardening.",
            next_action='"[[TAS-002-implement-parser]]"',
            body=(
                "# Context\n\nArea [[IDX-001-engine]].\n\n"
                "# Outcome\n\nParser hardening is coordinated."
            ),
        ),
    )
    write(
        "active",
        "TAS-002-implement-parser",
        _node(
            context_rev=1,
            updated="2024-01-05T00:00:00Z",
            priority="P0",
            summary="Implement the signed parser.",
            next_action="Implement signed-token parsing.",
            body=(
                "# Context\n\nParent [[TAS-001-coordinate-parser]].\n\n"
                "Depends on [[TAS-000-foundation]] at context_rev 1.\n\n"
                "# Outcome\n\nParser reads signed tokens."
            ),
        ),
    )
    write(
        "active",
        "TAS-003-verify-parser",
        _node(
            context_rev=1,
            updated="2024-01-06T00:00:00Z",
            priority="P2",
            summary="Verify the parser output.",
            next_action="Run the parser verification.",
            body=(
                "# Context\n\nParent [[TAS-001-coordinate-parser]].\n\n"
                "Depends on [[TAS-000-foundation]] at context_rev 1."
            ),
        ),
    )
    write(
        "blocked",
        "TAS-004-vendor-fixture",
        _node(
            context_rev=1,
            updated="2024-01-07T00:00:00Z",
            priority="P1",
            summary="Wait for the vendor fixture.",
            next_action="Request the vendor fixture.",
            body=(
                "# Context\n\nParent [[TAS-001-coordinate-parser]].\n\n"
                "# Blocked\n\nBlocked by the missing vendor fixture. "
                "Unblocks when the vendor ships the fixture."
            ),
        ),
    )
    return str(nodes)


def _cases(nodes_dir: str) -> list[tuple[str, list[str]]]:
    """Return the exact-value case name and verb argv for each new answer verb."""
    return [
        ("frontier", ["frontier"]),
        ("node", ["node", "TAS-000-foundation"]),
        ("impact", ["impact", "DEF-010-parser-contract"]),
        ("orient", ["orient"]),
        ("check-toon", ["check", "--format", "toon", nodes_dir]),
    ]


def _run(argv: list[str], root: Path, nodes_dir: str) -> subprocess.CompletedProcess[str]:
    env = os.environ.copy()
    env["BT_NODES_DIR"] = nodes_dir
    return subprocess.run(
        [sys.executable, "-m", "braintree", *argv],
        cwd=root,
        env=env,
        capture_output=True,
        text=True,
    )


def _answer(argv: list[str], root: Path, nodes_dir: str) -> Json:
    result = _run(argv, root, nodes_dir)
    if result.stderr:
        raise _FixtureError(f"verb {argv[0]} wrote to stderr: {result.stderr.strip()}")
    # ``check`` reports absolute node paths; pin them to a stable placeholder so
    # the baseline is independent of the temporary fixture location.
    stdout = result.stdout.replace(nodes_dir, "<nodes>")
    return {"exit": result.returncode, "stdout": stdout}


def _assert_fixture_valid(nodes_dir: str, root: Path) -> None:
    result = _run(["check", "--allow-stale", nodes_dir], root, nodes_dir)
    if result.returncode != 0:
        detail = result.stderr.strip() or result.stdout.strip()
        raise _FixtureError(f"gate fixture is not structurally valid: {detail}")


def _verify(produced: dict[str, Json]) -> int:
    expected = _baseline()["expected"]
    if set(expected) != set(produced):
        raise _FixtureError("baseline cases differ from the gate cases")
    for name, answer in produced.items():
        if expected[name] != answer:
            raise _FixtureError(
                f"verb baseline mismatch for {name}: "
                f"expected {expected[name]!r}, got {answer!r}"
            )
        print(f"verb_gate{{case,exit}}: {name},{answer['exit']}")
    print("verification: passed")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Emit or verify the direct-answer verb correctness baseline."""
    try:
        verify = _parse_options(sys.argv[1:] if argv is None else argv)
        with tempfile.TemporaryDirectory(prefix="bt-verb-gate-") as temp:
            root = Path(temp)
            nodes_dir = _write_fixture(root)
            _assert_fixture_valid(nodes_dir, root)
            produced = {
                name: _answer(case_argv, root, nodes_dir)
                for name, case_argv in _cases(nodes_dir)
            }
        if verify:
            return _verify(produced)
        document = {"protocol": PROTOCOL, "note": _NOTE, "expected": produced}
        print(json.dumps(document, indent=2, ensure_ascii=False))
        return 0
    except _UsageError as error:
        print(f"error: {error}", file=sys.stderr)
        _usage()
        return 2
    except _FixtureError as error:
        print(str(error), file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover - module entry point
    raise SystemExit(main())
