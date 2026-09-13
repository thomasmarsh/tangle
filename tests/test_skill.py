"""Contract tests for the Braintree skill surfaces and the live execution graph.

The skill ships one concise core (``SKILL.md``) plus canonical topical
references under ``references/``. These tests lock the literal grammar the graph
checker and clients genuinely depend on, and replace broad prose-fragment locks
with observable routing and behavioral invariants: the core routes to a topic,
each topic loads as its installed Markdown, every public verb answers
``--help``, and the core stays measurably smaller than the pre-split file.
"""

from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

from braintree import graph_check, main

_ROOT = Path(__file__).resolve().parents[1]
_SKILL = _ROOT / "SKILL.md"
_AGENTS = _ROOT / "AGENTS.md"
_README = _ROOT / "README.md"
_REFERENCES = _ROOT / "references"
_NODES = _ROOT / ".braintree"
_INDEX = _NODES / "index-map.md"

# The three conditional workflows the core routes to. Each name is both a
# ``braintree help`` topic and a canonical installed Markdown file.
_TOPICS = ("coordination", "dependencies", "authoring")

# The compact baseline this refactor must approach; the pre-split file measured
# 30,244 bytes. The bound keeps the core concise while allowing correct prose.
_CORE_SIZE_BOUND = 16_000

# A single routing instruction the core must always carry: load the reference a
# conditional workflow needs, and read the same Markdown through the command.
_CORE_ROUTING = (
    "Read the topical reference named below before the first conditional workflow",
    "`braintree help TOPIC` prints the same installed Markdown",
    "Load only the reference the current operation requires",
    "braintree <verb> --help",
)

# The invariants an agent must have before acting, kept in the core rather than
# a reference: authority, vault shape, admission, the durable-outcome boundary,
# status meaning, reachability, and mutation rules.
_CORE_INVARIANTS = (
    "Markdown is the durable, human-visible authority",
    "Obsidian-compatible",
    "Each node lives in exactly one fixed status directory",
    "Admit a node only when its conclusion or executable state is likely to change",
    "Independent resumability is necessary but not sufficient",
    "A fresh worker may continue the same graph node; agents and nodes are not one-to-one",
    "Change status by moving the unchanged filename between those directories",
    "the only accepted forms are a plain action sentence, `Do X.`, or a single "
    "`[[direct-child]]` link",
    "Every other node has exactly one primary, unpinned `Parent` or `Area` link",
    "keep only the candidate its coordinating parent's `next` route names",
    "Confirm each pinned dependency is `resolved` before executing",
    "Graph bookkeeping never broadens authorization",
)

# An inherited `updated` ahead of the host clock must not move the field
# backwards: the coordinator stamps real UTC at handoff and the worker clamps.
_UPDATED_CLAMP_RULE = (
    "A coordinator stamps the real UTC time at handoff",
    "a worker refreshing an inherited `updated` ahead of the host clock uses "
    "`max(now, previous updated)` and notes the clamp rather than moving it "
    "backwards",
)

# A slice write set is the compile-and-golden closure of its change, not a
# crate directory: the worker includes and reports additional in-scope paths,
# and stops and escalates only for another node's path or a shared hub.
_WRITE_SET_CLOSURE_RULE = (
    "write set is the compile-and-golden closure of the approved change, not a "
    "crate directory",
    "exhaustive matches and struct literals on the changed types",
    "every golden and baseline the change can invalidate (`tests/golden/**`,",
    "`baselines/**`)",
    "includes and reports the additional in-scope paths",
    "stops and escalates for a path owned by another node or a shared hub",
)

# A worker records a compact completion receipt before its long narrative
# report, and a `release` result at the recorded base hash is the completion
# signal the coordinator trusts over the run status when a run times out while
# the worker is still composing prose.
_COMPLETION_RECEIPT_RULE = (
    "records a compact structured completion receipt before its long "
    "narrative report",
    "the recorded base hash, the `release` result, a gate summary, and the "
    "commit SHAs",
    "A `release` result at the recorded base hash is the completion signal the "
    "coordinator trusts over the run status",
    "when a run times out while the worker is still composing prose",
)

# The durable-outcome boundary rule the admission decision added; it must not
# regress out of the always-loaded core.
_DURABLE_OUTCOME_BOUNDARY = (
    "One node owns one durable outcome or decision",
    "not an estimated session, commit, agent assignment, or amount of code",
    "one node may span sessions, and one session may advance several frontier nodes",
    "Reassess a boundary when execution reveals new evidence",
    "split when execution reveals another outcome that can be accepted, verified,",
    "retains durable execution-memory value",
    "consolidate adjacent nodes when they share one outcome, completion evidence,",
    "no checker or command claims semantic authority over scope",
)

_README_BOUNDARY = (
    "One node owns one durable outcome or decision",
    "one node may span sessions and one session may advance several nodes",
    "Reassess that boundary only when execution reveals evidence",
    "never merely because a session ended, an agent changed, several commits landed",
    "no checker or command has semantic authority over scope",
)

# Literal grammar the graph checker and clients genuinely depend on. Each token
# is emitted or parsed, not narrative: status directories, canonical edges, the
# pin and gate forms, frontmatter keys, and the ``Refs:`` footer convention.
_REQUIRED_GRAMMAR = (
    ".braintree/proposed/",
    ".braintree/active/",
    ".braintree/blocked/",
    ".braintree/resolved/",
    "Depends on [[DEF-auth-protocol]] at context_rev 7.",
    "Gated on [[DEF-auth-protocol]].",
    "Parent [[",
    "Area [[IDX-",
    "Superseded by [[",
    "Refs:",
    "context_rev",
    "updated",
    "summary",
    "braintree_revision:",
)

# The boundary rule is evidence-driven, so no mandatory per-node sizing command
# is documented on any surface.
_SIZING_COMMAND_ABSENT = (
    "braintree size",
    "braintree scope",
)

# Each reference must carry the working rules for its topic rather than only a
# heading. These are the load-bearing rules, not broad prose locks.
_TOPIC_RULES: dict[str, tuple[str, ...]] = {
    "coordination": (
        "they treat NODE as the opaque claim key",
        "A lease lasts 900 seconds by default",
        "release` distinguishes a lapsed matching lease (`expired`)",
        "coordinator assigns each worker a direct node path and an exclusive write set",
        "the coordinator alone performs a coordinating parent's resolving edit",
        "have workers read or write SQLite directly",
        "it refuses a network-mounted location unless overridden",
    ),
    "dependencies": (
        "The pin must terminate its line",
        "record it as a gate instead of a context edge",
        "never pin the gate",
        "`braintree check --allow-stale`",
        "Reconciliation is separate work owned by each consumer",
        "Supersede only when the outcome moves to a different node",
        "never rewrite, amend, or force-push the earlier commit",
    ),
    "authoring": (
        "braintree node record",
        "allocates the next id from Markdown",
        "The `FBK` type is the one feedback marker",
        "an `Attempted:`, a `Friction:`, and an `Improvement:` line",
        "`.braintree/index-map.md` holds intent and routing, not state",
        "Decompose just in time",
        "Roll up from evidence, not child counts",
    ),
}

_ABSENT_CONTRACT = (
    "stationary node metadata",
    "sequence ledger",
    "vault-wide revision",
    "increment it on every write",
)

# The unified `braintree` command must hide the implementation: no installed
# surface may name the runtime, toolchain, package layout, or internal commands.
_IMPLEMENTATION_LEAKS = (
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

# Every public verb, as the argv prefix a caller types before `--help`.
_PUBLIC_VERBS: tuple[tuple[str, ...], ...] = (
    ("status",),
    ("location",),
    ("init",),
    ("allocate",),
    ("claim",),
    ("release",),
    ("index",),
    ("search",),
    ("similar",),
    ("backlinks",),
    ("hash",),
    ("stale",),
    ("frontier",),
    ("node",),
    ("node", "record"),
    ("impact",),
    ("orient",),
    ("next",),
    ("clusters",),
    ("digest",),
    ("reconcile",),
    ("check",),
    ("semantic",),
    ("semantic", "embed"),
    ("feedback",),
    ("feedback", "scan"),
    ("feedback", "record"),
    ("benchmark",),
    ("benchmark", "token"),
    ("benchmark", "behavioral"),
    ("benchmark", "storage"),
    ("benchmark", "verbs"),
    ("benchmark", "staged"),
    ("benchmark", "embedding"),
    ("benchmark", "quality"),
    ("help",),
)


def _read(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def _normalized(text: str) -> str:
    """Collapse whitespace so a rule can be matched across line wrapping."""
    return re.sub(r"\s+", " ", text)


def _assert_contains(text: str, substrings: tuple[str, ...]) -> None:
    haystack = _normalized(text)
    missing = [value for value in substrings if _normalized(value) not in haystack]
    assert not missing, f"missing contract text: {missing!r}"


def _assert_absent(text: str, substrings: tuple[str, ...]) -> None:
    present = [value for value in substrings if value in text]
    assert not present, f"obsolete contract text survived: {present!r}"


def _reference(topic: str) -> str:
    return _read(_REFERENCES / f"{topic}.md")


def _frontmatter(text: str) -> str:
    match = re.match(r"^---\n(.*?)\n---\n", text, re.DOTALL)
    assert match is not None
    return match.group(1)


def test_skill_core_frontmatter_and_authority() -> None:
    text = _read(_SKILL)
    assert text.startswith("---\n")
    header = _frontmatter(text)
    assert re.search(r"^name: braintree$", header, re.MULTILINE)
    assert re.search(r"^description: .+", header, re.MULTILINE)
    _assert_absent(text, _ABSENT_CONTRACT)


def test_documented_surfaces_hide_the_implementation() -> None:
    surfaces = [_SKILL, _AGENTS, _README, *sorted(_REFERENCES.glob("*.md"))]
    for path in surfaces:
        text = _read(path)
        leaks = [value for value in _IMPLEMENTATION_LEAKS if value in text]
        assert not leaks, f"{path.name} leaks implementation detail: {leaks!r}"


def test_core_stays_concise() -> None:
    size = len(_SKILL.read_bytes())
    assert size < _CORE_SIZE_BOUND, f"SKILL.md grew to {size} bytes"


def test_core_keeps_the_invariants_and_routes_to_references() -> None:
    text = _read(_SKILL)
    _assert_contains(text, _CORE_ROUTING)
    _assert_contains(text, _CORE_INVARIANTS)
    for topic in _TOPICS:
        assert f"references/{topic}.md" in text
        assert f"braintree help {topic}" in text


def test_core_keeps_the_durable_outcome_boundary() -> None:
    text = _read(_SKILL)
    _assert_contains(text, _DURABLE_OUTCOME_BOUNDARY)
    _assert_absent(text, _SIZING_COMMAND_ABSENT)


def test_updated_ahead_of_the_host_clock_is_clamped() -> None:
    _assert_contains(_read(_SKILL), _UPDATED_CLAMP_RULE)


def test_write_set_is_the_change_closure() -> None:
    _assert_contains(_reference("coordination"), _WRITE_SET_CLOSURE_RULE)


def test_completion_receipt_is_the_trusted_signal() -> None:
    _assert_contains(_reference("coordination"), _COMPLETION_RECEIPT_RULE)


def test_readme_keeps_the_durable_outcome_boundary() -> None:
    _assert_contains(_read(_README), _README_BOUNDARY)
    _assert_absent(_read(_README), _SIZING_COMMAND_ABSENT)


def test_reference_topics_are_canonical() -> None:
    for topic, rules in _TOPIC_RULES.items():
        text = _reference(topic)
        assert len(text) > 1_000, f"{topic}.md is too small to be canonical prose"
        _assert_contains(text, rules)


def test_required_literal_grammar_survives() -> None:
    surface = _read(_SKILL) + "".join(_reference(topic) for topic in _TOPICS)
    _assert_contains(surface, _REQUIRED_GRAMMAR)
    _assert_absent(_read(_SKILL), _SIZING_COMMAND_ABSENT)


def test_help_topic_routes_to_the_installed_reference(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    """`braintree help TOPIC` is read-only and needs no vault or sidecar."""
    monkeypatch.chdir(tmp_path)
    monkeypatch.setenv("BT_SIDECAR_DIR", str(tmp_path / "sidecar"))
    monkeypatch.setenv("BT_PROJECT_ID", "skill-test")
    for topic in _TOPICS:
        assert main.main(["help", topic]) == 0
        assert capsys.readouterr().out == _reference(topic).rstrip("\n") + "\n"
    assert not (tmp_path / "sidecar").exists()
    assert not (tmp_path / ".braintree").exists()


def test_help_without_a_topic_lists_the_topics(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main.main(["help"]) == 0
    out = capsys.readouterr().out
    for topic in _TOPICS:
        assert f'"{topic}"' in out


def test_help_rejects_an_unknown_topic(capsys: pytest.CaptureFixture[str]) -> None:
    assert main.main(["help", "bogus"]) == 2
    out = capsys.readouterr().out
    assert 'error: "unknown help topic: bogus"' in out
    for topic in _TOPICS:
        assert topic in out


@pytest.mark.parametrize("verb", _PUBLIC_VERBS, ids=lambda verb: " ".join(verb))
def test_every_public_verb_has_bounded_help(
    verb: tuple[str, ...], capsys: pytest.CaptureFixture[str]
) -> None:
    assert main.main([*verb, "--help"]) == 0
    out = capsys.readouterr().out
    assert 'usage: "' in out, out
    assert "exits[3]{code,meaning}:" in out, out
    assert '"0"' in out and '"1"' in out and '"2"' in out, out


def test_global_help_is_the_command_and_topic_index(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert main.main(["--help"]) == 0
    out = capsys.readouterr().out
    assert "commands[" in out
    assert "topics[3]{topic,purpose}:" in out
    for topic in _TOPICS:
        assert f'"{topic}"' in out
    assert len(out) < 8_000, "global help is no longer the short index"


def test_live_vault_passes_graph_check() -> None:
    assert graph_check.main([str(_NODES)]) == 0


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


_FRONTIER_RECIPE = re.compile(r"^- Frontier: `([^`]+)`$", re.MULTILINE)
_FRONTIER_ID = re.compile(r'^\s*"([A-Z][A-Z0-9_]*-\d+)"', re.MULTILINE)
_NODE_ID = re.compile(r"^([A-Z][A-Z0-9_]*-\d+)-")


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
    return set(_FRONTIER_ID.findall(result.stdout))


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
        tmp_path / ".braintree/active/TAS-101-import-coordinator.md",
        _task("Coordinate import hardening.", '"[[TAS-102-validate-manifests]]"'),
    )
    _write_node(
        tmp_path / ".braintree/active/TAS-102-validate-manifests.md",
        _task("Validate signed manifests.", "Run the signed-manifest validation."),
    )
    _write_node(
        tmp_path / ".braintree/proposed/TAS-103-follow-up-cleanup.md",
        _task("Plan post-migration cleanup.", "Draft the cleanup plan."),
    )
    _write_node(
        tmp_path / ".braintree/resolved/TAS-100-old-work.md",
        "---\ncontext_rev: 1\nupdated: 2026-01-01T00:00:00Z\nsummary: Old work.\n---\n",
    )

    frontier = _run_frontier_recipe(tmp_path)

    assert frontier == {"TAS-102", "TAS-103"}


def test_frontier_recipe_matches_the_live_vault() -> None:
    expected: set[str] = set()
    for path in sorted(_NODES.glob("*/*.md")):
        if path.parent.name not in {"proposed", "active", "blocked"}:
            continue
        header = _frontmatter(path.read_text(encoding="utf-8"))
        next_match = re.search(r"^next:\s*(.+)$", header, re.MULTILINE)
        if next_match is not None and "[[" in next_match.group(1):
            continue
        match = _NODE_ID.match(path.name)
        assert match is not None
        expected.add(match.group(1))
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
