"""Resolve the Braintree vault directory and migrate the legacy layout.

The vault is the ``.braintree/`` directory that holds ``index-map.md`` and the
fixed status directories. Older vaults kept that same tree under ``nodes/``.
This module is the one place that decides which directory a command reads and
that performs the one-time, idempotent ``nodes/`` to ``.braintree/`` rename.

An explicit operand or ``BT_NODES_DIR`` always wins and is never migrated: the
caller named that directory, so the command only reads it. Only the default
resolution from the current directory may migrate a legacy vault, which keeps
the upgrade to a consuming project's own worktree and leaves every other vault
untouched.

A migration no command asked for is never silent: the resolver announces it in
one line on stderr, because the answer a command prints on stdout may be
machine-readable TOON that a notice would corrupt.
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass

__all__ = [
    "DIRECTORY_NAME",
    "INDEX_NAME",
    "LEGACY_DIRECTORY_NAME",
    "RESERVATION_NAME",
    "Migration",
    "default_directory",
    "legacy_directory",
    "migrate",
    "migration_notice",
    "resolve",
]

# The vault directory and the legacy name it replaced.
DIRECTORY_NAME = ".braintree"
LEGACY_DIRECTORY_NAME = "nodes"
INDEX_NAME = "index-map.md"
# The portable id-reservation markers live beside the status directories. The
# name is shared with ``node_record`` so the migrated nested reservations and a
# fresh reservation use the same location.
RESERVATION_NAME = "reservations"


@dataclass(frozen=True)
class Migration:
    """The one-time layout move a command performed."""

    source: str
    destination: str


def default_directory() -> str:
    """Return the configured vault directory or the default ``.braintree``."""
    return os.environ.get("BT_NODES_DIR", DIRECTORY_NAME)


def legacy_directory(root: str) -> str | None:
    """Return the legacy ``root/nodes`` vault when it should be migrated.

    It qualifies only when ``nodes/index-map.md`` exists and the destination
    ``root/.braintree`` does not. An already-migrated vault is never a
    candidate, and a ``nodes/`` that is not a vault is left alone.
    """
    source = os.path.join(root, LEGACY_DIRECTORY_NAME)
    destination = os.path.join(root, DIRECTORY_NAME)
    if os.path.isfile(os.path.join(source, INDEX_NAME)) and not os.path.exists(
        destination
    ):
        return source
    return None


def _merge_reservations(destination: str) -> None:
    """Absorb a legacy ``nodes/.braintree/reservations`` into the new layout.

    The old layout nested the portable reservation markers under the vault; the
    rename leaves them at ``.braintree/.braintree/reservations``. Move them
    beside the status directories and remove the nested directory so later
    reservations do not straddle two locations. A directory that is not the
    expected marker tree is left where it is rather than destroyed.
    """
    nested = os.path.join(destination, DIRECTORY_NAME)
    legacy = os.path.join(nested, RESERVATION_NAME)
    if not os.path.isdir(legacy):
        return
    reservations = os.path.join(destination, RESERVATION_NAME)
    try:
        os.makedirs(reservations, exist_ok=True)
        for name in os.listdir(legacy):
            target = os.path.join(reservations, name)
            if not os.path.exists(target):
                os.rename(os.path.join(legacy, name), target)
        os.rmdir(legacy)
        os.rmdir(nested)
    except OSError:
        # A pre-existing marker of the same name or an unexpected extra entry
        # just leaves the nested directory in place; it is coordination state,
        # not vault Markdown, so a partial merge is recoverable and harmless.
        return


def migrate(root: str) -> Migration | None:
    """Rename a qualifying ``root/nodes`` vault to ``root/.braintree``.

    Returns the move when it happened and ``None`` when the root has no legacy
    vault or is already migrated. The rename is the only write; it never edits
    the Markdown, the sidecar, or the Git index, so the pre-migration stamp and
    history remain recoverable from the consumer's Git.
    """
    source = legacy_directory(root)
    if source is None:
        return None
    destination = os.path.join(root, DIRECTORY_NAME)
    os.rename(source, destination)
    _merge_reservations(destination)
    return Migration(source=source, destination=destination)


def migration_notice(migration: Migration) -> str:
    """Return the one-line announcement of a migration a command performed.

    The notice names the move relative to the vault root the resolver read, so
    a command run from a project root reports ``nodes -> .braintree``, the two
    directory names the operator sees in the worktree.
    """
    return (
        f"migrated vault: {os.path.basename(migration.source)}"
        f" -> {os.path.basename(migration.destination)}"
    )


def resolve(override: str | None = None, *, migrate_legacy: bool = True) -> str:
    """Return the vault directory a command should read.

    An explicit operand or ``BT_NODES_DIR`` wins unchanged and is never
    migrated. Otherwise the default ``.braintree`` path is returned, after
    migrating a qualifying legacy ``nodes/`` vault in the current directory when
    ``migrate_legacy`` is set. A performed migration is announced with
    :func:`migration_notice` on stderr; stdout carries only the returned path
    and whatever the invoking command writes.
    """
    if override is not None:
        return override
    configured = os.environ.get("BT_NODES_DIR")
    if configured:
        return configured
    root = os.getcwd()
    if migrate_legacy:
        migration = migrate(root)
        if migration is not None:
            print(migration_notice(migration), file=sys.stderr)
    return os.path.join(root, DIRECTORY_NAME)
