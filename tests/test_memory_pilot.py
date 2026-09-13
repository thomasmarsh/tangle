"""Preregistration tests for the bounded separability pilot.

The pilot subset is a pure function of the frozen corpus, so these tests pin it
offline: the 8-12 bound, full family and curation-group coverage, the
required/control mix, determinism, and the prose preregistration's agreement
with the module. Everything here makes zero live model calls.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from braintree import memory_contract, memory_corpus, memory_scenario

_ROOT = Path(__file__).resolve().parents[1]
_DOCUMENT = _ROOT / "research" / "agent-memory-pilot-preregistration.md"


def _subset() -> tuple[memory_scenario.Scenario, ...]:
    return memory_corpus.pilot_subset(memory_corpus.load_corpus())


def _all_case_ids() -> set[str]:
    return {case.case_id for envelope in memory_corpus.load_corpus() for case in envelope.cases}


def _never_control(case: memory_scenario.Scenario) -> bool:
    del case
    return False


def test_pilot_protocol_arms_and_verdicts_are_literal() -> None:
    assert memory_corpus.PILOT_PROTOCOL == "memory-pilot-v1"
    assert memory_corpus.PILOT_ARMS == ("repository-only", "oracle")
    assert memory_corpus.PILOT_VERDICTS == ("proceed", "revise", "stop")
    for arm in memory_corpus.PILOT_ARMS:
        assert arm in memory_contract.CANONICAL_ARM_IDS
    assert memory_corpus.MIN_PILOT_CASES <= memory_corpus.MAX_PILOT_CASES


def test_pilot_subset_is_bounded_and_spans_every_family_and_group() -> None:
    subset = _subset()
    assert memory_corpus.MIN_PILOT_CASES <= len(subset) <= memory_corpus.MAX_PILOT_CASES
    assert {case.family for case in subset} == set(memory_contract.SCENARIO_FAMILIES)
    assert {memory_scenario.curation_group(case.family) for case in subset} == {
        group for group, _ in memory_contract.CURATION_GROUPS
    }
    assert memory_corpus.pilot_problems(memory_corpus.load_corpus()) == []


def test_pilot_subset_is_development_only_and_mixes_required_and_control() -> None:
    subset = _subset()
    assert all(case.split == "development" for case in subset)
    controls = [case for case in subset if memory_corpus.is_control(case)]
    required = [case for case in subset if not memory_corpus.is_control(case)]
    assert controls
    assert required
    assert len(controls) + len(required) == len(subset)
    assert len({case.case_id for case in subset}) == len(subset)


def test_pilot_subset_is_deterministic() -> None:
    first = [case.case_id for case in _subset()]
    second = [case.case_id for case in memory_corpus.pilot_subset(memory_corpus.load_corpus())]
    assert first == second


def test_pilot_problems_detect_a_missing_control(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(memory_corpus, "is_control", _never_control)
    problems = memory_corpus.pilot_problems(memory_corpus.load_corpus())
    assert any("control" in problem for problem in problems)


def test_pilot_problems_detect_an_out_of_range_subset(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(memory_corpus, "MIN_PILOT_CASES", 99)
    problems = memory_corpus.pilot_problems(memory_corpus.load_corpus())
    assert any("outside" in problem for problem in problems)


def test_document_preregisters_exactly_the_selected_cases() -> None:
    text = _DOCUMENT.read_text(encoding="utf-8")
    selected = {case.case_id for case in _subset()}
    listed = {case_id for case_id in _all_case_ids() if case_id in text}
    assert listed == selected


def test_document_records_protocol_arms_and_verdicts() -> None:
    text = _DOCUMENT.read_text(encoding="utf-8")
    assert memory_corpus.PILOT_PROTOCOL in text
    for arm in memory_corpus.PILOT_ARMS:
        assert arm in text, arm
    for verdict in memory_corpus.PILOT_VERDICTS:
        assert verdict in text, verdict


def test_document_records_the_authorization_gate() -> None:
    text = _DOCUMENT.read_text(encoding="utf-8")
    assert memory_contract.AUTHORIZATION in text
