"""The single installed ``braintree`` command.

One language-agnostic entry point fronts every Braintree capability: Markdown
validation, external-vault feedback, the derived index and sidecar queries, and
same-host coordination. Consuming projects and ``SKILL.md`` name only
``braintree``; the implementation language, package layout, and toolchain stay
behind this command.
"""

from __future__ import annotations

import os
import sqlite3
import sys
from collections.abc import Callable, Sequence

from . import (
    allocation,
    behavioral_benchmark,
    cli,
    decompose,
    embedding_benchmark,
    feedback_record,
    feedback_scan,
    graph_check,
    help,
    index,
    memory_authority,
    memory_causal,
    memory_corpus,
    memory_diagnostics,
    memory_pilot,
    node_record,
    node_references,
    provider,
    quality_benchmark,
    reservations,
    sidecar,
    staged_benchmark,
    storage_comparison,
    token_benchmark,
    vault,
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
    ("allocate PREFIX [COUNT]", "atomically allocate COUNT consecutive PREFIX-NNN ids"),
    (
        "reservations",
        "list allocated id prefixes and the burned ids no node uses",
    ),
    (
        "claim NODE AGENT --base-hash HASH [--lease-seconds N]",
        "acquire or renew an exclusive lease (default 900 seconds)",
    ),
    (
        "release NODE AGENT --base-hash HASH",
        "release the matching lease or report it expired",
    ),
    ("index [NODES]", "repair or rebuild the derived index from Markdown"),
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
    (
        "node references NODE",
        "show one node with the reconnaissance it directly references",
    ),
    (
        "node decompose --parent P --plan F [--dry-run]",
        "atomically write ordered direct children and advance the parent",
    ),
    (
        "node advance PARENT CHILD",
        "advance a coordinating parent's next to a direct child",
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
    (
        "benchmark token|behavioral|storage|verbs|staged|embedding|quality|corpus|"
        "pilot|causal|diagnostics|authority",
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

# The read-only verbs that answer a graph question in one call. Every one of
# them re-checks the vault for an unfinished node that cannot reach a hub, a
# reachability failure the client would otherwise see only from `braintree
# check`.
_DIRECT_ANSWER_COMMANDS = frozenset({"frontier", "next", "orient", "status"})

# The interactions that must not trigger derived-index upkeep: ``init`` creates
# the local coordination state, ``index`` is its explicit repair or rebuild,
# ``migrate`` changes the vault path the upkeep would read, and ``check``
# validates without writing any state at all.
_INDEX_UPKEEP_EXCLUDED = frozenset({"init", "index", "migrate", "check"})


def _warn_orphans() -> None:
    """Warn on stderr about each orphaned unfinished node, without failing.

    This is a read-only pre-check on the direct-answer verbs, so the verb still
    answers and keeps its exit code. The warning goes to stderr because those
    verbs print machine-readable TOON on stdout, matching the vault resolver's
    migration notice. The vault is resolved without migrating a legacy
    directory, so the pre-check has no side effect of its own.
    """
    nodes_dir = vault.resolve(migrate_legacy=False)
    if not os.path.isdir(nodes_dir):
        return
    orphans = [
        finding
        for finding in graph_check.findings(nodes_dir)
        if finding.code == "route-orphan"
    ]
    if not orphans:
        return
    noun = "node" if len(orphans) == 1 else "nodes"
    print(
        f"warning: {len(orphans)} orphaned unfinished {noun} cannot reach a hub; "
        "run `braintree check` for the repair",
        file=sys.stderr,
    )
    for finding in orphans:
        print(f"warning: {finding.detail}", file=sys.stderr)


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
    "diagnostics": memory_diagnostics.main,
    "authority": memory_authority.main,
}


def _maintain_index(command: str) -> None:
    """Bring the derived index up to date after one interaction.

    Trigger: every dispatched interaction except :data:`_INDEX_UPKEEP_EXCLUDED`,
    and only when the project's local coordination state already exists. Scope:
    the derived node, edge, and full-text rows for the resolved vault, rebuilt
    from Markdown alone, so repeated calls are idempotent and an unchanged vault
    writes nothing. Failure: the interaction's answer and exit code never
    change. An unresolvable state location, an absent state file, and a
    concurrent writer's lock are silent no-ops, so a read-only interaction
    creates no local state and a benign race raises no noise; any other failure
    is one warning on stderr, the same channel the orphan pre-check uses.
    """
    if command in _INDEX_UPKEEP_EXCLUDED:
        return
    try:
        database = sidecar.database_path()
    except sidecar.SidecarError:
        return
    if not database.is_file():
        return
    nodes_dir = vault.resolve(migrate_legacy=False)
    if not os.path.isdir(nodes_dir):
        return
    try:
        connection = sidecar.open_connection()
        try:
            index.refresh(connection, nodes_dir)
        finally:
            connection.close()
    except sqlite3.OperationalError as exc:
        # A lock is a benign race with another writer, not a failure to report.
        if "locked" in str(exc) or "busy" in str(exc):
            return
        _warn_index_upkeep(str(exc))
    except Exception as exc:  # upkeep must never fail a client interaction
        _warn_index_upkeep(str(exc))


def _warn_index_upkeep(detail: str) -> None:
    print(
        f"warning: unable to maintain the derived index: {detail}",
        file=sys.stderr,
    )


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
            "embedding, quality, corpus, pilot, causal, or authority",
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
    # Upkeep runs after the body, so a mutating interaction's own change is
    # already in Markdown when the index is brought up to date.
    code = _dispatch(command, args)
    _maintain_index(command)
    return code


def _dispatch(command: str, args: list[str]) -> int:
    """Run one command body and return its exit code."""
    if command in _DIRECT_ANSWER_COMMANDS:
        _warn_orphans()
    if command == "check":
        return graph_check.main(args[1:])
    if command == "reservations":
        return reservations.main(args[1:])
    # ``allocate`` is served by its own module because ``cli.py`` and
    # ``sidecar.py`` are frozen observable prompt files; see
    # ``braintree.allocation``.
    if command == "allocate":
        return allocation.main(args)
    # ``node record`` is the capture path beside ``feedback record``; a bare
    # ``node NODE`` stays with the sidecar/index engine that owns it.
    if command == "node" and len(args) > 1 and args[1] == "record":
        return node_record.main(args[2:])
    # ``node references`` is the opt-in reconnaissance read surface; a bare
    # ``node NODE`` stays with the sidecar/index engine that owns it.
    if command == "node" and len(args) > 1 and args[1] == "references":
        return node_references.main(args)
    # ``node decompose`` and ``node advance`` are the transactional authoring
    # paths beside ``node record``.
    if command == "node" and len(args) > 1 and args[1] == "decompose":
        return decompose.main(args)
    if command == "node" and len(args) > 1 and args[1] == "advance":
        return decompose.advance_main(args)
    if command == "feedback":
        return _feedback(args[1:])
    if command == "semantic":
        return _semantic(args[1:])
    if command == "benchmark":
        return _benchmark(args[1:])
    if command in _COORDINATION_COMMANDS:
        return cli.main(args)
    return _usage_error(f"unknown command: {command}")
