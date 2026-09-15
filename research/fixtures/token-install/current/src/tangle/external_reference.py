"""Durable cross-project external references and their unresolved state.

A canonical node may cite a node in another Tangle project with a durable
external reference URI, ``tangle://<prj-uid>/node/<node-id>``. The URI carries
the immutable project UID and never an alias or an Obsidian wikilink, so it
survives an alias rename or collision and can never resolve to a local node by
accident. Tangle never materializes the target as canonical Markdown: when the
referenced project is registered and its local vault carries the matching
project UID the reference is ``resolved``; when the project is not registered,
or its registered location is missing or identifies a different project, the
reference is ``unregistered`` or ``unavailable`` and stays visible as
unresolved.

``tangle external`` is the read-only surface that lists every external
reference found in the canonical store with its state, and the generated
``views/projects.md`` page renders the same list. The verb lives on its own
path because ``src/tangle/cli.py`` and ``src/tangle/sidecar.py`` are frozen
observable prompt content in ``benchmark/memory-authority-cases.json``.
"""

from __future__ import annotations

import os
import sys
from collections.abc import Iterable, Sequence
from dataclasses import dataclass
from typing import TYPE_CHECKING

from . import identity, index, vault, views
from .graph_check import _mask_code
from .toon import field

if TYPE_CHECKING:
    from .index import IndexedNode

__all__ = ["ExternalReference", "ExternalReport", "main", "scan"]

# The states a durable external reference can report. Every state other than
# ``resolved`` leaves the reference visible and unresolved.
_LOCAL = "local"
_RESOLVED = "resolved"
_UNREGISTERED = "unregistered"
_UNAVAILABLE = "unavailable"

_USAGE = (
    "usage: tangle external [--unresolved]\n"
    "List every durable cross-project reference found in canonical nodes with\n"
    "its resolution state; --unresolved lists only unresolved references.\n"
    "Exits 0 when the answer was produced, 1 when the vault is unreadable, and\n"
    "2 when the command line is malformed."
)

_HELP = "Run `tangle external --help` for operands and exit meanings."


@dataclass(frozen=True)
class ExternalReference:
    """One durable external reference and its resolved or unresolved state.

    ``source`` is the citing canonical node id, ``project`` the immutable
    project UID the URI names, ``node`` the target node id, and ``alias`` the
    registered alias when the project has one. ``state`` is ``resolved``,
    ``unregistered``, ``unavailable``, or ``local``; ``detail`` names the
    reason a reference is not resolved.
    """

    source: str
    source_name: str
    source_summary: str
    project: str
    node: str
    alias: str
    state: str
    detail: str = ""


@dataclass(frozen=True)
class ExternalReport:
    """Every durable external reference the canonical store cites."""

    root: str
    references: tuple[ExternalReference, ...]

    @property
    def unresolved(self) -> tuple[ExternalReference, ...]:
        """Return the references whose target is not a resolvable local vault."""
        return tuple(
            reference
            for reference in self.references
            if reference.state != _RESOLVED
        )


def _current_project_uid(root: str) -> str | None:
    """Return this vault's committed project UID, or none when it is absent."""
    try:
        return identity.read_project_uid(root)
    except identity.IdentityError:
        return None


def _registry_by_uid(root: str) -> dict[str, tuple[str, str]]:
    """Return the local registry keyed by immutable project UID.

    The alias ordering from the registry decides a duplicate UID's alias, so the
    answer is deterministic for a given registry file.
    """
    by_uid: dict[str, tuple[str, str]] = {}
    for alias, uid, location in views.registered_projects(root):
        if identity.is_project_uid(uid):
            by_uid.setdefault(uid, (alias, location))
    return by_uid


def _resolve(
    root: str,
    current: str | None,
    project: str,
    by_uid: dict[str, tuple[str, str]],
) -> tuple[str, str, str]:
    """Return ``(state, detail, alias)`` for one external target project.

    ``resolved`` requires a registered project whose local directory carries the
    matching committed UID, so a stale or mislabeled path can never masquerade
    as the referenced project.
    """
    if current is not None and project == current:
        return _LOCAL, "target is this project; use a local wikilink instead", ""
    entry = by_uid.get(project)
    if entry is None:
        return _UNREGISTERED, "project UID is not registered", ""
    alias, location = entry
    if not location:
        return _UNAVAILABLE, "registered project has no local path", alias
    candidate = location if os.path.isabs(location) else os.path.join(root, location)
    if not os.path.isdir(candidate):
        return _UNAVAILABLE, f"local path is not a directory: {location}", alias
    try:
        found = identity.read_project_uid(candidate)
    except identity.IdentityError:
        return _UNAVAILABLE, f"local path has a malformed {identity.PROJECT_UID_FILE}", alias
    if found is None:
        return _UNAVAILABLE, f"local path has no {identity.PROJECT_UID_FILE}", alias
    if found != project:
        return _UNAVAILABLE, f"local path identifies {found}", alias
    return _RESOLVED, "", alias


def scan(
    root: str, nodes: Iterable[IndexedNode] | None = None
) -> ExternalReport:
    """Return every durable external reference the canonical store cites.

    Quoted code is masked before the scan, so a URI documented inside an inline
    code span or fenced block is not treated as an authored reference. The
    result is ordered by citing node and target, so an unchanged vault produces
    the same answer.
    """
    if nodes is None:
        from .index import _read_nodes  # local import avoids an import cycle

        nodes = _read_nodes(root)
    current = _current_project_uid(root)
    by_uid = _registry_by_uid(root)
    found: list[ExternalReference] = []
    for node in nodes:
        for match in identity.EXTERNAL_REFERENCE.finditer(_mask_code(node.body)):
            project = match.group("project")
            target = match.group("node")
            state, detail, alias = _resolve(root, current, project, by_uid)
            found.append(
                ExternalReference(
                    source=node.id,
                    source_name=node.name,
                    source_summary=node.metadata.get("summary", ""),
                    project=project,
                    node=target,
                    alias=alias,
                    state=state,
                    detail=detail,
                )
            )
    found.sort(key=lambda reference: (reference.source, reference.project, reference.node))
    return ExternalReport(root=root, references=tuple(found))


def _usage_error(message: str) -> int:
    print(field("error", message))
    print(field("help", _HELP))
    return 2


def main(argv: Sequence[str] | None = None) -> int:
    """Run ``tangle external [--unresolved]`` and return the process exit code."""
    args = list(sys.argv[1:] if argv is None else argv)
    if args and args[0] == "external":
        args = args[1:]
    if args and args[0] in {"-h", "--help"}:
        print(_USAGE)
        return 0
    unresolved_only = False
    for token in args:
        if token == "--unresolved":
            unresolved_only = True
        else:
            return _usage_error(f"external takes no operand: {token}")
    root = vault.resolve(migrate_legacy=False)
    if not os.path.isdir(root):
        print(field("error", f"vault directory does not exist: {root}"))
        print(field("help", _HELP))
        return 1
    report = scan(root)
    selected = report.unresolved if unresolved_only else report.references
    print(field("root", report.root))
    print(field("unresolved", len(report.unresolved)))
    print(
        index.format_table(
            "references",
            "source,project,node,alias,state,detail",
            "references: 0 references",
            [
                (
                    reference.source,
                    reference.project,
                    reference.node,
                    reference.alias,
                    reference.state,
                    reference.detail,
                )
                for reference in selected
            ],
        )
    )
    return 0


if __name__ == "__main__":  # pragma: no cover - module entry point
    raise SystemExit(main())
