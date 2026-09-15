"""The strict ``tangle packet`` work-packet read surface.

``tangle orient`` dumps bounded sections and ``tangle frontier`` lists
candidates, but neither states which single node a fresh worker should execute.
This module adds that one answer: it follows the vault's ``index-map.md`` root
hubs and each coordinating node's single ``next`` route to at most one
executable node, and refuses to guess between more than one. A ``NODE`` operand
scopes the answer to that node's own ``next`` route instead of the whole vault.
It is read-only and derives everything from Markdown through
:func:`tangle.index.packet`.

The verb lives beside ``index.py`` rather than in ``cli.py`` because
``src/tangle/cli.py`` is frozen observable prompt content in
``benchmark/memory-authority-cases.json``; a byte change there would invalidate
the committed measurement.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Sequence

from . import graph_check, index
from .cli import _require_nodes_directory
from .toon import field

__all__ = ["main"]

_USAGE = (
    "usage: tangle packet [NODE]\n"
    "Print the one executable frontier node and its minimal execution context,\n"
    "or a structured blocked, ambiguous, or invalid result. With NODE, answer for\n"
    "that node's next route instead of the whole vault. Read-only.\n"
    "Exits 0 only when result is ready; ambiguous, blocked, and invalid exit 1."
)


# The operation that records progress on the routed node. There is no command
# that updates an existing node: progress is the in-place ``status`` edit plus the
# ``# Result`` body change that lands in the same commit, and ``tangle check``
# runs before handoff. The packet names that operation so its answer covers
# closing the work, not only starting it.
PACKET_RECORD = "edit status in place and add # Result; run tangle check before handoff"

# Bound the completion criteria so the packet stays a bounded answer; a longer
# section reports the overage explicitly rather than silently truncating.
_CRITERIA_LIMIT = 20


def _usage_error(message: str) -> int:
    print(field("error", message))
    print(
        field(
            "help",
            "Run `tangle packet --help` for operands and exit meanings.",
        )
    )
    return 2


def _packet_files(
    node: index.PacketCandidate, manifest: index.ManifestView | None
) -> list[tuple[str, str, str]]:
    """Return the ``kind,path,state`` rows for the packet node and its manifest paths.

    The node's own Markdown path is always the first row. Manifest ``source``
    and ``test`` entries follow as repository paths with their derived state, so
    a still-to-be-created file reads as ``absent`` intent rather than vanishing.
    """
    rows: list[tuple[str, str, str]] = [("node", node.path, "present")]
    if manifest is not None:
        for entry in manifest.entries:
            if entry.kind in {"source", "test"}:
                rows.append((entry.kind, entry.detail or entry.value, entry.state))
    return rows


def _packet_verification(manifest: index.ManifestView | None) -> list[tuple[str]]:
    """Return the final gates: the fixed gates plus the manifest ``verify`` entries.

    Manifest gates are appended in authored order and deduplicated against the
    fixed gates, so a node that names ``make test`` does not print it twice.
    """
    gates: list[str] = list(index.PACKET_VERIFICATION)
    if manifest is not None:
        for entry in manifest.entries:
            if entry.kind == "verify" and entry.value not in gates:
                gates.append(entry.value)
    return [(gate,) for gate in gates]


def _packet_compat(manifest: index.ManifestView | None) -> list[tuple[str]]:
    """Return the manifest ``compat`` constraints as single-column rows."""
    if manifest is None:
        return []
    return [(entry.value,) for entry in manifest.entries if entry.kind == "compat"]


def _node_body(root: str, node: index.PacketCandidate) -> str:
    """Read the routed node's Markdown body for its ``# Done when`` section.

    The rest of the packet derives from the index's typed view; the completion
    criteria are body prose that view does not carry, so the read surface reads
    the routed node's own file. A vanished file yields no criteria, not an error.
    """
    try:
        with open(os.path.join(os.path.abspath(root), node.path), encoding="utf-8") as handle:
            return handle.read()
    except OSError:
        return ""


def _print_ready(packet: index.WorkPacket, root: str) -> int:
    node = packet.node
    assert node is not None
    manifest = index.manifest(root, node.id)
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
    print(
        index.format_table(
            "files", "kind,path,state", "files: 0 files", _packet_files(node, manifest)
        )
    )
    print(
        index.format_table(
            "verification",
            "gate",
            "verification: 0 gates",
            _packet_verification(manifest),
        )
    )
    print(
        index.format_table(
            "compat", "constraint", "compat: 0 constraints", _packet_compat(manifest)
        )
    )
    criteria = graph_check.parse_done_when(_node_body(root, node))
    criteria_rows = [(criterion,) for criterion in criteria[:_CRITERIA_LIMIT]]
    print(field("record", PACKET_RECORD))
    print(
        index.format_table("criteria", "criterion", "criteria: 0 criteria", criteria_rows)
    )
    omitted = len(criteria) - len(criteria_rows)
    if omitted:
        print(field("omitted", f"{omitted} further criteria"))
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
    if len(args) > 1:
        return _usage_error(f"packet takes at most one NODE: {args[1]}")
    scope = args[0] if args else None
    root = _require_nodes_directory()
    if root is None:
        return 1
    packet = index.packet(root, scope)
    if packet.result == "ready":
        return _print_ready(packet, root)
    if packet.result == "blocked":
        return _print_blocked(packet)
    if packet.result == "ambiguous":
        return _print_ambiguous(packet)
    return _print_invalid(packet)


if __name__ == "__main__":  # pragma: no cover - module entry point
    raise SystemExit(main())
