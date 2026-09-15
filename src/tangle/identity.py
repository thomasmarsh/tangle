"""Canonical project and node identities for the stationary-store format.

The legacy ``TAS-001`` names remain readable during the compatibility window,
but anything newly written by the stationary store uses an immutable lowercase
128-bit identifier.  This module deliberately has no sidecar dependency:
project authority is a committed vault fact, whereas the sidecar's Git-common-
directory hash remains local coordination state.
"""

from __future__ import annotations

import os
import re
import secrets
from collections.abc import Mapping
from dataclasses import dataclass
from pathlib import Path

__all__ = [
    "CANONICAL_ID",
    "PROJECT_UID",
    "PROJECT_UID_FILE",
    "IdentityError",
    "Reference",
    "abbreviate",
    "ensure_project_uid",
    "generate_node_id",
    "generate_project_uid",
    "is_node_id",
    "is_project_alias",
    "is_project_uid",
    "normalize_node_id",
    "parse_reference",
    "read_project_uid",
]

_ALPHABET = "0123456789abcdefghjkmnpqrstvwxyz"
_PAYLOAD = r"[0-7][0-9a-hjkmnp-tv-z]{25}"
_TYPES = "tas|tho|def|dec|idx|fbk"
CANONICAL_ID = re.compile(rf"(?:{_TYPES})-{_PAYLOAD}\Z")
PROJECT_UID = re.compile(rf"prj-{_PAYLOAD}\Z")
_LEGACY_ID = re.compile(r"[A-Z][A-Z0-9_]*-\d+\Z")
_ALIAS = re.compile(r"[a-z][a-z0-9-]{0,62}\Z")
PROJECT_UID_FILE = "project-id"


class IdentityError(ValueError):
    """An identity, alias, or durable reference is malformed."""


@dataclass(frozen=True)
class Reference:
    """A resolved project-scoped node reference.

    ``qualified`` records whether the caller supplied an alias; callers that
    persist a cross-project edge use ``project_uid`` and never the alias.
    """

    project_uid: str
    node_id: str
    qualified: bool


def _encode_128(value: bytes) -> str:
    """Encode exactly sixteen random bytes in fixed-width Crockford Base32."""
    if len(value) != 16:
        raise ValueError("a 128-bit identity needs exactly 16 bytes")
    number = int.from_bytes(value, "big")
    characters: list[str] = []
    for _ in range(26):
        characters.append(_ALPHABET[number & 31])
        number >>= 5
    return "".join(reversed(characters))


def generate_project_uid() -> str:
    """Return a new immutable, committed project authority identifier."""
    return "prj-" + _encode_128(secrets.token_bytes(16))


def generate_node_id(node_type: str) -> str:
    """Return a new canonical node identity for one supported type."""
    prefix = node_type.strip().lower()
    if prefix not in _TYPES.split("|"):
        raise IdentityError("node type must be tas, tho, def, dec, idx, or fbk")
    return prefix + "-" + _encode_128(secrets.token_bytes(16))


def is_project_uid(value: str) -> bool:
    """Return whether ``value`` is already a canonical project UID."""
    return PROJECT_UID.fullmatch(value) is not None


def is_project_alias(value: str) -> bool:
    """Return whether ``value`` is a valid lowercase project alias."""
    return _ALIAS.fullmatch(value) is not None


def is_node_id(value: str) -> bool:
    """Return whether ``value`` is a canonical or readable legacy node ID."""
    return CANONICAL_ID.fullmatch(value) is not None or _LEGACY_ID.fullmatch(value) is not None


def normalize_node_id(value: str) -> str:
    """Normalize a user-supplied node ID without accepting abbreviations."""
    candidate = value.strip()
    lowered = candidate.lower()
    if CANONICAL_ID.fullmatch(lowered) is not None:
        return lowered
    if _LEGACY_ID.fullmatch(candidate) is not None:
        return candidate
    raise IdentityError(f"invalid node identity: {value!r}")


def read_project_uid(nodes_dir: str | Path) -> str | None:
    """Return the committed project UID, rejecting a malformed authority file."""
    path = Path(nodes_dir) / PROJECT_UID_FILE
    try:
        value = path.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return None
    except OSError as exc:
        raise IdentityError(f"unable to read project UID: {path}") from exc
    if not is_project_uid(value):
        raise IdentityError(f"invalid project UID in {path}")
    return value


def ensure_project_uid(nodes_dir: str | Path) -> str:
    """Read or atomically create the vault's clone-stable project UID."""
    directory = Path(nodes_dir)
    try:
        existing = read_project_uid(directory)
    except IdentityError:
        # A concurrent exclusive creator may have published the directory entry
        # before it has finished writing its fixed-size value.  The FileExists
        # path below retries that transient state and still rejects a malformed
        # value that remains after publication.
        existing = None
    if existing is not None:
        return existing
    path = directory / PROJECT_UID_FILE
    value = generate_project_uid()
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError:
        # An exclusive create makes the authority unambiguous, but another
        # thread may observe the just-created file before its writer closes it.
        # Retry that short publication window instead of treating an empty or
        # partial file as a malformed committed UID.
        for _ in range(100):
            try:
                raced = read_project_uid(directory)
            except IdentityError:
                continue
            if raced is not None:
                return raced
        raise IdentityError(f"project UID was not published while reading {path}") from None
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
            handle.write(value + "\n")
    except OSError:
        try:
            path.unlink()
        except OSError:
            pass
        raise
    return value


def parse_reference(
    value: str, current_project_uid: str, aliases: Mapping[str, str] | None = None
) -> Reference:
    """Resolve ``node`` or ``alias:node`` input to immutable authority.

    Qualified shorthand is explicitly an input/display convenience.  The
    returned UID is what a durable cross-project relation stores.
    """
    if not is_project_uid(current_project_uid):
        raise IdentityError("current project UID is malformed")
    text = value.strip()
    if ":" not in text:
        return Reference(current_project_uid, normalize_node_id(text), False)
    alias, node = text.split(":", 1)
    if _ALIAS.fullmatch(alias) is None:
        raise IdentityError(f"invalid project alias: {alias!r}")
    if aliases is None or alias not in aliases:
        raise IdentityError(f"unknown project alias: {alias}")
    project_uid = aliases[alias]
    if not is_project_uid(project_uid):
        raise IdentityError(f"invalid project UID registered for alias: {alias}")
    return Reference(project_uid, normalize_node_id(node), True)


def abbreviate(node_ids: list[str], *, minimum: int = 8) -> dict[str, str]:
    """Return deterministic collision-aware terminal abbreviations.

    Canonical ids never become accepted input; this helper is presentation-only.
    """
    if minimum < 8:
        raise ValueError("abbreviations require at least eight payload characters")
    canonical = [normalize_node_id(value) for value in node_ids]
    result: dict[str, str] = {}
    for node_id in canonical:
        if _LEGACY_ID.fullmatch(node_id) is not None:
            result[node_id] = node_id
            continue
        prefix, payload = node_id.split("-", 1)
        width = minimum
        while any(
            other != node_id
            and other.split("-", 1)[0] == prefix
            and other.split("-", 1)[1].startswith(payload[:width])
            for other in canonical
            if CANONICAL_ID.fullmatch(other) is not None
        ):
            width += 1
        result[node_id] = f"{prefix}-{payload[:width]}..."
    return result
