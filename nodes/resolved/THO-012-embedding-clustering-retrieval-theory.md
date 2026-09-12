---
context_rev: 1
updated: 2026-09-12T19:37:00Z
summary: "Settled: off-the-shelf embeddings and HDBSCAN lose near-duplicate retrieval to the lexical baseline and do not recover graph routes; kept only as an optional advisory paraphrase and digest layer."
---

# Question

Parent [[TAS-087-off-the-shelf-embedding-and-clustering]].

Do off-the-shelf sentence embeddings, reduced with UMAP or t-SNE and clustered
with HDBSCAN, improve near-duplicate admission and advisory grouping for the
vault, and reduce client round trips, without training a model and without
weakening the deterministic lexical baseline?

# Hypothesis

Lexical retrieval misses paraphrases that share no tokens, so an agent
re-derives near-duplicates and hand-groups the frontier. Off-the-shelf
embeddings close the paraphrase gap, and manifold plus density clustering turn
the derived embedding space into advisory clusters and outliers a client can
consume in one bounded answer. Because the models are used as published and the
results are advisory and derived, correctness never depends on the capability
and the default install is unchanged.

# Prediction

Cluster and near-duplicate answers computed from published embeddings agree with
the graph's own routes more often than the lexical baseline, and replace several
shell or search round trips with one bounded command. A trained model is not
required for the gain, and under
[[DEC-006-semantic-layer-capability-boundary]] every core answer is identical
when the capability is absent.

# Test

- Model and runtime selection: [[TAS-089-embedding-model-selection]].
- Native provider: [[TAS-090-native-embedding-provider]].
- Manifold and density reduction: [[TAS-091-manifold-reduction]] and
  [[TAS-092-density-clustering]].
- Answer surface: [[TAS-093-cluster-answer-verbs]].
- Quality and round-trip gate: [[TAS-094-clustering-quality-gate]].

# Evidence

Measured on the frozen 118-document, 76-probe corpus by the resolved children;
`benchmark/clustering-quality-evidence.json` is the committed record that
`braintree benchmark quality verify` re-checks offline.

Retrieval against the lexical baseline, same probes and documents
([[TAS-089-embedding-model-selection]],
[[TAS-094-clustering-quality-gate]]):

```text
retrieval{family,probes,lexical_mrr,embedding_mrr,lexical_recall@5,embedding_recall@5}:
  near-duplicate,30,0.5856,0.4420,0.9667,0.7667
  paraphrase,46,0.1866,0.2532,0.3261,0.4130
  overall,76,0.3441,0.3277,0.5789,0.5526
```

Clustering of the same 118 documents ([[TAS-092-density-clustering]],
[[TAS-094-clustering-quality-gate]]):

```text
clustering{space,clusters,noise,members,over_broad,min_cluster_size,min_samples}:
  raw,3,65,118,2,6,2
stability{space,runs,ari}: raw,10,0.6445 | reduced,10,0.5132
route_agreement{distinct_routes,ari,purity}: 21,0.0307,0.3136
outlier{threshold,flagged,graph_isolated,true_outliers,false_outliers,recall}:
  0.9,0,7,0,0,0.0; sweep 0.8..0.4 all flag 0
```

Supporting measurements: [[TAS-088-optional-embedding-extra]] keeps
`dependencies = []` with the layer in an opt-in extra;
[[TAS-090-native-embedding-provider]] ships the in-process provider behind the
existing seam and reports a paraphrase rerank it wins;
[[TAS-093-cluster-answer-verbs]] lands `clusters`, the reranked `similar`, and
the graph-only `digest`, with the capability-absent `clusters` line at exit 0
byte-identical to the unconfigured run; and
[[TAS-094-clustering-quality-gate]] passes `braintree benchmark verbs --verify`
with no live call and records the retrieval/clustering `revise` and digest
`keep` decisions. The chosen cluster space is snapshot- and corpus-dependent:
[[TAS-093-cluster-answer-verbs]] chose the reduced UMAP space on the live
vault, while [[TAS-094-clustering-quality-gate]]'s frozen-corpus run chose the
raw space.

# Conclusion

The strong hypothesis is REJECTED in its strong form. Off-the-shelf embeddings
do not improve near-duplicate admission and HDBSCAN does not recover the
graph's own routes:

- Near-duplicate retrieval LOSES to the lexical baseline: MRR 0.4420 against
  0.5856 and recall@5 0.7667 against 0.9667, with the whole set also trailing
  (0.3277 against 0.3441). Embedding cosine is not a better near-duplicate or
  admission signal than the shipped lexical metric.
- Clusters do NOT recover the graph's routes: route-agreement ARI 0.0307 and
  purity 0.3136 across 21 distinct routes, with 65 of 118 nodes left as noise.
  The raw partition is stable across seeds and subsamples (ARI 0.6445 against
  0.5132 for the reduced space), but that stability is partly agreement about
  noise, not agreement about routes.
- The outlier view is inert: 0 nodes flagged at the default 0.9 threshold and
  at every swept threshold down to 0.4, against 7 graph-isolated nodes.
- The stated `Prediction` that cluster and near-duplicate answers agree with
  the graph's own routes more often than the lexical baseline is false on both
  halves (near-duplicate admission and route recovery).

Narrow support is ACCEPTED. The layer earns a bounded, opt-in place:

- Paraphrase recall improves where lexical search has no tokens to match: MRR
  0.2532 against 0.1866 and recall@5 0.4130 against 0.3261.
- It adds one bounded advisory answer surface (`clusters`, the reranked
  `similar`, and the graph-only `digest`) with zero model training, an
  unchanged `dependencies = []` default install, and byte-identical
  capability-absent behavior under
  [[DEC-006-semantic-layer-capability-boundary]].
- Per [[TAS-094-clustering-quality-gate]], `digest` keeps while retrieval and
  clustering are revised and advisory only. No trained model is needed for the
  paraphrase gain, which is the part of the `Prediction` that held.

Verdict: the lexical answer stays the correctness reference; the off-the-shelf
layer is kept only as optional, advisory, derived insight -- not as a
near-duplicate admission improvement and not as route recovery. The
round-trip half of the `Prediction` is unsettled rather than supported:
round-trip counts are unavailable in the committed records, so it is disposed
against [[TAS-094-clustering-quality-gate]]'s bounded open item (cf.
[[TAS-080-staged-token-ab]]) rather than restated.

No new node is admitted. The rejection creates no independently resumable
future action that no existing node owns:
[[TAS-094-clustering-quality-gate]] already records the retrieval and
clustering `revise` decisions and the inert outlier view, so the residual is
dispositioned here instead of as a new leaf. This settles an unanswered
question that no consumer pins, so `context_rev` stays `1`; there is no pinned
consumer to reread.
