"""Create a routed, stamped Braintree node of a named type in one step.

This is the generic capture path behind ``braintree node record``. It supplies
the id, route, timestamp, and required frontmatter a caller would otherwise
hand-author: it allocates the next id from Markdown and discovers the primary
route to the vault's root hub the way ``braintree feedback record`` does for
``FBK``. The Markdown-node writer primitives it holds are the single spelling
of allocation, route discovery, and non-clobbering writes shared with that
command. It is stdlib-only: it never opens the sidecar, never touches the
network.
"""

from __future__ import annotations

import glob
import os
import re
import sys
from collections.abc import Sequence
from datetime import UTC, datetime

from .toon import field

__all__ = [
    "discover_route",
    "existing_ids",
    "id_number",
    "main",
    "next_number",
    "normalize_route",
    "single_line",
    "slugify",
    "utc_now",
    "write_new",
]

_USAGE = (
    "usage: braintree node record --type TYPE --summary TEXT --body TEXT "
    "[--status proposed|active|blocked|resolved] [--next TEXT] [--nodes DIR] "
    "[--route ROUTE] [--id ID] [--slug SLUG]\n"
    "Write one routed, stamped node of the named type without a sidecar."
)

# The capture types the vault documents, split by the ``next`` rule the checker
# enforces: a knowledge type records a question, invariant, or decision, while
# a task type is executable work and needs one. FBK is recorded by
# ``braintree feedback record`` and a root IDX hub is declared in
# ``index-map.md``, so neither is a capture target.
_KNOWLEDGE_TYPES = ("THO", "DEF", "DEC")
_TASK_TYPES = ("TAS",)
_CAPTURE_TYPES = _KNOWLEDGE_TYPES + _TASK_TYPES
_STATUSES = ("proposed", "active", "blocked", "resolved")
_DEFAULT_STATUS = "proposed"
_BLOCKED_HEADING = re.compile(r"^# Blocked\s*$", re.MULTILINE)

_ROUTE = re.compile(r"^(?:Parent|Area) \[\[([^\]]+)\]\]\Z")
_ROOT_ROUTE = re.compile(r"^\s*- Indexes \[\[([^\]]+)\]\]", re.MULTILINE)
_WIKILINK_ONLY = re.compile(r"\[\[([^\]]+)\]\]\Z")
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
        "--type",
        "--status",
        "--next",
        "--body",
    }
)


def single_line(value: str) -> str:
    """Collapse ``value`` to one whitespace-normalized line."""
    return _WHITESPACE.sub(" ", value).strip()


def slugify(value: str, fallback: str) -> str:
    """Return a lowercase filename slug, or ``fallback`` when none survives."""
    slug = _NON_SLUG.sub("-", value.lower()).strip("-")
    return slug[:_SLUG_LIMIT].strip("-") or fallback


def id_number(node_id: str, prefix: str) -> int | None:
    """Return the number of a ``<prefix>-NNN`` id, or ``None`` when malformed."""
    match = re.fullmatch(re.escape(prefix) + r"-(\d+)", node_id)
    return int(match.group(1)) if match is not None else None


def existing_ids(nodes_dir: str, prefix: str) -> dict[str, str]:
    """Map every ``<prefix>-NNN`` id already on disk to its path, across statuses."""
    found: dict[str, str] = {}
    for path in sorted(glob.glob(os.path.join(nodes_dir, "*", f"{prefix}-*.md"))):
        parts = os.path.basename(path)[:-3].split("-", 2)
        if len(parts) >= 2 and parts[1].isdigit():
            found[f"{parts[0]}-{parts[1]}"] = path
    return found


def next_number(nodes_dir: str, prefix: str) -> int:
    """Return the next free number for ``prefix`` from Markdown alone."""
    numbers = [int(node_id.split("-")[1]) for node_id in existing_ids(nodes_dir, prefix)]
    return max(numbers, default=0) + 1


def discover_route(nodes_dir: str) -> str | None:
    """Return the primary route to the root hub ``index-map.md`` names."""
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


def normalize_route(route: str) -> str | None:
    """Return the canonical ``Parent``/``Area`` route, or ``None`` if malformed."""
    candidate = single_line(route).rstrip(".")
    return candidate if _ROUTE.fullmatch(candidate) is not None else None


def write_new(path: str, content: str) -> bool:
    """Create ``path`` without clobbering an existing node."""
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError:
        return False
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(content)
    return True


def utc_now() -> str:
    """Return the current UTC timestamp in the vault's frontmatter format."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def _next_field(value: str) -> str:
    """Render a ``next`` value, quoting a lone wikilink to keep it a scalar."""
    if _WIKILINK_ONLY.fullmatch(value) is None:
        return value
    return f'"{value}"'


def _render(route: str, summary: str, next_line: str | None, body: str, updated: str) -> str:
    header = ["---", "context_rev: 1", f"updated: {updated}", f"summary: {summary}"]
    if next_line is not None:
        header.append(f"next: {_next_field(next_line)}")
    header.append("---")
    return "\n".join(header) + "\n\n" + f"{route}.\n\n" + body + "\n"


def main(argv: Sequence[str] | None = None) -> int:
    """Run ``braintree node record`` and return the process exit code."""
    args = list(sys.argv[1:] if argv is None else argv)
    nodes_dir = os.environ.get("BT_NODES_DIR", "nodes")
    node_type: str | None = None
    route: str | None = None
    explicit_id: str | None = None
    summary: str | None = None
    slug: str | None = None
    status = _DEFAULT_STATUS
    next_value: str | None = None
    body: str | None = None
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
            elif argument == "--type":
                node_type = value
            elif argument == "--status":
                status = value
            elif argument == "--next":
                next_value = value
            else:
                body = value
        elif argument.startswith("-"):
            print(field("error", f"unknown option: {argument}"))
            return 2
        else:
            print(field("error", f"unexpected argument: {argument}"))
            return 2

    node_type = single_line(node_type or "").upper()
    if node_type not in _CAPTURE_TYPES:
        print(field("error", f"--type must be one of {', '.join(_CAPTURE_TYPES)}"))
        print(
            field(
                "help",
                "FBK friction is recorded with `braintree feedback record`, and a "
                "root IDX hub is declared in index-map.md.",
            )
        )
        return 2

    status = single_line(status).lower()
    if status not in _STATUSES:
        print(field("error", f"--status must be one of {', '.join(_STATUSES)}"))
        return 2

    summary = single_line(summary or "")[:_SUMMARY_LIMIT].strip()
    if not summary:
        print(field("error", "braintree node record requires --summary"))
        return 2

    body = (body or "").strip("\n")
    if not body.strip():
        print(field("error", "braintree node record requires --body"))
        return 2

    next_line = single_line(next_value) if next_value is not None else None
    if status == "resolved":
        if next_line:
            print(field("error", "a resolved node must omit --next"))
            return 2
        next_line = None
    elif node_type in _TASK_TYPES and not next_line:
        print(field("error", f"a {node_type} node in {status} requires --next"))
        print(
            field(
                "help",
                "Pass the one action, for example --next 'Add the boundary test.' "
                "or --next '[[direct-child]]'.",
            )
        )
        return 2
    if status == "blocked" and (
        _BLOCKED_HEADING.search(body) is None
        or "Blocked by" not in body
        or "Unblocks when" not in body
    ):
        print(
            field(
                "error",
                "a blocked node body requires a # Blocked section with "
                "Blocked by and Unblocks when",
            )
        )
        print(field("help", "Pass that section in --body, or choose another --status."))
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

    existing = existing_ids(nodes_dir, node_type)
    if explicit_id is not None:
        explicit_id = single_line(explicit_id)
        number = id_number(explicit_id, node_type)
        if number is None:
            print(field("error", f"id must look like {node_type}-001"))
            return 2
        if explicit_id in existing:
            print(field("error", f"node already exists: {existing[explicit_id]}"))
            return 1
    else:
        number = next_number(nodes_dir, node_type)

    directory = os.path.join(nodes_dir, status)
    try:
        os.makedirs(directory, exist_ok=True)
    except OSError as error:
        print(field("error", f"unable to create {directory}: {error}"))
        return 1

    slug = slugify(slug if slug is not None else summary, "node")
    updated = utc_now()
    for _ in range(100):
        node_id = f"{node_type}-{number:03d}"
        path = os.path.join(directory, f"{node_id}-{slug}.md")
        if write_new(path, _render(route, summary, next_line, body, updated)):
            print(field("result", "recorded"))
            print(field("id", node_id))
            print(field("path", path))
            print(field("status", status))
            return 0
        if explicit_id is not None:
            print(field("error", f"node already exists: {path}"))
            return 1
        number += 1

    print(field("error", f"unable to allocate a free {node_type} id"))
    return 1


if __name__ == "__main__":  # pragma: no cover - module entry point
    raise SystemExit(main())
