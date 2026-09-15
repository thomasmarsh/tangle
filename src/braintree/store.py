"""Discover legacy and stationary canonical Markdown nodes.

The compatibility window deliberately permits a vault to contain both historic
status-directory nodes and stationary ``canonical/`` nodes. Status comes from
the directory only for the former; stationary nodes carry it in frontmatter.
"""

from __future__ import annotations

import glob
import os
import re
from collections.abc import Iterator
from dataclasses import dataclass

__all__ = [
    "CANONICAL_DIRECTORY",
    "NON_NODE_DIRECTORIES",
    "NodePath",
    "find_by_name",
    "iter_node_paths",
]

CANONICAL_DIRECTORY = "canonical"
# Directories under the vault that hold non-authoritative local state rather
# than canonical nodes. Node discovery and graph validation skip them, so a
# generated view or a future proposal, acceptance, or receipt file is never
# mistaken for a node in an invalid status directory.
NON_NODE_DIRECTORIES = frozenset({"views", "proposals", "acceptances", "receipts"})
_STATUSES = frozenset({"proposed", "active", "blocked", "resolved"})
_STATUS = re.compile(r"^status:\s*(?:['\"])?([a-z]+)(?:['\"])?\s*$", re.MULTILINE)


@dataclass(frozen=True)
class NodePath:
    """A discovered canonical node and its authoritative status, if readable."""

    path: str
    status: str | None
    stationary: bool


def _stationary_status(path: str) -> str | None:
    try:
        with open(path, encoding="utf-8") as handle:
            text = handle.read()
    except OSError:
        return None
    if not text.startswith("---\n"):
        return None
    match = _STATUS.search(text.split("---", 2)[1])
    return match.group(1) if match is not None else None


def iter_node_paths(root: str) -> Iterator[NodePath]:
    """Yield authority-bearing Markdown while excluding views and local state."""
    root = os.path.abspath(root)
    if not os.path.isdir(root):
        return
    for name in sorted(os.listdir(root)):
        if name == CANONICAL_DIRECTORY or name in NON_NODE_DIRECTORIES:
            continue
        directory = os.path.join(root, name)
        if not os.path.isdir(directory):
            continue
        for filename in sorted(os.listdir(directory)):
            path = os.path.join(directory, filename)
            if filename.endswith(".md") and os.path.isfile(path):
                yield NodePath(path, name, False)
    canonical = os.path.join(root, CANONICAL_DIRECTORY)
    if not os.path.isdir(canonical):
        return
    for directory, _subdirectories, names in os.walk(canonical):
        for name in sorted(names):
            path = os.path.join(directory, name)
            if name.endswith(".md") and os.path.isfile(path):
                yield NodePath(path, _stationary_status(path), True)


def find_by_name(root: str, basename: str) -> tuple[str, str] | None:
    """Return ``(status, path)`` for one basename across both layouts.

    A caller that cites ``.braintree/<status>/<basename>`` looks a node up by
    its stable basename, so a node discovered in the stationary layout still
    answers with the status it carries. The status is the legacy directory or
    the stationary frontmatter field; ``None`` when a stationary node has no
    readable status.
    """
    if os.path.basename(basename) != basename:
        return None
    for status in sorted(_STATUSES):
        legacy = os.path.join(root, status, basename)
        if os.path.isfile(legacy):
            return status, legacy
    for candidate in sorted(
        glob.glob(os.path.join(root, CANONICAL_DIRECTORY, "*", basename))
    ):
        stationary = _stationary_status(candidate)
        if stationary in _STATUSES:
            return stationary, candidate
    return None
