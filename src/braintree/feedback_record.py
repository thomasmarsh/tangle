"""Record a routed Braintree ``FBK`` feedback node in a consuming project.

This is the writing half of the feedback mechanism. It stamps the installed
Braintree revision, allocates the next ``FBK`` id from Markdown, discovers a
primary route to the vault's root hub, and writes a valid feedback node in one
step. It is stdlib-only: it never opens the sidecar, never touches the network,
and reads the installed revision record through
:func:`braintree.revision.feedback_revision`.
"""

from __future__ import annotations

import glob
import os
import re
import sys
from collections.abc import Sequence
from datetime import UTC, datetime

from .revision import feedback_revision
from .toon import field

__all__ = ["main"]

_USAGE = (
    "usage: braintree feedback record [--nodes DIR] [--route ROUTE] [--id FBK-NNN] "
    "[--summary TEXT] [--slug SLUG] --attempted TEXT --friction TEXT "
    "--improvement TEXT\n"
    "Write one routed, revision-stamped FBK feedback node without a sidecar."
)

_FEEDBACK_GLOB = "FBK-*.md"
_FEEDBACK_ID = re.compile(r"FBK-(\d+)\Z")
_ROUTE = re.compile(r"^(?:Parent|Area) \[\[([^\]]+)\]\]\Z")
_ROOT_ROUTE = re.compile(r"^\s*- Indexes \[\[([^\]]+)\]\]", re.MULTILINE)
_NON_SLUG = re.compile(r"[^a-z0-9]+")
_WHITESPACE = re.compile(r"\s+")
_SUMMARY_LIMIT = 96
_SLUG_LIMIT = 48
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


def _single_line(value: str) -> str:
    return _WHITESPACE.sub(" ", value).strip()


def _slugify(value: str) -> str:
    slug = _NON_SLUG.sub("-", value.lower()).strip("-")
    return slug[:_SLUG_LIMIT].strip("-") or "feedback"


def _feedback_files(nodes_dir: str) -> list[tuple[str, str]]:
    """Return ``(id, path)`` for every ``FBK`` node already on disk."""
    found: list[tuple[str, str]] = []
    for path in sorted(glob.glob(os.path.join(nodes_dir, "*", _FEEDBACK_GLOB))):
        parts = os.path.basename(path)[:-3].split("-", 2)
        if len(parts) >= 2 and parts[1].isdigit():
            found.append((f"{parts[0]}-{parts[1]}", path))
    return found


def _existing_feedback(nodes_dir: str) -> dict[str, str]:
    """Map every ``FBK`` id already on disk to its path, across statuses."""
    return dict(_feedback_files(nodes_dir))


def _next_number(nodes_dir: str) -> int:
    numbers = [int(node_id.split("-")[1]) for node_id, _ in _feedback_files(nodes_dir)]
    return max(numbers, default=0) + 1


def _discover_route(nodes_dir: str) -> str | None:
    index_path = os.path.join(nodes_dir, "index-map.md")
    try:
        with open(index_path, encoding="utf-8") as handle:
            text = handle.read()
    except OSError:
        return None
    match = _ROOT_ROUTE.search(text)
    if match is None:
        return None
    return f"Area [[{match.group(1)}]]"


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


def _write_new(path: str, content: str) -> bool:
    """Create ``path`` without clobbering an existing node."""
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError:
        return False
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(content)
    return True


def main(argv: Sequence[str] | None = None) -> int:
    """Run the ``braintree feedback record`` command and return the exit code."""
    args = list(sys.argv[1:] if argv is None else argv)
    nodes_dir = os.environ.get("BT_NODES_DIR", "nodes")
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

    attempted = _single_line(content.get("attempted", ""))
    friction = _single_line(content.get("friction", ""))
    improvement = _single_line(content.get("improvement", ""))
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

    if not os.path.isdir(nodes_dir):
        print(field("error", f"nodes directory does not exist: {nodes_dir}"))
        print(
            field(
                "help",
                "Run from a vault root or pass --nodes pointing at its nodes directory.",
            )
        )
        return 1

    if route is None:
        route = _discover_route(nodes_dir)
        if route is None:
            print(field("error", "unable to discover a root hub in index-map.md"))
            print(field("help", "Pass --route 'Area [[IDX-...]]' to route the node."))
            return 1
    route = _single_line(route).rstrip(".")
    if _ROUTE.fullmatch(route) is None:
        print(field("error", "route must be 'Parent [[NODE]]' or 'Area [[NODE]]'"))
        return 2

    summary = _single_line(summary) if summary is not None else friction
    if not summary:
        summary = friction
    summary = summary[:_SUMMARY_LIMIT].strip()
    slug = _slugify(slug if slug is not None else summary)

    existing = _existing_feedback(nodes_dir)
    if explicit_id is not None:
        explicit_id = _single_line(explicit_id)
        if _FEEDBACK_ID.fullmatch(explicit_id) is None:
            print(field("error", "id must look like FBK-001"))
            return 2
        if explicit_id in existing:
            print(field("error", f"feedback node already exists: {existing[explicit_id]}"))
            return 1
        number = int(explicit_id.split("-")[1])
    else:
        number = _next_number(nodes_dir)

    proposed = os.path.join(nodes_dir, "proposed")
    try:
        os.makedirs(proposed, exist_ok=True)
    except OSError as error:
        print(field("error", f"unable to create {proposed}: {error}"))
        return 1

    revision = feedback_revision()
    updated = datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")
    for _ in range(100):
        node_id = f"FBK-{number:03d}"
        path = os.path.join(proposed, f"{node_id}-{slug}.md")
        body = _render(route, summary, revision, attempted, friction, improvement, updated)
        if _write_new(path, body):
            print(field("result", "recorded"))
            print(field("id", node_id))
            print(field("path", path))
            print(field("braintree_revision", revision))
            return 0
        if explicit_id is not None:
            print(field("error", f"feedback node already exists: {path}"))
            return 1
        number += 1

    print(field("error", "unable to allocate a free FBK id"))
    return 1


if __name__ == "__main__":  # pragma: no cover - module entry point
    raise SystemExit(main())
