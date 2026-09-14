"""The opt-in ``braintree node references`` reconnaissance read surface.

``braintree node NODE`` keeps its exact output; this module adds the one-hop
expansion a reader requests explicitly, so the directly referenced
reconnaissance is loaded only when asked for. It reaches the answer through its
own module because ``src/braintree/cli.py`` is frozen observable prompt content
in ``benchmark/memory-authority-cases.json``; a byte change there would
invalidate the committed measurement.
"""

from __future__ import annotations

import sys
from collections.abc import Sequence

from . import index
from .cli import _require_nodes_directory, _unknown_node
from .toon import field

__all__ = ["main"]

_USAGE = (
    "usage: braintree node references NODE\n"
    "Show one node with the reconnaissance it directly references.\n"
    "The expansion is one hop, so reference cycles terminate and output is\n"
    "bounded by the node's direct references."
)


def _usage_error(message: str) -> int:
    print(field("error", message))
    print(
        field(
            "help",
            "Run `braintree node references --help` for operands and exit meanings.",
        )
    )
    return 2


def main(argv: Sequence[str] | None = None) -> int:
    """Run ``braintree node references NODE`` and return the process exit code."""
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "node":
        args = args[1:]
    if args and args[0] == "references":
        args = args[1:]
    if args and args[0] in {"-h", "--help"}:
        print(_USAGE)
        return 0
    if len(args) != 1 or args[0].startswith("-"):
        return _usage_error("node references requires NODE")
    root = _require_nodes_directory()
    if root is None:
        return 1
    view = index.reference_view(root, args[0])
    if view is None:
        return _unknown_node(args[0])
    node = view.node
    print(field("node", node.id))
    print(field("name", node.name))
    print(field("status", node.status))
    print(field("path", node.path))
    print(field("summary", node.metadata.get("summary", "")))
    print(field("route_relation", view.route_relation))
    print(field("route", view.route))
    print(
        index.format_table(
            "references",
            "id,status,context_rev,summary",
            "references: 0 references",
            [
                (item.id, item.status, str(item.context_rev), item.summary)
                for item in view.references
            ],
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - module entry point
    raise SystemExit(main())
