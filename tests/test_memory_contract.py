"""Contract tests for the frozen memory-evaluation protocol.

These tests protect the literal protocol the later memory-evaluation harness
must agree on: the protocol version, the five causal arms, the reconstructibility
categories, the token vocabulary shared with the token benchmark, the scenario
family partition, the statistical thresholds, and the prose contract's agreement
with the module. Everything here is offline and imports no model runtime.
"""

from __future__ import annotations

import json

import pytest

from tangle import memory_contract as harness
from tangle import token_benchmark


def test_protocol_is_literal() -> None:
    assert harness.PROTOCOL == "memory-eval-contract-v1"
    assert harness.PRIMARY_TARGET == "memory-dependent downstream action quality"


def test_arms_are_the_five_canonical_conditions() -> None:
    assert harness.CANONICAL_ARM_IDS == (
        "repository-only",
        "raw-history",
        "flat-memory",
        "tangle",
        "oracle",
    )
    assert list(harness.CANONICAL_ARM_IDS) == [arm.id for arm in harness.ARMS]
    assert len(set(harness.CANONICAL_ARM_IDS)) == 5
    for arm in harness.ARMS:
        assert arm.available_state.strip()
        assert arm.isolates.strip()


def test_reconstructibility_covers_the_five_failures() -> None:
    names = {test.name for test in harness.RECONSTRUCTIBILITY_TESTS}
    assert names == {
        "unavailable",
        "unreliable",
        "ambiguous",
        "nondeterministic",
        "disproportionately-costly",
    }
    for test in harness.RECONSTRUCTIBILITY_TESTS:
        assert test.question.strip().endswith("?")
    assert not harness.ADMISSION_RULE.strip().startswith("Never")
    assert "disproportionately costly" in harness.ADMISSION_RULE


def test_primary_secondary_and_diagnostic_names_are_unique() -> None:
    assert harness.PRIMARY_ENDPOINTS
    names = (
        [endpoint.name for endpoint in harness.PRIMARY_ENDPOINTS]
        + [endpoint.name for endpoint in harness.SECONDARY_ENDPOINTS]
        + list(harness.DIAGNOSTIC_LABELS)
    )
    assert len(names) == len(set(names))
    for endpoint in (*harness.PRIMARY_ENDPOINTS, *harness.SECONDARY_ENDPOINTS):
        assert endpoint.definition.strip()


def test_token_metrics_share_the_token_benchmark_vocabulary() -> None:
    assert set(harness.TOKEN_METRICS) == {*token_benchmark.FIELDS, "uncached_input_tokens"}
    assert len(harness.TOKEN_METRICS) == len(set(harness.TOKEN_METRICS))
    assert "total_tokens" in harness.COST_METRICS
    assert "tool_calls" in harness.INTERACTION_METRICS


def test_curation_groups_partition_the_families() -> None:
    grouped = [family for _, families in harness.CURATION_GROUPS for family in families]
    assert sorted(grouped) == sorted(harness.SCENARIO_FAMILIES)
    assert len(grouped) == len(set(grouped))


def test_splits_and_statistical_thresholds_are_preregistered() -> None:
    assert harness.SPLITS == ("development", "held-out")
    assert harness.MIN_MODELS >= 3
    assert harness.MIN_REPETITIONS >= 3
    assert harness.BOOTSTRAP_RESAMPLES >= 1_000
    assert 0.0 < harness.CONFIDENCE_LEVEL < 1.0
    assert "correctness" in harness.CORRECTNESS_GATE.lower()
    assert "confirmed" in harness.DECISION_VERDICTS
    assert any("held-out" in criterion for criterion in harness.SUPPORT_CRITERIA)
    assert "authorization" in harness.AUTHORIZATION.lower()


def test_contract_is_deterministic_and_serializable() -> None:
    first = harness.contract()
    second = harness.contract()
    assert first == second
    assert json.loads(json.dumps(first)) == first
    assert first["protocol"] == harness.PROTOCOL
    assert [arm["id"] for arm in first["arms"]] == list(harness.CANONICAL_ARM_IDS)


def test_verify_passes_on_the_frozen_contract() -> None:
    assert harness.verify() == []


def test_verify_detects_arm_drift(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(harness, "CANONICAL_ARM_IDS", ("repository-only", "oracle"))
    problems = harness.verify()
    assert any("arm ids drifted" in problem for problem in problems)


def test_verify_detects_a_family_partition_gap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        harness,
        "CURATION_GROUPS",
        (("admission", ("admission",)),),
    )
    problems = harness.verify()
    assert any("partition" in problem for problem in problems)
