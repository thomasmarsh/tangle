"""Contract tests for ``SKILL.md`` and the live repository execution graph.

Ported from ``tests/skill.sh`` so the skill text and the checked-in vault are
validated with the Python toolchain instead of Ruby.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

from braintree import graph_check

_ROOT = Path(__file__).resolve().parents[1]
_SKILL = _ROOT / "SKILL.md"
_AGENTS = _ROOT / "AGENTS.md"
_NODES = _ROOT / "nodes"
_INDEX = _NODES / "index-map.md"

_GRAPH_CHECK_COMMAND = "After each integration, run `braintree check nodes`"

_HYBRID_CONTRACT: tuple[str, ...] = (
    "nodes/proposed/",
    "nodes/active/",
    "nodes/blocked/",
    "nodes/resolved/",
    "Markdown is the durable, human-visible authority",
    "Obsidian-compatible",
    "installed `braintree` command",
    "workers read or write SQLite directly",
    "braintree index [nodes]",
    "FTS data from Markdown",
    "authoritative only for local operational coordination",
    "braintree allocate PREFIX",
    "braintree claim NODE AGENT",
    "braintree hash NODE",
    "SHA-256 hex digest of the node file's raw UTF-8 bytes",
    "frontmatter included",
    "Loss of the database may lose claims and indexes",
    "`braintree init` then `braintree index`",
    "one host and a local filesystem",
    "network-mounted",
    "PostgreSQL",
    "stationary-path/status-in-database migration is deferred",
    "context_rev",
    "not an edit counter",
)

_ADMISSION_CONTRACT: tuple[str, ...] = (
    "Admit a node only when",
    "future decision or action",
    "tool-call logs",
    "routine narration or",
    "duplicate source material",
    "Prefer updating the existing node",
    "independently resumable outcome, blocker, dependency,",
    "Independent resumability is\nnecessary but not sufficient",
    "materially reduce future resumption cost",
    "Agent boundaries, exclusive write-set",
    "failed checks, incidental or mechanical cleanup, routine",
    "verification, and handoffs alone never qualify",
    "A fresh worker may continue the same graph\n"
    "node; agents and nodes are not one-to-one",
)

_PARALLEL_CONTRACT: tuple[str, ...] = (
    "advisory navigation, never a work claim",
    "coordinator assigns each worker a direct node path and an exclusive write set",
    "One agent writes a node and its status path at a time",
    "Shared parents, `index-map.md`, definitions, and root hubs are coordinator-owned",
    "explicitly serialized",
    "A worktree is a snapshot, not global truth",
    "alone resolves a coordinating parent after all required child work is integrated",
    "Coordinator preallocation",
    "explicitly disjoint numeric ranges",
    "checks for an existing collision only; it is never an ID reservation",
    "`braintree allocate PREFIX` to atomically reserve an ID",
    "Branch-local `owner` or claim metadata is insufficient",
    "worker records the integration base and its assigned node path and write set",
    "hashes its starting Markdown node with `braintree hash`, and claims it with `braintree claim`",
    "then release the matching claim",
    "A worktree slice is not a node boundary: a fresh worker may continue the assigned node",
    "content update and its status move coherent in one commit or handoff bundle",
    "verify every changed, created, and moved path remains in that assigned write set",
    "Report the base, touched paths, created paths, moved paths, dependency evidence, "
    "and test evidence",
    "coordinator integrates worker branches one at a time",
    "Never blindly auto-merge an upstream change to the assigned node or divergent status paths",
    "manual semantic reconciliation",
    _GRAPH_CHECK_COMMAND,
    "exact `rg -n -F 'Depends on [[ID]] at context_rev '` searches",
    "reconcile stale consumers before their dependent execution",
    "only after its required child evidence has been integrated",
)

_CANONICAL_CONTRACT: tuple[str, ...] = (
    "Store each relationship in one canonical direction",
    "put `Parent` on the child",
    "do not store them as reciprocal edges",
    "exactly one primary",
    "orphan",
    "Decompose just in time",
    "independently resumable",
    "verification boundary that also retains durable execution-memory value",
    "one concrete frontier action",
    "one wikilinked direct child",
    "Roll up from evidence",
    "resolving children alone does not complete the parent",
    "A `DEC` node records a settled choice",
    "resolved `DEF` or `DEC` is current knowledge",
    "A settled `DEF` or `DEC` is `resolved`",
    "`braintree check` reports a pinned dependency whose target is "
    "`proposed`, `active`, or `blocked`",
    "`--allow-stale` does not relax that check",
    "The bump commit shape:",
    "commit the semantic `context_rev` bump with the bumped node alone",
    "sanctioned staged-staleness gate `braintree check --allow-stale nodes`",
    "still rejects a missing or malformed pin",
    "relaxes only the revision equality",
    "Reconciliation is separate work",
    "reset the pin to the current `context_rev`",
    "before that consumer executes",
    "When the frontier is a knowledge node (`THO`/`DEF`/`DEC`)",
    "answer the question and resolve it like any other frontier node",
    "advance the coordinating parent's `next` to the next deliberate frontier child",
    "leave its `context_rev` unchanged because `next` is navigation",
    "Advancing a coordinating parent's `next` after its frontier child is resolved "
    "is part of that resolution rather than bookkeeping",
    "refresh the parent's `updated` and leave its `context_rev` unchanged, "
    "because `next` is navigation",
)

_FEEDBACK_CONTRACT: tuple[str, ...] = (
    "## Feedback nodes",
    "records Braintree friction as an `FBK` node",
    "The `FBK` type is the one feedback marker",
    "find nodes -name 'FBK-*.md'",
    "from Markdown alone, with no sidecar, network, or write to the scanned vault",
    "`FBK-<n>-<slug>.md`",
    "braintree_revision:",
    "braintree_revision: 0.5.0+g1b58d57",
    "braintree_revision: unknown",
    "Read the revision to record with `braintree --version`",
    "generated `installed-revision` stamp",
    "`<version>+g<short-sha>`",
    "`<version>+unknown`",
    "Treat the public `<version>` as the compatibility signal",
    "`+g<short-sha>` as provenance",
    "never resolve the source revision against the remote",
    "one `# Feedback` section",
    "an `Attempted:`, a `Friction:`, and an `Improvement:` line",
    "`braintree check` rejects an `FBK` node that omits or malforms `braintree_revision`",
    "Record feedback with the writing half of the mechanism",
    "`braintree feedback record`",
    "allocates the next `FBK` id from Markdown",
    "routes the node to the vault's root hub",
    "degrades explicitly to `<version>+unknown` when no record is present",
    "valid, routed `FBK` node that `braintree check` accepts",
    "read-only `braintree feedback scan` command over one or more vault roots",
    "feedback: 0 nodes",
    "no sidecar or network",
    "Triage each scanned result into this graph",
    "cite the feedback id and revision in the admitted node",
    "dispose the result explicitly rather than dropping it silently",
)


_MECHANICAL_COMMIT_CONTRACT: tuple[str, ...] = (
    "mechanical change with no independently resumable outcome",
    "enclosing node's `next` or result",
    "`Refs:` footer",
)

_ABSENT_CONTRACT: tuple[str, ...] = (
    "stationary node metadata",
    "sequence ledger",
    "vault-wide revision",
    "increment it on every write",
)

# The unified `braintree` command must hide the implementation: no documented
# surface may name the runtime, toolchain, package layout, or internal command
# names.
_IMPLEMENTATION_LEAKS: tuple[str, ...] = (
    "uv run",
    "--frozen",
    "pyproject",
    "uv.lock",
    "python",
    "Python",
    ".venv",
    "graph-check",
    "feedback-scan",
    "feedback-record",
    ".agents/skills",
    ".claude/skills",
    ".pi/skills",
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


_FRONTIER_RECIPE = re.compile(r"^- Frontier: `([^`]+)`$", re.MULTILINE)


def _frontier_recipe() -> str:
    match = _FRONTIER_RECIPE.search(_read(_INDEX))
    assert match is not None, "index-map.md lacks a Frontier query recipe"
    return match.group(1)


def _run_frontier_recipe(root: Path) -> set[str]:
    result = subprocess.run(
        ["sh", "-c", _frontier_recipe()],
        cwd=root,
        capture_output=True,
        text=True,
        check=True,
    )
    return set(result.stdout.split())


def _frontmatter(text: str) -> str:
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    assert match is not None
    return match.group(1)


def _assert_present(text: str, substrings: tuple[str, ...]) -> None:
    missing = [value for value in substrings if value not in text]
    assert not missing, f"missing contract text: {missing!r}"


def _assert_absent(text: str, substrings: tuple[str, ...]) -> None:
    present = [value for value in substrings if value in text]
    assert not present, f"obsolete contract text survived: {present!r}"


def test_skill_frontmatter_and_hybrid_contract() -> None:
    text = _read(_SKILL)
    assert text.startswith("---\n")
    header = _frontmatter(text)
    assert re.search(r"^name: braintree$", header, re.MULTILINE)
    assert re.search(r"^description: .+", header, re.MULTILINE)
    _assert_present(text, _HYBRID_CONTRACT)
    _assert_absent(text, _ABSENT_CONTRACT)


def test_documented_surfaces_hide_the_implementation() -> None:
    for path in (_SKILL, _AGENTS, _ROOT / "README.md"):
        text = _read(path)
        leaks = [value for value in _IMPLEMENTATION_LEAKS if value in text]
        assert not leaks, f"{path.name} leaks implementation detail: {leaks!r}"


def test_skill_admission_and_parallel_contract() -> None:
    text = _read(_SKILL)
    _assert_present(text, _ADMISSION_CONTRACT)
    _assert_present(text, _PARALLEL_CONTRACT)


def test_mechanical_change_commit_path() -> None:
    for path in (_SKILL, _AGENTS):
        _assert_present(_read(path), _MECHANICAL_COMMIT_CONTRACT)


def test_live_vault_passes_graph_check() -> None:
    assert graph_check.main([str(_NODES)]) == 0


def test_skill_canonical_edge_and_lifecycle_contract() -> None:
    text = _read(_SKILL)
    _assert_present(text, _CANONICAL_CONTRACT)


def test_skill_feedback_contract() -> None:
    text = _read(_SKILL)
    _assert_present(text, _FEEDBACK_CONTRACT)


def test_index_is_routing_not_a_catalog() -> None:
    index = _read(_INDEX)
    assert not re.search(r"^\| .*\[\[", index, re.MULTILINE)
    assert "not copied node state" in index
    assert re.search(r"Indexes \[\[", index)
    hubs = re.findall(r"^\s*- Indexes \[\[([^\]]+)\]\]", index, re.MULTILINE)
    assert hubs
    for hub in hubs:
        assert re.match(r"IDX-\d+", hub)
        hub_text = _read(_NODES / "resolved" / f"{hub}.md")
        assert not re.search(r"^(?:Parent|Area) \[\[", hub_text, re.MULTILINE)


def _write_node(path: Path, body: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(body, encoding="utf-8")


def _task(summary: str, next_line: str) -> str:
    return (
        "---\n"
        "context_rev: 1\n"
        "updated: 2026-01-01T00:00:00Z\n"
        f"summary: {summary}\n"
        f"next: {next_line}\n"
        "---\n"
    )


def test_frontier_recipe_resolves_a_coordinating_next(tmp_path: Path) -> None:
    _write_node(
        tmp_path / "nodes/active/TAS-101-import-coordinator.md",
        _task("Coordinate import hardening.", '"[[TAS-102-validate-manifests]]"'),
    )
    _write_node(
        tmp_path / "nodes/active/TAS-102-validate-manifests.md",
        _task("Validate signed manifests.", "Run the signed-manifest validation."),
    )
    _write_node(
        tmp_path / "nodes/proposed/TAS-103-follow-up-cleanup.md",
        _task("Plan post-migration cleanup.", "Draft the cleanup plan."),
    )
    _write_node(
        tmp_path / "nodes/resolved/TAS-100-old-work.md",
        "---\ncontext_rev: 1\nupdated: 2026-01-01T00:00:00Z\nsummary: Old work.\n---\n",
    )

    frontier = _run_frontier_recipe(tmp_path)

    assert "nodes/active/TAS-102-validate-manifests.md" in frontier
    assert "nodes/proposed/TAS-103-follow-up-cleanup.md" in frontier
    assert "nodes/active/TAS-101-import-coordinator.md" not in frontier
    assert not any(path.startswith("nodes/resolved/") for path in frontier)


def test_frontier_recipe_matches_the_live_vault() -> None:
    expected: set[str] = set()
    for path in sorted(_NODES.glob("*/*.md")):
        if path.parent.name not in {"proposed", "active", "blocked"}:
            continue
        header = _frontmatter(path.read_text(encoding="utf-8"))
        next_match = re.search(r"^next:\s*(.+)$", header, re.MULTILINE)
        if next_match is not None and "[[" in next_match.group(1):
            continue
        expected.add(str(path.relative_to(_ROOT)))
    assert _run_frontier_recipe(_ROOT) == expected


def test_decomposition_roll_up() -> None:
    parent = _read(_NODES / "resolved" / "TAS-008-fit-for-purpose-hardening.md")
    child = _read(_NODES / "resolved" / "TAS-012-decomposition-rollup.md")
    admission = _read(_NODES / "resolved" / "TAS-016-actionable-admission-policy.md")
    assert "# Outcome\n" in parent
    assert "# Done when\n" in parent
    assert re.search(r"^next:", parent, re.MULTILINE) is None
    assert "# Outcome\n" in child
    assert "# Done when\n" in child
    assert "# Result\n" in child
    assert "Parent [[TAS-008-fit-for-purpose-hardening]]." in child
    assert re.search(r"^next:", admission, re.MULTILINE) is None
    assert "# Result\n" in admission
    assert "Parent [[TAS-008-fit-for-purpose-hardening]]." in admission


def test_stationary_storage_decision() -> None:
    storage = _read(_NODES / "resolved" / "TAS-017-stationary-canonical-storage.md")
    parent = _read(_NODES / "resolved" / "TAS-008-fit-for-purpose-hardening.md")
    assert re.search(r"^next:", storage, re.MULTILINE) is None
    assert "# Result\n" in storage
    assert "storage-comparison.rb" in storage
    assert "TAS-017" in parent
    assert "# Result\n" in parent


def test_decision_lifecycle() -> None:
    decision = _read(_NODES / "resolved" / "DEC-001-decision-node-convention.md")
    task = _read(_NODES / "resolved" / "TAS-013-decision-memory.md")
    for section in ("Decision", "Rationale", "Consequences"):
        assert f"# {section}\n" in decision
    assert "Parent [[TAS-013-decision-memory]]." in decision
    assert re.search(r"^disposition:", decision, re.MULTILINE) is None
    assert re.search(r"^next:", task, re.MULTILINE) is None
    assert "# Result\n" in task
