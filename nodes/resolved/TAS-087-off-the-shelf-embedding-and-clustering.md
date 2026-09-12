---
context_rev: 1
priority: P1
updated: 2026-09-12T19:40:11Z
summary: Add an optional off-the-shelf embedding and manifold-clustering retrieval layer behind the DEC-006 capability boundary without training any model.
---

# Context

Area [[IDX-001-execution-graph]].

Depends on [[DEC-006-semantic-layer-capability-boundary]] at context_rev 1.

Depends on [[TAS-079-optional-semantic-retrieval]] at context_rev 1.

The direct-answer thrust [[TAS-068-direct-answer-surface]] landed deterministic
verbs, a lexical `similar`, and an optional embedding seam whose provider is an
external command. It did not land off-the-shelf embedding models or manifold
clustering. That exploration proposed those and they were never admitted, so
this thrust admits them now.

Hard constraints:

- No model is trained, fine-tuned, distilled, or shipped as weights authored
  here. Use off-the-shelf Hugging Face sentence-embedding models as-is.
- No Ollama or other external model service. Inference runs in-process in
  Python through an opt-in extra, so the default install keeps
  `dependencies = []`.
- Clustering uses standard manifold and density algorithms (UMAP, t-SNE, PCA,
  HDBSCAN), not a learned model.
- Everything here is advisory and derived under
  [[DEC-006-semantic-layer-capability-boundary]]. Every core answer is identical
  when the capability is absent, and the lexical baseline stays the correctness
  reference.

This is a user-requested plan, so the children are created up front as proposed
work and are resolved or disposed as reality arrives.

Planned order:

1. [[TAS-088-optional-embedding-extra]] - opt-in dependencies and an offline
   model cache without changing the default install.
2. [[TAS-089-embedding-model-selection]] - choose the off-the-shelf models and
   the inference runtime.
3. [[TAS-090-native-embedding-provider]] - implement the native Python provider
   behind the existing probe.
4. [[TAS-091-manifold-reduction]] - UMAP, t-SNE, and PCA coordinates.
5. [[TAS-092-density-clustering]] - HDBSCAN clusters and outliers.
6. [[TAS-093-cluster-answer-verbs]] - expose clusters, reranked retrieval, and
   digests.
7. [[TAS-094-clustering-quality-gate]] - cluster-quality and round-trip
   evidence with a keep, revise, or revert decision.

Theory under test: [[THO-012-embedding-clustering-retrieval-theory]].

# Outcome

An operator who installs the optional extra can compute off-the-shelf
embeddings, reduce them with UMAP or t-SNE, cluster them with HDBSCAN, and get
advisory cluster, near-duplicate, and outlier answers from `braintree` directly,
with no model training and no change to the default install.

# Done when

- Every child is resolved or disposed with rationale.
- The default install still has zero runtime dependencies and every command is
  byte-identical without the capability.
- The chosen embedding models, reduction, and clustering are off-the-shelf and
  documented with their versions.
- `make test` passes.

# Result

All eight children resolved; none was disposed or blocked. The thrust landed an
opt-in, derived, advisory layer behind
[[DEC-006-semantic-layer-capability-boundary]]; nothing in it is authoritative
and the default install is unchanged.

- [[TAS-088-optional-embedding-extra]] - a `semantic` extra pins the shipped
  inference and clustering libraries while `dependencies = []` is preserved,
  with a documented offline model cache.
- [[TAS-089-embedding-model-selection]] - fastembed on ONNX Runtime is the
  shipped runtime, `sentence-transformers/all-MiniLM-L6-v2` is the default and
  `BAAI/bge-small-en-v1.5` the fallback; no candidate beat the lexical baseline
  across the fixed corpus.
- [[TAS-090-native-embedding-provider]] - `braintree semantic embed` speaks the
  existing stdin/stdout seam, loads the model once per process, reads only the
  local cache, and degrades to lexical on a cold cache.
- [[TAS-091-manifold-reduction]] - deterministic UMAP with PCA and t-SNE
  comparisons, cached by content hash and parameters.
- [[TAS-092-density-clustering]] - advisory HDBSCAN over the raw and reduced
  spaces with explicit noise and a separate outlier view.
- [[TAS-093-cluster-answer-verbs]] - bounded `clusters`, embedding-reranked
  `similar`, and a graph-only `digest`, byte-identical when the capability is
  absent.
- [[TAS-094-clustering-quality-gate]] - `braintree benchmark quality` records
  stability, route agreement, retrieval, outlier, and token evidence and
  decides retrieval -> revise, clustering -> revise, digest -> keep.
- [[THO-012-embedding-clustering-retrieval-theory]] - the strong hypothesis is
  rejected (embeddings lose near-duplicate retrieval and clusters do not
  recover the graph's routes) and the narrow one accepted (paraphrase recall and
  a bounded advisory answer surface at zero training and zero default
  dependencies).

The default install keeps `dependencies = []`, the dev environment imports no
heavy module, and every capability-absent answer is byte-identical to the
lexical baseline. `braintree check nodes`, `braintree index nodes`, `make test`
(370 passed, 3 heavy-module skips), and `make verb-benchmark` pass.
