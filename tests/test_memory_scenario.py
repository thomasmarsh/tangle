"""Schema and grader tests for the versioned memory-evaluation scenario format.

These tests protect the scenario contract the gold corpus and the later harness
must agree on: the schema version, the field separation between memory
construction and query-time visibility, the parser's rejections, arm-neutral
fixtures, the deterministic grader, agreement with the frozen
``braintree.memory_contract``, and the prose document's agreement with the
module. Everything here is offline and imports no model runtime.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from braintree import memory_contract
from braintree import memory_scenario as schema

_ROOT = Path(__file__).resolve().parents[1]
_DOCUMENT = _ROOT / "research" / "agent-memory-scenario-schema.md"


def _document() -> dict[str, Any]:
    return copy.deepcopy(schema.MINIMAL_SCENARIO_DOCUMENT)


def test_schema_version_is_literal() -> None:
    assert schema.SCENARIO_SCHEMA_VERSION == "memory-scenario-v1"
    assert schema.VALID_SCHEMA_VERSIONS == (schema.SCENARIO_SCHEMA_VERSION,)


def test_schema_imports_the_frozen_contract_literals() -> None:
    assert schema.SCENARIO_FAMILIES == memory_contract.SCENARIO_FAMILIES
    assert schema.CURATION_GROUPS == memory_contract.CURATION_GROUPS
    assert schema.SPLITS == memory_contract.SPLITS
    assert schema.ARM_IDS == memory_contract.CANONICAL_ARM_IDS
    assert schema.PRIMARY_ENDPOINT == memory_contract.PRIMARY_ENDPOINTS[0].name
    assert schema.PRIMARY_ENDPOINT == "action-correctness"
    assert schema.CORRECTNESS_GATE == memory_contract.CORRECTNESS_GATE
    assert schema.PIN_FIELDS == memory_contract.PIN_FIELDS
    assert schema.curation_group("temporal-update") == "revision-and-conflict"


def test_minimal_fixture_round_trips() -> None:
    scenario = schema.minimal_scenario()
    document = schema.scenario_document(scenario)
    assert document == schema.MINIMAL_SCENARIO_DOCUMENT
    assert json.loads(json.dumps(document)) == schema.MINIMAL_SCENARIO_DOCUMENT
    assert schema.parse_scenario(document) == scenario


def test_minimal_fixture_records_every_required_field() -> None:
    scenario = schema.minimal_scenario()
    assert scenario.case_id and scenario.family and scenario.split and scenario.severity
    assert scenario.source_revision
    assert [episode.sequence for episode in scenario.construction.episodes] == [1, 2]
    assert all(episode.evidence for episode in scenario.construction.episodes)
    assert scenario.query.task
    assert scenario.query.observable_paths
    assert scenario.query.allowed_actions
    assert scenario.grading.gold_evidence
    assert scenario.grading.expected_outcome in scenario.query.allowed_actions


def test_construction_is_separate_from_query_time_visibility() -> None:
    scenario = schema.minimal_scenario()
    episode_statements = {episode.statement for episode in scenario.construction.episodes}
    gold_statements = {evidence.statement for evidence in scenario.grading.gold_evidence}
    assert not (episode_statements & gold_statements)
    query = schema.scenario_document(scenario)["query"]
    assert set(query) == {"task", "observable_paths", "allowed_actions"}


def test_arm_fixtures_cover_every_arm_with_one_shared_case() -> None:
    scenario = schema.minimal_scenario()
    fixtures = schema.arm_fixtures(scenario)
    assert [fixture.arm_id for fixture in fixtures] == list(memory_contract.CANONICAL_ARM_IDS)
    assert len({fixture.task for fixture in fixtures}) == 1
    assert len({fixture.observable_paths for fixture in fixtures}) == 1
    assert len({fixture.allowed_actions for fixture in fixtures}) == 1
    for fixture in fixtures:
        assert scenario.grading.expected_outcome not in fixture.task
        for action in scenario.query.allowed_actions:
            assert action not in fixture.task
    by_arm = {fixture.arm_id: fixture for fixture in fixtures}
    assert by_arm["repository-only"].memory == ()
    assert by_arm["oracle"].construction == ()
    assert by_arm["oracle"].memory
    assert by_arm["raw-history"].memory
    assert by_arm["flat-memory"].memory


def test_grader_scores_the_primary_endpoint_before_cost() -> None:
    scenario = schema.minimal_scenario()
    good = schema.grade(scenario, scenario.grading.expected_outcome)
    assert good.endpoint == schema.PRIMARY_ENDPOINT
    assert good.correct and good.credit == 1.0 and good.regret == 0.0
    assert schema.cost_eligible(good)
    bad = schema.grade(scenario, "add-second-backoff")
    assert not bad.correct and bad.credit == 0.0
    assert bad.regret == schema.SEVERITY_WEIGHTS[scenario.severity]
    assert not schema.cost_eligible(bad)


def test_acceptable_set_grader_admits_each_declared_action() -> None:
    document = _document()
    document["grading"]["grader"] = "action-acceptable"
    document["grading"]["acceptable_actions"] = [
        "retain-existing-helper",
        "add-second-backoff",
    ]
    scenario = schema.parse_scenario(document)
    assert schema.grade(scenario, "add-second-backoff").correct
    assert not schema.grade(scenario, "discard-observation").correct


def test_parser_rejects_unsupported_schema_version() -> None:
    document = _document()
    document["schema_version"] = "memory-scenario-v2"
    with pytest.raises(schema.ScenarioError, match="unsupported schema version"):
        schema.parse_scenario(document)


def test_parser_rejects_missing_gold_evidence() -> None:
    document = _document()
    document["grading"]["gold_evidence"] = []
    with pytest.raises(schema.ScenarioError, match="gold_evidence is missing"):
        schema.parse_scenario(document)


def test_parser_rejects_episode_without_evidence() -> None:
    document = _document()
    document["construction"]["episodes"][0]["evidence"] = []
    with pytest.raises(schema.ScenarioError, match="evidence"):
        schema.parse_scenario(document)


def test_parser_rejects_invalid_observable_path() -> None:
    document = _document()
    document["query"]["observable_paths"] = ["../secrets.env"]
    with pytest.raises(schema.ScenarioError, match="repository-relative"):
        schema.parse_scenario(document)


def test_parser_rejects_invalid_episode_path() -> None:
    document = _document()
    document["construction"]["episodes"][0]["evidence"] = ["/etc/passwd"]
    with pytest.raises(schema.ScenarioError, match="repository-relative"):
        schema.parse_scenario(document)


def test_parser_rejects_ambiguous_exact_grading() -> None:
    document = _document()
    document["grading"]["acceptable_actions"] = [
        "retain-existing-helper",
        "add-second-backoff",
    ]
    with pytest.raises(schema.ScenarioError, match="ambiguous"):
        schema.parse_scenario(document)


def test_parser_rejects_acceptable_action_outside_allowed() -> None:
    document = _document()
    document["grading"]["grader"] = "action-acceptable"
    document["grading"]["acceptable_actions"] = ["retain-existing-helper", "invent-action"]
    with pytest.raises(schema.ScenarioError, match="outside query.allowed_actions"):
        schema.parse_scenario(document)


def test_parser_rejects_unknown_family() -> None:
    document = _document()
    document["family"] = "not-a-family"
    with pytest.raises(schema.ScenarioError, match="unknown scenario family"):
        schema.parse_scenario(document)


def test_parser_rejects_bad_split() -> None:
    document = _document()
    document["split"] = "training"
    with pytest.raises(schema.ScenarioError, match="split"):
        schema.parse_scenario(document)


def test_parser_rejects_unknown_grader() -> None:
    document = _document()
    document["grading"]["grader"] = "human-review"
    with pytest.raises(schema.ScenarioError, match="grader"):
        schema.parse_scenario(document)


def test_parser_rejects_unknown_gold_source() -> None:
    document = _document()
    document["grading"]["gold_evidence"][0]["source_episodes"] = ["ep-9"]
    with pytest.raises(schema.ScenarioError, match="unknown episodes"):
        schema.parse_scenario(document)


def test_parser_rejects_out_of_order_episodes() -> None:
    document = _document()
    document["construction"]["episodes"][1]["sequence"] = 3
    with pytest.raises(schema.ScenarioError, match="1-based episode order"):
        schema.parse_scenario(document)


def test_parser_rejects_duplicate_episode_ids() -> None:
    document = _document()
    document["construction"]["episodes"][1]["id"] = "ep-1"
    with pytest.raises(schema.ScenarioError, match="duplicated"):
        schema.parse_scenario(document)


def test_verify_passes_on_the_frozen_schema() -> None:
    assert schema.verify() == []


def test_verify_detects_arm_drift(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(schema, "ARM_IDS", ("repository-only", "oracle"))
    problems = schema.verify()
    assert any("arms drifted" in problem for problem in problems)


def test_verify_detects_family_partition_gap(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(schema, "CURATION_GROUPS", (("admission", ("admission",)),))
    problems = schema.verify()
    assert any("partition" in problem for problem in problems)


def test_document_records_the_schema_literals() -> None:
    text = _DOCUMENT.read_text(encoding="utf-8")
    assert schema.SCENARIO_SCHEMA_VERSION in text
    assert schema.PRIMARY_ENDPOINT in text
    for family in schema.SCENARIO_FAMILIES:
        assert family in text, family
    for arm in schema.ARM_IDS:
        assert arm in text, arm
    for severity in schema.SEVERITIES:
        assert severity in text, severity
    for grader in schema.GRADER_IDS:
        assert grader in text, grader
