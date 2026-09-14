---
status: resolved
context_rev: 1
priority: P1
updated: 2026-09-14T23:40:13Z
summary: Gate the embedding and clustering layer with cluster-quality, retrieval, and round-trip evidence plus an explicit keep, revise, or revert decision.
---

# Context

Parent [[TAS-087-off-the-shelf-embedding-and-clustering]].

Depends on [[TAS-093-cluster-answer-verbs]] at context_rev 1.

Depends on [[TAS-078-round-trip-telemetry-and-gates]] at context_rev 1.

Depends on [[DEC-006-semantic-layer-capability-boundary]] at context_rev 1.

The capability boundary keeps the layer optional, but it must still earn its
cost. This task measures the layer against the lexical baseline and the graph's
own weak labels, and decides whether to keep, revise, or revert each answer.

# Outcome

A recorded, correctness-gated comparison of the embedding and clustering layer
against the lexical baseline, with a keep, revise, or revert decision for the
retrieval, clustering, and digest answers.

# Done when

- Cluster quality is measured by stability (ARI or AMI across seeds and
  subsamples) and by agreement with graph routes as weak ground truth.
- Near-duplicate retrieval is measured against the lexical baseline using the
  same fixed corpus from [[TAS-089-embedding-model-selection]].
- Round trips and tokens are compared with and without the capability using the
  existing benchmark harness, and every sample passes its exact-value gate.
- Outlier precision is reported, and false outliers are quantified.
- Each answer records keep, revise, or revert with its rationale, and the
  comparison is reproducible offline from committed fixtures.
- `make test` passes.

# Result

The gate landed as `braintree benchmark quality` (`src/braintree/quality_benchmark.py`,
registered in `main.py`). `emit` measures on the committed TAS-089 corpus
(`benchmark/embedding-corpus.json` plus `benchmark/embedding-documents.jsonl`:
118 documents and 76 probes frozen at revision `5c8faeb4`) and writes
`benchmark/clustering-quality-evidence.json`; `verify` re-checks the corpus
digest, the lexical baseline, the route parse, the decision shape, and the verb
gate fully offline. The embedding and clustering side reuses the shipped seams
(`braintree.semantic`, `braintree.reduction`, `braintree.clustering`), so the
evidence describes the answers `braintree similar` and `braintree clusters`
actually give and not a reimplementation. Nothing is trained, and no command on
the interactive path loads a model.

The verdict is derived from declared quality bars, not asserted: retrieval keeps
only if embedding near-duplicate MRR reaches lexical and revises when it loses
there but wins another family; clustering keeps at stability >= 0.5, route
agreement ARI >= 0.3, and noise share <= 0.5, revises when a stable partition
fails either of the latter, and reverts when unstable; the digest keeps when the
verb gate proves its bounded answer exact.

Measured on the frozen corpus (hash-order inputs, exactly as `index.cluster_source`
orders them; two independent `emit` runs wrote byte-identical evidence). Routes
are parsed from the committed bodies: 117 of 118 documents route, 1 is routeless,
and there are 21 distinct routes.

```text
retrieval{family,probes,lexical_mrr,lexical_recall@5,embedding_mrr,embedding_recall@5,delta_mrr}:
  overall,76,0.3441,0.5789,0.3277,0.5526,-0.0164
  near-duplicate,30,0.5856,0.9667,0.4420,0.7667,-0.1436
  paraphrase,46,0.1866,0.3261,0.2532,0.4130,+0.0666

clustering{space,clusters,noise,members,over_broad,min_cluster_size,min_samples}:
  raw,3,65,118,2,6,2
stability{space,runs,ari}: raw,10,0.6445 | reduced,10,0.5132
route_agreement{distinct_routes,ari,purity}: 21,0.0307,0.3136
outlier{threshold,flagged,graph_isolated,true_outliers,false_outliers,precision,recall}:
  0.9,0,7,0,0,n/a,0.0; sweep 0.8..0.4 all flag 0
answer_surface{verb_gate}: passed{frontier,node,impact,orient,check-toon=1,digest,clusters}
staged{uncached_delta,total_delta}: -1102,+38370 (round trips unavailable in the committed records)
```

Decisions:

- **retrieval -> revise.** Embedding cosine loses near-duplicate retrieval to
  the lexical baseline (MRR 0.4420 against 0.5856; recall@5 0.7667 against
  0.9667) but improves paraphrase recall (MRR 0.2532 against 0.1866), and it
  trails on the whole set (0.3277 against 0.3441). Keep the opt-in rerank where
  it helps and keep lexical as the near-duplicate and admission reference; do
  not present the rerank as a retrieval improvement. A full revert is not
  warranted because the paraphrase gain is real and the absent path is
  byte-identical, and it would reach `index.py`/`cli.py`, outside this slice.
- **clustering -> revise.** The chosen raw partition reproduces across seeds and
  seeded subsamples (ARI 0.6445 against 0.5132 for the reduced space), but it
  agrees weakly with the graph's own routes (ARI 0.0307, purity 0.3136), leaves
  65 of 118 nodes as noise, and the GLOSH outlier view flags nothing at the
  default 0.9 threshold or any swept threshold down to 0.4. Keep the advisory
  grouping and correct the claims: high stability is partly agreement about
  noise, the clusters do not recover settled routes, and the outlier view is
  inert on this corpus. A stable-but-weak answer is a revise, not a keep, and
  reverting the whole answer would reach beyond this slice.
- **digest -> keep.** It is graph-only and needs no capability, its bounded
  answer is exact (`braintree benchmark verbs --verify` passes `digest` at exit
  0), and it adds no dependency.

No landed verb was reverted, so no reversal record is due. The round-trip and
token side reuses the existing harnesses with no live call:
`braintree benchmark verbs --verify` gates every answer (including `clusters`
and `digest`) exactly, the capability-absent `clusters` answer is the recorded
`clusters: "capability absent"` at exit 0 with no model loaded, and
`braintree benchmark staged` compares the committed matched token records
(`token-ab-tight` to `token-ab-current`: uncached -1102, total +38370, revise).
Round-trip counts are unavailable in those records because they predate the
telemetry; measuring the agent-level round-trip delta of the new answers needs
one bounded matched live Codex pair, which is not authorized, so it is recorded
as the evidence's bounded open item exactly as [[TAS-080-staged-token-ab]] is.
Outlier precision is reported as vacuous at the default threshold (0 flagged, 7
graph-isolated, 0 false outliers) and 0 across the sweep, which is the honest
"the view never fires" result rather than a precision number.

`tests/test_quality_benchmark.py` covers the route parse, both rankings on the
same probes, the stability/agreement/outlier record, the empty-embedding
refusal, every decision branch, offline `emit` determinism against the committed
corpus, `verify` on the committed evidence and on a corrupted copy, and a fresh
interpreter proving `benchmark quality verify` loads no heavy module. Adding
`src/braintree/quality_benchmark.py` moved the token benchmark's composite
local-fixture file count from 73 to 74, updated in the same change.
`braintree check nodes`, `braintree index nodes`, `make test`, and
`make verb-benchmark` pass. Resolving this node advanced the parent's `next` to
[[THO-012-embedding-clustering-retrieval-theory]].
