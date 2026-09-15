"""Committed separability-pilot result: structure and grader agreement.

The pilot ran once against the frozen corpus and its verdict is evidence, not a
recomputation. These tests pin the pins, coverage, and the deterministic grader
agreement offline; they make zero live model calls.
"""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any, cast

from tangle import memory_corpus, memory_scenario

_ROOT = Path(__file__).resolve().parents[1]
_RESULT = _ROOT / "benchmark" / "memory-pilot-result.json"

# Cases the v1 pilot ran that the round-3 corpus repair has since replaced. The
# result stays frozen historical evidence; these samples have no live grader.
_HISTORICAL_ONLY = frozenset({"implicit-retrieval-after-decision-derived-membership-001"})


def _result() -> dict[str, Any]:
    return cast(dict[str, Any], json.loads(_RESULT.read_text(encoding="utf-8")))


def test_result_pins_protocol_model_and_verdict() -> None:
    result = _result()
    assert result["protocol"] == memory_corpus.PILOT_PROTOCOL
    assert result["model"]
    assert result["reasoning_effort"]
    assert result["grader"] == "memory_scenario.grade"
    assert result["verdict"] in memory_corpus.PILOT_VERDICTS


def test_result_covers_every_preregistered_case_and_arm() -> None:
    result = _result()
    cases = {sample["case_id"] for sample in result["samples"]}
    assert result["case_count"] == len(cases) == 12
    assert result["sample_count"] == 2 * len(cases) == len(result["samples"])
    keys = {(sample["case_id"], sample["arm"]) for sample in result["samples"]}
    assert keys == {(case_id, arm) for case_id in cases for arm in memory_corpus.PILOT_ARMS}
    # The v1 result is historical: its subset predates the round-3 corpus repair.
    assert _HISTORICAL_ONLY <= cases


def test_result_correctness_agrees_with_the_committed_grader() -> None:
    result = _result()
    cases = {
        case.case_id: case for envelope in memory_corpus.load_corpus() for case in envelope.cases
    }
    for sample in result["samples"]:
        case = cases.get(sample["case_id"])
        if case is None:
            # A case the round-3 repair replaced has no live committed grader.
            assert sample["case_id"] in _HISTORICAL_ONLY
            continue
        assert sample["control"] == memory_corpus.is_control(case)
        assert sample["expected_outcome"] == case.grading.expected_outcome
        assert sample["correct"] == memory_scenario.grade(case, sample["action"]).correct
