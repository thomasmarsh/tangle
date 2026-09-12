"""Local SQLite sidecar coordination for the Braintree graph.

Typed Python port of the coordination half of ``scripts/bt``: project
identity, external sidecar location, the ``df``-based network-filesystem
guard, schema initialization, and atomic ID allocation and lease claims.
Markdown stays authoritative; the sidecar only holds rebuildable indexes and
same-host coordination state.
"""

from __future__ import annotations

import hashlib
import os
import sqlite3
import subprocess
import time
from collections.abc import Callable, Container, Mapping
from pathlib import Path

__all__ = [
    "ClaimConflict",
    "ReleaseConflict",
    "SidecarError",
    "allocate",
    "claim",
    "content_hash",
    "database_path",
    "ensure_sidecar",
    "location_fields",
    "open_connection",
    "project_id",
    "reconcile_sequences",
    "release",
    "reservations",
    "state_root",
    "status_fields",
]

_DATABASE_NAME = "graph.sqlite3"
_BUSY_TIMEOUT_SECONDS = 1.0
_BUSY_RETRIES = 4
_COORDINATION_SCHEMA = """
PRAGMA journal_mode = WAL;
PRAGMA foreign_keys = ON;
CREATE TABLE IF NOT EXISTS id_sequences (
  prefix TEXT PRIMARY KEY,
  next_value INTEGER NOT NULL CHECK(next_value > 0)
);
CREATE TABLE IF NOT EXISTS claims (
  node_id TEXT PRIMARY KEY,
  agent_id TEXT NOT NULL,
  base_content_hash TEXT NOT NULL,
  lease_expires_at INTEGER NOT NULL
);
CREATE INDEX IF NOT EXISTS claims_lease_expiry ON claims(lease_expires_at);
"""


class SidecarError(Exception):
    """A recoverable runtime error rendered as a TOON ``error`` field."""


class ClaimConflict(Exception):
    """An existing claim belongs to a different agent or base hash."""

    def __init__(self, owner: str) -> None:
        super().__init__(owner)
        self.owner = owner


class ReleaseConflict(Exception):
    """A release did not match the agent or base hash recorded by the claim."""

    def __init__(self, owner: str, recorded_hash: str) -> None:
        super().__init__(owner)
        self.owner = owner
        self.recorded_hash = recorded_hash


def content_hash(data: bytes) -> str:
    """Return the SHA-256 hex digest of a node's raw UTF-8 file bytes.

    This is the base hash ``bt claim`` records and ``bt hash`` prints: the
    digest covers the whole file, frontmatter included, exactly as stored.
    """
    return hashlib.sha256(data).hexdigest()


def project_id() -> str:
    """Return the stable project identity for the current Git common directory."""
    override = os.environ.get("BT_PROJECT_ID")
    if override:
        return override
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--path-format=absolute", "--git-common-dir"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError) as exc:
        raise SidecarError(
            "run bt inside a Git project or set BT_PROJECT_ID for an isolated test"
        ) from exc
    common = result.stdout.strip()
    return hashlib.sha256(common.encode("utf-8")).hexdigest()[:20]


def state_root() -> Path:
    """Return the base directory that holds every project sidecar."""
    override = os.environ.get("BT_SIDECAR_DIR")
    if override:
        return Path(override)
    xdg = os.environ.get("XDG_STATE_HOME")
    if xdg:
        return Path(xdg) / "braintree"
    home = os.environ.get("HOME")
    if not home:
        raise SidecarError("HOME is required when XDG_STATE_HOME is unset")
    return Path(home) / ".local" / "state" / "braintree"


def database_path() -> Path:
    """Return the SQLite file for the current project."""
    return state_root() / "projects" / project_id() / _DATABASE_NAME


def location_fields() -> list[tuple[str, str]]:
    """Return the ``project_id`` and ``sidecar`` location fields."""
    return [("project_id", project_id()), ("sidecar", str(database_path()))]


def _network_guard(directory: Path) -> None:
    """Refuse an apparent network-mounted sidecar location."""
    if os.environ.get("BT_ALLOW_NETWORK_SIDECAR") == "1":
        return
    probe = directory
    while not probe.exists():
        parent = probe.parent
        if parent == probe:
            break
        probe = parent
    try:
        result = subprocess.run(
            ["df", "-P", str(probe)],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return
    lines = result.stdout.splitlines()
    if len(lines) < 2:
        return
    fields = lines[1].split()
    source = fields[0] if fields else ""
    if source.startswith("//") or ":" in source or source.startswith("nfs"):
        raise SidecarError(
            "sidecar filesystem appears network-mounted; "
            "SQLite WAL requires a local same-host filesystem"
        )


def _retry_busy[T](operation: Callable[[], T]) -> T:
    attempt = 0
    while True:
        try:
            return operation()
        except sqlite3.OperationalError as exc:
            message = str(exc)
            if ("locked" in message or "busy" in message) and attempt < _BUSY_RETRIES:
                attempt += 1
                time.sleep(1)
                continue
            raise


def _connect(path: Path) -> sqlite3.Connection:
    return sqlite3.connect(path, timeout=_BUSY_TIMEOUT_SECONDS, isolation_level=None)


def _ensure_directory(directory: Path) -> None:
    try:
        directory.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise SidecarError(f"unable to create sidecar directory: {directory}") from exc


def ensure_sidecar() -> Path:
    """Create or repair the coordination sidecar and return its path."""
    path = database_path()
    _network_guard(path.parent)
    _ensure_directory(path.parent)
    try:
        def initialize() -> None:
            conn = _connect(path)
            try:
                conn.executescript(_COORDINATION_SCHEMA)
            finally:
                conn.close()

        _retry_busy(initialize)
    except (sqlite3.Error, SidecarError) as exc:
        raise SidecarError("unable to initialize the SQLite sidecar") from exc
    return path


def open_connection() -> sqlite3.Connection:
    """Open the initialized sidecar for a coordination or index command."""
    ensure_sidecar()
    return _connect(database_path())


def _run_transaction[T](conn: sqlite3.Connection, body: Callable[[sqlite3.Connection], T]) -> T:
    def operation() -> T:
        conn.execute("BEGIN IMMEDIATE")
        try:
            result = body(conn)
        except BaseException:
            conn.execute("ROLLBACK")
            raise
        conn.execute("COMMIT")
        return result

    return _retry_busy(operation)


def allocate(prefix: str, taken: Container[int] | None = None) -> int:
    """Atomically allocate the next unused integer for ``prefix``.

    ``next_value`` is the integer the next allocation returns. ``taken`` holds
    the numeric suffixes already present on disk; a candidate that appears there
    is skipped so allocation never returns an identity that duplicates an
    existing node filename, even when the counter is behind Markdown.
    """
    blocked: Container[int] = () if taken is None else taken
    try:
        conn = open_connection()
        try:
            def body(connection: sqlite3.Connection) -> int:
                connection.execute(
                    "INSERT INTO id_sequences(prefix,next_value) VALUES(?, 1) "
                    "ON CONFLICT(prefix) DO NOTHING",
                    (prefix,),
                )
                while True:
                    row = connection.execute(
                        "SELECT next_value FROM id_sequences WHERE prefix = ?",
                        (prefix,),
                    ).fetchone()
                    candidate = int(row[0])
                    connection.execute(
                        "UPDATE id_sequences SET next_value = next_value + 1 "
                        "WHERE prefix = ?",
                        (prefix,),
                    )
                    if candidate not in blocked:
                        return candidate

            return _run_transaction(conn, body)
        finally:
            conn.close()
    except sqlite3.Error as exc:
        raise SidecarError("unable to allocate an ID atomically") from exc


def reconcile_sequences(maxima: Mapping[str, int]) -> None:
    """Raise each prefix's next allocation above its Markdown maximum."""
    if not maxima:
        return
    try:
        conn = open_connection()
        try:
            def body(connection: sqlite3.Connection) -> None:
                for prefix, maximum in maxima.items():
                    connection.execute(
                        "INSERT INTO id_sequences(prefix,next_value) VALUES(?, ?) "
                        "ON CONFLICT(prefix) DO UPDATE SET next_value = "
                        "MAX(id_sequences.next_value, excluded.next_value)",
                        (prefix, maximum + 1),
                    )

            _run_transaction(conn, body)
        finally:
            conn.close()
    except sqlite3.Error as exc:
        raise SidecarError("unable to reconcile the id reservations") from exc


def reservations() -> list[tuple[str, str]]:
    """Return reserved prefixes and their next allocation when initialized."""
    path = database_path()
    if not path.is_file():
        return []
    try:
        conn = _connect(path)
        try:
            cursor = conn.execute(
                "SELECT prefix, next_value FROM id_sequences ORDER BY prefix"
            )
            return [(str(row[0]), str(row[1])) for row in cursor.fetchall()]
        finally:
            conn.close()
    except sqlite3.Error:
        return []


def claim(
    node: str, agent: str, base_hash: str, lease_seconds: int
) -> tuple[str, str, int, int]:
    """Acquire or renew an exclusive lease, returning owner/hash/expiry/remaining."""
    now = int(time.time())
    expires = now + lease_seconds
    try:
        conn = open_connection()
        try:
            def body(connection: sqlite3.Connection) -> tuple[str, str, int]:
                connection.execute("DELETE FROM claims WHERE lease_expires_at <= ?", (now,))
                connection.execute(
                    "INSERT INTO claims(node_id,agent_id,base_content_hash,lease_expires_at) "
                    "VALUES(?,?,?,?) ON CONFLICT(node_id) DO UPDATE SET "
                    "lease_expires_at=excluded.lease_expires_at "
                    "WHERE claims.agent_id=excluded.agent_id "
                    "AND claims.base_content_hash=excluded.base_content_hash",
                    (node, agent, base_hash, expires),
                )
                row = connection.execute(
                    "SELECT agent_id, base_content_hash, lease_expires_at "
                    "FROM claims WHERE node_id = ?",
                    (node,),
                ).fetchone()
                return (str(row[0]), str(row[1]), int(row[2]))

            owner, recorded_hash, recorded_expiry = _run_transaction(conn, body)
        finally:
            conn.close()
    except sqlite3.Error as exc:
        raise SidecarError("unable to acquire the claim atomically") from exc
    if owner != agent or recorded_hash != base_hash:
        raise ClaimConflict(owner)
    return owner, recorded_hash, recorded_expiry, recorded_expiry - now


def release(node: str, agent: str, base_hash: str) -> tuple[str, int]:
    """Release the matching lease, returning the result and remaining seconds.

    Returns ``("released", remaining)`` when the matching unexpired lease was
    removed, ``("expired", 0)`` when this agent's matching lease had already
    lapsed, and ``("no-op", 0)`` when the node records no matching claim at
    all, so a lapsed claim is distinguishable from one never held. Raises
    :class:`ReleaseConflict` when a live lease exists for another agent or
    records a different base hash, so a stale post-edit hash can never be
    mistaken for a successful release.
    """
    now = int(time.time())
    try:
        conn = open_connection()
        try:
            def body(connection: sqlite3.Connection) -> tuple[str, str, str, int]:
                lapsed = connection.execute(
                    "SELECT agent_id, base_content_hash FROM claims "
                    "WHERE node_id = ? AND lease_expires_at <= ?",
                    (node, now),
                ).fetchone()
                connection.execute("DELETE FROM claims WHERE lease_expires_at <= ?", (now,))
                row = connection.execute(
                    "SELECT agent_id, base_content_hash, lease_expires_at "
                    "FROM claims WHERE node_id = ?",
                    (node,),
                ).fetchone()
                if row is None:
                    if (
                        lapsed is not None
                        and str(lapsed[0]) == agent
                        and str(lapsed[1]) == base_hash
                    ):
                        return ("expired", agent, base_hash, 0)
                    return ("no-op", "", "", 0)
                owner, recorded_hash = str(row[0]), str(row[1])
                if owner == agent and recorded_hash == base_hash:
                    connection.execute("DELETE FROM claims WHERE node_id = ?", (node,))
                    return ("released", owner, recorded_hash, int(row[2]) - now)
                return ("conflict", owner, recorded_hash, 0)

            result, owner, recorded_hash, remaining = _run_transaction(conn, body)
        finally:
            conn.close()
    except sqlite3.Error as exc:
        raise SidecarError("unable to release the claim atomically") from exc
    if result == "conflict":
        raise ReleaseConflict(owner, recorded_hash)
    return result, remaining


def status_fields() -> list[tuple[str, str]]:
    """Return the location plus initialization and active-claim fields."""
    fields = location_fields()
    path = database_path()
    if path.is_file():
        count = "?"
        try:
            conn = _connect(path)
            try:
                row = conn.execute("SELECT count(*) FROM claims;").fetchone()
                count = str(row[0])
            finally:
                conn.close()
        except sqlite3.Error:
            count = "?"
        fields.append(("initialized", "true"))
        fields.append(("active_claims", count))
    else:
        fields.append(("initialized", "false"))
        fields.append(("active_claims", "0"))
    return fields
