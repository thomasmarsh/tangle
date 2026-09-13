"""Contract tests for the embedding model and runtime selection harness.

The harness freezes a retrieval corpus, scores the lexical ``braintree similar``
baseline on it, and compares candidate off-the-shelf models. The real comparison
is an explicit batch run that downloads weights and imports the optional
``semantic`` extra, so these tests drive the same pipeline with an injected
embedder: the lexical metric re-expressed as dense vectors, which must reproduce
the shipped lexical baseline exactly. Nothing here imports torch, fastembed, or
any other heavy module, and nothing here touches the network.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from collections.abc import Sequence
from pathlib import Path

import pytest

from braintree import embedding_benchmark as harness
from braintree import index, main

# Benchmark verification scores the committed corpus, so it is opt-in.
pytestmark = pytest.mark.benchmark

_ROOT = Path(__file__).resolve().parents[1]
_HEAVY_MODULES = ("torch", "sentence_transformers", "fastembed", "onnxruntime")

# Driving the harness in a fresh interpreter is the only way to observe the real
# import graph. Every command below is a default-install path that must answer
# without the optional extra, and the probe reports what it loaded.
_IMPORT_PROBE = """\
import sys
from braintree import embedding_benchmark, main

assert main.main(["--help"]) == 0
assert main.main(["benchmark", "embedding", "--help"]) == 0
assert main.main(["benchmark", "embedding", "corpus", "--verify"]) == 0
assert embedding_benchmark.load_corpus().documents
print("heavy:" + ",".join(name for name in sys.argv[1:] if name in sys.modules))
"""


def _lexical_vectors(
    corpus: harness.Corpus, probes: Sequence[harness.Probe]
) -> harness.Embedder:
    """Return an embedder whose cosine is exactly the shipped lexical metric.

    Every token the corpus and the probes use becomes one dimension, so a text
    is the dense form of the same lowercased token counts
    :func:`braintree.index._similar_lexical` compares, and vector cosine equals
    token-count cosine. This makes the whole scoring pipeline checkable offline:
    if the harness ranks by anything other than the shipped metric, the two
    results diverge.
    """
    texts = [document.text() for document in corpus.documents]
    texts.extend(probe.query for probe in probes)
    vocabulary = sorted({token for text in texts for token in index._token_counts(text)})

    def encode(values: Sequence[str]) -> list[list[float]]:
        vectors: list[list[float]] = []
        for value in values:
            counts = index._token_counts(value)
            vectors.append([float(counts.get(token, 0)) for token in vocabulary])
        return vectors

    return harness.Embedder(
        runtime="lexical-fake",
        query=encode,
        passage=encode,
        import_seconds=0.0,
        load_seconds=0.0,
    )


def test_corpus_command_verifies_the_committed_files(
    capsys: pytest.CaptureFixture[str],
) -> None:
    assert harness.main(["corpus", "--verify"]) == 0
    out = capsys.readouterr().out
    assert "verification: passed" in out
    assert "families{near-duplicate,paraphrase}" in out
    assert "splits{dev,heldout}" in out


def test_committed_corpus_is_valid_and_held_out() -> None:
    corpus = harness.load_corpus()
    assert harness.verify_corpus(corpus, _ROOT) == []
    assert len(corpus.documents) >= 100
    assert len(corpus.probes) >= 8
    for family in {probe.family for probe in corpus.probes}:
        dev = {probe.positives[0] for probe in corpus.probes if probe.family == family
               and probe.split == "dev"}
        heldout = {probe.positives[0] for probe in corpus.probes if probe.family == family
                   and probe.split == "heldout"}
        assert dev and heldout
        assert not dev & heldout


def test_verify_reports_a_missing_positive(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    corpus = harness.load_corpus()
    broken = harness.Corpus(
        protocol=corpus.protocol,
        nodes_root=corpus.nodes_root,
        revision=corpus.revision,
        documents=corpus.documents,
        probes=(
            harness.Probe(
                id="paraphrase-999",
                family="paraphrase",
                split="dev",
                query="anything",
                positives=("TAS-999",),
                negatives=(),
                exclude=(),
            ),
        ),
    )
    problems = harness.verify_corpus(broken, tmp_path)
    assert any("unknown document TAS-999" in problem for problem in problems)
    assert any("too few probes" in problem for problem in problems)


def test_metrics_math() -> None:
    probes = (
        harness.Probe("a", "paraphrase", "dev", "q", ("X",), (), ()),
        harness.Probe("b", "paraphrase", "dev", "q", ("Y",), (), ()),
        harness.Probe("c", "paraphrase", "heldout", "q", ("Z",), (), ()),
    )
    perfect = harness.metrics_for({"a": ["X"], "b": ["Y"], "c": ["Z"]}, probes)
    assert perfect.as_record() == {
        "probes": 3,
        "mrr": 1.0,
        "recall@1": 1.0,
        "recall@5": 1.0,
        "recall@10": 1.0,
    }
    mixed = harness.metrics_for({"a": ["Q", "X"], "b": ["Q", "Y"], "c": []}, probes)
    assert mixed.mrr == pytest.approx(1 / 3)
    assert mixed.recall_at_1 == 0.0
    assert mixed.recall_at_5 == pytest.approx(2 / 3)


def test_lexical_order_matches_the_shipped_similar_baseline(tmp_path: Path) -> None:
    """The harness ranks with the same metric ``braintree similar`` ships."""
    corpus = harness.load_corpus()
    nodes = [
        index.IndexedNode(
            id=document.id,
            name=document.name,
            path=f"{document.status}/{document.name}.md",
            status=document.status,
            metadata={"summary": document.summary},
            body=document.body,
        )
        for document in corpus.documents
    ]
    probe = corpus.probes[0]
    shipped = [
        candidate.id
        for candidate in index._similar_lexical(nodes, probe.query, len(nodes))
    ]
    harness_order = harness._lexical_order(
        corpus.documents, probe.query, frozenset(probe.exclude)
    )
    assert harness_order == [node_id for node_id in shipped if node_id not in probe.exclude]


def test_evaluate_reproduces_the_lexical_baseline() -> None:
    """A vector embedder equal to the lexical metric scores exactly the baseline."""
    corpus = harness.load_corpus()
    probes = corpus.probes
    expected = harness.metrics_for(
        harness.lexical_orders(corpus, probes), probes
    ).as_record()
    measured = harness.evaluate(corpus, probes, _lexical_vectors(corpus, probes))
    assert measured["metrics"]["overall"] == expected  # type: ignore[index]


def test_evidence_reproduces_the_recorded_lexical_baseline() -> None:
    """The committed evidence's lexical row is recomputable from the corpus."""
    evidence = json.loads((_ROOT / harness.EVIDENCE_RELATIVE).read_text(encoding="utf-8"))
    corpus = harness.load_corpus()
    batch = evidence["batch"]
    options = harness.RunOptions(
        models=tuple(batch["models"]) if batch["models"] != ["all"] else (),
        runtimes=tuple(batch["runtimes"]),
        limit=batch["limit"],
        probes_limit=batch["probes_limit"],
        time_budget=batch["time_budget"],
    )
    probes = harness._selected_probes(corpus, options)
    rebuilt = harness._split_records(harness.lexical_orders(corpus, probes), probes)
    assert rebuilt == evidence["lexical"]
    assert evidence["corpus"]["digest"] == harness._corpus_digest(_ROOT)
    assert evidence["corpus"]["source_revision"] == corpus.revision


def test_run_records_every_candidate_when_the_extra_is_absent() -> None:
    """A missing extra is recorded per candidate, never dropped or raised."""

    def unavailable(
        candidate: harness.Candidate, cache_dir: Path, local_only: bool
    ) -> harness.Embedder:
        raise ImportError("No module named 'sentence_transformers'")

    corpus = harness.load_corpus()
    options = harness.RunOptions(runtimes=("sentence-transformers",), probes_limit=6)
    document = harness.run(
        corpus,
        options,
        embedders={"sentence-transformers": unavailable},
        cache_dir=Path("/nonexistent"),
    )
    records = document["records"]
    assert isinstance(records, list)
    assert len(records) == len(harness.CANDIDATES)
    for record in records:
        assert record["status"] == "unavailable"
        assert "sentence_transformers" in record["reason"]
    lexical = document["lexical"]
    assert isinstance(lexical, dict)
    overall = lexical["overall"]
    assert isinstance(overall, dict)
    assert overall["probes"] == 6


def test_run_records_an_unlisted_model_for_the_onnx_runtime() -> None:
    """A runtime that cannot serve a candidate says so instead of guessing."""

    def unlisted(
        candidate: harness.Candidate, cache_dir: Path, local_only: bool
    ) -> harness.Embedder:
        raise harness._CandidateUnavailable(f"fastembed does not list {candidate.model}")

    document = harness.run(
        harness.load_corpus(),
        harness.RunOptions(runtimes=("fastembed",), probes_limit=2),
        embedders={"fastembed": unlisted},
        cache_dir=Path("/nonexistent"),
    )
    records = document["records"]
    assert isinstance(records, list)
    assert all(record["status"] == "unavailable" for record in records)
    assert all("does not list" in str(record["reason"]) for record in records)


def test_time_budget_marks_the_remainder_skipped() -> None:
    """An exhausted budget stops the batch and names why."""

    def never_loaded(
        candidate: harness.Candidate, cache_dir: Path, local_only: bool
    ) -> harness.Embedder:
        raise AssertionError("the time budget must stop the batch before loading")

    document = harness.run(
        harness.load_corpus(),
        harness.RunOptions(runtimes=("sentence-transformers",), time_budget=0.0),
        embedders={"sentence-transformers": never_loaded},
        cache_dir=Path("/nonexistent"),
    )
    records = document["records"]
    assert isinstance(records, list)
    assert records and all(record["status"] == "skipped" for record in records)
    assert all(record["reason"] == "time budget exhausted" for record in records)


def test_probes_limit_spans_both_families() -> None:
    corpus = harness.load_corpus()
    selected = harness._selected_probes(corpus, harness.RunOptions(probes_limit=6))
    assert len(selected) == 6
    assert {probe.family for probe in selected} == {"paraphrase", "near-duplicate"}


def test_corpus_command_reports_a_missing_vault(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    assert harness.main(["corpus", "--nodes", str(tmp_path / "absent"), "--emit"]) == 1
    assert "nodes directory does not exist" in capsys.readouterr().err


def test_usage_errors(capsys: pytest.CaptureFixture[str]) -> None:
    assert harness.main(["bogus"]) == 2
    assert "error: unknown argument: bogus" in capsys.readouterr().err
    assert harness.main(["run", "--models", "not-a-model"]) == 2
    assert "error: unknown model" in capsys.readouterr().err
    assert harness.main(["run", "--runtimes", "not-a-runtime"]) == 2
    assert "error: unknown runtime" in capsys.readouterr().err
    assert harness.main(["semantic", "--verify"]) == 2
    assert "error: unknown argument: semantic" in capsys.readouterr().err


def test_benchmark_embedding_is_dispatched(capsys: pytest.CaptureFixture[str]) -> None:
    assert main.main(["--help"]) == 0
    assert (
        "benchmark token|behavioral|storage|verbs|staged|embedding|quality"
        in capsys.readouterr().out
    )


def test_default_install_imports_no_heavy_module(tmp_path: Path) -> None:
    """The default install answers the harness commands with no heavy import."""
    env = dict(os.environ)
    env["BT_MODEL_CACHE"] = str(tmp_path / "cache")
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
