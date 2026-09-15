"""Zero-live tests for the isolated repeated separability-pilot harness (v2).

The first group pins the protocol literals, the isolated child profile, and the
72-episode plan; the second pins the fixture builder and the output parser; the
third pins the recorder, the paired-majority rule, incomplete-run handling, and
the result schema. Every test is offline and makes zero live model calls.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any

import pytest

from tangle import memory_contract, memory_corpus, memory_pilot, memory_scenario

_ROOT = Path(__file__).resolve().parents[1]
_PROFILE = _ROOT / ".pi" / "agents" / "memory-pilot-child.md"


def _corpus() -> tuple[memory_corpus.Envelope, ...]:
    return memory_corpus.load_corpus()


def _cases() -> dict[str, memory_scenario.Scenario]:
    return {case.case_id: case for envelope in _corpus() for case in envelope.cases}


def _plan() -> dict[str, Any]:
    return memory_pilot.plan_document()


def _required_cases() -> list[memory_scenario.Scenario]:
    return [
        case for case in memory_corpus.pilot_subset(_corpus()) if not memory_corpus.is_control(case)
    ]


def _control_cases() -> list[memory_scenario.Scenario]:
    return [
        case for case in memory_corpus.pilot_subset(_corpus()) if memory_corpus.is_control(case)
    ]


def _key(case_id: str, arm: str, repetition: int) -> str:
    return f"{case_id}--{arm}--r{repetition}"


def _action(case: memory_scenario.Scenario, wrong: bool) -> str:
    if not wrong:
        return case.grading.expected_outcome
    acceptable = set(case.grading.acceptable_actions)
    return next(
        candidate for candidate in case.query.allowed_actions if candidate not in acceptable
    )


def _telemetry() -> dict[str, Any]:
    return {
        **{metric: 7 for metric in memory_pilot.REQUIRED_TELEMETRY if metric != "monetary_cost"},
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
            "model": model or memory_pilot.PILOT_V2_MODEL,
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


def _separating_wrong_keys(cases: list[memory_scenario.Scenario]) -> set[str]:
    wrong: set[str] = set()
    for case in cases:
        for repetition in (1, 2):
            wrong.add(_key(case.case_id, "repository-only", repetition))
    return wrong


def _profile() -> tuple[dict[str, str], str]:
    text = _PROFILE.read_text(encoding="utf-8")
    assert text.startswith("---\n")
    _, frontmatter, body = text.split("---\n", 2)
    fields: dict[str, str] = {}
    for line in frontmatter.splitlines():
        if not line.strip():
            continue
        name, _, value = line.partition(":")
        fields[name.strip()] = value.strip()
    return fields, body.strip("\n")


# --------------------------------------------------------------------------- #
# Protocol, child profile, and plan
# --------------------------------------------------------------------------- #


def test_protocol_literals_are_pinned() -> None:
    assert memory_pilot.PILOT_V2_PROTOCOL == "memory-pilot-v2"
    assert memory_pilot.PILOT_V2_ARMS == ("repository-only", "oracle")
    assert memory_pilot.PILOT_V2_REPETITIONS == 3
    assert memory_pilot.PILOT_V2_SEPARATION_THRESHOLD == 2
    assert memory_pilot.PILOT_V2_CONTROL_THRESHOLD == 2
    assert memory_pilot.PILOT_V2_MODEL == "deepseek/deepseek-v4-flash"
    assert memory_pilot.PILOT_V2_REASONING_EFFORT == "high"
    assert memory_pilot.PILOT_V2_VERDICTS == ("proceed", "revise", "stop")
    assert memory_pilot.verify() == []


def test_child_profile_is_isolated_and_model_pinned() -> None:
    fields, _ = _profile()
    assert fields["name"] == "memory-pilot-child"
    assert fields["tools"] == ""
    assert fields["extensions"] == ""
    assert fields["systemPromptMode"] == "replace"
    assert fields["inheritProjectContext"] == "false"
    assert fields["inheritGlobalContext"] == "false"
    assert fields["inheritSkills"] == "false"
    assert fields["defaultContext"] == "fresh"
    assert fields["model"] == memory_pilot.PILOT_V2_MODEL
    assert fields["thinking"] == memory_pilot.PILOT_V2_REASONING_EFFORT
    assert "fallbackModels" not in fields


def test_child_profile_system_prompt_matches_the_module() -> None:
    _, body = _profile()
    assert body == memory_pilot.SYSTEM_PROMPT


def test_plan_has_72_unique_keyed_episodes_in_three_batches() -> None:
    plan = _plan()
    episodes = plan["episodes"]
    assert len(episodes) == 72
    assert len({episode["key"] for episode in episodes}) == 72
    assert Counter(episode["batch"] for episode in episodes) == {1: 24, 2: 24, 3: 24}
    for episode in episodes:
        assert episode["launch"]["agent"] == memory_pilot.PILOT_V2_CHILD_PROFILE
        assert episode["launch"]["model"] == memory_pilot.PILOT_V2_MODEL
        assert episode["launch"]["thinking"] == memory_pilot.PILOT_V2_REASONING_EFFORT
        assert episode["launch"]["context"] == "fresh"


def test_plan_covers_every_case_arm_and_repetition() -> None:
    plan = _plan()
    keys = {episode["key"] for episode in plan["episodes"]}
    for case in memory_corpus.pilot_subset(_corpus()):
        for arm in memory_pilot.PILOT_V2_ARMS:
            for repetition in range(1, memory_pilot.PILOT_V2_REPETITIONS + 1):
                assert _key(case.case_id, arm, repetition) in keys
    assert plan["case_count"] == 12
    assert plan["sample_count"] == 72


def test_plan_pins_every_contract_field() -> None:
    plan = _plan()
    assert set(plan["pins"]) == set(memory_contract.PIN_FIELDS)
    assert plan["pins"]["model"] == memory_pilot.PILOT_V2_MODEL
    assert plan["pins"]["reasoning-effort"] == memory_pilot.PILOT_V2_REASONING_EFFORT
    assert plan["corpus_digest"] == memory_corpus.corpus_digest(_corpus())


def test_plan_is_deterministic_and_content_addressed() -> None:
    first = _plan()
    second = _plan()
    assert first["plan_digest"] == second["plan_digest"]
    assert first["plan_digest"] == memory_pilot.plan_digest(first)
    assert memory_pilot.plan_problems() == []


# --------------------------------------------------------------------------- #
# Fixtures and the output parser
# --------------------------------------------------------------------------- #


def test_prompt_embeds_observable_bytes_and_only_the_arm_memory() -> None:
    case = _required_cases()[0]
    repository = memory_pilot.build_fixture(case, "repository-only")
    oracle = memory_pilot.build_fixture(case, "oracle")
    repository_prompt = memory_pilot.render_prompt(repository)
    oracle_prompt = memory_pilot.render_prompt(oracle)
    assert repository.observable == oracle.observable
    for item in repository.observable:
        assert item.content.rstrip("\n") in repository_prompt
        assert item.content.rstrip("\n") in oracle_prompt
    assert repository.memory == ()
    assert oracle.memory == tuple(
        evidence.statement for evidence in case.grading.gold_evidence
    )
    for statement in oracle.memory:
        assert statement in oracle_prompt
        assert statement not in repository_prompt


def test_parse_action_accepts_json_and_tolerates_extra_keys() -> None:
    assert memory_pilot.parse_action('{"action": "a"}', ["a"]) == "a"
    assert memory_pilot.parse_action('Sure:\n{"action": "a", "why": "x"}', ["a"]) == "a"


def test_parse_action_rejects_missing_or_disallowed_actions() -> None:
    for raw in ("no object", "{bad json}", '{"other": 1}', '{"action": 1}'):
        with pytest.raises(memory_pilot.PilotOutputError):
            memory_pilot.parse_action(raw, ["a"])
    with pytest.raises(memory_pilot.PilotOutputError):
        memory_pilot.parse_action('{"action": "b"}', ["a"])


# --------------------------------------------------------------------------- #
# Recorder, paired majority, and the result schema
# --------------------------------------------------------------------------- #


def test_record_proceeds_when_every_required_case_separates() -> None:
    plan = _plan()
    wrong = _separating_wrong_keys(_required_cases())
    result = memory_pilot.record(plan, _samples(plan, wrong_keys=wrong))
    assert result["status"] == "complete"
    assert result["verdict"] == "proceed"
    assert memory_pilot.result_problems(result) == []


def test_record_is_stop_when_required_cases_do_not_separate() -> None:
    plan = _plan()
    result = memory_pilot.record(plan, _samples(plan))
    assert result["status"] == "complete"
    assert result["verdict"] == "stop"
    assert all(
        record["classification"] == "fails"
        for record in result["cases"]
        if not record["control"]
    )


def test_record_is_revise_when_one_required_case_fails() -> None:
    plan = _plan()
    required = sorted(_required_cases(), key=lambda case: case.case_id)
    wrong = _separating_wrong_keys(required[1:])
    result = memory_pilot.record(plan, _samples(plan, wrong_keys=wrong))
    assert result["verdict"] == "revise"
    failing = [record for record in result["cases"] if record["classification"] == "fails"]
    assert [record["case_id"] for record in failing] == [required[0].case_id]


def test_separation_requires_two_of_three_paired_repetitions() -> None:
    plan = _plan()
    case = _required_cases()[0]
    one = memory_pilot.record(
        plan, _samples(plan, wrong_keys={_key(case.case_id, "repository-only", 1)})
    )
    two = memory_pilot.record(
        plan,
        _samples(
            plan,
            wrong_keys={
                _key(case.case_id, "repository-only", 1),
                _key(case.case_id, "repository-only", 2),
            },
        ),
    )
    first = next(record for record in one["cases"] if record["case_id"] == case.case_id)
    second = next(record for record in two["cases"] if record["case_id"] == case.case_id)
    assert first["paired_separations"] == 1 and first["classification"] == "fails"
    assert second["paired_separations"] == 2 and second["classification"] == "separates"


def test_control_requires_two_of_three_repository_correct() -> None:
    plan = _plan()
    case = _control_cases()[0]
    one = memory_pilot.record(
        plan, _samples(plan, wrong_keys={_key(case.case_id, "repository-only", 1)})
    )
    two = memory_pilot.record(
        plan,
        _samples(
            plan,
            wrong_keys={
                _key(case.case_id, "repository-only", 1),
                _key(case.case_id, "repository-only", 2),
            },
        ),
    )
    first = next(record for record in one["cases"] if record["case_id"] == case.case_id)
    second = next(record for record in two["cases"] if record["case_id"] == case.case_id)
    assert first["classification"] == "valid"
    assert second["classification"] == "invalid"


def test_case_verdict_stops_when_a_curation_group_cannot_be_retained() -> None:
    records: list[dict[str, Any]] = []
    for case in memory_corpus.pilot_subset(_corpus()):
        control = memory_corpus.is_control(case)
        if case.family in {"resumption", "implicit-retrieval"}:
            classification = "invalid" if control else "fails"
        else:
            classification = "valid" if control else "separates"
        records.append(
            {
                "case_id": case.case_id,
                "family": case.family,
                "control": control,
                "classification": classification,
            }
        )
    assert (
        sum(
            1
            for record in records
            if record["classification"] in {"fails", "invalid"} and not record["control"]
        )
        == 2
    )
    assert memory_pilot.case_verdict(records) == "stop"


def test_missing_sample_makes_a_run_incomplete_without_a_verdict() -> None:
    plan = _plan()
    dropped = plan["episodes"][0]["key"]
    result = memory_pilot.record(plan, _samples(plan, drop_keys={dropped}))
    assert result["status"] == "incomplete"
    assert result["verdict"] is None
    assert result["missing_keys"] == [dropped]
    assert memory_pilot.result_problems(result) == []


def test_infrastructure_failure_makes_a_run_incomplete() -> None:
    plan = _plan()
    failed = plan["episodes"][0]["key"]
    result = memory_pilot.record(plan, _samples(plan, infra_keys={failed}))
    assert result["status"] == "incomplete"
    assert result["verdict"] is None
    assert any(failed in reason for reason in result["incomplete_reasons"])


def test_wrong_model_pin_is_an_infrastructure_failure() -> None:
    plan = _plan()
    result = memory_pilot.record(plan, _samples(plan, model="deepseek/deepseek-v4-pro"))
    assert result["status"] == "incomplete"
    assert any("model" in reason for reason in result["incomplete_reasons"])


def test_malformed_output_is_a_model_failure_not_infrastructure() -> None:
    plan = _plan()
    case = _required_cases()[0]
    key = _key(case.case_id, "repository-only", 1)
    result = memory_pilot.record(plan, _samples(plan, bad_output_keys={key}))
    assert result["status"] == "complete"
    sample = next(record for record in result["samples"] if record["key"] == key)
    assert sample["incomplete"] is False
    assert sample["parse_error"]
    assert sample["correct"] is False


def test_latency_is_computed_and_every_pin_and_telemetry_field_is_retained() -> None:
    plan = _plan()
    wrong = _separating_wrong_keys(_required_cases())
    result = memory_pilot.record(plan, _samples(plan, wrong_keys=wrong, latency_seconds=12))
    sample = result["samples"][0]
    assert sample["telemetry"]["latency_ms"] == 12_000
    assert sample["child_run_id"].startswith("run-")
    assert sample["raw_output_ref"].startswith("raw/")
    for metric in memory_pilot.REQUIRED_TELEMETRY:
        assert metric in sample["telemetry"]
    assert set(result["pins"]) == set(memory_contract.PIN_FIELDS)


def test_self_reported_latency_is_ignored_and_telemetry_errors_are_infrastructure() -> None:
    plan = _plan()
    samples = _samples(plan)
    samples[0]["telemetry"]["latency_ms"] = 999_999
    result = memory_pilot.record(plan, samples)
    sample = next(record for record in result["samples"] if record["key"] == samples[0]["key"])
    assert sample["telemetry"]["latency_ms"] == 12_000
    samples = _samples(plan)
    del samples[0]["telemetry"]["input_tokens"]
    result = memory_pilot.record(plan, samples)
    assert result["status"] == "incomplete"
    assert any("input_tokens" in reason for reason in result["incomplete_reasons"])


def test_result_problems_reject_a_malformed_schema() -> None:
    plan = _plan()
    wrong = _separating_wrong_keys(_required_cases())
    result = memory_pilot.record(plan, _samples(plan, wrong_keys=wrong))
    assert memory_pilot.result_problems(result) == []
    missing = {key: value for key, value in result.items() if key != "pins"}
    assert any("pins" in problem for problem in memory_pilot.result_problems(missing))
    tampered = memory_pilot.record(plan, _samples(plan))
    tampered["samples"][0]["correct"] = None
    assert any("correct" in problem for problem in memory_pilot.result_problems(tampered))


def test_result_problems_accept_complete_revise_stop_and_incomplete_samples() -> None:
    plan = _plan()
    required = sorted(_required_cases(), key=lambda case: case.case_id)
    revise = memory_pilot.record(
        plan, _samples(plan, wrong_keys=_separating_wrong_keys(required[1:]))
    )
    assert revise["verdict"] == "revise"
    assert memory_pilot.result_problems(revise) == []
    stop = memory_pilot.record(plan, _samples(plan))
    assert stop["verdict"] == "stop"
    assert memory_pilot.result_problems(stop) == []
    incomplete = memory_pilot.record(
        plan, _samples(plan, infra_keys={plan["episodes"][0]["key"]})
    )
    assert incomplete["status"] == "incomplete"
    assert memory_pilot.result_problems(incomplete) == []


def test_result_problems_reject_a_verdict_that_contradicts_cases() -> None:
    plan = _plan()
    result = memory_pilot.record(plan, _samples(plan))
    assert result["verdict"] == "stop"
    result["verdict"] = "proceed"
    assert any("verdict" in problem for problem in memory_pilot.result_problems(result))


def test_dry_run_passes_without_a_live_call() -> None:
    assert memory_pilot.dry_run_problems() == []
    result = memory_pilot.dry_run()
    assert result["status"] == "complete"
    assert result["verdict"] == "proceed"
    assert result["sample_count"] == 72
