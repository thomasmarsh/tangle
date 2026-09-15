"""Whole-corpus validation, split, leakage, and digest tests.

These tests freeze the whole gold memory corpus as one validated, reproducibly
split, content-addressed artifact. The first group proves the committed corpus
and its manifest are valid; the second mutates one invariant at a time and
proves the validator reports it, so no invariant can silently regress. Every
test is offline and makes zero live model calls.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path
from typing import Any

import pytest

from tangle import memory_corpus as corpus
from tangle import memory_scenario as schema

_ROOT = Path(__file__).resolve().parents[1]
_MANIFEST = _ROOT / corpus.CORPUS_DIR_RELATIVE / corpus.MANIFEST_NAME
_DOCUMENT = _ROOT / "research" / "agent-memory-corpus-validation.md"


def _documents() -> dict[str, dict[str, Any]]:
    documents: dict[str, dict[str, Any]] = copy.deepcopy(corpus.load_documents())
    return documents


def _cases(documents: dict[str, dict[str, Any]], family: str) -> list[dict[str, Any]]:
    cases = documents[family]["cases"]
    assert isinstance(cases, list)
    return cases


def _find(documents: dict[str, dict[str, Any]], case_id: str) -> dict[str, Any]:
    for envelope in documents.values():
        cases: list[dict[str, Any]] = envelope["cases"]
        for case in cases:
            if case["case_id"] == case_id:
                return case
    raise AssertionError(f"missing case {case_id}")


def _mutate(case_id: str, mutate: Any) -> dict[str, dict[str, Any]]:
    documents = _documents()
    mutate(_find(documents, case_id))
    return documents


def _envelope(document: dict[str, Any]) -> corpus.Envelope:
    return corpus.Envelope(
        family=document["family"],
        corpus_version=corpus.expected_corpus_version(document["family"]),
        schema_version=schema.SCENARIO_SCHEMA_VERSION,
        source_revision=document["source_revision"],
        cases=(schema.parse_scenario(document),),
    )


def _scenario(
    case_id: str,
    family: str = "admission",
    *,
    split: str = "development",
    observable: tuple[str, ...] = ("AGENTS.md",),
    hidden: tuple[str, ...] = ("SKILL.md",),
    task: str = "Decide the next action for the caller.",
) -> dict[str, Any]:
    return {
        "schema_version": schema.SCENARIO_SCHEMA_VERSION,
        "case_id": case_id,
        "family": family,
        "split": split,
        "severity": "major",
        "source_revision": "0d56bc7",
        "construction": {
            "episodes": [
                {
                    "id": "ep-1",
                    "sequence": 1,
                    "kind": "observation",
                    "statement": "A hidden fact governs the caller.",
                    "evidence": list(hidden),
                }
            ]
        },
        "query": {
            "task": task,
            "observable_paths": list(observable),
            "allowed_actions": ["act-on-current-evidence", "do-something-else"],
        },
        "grading": {
            "grader": "action-exact",
            "expected_outcome": "act-on-current-evidence",
            "acceptable_actions": ["act-on-current-evidence"],
            "gold_evidence": [
                {
                    "id": "gold-1",
                    "statement": "The hidden fact decides the correct next action.",
                    "source_episodes": ["ep-1"],
                }
            ],
        },
    }


# --- the valid corpus and its committed manifest ----------------------------


def test_committed_corpus_validates() -> None:
    assert corpus.validate(_documents()) == []


def test_committed_corpus_has_no_leakage() -> None:
    assert corpus.leakage(corpus.load_corpus()) == []


def test_committed_manifest_verifies_offline() -> None:
    assert corpus.verify() == []


def test_committed_manifest_matches_a_re_derivation() -> None:
    committed = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    assert committed == corpus.build_manifest(corpus.load_corpus())


def test_case_count_and_digest_are_recorded() -> None:
    documents = _documents()
    loaded = corpus.parse_documents(documents)
    manifest = corpus.build_manifest(loaded)
    assert manifest["cases"] == sum(len(envelope.cases) for envelope in loaded)
    assert corpus.MIN_TOTAL_CASES <= manifest["cases"] <= corpus.MAX_TOTAL_CASES
    assert manifest["digest"] == corpus.corpus_digest(loaded)
    assert manifest["digest"].startswith("sha256:")


def test_digest_is_deterministic() -> None:
    first = corpus.build_manifest(corpus.load_corpus())
    second = corpus.build_manifest(corpus.load_corpus())
    assert first == second
    assert first["digest"] == second["digest"]


def test_digest_changes_when_a_case_changes() -> None:
    original = corpus.corpus_digest(corpus.load_corpus())
    documents = _mutate(
        "admission-discard-current-code-fact-001",
        lambda case: case["query"].__setitem__("task", "A rewritten task."),
    )
    assert corpus.corpus_digest(corpus.parse_documents(documents)) != original


def test_family_digests_are_distinct_and_stable() -> None:
    digests = [corpus.family_digest(envelope) for envelope in corpus.load_corpus()]
    assert len(digests) == len(set(digests))
    assert digests == [corpus.family_digest(envelope) for envelope in corpus.load_corpus()]


def test_prose_authority_agrees_with_the_corpus() -> None:
    text = _DOCUMENT.read_text(encoding="utf-8")
    assert corpus.PROTOCOL in text
    assert corpus.CORPUS_DIR_RELATIVE in text
    assert "tangle benchmark corpus verify" in text
    assert "tangle benchmark corpus freeze" in text
    assert "observable_paths" in text
    for family in schema.SCENARIO_FAMILIES:
        assert family in text, family
    for growth in corpus.GROWTH_CLASSES:
        assert growth in text, growth


def test_manifest_problems_reports_each_drift() -> None:
    recomputed = corpus.build_manifest(corpus.load_corpus())
    for key in ("protocol", "cases", "digest", "families", "splits", "controls", "growth", "audit"):
        committed = dict(recomputed)
        committed[key] = "drifted"
        assert any(key in problem for problem in corpus.manifest_problems(committed, recomputed))


def test_verify_reports_a_missing_manifest(tmp_path: Path) -> None:
    problems = corpus.verify(_ROOT)
    assert problems == []
    assert corpus.verify(tmp_path) == ["missing corpus directory: benchmark/memory-corpus"]


def test_load_documents_rejects_a_missing_directory(tmp_path: Path) -> None:
    with pytest.raises(corpus.CorpusError):
        corpus.load_documents(tmp_path)


# --- structural validation failures -----------------------------------------


def test_missing_envelope_is_reported() -> None:
    documents = _documents()
    del documents["admission"]
    assert any("missing family file admission.json" in p for p in corpus.validate(documents))


def test_unknown_envelope_is_reported() -> None:
    documents = _documents()
    documents["bogus"] = {"schema_version": schema.SCENARIO_SCHEMA_VERSION}
    assert any("unknown family file bogus.json" in p for p in corpus.validate(documents))


def test_wrong_envelope_schema_version_is_reported() -> None:
    documents = _documents()
    documents["admission"]["schema_version"] = "memory-scenario-v9"
    assert any("schema_version must be" in p for p in corpus.validate(documents))


def test_wrong_envelope_corpus_version_is_reported() -> None:
    documents = _documents()
    documents["admission"]["corpus_version"] = "memory-admission-corpus-v9"
    assert any("corpus_version must be" in p for p in corpus.validate(documents))


def test_envelope_family_mismatch_is_reported() -> None:
    documents = _documents()
    documents["admission"]["family"] = "resumption"
    assert any("family must be admission" in p for p in corpus.validate(documents))


def test_bad_source_revision_is_reported() -> None:
    documents = _documents()
    documents["admission"]["source_revision"] = "!!"
    problems = corpus.validate(documents)
    assert any("source_revision is not a revision" in p for p in problems)


def test_duplicate_case_id_is_reported() -> None:
    documents = _documents()
    clone = copy.deepcopy(_cases(documents, "admission")[0])
    clone["family"] = "cascading-invalidation"
    clone["source_revision"] = documents["cascading-invalidation"]["source_revision"]
    documents["cascading-invalidation"]["cases"].append(clone)
    assert any("duplicate id" in p for p in corpus.validate(documents))


def test_case_family_mismatch_is_reported() -> None:
    documents = _documents()
    _find(documents, "admission-discard-current-code-fact-001")["family"] = "resumption"
    assert any("differs from envelope admission" in p for p in corpus.validate(documents))


def test_case_source_revision_mismatch_is_reported() -> None:
    documents = _mutate(
        "admission-discard-current-code-fact-001",
        lambda case: case.__setitem__("source_revision", "deadbee"),
    )
    assert any("source_revision differs" in p for p in corpus.validate(documents))


def test_missing_cited_path_is_reported() -> None:
    documents = _mutate(
        "admission-discard-current-code-fact-001",
        lambda case: case["construction"]["episodes"][0].__setitem__(
            "evidence", ["does/not/exist.md"]
        ),
    )
    assert any("cited path does not exist" in p for p in corpus.validate(documents))


def test_status_move_does_not_break_a_node_citation() -> None:
    """A ``.tangle`` citation resolves by node name across status directories."""
    documents = _documents()
    case = _find(documents, "resumption-handoff-corpus-continuation-001")
    node_paths = [
        path
        for episode in case["construction"]["episodes"]
        for path in episode["evidence"]
        if path.startswith(".tangle/")
    ]
    assert node_paths
    assert all(corpus.path_exists(_ROOT, path) for path in node_paths)
    # A cited status directory may be stale after a move; the name is the identity.
    moved = ".tangle/proposed/TAS-135-corpus-validator-splits.md"
    assert corpus.path_exists(_ROOT, moved)
    assert not (_ROOT / moved).exists()


def test_episode_order_is_reported() -> None:
    documents = _mutate(
        "admission-retain-owner-compression-constraint-001",
        lambda case: case["construction"]["episodes"][1].__setitem__("sequence", 1),
    )
    assert any("episode order" in p for p in corpus.validate(documents))


def test_gold_source_unknown_episode_is_reported() -> None:
    documents = _mutate(
        "admission-discard-current-code-fact-001",
        lambda case: case["grading"]["gold_evidence"][0].__setitem__("source_episodes", ["ep-404"]),
    )
    assert any("unknown episodes" in p for p in corpus.validate(documents))


def test_unknown_grader_is_reported() -> None:
    documents = _mutate(
        "admission-discard-current-code-fact-001",
        lambda case: case["grading"].__setitem__("grader", "action-magic"),
    )
    assert any("grading.grader must be" in p for p in corpus.validate(documents))


def test_unsupported_observable_path_is_reported() -> None:
    documents = _mutate(
        "admission-discard-current-code-fact-001",
        lambda case: case["query"].__setitem__("observable_paths", ["../secrets.env"]),
    )
    assert any("not a repository-relative path" in p for p in corpus.validate(documents))


def test_family_below_minimum_count_is_reported() -> None:
    documents = _documents()
    documents["conflict-and-uncertainty"]["cases"] = _cases(documents, "conflict-and-uncertainty")[
        :2
    ]
    assert any("below the 3 minimum" in p for p in corpus.validate(documents))


def test_total_count_outside_the_admitted_range_is_reported() -> None:
    documents = _documents()
    for envelope in documents.values():
        envelope["cases"] = envelope["cases"][:1]
    assert any("outside 40..60" in p for p in corpus.validate(documents))


def test_family_missing_a_split_is_reported() -> None:
    documents = _documents()
    for case in _cases(documents, "temporal-update"):
        case["split"] = "development"
    assert any("no held-out cases" in p for p in corpus.validate(documents))


def test_unbalanced_family_split_is_reported() -> None:
    documents = _documents()
    for case in _cases(documents, "cascading-invalidation")[:3]:
        case["split"] = "development"
    assert any("split cascading-invalidation: unbalanced" in p for p in corpus.validate(documents))


def test_unbalanced_outcome_stratum_is_reported() -> None:
    documents = _documents()
    moved = 0
    for case in _cases(documents, "admission"):
        if case["case_id"].startswith("admission-retain") and case["split"] == "held-out":
            case["split"] = "development"
            moved += 1
    assert moved == 2
    assert any("split stratum admission/retain" in p for p in corpus.validate(documents))


def test_incident_crossing_splits_is_reported() -> None:
    documents = _documents()
    original = _find(documents, "admission-retain-owner-compression-constraint-001")
    variant = copy.deepcopy(original)
    variant["case_id"] = "admission-retain-owner-compression-constraint-002"
    variant["split"] = "held-out"
    documents["admission"]["cases"].append(variant)
    problems = corpus.validate(documents)
    assert any(
        "split incident admission-retain-owner-compression-constraint" in p for p in problems
    )


def test_missing_controls_are_reported() -> None:
    documents = _documents()
    for envelope in documents.values():
        for case in envelope["cases"]:
            scenario = schema.parse_scenario(case)
            if corpus.is_control(scenario):
                case["query"]["observable_paths"] = ["SKILL.md"]
    problems = corpus.validate(documents)
    assert any("no memory-irrelevant control" in p for p in problems)
    assert any("families carry controls" in p for p in problems)


def test_missing_growth_class_is_reported() -> None:
    documents = _documents()
    for case in _cases(documents, "forgetting-and-interference"):
        if "irrelevant-growth" in case["case_id"]:
            case["case_id"] = "forgetting-and-interference-irrelevant-volume-001"
    assert any("misses ['irrelevant-growth']" in p for p in corpus.validate(documents))


def test_conflict_norm_citation_is_enforced() -> None:
    documents = _documents()
    for case in _cases(documents, "conflict-and-uncertainty"):
        for episode in case["construction"]["episodes"]:
            episode["evidence"] = ["AGENTS.md"]
        case["query"]["observable_paths"] = ["src/tangle/quality_benchmark.py"]
    problems = corpus.validate(documents)
    assert any("does not cite research/agent-memory-theory-evaluation.md" in p for p in problems)


# --- leakage failures -------------------------------------------------------


def test_answer_in_the_task_is_reported() -> None:
    documents = _mutate(
        "admission-discard-current-code-fact-001",
        lambda case: case["query"].__setitem__(
            "task", "Decide whether to discard-observation now."
        ),
    )
    problems = corpus.leakage(corpus.parse_documents(documents))
    assert any("expected outcome appears in the task" in p for p in problems)


def test_node_id_in_the_task_is_reported() -> None:
    documents = _mutate(
        "admission-discard-current-code-fact-001",
        lambda case: case["query"].__setitem__("task", "Resolve TAS-999 before acting."),
    )
    assert any("names a node id" in p for p in corpus.leakage(corpus.parse_documents(documents)))


def test_wikilink_in_the_task_is_reported() -> None:
    documents = _mutate(
        "admission-discard-current-code-fact-001",
        lambda case: case["query"].__setitem__("task", "Resolve [[TAS-999]] first."),
    )
    assert any("carries a wikilink" in p for p in corpus.leakage(corpus.parse_documents(documents)))


def test_gold_statement_copied_into_the_task_is_reported() -> None:
    def mutate(case: dict[str, Any]) -> None:
        statement = case["grading"]["gold_evidence"][0]["statement"]
        case["query"]["task"] = statement

    documents = _mutate("admission-discard-current-code-fact-001", mutate)
    assert any(
        "gold statement is copied into the task" in p
        for p in corpus.leakage(corpus.parse_documents(documents))
    )


def test_gold_evidence_restating_an_episode_is_reported() -> None:
    def mutate(case: dict[str, Any]) -> None:
        case["grading"]["gold_evidence"][0]["statement"] = case["construction"]["episodes"][0][
            "statement"
        ]

    documents = _mutate("admission-discard-current-code-fact-001", mutate)
    assert any(
        "gold evidence restates a construction episode" in p
        for p in corpus.leakage(corpus.parse_documents(documents))
    )


def test_answer_and_gold_written_into_an_observable_file_is_reported(
    tmp_path: Path,
) -> None:
    document = _scenario(
        "admission-leak-check-001",
        family="admission",
        observable=("obs.md",),
        hidden=("obs.md",),
    )
    observed = tmp_path / "obs.md"
    observed.write_text(
        "The hidden fact decides the correct next action, so act on current evidence "
        "and act on current evidence.\n",
        encoding="utf-8",
    )
    envelope = _envelope(document)
    problems = corpus.leakage((envelope,), root=tmp_path)
    assert any("the expected action is written in obs.md" in p for p in problems)
    assert any("a gold phrase is written in obs.md" in p for p in problems)


def test_gold_phrase_in_an_observable_file_is_reported(tmp_path: Path) -> None:
    document = _scenario(
        "admission-leak-phrase-001",
        family="admission",
        observable=("obs.md",),
        hidden=("obs.md",),
    )
    observed = tmp_path / "obs.md"
    observed.write_text(
        "The hidden fact decides the correct next action for the caller.\n",
        encoding="utf-8",
    )
    envelope = _envelope(document)
    problems = corpus.leakage((envelope,), root=tmp_path)
    assert any("a gold phrase is written in obs.md" in p for p in problems)


# --- helpers and CLI --------------------------------------------------------


def test_source_incident_groups_sequence_variants() -> None:
    assert (
        corpus.source_incident("admission-retain-owner-compression-constraint-001")
        == "admission-retain-owner-compression-constraint"
    )
    assert corpus.source_incident("no-trailing-sequence") == "no-trailing-sequence"


def test_outcome_label_uses_the_admission_verb_and_otherwise_the_outcome() -> None:
    admission = schema.parse_scenario(
        _find(_documents(), "admission-retain-owner-compression-constraint-001")
    )
    assert corpus.outcome_label(admission) == "retain"
    temporal = schema.parse_scenario(_find(_documents(), "temporal-update-cosmetic-edit-001"))
    assert corpus.outcome_label(temporal) == temporal.grading.expected_outcome


def test_control_balance_reports_the_curated_distribution() -> None:
    balance = corpus.control_balance(corpus.load_corpus())
    assert balance["admission"]["observable-only-controls"] == 8
    assert balance["resumption"]["observable-only-controls"] == 1
    assert balance["implicit-retrieval"]["observable-only-controls"] == 2
    assert balance["temporal-update"]["memory-required"] == 4


def test_split_manifest_is_sorted_and_complete() -> None:
    manifest = corpus.split_manifest(corpus.load_corpus())
    assert set(manifest) == set(schema.SPLITS)
    for split, case_ids in manifest.items():
        assert case_ids == sorted(case_ids)
        assert case_ids, split
    assert len(manifest["development"]) + len(manifest["held-out"]) == 53


def test_cli_verify_passes_and_bad_arguments_exit_two(capsys: pytest.CaptureFixture[str]) -> None:
    assert corpus.main(["verify"]) == 0
    assert "verification: passed" in capsys.readouterr().out
    assert corpus.main([]) == 2
    assert corpus.main(["bogus"]) == 2
    assert corpus.main(["--help"]) == 0
    assert corpus.main(["verify", "extra"]) == 2


def test_cli_freeze_round_trips_the_committed_manifest(
    capsys: pytest.CaptureFixture[str], monkeypatch: pytest.MonkeyPatch
) -> None:
    committed = _MANIFEST.read_text(encoding="utf-8")
    written: list[str] = []

    def capture(self: Path, data: str, *args: Any, **kwargs: Any) -> int:
        written.append(data)
        return len(data)

    monkeypatch.setattr(Path, "write_text", capture)
    assert corpus.main(["freeze"]) == 0
    assert written == [committed]
    capsys.readouterr()
