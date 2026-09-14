"""Migrate legacy status-directory nodes into the stationary canonical store.

The compatibility window reads uppercase numeric nodes from the fixed status
directories. This module is the explicit, opt-in path that retires that layout
for one vault: every legacy node moves once to ``canonical/<suffix>/`` with an
authoritative ``status`` field, so later status changes become content edits
instead of path moves.

The migration is deliberately conservative:

- it preserves the node's identity, basename, and wikilinks, so no consumer
  reference changes and Git can detect the move as a rename;
- it plans every move and rejects the whole plan on a collision before writing
  anything;
- it refreshes only ``updated`` and the authoritative ``status`` field, and it
  never bumps ``context_rev`` because the node's meaning is unchanged;
- an apply journals each original byte string and rolls every completed move
  back when a later one fails;
- a case-only rename is staged through an intermediate name so a
  case-insensitive filesystem cannot turn it into a silent no-op.

It never runs implicitly. ``braintree stationarize`` plans by default and only
writes with ``--apply``.
"""

from __future__ import annotations

import os
import re
import sys
from collections.abc import Iterator, Sequence
from dataclasses import dataclass

from . import identity, store, vault
from .node_record import utc_now
from .toon import field, table

__all__ = [
    "LegacyNode",
    "MigrationError",
    "MigrationPlan",
    "MigrationResult",
    "apply",
    "case_safe_move",
    "main",
    "plan",
]

_STATUSES = ("proposed", "active", "blocked", "resolved")
# The legacy basename is the uppercase numeric id plus an optional slug. The id
# itself contains a hyphen, so match it before splitting off the slug.
_LEGACY_BASENAME = re.compile(r"^(?P<id>[A-Z][A-Z0-9_]*-\d+)(?:-(?P<slug>.*))?\.md$")
_USAGE = "usage: braintree stationarize [NODES] [--apply]"


class MigrationError(Exception):
    """A vault cannot be migrated as planned without losing or merging state."""


@dataclass(frozen=True)
class LegacyNode:
    """One legacy node and the stationary path it will occupy."""

    node_id: str
    status: str
    source: str
    target: str


@dataclass(frozen=True)
class MigrationPlan:
    """The complete, collision-checked set of moves for one vault."""

    nodes_dir: str
    nodes: tuple[LegacyNode, ...]

    @property
    def is_empty(self) -> bool:
        return not self.nodes


@dataclass(frozen=True)
class MigrationResult:
    """What one applied migration changed."""

    moved: int
    project_uid: str


def _node_id(basename: str) -> str | None:
    """Return the legacy node id a status-directory basename carries, if any."""
    match = _LEGACY_BASENAME.fullmatch(basename)
    if match is None:
        return None
    return match.group("id")


def plan(nodes_dir: str) -> MigrationPlan:
    """Return the migration plan for one vault without writing anything.

    Discovery uses the same authority-bearing file set as every read command,
    so a stationary node is never re-migrated. Any collision that would merge
    or overwrite state raises :class:`MigrationError` for the whole vault.
    """
    nodes_dir = os.path.abspath(nodes_dir)
    if not os.path.isdir(nodes_dir):
        raise MigrationError(f"vault directory does not exist: {nodes_dir}")

    moves: list[LegacyNode] = []
    by_identity: dict[str, str] = {}
    planned_targets: dict[str, str] = {}
    for entry in store.iter_node_paths(nodes_dir):
        if entry.stationary or entry.status not in _STATUSES:
            continue
        basename = os.path.basename(entry.path)
        node_id = _node_id(basename)
        if node_id is None or not identity.is_node_id(node_id):
            raise MigrationError(
                f"legacy node has no readable uppercase numeric identity: {entry.path}"
            )
        if node_id in by_identity:
            raise MigrationError(
                f"duplicate node identity {node_id}: "
                f"{by_identity[node_id]} and {entry.path}"
            )
        by_identity[node_id] = entry.path
        target = os.path.join(
            nodes_dir, store.CANONICAL_DIRECTORY, node_id[-2:], basename
        )
        if target in planned_targets:
            raise MigrationError(
                f"two nodes would share the canonical path {target}: "
                f"{planned_targets[target]} and {entry.path}"
            )
        planned_targets[target] = entry.path
        if os.path.exists(target):
            raise MigrationError(f"canonical target already exists: {target}")
        moves.append(
            LegacyNode(
                node_id=node_id, status=entry.status, source=entry.path, target=target
            )
        )
    moves.sort(key=lambda move: move.source)
    return MigrationPlan(nodes_dir=nodes_dir, nodes=tuple(moves))


def apply(plan: MigrationPlan, *, updated: str | None = None) -> MigrationResult:
    """Perform every planned move, rolling all completed moves back on failure.

    The caller's plan is the complete authority for this attempt. Each source
    byte string is read before its move and journalled, so an error in a later
    move restores every earlier source exactly and removes its partial target.
    """
    if plan.is_empty:
        raise MigrationError("the plan has no legacy nodes to migrate")
    project_uid = identity.ensure_project_uid(plan.nodes_dir)
    timestamp = utc_now() if updated is None else updated
    journal: list[tuple[LegacyNode, str]] = []
    try:
        for node in plan.nodes:
            original = _read(node.source)
            stamped = _stamp_status(original, node.status, timestamp)
            journal.append((node, original))
            case_safe_move(node.source, node.target, stamped)
    except Exception:
        for node, original in reversed(journal):
            _restore(node, original)
        raise
    return MigrationResult(moved=len(plan.nodes), project_uid=project_uid)


def _read(path: str) -> str:
    try:
        with open(path, encoding="utf-8") as handle:
            return handle.read()
    except OSError as exc:
        raise MigrationError(f"unable to read {path}: {exc}") from exc


def _stamp_status(text: str, status: str, timestamp: str) -> str:
    """Return ``text`` with an authoritative status and a fresh ``updated``.

    Only the two mutable fields change. ``context_rev`` is deliberately left
    alone: a storage migration does not alter what a pinned consumer reads.
    """
    lines = text.split("\n")
    if not lines or lines[0] != "---":
        raise MigrationError("legacy node is missing its frontmatter")
    try:
        close = lines.index("---", 1)
    except ValueError as exc:
        raise MigrationError("legacy node has unterminated frontmatter") from exc
    front = lines[1:close]
    rest = lines[close + 1 :]

    existing: str | None = None
    found_updated = False
    for position, line in enumerate(front):
        key, separator, value = line.partition(":")
        if key.strip() == "status":
            existing = value.strip().strip("'\"") if separator else ""
        elif key.strip() == "updated":
            front[position] = f"updated: {timestamp}"
            found_updated = True
    if existing is not None and existing != status:
        raise MigrationError(
            f"frontmatter status {existing!r} disagrees with its directory {status!r}"
        )
    if not found_updated:
        raise MigrationError("legacy node is missing the required updated field")
    if existing is None:
        front.insert(0, f"status: {status}")
    return "\n".join(["---", *front, "---", *rest])


def case_safe_move(source: str, target: str, text: str) -> None:
    """Write ``text`` to ``target`` and remove ``source``.

    When the two names differ only by case, the move goes through an
    intermediate name first: a case-insensitive filesystem would otherwise
    resolve both to the same directory entry and quietly do nothing.
    """
    os.makedirs(os.path.dirname(target), exist_ok=True)
    case_only = source != target and source.casefold() == target.casefold()
    if not case_only and os.path.exists(target):
        raise MigrationError(f"canonical target already exists: {target}")
    staged = source
    # Case-insensitive-equal but string-unequal is the case-only signature on
    # every platform, whether the running filesystem is case-sensitive or not.
    if case_only:
        staged = source + ".case-migrating"
        os.replace(source, staged)
    try:
        with open(target, "w", encoding="utf-8") as handle:
            handle.write(text)
    except OSError:
        if staged != source:
            os.replace(staged, source)
        raise
    try:
        os.remove(staged)
    except OSError:
        if staged != source and os.path.exists(staged):
            os.replace(staged, source)
        if os.path.exists(target):
            os.remove(target)
        raise


def _restore(node: LegacyNode, original: str) -> None:
    """Put one journalled source back exactly and drop any partial target."""
    os.makedirs(os.path.dirname(node.source), exist_ok=True)
    with open(node.source, "w", encoding="utf-8") as handle:
        handle.write(original)
    for leftover in (node.target, node.source + ".case-migrating"):
        try:
            os.remove(leftover)
        except OSError:
            pass


def _moves(plan: MigrationPlan) -> Iterator[tuple[str, str, str, str]]:
    for node in plan.nodes:
        yield (node.node_id, node.status, node.source, node.target)


def main(argv: Sequence[str] | None = None) -> int:
    """Run ``braintree stationarize`` and return the process exit code."""
    args = list(sys.argv[1:] if argv is None else argv)
    apply_plan = False
    operand: str | None = None
    while args:
        argument = args.pop(0)
        if argument in {"-h", "--help"}:
            print(_USAGE)
            return 0
        if argument == "--apply":
            apply_plan = True
        elif argument == "--nodes":
            if not args:
                print(field("error", "--nodes requires a directory"))
                return 2
            operand = args.pop(0)
        elif argument.startswith("-"):
            print(field("error", f"unknown option: {argument}"))
            return 2
        elif operand is None:
            operand = argument
        else:
            print(field("error", f"unexpected argument: {argument}"))
            return 2

    nodes_dir = vault.resolve(operand)
    try:
        migration_plan = plan(nodes_dir)
    except MigrationError as error:
        print(field("error", str(error)))
        return 1
    if migration_plan.is_empty:
        print(field("result", "no-op"))
        print(field("detail", "no legacy status-directory nodes to migrate"))
        return 0
    if not apply_plan:
        print(field("result", "planned"))
        print(table("moves", "id,status,source,target", _moves(migration_plan)))
        print(field("apply", "rerun with --apply to perform the migration"))
        return 0
    try:
        result = apply(migration_plan)
    except MigrationError as error:
        print(field("error", str(error)))
        return 1
    print(field("result", "migrated"))
    print(field("moved", result.moved))
    print(field("project_uid", result.project_uid))
    return 0


if __name__ == "__main__":  # pragma: no cover - module entry point
    raise SystemExit(main())
