"""The frozen contract for the Tangle memory-evaluation program.

This module is the machine-readable half of the evaluation contract; the prose
authority is ``research/agent-memory-evaluation-contract.md``. It fixes the
literal protocol a later harness must agree on: the claim, the
reconstructibility boundary, the five causal arms, the primary and cost
endpoints, the pipeline diagnostics, the scenario families, the statistical
decision rules, the version pins, and the live-run authorization requirement.

Everything here is dependency-free. The contract, like the schema, gold corpus,
validator, and contract tests it governs, makes zero live model calls, so a
default install can read and test it offline.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass
from typing import Any

from . import token_benchmark

__all__ = [
    "ADMISSION_RULE",
    "ARMS",
    "AUTHORIZATION",
    "BOOTSTRAP_RESAMPLES",
    "CANONICAL_ARM_IDS",
    "CLAIM",
    "CONFIDENCE_LEVEL",
    "CORRECTNESS_GATE",
    "COST_METRICS",
    "CURATION_GROUPS",
    "DECISION_VERDICTS",
    "DIAGNOSTIC_LABELS",
    "INTERACTION_METRICS",
    "MEMORY_SCOPE",
    "MIN_MODELS",
    "MIN_REPETITIONS",
    "OBSERVABLE_INFORMATION",
    "OUT_OF_SCOPE",
    "PIN_FIELDS",
    "PRIMARY_ENDPOINTS",
    "PRIMARY_TARGET",
    "PROTOCOL",
    "RECONSTRUCTIBILITY_TESTS",
    "SCENARIO_FAMILIES",
    "SECONDARY_ENDPOINTS",
    "SPLITS",
    "SUPPORT_CRITERIA",
    "TOKEN_METRICS",
    "Arm",
    "Endpoint",
    "ReconstructibilityTest",
    "contract",
    "verify",
]

Json = dict[str, Any]

PROTOCOL = "memory-eval-contract-v1"

CLAIM = (
    "Selective Tangle memory improves the correctness of memory-dependent "
    "engineering actions at acceptable total interaction cost relative to "
    "repository-only, raw-history, and flat-memory baselines, and stays below "
    "an oracle that supplies the minimal gold memory."
)
PRIMARY_TARGET = "memory-dependent downstream action quality"

# What an agent may observe at query time, independent of any memory arm. The
# corpus records the frozen source revision so this boundary is reproducible.
OBSERVABLE_INFORMATION = (
    "repository contents at the frozen source revision",
    "system prompt and tool definitions",
    "current environment state",
    "tool output produced within the arm budget",
)
# The memory types in scope for the claim. Model weights and network
# architecture are out of scope by the theory question the program reassesses.
MEMORY_SCOPE = (
    "prospective task state",
    "semantic definitions and decisions",
    "reflective thoughts and feedback",
    "procedural skill text",
    "compressed episodic results",
)
OUT_OF_SCOPE = (
    "model weights and fine-tuning",
    "inference-network architecture",
    "external entitlements or credentials that no node in the vault owns",
)


@dataclass(frozen=True)
class ReconstructibilityTest:
    """One way reacquiring state can fail, and the question that decides it."""

    name: str
    question: str


# The cost-sensitive reconstructibility test. A memory is in scope when the
# needed historical state fails at least one of these tests; the broad
# admission threshold is retained rather than the absolute "never
# reconstructible" rule.
RECONSTRUCTIBILITY_TESTS = (
    ReconstructibilityTest(
        "unavailable",
        "Is the historical state absent from every currently observable source?",
    ),
    ReconstructibilityTest(
        "unreliable",
        "Would reacquisition yield a different or contradictory value?",
    ),
    ReconstructibilityTest(
        "ambiguous",
        "Does current observable state fail to identify which prior decision or "
        "definition applies?",
    ),
    ReconstructibilityTest(
        "nondeterministic",
        "Would re-deriving the state repeat a nondeterministic experiment or sampling step?",
    ),
    ReconstructibilityTest(
        "disproportionately-costly",
        "Does reacquisition cost more than the expected value of retaining the state?",
    ),
)
ADMISSION_RULE = (
    "Store decision-relevant historical state that is unavailable, unreliable, "
    "ambiguous, or disproportionately costly to reacquire; prefer a pointer or "
    "reproducible derivation when current authoritative material is cheap and "
    "sufficient."
)


@dataclass(frozen=True)
class Arm:
    """One causal condition with fixed available state and what it isolates."""

    id: str
    available_state: str
    isolates: str


# The five causal arms. Every arm gets identical fixtures, task prompts, tools,
# model settings, budgets, and graders; only the available persistent history
# differs. The oracle is an upper bound, not a competitor.
ARMS = (
    Arm(
        "repository-only",
        "current repository files, prompt, and tools, with no persistent episodic history",
        "whether the case actually requires memory",
    ),
    Arm(
        "raw-history",
        "prior public action and observation transcripts within the same retrieval budget",
        "whether selective consolidation beats recency and lexical search of full history",
    ),
    Arm(
        "flat-memory",
        "untyped timestamped notes with lexical retrieval and the same budget",
        "whether graph lifecycle and governance beat mere persistence",
    ),
    Arm(
        "tangle",
        "the graph, lifecycle, revisions, and bounded retrieval commands",
        "the system under test",
    ),
    Arm(
        "oracle",
        "only the minimal gold memory the case requires, injected directly",
        "loss attributable to memory construction and retrieval rather than reading and reasoning",
    ),
)
CANONICAL_ARM_IDS = tuple(arm.id for arm in ARMS)


@dataclass(frozen=True)
class Endpoint:
    """One measured outcome with its definition and direction of good."""

    name: str
    definition: str


# The primary endpoint decides the claim; correctness is scored before cost.
PRIMARY_ENDPOINTS = (
    Endpoint(
        "action-correctness",
        "exact or partial correctness of the required memory-dependent action, "
        "from the case grader",
    ),
)
SECONDARY_ENDPOINTS = (
    Endpoint("next-action-correct", "whether the first executed action is the acceptable one"),
    Endpoint(
        "avoidable-rework",
        "repeated or discarded work a correct memory would have prevented",
    ),
    Endpoint("repeated-failure", "recurrence of a failure the retained history already knew about"),
    Endpoint("decision-regret", "severity-weighted distance from the best acceptable action"),
    Endpoint("negative-transfer", "harm caused by applying a memory outside its valid scope"),
    Endpoint("unnecessary-action", "work performed when the correct action was to abstain"),
)

# Cost is reported alongside, never instead of, correctness. Token names mirror
# the existing token benchmark so one telemetry vocabulary spans the program.
TOKEN_METRICS = (
    "input_tokens",
    "cached_input_tokens",
    "uncached_input_tokens",
    "output_tokens",
    "reasoning_output_tokens",
    "total_tokens",
)
INTERACTION_METRICS = (
    "tool_calls",
    "shell_calls",
    "model_turns",
    "files_opened",
    "nodes_opened",
    "latency_ms",
    "monetary_cost",
)
COST_METRICS = TOKEN_METRICS + INTERACTION_METRICS

# Diagnostic labels a failure is attributed to; they are mutually
# distinguishable so a change targets the demonstrated bottleneck.
DIAGNOSTIC_LABELS = (
    "write-miss",
    "organization-error",
    "retrieval-miss",
    "stale-or-conflicting-retrieval",
    "reader-failure",
    "action-failure",
)

# The scenario families every case carries. Each belongs to exactly one
# curation group, so a later corpus is stratified and balanced by family.
SCENARIO_FAMILIES = (
    "admission",
    "resumption",
    "implicit-retrieval",
    "temporal-update",
    "cascading-invalidation",
    "conflict-and-uncertainty",
    "experience-transfer",
    "forgetting-and-interference",
    "poisoning-and-authority",
)
CURATION_GROUPS = (
    ("admission", ("admission",)),
    ("resumption-and-implicit-retrieval", ("resumption", "implicit-retrieval")),
    (
        "revision-and-conflict",
        ("temporal-update", "cascading-invalidation", "conflict-and-uncertainty"),
    ),
    (
        "transfer-interference-and-authority",
        ("experience-transfer", "forgetting-and-interference", "poisoning-and-authority"),
    ),
)

SPLITS = ("development", "held-out")
# Development is where mechanisms are iterated; held-out is frozen before a
# confirmatory run and is the only split that can confirm a claim.
EXPLORATORY_RULE = (
    "Development-split and underpowered results are exploratory only; a claim is "
    "confirmed only by a paired effect on the frozen held-out split."
)
MIN_MODELS = 3
MIN_REPETITIONS = 3
BOOTSTRAP_RESAMPLES = 10_000
CONFIDENCE_LEVEL = 0.95
CORRECTNESS_GATE = (
    "A sample enters cost summaries only after it passes its case grader and "
    "telemetry validation; correctness is decided before cost."
)
DECISION_VERDICTS = ("confirmed", "rejected", "exploratory", "untested")
SUPPORT_CRITERIA = (
    "The primary endpoint improves on held-out cases against both repository-only "
    "and raw-history, with a paired 95% confidence interval excluding zero.",
    "Total interaction cost does not regress beyond the preregistered budget.",
    "No integrity or safety endpoint (orphan, stale-pin, invalidation, poisoning, "
    "authority escalation) regresses.",
)

# Everything frozen for a comparison. A run that cannot name every pin is not a
# comparable sample.
PIN_FIELDS = (
    "protocol",
    "corpus-digest",
    "fixture-version",
    "source-revision",
    "model",
    "model-revision",
    "reasoning-effort",
    "prompt-revision",
    "tool-revision",
    "budget",
    "allowed-commands",
    "grader-version",
)
AUTHORIZATION = (
    "Live or paid model runs require explicit owner authorization recorded before "
    "execution; the contract, scenario schema, gold corpus, validator, and contract "
    "tests make zero live model calls."
)


def contract() -> Json:
    """Return the whole contract as a plain JSON-serializable document."""
    return {
        "protocol": PROTOCOL,
        "claim": CLAIM,
        "primary_target": PRIMARY_TARGET,
        "observable_information": list(OBSERVABLE_INFORMATION),
        "memory_scope": list(MEMORY_SCOPE),
        "out_of_scope": list(OUT_OF_SCOPE),
        "admission_rule": ADMISSION_RULE,
        "reconstructibility_tests": [asdict(test) for test in RECONSTRUCTIBILITY_TESTS],
        "arms": [asdict(arm) for arm in ARMS],
        "primary_endpoints": [asdict(endpoint) for endpoint in PRIMARY_ENDPOINTS],
        "secondary_endpoints": [asdict(endpoint) for endpoint in SECONDARY_ENDPOINTS],
        "cost_metrics": list(COST_METRICS),
        "diagnostic_labels": list(DIAGNOSTIC_LABELS),
        "scenario_families": list(SCENARIO_FAMILIES),
        "curation_groups": [
            {"group": group, "families": list(families)} for group, families in CURATION_GROUPS
        ],
        "splits": list(SPLITS),
        "exploratory_rule": EXPLORATORY_RULE,
        "min_models": MIN_MODELS,
        "min_repetitions": MIN_REPETITIONS,
        "bootstrap_resamples": BOOTSTRAP_RESAMPLES,
        "confidence_level": CONFIDENCE_LEVEL,
        "correctness_gate": CORRECTNESS_GATE,
        "decision_verdicts": list(DECISION_VERDICTS),
        "support_criteria": list(SUPPORT_CRITERIA),
        "pin_fields": list(PIN_FIELDS),
        "authorization": AUTHORIZATION,
    }


def _duplicates(values: tuple[str, ...]) -> list[str]:
    """Return the values that appear more than once, in first-seen order."""
    seen: set[str] = set()
    repeated: list[str] = []
    for value in values:
        if value in seen and value not in repeated:
            repeated.append(value)
        seen.add(value)
    return repeated


def verify() -> list[str]:
    """Return the internal inconsistencies that would make the contract unusable.

    This is a structural self-check, not a semantic authority: it proves the
    literal protocol is well-formed and internally consistent so contract tests
    and the later harness can import it as one source of truth.
    """
    problems: list[str] = []
    if not PROTOCOL:
        problems.append("protocol is empty")
    if not CLAIM.strip() or not PRIMARY_TARGET.strip():
        problems.append("claim and primary target must be non-empty")
    if CANONICAL_ARM_IDS != (
        "repository-only",
        "raw-history",
        "flat-memory",
        "tangle",
        "oracle",
    ):
        problems.append(f"arm ids drifted: {CANONICAL_ARM_IDS}")
    if repeated := _duplicates(CANONICAL_ARM_IDS):
        problems.append(f"duplicate arm ids: {repeated}")
    if repeated := _duplicates(tuple(test.name for test in RECONSTRUCTIBILITY_TESTS)):
        problems.append(f"duplicate reconstructibility tests: {repeated}")
    expected_tests = {
        "unavailable",
        "unreliable",
        "ambiguous",
        "nondeterministic",
        "disproportionately-costly",
    }
    if {test.name for test in RECONSTRUCTIBILITY_TESTS} != expected_tests:
        problems.append("reconstructibility tests do not cover the five categories")
    if set(TOKEN_METRICS) != {*token_benchmark.FIELDS, "uncached_input_tokens"}:
        problems.append("token metrics drifted from the token benchmark telemetry")
    for label in (
        tuple(endpoint.name for endpoint in PRIMARY_ENDPOINTS)
        + tuple(endpoint.name for endpoint in SECONDARY_ENDPOINTS)
        + COST_METRICS
        + DIAGNOSTIC_LABELS
    ):
        if not label.strip():
            problems.append("an endpoint, cost metric, or diagnostic label is empty")
    if repeated := _duplicates(DIAGNOSTIC_LABELS):
        problems.append(f"duplicate diagnostic labels: {repeated}")
    if repeated := _duplicates(SCENARIO_FAMILIES):
        problems.append(f"duplicate scenario families: {repeated}")
    grouped = [family for _, families in CURATION_GROUPS for family in families]
    if sorted(grouped) != sorted(SCENARIO_FAMILIES):
        problems.append("curation groups do not partition the scenario families")
    if len(SPLITS) != 2 or "held-out" not in SPLITS or "development" not in SPLITS:
        problems.append("splits must be exactly development and held-out")
    if MIN_MODELS < 3:
        problems.append("at least three models or model families are required")
    if MIN_REPETITIONS < 3:
        problems.append("at least three repetitions per case and model are required")
    if BOOTSTRAP_RESAMPLES < 1_000:
        problems.append("bootstrap resamples are too few for a stable interval")
    if not 0.0 < CONFIDENCE_LEVEL < 1.0:
        problems.append("confidence level must lie strictly between zero and one")
    if repeated := _duplicates(PIN_FIELDS):
        problems.append(f"duplicate version pins: {repeated}")
    return problems
