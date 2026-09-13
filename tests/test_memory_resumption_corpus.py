"""Corpus tests for the curated resumption and implicit-retrieval gold cases.

These tests freeze the resumption and implicit-retrieval families of the
memory-evaluation program: the versioned envelopes, schema conformance of every
case, the interruption-kind coverage, the low-lexical-overlap count, the control
versus memory-required observable-path property, split population, evidence-path
existence, arm-neutral tasks, the declared-action grading, and agreement between
the corpora and their prose authority. TAS-135 later owns the whole-corpus
validator, split digest, and leakage audit; this module only guards the two
families produced by TAS-132. Everything here is offline and makes zero live
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
_DOCUMENT = _ROOT / "research" / "agent-memory-resumption-cases.md"

# family -> (filename, corpus_version, expected case count).
_CORPORA = {
    "resumption": ("resumption.json", "memory-resumption-corpus-v1", 7),
    "implicit-retrieval": ("implicit-retrieval.json", "memory-implicit-retrieval-corpus-v1", 8),
}
_IMPLICIT = "implicit-retrieval"
_RESUMPTION = "resumption"

# The five interruption kinds the TAS-132 Done-when names, plus the
# memory-irrelevant control. The required kinds must all be covered.
_REQUIRED_KINDS = (
    "after-decision",
    "partial-implementation",
    "blocker",
    "failed-experiment",
    "handoff",
)
_CONTROL_KIND = "control"
_KINDS = _REQUIRED_KINDS + (_CONTROL_KIND,)

# The interruption kind each case exercises. Pinned here so the corpus cannot
# silently lose coverage of the Done-when kind list.
_CASE_KIND = {
    "resumption-after-decision-shared-install-001": "after-decision",
    "resumption-after-decision-semantic-optional-001": "after-decision",
    "resumption-partial-implementation-vault-notice-001": "partial-implementation",
    "resumption-blocker-live-authorization-001": "blocker",
    "resumption-failed-experiment-cold-resume-rule-001": "failed-experiment",
    "resumption-handoff-corpus-continuation-001": "handoff",
    "resumption-control-vault-rename-001": "control",
    "implicit-retrieval-failed-experiment-embedding-default-001": "failed-experiment",
    "implicit-retrieval-after-decision-derived-membership-001": "after-decision",
    "implicit-retrieval-blocker-lease-handoff-001": "blocker",
    "implicit-retrieval-failed-experiment-orientation-compaction-001": "failed-experiment",
    "implicit-retrieval-handoff-parent-next-001": "handoff",
    "implicit-retrieval-partial-implementation-write-set-closure-001": "partial-implementation",
    "implicit-retrieval-control-version-declaration-001": "control",
    "implicit-retrieval-control-offline-gate-001": "control",
}

# The exact low-lexical-overlap case set. Pinned so a regression cannot satisfy
# the at-least-half bar by moving overlap around between cases.
_EXPECTED_LOW_OVERLAP = frozenset(
    {
        "resumption-partial-implementation-vault-notice-001",
        "resumption-failed-experiment-cold-resume-rule-001",
        "resumption-handoff-corpus-continuation-001",
        "resumption-control-vault-rename-001",
        "implicit-retrieval-failed-experiment-embedding-default-001",
        "implicit-retrieval-blocker-lease-handoff-001",
        "implicit-retrieval-failed-experiment-orientation-compaction-001",
        "implicit-retrieval-handoff-parent-next-001",
        "implicit-retrieval-partial-implementation-write-set-closure-001",
        "implicit-retrieval-control-version-declaration-001",
        "implicit-retrieval-control-offline-gate-001",
    }
)

# Every Braintree surface that states the lexical-reference / optional-advisory
# conclusion of DEC-006 and THO-012. The two semantic cases must not observe any
# of them.
_SEMANTIC_DECIDING_SURFACES = frozenset(
    {
        "src/braintree/index.py",
        "src/braintree/semantic.py",
        "src/braintree/clustering.py",
        "src/braintree/provider.py",
        "src/braintree/reduction.py",
        "src/braintree/quality_benchmark.py",
        "src/braintree/embedding_benchmark.py",
        "benchmark/embedding-corpus.json",
        "benchmark/embedding-documents.jsonl",
    }
)

# Surfaces that state a memory-required case's deciding fact. They must never
# appear in that case's observable paths, or a repository-only arm could answer
# it. The review of TAS-132 found six such leaks; this pins the fix.
_FORBIDDEN_OBSERVABLE = {
    "resumption-after-decision-shared-install-001": {
        "scripts/install.sh",
        ".braintree/resolved/DEC-007-install-one-shared-per-root-program-per-agent-in.md",
        ".braintree/resolved/TAS-108-install-one-shared-per-root-program-so-agent-ski.md",
        "src/braintree/revision.py",
    },
    "resumption-after-decision-semantic-optional-001": set(_SEMANTIC_DECIDING_SURFACES),
    "resumption-partial-implementation-vault-notice-001": {
        "README.md",
        "src/braintree/vault.py",
    },
    "implicit-retrieval-failed-experiment-embedding-default-001": set(_SEMANTIC_DECIDING_SURFACES),
    "implicit-retrieval-after-decision-derived-membership-001": {
        "SKILL.md",
        ".braintree/index-map.md",
        ".braintree/resolved/TAS-011-reachability-contract.md",
    },
    "implicit-retrieval-blocker-lease-handoff-001": {
        "references/coordination.md",
        "src/braintree/sidecar.py",
        "src/braintree/cli.py",
        "src/braintree/main.py",
    },
}

# A case is low lexical overlap when its task shares at most two content words
# with its gold evidence, after removing stopwords and single-character tokens.
_LOW_OVERLAP_MAX = 2
_NODE_ID = re.compile(r"\b(?:TAS|THO|DEC|DEF|IDX|FBK)-?\d")
_STOPWORDS = frozenset(
    "a an the and or of to in is are was were be been being it its this that "
    "these those for on with as by at from we you i they he she them us our "
    "your not no do does did so if then than but can could should would may "
    "might must will shall have has had".split()
)


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


def _content_words(text: str) -> set[str]:
    return {
        word
        for word in re.findall(r"[a-z0-9]+", text.lower())
        if word not in _STOPWORDS and len(word) > 1
    }


def _is_low_overlap(scenario: schema.Scenario) -> bool:
    task = _content_words(scenario.query.task)
    gold = _content_words(" ".join(item.statement for item in scenario.grading.gold_evidence))
    return len(task & gold) <= _LOW_OVERLAP_MAX


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


def test_interruption_kinds_are_covered() -> None:
    assert set(_REQUIRED_KINDS) <= set(_CASE_KIND.values())
    assert set(_CASE_KIND.values()) <= set(_KINDS)
    assert set(_CASE_KIND) == {scenario.case_id for scenario in _all_scenarios()}


def test_low_lexical_overlap_cases_are_at_least_half() -> None:
    low = {scenario.case_id for scenario in _all_scenarios() if _is_low_overlap(scenario)}
    assert low == set(_EXPECTED_LOW_OVERLAP)
    total = len(_all_scenarios())
    assert len(low) >= (total + 1) // 2


def test_memory_required_cases_do_not_observe_their_deciding_surface() -> None:
    for scenario in _all_scenarios():
        forbidden = _FORBIDDEN_OBSERVABLE.get(scenario.case_id, set())
        overlap = forbidden & set(scenario.query.observable_paths)
        assert not overlap, f"{scenario.case_id} observes deciding paths: {sorted(overlap)}"


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
    for scenario in _all_scenarios():
        assert scenario.severity in schema.SEVERITIES


def test_controls_are_memory_irrelevant_and_required_cases_are_not() -> None:
    for scenario in _all_scenarios():
        gold_paths = _gold_paths(scenario)
        observable = set(scenario.query.observable_paths)
        if _CASE_KIND[scenario.case_id] == _CONTROL_KIND:
            assert gold_paths <= observable, scenario.case_id
        else:
            assert gold_paths - observable, scenario.case_id


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


def test_verify_rejects_a_mutated_case() -> None:
    envelope = _envelope(_IMPLICIT)
    case = envelope["cases"][0]
    case["query"]["observable_paths"] = ["../secrets.env"]
    with pytest.raises(schema.ScenarioError):
        schema.parse_scenario(case)
