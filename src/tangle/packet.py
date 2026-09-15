"""The strict ``tangle packet`` work-packet read surface.

``tangle orient`` dumps bounded sections and ``tangle frontier`` lists
candidates, but neither states which single node a fresh worker should execute.
This module adds that one answer: it follows the vault's ``index-map.md`` root
hubs and each coordinating node's single ``next`` route to at most one
executable node, and refuses to guess between more than one. It is read-only and
derives everything from Markdown through :func:`tangle.index.packet`.

The verb lives beside ``index.py`` rather than in ``cli.py`` because
``src/tangle/cli.py`` is frozen observable prompt content in
``benchmark/memory-authority-cases.json``; a byte change there would invalidate
the committed measurement.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence

from . import index
from .cli import _require_nodes_directory
from .toon import field

__all__ = ["main"]

_USAGE = (
    "usage: tangle packet\n"
    "Print the one executable frontier node and its minimal execution context,\n"
    "or a structured blocked, ambiguous, or invalid result. Read-only.\n"
    "Exits 0 only when result is ready; ambiguous, blocked, and invalid exit 1."
)


def _usage_error(message: str) -> int:
    print(field("error", message))
    print(
        field(
            "help",
            "Run `tangle packet --help` for operands and exit meanings.",
        )
    )
    return 2


def _print_ready(packet: index.WorkPacket) -> int:
    node = packet.node
    assert node is not None
    print(field("result", "ready"))
    print(field("id", node.id))
    print(field("name", node.name))
    print(field("path", node.path))
    print(field("status", node.status))
    print(field("summary", node.summary))
    print(field("next", node.next))
    print(
        index.format_table(
            "route",
            "parent,relation,child",
            "route: 0 hops",
            [(hop.parent, hop.relation, hop.child) for hop in node.route],
        )
    )
    print(
        index.format_table(
            "dependencies",
            "relation,target,pinned,current,status,stale",
            "dependencies: 0 context edges",
            [
                (
                    edge.relation,
                    edge.target,
                    edge.pinned,
                    edge.current,
                    edge.status,
                    edge.stale,
                )
                for edge in node.dependencies
            ],
        )
    )
    print(index.format_table("files", "path", "files: 0 files", [(node.path,)]))
    print(
        index.format_table(
            "verification",
            "gate",
            "verification: 0 gates",
            [(gate,) for gate in index.PACKET_VERIFICATION],
        )
    )
    return 0


def _print_blocked(packet: index.WorkPacket) -> int:
    print(field("result", "blocked"))
    print(
        index.format_table(
            "terminals",
            "node,status,reason,summary,route,path",
            "terminals: 0 routes",
            [
                (
                    terminal.node,
                    terminal.status,
                    terminal.reason,
                    terminal.summary,
                    terminal.route,
                    terminal.path,
                )
                for terminal in packet.terminals
            ],
        )
    )
    return 1


def _print_ambiguous(packet: index.WorkPacket) -> int:
    print(field("result", "ambiguous"))
    print(
        index.format_table(
            "candidates",
            "id,status,summary,next,route",
            "candidates: 0 candidates",
            [
                (
                    candidate.id,
                    candidate.status,
                    candidate.summary,
                    candidate.next,
                    candidate.route_text,
                )
                for candidate in packet.candidates
            ],
        )
    )
    return 1


def _print_invalid(packet: index.WorkPacket) -> int:
    print(field("result", "invalid"))
    print(
        index.format_table(
            "problems",
            "code,node,detail",
            "problems: 0 problems",
            [
                (problem.code, problem.node, problem.detail)
                for problem in packet.problems
            ],
        )
    )
    return 1


def main(argv: Sequence[str] | None = None) -> int:
    """Run ``tangle packet`` and return the process exit code."""
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "packet":
        args = args[1:]
    if args and args[0] in {"-h", "--help"}:
        print(_USAGE)
        return 0
    if args:
        return _usage_error(f"packet takes no arguments: {args[0]}")
    root = _require_nodes_directory()
    if root is None:
        return 1
    packet = index.packet(root)
    if packet.result == "ready":
        return _print_ready(packet)
    if packet.result == "blocked":
        return _print_blocked(packet)
    if packet.result == "ambiguous":
        return _print_ambiguous(packet)
    return _print_invalid(packet)


if __name__ == "__main__":  # pragma: no cover - module entry point
    raise SystemExit(main())
