"""Corpus tests for the curated admission gold cases.

These tests freeze the admission-family gold corpus of the memory-evaluation
program: the versioned envelope, schema conformance of every case, the
retain/update-existing/discard label balance, split balance, evidence-path
existence, arm-neutral task prompts, and agreement between the corpus and its
prose authority. TAS-135 later owns the whole-corpus validator, split digest,
and leakage audit; this module only guards the admission family produced by
TAS-131. Everything here is offline and makes zero live model calls.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from tangle import memory_corpus
from tangle import memory_scenario as schema

_ROOT = Path(__file__).resolve().parents[1]
_CORPUS = _ROOT / "benchmark" / "memory-corpus" / "admission.json"
_DOCUMENT = _ROOT / "research" / "agent-memory-admission-cases.md"

_CORPUS_VERSION = "memory-admission-corpus-v1"
_LABELS = ("retain", "update-existing", "discard")
_INPUT_KINDS = (
    "current code fact",
    "expensive derived result",
    "user constraint",
    "rejected alternative",
    "repeated gotcha",
    "transient failure",
    "unsupported hypothesis",
)

# The required input kind each case exercises. Pinned here so the corpus cannot
# silently lose coverage of the Done-when input list.
_CASE_INPUT = {
    "admission-retain-owner-compression-constraint-001": "user constraint",
    "admission-retain-offline-grading-constraint-001": "user constraint",
    "admission-retain-heldout-separation-hypothesis-001": "unsupported hypothesis",
    "admission-retain-label-stability-hypothesis-001": "unsupported hypothesis",
    "admission-retain-envelope-layout-alternative-001": "rejected alternative",
    "admission-update-existing-context-rev-001": "repeated gotcha",
    "admission-update-existing-fast-suite-001": "expensive derived result",
    "admission-update-existing-seam-reuse-001": "repeated gotcha",
    "admission-update-existing-clamp-rule-001": "repeated gotcha",
    "admission-update-existing-staging-gotcha-001": "repeated gotcha",
    "admission-discard-current-code-fact-001": "current code fact",
    "admission-discard-transient-failure-001": "transient failure",
    "admission-discard-cache-speculation-001": "unsupported hypothesis",
    "admission-discard-routine-verification-001": "routine narration",
    "admission-discard-duplicate-source-001": "duplicate source material",
}


def _envelope() -> dict[str, Any]:
    data = json.loads(_CORPUS.read_text(encoding="utf-8"))
    assert isinstance(data, dict)
    return data


def _scenarios() -> list[schema.Scenario]:
    return [schema.parse_scenario(raw) for raw in _envelope()["cases"]]


def _label(scenario: schema.Scenario) -> str:
    outcome = scenario.grading.expected_outcome
    prefixes = (("retain", "retain-"), ("update-existing", "update-"), ("discard", "discard-"))
    for label, prefix in prefixes:
        if outcome.startswith(prefix):
            return label
    raise AssertionError(f"case {scenario.case_id} has no admission label prefix: {outcome}")


def test_envelope_is_versioned_and_admission_only() -> None:
    envelope = _envelope()
    assert envelope["corpus_version"] == _CORPUS_VERSION
    assert envelope["schema_version"] == schema.SCENARIO_SCHEMA_VERSION
    assert envelope["family"] == "admission"
    assert envelope["source_revision"]
    assert len(envelope["cases"]) == 15


def test_every_case_parses_and_agrees_with_the_envelope() -> None:
    envelope = _envelope()
    for scenario in _scenarios():
        assert scenario.family == "admission"
        assert scenario.split in schema.SPLITS
        assert scenario.severity in schema.SEVERITIES
        assert scenario.source_revision == envelope["source_revision"]


def test_case_ids_are_unique() -> None:
    ids = [scenario.case_id for scenario in _scenarios()]
    assert len(ids) == len(set(ids))


def test_labels_are_balanced() -> None:
    counts = {label: 0 for label in _LABELS}
    for scenario in _scenarios():
        counts[_label(scenario)] += 1
    assert counts == {"retain": 5, "update-existing": 5, "discard": 5}


def test_splits_are_populated_for_every_label() -> None:
    splits = {label: {split: 0 for split in schema.SPLITS} for label in _LABELS}
    for scenario in _scenarios():
        splits[_label(scenario)][scenario.split] += 1
    for label in _LABELS:
        assert splits[label]["development"] == 3, label
        assert splits[label]["held-out"] == 2, label


def test_required_input_kinds_are_covered() -> None:
    assert set(_INPUT_KINDS) <= set(_CASE_INPUT.values())
    assert set(_CASE_INPUT) == {scenario.case_id for scenario in _scenarios()}


def test_every_cited_path_exists_in_the_repository() -> None:
    paths: set[str] = set()
    for scenario in _scenarios():
        paths.update(scenario.query.observable_paths)
        for episode in scenario.construction.episodes:
            paths.update(episode.evidence)
    missing = sorted(path for path in paths if not memory_corpus.path_exists(_ROOT, path))
    assert missing == []


def test_task_prompts_are_arm_neutral() -> None:
    for scenario in _scenarios():
        assert scenario.grading.expected_outcome not in scenario.query.task
        for action in scenario.query.allowed_actions:
            assert action not in scenario.query.task
        episode_statements = {episode.statement for episode in scenario.construction.episodes}
        gold_statements = {evidence.statement for evidence in scenario.grading.gold_evidence}
        assert episode_statements.isdisjoint(gold_statements)


def test_each_case_grades_only_its_declared_actions() -> None:
    for scenario in _scenarios():
        expected = schema.grade(scenario, scenario.grading.expected_outcome)
        assert expected.correct and schema.cost_eligible(expected)
        for action in scenario.query.allowed_actions:
            grade = schema.grade(scenario, action)
            assert grade.correct == (action in scenario.grading.acceptable_actions)


def test_each_case_names_gold_evidence_with_a_later_decision_or_no_value() -> None:
    for scenario in _scenarios():
        assert scenario.grading.gold_evidence
        for evidence in scenario.grading.gold_evidence:
            assert evidence.statement.strip()
            assert evidence.source_episodes


def test_document_agrees_with_the_corpus() -> None:
    text = _DOCUMENT.read_text(encoding="utf-8")
    assert _CORPUS_VERSION in text
    assert schema.SCENARIO_SCHEMA_VERSION in text
    for scenario in _scenarios():
        assert scenario.case_id in text, scenario.case_id
    for kind in _INPUT_KINDS:
        assert kind in text, kind
