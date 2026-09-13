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
    embedding_benchmark,
    feedback_record,
    feedback_scan,
    graph_check,
    help,
    memory_causal,
    memory_corpus,
    memory_pilot,
    node_record,
    provider,
    quality_benchmark,
    staged_benchmark,
    storage_comparison,
    token_benchmark,
    verb_benchmark,
)
from .revision import reported_version
from .toon import escape, field, table

__all__ = ["main"]

_USAGE = "braintree <command> [arguments]"

_COMMANDS: tuple[tuple[str, str], ...] = (
    ("status", "show the current coordination state"),
    ("location", "show the stable project identity and state path"),
    ("init", "create or repair local coordination state"),
    ("migrate [ROOT]", "rename a legacy nodes/ vault to .braintree/"),
    ("allocate PREFIX", "atomically allocate PREFIX-NNN"),
    (
        "claim NODE AGENT --base-hash HASH [--lease-seconds N]",
        "acquire or renew an exclusive lease (default 900 seconds)",
    ),
    (
        "release NODE AGENT --base-hash HASH",
        "release the matching lease or report it expired",
    ),
    ("index [NODES]", "rebuild the derived index from Markdown"),
    (
        "search QUERY [--limit N] [--status S] [--type T] [--priority P] "
        "[--parent REF] [--dependency REF]",
        "full-text search derived Markdown content",
    ),
    ("similar TEXT|--file PATH [--limit N]", "rank nodes by lexical similarity"),
    ("backlinks NODE", "list derived incoming graph edges"),
    ("hash NODE", "print the raw-content SHA-256 of a node file"),
    ("stale", "find missing or outdated dependency pins"),
    (
        "frontier [--group] [--limit N]",
        "list frontier candidates or cluster them into advisory workstreams",
    ),
    ("node NODE", "show one node's frontmatter, route, edges, and backlinks"),
    (
        "node record [OPTIONS]",
        "create one routed, stamped node of a named type",
    ),
    ("impact NODE", "list direct and transitive dependents of a node"),
    ("orient [--section NAME] [--limit N]", "print a bounded orientation packet"),
    ("next [--rank] [--limit N]", "rank frontier candidates for the next actor"),
    (
        "clusters [--limit N]",
        "list advisory clusters, over-broad routes, and outlier nodes",
    ),
    ("digest NODE [--limit N]", "digest a hub's or node's unresolved direct members"),
    (
        "reconcile [--base REF] [--head REF ...] [NODES]",
        "plan duplicate, divergence, and stale-pin repairs from a Git change set",
    ),
    ("check [OPTIONS] [NODES]", "validate a vault without writing state"),
    (
        "semantic embed [--model NAME]",
        "embed JSON texts as JSON vectors for BT_SEMANTIC_PROVIDER",
    ),
    ("feedback scan VAULT ...", "collect FBK feedback from external vaults"),
    ("feedback record [OPTIONS]", "record Braintree friction as an FBK node"),
    ("benchmark token|behavioral|storage|verbs|staged|embedding|quality|corpus|pilot|causal",
        "run a development benchmark",
    ),
    ("help [TOPIC]", "print the topic index or one installed workflow reference"),
)

_COORDINATION_COMMANDS = frozenset(
    {
        "status",
        "location",
        "init",
        "migrate",
        "allocate",
        "claim",
        "release",
        "index",
        "search",
        "similar",
        "backlinks",
        "hash",
        "stale",
        "frontier",
        "node",
        "impact",
        "orient",
        "next",
        "clusters",
        "digest",
        "reconcile",
    }
)

_BENCHMARKS: dict[str, Callable[[Sequence[str] | None], int]] = {
    "token": token_benchmark.main,
    "behavioral": behavioral_benchmark.main,
    "storage": storage_comparison.main,
    "verbs": verb_benchmark.main,
    "staged": staged_benchmark.main,
    "embedding": embedding_benchmark.main,
    "quality": quality_benchmark.main,
    "corpus": memory_corpus.main,
    "pilot": memory_pilot.main,
    "causal": memory_causal.main,
}


def _print_usage() -> None:
    print(
        field(
            "description",
            "Validate, query, and coordinate a Markdown-canonical graph.",
        )
    )
    print(field("usage", _USAGE))
    print(
        field(
            "help",
            "Run `braintree <command> --help` for operands and exit meanings, "
            "or `braintree help TOPIC` for a workflow reference.",
        )
    )
    print(f"commands[{len(_COMMANDS)}]{{command,purpose}}:")
    for name, purpose in _COMMANDS:
        print(f'  "{escape(name)}","{escape(purpose)}"')
    print(table("topics", "topic,purpose", help.topic_rows(), "topics: 0 references"))


def _usage_error(message: str, command: str = "") -> int:
    print(field("error", message))
    if command:
        print(
            field(
                "help",
                f"Run `braintree {command} --help` for operands and exit meanings.",
            )
        )
    else:
        print(field("help", "Run `braintree --help` for the command and topic index."))
    return 2


def _feedback(args: list[str]) -> int:
    if not args:
        return _usage_error("feedback requires scan or record", "feedback")
    group = args[0]
    if group == "scan":
        return feedback_scan.main(args[1:])
    if group == "record":
        return feedback_record.main(args[1:])
    return _usage_error(f"unknown feedback command: {group}", "feedback")


def _semantic(args: list[str]) -> int:
    if not args:
        return _usage_error("semantic requires embed", "semantic")
    group = args[0]
    if group == "embed":
        return provider.main(args[1:])
    return _usage_error(f"unknown semantic command: {group}", "semantic")


def _benchmark(args: list[str]) -> int:
    if not args:
        return _usage_error(
            "benchmark requires token, behavioral, storage, verbs, staged, "
            "embedding, quality, corpus, pilot, or causal",
            "benchmark",
        )
    name = args[0]
    if name not in _BENCHMARKS:
        return _usage_error(f"unknown benchmark: {name}", "benchmark")
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
    if command == "help":
        return help.help_command(args[1:])
    # A per-verb help request is answered here, before any command body runs, so
    # every public verb gets bounded help with no vault and no sidecar.
    if help.wants_help(args):
        return help.render_verb(help.verb_key(args))
    if command == "check":
        return graph_check.main(args[1:])
    # ``node record`` is the capture path beside ``feedback record``; a bare
    # ``node NODE`` stays with the sidecar/index engine that owns it.
    if command == "node" and len(args) > 1 and args[1] == "record":
        return node_record.main(args[2:])
    if command == "feedback":
        return _feedback(args[1:])
    if command == "semantic":
        return _semantic(args[1:])
    if command == "benchmark":
        return _benchmark(args[1:])
    if command in _COORDINATION_COMMANDS:
        return cli.main(args)
    return _usage_error(f"unknown command: {command}")
