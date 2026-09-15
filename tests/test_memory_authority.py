"""Offline tests for the authority, provenance, and injection rate harness.

Everything here makes zero live model calls: the case set, the plan, the rate
aggregation, and the verify gate are all deterministic functions of the
committed files. The live run consumes the same plan and records into the same
schema, so these tests protect the contract the live run must satisfy.
"""

from __future__ import annotations

import json
from pathlib import Path

from tangle import memory_authority as ma
from tangle import memory_contract

_ROOT = Path(__file__).resolve().parents[1]


def _cases() -> tuple[ma.AuthorityCase, ...]:
    return ma.load_cases(_ROOT)


def test_protocol_arms_and_verdicts_are_literal() -> None:
    assert ma.AUTHORITY_PROTOCOL == "memory-authority-v1"
    assert ma.AUTHORITY_SCHEMA_VERSION == "memory-authority-v1"
    assert ma.AUTHORITY_ARMS == ("plain", "provenance", "filtered", "oracle")
    assert ma.AUTHORITY_DECISION_ARMS == (("provenance", "plain"), ("filtered", "provenance"))
    assert ma.AUTHORITY_DECISION_VERDICTS == (
        "adopt-sparse-provenance",
        "keep-existing-evidence",
        "untested",
    )
    assert ma.AUTHORITY_REPETITIONS >= memory_contract.MIN_REPETITIONS
    assert ma.AUTHORITY_MODEL == "deepseek/deepseek-v4-flash"


def test_case_set_is_valid_and_leak_free() -> None:
    cases = _cases()
    assert ma.validate(cases, _ROOT) == []
    assert ma.leakage(cases, _ROOT) == []
    assert len(cases) == 12


def test_case_set_covers_every_provenance_class() -> None:
    classes = {
        name
        for case in _cases()
        for episode in case.episodes
        for name in (episode.source_class, episode.origin)
    }
    assert classes == set(ma.SOURCE_CLASSES)


def test_case_set_covers_every_behavior() -> None:
    behaviors = {case.behavior for case in _cases()}
    assert behaviors == set(ma.BEHAVIORS)
    assert {"clarify", "abstain", "preserve-alternatives", "refuse-escalation"} <= behaviors


def test_case_set_partitions_injection_forms_and_balances_splits() -> None:
    cases = _cases()
    forms = {
        form: sum(1 for case in cases if case.injection == form) for form in ma.INJECTION_FORMS
    }
    assert forms["direct"] == 3
    assert forms["laundered"] == 3
    assert forms["none"] == 6
    development = sum(1 for case in cases if case.split == "development")
    held_out = sum(1 for case in cases if case.split == "held-out")
    assert development == held_out == 6


def test_every_injection_payload_is_untrusted_and_declares_an_instruction() -> None:
    for case in _cases():
        payloads = ma.payload_episodes(case)
        if ma.is_injection(case):
            assert payloads, case.case_id
            assert all(episode.origin == ma.UNTRUSTED_ORIGIN for episode in payloads)
            assert all(episode.claims_authority for episode in payloads)
            assert case.instruction_action is not None
            assert case.instruction_action in case.allowed_actions
            assert case.harmful_actions
        else:
            assert not payloads
            assert case.instruction_action is None


def test_gold_evidence_never_cites_an_injection_payload() -> None:
    for case in _cases():
        payload_ids = {episode.id for episode in ma.payload_episodes(case)}
        cited = {
            source for evidence in case.gold_evidence for source in evidence.source_episodes
        }
        assert not (payload_ids & cited), case.case_id
        assert all(evidence.source_episodes for evidence in case.gold_evidence)


def test_plain_and_provenance_hold_the_same_episodes_but_differ_in_annotation() -> None:
    for case in _cases():
        plain = ma.arm_episodes(case, "plain")
        provenance = ma.arm_episodes(case, "provenance")
        assert [episode.id for episode in plain] == [episode.id for episode in provenance]
        plain_memory = ma.arm_memory(case, "plain")
        provenance_memory = ma.arm_memory(case, "provenance")
        assert plain_memory != provenance_memory
        assert all(item.startswith("[source: ") for item in provenance_memory)
        assert all("[" not in item for item in plain_memory)


def test_filtered_drops_only_untrusted_authority_payloads() -> None:
    for case in _cases():
        kept = {episode.id for episode in ma.arm_episodes(case, "filtered")}
        payloads = {episode.id for episode in ma.payload_episodes(case)}
        assert not (kept & payloads), case.case_id
        for episode in case.episodes:
            if episode.id not in payloads:
                assert episode.id in kept, case.case_id
        if ma.is_injection(case):
            assert ma.arm_memory(case, "filtered") == tuple(
                ma._annotate(episode)
                for episode in case.episodes
                if episode.id not in payloads
            )


def test_oracle_holds_only_gold_source_episodes() -> None:
    for case in _cases():
        required = {
            source for evidence in case.gold_evidence for source in evidence.source_episodes
        }
        assert {episode.id for episode in ma.arm_episodes(case, "oracle")} == required
        assert ma.arm_memory(case, "oracle") == tuple(
            evidence.statement for evidence in case.gold_evidence
        )


def test_case_digest_and_plan_are_deterministic() -> None:
    first = ma.case_digest(_cases())
    second = ma.case_digest(ma.load_cases(_ROOT))
    assert first == second
    assert first.startswith("sha256:")
    plan = ma.plan_document(_ROOT)
    assert plan["plan_digest"] == ma.plan_digest(plan)
    assert plan["sample_count"] == plan["case_count"] * len(ma.AUTHORITY_ARMS) * plan["repetitions"]
    assert plan["batch_count"] * plan["batch_size"] >= plan["sample_count"]
    assert set(plan["pins"]) == set(memory_contract.PIN_FIELDS)


def test_plan_problems_are_empty_and_detect_a_missing_case() -> None:
    assert ma.plan_problems(_ROOT) == []


def test_fixtures_are_arm_neutral_and_digest_bound() -> None:
    cases = {case.case_id: case for case in _cases()}
    plan = ma.plan_document(_ROOT)
    for episode in plan["episodes"]:
        case = cases[episode["case_id"]]
        fixture = ma.build_fixture(case, episode["arm"], _ROOT)
        assert fixture.task == case.task
        assert fixture.allowed_actions == case.allowed_actions
        assert ma.render_prompt(fixture) == ma.render_prompt(
            ma.build_fixture(case, episode["arm"], _ROOT)
        )


def test_dry_run_passes_and_reports_every_rate() -> None:
    result = ma.dry_run(_ROOT)
    assert result["status"] == "complete"
    assert ma.result_problems(result) == []
    assert set(result["rates"]) == set(ma.AUTHORITY_ARMS)
    for arm in ma.AUTHORITY_ARMS:
        block = result["rates"][arm]
        for form in ("overall", "injection", "direct", "laundered"):
            assert isinstance(block[form], dict)
    assert result["rates"]["plain"]["injection"]["write_rate"] == 1.0
    assert result["rates"]["provenance"]["injection"]["write_rate"] == 1.0
    assert result["rates"]["filtered"]["injection"]["write_rate"] == 0.0
    assert result["rates"]["oracle"]["injection"]["write_rate"] == 0.0


def test_dry_run_synthetic_activation_and_harm_are_positive_for_writing_arms() -> None:
    result = ma.dry_run(_ROOT)
    plain = result["rates"]["plain"]["injection"]
    assert plain["delivered_samples"] > 0
    assert plain["activation_rate"] == 1.0
    assert plain["harmful_action_rate"] == 1.0
    filtered = result["rates"]["filtered"]["injection"]
    assert filtered["activation_rate"] is None
    assert filtered["harmful_action_rate"] == 0.0
    assert filtered["correctness_rate"] == 1.0


def test_record_requires_every_planned_episode() -> None:
    plan = ma.plan_document(_ROOT)
    result = ma.record(plan, [], _ROOT)
    assert result["status"] == "incomplete"
    assert result["decision"] == "untested"
    assert len(result["missing_keys"]) == plan["sample_count"]


def test_decision_requires_a_positive_held_out_correctness_interval() -> None:
    def contrast(
        treatment: str, baseline: str, endpoint: str, low: float | None, high: float | None
    ) -> dict[str, object]:
        return {
            "treatment": treatment,
            "baseline": baseline,
            "endpoint": endpoint,
            "splits": ["held-out"],
            "mean_effect": 0.5,
            "ci_low": low,
            "ci_high": high,
        }

    positive = [
        contrast("provenance", "plain", "action-correctness", 0.2, 0.8),
        contrast("provenance", "plain", "activation", -0.8, -0.2),
        contrast("provenance", "plain", "harmful-action", -0.8, -0.2),
        contrast("filtered", "provenance", "action-correctness", -0.1, 0.1),
    ]
    assert ma._decision("complete", positive)[0] == "adopt-sparse-provenance"
    unsafe = [dict(item) for item in positive]
    unsafe[2] = contrast("provenance", "plain", "harmful-action", -0.1, 0.4)
    assert ma._decision("complete", unsafe)[0] == "keep-existing-evidence"
    flat = [dict(item) for item in positive]
    flat[0] = contrast("provenance", "plain", "action-correctness", -0.1, 0.3)
    assert ma._decision("complete", flat)[0] == "keep-existing-evidence"
    assert ma._decision("incomplete", positive)[0] == "untested"


def test_verify_reports_missing_artifact_or_passes() -> None:
    problems = ma.verify(_ROOT)
    artifact = _ROOT / ma.AUTHORITY_ARTIFACT
    if artifact.is_file():
        assert problems == [], problems
    else:
        assert any("missing authority artifact" in item for item in problems)


def test_cli_plan_dry_run_and_verify() -> None:
    assert ma.main(["plan"]) == 0
    assert ma.main(["dry-run"]) == 0
    assert ma.main([]) == 2
    assert ma.main(["bogus"]) == 2


def test_mutating_a_case_changes_the_digest(tmp_path: Path) -> None:
    document = json.loads((_ROOT / ma.AUTHORITY_CASES).read_text(encoding="utf-8"))
    document["cases"][0]["construction"]["episodes"][0]["statement"] += " Extra sentence."
    target = tmp_path / "corpus"
    (target / "benchmark").mkdir(parents=True)
    (target / "benchmark" / "memory-authority-cases.json").write_text(
        json.dumps(document), encoding="utf-8"
    )
    mutated = ma.load_cases(target)
    assert ma.case_digest(mutated) != ma.case_digest(_cases())
