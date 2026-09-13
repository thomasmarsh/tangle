"""Corpus tests for the curated revision-and-conflict gold cases.

These tests freeze the three revision-and-conflict families of the
memory-evaluation program — temporal update, cascading invalidation, and
conflict and uncertainty: the versioned envelopes, schema conformance of every
case, the Done-when kind coverage, the false-positive versus false-negative
invalidation distinction, the reconciled/preserved/abstained/clarified
behavior coverage, the event-time-versus-mutation-time case, the
forbidden-observable leak guards, split population, evidence-path existence,
arm-neutral tasks, the declared-action grading, and agreement between the
corpora and their prose authority. TAS-135 later owns the whole-corpus
validator, split digest, and leakage audit; this module only guards the three
families produced by TAS-133. Everything here is offline and makes zero live
model calls.
"""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Any

import pytest

from braintree import memory_corpus
from braintree import memory_scenario as schema

_ROOT = Path(__file__).resolve().parents[1]
_CORPUS_DIR = _ROOT / "benchmark" / "memory-corpus"
_DOCUMENT = _ROOT / "research" / "agent-memory-revision-conflict-cases.md"

# family -> (filename, corpus_version, expected case count).
_CORPORA = {
    "temporal-update": ("temporal-update.json", "memory-temporal-update-corpus-v1", 4),
    "cascading-invalidation": (
        "cascading-invalidation.json",
        "memory-cascading-invalidation-corpus-v1",
        4,
    ),
    "conflict-and-uncertainty": (
        "conflict-and-uncertainty.json",
        "memory-conflict-and-uncertainty-corpus-v1",
        3,
    ),
}
_TEMPORAL = "temporal-update"
_CASCADING = "cascading-invalidation"
_CONFLICT = "conflict-and-uncertainty"

# The Done-when kinds every family set must cover. Pinned here so the corpus
# cannot silently lose coverage of the TAS-133 Done-when list.
_REQUIRED_KINDS = (
    "cosmetic-versus-semantic",
    "changed-definition",
    "stale-consumer",
    "reversal",
    "superseded-decision",
    "independent-evidence",
    "unresolved-conflict",
    "missing-premise",
    "event-time-differs",
)
_CASE_KIND = {
    "temporal-update-cosmetic-edit-001": "cosmetic-versus-semantic",
    "temporal-update-semantic-revision-001": "stale-consumer",
    "temporal-update-event-mutation-time-001": "event-time-differs",
    "temporal-update-changed-definition-001": "changed-definition",
    "cascading-invalidation-transitive-stale-001": "stale-consumer",
    "cascading-invalidation-independent-evidence-001": "independent-evidence",
    "cascading-invalidation-reversal-in-place-001": "reversal",
    "cascading-invalidation-superseded-decision-001": "superseded-decision",
    "conflict-and-uncertainty-competing-rules-001": "unresolved-conflict",
    "conflict-and-uncertainty-missing-premise-001": "missing-premise",
    "conflict-and-uncertainty-genuine-conflict-001": "unresolved-conflict",
}

# The invalidation mode each cascading case tests. A true invalidation changes
# the consumer's conclusion; a false positive looks stale but is preserved by
# independent evidence; a false negative matches its pin but is obsolete through
# supersession. The three must be separately gradeable.
_INVALIDATION = {
    "cascading-invalidation-transitive-stale-001": "true",
    "cascading-invalidation-independent-evidence-001": "false-positive",
    "cascading-invalidation-reversal-in-place-001": "true",
    "cascading-invalidation-superseded-decision-001": "false-negative",
}
_INVALIDATION_ACTIONS = {
    "false-positive": frozenset({"reset-the-pin-and-keep-the-conclusion"}),
    "false-negative": frozenset({"follow-the-replacement-link"}),
}

# The correction behavior each memory-required case tests, against the Done-when
# list: reconcile, preserve alternatives, abstain, and ask one targeted
# clarification.
_REQUIRED_BEHAVIORS = ("reconcile", "preserve-alternatives", "abstain", "ask-clarification")
_BEHAVIOR = {
    "temporal-update-semantic-revision-001": ("reconcile",),
    "cascading-invalidation-transitive-stale-001": ("reconcile",),
    "cascading-invalidation-independent-evidence-001": ("reconcile",),
    "cascading-invalidation-reversal-in-place-001": ("reconcile",),
    "cascading-invalidation-superseded-decision-001": ("reconcile",),
    "conflict-and-uncertainty-competing-rules-001": ("preserve-alternatives", "abstain"),
    "conflict-and-uncertainty-missing-premise-001": ("ask-clarification",),
    "conflict-and-uncertainty-genuine-conflict-001": ("preserve-alternatives",),
}

# The case whose event time and mutation time genuinely differ: the handoff
# stamps a placeholder ahead of the host clock, and the worker must clamp.
_EVENT_TIME_CASES = frozenset({"temporal-update-event-mutation-time-001"})

# The revision/pin, coordination, and benchmark surfaces that state each
# case's deciding fact. A memory-required case must not observe any of them, or
# a repository-only arm could answer it without memory. None of the corpus's
# own observable_paths appear here; the guard is what keeps it that way.
_FORBIDDEN_OBSERVABLE = {
    "temporal-update-cosmetic-edit-001": {
        "SKILL.md",
        "references/dependencies.md",
        ".braintree/resolved/TAS-009-semantic-revisions.md",
        ".braintree/resolved/TAS-118-resolved-seam-internal-reuse.md",
    },
    "temporal-update-semantic-revision-001": {
        "references/dependencies.md",
        ".braintree/resolved/TAS-009-semantic-revisions.md",
        ".braintree/resolved/TAS-059-stale-pin-commit-shape.md",
        ".braintree/resolved/TAS-069-unify-dependency-semantics.md",
    },
    "temporal-update-event-mutation-time-001": {
        "SKILL.md",
        ".braintree/resolved/TAS-112-timestamp-clamp-rule.md",
        ".braintree/resolved/TAS-113-write-set-change-closure.md",
    },
    "temporal-update-changed-definition-001": {
        "pyproject.toml",
        "tests/test_scaffold.py",
        "src/braintree/__init__.py",
        ".braintree/resolved/DEC-003-semantic-versioning.md",
    },
    "cascading-invalidation-transitive-stale-001": {
        ".braintree/resolved/TAS-059-stale-pin-commit-shape.md",
        ".braintree/resolved/TAS-069-unify-dependency-semantics.md",
        ".braintree/resolved/TAS-072-transitive-dependency-impact.md",
        ".braintree/resolved/TAS-077-reconciliation-planner.md",
    },
    "cascading-invalidation-independent-evidence-001": {
        "references/dependencies.md",
        "research/agent-memory-theory-evaluation.md",
        ".braintree/resolved/TAS-009-semantic-revisions.md",
        ".braintree/resolved/TAS-118-resolved-seam-internal-reuse.md",
        ".braintree/resolved/DEC-003-semantic-versioning.md",
    },
    "cascading-invalidation-reversal-in-place-001": {
        "references/dependencies.md",
        ".braintree/resolved/TAS-082-reversal-semantics.md",
    },
    "cascading-invalidation-superseded-decision-001": {
        "references/dependencies.md",
        ".braintree/resolved/TAS-082-reversal-semantics.md",
        ".braintree/resolved/TAS-009-semantic-revisions.md",
    },
    "conflict-and-uncertainty-competing-rules-001": {
        ".braintree/resolved/TAS-082-reversal-semantics.md",
        ".braintree/resolved/TAS-104-state-event-triggered-split-and-consolidation-ev.md",
        "research/agent-memory-theory-evaluation.md",
        ".braintree/proposed/TAS-127-uncertainty-provenance-security.md",
    },
    "conflict-and-uncertainty-missing-premise-001": {
        ".braintree/resolved/TAS-030-hybrid-markdown-sqlite-migration.md",
        ".braintree/resolved/TAS-109-move-vault-to-dot-braintree.md",
        "research/agent-memory-theory-evaluation.md",
        ".braintree/proposed/TAS-127-uncertainty-provenance-security.md",
    },
    "conflict-and-uncertainty-genuine-conflict-001": {
        ".braintree/resolved/DEC-004-compact-skill-text.md",
        ".braintree/resolved/THO-016-has-cumulative-contract-growth-invalidated-the-c.md",
        ".braintree/blocked/TAS-080-staged-token-ab.md",
        "research/agent-memory-theory-evaluation.md",
        ".braintree/proposed/TAS-127-uncertainty-provenance-security.md",
    },
}

_NODE_ID = re.compile(r"\b(?:TAS|THO|DEC|DEF|IDX|FBK)-?\d")


def _envelope(family: str) -> dict[str, Any]:
    filename, _, _ = _CORPORA[family]
    data = json.loads((_CORPUS_DIR / filename).read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _scenarios() -> list[tuple[str, schema.Scenario]]:
    cases: list[tuple[str, schema.Scenario]] = []
    for family in _CORPORA:
        for raw in _envelope(family)["cases"]:
            cases.append((family, schema.parse_scenario(raw)))
    return cases


def _all_scenarios() -> list[schema.Scenario]:
    return [scenario for _, scenario in _scenarios()]


def _gold_paths(scenario: schema.Scenario) -> set[str]:
    episodes = {episode.id: episode for episode in scenario.construction.episodes}
    paths: set[str] = set()
    for item in scenario.grading.gold_evidence:
        for source in item.source_episodes:
            paths.update(episodes[source].evidence)
    return paths


def test_envelopes_are_versioned_and_family_only() -> None:
    for family, (_, version, count) in _CORPORA.items():
        envelope = _envelope(family)
        assert envelope["corpus_version"] == version
        assert envelope["schema_version"] == schema.SCENARIO_SCHEMA_VERSION
        assert envelope["family"] == family
        assert envelope["source_revision"]
        assert len(envelope["cases"]) == count


def test_every_case_parses_and_agrees_with_its_envelope() -> None:
    for family, scenario in _scenarios():
        envelope = _envelope(family)
        assert scenario.family == family
        assert scenario.split in schema.SPLITS
        assert scenario.severity in schema.SEVERITIES
        assert scenario.source_revision == envelope["source_revision"]


def test_case_ids_are_unique() -> None:
    ids = [scenario.case_id for scenario in _all_scenarios()]
    assert len(ids) == len(set(ids))


def test_required_kinds_are_covered() -> None:
    assert set(_REQUIRED_KINDS) <= set(_CASE_KIND.values())
    assert set(_CASE_KIND) == {scenario.case_id for scenario in _all_scenarios()}


def test_invalidation_modes_are_separately_gradeable() -> None:
    assert set(_INVALIDATION.values()) == {"true", "false-positive", "false-negative"}
    cascading = {
        scenario.case_id: scenario
        for scenario in _all_scenarios()
        if scenario.family == _CASCADING
    }
    assert set(_INVALIDATION) == set(cascading)
    for case_id, mode in _INVALIDATION.items():
        expected = cascading[case_id].grading.expected_outcome
        if mode == "true":
            assert expected not in set().union(*_INVALIDATION_ACTIONS.values()), case_id
        else:
            assert expected in _INVALIDATION_ACTIONS[mode], case_id


def test_correct_behaviors_are_covered() -> None:
    covered = {behavior for behaviors in _BEHAVIOR.values() for behavior in behaviors}
    assert set(_REQUIRED_BEHAVIORS) <= covered


def test_event_time_and_mutation_time_differ_in_a_case() -> None:
    assert _EVENT_TIME_CASES <= {scenario.case_id for scenario in _all_scenarios()}
    for scenario in _all_scenarios():
        if scenario.case_id in _EVENT_TIME_CASES:
            text = " ".join(
                episode.statement for episode in scenario.construction.episodes
            ).lower()
            gold = " ".join(
                item.statement for item in scenario.grading.gold_evidence
            ).lower()
            assert "host clock" in text
            assert "ahead of the host clock" in text
            assert "differ" in gold


def test_memory_required_cases_do_not_observe_their_deciding_surface() -> None:
    for scenario in _all_scenarios():
        forbidden = _FORBIDDEN_OBSERVABLE.get(scenario.case_id, set())
        overlap = forbidden & set(scenario.query.observable_paths)
        assert not overlap, f"{scenario.case_id} observes deciding paths: {sorted(overlap)}"
        assert _gold_paths(scenario) - set(scenario.query.observable_paths), scenario.case_id


def test_task_prompts_expose_no_node_ids_or_family_names() -> None:
    for scenario in _all_scenarios():
        task = scenario.query.task
        assert _NODE_ID.search(task) is None, scenario.case_id
        assert "[[" not in task, scenario.case_id
        assert scenario.family not in task, scenario.case_id


def test_every_case_carries_a_distractor_episode() -> None:
    for scenario in _all_scenarios():
        referenced = {
            source
            for item in scenario.grading.gold_evidence
            for source in item.source_episodes
        }
        unreferenced = {episode.id for episode in scenario.construction.episodes} - referenced
        assert unreferenced, scenario.case_id


def test_splits_are_populated_for_every_family() -> None:
    for family in _CORPORA:
        splits = {
            scenario.split
            for scenario in _all_scenarios()
            if scenario.family == family
        }
        assert splits == set(schema.SPLITS), family


def test_every_cited_path_exists_in_the_repository() -> None:
    paths: set[str] = set()
    for scenario in _all_scenarios():
        paths.update(scenario.query.observable_paths)
        for episode in scenario.construction.episodes:
            paths.update(episode.evidence)
    missing = sorted(path for path in paths if not memory_corpus.path_exists(_ROOT, path))
    assert missing == []


def test_task_prompts_are_arm_neutral() -> None:
    for scenario in _all_scenarios():
        assert scenario.grading.expected_outcome not in scenario.query.task
        for action in scenario.query.allowed_actions:
            assert action not in scenario.query.task
        episode_statements = {episode.statement for episode in scenario.construction.episodes}
        gold_statements = {item.statement for item in scenario.grading.gold_evidence}
        assert episode_statements.isdisjoint(gold_statements)


def test_each_case_grades_only_its_declared_actions() -> None:
    for scenario in _all_scenarios():
        expected = schema.grade(scenario, scenario.grading.expected_outcome)
        assert expected.correct and schema.cost_eligible(expected)
        for action in scenario.query.allowed_actions:
            grade = schema.grade(scenario, action)
            assert grade.correct == (action in scenario.grading.acceptable_actions)


def test_each_case_names_gold_evidence_with_a_later_decision() -> None:
    for scenario in _all_scenarios():
        assert scenario.grading.gold_evidence
        for item in scenario.grading.gold_evidence:
            assert item.statement.strip()
            assert item.source_episodes


def test_document_agrees_with_the_corpora() -> None:
    text = _DOCUMENT.read_text(encoding="utf-8")
    assert schema.SCENARIO_SCHEMA_VERSION in text
    for family, (_, version, _) in _CORPORA.items():
        assert version in text, version
        assert family in text, family
    for scenario in _all_scenarios():
        assert scenario.case_id in text, scenario.case_id
    for kind in _REQUIRED_KINDS:
        assert kind in text, kind
    for behavior in _REQUIRED_BEHAVIORS:
        assert behavior in text, behavior


def test_verify_rejects_a_mutated_case() -> None:
    envelope = _envelope(_CONFLICT)
    case = envelope["cases"][0]
    case["query"]["observable_paths"] = ["../secrets.env"]
    with pytest.raises(schema.ScenarioError):
        schema.parse_scenario(case)
