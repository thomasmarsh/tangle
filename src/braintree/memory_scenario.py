"""Versioned scenario schema and deterministic grader for the gold corpus.

This module is the scenario half of the frozen evaluation contract in
:mod:`braintree.memory_contract`. It fixes one JSON-serializable record that
every gold case must satisfy, keeps the information used to *construct* memory
strictly separate from the information visible *at query time*, and provides
the deterministic parser and grader a later harness uses to admit and score
cases.

Every literal shared with the contract is imported from
``braintree.memory_contract`` rather than restated: the nine scenario families
and their four curation groups, the development/held-out splits, the five
causal arm ids, the ``action-correctness`` primary endpoint, the
correctness-before-cost gate, and the version-pin list. The schema and its
tests make zero live model calls, so a default install validates the format
offline; a live or paid run needs the contract's recorded owner authorization
first.
"""

from __future__ import annotations

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any

from . import memory_contract

__all__ = [
    "ARM_IDS",
    "CORRECTNESS_GATE",
    "CURATION_GROUPS",
    "EPISODE_KINDS",
    "GRADER_IDS",
    "MINIMAL_SCENARIO_DOCUMENT",
    "PIN_FIELDS",
    "PRIMARY_ENDPOINT",
    "SCENARIO_FAMILIES",
    "SCENARIO_SCHEMA_VERSION",
    "SEVERITIES",
    "SEVERITY_WEIGHTS",
    "SPLITS",
    "VALID_SCHEMA_VERSIONS",
    "ArmFixture",
    "Construction",
    "Episode",
    "GoldEvidence",
    "GradeResult",
    "Grading",
    "Query",
    "Scenario",
    "ScenarioError",
    "arm_fixtures",
    "cost_eligible",
    "curation_group",
    "grade",
    "minimal_scenario",
    "parse_scenario",
    "scenario_document",
    "verify",
]

Json = dict[str, Any]

SCENARIO_SCHEMA_VERSION = "memory-scenario-v1"
VALID_SCHEMA_VERSIONS = (SCENARIO_SCHEMA_VERSION,)

# Literals owned by the frozen contract. Import them so a scenario can never
# drift from the protocol it is admitted into.
SCENARIO_FAMILIES = memory_contract.SCENARIO_FAMILIES
CURATION_GROUPS = memory_contract.CURATION_GROUPS
SPLITS = memory_contract.SPLITS
ARM_IDS = memory_contract.CANONICAL_ARM_IDS
PRIMARY_ENDPOINT = memory_contract.PRIMARY_ENDPOINTS[0].name
CORRECTNESS_GATE = memory_contract.CORRECTNESS_GATE
PIN_FIELDS = memory_contract.PIN_FIELDS

# The schema's own vocabularies. A historical episode is one typed statement;
# severity orders decision regret for the action-correctness endpoint; a grader
# id names one deterministic scoring rule.
EPISODE_KINDS = ("observation", "decision", "action", "result", "failure", "feedback")
SEVERITIES = ("minor", "moderate", "major", "critical")
SEVERITY_WEIGHTS: dict[str, float] = {
    "minor": 1.0,
    "moderate": 2.0,
    "major": 3.0,
    "critical": 5.0,
}
GRADER_IDS = ("action-exact", "action-acceptable")

_CASE_ID = re.compile(r"^[a-z0-9][a-z0-9-]*$")
_REVISION = re.compile(r"^[0-9A-Za-z._-]{4,64}$")


class ScenarioError(ValueError):
    """A scenario document is malformed, ambiguous, or unsupported."""


@dataclass(frozen=True)
class Episode:
    """One ordered piece of historical evidence used to construct memory."""

    id: str
    sequence: int
    kind: str
    statement: str
    evidence: tuple[str, ...]


@dataclass(frozen=True)
class Construction:
    """The unavailable history a memory system may write from."""

    episodes: tuple[Episode, ...]


@dataclass(frozen=True)
class Query:
    """What every causal arm sees at query time, independent of memory."""

    task: str
    observable_paths: tuple[str, ...]
    allowed_actions: tuple[str, ...]


@dataclass(frozen=True)
class GoldEvidence:
    """The minimal memory a case requires, with its source episodes."""

    id: str
    statement: str
    source_episodes: tuple[str, ...]


@dataclass(frozen=True)
class Grading:
    """The deterministic rule that scores an action and its gold evidence."""

    grader: str
    expected_outcome: str
    acceptable_actions: tuple[str, ...]
    gold_evidence: tuple[GoldEvidence, ...]


@dataclass(frozen=True)
class Scenario:
    """One versioned gold-corpus case."""

    schema_version: str
    case_id: str
    family: str
    split: str
    severity: str
    source_revision: str
    construction: Construction
    query: Query
    grading: Grading


@dataclass(frozen=True)
class GradeResult:
    """The score for one action against one scenario's primary endpoint."""

    case_id: str
    endpoint: str
    action: str
    expected_outcome: str
    correct: bool
    credit: float
    severity: str
    regret: float


@dataclass(frozen=True)
class ArmFixture:
    """The same case as seen by one causal arm.

    ``task``, ``observable_paths``, and ``allowed_actions`` are identical across
    arms; only ``construction`` (what the arm may write memory from) and
    ``memory`` (what it holds at query time) differ.
    """

    arm_id: str
    task: str
    observable_paths: tuple[str, ...]
    allowed_actions: tuple[str, ...]
    construction: tuple[str, ...]
    memory: tuple[str, ...]


def curation_group(family: str) -> str:
    """Return the curation group that owns ``family``."""
    for group, families in CURATION_GROUPS:
        if family in families:
            return group
    raise ScenarioError(f"unknown scenario family: {family}")


def _require_mapping(value: Any, where: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise ScenarioError(f"{where} must be a mapping")
    return value


def _require_list(value: Any, where: str) -> list[Any]:
    if not isinstance(value, list):
        raise ScenarioError(f"{where} must be a list")
    return value


def _require_string(value: Any, where: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ScenarioError(f"{where} must be a non-empty string")
    return value


def _require_string_list(value: Any, where: str) -> tuple[str, ...]:
    items = _require_list(value, where)
    if not items:
        raise ScenarioError(f"{where} must be non-empty")
    strings = tuple(_require_string(item, f"{where} entry") for item in items)
    if len(strings) != len(set(strings)):
        raise ScenarioError(f"{where} entries must be unique")
    return strings


def _validate_path(path: Any, where: str) -> str:
    """Return a normalized repository-relative POSIX path or reject it."""
    text = _require_string(path, where)
    if text.startswith("/") or "\\" in text or "\x00" in text:
        raise ScenarioError(f"{where} is not a repository-relative path: {text!r}")
    if any(segment in {"", ".", ".."} for segment in text.split("/")):
        raise ScenarioError(f"{where} is not a repository-relative path: {text!r}")
    return text


def _validate_paths(value: Any, where: str) -> tuple[str, ...]:
    paths = _require_string_list(value, where)
    return tuple(_validate_path(path, where) for path in paths)


def _parse_episode(raw: Any, index: int, seen_ids: set[str]) -> Episode:
    where = f"construction.episodes[{index}]"
    episode = _require_mapping(raw, where)
    episode_id = _require_string(episode.get("id"), f"{where}.id")
    if episode_id in seen_ids:
        raise ScenarioError(f"{where}.id is duplicated: {episode_id}")
    seen_ids.add(episode_id)
    sequence = episode.get("sequence")
    if not isinstance(sequence, int) or isinstance(sequence, bool) or sequence < 1:
        raise ScenarioError(f"{where}.sequence must be a positive integer")
    if sequence != index + 1:
        raise ScenarioError(f"{where}.sequence must continue the 1-based episode order")
    kind = _require_string(episode.get("kind"), f"{where}.kind")
    if kind not in EPISODE_KINDS:
        raise ScenarioError(f"{where}.kind must be one of {', '.join(EPISODE_KINDS)}")
    statement = _require_string(episode.get("statement"), f"{where}.statement")
    evidence = _validate_paths(episode.get("evidence"), f"{where}.evidence")
    return Episode(
        id=episode_id,
        sequence=sequence,
        kind=kind,
        statement=statement,
        evidence=evidence,
    )


def _parse_construction(raw: Any) -> Construction:
    construction = _require_mapping(raw, "construction")
    raw_episodes = _require_list(construction.get("episodes"), "construction.episodes")
    if not raw_episodes:
        raise ScenarioError("construction.episodes must be non-empty")
    seen_ids: set[str] = set()
    episodes = tuple(
        _parse_episode(item, index, seen_ids) for index, item in enumerate(raw_episodes)
    )
    return Construction(episodes=episodes)


def _parse_query(raw: Any) -> Query:
    query = _require_mapping(raw, "query")
    task = _require_string(query.get("task"), "query.task")
    observable_paths = _validate_paths(query.get("observable_paths"), "query.observable_paths")
    allowed_actions = _require_string_list(query.get("allowed_actions"), "query.allowed_actions")
    return Query(task=task, observable_paths=observable_paths, allowed_actions=allowed_actions)


def _parse_gold_evidence(raw: Any, index: int, episode_ids: set[str]) -> GoldEvidence:
    where = f"grading.gold_evidence[{index}]"
    evidence = _require_mapping(raw, where)
    evidence_id = _require_string(evidence.get("id"), f"{where}.id")
    statement = _require_string(evidence.get("statement"), f"{where}.statement")
    sources = _require_string_list(evidence.get("source_episodes"), f"{where}.source_episodes")
    unknown = [source for source in sources if source not in episode_ids]
    if unknown:
        raise ScenarioError(f"{where}.source_episodes reference unknown episodes: {unknown}")
    return GoldEvidence(id=evidence_id, statement=statement, source_episodes=sources)


def _parse_grading(raw: Any, allowed_actions: tuple[str, ...], episode_ids: set[str]) -> Grading:
    grading = _require_mapping(raw, "grading")
    grader = _require_string(grading.get("grader"), "grading.grader")
    if grader not in GRADER_IDS:
        raise ScenarioError(f"grading.grader must be one of {', '.join(GRADER_IDS)}")
    expected_outcome = _require_string(grading.get("expected_outcome"), "grading.expected_outcome")
    if expected_outcome not in allowed_actions:
        raise ScenarioError("grading.expected_outcome must be one of query.allowed_actions")
    raw_acceptable = grading.get("acceptable_actions", [expected_outcome])
    acceptable_actions = _require_string_list(raw_acceptable, "grading.acceptable_actions")
    if expected_outcome not in acceptable_actions:
        raise ScenarioError("grading.expected_outcome must be an acceptable action")
    outside = [action for action in acceptable_actions if action not in allowed_actions]
    if outside:
        raise ScenarioError(f"grading.acceptable_actions outside query.allowed_actions: {outside}")
    if grader == "action-exact" and acceptable_actions != (expected_outcome,):
        raise ScenarioError("action-exact grading has ambiguous acceptable outcomes")
    raw_evidence = _require_list(grading.get("gold_evidence"), "grading.gold_evidence")
    if not raw_evidence:
        raise ScenarioError("grading.gold_evidence is missing")
    gold_evidence = tuple(
        _parse_gold_evidence(item, index, episode_ids) for index, item in enumerate(raw_evidence)
    )
    evidence_ids = [evidence.id for evidence in gold_evidence]
    if len(evidence_ids) != len(set(evidence_ids)):
        raise ScenarioError("grading.gold_evidence ids must be unique")
    return Grading(
        grader=grader,
        expected_outcome=expected_outcome,
        acceptable_actions=acceptable_actions,
        gold_evidence=gold_evidence,
    )


def parse_scenario(document: Mapping[str, Any]) -> Scenario:
    """Validate and return the scenario a JSON document encodes.

    Raises :class:`ScenarioError` for an unsupported schema version, a malformed
    or ambiguous record, a missing evidence citation, or an invalid repository
    path.
    """
    version = document.get("schema_version")
    if not isinstance(version, str) or version not in VALID_SCHEMA_VERSIONS:
        raise ScenarioError(f"unsupported schema version: {version!r}")
    case_id = _require_string(document.get("case_id"), "case_id")
    if _CASE_ID.fullmatch(case_id) is None:
        raise ScenarioError(f"case_id must be a lowercase slug: {case_id!r}")
    family = _require_string(document.get("family"), "family")
    if family not in SCENARIO_FAMILIES:
        raise ScenarioError(f"unknown scenario family: {family}")
    split = _require_string(document.get("split"), "split")
    if split not in SPLITS:
        raise ScenarioError(f"split must be one of {', '.join(SPLITS)}")
    severity = _require_string(document.get("severity"), "severity")
    if severity not in SEVERITIES:
        raise ScenarioError(f"severity must be one of {', '.join(SEVERITIES)}")
    source_revision = _require_string(document.get("source_revision"), "source_revision")
    if _REVISION.fullmatch(source_revision) is None:
        raise ScenarioError(f"source_revision is not a revision: {source_revision!r}")
    construction = _parse_construction(document.get("construction"))
    query = _parse_query(document.get("query"))
    episode_ids = {episode.id for episode in construction.episodes}
    grading = _parse_grading(document.get("grading"), query.allowed_actions, episode_ids)
    return Scenario(
        schema_version=version,
        case_id=case_id,
        family=family,
        split=split,
        severity=severity,
        source_revision=source_revision,
        construction=construction,
        query=query,
        grading=grading,
    )


def scenario_document(scenario: Scenario) -> Json:
    """Return the JSON-serializable document for ``scenario``."""
    return {
        "schema_version": scenario.schema_version,
        "case_id": scenario.case_id,
        "family": scenario.family,
        "split": scenario.split,
        "severity": scenario.severity,
        "source_revision": scenario.source_revision,
        "construction": {
            "episodes": [
                {
                    "id": episode.id,
                    "sequence": episode.sequence,
                    "kind": episode.kind,
                    "statement": episode.statement,
                    "evidence": list(episode.evidence),
                }
                for episode in scenario.construction.episodes
            ]
        },
        "query": {
            "task": scenario.query.task,
            "observable_paths": list(scenario.query.observable_paths),
            "allowed_actions": list(scenario.query.allowed_actions),
        },
        "grading": {
            "grader": scenario.grading.grader,
            "expected_outcome": scenario.grading.expected_outcome,
            "acceptable_actions": list(scenario.grading.acceptable_actions),
            "gold_evidence": [
                {
                    "id": evidence.id,
                    "statement": evidence.statement,
                    "source_episodes": list(evidence.source_episodes),
                }
                for evidence in scenario.grading.gold_evidence
            ],
        },
    }


def grade(scenario: Scenario, action: str) -> GradeResult:
    """Score ``action`` for ``scenario`` against the action-correctness endpoint."""
    acceptable = set(scenario.grading.acceptable_actions)
    correct = action in acceptable
    weight = SEVERITY_WEIGHTS[scenario.severity]
    return GradeResult(
        case_id=scenario.case_id,
        endpoint=PRIMARY_ENDPOINT,
        action=action,
        expected_outcome=scenario.grading.expected_outcome,
        correct=correct,
        credit=1.0 if correct else 0.0,
        severity=scenario.severity,
        regret=0.0 if correct else weight,
    )


def cost_eligible(result: GradeResult) -> bool:
    """Return whether a sample may enter cost summaries under the gate.

    The frozen gate admits a sample only after it passes its case grader, so an
    incorrect cheap arm can never win.
    """
    return result.correct


MINIMAL_SCENARIO_DOCUMENT: Json = {
    "schema_version": SCENARIO_SCHEMA_VERSION,
    "case_id": "admission-minimal-001",
    "family": "admission",
    "split": "development",
    "severity": "major",
    "source_revision": "0d56bc7",
    "construction": {
        "episodes": [
            {
                "id": "ep-1",
                "sequence": 1,
                "kind": "observation",
                "statement": "A retry helper already lives at src/braintree/retry.py.",
                "evidence": ["src/braintree/retry.py"],
            },
            {
                "id": "ep-2",
                "sequence": 2,
                "kind": "decision",
                "statement": "A second backoff implementation was rejected on review.",
                "evidence": ["docs/adr/0007-retry.md"],
            },
        ]
    },
    "query": {
        "task": "Decide how the caller should handle a transient upstream failure.",
        "observable_paths": ["src/braintree/retry.py"],
        "allowed_actions": [
            "retain-existing-helper",
            "add-second-backoff",
            "discard-observation",
        ],
    },
    "grading": {
        "grader": "action-exact",
        "expected_outcome": "retain-existing-helper",
        "acceptable_actions": ["retain-existing-helper"],
        "gold_evidence": [
            {
                "id": "gold-1",
                "statement": "A retry helper exists and a duplicate was rejected.",
                "source_episodes": ["ep-1", "ep-2"],
            }
        ],
    },
}


def minimal_scenario() -> Scenario:
    """Return the smallest valid case that exercises the schema."""
    return parse_scenario(MINIMAL_SCENARIO_DOCUMENT)


def arm_fixtures(scenario: Scenario | None = None) -> tuple[ArmFixture, ...]:
    """Return the one case as each canonical arm sees it.

    The task, observable paths, and allowed actions are shared; only the
    construction input and the query-time memory differ, so the fixture
    demonstrates the schema's arm neutrality without an arm-specific answer in
    the task prompt.
    """
    case = minimal_scenario() if scenario is None else scenario
    episodes = tuple(episode.statement for episode in case.construction.episodes)
    flat = tuple(
        f"{episode.sequence}. {episode.statement}" for episode in case.construction.episodes
    )
    gold = tuple(evidence.statement for evidence in case.grading.gold_evidence)
    fixtures: list[ArmFixture] = []
    for arm_id in ARM_IDS:
        construction: tuple[str, ...]
        memory: tuple[str, ...]
        if arm_id == "repository-only":
            construction, memory = (), ()
        elif arm_id == "raw-history":
            construction, memory = episodes, episodes
        elif arm_id == "flat-memory":
            construction, memory = flat, flat
        elif arm_id == "braintree":
            construction, memory = episodes, gold
        else:  # oracle
            construction, memory = (), gold
        fixtures.append(
            ArmFixture(
                arm_id=arm_id,
                task=case.query.task,
                observable_paths=case.query.observable_paths,
                allowed_actions=case.query.allowed_actions,
                construction=construction,
                memory=memory,
            )
        )
    return tuple(fixtures)


def verify() -> list[str]:
    """Return the schema inconsistencies that would make it unusable.

    This is a structural self-check, not a semantic authority: it proves the
    schema still agrees with the frozen contract and that its minimal fixture
    round-trips.
    """
    problems: list[str] = []
    if SCENARIO_SCHEMA_VERSION not in VALID_SCHEMA_VERSIONS:
        problems.append("schema version is not declared valid")
    if SCENARIO_FAMILIES != memory_contract.SCENARIO_FAMILIES:
        problems.append("scenario families drifted from the contract")
    if CURATION_GROUPS != memory_contract.CURATION_GROUPS:
        problems.append("curation groups drifted from the contract")
    grouped = [family for _, families in CURATION_GROUPS for family in families]
    if sorted(grouped) != sorted(SCENARIO_FAMILIES) or len(grouped) != len(set(grouped)):
        problems.append("curation groups do not partition the scenario families")
    if SPLITS != memory_contract.SPLITS:
        problems.append("splits drifted from the contract")
    if ARM_IDS != memory_contract.CANONICAL_ARM_IDS:
        problems.append("arms drifted from the contract")
    if PRIMARY_ENDPOINT != memory_contract.PRIMARY_ENDPOINTS[0].name:
        problems.append("primary endpoint drifted from the contract")
    if CORRECTNESS_GATE != memory_contract.CORRECTNESS_GATE:
        problems.append("correctness gate drifted from the contract")
    if PIN_FIELDS != memory_contract.PIN_FIELDS:
        problems.append("version pins drifted from the contract")
    if set(SEVERITIES) != set(SEVERITY_WEIGHTS):
        problems.append("severity weights do not cover the severities")
    if len(GRADER_IDS) != len(set(GRADER_IDS)):
        problems.append("grader ids must be unique")
    try:
        scenario = minimal_scenario()
        if scenario_document(scenario) != MINIMAL_SCENARIO_DOCUMENT:
            problems.append("the minimal fixture does not round-trip")
    except ScenarioError as error:
        problems.append(f"the minimal fixture is invalid: {error}")
    return problems
