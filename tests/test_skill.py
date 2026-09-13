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
# backwards: the coordinator stamps the real host clock at handoff, not a
# rounded or estimated value, so no future `updated` is carried, and the
# worker clamps.
_COORDINATOR_HOST_CLOCK_STAMP_RULE = (
    "A coordinator stamps the host clock at handoff",
    "the real host clock time, not a rounded or estimated value",
)
_UPDATED_CLAMP_RULE = (
    "a worker refreshing an inherited `updated` ahead of the host clock uses "
    "`max(now, previous updated)` and notes the clamp rather than moving it "
    "backwards",
)

# A slice write set is the compile-and-golden closure of its change, not a
# crate directory: the worker includes and reports additional in-scope paths,
# and stops and escalates only for another node's path or a shared hub. The
# closure also names the workspace manifest and lockfile a dependency needs and
# the generated artifacts a source shape change invalidates.
_WRITE_SET_CLOSURE_RULE = (
    "write set is the compile-and-golden closure of the approved change, not a "
    "crate directory",
    "exhaustive matches and struct literals on the changed types",
    "every golden and baseline the change can invalidate (`tests/golden/**`,",
    "`baselines/**`)",
    "the workspace manifest and lockfile when the approved change needs a "
    "dependency",
    "the generated artifacts a source shape change invalidates (JSON schemas, "
    "snapshots, pinned-hash fixtures)",
    "includes and reports the additional in-scope paths",
    "stops and escalates for a path owned by another node or a shared hub",
)

# Falsification probe for the closure enumeration: the pre-change paragraph
# named only goldens and baselines, so the guard must reject it. The probe
# carries the new enumeration's forbidden tokens by their absence, and it fails
# when the guard stops detecting them rather than when the reference merely
# reflows.
_WRITE_SET_CLOSURE_PRE_CHANGE = (
    "The assigned write set is the compile-and-golden closure of the approved "
    "change, not a crate directory: membership covers every file the change must "
    "touch, including exhaustive matches and struct literals on the changed "
    "types, plus every golden and baseline the change can invalidate "
    "(`tests/golden/**`, `baselines/**`). When the closure exceeds the assigned "
    "set, the worker includes and reports the additional in-scope paths; it "
    "stops and escalates for a path owned by another node or a shared hub."
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

# An additive, optional, behavior-preserving field on a seam a resolved sibling
# owns is authored by the assigned worker when its own Done-when requires it,
# rather than escalated: the worker records the field and the affected consumer
# in its own result, stays out of the resolved node, keeps mechanical literal
# updates in the owner's tests in its own write set, and the coordinator decides
# at integration whether the owner's `context_rev` needs a bump.
_ADDITIVE_RESOLVED_SEAM_FIELD_RULE = (
    "an additive, optional, behavior-preserving field on a seam a resolved "
    "sibling owns, when the assigned node's `Done when` requires it, is "
    "authored by the assigned worker rather than escalated",
    "records the field and the affected consumer in its own",
    "does not edit the resolved node",
    "mechanical literal updates in the owner's tests stay inside the consumer's "
    "write set",
    "the coordinator decides at integration whether the owner's `context_rev` "
    "needs a bump",
)

# An internal, non-behavioral reuse change in a resolved node's module — a
# `pub(crate)` widening or helper — is authored by the assigned worker without
# escalation when it changes no artifact byte, no public API, and no behavior:
# the worker records the widened items, the reason, and the resolved owner,
# stays out of the resolved node, does not bump its `context_rev`, and prefers
# duplicating the seam over escalating when reuse would copy the spelling.
_INTERNAL_SEAM_REUSE_RULE = (
    "An internal, non-behavioral reuse change in a resolved node's module",
    "widening an item to `pub(crate)`",
    "adding a `pub(crate)` helper an existing private item delegates to",
    "authored by the assigned worker without escalation when it changes no "
    "artifact byte, no public API, and no behavior",
    "records the widened items, the reason (one spelling instead of two), and "
    "the resolved owner in its own `# Result`",
    "does not edit the resolved node and does not bump its `context_rev`, "
    "because no consumer assumption changes",
    "Visibility and `pub(crate)` factoring are not seam alterations unless a "
    "consumer outside the crate or an artifact shape changes",
    "duplicating the seam inside the new module is preferred over escalating "
    "when reuse would otherwise copy the spelling",
)

# Resolving a frontier child includes advancing the coordinating parent's
# `next`, so the resolving worker owns that edit; when the handoff's write set
# names the parent, the advance folds into the child's resolution commit, and
# when it excludes the parent the child's resolution commit completes the slice
# and the pending advance is the handoff action.
_PARENT_NEXT_OWNERSHIP_RULE = (
    "the resolving worker owns that edit",
    "A handoff whose write set names the parent — or its `next` line — folds "
    "that advance into the child's resolution commit",
    "A handoff whose write set excludes the parent cannot make that edit",
    "the child's resolution commit completes the worker's slice and the pending "
    "advance is its handoff action",
)

# The multi-writer transient — a resolved frontier child whose parent advance a
# handoff still owes — is the same Markdown as a genuine stale route, so the
# stateless checker separates them by declaration: the sanctioned
# `--allow-pending-advance PARENT` names the one pending advance, and the plain
# gate keeps failing for a genuine stale route until the coordinator advances.
_PENDING_ADVANCE_RULE = (
    "check with `braintree check --allow-pending-advance PARENT`",
    "which sanctions that declared pending advance",
    "That window is the multi-writer transient, not a failed slice",
    "a genuine stale route",
    "the plain `braintree check` flags as `next-resolved-node`",
    "the coordinator clears it at integration",
)

_PENDING_ADVANCE_REFERENCE_RULE = (
    "The window between the child's resolution and the parent's advance is the "
    "multi-writer transient",
    "the parent's `next` names an already-resolved child while its advance is "
    "still owed",
    "the failure appears the moment the child's file moves, before any commit",
    "A genuine stale route is the same Markdown with no pending advance behind it",
    "no file content separates the two: the checker is stateless",
    "therefore separates them by declaration rather than by inference",
    "sanctions exactly the one named parent whose `next` names an already-resolved "
    "child and relaxes nothing else",
    "the coordinator's integration gate is the plain",
)

# A handoff that orders reuse of an existing artifact names its concrete path — or
# the node that owns it — and a new ordered artifact has its path and format
# declared by the handoff or the node's plan: the worker reads an input instead of
# inferring a shape, and stops and asks the coordinator rather than inventing a
# referenced artifact that does not exist, because a fabricated artifact silently
# becomes the interface a downstream slice consumes.
_HANDOFF_ARTIFACT_NAMING_RULE = (
    "A handoff that orders reuse of an existing artifact names its concrete path",
    "or the node that owns it",
    "A worker that cannot resolve an ordered artifact to a path or an owning node "
    "does not invent it",
    "it stops and asks the coordinator",
    "When the ordered artifact is new, the handoff or the node's plan declares its "
    "path and format",
)

# Falsification probe for the artifact-naming rule: the pre-change handoff
# paragraph named the assigned write set and the changed, created, and moved paths
# a worker reports but stated no rule that an ordered artifact is named or that a
# worker stops rather than inventing one, so the guard must reject it. The probe
# fails when the guard stops detecting the rule rather than when the paragraph
# merely reflows.
_HANDOFF_ARTIFACT_NAMING_PROBE = (
    "Before editing, a worker records the integration base and its assigned node "
    "path and write set, hashes its starting Markdown node with `braintree hash`, "
    "and claims it with `braintree claim`. `braintree hash` takes the node's bare "
    "ID or full node name, never the path the handoff supplies, and its "
    "`content_hash` field is the bare digest passed as `--base-hash`; `claim` and "
    "`release` treat NODE as the same opaque claim key. The base hash names the "
    "node content as handed off: the node's own frontier transition — the status "
    "move and `# Context` edit — belongs to the claimed edit, not to the handoff. "
    "Before handoff, verify every changed, created, and moved path remains in that "
    "assigned write set, then release the matching claim. Report the base, touched "
    "paths, created paths, moved paths, dependency evidence, and test evidence to "
    "the coordinator."
)

# Falsification probe for the transient rule: the pre-change paragraph stated the
# stale-route definition and the ownership exception but no completion path and
# no distinction between a pending advance and a genuine stale route, so the
# widened guard must reject it. The probe fails when the guard stops detecting
# the rule rather than when the paragraph merely reflows.
_PENDING_ADVANCE_PROBE_STALE_ROUTE_PARAGRAPH = (
    "A handoff whose write set excludes the coordinating parent cannot advance "
    "its `next`. Either the handoff names the parent — or the parent's `next` "
    "line — in the write set, so the resolving worker owns the advance, or the "
    "coordinator owns the advance and the worker reports the stale route as its "
    "handoff action instead of editing outside its set. A stale route is an "
    "unfinished coordinating node whose `next` is a single direct-child link "
    "naming an already-resolved child; `braintree check` reports it as "
    "`next-resolved-node`."
)

# A brief that places a new artifact in an existing directory names the test
# suites that enumerate that directory before the artifact path is chosen: a
# directory-walking gate can reject a correctly authored new file, so the
# enumerating suite is a path constraint the brief surfaces, not a verification
# surprise.
_ENTERED_GATE_BRIEF_RULE = (
    "An increment brief — a node's body or a worker handoff — that places a new "
    'artifact in an existing directory carries a "gates my artifact enters" '
    "line naming the test suites that enumerate that directory",
    "before the artifact path is chosen",
    "a gate that walks a directory and asserts a property of every file in it "
    "can reject a correctly authored new file",
)

# One session records one session `FBK` node and the coordinator owns it, so
# parallel workers do not each create one: a worker reports friction in its run
# report instead of creating a node, and only the coordinator can admit the
# report as the session node, fold it into one already recorded, or dispose it.
# The one-per-session rule scopes to the orchestration session, not each run.
_SINGLE_SESSION_FEEDBACK_OWNERSHIP_RULE = (
    "One session records one session `FBK` node, and the coordinator owns it",
    "a worker that hits friction reports it in its run report",
    "the attempted action, the friction, and the improvement",
    "instead of creating a node",
    "the coordinator decides whether that report becomes the session `FBK` "
    "node, folds into one already recorded, or is disposed",
    "A worker creates an `FBK` node only when the coordinator explicitly "
    "grants it",
    "The one-per-session rule scopes to the orchestration session, not to each "
    "worker run",
    "two workers that each hit friction in one session owe one report, not two "
    "nodes",
)

# Falsification probe for the ownership rule: the feedback-node introduction
# already names the `FBK` type and how feedback is discovered but states no
# owner, so the guard must reject it. The probe fails when the guard stops
# detecting the ownership rule rather than when the reference merely reflows.
_SINGLE_SESSION_FEEDBACK_OWNERSHIP_INTRO_ONLY = (
    "A consuming project records Braintree friction as an `FBK` node. The `FBK` "
    "type is the one feedback marker, so `find .braintree -name 'FBK-*.md'` "
    "discovers feedback from Markdown alone, with no sidecar, network, or write "
    "to the scanned vault."
)

# Proving the absence of a branch on a named mode or scenario accepts a
# checked-in source-text guard over the module when it is paired with a
# falsification probe, and it names the exact tokens it forbids and the
# modules it covers.
_NEGATIVE_ASSERTION_RULE = (
    "a checked-in source-text guard over the module is an acceptable negative "
    "assertion when it is paired with a falsification probe",
    "a fixture source that carries the forbidden token and that the guard must "
    "reject",
    "the test fails when the guard stops detecting rather than when the "
    "forbidden token merely moves",
    "names the exact tokens it forbids and the modules it covers",
    "matches whole tokens rather than substrings",
)

# A timed-out run leaves a partial state, not a lost one: the coordinator
# inspects the partial diff and runs the tests it touches to establish whether
# the state is behavior-preserving, re-dispatches a narrow finishing brief or
# accepts a green slice on the same node instead of reverting it, reverts and
# re-scopes a non-green one, leaves the node `proposed` until the finishing
# worker resolves it, and only verifies a run that timed out after resolving and
# splitting.
_TIMED_OUT_WORKER_RECOVERY_RULE = (
    "A timed-out run leaves a partial state, not a lost one",
    "inspect it and run the tests the diff touches",
    "establish whether that partial state is behavior-preserving",
    "re-dispatch a narrow finishing brief for the remaining slice",
    "accept the coherent slice on the same node instead of reverting it",
    "revert it and re-scope the remaining slice against the reverted base",
    "The node stays `proposed` until the finishing worker resolves it",
    "needs only coordinator verification",
)

# Falsification probe for the recovery procedure: the completion-receipt
# paragraph already names a timed-out run but states no recovery procedure, so
# the guard must reject it. The probe fails when the guard stops detecting the
# procedure rather than when the reference merely reflows.
_TIMED_OUT_WORKER_RECOVERY_SIGNAL_ONLY = (
    "A worker records a compact structured completion receipt before its long "
    "narrative report: the recorded base hash, the `release` result, a gate "
    "summary, and the commit SHAs. A `release` result at the recorded base hash "
    "is the completion signal the coordinator trusts over the run status: when a "
    "run times out while the worker is still composing prose, that release "
    "states the work is finished even though the run reported failure."
)

# A status move and the node's body edit belong in one commit: `git mv` can
# stage the pre-edit blob, so the destination is `git add`-ed after the move,
# and the move is the last step before committing that node.
_STATUS_MOVE_STAGING_RULE = (
    "Stage that move and the node's `# Result`/`# Resolution` body edit in the "
    "same commit",
    "`git mv` can stage the pre-edit blob",
    "`git add` the destination after the move",
    "make the move the last step before committing that node",
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

# In a warnings-as-errors workspace a type or trait landed before its consumer
# fails the dead-code gate, so a just-in-time slice is not independently
# acceptable: the slice includes a live consumer, or the node's `next` names
# that consumer as a mandatory companion.
_JUST_IN_TIME_LIVE_CONSUMER_RULE = (
    "A just-in-time slice in a warnings-as-errors workspace is not independently "
    "acceptable when it lands a type or trait before its consumer",
    "the slice includes a live consumer",
    "or the node's `next` names that consumer as a mandatory companion",
)

# `braintree allocate` advances a counter that never rewinds, so an allocation
# the caller discards is burned permanently and no contract may leave that id
# invisible: the reference states the burn, the read-only `braintree status`
# listing that names the burned ids, and the no-reclaim rationale.
_ALLOCATION_BURN_RULE = (
    "An allocated id is burned permanently",
    "an allocation the caller discards is never returned and never reused",
    "`braintree reservations` lists each prefix's burned ids",
    "reserved with no node on disk",
    "so a gap in the vault is a discarded allocation, not a missing node",
    "There is no release or reclaim",
)

# Falsification probe for the burn rule: the pre-change reference names the
# allocate reservation but states no burn, visibility, or reclaim rule, so the
# guard must reject it. The probe fails when the guard stops detecting the rule
# rather than when the allocate bullet merely reflows.
_ALLOCATION_BURN_SIGNAL_ONLY = (
    "For parallel creation, use `braintree allocate PREFIX` to atomically reserve "
    "an ID; Coordinator preallocation or explicitly disjoint numeric ranges are "
    "valid offline alternatives. A local `find` checks for an existing collision "
    "only; it is never an ID reservation."
)

# The burn rule must also survive in the always-loaded core, not only the
# reference, because a worker reads the mutation rules before any coordination
# reference.
_ALLOCATION_BURN_CORE_RULE = (
    "A discarded `braintree allocate` burns its id permanently",
    "there is no release or reclaim",
    "`braintree reservations` lists each prefix's reserved-but-unwritten ids",
)

# A recorded premise or `# Outcome` statement the code contradicts is a
# factual correction, not a scope change: the worker records the corrected state
# and its evidence in `# Result`, bumps `context_rev` only when a pinned consumer
# relied on the premise, and escalates only when the correction would change the
# declared scope, outcome, or `Done when`. A repeated wrong premise in the
# coordinating parent is corrected by the coordinator, which owns the shared
# parent, so the finding worker never edits outside its own node.
_PREMISE_CORRECTION_RULE = (
    "A recorded premise or `# Outcome` statement that the code contradicts is a "
    "factual correction, not a scope change",
    "record the corrected state and the evidence that shows it in `# Result`",
    "bump `context_rev` only when a pinned consumer relied on the premise",
    "Escalate instead of correcting when the correction would change the "
    "declared scope, outcome, or `Done when`",
    "the worker that found it reports the correction with evidence",
    "the coordinator, which owns the shared parent, edits the parent",
)

# Falsification probe for the premise-correction rule: read-and-execute step 5
# already names the evidence, `context_rev`, and `updated` a worker writes but
# states no rule for a contradicted premise, so the guard must reject it. The
# probe fails when the guard stops detecting the rule rather than when the loop
# step merely reflows.
_PREMISE_CORRECTION_PROBE_STEP_ONLY = (
    "Execute the smallest coherent unit and update summary, `next`, evidence, "
    "status, `context_rev`, and `updated`."
)

# An action-sentence `next` may carry no wikilink; the checker names the token it
# treated as the frontier route instead of leaving the offending link to be found
# by trial.
_NEXT_ACTION_NO_WIKILINK_RULE = (
    "A `next` written as an action sentence must contain no wikilink",
    "`braintree check` names the token it treated as the frontier route",
)

# Falsification probe for the no-wikilink rule: the pre-change sentence named
# the accepted `next` forms but never forbade a wikilink inside an action
# sentence, so the guard must reject it. The probe fails when the guard stops
# detecting the rule rather than when the sentence merely reflows.
_NEXT_ACTION_NO_WIKILINK_PROBE = (
    "A node's `next` is the one deliberate frontier route: the only accepted "
    "forms are a plain action sentence, `Do X.`, or a single `[[direct-child]]` "
    "link."
)

# The dependency search recipes anchor to the start of an authored pin or gate
# line rather than the command text where a node or the reference quotes it, so a
# zero-consumer reading needs no inspection; the self-match hazard is stated.
_ANCHORED_DEPENDENCY_SEARCH_RULE = (
    "line-anchored",
    "^Gated on \\[\\[DEF-auth-protocol\\]\\]",
    "^Depends on \\[\\[[^]]+\\]\\] at context_rev [0-9]+\\.",
    "not the command text where",
)

# Falsification probe for the anchored recipe: the pre-change recipes used a
# literal `-F` search for the command text, which self-matches the quote, so the
# guard must reject it. It fails when the guard stops detecting the anchor rather
# than when the recipe merely reflows.
_ANCHORED_DEPENDENCY_SEARCH_PROBE = (
    "`rg -n -F 'Depends on [[ID]] at context_rev '` searches for every "
    "context-bearing dependency"
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
        "A stale route is an unfinished coordinating node whose `next` is a single "
        "direct-child link naming an already-resolved child",
        "`braintree check` reports it as `next-resolved-node`",
        "The window between the child's resolution and the parent's advance is the "
        "multi-writer transient",
        "The sanction never clears the advance",
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
    ("reservations",),
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


def test_just_in_time_slice_includes_or_names_a_live_consumer() -> None:
    _assert_contains(_read(_SKILL), _JUST_IN_TIME_LIVE_CONSUMER_RULE)


def test_allocation_burn_and_visibility_are_stated() -> None:
    _assert_contains(_reference("coordination"), _ALLOCATION_BURN_RULE)
    _assert_contains(_read(_SKILL), _ALLOCATION_BURN_CORE_RULE)


def test_allocation_burn_guard_rejects_the_reservation_signal_alone() -> None:
    """Falsification probe: the guard must reject a reservation with no burn rule."""
    with pytest.raises(AssertionError):
        _assert_contains(_ALLOCATION_BURN_SIGNAL_ONLY, _ALLOCATION_BURN_RULE)


def test_premise_correction_rule_is_stated() -> None:
    _assert_contains(_read(_SKILL), _PREMISE_CORRECTION_RULE)


def test_premise_correction_guard_rejects_the_loop_step_alone() -> None:
    """Falsification probe: the guard must reject a step with no correction rule."""
    with pytest.raises(AssertionError):
        _assert_contains(_PREMISE_CORRECTION_PROBE_STEP_ONLY, _PREMISE_CORRECTION_RULE)


def test_action_sentence_next_forbids_a_wikilink() -> None:
    _assert_contains(_read(_SKILL), _NEXT_ACTION_NO_WIKILINK_RULE)


def test_no_wikilink_guard_rejects_the_pre_change_accepted_forms() -> None:
    """Falsification probe: the guard must reject the accepted-forms sentence."""
    with pytest.raises(AssertionError):
        _assert_contains(_NEXT_ACTION_NO_WIKILINK_PROBE, _NEXT_ACTION_NO_WIKILINK_RULE)


def test_dependency_search_recipes_are_line_anchored() -> None:
    surface = _reference("dependencies") + _reference("coordination")
    _assert_contains(surface, _ANCHORED_DEPENDENCY_SEARCH_RULE)


def test_anchored_recipe_guard_rejects_the_unanchored_command() -> None:
    """Falsification probe: the guard must reject an unanchored `-F` recipe."""
    with pytest.raises(AssertionError):
        _assert_contains(
            _ANCHORED_DEPENDENCY_SEARCH_PROBE, _ANCHORED_DEPENDENCY_SEARCH_RULE
        )


def test_updated_ahead_of_the_host_clock_is_clamped() -> None:
    _assert_contains(_read(_SKILL), _UPDATED_CLAMP_RULE)


def test_coordinator_stamps_the_host_clock_at_handoff() -> None:
    _assert_contains(_read(_SKILL), _COORDINATOR_HOST_CLOCK_STAMP_RULE)


def test_write_set_is_the_change_closure() -> None:
    _assert_contains(_reference("coordination"), _WRITE_SET_CLOSURE_RULE)


def test_write_set_closure_guard_rejects_the_pre_change_enumeration() -> None:
    """Falsification probe: the guard must reject the pre-change closure."""
    with pytest.raises(AssertionError):
        _assert_contains(_WRITE_SET_CLOSURE_PRE_CHANGE, _WRITE_SET_CLOSURE_RULE)


def test_completion_receipt_is_the_trusted_signal() -> None:
    _assert_contains(_reference("coordination"), _COMPLETION_RECEIPT_RULE)


def test_timed_out_worker_recovery_procedure_is_stated() -> None:
    _assert_contains(_reference("coordination"), _TIMED_OUT_WORKER_RECOVERY_RULE)


def test_timed_out_worker_recovery_guard_rejects_the_timeout_signal_alone() -> None:
    """Falsification probe: the guard must reject a timeout signal with no procedure."""
    with pytest.raises(AssertionError):
        _assert_contains(
            _TIMED_OUT_WORKER_RECOVERY_SIGNAL_ONLY, _TIMED_OUT_WORKER_RECOVERY_RULE
        )


def test_additive_field_on_a_resolved_seam_is_authored_by_the_consumer() -> None:
    _assert_contains(_reference("coordination"), _ADDITIVE_RESOLVED_SEAM_FIELD_RULE)


def test_internal_reuse_of_a_resolved_seam_is_authored_by_the_consumer() -> None:
    _assert_contains(_reference("coordination"), _INTERNAL_SEAM_REUSE_RULE)


def test_parent_next_advance_names_the_write_set_exception() -> None:
    _assert_contains(_read(_SKILL), _PARENT_NEXT_OWNERSHIP_RULE)


def test_handoff_names_a_referenced_artifact() -> None:
    _assert_contains(_reference("coordination"), _HANDOFF_ARTIFACT_NAMING_RULE)


def test_artifact_naming_guard_rejects_the_handoff_protocol_alone() -> None:
    """Falsification probe: the guard must reject a handoff protocol with no rule."""
    with pytest.raises(AssertionError):
        _assert_contains(
            _HANDOFF_ARTIFACT_NAMING_PROBE, _HANDOFF_ARTIFACT_NAMING_RULE
        )


def test_pending_advance_transient_is_stated() -> None:
    _assert_contains(_read(_SKILL), _PENDING_ADVANCE_RULE)
    _assert_contains(_reference("coordination"), _PENDING_ADVANCE_REFERENCE_RULE)


def test_pending_advance_guard_rejects_the_pre_change_stale_route_paragraph() -> None:
    """Falsification probe: the guard must reject the pre-change paragraph."""
    with pytest.raises(AssertionError):
        _assert_contains(
            _PENDING_ADVANCE_PROBE_STALE_ROUTE_PARAGRAPH,
            _PENDING_ADVANCE_REFERENCE_RULE,
        )


def test_status_move_is_staged_with_its_body_edit() -> None:
    _assert_contains(_read(_SKILL), _STATUS_MOVE_STAGING_RULE)


def test_readme_keeps_the_durable_outcome_boundary() -> None:
    _assert_contains(_read(_README), _README_BOUNDARY)
    _assert_absent(_read(_README), _SIZING_COMMAND_ABSENT)


def test_negative_assertion_names_its_probe_tokens_and_modules() -> None:
    _assert_contains(_reference("authoring"), _NEGATIVE_ASSERTION_RULE)


def test_brief_names_the_gates_an_entered_directory_enumerates() -> None:
    _assert_contains(_reference("authoring"), _ENTERED_GATE_BRIEF_RULE)


def test_single_session_feedback_node_is_coordinator_owned() -> None:
    _assert_contains(_reference("authoring"), _SINGLE_SESSION_FEEDBACK_OWNERSHIP_RULE)


def test_single_session_feedback_ownership_guard_rejects_the_intro_alone() -> None:
    """Falsification probe: the guard must reject an intro with no owner."""
    with pytest.raises(AssertionError):
        _assert_contains(
            _SINGLE_SESSION_FEEDBACK_OWNERSHIP_INTRO_ONLY,
            _SINGLE_SESSION_FEEDBACK_OWNERSHIP_RULE,
        )


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
