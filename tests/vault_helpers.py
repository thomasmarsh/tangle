"""Storage-agnostic fixtures for canonical Tangle test vaults.

The stationary store shards a node under the last two characters of its
identity (``.tangle/canonical/<suffix>/<id>-<slug>.md``) and mints new
identities from cryptographic entropy. Behavioral tests must not restate
either rule: they seed and look nodes up through :func:`canonical_path` and
:func:`write_node`, and they make generated identities predictable with
:func:`fixed_identity` or :func:`deterministic_id`. A storage-layout or
identity change then edits this module instead of scattered assertions.
"""

from __future__ import annotations

import itertools
from pathlib import Path

import pytest

from tangle import identity, store

__all__ = [
    "canonical_path",
    "deterministic_id",
    "find_node",
    "find_nodes",
    "find_typed",
    "fixed_identity",
    "iter_nodes",
    "write_node",
]


def canonical_path(nodes_dir: str | Path, node_id: str, slug: str) -> Path:
    """Return the stationary canonical path for ``node_id``.

    This is the one test-side spelling of the shard rule; it derives the path
    itself rather than calling production, so it stays an independent oracle.
    """
    canonical = identity.normalize_node_id(node_id)
    return (
        Path(nodes_dir)
        / store.CANONICAL_DIRECTORY
        / canonical[-2:]
        / f"{canonical}-{slug}.md"
    )


def write_node(nodes_dir: str | Path, node_id: str, slug: str, text: str) -> Path:
    """Seed one node with a deterministic identity at its canonical path."""
    path = canonical_path(nodes_dir, node_id, slug)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")
    return path


def iter_nodes(nodes_dir: str | Path) -> list[Path]:
    """Return every canonical node file regardless of its shard."""
    root = Path(nodes_dir) / store.CANONICAL_DIRECTORY
    if not root.is_dir():
        return []
    return sorted(path for path in root.glob("*/*.md") if path.is_file())


def find_node(nodes_dir: str | Path, node_id: str) -> Path:
    """Return the one canonical file whose identity is ``node_id``."""
    canonical = identity.normalize_node_id(node_id)
    matches = [path for path in iter_nodes(nodes_dir) if path.name.startswith(f"{canonical}-")]
    if len(matches) != 1:
        raise AssertionError(f"expected exactly one canonical {canonical}, found {matches}")
    return matches[0]


def find_nodes(nodes_dir: str | Path, node_type: str, slug: str) -> list[Path]:
    """Return the canonical files of one type and slug, whatever their ids."""
    return [
        path
        for path in find_typed(nodes_dir, node_type)
        if path.stem.endswith(f"-{slug}")
    ]


def find_typed(nodes_dir: str | Path, node_type: str) -> list[Path]:
    """Return the canonical files of one node type, whatever their shard."""
    prefix = node_type.strip().lower()
    return [path for path in iter_nodes(nodes_dir) if path.name.startswith(f"{prefix}-")]


def deterministic_id(node_type: str, sequence: int = 0) -> str:
    """Return a valid canonical identity that is distinct per ``sequence``."""
    candidate = f"{node_type.strip().lower()}-{sequence:026d}"
    if identity.CANONICAL_ID.fullmatch(candidate) is None:
        raise ValueError(f"sequence {sequence} has no canonical identity: {candidate}")
    return candidate


def fixed_identity(monkeypatch: pytest.MonkeyPatch) -> None:
    """Make in-process identity generation deterministic and unique per call.

    Writers that allocate an id themselves (capture, decomposition) call
    :func:`tangle.identity.generate_node_id`, so patching it there covers every
    path. The first call yields ``deterministic_id(type, 0)``, the next
    ``deterministic_id(type, 1)``, and so on. Cross-process writers (the shell
    installer test) instead pass an explicit ``--id``.
    """
    counter = itertools.count()

    def generate(node_type: str) -> str:
        return deterministic_id(node_type, next(counter))

    monkeypatch.setattr(identity, "generate_node_id", generate)
