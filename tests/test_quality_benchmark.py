"""Contract tests for the embedding and clustering quality gate.

The gate measures the optional layer on the committed ``TAS-089`` corpus and
records one keep/revise/revert verdict per answer. The real measurement imports
the optional ``semantic`` extra, so these tests drive the same pipeline with an
injected embedder, clusterer, and reducer, and verify the committed evidence
offline. Nothing here imports a heavy module or touches the network.
"""

from __future__ import annotations

import hashlib
import json
import os
import shutil
import sqlite3
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

import pytest

from braintree import embedding_benchmark, main
from braintree import quality_benchmark as harness

# Benchmark verification scores the committed corpus, so it is opt-in.
pytestmark = pytest.mark.benchmark

_ROOT = Path(__file__).resolve().parents[1]
_WIDTH = 8
_HEAVY_MODULES = (
    "numpy",
    "sklearn",
    "umap",
    "hdbscan",
    "fastembed",
    "onnxruntime",
    "torch",
    "sentence_transformers",
)
# Driving the gate in a fresh interpreter is the only way to observe the real
# import graph. Every command below is a default-install path that must answer
# without the optional extra, and the probe reports what it loaded.
_IMPORT_PROBE = """\
import sys
from braintree import main, quality_benchmark

assert main.main(["--help"]) == 0
assert main.main(["benchmark", "quality", "--help"]) == 0
assert quality_benchmark.verify() == []
print("heavy:" + ",".join(name for name in sys.argv[1:] if name in sys.modules))
"""


def _embed(texts: Sequence[str]) -> list[list[float]]:
    """A deterministic stand-in embedder: a hash-derived vector per text."""
    vectors: list[list[float]] = []
    for text in texts:
        digest = hashlib.sha256(text.encode("utf-8")).digest()
        vectors.append([digest[index % len(digest)] / 255.0 for index in range(_WIDTH)])
    return vectors


def _reducer(
    provider: str, matrix: Sequence[Sequence[float]], params: object
) -> list[list[float]]:
    """A deterministic two-dimensional stand-in reduction."""
    return [[row[0], row[1]] for row in matrix]


def _clusterer(
    matrix: Sequence[Sequence[float]], params: object
) -> tuple[list[int], list[float]]:
    """A deterministic stand-in clusterer: split by the first coordinate."""
    labels = [0 if row[0] < 0.5 else 1 for row in matrix]
    scores = [abs(row[0] - 0.5) for row in matrix]
    return labels, scores


def _emit_offline(corpus: embedding_benchmark.Corpus | None = None) -> harness.Json:
    """Run the whole gate offline with the deterministic stand-ins."""
    return harness.emit(
        embed=_embed,
        clusterer=_clusterer,
        reducer=_reducer,
        connection=sqlite3.connect(":memory:"),
        corpus=corpus,
    )


def _retrieval_record(
    near_embedding: float, near_lexical: float, para_embedding: float, para_lexical: float
) -> dict[str, object]:
    def metrics(mrr: float) -> dict[str, float]:
        return {"probes": 30, "mrr": mrr, "recall@1": 0.0, "recall@5": 0.0, "recall@10": 0.0}

    return {
        "near-duplicate": {
            "lexical": metrics(near_lexical),
            "embedding": metrics(near_embedding),
        },
        "paraphrase": {"lexical": metrics(para_lexical), "embedding": metrics(para_embedding)},
    }


def _clustering_record(
    stability: float, agreement: float, noise: int, members: int = 100
) -> dict[str, object]:
    return {
        "space": "raw",
        "members": members,
        "noise": noise,
        "stability": [{"space": "raw", "runs": 10, "ari": stability}],
        "route_agreement": {"ari": agreement},
        "outlier": {"default": {"flagged": 0}},
    }


def test_corpus_routes_resolve_from_the_committed_bodies() -> None:
    corpus = embedding_benchmark.load_corpus()
    routes = harness.document_routes(corpus)
    assert set(routes) == {document.id for document in corpus.documents}
    known = {document.id for document in corpus.documents}
    resolved = [route for route in routes.values() if route]
    assert resolved, "no committed document names a primary route"
    assert set(resolved) <= known
    assert any(route == "IDX-001" for route in routes.values())


def test_retrieval_scores_both_rankings_on_the_same_probes() -> None:
    corpus = embedding_benchmark.load_corpus()
    vectors = harness._provider_vectors(corpus, _embed)
    records = harness.measure_retrieval(corpus, vectors)
    assert set(records) >= {"overall", "near-duplicate", "paraphrase"}
    for family, record in records.items():
        probes = [probe for probe in corpus.probes if family == "overall" or probe.family == family]
        assert record["probes"] == len(probes)
        assert record["lexical"] == embedding_benchmark.metrics_for(
            embedding_benchmark.lexical_orders(corpus, probes), probes
        ).as_record()
        difference = record["embedding"]["mrr"] - record["lexical"]["mrr"]
        assert abs(record["delta"]["mrr"] - difference) < 0.001


def test_clustering_reports_stability_agreement_and_outliers() -> None:
    corpus = embedding_benchmark.load_corpus()
    vectors = harness._provider_vectors(corpus, _embed)
    record = harness.measure_clustering(
        corpus,
        vectors,
        harness.document_routes(corpus),
        clusterer=_clusterer,
        reducer=_reducer,
        connection=sqlite3.connect(":memory:"),
    )
    assert record["members"] == len(corpus.documents)
    assert record["stability"]
    assert 0.0 <= record["route_agreement"]["ari"] <= 1.0
    assert 0.0 <= record["route_agreement"]["purity"] <= 1.0
    default = record["outlier"]["default"]
    assert default["true_outliers"] + default["false_outliers"] == default["flagged"]
    assert [row["threshold"] for row in record["outlier"]["sweep"]] == [
        0.9,
        0.8,
        0.7,
        0.6,
        0.5,
        0.4,
    ]


def test_clustering_refuses_an_empty_embedding_set() -> None:
    empty = embedding_benchmark.Corpus(
        protocol=embedding_benchmark.PROTOCOL,
        nodes_root="",
        revision="",
        documents=(),
        probes=(),
    )
    with pytest.raises(harness._QualityError):
        harness.measure_clustering(empty, {}, {}, connection=sqlite3.connect(":memory:"))


def test_retrieval_verdict_keeps_revises_or_reverts() -> None:
    keep = harness._retrieval_decision(_retrieval_record(0.60, 0.55, 0.20, 0.18))
    revise = harness._retrieval_decision(_retrieval_record(0.44, 0.58, 0.25, 0.18))
    revert = harness._retrieval_decision(_retrieval_record(0.44, 0.58, 0.15, 0.18))
    assert [keep.verdict, revise.verdict, revert.verdict] == ["keep", "revise", "revert"]


def test_clustering_verdict_reads_all_three_bars() -> None:
    keep = harness._clustering_decision(_clustering_record(0.6, 0.4, 10))
    weak_agreement = harness._clustering_decision(_clustering_record(0.6, 0.03, 10))
    too_much_noise = harness._clustering_decision(_clustering_record(0.6, 0.4, 65))
    unstable = harness._clustering_decision(_clustering_record(0.2, 0.4, 10))
    assert [d.verdict for d in (keep, weak_agreement, too_much_noise, unstable)] == [
        "keep",
        "revise",
        "revise",
        "revert",
    ]


def test_digest_verdict_needs_a_passing_gate() -> None:
    passing = {"verb_gate": {"passed": True, "cases": [{"case": "digest", "exit": 0}]}}
    failing = {"verb_gate": {"passed": True, "cases": [{"case": "digest", "exit": 1}]}}
    assert harness._digest_decision(passing).verdict == "keep"
    assert harness._digest_decision(failing).verdict == "revert"


def test_emit_is_deterministic_offline_with_injected_inputs() -> None:
    first = _emit_offline()
    second = _emit_offline()
    assert first == second
    assert first["protocol"] == harness.PROTOCOL
    assert set(first["decisions"]) == {"retrieval", "clustering", "digest"}
    assert first["answer_surface"]["verb_gate"]["passed"] is True
    assert first["answer_surface"]["capability_absent"]["line"] == 'clusters: "capability absent"'
    assert first["retrieval"]["near-duplicate"]["lexical"]["mrr"] == 0.5856
    assert first["corpus"]["documents"] == len(embedding_benchmark.load_corpus().documents)


def test_verify_passes_on_the_committed_evidence() -> None:
    assert harness.verify() == []


def test_verify_reports_a_corrupted_evidence(tmp_path: Path) -> None:
    benchmark = tmp_path / "benchmark"
    benchmark.mkdir()
    for relative in (
        embedding_benchmark.CORPUS_RELATIVE,
        embedding_benchmark.DOCUMENTS_RELATIVE,
    ):
        shutil.copy(_ROOT / relative, benchmark / Path(relative).name)
    shutil.copy(_ROOT / harness.EVIDENCE_RELATIVE, benchmark / Path(harness.EVIDENCE_RELATIVE).name)
    shutil.copy(_ROOT / "benchmark" / "verb-baseline.json", benchmark / "verb-baseline.json")
    assert harness.verify(tmp_path) == []

    evidence_path = tmp_path / harness.EVIDENCE_RELATIVE
    document = json.loads(evidence_path.read_text(encoding="utf-8"))
    document["decisions"]["clustering"] = {"decision": "maybe", "rationale": ""}
    document["retrieval"]["near-duplicate"]["lexical"]["mrr"] = 0.0
    evidence_path.write_text(json.dumps(document), encoding="utf-8")
    problems = harness.verify(tmp_path)
    assert any("decision malformed for clustering" in problem for problem in problems)
    assert any("lexical baseline drifts" in problem for problem in problems)


def test_verify_reports_a_missing_evidence(tmp_path: Path) -> None:
    assert harness.verify(tmp_path) == [f"missing committed evidence: {harness.EVIDENCE_RELATIVE}"]


def test_quality_verify_command_reports_the_decisions(capsys: pytest.CaptureFixture[str]) -> None:
    assert harness.main(["verify"]) == 0
    out = capsys.readouterr().out
    assert "verification: passed" in out
    assert "quality{retrieval,decision}: retrieval," in out


def test_quality_rejects_unknown_arguments(capsys: pytest.CaptureFixture[str]) -> None:
    assert harness.main(["frobnicate"]) == 2
    assert "unknown argument: frobnicate" in capsys.readouterr().err


def test_benchmark_quality_is_dispatched(capsys: pytest.CaptureFixture[str]) -> None:
    assert main.main(["--help"]) == 0
    assert (
        "benchmark token|behavioral|storage|verbs|staged|embedding|quality"
        in capsys.readouterr().out
    )


def test_default_install_imports_no_heavy_module() -> None:
    """The default install verifies the evidence with no heavy import."""
    env = dict(os.environ)
    env["BT_MODEL_CACHE"] = "/nonexistent-model-cache"
    probe = subprocess.run(
        [sys.executable, "-c", _IMPORT_PROBE, *_HEAVY_MODULES],
        cwd=str(_ROOT),
        env=env,
        capture_output=True,
        text=True,
    )
    assert probe.returncode == 0, probe.stderr
    report = [line for line in probe.stdout.splitlines() if line.startswith("heavy:")]
    assert report == ["heavy:"]
