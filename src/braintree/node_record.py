"""Create a routed, stamped Braintree node of a named type in one step.

This is the generic capture path behind ``braintree node record``. It supplies
the id, route, timestamp, and required frontmatter a caller would otherwise
hand-author: it generates a lowercase 128-bit id from cryptographic entropy and
discovers the primary route to the vault's root hub the way
``braintree feedback record`` does for ``FBK``. The Markdown-node writer
primitives it holds are the single spelling of identity generation, route
discovery, summary fitting, and non-clobbering writes shared with that command.
It depends only on the standard library; legacy numeric allocation helpers
remain for the compatibility window. It never touches the network.
"""

from __future__ import annotations

import glob
import os
import re
import subprocess
import sys
from collections.abc import Sequence
from datetime import UTC, datetime

from . import identity, sidecar, store, vault
from .toon import field

__all__ = [
    "SUMMARY_LIMIT",
    "AllocationError",
    "discover_route",
    "existing_ids",
    "fit_summary",
    "id_number",
    "canonical_path",
    "main",
    "next_number",
    "normalize_route",
    "render",
    "reservation_dir",
    "reserve_number",
    "reserved_numbers",
    "single_line",
    "slugify",
    "summary_warning",
    "taken_numbers",
    "utc_now",
    "write_new",
]

_USAGE = (
    "usage: braintree node record --type TYPE --summary TEXT --body TEXT "
    "[--status proposed|active|blocked|resolved] [--next TEXT] [--nodes DIR] "
    "[--route ROUTE] [--id ID] [--slug SLUG]\n"
    "Write one routed, stamped node of the named type, generating a lowercase "
    "128-bit id and writing the stationary canonical file."
)


class AllocationError(Exception):
    """A capture path could not reserve a free id."""


# The capture types the vault documents, split by the ``next`` rule the checker
# enforces: a knowledge type records a question, invariant, or decision, while
# a task type is executable work and needs one. FBK is recorded by
# ``braintree feedback record`` and a root IDX hub is declared in
# ``index-map.md``, so neither is a capture target.
_KNOWLEDGE_TYPES = ("THO", "DEF", "DEC")
_TASK_TYPES = ("TAS",)
_CAPTURE_TYPES = _KNOWLEDGE_TYPES + _TASK_TYPES
_STATUSES = ("proposed", "active", "blocked", "resolved")
_DEFAULT_STATUS = "proposed"
_BLOCKED_HEADING = re.compile(r"^# Blocked\s*$", re.MULTILINE)

_ROUTE = re.compile(r"^(?:Parent|Area) \[\[([^\]]+)\]\]\Z")
_ROOT_ROUTE = re.compile(r"^\s*- Indexes \[\[([^\]]+)\]\]", re.MULTILINE)
_WIKILINK_ONLY = re.compile(r"\[\[([^\]]+)\]\]\Z")
_NON_SLUG = re.compile(r"[^a-z0-9]+")
_WHITESPACE = re.compile(r"\s+")
_SLUG_LIMIT = 48

# The one capture summary limit both write paths share. A stored summary is one
# line of at most this many characters, and an over-long value is cut on a word
# boundary and marked with the ellipsis below so it never ends mid-phrase.
SUMMARY_LIMIT = 96
_ELLIPSIS = "..."

# The portable fallback keeps one ``PREFIX-NNN`` marker per reserved number in
# ``<vault>/reservations``. The markers are not ``.md``, so the checker's
# ``*/*.md`` status-directory scan ignores them.
_ALLOCATION_ATTEMPTS = 1000
_VALUE_OPTIONS = frozenset(
    {
        "--nodes",
        "--route",
        "--id",
        "--summary",
        "--slug",
        "--type",
        "--status",
        "--next",
        "--body",
    }
)


def single_line(value: str) -> str:
    """Collapse ``value`` to one whitespace-normalized line."""
    return _WHITESPACE.sub(" ", value).strip()


def fit_summary(value: str) -> tuple[str, bool]:
    """Return one summary within ``SUMMARY_LIMIT`` and whether it was shortened.

    The summary is one whitespace-normalized line. A value already within the
    limit is returned unchanged. A longer value is cut at the last word boundary
    that leaves room for a trailing ``...``, so the stored summary states its own
    truncation instead of ending mid-phrase; the boolean tells the caller to warn
    that the phrase was shortened.
    """
    text = single_line(value)
    if len(text) <= SUMMARY_LIMIT:
        return text, False
    head = text[: SUMMARY_LIMIT - len(_ELLIPSIS)]
    return head.rsplit(" ", 1)[0].rstrip() + _ELLIPSIS, True


def summary_warning(summary: str) -> str:
    """Return the one capture warning for a summary ``fit_summary`` shortened."""
    return (
        f"summary exceeds {SUMMARY_LIMIT} characters; stored the word-boundary "
        f"truncation '{summary}'"
    )


def slugify(value: str, fallback: str) -> str:
    """Return a lowercase filename slug, or ``fallback`` when none survives.

    The slug is capped at :data:`_SLUG_LIMIT` characters. An over-long value is
    cut at the last whole-word boundary inside the cap so a derived basename
    does not end in a mid-word fragment; a single word longer than the cap has
    no boundary to cut at, so it is clipped at the cap and the fallback still
    applies when nothing survives. The caller can always override the result
    with ``--slug``.
    """
    slug = _NON_SLUG.sub("-", value.lower()).strip("-")
    if len(slug) > _SLUG_LIMIT:
        head = slug[:_SLUG_LIMIT]
        boundary = head.rsplit("-", 1)[0].rstrip("-")
        slug = boundary or head.rstrip("-")
    return slug or fallback


def id_number(node_id: str, prefix: str) -> int | None:
    """Return the number of a ``<prefix>-NNN`` id, or ``None`` when malformed."""
    match = re.fullmatch(re.escape(prefix) + r"-(\d+)", node_id)
    return int(match.group(1)) if match is not None else None


def existing_ids(nodes_dir: str, prefix: str) -> dict[str, str]:
    """Map every ``<prefix>-NNN`` id already on disk to its path, across statuses."""
    found: dict[str, str] = {}
    for path in sorted(glob.glob(os.path.join(nodes_dir, "*", f"{prefix}-*.md"))):
        parts = os.path.basename(path)[:-3].split("-", 2)
        if len(parts) >= 2 and parts[1].isdigit():
            found[f"{parts[0]}-{parts[1]}"] = path
    return found


def next_number(nodes_dir: str, prefix: str) -> int:
    """Return the next free number for ``prefix`` from Markdown alone."""
    numbers = [int(node_id.split("-")[1]) for node_id in existing_ids(nodes_dir, prefix)]
    return max(numbers, default=0) + 1


def discover_route(nodes_dir: str) -> str | None:
    """Return the primary route to the root hub ``index-map.md`` names."""
    index_path = os.path.join(nodes_dir, "index-map.md")
    try:
        with open(index_path, encoding="utf-8") as handle:
            text = handle.read()
    except OSError:
        return None
    match = _ROOT_ROUTE.search(text)
    if match is None:
        return None
    return f"Area [[{match.group(1)}]]"


def normalize_route(route: str) -> str | None:
    """Return the canonical ``Parent``/``Area`` route, or ``None`` if malformed."""
    candidate = single_line(route).rstrip(".")
    return candidate if _ROUTE.fullmatch(candidate) is not None else None


def write_new(path: str, content: str) -> bool:
    """Create ``path`` without clobbering an existing node."""
    try:
        descriptor = os.open(path, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
    except FileExistsError:
        return False
    with os.fdopen(descriptor, "w", encoding="utf-8") as handle:
        handle.write(content)
    return True


def utc_now() -> str:
    """Return the current UTC timestamp in the vault's frontmatter format."""
    return datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ")


def reservation_dir(nodes_dir: str) -> str:
    """Return the portable reservation directory inside a vault directory.

    It holds one ``PREFIX-NNN`` marker per number the no-sidecar fallback has
    reserved. It is local coordination state, not vault Markdown: the markers
    are outside the checker's status-directory scan.
    """
    return os.path.join(nodes_dir, vault.RESERVATION_NAME)


def reserved_numbers(nodes_dir: str, prefix: str) -> set[int]:
    """Return the numbers the portable fallback already reserved for ``prefix``."""
    numbers: set[int] = set()
    for path in glob.glob(os.path.join(reservation_dir(nodes_dir), f"{prefix}-*")):
        number = id_number(os.path.basename(path), prefix)
        if number is not None:
            numbers.add(number)
    return numbers


def taken_numbers(nodes_dir: str, prefix: str) -> set[int]:
    """Return every number already taken for ``prefix`` by a node or a reservation."""
    on_disk = {int(node_id.split("-", 1)[1]) for node_id in existing_ids(nodes_dir, prefix)}
    return on_disk | reserved_numbers(nodes_dir, prefix)


def _vault_in_current_worktree(nodes_dir: str) -> bool:
    """Return whether ``nodes_dir`` lies inside the current Git worktree.

    The sidecar counter is scoped to one project, so it only governs that
    project's own vault. Numbering an unrelated vault from it would advance an
    identity space the vault does not share, so capture falls back to a
    vault-local reservation there instead.
    """
    try:
        completed = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            capture_output=True,
            text=True,
            check=True,
        )
    except (OSError, subprocess.CalledProcessError):
        return False
    root = os.path.realpath(completed.stdout.strip() or os.sep)
    nodes = os.path.realpath(nodes_dir)
    return nodes == root or nodes.startswith(root + os.sep)


def _sidecar_reserve(nodes_dir: str, prefix: str, taken: set[int]) -> int | None:
    """Reserve ``prefix`` through the hybrid sidecar when it governs the vault.

    Returns ``None`` when no sidecar exists or the target vault is outside the
    sidecar's project, which selects the portable fallback. A sidecar that
    exists and governs the vault is authoritative: an allocation error is
    raised rather than silently mixed with the fallback, which could hand out a
    number the sidecar had already reserved.
    """
    try:
        if not sidecar.database_path().is_file():
            return None
    except sidecar.SidecarError:
        return None
    if not _vault_in_current_worktree(nodes_dir):
        return None
    return sidecar.allocate(prefix, taken)


def _reserve_on_disk(nodes_dir: str, prefix: str, taken: set[int]) -> int:
    """Reserve the next free number with an exclusive-create marker file.

    ``taken`` is a snapshot used to skip known numbers; the exclusive create is
    what makes the reservation atomic, so a marker another writer created after
    the snapshot still fails and advances the candidate. A marker is never
    released: the written node file supersedes it, and a writer that fails
    leaves a wasted number rather than a duplicate identity.
    """
    directory = reservation_dir(nodes_dir)
    try:
        os.makedirs(directory, exist_ok=True)
    except OSError as error:
        raise AllocationError(
            f"unable to create the reservation directory {directory}"
        ) from error
    number = next_number(nodes_dir, prefix)
    for _ in range(_ALLOCATION_ATTEMPTS):
        if number not in taken:
            marker = os.path.join(directory, f"{prefix}-{number:03d}")
            try:
                descriptor = os.open(marker, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o644)
            except FileExistsError:
                pass
            else:
                os.close(descriptor)
                return number
        number += 1
    raise AllocationError(f"unable to reserve a free {prefix} id")


def reserve_number(nodes_dir: str, prefix: str) -> int:
    """Atomically reserve and return the next free ``PREFIX-NNN`` number.

    This is the one allocation contract shared by ``braintree node record`` and
    ``braintree feedback record``: a number is reserved before its node file is
    written, so two concurrent callers with different slugs cannot both choose
    the same number. When the project's sidecar exists and owns the vault, the
    number comes from the same atomic counter ``braintree allocate`` uses, so
    the reservation spans worktrees; otherwise the portable vault-local fallback
    above reserves it. A number already taken by a node or an earlier
    reservation is always skipped.
    """
    taken = taken_numbers(nodes_dir, prefix)
    sidecar_number = _sidecar_reserve(nodes_dir, prefix, taken)
    if sidecar_number is not None:
        return sidecar_number
    return _reserve_on_disk(nodes_dir, prefix, taken)


def _next_field(value: str) -> str:
    """Render a ``next`` value, quoting a lone wikilink to keep it a scalar."""
    if _WIKILINK_ONLY.fullmatch(value) is None:
        return value
    return f'"{value}"'


def _render(
    route: str,
    summary: str,
    next_line: str | None,
    body: str,
    updated: str,
    status: str | None = None,
) -> str:
    header = ["---", "context_rev: 1"]
    if status is not None:
        header.append(f"status: {status}")
    header.extend([f"updated: {updated}", f"summary: {summary}"])
    if next_line is not None:
        header.append(f"next: {_next_field(next_line)}")
    header.append("---")
    return "\n".join(header) + "\n\n" + f"{route}.\n\n" + body + "\n"


def render(
    route: str,
    summary: str,
    next_line: str | None,
    body: str,
    updated: str,
    status: str | None = None,
) -> str:
    """Render one captured node's Markdown from its validated fields.

    This is the single spelling of the captured-node shape shared by
    ``braintree node record`` and the transactional
    ``braintree node decompose`` path, so a child a decomposition writes byte-
    matches one the single-record path would have written.
    """
    return _render(route, summary, next_line, body, updated, status)


def canonical_path(nodes_dir: str, node_id: str, slug: str) -> str:
    """Return the stationary, sharded canonical path for a new node."""
    canonical = identity.normalize_node_id(node_id)
    if not identity.CANONICAL_ID.fullmatch(canonical):
        raise identity.IdentityError("new nodes require a canonical lowercase identity")
    return os.path.join(
        nodes_dir, store.CANONICAL_DIRECTORY, canonical[-2:], f"{canonical}-{slug}.md"
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run ``braintree node record`` and return the process exit code."""
    args = list(sys.argv[1:] if argv is None else argv)
    nodes_dir: str | None = None
    node_type: str | None = None
    route: str | None = None
    explicit_id: str | None = None
    summary: str | None = None
    slug: str | None = None
    status = _DEFAULT_STATUS
    next_value: str | None = None
    body: str | None = None
    while args:
        argument = args.pop(0)
        if argument in {"-h", "--help"}:
            print(_USAGE)
            return 0
        if argument in _VALUE_OPTIONS:
            if not args:
                print(field("error", f"{argument} requires a value"))
                return 2
            value = args.pop(0)
            if argument == "--nodes":
                nodes_dir = value
            elif argument == "--route":
                route = value
            elif argument == "--id":
                explicit_id = value
            elif argument == "--summary":
                summary = value
            elif argument == "--slug":
                slug = value
            elif argument == "--type":
                node_type = value
            elif argument == "--status":
                status = value
            elif argument == "--next":
                next_value = value
            else:
                body = value
        elif argument.startswith("-"):
            print(field("error", f"unknown option: {argument}"))
            return 2
        else:
            print(field("error", f"unexpected argument: {argument}"))
            return 2

    node_type = single_line(node_type or "").upper()
    if node_type not in _CAPTURE_TYPES:
        print(field("error", f"--type must be one of {', '.join(_CAPTURE_TYPES)}"))
        print(
            field(
                "help",
                "FBK friction is recorded with `braintree feedback record`, and a "
                "root IDX hub is declared in index-map.md.",
            )
        )
        return 2

    status = single_line(status).lower()
    if status not in _STATUSES:
        print(field("error", f"--status must be one of {', '.join(_STATUSES)}"))
        return 2

    summary, truncated = fit_summary(summary or "")
    if not summary:
        print(field("error", "braintree node record requires --summary"))
        return 2

    body = (body or "").strip("\n")
    if not body.strip():
        print(field("error", "braintree node record requires --body"))
        return 2

    next_line = single_line(next_value) if next_value is not None else None
    if status == "resolved":
        if next_line:
            print(field("error", "a resolved node must omit --next"))
            return 2
        next_line = None
    elif node_type in _TASK_TYPES and not next_line:
        print(field("error", f"a {node_type} node in {status} requires --next"))
        print(
            field(
                "help",
                "Pass the one action, for example --next 'Add the boundary test.' "
                "or --next '[[direct-child]]'.",
            )
        )
        return 2
    if status == "blocked" and (
        _BLOCKED_HEADING.search(body) is None
        or "Blocked by" not in body
        or "Unblocks when" not in body
    ):
        print(
            field(
                "error",
                "a blocked node body requires a # Blocked section with "
                "Blocked by and Unblocks when",
            )
        )
        print(field("help", "Pass that section in --body, or choose another --status."))
        return 2

    nodes_dir = vault.resolve(nodes_dir)
    if not os.path.isdir(nodes_dir):
        print(field("error", f"nodes directory does not exist: {nodes_dir}"))
        print(
            field(
                "help",
                "Run from a vault root or pass --nodes pointing at its nodes directory.",
            )
        )
        return 1
    try:
        identity.ensure_project_uid(nodes_dir)
    except identity.IdentityError as error:
        print(field("error", str(error)))
        return 1

    if route is None:
        discovered = discover_route(nodes_dir)
        if discovered is None:
            print(field("error", "unable to discover a root hub in index-map.md"))
            print(field("help", "Pass --route 'Area [[IDX-...]]' to route the node."))
            return 1
        route = discovered
    normalized = normalize_route(route)
    if normalized is None:
        print(field("error", "route must be 'Parent [[NODE]]' or 'Area [[NODE]]'"))
        return 2
    route = normalized

    node_id: str | None = None
    if explicit_id is not None:
        try:
            node_id = identity.normalize_node_id(single_line(explicit_id))
        except identity.IdentityError:
            print(field("error", f"id must be a canonical {node_type.lower()} identity"))
            return 2
        if not (
            node_id.startswith(node_type.lower() + "-")
            and identity.CANONICAL_ID.fullmatch(node_id)
        ):
            print(field("error", f"id must be a canonical {node_type.lower()} identity"))
            return 2

    slug = slugify(slug if slug is not None else summary, "node")
    updated = utc_now()
    for _ in range(100):
        if explicit_id is None:
            node_id = identity.generate_node_id(node_type)
        assert node_id is not None
        path = canonical_path(nodes_dir, node_id, slug)
        try:
            os.makedirs(os.path.dirname(path), exist_ok=True)
        except OSError as error:
            print(field("error", f"unable to create canonical node directory: {error}"))
            return 1
        if write_new(path, _render(route, summary, next_line, body, updated, status)):
            if truncated:
                print(field("warning", summary_warning(summary)))
            print(field("result", "recorded"))
            print(field("id", node_id))
            print(field("path", path))
            print(field("status", status))
            return 0
        if explicit_id is not None:
            print(field("error", f"node already exists: {path}"))
            return 1

    print(field("error", f"unable to generate a unique {node_type.lower()} identity"))
    return 1


if __name__ == "__main__":  # pragma: no cover - module entry point
    raise SystemExit(main())
