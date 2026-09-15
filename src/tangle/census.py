"""Pre-dispatch hash census of the canonical store and its diagnostic surface.

Every project-scoped interaction that maintains derived state first enumerates
the complete canonical node store and reconciles the derived index against it
*before* its command body runs, so a direct Markdown edit is observed before the
next command answers. The census is a cryptographic one: it reads each
authority-bearing Markdown file and hashes its exact bytes, so mtime, size,
inode, watchers, Git status, and caller-supplied paths never substitute for it
and a preserved-mtime byte edit is still detected. Node discovery excludes the
disposable ``views/`` pages and the reserved ``proposals/``, ``acceptances/``,
and ``receipts/`` directories, and a same-directory temporary file does not end
in ``.md``, so none of them is mistaken for a node.

The reconciliation is the incremental :func:`tangle.index.refresh`: it compares
path, identity, and digest sets, writes only the changed node, edge, and
full-text rows, removes the rows of vanished files, and raises each prefix's id
reservation above Markdown. A lost, partial, or foreign index is rebuilt from
the same Markdown snapshot the whole :func:`tangle.index.reindex` uses, which is
a full parse. An absent sidecar is a silent no-op so a fresh vault creates no
local state.

``tangle census`` is the dedicated diagnostic surface: it reports whether the
last hash census found zero or N changes and whether the generated views were
current, updated, or failed. Routine interactions stay silent on a successful
no-op; this surface is the one that speaks. Except for the disposable view
projection it republishes from the reconciled snapshot, it writes nothing, and
it never creates local state for a vault that has none.

``src/tangle/cli.py`` and ``src/tangle/sidecar.py`` are frozen observable prompt
content in ``benchmark/memory-authority-cases.json``; this module keeps the
census on a new, non-observable path that ``main.py`` dispatches.
"""

from __future__ import annotations

import os
import sqlite3
import sys
from collections.abc import Sequence
from dataclasses import dataclass

from . import index, sidecar, vault, views
from .toon import field

__all__ = ["CensusReport", "last_report", "main", "reconcile"]

_USAGE = (
    "usage: tangle census\n"
    "Reconcile the canonical-store hash census before dispatch and report the\n"
    "last census change count and the generated-view state.\n"
    "Exits 0 when the census reconciled or no local state exists; 1 when the\n"
    "vault or local state is unavailable or the reconciliation failed."
)

# The statuses at which the census reached the vault and reconciled it, so the
# view projection is meaningful and the surface reports success.
_ANSWERED = frozenset({"reconciled", "uninitialized"})


@dataclass(frozen=True)
class CensusReport:
    """The outcome of one pre-dispatch canonical-store hash census.

    ``status`` is ``reconciled`` when the census hashed the store and reconciled
    the derived index, ``uninitialized`` when no local state exists (nothing was
    created), ``unavailable`` when the vault or state location cannot be read,
    ``busy`` when another writer held the state lock, and ``failed`` when the
    reconciliation raised. ``changes`` counts the canonical node files the
    census found new or changed, ``edges`` counts the edge rows it rewrote, and
    ``removed`` counts the vanished node rows it deleted. ``detail`` carries the
    failure message for ``busy`` and ``failed``.
    """

    status: str
    root: str
    changes: int
    edges: int
    removed: int
    detail: str = ""


_LAST: CensusReport | None = None


def last_report() -> CensusReport | None:
    """Return the census recorded for the interaction in progress, if any."""
    return _LAST


def _stored_ids(connection: sqlite3.Connection) -> set[str]:
    """Return the node ids the index stores, or none before its schema exists."""
    try:
        rows = connection.execute("SELECT id FROM nodes").fetchall()
    except sqlite3.OperationalError:
        return set()
    return {str(row[0]) for row in rows}


def reconcile() -> CensusReport:
    """Hash the canonical store and reconcile the derived index before dispatch.

    The vault is resolved without migrating a legacy ``nodes/`` directory, so a
    routine command's own resolver still owns that one-time move. An unresolvable
    state location, an absent state file, and a concurrent writer's lock are
    silent no-ops that create nothing and change no answer. Any other failure is
    recorded in the report rather than raised, because the interaction's answer
    and exit code must not depend on upkeep. The report is stored so
    :func:`main` can report the census the interaction actually ran.
    """
    global _LAST
    root = vault.resolve(migrate_legacy=False)
    try:
        database = sidecar.database_path()
    except sidecar.SidecarError as exc:
        _LAST = CensusReport("unavailable", root, 0, 0, 0, str(exc))
        return _LAST
    # No sidecar means no derived state to reconcile; a census must never create
    # it, so a fresh read-only vault stays untouched.
    if not database.is_file():
        _LAST = CensusReport("uninitialized", root, 0, 0, 0)
        return _LAST
    if not os.path.isdir(root):
        _LAST = CensusReport("unavailable", root, 0, 0, 0, "vault directory does not exist")
        return _LAST
    try:
        connection = sidecar.open_connection()
        try:
            before = _stored_ids(connection)
            nodes, edges, absolute = index.refresh(connection, root)
            removed = len(before - _stored_ids(connection))
        finally:
            connection.close()
    except sqlite3.OperationalError as exc:
        if "locked" in str(exc) or "busy" in str(exc):
            _LAST = CensusReport("busy", root, 0, 0, 0, str(exc))
            return _LAST
        _LAST = CensusReport("failed", root, 0, 0, 0, str(exc))
        return _LAST
    except Exception as exc:  # a census can never fail the interaction it fronts
        _LAST = CensusReport("failed", root, 0, 0, 0, str(exc))
        return _LAST
    _LAST = CensusReport("reconciled", absolute, nodes, edges, removed)
    return _LAST


def _views_state(report: CensusReport) -> str:
    """Republish the generated pages and report ``current``, ``updated``, or ``failed``.

    A census that did not reach the vault (no local state, or an unreadable
    vault) publishes nothing and reports ``unavailable``. Otherwise the pages
    are rebuilt from the reconciled snapshot: an unchanged vault reproduces them
    byte for byte and reports ``current``, a pending projection is republished
    and reports ``updated``, and a publication error is reported as ``failed``
    and stays retryable on the next interaction.
    """
    if report.status != "reconciled" or not os.path.isdir(report.root):
        return "unavailable"
    try:
        result = views.publish(report.root)
    except Exception as exc:  # a projection failure must be visible, not fatal
        return f"failed: {exc}"
    if result.current:
        return f"current ({len(result.unchanged)})"
    return f"updated {result.updated}"


def _usage_error(message: str) -> int:
    print(field("error", message))
    print(
        field(
            "help",
            "Run `tangle census --help` for operands and exit meanings.",
        )
    )
    return 2


def main(argv: Sequence[str] | None = None) -> int:
    """Run ``tangle census`` and return the process exit code."""
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "census":
        args = args[1:]
    if args and args[0] in {"-h", "--help"}:
        print(_USAGE)
        return 0
    if args:
        return _usage_error(f"census takes no arguments: {args[0]}")
    report = _LAST if _LAST is not None else reconcile()
    view_state = _views_state(report)
    print(field("census", report.status))
    print(field("root", report.root))
    print(field("changes", report.changes))
    print(field("edges", report.edges))
    print(field("removed", report.removed))
    print(field("views", view_state))
    if report.detail:
        print(field("detail", report.detail))
    if report.status not in _ANSWERED:
        return 1
    return 1 if view_state.startswith("failed") else 0


if __name__ == "__main__":  # pragma: no cover - module entry point
    raise SystemExit(main())
