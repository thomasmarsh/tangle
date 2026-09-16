"""Gate the optional embedding and clustering layer with recorded quality evidence.

The off-the-shelf semantic layer (see TAS-087) is advisory under the
capability-boundary decision, but it still has to earn its cost. This module is
the explicit batch tool that decides: it measures the layer against the lexical
baseline and the graph's own weak labels on one frozen corpus, records the
numbers in ``benchmark/clustering-quality-evidence.json``, and derives a keep,
revise, or revert verdict for each answer the layer backs -- the reranked
retrieval, the advisory clustering, and the graph digest.

Everything is measured on the committed corpus from ``TAS-089``
(``benchmark/embedding-corpus.json`` plus ``benchmark/embedding-documents.jsonl``)
so both the lexical and the embedding side are scored on identical probes and
documents. Three quality signals are reported:

- **Cluster stability** is the mean pairwise Adjusted Rand Index the clustering
  layer already computes across seeds and seeded subsamples; it says whether one
  partition reproduces under resampling.
- **Route agreement** is the same Adjusted Rand Index between the reported
  cluster labels and each node's primary ``Parent``/``Area`` route, plus cluster
  purity. The graph's routes are weak ground truth: a layer whose clusters track
  them is recovering settled structure, and one that does not is at best
  advisory grouping.
- **Outlier precision** treats a node whose primary route is shared by no other
  corpus node as graph-isolated and asks how many reported GLOSH outliers are
  actually isolated. Because the default threshold can flag nothing, the
  precision is also swept across lower thresholds; false outliers are the flagged
  members that share a route with another node.

The round-trip and token side reuses the existing evidence rather than a new
harness: the committed verb baseline records the repository-only exact-value
gate for every direct-answer verb (including ``clusters`` and ``digest``), and
the zero-live staged A/B compares the committed matched token records. The
capability changes no core answer, so the absent path is byte-identical;
measuring the agent-level round-trip delta of the new answers would need a live
Codex pair, which is recorded as a bounded open item instead of blocking,
exactly as ``TAS-080`` is.

The harness imports no heavy module at top level. ``emit`` needs the optional
extra because the clustering fit does; ``verify`` is fully offline and checks the
committed corpus digest, the recorded lexical baseline, the route parse, the
decision shape, and the recorded verb-gate result, so ``make test`` never loads
a model and never downloads one.
"""

from __future__ import annotations

import contextlib
import io
import json
import sqlite3
import sys
import tempfile
from collections import Counter
from collections.abc import Callable, Mapping, Sequence
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from . import clustering, embedding_benchmark, provider, reduction, staged_benchmark
from .index import _PRIMARY_ROUTE
from .sidecar import content_hash

__all__ = [
    "PROTOCOL",
    "Decision",
    "document_routes",
    "emit",
    "load_evidence",
    "main",
    "measure_clustering",
    "measure_retrieval",
    "verify",
]

Json = dict[str, Any]
Embedder = Callable[[Sequence[str]], list[list[float]]]

PROTOCOL = "clustering-quality-v1"
EVIDENCE_RELATIVE = "benchmark/clustering-quality-evidence.json"
# The committed matched direct-answer records the round-trip/token section
# compares through the existing staged harness. They are ``codex-session-token-v2``
# records of the same controlled task, so the staged A/B matches on fixture,
# model, effort, and CLI version and only the state under test differs.
STAGED_BEFORE_RELATIVE = "benchmark/token-ab-tight.json"
STAGED_AFTER_RELATIVE = "benchmark/token-ab-current.json"
# The provider identity the reduction cache is keyed by. The measurement uses an
# in-memory sidecar, so the value only has to be stable within one emit.
_PROVIDER_KEY = "quality-benchmark"
# The declared quality bars the verdict reads. Stability is the mean pairwise ARI
# the clustering layer reports for the chosen space: a partition that reproduces
# most of itself under resampling clears 0.5, though agreement about noise inflates
# it, which is why a noise bar also applies. Route agreement is the ARI between
# cluster labels and primary routes: chance is zero and the graph's routes are
# often coarse, so 0.3 is the bar for "clusters track settled structure at all".
# Noise share is the fraction of members no cluster claims; past half the answer
# is mostly an attrition list rather than a grouping.
_STABILITY_KEEP = 0.5
_AGREEMENT_KEEP = 0.3
_NOISE_KEEP = 0.5
# Precision is swept below the default threshold because the default can flag
# nothing; these are the thresholds the report tabulates.
_OUTLIER_SWEEP = (0.9, 0.8, 0.7, 0.6, 0.5, 0.4)
_ANSWERS = ("retrieval", "clustering", "digest")
_VERDICTS = ("keep", "revise", "revert")
_VERB_GATE_CASES = (
    ("frontier", 0),
    ("node", 0),
    ("impact", 0),
    ("orient", 0),
    ("check-toon", 1),
    ("digest", 0),
    ("clusters", 0),
)
_NOTE = (
    "Cluster, retrieval, and round-trip quality for the optional embedding and "
    "clustering layer, measured on the committed TAS-089 corpus and the committed "
    "matched token records. Advisory evidence for one keep/revise/revert verdict per answer."
)
_REPRODUCE = (
    "UV_PROJECT_ENVIRONMENT=/tmp/tangle-quality-venv uv sync --extra semantic; "
    "UV_PROJECT_ENVIRONMENT=/tmp/tangle-quality-venv uv run tangle benchmark quality emit"
)
_OPEN_ITEM = (
    "The agent-level round-trip delta of `clusters` and `digest` needs one bounded "
    "matched live Codex pair, which is not authorized (cf. TAS-080); the zero-live "
    "verb gate and staged record parsers are used instead."
)
_USAGE = (
    "usage: tangle benchmark quality emit [--output PATH]\n"
    "       tangle benchmark quality verify\n"
    "Measure and record the embedding and clustering quality gate, or verify the\n"
    "committed evidence offline (corpus digest, lexical baseline, decisions, verb gate)."
)


class _UsageError(Exception):
    """A command-line error that maps to exit code 2."""


class _QualityError(Exception):
    """A measurement the harness cannot produce, reported without a traceback."""


@dataclass(frozen=True)
class Decision:
    """One answer's verdict with the measured numbers that produced it."""

    answer: str
    verdict: str
    rationale: str

    def as_record(self) -> dict[str, str]:
        return {"decision": self.verdict, "rationale": self.rationale}


def _repo_root() -> Path:
    """Return the checkout root that holds the committed corpus and evidence."""
    return Path(__file__).resolve().parents[2]


def _usage() -> None:
    print(_USAGE)


def _digest(text: str) -> str:
    """Return the semantic layer's own content-hash key for an embedded text."""
    return content_hash(text.encode("utf-8"))


def document_routes(corpus: embedding_benchmark.Corpus) -> dict[str, str]:
    """Return each corpus document's resolved primary ``Parent``/``Area`` route.

    The route is parsed from the committed body text with the same rule
    :func:`tangle.index.cluster_source` uses, then resolved against the corpus
    document set by name or id, so the weak ground truth is reproducible from the
    committed fixtures alone and needs no live vault.
    """
    by_reference: dict[str, str] = {}
    for document in corpus.documents:
        by_reference[document.name] = document.id
        by_reference[document.id] = document.id
    routes: dict[str, str] = {}
    for document in corpus.documents:
        match = _PRIMARY_ROUTE.search(document.body)
        target = match.group(2) if match is not None else ""
        routes[document.id] = by_reference.get(target, target)
    return routes


def _document_vectors(
    corpus: embedding_benchmark.Corpus, vectors: Mapping[str, Sequence[float]]
) -> dict[str, list[float]]:
    """Return one embedding vector per document id, keyed the way ``similar`` ranks."""
    return {
        document.id: [float(value) for value in vectors[_digest(document.text())]]
        for document in corpus.documents
    }


def _order(
    document_vectors: Mapping[str, list[float]],
    query: Sequence[float],
    exclude: frozenset[str],
) -> list[str]:
    """Rank documents by embedding cosine, skipping the probe's exclusions.

    This reuses the shipped ``tangle similar`` rerank ranking, so the measured
    embedding order cannot drift from the verb's own order.
    """
    return embedding_benchmark._vector_order(
        dict(document_vectors), [float(value) for value in query], exclude
    )


def _families(corpus: embedding_benchmark.Corpus) -> dict[str, list[embedding_benchmark.Probe]]:
    """Return the overall probe set and one selection per probe family."""
    selections: dict[str, list[embedding_benchmark.Probe]] = {"overall": list(corpus.probes)}
    for probe in corpus.probes:
        selections.setdefault(probe.family, []).append(probe)
    return selections


def measure_retrieval(
    corpus: embedding_benchmark.Corpus, vectors: Mapping[str, Sequence[float]]
) -> Json:
    """Compare the embedding ranking with the lexical baseline per probe family.

    Every probe is scored over the same document set and exclusions for both
    rankings, so the only difference is the metric: the shipped lexical cosine
    over lowercased tokens against the provider's embedding cosine. Each family
    record carries both metric sets and their delta, so a family the embedding
    side wins and a family it loses are both visible.
    """
    document_vectors = _document_vectors(corpus, vectors)
    records: Json = {}
    for family, probes in _families(corpus).items():
        lexical = embedding_benchmark.metrics_for(
            embedding_benchmark.lexical_orders(corpus, probes), probes
        )
        embedded = embedding_benchmark.metrics_for(
            {
                probe.id: _order(
                    document_vectors,
                    vectors[_digest(probe.query)],
                    frozenset(probe.exclude),
                )
                for probe in probes
            },
            probes,
        )
        records[family] = {
            "probes": len(probes),
            "lexical": lexical.as_record(),
            "embedding": embedded.as_record(),
            "delta": {
                name: round(getattr(embedded, name) - getattr(lexical, name), 4)
                for name in ("mrr", "recall_at_1", "recall_at_5", "recall_at_10")
            },
        }
    return records


def _purity(labels: Sequence[int], routes: Sequence[str]) -> float:
    """Return the share of members in their cluster's most common route."""
    if not labels:
        return 0.0
    grouped: dict[int, Counter[str]] = {}
    for label, route in zip(labels, routes, strict=True):
        grouped.setdefault(label, Counter())[route] += 1
    return sum(max(counts.values()) for counts in grouped.values()) / len(labels)


def _outlier_quality(
    scores: Sequence[float], routes: Sequence[str], threshold: float
) -> Json:
    """Report outlier precision against the graph-isolated weak ground truth.

    A graph-isolated node is one whose primary route no other corpus node shares;
    that is the only offline signal that a node stands apart, so it is used as a
    weak label, not an authority. ``precision`` is ``None`` when the threshold
    flags nothing, because there is no positive to measure; ``recall`` is the
    share of isolated nodes the threshold found.
    """
    counts = Counter(routes)
    isolated = [route for route in routes if counts[route] == 1]
    flagged = [index for index, score in enumerate(scores) if score >= threshold]
    found = [index for index in flagged if counts[routes[index]] == 1]
    false_outliers = [index for index in flagged if counts[routes[index]] != 1]
    return {
        "threshold": threshold,
        "flagged": len(flagged),
        "graph_isolated": len(isolated),
        "true_outliers": len(found),
        "false_outliers": len(false_outliers),
        "precision": round(len(found) / len(flagged), 4) if flagged else None,
        "recall": round(len(found) / len(isolated), 4) if isolated else None,
    }


def measure_clustering(
    corpus: embedding_benchmark.Corpus,
    vectors: Mapping[str, Sequence[float]],
    routes: Mapping[str, str],
    *,
    clusterer: clustering.Clusterer | None = None,
    reducer: reduction.Reducer | None = None,
    connection: sqlite3.Connection | None = None,
    params: clustering.ClusterParams | None = None,
) -> Json:
    """Measure stability, route agreement, and outlier precision of the clustering.

    The vectors are clustered exactly as ``tangle clusters`` clusters them --
    the layer's own :func:`tangle.clustering.clusters`, over both spaces, with
    the more stable space chosen -- so the evidence describes the shipped answer
    and not a reimplementation. ``clusterer``, ``reducer``, and ``connection``
    replace the real fit in tests.
    """
    owned = connection is None
    active = sqlite3.connect(":memory:") if connection is None else connection
    try:
        keyed = {
            _digest(document.text()): [float(value) for value in vectors[_digest(document.text())]]
            for document in corpus.documents
        }
        facts = {
            _digest(document.text()): clustering.NodeFacts(
                node_id=document.id, route=routes[document.id]
            )
            for document in corpus.documents
        }
        result = clustering.clusters(
            keyed, _PROVIDER_KEY, active, facts, params, reducer, clusterer
        )
    finally:
        if owned:
            active.close()
    if not result.available:
        raise _QualityError(f"clustering unavailable: {result.reason}")

    order = sorted(member.node_id for member in result.members)
    labels = {member.node_id: member.cluster for member in result.members}
    scores = {member.node_id: member.outlier_score for member in result.members}
    cluster_labels = [labels[node] for node in order]
    route_labels = [routes[node] or "" for node in order]
    route_index = {route: index for index, route in enumerate(sorted(set(route_labels)))}
    return {
        "space": result.space,
        "method": result.method,
        "params": {
            "min_cluster_size": result.params.min_cluster_size,
            "min_samples": result.params.min_samples,
        },
        "clusters": len(result.clusters),
        "noise": len(result.noise),
        "over_broad_routes": len(clustering.over_broad_routes(result)),
        "members": len(order),
        "stability": [
            {"space": row.space, "runs": row.runs, "ari": round(row.ari, 4)}
            for row in result.stability
        ],
        "route_agreement": {
            "routed": sum(1 for node in order if routes[node]),
            "routeless": sum(1 for node in order if not routes[node]),
            "distinct_routes": len({routes[node] or "" for node in order}),
            "ari": round(
                clustering._ari(
                    cluster_labels, [route_index[route] for route in route_labels]
                ),
                4,
            ),
            "purity": round(_purity(cluster_labels, route_labels), 4),
        },
        "outlier": {
            "default": _outlier_quality(
                [scores[node] for node in order],
                [routes[node] or "" for node in order],
                result.params.outlier_threshold,
            ),
            "sweep": [
                _outlier_quality(
                    [scores[node] for node in order],
                    [routes[node] or "" for node in order],
                    threshold,
                )
                for threshold in _OUTLIER_SWEEP
            ],
        },
    }


def _chosen_stability(clustering_record: Mapping[str, Any]) -> float:
    """Return the mean pairwise stability of the space the layer chose."""
    rows = clustering_record["stability"]
    assert isinstance(rows, list) and rows
    chosen = clustering_record["space"]
    for row in rows:
        if row["space"] == chosen:
            return float(row["ari"])
    return float(max(row["ari"] for row in rows))


def _retrieval_decision(retrieval: Mapping[str, Any]) -> Decision:
    """Verdict for the reranked retrieval answer, from the measured deltas.

    The embedding ranking keeps the answer when it beats the lexical baseline on
    near-duplicate retrieval, the family the answer is for. When it loses there
    but still wins another family it earns a revise: keep the opt-in rerank where
    it helps, but do not present it as the near-duplicate reference. Losing
    everywhere is a revert.
    """
    near = retrieval["near-duplicate"]
    paraphrase = retrieval["paraphrase"]
    near_lexical = float(near["lexical"]["mrr"])
    near_embedding = float(near["embedding"]["mrr"])
    para_lexical = float(paraphrase["lexical"]["mrr"])
    para_embedding = float(paraphrase["embedding"]["mrr"])
    if near_embedding >= near_lexical:
        return Decision(
            "retrieval",
            "keep",
            f"near-duplicate MRR {near_embedding:.4f} >= lexical {near_lexical:.4f}",
        )
    if para_embedding > para_lexical:
        return Decision(
            "retrieval",
            "revise",
            f"near-duplicate MRR {near_embedding:.4f} < lexical {near_lexical:.4f} "
            f"but paraphrase MRR {para_embedding:.4f} > lexical {para_lexical:.4f}; "
            "keep the opt-in rerank, keep lexical as the near-duplicate reference",
        )
    return Decision(
        "retrieval",
        "revert",
        f"embedding MRR trails lexical on near-duplicate ({near_embedding:.4f} < "
        f"{near_lexical:.4f}) and paraphrase ({para_embedding:.4f} <= {para_lexical:.4f})",
    )


def _clustering_decision(clustering_record: Mapping[str, Any]) -> Decision:
    """Verdict for the advisory clustering answer, from stability and agreement.

    All three bars must clear for a keep: a partition that reproduces, tracks the
    graph's settled routes, and clusters most of its members. A stable partition
    that fails agreement or leaves most members as noise earns a revise, because
    the grouping reproduces but does not recover settled structure; failing
    stability is a revert.
    """
    stability = _chosen_stability(clustering_record)
    agreement = float(clustering_record["route_agreement"]["ari"])
    members = int(clustering_record["members"])
    noise = int(clustering_record["noise"])
    flagged = int(clustering_record["outlier"]["default"]["flagged"])
    share = noise / members if members else 1.0
    detail = (
        f"stability {stability:.4f} (bar {_STABILITY_KEEP}), route agreement "
        f"{agreement:.4f} (bar {_AGREEMENT_KEEP}), noise {noise}/{members} "
        f"(bar {_NOISE_KEEP}), outlier view flags {flagged} at the default threshold"
    )
    if stability >= _STABILITY_KEEP and agreement >= _AGREEMENT_KEEP and share <= _NOISE_KEEP:
        return Decision("clustering", "keep", detail)
    if stability >= _STABILITY_KEEP:
        return Decision("clustering", "revise", f"stable but weak answer: {detail}")
    return Decision("clustering", "revert", f"unstable across seeds/subsamples: {detail}")


def _digest_decision(answer_surface: Mapping[str, Any]) -> Decision:
    """Verdict for the graph digest answer, from its exact-value gate.

    The digest is graph-only and needs no capability, so it keeps whenever the
    verb gate proves its bounded answer exact.
    """
    gate = answer_surface["verb_gate"]
    cases = {case["case"]: case["exit"] for case in gate["cases"]}
    if gate["passed"] and cases.get("digest") == 0:
        return Decision(
            "digest",
            "keep",
            "graph-only bounded answer; exact-value gate passed at exit 0",
        )
    return Decision("digest", "revert", "exact-value gate did not pass")


def _decisions(
    retrieval: Mapping[str, Any],
    clustering_record: Mapping[str, Any],
    answer_surface: Mapping[str, Any],
) -> dict[str, dict[str, str]]:
    """Return the three verdicts keyed by answer."""
    verdicts = (
        _retrieval_decision(retrieval),
        _clustering_decision(clustering_record),
        _digest_decision(answer_surface),
    )
    return {decision.answer: decision.as_record() for decision in verdicts}


def _verb_gate(root: Path) -> Json:
    """Check the committed repository-only verb baseline's complete schema.

    The executable gate lives in ``tangle_research``. The still-installed quality
    command checks its frozen seven-case result without importing, probing for,
    or installing the development-only package. ``passed`` means the committed
    artifact is structurally intact, not that this call executed the verb gate.
    """
    baseline: Json = json.loads((root / "benchmark" / "verb-baseline.json").read_text("utf-8"))
    expected = baseline.get("expected")
    required = dict(_VERB_GATE_CASES)
    valid = (
        set(baseline) == {"protocol", "note", "expected"}
        and baseline.get("protocol") == "direct-answer-verb-v1"
        and isinstance(baseline.get("note"), str)
        and bool(baseline.get("note"))
        and isinstance(expected, dict)
    )
    cases: list[Json] = []
    if isinstance(expected, dict):
        valid = valid and set(expected) == set(required)
        for name, exit_code in _VERB_GATE_CASES:
            answer = expected.get(name)
            answer_valid = (
                isinstance(answer, dict)
                and set(answer) == {"exit", "stdout"}
                and type(answer.get("exit")) is int
                and answer.get("exit") == exit_code
                and isinstance(answer.get("stdout"), str)
                and bool(answer.get("stdout"))
            )
            valid = valid and answer_valid
            if isinstance(answer, dict):
                cases.append({"case": name, "exit": answer.get("exit")})
    return {
        "harness": "committed benchmark/verb-baseline.json integrity",
        "passed": valid,
        "cases": cases,
    }


def _staged_pair(root: Path) -> Json:
    """Compare the committed matched records through the existing staged harness."""
    before = root / STAGED_BEFORE_RELATIVE
    after = root / STAGED_AFTER_RELATIVE
    if not before.is_file() or not after.is_file():
        raise _QualityError("missing committed staged token records")
    with tempfile.TemporaryDirectory(prefix="tangle-quality-staged-") as directory:
        report_path = Path(directory) / "staged-ab.json"
        capture = io.StringIO()
        with contextlib.redirect_stdout(capture):
            status = staged_benchmark.main(
                ["--before", str(before), "--after", str(after), "--output", str(report_path)]
            )
        if status != 0 or not report_path.is_file():
            raise _QualityError("staged harness rejected the committed records")
        report: Json = json.loads(report_path.read_text(encoding="utf-8"))
    tokens = report["tokens"]
    return {
        "harness": "tangle benchmark staged",
        "before": STAGED_BEFORE_RELATIVE,
        "after": STAGED_AFTER_RELATIVE,
        "decision": report["decision"],
        "matched": report["matched"],
        "round_trips": report["round_trips"],
        "tokens": {
            "uncached_delta": tokens["delta"]["uncached_input_tokens"],
            "total_delta": tokens["delta"]["total_tokens"],
        },
    }


def _capability_absent(root: Path) -> Json:
    """Return the recorded capability-absent ``clusters`` answer from the verb gate.

    The committed verb baseline holds the exact answer with no provider loaded, so
    reading it documents that the capability changes no core answer and adds only
    the explicit ``clusters`` answer.
    """
    baseline: Json = json.loads((root / "benchmark" / "verb-baseline.json").read_text("utf-8"))
    answer: Json = baseline["expected"]["clusters"]
    stdout = str(answer["stdout"])
    line = next((row for row in stdout.splitlines() if row.startswith("clusters:")), "")
    return {"exit": answer["exit"], "line": line, "byte_identical": "capability absent" in line}


def measure_answer_surface(root: Path) -> Json:
    """Measure the round-trip and token side from zero-live evidence and harnesses."""
    return {
        "verb_gate": _verb_gate(root),
        "staged": _staged_pair(root),
        "capability_absent": _capability_absent(root),
        "open_item": _OPEN_ITEM,
    }


def _provider_vectors(
    corpus: embedding_benchmark.Corpus, embed: Embedder
) -> dict[str, list[float]]:
    """Embed every document and probe query once, keyed by the layer's content hash.

    Documents and probe queries share one text space, so the same text is
    embedded once and each near-duplicate probe reuses its document's vector.
    """
    texts: dict[str, str] = {}
    for document in corpus.documents:
        texts[_digest(document.text())] = document.text()
    for probe in corpus.probes:
        texts[_digest(probe.query)] = probe.query
    keys = sorted(texts)
    produced = embed([texts[key] for key in keys])
    if len(produced) != len(keys):
        raise _QualityError(f"embedder returned {len(produced)} vectors for {len(keys)} texts")
    return {
        key: [float(value) for value in vector]
        for key, vector in zip(keys, produced, strict=True)
    }


def emit(
    root: Path | None = None,
    *,
    embed: Embedder | None = None,
    corpus: embedding_benchmark.Corpus | None = None,
    clusterer: clustering.Clusterer | None = None,
    reducer: reduction.Reducer | None = None,
    connection: sqlite3.Connection | None = None,
    params: clustering.ClusterParams | None = None,
) -> Json:
    """Measure the whole quality gate and return the evidence document.

    ``embed`` defaults to the native provider, ``clusterer`` and ``reducer`` to
    the real fits, and ``corpus`` to the committed one. The result is a plain
    document so a caller can write it and a test can inspect it without touching
    the filesystem.
    """
    base = _repo_root() if root is None else root
    loaded = embedding_benchmark.load_corpus(base) if corpus is None else corpus
    problems = embedding_benchmark.verify_corpus(loaded, base)
    if problems:
        raise _QualityError(f"committed corpus is invalid: {problems[0]}")
    vectors = _provider_vectors(loaded, provider.embed if embed is None else embed)
    routes = document_routes(loaded)
    retrieval = measure_retrieval(loaded, vectors)
    clustering_record = measure_clustering(
        loaded,
        vectors,
        routes,
        clusterer=clusterer,
        reducer=reducer,
        connection=connection,
        params=params,
    )
    answer_surface = measure_answer_surface(base)
    return {
        "protocol": PROTOCOL,
        "note": _NOTE,
        "host": embedding_benchmark.host_record(),
        "model": {
            "runtime": "fastembed",
            "model": provider.DEFAULT_MODEL,
            "fallback": provider.FALLBACK_MODEL,
            "dimensions": len(next(iter(vectors.values()))),
            "weights": "see benchmark/embedding-evidence.json",
        },
        "corpus": {
            "path": embedding_benchmark.CORPUS_RELATIVE,
            "digest": embedding_benchmark._corpus_digest(base),
            "source_revision": loaded.revision,
            "documents": len(loaded.documents),
            "probes": len(loaded.probes),
        },
        "retrieval": retrieval,
        "clustering": clustering_record,
        "answer_surface": answer_surface,
        "decisions": _decisions(retrieval, clustering_record, answer_surface),
        "reproduce": _REPRODUCE,
    }


def load_evidence(root: Path | None = None) -> Json:
    """Read the committed quality evidence; raise when it is missing or malformed."""
    base = _repo_root() if root is None else root
    path = base / EVIDENCE_RELATIVE
    if not path.is_file():
        raise _QualityError(f"missing committed evidence: {EVIDENCE_RELATIVE}")
    try:
        document = json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as error:
        raise _QualityError(f"unreadable evidence {EVIDENCE_RELATIVE}: {error}") from error
    if not isinstance(document, dict):
        raise _QualityError("evidence is not a JSON object")
    return document


def verify(root: Path | None = None) -> list[str]:
    """Return the integrity problems that make the committed evidence unusable.

    Offline and model-free: it re-derives the corpus digest, recomputes the
    lexical baseline the evidence records, re-parses the routes, and checks the
    protocol, decision shape, and verb gate. The embedding and clustering numbers
    themselves need the optional extra to recompute, so they are not re-derived
    here; a problem list rather than a raise reports every defect in one pass.
    """
    base = _repo_root() if root is None else root
    problems: list[str] = []
    try:
        evidence = load_evidence(base)
    except _QualityError as error:
        return [str(error)]
    if evidence.get("protocol") != PROTOCOL:
        problems.append(f"protocol mismatch: {evidence.get('protocol')}")
    corpus = embedding_benchmark.load_corpus(base)
    problems.extend(embedding_benchmark.verify_corpus(corpus, base))
    committed = evidence.get("corpus")
    if not isinstance(committed, dict):
        problems.append("evidence has no corpus record")
    elif committed.get("digest") != embedding_benchmark._corpus_digest(base):
        problems.append("corpus digest differs from the committed corpus")
    retrieval = evidence.get("retrieval")
    if not isinstance(retrieval, dict):
        problems.append("evidence has no retrieval record")
    else:
        for family, probes in _families(corpus).items():
            recorded = retrieval.get(family)
            recomputed = embedding_benchmark.metrics_for(
                embedding_benchmark.lexical_orders(corpus, probes), probes
            ).as_record()
            if not isinstance(recorded, dict):
                problems.append(f"retrieval lacks {family}")
            elif recorded.get("lexical") != recomputed:
                problems.append(f"retrieval lexical baseline drifts for {family}")
    clustering_record = evidence.get("clustering")
    if not isinstance(clustering_record, dict):
        problems.append("evidence has no clustering record")
    else:
        agreement = clustering_record.get("route_agreement")
        routed = sum(1 for route in document_routes(corpus).values() if route)
        if not isinstance(agreement, dict):
            problems.append("clustering lacks route agreement")
        elif agreement.get("routed") != routed:
            problems.append("clustering route count differs from the committed corpus")
    answer_surface = evidence.get("answer_surface")
    expected_gate = _verb_gate(base)
    if not isinstance(answer_surface, dict):
        problems.append("evidence has no answer-surface record")
    else:
        gate = answer_surface.get("verb_gate")
        if gate != expected_gate:
            problems.append("recorded verb baseline integrity evidence differs")
    if expected_gate["passed"] is not True:
        problems.append("committed verb baseline integrity check failed")
    decisions = evidence.get("decisions")
    if not isinstance(decisions, dict):
        problems.append("evidence has no decisions")
    else:
        for answer in _ANSWERS:
            record = decisions.get(answer)
            if not isinstance(record, dict):
                problems.append(f"decision missing for {answer}")
            elif record.get("decision") not in _VERDICTS or not str(
                record.get("rationale", "")
            ).strip():
                problems.append(f"decision malformed for {answer}")
    return problems


def _emit_command(argv: Sequence[str]) -> int:
    output = None
    position = 0
    while position < len(argv):
        token = argv[position]
        if token in {"-h", "--help"}:
            _usage()
            return 0
        if token == "--output" or token.startswith("--output="):
            value = token.partition("=")[2]
            if not value and token == "--output":
                position += 1
                if position >= len(argv):
                    raise _UsageError("missing value for --output")
                value = argv[position]
            output = Path(value)
        else:
            raise _UsageError(f"unknown argument: {token}")
        position += 1
    target = output or _repo_root() / EVIDENCE_RELATIVE
    document = emit()
    target.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")
    for answer in _ANSWERS:
        print(f"quality{{{answer},decision}}: {answer},{document['decisions'][answer]['decision']}")
    staged = document["answer_surface"]["staged"]
    print(
        f"quality{{staged_decision,uncached_delta,total_delta}}: {staged['decision']},"
        f"{staged['tokens']['uncached_delta']},{staged['tokens']['total_delta']}"
    )
    print(f"evidence: {target}")
    return 0


def _verify_command(argv: Sequence[str]) -> int:
    if any(token not in {"-h", "--help"} for token in argv):
        raise _UsageError(f"unknown argument: {argv[0]}")
    if argv:
        _usage()
        return 0
    problems = verify()
    for problem in problems:
        print(f"problem: {problem}")
    if problems:
        return 1
    evidence = load_evidence()
    print(f'evidence: "{EVIDENCE_RELATIVE}"')
    for answer in _ANSWERS:
        print(f"quality{{{answer},decision}}: {answer},{evidence['decisions'][answer]['decision']}")
    print("verification: passed")
    return 0


def main(argv: Sequence[str] | None = None) -> int:
    """Measure and record the quality gate, or verify the committed evidence."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments:
        _usage()
        return 2
    command = arguments[0]
    try:
        if command == "emit":
            return _emit_command(arguments[1:])
        if command == "verify":
            return _verify_command(arguments[1:])
        if command in {"-h", "--help"}:
            _usage()
            return 0
        raise _UsageError(f"unknown argument: {command}")
    except _UsageError as error:
        print(f"error: {error}", file=sys.stderr)
        _usage()
        return 2
    except _QualityError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1
