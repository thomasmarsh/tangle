---
context_rev: 1
priority: P1
updated: 2026-09-12T17:22:00Z
summary: Gate the embedding and clustering layer with cluster-quality, retrieval, and round-trip evidence plus an explicit keep, revise, or revert decision.
next: Define the quality and round-trip gates and record baseline samples.
---

# Context

Parent [[TAS-087-off-the-shelf-embedding-and-clustering]].

Gated on [[TAS-093-cluster-answer-verbs]].

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
