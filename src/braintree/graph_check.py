"""The read-only ``graph-check`` vault validator.

Typed Python implementation of the read-only vault validator. It enforces the same
status-directory, frontmatter, lifecycle, canonical-edge, dependency-pin,
reachability, cycle, and focus rules, and preserves the option surface,
exit codes, and error strings. The checker is deliberately stateless.
"""

from __future__ import annotations

import glob
import os
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass

__all__ = ["main"]

_USAGE = (
    "usage: graph-check [--allow-stale] [--allow-orphan NODE] [nodes-directory]\n"
    "Validate a file-only Braintree vault without writing state."
)

_STATUSES = frozenset({"proposed", "active", "blocked", "resolved"})
_CONTEXT_EDGES = ("Depends on", "Implements", "Requires", "Governed by")
_FORBIDDEN_FIELDS = ("id", "type", "status", "seq", "mtime", "rev")

_RECIPROCAL_EDGE = re.compile(
    r"(?:Child|Parent of|Indexed by|Depended on by|Supersedes|Backlink)\s+\[\["
)
_UPDATED_LINE = re.compile(r"^updated: ([^\n]+)$", re.MULTILINE)
_UPDATED_VALUE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
_WIKILINK = re.compile(r"\[\[([^\]]+)\]\]")
_CONTEXT_EDGE_LINE = re.compile(
    r"^(?:" + "|".join(_CONTEXT_EDGES) + r")\s+\[\[([^\]]+)\]\](.*)$",
    re.MULTILINE,
)
_CONTEXT_PIN = re.compile(r" at context_rev (\d+)\.")
_PRIMARY_ROUTE = re.compile(r"^(?:Parent|Area) \[\[([^\]]+)\]\]\.", re.MULTILINE)
_NODE_ID = re.compile(r"[A-Z]+-\d+")
_ROOT_ROUTE = re.compile(r"^\s*- Indexes \[\[([^\]]+)\]\]", re.MULTILINE)
_FOCUS_BLOCK = re.compile(r"^# Focus\n(.*?)(?=^# |\Z)", re.MULTILINE | re.DOTALL)
_INDEX_TABLE = re.compile(r"^\| .*\[\[", re.MULTILINE)
_INDEX_LINK = re.compile(r"\[\[([A-Z]+-\d+[^\]]*)\]\]")
_ID_ANCHOR = re.compile(r"IDX-\d+")
_NUMBER = re.compile(r"-?\d+")


class _MappingError(Exception):
    """Frontmatter was not a flat mapping."""


@dataclass
class _Node:
    path: str
    name: str
    node_id: str | None
    status: str
    text: str
    metadata: dict[str, object]


def _parse_scalar(value: str) -> object:
    if value in {"", "~", "null", "Null", "NULL"}:
        return None
    if len(value) >= 2 and value[0] == value[-1] and value[0] in {'"', "'"}:
        return value[1:-1]
    if _NUMBER.fullmatch(value):
        return int(value)
    if value in {"true", "True"}:
        return True
    if value in {"false", "False"}:
        return False
    return value


def _parse_frontmatter(header: str) -> dict[str, object]:
    """Parse the flat scalar frontmatter the vault uses.

    The stdlib has no YAML parser; the vault only stores single-line
    ``key: value`` pairs, so a strict line parser is enough and avoids adding
    a runtime dependency.
    """
    metadata: dict[str, object] = {}
    for raw_line in header.splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#"):
            continue
        key, separator, value = line.partition(":")
        if not separator or not key.strip():
            raise _MappingError
        metadata[key.strip()] = _parse_scalar(value.strip())
    if not metadata:
        raise _MappingError
    return metadata


def _extract_frontmatter(text: str) -> str | None:
    if not text.startswith("---\n"):
        return None
    lines = text.split("\n")
    for index in range(1, len(lines)):
        if re.fullmatch(r"---\s*", lines[index]):
            return "\n".join(lines[1:index])
    return None


def _read_text(path: str) -> str:
    with open(path, encoding="utf-8") as handle:
        return handle.read()


def _collect_nodes(nodes_dir: str, errors: list[str]) -> list[_Node]:
    paths = sorted(glob.glob(os.path.join(nodes_dir, "*", "*.md")))
    if not paths:
        errors.append(f"no node files under {nodes_dir}")
    nodes: list[_Node] = []
    for path in paths:
        status = os.path.basename(os.path.dirname(path))
        name = os.path.basename(path)[:-3]
        text = _read_text(path)
        if status not in _STATUSES:
            errors.append(f"{path}: invalid status directory {status}")
            continue
        header = _extract_frontmatter(text)
        if header is None:
            errors.append(f"{path}: missing frontmatter")
            continue
        try:
            metadata = _parse_frontmatter(header)
        except _MappingError:
            errors.append(f"{path}: frontmatter must be a mapping")
            continue
        context_rev = metadata.get("context_rev")
        context_rev_ok = (
            isinstance(context_rev, int)
            and not isinstance(context_rev, bool)
            and context_rev > 0
        )
        if not context_rev_ok:
            errors.append(f"{path}: context_rev must be a positive integer")
        updated_match = _UPDATED_LINE.search(header)
        updated = updated_match.group(1) if updated_match else None
        if updated is None or _UPDATED_VALUE.fullmatch(updated) is None:
            errors.append(f"{path}: updated must be UTC ISO-8601")
        summary = metadata.get("summary")
        if not (isinstance(summary, str) and summary != ""):
            errors.append(f"{path}: summary is required")
        forbidden = [key for key in metadata if key in _FORBIDDEN_FIELDS]
        if forbidden:
            errors.append(f"{path}: duplicated authority fields: {', '.join(forbidden)}")
        if status in {"active", "proposed"} and name.startswith("TAS-"):
            next_value = metadata.get("next")
            if not (isinstance(next_value, str) and next_value != ""):
                errors.append(f"{path}: unfinished task requires next")
        if status == "resolved" and "next" in metadata:
            errors.append(f"{path}: resolved node must omit next")
        if _RECIPROCAL_EDGE.search(text):
            errors.append(f"{path}: stored reciprocal edge")
        id_match = _NODE_ID.match(name)
        nodes.append(
            _Node(
                path=path,
                name=name,
                node_id=id_match.group(0) if id_match else None,
                status=status,
                text=text,
                metadata=metadata,
            )
        )
    return nodes


def _check_duplicates(nodes: list[_Node], errors: list[str]) -> dict[str, list[_Node]]:
    by_name: dict[str, list[_Node]] = {}
    for node in nodes:
        by_name.setdefault(node.name, []).append(node)
    for name, matches in by_name.items():
        if len(matches) > 1:
            errors.append(f"duplicate node identity: {name}")
    by_id: dict[str | None, list[_Node]] = {}
    for node in nodes:
        by_id.setdefault(node.node_id, []).append(node)
    for node_id, matches in by_id.items():
        if len(matches) > 1:
            label = node_id if node_id is not None else matches[0].name
            errors.append(f"duplicate node identity: {label}")
    return by_name


def _check_links(nodes: list[_Node], by_name: dict[str, list[_Node]], errors: list[str]) -> None:
    for node in nodes:
        for target in _WIKILINK.findall(node.text):
            if target not in by_name:
                errors.append(f"{node.path}: broken link [[{target}]]")


def _check_context_edges(
    nodes: list[_Node],
    by_name: dict[str, list[_Node]],
    allow_stale: bool,
    errors: list[str],
) -> None:
    for node in nodes:
        for target, suffix in _CONTEXT_EDGE_LINE.findall(node.text):
            pin_match = _CONTEXT_PIN.fullmatch(suffix)
            if pin_match is None:
                errors.append(f"{node.path}: invalid or missing context_rev pin for [[{target}]]")
                continue
            pin = int(pin_match.group(1))
            target_nodes = by_name.get(target)
            if target_nodes is None:
                continue
            current = target_nodes[0].metadata.get("context_rev")
            if not allow_stale and current != pin:
                label = current if isinstance(current, int) else ""
                errors.append(
                    f"{node.path}: context_rev mismatch for [[{target}]] "
                    f"(pinned {pin}, current {label})"
                )


def _validate(
    nodes_dir: str,
    *,
    allow_stale: bool,
    allowed_orphans: list[str | None],
) -> tuple[list[str], int]:
    errors: list[str] = []
    if not os.path.isdir(nodes_dir):
        return [f"nodes directory does not exist: {nodes_dir}"], 0
    nodes = _collect_nodes(nodes_dir, errors)
    by_name = _check_duplicates(nodes, errors)
    _check_links(nodes, by_name, errors)

    index_path = os.path.join(nodes_dir, "index-map.md")
    index_text = _read_text(index_path) if os.path.isfile(index_path) else ""
    if not os.path.isfile(index_path):
        errors.append("missing index-map.md")
    if _INDEX_TABLE.search(index_text):
        errors.append("index-map.md contains copied node-state table")
    root_hubs = list(dict.fromkeys(_ROOT_ROUTE.findall(index_text)))
    if not root_hubs:
        errors.append("index-map.md lacks an Indexes root route")
    for hub in root_hubs:
        if _ID_ANCHOR.match(hub) is None:
            errors.append(f"root hub is not IDX: {hub}")
    focus_match = _FOCUS_BLOCK.search(index_text)
    focus = list(dict.fromkeys(_WIKILINK.findall(focus_match.group(1) if focus_match else "")))

    _check_context_edges(nodes, by_name, allow_stale, errors)
    for target in _INDEX_LINK.findall(index_text):
        if target not in by_name:
            errors.append(f"index-map.md: broken link [[{target}]]")

    routes: dict[str, str | None] = {}
    for node in nodes:
        found = _PRIMARY_ROUTE.findall(node.text)
        if node.name in root_hubs:
            if found:
                errors.append(f"{node.path}: root hub must not have Parent or Area")
        elif len(found) != 1 and node.name not in allowed_orphans:
            errors.append(f"{node.path}: requires exactly one primary Parent or Area route")
        else:
            routes[node.name] = found[0] if found else None

    for node in nodes:
        next_value = node.metadata.get("next")
        if not isinstance(next_value, str) or next_value == "":
            continue
        frontier = _WIKILINK.findall(next_value)
        if len(frontier) > 1:
            errors.append(f"{node.path}: next names multiple frontier nodes")
        if len(frontier) == 1 and routes.get(frontier[0]) != node.name:
            errors.append(f"{node.path}: frontier is not a direct child")

    for node in nodes:
        if node.status == "resolved":
            continue
        current: str | None = node.name
        seen: set[str | None] = set()
        while current not in root_hubs and current not in focus:
            if current in seen:
                errors.append(f"{node.path}: parent cycle at {current}")
                break
            seen.add(current)
            if current is None or current not in routes:
                if node.name not in allowed_orphans and node.node_id not in allowed_orphans:
                    errors.append(f"{node.path}: orphan unfinished node")
                break
            current = routes[current]

    active_tasks = [
        node for node in nodes if node.status == "active" and node.name.startswith("TAS-")
    ]
    if not active_tasks and focus:
        errors.append("index-map.md: Focus remains without active tasks")
    for target in focus:
        target_nodes = by_name.get(target)
        if target_nodes is None or target_nodes[0].status != "active":
            errors.append(f"index-map.md: Focus target is not active: {target}")
    return errors, len(nodes)


def main(argv: Sequence[str] | None = None) -> int:
    """Run the ``graph-check`` command and return the process exit code."""
    args = list(sys.argv[1:] if argv is None else argv)
    allow_stale = False
    allowed_orphans: list[str | None] = []
    while args and args[0].startswith("-"):
        option = args.pop(0)
        if option == "--allow-stale":
            allow_stale = True
        elif option == "--allow-orphan":
            allowed_orphans.append(args.pop(0) if args else None)
        elif option in {"-h", "--help"}:
            print(_USAGE)
            return 0
        else:
            print("error: unknown option", file=sys.stderr)
            return 1
    nodes_dir = args.pop(0) if args else "nodes"
    if args:
        print(_USAGE)
        return 2
    errors, node_count = _validate(
        nodes_dir, allow_stale=allow_stale, allowed_orphans=allowed_orphans
    )
    for error in errors:
        print(f"error: {error}", file=sys.stderr)
    if errors:
        return 1
    print(f"graph check: passed ({node_count} nodes)")
    return 0


if __name__ == "__main__":  # pragma: no cover - module entry point
    raise SystemExit(main())
