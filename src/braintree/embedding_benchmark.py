"""Select an off-the-shelf embedding model and inference runtime, with evidence.

The off-the-shelf semantic layer (see TAS-087) needs a default embedding model,
a fallback, and one in-process runtime. This module is the explicit batch tool
that answers those questions: it freezes a retrieval corpus derived from the
vault's own link structure and resolved near-duplicate history, scores the
lexical ``braintree similar`` baseline and every candidate model on it, and
writes the measurements to ``benchmark/embedding-evidence.json``.

Nothing here runs on an interactive path. ``corpus`` reads Markdown and needs no
third-party module; ``run`` imports the optional ``semantic`` extra lazily, one
runtime at a time, and reports a candidate the environment cannot serve instead
of raising. Model weights are downloaded only by an explicit ``run`` into the
documented offline cache, never at query time, so the default install and
``make test`` never import a heavy module.

The frozen corpus is two committed files: ``benchmark/embedding-corpus.json``
holds the protocol, the source revision, and the probes, and
``benchmark/embedding-documents.jsonl`` holds one retrieval document per line
with the exact ``summary`` plus body text ``braintree similar`` compares.
"""

from __future__ import annotations

import importlib
import json
import os
import platform
import subprocess
import sys
import time
from collections.abc import Callable, Sequence
from dataclasses import dataclass
from hashlib import sha256
from importlib.metadata import PackageNotFoundError
from importlib.metadata import version as distribution_version
from pathlib import Path
from types import ModuleType

from . import semantic, vault
from .graph_check import CONTEXT_RELATIONS
from .index import IndexedNode, _cosine, _read_nodes, _token_counts

__all__ = [
    "CANDIDATES",
    "PROTOCOL",
    "RUNTIMES",
    "Candidate",
    "Corpus",
    "Document",
    "Embedder",
    "Metrics",
    "Probe",
    "RunOptions",
    "build_corpus",
    "evaluate",
    "lexical_orders",
    "load_corpus",
    "main",
    "metrics_for",
    "run",
    "verify_corpus",
]

PROTOCOL = "embedding-selection-v1"
CORPUS_RELATIVE = "benchmark/embedding-corpus.json"
DOCUMENTS_RELATIVE = "benchmark/embedding-documents.jsonl"
EVIDENCE_RELATIVE = "benchmark/embedding-evidence.json"

_USAGE = (
    "usage: braintree benchmark embedding corpus [--nodes DIR] [--emit | --verify]\n"
    "       braintree benchmark embedding run [--models LIST] [--runtimes LIST]\n"
    "           [--limit N] [--probes N] [--time-budget SECONDS] [--output PATH]\n"
    "Freeze or verify the fixed retrieval corpus, or run the explicit batch\n"
    "comparison of candidate embedding models and inference runtimes."
)
_NOTE = (
    "Cold-start and per-node costs are measured once per runtime in one process; "
    "the interactive path never loads a model. Weights are read from the "
    "documented offline cache and nothing is downloaded at query time."
)
# The paraphrase family is derived from the vault's canonical context edges: the
# dependent node's summary is the query and the dependency it names is the
# positive. A summary can name a dependency in different words than the
# dependency itself uses, which is exactly the recall gap a lexical baseline has.
_FAMILY_PARAPHRASE = "paraphrase"
# The near-duplicate family is derived from the vault's resolved near-duplicate
# history: pairs of resolved documents whose text is nearly identical. One
# member's text is the query, the other is the positive, and the query member is
# excluded from the ranking because a draft is not a node yet.
_FAMILY_NEAR_DUPLICATE = "near-duplicate"
# A held-out probe is one whose positive falls on the held-out side of this
# deterministic split by digest, so a positive document is a positive in exactly
# one split and the held-out metrics never reuse a screening positive.
_HELD_OUT_MODULUS = 2
_NEAR_DUPLICATE_THRESHOLD = 0.75
_HARD_NEGATIVES = 3
_RECALL_KS = (1, 5, 10)
_SPLITS = ("overall", "dev", "heldout")


@dataclass(frozen=True)
class Candidate:
    """One off-the-shelf candidate model with its prompt convention and license."""

    model: str
    license: str
    query_prefix: str = ""
    passage_prefix: str = ""
    trust_remote_code: bool = False
    note: str = ""


# The runtime packages and their pinned lower bounds live in ``pyproject.toml``;
# the upstream weight revisions are resolved at measurement time and recorded in
# the evidence.
CANDIDATES: tuple[Candidate, ...] = (
    Candidate(
        model="sentence-transformers/all-MiniLM-L6-v2",
        license="apache-2.0",
        note="smallest widely used English retrieval encoder; no prompt convention",
    ),
    Candidate(
        model="BAAI/bge-small-en-v1.5",
        license="mit",
        query_prefix="Represent this sentence for searching relevant passages: ",
        note="v1.5 recommends the short-query instruction",
    ),
    Candidate(
        model="thenlper/gte-small",
        license="mit",
        note="no prompt convention",
    ),
    Candidate(
        model="intfloat/e5-small-v2",
        license="mit",
        query_prefix="query: ",
        passage_prefix="passage: ",
        note="requires the asymmetric query:/passage: prefixes",
    ),
    Candidate(
        model="nomic-ai/nomic-embed-text-v1.5",
        license="apache-2.0",
        query_prefix="search_query: ",
        passage_prefix="search_document: ",
        trust_remote_code=True,
        note="requires trust_remote_code and its modeling dependencies",
    ),
    Candidate(
        model="Snowflake/snowflake-arctic-embed-s",
        license="apache-2.0",
        query_prefix="Represent this sentence for searching relevant passages: ",
        note="short-query instruction is recommended for retrieval",
    ),
)

RUNTIMES: tuple[str, ...] = ("sentence-transformers", "fastembed")


@dataclass(frozen=True)
class Document:
    """One retrieval document: the exact text ``braintree similar`` compares."""

    id: str
    name: str
    status: str
    summary: str
    body: str

    def text(self) -> str:
        """Return the summary-plus-body text ``braintree similar`` embeds."""
        return self.summary + "\n" + self.body


@dataclass(frozen=True)
class Probe:
    """One retrieval probe: its query, its known positives, and its exclusions."""

    id: str
    family: str
    split: str
    query: str
    positives: tuple[str, ...]
    negatives: tuple[str, ...]
    exclude: tuple[str, ...]


@dataclass(frozen=True)
class Corpus:
    """The fixed evaluation corpus: its source revision, documents, and probes."""

    protocol: str
    nodes_root: str
    revision: str
    documents: tuple[Document, ...]
    probes: tuple[Probe, ...]


@dataclass(frozen=True)
class Metrics:
    """Retrieval quality over one probe set: MRR and recall@k."""

    probes: int
    mrr: float
    recall_at_1: float
    recall_at_5: float
    recall_at_10: float

    def as_record(self) -> dict[str, float | int]:
        return {
            "probes": self.probes,
            "mrr": round(self.mrr, 4),
            "recall@1": round(self.recall_at_1, 4),
            "recall@5": round(self.recall_at_5, 4),
            "recall@10": round(self.recall_at_10, 4),
        }


@dataclass(frozen=True)
class Embedder:
    """A loaded runtime with its query and passage encoders and its load costs."""

    runtime: str
    query: Callable[[Sequence[str]], list[list[float]]]
    passage: Callable[[Sequence[str]], list[list[float]]]
    import_seconds: float
    load_seconds: float
    weight_slug: str = ""


@dataclass(frozen=True)
class RunOptions:
    """The bounded batch the explicit evaluation run may spend."""

    models: tuple[str, ...] = ()
    runtimes: tuple[str, ...] = RUNTIMES
    limit: int | None = None
    probes_limit: int | None = None
    time_budget: float | None = None


class _UsageError(Exception):
    """A command-line error that maps to exit code 2."""


class _RunError(Exception):
    """A measurement the harness cannot produce, reported without a traceback."""


class _CandidateUnavailable(Exception):
    """A candidate model or runtime this environment cannot serve."""


def _repo_root() -> Path:
    """Return the checkout root that holds the committed corpus and evidence."""
    return Path(__file__).resolve().parents[2]


def _usage() -> None:
    print(_USAGE)


# --- Corpus derivation -------------------------------------------------------


def _split_of(family: str, positive: str) -> str:
    """Return the deterministic dev-or-heldout split of a probe's positive.

    The split is a function of the positive document, so one document is a
    positive in exactly one split and the held-out metrics never reuse a
    screening positive. It is a digest, not a random draw, so regenerating the
    corpus from the same revision reproduces the same split.
    """
    digest = sha256(f"{family}:{positive}".encode()).hexdigest()
    if int(digest[:8], 16) % _HELD_OUT_MODULUS == 0:
        return "heldout"
    return "dev"


def _document(node: IndexedNode) -> Document:
    return Document(
        id=node.id,
        name=node.name,
        status=node.status,
        summary=node.metadata.get("summary", ""),
        body=node.body,
    )


def _lexical_order(
    documents: Sequence[Document], text: str, exclude: frozenset[str]
) -> list[str]:
    """Rank ``documents`` by the shipped lexical baseline, skipping ``exclude``.

    This is the same lowercased-token cosine ``braintree similar`` ranks with:
    the score comes from :func:`braintree.index._cosine` over
    :func:`braintree.index._token_counts`, so the baseline measured here cannot
    drift from the baseline the shipped verb answers with.
    """
    query = _token_counts(text)
    scored: list[tuple[float, str]] = []
    for document in documents:
        if document.id in exclude:
            continue
        score = _cosine(query, _token_counts(document.text()))
        if score <= 0:
            continue
        scored.append((score, document.id))
    scored.sort(key=lambda pair: (-pair[0], pair[1]))
    return [document_id for _score, document_id in scored]


def _context_edges(node: IndexedNode) -> list[str]:
    """Return the canonical context-edge targets named in a node body, in order."""
    targets: list[str] = []
    for line in node.body.splitlines():
        stripped = line.strip()
        for relation in CONTEXT_RELATIONS:
            prefix = f"{relation} [["
            if stripped.startswith(prefix) and "]]" in stripped:
                target = stripped[len(prefix) : stripped.index("]]")]
                if target and target not in targets:
                    targets.append(target)
    return targets


def _near_duplicate_pairs(documents: Sequence[Document]) -> list[tuple[Document, Document]]:
    """Return the resolved near-duplicate pairs the vault has already settled.

    Two resolved documents are near-duplicates when their summary-plus-body text
    ranks at or above the near-duplicate threshold on the same lexical cosine the
    admission check uses. Only resolved documents are compared, because a
    proposal that is still moving is not settled near-duplicate history.
    """
    resolved = [document for document in documents if document.status == "resolved"]
    counts = {document.id: _token_counts(document.text()) for document in resolved}
    pairs: list[tuple[Document, Document]] = []
    for index, left in enumerate(resolved):
        for right in resolved[index + 1 :]:
            if _cosine(counts[left.id], counts[right.id]) >= _NEAR_DUPLICATE_THRESHOLD:
                pairs.append((left, right))
    return pairs


def build_corpus(nodes_root: str, revision: str) -> Corpus:
    """Derive the fixed corpus from the Markdown vault under ``nodes_root``.

    Two probe families are derived, both from the vault's own settled structure.
    A paraphrase probe comes from a canonical context edge: the dependent's
    summary is the query and the dependency it names is the positive, with the
    dependent excluded because a node is not its own answer. A near-duplicate
    probe comes from the resolved near-duplicate history: two resolved documents
    whose full text is nearly identical, one used as the query and the other as
    the positive. Each probe also records the lexical baseline's nearest
    non-positive documents as hard negatives, which documents what the lexical
    ranking confuses; the metrics themselves are computed over the whole
    document set, so the recorded negatives never flatter a candidate.
    """
    nodes = _read_nodes(nodes_root)
    documents = tuple(sorted((_document(node) for node in nodes), key=lambda doc: doc.id))
    by_name = {node.name: node for node in nodes}
    by_id = {node.id: node for node in nodes}
    drafts: list[Probe] = []

    for node in sorted(nodes, key=lambda item: item.id):
        summary = node.metadata.get("summary", "").strip()
        if not summary:
            continue
        for target_name in _context_edges(node):
            target = by_name.get(target_name) or by_id.get(target_name)
            if target is None or target.id == node.id:
                continue
            drafts.append(
                Probe(
                    id="",
                    family=_FAMILY_PARAPHRASE,
                    split=_split_of(_FAMILY_PARAPHRASE, target.id),
                    query=summary,
                    positives=(target.id,),
                    negatives=(),
                    exclude=(node.id,),
                )
            )

    for left, right in _near_duplicate_pairs(documents):
        drafts.append(
            Probe(
                id="",
                family=_FAMILY_NEAR_DUPLICATE,
                split=_split_of(_FAMILY_NEAR_DUPLICATE, left.id),
                query=right.text(),
                positives=(left.id,),
                negatives=(),
                exclude=(right.id,),
            )
        )

    deduped: dict[tuple[str, str, str], Probe] = {}
    for probe in drafts:
        deduped.setdefault((probe.family, probe.query, probe.positives[0]), probe)
    filled: list[Probe] = []
    ordered = sorted(deduped.values(), key=lambda item: (item.family, item.positives[0]))
    for position, probe in enumerate(ordered, start=1):
        ranked = _lexical_order(documents, probe.query, frozenset(probe.exclude))
        negatives = tuple(
            document_id for document_id in ranked if document_id not in probe.positives
        )[:_HARD_NEGATIVES]
        filled.append(
            Probe(
                id=f"{probe.family}-{position:03d}",
                family=probe.family,
                split=probe.split,
                query=probe.query,
                positives=probe.positives,
                negatives=negatives,
                exclude=probe.exclude,
            )
        )
    return Corpus(
        protocol=PROTOCOL,
        nodes_root=nodes_root,
        revision=revision,
        documents=documents,
        probes=tuple(filled),
    )


# --- Corpus serialization ----------------------------------------------------


def _corpus_header(corpus: Corpus) -> dict[str, object]:
    return {
        "protocol": corpus.protocol,
        "source": {
            "nodes_root": corpus.nodes_root,
            "revision": corpus.revision,
            "documents": len(corpus.documents),
            "probes": len(corpus.probes),
            "dev": sum(1 for probe in corpus.probes if probe.split == "dev"),
            "heldout": sum(1 for probe in corpus.probes if probe.split == "heldout"),
        },
        "probes": [
            {
                "id": probe.id,
                "family": probe.family,
                "split": probe.split,
                "query": probe.query,
                "positives": list(probe.positives),
                "negatives": list(probe.negatives),
                "exclude": list(probe.exclude),
            }
            for probe in corpus.probes
        ],
    }


def _document_record(document: Document) -> dict[str, str]:
    return {
        "id": document.id,
        "name": document.name,
        "status": document.status,
        "summary": document.summary,
        "body": document.body,
    }


def _write_corpus(corpus: Corpus, root: Path) -> None:
    (root / CORPUS_RELATIVE).write_text(
        json.dumps(_corpus_header(corpus), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    (root / DOCUMENTS_RELATIVE).write_text(
        "".join(
            json.dumps(_document_record(document), ensure_ascii=False) + "\n"
            for document in corpus.documents
        ),
        encoding="utf-8",
    )


def load_corpus(root: Path | None = None) -> Corpus:
    """Read the committed corpus; raise :class:`_RunError` when it is incomplete."""
    base = _repo_root() if root is None else root
    corpus_path = base / CORPUS_RELATIVE
    documents_path = base / DOCUMENTS_RELATIVE
    if not corpus_path.is_file() or not documents_path.is_file():
        raise _RunError(
            "missing committed corpus; run `braintree benchmark embedding corpus`"
        )
    header = json.loads(corpus_path.read_text(encoding="utf-8"))
    documents = tuple(
        Document(
            id=str(record["id"]),
            name=str(record["name"]),
            status=str(record["status"]),
            summary=str(record["summary"]),
            body=str(record["body"]),
        )
        for record in (
            json.loads(line)
            for line in documents_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        )
    )
    source = header["source"]
    probes = tuple(
        Probe(
            id=str(record["id"]),
            family=str(record["family"]),
            split=str(record["split"]),
            query=str(record["query"]),
            positives=tuple(str(value) for value in record["positives"]),
            negatives=tuple(str(value) for value in record["negatives"]),
            exclude=tuple(str(value) for value in record["exclude"]),
        )
        for record in header["probes"]
    )
    return Corpus(
        protocol=str(header["protocol"]),
        nodes_root=str(source["nodes_root"]),
        revision=str(source["revision"]),
        documents=documents,
        probes=probes,
    )


def _corpus_digest(root: Path) -> str:
    """Return the digest of the two committed corpus files."""
    digest = sha256()
    for relative in (CORPUS_RELATIVE, DOCUMENTS_RELATIVE):
        digest.update((root / relative).read_bytes())
    return digest.hexdigest()


def verify_corpus(corpus: Corpus, root: Path) -> list[str]:
    """Return the integrity problems that make the corpus unusable for scoring.

    The committed files are checked against the protocol and against what makes a
    probe scorable: a query, a resolvable positive, and only documents that
    exist, in both probe families and both splits. A problem list rather than a
    raise lets the command report every defect in one pass.
    """
    problems: list[str] = []
    if corpus.protocol != PROTOCOL:
        problems.append(f"protocol mismatch: {corpus.protocol}")
    ids = [document.id for document in corpus.documents]
    if len(set(ids)) != len(ids):
        problems.append("duplicate document ids")
    if len(corpus.documents) < 20:
        problems.append(f"too few documents: {len(corpus.documents)}")
    if len(corpus.probes) < 8:
        problems.append(f"too few probes: {len(corpus.probes)}")
    known = set(ids)
    for probe in corpus.probes:
        if not probe.query.strip():
            problems.append(f"{probe.id}: empty query")
        if not probe.positives:
            problems.append(f"{probe.id}: no positive")
        if probe.family not in {_FAMILY_PARAPHRASE, _FAMILY_NEAR_DUPLICATE}:
            problems.append(f"{probe.id}: unknown family {probe.family}")
        if probe.split not in {"dev", "heldout"}:
            problems.append(f"{probe.id}: unknown split {probe.split}")
        for reference in (*probe.positives, *probe.negatives, *probe.exclude):
            if reference not in known:
                problems.append(f"{probe.id}: unknown document {reference}")
    families = {probe.family for probe in corpus.probes}
    splits = {probe.split for probe in corpus.probes}
    if families != {_FAMILY_PARAPHRASE, _FAMILY_NEAR_DUPLICATE}:
        problems.append(f"missing probe family: {sorted(families)}")
    if splits != {"dev", "heldout"}:
        problems.append(f"missing probe split: {sorted(splits)}")
    documents_path = root / DOCUMENTS_RELATIVE
    if documents_path.is_file():
        committed = {
            str(json.loads(line)["id"])
            for line in documents_path.read_text(encoding="utf-8").splitlines()
            if line.strip()
        }
        if committed != known:
            problems.append("committed documents differ from the probed document set")
    return problems


# --- Scoring -----------------------------------------------------------------


def _vector_order(
    vectors: dict[str, list[float]],
    query: list[float],
    exclude: frozenset[str],
) -> list[str]:
    """Rank documents by embedding cosine, skipping ``exclude``."""
    scored: list[tuple[float, str]] = []
    for document_id, vector in vectors.items():
        if document_id in exclude:
            continue
        score = semantic.cosine(query, vector)
        if score <= 0:
            continue
        scored.append((score, document_id))
    scored.sort(key=lambda pair: (-pair[0], pair[1]))
    return [document_id for _score, document_id in scored]


def metrics_for(orders: dict[str, list[str]], probes: Sequence[Probe]) -> Metrics:
    """Return MRR and recall@k for one ranked order per probe.

    A positive is found at the rank of the first positive document in the order;
    MRR averages its reciprocal rank and recall@k is the fraction of probes with
    a positive in the first ``k``. A probe with no positive in its order
    contributes zero, so a missing answer is a real failure rather than a
    silently dropped row.
    """
    if not probes:
        return Metrics(probes=0, mrr=0.0, recall_at_1=0.0, recall_at_5=0.0, recall_at_10=0.0)
    reciprocal = 0.0
    hits = {k: 0 for k in _RECALL_KS}
    for probe in probes:
        order = orders.get(probe.id, [])
        rank = next(
            (
                position
                for position, document_id in enumerate(order, start=1)
                if document_id in probe.positives
            ),
            None,
        )
        if rank is None:
            continue
        reciprocal += 1.0 / rank
        for k in _RECALL_KS:
            if rank <= k:
                hits[k] += 1
    total = float(len(probes))
    return Metrics(
        probes=len(probes),
        mrr=reciprocal / total,
        recall_at_1=hits[1] / total,
        recall_at_5=hits[5] / total,
        recall_at_10=hits[10] / total,
    )


def _split_records(
    orders: dict[str, list[str]], probes: Sequence[Probe]
) -> dict[str, dict[str, float | int]]:
    selections: dict[str, list[Probe]] = {
        "overall": list(probes),
        "dev": [probe for probe in probes if probe.split == "dev"],
        "heldout": [probe for probe in probes if probe.split == "heldout"],
    }
    families = {
        family: [probe for probe in probes if probe.family == family]
        for family in {probe.family for probe in probes}
    }
    records = {
        name: metrics_for(orders, selection).as_record()
        for name, selection in selections.items()
    }
    records.update(
        {
            family: metrics_for(orders, selection).as_record()
            for family, selection in families.items()
        }
    )
    for name in _SPLITS:
        records.setdefault(name, Metrics(0, 0.0, 0.0, 0.0, 0.0).as_record())
    return records


def lexical_orders(corpus: Corpus, probes: Sequence[Probe]) -> dict[str, list[str]]:
    """Return the lexical baseline's ranked order for each probe."""
    return {
        probe.id: _lexical_order(corpus.documents, probe.query, frozenset(probe.exclude))
        for probe in probes
    }


def evaluate(corpus: Corpus, probes: Sequence[Probe], embedder: Embedder) -> dict[str, object]:
    """Score ``probes`` for one ``embedder`` and return its measured record.

    The documents are encoded once, so the ranking varies only by the query
    vector; ``ms_per_node`` is the passage encode time divided by the document
    count and ``ms_per_query`` the query encode time divided by the probe count.
    One encode of each kind runs untimed first, so the reported cost is the
    steady-state cost per item and not the runtime's first-call initialization;
    the load and import costs are recorded separately.
    """
    documents = list(corpus.documents)
    if documents:
        embedder.passage([documents[0].text()])
    if probes:
        embedder.query([probes[0].query])
    started = time.perf_counter()
    passage_vectors = embedder.passage([document.text() for document in documents])
    passage_seconds = time.perf_counter() - started
    if len(passage_vectors) != len(documents):
        raise _RunError("runtime returned a different number of document vectors")
    vectors = {
        document.id: vector
        for document, vector in zip(documents, passage_vectors, strict=True)
    }
    started = time.perf_counter()
    query_vectors = embedder.query([probe.query for probe in probes])
    query_seconds = time.perf_counter() - started
    if len(query_vectors) != len(probes):
        raise _RunError("runtime returned a different number of query vectors")
    orders = {
        probe.id: _vector_order(vectors, vector, frozenset(probe.exclude))
        for probe, vector in zip(probes, query_vectors, strict=True)
    }
    return {
        "import_seconds": round(embedder.import_seconds, 3),
        "load_seconds": round(embedder.load_seconds, 3),
        "passage_seconds": round(passage_seconds, 3),
        "query_seconds": round(query_seconds, 3),
        "ms_per_node": round(1000.0 * passage_seconds / max(len(documents), 1), 3),
        "ms_per_query": round(1000.0 * query_seconds / max(len(probes), 1), 3),
        "metrics": _split_records(orders, probes),
    }


# --- Runtimes ----------------------------------------------------------------


def _load_sentence_transformers(
    candidate: Candidate, cache_dir: Path, local_only: bool
) -> Embedder:
    """Load one candidate through sentence-transformers on CPU torch."""
    started = time.perf_counter()
    module = importlib.import_module("sentence_transformers")
    import_seconds = time.perf_counter() - started
    started = time.perf_counter()
    model = module.SentenceTransformer(
        candidate.model,
        cache_folder=str(cache_dir),
        device="cpu",
        trust_remote_code=candidate.trust_remote_code,
        local_files_only=local_only,
    )
    load_seconds = time.perf_counter() - started

    def encode(texts: Sequence[str], prefix: str) -> list[list[float]]:
        payload = [prefix + text for text in texts] if prefix else list(texts)
        produced = model.encode(
            payload, normalize_embeddings=True, batch_size=32, show_progress_bar=False
        )
        return [[float(value) for value in row] for row in produced]

    return Embedder(
        runtime="sentence-transformers",
        query=lambda texts: encode(texts, candidate.query_prefix),
        passage=lambda texts: encode(texts, candidate.passage_prefix),
        import_seconds=import_seconds,
        load_seconds=load_seconds,
        weight_slug=candidate.model,
    )


def _fastembed_registry(module: ModuleType) -> dict[str, tuple[str, str]]:
    """Return the fastembed registry keyed by lowercased repository id.

    Registry keys are the Hugging Face repository ids fastembed accepts, but
    some differ from the canonical casing (``snowflake/...`` for the
    ``Snowflake/...`` repository), so lookup is case-insensitive and the
    registry's own spelling is what the runtime is asked to load. Each entry
    also names the repository the ONNX weights come from, which is often a
    quantized copy published by the runtime rather than the model's own
    repository; that source is what the weight size must be measured against.
    """
    listing = module.TextEmbedding.list_supported_models()
    registry: dict[str, tuple[str, str]] = {}
    for entry in listing:
        name = entry.get("model", entry.get("model_name", ""))
        if not name:
            continue
        sources = entry.get("sources") or {}
        source = ""
        if isinstance(sources, dict):
            source = str(sources.get("hf", "") or "")
        registry[str(name).lower()] = (str(name), source or str(name))
    return registry


def _load_fastembed(candidate: Candidate, cache_dir: Path, local_only: bool) -> Embedder:
    """Load one candidate through the ONNX path, or report it unavailable.

    Only the models in fastembed's own registry can run through this path, so a
    model the registry does not list is reported as unavailable for the runtime
    rather than silently served by another one. fastembed applies its registry's
    query and passage prefixes internally, so this path ignores the candidate's
    prefix strings and records that in the evidence.
    """
    started = time.perf_counter()
    module = importlib.import_module("fastembed")
    import_seconds = time.perf_counter() - started
    listed = _fastembed_registry(module).get(candidate.model.lower())
    if listed is None:
        raise _CandidateUnavailable(f"fastembed does not list {candidate.model}")
    registry_name, weight_source = listed
    started = time.perf_counter()
    model = module.TextEmbedding(
        model_name=registry_name,
        cache_dir=str(cache_dir),
        local_files_only=local_only,
    )
    load_seconds = time.perf_counter() - started

    def encode(texts: Sequence[str], query: bool) -> list[list[float]]:
        payload = list(texts) if texts else [""]
        produced = model.query_embed(payload) if query else model.passage_embed(payload)
        return [[float(value) for value in list(vector)] for vector in produced]

    return Embedder(
        runtime="fastembed",
        query=lambda texts: encode(texts, True),
        passage=lambda texts: encode(texts, False),
        import_seconds=import_seconds,
        load_seconds=load_seconds,
        weight_slug=weight_source,
    )


Loaders = dict[str, Callable[[Candidate, Path, bool], Embedder]]


def _default_loaders() -> Loaders:
    return {
        "sentence-transformers": _load_sentence_transformers,
        "fastembed": _load_fastembed,
    }


def _cached_entries(cache_dir: Path, model: str) -> dict[Path, set[str]]:
    """Return each real cached file once, with every name the cache gives it.

    The Hugging Face cache keeps one content-addressed blob per file and
    symlinks the snapshot entries to it, so a raw recursive walk double-counts
    every weight. Keying by the resolved path counts a blob once while keeping
    the human-readable snapshot names, which is what a size filter must match.
    """
    root = cache_dir / ("models--" + model.replace("/", "--"))
    if not root.is_dir():
        return {}
    entries: dict[Path, set[str]] = {}
    for path in root.rglob("*"):
        try:
            if not path.is_file():
                continue
            resolved = path.resolve()
        except OSError:
            continue
        if resolved.is_file():
            entries.setdefault(resolved, set()).add(path.name)
    return entries


def _cache_bytes(cache_dir: Path, model: str) -> int:
    """Return the on-disk bytes a model's whole cache directory occupies."""
    return sum(path.stat().st_size for path in _cached_entries(cache_dir, model))


def _weight_bytes(cache_dir: Path, model: str, runtime: str) -> int:
    """Return the bytes of the weights one runtime actually loads.

    A model repository can ship both a safetensors and an ONNX copy, and the
    ONNX path often loads a quantized copy published by the runtime itself, so
    the whole-directory size is not the weight cost either runtime pays. The
    ONNX path loads ``.onnx`` files and their external data; the torch path
    prefers safetensors and falls back to the pickle only when the repository
    has no safetensors file.
    """
    entries = _cached_entries(cache_dir, model)
    if runtime == "fastembed":
        return sum(
            path.stat().st_size
            for path, names in entries.items()
            if any(_is_onnx_name(name) for name in names)
        )
    suffix = ".safetensors"
    if not any(
        name.endswith(suffix) for names in entries.values() for name in names
    ):
        suffix = ".bin"
    return sum(
        path.stat().st_size
        for path, names in entries.items()
        if any(name.endswith(suffix) for name in names)
    )


def _cache_revision(cache_dir: Path, model: str) -> str:
    """Return the resolved upstream revision of the cached weights, or "".

    A snapshot directory is named by the commit the download resolved to, so the
    exact weights a measurement used are recoverable offline from the cache
    alone; nothing here contacts the Hub.
    """
    snapshots = cache_dir / ("models--" + model.replace("/", "--")) / "snapshots"
    if not snapshots.is_dir():
        return ""
    names = sorted(path.name for path in snapshots.iterdir() if path.is_dir())
    return names[0] if names else ""


def _is_onnx_name(name: str) -> bool:
    """Return whether a cached file name holds ONNX weights or their data."""
    return name.endswith(".onnx") or name.startswith("model.onnx")


_RUNTIME_DISTRIBUTIONS = (
    "torch",
    "sentence-transformers",
    "transformers",
    "numpy",
    "onnxruntime",
    "fastembed",
    "huggingface-hub",
)


def host_record() -> dict[str, object]:
    """Return the host and installed runtime versions the measurements describe.

    The torch path and the ONNX path are not equally installable on every
    platform, so a measurement without its host is not reproducible evidence.
    Versions come from installed metadata, which imports nothing heavy.
    """
    versions: dict[str, str] = {}
    for name in _RUNTIME_DISTRIBUTIONS:
        try:
            versions[name] = distribution_version(name)
        except PackageNotFoundError:
            continue
    return {
        "platform": platform.platform(),
        "machine": platform.machine(),
        "python": platform.python_version(),
        "versions": versions,
    }


# --- Run ---------------------------------------------------------------------


def _selected_probes(corpus: Corpus, options: RunOptions) -> tuple[Probe, ...]:
    """Return the probes a bounded run scores, sampled across the whole corpus.

    A bounded selection strides through the probe list instead of taking its
    head, so a small smoke batch still covers both families and both splits
    rather than only the family that sorts first.
    """
    if options.probes_limit is None or options.probes_limit >= len(corpus.probes):
        return corpus.probes
    count = max(options.probes_limit, 1)
    step = len(corpus.probes) / count
    return tuple(corpus.probes[int(position * step)] for position in range(count))


def _selected_corpus(corpus: Corpus, options: RunOptions) -> Corpus:
    """Return the document pool the run embeds, bounded by ``options.limit``.

    The pool always keeps every document the selected probes reference, because
    dropping a positive or an exclusion would make the probe unscorable; the
    remaining budget is filled with the first documents in id order, so a small
    ``--limit`` bounds the embedding cost without changing any probe's answer
    set.
    """
    if options.limit is None:
        return corpus
    referenced = {
        reference
        for probe in _selected_probes(corpus, options)
        for reference in (*probe.positives, *probe.negatives, *probe.exclude)
    }
    kept = [document for document in corpus.documents if document.id in referenced]
    for document in corpus.documents:
        if len(kept) >= options.limit:
            break
        if document.id not in referenced:
            kept.append(document)
    kept.sort(key=lambda document: document.id)
    return Corpus(
        protocol=corpus.protocol,
        nodes_root=corpus.nodes_root,
        revision=corpus.revision,
        documents=tuple(kept),
        probes=corpus.probes,
    )


def run(
    corpus: Corpus,
    options: RunOptions,
    root: Path | None = None,
    embedders: Loaders | None = None,
    cache_dir: Path | None = None,
) -> dict[str, object]:
    """Score every selected candidate and return the evidence document.

    The lexical baseline is scored first, then each runtime loads once per
    candidate. A candidate that cannot run on this platform or in this
    environment is recorded with its reason instead of being dropped, so the
    evidence names every candidate in the comparison. After a model loads, the
    documented cache is re-read with local-only loading to record whether the
    weights are genuinely available offline.
    """
    base = _repo_root() if root is None else root
    cache = semantic.model_cache() if cache_dir is None else cache_dir
    available = _default_loaders() if embedders is None else embedders
    probes = _selected_probes(corpus, options)
    scored = _selected_corpus(corpus, options)
    started = time.perf_counter()
    lexical = _split_records(lexical_orders(scored, probes), probes)
    records: list[dict[str, object]] = []
    for runtime in options.runtimes:
        loader = available.get(runtime)
        if loader is None:
            raise _RunError(f"unknown runtime: {runtime}")
        for candidate in CANDIDATES:
            if options.models and candidate.model not in options.models:
                continue
            record: dict[str, object] = {
                "model": candidate.model,
                "runtime": runtime,
                "license": candidate.license,
                "trust_remote_code": candidate.trust_remote_code,
                "note": candidate.note,
            }
            spent = time.perf_counter() - started
            if options.time_budget is not None and spent > options.time_budget:
                records.append(
                    {**record, "status": "skipped", "reason": "time budget exhausted"}
                )
                continue
            try:
                embedder = loader(candidate, cache, False)
                measured = evaluate(scored, probes, embedder)
                offline = False
                offline_reason = ""
                try:
                    loader(candidate, cache, True)
                    offline = True
                except Exception as error:  # the local cache is what makes it offline
                    offline_reason = f"{type(error).__name__}: {error}"
                records.append(
                    {
                        **record,
                        "status": "ok",
                        **measured,
                        "weight_source": embedder.weight_slug or candidate.model,
                        "weight_revision": _cache_revision(
                            cache, embedder.weight_slug or candidate.model
                        ),
                        "model_cache_bytes": _cache_bytes(
                            cache, embedder.weight_slug or candidate.model
                        ),
                        "weight_bytes": _weight_bytes(
                            cache, embedder.weight_slug or candidate.model, runtime
                        ),
                        "offline": offline,
                        "offline_detail": offline_reason,
                    }
                )
            except _CandidateUnavailable as error:
                records.append({**record, "status": "unavailable", "reason": str(error)})
            except Exception as error:
                records.append(
                    {
                        **record,
                        "status": "unavailable",
                        "reason": f"{type(error).__name__}: {error}",
                    }
                )
    return {
        "protocol": PROTOCOL,
        "note": _NOTE,
        "host": host_record(),
        "batch": {
            "models": list(options.models) or ["all"],
            "runtimes": list(options.runtimes),
            "limit": options.limit,
            "probes_limit": options.probes_limit,
            "time_budget": options.time_budget,
        },
        "corpus": {
            "path": CORPUS_RELATIVE,
            "digest": _corpus_digest(base),
            "source_revision": corpus.revision,
            "nodes_root": corpus.nodes_root,
            "documents": len(scored.documents),
            "probes": len(probes),
            "runtime_seconds": round(time.perf_counter() - started, 3),
        },
        "lexical": lexical,
        "records": records,
    }


# --- Command line ------------------------------------------------------------


_FLAGS = {"--emit", "--verify"}


def _parse_shared(argv: Sequence[str]) -> tuple[dict[str, str], list[str]]:
    """Parse ``--name value`` options, bare flags, and positional arguments."""
    options: dict[str, str] = {}
    positional: list[str] = []
    index = 0
    while index < len(argv):
        token = argv[index]
        if token in {"-h", "--help"}:
            _usage()
            raise SystemExit(0)
        if token.startswith("--"):
            if "=" in token:
                name, _, value = token.partition("=")
            elif token in _FLAGS:
                name, value = token, "true"
            else:
                name = token
                index += 1
                if index >= len(argv):
                    raise _UsageError(f"missing value for {name}")
                value = argv[index]
            options[name] = value
        else:
            positional.append(token)
        index += 1
    return options, positional


def _comma_list(value: str) -> tuple[str, ...]:
    return tuple(item.strip() for item in value.split(",") if item.strip())


def _git_revision() -> str:
    """Return the HEAD revision the corpus was derived from."""
    try:
        result = subprocess.run(
            ["git", "-C", str(_repo_root()), "rev-parse", "HEAD"],
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError:
        return "unknown"
    return result.stdout.strip() if result.returncode == 0 else "unknown"


def _report_corpus(corpus: Corpus) -> None:
    families = sorted({probe.family for probe in corpus.probes})
    splits = sorted({probe.split for probe in corpus.probes})
    print(f'corpus: "{corpus.revision}"')
    print(f"documents: {len(corpus.documents)}")
    print(f"probes: {len(corpus.probes)}")
    print("families{" + ",".join(families) + "}")
    print("splits{" + ",".join(splits) + "}")


def _corpus_command(argv: Sequence[str]) -> int:
    options, positional = _parse_shared(argv)
    if positional:
        raise _UsageError(f"unknown argument: {positional[0]}")
    unknown = set(options) - {"--nodes", "--emit", "--verify"}
    if unknown:
        raise _UsageError(f"unknown option: {sorted(unknown)[0]}")
    if "--verify" in options:
        corpus = load_corpus()
        problems = verify_corpus(corpus, _repo_root())
        for problem in problems:
            print(f"problem: {problem}")
        if problems:
            return 1
        _report_corpus(corpus)
        print("verification: passed")
        return 0
    nodes_root = options.get("--nodes", str(_repo_root() / vault.DIRECTORY_NAME))
    if not os.path.isdir(nodes_root):
        raise _RunError(f"nodes directory does not exist: {nodes_root}")
    corpus = build_corpus(nodes_root, _git_revision())
    problems = verify_corpus(corpus, _repo_root())
    if problems:
        raise _RunError(f"derived corpus is invalid: {problems[0]}")
    _write_corpus(corpus, _repo_root())
    _report_corpus(corpus)
    return 0


def _integer_option(options: dict[str, str], name: str, cast: type[int] | type[float]) -> object:
    raw = options.get(name)
    if raw is None:
        return None
    try:
        return cast(raw)
    except ValueError as error:
        raise _UsageError(f"invalid value for {name}: {raw}") from error


def _run_command(argv: Sequence[str]) -> int:
    options, positional = _parse_shared(argv)
    if positional:
        raise _UsageError(f"unknown argument: {positional[0]}")
    unknown = set(options) - {
        "--models",
        "--runtimes",
        "--limit",
        "--probes",
        "--time-budget",
        "--output",
    }
    if unknown:
        raise _UsageError(f"unknown option: {sorted(unknown)[0]}")
    models = _comma_list(options.get("--models", ""))
    known_models = {candidate.model for candidate in CANDIDATES}
    missing = [model for model in models if model not in known_models]
    if missing:
        raise _UsageError(f"unknown model: {missing[0]}")
    runtimes = _comma_list(options.get("--runtimes", "")) or RUNTIMES
    for runtime in runtimes:
        if runtime not in RUNTIMES:
            raise _UsageError(f"unknown runtime: {runtime}")
    limit = _integer_option(options, "--limit", int)
    probes = _integer_option(options, "--probes", int)
    budget = _integer_option(options, "--time-budget", float)
    run_options = RunOptions(
        models=models,
        runtimes=runtimes,
        limit=limit if isinstance(limit, int) else None,
        probes_limit=probes if isinstance(probes, int) else None,
        time_budget=budget if isinstance(budget, float) else None,
    )
    corpus = load_corpus()
    problems = verify_corpus(corpus, _repo_root())
    if problems:
        raise _RunError(f"committed corpus is invalid: {problems[0]}")
    document = run(corpus, run_options)
    output = Path(options.get("--output", str(_repo_root() / EVIDENCE_RELATIVE)))
    output.write_text(
        json.dumps(document, indent=2, ensure_ascii=False) + "\n", encoding="utf-8"
    )
    _print_report(document)
    print(f"evidence: {output}")
    return 0


def _print_report(document: dict[str, object]) -> None:
    lexical = document["lexical"]
    assert isinstance(lexical, dict)
    overall = lexical["overall"]
    assert isinstance(overall, dict)
    print(
        "lexical{"
        + ",".join(str(name) for name in overall)
        + "}: "
        + ",".join(str(value) for value in overall.values())
    )
    records = document["records"]
    assert isinstance(records, list)
    print(
        f"records[{len(records)}]"
        "{model,runtime,status,mrr,recall@5,load_s,ms_per_node}:"
    )
    for record in records:
        assert isinstance(record, dict)
        metrics = record.get("metrics")
        scored = metrics.get("overall", {}) if isinstance(metrics, dict) else {}
        assert isinstance(scored, dict)
        row = (
            str(record.get("model", "")),
            str(record.get("runtime", "")),
            str(record.get("status", "")),
            str(scored.get("mrr", "")),
            str(scored.get("recall@5", "")),
            str(record.get("load_seconds", "")),
            str(record.get("ms_per_node", "")),
        )
        print('  "' + '","'.join(row) + '"')


def main(argv: Sequence[str] | None = None) -> int:
    """Freeze or verify the corpus, or run the explicit embedding comparison."""
    arguments = list(sys.argv[1:] if argv is None else argv)
    if not arguments:
        _usage()
        return 2
    command = arguments[0]
    try:
        if command == "corpus":
            return _corpus_command(arguments[1:])
        if command == "run":
            return _run_command(arguments[1:])
        if command in {"-h", "--help"}:
            _usage()
            return 0
        raise _UsageError(f"unknown argument: {command}")
    except _UsageError as error:
        print(f"error: {error}", file=sys.stderr)
        _usage()
        return 2
    except _RunError as error:
        print(f"error: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":  # pragma: no cover - module entry point
    raise SystemExit(main())
