"""Zero-live tests for the confirmatory held-out evaluation.

These tests pin the confirmatory protocol and split map, the whole-frozen
held-out case selection, the confirmatory plan geometry and content-addressed
pins, the confirmatory analysis label and decision path, and the
preregistration document. Every test is offline and makes zero live model
calls.
"""

from __future__ import annotations

import json
from collections import Counter
from pathlib import Path
from typing import Any

import pytest

from tangle import (
    memory_causal,
    memory_contract,
    memory_corpus,
    memory_pilot,
    memory_scenario,
)

_ROOT = Path(__file__).resolve().parents[1]
_DOCUMENT = _ROOT / "research" / "agent-memory-confirmatory-preregistration.md"
_MANIFEST = _ROOT / "benchmark" / "memory-corpus" / "manifest.json"


def _corpus() -> tuple[memory_corpus.Envelope, ...]:
    return memory_corpus.load_corpus()


def _held_out() -> tuple[memory_scenario.Scenario, ...]:
    return memory_causal.held_out_cases(_corpus())


def _manifest_held_out() -> list[str]:
    manifest: dict[str, Any] = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    return list(manifest["splits"]["held-out"])


# --------------------------------------------------------------------------- #
# Protocol and split map
# --------------------------------------------------------------------------- #


def test_confirmatory_protocol_and_split_map() -> None:
    assert memory_causal.CAUSAL_CONFIRMATORY_PROTOCOL == "memory-causal-confirmatory-v1"
    assert memory_causal.CAUSAL_CONFIRMATORY_SPLIT == "held-out"
    assert memory_causal.CAUSAL_SPLIT_PROTOCOLS == {
        "development": memory_causal.CAUSAL_PROTOCOL,
        "held-out": memory_causal.CAUSAL_CONFIRMATORY_PROTOCOL,
    }
    assert set(memory_causal.CAUSAL_SPLIT_PROTOCOLS) == set(memory_contract.SPLITS)
    assert memory_causal.verify() == []


def test_unknown_split_is_rejected() -> None:
    with pytest.raises(memory_causal.CausalError):
        memory_causal.plan_document(split="future")
    assert any("future" in problem for problem in memory_causal.plan_problems(split="future"))
    assert any("future" in problem for problem in memory_causal.dry_run_problems(split="future"))


# --------------------------------------------------------------------------- #
# The frozen held-out case set
# --------------------------------------------------------------------------- #


def test_held_out_case_set_is_the_whole_frozen_split() -> None:
    cases = _held_out()
    assert sorted(case.case_id for case in cases) == _manifest_held_out()
    assert len(cases) == 24
    assert {case.split for case in cases} == {"held-out"}
    assert len({case.case_id for case in cases}) == len(cases)


def test_held_out_case_set_spans_families_groups_and_controls() -> None:
    cases = _held_out()
    families = Counter(case.family for case in cases)
    assert set(families) == set(memory_contract.SCENARIO_FAMILIES)
    for family in memory_contract.SCENARIO_FAMILIES:
        assert families[family] >= 1, family
    group_of = {
        family: group
        for group, group_families in memory_contract.CURATION_GROUPS
        for family in group_families
    }
    groups = Counter(group_of[case.family] for case in cases)
    assert set(groups) == {group for group, _ in memory_contract.CURATION_GROUPS}
    controls = [case for case in cases if memory_corpus.is_control(case)]
    assert controls
    assert len([case for case in cases if not memory_corpus.is_control(case)]) == 19
    assert len(controls) == 5


def test_held_out_selection_is_deterministic() -> None:
    corpus = _corpus()
    first = memory_causal.held_out_cases(corpus)
    second = memory_causal.held_out_cases(corpus)
    assert [case.case_id for case in first] == [case.case_id for case in second]


# --------------------------------------------------------------------------- #
# Plan geometry and content-addressed pins
# --------------------------------------------------------------------------- #


def test_confirmatory_plan_geometry() -> None:
    plan = memory_causal.plan_document(split="held-out")
    assert plan["protocol"] == memory_causal.CAUSAL_CONFIRMATORY_PROTOCOL
    assert plan["split"] == "held-out"
    assert plan["case_count"] == 24
    assert plan["arm_count"] == 5
    assert plan["model_count"] == 3
    assert plan["sample_count"] == 24 * 5 * 3 * 3
    assert plan["sample_count"] == 1080
    assert plan["batch_count"] == 18
    keys = [episode["key"] for episode in plan["episodes"]]
    assert len(keys) == len(set(keys)) == 1080
    counts = Counter(episode["batch"] for episode in plan["episodes"])
    assert set(counts) == set(range(1, 19))
    assert all(count <= memory_causal.CAUSAL_BATCH_SIZE for count in counts.values())
    assert memory_causal.plan_problems(split="held-out") == []


def test_confirmatory_plan_is_content_addressed_with_confirmatory_pins() -> None:
    first = memory_causal.plan_document(split="held-out")
    second = memory_causal.plan_document(split="held-out")
    assert first["plan_digest"] == second["plan_digest"]
    assert first["plan_digest"] == memory_causal.plan_digest(first)
    assert set(first["pins"]) == set(memory_contract.PIN_FIELDS)
    assert first["pins"]["protocol"] == memory_causal.CAUSAL_CONFIRMATORY_PROTOCOL
    assert first["pins"]["model"] == ",".join(memory_causal.CAUSAL_MODELS)


def test_development_and_confirmatory_plans_are_distinct() -> None:
    development = memory_causal.plan_document()
    confirmatory = memory_causal.plan_document(split="held-out")
    assert development["protocol"] == memory_causal.CAUSAL_PROTOCOL
    assert development["split"] == "development"
    assert development["sample_count"] == 540
    assert development["batch_count"] == 9
    assert development["plan_digest"] != confirmatory["plan_digest"]
    assert memory_causal.plan_problems() == []


# --------------------------------------------------------------------------- #
# Confirmatory analysis and incomplete runs
# --------------------------------------------------------------------------- #


def test_confirmatory_dry_run_is_complete_and_confirmatory() -> None:
    assert memory_causal.dry_run_problems(split="held-out") == []
    result = memory_causal.dry_run(split="held-out")
    assert result["status"] == "complete"
    assert result["evidence"] == "confirmatory"
    assert result["decision"] == "confirmed"
    assert result["split"] == "held-out"
    assert result["protocol"] == memory_causal.CAUSAL_CONFIRMATORY_PROTOCOL
    assert result["sample_count"] == 1080
    assert memory_causal.result_problems(result) == []


def test_confirmatory_result_accepts_confirmatory_protocol() -> None:
    plan = memory_causal.plan_document(split="held-out")
    samples = memory_causal._synthetic_samples(plan, _ROOT)
    result = memory_causal.record(plan, samples, _ROOT)
    assert result["protocol"] == memory_causal.CAUSAL_CONFIRMATORY_PROTOCOL
    assert memory_causal.result_problems(result) == []


def test_incomplete_confirmatory_run_is_untested() -> None:
    plan = memory_causal.plan_document(split="held-out")
    samples = memory_causal._synthetic_samples(plan, _ROOT)
    dropped = plan["episodes"][0]["key"]
    samples = [sample for sample in samples if sample["key"] != dropped]
    result = memory_causal.record(plan, samples, _ROOT)
    assert result["status"] == "incomplete"
    assert result["evidence"] == "untested"
    assert result["decision"] == "untested"
    assert result["missing_keys"] == [dropped]
    assert memory_causal.result_problems(result) == []


def test_all_correct_confirmatory_run_has_no_improvement_and_is_rejected() -> None:
    plan = memory_causal.plan_document(split="held-out")
    corpus = memory_corpus.load_corpus(_ROOT)
    cases = {case.case_id: case for envelope in corpus for case in envelope.cases}
    samples = []
    for episode in plan["episodes"]:
        case = cases[episode["case_id"]]
        samples.append(
            {
                "key": episode["key"],
                "child_run_id": f"synthetic-{episode['key']}",
                "raw_output_ref": "synthetic",
                "started_at": "2026-09-13T00:00:00Z",
                "finished_at": "2026-09-13T00:00:12Z",
                "model": episode["model"],
                "prompt_digest": episode["prompt_digest"],
                "raw_output": json.dumps({"action": case.grading.expected_outcome}),
                "telemetry": {
                    **{
                        metric: 1
                        for metric in memory_pilot.REQUIRED_TELEMETRY
                        if metric != "monetary_cost"
                    },
                    "monetary_cost": 0.0,
                },
            }
        )
    result = memory_causal.record(plan, samples, _ROOT)
    assert result["status"] == "complete"
    assert result["evidence"] == "confirmatory"
    assert result["decision"] == "rejected"


# --------------------------------------------------------------------------- #
# CLI and the preregistration document
# --------------------------------------------------------------------------- #


def test_cli_held_out_split(capsys: Any) -> None:
    assert memory_causal.main(["plan", "--split", "held-out"]) == 0
    out = capsys.readouterr().out
    assert memory_causal.CAUSAL_CONFIRMATORY_PROTOCOL in out
    assert "held-out" in out
    assert memory_causal.main(["dry-run", "--split", "held-out"]) == 0
    dry = capsys.readouterr().out
    assert "dry-run: passed" in dry
    assert "confirmatory" in dry
    assert memory_causal.main(["plan", "--split", "bogus"]) == 1
    assert memory_causal.main(["plan", "extra"]) == 1


def test_document_preregisters_confirmatory_protocol() -> None:
    text = _DOCUMENT.read_text(encoding="utf-8")
    assert memory_causal.CAUSAL_CONFIRMATORY_PROTOCOL in text
    assert memory_causal.CAUSAL_CONFIRMATORY_SPLIT in text
    assert memory_contract.AUTHORIZATION in text
    for arm in memory_causal.CAUSAL_ARMS:
        assert arm in text, arm
    for model in memory_causal.CAUSAL_MODELS:
        assert model in text, model
    for token in (
        "held_out_cases",
        "--split held-out",
        "memory-causal-confirmatory-result.json",
        "scripts/memory_causal_run.py",
        "1,080",
        "18",
        "keep-existing-evidence",
    ):
        assert token in text, token
