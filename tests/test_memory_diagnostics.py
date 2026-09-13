"""Zero-live tests for the pipeline diagnostics module.

The first group pins the taxonomy against the frozen contract. The second pins
the two-stage adjudication procedure: separate retrieval scoring, the arm-aware
memory labels, the downstream labels, and the independent reviewer's
disagreement. The third pins the report, its reproducibility, and the CLI. Every
test is offline and makes zero live model calls.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from braintree import (
    memory_causal,
    memory_contract,
    memory_corpus,
    memory_diagnostics,
    memory_scenario,
)

_ROOT = Path(__file__).resolve().parents[1]
_CORPUS = memory_corpus.load_corpus(_ROOT)
_CASES = {case.case_id: case for envelope in _CORPUS for case in envelope.cases}


def _case(case_id: str) -> memory_scenario.Scenario:
    return _CASES[case_id]


def _scenario(**overrides: Any) -> memory_scenario.Scenario:
    document = copy.deepcopy(memory_scenario.MINIMAL_SCENARIO_DOCUMENT)
    document.update(overrides)
    return memory_scenario.parse_scenario(document)


_DOCUMENT = _ROOT / "research" / "agent-memory-pipeline-diagnostics.md"


def test_diagnostic_labels_match_the_contract() -> None:
    assert set(memory_diagnostics.DIAGNOSTIC_LABELS) == set(memory_contract.DIAGNOSTIC_LABELS)
    assert len(set(memory_diagnostics.DIAGNOSTIC_LABELS)) == len(
        memory_diagnostics.DIAGNOSTIC_LABELS
    )
    stages = [stage for _, stage, _, _ in memory_diagnostics.DIAGNOSTIC_TAXONOMY]
    assert len(set(stages)) == len(stages)
    assert memory_diagnostics.MEMORY_LABELS == (
        "write-miss",
        "organization-error",
        "retrieval-miss",
    )
    assert memory_diagnostics.DOWNSTREAM_LABELS == (
        "stale-or-conflicting-retrieval",
        "reader-failure",
        "action-failure",
    )


def test_retrieval_is_scored_separately_per_arm() -> None:
    case = _case("poisoning-and-authority-direct-injection-001")
    bare = memory_diagnostics._retrieval_record(case, "repository-only")
    assert bare["score"] == 0.0
    assert bare["missed"]
    treated = memory_diagnostics._retrieval_record(case, "braintree")
    assert treated["score"] == 1.0
    assert treated["missed"] == []
    flat = memory_diagnostics._retrieval_record(case, "flat-memory")
    assert flat["score"] == 1.0
    assert flat["missed"] == []
    oracle = memory_diagnostics._retrieval_record(case, "oracle")
    assert oracle["score"] == 1.0


def test_flat_memory_and_raw_history_deliver_the_same_episodes() -> None:
    """Regression: flat-memory frames notes with a prefix; matching must see through it."""
    for case in memory_corpus.pilot_subset(_CORPUS):
        raw = memory_diagnostics._delivered_episode_ids(case, "raw-history")
        flat = memory_diagnostics._delivered_episode_ids(case, "flat-memory")
        assert raw == flat, case.case_id
        assert memory_diagnostics._retrieval_record(case, "flat-memory")["score"] == 1.0


def test_repository_only_failure_is_a_write_miss() -> None:
    case = _case("admission-retain-label-stability-hypothesis-001")
    label, rule = memory_diagnostics.adjudicate(
        case, "repository-only", "discard-observation"
    )
    assert (label, rule) == ("write-miss", "memory-stage")


def test_braintree_organization_and_flat_memory_retrieval_are_distinct(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _scenario()
    monkeypatch.setattr(memory_causal, "arm_memory", lambda *args, **kwargs: ())
    assert memory_diagnostics._memory_label(case, "braintree") == "organization-error"
    assert memory_diagnostics._memory_label(case, "raw-history") == "retrieval-miss"
    assert memory_diagnostics._memory_label(case, "flat-memory") == "retrieval-miss"


def test_oracle_retrieval_is_exact_even_when_arm_memory_is_empty(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _scenario()
    monkeypatch.setattr(memory_causal, "arm_memory", lambda *args, **kwargs: ())
    assert memory_diagnostics._memory_label(case, "oracle") is None


def test_delivered_discard_action_is_an_action_failure() -> None:
    case = _case("poisoning-and-authority-direct-injection-001")
    label, rule = memory_diagnostics.adjudicate(
        case, "braintree", "discard-the-note-and-the-reproducer"
    )
    assert (label, rule) == ("action-failure", "downstream-stage")


def test_delivered_non_discard_action_is_a_reader_failure() -> None:
    case = _case("cascading-invalidation-independent-evidence-001")
    label, rule = memory_diagnostics.adjudicate(
        case, "braintree", "revise-the-consumer-conclusion"
    )
    assert (label, rule) == ("reader-failure", "downstream-stage")


def test_competing_delivered_decision_is_stale_or_conflicting(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _conflict_case_with_competitor()
    statements = tuple(episode.statement for episode in case.construction.episodes)
    monkeypatch.setattr(memory_causal, "arm_memory", lambda *args, **kwargs: statements)
    label, rule = memory_diagnostics.adjudicate(case, "raw-history", "add-second-backoff")
    assert (label, rule) == ("stale-or-conflicting-retrieval", "downstream-stage")


def test_unrelated_delivered_observation_is_not_stale(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    case = _conflict_case_with_competitor()
    statements = tuple(
        episode.statement
        for episode in case.construction.episodes
        if episode.kind != "decision" or episode.id in {"ep-1", "ep-2"}
    )
    monkeypatch.setattr(memory_causal, "arm_memory", lambda *args, **kwargs: statements)
    label, _ = memory_diagnostics.adjudicate(case, "raw-history", "add-second-backoff")
    assert label == "reader-failure"


def test_second_opinion_disagrees_exactly_at_the_action_first_boundary() -> None:
    case = _scenario()
    committed, _ = memory_diagnostics.adjudicate(case, "repository-only", "discard-observation")
    other, rule = memory_diagnostics.second_opinion(
        case, "repository-only", "discard-observation"
    )
    assert committed == "write-miss"
    assert other == "action-failure"
    assert rule == "action-first"


def test_failure_records_cover_every_causal_failure() -> None:
    causal = json.loads(
        (_ROOT / memory_diagnostics.CAUSAL_ARTIFACT).read_text(encoding="utf-8")
    )
    records = memory_diagnostics.failure_records(_ROOT)
    assert len(records) == len(causal["failures"])
    for record in records:
        assert record["label"] in memory_diagnostics.DIAGNOSTIC_LABELS
        assert record["reviewer"]["label"] in memory_diagnostics.DIAGNOSTIC_LABELS


def test_diagnose_is_deterministic_and_internally_consistent() -> None:
    first = memory_diagnostics.diagnose(_ROOT)
    second = memory_diagnostics.diagnose(_ROOT)
    assert first == second
    assert memory_diagnostics.report_problems(first) == []
    assert sum(int(row["count"]) for row in first["labels"]) == len(first["failures"])
    agreement = sum(1 for record in first["failures"] if record["agreement"])
    assert first["review"]["agreement"] == agreement
    severities = [float(row["severity_weighted"]) for row in first["bottlenecks"]]
    assert severities == sorted(severities, reverse=True)
    assert len(first["justified_workstreams"]) == 4
    assert first["limits"]["retrieval_saturated"] is True
    assert first["source"]["split"] == "development"


def test_load_result_rejects_a_mismatched_corpus_digest(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(memory_corpus, "corpus_digest", lambda corpus: "sha256:deadbeef")
    with pytest.raises(memory_diagnostics.DiagnosticError, match="corpus digest"):
        memory_diagnostics._load_result(_ROOT)


def test_report_problems_reject_tampering() -> None:
    report = memory_diagnostics.diagnose(_ROOT)
    tampered = copy.deepcopy(report)
    tampered["protocol"] = "not-the-protocol"
    assert any("protocol" in problem for problem in memory_diagnostics.report_problems(tampered))
    tampered = copy.deepcopy(report)
    tampered["review"]["agreement"] = -1
    assert any(
        "agreement" in problem for problem in memory_diagnostics.report_problems(tampered)
    )


def test_committed_artifact_re_derives() -> None:
    assert memory_diagnostics.verify(_ROOT) == []
    committed = json.loads(
        (_ROOT / memory_diagnostics.DIAGNOSTIC_ARTIFACT).read_text(encoding="utf-8")
    )
    assert committed == memory_diagnostics.diagnose(_ROOT)


def test_document_matches_the_module() -> None:
    text = _DOCUMENT.read_text(encoding="utf-8")
    assert memory_diagnostics.DIAGNOSTIC_PROTOCOL in text
    for label in memory_diagnostics.DIAGNOSTIC_LABELS:
        assert label in text
    for workstream in (
        "TAS-124",
        "TAS-125",
        "TAS-126",
        "TAS-127",
    ):
        assert workstream in text


def test_cli_record_and_verify(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    output = tmp_path / "report.json"
    assert memory_diagnostics.main(["record", "--output", str(output)]) == 0
    written = json.loads(output.read_text(encoding="utf-8"))
    assert written == memory_diagnostics.diagnose(_ROOT)
    assert memory_diagnostics.main(["verify"]) == 0
    captured = capsys.readouterr()
    assert "verification: passed" in captured.out
    assert memory_diagnostics.main(["unknown"]) == 2


def test_cli_verify_reports_a_missing_artifact(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    monkeypatch.setattr(memory_diagnostics, "DIAGNOSTIC_ARTIFACT", "benchmark/missing.json")
    problems = memory_diagnostics.verify(_ROOT)
    assert problems and "missing diagnostics artifact" in problems[0]


def _conflict_case_with_competitor() -> memory_scenario.Scenario:
    """Return a conflict-family case with one delivered non-gold decision and observation."""
    document = copy.deepcopy(memory_scenario.MINIMAL_SCENARIO_DOCUMENT)
    document["family"] = "conflict-and-uncertainty"
    document["construction"]["episodes"].extend(
        [
            {
                "id": "ep-3",
                "sequence": 3,
                "kind": "decision",
                "statement": "An earlier note argued for a second backoff implementation.",
                "evidence": ["docs/adr/0007-retry.md"],
            },
            {
                "id": "ep-4",
                "sequence": 4,
                "kind": "observation",
                "statement": "An unrelated note renamed an output helper.",
                "evidence": ["docs/adr/0007-retry.md"],
            },
        ]
    )
    return memory_scenario.parse_scenario(document)
