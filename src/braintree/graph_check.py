"""The read-only ``graph-check`` vault validator.

Typed Python implementation of the read-only vault validator. It enforces the same
status-directory, frontmatter, lifecycle, canonical-edge, dependency-pin,
reachability, cycle, and focus rules, and preserves the option surface,
exit codes, and error strings. The checker is deliberately stateless.

Every finding carries a documented stable code so a client can branch on the
finding without parsing the human sentence. The codes are the keys of
:data:`FINDING_CODES`; ``--format toon`` emits one ``code,node,detail`` record
per finding while the default human output stays byte-for-byte identical.

Finding codes by class:

- Vault: ``vault-no-nodes``, ``vault-missing-directory``.
- Node frontmatter and lifecycle: ``node-status-directory``,
  ``node-frontmatter-missing``, ``node-frontmatter-mapping``,
  ``node-context-rev``, ``node-updated``, ``node-summary``,
  ``node-authority-fields``, ``node-next-required``, ``node-blocked-section``,
  ``node-disposition``, ``node-disposition-status``, ``node-resolved-next``,
  ``node-reciprocal-edge``, ``node-duplicate-identity``, ``node-broken-link``.
- Feedback: ``feedback-revision-missing``, ``feedback-revision-format``,
  ``feedback-section-missing``, ``feedback-content-missing``.
- Context edges: ``context-pin-trailing-text``, ``context-pin-missing``,
  ``context-unresolved``, ``context-rev-mismatch``.
- Gate placement: ``gate-outside-context``.
- Reconnaissance references: ``reference-malformed``,
  ``reference-outside-context``, ``reference-target-type``,
  ``reference-duplicate``.
- Index map: ``index-missing``, ``index-copied-state``,
  ``index-root-route-missing``, ``index-root-hub-type``, ``index-broken-link``,
  ``index-focus-without-active``, ``index-focus-target``.
- Routes and frontier: ``route-root-hub-unrouted``, ``route-primary-missing``,
  ``route-cycle``, ``route-orphan``, ``next-multiple-frontiers``,
  ``next-action-wikilink``, ``next-not-direct-child``, ``next-resolved-node``.
"""

from __future__ import annotations

import os
import re
import sys
from collections.abc import Sequence
from dataclasses import dataclass

from . import store, vault
from .revision import reported_version
from .toon import field, table

__all__ = [
    "CONTEXT_EDGE_LINE",
    "CONTEXT_PIN",
    "CONTEXT_PIN_LINE",
    "CONTEXT_RELATIONS",
    "FINDING_CODES",
    "GATED_RELATION",
    "Finding",
    "PROBLEM_MISMATCH",
    "PROBLEM_MISSING",
    "PROBLEM_UNPINNED",
    "PROBLEM_UNRESOLVED",
    "REFERENCE_LINE",
    "REFERENCE_RELATION",
    "REFERENCE_TARGET_TYPES",
    "context_pin_problem",
    "findings",
    "main",
    "reference_targets",
    "stale_reason",
]

_USAGE = (
    "usage: braintree check [--version] [--allow-stale] [--allow-orphan NODE] "
    "[--allow-pending-advance NODE] [--format text|toon] [nodes-directory]\n"
    "Validate a file-only Braintree vault without writing state.\n"
    "--format toon prints one code,node,detail record per finding."
)

_STATUSES = frozenset({"proposed", "active", "blocked", "resolved"})

# One canonical context-edge definition, shared with the derived index so
# ``braintree check`` and ``braintree stale`` cannot disagree. A context edge
# supplies consumer-relevant context, so it carries a terminating
# ``at context_rev N.`` pin. ``Depends on`` is the common case; ``Implements``,
# ``Requires``, and ``Governed by`` are equally context-bearing. Navigation
# relations such as ``Parent``, ``Area``, ``Indexes``, and ``Superseded by`` are
# deliberately absent, and so is the gate ``Gated on``: a target that is not yet
# resolved has no consumable context to pin, so the gate stands in for the
# pinned edge until the target resolves.
CONTEXT_RELATIONS: tuple[str, ...] = (
    "Depends on",
    "Implements",
    "Requires",
    "Governed by",
)
GATED_RELATION = "Gated on"
# One canonical, non-pinned reference relation: a node cites durable
# reconnaissance (a THO, DEF, or DEC) it was informed by without making it a
# dependency. It carries no `context_rev` pin, so it never affects readiness,
# staleness, primary routing, ownership, or automatic context loading; the
# directly referenced context is loaded only when a reader asks for it.
REFERENCE_RELATION = "Informed by"
REFERENCE_TARGET_TYPES = ("THO", "DEF", "DEC")
REFERENCE_LINE = re.compile(
    rf"^{REFERENCE_RELATION} \[\[([^\]]+)\]\]\.$", re.MULTILINE
)
# The malformed-use detector is intentionally anchored on the wikilink form so an
# ordinary prose sentence that merely begins with the relation words is not a
# reference line at all.
REFERENCE_ANY = re.compile(
    rf"^{REFERENCE_RELATION} \[\[.*$", re.MULTILINE
)
CONTEXT_EDGE_LINE = re.compile(
    r"^(?:" + "|".join(CONTEXT_RELATIONS) + r")\s+\[\[([^\]]+)\]\](.*)$",
    re.MULTILINE,
)
# The gate is a plain relation line, not a context edge: it carries no pin, so
# only its placement is checked. Anchoring both ends makes the match an exact
# relation, so prose that mentions or quotes the form is not one.
GATED_LINE = re.compile(
    rf"^{GATED_RELATION} \[\[([^\]]+)\]\]\.\s*$", re.MULTILINE
)
CONTEXT_PIN = re.compile(r" at context_rev (\d+)\.")
CONTEXT_PIN_LINE = re.compile(r" at context_rev (\d+)\.\s*")

# One problem per context edge, in precedence order: an unpinned edge is
# malformed, a missing target is unreadable, an unresolved target is not ready
# to consume, and a revision mismatch is stale context.
PROBLEM_UNPINNED = "unpinned"
PROBLEM_MISSING = "missing"
PROBLEM_UNRESOLVED = "unresolved"
PROBLEM_MISMATCH = "mismatch"

_STALE_REASONS: dict[str, str] = {
    PROBLEM_UNPINNED: "missing context_rev pin",
    PROBLEM_MISSING: "missing target",
    PROBLEM_MISMATCH: "context_rev mismatch",
}

# The documented, stable code for every existing check error class. A code
# never changes meaning once shipped; add a new code rather than repurposing
# one. ``node`` is the offending node path, or the index map, duplicate
# identity, or vault location when the finding is not owned by one node.
FINDING_CODES: dict[str, str] = {
    "vault-no-nodes": "nodes directory contains no node files",
    "vault-missing-directory": "nodes directory does not exist",
    "node-status-directory": "node is not in a known status directory",
    "node-frontmatter-missing": "node has no frontmatter block",
    "node-frontmatter-mapping": "frontmatter is not a flat mapping",
    "node-context-rev": "context_rev is not a positive integer",
    "node-updated": "updated is not a UTC ISO-8601 timestamp",
    "node-summary": "summary is missing or empty",
    "node-authority-fields": "frontmatter duplicates authority fields",
    "node-next-required": "unfinished task omits next",
    "node-blocked-section": "blocked node lacks a # Blocked section",
    "node-disposition": "disposition is not an allowed value",
    "node-disposition-status": "disposition on a node that is not resolved",
    "node-resolved-next": "resolved node still carries next",
    "node-reciprocal-edge": "node stores a reciprocal edge",
    "node-duplicate-identity": "two nodes share a node identity",
    "node-broken-link": "node links to a missing node",
    "feedback-revision-missing": "feedback node omits braintree_revision",
    "feedback-revision-format": "braintree_revision is malformed",
    "feedback-section-missing": "feedback node lacks a # Feedback section",
    "feedback-content-missing": "feedback node lacks a required Feedback label",
    "context-pin-trailing-text": "context_rev pin is followed by trailing text",
    "context-pin-missing": "context edge has no valid context_rev pin",
    "context-unresolved": "pinned dependency is not resolved",
    "context-rev-mismatch": "pinned dependency revision differs from current",
    "gate-outside-context": "Gated on relation appears outside the # Context section",
    "reference-malformed": "reference relation is not exactly Informed by [[TARGET]].",
    "reference-outside-context": "reference relation appears outside the # Context section",
    "reference-target-type": "referenced reconnaissance is not a THO, DEF, or DEC",
    "reference-duplicate": "node repeats the same reconnaissance reference",
    "index-missing": "index-map.md is missing",
    "index-copied-state": "index-map.md copies node state",
    "index-root-route-missing": "index-map.md lacks an Indexes root route",
    "index-root-hub-type": "root hub is not an IDX node",
    "index-broken-link": "index-map.md links to a missing node",
    "index-focus-without-active": "index-map.md keeps Focus without active tasks",
    "index-focus-target": "Focus target is not an active node",
    "route-root-hub-unrouted": "root hub carries a Parent or Area route",
    "route-primary-missing": "node lacks one primary Parent or Area route",
    "route-cycle": "parent route forms a cycle",
    "route-orphan": "unfinished node cannot reach a hub",
    "next-multiple-frontiers": "next names more than one frontier node",
    "next-action-wikilink": "action-sentence next contains a wikilink",
    "next-not-direct-child": "next frontier is not a direct child",
    "next-resolved-node": "next frontier is already resolved",
}

_FORBIDDEN_FIELDS = ("id", "type", "status", "seq", "mtime", "rev")
# Types that record knowledge rather than executable work; only tasks require `next`.
# `FBK` records Braintree friction as a durable, discoverable feedback node.
_KNOWLEDGE_TYPES = frozenset({"THO", "DEF", "DEC", "IDX", "FBK"})
_DISPOSITIONS = frozenset({"abandoned", "deprecated", "superseded"})
_FEEDBACK_TYPE = "FBK"
_FEEDBACK_LABELS = ("Attempted", "Friction", "Improvement")
_FEEDBACK_REVISION_FIELD = "braintree_revision"

_RECIPROCAL_EDGE = re.compile(
    r"(?:Child|Parent of|Indexed by|Depended on by|Supersedes|Backlink)\s+\[\["
)
_UPDATED_LINE = re.compile(r"^updated: ([^\n]+)$", re.MULTILINE)
_UPDATED_VALUE = re.compile(r"\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z")
_WIKILINK = re.compile(r"\[\[([^\]]+)\]\]")
_PRIMARY_ROUTE = re.compile(r"^(?:Parent|Area) \[\[([^\]]+)\]\]\.", re.MULTILINE)
_NODE_ID = re.compile(
    r"(?:[A-Z][A-Z0-9_]*-\d+|(?:tas|tho|def|dec|idx|fbk)-[0-7][0-9a-hjkmnp-tv-z]{25})"
)
_ROOT_ROUTE = re.compile(r"^\s*- Indexes \[\[([^\]]+)\]\]", re.MULTILINE)
_FOCUS_BLOCK = re.compile(r"^# Focus\n(.*?)(?=^# |\Z)", re.MULTILINE | re.DOTALL)
_CONTEXT_BLOCK = re.compile(r"^# Context\n(.*?)(?=^# |\Z)", re.MULTILINE | re.DOTALL)
_BLOCKED_BLOCK = re.compile(r"^# Blocked\n(.*?)(?=^# |\Z)", re.MULTILINE | re.DOTALL)
_INDEX_TABLE = re.compile(r"^\| .*\[\[", re.MULTILINE)
_INDEX_LINK = re.compile(r"\[\[([A-Z]+-\d+[^\]]*)\]\]")
_ID_ANCHOR = re.compile(
    r"(?:IDX-\d+|idx-[0-7][0-9a-hjkmnp-tv-z]{25})(?:-|\Z)"
)
_FEEDBACK_BLOCK = re.compile(r"^# Feedback\n(.*?)(?=^# |\Z)", re.MULTILINE | re.DOTALL)
_FEEDBACK_LINE = re.compile(
    r"^(" + "|".join(_FEEDBACK_LABELS) + r"):\s*(\S.*)$", re.MULTILINE
)
_BRAINTREE_REVISION = re.compile(r"\d+\.\d+\.\d+(?:[+\-][0-9A-Za-z.\-]+)?\Z")
_UNKNOWN_REVISION = "unknown"
_NUMBER = re.compile(r"-?\d+")

# Markdown code is quoted text, not graph syntax: a wikilink-shaped token inside
# an inline code span or a fenced code block documents the grammar, so link
# scanning reads a copy with those regions blanked. Masking preserves length and
# line breaks, so the scan sees the same structure without the quoted tokens.
_FENCE_OPEN = re.compile(r"^ {0,3}(`{3,}|~{3,})")
_FENCE_RUN = re.compile(r"^ {0,3}([`~]+)[ \t]*$")
_BACKTICK_RUN = re.compile(r"`+")


def _mask_inline_code(line: str) -> str:
    """Blank backtick-delimited code spans on one line, preserving length.

    A code span closes on the next run of exactly the opening backtick count,
    so a shorter or longer run stays literal text and never opens a span.
    """
    runs = list(_BACKTICK_RUN.finditer(line))
    if not runs:
        return line
    chars = list(line)
    index = 0
    while index < len(runs):
        opening = runs[index]
        closing_index = index + 1
        while closing_index < len(runs) and len(
            runs[closing_index].group(0)
        ) != len(opening.group(0)):
            closing_index += 1
        if closing_index == len(runs):
            index += 1
            continue
        closing = runs[closing_index]
        chars[opening.start() : closing.end()] = " " * (
            closing.end() - opening.start()
        )
        index = closing_index + 1
    return "".join(chars)


def _mask_code(text: str) -> str:
    """Blank inline code spans and fenced code blocks, preserving offsets."""
    masked: list[str] = []
    fence_char: str | None = None
    fence_len = 0
    for line in text.splitlines(keepends=True):
        content = line.rstrip("\r\n")
        tail = line[len(content) :]
        if fence_char is not None:
            closing = _FENCE_RUN.match(content)
            if (
                closing is not None
                and closing.group(1)[0] == fence_char
                and len(closing.group(1)) >= fence_len
            ):
                fence_char = None
            masked.append(" " * len(content) + tail)
            continue
        opening = _FENCE_OPEN.match(content)
        if opening is not None:
            fence_char = opening.group(1)[0]
            fence_len = len(opening.group(1))
            masked.append(" " * len(content) + tail)
            continue
        masked.append(_mask_inline_code(content) + tail)
    return "".join(masked)


@dataclass(frozen=True)
class Finding:
    """One validator finding: a stable code, its node, and the human detail."""

    code: str
    node: str
    detail: str


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


def _gate_hint(target: str, target_status: str | None) -> str:
    """Name the sanctioned gate form when the target is not yet ``resolved``.

    The gate is the unpinned ``Gated on [[X]].`` line, recorded in ``# Context``,
    that stands in for a context edge whose target cannot be consumed yet;
    returning the same clause for both the missing-pin and unresolved-target
    diagnostics keeps them pointing at that one documented form. Naming the
    section keeps the repair from itself triggering ``gate-outside-context``. A
    resolved or missing target has no gate to name, so the hint is empty.
    """
    if target_status is None or target_status == "resolved":
        return ""
    return (
        f"; a not-yet-resolved predecessor is recorded in `# Context` as "
        f"{GATED_RELATION} [[{target}]]."
    )


def context_pin_problem(
    pinned: int | None,
    target_status: str | None,
    current_rev: int | None,
) -> str | None:
    """Return the shared verdict for one context edge, or ``None`` if current.

    ``pinned`` is the ``context_rev`` recorded by the edge, ``target_status``
    is the pinned target's status directory (``None`` when the target is
    missing), and ``current_rev`` is the target's current ``context_rev``.
    """
    if pinned is None:
        return PROBLEM_UNPINNED
    if target_status is None:
        return PROBLEM_MISSING
    if target_status != "resolved":
        return PROBLEM_UNRESOLVED
    if current_rev != pinned:
        return PROBLEM_MISMATCH
    return None


def stale_reason(problem: str, target_status: str | None = None) -> str:
    """Render a shared verdict as the compact reason ``braintree stale`` prints."""
    if problem == PROBLEM_UNRESOLVED and target_status:
        return f"target is {target_status}, not resolved"
    return _STALE_REASONS[problem]


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


def reference_targets(text: str) -> list[str]:
    """Return the reconnaissance targets a node references, in authored order.

    This is the one canonical reader for :data:`REFERENCE_RELATION`. It masks
    quoted code like every other graph scan, so a relation shape documented
    inside an inline code span or fenced block is not itself a reference.
    """
    return [
        match.group(1) for match in REFERENCE_LINE.finditer(_mask_code(text))
    ]


def _check_feedback(
    path: str,
    text: str,
    metadata: dict[str, object],
    errors: list[Finding],
) -> None:
    """Validate the discoverable ``FBK`` feedback-node convention."""
    revision = metadata.get(_FEEDBACK_REVISION_FIELD)
    if not (isinstance(revision, str) and revision != ""):
        errors.append(
            Finding(
                "feedback-revision-missing",
                path,
                f"{path}: feedback node requires {_FEEDBACK_REVISION_FIELD} "
                "(use `unknown` when no revision is recorded)",
            )
        )
    elif revision != _UNKNOWN_REVISION and _BRAINTREE_REVISION.match(revision) is None:
        errors.append(
            Finding(
                "feedback-revision-format",
                path,
                f"{path}: {_FEEDBACK_REVISION_FIELD} must be a version like "
                "0.4.0+g1b58d57 or unknown",
            )
        )
    section = _FEEDBACK_BLOCK.search(text)
    if section is None:
        errors.append(
            Finding(
                "feedback-section-missing",
                path,
                f"{path}: feedback node requires a # Feedback section",
            )
        )
        return
    seen = {match.group(1) for match in _FEEDBACK_LINE.finditer(section.group(1))}
    for label in _FEEDBACK_LABELS:
        if label not in seen:
            errors.append(
                Finding(
                    "feedback-content-missing",
                    path,
                    f"{path}: feedback node requires a {label}: line in # Feedback",
                )
            )


def _collect_nodes(nodes_dir: str, errors: list[Finding]) -> list[_Node]:
    entries = list(store.iter_node_paths(nodes_dir))
    if not entries:
        errors.append(
            Finding("vault-no-nodes", "", f"no node files under {nodes_dir}")
        )
    nodes: list[_Node] = []
    for entry in entries:
        path, status = entry.path, entry.status
        name = os.path.basename(path)[:-3]
        text = _read_text(path)
        if status not in _STATUSES:
            errors.append(
                Finding(
                    "node-status-directory",
                    path,
                    f"{path}: invalid "
                    f"{'frontmatter status' if entry.stationary else 'status directory'} "
                    f"{status}",
                )
            )
            continue
        header = _extract_frontmatter(text)
        if header is None:
            errors.append(
                Finding("node-frontmatter-missing", path, f"{path}: missing frontmatter")
            )
            continue
        try:
            metadata = _parse_frontmatter(header)
        except _MappingError:
            errors.append(
                Finding(
                    "node-frontmatter-mapping",
                    path,
                    f"{path}: frontmatter must be a mapping",
                )
            )
            continue
        context_rev = metadata.get("context_rev")
        context_rev_ok = (
            isinstance(context_rev, int)
            and not isinstance(context_rev, bool)
            and context_rev > 0
        )
        if not context_rev_ok:
            errors.append(
                Finding(
                    "node-context-rev",
                    path,
                    f"{path}: context_rev must be a positive integer",
                )
            )
        updated_match = _UPDATED_LINE.search(header)
        updated = updated_match.group(1) if updated_match else None
        if updated is None or _UPDATED_VALUE.fullmatch(updated) is None:
            errors.append(
                Finding("node-updated", path, f"{path}: updated must be UTC ISO-8601")
            )
        summary = metadata.get("summary")
        if not (isinstance(summary, str) and summary != ""):
            errors.append(
                Finding("node-summary", path, f"{path}: summary is required")
            )
        forbidden = [
            key
            for key in metadata
            if key in _FORBIDDEN_FIELDS and not (entry.stationary and key == "status")
        ]
        if forbidden:
            errors.append(
                Finding(
                    "node-authority-fields",
                    path,
                    f"{path}: duplicated authority fields: {', '.join(forbidden)}",
                )
            )
        id_match = _NODE_ID.match(name)
        node_type = id_match.group(0).split("-")[0].upper() if id_match else None
        if (
            status in {"active", "proposed"}
            and node_type is not None
            and node_type not in _KNOWLEDGE_TYPES
        ):
            next_value = metadata.get("next")
            if not (isinstance(next_value, str) and next_value != ""):
                errors.append(
                    Finding(
                        "node-next-required",
                        path,
                        f"{path}: unfinished task requires next",
                    )
                )
        if node_type == _FEEDBACK_TYPE:
            _check_feedback(path, text, metadata, errors)
        if status == "blocked":
            blocked_match = _BLOCKED_BLOCK.search(text)
            blocked_section = blocked_match.group(1) if blocked_match else ""
            if "Blocked by" not in blocked_section or "Unblocks when" not in blocked_section:
                errors.append(
                    Finding(
                        "node-blocked-section",
                        path,
                        f"{path}: blocked node requires a # Blocked section with "
                        "Blocked by and Unblocks when",
                    )
                )
        disposition = metadata.get("disposition")
        if disposition is not None:
            if not (isinstance(disposition, str) and disposition in _DISPOSITIONS):
                errors.append(
                    Finding(
                        "node-disposition",
                        path,
                        f"{path}: disposition must be abandoned, deprecated, or superseded",
                    )
                )
            elif status != "resolved":
                errors.append(
                    Finding(
                        "node-disposition-status",
                        path,
                        f"{path}: disposition requires a resolved node",
                    )
                )
        if status == "resolved" and "next" in metadata:
            errors.append(
                Finding(
                    "node-resolved-next",
                    path,
                    f"{path}: resolved node must omit next",
                )
            )
        if _RECIPROCAL_EDGE.search(text):
            errors.append(
                Finding(
                    "node-reciprocal-edge",
                    path,
                    f"{path}: stored reciprocal edge",
                )
            )
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


def _check_duplicates(nodes: list[_Node], errors: list[Finding]) -> dict[str, list[_Node]]:
    by_name: dict[str, list[_Node]] = {}
    for node in nodes:
        by_name.setdefault(node.name, []).append(node)
    for name, matches in by_name.items():
        if len(matches) > 1:
            errors.append(
                Finding(
                    "node-duplicate-identity",
                    name,
                    f"duplicate node identity: {name}",
                )
            )
    by_id: dict[str | None, list[_Node]] = {}
    for node in nodes:
        by_id.setdefault(node.node_id, []).append(node)
    for node_id, matches in by_id.items():
        if len(matches) > 1:
            label = node_id if node_id is not None else matches[0].name
            errors.append(
                Finding(
                    "node-duplicate-identity",
                    label,
                    f"duplicate node identity: {label}",
                )
            )
    return by_name


def _check_links(
    nodes: list[_Node], by_name: dict[str, list[_Node]], errors: list[Finding]
) -> None:
    for node in nodes:
        for target in _WIKILINK.findall(_mask_code(node.text)):
            if target not in by_name:
                errors.append(
                    Finding(
                        "node-broken-link",
                        node.path,
                        f"{node.path}: broken link [[{target}]]",
                    )
                )


def _check_context_edges(
    nodes: list[_Node],
    by_name: dict[str, list[_Node]],
    allow_stale: bool,
    errors: list[Finding],
) -> None:
    for node in nodes:
        for target, suffix in CONTEXT_EDGE_LINE.findall(node.text):
            target_nodes = by_name.get(target)
            target_status = target_nodes[0].status if target_nodes else None
            pin_match = CONTEXT_PIN_LINE.fullmatch(suffix)
            if pin_match is None:
                partial = CONTEXT_PIN.search(suffix)
                trailing = suffix[partial.end() :].strip() if partial else ""
                if trailing:
                    errors.append(
                        Finding(
                            "context-pin-trailing-text",
                            node.path,
                            f"{node.path}: context_rev pin for [[{target}]] has "
                            f"trailing text: {trailing}",
                        )
                    )
                else:
                    errors.append(
                        Finding(
                            "context-pin-missing",
                            node.path,
                            f"{node.path}: invalid or missing context_rev pin for "
                            f"[[{target}]]{_gate_hint(target, target_status)}",
                        )
                    )
                continue
            pin = int(pin_match.group(1))
            if target_nodes is None:
                continue
            target_node = target_nodes[0]
            current = target_node.metadata.get("context_rev")
            problem = context_pin_problem(
                pin,
                target_node.status,
                current if isinstance(current, int) else None,
            )
            if problem == PROBLEM_UNRESOLVED:
                errors.append(
                    Finding(
                        "context-unresolved",
                        node.path,
                        f"{node.path}: pinned dependency [[{target}]] is "
                        f"{target_node.status}, not resolved"
                        f"{_gate_hint(target, target_node.status)}",
                    )
                )
            elif problem == PROBLEM_MISMATCH and not allow_stale:
                label = current if isinstance(current, int) else ""
                errors.append(
                    Finding(
                        "context-rev-mismatch",
                        node.path,
                        f"{node.path}: context_rev mismatch for [[{target}]] "
                        f"(pinned {pin}, current {label})",
                    )
                )


def _check_gate_placement(nodes: list[_Node], errors: list[Finding]) -> None:
    """Flag a gate relation authored outside a node's ``# Context`` section.

    The gate stands in for the pinned context edge until its target resolves,
    and the section is the one place that edge belongs. A node without a
    ``# Context`` section offers no valid placement, so its gate is misplaced
    too. Quoted and fenced copies of the form are masked out before the scan,
    so only authored relation lines can be flagged.
    """
    for node in nodes:
        masked = _mask_code(node.text)
        context_spans = [match.span(1) for match in _CONTEXT_BLOCK.finditer(masked)]
        for match in GATED_LINE.finditer(masked):
            if any(start <= match.start() < end for start, end in context_spans):
                continue
            errors.append(
                Finding(
                    "gate-outside-context",
                    node.path,
                    f"{node.path}: {GATED_RELATION} [[{match.group(1)}]] must appear "
                    "in # Context",
                )
            )


def _check_references(
    nodes: list[_Node], by_name: dict[str, list[_Node]], errors: list[Finding]
) -> None:
    """Validate the non-pinned reconnaissance reference relation structurally.

    The checker answers only structural questions: the line is exactly
    ``Informed by [[TARGET]].`` with no pin or trailing text, it sits in
    ``# Context``, its target is a knowledge node (a ``THO``/``DEF``/``DEC``),
    and a node does not repeat a target. It never judges whether the referenced
    reconnaissance is useful, current, or sufficient. A missing target is
    already a ``node-broken-link``, so it is not reported again here; the read
    surface reports it as ``missing``.
    """
    for node in nodes:
        masked = _mask_code(node.text)
        context_spans = [match.span(1) for match in _CONTEXT_BLOCK.finditer(masked)]
        seen: set[str] = set()
        for match in REFERENCE_ANY.finditer(masked):
            line = match.group(0).rstrip()
            exact = REFERENCE_LINE.fullmatch(line)
            if exact is None:
                errors.append(
                    Finding(
                        "reference-malformed",
                        node.path,
                        f"{node.path}: {REFERENCE_RELATION} line must be exactly "
                        f"'{REFERENCE_RELATION} [[TARGET]].'",
                    )
                )
                continue
            target = exact.group(1)
            if not any(start <= match.start() < end for start, end in context_spans):
                errors.append(
                    Finding(
                        "reference-outside-context",
                        node.path,
                        f"{node.path}: {REFERENCE_RELATION} [[{target}]] must appear "
                        "in # Context",
                    )
                )
            if target in seen:
                errors.append(
                    Finding(
                        "reference-duplicate",
                        node.path,
                        f"{node.path}: repeated {REFERENCE_RELATION} [[{target}]]",
                    )
                )
                continue
            seen.add(target)
            target_nodes = by_name.get(target)
            if target_nodes is None:
                continue
            node_type = (target_nodes[0].node_id or "").split("-", 1)[0].upper()
            if node_type not in REFERENCE_TARGET_TYPES:
                errors.append(
                    Finding(
                        "reference-target-type",
                        node.path,
                        f"{node.path}: {REFERENCE_RELATION} [[{target}]] must be a "
                        f"{'/'.join(REFERENCE_TARGET_TYPES)} node",
                    )
                )


def _validate(
    nodes_dir: str,
    *,
    allow_stale: bool,
    allowed_orphans: list[str | None],
    allowed_pending: Sequence[str | None] = (),
) -> tuple[list[Finding], int]:
    errors: list[Finding] = []
    if not os.path.isdir(nodes_dir):
        return [
            Finding(
                "vault-missing-directory",
                nodes_dir,
                f"nodes directory does not exist: {nodes_dir}",
            )
        ], 0
    nodes = _collect_nodes(nodes_dir, errors)
    by_name = _check_duplicates(nodes, errors)
    _check_links(nodes, by_name, errors)

    index_path = os.path.join(nodes_dir, "index-map.md")
    index_text = _read_text(index_path) if os.path.isfile(index_path) else ""
    if not os.path.isfile(index_path):
        errors.append(
            Finding("index-missing", index_path, "missing index-map.md")
        )
    if _INDEX_TABLE.search(index_text):
        errors.append(
            Finding(
                "index-copied-state",
                index_path,
                "index-map.md contains copied node-state table",
            )
        )
    root_hubs = list(dict.fromkeys(_ROOT_ROUTE.findall(index_text)))
    if not root_hubs:
        errors.append(
            Finding(
                "index-root-route-missing",
                index_path,
                "index-map.md lacks an Indexes root route",
            )
        )
    for hub in root_hubs:
        if _ID_ANCHOR.match(hub) is None:
            errors.append(
                Finding("index-root-hub-type", hub, f"root hub is not IDX: {hub}")
            )
    focus_match = _FOCUS_BLOCK.search(index_text)
    focus = list(dict.fromkeys(_WIKILINK.findall(focus_match.group(1) if focus_match else "")))

    _check_context_edges(nodes, by_name, allow_stale, errors)
    _check_gate_placement(nodes, errors)
    _check_references(nodes, by_name, errors)
    for target in _INDEX_LINK.findall(index_text):
        if target not in by_name:
            errors.append(
                Finding(
                    "index-broken-link",
                    index_path,
                    f"index-map.md: broken link [[{target}]]",
                )
            )

    routes: dict[str, str | None] = {}
    for node in nodes:
        found = _PRIMARY_ROUTE.findall(node.text)
        if node.name in root_hubs:
            if found:
                errors.append(
                    Finding(
                        "route-root-hub-unrouted",
                        node.path,
                        f"{node.path}: root hub must not have Parent or Area",
                    )
                )
        elif len(found) != 1 and node.name not in allowed_orphans:
            errors.append(
                Finding(
                    "route-primary-missing",
                    node.path,
                    f"{node.path}: requires exactly one primary Parent or Area route",
                )
            )
        else:
            routes[node.name] = found[0] if found else None

    for node in nodes:
        next_value = node.metadata.get("next")
        if not isinstance(next_value, str) or next_value == "":
            continue
        frontier = _WIKILINK.findall(next_value)
        # The only accepted wikilink form is a lone ``[[direct-child]]`` route;
        # a ``next`` written as an action sentence carries no wikilink at all.
        lone_link = _WIKILINK.fullmatch(next_value.strip())
        if len(frontier) > 1:
            errors.append(
                Finding(
                    "next-multiple-frontiers",
                    node.path,
                    f"{node.path}: next names multiple frontier nodes: "
                    + ", ".join(f"[[{target}]]" for target in frontier),
                )
            )
        elif frontier and lone_link is None:
            # The checker treated an action sentence's embedded link as the
            # frontier route; name the offending token so it need not be found
            # by trial.
            errors.append(
                Finding(
                    "next-action-wikilink",
                    node.path,
                    f"{node.path}: action-sentence next contains a wikilink: "
                    f"[[{frontier[0]}]]",
                )
            )
        elif lone_link is not None:
            target = lone_link.group(1)
            if routes.get(target) != node.name:
                errors.append(
                    Finding(
                        "next-not-direct-child",
                        node.path,
                        f"{node.path}: next frontier [[{target}]] is not a direct "
                        "child",
                    )
                )
            elif node.status != "resolved":
                child_nodes = by_name.get(target)
                if child_nodes is not None and child_nodes[0].status == "resolved":
                    # A pending advance — a resolved frontier child whose advance
                    # a handoff still owes — and a genuine stale route are the
                    # same Markdown, so a stateless checker cannot derive the
                    # difference from file content. A declaration names the
                    # pending advance; every undeclared instance remains this
                    # failure.
                    if (
                        node.name not in allowed_pending
                        and node.node_id not in allowed_pending
                    ):
                        errors.append(
                            Finding(
                                "next-resolved-node",
                                node.path,
                                f"{node.path}: next frontier [[{target}]] is already "
                                "resolved",
                            )
                        )

    for node in nodes:
        if node.status == "resolved":
            continue
        current: str | None = node.name
        seen: set[str | None] = set()
        while current not in root_hubs and current not in focus:
            if current in seen:
                errors.append(
                    Finding(
                        "route-cycle",
                        node.path,
                        f"{node.path}: parent cycle at {current}",
                    )
                )
                break
            seen.add(current)
            if current is None or current not in routes:
                if node.name not in allowed_orphans and node.node_id not in allowed_orphans:
                    errors.append(
                        Finding(
                            "route-orphan",
                            node.path,
                            f"{node.path}: orphan unfinished node",
                        )
                    )
                break
            current = routes[current]

    active_tasks = [
        node for node in nodes if node.status == "active" and node.name.startswith("TAS-")
    ]
    if not active_tasks and focus:
        errors.append(
            Finding(
                "index-focus-without-active",
                index_path,
                "index-map.md: Focus remains without active tasks",
            )
        )
    for target in focus:
        target_nodes = by_name.get(target)
        if target_nodes is None or target_nodes[0].status != "active":
            errors.append(
                Finding(
                    "index-focus-target",
                    index_path,
                    f"index-map.md: Focus target is not active: {target}",
                )
            )
    return errors, len(nodes)


def findings(nodes_dir: str) -> list[Finding]:
    """Return the findings ``braintree check`` would report for ``nodes_dir``.

    A read-only wrapper over the same validation the command runs, so an
    orientation packet reports exactly the conflicts the checker would.
    """
    errors, _ = _validate(nodes_dir, allow_stale=False, allowed_orphans=[])
    return errors


def _print_toon(findings: list[Finding], node_count: int) -> None:
    """Emit one structured record per finding plus the run summary."""
    print(field("result", "failed" if findings else "passed"))
    print(field("nodes", node_count))
    print(
        table(
            "findings",
            "code,node,detail",
            ((finding.code, finding.node, finding.detail) for finding in findings),
            "findings: 0",
        )
    )


def main(argv: Sequence[str] | None = None) -> int:
    """Run the ``braintree check`` command and return the process exit code."""
    args = list(sys.argv[1:] if argv is None else argv)
    allow_stale = False
    allowed_orphans: list[str | None] = []
    allowed_pending: list[str | None] = []
    output_format = "text"
    while args and args[0].startswith("-"):
        option = args.pop(0)
        if option == "--allow-stale":
            allow_stale = True
        elif option == "--allow-orphan":
            allowed_orphans.append(args.pop(0) if args else None)
        elif option == "--allow-pending-advance":
            allowed_pending.append(args.pop(0) if args else None)
        elif option == "--format":
            if not args:
                print("error: --format requires text or toon", file=sys.stderr)
                return 1
            output_format = args.pop(0)
            if output_format not in {"text", "toon"}:
                print(f"error: unknown format: {output_format}", file=sys.stderr)
                return 1
        elif option in {"-h", "--help"}:
            print(_USAGE)
            return 0
        elif option in {"--version", "-v", "-V"}:
            print(reported_version())
            return 0
        else:
            print("error: unknown option", file=sys.stderr)
            return 1
    nodes_dir = args.pop(0) if args else vault.resolve()
    if args:
        print(_USAGE)
        return 2
    errors, node_count = _validate(
        nodes_dir,
        allow_stale=allow_stale,
        allowed_orphans=allowed_orphans,
        allowed_pending=allowed_pending,
    )
    if output_format == "toon":
        _print_toon(errors, node_count)
    else:
        for error in errors:
            print(f"error: {error.detail}", file=sys.stderr)
    if errors:
        return 1
    if output_format != "toon":
        print(f"graph check: passed ({node_count} nodes)")
    return 0


if __name__ == "__main__":  # pragma: no cover - module entry point
    raise SystemExit(main())
