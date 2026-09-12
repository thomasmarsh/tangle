"""The single installed ``braintree`` command.

One language-agnostic entry point fronts every Braintree capability: Markdown
validation, external-vault feedback, the derived index and sidecar queries, and
same-host coordination. Consuming projects and ``SKILL.md`` name only
``braintree``; the implementation language, package layout, and toolchain stay
behind this command.
"""

from __future__ import annotations

import sys
from collections.abc import Callable, Sequence

from . import (
    behavioral_benchmark,
    cli,
    feedback_record,
    feedback_scan,
    graph_check,
    storage_comparison,
    token_benchmark,
)
from .revision import reported_version
from .toon import escape, field

__all__ = ["main"]

_USAGE = "braintree <command> [arguments]"

_COMMANDS: tuple[tuple[str, str], ...] = (
    ("status", "show the current coordination state"),
    ("location", "show the stable project identity and state path"),
    ("init", "create or repair local coordination state"),
    ("allocate PREFIX", "atomically allocate PREFIX-NNN"),
    ("claim NODE AGENT --base-hash HASH", "acquire or renew an exclusive lease"),
    ("release NODE AGENT --base-hash HASH", "release the matching unexpired lease"),
    ("index [NODES]", "rebuild the derived index from Markdown"),
    ("search QUERY [--limit N]", "full-text search derived Markdown content"),
    ("backlinks NODE", "list derived incoming graph edges"),
    ("hash NODE", "print the raw-content SHA-256 of a node file"),
    ("stale", "find missing or outdated dependency pins"),
    ("frontier", "list unfinished nodes whose next is an action"),
    ("node NODE", "show one node's frontmatter, route, edges, and backlinks"),
    ("impact NODE", "list direct and transitive dependents of a node"),
    ("check [OPTIONS] [NODES]", "validate a vault without writing state"),
    ("feedback scan VAULT ...", "collect FBK feedback from external vaults"),
    ("feedback record [OPTIONS]", "record Braintree friction as an FBK node"),
    ("benchmark token|behavioral|storage", "run a development benchmark"),
)

_COORDINATION_COMMANDS = frozenset(
    {
        "status",
        "location",
        "init",
        "allocate",
        "claim",
        "release",
        "index",
        "search",
        "backlinks",
        "hash",
        "stale",
        "frontier",
        "node",
        "impact",
    }
)

_BENCHMARKS: dict[str, Callable[[Sequence[str] | None], int]] = {
    "token": token_benchmark.main,
    "behavioral": behavioral_benchmark.main,
    "storage": storage_comparison.main,
}


def _print_usage() -> None:
    print(
        field(
            "description",
            "Validate, query, and coordinate a Markdown-canonical graph.",
        )
    )
    print(field("usage", _USAGE))
    print(f"commands[{len(_COMMANDS)}]{{command,purpose}}:")
    for name, purpose in _COMMANDS:
        print(f'  "{escape(name)}","{escape(purpose)}"')


def _usage_error(message: str) -> int:
    print(field("error", message))
    print(field("help", "Run `braintree --help` for command usage."))
    return 2


def _feedback(args: list[str]) -> int:
    if not args:
        return _usage_error("feedback requires scan or record")
    group = args[0]
    if group == "scan":
        return feedback_scan.main(args[1:])
    if group == "record":
        return feedback_record.main(args[1:])
    return _usage_error(f"unknown feedback command: {group}")


def _benchmark(args: list[str]) -> int:
    if not args:
        return _usage_error("benchmark requires token, behavioral, or storage")
    name = args[0]
    if name not in _BENCHMARKS:
        return _usage_error(f"unknown benchmark: {name}")
    return _BENCHMARKS[name](args[1:])


def main(argv: Sequence[str] | None = None) -> int:
    """Run the ``braintree`` command and return the process exit code."""
    args = list(sys.argv[1:] if argv is None else argv)
    if not args:
        _print_usage()
        return 0
    command = args[0]
    if command in {"--version", "-v", "-V"}:
        if len(args) != 1:
            return _usage_error(f"unknown argument: {args[1]}")
        print(reported_version())
        return 0
    if command in {"--help", "-h"}:
        _print_usage()
        return 0
    if command == "check":
        return graph_check.main(args[1:])
    if command == "feedback":
        return _feedback(args[1:])
    if command == "benchmark":
        return _benchmark(args[1:])
    if command in _COORDINATION_COMMANDS:
        return cli.main(args)
    return _usage_error(f"unknown command: {command}")
