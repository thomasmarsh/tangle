"""Record a routed Braintree ``FBK`` feedback node in a consuming project.

This is the writing half of the feedback mechanism. It stamps the installed
Braintree revision, reserves the next ``FBK`` id atomically, discovers a
primary route to the vault's root hub, and writes a valid feedback node in one
step. The id reservation, route discovery, and non-clobbering write are the
shared capture primitives of :mod:`braintree.node_record`, so both capture
paths cannot disagree. It depends only on the standard library, opening the
sidecar solely through that shared reservation, and reads the installed
revision record through :func:`braintree.revision.feedback_revision`.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Sequence

from . import identity, vault
from .node_record import (
    canonical_path,
    discover_route,
    fit_summary,
    normalize_route,
    single_line,
    slugify,
    summary_warning,
    utc_now,
    write_new,
)
from .revision import feedback_revision
from .toon import field

__all__ = ["main"]

_USAGE = (
    "usage: braintree feedback record [--nodes DIR] [--route ROUTE] [--id FBK-NNN] "
    "[--summary TEXT] [--slug SLUG] --attempted TEXT --friction TEXT "
    "--improvement TEXT\n"
    "Write one routed, revision-stamped FBK feedback node, reserving its id "
    "atomically and falling back to a vault-local reservation without a sidecar."
)

_FEEDBACK_TYPE = "FBK"
_VALUE_OPTIONS = frozenset(
    {
        "--nodes",
        "--route",
        "--id",
        "--summary",
        "--slug",
        "--attempted",
        "--friction",
        "--improvement",
    }
)


def _render(
    route: str,
    summary: str,
    revision: str,
    attempted: str,
    friction: str,
    improvement: str,
    updated: str,
) -> str:
    return (
        "---\n"
        "context_rev: 1\n"
        "status: proposed\n"
        f"updated: {updated}\n"
        f"summary: {summary}\n"
        f"braintree_revision: {revision}\n"
        "---\n"
        "\n"
        f"{route}.\n"
        "\n"
        "# Feedback\n"
        "\n"
        f"Attempted: {attempted}\n"
        f"Friction: {friction}\n"
        f"Improvement: {improvement}\n"
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the ``braintree feedback record`` command and return the exit code."""
    args = list(sys.argv[1:] if argv is None else argv)
    nodes_dir: str | None = None
    route: str | None = None
    explicit_id: str | None = None
    summary: str | None = None
    slug: str | None = None
    content: dict[str, str] = {}
    while args:
        argument = args.pop(0)
        if argument in {"-h", "--help"}:
            print(_USAGE)
            return 0
        if argument in _VALUE_OPTIONS:
            if not args:
                print(field("error", f"{argument} requires a value"))
                return 2
            value = args.pop(0)
            if argument == "--nodes":
                nodes_dir = value
            elif argument == "--route":
                route = value
            elif argument == "--id":
                explicit_id = value
            elif argument == "--summary":
                summary = value
            elif argument == "--slug":
                slug = value
            else:
                content[argument[2:]] = value
        elif argument.startswith("-"):
            print(field("error", f"unknown option: {argument}"))
            return 2
        else:
            print(field("error", f"unexpected argument: {argument}"))
            return 2

    attempted = single_line(content.get("attempted", ""))
    friction = single_line(content.get("friction", ""))
    improvement = single_line(content.get("improvement", ""))
    missing = [
        label
        for label, value in (
            ("--attempted", attempted),
            ("--friction", friction),
            ("--improvement", improvement),
        )
        if not value
    ]
    if missing:
        print(field("error", f"braintree feedback record requires {', '.join(missing)}"))
        return 2

    nodes_dir = vault.resolve(nodes_dir)
    if not os.path.isdir(nodes_dir):
        print(field("error", f"nodes directory does not exist: {nodes_dir}"))
        print(
            field(
                "help",
                "Run from a vault root or pass --nodes pointing at its nodes directory.",
            )
        )
        return 1
    try:
        identity.ensure_project_uid(nodes_dir)
    except identity.IdentityError as error:
        print(field("error", str(error)))
        return 1

    if route is None:
        discovered = discover_route(nodes_dir)
        if discovered is None:
            print(field("error", "unable to discover a root hub in index-map.md"))
            print(field("help", "Pass --route 'Area [[IDX-...]]' to route the node."))
            return 1
        route = discovered
    normalized = normalize_route(route)
    if normalized is None:
        print(field("error", "route must be 'Parent [[NODE]]' or 'Area [[NODE]]'"))
        return 2
    route = normalized

    chosen = single_line(summary) if summary is not None else friction
    if not chosen:
        chosen = friction
    summary, truncated = fit_summary(chosen)
    slug = slugify(slug if slug is not None else summary, "feedback")

    node_id: str | None = None
    if explicit_id is not None:
        try:
            node_id = identity.normalize_node_id(single_line(explicit_id))
        except identity.IdentityError:
            print(field("error", "id must be a canonical fbk identity"))
            return 2
        if not node_id.startswith("fbk-") or not identity.CANONICAL_ID.fullmatch(node_id):
            print(field("error", "id must be a canonical fbk identity"))
            return 2

    revision = feedback_revision()
    updated = utc_now()
    for _ in range(100):
        if explicit_id is None:
            node_id = identity.generate_node_id(_FEEDBACK_TYPE)
        assert node_id is not None
        path = canonical_path(nodes_dir, node_id, slug)
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
        except OSError as error:
            print(field("error", f"unable to create canonical node directory: {error}"))
            return 1
        body = _render(route, summary, revision, attempted, friction, improvement, updated)
        if write_new(path, body):
            if truncated:
                print(field("warning", summary_warning(summary)))
            print(field("result", "recorded"))
            print(field("id", node_id))
            print(field("path", path))
            print(field("braintree_revision", revision))
            return 0
        if explicit_id is not None:
            print(field("error", f"feedback node already exists: {path}"))
            return 1

    print(field("error", "unable to generate a unique fbk identity"))
    return 1


if __name__ == "__main__":  # pragma: no cover - module entry point
    raise SystemExit(main())
