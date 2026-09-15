"""The ``tangle manifest NODE`` execution-surface read surface.

A node's authored ``# Manifest`` section declares the source files a task
expects to touch, the focused tests that cover it, the final verification gates
that accept it, and the compatibility constraints it must preserve. This verb
prints those authored entries beside the data derived from them so a fresh
worker can orient without a broad repository search, and it reports a malformed
or unknown entry instead of silently dropping it.

The verb lives beside ``index.py`` rather than in ``cli.py`` because
``src/tangle/cli.py`` is frozen observable prompt content in
``benchmark/memory-authority-cases.json``; a byte change there would invalidate
the committed measurement.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence

from . import cli, index
from .toon import field

__all__ = ["main"]

_USAGE = (
    "usage: tangle manifest NODE\n"
    "Print one node's authored execution-surface entries beside their derived\n"
    "resolution, or a structured invalid result for a malformed entry.\n"
    "Exits 0 for ready or empty; invalid and unknown-node exit 1."
)


def _usage_error(message: str) -> int:
    print(field("error", message))
    print(
        field(
            "help",
            "Run `tangle manifest --help` for operands and exit meanings.",
        )
    )
    return 2


def _print_manifest(view: index.ManifestView) -> int:
    node = view.node
    print(field("result", view.result))
    print(field("id", node.id))
    print(field("name", node.name))
    print(field("status", node.status))
    print(
        index.format_table(
            "authored",
            "kind,value",
            "authored: 0 entries",
            [(entry.kind, entry.value) for entry in view.entries],
        )
    )
    print(
        index.format_table(
            "derived",
            "kind,value,state,detail",
            "derived: 0 entries",
            [
                (entry.kind, entry.value, entry.state, entry.detail)
                for entry in view.entries
            ],
        )
    )
    if view.problems:
        print(
            index.format_table(
                "problems",
                "code,node,detail",
                "problems: 0 problems",
                [
                    (problem.code, problem.node, problem.detail)
                    for problem in view.problems
                ],
            )
        )
    return 0 if view.result in {"ready", "empty"} else 1


def main(argv: Sequence[str] | None = None) -> int:
    """Run ``tangle manifest`` and return the process exit code."""
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "manifest":
        args = args[1:]
    if args and args[0] in {"-h", "--help"}:
        print(_USAGE)
        return 0
    if not args:
        return _usage_error("manifest requires one NODE")
    if len(args) > 1:
        return _usage_error(f"manifest takes one NODE: {args[1]}")
    node = args[0]
    root = cli._require_nodes_directory()
    if root is None:
        return 1
    view = index.manifest(root, node)
    if view is None:
        return cli._unknown_node(node)
    return _print_manifest(view)


if __name__ == "__main__":  # pragma: no cover - module entry point
    raise SystemExit(main())
