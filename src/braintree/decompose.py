"""Transactional decomposition authoring: ordered children plus the parent advance.

``braintree node decompose`` validates a whole ordered-child plan before it
mutates Markdown, reserves every child id, writes each child with its canonical
``Parent`` route and its executable ``next``, and advances the parent's ``next``
to the first child in one all-or-nothing operation. ``braintree node advance``
is the parent-advance-only shorthand. Both live here because
``src/braintree/cli.py`` is frozen observable prompt content in
``benchmark/memory-authority-cases.json``; a byte change there would invalidate
the committed measurement.

The plan is a small JSON document, ``{"children": [...]}``, so every child is
validated before any id is reserved: a rejected plan burns nothing, and a write
failure removes the children already written and leaves the parent unchanged.
The ids reserved before such a failure stay burned, exactly as the discard rule
for ``braintree allocate`` states.
"""

from __future__ import annotations

import json
import os
import re
import sys
import tempfile
from collections.abc import Sequence
from dataclasses import dataclass

from . import index, node_record, store, vault
from .toon import field

__all__ = ["advance_main", "main"]

_DECOMPOSE_USAGE = (
    "usage: braintree node decompose --parent PARENT --plan FILE "
    "[--nodes DIR] [--dry-run]\n"
    "Validate an ordered-child plan, allocate its ids, write every child with "
    "its canonical Parent route and executable next, and advance the parent to "
    "the first child atomically."
)
_ADVANCE_USAGE = (
    "usage: braintree node advance PARENT CHILD [--nodes DIR]\n"
    "Advance one coordinating parent's next to a direct child."
)

# The plan grammar is closed: an unknown key is rejected rather than ignored, so
# a typo cannot silently drop a child field.
_PLAN_KEYS = frozenset({"children"})
_CHILD_KEYS = frozenset({"type", "summary", "body", "next", "status", "slug"})

_NEXT_LINE = re.compile(r"^next:.*$", re.MULTILINE)
_UPDATED_LINE = re.compile(r"^updated:.*$", re.MULTILINE)
_PARENT_ROUTE = re.compile(r"^Parent \[\[([^\]]+)\]\]\.", re.MULTILINE)


class _DecomposeError(Exception):
    """A decomposition could not be validated or committed."""


@dataclass(frozen=True)
class PlanChild:
    """One validated ordered child from a decomposition plan."""

    node_type: str
    summary: str
    body: str
    next_line: str | None
    status: str
    slug: str
    truncated: bool


def _read_text(path: str) -> str:
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def _atomic_write(path: str, text: str) -> None:
    """Replace ``path`` with ``text`` through a same-directory temp rename."""
    directory = os.path.dirname(path)
    descriptor, temporary = tempfile.mkstemp(dir=directory, prefix=".node-", suffix=".tmp")
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(text)
        os.replace(temporary, path)
    except OSError:
        try:
            os.unlink(temporary)
        except OSError:
            pass
        raise


def _find_node(nodes_dir: str, reference: str) -> tuple[str, str] | None:
    """Resolve a bare id or full node name to ``(status, path)``, or ``None``."""
    matches = [
        entry
        for entry in store.iter_node_paths(nodes_dir)
        if (stem := os.path.basename(entry.path)[:-3]) == reference
        or stem.startswith(reference + "-")
    ]
    if len(matches) != 1:
        return None
    entry = matches[0]
    return (entry.status, entry.path) if entry.status is not None else None


def _parse_child(index: int, item: object) -> tuple[PlanChild | None, str | None]:
    if not isinstance(item, dict):
        return None, f"child {index} must be a JSON object"
    unknown = sorted(set(item) - _CHILD_KEYS)
    if unknown:
        return None, f"child {index} has unknown keys: {', '.join(unknown)}"
    node_type = node_record.single_line(str(item.get("type", ""))).upper()
    if node_type not in node_record._CAPTURE_TYPES:
        return None, (
            f"child {index} type must be one of "
            f"{', '.join(node_record._CAPTURE_TYPES)}"
        )
    raw_summary = item.get("summary")
    if not isinstance(raw_summary, str) or not raw_summary.strip():
        return None, f"child {index} requires a summary"
    summary, truncated = node_record.fit_summary(raw_summary)
    raw_body = item.get("body")
    if not isinstance(raw_body, str) or not raw_body.strip():
        return None, f"child {index} requires a body"
    body = raw_body.strip("\n")
    status = node_record.single_line(str(item.get("status", "proposed"))).lower()
    if status not in node_record._STATUSES:
        return None, (
            f"child {index} status must be one of "
            f"{', '.join(node_record._STATUSES)}"
        )
    raw_next = item.get("next")
    if raw_next is not None and not isinstance(raw_next, str):
        return None, f"child {index} next must be a string"
    next_line = node_record.single_line(raw_next) if raw_next else None
    if status == "resolved":
        if next_line:
            return None, f"child {index} is resolved and must omit next"
        next_line = None
    elif node_type in node_record._TASK_TYPES and not next_line:
        return None, f"child {index} is an unfinished {node_type} and requires next"
    if status == "blocked" and (
        node_record._BLOCKED_HEADING.search(body) is None
        or "Blocked by" not in body
        or "Unblocks when" not in body
    ):
        return None, (
            f"child {index} is blocked and requires a # Blocked section with "
            "Blocked by and Unblocks when"
        )
    raw_slug = item.get("slug")
    if raw_slug is not None and not isinstance(raw_slug, str):
        return None, f"child {index} slug must be a string"
    slug = node_record.slugify(raw_slug if raw_slug is not None else summary, "node")
    return (
        PlanChild(
            node_type=node_type,
            summary=summary,
            body=body,
            next_line=next_line,
            status=status,
            slug=slug,
            truncated=truncated,
        ),
        None,
    )


def _load_plan(path: str) -> tuple[list[PlanChild] | None, str | None]:
    try:
        with open(path, encoding="utf-8") as handle:
            raw = json.load(handle)
    except OSError as error:
        return None, f"unable to read plan {path}: {error}"
    except json.JSONDecodeError as error:
        return None, f"plan is not valid JSON: {error}"
    if not isinstance(raw, dict):
        return None, "plan must be a JSON object"
    unknown = sorted(set(raw) - _PLAN_KEYS)
    if unknown:
        return None, f"plan has unknown keys: {', '.join(unknown)}"
    items = raw.get("children")
    if not isinstance(items, list) or not items:
        return None, "plan requires a non-empty children list"
    children: list[PlanChild] = []
    for position, item in enumerate(items):
        child, problem = _parse_child(position, item)
        if problem is not None:
            return None, problem
        assert child is not None
        children.append(child)
    return children, None


def _insert_next(text: str, line: str) -> str:
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        raise _DecomposeError("parent has no frontmatter to advance")
    for line_index in range(1, len(lines)):
        if lines[line_index].strip() == "---":
            lines.insert(line_index, line)
            return "\n".join(lines)
    raise _DecomposeError("parent frontmatter is unterminated")


def _advance_parent(text: str, child_name: str, updated: str) -> str:
    """Return ``text`` with ``next`` pointing at ``child_name`` and a fresh stamp."""
    if _UPDATED_LINE.search(text) is None:
        raise _DecomposeError("parent frontmatter has no updated line")
    advanced = _UPDATED_LINE.sub(f"updated: {updated}", text, count=1)
    line = f'next: "[[{child_name}]]"'
    if _NEXT_LINE.search(advanced):
        return _NEXT_LINE.sub(line, advanced, count=1)
    return _insert_next(advanced, line)


def _advance(nodes_dir: str, reference: str, child_name: str) -> str:
    """Advance an unfinished parent and return the first child's full name."""
    found = _find_node(nodes_dir, reference)
    if found is None:
        raise _DecomposeError(f"unknown parent: {reference}")
    status, path = found
    if status == "resolved":
        raise _DecomposeError(f"parent is resolved and cannot carry next: {reference}")
    updated = node_record.utc_now()
    _atomic_write(path, _advance_parent(_read_text(path), child_name, updated))
    return child_name


def _usage_error(usage: str, message: str) -> int:
    print(field("error", message))
    print(field("help", f"Run `{usage}`."))
    return 2


def _option_value(args: list[str], option: str) -> str | None:
    if not args:
        return None
    return args.pop(0)


def main(argv: Sequence[str] | None = None) -> int:
    """Run ``braintree node decompose`` and return the process exit code."""
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "node":
        args = args[1:]
    if args and args[0] == "decompose":
        args = args[1:]
    parent: str | None = None
    plan_path: str | None = None
    nodes_override: str | None = None
    dry_run = False
    while args:
        argument = args.pop(0)
        if argument in {"-h", "--help"}:
            print(_DECOMPOSE_USAGE)
            return 0
        if argument == "--dry-run":
            dry_run = True
        elif argument in {"--parent", "--plan", "--nodes"}:
            value = _option_value(args, argument)
            if value is None:
                return _usage_error(_DECOMPOSE_USAGE, f"{argument} requires a value")
            if argument == "--parent":
                parent = value
            elif argument == "--plan":
                plan_path = value
            else:
                nodes_override = value
        elif argument.startswith("-"):
            return _usage_error(_DECOMPOSE_USAGE, f"unknown option: {argument}")
        else:
            return _usage_error(_DECOMPOSE_USAGE, f"unexpected argument: {argument}")
    if parent is None or plan_path is None:
        return _usage_error(
            _DECOMPOSE_USAGE, "node decompose requires --parent and --plan"
        )
    nodes_dir = vault.resolve(nodes_override)
    if not os.path.isdir(nodes_dir):
        print(field("error", f"nodes directory does not exist: {nodes_dir}"))
        print(field("help", "Run from a vault root or pass --nodes."))
        return 1
    found = _find_node(nodes_dir, parent)
    if found is None:
        print(field("error", f"unknown parent: {parent}"))
        return 1
    parent_status, parent_path = found
    if parent_status == "resolved":
        print(field("error", f"parent is resolved: {parent}"))
        return 1
    parent_name = os.path.basename(parent_path)[:-3]
    children, error = _load_plan(plan_path)
    if error is not None:
        print(field("error", error))
        print(field("help", "See `braintree help authoring` for the plan grammar."))
        return 2
    assert children is not None
    if dry_run:
        print(field("result", "dry-run"))
        print(field("parent", parent_name))
        print(
            _planned_table(children)
        )
        return 0
    allocated: list[tuple[int, PlanChild]] = []
    for child in children:
        allocated.append((node_record.reserve_number(nodes_dir, child.node_type), child))
    created: list[str] = []
    try:
        updated = node_record.utc_now()
        for number, child in allocated:
            node_id = f"{child.node_type}-{number:03d}"
            path = os.path.join(
                nodes_dir, child.status, f"{node_id}-{child.slug}.md"
            )
            os.makedirs(os.path.dirname(path), exist_ok=True)
            content = node_record.render(
                f"Parent [[{parent_name}]]",
                child.summary,
                child.next_line,
                child.body,
                updated,
            )
            if not node_record.write_new(path, content):
                raise _DecomposeError(f"node already exists: {path}")
            created.append(path)
        first = allocated[0]
        first_name = f"{first[1].node_type}-{first[0]:03d}-{first[1].slug}"
        _advance(nodes_dir, parent_name, first_name)
    except (_DecomposeError, OSError) as error:
        for path in created:
            try:
                os.unlink(path)
            except OSError:
                pass
        print(field("error", str(error)))
        print(
            field(
                "help",
                "No child or parent edit was kept; any reserved id remains burned.",
            )
        )
        return 1
    print(field("result", "decomposed"))
    print(field("parent", parent_name))
    print(field("next", first_name))
    print(
        _recorded_table(allocated)
    )
    for _number, child in allocated:
        if child.truncated:
            print(field("warning", node_record.summary_warning(child.summary)))
    return 0


def advance_main(argv: Sequence[str] | None = None) -> int:
    """Run ``braintree node advance PARENT CHILD`` and return the exit code."""
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "node":
        args = args[1:]
    if args and args[0] == "advance":
        args = args[1:]
    nodes_override: str | None = None
    positional: list[str] = []
    while args:
        argument = args.pop(0)
        if argument in {"-h", "--help"}:
            print(_ADVANCE_USAGE)
            return 0
        if argument == "--nodes":
            value = _option_value(args, argument)
            if value is None:
                return _usage_error(_ADVANCE_USAGE, "--nodes requires a value")
            nodes_override = value
        elif argument.startswith("-"):
            return _usage_error(_ADVANCE_USAGE, f"unknown option: {argument}")
        else:
            positional.append(argument)
    if len(positional) != 2:
        return _usage_error(_ADVANCE_USAGE, "node advance requires PARENT and CHILD")
    parent, child = positional
    nodes_dir = vault.resolve(nodes_override)
    if not os.path.isdir(nodes_dir):
        print(field("error", f"nodes directory does not exist: {nodes_dir}"))
        return 1
    found = _find_node(nodes_dir, child)
    if found is None:
        print(field("error", f"unknown child: {child}"))
        return 1
    _child_status, child_path = found
    child_name = os.path.basename(child_path)[:-3]
    parent_found = _find_node(nodes_dir, parent)
    if parent_found is None:
        print(field("error", f"unknown parent: {parent}"))
        return 1
    _parent_status, parent_path = parent_found
    parent_name = os.path.basename(parent_path)[:-3]
    route = _PARENT_ROUTE.search(_read_text(child_path))
    if route is None or route.group(1) != parent_name:
        print(
            field(
                "error",
                f"{child_name} is not a direct child of {parent_name}",
            )
        )
        print(field("help", "Advance only a child whose Parent route names PARENT."))
        return 1
    try:
        _advance(nodes_dir, parent_name, child_name)
    except (_DecomposeError, OSError) as error:
        print(field("error", str(error)))
        return 1
    print(field("result", "advanced"))
    print(field("parent", parent_name))
    print(field("next", child_name))
    return 0


def _planned_table(children: Sequence[PlanChild]) -> str:
    return index.format_table(
        "children",
        "type,status,summary",
        "children: 0 children",
        [(child.node_type, child.status, child.summary) for child in children],
    )


def _recorded_table(allocated: Sequence[tuple[int, PlanChild]]) -> str:
    rows = []
    for number, child in allocated:
        rows.append(
            (
                f"{child.node_type}-{number:03d}",
                child.status,
                f"{child.node_type}-{number:03d}-{child.slug}.md",
            )
        )
    return index.format_table(
        "children",
        "id,status,filename",
        "children: 0 children",
        rows,
    )
