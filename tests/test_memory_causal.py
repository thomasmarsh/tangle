"""Zero-live tests for the matched five-arm causal runner.

The first group pins the protocol literals and the arm partition; the second
pins the shared fixtures and the memory-construction semantics; the third pins
the plan, its coverage, and its batch geometry; the fourth pins the
correctness-before-cost gate, the paired bootstrap analysis, the exploratory
label, and incomplete-run handling. Every test is offline and makes zero live
model calls.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from functools import lru_cache
from pathlib import Path
from typing import Any

import pytest

from braintree import (
    memory_causal,
    memory_contract,
    memory_corpus,
    memory_pilot,
    memory_scenario,
)

_ROOT = Path(__file__).resolve().parents[1]


@lru_cache(maxsize=1)
def _plan() -> dict[str, Any]:
    return memory_causal.plan_document()


def _corpus() -> tuple[memory_corpus.Envelope, ...]:
    return memory_corpus.load_corpus()


def _cases() -> dict[str, memory_scenario.Scenario]:
    return {case.case_id: case for envelope in _corpus() for case in envelope.cases}


def _subset() -> tuple[memory_scenario.Scenario, ...]:
    return memory_corpus.pilot_subset(_corpus())


def _required_cases() -> list[memory_scenario.Scenario]:
    return [case for case in _subset() if not memory_corpus.is_control(case)]


def _control_cases() -> list[memory_scenario.Scenario]:
    return [case for case in _subset() if memory_corpus.is_control(case)]


def _action(case: memory_scenario.Scenario, wrong: bool) -> str:
    if not wrong:
        return case.grading.expected_outcome
    acceptable = set(case.grading.acceptable_actions)
    return next(
        candidate for candidate in case.query.allowed_actions if candidate not in acceptable
    )


def _telemetry() -> dict[str, Any]:
    return {
        **{
            metric: 7
            for metric in memory_pilot.REQUIRED_TELEMETRY
            if metric != "monetary_cost"
        },
        "monetary_cost": 0.0,
    }


def _samples(
    plan: dict[str, Any],
    *,
    wrong_keys: set[str] | None = None,
    drop_keys: set[str] | None = None,
    infra_keys: set[str] | None = None,
    bad_output_keys: set[str] | None = None,
    model: str | None = None,
    latency_seconds: int = 12,
) -> list[dict[str, Any]]:
    wrong = wrong_keys or set()
    drop = drop_keys or set()
    infra = infra_keys or set()
    bad_output = bad_output_keys or set()
    cases = _cases()
    start = datetime.fromisoformat("2026-09-13T00:00:00+00:00")
    finish = start + timedelta(seconds=latency_seconds)
    samples: list[dict[str, Any]] = []
    for episode in plan["episodes"]:
        key = episode["key"]
        if key in drop:
            continue
        case = cases[episode["case_id"]]
        sample: dict[str, Any] = {
            "key": key,
            "child_run_id": f"run-{key}",
            "raw_output_ref": f"raw/{key}.txt",
            "started_at": start.isoformat(),
            "finished_at": finish.isoformat(),
            "model": model or episode["model"],
            "prompt_digest": episode["prompt_digest"],
            "raw_output": f'{{"action": "{_action(case, key in wrong)}"}}',
            "telemetry": _telemetry(),
        }
        if key in infra:
            sample["infrastructure_error"] = "child process crashed"
        if key in bad_output:
            sample["raw_output"] = "I cannot answer without more information."
        samples.append(sample)
    return samples


def _keys_for(
    cases: list[memory_scenario.Scenario],
    arm: str,
    *,
    models: tuple[str, ...] | None = None,
    repetitions: tuple[int, ...] = (1, 2, 3),
) -> set[str]:
    selected = models or tuple(_plan()["models"])
    return {
        f"{case.case_id}--{arm}--{model.split('/')[-1]}--r{repetition}"
        for case in cases
        for model in selected
        for repetition in repetitions
    }


# --------------------------------------------------------------------------- #
# Protocol literals and the arm partition
# --------------------------------------------------------------------------- #


def test_protocol_literals_and_verify() -> None:
    assert memory_causal.CAUSAL_PROTOCOL == "memory-causal-v1"
    assert memory_causal.CAUSAL_ARMS == memory_contract.CANONICAL_ARM_IDS
    assert memory_causal.CAUSAL_BASELINE_ARMS == ("repository-only", "raw-history", "flat-memory")
    assert memory_causal.CAUSAL_TREATMENT_ARM == "braintree"
    assert memory_causal.CAUSAL_CEILING_ARM == "oracle"
    assert memory_causal.CAUSAL_MODELS == (
        "deepseek/deepseek-flash",
        "deepseek/deepseek-v4-flash",
        "deepseek/deepseek-v4-pro",
    )
    assert memory_causal.CAUSAL_REPETITIONS == memory_contract.MIN_REPETITIONS
    assert memory_causal.CAUSAL_BOOTSTRAP_RESAMPLES == memory_contract.BOOTSTRAP_RESAMPLES
    assert memory_causal.verify() == []


def test_decision_contrasts_match_the_contract_support_criterion() -> None:
    assert memory_causal.CAUSAL_DECISION_CONTRASTS == (
        ("braintree", "repository-only"),
        ("braintree", "raw-history"),
    )
    assert set(memory_causal.CAUSAL_CONTRASTS) >= set(memory_causal.CAUSAL_DECISION_CONTRASTS)


# --------------------------------------------------------------------------- #
# Shared fixtures and memory construction
# --------------------------------------------------------------------------- #


def test_every_arm_shares_task_observables_and_allowed_actions() -> None:
    case = _required_cases()[0]
    fixtures = [memory_causal.build_fixture(case, arm) for arm in memory_causal.CAUSAL_ARMS]
    reference = fixtures[0]
    for fixture in fixtures:
        assert fixture.task == reference.task
        assert fixture.observable == reference.observable
        assert fixture.allowed_actions == reference.allowed_actions
        assert fixture.case_id == reference.case_id
    assert len({fixture.memory for fixture in fixtures}) == len(memory_causal.CAUSAL_ARMS)


def test_repository_only_has_no_memory_and_oracle_has_the_gold() -> None:
    case = _required_cases()[0]
    assert memory_causal.arm_memory(case, "repository-only") == ()
    assert memory_causal.arm_memory(case, "oracle") == tuple(
        evidence.statement for evidence in case.grading.gold_evidence
    )


def test_braintree_retrieves_the_deciding_chain_and_every_arm_is_bounded() -> None:
    case = _required_cases()[0]
    deciding = {
        source
        for evidence in case.grading.gold_evidence
        for source in evidence.source_episodes
    }
    statements = {
        episode.statement for episode in case.construction.episodes if episode.id in deciding
    }
    assert set(memory_causal.arm_memory(case, "braintree")) <= statements
    for arm in memory_causal.CAUSAL_ARMS:
        assert len(memory_causal.arm_memory(case, arm)) <= memory_causal.CAUSAL_MEMORY_BUDGET


def test_raw_history_and_flat_memory_differ_only_in_framing() -> None:
    case = _required_cases()[0]
    raw = memory_causal.arm_memory(case, "raw-history")
    flat = memory_causal.arm_memory(case, "flat-memory")
    assert len(raw) == len(flat)
    for raw_statement, note in zip(raw, flat, strict=True):
        assert note.endswith(raw_statement)
        assert note.startswith("note ")


def test_unknown_arm_is_rejected() -> None:
    with pytest.raises(memory_causal.CausalError):
        memory_causal.arm_memory(_required_cases()[0], "not-an-arm")


# --------------------------------------------------------------------------- #
# Plan, coverage, and batch geometry
# --------------------------------------------------------------------------- #


def test_plan_covers_every_case_arm_model_and_repetition() -> None:
    plan = _plan()
    cases = _subset()
    expected = sum(
        1
        for case in cases
        for _arm in memory_causal.CAUSAL_ARMS
        for _model in plan["models"]
        for _repetition in range(1, memory_causal.CAUSAL_REPETITIONS + 1)
    )
    assert plan["sample_count"] == expected
    assert plan["case_count"] == len(cases)
    assert plan["arm_count"] == 5
    assert plan["model_count"] == 3
    keys = {episode["key"] for episode in plan["episodes"]}
    assert len(keys) == expected
    assert memory_causal.plan_problems() == []


def test_plan_batches_match_the_preregistered_geometry() -> None:
    plan = _plan()
    counts = Counter(episode["batch"] for episode in plan["episodes"])
    assert set(counts) == set(range(1, memory_causal.CAUSAL_BATCH_COUNT + 1))
    assert all(count <= memory_causal.CAUSAL_BATCH_SIZE for count in counts.values())
    assert sum(counts.values()) == plan["sample_count"]


def test_plan_is_deterministic_and_content_addressed() -> None:
    first = _plan()
    second = memory_causal.plan_document()
    assert first["plan_digest"] == second["plan_digest"]
    assert first["plan_digest"] == memory_causal.plan_digest(first)
    assert set(first["pins"]) == set(memory_contract.PIN_FIELDS)
    assert first["pins"]["model"] == ",".join(memory_causal.CAUSAL_MODELS)


def test_plan_rejects_underpowered_launches() -> None:
    with pytest.raises(memory_causal.CausalError):
        memory_causal.build_plan(models=("deepseek/deepseek-v4-flash",))
    with pytest.raises(memory_causal.CausalError):
        memory_causal.build_plan(repetitions=2)


# --------------------------------------------------------------------------- #
# Correctness gate, paired analysis, and incomplete runs
# --------------------------------------------------------------------------- #


def test_bootstrap_interval_is_deterministic_and_ordered() -> None:
    values = [1.0, 0.0, 1.0, 0.0, 1.0]
    low, high = memory_causal.bootstrap_confidence_interval(values, resamples=1000)
    repeat_low, repeat_high = memory_causal.bootstrap_confidence_interval(values, resamples=1000)
    assert (low, high) == (repeat_low, repeat_high)
    assert low <= high
    assert low <= 0.6 <= high
    constant_low, constant_high = memory_causal.bootstrap_confidence_interval(
        [1.0, 1.0, 1.0], resamples=1000
    )
    assert (constant_low, constant_high) == (1.0, 1.0)


def test_bootstrap_rejects_too_few_resamples() -> None:
    with pytest.raises(memory_causal.CausalError):
        memory_causal.bootstrap_confidence_interval([1.0], resamples=10)


def test_correctness_before_cost_gate_excludes_incorrect_arms() -> None:
    plan = _plan()
    wrong = _keys_for(list(_subset()), "repository-only")
    result = memory_causal.record(plan, _samples(plan, wrong_keys=wrong))
    assert result["status"] == "complete"
    bare = result["costs"]["repository-only"]
    treated = result["costs"]["braintree"]
    per_model = len(plan["models"]) * memory_causal.CAUSAL_REPETITIONS
    assert bare["admitted"] == 0
    assert sum(bare["tokens"].values()) == 0
    assert treated["admitted"] == plan["case_count"] * per_model
    assert sum(treated["tokens"].values()) > 0
    assert memory_causal.result_problems(result) == []


def test_memory_required_cases_produce_a_positive_treatment_effect() -> None:
    plan = _plan()
    wrong = _keys_for(_required_cases(), "repository-only")
    result = memory_causal.record(plan, _samples(plan, wrong_keys=wrong))
    contrast = next(
        record
        for record in result["contrasts"]
        if record["treatment"] == "braintree" and record["baseline"] == "repository-only"
    )
    assert contrast["mean_effect"] == len(_required_cases()) / plan["case_count"]
    assert contrast["ci_low"] > 0
    assert contrast["decision_contrast"] is True


def test_development_evidence_is_always_exploratory() -> None:
    plan = _plan()
    wrong = _keys_for(_required_cases(), "repository-only")
    result = memory_causal.record(plan, _samples(plan, wrong_keys=wrong))
    assert result["evidence"] == "exploratory"
    assert result["decision"] == "exploratory"
    assert result["split"] == "development"


def test_missing_sample_is_incomplete_and_never_decides() -> None:
    plan = _plan()
    dropped = plan["episodes"][0]["key"]
    result = memory_causal.record(plan, _samples(plan, drop_keys={dropped}))
    assert result["status"] == "incomplete"
    assert result["decision"] == "untested"
    assert result["evidence"] == "untested"
    assert result["missing_keys"] == [dropped]
    assert memory_causal.result_problems(result) == []


def test_infrastructure_failure_and_wrong_model_are_incomplete() -> None:
    plan = _plan()
    failed = plan["episodes"][0]["key"]
    result = memory_causal.record(plan, _samples(plan, infra_keys={failed}))
    assert result["status"] == "incomplete"
    assert any(failed in reason for reason in result["incomplete_reasons"])
    wrong_model = memory_causal.record(
        plan, _samples(plan, model="deepseek/deepseek-v4-pro")
    )
    assert wrong_model["status"] == "incomplete"


def test_malformed_output_is_a_model_failure_not_infrastructure() -> None:
    plan = _plan()
    bad = plan["episodes"][0]["key"]
    result = memory_causal.record(plan, _samples(plan, bad_output_keys={bad}))
    assert result["status"] == "complete"
    sample = next(record for record in result["samples"] if record["key"] == bad)
    assert sample["incomplete"] is False
    assert sample["parse_error"]
    assert any(failure["key"] == bad for failure in result["failures"])


def test_reproduction_commands_and_pins_are_recorded() -> None:
    result = memory_causal.record(_plan(), _samples(_plan()))
    assert result["reproduction"]
    assert any("benchmark causal plan" in command for command in result["reproduction"])
    assert any("benchmark causal record" in command for command in result["reproduction"])
    assert set(result["pins"]) == set(memory_contract.PIN_FIELDS)
    assert result["correctness_gate"]["gate"] == memory_contract.CORRECTNESS_GATE


def test_dry_run_passes_without_a_live_call() -> None:
    assert memory_causal.dry_run_problems() == []
    result = memory_causal.dry_run()
    assert result["status"] == "complete"
    assert result["evidence"] == "exploratory"
    assert result["sample_count"] == _plan()["sample_count"]


def test_cli_plan_dry_run_and_bad_arguments(capsys: pytest.CaptureFixture[str]) -> None:
    assert memory_causal.main(["plan"]) == 0
    out = capsys.readouterr().out
    assert "memory-causal-v1" in out
    assert memory_causal.main(["dry-run"]) == 0
    assert "dry-run: passed" in capsys.readouterr().out
    assert memory_causal.main([]) == 2
    assert memory_causal.main(["bogus"]) == 2
    assert memory_causal.main(["--help"]) == 0


def test_paired_effects_ignore_incomplete_samples() -> None:
    plan = _plan()
    wrong = _keys_for(_required_cases(), "repository-only")
    samples = _samples(plan, wrong_keys=wrong)
    result = memory_causal.record(plan, samples)
    contrast = memory_causal.paired_effects(result["samples"], "braintree", "repository-only")
    assert contrast["n_strata"] == plan["case_count"] * len(plan["models"])
    assert contrast["mean_effect"] == len(_required_cases()) / plan["case_count"]
    assert memory_causal.paired_effects([], "braintree", "repository-only")["n_pairs"] == 0


# --------------------------------------------------------------------------- #
# Preregistration document
# --------------------------------------------------------------------------- #


def test_document_preregisters_protocol_arms_models_and_gate() -> None:
    document = _ROOT / "research" / "agent-memory-causal-preregistration.md"
    text = document.read_text(encoding="utf-8")
    assert memory_causal.CAUSAL_PROTOCOL in text
    assert memory_contract.AUTHORIZATION in text
    for arm in memory_causal.CAUSAL_ARMS:
        assert arm in text, arm
    for model in memory_causal.CAUSAL_MODELS:
        assert model in text, model
    assert "braintree benchmark causal" in text
    assert "scripts/memory_causal_run.py" in text
    assert ".pi/agents/memory-pilot-child.md" in text
    assert "pilot_subset" in text
    assert "resumption-after-decision-shared-install-001" in text
